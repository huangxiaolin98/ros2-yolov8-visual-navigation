#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YOLOv8 检测节点
- 订阅 /camera/image
- 调用 YOLOv8 进行目标检测
- 将检测结果封装为 vision_msgs/Detection2DArray
- 发布到 /detected_objects
"""

import os
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import Image
from vision_msgs.msg import Detection2DArray, Detection2D, ObjectHypothesisWithPose
from cv_bridge import CvBridge
import cv2
import numpy as np


class YoloDetectorNode(Node):
    def __init__(self):
        super().__init__('yolo_detector')

        # 参数
        self.declare_parameter('input_topic', '/camera/image')
        self.declare_parameter('output_topic', '/detected_objects')
        self.declare_parameter('model_path', 'yolov8n.pt')
        self.declare_parameter('target_class', 'bottle')
        self.declare_parameter('confidence_threshold', 0.5)
        self.declare_parameter('process_rate', 15.0)

        input_topic = self.get_parameter('input_topic').value
        output_topic = self.get_parameter('output_topic').value
        model_path = self.get_parameter('model_path').value
        self.target_class = self.get_parameter('target_class').value
        self.conf_threshold = self.get_parameter('confidence_threshold').value
        self.process_rate = self.get_parameter('process_rate').value

        self.get_logger().info(
            f'模型: {model_path}，目标类别: {self.target_class}'
        )

        # 延迟加载模型，避免在 import 阶段耗时
        self.model = None
        self.bridge = CvBridge()
        self.latest_image = None
        self.last_process_time = self.get_clock().now()

        # 图像订阅使用 best_effort，保证实时性
        image_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            depth=5
        )
        self.image_sub = self.create_subscription(
            Image, input_topic, self.image_callback, image_qos
        )

        # 检测结果发布使用 reliable
        self.det_pub = self.create_publisher(Detection2DArray, output_topic, 10)

        # 用定时器控制检测频率（15Hz）
        self.timer = self.create_timer(1.0 / self.process_rate, self.process_frame)

    def load_model(self):
        """懒加载 YOLOv8 模型。"""
        if self.model is not None:
            return True
        try:
            from ultralytics import YOLO
            model_path = self.get_parameter('model_path').value
            # 若指定为相对路径，优先在项目 models 目录下查找
            if not os.path.isabs(model_path) and not os.path.exists(model_path):
                pkg_share = os.path.join(
                    os.path.dirname(os.path.dirname(__file__)),
                    'models', model_path
                )
                if os.path.exists(pkg_share):
                    model_path = pkg_share
            self.model = YOLO(model_path)
            self.get_logger().info('YOLOv8 模型加载完成')
            return True
        except Exception as e:
            self.get_logger().error(f'模型加载失败: {e}')
            return False

    def image_callback(self, msg: Image):
        """缓存最新图像。"""
        self.latest_image = msg

    def process_frame(self):
        """按控制频率执行检测并发布结果。"""
        if self.latest_image is None:
            return
        if not self.load_model():
            return

        try:
            cv_image = self.bridge.imgmsg_to_cv2(self.latest_image, 'bgr8')
        except Exception as e:
            self.get_logger().warn(f'图像转换失败: {e}')
            return

        # YOLOv8 推理
        results = self.model(cv_image, verbose=False)

        det_array = Detection2DArray()
        det_array.header = self.latest_image.header
        det_array.header.stamp = self.get_clock().now().to_msg()

        h, w = cv_image.shape[:2]

        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue
            for box in boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                name = self.model.names.get(cls_id, str(cls_id))

                if name != self.target_class or conf < self.conf_threshold:
                    continue

                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                cx = (x1 + x2) / 2.0
                cy = (y1 + y2) / 2.0
                bw = x2 - x1
                bh = y2 - y1

                det = Detection2D()
                det.header = det_array.header
                det.bbox.center.position.x = cx
                det.bbox.center.position.y = cy
                det.bbox.size_x = bw
                det.bbox.size_y = bh

                hypothesis = ObjectHypothesisWithPose()
                hypothesis.hypothesis.class_id = name
                hypothesis.hypothesis.score = conf
                det.results.append(hypothesis)

                det_array.detections.append(det)

        self.det_pub.publish(det_array)
        if det_array.detections:
            self.get_logger().info(
                f'检测到 {len(det_array.detections)} 个 {self.target_class}'
            )


def main(args=None):
    rclpy.init(args=args)
    node = YoloDetectorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
