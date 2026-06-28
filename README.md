# ros2-yolov8-visual-navigation

基于 ROS2 与 YOLOv8 的移动机器人视觉引导自主导航系统设计与实现。

## 项目简介

本项目为《ROS2 智能机器人》课程设计，在 Gazebo 仿真环境中构建一个多节点协同的视觉引导导航机器人系统：

- 摄像头采集图像并通过 ROS2 话题发布
- YOLOv8 检测目标并输出二维检测框
- 坐标转换节点将像素坐标转换为地图坐标系下的目标位姿
- 导航控制节点调用 Nav2 的 `NavigateToPose` Action 完成自主导航

系统采用四节点解耦架构，体现了 ROS2 单一职责、松耦合的设计思想。

## 系统架构

```
┌──────────────────────────────────────────────┐
│              Gazebo 仿真层                    │
│      RGB 相机 / 2D 激光雷达 / 里程计           │
│        (gazebo_ros 插件直接输出 ROS2 话题)     │
└───────────────────┬──────────────────────────┘
                    │ gazebo_ros plugins
┌───────────────────▼──────────────────────────┐
│                ROS2 节点层                    │
│  image_publisher → yolo_detector →           │
│  coord_transformer → nav_controller          │
└───────────────────┬──────────────────────────┘
                    │
┌───────────────────▼──────────────────────────┐
│              Nav2 导航栈                      │
│   SLAM 建图 / AMCL 定位 / 路径规划 / 控制器    │
└──────────────────────────────────────────────┘
```

## 环境要求

| 项目 | 配置 |
|------|------|
| 操作系统 | Ubuntu 22.04（Docker）|
| ROS2 | Humble Hawksbill |
| Python | 3.10 |
| 仿真平台 | Gazebo Classic 11 |
| 导航框架 | Nav2 |
| AI 检测库 | Ultralytics YOLOv8 |
| 硬件 | 任意 x86_64 / ARM64（M4 Pro 通过 Rosetta/Docker）|

## 项目目录结构

```
ros2-yolov8-visual-navigation/
├── src/robot_nav/
│   ├── robot_nav/               # Python 节点源码
│   │   ├── image_publisher.py   # 图像发布节点
│   │   ├── yolo_detector.py     # YOLOv8 检测节点
│   │   ├── coord_transformer.py # 坐标转换节点
│   │   └── nav_controller.py    # 导航控制节点
│   ├── launch/                  # Launch 启动文件
│   │   ├── gazebo.launch.py     # Gazebo 仿真启动
│   │   ├── slam.launch.py       # SLAM 建图
│   │   ├── nav2.launch.py       # Nav2 导航栈
│   │   ├── vision.launch.py     # 视觉节点链路
│   │   └── visual_navigation.launch.py  # 主启动文件
│   ├── config/                  # 配置文件
│   │   ├── nav2_params.yaml     # Nav2 参数
│   │   └── slam_params.yaml     # SLAM 参数
│   ├── urdf/                    # 机器人 URDF 模型
│   │   └── robot_nav.urdf.xacro
│   ├── worlds/                  # Gazebo 世界文件
│   │   └── indoor_env.world
│   ├── rviz/                    # RViz2 配置文件
│   │   └── nav_config.rviz
│   ├── maps/                    # 栅格地图文件
│   └── models/                  # YOLOv8 模型权重
├── Dockerfile                   # Docker 镜像构建
├── docker-compose.yml           # Docker 容器编排
├── requirements.txt             # Python 依赖
└── README.md                    # 项目说明
```

## 快速开始（Docker）

### 第一步：构建镜像

```bash
cd ros2-yolov8-visual-navigation
docker compose build
```

### 第二步：启动容器

```bash
# macOS：先启动 XQuartz（用于显示 Gazebo/RViz GUI）
# open -a XQuartz
# xhost +

docker compose up -d
docker exec -it ros2_visual_nav bash
```

### 第三步：编译项目

```bash
# 容器内
cd /root/ros2_ws
colcon build --symlink-install
source install/setup.bash
```

### 第四步：启动系统

```bash
# 一键启动完整系统（Gazebo + Nav2 + 视觉节点）
ros2 launch robot_nav visual_navigation.launch.py

# 或分步启动
ros2 launch robot_nav gazebo.launch.py   # 终端1：Gazebo
ros2 launch robot_nav nav2.launch.py     # 终端2：Nav2
ros2 launch robot_nav vision.launch.py   # 终端3：视觉节点
```

### SLAM 建图

```bash
# 启动 Gazebo + SLAM
ros2 launch robot_nav slam.launch.py

# 键盘遥控控制机器人探索
ros2 run teleop_twist_keyboard teleop_twist_keyboard

# 保存地图
ros2 run nav2_map_server map_saver_cli -f maps/simulation_map
```

## 节点说明

| 节点名称 | 订阅话题 | 发布话题 | 职责 |
|----------|----------|----------|------|
| `image_publisher` | `/camera/image_raw` | `/camera/image` | 图像采集与格式转换 |
| `yolo_detector` | `/camera/image` | `/detected_objects` | YOLOv8 目标检测 |
| `coord_transformer` | `/detected_objects` | `/target_pose` | 像素坐标 → 地图坐标 |
| `nav_controller` | `/target_pose` | `navigate_to_pose` Action | 导航状态机管理 |

## 主要话题

| 话题名称 | 消息类型 | 说明 |
|----------|----------|------|
| `/camera/image_raw` | `sensor_msgs/Image` | Gazebo 相机原始图像 |
| `/camera/image` | `sensor_msgs/Image` | 标准化图像数据 |
| `/camera/camera_info` | `sensor_msgs/CameraInfo` | 相机内参 |
| `/detected_objects` | `vision_msgs/Detection2DArray` | 检测结果 |
| `/target_pose` | `geometry_msgs/PoseStamped` | 目标地图坐标 |
| `/scan` | `sensor_msgs/LaserScan` | 激光雷达数据（360°/10Hz）|
| `/odom` | `nav_msgs/Odometry` | 里程计数据（20Hz）|
| `/cmd_vel` | `geometry_msgs/Twist` | 速度控制指令 |
| `/tf` | `tf2_msgs/TFMessage` | 坐标变换 |

## 课程设计报告

详细设计文档与实验分析见项目根目录下的 `system_design.md`。
