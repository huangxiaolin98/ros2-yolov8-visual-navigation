from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('target_class', default_value='bottle',
                              description='YOLOv8 要检测的目标类别'),
        DeclareLaunchArgument('model_path', default_value='yolov8n.pt',
                              description='YOLOv8 模型路径'),
        DeclareLaunchArgument('camera_frame', default_value='camera_link',
                              description='相机坐标系名称'),
        DeclareLaunchArgument('map_frame', default_value='map',
                              description='地图坐标系名称'),

        Node(
            package='robot_nav',
            executable='image_publisher',
            name='image_publisher',
            output='screen',
            parameters=[{
                'input_image_topic': '/webots/camera',
                'output_image_topic': '/camera/image',
                'output_camera_info_topic': '/camera/camera_info',
                'publish_rate': 30.0,
            }]
        ),

        Node(
            package='robot_nav',
            executable='yolo_detector',
            name='yolo_detector',
            output='screen',
            parameters=[{
                'input_topic': '/camera/image',
                'output_topic': '/detected_objects',
                'model_path': LaunchConfiguration('model_path'),
                'target_class': LaunchConfiguration('target_class'),
                'confidence_threshold': 0.5,
                'process_rate': 15.0,
            }]
        ),

        Node(
            package='robot_nav',
            executable='coord_transformer',
            name='coord_transformer',
            output='screen',
            parameters=[{
                'detection_topic': '/detected_objects',
                'camera_info_topic': '/camera/camera_info',
                'target_pose_topic': '/target_pose',
                'camera_frame': LaunchConfiguration('camera_frame'),
                'map_frame': LaunchConfiguration('map_frame'),
                'target_class': LaunchConfiguration('target_class'),
                'default_depth': 1.0,
                'publish_rate': 10.0,
            }]
        ),

        Node(
            package='robot_nav',
            executable='nav_controller',
            name='nav_controller',
            output='screen',
            parameters=[{
                'target_pose_topic': '/target_pose',
                'navigation_timeout': 60.0,
                'recovery_timeout': 10.0,
                'confirm_frames': 3,
            }]
        ),
    ])
