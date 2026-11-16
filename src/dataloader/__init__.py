import os
import re
import json
import struct
import shutil
from typing import Tuple, Union
from enum import Enum
import cv2
import numpy as np
import torch
import quaternion
import trimesh
from trimesh import visual
import open3d as o3d

import rospy

from geometry_msgs.msg import Point, Pose, Quaternion

from activesplat.srv import GetDatasetConfigResponse
from utils import OPENCV_TO_OPENGL

HABITAT_TRANSFORM_MATRIX = np.array([
    [1, 0, 0, 0],
    [0, 0, -1, 0],
    [0, 1, 0, 0],
    [0, 0, 0, 1]
])

class PoseDataType(Enum):
    C2W_OPENCV = 'C2W_OPENCV'
    C2W_OPENGL = 'C2W_OPENGL'
    W2C_OPENCV = 'W2C_OPENCV'
    W2C_OPENGL = 'W2C_OPENGL'
    
class HeightDirection(Enum):
    X_NEGATIVE = 0
    X_POSITIVE = 1
    Y_NEGATIVE = 2
    Y_POSITIVE = 3
    Z_NEGATIVE = 4
    Z_POSITIVE = 5

class DatasetFormats(Enum):
    MP3D = 'mp3d'
    GIBSON = 'gibson'
    REPLICA = 'replica'
    
def convert_to_c2w_opencv(c2w:np.ndarray, pose_data_type:PoseDataType) -> np.ndarray:
    if pose_data_type in [PoseDataType.C2W_OPENGL, PoseDataType.W2C_OPENGL]:
        # NOTE: Convert to OpenCV coordinate system
        c2w = OPENCV_TO_OPENGL @ c2w @ OPENCV_TO_OPENGL
    if pose_data_type in [PoseDataType.W2C_OPENCV, PoseDataType.W2C_OPENGL]:
        # NOTE: Convert to c2w
        c2w = np.linalg.inv(c2w)
    return c2w
    
