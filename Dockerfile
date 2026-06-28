# ============================================================
# ROS2 Humble + Nav2 + YOLOv8 视觉导航开发环境（RViz2 可视化）
# ============================================================
# 构建:  docker build --network=host -t ros2_visual_nav:latest .
# 运行:  docker compose up -d
# 进入:  docker exec -it ros2_visual_nav bash
# ============================================================

FROM docker.m.daocloud.io/library/ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV ROS_DISTRO=humble
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

# ==================== 阶段1：系统源配置 ====================
# ARM64 ports 源替换为阿里云镜像（HTTP，避免最小镜像无 ca-certificates）
RUN sed -i 's|http://ports.ubuntu.com/ubuntu-ports|http://mirrors.aliyun.com/ubuntu-ports|g' /etc/apt/sources.list

# ==================== 阶段2：基础工具 ====================
RUN apt-get update
RUN apt-get install -y curl
RUN apt-get install -y gnupg2
RUN apt-get install -y lsb-release
RUN apt-get install -y locales
RUN apt-get install -y ca-certificates
RUN locale-gen en_US.UTF-8
RUN update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
RUN rm -rf /var/lib/apt/lists/*

ENV LANG=en_US.UTF-8

# ==================== 阶段3：ROS2 apt 源 ====================
# GPG key 从本地 COPY（避免 Docker 构建时网络拦截）
COPY ros.key /usr/share/keyrings/ros-archive-keyring.gpg
RUN echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(lsb_release -cs) main" > /etc/apt/sources.list.d/ros2.list

# ==================== 阶段4：ROS2 Desktop + Nav2 + SLAM ====================
RUN apt-get update
# ROS2 桌面版（不含 Ignition Gazebo，避免 arm64 依赖冲突）
RUN apt-get install -y --fix-missing ros-humble-desktop
# Nav2 导航栈
RUN apt-get install -y --fix-missing ros-humble-navigation2
RUN apt-get install -y --fix-missing ros-humble-nav2-bringup
RUN apt-get install -y --fix-missing ros-humble-nav2-map-server
RUN apt-get install -y --fix-missing ros-humble-nav2-amcl
RUN apt-get install -y --fix-missing ros-humble-nav2-planner
RUN apt-get install -y --fix-missing ros-humble-nav2-controller
RUN apt-get install -y --fix-missing ros-humble-nav2-bt-navigator
RUN apt-get install -y --fix-missing ros-humble-nav2-lifecycle-manager
RUN apt-get install -y --fix-missing ros-humble-nav2-msgs
RUN apt-get install -y --fix-missing ros-humble-nav2-simple-commander
# SLAM 建图
RUN apt-get install -y --fix-missing ros-humble-slam-toolbox
# 消息类型
RUN apt-get install -y --fix-missing ros-humble-vision-msgs
RUN apt-get install -y --fix-missing ros-humble-tf2-geometry-msgs
RUN apt-get install -y --fix-missing ros-humble-tf2-ros-py
# 图像工具
RUN apt-get install -y --fix-missing ros-humble-cv-bridge
RUN apt-get install -y --fix-missing ros-humble-image-transport
# 键盘遥控
RUN apt-get install -y --fix-missing ros-humble-teleop-twist-keyboard
# Python 工具
RUN apt-get install -y --fix-missing python3-pip python3-opencv
# 构建工具
RUN apt-get install -y --fix-missing python3-colcon-common-extensions git
RUN rm -rf /var/lib/apt/lists/*
# 验证关键包是否安装成功
RUN dpkg -l ros-humble-desktop ros-humble-navigation2 ros-humble-slam-toolbox \
    ros-humble-nav2-bringup ros-humble-cv-bridge ros-humble-teleop-twist-keyboard \
    python3-colcon-common-extensions 2>&1 | grep "^dpkg-query: no packages found" && exit 1 || true

# ==================== 阶段5：Python 依赖 ====================
RUN pip3 install --no-cache-dir ultralytics
RUN pip3 install --no-cache-dir opencv-python
RUN pip3 install --no-cache-dir transforms3d

# ==================== 阶段6：项目工作空间 ====================
WORKDIR /root/ros2_ws
COPY . /root/ros2_ws/

# 自动 source ROS2 + 项目环境
RUN echo "source /opt/ros/humble/setup.bash" >> /root/.bashrc && \
    echo 'if [ -f /root/ros2_ws/install/setup.bash ]; then source /root/ros2_ws/install/setup.bash; fi' >> /root/.bashrc

# 编译项目
RUN /bin/bash -c "source /opt/ros/humble/setup.bash && \
    colcon build --symlink-install"

# 默认命令：保持容器运行
CMD ["tail", "-f", "/dev/null"]
