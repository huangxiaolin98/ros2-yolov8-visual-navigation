# ros2-yolov8-visual-navigation

基于 ROS2 与 YOLOv8 的移动机器人视觉引导自主导航系统设计与实现。

## 项目简介

本项目为《ROS2 智能机器人》课程设计，在 Webots 仿真环境中构建一个多节点协同的视觉引导导航机器人系统：

- 摄像头采集图像并通过 ROS2 话题发布
- YOLOv8 检测目标并输出二维检测框
- 坐标转换节点将像素坐标转换为地图坐标系下的目标位姿
- 导航控制节点调用 Nav2 的 `NavigateToPose` Action 完成自主导航

系统采用四节点解耦架构，体现了 ROS2 单一职责、松耦合的设计思想。

## 系统架构

```
┌──────────────────────────────────────────────┐
│                Webots 仿真层                  │
│        RGB 相机 / 激光雷达 / 里程计            │
└───────────────────┬──────────────────────────┘
                    │ webots_ros2 桥接
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

- 操作系统：macOS（Apple Silicon）
- ROS2：Humble Hawksbill
- Python：3.11（通过 pyenv 管理）
- 仿真平台：Webots R2023b
- 导航框架：Nav2
- AI 检测库：Ultralytics YOLOv8

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
│   │   ├── webots.launch.py
│   │   ├── slam.launch.py
│   │   ├── nav2.launch.py
│   │   ├── vision.launch.py
│   │   └── visual_navigation.launch.py
│   ├── config/                  # 配置文件
│   │   ├── nav2_params.yaml
│   │   └── slam_params.yaml
│   ├── worlds/                  # Webots 世界文件
│   ├── maps/                    # 栅格地图文件
│   └── models/                  # YOLOv8 模型权重
├── outputs/                     # 实验输出（图表、日志）
├── requirements.txt             # Python 依赖
└── README.md                    # 项目说明
```

## 安装依赖

```bash
# 使用与 ROS2 相同的 Python 版本
export PYENV_VERSION=3.11.9
source /Users/huangxiaogua/Documents/ros2/install/setup.zsh

# 安装 Python 依赖
python -m pip install -r requirements.txt

# 编译工作空间
cd /Users/huangxiaogua/Documents/2026/ros2/ros2-yolov8-visual-navigation
colcon build --symlink-install
source install/setup.zsh
```

## 节点说明

| 节点名称 | 订阅话题 | 发布话题 | 职责 |
|----------|----------|----------|------|
| `image_publisher` | `/webots/camera` | `/camera/image` | 图像采集与格式转换 |
| `yolo_detector` | `/camera/image` | `/detected_objects` | 目标检测 |
| `coord_transformer` | `/detected_objects` | `/target_pose` | 像素坐标 → 地图坐标 |
| `nav_controller` | `/target_pose` | `navigate_to_pose` Action | 导航状态机管理 |

## 快速启动

### 一键启动完整系统

```bash
ros2 launch robot_nav visual_navigation.launch.py
```

### 单独启动视觉链路

```bash
ros2 launch robot_nav vision.launch.py
```

### SLAM 建图

```bash
ros2 launch robot_nav slam.launch.py
```

## 主要话题

| 话题名称 | 消息类型 | 说明 |
|----------|----------|------|
| `/camera/image` | `sensor_msgs/Image` | 标准化图像数据 |
| `/camera/camera_info` | `sensor_msgs/CameraInfo` | 相机内参 |
| `/detected_objects` | `vision_msgs/Detection2DArray` | 检测结果 |
| `/target_pose` | `geometry_msgs/PoseStamped` | 目标地图坐标 |
| `/scan` | `sensor_msgs/LaserScan` | 激光雷达数据 |
| `/odom` | `nav_msgs/Odometry` | 里程计数据 |
| `/cmd_vel` | `geometry_msgs/Twist` | 速度控制指令 |

## 课程设计报告

详细设计文档与实验分析见项目根目录下的 `system_design.md`。
