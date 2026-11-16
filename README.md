<p align="center">

  <h2 align="center">ActiveSplat: High-Fidelity Scene Reconstruction<br>through Active Gaussian Splatting</h2>
  <p align="center">
    <a href="https://li-yuetao.github.io/"><strong>Yuetao Li</strong></a><sup>1,2*</sup>
    ·
    <a href="https://github.com/kzj18"><strong>Zijia Kuang</strong></a><sup>2*</sup>
    ·
    <a href="https://laura-ting.github.io/"><strong>Ting Li</strong></a><sup>2</sup>
    ·
    <a href=""><strong>Qun Hao</strong></a><sup>1</sup>
    ·
    <a href="https://zikeyan.github.io/"><strong>Zike Yan</strong></a><sup>2†</sup>
    ·
    <a href="https://air.tsinghua.edu.cn/en/info/1046/1196.htm"><strong>Guyue Zhou</strong></a><sup>2</sup>
    ·
    <a href="https://scholar.google.nl/citations?hl=en&user=GDQ23eAAAAAJ&view_op=list_works"><strong>Shaohui Zhang</strong></a><sup>1†</sup>
  <p align="center">
        <sup>1</sup>Beijing Institute of Technology, <sup>2</sup>AIR, Tsinghua University
  </p>

<h3 align="center">
    <a href="https://ieeexplore.ieee.org/abstract/document/11037548"> <img src="https://img.shields.io/badge/IEEE-RA--L-004c99"> </a>
    <a href="https://arxiv.org/abs/2410.21955" target="_blank">
    <img src="https://img.shields.io/badge/arXiv-2410.21955-blue?logo=arxiv&color=%23B31B1B" alt="Paper arXiv"></a>
    <a href="https://li-yuetao.github.io/ActiveSplat/" target="_blank">
    <img src="https://img.shields.io/badge/Project-Page-a" alt="Project Page"></a>
    <a href="https://opensource.org/licenses/MIT" target="_blank">
    <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT"></a>
</h3>
<div align="center"></div>

<div align=center> <img src="media/ui-x5.gif" width="850"/> </div>

<span class="dperact">ActiveSplat</span> enables the agent to explore the environment autonomously to build a 3D map on the fly. The integration of a Gaussian map and a Voronoi graph assures efficient and complete exploration with high-fidelity reconstruction results.

## 💡 News
* **[16 June 2025]** 🎉 Our paper **ActiveSplat** has been officially published by **IEEE RA-L 2025**!
* **[27 May 2025]** Our paper **ActiveSplat** has been accepted to **IEEE RA-L 2025**!
* **[25 Feb 2025]** 🚀 The source code of **ActiveSplat** is now **publicly available**!

## 🛠️ Installation

Our environment has been tested on Ubuntu 20.04 with CUDA 11.8. We also provide a `ros2-humble` branch tested on Ubuntu 22.04 with CUDA 11.8.

Clone the repository and create the conda environment:

```bash
mkdir -p ~/Workspace/activesplat_ws/src
git clone git@github.com:Li-Yuetao/ActiveSplat.git ~/Workspace/activesplat_ws/src/ActiveSplat && cd ~/Workspace/activesplat_ws/src/ActiveSplat
git submodule update --init --progress

conda env create -f environment.yaml
conda activate ActiveSplat
```

