---
type: "test"
title: "One camera plus simulated pelvis and thigh sensors, against the motion capture"
status: "passed"
area: "pipeline"
parent: "[[kin-camera-plus-imu-sim]]"
expected: "With pelvis and thigh sensors under assumed noise, the one-camera MediaPipe route's sagittal hip error at lag 0 is at most 10 degrees and pelvis tilt at most 5 degrees, as means over subjects"
result: "Met (2026-11-16): with simulated pelvis and thigh sensors under assumed noise, the one-camera route's sagittal hip RMSE at lag 0 is 5.9 deg and pelvis tilt 4.5 deg (89 trials, 9 subjects, without walking); an upper bound, since the sensors are computed from the reference"
fresh: "no"
record: "validation/results/kin_camera_plus_imu_sim.json"
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

**Result (2026-11-16): the expected result is met.** One-camera MediaPipe route, pelvis and thigh sensors, assumed
noise, without walking (89 trials, 9 subjects): sagittal hip RMSE **5.9°** (limit 10°) and pelvis tilt **4.5°**
(limit 5°). Without sensors they are 34.5° and 19.2°. All 196 route-trials solved in all five conditions. Figures:
`validation/results/kin_camera_plus_imu_sim.json`; scripts: `validation/runs/kin_camera_plus_imu_sim/`.

**How to read it.** The sensors are computed from the same motion capture the result is compared with, so this is an
upper bound and partly circular. Noise-free, the error on a sensed segment is about 0.7°: the solver simply follows
the sensor. Under the assumed noise the error is about the size of the noise put in. It shows that the fusion
works, and that the camera's markers do not pull the pelvis and thighs away from good sensors at these weights. It
does not show what real sensors achieve: mounting, soft tissue, magnetic disturbance, real drift and
sensor-to-segment calibration on a real body are not in it.

Each cell is RMSE in degrees (bias / spread), a mean over subjects of the subject's mean; hip and knee average right
and left.

One camera, without walking (89 trials, 9 subjects):

| Sensors | Pelvis tilt | Hip, sagittal | Knee, sagittal | Pelvis, frontal | Hip, frontal |
|---|---|---|---|---|---|
| No sensors | 19.2 (+15.8 / 9.7) | 34.5 (-29.4 / 17.2) | 21.2 (-2.6 / 19.2) | 5.3 (-4.0 / 3.0) | 6.2 (-2.2 / 4.7) |
| Pelvis, noise-free | 0.7 (+0.4 / 0.4) | 19.0 (-13.2 / 12.8) | 21.2 (-1.1 / 19.0) | 3.5 (-2.8 / 1.7) | 7.1 (-2.3 / 4.4) |
| Pelvis, assumed noise | 4.5 (+0.0 / 3.1) | 19.3 (-12.9 / 13.3) | 21.3 (-1.1 / 19.0) | 5.6 (-2.7 / 3.6) | 8.9 (-2.1 / 5.9) |
| Pelvis + thighs, noise-free | 0.7 (+0.3 / 0.4) | 0.7 (-0.5 / 0.4) | 14.9 (+10.8 / 8.5) | 3.5 (-2.8 / 1.7) | 0.6 (-0.5 / 0.3) |
| Pelvis + thighs, assumed noise | 4.5 (-0.0 / 3.1) | 5.9 (-0.2 / 4.3) | 15.6 (+10.9 / 9.4) | 5.5 (-2.7 / 3.6) | 7.7 (-0.1 / 5.2) |

One camera with the augmenter, without walking (50 trials, 8 subjects):

| Sensors | Pelvis tilt | Hip, sagittal | Knee, sagittal | Pelvis, frontal | Hip, frontal |
|---|---|---|---|---|---|
| No sensors | 15.8 (+11.2 / 8.4) | 27.9 (-21.2 / 17.3) | 22.5 (-0.1 / 21.0) | 6.3 (-0.3 / 2.2) | 6.1 (-2.6 / 3.9) |
| Pelvis, noise-free | 0.2 (+0.1 / 0.1) | 18.5 (-9.8 / 12.9) | 22.7 (+0.2 / 21.2) | 1.0 (-0.5 / 0.4) | 7.6 (-2.5 / 3.1) |
| Pelvis, assumed noise | 4.1 (-0.3 / 3.0) | 19.2 (-9.8 / 13.4) | 22.7 (+0.1 / 21.2) | 4.2 (-0.5 / 3.2) | 9.8 (-2.4 / 4.8) |
| Pelvis + thighs, noise-free | 0.2 (+0.0 / 0.1) | 0.7 (-0.4 / 0.4) | 14.9 (+9.3 / 9.7) | 1.0 (-0.5 / 0.5) | 0.9 (-0.8 / 0.4) |
| Pelvis + thighs, assumed noise | 4.1 (-0.4 / 3.0) | 5.8 (-0.5 / 4.3) | 15.4 (+8.9 / 10.7) | 4.2 (-0.5 / 3.2) | 7.6 (-1.0 / 5.1) |

Walking, one camera (54 trials, 9 subjects; the augmenter route has only 3 walking trials, in the results file):

| Sensors | Pelvis tilt | Hip, sagittal | Knee, sagittal | Pelvis, frontal | Hip, frontal |
|---|---|---|---|---|---|
| No sensors | 7.3 (-2.6 / 4.5) | 21.9 (+1.4 / 20.6) | 32.8 (+8.3 / 31.2) | 8.7 (-7.6 / 3.8) | 9.5 (-2.7 / 6.5) |
| Pelvis, noise-free | 0.4 (+0.1 / 0.3) | 22.2 (-3.0 / 21.6) | 32.5 (+8.6 / 30.3) | 0.4 (+0.0 / 0.2) | 5.2 (-1.7 / 4.6) |
| Pelvis, assumed noise | 3.8 (-0.0 / 3.0) | 22.6 (-3.0 / 21.8) | 32.5 (+8.5 / 30.4) | 4.1 (-0.5 / 3.0) | 6.9 (-1.7 / 5.7) |
| Pelvis + thighs, noise-free | 0.4 (+0.0 / 0.3) | 2.1 (+0.4 / 2.1) | 44.8 (+16.8 / 41.1) | 0.4 (-0.1 / 0.3) | 0.7 (-0.2 / 0.6) |
| Pelvis + thighs, assumed noise | 3.8 (-0.1 / 3.0) | 5.8 (+0.7 / 4.8) | 45.0 (+17.0 / 41.1) | 4.1 (-0.5 / 3.0) | 6.0 (-0.0 / 4.6) |

- **The prediction holds in part.**
  - It passes, as predicted.
  - Pelvis only: pelvis tilt is fixed (4.5°), and hip flexion falls from 34.5° to 19.3° but stays far from
    10°, so the thigh sensors are needed for the hip.
  - The knee does not just improve least. Without walking it falls from 21.2° to 15.6°. In walking it gets
    worse, 32.8° to 45.0°.
- **The error moves down the leg.** With the thigh fixed by its sensor, the camera's wrong knee and ankle
  keypoints can only be met by bending the knee and ankle. The sagittal ankle error rises from 24.5° to
  43.5° without walking (in the results file). A shank sensor was not part of this test.
- **Frontal angles under the assumed noise** end up near the noise level: the pelvis 5.5° and the hip
  7.7°, no better than without sensors (5.3° and 6.2°). The assumed noise is unfiltered
  and independent per frame, which real sensor fusion would smooth.
- **The baseline** is the script's own no-sensor solve. It reproduces the route's IK, so its figures match the
  round-0 ones over these trials.

