#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图像发布节点
- 订阅摄像头原始话题 /camera/image_raw
- 将图像重新发布到标准化话题 /camera/image
- 同时转发相机内参到 /camera/camera_info_out
- 以 30Hz 频率发布，解耦仿真平台依赖
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, CameraInfo


class ImagePublisherNode(Node):
    def __init__(self):
        super().__init__('image_publisher')

        # 声明参数：原始话题名可在 launch 中覆盖
        self.declare_parameter('input_image_topic', '/camera/image_raw')
        self.declare_parameter('input_camera_info_topic', '/camera/camera_info')
        self.declare_parameter('output_image_topic', '/camera/image')
        self.declare_parameter('output_camera_info_topic', '/camera/camera_info_out')
        self.declare_parameter('publish_rate', 30.0)

        input_topic = self.get_parameter('input_image_topic').value
        input_info_topic = self.get_parameter('input_camera_info_topic').value
        output_topic = self.get_parameter('output_image_topic').value
        info_topic = self.get_parameter('output_camera_info_topic').value
        rate = self.get_parameter('publish_rate').value

        self.get_logger().info(
            f'订阅 {input_topic}，转发到 {output_topic}，频率 {rate}Hz'
        )

        # 发布者
        self.image_pub = self.create_publisher(Image, output_topic, 10)
        self.info_pub = self.create_publisher(CameraInfo, info_topic, 10)

        # 订阅者：缓存最新图像与相机内参
        self.latest_image = None
        self.latest_info = None
        self.image_sub = self.create_subscription(
            Image, input_topic, self.image_callback, 10
        )
        self.info_sub = self.create_subscription(
            CameraInfo, input_info_topic, self.info_callback, 10
        )

        # 30Hz 定时发布
        self.timer = self.create_timer(1.0 / rate, self.timer_callback)

    def image_callback(self, msg: Image):
        """缓存最新图像帧，更新时间戳为当前 ROS 时间。"""
        self.latest_image = msg
        self.latest_image.header.stamp = self.get_clock().now().to_msg()

    def info_callback(self, msg: CameraInfo):
        """缓存最新相机内参。"""
        self.latest_info = msg

    def timer_callback(self):
        """定时发布图像与相机内参。"""
        if self.latest_image is not None:
            self.latest_image.header.stamp = self.get_clock().now().to_msg()
            self.image_pub.publish(self.latest_image)
        if self.latest_info is not None:
            self.info_pub.publish(self.latest_info)


def main(args=None):
    rclpy.init(args=args)
    node = ImagePublisherNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
