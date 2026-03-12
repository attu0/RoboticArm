import os
import yaml
import xacro
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import RegisterEventHandler
from launch.event_handlers import OnProcessExit
from launch_ros.actions import Node


def load_yaml(pkg_path, file_path):
    full_path = os.path.join(pkg_path, file_path)
    with open(full_path, 'r') as f:
        return yaml.safe_load(f)


def generate_launch_description():
    urdf_pkg   = get_package_share_directory('urdf_description')
    moveit_pkg = get_package_share_directory('urdf_moveit_config')

    # Robot description
    robot_description = {
        'robot_description': xacro.process_file(
            os.path.join(urdf_pkg, 'urdf', 'urdf.xacro')
        ).toxml()
    }

    # SRDF
    with open(os.path.join(moveit_pkg, 'config', 'urdf.srdf'), 'r') as f:
        robot_description_semantic = {'robot_description_semantic': f.read()}

    # Config yamls
    kinematics_yaml    = load_yaml(moveit_pkg, 'config/kinematics.yaml')
    ompl_yaml          = load_yaml(moveit_pkg, 'config/ompl_planning.yaml')
    moveit_ctrl_yaml   = load_yaml(moveit_pkg, 'config/moveit_controllers.yaml')
    joint_limits_yaml  = load_yaml(moveit_pkg, 'config/joint_limits.yaml')

    ompl_planning_pipeline = {
        'planning_pipelines': ['ompl'],
        'ompl': {
            'planning_plugin': ompl_yaml['planning_plugin'],
            'request_adapters': ompl_yaml['request_adapters'],
            'start_state_max_bounds_error': ompl_yaml['start_state_max_bounds_error'],
        }
    }

    trajectory_execution = {
        'moveit_manage_controllers': True,
        'trajectory_execution.allowed_execution_duration_scaling': 1.2,
        'trajectory_execution.allowed_goal_duration_margin': 0.5,
        'trajectory_execution.allowed_start_tolerance': 0.01,
    }

    planning_scene_monitor = {
        'publish_planning_scene': True,
        'publish_geometry_updates': True,
        'publish_state_updates': True,
        'publish_transforms_updates': True,
    }

    # Nodes
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[robot_description],
        output='screen'
    )

    controller_manager = Node(
        package='controller_manager',
        executable='ros2_control_node',
        parameters=[
            robot_description,
            os.path.join(urdf_pkg, 'config', 'controllers.yaml')
        ],
        output='screen'
    )

    joint_state_broadcaster_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['joint_state_broadcaster', '--controller-manager', '/controller_manager'],
        output='screen'
    )

    arm_controller_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['arm_controller', '--controller-manager', '/controller_manager'],
        output='screen'
    )

    delay_arm_controller = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=joint_state_broadcaster_spawner,
            on_exit=[arm_controller_spawner]
        )
    )

    move_group_node = Node(
        package='moveit_ros_move_group',
        executable='move_group',
        parameters=[
            robot_description,
            robot_description_semantic,
            {'robot_description_kinematics': kinematics_yaml},
            ompl_planning_pipeline,
            trajectory_execution,
            moveit_ctrl_yaml,
            planning_scene_monitor,
            {'use_sim_time': False},
        ],
        output='screen'
    )

    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', os.path.join(moveit_pkg, 'config', 'moveit.rviz')],
        parameters=[
            robot_description,
            robot_description_semantic,
            {'robot_description_kinematics': kinematics_yaml},
        ],
        output='screen'
    )

    return LaunchDescription([
        robot_state_publisher,
        controller_manager,
        joint_state_broadcaster_spawner,
        delay_arm_controller,
        move_group_node,
        rviz_node,
    ])
