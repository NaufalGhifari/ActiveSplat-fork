import os

import numpy as np
import random
import torch
import cv2
from imgviz import depth2rgb


def seed_everything(seed=42):
    """
        Set the `seed` value for torch and numpy seeds. Also turns on
        deterministic execution for cudnn.
        
        Parameters:
        - seed:     A hashable seed value
    """
    random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    print(f"Seed set to: {seed} (type: {type(seed)})")


def params2cpu(params):
    res = {}
    for k, v in params.items():
        if isinstance(v, torch.Tensor):
            res[k] = v.detach().cpu().contiguous().numpy()
        else:
            res[k] = v
    return res


def save_gaussians_ply(params_cpu, ply_path):
    """Export 3D Gaussians to a binary little-endian PLY file compatible with both
    3DGS viewers (f_dc, opacity, scale, rot) and point-cloud viewers (red, green, blue).
    """
    xyz = np.asarray(params_cpu['means3D'], dtype=np.float32)
    num_pts = xyz.shape[0]
    normals = np.zeros_like(xyz, dtype=np.float32)

    rgb = np.clip(np.asarray(params_cpu['rgb_colors'], dtype=np.float32), 0.0, 1.0)
    C0 = 0.28209479177387814
    f_dc = ((rgb - 0.5) / C0).astype(np.float32)
    rgb_u8 = np.clip(np.rint(rgb * 255.0), 0, 255).astype(np.uint8)

    opacities = np.asarray(params_cpu['logit_opacities'], dtype=np.float32).reshape(num_pts, 1)

    scales = np.asarray(params_cpu['log_scales'], dtype=np.float32)
    if scales.ndim == 1:
        scales = scales.reshape(num_pts, 1)
    if scales.shape[1] == 1:
        scales = np.repeat(scales, 3, axis=1)

    rots = np.asarray(params_cpu['unnorm_rotations'], dtype=np.float32).reshape(num_pts, 4)
    rot_norms = np.linalg.norm(rots, axis=1, keepdims=True)
    rots = rots / np.maximum(rot_norms, 1e-8)

    dtype_full = [
        ('x', '<f4'), ('y', '<f4'), ('z', '<f4'),
        ('nx', '<f4'), ('ny', '<f4'), ('nz', '<f4'),
        ('f_dc_0', '<f4'), ('f_dc_1', '<f4'), ('f_dc_2', '<f4'),
        ('opacity', '<f4'),
        ('scale_0', '<f4'), ('scale_1', '<f4'), ('scale_2', '<f4'),
        ('rot_0', '<f4'), ('rot_1', '<f4'), ('rot_2', '<f4'), ('rot_3', '<f4'),
        ('red', 'u1'), ('green', 'u1'), ('blue', 'u1'),
    ]
    elements = np.empty(num_pts, dtype=dtype_full)
    float_attrs = np.hstack((xyz, normals, f_dc, opacities, scales, rots))
    float_names = [
        'x', 'y', 'z', 'nx', 'ny', 'nz',
        'f_dc_0', 'f_dc_1', 'f_dc_2', 'opacity',
        'scale_0', 'scale_1', 'scale_2',
        'rot_0', 'rot_1', 'rot_2', 'rot_3',
    ]
    for idx, name in enumerate(float_names):
        elements[name] = float_attrs[:, idx]
    elements['red'] = rgb_u8[:, 0]
    elements['green'] = rgb_u8[:, 1]
    elements['blue'] = rgb_u8[:, 2]

    header_lines = [
        "ply",
        "format binary_little_endian 1.0",
        f"element vertex {num_pts}",
    ]
    for name in float_names:
        header_lines.append(f"property float {name}")
    header_lines.extend([
        "property uchar red",
        "property uchar green",
        "property uchar blue",
        "end_header\n",
    ])
    header_bytes = "\n".join(header_lines).encode("ascii")
    with open(ply_path, "wb") as f:
        f.write(header_bytes)
        f.write(elements.tobytes())
    print(f"Saved 3DGS PLY ({num_pts} Gaussians) to: {ply_path}")


def save_params(output_params, output_dir):
    # Convert to CPU Numpy Arrays
    to_save = params2cpu(output_params)
    # Save the Parameters containing the Gaussian Trajectories
    os.makedirs(output_dir, exist_ok=True)
    print(f"Saving parameters to: {output_dir}")
    save_path = os.path.join(output_dir, "params.npz")
    np.savez(save_path, **to_save)
    if 'means3D' in to_save and 'rgb_colors' in to_save:
        ply_path = os.path.join(output_dir, "point_cloud.ply")
        save_gaussians_ply(to_save, ply_path)
    
def save_keyframes(keyframe_list, keyframe_dir, rgbd_sensor):
    os.makedirs(keyframe_dir, exist_ok=True)
    for keyframe in keyframe_list:
        # save color and depth
        color_vis:np.ndarray = torch.permute(keyframe['color'], (1, 2, 0)).detach().cpu().numpy()
        color_vis = np.clip(color_vis, 0, 1)
        color_vis = np.uint8(color_vis * 255)
        depth_vis:np.ndarray = keyframe['depth'].float().detach().cpu().numpy()
        depth_vis = depth_vis.reshape(rgbd_sensor.height, rgbd_sensor.width)
        depth_vis = depth2rgb(depth_vis, min_value=rgbd_sensor.depth_min, max_value=rgbd_sensor.depth_max)
        cur_frame_id = keyframe['id']
        
        rgbd = np.hstack((color_vis, depth_vis)) # (H, W*2, 3)
        cv2.imwrite(os.path.join(keyframe_dir, f"{str(cur_frame_id).zfill(4)}.png"), cv2.cvtColor(rgbd, cv2.COLOR_RGB2BGR))
        
def save_params_ckpt(output_params, output_dir, time_idx):
    # Convert to CPU Numpy Arrays
    to_save = params2cpu(output_params)
    # Save the Parameters containing the Gaussian Trajectories
    os.makedirs(output_dir, exist_ok=True)
    print(f"Saving parameters to: {output_dir}")
    save_path = os.path.join(output_dir, "params"+str(time_idx)+".npz")
    np.savez(save_path, **to_save)


def save_seq_params(all_params, output_dir):
    params_to_save = {}
    for frame_idx, params in enumerate(all_params):
        params_to_save[f"frame_{frame_idx}"] = params2cpu(params)
    # Save the Parameters containing the Sequence of Gaussians
    os.makedirs(output_dir, exist_ok=True)
    print(f"Saving parameters to: {output_dir}")
    save_path = os.path.join(output_dir, "params.npz")
    np.savez(save_path, **params_to_save)


def save_seq_params_ckpt(all_params, output_dir,time_idx):
    params_to_save = {}
    for frame_idx, params in enumerate(all_params):
        params_to_save[f"frame_{frame_idx}"] = params2cpu(params)
    # Save the Parameters containing the Sequence of Gaussians
    os.makedirs(output_dir, exist_ok=True)
    print(f"Saving parameters to: {output_dir}")
    save_path = os.path.join(output_dir, "params"+str(time_idx)+".npz")
    np.savez(save_path, **params_to_save)