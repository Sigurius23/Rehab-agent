"""SKEL parameter and joint names (SKEL v1.1, skel/kin_skel.py in MarilynKeller/SKEL).

Most lower-limb names coincide with Rajagopal/Pose2Sim OpenSim coordinates;
spine (lumbar/thorax/head) and shoulder (scapula + 3-DoF shoulder) do not map
one-to-one, which is why the OpenSim stage solves IK on markers instead of
copying angles.
"""

SKEL_JOINT_NAMES = [
    "pelvis", "femur_r", "tibia_r", "talus_r", "calcn_r", "toes_r",
    "femur_l", "tibia_l", "talus_l", "calcn_l", "toes_l",
    "lumbar_body", "thorax", "head",
    "scapula_r", "humerus_r", "ulna_r", "radius_r", "hand_r",
    "scapula_l", "humerus_l", "ulna_l", "radius_l", "hand_l",
]

SKEL_POSE_PARAM_NAMES = [
    "pelvis_tilt", "pelvis_list", "pelvis_rotation",
    "hip_flexion_r", "hip_adduction_r", "hip_rotation_r", "knee_angle_r",
    "ankle_angle_r", "subtalar_angle_r", "mtp_angle_r",
    "hip_flexion_l", "hip_adduction_l", "hip_rotation_l", "knee_angle_l",
    "ankle_angle_l", "subtalar_angle_l", "mtp_angle_l",
    "lumbar_bending", "lumbar_extension", "lumbar_twist",
    "thorax_bending", "thorax_extension", "thorax_twist",
    "head_bending", "head_extension", "head_twist",
    "scapula_abduction_r", "scapula_elevation_r", "scapula_upward_rot_r",
    "shoulder_r_x", "shoulder_r_y", "shoulder_r_z",
    "elbow_flexion_r", "pro_sup_r", "wrist_flexion_r", "wrist_deviation_r",
    "scapula_abduction_l", "scapula_elevation_l", "scapula_upward_rot_l",
    "shoulder_l_x", "shoulder_l_y", "shoulder_l_z",
    "elbow_flexion_l", "pro_sup_l", "wrist_flexion_l", "wrist_deviation_l",
]

assert len(SKEL_JOINT_NAMES) == 24 and len(SKEL_POSE_PARAM_NAMES) == 46
