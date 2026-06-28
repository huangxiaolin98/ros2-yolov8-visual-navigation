# ros2-yolov8-visual-navigation

基于 ROS2 与 YOLOv8 的移动机器人视觉引导自主导航系统设计与实现。

## 项目简介

本项目为《ROS2 智能机器人》课程设计，在 Docker 容器化环境中构建一个多节点协同的视觉引导导航机器人系统：

- Mock 传感器节点模拟机器人传感器数据（相机、激光雷达、里程计）
- YOLOv8 检测目标并输出二维检测框
- 坐标转换节点将像素坐标转换为地图坐标系下的目标位姿
- 导航控制节点调用 Nav2 的 `NavigateToPose` Action 完成自主导航

系统采用四节点解耦架构，体现了 ROS2 单一职责、松耦合的设计思想。

## 系统架构

```
┌──────────────────────────────────────────────┐
│           Mock 传感器仿真层                    │
│   RGB 相机(30Hz) / 激光雷达(10Hz) / 里程计(20Hz) │
│        (mock_sensors 节点纯软件模拟)           │
└───────────────────┬──────────────────────────┘
                    │ ROS2 话题 + TF2
┌───────────────────▼──────────────────────────┐
│                ROS2 节点层                    │
│  image_publisher → yolo_detector →           │
│  coord_transformer → nav_controller          │
└───────────────────┬──────────────────────────┘
                    │ NavigateToPose Action
┌───────────────────▼──────────────────────────┐
│              Nav2 导航栈                      │
│   SLAM 建图 / AMCL 定位 / 路径规划 / 控制器    │
└──────────────────────────────────────────────┘
```

## 环境要求

| 项目 | 配置 |
|------|------|
| 操作系统 | macOS（Apple Silicon）/ Ubuntu 22.04（Docker 容器内）|
| 容器平台 | Docker Desktop |
| ROS2 | Humble Hawksbill |
| Python | 3.10 |
| 仿真方案 | Mock 传感器节点（纯软件，无 Gazebo/Webots）|
| 导航框架 | Nav2 |
| AI 检测库 | Ultralytics YOLOv8 |
| 硬件 | 任意 x86_64 / ARM64（Apple M4 Pro 等）|

## 项目目录结构

```
ros2-yolov8-visual-navigation/
├── src/robot_nav/
│   ├── robot_nav/                       # Python 节点源码
│   │   ├── mock_sensors.py              # Mock 传感器节点
│   │   ├── image_publisher.py           # 图像发布节点
│   │   ├── yolo_detector.py             # YOLOv8 检测节点
│   │   ├── coord_transformer.py         # 坐标转换节点
│   │   └── nav_controller.py            # 导航控制节点
│   ├── launch/                          # Launch 启动文件
│   │   ├── visual_navigation.launch.py  # 主启动文件（一键启动）
│   │   ├── nav2.launch.py               # Nav2 导航栈
│   │   ├── vision.launch.py             # 视觉节点链路
│   │   ├── slam.launch.py               # SLAM 建图
│   │   └── gazebo.launch.py             # Gazebo 仿真（可选）
│   ├── config/                          # 配置文件
│   │   ├── nav2_params.yaml             # Nav2 参数
│   │   └── slam_params.yaml             # SLAM 参数
│   ├── maps/                            # 栅格地图文件
│   │   ├── simulation_map.pgm
│   │   └── simulation_map.yaml
│   ├── urdf/                            # 机器人 URDF 模型
│   │   └── robot_nav.urdf.xacro
│   ├── worlds/                          # Gazebo 世界文件（可选）
│   │   └── indoor_env.world
│   ├── rviz/                            # RViz2 配置文件
│   │   └── nav_config.rviz
│   └── models/                          # YOLOv8 模型权重
├── data/
│   └── screenshots/                     # 实验截图（17 张）
├── report.md                            # 课程设计报告（Markdown）
├── report.docx                          # 课程设计报告（Word）
├── system_design.md                     # 系统设计文档
├── Dockerfile                           # Docker 镜像构建
├── docker-compose.yml                   # Docker 容器编排
├── requirements.txt                     # Python 依赖
└── README.md                            # 项目说明
```

## 快速开始

### 第一步：构建镜像

```bash
cd ros2-yolov8-visual-navigation
docker compose build
```

### 第二步：启动容器

```bash
docker compose up -d
docker exec -it ros2_visual_nav bash
```

### 第三步：编译项目

```bash
# 容器内执行
source /opt/ros/humble/setup.bash
cd /root/ros2_ws
colcon build --symlink-install
source install/setup.bash
```

