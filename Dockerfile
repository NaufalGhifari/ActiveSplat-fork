FROM nvidia/cuda:11.8.0-devel-ubuntu20.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Jakarta
ENV CUDA_HOME=/usr/local/cuda-11.8
ENV PATH=${CUDA_HOME}/bin:/opt/conda/bin:${PATH}
ENV LD_LIBRARY_PATH=${CUDA_HOME}/lib64:${LD_LIBRARY_PATH}
ENV TORCH_CUDA_ARCH_LIST="8.6"
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=all

# 1. System + OpenGL/EGL (for Habitat-Sim) + ROS Noetic dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl wget git build-essential cmake ninja-build pkg-config \
    lsb-release gnupg2 ca-certificates sudo vim nano \
    libjpeg-dev libglm-dev libgl1-mesa-glx libgl1-mesa-dev \
    libegl1-mesa-dev libgles2-mesa-dev libglew-dev \
    libx11-dev libxcursor-dev libxrandr-dev libxinerama-dev libxi-dev \
    libsm6 libxext6 libxrender-dev libgomp1 \
    python3-dev python3-pip \
    && rm -rf /var/lib/apt/lists/*

# 2. Add ROS Noetic repository and install ROS Noetic packages
RUN sh -c 'echo "deb http://packages.ros.org/ros/ubuntu $(lsb_release -sc) main" > /etc/apt/sources.list.d/ros-latest.list' && \
    curl -s https://raw.githubusercontent.com/ros/rosdistro/master/ros.asc | apt-key add - && \
    apt-get update && apt-get install -y --no-install-recommends \
    ros-noetic-ros-base \
    ros-noetic-cv-bridge \
    ros-noetic-tf \
    ros-noetic-tf2-ros \
    ros-noetic-nav-msgs \
    ros-noetic-sensor-msgs \
    ros-noetic-geometry-msgs \
    ros-noetic-visualization-msgs \
    ros-noetic-std-msgs \
    python3-catkin-tools \
    python3-rosdep \
    python3-rospkg \
    && rm -rf /var/lib/apt/lists/*

# 3. Install Miniconda & create ActiveSplat Python 3.9 environment
RUN wget -q https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O /tmp/miniconda.sh && \
    bash /tmp/miniconda.sh -b -p /opt/conda && \
    rm /tmp/miniconda.sh && \
    /opt/conda/bin/conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main || true && \
    /opt/conda/bin/conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r || true && \
    /opt/conda/bin/conda create -y -n ActiveSplat python=3.9 pip && \
    /opt/conda/bin/conda clean --all -y

# 4. Install PyTorch 2.0.1+cu118 and ActiveSplat requirements.txt
COPY requirements.txt /tmp/requirements.txt
RUN /opt/conda/envs/ActiveSplat/bin/pip install --no-cache-dir \
    torch==2.0.1+cu118 torchvision==0.15.2+cu118 torchaudio==2.0.2+cu118 \
    --extra-index-url https://download.pytorch.org/whl/cu118 && \
    /opt/conda/envs/ActiveSplat/bin/pip install --no-cache-dir \
    "numpy<2.0" "setuptools<70.0" wheel catkin_pkg empy==3.3.4 defusedxml netifaces \
    -r /tmp/requirements.txt

# Configure bashrc so every shell sources ROS Noetic + activates ActiveSplat conda env
RUN echo "source /opt/ros/noetic/setup.bash" >> /root/.bashrc && \
    echo "source /opt/conda/etc/profile.d/conda.sh && conda activate ActiveSplat" >> /root/.bashrc && \
    echo "if [ -f /root/Workspace/activesplat_ws/devel/setup.bash ]; then source /root/Workspace/activesplat_ws/devel/setup.bash; fi" >> /root/.bashrc

WORKDIR /root/Workspace/activesplat_ws
CMD ["/bin/bash"]