Install pytorch by following the [instructions](https://pytorch.org/get-started/locally/). For torch 2.0.1 with CUDA version 11.8:

```bash
pip install torch==2.0.1+cu118 torchvision==0.15.2+cu118 torchaudio==2.0.2+cu118 --extra-index-url https://download.pytorch.org/whl/cu118

pip install -r requirements.txt
```

Install diff-gaussian-rasterization (Note: You should be on CUDA version: 11.8)

```bash
cd ~/Workspace/activesplat_ws/src/ActiveSplat/submodules/diff-gaussian-rasterization
python setup.py install
pip install .
```

## 🖥️ Preparation

### Simulated environment

[Habitat-lab](https://github.com/facebookresearch/habitat-lab) and [habitat-sim](https://github.com/facebookresearch/habitat-sim) need to be installed for simulation. We use v0.2.3 (`git checkout tags/v0.2.3`) for habitat-sim & habitat-lab and install the habitat-sim with the flag `--with-cuda`.

```bash
cd ~/Workspace/activesplat_ws/src/ActiveSplat/submodules/habitat/habitat-lab && git checkout tags/v0.2.3
pip install -e habitat-lab
pip install -e habitat-baselines
cd ~/Workspace/activesplat_ws/src/ActiveSplat/submodules/habitat/habitat-sim && git checkout tags/v0.2.3
# if you have bad network, you can use the following command to speed up
sed -i 's/https:\/\/github.com\//git@github.com:/g' .gitmodules # use `sed -i 's/git@github.com:/https:\/\/github.com\//g' .gitmodules` to restore
git submodule update --init --progress --recursive
python setup.py install --with-cuda
```

### Build

```bash
cd ~/Workspace/activesplat_ws/ && catkin_make -DPYTHON_EXECUTABLE=/usr/bin/python3
echo "source ~/Workspace/activesplat_ws/devel/setup.bash" >> ~/.bashrc
```

## 🚀 Run

### Config Datasets Path
Copy the `user_config.json` file from the `config/.templates` folder to the `config` folder, and set the paths for the [Gibson](https://docs.google.com/forms/d/e/1FAIpQLScWlx5Z1DM1M-wTSXaa6zV8lTFkPmTHW1LqMsoCBDWsTDjBkQ/viewform) and [MP3D](https://niessner.github.io/Matterport/#download) datasets in `user_config.json`.

<details>
  <summary>[Datasets folder structure (click to expand)]</summary>

```
  datasets_folder
    ├── gibson_habitat
    │   ├── gibson
    │   │   ├── Adrian.glb
    │   │   └── ...
    │   └── ...
    ├── matterport
    │   ├── v1
    │   │   ├── scans
    │   │   └── tasks
    │   |       ├── 1LXtFkjw3qL
    │   |       |   ├── 1LXtFkjw3qL.glb
    │   |       |   └── ...
    │   |       └── ...
    │   ├── v2
    |   └── ...
    └── ...
```
</details>

### Run ActiveSplat

#### Single scene
```bash
# If you want to save runtime data, you can add the `save_runtime_data:=1` flag
# e.g. Gibson-Denmark
roslaunch activesplat habitat.launch config:=config/datasets/gibson.json scene_id:=Denmark
# e.g. MP3D-pLe4wQe7qrG
roslaunch activesplat habitat.launch config:=config/datasets/mp3d.json scene_id:=pLe4wQe7qrG
```
<details>
  <summary>[Result folder structure (click to expand)]</summary>

```bash
  2025-04-13_22-34-21_gibson_Eudora
    ├── gaussians_data
    │   ├── depth
    │   ├── keyframes
    │   ├── rgb
    │   ├── config.py
    │   ├── params.npz
    │   └── transforms.json
    ├── render_rgbd # save_runtime_data:=1
    ├── runtime_data # save_runtime_data:=1
    ├── subregion_map # save_runtime_data:=1
    ├── subregion_map # save_runtime_data:=1
    ├── topdown_map # save_runtime_data:=1
    ├── actions.txt
    ├── config.json
    ├── gt_mesh.json
    ├── topdown_free_map.png
    └── visited_map.png
```
</details>

#### Batch scenes
Here the system will run active mapping on 13 scenes ([gibson_small.txt](./scripts/batch/gibson_small.txt), [gibson_big.txt](./scripts/batch/gibson_big.txt), [mp3d_small.txt](./scripts/batch/mp3d_small.txt), [mp3d_big.txt](./scripts/batch/mp3d_big.txt)) in the Gibson & MP3D datasets. The results will be saved in the `results` folder.
```bash
bash scripts/batch/run_batch_scenes.sh
```

### Eval Results
Evaluate actions, this will read the actions from the `actions.txt` file in the result folder and evaluate them to generate the `actions_error.txt` file.
#### Single scene
```bash
result_name="2025-02-25_11-43-48_gibson_Denmark"
python scripts/judges/eval_actions.py --save_path results/$result_name/actions_error.txt --config results/$result_name/config.json --user_config config/user_config.json --actions results/$result_name/actions.txt --gpu_id 0
```

#### Batch scenes
```bash
# If you want to force re-evaluation, you can add the `--force` flag
python scripts/batch/eval_results_actions.py --results_dir ./results --gpu_id 0
```

## ✏️ Acknowledgments

Our implementation is built upon <a href="https://github.com/kzj18/activeINR-S">ANM-S</a>. We would also like to thank the authors of the following open-source repositories:

- <a href="https://github.com/spla-tam/SplaTAM">SplaTAM</a> for the mapper implementation.
- <a href="https://github.com/muskie82/MonoGS">MonoGS</a> for the online gaussian map visualization.

If you find these works helpful, please consider citing them as well.

## 🎓 Citation

If you find our code/work useful in your research, please consider citing the following:
```bibtex
@article{li2025activesplat,
    title={Activesplat: High-fidelity scene reconstruction through active gaussian splatting},
    author={Li, Yuetao and Kuang, Zijia and Li, Ting and Hao, Qun and Yan, Zike and Zhou, Guyue and Zhang, Shaohui},
    journal={IEEE Robotics and Automation Letters},
    year={2025},
    publisher={IEEE}
}
```

---
# Naufal Ghifari's Fork Additions

## 1. Raw Replica Scene Support (Automatic `stage_habitat.glb` & `stage_habitat.navmesh`)

Out of the box, loading raw Replica scenes (`mesh.ply` or `stage.ply`) in Habitat-Sim has three pitfalls:
1. **Dark / 10% brightness RGB rendering:** Standalone `.ply` files have no embedded material, so Habitat-Sim falls back to `DEFAULT_MATERIAL_KEY` (`PhongMaterialData` with `ambientColor = 0.1`), multiplying all RGB vertex colors by `0.1`.
2. **90° Z-up vs. Y-up orientation & quad faces:** Raw Replica meshes are Z-up (and `mesh.ply` uses quad faces), whereas Habitat-Sim operates in Y-up and only auto-rotates `.glb` stages (or PTex `mesh.ply`, which crashes if `habitat/sorted_faces.bin` is absent).
3. **`stage.stage_config.json` override:** Passing a file named `stage.<ext>` causes Habitat-Sim to load `stage.stage_config.json` (which points back to `stage.ply`) if present.

### Automatic First-Run Conversion
`get_scene_mesh_url()` in [`src/dataloader/__init__.py`](./src/dataloader/__init__.py) now handles this **automatically** on first launch for any Replica scene (`room_0`, `apartment_0`, etc.):
- If `stage_habitat.glb` does not exist in `/datasets/replica/<scene_id>/`, it loads `stage.ply` (or raw `mesh.ply`, automatically triangulating quad faces via `trimesh`) and exports `stage_habitat.glb` with a full-brightness `baseColorFactor = [1.0, 1.0, 1.0, 1.0]` glTF material (which Habitat-Sim also automatically rotates from Z-up to Y-up).
- If `stage_habitat.navmesh` does not exist, it automatically copies it from `mesh.navmesh` or `habitat/mesh_semantic.navmesh`.
- For Open3D visualization and evaluation (`scene_mesh_url`), it uses `stage.ply` if present or falls back directly to `mesh.ply`.

---

## 2. Automatic `.ply` Export & Compute Profiling

At the end of every run (including early termination via `Ctrl+C`), this fork automatically saves two additional files in the result directory (`results/<timestamp>_<dataset>_<scene_id>/`):
- **`gaussians_data/point_cloud.ply`**: Binary little-endian PLY of the reconstructed 3D Gaussians containing both standard 3DGS attributes (`x, y, z, nx, ny, nz, f_dc_0..2, opacity, scale_0..2, rot_0..3`) and 8-bit RGB vertex colors (`red, green, blue`) for viewing in SuperSplat, CloudCompare, MeshLab, or Open3D.
- **`compute_metrics.json`**: End-to-end compute and resource profile including:
  - `run_info`: Completed steps, mapped frames, keyframes, densification events, total mapping iterations, and trajectory path length (m).
  - `runtime`: Total wall-clock time, effective steps/sec, mapped FPS, and average SplaTAM iteration/frame times.
  - `timing_breakdown_ms`: Count, total time, % of wall-clock, mean, std, median, P95, and max (ms) for `mapper_run_active`, `topdown_render`, `global_visibility_query`, `local_visibility_query`, and `rgbd_novel_view_render`.
  - `memory`: GPU model, total GPU VRAM, PyTorch peak/final allocated & reserved VRAM (MB), total device used VRAM (MB), and host peak RSS RAM (MB).
  - `gaussian_map`: Initial, peak, and final 3D Gaussian counts, Gaussians per frame/meter, `params.npz` & `point_cloud.ply` sizes (MB), and periodic `step_history` snapshots.

---

## 3. Running ActiveSplat (Docker)

1. **On host shell**, grant local Docker containers permission to connect to the X11 display:
   ```bash
   xhost +local:docker
   ```

2. **Start and enter the Docker container:**
   ```bash
   docker start activesplat_dev
   docker exec -it activesplat_dev bash
   ```

3. **Run ActiveSplat inside the container shell:**
   ```bash
   export ROS_IP=127.0.0.1 && \
   export ROS_MASTER_URI=http://127.0.0.1:11311 && \
   export LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libstdc++.so.6:/lib/x86_64-linux-gnu/libffi.so.7 && \
   export LIBGL_ALWAYS_SOFTWARE=1 && \
   cd /root/Workspace/activesplat_ws/src/ActiveSplat && \
   roslaunch activesplat habitat.launch \
     config:=/root/Workspace/activesplat_ws/src/ActiveSplat/config/datasets/replica.json \
     scene_id:=room_0 save_runtime_data:=1
   ```
   *(For `apartment_0`, set `config:=/root/Workspace/activesplat_ws/src/ActiveSplat/config/datasets/replica_apartment_0.json scene_id:=apartment_0`.)*

---

## 4. Evaluating a Run

To evaluate a completed run's 3D exploration completeness and reconstruction accuracy against the ground-truth mesh, run inside the container shell:

```bash
result_name="2026-11-16_17-21-19_replica_room_0"
python scripts/judges/eval_actions.py \
  --save_path results/$result_name/actions_error.txt \
  --config results/$result_name/config.json \
  --user_config config/user_config.json \
  --actions results/$result_name/actions.txt \
  --gpu_id 0
```
*(Add `--force` to re-run and back up an existing `actions_error.txt`.)*

### Understanding the Evaluation Output
- **Terminal summary:**
  ```text
  ActiveSplat: room_0: Ratio/Error: 95.75/1.07, Contains Inf: 95.75/1.07, Path Length: 25.22 m, Acc.: 1.64 cm
  ```
  - `Ratio/Error`: **Completeness Ratio (%)** ($< 5\text{ cm}$ threshold) / **Completeness Error (cm)** (clamped at $1.0\text{ m}$ max distance).
  - `Contains Inf`: Unclamped **Completeness Ratio (%)** / **Completeness Error (cm)**.
  - `Path Length`: Total distance traveled by the agent in meters.
  - `Acc.`: **Reconstruction Accuracy (cm)** (mean distance from observed points to ground-truth mesh surface).
- **Saved file (`results/$result_name/actions_error.txt`):**
  Contains one line per step ($t = 0 \dots T$) with 6 space-separated columns:
  ```text
  <min_comp_m> <min_comp_ratio> <min_comp_inf_m> <min_comp_ratio_inf> <path_length_m> <min_acc_m>
  ```