import os
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    package_dir = get_package_share_directory('robot_nav')

    nav2_launch = os.path.join(package_dir, 'launch', 'nav2.launch.py')
    vision_launch = os.path.join(package_dir, 'launch', 'vision.launch.py')

    return LaunchDescription([
        # 第一层：启动 mock 传感器节点（替代 Gazebo 仿真）
        Node(
            package='robot_nav',
            executable='mock_sensors',
            name='mock_sensors',
            output='screen',
        ),

        # 第二层：延迟 3 秒后启动 Nav2，确保 mock 传感器和 TF 已就绪
        TimerAction(
            period=3.0,
            actions=[
                IncludeLaunchDescription(
                    PythonLaunchDescriptionSource(nav2_launch),
                )
            ]
        ),

        # 第三层：延迟 8 秒后启动视觉导航节点，确保 Nav2 初始化完成
        TimerAction(
            period=8.0,
            actions=[
                IncludeLaunchDescription(
                    PythonLaunchDescriptionSource(vision_launch)
                )
            ]
        ),
    ])
