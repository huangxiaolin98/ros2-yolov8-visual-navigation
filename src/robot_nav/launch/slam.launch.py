import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    package_dir = get_package_share_directory('robot_nav')
    slam_params = os.path.join(package_dir, 'config', 'slam_params.yaml')

    return LaunchDescription([
        DeclareLaunchArgument('slam_params_file', default_value=slam_params,
                              description='SLAM 参数文件路径'),

        # 启动 mock 传感器节点
        Node(
            package='robot_nav',
            executable='mock_sensors',
            name='mock_sensors',
            output='screen',
        ),

        # 启动 slam_toolbox 在线建图
        Node(
            package='slam_toolbox',
            executable='async_slam_toolbox_node',
            name='slam_toolbox',
            output='screen',
            parameters=[LaunchConfiguration('slam_params_file')],
        ),
    ])
