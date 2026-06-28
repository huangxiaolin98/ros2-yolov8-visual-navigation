import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, RegisterEventHandler
from launch.substitutions import LaunchConfiguration, Command
from launch_ros.actions import Node
from launch.event_handlers import OnProcessExit
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    package_dir = get_package_share_directory('robot_nav')

    # 默认参数
    world_file = os.path.join(package_dir, 'worlds', 'indoor_env.world')
    urdf_file = os.path.join(package_dir, 'urdf', 'robot_nav.urdf.xacro')

    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    world = LaunchConfiguration('world', default=world_file)
    x_pos = LaunchConfiguration('x_pos', default='0.0')
    y_pos = LaunchConfiguration('y_pos', default='0.0')
    z_pos = LaunchConfiguration('z_pos', default='0.01')

    # 读取 URDF（通过 xacro 处理）
    robot_description = Command(['xacro ', urdf_file])

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='true',
                              description='是否使用仿真时间'),
        DeclareLaunchArgument('world', default_value=world_file,
                              description='Gazebo 世界文件路径'),
        DeclareLaunchArgument('x_pos', default_value='0.0',
                              description='机器人初始 X 坐标'),
        DeclareLaunchArgument('y_pos', default_value='0.0',
                              description='机器人初始 Y 坐标'),
        DeclareLaunchArgument('z_pos', default_value='0.01',
                              description='机器人初始 Z 坐标'),

        # 启动 Gazebo（server + client）
        ExecuteProcess(
            cmd=['gazebo', '--verbose', '-s', 'libgazebo_ros_init.so',
                 '-s', 'libgazebo_ros_factory.so', world],
            output='screen'
        ),

        # robot_state_publisher：发布 TF 树（base_link -> camera_link 等）
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name='robot_state_publisher',
            output='screen',
            parameters=[{
                'robot_description': robot_description,
                'use_sim_time': use_sim_time,
            }]
        ),

        # spawn_entity：在 Gazebo 中生成机器人
        Node(
            package='gazebo_ros',
            executable='spawn_entity.py',
            name='spawn_entity',
            output='screen',
            arguments=[
                '-topic', 'robot_description',
                '-entity', 'robot_nav',
                '-x', x_pos,
                '-y', y_pos,
                '-z', z_pos,
            ]
        ),
    ])
