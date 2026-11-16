---
type: "test"
title: "One camera plus simulated pelvis, thigh and shank sensors, against the motion capture"
status: "planned"
area: "pipeline"
parent: "[[kin-camera-plus-imu-sim]]"
expected: "Under the assumed noise, with pelvis, thigh and shank sensors, the one-camera MediaPipe route's sagittal knee error at lag 0 is at most 8 degrees and its ankle at most 10 degrees, as means over subjects; the hip and pelvis tilt stay within part 1's limits (10 and 5 degrees)"
fresh: "no"
source: "owner 2026-11-16, after t-kin-camera-plus-imu-sim"
updated: "2026-11-16"
---
# One camera plus simulated pelvis, thigh and shank sensors, against the motion capture

The expected result above was approved by the owner on 2026-11-16, before anything was computed. This is part 2 of [[t-kin-camera-plus-imu-sim]].

**Method:** exactly as [[t-kin-camera-plus-imu-sim]] and its committed details (commit bf56aea), with one more sensor set: pelvis, both thighs and both shanks. The assumed noise, the weights, the calibration, the trials and lag 0 are the same, and nothing else changes. The shank sensors sit on the pipeline model's `tibia_r` and `tibia_l`. Their orientations come from the motion-capture model's tibias by forward kinematics, which also needs the motion capture's knee angles.

**Prediction, written first:**
- it passes for the knee;
- the ankle stays above 10°, because the camera's foot keypoints now pull only the ankle;
- walking is reported separately and is worse.

**Reported** as in part 1, beside the pelvis-plus-thighs results, with the same caveat: the sensors are computed from the motion capture the result is compared with, so this is an upper bound and partly circular.

**Fresh:** no. This is the last planned analysis on LabValidation. The force data, `Dynamics` and EMG are not opened.
