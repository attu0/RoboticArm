ros2 launch urdf_description display.launch.py

cd ~/robotic_arm && colcon build && source install/setup.bash && ros2 launch urdf_moveit_config moveit.launch.py

killall -9 rviz2 move_group ros2_control_node robot_state_publisher joint_state_publisher joint_state_publisher_gui spawner 2>/dev/null; sleep 2 && echo "All killed"