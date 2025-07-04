# Copyright (C) 2024-present Naver Corporation. All rights reserved.
# Licensed under CC BY-NC-SA 4.0 (non-commercial use only).
#
# --------------------------------------------------------
# post process function for all heads: extract 3D points/confidence from output
# --------------------------------------------------------
import torch


def postprocess(out, depth_mode, conf_mode):
    """
    extract 3D points/confidence from prediction head output
    """
    fmap = out.permute(0, 2, 3, 1)  # B,H,W,3
    res = dict(pts3d=reg_dense_depth(fmap[:, :, :, 0:3], mode=depth_mode))
    
    if conf_mode is not None:
        res['conf'] = reg_dense_conf(fmap[:, :, :, 3], mode=conf_mode)
    return res


def reg_dense_depth(xyz, mode):
    """
    extract 3D points from prediction head output
    """
    mode, vmin, vmax = mode

    no_bounds = (vmin == -float('inf')) and (vmax == float('inf'))
    # assert no_bounds

    if mode == 'range':
        xyz = xyz.sigmoid()
        xyz = (1 - xyz) * vmin + xyz * vmax
        return xyz

    if mode == 'linear':
        if no_bounds:
            return xyz  # [-inf, +inf]
        return xyz.clip(min=vmin, max=vmax)

    if mode == 'exp_direct':
        xyz = xyz.expm1()
        return xyz.clip(min=vmin, max=vmax)

    # distance to origin
    d = xyz.norm(dim=-1, keepdim=True)
    xyz = xyz / d.clip(min=1e-8)

    if mode == 'square':
        return xyz * d.square()

    if mode == 'exp':
        exp_d = d.expm1()
        if not no_bounds:
            exp_d = exp_d.clip(min=vmin, max=vmax)
        xyz = xyz * exp_d
        # if not no_bounds:
        #     # xyz = xyz.clip(min=vmin, max=vmax)
        #     depth = xyz.clone()[..., 2].clip(min=vmin, max=vmax)
        #     xyz = torch.cat([xyz[..., :2], depth.unsqueeze(-1)], dim=-1)
        return xyz

    raise ValueError(f'bad {mode=}')


def reg_dense_conf(x, mode):
    """
    extract confidence from prediction head output
    """
    mode, vmin, vmax = mode
    if mode == 'opacity':
        return x.sigmoid()
    if mode == 'exp':
        return vmin + x.exp().clip(max=vmax-vmin)
    if mode == 'sigmoid':
        return (vmax - vmin) * torch.sigmoid(x) + vmin
    raise ValueError(f'bad {mode=}')
