import os
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    package_dir = get_package_share_directory('robot_nav')

    webots_launch = os.path.join(package_dir, 'launch', 'webots.launch.py')
    nav2_launch = os.path.join(package_dir, 'launch', 'nav2.launch.py')
    vision_launch = os.path.join(package_dir, 'launch', 'vision.launch.py')

    return LaunchDescription([
        # 第一层：启动 Webots 仿真环境
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(webots_launch)
        ),

        # 第二层：延迟 5 秒后启动 Nav2，确保仿真环境已就绪
        TimerAction(
            period=5.0,
            actions=[
                IncludeLaunchDescription(
                    PythonLaunchDescriptionSource(nav2_launch),
                    launch_arguments={'use_sim_time': 'true'}.items()
                )
            ]
        ),

        # 第三层：延迟 10 秒后启动视觉导航节点，确保 Nav2 初始化完成
        TimerAction(
            period=10.0,
            actions=[
                IncludeLaunchDescription(
                    PythonLaunchDescriptionSource(vision_launch)
                )
            ]
        ),
    ])
