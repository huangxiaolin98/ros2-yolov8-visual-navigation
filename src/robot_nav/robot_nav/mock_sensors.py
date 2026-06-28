#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mock 传感器节点 - 模拟机器人传感器数据
用于在没有 Gazebo/Webots 的情况下测试 ROS2 导航系统

发布话题:
  /camera/image_raw (sensor_msgs/Image) - 30Hz 模拟摄像头
  /scan (sensor_msgs/LaserScan) - 10Hz 模拟激光雷达
  /odom (nav_msgs/Odometry) - 20Hz 模拟里程计

广播 TF:
  odom -> base_link -> camera_link

订阅话题:
  /cmd_vel (geometry_msgs/Twist) - 更新机器人位姿
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, LaserScan, CameraInfo
from nav_msgs.msg import Odometry
from geometry_msgs.msg import TransformStamped, Twist
from tf2_ros import TransformBroadcaster
import numpy as np
import math


class MockSensors(Node):
    def __init__(self):
        super().__init__('mock_sensors')

        # 参数声明
        self.declare_parameter('image_width', 640)
        self.declare_parameter('image_height', 480)
        self.declare_parameter('laser_range', 10.0)
        self.declare_parameter('laser_fov', math.pi)
        self.declare_parameter('laser_count', 360)

        self.img_width = self.get_parameter('image_width').value
        self.img_height = self.get_parameter('image_height').value
        self.laser_range = self.get_parameter('laser_range').value
        self.laser_fov = self.get_parameter('laser_fov').value
        self.laser_count = self.get_parameter('laser_count').value

        # 机器人位姿（差分驱动模型）
        self.x = 0.0
        self.y = 0.0
        self.theta = 0.0
        self.linear_vel = 0.0
        self.angular_vel = 0.0

        # TF 广播器
        self.tf_broadcaster = TransformBroadcaster(self)

        # 订阅 cmd_vel 更新机器人运动
        self.cmd_sub = self.create_subscription(
            Twist, '/cmd_vel', self.cmd_callback, 10
        )

        # 发布者
        self.image_pub = self.create_publisher(Image, '/camera/image_raw', 10)
        self.camera_info_pub = self.create_publisher(CameraInfo, '/camera/camera_info', 10)
        self.scan_pub = self.create_publisher(LaserScan, '/scan', 10)
        self.odom_pub = self.create_publisher(Odometry, '/odom', 10)

        # 定时器：odom 20Hz, scan 10Hz, image 30Hz
        self.create_timer(0.05, self.odom_callback)       # 20Hz
        self.create_timer(0.1, self.scan_callback)         # 10Hz
        self.create_timer(1.0 / 30.0, self.image_callback) # 30Hz

        # 帧计数
        self.seq = 0

        self.get_logger().info('Mock 传感器节点已启动')
        self.get_logger().info('  - /camera/image_raw (30Hz)')
        self.get_logger().info('  - /scan (10Hz)')
        self.get_logger().info('  - /odom (20Hz)')
        self.get_logger().info('  - TF: odom -> base_link -> camera_link')

    def cmd_callback(self, msg: Twist):
        """接收 cmd_vel，更新速度"""
        self.linear_vel = msg.linear.x
        self.angular_vel = msg.angular.z

    def odom_callback(self):
        """20Hz: 更新里程计 + TF"""
        now = self.get_clock().now()
        dt = 0.05

        # 差分驱动运动学更新位姿
        self.x += self.linear_vel * math.cos(self.theta) * dt
        self.y += self.linear_vel * math.sin(self.theta) * dt
        self.theta += self.angular_vel * dt
        # 归一化角度到 [-pi, pi]
        self.theta = math.atan2(math.sin(self.theta), math.cos(self.theta))

        # 发布 odom
        odom = Odometry()
        odom.header.stamp = now.to_msg()
        odom.header.frame_id = 'odom'
        odom.child_frame_id = 'base_link'
        odom.pose.pose.position.x = self.x
        odom.pose.pose.position.y = self.y
        odom.pose.pose.position.z = 0.0
        odom.pose.pose.orientation.z = math.sin(self.theta / 2.0)
        odom.pose.pose.orientation.w = math.cos(self.theta / 2.0)
        odom.twist.twist.linear.x = self.linear_vel
        odom.twist.twist.angular.z = self.angular_vel
        self.odom_pub.publish(odom)

        # 广播 TF: odom -> base_link
        t1 = TransformStamped()
        t1.header.stamp = now.to_msg()
        t1.header.frame_id = 'odom'
        t1.child_frame_id = 'base_link'
        t1.transform.translation.x = self.x
        t1.transform.translation.y = self.y
        t1.transform.translation.z = 0.0
        t1.transform.rotation.z = math.sin(self.theta / 2.0)
        t1.transform.rotation.w = math.cos(self.theta / 2.0)
        self.tf_broadcaster.sendTransform(t1)

        # 广播 TF: base_link -> camera_link
        t2 = TransformStamped()
        t2.header.stamp = now.to_msg()
        t2.header.frame_id = 'base_link'
        t2.child_frame_id = 'camera_link'
        t2.transform.translation.x = 0.2   # 相机在机器人前方 0.2m
        t2.transform.translation.y = 0.0
        t2.transform.translation.z = 0.3   # 相机高度 0.3m
        t2.transform.rotation.w = 1.0
        self.tf_broadcaster.sendTransform(t2)

    def scan_callback(self):
        """10Hz: 生成模拟激光雷达数据"""
        now = self.get_clock().now()
        scan = LaserScan()
        scan.header.stamp = now.to_msg()
        scan.header.frame_id = 'base_link'
        scan.angle_min = -self.laser_fov / 2.0
        scan.angle_max = self.laser_fov / 2.0
        scan.angle_increment = (scan.angle_max - scan.angle_min) / self.laser_count
        scan.range_min = 0.1
        scan.range_max = self.laser_range
        scan.time_increment = 0.0
        # 模拟一个简单场景：前方有障碍物
        ranges = []
        for i in range(self.laser_count + 1):
            angle = scan.angle_min + i * scan.angle_increment
            # 模拟前方 2m 处有一面墙
            base_range = 2.0
            # 正前方最近（模拟桌子等），两侧较远
            noise = np.random.uniform(-0.1, 0.1)
            if abs(angle) < 0.3:
                # 正前方有障碍物（模拟桌椅）
                r = 1.5 + noise
            elif abs(angle) < 0.8:
                r = 3.0 + noise
            else:
                r = 5.0 + noise
            r = max(0.1, min(r, self.laser_range))
            ranges.append(r)
        scan.ranges = ranges
        self.scan_pub.publish(scan)

    def image_callback(self):
        """30Hz: 生成模拟摄像头图像"""
        now = self.get_clock().now()
        img = Image()
        img.header.stamp = now.to_msg()
        img.header.frame_id = 'camera_link'
        img.height = self.img_height
        img.width = self.img_width
        img.encoding = 'bgr8'
        img.is_bigendian = 0
        img.step = self.img_width * 3

        # 生成一个带随机噪声的图像（模拟场景）
        # 使用低分辨率的随机噪声即可，不浪费太多 CPU
        data = np.random.randint(50, 200, size=(self.img_height, self.img_width, 3), dtype=np.uint8)
        # 在图像中央放一个矩形区域模拟目标物体（如椅子）
        cy = self.img_height // 2
        cx = self.img_width // 2
        h, w = 60, 40
        data[cy - h:cy + h, cx - w:cx + w] = [0, 0, 180]  # 红色矩形

        img.data = data.tobytes()
        self.image_pub.publish(img)

        # 同时发布相机内参
        info = CameraInfo()
        info.header.stamp = now.to_msg()
        info.header.frame_id = 'camera_link'
        info.height = self.img_height
        info.width = self.img_width
        info.distortion_model = 'plumb_bob'
        fx = fy = 525.0
        cx_cam = self.img_width / 2.0
        cy_cam = self.img_height / 2.0
        info.k = [fx, 0.0, cx_cam, 0.0, fy, cy_cam, 0.0, 0.0, 1.0]
        info.p = [fx, 0.0, cx_cam, 0.0, 0.0, fy, cy_cam, 0.0, 0.0, 0.0, 1.0, 0.0]
        self.camera_info_pub.publish(info)


def main(args=None):
    rclpy.init(args=args)
    node = MockSensors()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