def _ensure_replica_stage_habitat(scene_dir:str) -> Tuple[str, str]:
    """Ensure stage_habitat.glb and stage_habitat.navmesh exist for a Replica scene.
    Supports both raw Replica scenes (mesh.ply + habitat/mesh_semantic.navmesh)
    and preprocessed scenes (stage.ply + mesh.navmesh).
    """
    stage_ply = os.path.join(scene_dir, 'stage.ply')
    mesh_ply = os.path.join(scene_dir, 'mesh.ply')
    scene_mesh_url = stage_ply if os.path.exists(stage_ply) else mesh_ply

    habitat_mesh_url = os.path.join(scene_dir, 'stage_habitat.glb')
    if not os.path.exists(habitat_mesh_url) and os.path.exists(scene_mesh_url):
        msg = f"stage_habitat.glb not found in {scene_dir}, generating a new one from {os.path.basename(scene_mesh_url)}..."
        print(f"[ActiveSplat] {msg}")
        rospy.loginfo(msg)
        m = trimesh.load(scene_mesh_url)
        if isinstance(m, trimesh.Scene):
            m = m.dump(concatenate=True)
        verts = np.asarray(m.vertices, dtype=np.float32)
        faces = np.asarray(m.faces, dtype=np.uint32)
        mesh_visual = m.visual
        if isinstance(mesh_visual, visual.TextureVisuals):
            mesh_visual = mesh_visual.to_color()
        colors = np.asarray(mesh_visual.vertex_colors, dtype=np.uint8)
        if colors.shape[1] == 3:
            colors = np.hstack([colors, np.full((len(colors), 1), 255, dtype=np.uint8)])

        v_bin, c_bin, f_bin = verts.tobytes(), colors.tobytes(), faces.tobytes()
        pad = lambda b: b + b'\x00' * ((4 - len(b) % 4) % 4)
        v_bin, c_bin, f_bin = pad(v_bin), pad(c_bin), pad(f_bin)
        blob = v_bin + c_bin + f_bin

        gltf = {
            'asset': {'version': '2.0'},
            'scene': 0,
            'scenes': [{'nodes': [0]}],
            'nodes': [{'mesh': 0}],
            'materials': [{
                'pbrMetallicRoughness': {
                    'baseColorFactor': [1.0, 1.0, 1.0, 1.0],
                    'metallicFactor': 0.0,
                    'roughnessFactor': 1.0,
                }
            }],
            'meshes': [{
                'primitives': [{
                    'attributes': {'POSITION': 0, 'COLOR_0': 1},
                    'indices': 2,
                    'material': 0,
                    'mode': 4,
                }]
            }],
            'accessors': [
                {
                    'bufferView': 0,
                    'componentType': 5126,
                    'count': len(verts),
                    'type': 'VEC3',
                    'min': verts.min(axis=0).tolist(),
                    'max': verts.max(axis=0).tolist(),
                },
                {
                    'bufferView': 1,
                    'componentType': 5121,
                    'normalized': True,
                    'count': len(colors),
                    'type': 'VEC4',
                },
                {
                    'bufferView': 2,
                    'componentType': 5125,
                    'count': int(faces.size),
                    'type': 'SCALAR',
                },
            ],
            'bufferViews': [
                {'buffer': 0, 'byteOffset': 0, 'byteLength': len(v_bin), 'target': 34962},
                {'buffer': 0, 'byteOffset': len(v_bin), 'byteLength': len(c_bin), 'target': 34962},
                {'buffer': 0, 'byteOffset': len(v_bin) + len(c_bin), 'byteLength': len(f_bin), 'target': 34963},
            ],
            'buffers': [{'byteLength': len(blob)}],
        }
        jb = json.dumps(gltf, separators=(',', ':')).encode('utf-8')
        jb += b' ' * ((4 - len(jb) % 4) % 4)
        total = 12 + 8 + len(jb) + 8 + len(blob)
        with open(habitat_mesh_url, 'wb') as f:
            f.write(struct.pack('<III', 0x46546C67, 2, total))
            f.write(struct.pack('<II', len(jb), 0x4E4F534A) + jb)
            f.write(struct.pack('<II', len(blob), 0x004E4942) + blob)
        done_msg = f"Saved {habitat_mesh_url} ({len(verts)} vertices, {len(faces)} triangles)."
        print(f"[ActiveSplat] {done_msg}")
        rospy.loginfo(done_msg)

    target_navmesh = os.path.join(scene_dir, 'stage_habitat.navmesh')
    if not os.path.exists(target_navmesh):
        navmesh_candidates = [
            os.path.join(scene_dir, 'mesh.navmesh'),
            os.path.join(scene_dir, 'habitat', 'mesh_semantic.navmesh'),
            os.path.join(scene_dir, 'habitat', 'mesh_preseg_semantic.navmesh'),
        ]
        for candidate in navmesh_candidates:
            if os.path.exists(candidate):
                nav_msg = f"stage_habitat.navmesh not found in {scene_dir}, copying from {candidate}..."
                print(f"[ActiveSplat] {nav_msg}")
                rospy.loginfo(nav_msg)
                shutil.copyfile(candidate, target_navmesh)
                break

    return habitat_mesh_url, scene_mesh_url


def get_scene_mesh_url(dataset_format:DatasetFormats, dataset_root_url:str, scene_id:str) -> Tuple[Union[str, None], Union[str, None]]:
    assert dataset_format in DatasetFormats, f"Invalid dataset format: {dataset_format.name}"
    if dataset_format == DatasetFormats.MP3D:
        habitat_mesh_url = os.path.join(dataset_root_url, 'v1', 'tasks', scene_id, f'{scene_id}.glb')
        scene_mesh_url = os.path.join(dataset_root_url, 'v1', 'tasks', scene_id, f'{scene_id}_semantic.ply')
    elif dataset_format == DatasetFormats.GIBSON:
        habitat_mesh_url = scene_mesh_url = os.path.join(dataset_root_url, f'{scene_id}.glb')
    elif dataset_format == DatasetFormats.REPLICA:
        scene_dir = os.path.join(dataset_root_url, scene_id)
        habitat_mesh_url, scene_mesh_url = _ensure_replica_stage_habitat(scene_dir)
    else:
        raise NotImplementedError(f"Dataset format: {dataset_format.name} not implemented")
    return habitat_mesh_url, scene_mesh_url

