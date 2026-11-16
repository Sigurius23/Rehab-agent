---
type: "test"
title: "One camera plus simulated pelvis and thigh sensors, against the motion capture"
status: "running"
area: "pipeline"
parent: "[[kin-camera-plus-imu-sim]]"
expected: "With pelvis and thigh sensors under assumed noise, the one-camera MediaPipe route's sagittal hip error at lag 0 is at most 10 degrees and pelvis tilt at most 5 degrees, as means over subjects"
fresh: "no"
source: "owner 2026-11-16"
updated: "2026-11-16"
---
# One camera plus simulated pelvis and thigh sensors, against the motion capture

The expected result above was approved by the owner on 2026-11-16, before anything was computed.

**Method:**
- **Virtual sensors** on the pelvis and both femurs. Their orientations come from each trial's motion-capture IK, on the subject's motion-capture-scaled model, by forward kinematics.
- **Calibration as OpenSense does it:** sensor-to-segment offsets are taken from the trial's first frame, then applied to the pipeline's own model.
- **Two noise conditions:**
  - noise-free;
  - assumed noise: 3° RMS random per axis, plus a heading drift growing linearly to 10° over the trial. Both are assumed, not measured.
- **Two sensor sets:** pelvis only, and pelvis plus both thighs.
- **Fusion:** one IK solving markers and orientations together, using OpenSim's `InverseKinematicsSolver` with a `MarkersReference` and an `OrientationsReference`. The markers are the one-camera MediaPipe route's own IK targets (round 0, with and without the augmenter). Body: the height-scaled body, as in the benchmark.
- **Weights:** orientation weight 1 and the pipeline's own marker weights, fixed before running and not tuned.
- **Code:** a script under `validation/runs/`. No pipeline code is changed.
- **Comparison:** lag 0, the benchmark's trials and evaluation rules, walking reported separately, against the same route without sensors.

**Prediction, written first:** it passes. The sensors fix the pelvis and hip directly. The knee improves least, since there is no shank sensor, and the pelvis-only set fixes pelvis tilt but not hip flexion.

**Fresh:** no; LabValidation has been used throughout.

**Reported,** per route, sensor set and noise condition: RMSE, bias and spread for pelvis tilt, hip and knee sagittal, and the frontal pelvis and hip, beside the no-sensor baseline. The force data, `Dynamics` and EMG are not opened.

**Details fixed before the run (2026-11-16),** where the method above leaves a choice. Script:
`validation/runs/kin_camera_plus_imu_sim/fuse_trial.py`. No pipeline code is changed.
- **Inputs per trial:** the route's round-0 scaled model, its `markers_dynamic.trc` and the marker weights and time
  range of its own IK setup (its longest solved segment). Constraint weight and accuracy are the route's.
- **Sensor readings:** the body's orientation in ground from the motion-capture IK (pelvis and hip coordinates set
  on the subject's motion-capture-scaled model), interpolated to the route's own frame times, so lag 0. Each
  sensor has a fixed random mounting rotation.
- **Heading:** the sensors' world is the motion capture's ground, and the route's ground has its own heading. As
  OpenSense's base-sensor heading correction does, all readings are turned about the vertical so that the
  pelvis's forward axis at the first frame matches the route's own no-sensor IK at that frame.
- **Calibration:** offset = (the body's orientation at the first frame, motion-capture model)ᵀ × (the sensor's
  reading at the first frame). In the noisy condition the first frame's noise is therefore part of the offset. The
  offset is put on the pipeline model's body of the same name (`pelvis`, `femur_r`, `femur_l`) as a `<body>_imu`
  frame.
- **Assumed noise:** per frame and axis, independent Gaussian rotations of 3° RMS, plus a heading drift about the
  vertical growing linearly from 0 to 10° over the solved time range, its sign drawn per sensor. It is seeded by
  subject, trial and route, and is not filtered.
- **Baseline:** the same script without sensors. On the test trial it reproduces the route's own `ik.mot` to
  0.000°.
- **Evaluation:** the trials evaluated for that route in round 0; `validation.compare` at lag 0 against the
  motion-capture IK; RMSE, bias and spread per coordinate, as means over subjects of the subject's mean; hip and
  knee average right and left; subject 2's `squats1` left out.
- **The figure judged:** the one-camera MediaPipe route without the augmenter, pelvis and thigh sensors, assumed
  noise, without walking: sagittal hip RMSE at most 10° and pelvis tilt RMSE at most 5°. Walking, and all
  movements together, are reported beside it.
- **Tested once before this commit:** subject 2's `squats1` (the seen trial): all five conditions solved; no error
  was computed.

