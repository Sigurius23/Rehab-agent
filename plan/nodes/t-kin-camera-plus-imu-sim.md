---
type: "test"
title: "One camera plus simulated pelvis and thigh sensors, against the motion capture"
status: "planned"
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