CV_FILENODE_TYPE = {
    cv2.FILE_NODE_NONE: 'FILE_NODE_NONE',
    cv2.FILE_NODE_INT: 'FILE_NODE_INT',
    cv2.FILE_NODE_REAL: 'FILE_NODE_REAL',
    cv2.FILE_NODE_STRING: 'FILE_NODE_STRING',
    cv2.FILE_NODE_SEQ: 'FILE_NODE_SEQ',
    cv2.FILE_NODE_MAP: 'FILE_NODE_MAP',
    cv2.FILE_NODE_TYPE_MASK: 'FILE_NODE_TYPE_MASK',
    cv2.FILE_NODE_FLOAT: 'FILE_NODE_FLOAT',
    cv2.FILE_NODE_FLOW: 'FILE_NODE_FLOW',
    cv2.FILE_NODE_STR: 'FILE_NODE_STR',
    cv2.FILE_NODE_UNIFORM: 'FILE_NODE_UNIFORM',
    cv2.FILE_NODE_EMPTY: 'FILE_NODE_EMPTY',
    cv2.FILE_NODE_NAMED: 'FILE_NODE_NAMED'
}
# print(json.dumps(CV_FILENODE_TYPE, indent=4))

def readSeqFileNode(file_node:cv2.FileNode):
    assert(file_node.isSeq())
    res = []
    for i in range(file_node.size()):
        res.append(file_node.at(i).real())
    return res

def readMapFileNode(file_root:cv2.FileNode, deep=False):
    res = dict()
    for key in file_root.keys():
        file_node = file_root.getNode(key)
        file_node_type = file_node.type()
        rospy.logdebug(key, CV_FILENODE_TYPE[file_node_type], ":")
        if file_node_type == cv2.FILE_NODE_INT:
            res[key] = int(file_node.real())
        elif file_node_type == cv2.FILE_NODE_REAL:
            res[key] = file_node.real()
        elif file_node_type == cv2.FILE_NODE_STRING:
            res[key] = file_node.string()
        elif file_node_type == cv2.FILE_NODE_SEQ:
            res[key] = readSeqFileNode(file_node)
        elif file_node_type == cv2.FILE_NODE_MAP:
            res[key] = readMapFileNode(file_node)
            if not deep:
                res[key] = np.reshape(np.array(res[key]["data"]), (int(res[key]["rows"]), int(res[key]["cols"])))
        elif file_node_type == cv2.FILE_NODE_TYPE_MASK:
            raise NotImplementedError
        elif file_node_type == cv2.FILE_NODE_FLOAT:
            res[key] = file_node.real()
        elif file_node_type == cv2.FILE_NODE_FLOW:
            raise NotImplementedError
        elif file_node_type == cv2.FILE_NODE_STR:
            res[key] = file_node.string()
        elif file_node_type == cv2.FILE_NODE_UNIFORM:
            raise NotImplementedError
        elif file_node_type == cv2.FILE_NODE_EMPTY:
            raise NotImplementedError
        elif file_node_type == cv2.FILE_NODE_NAMED:
            raise NotImplementedError
        else:
            raise NotImplementedError
        rospy.logdebug(res[key])
    return res
    
def load_scene_mesh(scene_mesh_url:str, transform_matrix:np.ndarray) -> Tuple[o3d.geometry.TriangleMesh, np.ndarray]:
    scene_mesh_trimesh = trimesh.load(scene_mesh_url)
    if isinstance(scene_mesh_trimesh, trimesh.Scene):
        scene_mesh_trimesh:trimesh.Trimesh = scene_mesh_trimesh.dump(concatenate=True)
        
    scene_mesh_trimesh.apply_transform(transform_matrix)
    
    scene_mesh_visual = scene_mesh_trimesh.visual
    if isinstance(scene_mesh_visual, visual.TextureVisuals):
        scene_mesh_visual = scene_mesh_visual.to_color()
    scene_mesh = o3d.geometry.TriangleMesh(
        o3d.utility.Vector3dVector(scene_mesh_trimesh.vertices),
        o3d.utility.Vector3iVector(scene_mesh_trimesh.faces))
    scene_mesh.vertex_colors = o3d.utility.Vector3dVector(scene_mesh_visual.vertex_colors[:, :3] / 255.0)
    scene_mesh.compute_vertex_normals()
    
    scene_bbox_o3d = scene_mesh.get_axis_aligned_bounding_box()
    scene_bbox = np.array(
        [scene_bbox_o3d.get_min_bound(), scene_bbox_o3d.get_max_bound()]).T
    
    return scene_mesh, scene_bbox