### 第四步：启动系统

```bash
# 一键启动完整系统（Mock 传感器 + Nav2 + 视觉节点，分层延迟启动）
ros2 launch robot_nav visual_navigation.launch.py
```

系统启动顺序：
1. `mock_sensors` 节点立即启动（0s）
2. Nav2 导航栈延迟 3 秒启动
3. 视觉节点链路延迟 8 秒启动

### 第五步：发送 AMCL 初始位姿

Nav2 启动后，AMCL 需要初始位姿才能建立 `map → odom` TF 变换：

```bash
ros2 topic pub --once /initialpose geometry_msgs/PoseStamped \
  "{header: {frame_id: 'map'}, \
   pose: {position: {x: 0.0, y: 0.0}, orientation: {w: 1.0}}}"
```

### 分步调试

```bash
# 仅启动 Mock 传感器（调试传感器数据）
ros2 run robot_nav mock_sensors

# 仅启动 SLAM 建图
ros2 launch robot_nav slam.launch.py

# 仅启动 Nav2 导航栈
ros2 launch robot_nav nav2.launch.py

# 仅启动视觉节点链路（调试检测逻辑）
ros2 launch robot_nav vision.launch.py
```

### SLAM 建图

```bash
# 启动 Mock 传感器 + SLAM
ros2 launch robot_nav slam.launch.py

# 另一终端：键盘遥控控制机器人探索
ros2 run teleop_twist_keyboard teleop_twist_keyboard

# 保存地图
ros2 run nav2_map_server map_saver_cli -f src/robot_nav/maps/simulation_map
```

## 节点说明

| 节点名称 | 订阅话题 | 发布话题 | 频率 | 职责 |
|----------|----------|----------|------|------|
| `mock_sensors` | `/cmd_vel` | `/camera/image_raw`, `/scan`, `/odom`, TF | 30/10/20Hz | 模拟传感器数据 |
| `image_publisher` | `/camera/image_raw` | `/camera/image` | 30Hz | 图像格式标准化 |
| `yolo_detector` | `/camera/image` | `/detected_objects` | 15Hz | YOLOv8 目标检测 |
| `coord_transformer` | `/detected_objects` | `/target_pose` | 10Hz | 像素坐标 → 地图坐标 |
| `nav_controller` | `/target_pose` | `navigate_to_pose` Action | - | 导航状态机管理 |

## 主要话题

| 话题名称 | 消息类型 | 频率 | 说明 |
|----------|----------|------|------|
| `/camera/image_raw` | `sensor_msgs/Image` | 30Hz | 模拟相机原始图像（640×480 bgr8）|
| `/camera/image` | `sensor_msgs/Image` | 30Hz | 标准化图像数据 |
| `/camera/camera_info` | `sensor_msgs/CameraInfo` | 30Hz | 相机内参（fx=fy=525, cx=320, cy=240）|
| `/scan` | `sensor_msgs/LaserScan` | 10Hz | 激光雷达（360°/10m 量程）|
| `/odom` | `nav_msgs/Odometry` | 20Hz | 里程计（差分驱动运动学模型）|
| `/detected_objects` | `vision_msgs/Detection2DArray` | 15Hz | YOLOv8 检测结果 |
| `/target_pose` | `geometry_msgs/PoseStamped` | 10Hz | 目标地图坐标 |
| `/cmd_vel` | `geometry_msgs/Twist` | 20Hz | Nav2 速度控制指令 |
| `/tf` | `tf2_msgs/TFMessage` | 20Hz | 坐标变换（map→odom→base_link→camera_link）|

## TF 坐标树

```
map
 └── odom          （AMCL 发布，需 initialpose 激活）
      └── base_link   （mock_sensors 发布，20Hz 动态）
           └── camera_link （mock_sensors 发布，静态，前方 0.2m / 高度 0.3m）
```

## Mock 传感器参数

| 传感器 | 参数 | 话题 | 频率 |
|--------|------|------|------|
| RGB 相机 | 640×480 / bgr8 | `/camera/image_raw` | 30Hz |
| 激光雷达 | 360° / 10m 量程 / 360 个点 | `/scan` | 10Hz |
| 里程计 | 差分驱动运动学 | `/odom` | 20Hz |

里程计运动学模型：
- 线速度 `v` 和角速度 `ω` 从 `/cmd_vel` 获取
- 位姿更新：`x += v·cos(θ)·dt`，`y += v·sin(θ)·dt`，`θ += ω·dt`
