---
type: "test"
title: "Positive control: OpenCap's own result against the motion capture"
status: "passed"
area: "pipeline"
parent: "[[kin-labvalidation]]"
expected: "Proposal: through this pipeline's comparison, OpenCap's five-camera result on subject 2's squats1 has a mean absolute error over the lower-limb and trunk angles within 2 degrees of the 4.5 degrees its paper reports, with one clear lag"
result: "Met (2026-11-10): MAE over the 18 lower-limb and trunk angles 6.32 deg, +1.82 from the paper's 4.5 (16 without subtalar: 6.44); one clear lag, 0.417 s (ratio 3.02)"
fresh: "no"
record: "validation/results/kin_control_opencap_subject2_squats1.json"
source: "video pilot of 2026-11-10 (plan/nodes/t-kin-pilot.md)"
updated: "2026-11-10"
---
# Positive control: OpenCap's own result against the motion capture

The expected result above was proposed on 2026-11-10 and approved by the owner before the control ran.

It answers two questions the pilot left open:
- **Does the comparison tool reproduce a published number?** OpenCap's paper reports a mean absolute error of 4.5° against marker motion capture, over all its activities. If this tool gives a very different figure from OpenCap's own files, the tool is wrong somewhere: the lag, a coordinate's name or sign, or how the motion capture is read.
- **What is the bar?** OpenCap's result uses the same model as the motion capture, so its errors carry no difference between model definitions. The gap between its errors and the pipeline's shows how much of the pipeline's bias comes from its model.

It needs no videos and no GPU. OpenCap's result for the pilot's trial is already on the laptop, from the fixture. If the LabValidation copy also holds OpenCap's results for the other subjects and trials, the control extends to all of them; whether it does is to be checked on the laptop.

Not fresh for the pilot's trial: its lag against the motion capture has been looked at (0.417 s, clear), but no error. The paper's figure covers all activities, so a squat alone may differ; that is why the proposal allows 2°.

**Lag, recorded before any error was computed (2026-11-10, lab laptop).** OpenCap's `squats1.mot` from the fixture
against the motion capture, aligned as `rehabtwin validate` aligns them (14 shared sagittal coordinates, ±4 s):
best lag 0.417 s, next local minimum at −1.183 s with 3.02 times the best's objective. The peak is clear by the
pilot's criterion (at least 0.2 s inside the window; every other minimum more than 0.3 s away at least twice the
best).

**Angle set, fixed before any error was computed.** "Lower-limb and trunk angles" are taken as 18 coordinates:
pelvis tilt, list and rotation; per side hip flexion, adduction and rotation, knee angle, ankle angle and subtalar
angle; lumbar extension, bending and rotation. A secondary figure leaves out the two subtalar angles (16), in case
the paper's set has none; the expected result is judged on the 18.

**Result (2026-11-10): the expected result is met, near its edge.** The mean absolute error over the
18 lower-limb and trunk angles is 6.32°, +1.82° from the paper's 4.5° (allowed ±2°); without the subtalar
angles, 6.44°. The lag is 0.417 s, with a clear peak. Coverage 99.8%. Figures:
`validation/results/kin_control_opencap_subject2_squats1.json`; scripts: `validation/runs/kin_control_opencap_subject2_squats1/`.

| Coordinate (the first 18 are the set) | RMSE | MAE | Bias | Spread |
|---|---|---|---|---|
| ankle_angle_l | 4.70 | 3.97 | -3.82 | 2.74 |
| ankle_angle_r | 6.31 | 5.18 | -4.91 | 3.96 |
| hip_adduction_l | 7.86 | 6.49 | +6.24 | 4.78 |
| hip_adduction_r | 8.33 | 6.88 | -6.04 | 5.74 |
| hip_flexion_l | 13.90 | 12.08 | -8.89 | 10.69 |
| hip_flexion_r | 11.54 | 10.25 | -8.44 | 7.87 |
| hip_rotation_l | 6.50 | 5.82 | -0.18 | 6.50 |
| hip_rotation_r | 6.08 | 5.14 | -0.41 | 6.07 |
| knee_angle_l | 3.95 | 3.61 | -3.61 | 1.59 |
| knee_angle_r | 3.13 | 2.65 | -0.65 | 3.06 |
| lumbar_bending | 1.81 | 1.51 | +0.12 | 1.80 |
| lumbar_extension | 10.85 | 9.52 | -3.12 | 10.39 |
| lumbar_rotation | 9.40 | 8.69 | -8.69 | 3.59 |
| pelvis_list | 3.56 | 2.82 | +2.63 | 2.40 |
| pelvis_rotation | 8.82 | 8.36 | +8.36 | 2.79 |
| pelvis_tilt | 11.66 | 10.11 | +7.39 | 9.03 |
| subtalar_angle_l | 4.10 | 3.31 | -2.08 | 3.53 |
| subtalar_angle_r | 9.42 | 7.40 | -7.22 | 6.06 |
| arm_add_l | 2.64 | 2.24 | +1.55 | 2.14 |
| arm_add_r | 3.15 | 2.52 | +2.20 | 2.26 |
| arm_flex_l | 8.72 | 7.18 | -6.54 | 5.77 |
| arm_flex_r | 11.61 | 9.86 | -9.41 | 6.80 |
| arm_rot_l | 2.31 | 1.87 | -0.81 | 2.16 |
| arm_rot_r | 4.02 | 3.15 | -1.23 | 3.83 |
| elbow_flex_l | 7.48 | 6.19 | -1.32 | 7.37 |
| elbow_flex_r | 8.42 | 7.43 | +1.09 | 8.35 |
| mtp_angle_l | 7.47 | 7.47 | +7.47 | 0.24 |
| mtp_angle_r | 7.47 | 7.47 | +7.47 | 0.24 |
| pro_sup_l | 29.66 | 28.71 | -28.70 | 7.46 |
| pro_sup_r | 8.49 | 7.47 | -7.26 | 4.40 |

Spread is the SD of the difference. The largest errors in the set are hip flexion (MAE 12.1° left, 10.3° right), pelvis
tilt (10.1°) and lumbar extension (9.5°), with biases of opposite sign at the pelvis (+7.4°) and the hips (−8.9° and
−8.4°). That pattern is one squat, one subject; whether it comes from the trial or from the comparison is not settled
here.

**OpenCap's own video results in the LabValidation copy** (checked from the zip's listing; nothing extracted or
opened): `LabValidation_withoutVideos.zip` holds `<subject>/OpenSimData/Video/` for all 10 subjects. That is 1,440 IK
results, 144 per subject: three pose estimators (HRNet, OpenPose default, OpenPose high accuracy), each with 2, 3 and
5 cameras, and 16 trials per setup (squats, sit-to-stand, drop jumps, walking), about 2.1 GB uncompressed. The
laptop's extracted copy holds only the motion capture, so these would have to be extracted first. HRNet with two
cameras also has a `Dynamics` folder, which was not opened. None of it has been run.