class RGBDSensor:
    
    def __init__(self,
                 height:int,
                 width:int,
                 fx:float,
                 fy:float,
                 cx:float,
                 cy:float,
                 depth_min:float,
                 depth_max:float,
                 depth_scale:float,
                 position:np.ndarray,
                 downsample_factor:float=1.0,
                 need_downsample:bool=True):
        '''
        depth_max: unit in meters
        depth_min: unit in meters
        '''
        if downsample_factor > 1.0 and need_downsample:
            self.height = int(np.ceil(height / downsample_factor))
            self.width = int(np.ceil(width / downsample_factor))
            self.fx = fx * self.width / width
            self.fy = fy * self.height / height
            self.cx = cx * self.width / width
            self.cy = cy * self.height / height
        elif downsample_factor == 1.0 or not need_downsample:
            self.height = height
            self.width = width
            self.fx = fx
            self.fy = fy
            self.cx = cx
            self.cy = cy
        else:
            raise ValueError(f"Invalid downsample factor: {downsample_factor}")
        self.depth_max = depth_max
        self.depth_min = depth_min
        self.depth_scale = depth_scale
        self.position = position
        self.downsample_factor = downsample_factor
        self.directions = get_camera_rays(self.height, self.width, self.fx, self.fy, self.cx, self.cy)
        self.intrinsics = np.array([self.fx, 0, self.cx, 0, self.fy, self.cy, 0, 0, 1]).reshape(3, 3)
        self.hfov = 2 * np.arctan(self.width / (2 * self.fx))
        self.vfov = 2 * np.arctan(self.height / (2 * self.fy))
        
# ROS conversion functions
        
def dataset_config_to_ros(dataset_config:dict) -> GetDatasetConfigResponse:
    dataset_config_ros = dataset_config.copy()
    for key, value in dataset_config.items():
        if issubclass(type(value), (int, float, str)):
            pass
        elif isinstance(value, np.ndarray):
            if value.shape == (3, ):
                dataset_config_ros[key] = Point(*value)
            elif value.shape == (4, 4):
                value_ros = Pose()
                value_ros.position = Point(*value[:3, 3])
                value_ros.orientation = Quaternion(
                    *np.roll(
                        quaternion.as_float_array(quaternion.from_rotation_matrix(value[:3, :3])),
                        -1))
                dataset_config_ros[key] = value_ros
            else:
                raise ValueError(f'Invalid shape of {key}, get {type(value)}')
        else:
            raise ValueError(f'Invalid type of {key}, get {type(value)}')
    return GetDatasetConfigResponse(**dataset_config_ros)

# Camera intrinsics conversion functions

def as_intrinsics_matrix(intrinsics):
    """
    Get matrix representation of intrinsics.

    """
    K = np.eye(3)
    K[0, 0] = intrinsics[0]
    K[1, 1] = intrinsics[1]
    K[0, 2] = intrinsics[2]
    K[1, 2] = intrinsics[3]
    return K

def alphanum_key(s):
    """ Turn a string into a list of string and number chunks.
        "z23a" -> ["z", 23, "a"]
    """
    return [int(x) if x.isdigit() else x for x in re.split('([0-9]+)', s)]

def get_camera_rays(H, W, fx, fy=None, cx=None, cy=None, type='OpenGL'):
    """Get ray origins, directions from a pinhole camera."""
    #  ----> i
    # |
    # |
    # X
    # j
    i, j = torch.meshgrid(torch.arange(W, dtype=torch.float32),
                       torch.arange(H, dtype=torch.float32), indexing='xy')
    
    # View direction (X, Y, Lambda) / lambda
    # Move to the center of the screen
    #  -------------
    # |      y      |
    # |      |      |
    # |      .-- x  |
    # |             |
    # |             |
    #  -------------

    if cx is None:
        cx, cy = 0.5 * W, 0.5 * H

    if fy is None:
        fy = fx
    if type == 'OpenGL':
        dirs = torch.stack([(i - cx)/fx, -(j - cy)/fy, -torch.ones_like(i)], -1)
    elif type == 'OpenCV':
        dirs = torch.stack([(i - cx)/fx, (j - cy)/fy, torch.ones_like(i)], -1)
    else:
        raise NotImplementedError()

    rays_d = dirs
    return rays_d

def compute_intrinsics(width, height, hfov_rad, vfov_rad=None):
    fx = 0.5 * width / np.tan(hfov_rad / 2.)
    if vfov_rad is None:
        # NOTE: In habitat, fx is equal to fy
        fy = fx
    else:
        fy = 0.5 * height / np.tan(vfov_rad / 2.)
    cx = width / 2 - 1
    cy = height / 2 - 1
    return fx, fy, cx, cy