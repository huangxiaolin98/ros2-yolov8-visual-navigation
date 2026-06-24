#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
导航控制节点
- 订阅 /target_pose
- 调用 Nav2 的 NavigateToPose Action
- 实现 IDLE / DETECTING / NAVIGATING / RECOVERING 状态机
- 支持超时取消、目标更新、失败恢复
"""

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import NavigateToPose
from action_msgs.msg import GoalStatus


class NavControllerNode(Node):
    def __init__(self):
        super().__init__('nav_controller')

        # 参数
        self.declare_parameter('target_pose_topic', '/target_pose')
        self.declare_parameter('navigate_to_pose_action', 'navigate_to_pose')
        self.declare_parameter('navigation_timeout', 60.0)
        self.declare_parameter('recovery_timeout', 10.0)
        self.declare_parameter('confirm_frames', 3)

        self.target_topic = self.get_parameter('target_pose_topic').value
        self.nav_action = self.get_parameter('navigate_to_pose_action').value
        self.nav_timeout = self.get_parameter('navigation_timeout').value
        self.recovery_timeout = self.get_parameter('recovery_timeout').value
        self.confirm_frames = self.get_parameter('confirm_frames').value

        # Action 客户端
        self.nav_client = ActionClient(self, NavigateToPose, self.nav_action)

        # 订阅目标位姿
        self.target_sub = self.create_subscription(
            PoseStamped, self.target_topic, self.target_callback, 10
        )

        # 状态机
        self.state = 'IDLE'
        self.current_goal_handle = None
        self.latest_target = None
        self.detect_count = 0
        self.nav_start_time = None
        self.recovery_start_time = None

        # 定时器：状态机主循环 10Hz
        self.timer = self.create_timer(0.1, self.state_machine_loop)

        self.get_logger().info('导航控制节点已启动，状态: IDLE')

    def target_callback(self, msg: PoseStamped):
        """接收目标位姿并缓存。"""
        self.latest_target = msg

    def state_machine_loop(self):
        """状态机主循环。"""
        now = self.get_clock().now()

        if self.state == 'IDLE':
            if self.latest_target is not None:
                self.state = 'DETECTING'
                self.detect_count = 0
                self.get_logger().info('检测到目标候选，进入确认阶段')

        elif self.state == 'DETECTING':
            if self.latest_target is None:
                self.state = 'IDLE'
                return
            self.detect_count += 1
            if self.detect_count >= self.confirm_frames:
                self.get_logger().info('目标确认，发送导航 Goal')
                self.send_goal(self.latest_target)
                self.state = 'NAVIGATING'
                self.nav_start_time = now

        elif self.state == 'NAVIGATING':
            # 检查导航超时
            if self.nav_start_time is not None:
                elapsed = (now - self.nav_start_time).nanoseconds / 1e9
                if elapsed > self.nav_timeout:
                    self.get_logger().warn('导航超时，取消当前任务')
                    self.cancel_goal()
                    self.state = 'RECOVERING'
                    self.recovery_start_time = now
                    return

            # 目标更新：如果收到新目标且位置变化较大，重新导航
            if self.latest_target is not None and self.current_goal_handle is not None:
                # 简单策略：只要有新目标就重新发送
                self.get_logger().info('目标更新，重新发送导航 Goal')
                self.cancel_goal()
                self.send_goal(self.latest_target)
                self.nav_start_time = now

        elif self.state == 'RECOVERING':
            if self.recovery_start_time is not None:
                elapsed = (now - self.recovery_start_time).nanoseconds / 1e9
                if elapsed > self.recovery_timeout:
                    self.get_logger().info('恢复超时，回到 IDLE')
                    self.state = 'IDLE'
                    return
            if self.latest_target is not None:
                self.get_logger().info('恢复阶段重新检测到目标，再次导航')
                self.send_goal(self.latest_target)
                self.state = 'NAVIGATING'
                self.nav_start_time = now

    def send_goal(self, pose: PoseStamped):
        """异步发送导航目标。"""
        if not self.nav_client.wait_for_server(timeout_sec=2.0):
            self.get_logger().error('Nav2 Action 服务端未连接')
            return

        goal_msg = NavigateToPose.Goal()
        goal_msg.pose = pose

        self.get_logger().info(
            f'发送目标: ({pose.pose.position.x:.2f}, {pose.pose.position.y:.2f})'
        )

        send_goal_future = self.nav_client.send_goal_async(
            goal_msg,
            feedback_callback=self.feedback_callback
        )
        send_goal_future.add_done_callback(self.goal_response_callback)

    def goal_response_callback(self, future):
        """Goal 被接受/拒绝的回调。"""
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().warn('导航 Goal 被拒绝')
            self.state = 'RECOVERING'
            self.recovery_start_time = self.get_clock().now()
            return

        self.current_goal_handle = goal_handle
        self.get_logger().info('导航 Goal 已接受')

        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(self.result_callback)

    def feedback_callback(self, feedback_msg):
        """实时反馈回调，打印剩余距离。"""
        feedback = feedback_msg.feedback
        remaining = feedback.distance_remaining
        self.get_logger().info(f'剩余距离: {remaining:.2f} m')

    def result_callback(self, future):
        """导航结果回调。"""
        result = future.result()
        status = result.status
        self.current_goal_handle = None

        if status == GoalStatus.STATUS_SUCCEEDED:
            self.get_logger().info('导航成功！')
            self.state = 'IDLE'
        elif status == GoalStatus.STATUS_CANCELED:
            self.get_logger().warn('导航被取消')
            self.state = 'RECOVERING'
            self.recovery_start_time = self.get_clock().now()
        else:
            self.get_logger().warn(f'导航失败，状态码: {status}，进入恢复模式')
            self.state = 'RECOVERING'
            self.recovery_start_time = self.get_clock().now()

    def cancel_goal(self):
        """取消当前导航任务。"""
        if self.current_goal_handle is not None:
            self.get_logger().info('取消当前导航 Goal')
            cancel_future = self.current_goal_handle.cancel_goal_async()
            cancel_future.add_done_callback(self.cancel_done_callback)
            self.current_goal_handle = None

    def cancel_done_callback(self, future):
        """取消完成回调。"""
        cancel_response = future.result()
        if len(cancel_response.goals_canceling) > 0:
            self.get_logger().info('取消请求已生效')
        else:
            self.get_logger().warn('取消请求未生效')


def main(args=None):
    rclpy.init(args=args)
    node = NavControllerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
