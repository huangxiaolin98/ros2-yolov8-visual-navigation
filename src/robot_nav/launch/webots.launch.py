import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    package_dir = get_package_share_directory('robot_nav')
    world_file = os.path.join(package_dir, 'worlds', 'indoor_env.wbt')

    return LaunchDescription([
        DeclareLaunchArgument('world', default_value=world_file,
                              description='Webots 世界文件路径'),
        DeclareLaunchArgument('robot_name', default_value='my_robot',
                              description='机器人名称'),

        Node(
            package='webots_ros2_driver',
            executable='driver',
            output='screen',
            parameters=[
                {'robot_description': ''},
                {'use_sim_time': True},
            ],
            arguments=['--webots-robot-name', LaunchConfiguration('robot_name')]
        ),
    ])
