from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'robot_nav'

setup(
    name=package_name,
    version='0.0.1',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob(os.path.join('launch', '*.launch.py'))),
        (os.path.join('share', package_name, 'config'), glob(os.path.join('config', '*'))),
        (os.path.join('share', package_name, 'worlds'), glob(os.path.join('worlds', '*'))),
        (os.path.join('share', package_name, 'maps'), glob(os.path.join('maps', '*'))),
        (os.path.join('share', package_name, 'models'), glob(os.path.join('models', '*'))),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='huangxiaogua',
    maintainer_email='huangxiaogua@example.com',
    description='基于ROS2与YOLOv8的移动机器人视觉引导自主导航系统',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'image_publisher = robot_nav.image_publisher:main',
            'yolo_detector = robot_nav.yolo_detector:main',
            'coord_transformer = robot_nav.coord_transformer:main',
            'nav_controller = robot_nav.nav_controller:main',
        ],
    },
)
