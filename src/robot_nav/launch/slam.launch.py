import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.substitutions import LaunchConfiguration
from launch.launch_description_sources import PythonLaunchDescriptionSource
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    package_dir = get_package_share_directory('robot_nav')
    slam_params = os.path.join(package_dir, 'config', 'slam_params.yaml')

    return LaunchDescription([
        DeclareLaunchArgument('slam_params_file', default_value=slam_params,
                              description='SLAM 参数文件路径'),

        # 启动 Webots 仿真环境
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(package_dir, 'launch', 'webots.launch.py')
            )
        ),

        # 启动 slam_toolbox 在线建图
        # 注：需要已安装 ros-humble-slam-toolbox
        Node(
            package='slam_toolbox',
            executable='online_async_launch.py',
            name='slam_toolbox',
            output='screen',
            parameters=[LaunchConfiguration('slam_params_file')],
        ),
    ])
