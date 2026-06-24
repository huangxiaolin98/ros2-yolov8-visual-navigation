#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
坐标转换节点
- 订阅 /detected_objects 与 /camera/camera_info
- 将图像像素坐标通过相机内参反投影到相机坐标系
- 通过 TF2 查询 camera_link -> map 的变换，转换到地图坐标系
- 发布 /target_pose (geometry_msgs/PoseStamped)
"""

import rclpy
from rclpy.node import Node
from vision_msgs.msg import Detection2DArray
from sensor_msgs.msg import CameraInfo
from geometry_msgs.msg import PoseStamped, Point
import tf2_ros
from tf2_geometry_msgs import do_transform_point
import numpy as np


class CoordTransformerNode(Node):
    def __init__(self):
        super().__init__('coord_transformer')

        # 参数
        self.declare_parameter('detection_topic', '/detected_objects')
        self.declare_parameter('camera_info_topic', '/camera/camera_info')
        self.declare_parameter('target_pose_topic', '/target_pose')
        self.declare_parameter('camera_frame', 'camera_link')
        self.declare_parameter('map_frame', 'map')
        self.declare_parameter('target_class', 'bottle')
        self.declare_parameter('default_depth', 1.0)
        self.declare_parameter('publish_rate', 10.0)

        self.det_topic = self.get_parameter('detection_topic').value
        self.info_topic = self.get_parameter('camera_info_topic').value
        self.pose_topic = self.get_parameter('target_pose_topic').value
        self.camera_frame = self.get_parameter('camera_frame').value
        self.map_frame = self.get_parameter('map_frame').value
        self.target_class = self.get_parameter('target_class').value
        self.default_depth = self.get_parameter('default_depth').value
        self.publish_rate = self.get_parameter('publish_rate').value

        self.get_logger().info(
            f'相机坐标系: {self.camera_frame}，地图坐标系: {self.map_frame}'
        )

        # TF2
        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self)

        # 相机内参
        self.camera_matrix = None
        self.latest_detections = None

        # 订阅与发布
        self.det_sub = self.create_subscription(
            Detection2DArray, self.det_topic, self.detection_callback, 10
        )
        self.info_sub = self.create_subscription(
            CameraInfo, self.info_topic, self.camera_info_callback, 10
        )
        self.pose_pub = self.create_publisher(PoseStamped, self.pose_topic, 10)

        # 定时发布目标位姿
        self.timer = self.create_timer(1.0 / self.publish_rate, self.timer_callback)

    def camera_info_callback(self, msg: CameraInfo):
        """提取 3x3 内参矩阵 K。"""
        if self.camera_matrix is None:
            self.camera_matrix = np.array(msg.k).reshape(3, 3)
            self.get_logger().info(f'相机内参: fx={self.camera_matrix[0,0]:.2f}, fy={self.camera_matrix[1,1]:.2f}')

    def detection_callback(self, msg: Detection2DArray):
        """缓存最新检测结果，只保留目标类别中置信度最高的一个。"""
        best_det = None
        best_score = 0.0
        for det in msg.detections:
            for result in det.results:
                if result.hypothesis.class_id != self.target_class:
                    continue
                if result.hypothesis.score > best_score:
                    best_score = result.hypothesis.score
                    best_det = det
        self.latest_detections = best_det

    def pixel_to_camera(self, u: float, v: float) -> tuple:
        """
        像素坐标反投影到相机坐标系（固定深度）。
        返回 (x, y, z) in camera_frame。
        """
        if self.camera_matrix is None:
            return None
        fx = self.camera_matrix[0, 0]
        fy = self.camera_matrix[1, 1]
        cx = self.camera_matrix[0, 2]
        cy = self.camera_matrix[1, 2]

        # 归一化图像坐标
        x_norm = (u - cx) / fx
        y_norm = (v - cy) / fy

        d = self.default_depth
        X = d * x_norm
        Y = d * y_norm
        Z = d
        return (X, Y, Z)

    def timer_callback(self):
        if self.latest_detections is None or self.camera_matrix is None:
            return

        det = self.latest_detections
        u = det.bbox.center.position.x
        v = det.bbox.center.position.y

        camera_coord = self.pixel_to_camera(u, v)
        if camera_coord is None:
            return

        # 查询 camera_link -> map 的变换
        try:
            transform = self.tf_buffer.lookup_transform(
                self.map_frame,
                self.camera_frame,
                rclpy.time.Time(),
                timeout=rclpy.duration.Duration(seconds=0.5)
            )
        except tf2_ros.TransformException as e:
            self.get_logger().warn(f'TF 变换失败: {e}')
            return

        # 将相机坐标系下的点转换到地图坐标系
        point_cam = Point()
        point_cam.x, point_cam.y, point_cam.z = camera_coord
        point_map = do_transform_point(point_cam, transform)

        # 发布目标位姿（目标在地面上，z 设为 0）
        pose = PoseStamped()
        pose.header.stamp = self.get_clock().now().to_msg()
        pose.header.frame_id = self.map_frame
        pose.pose.position.x = point_map.point.x
        pose.pose.position.y = point_map.point.y
        pose.pose.position.z = 0.0
        pose.pose.orientation.w = 1.0

        self.pose_pub.publish(pose)
        self.get_logger().info(
            f'目标位姿: ({pose.pose.position.x:.2f}, {pose.pose.position.y:.2f})'
        )


def main(args=None):
    rclpy.init(args=args)
    node = CoordTransformerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
