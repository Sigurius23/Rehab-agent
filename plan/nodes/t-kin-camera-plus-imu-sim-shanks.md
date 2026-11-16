---
type: "test"
title: "One camera plus simulated pelvis, thigh and shank sensors, against the motion capture"
status: "failed"
area: "pipeline"
parent: "[[kin-camera-plus-imu-sim]]"
expected: "Under the assumed noise, with pelvis, thigh and shank sensors, the one-camera MediaPipe route's sagittal knee error at lag 0 is at most 8 degrees and its ankle at most 10 degrees, as means over subjects; the hip and pelvis tilt stay within part 1's limits (10 and 5 degrees)"
result: "Not met (2026-11-17): with simulated pelvis, thigh and shank sensors under assumed noise the knee is 5.2 deg, the hip 5.8 and pelvis tilt 4.5, all within their limits, but the ankle is 56.6 deg against 10 (89 trials, 9 subjects, without walking)"
fresh: "no"
record: "validation/results/kin_camera_plus_imu_sim_shanks.json"
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

**Result (2026-11-17): the expected result is not met, because of the ankle.** One-camera MediaPipe route, pelvis,
thigh and shank sensors, assumed noise, without walking (89 trials, 9 subjects):
- knee **5.2°** (limit 8°), hip 5.8° (limit 10°) and pelvis tilt 4.5° (limit 5°) are within their limits;
- the ankle is **56.6°** (limit 10°).

All 196 route-trials solved. Figures: `validation/results/kin_camera_plus_imu_sim_shanks.json`; scripts:
`validation/runs/kin_camera_plus_imu_sim/` (`fuse_trial_shanks.py`).

**The same caveat as part 1.** The sensors are computed from the motion capture the result is compared with, so this
is an upper bound and partly circular. On a sensed segment the error is about the noise put in. It does not show
what real sensors achieve.

**Same draws as part 1.** The pelvis and thigh sensors use the same random draws; on the check trial the
pelvis-plus-thighs solve reproduces part 1's file to 0.0°. The shank sensors' draws come from a second generator.

Each cell is RMSE in degrees (bias / spread), a mean over subjects of the subject's mean; hip, knee and ankle average
right and left.

One camera, without walking (89 trials, 9 subjects):

| Sensors | Pelvis tilt | Hip, sagittal | Knee, sagittal | Ankle, sagittal | Pelvis, frontal | Hip, frontal |
|---|---|---|---|---|---|---|
| No sensors | 19.2 (+15.8 / 9.7) | 34.5 (-29.4 / 17.2) | 21.2 (-2.6 / 19.2) | 24.5 (-9.8 / 18.2) | 5.3 (-4.0 / 3.0) | 6.2 (-2.2 / 4.7) |
| Pelvis + thighs, noise-free | 0.7 (+0.3 / 0.4) | 0.7 (-0.5 / 0.4) | 14.9 (+10.8 / 8.5) | 43.3 (-25.6 / 30.6) | 3.5 (-2.8 / 1.7) | 0.6 (-0.5 / 0.3) |
| Pelvis + thighs, assumed noise | 4.5 (-0.0 / 3.1) | 5.9 (-0.2 / 4.3) | 15.6 (+10.9 / 9.4) | 43.5 (-23.9 / 31.4) | 5.5 (-2.7 / 3.6) | 7.7 (-0.1 / 5.2) |
| Pelvis + thighs + shanks, noise-free | 0.7 (+0.3 / 0.4) | 1.2 (-1.0 / 0.6) | 1.0 (-0.3 / 0.8) | 56.9 (-46.8 / 28.4) | 3.6 (-2.9 / 1.6) | 0.5 (-0.4 / 0.2) |
| Pelvis + thighs + shanks, assumed noise | 4.5 (-0.1 / 3.0) | 5.8 (-0.5 / 4.2) | 5.2 (-0.3 / 4.1) | 56.6 (-44.8 / 29.9) | 5.5 (-2.8 / 3.5) | 6.5 (-0.2 / 4.6) |

One camera with the augmenter, without walking (50 trials, 8 subjects):

| Sensors | Pelvis tilt | Hip, sagittal | Knee, sagittal | Ankle, sagittal | Pelvis, frontal | Hip, frontal |
|---|---|---|---|---|---|---|
| No sensors | 15.8 (+11.2 / 8.4) | 27.9 (-21.2 / 17.3) | 22.5 (-0.1 / 21.0) | 26.2 (-14.7 / 18.8) | 6.3 (-0.3 / 2.2) | 6.1 (-2.6 / 3.9) |
| Pelvis + thighs, noise-free | 0.2 (+0.0 / 0.1) | 0.7 (-0.4 / 0.4) | 14.9 (+9.3 / 9.7) | 29.2 (-18.7 / 19.3) | 1.0 (-0.5 / 0.5) | 0.9 (-0.8 / 0.4) |
| Pelvis + thighs, assumed noise | 4.1 (-0.4 / 3.0) | 5.8 (-0.5 / 4.3) | 15.4 (+8.9 / 10.7) | 29.1 (-18.2 / 19.6) | 4.2 (-0.5 / 3.2) | 7.6 (-1.0 / 5.1) |
| Pelvis + thighs + shanks, noise-free | 0.4 (-0.1 / 0.2) | 1.2 (-0.8 / 0.7) | 1.1 (-0.0 / 1.0) | 36.7 (-31.9 / 15.6) | 1.1 (-0.4 / 0.5) | 0.7 (-0.6 / 0.3) |
| Pelvis + thighs + shanks, assumed noise | 4.1 (-0.5 / 3.0) | 5.6 (-0.6 / 4.2) | 5.4 (-0.3 / 4.1) | 36.9 (-31.5 / 16.7) | 4.1 (-0.4 / 3.1) | 6.4 (-0.5 / 4.5) |

Walking, one camera (54 trials, 9 subjects; the augmenter route's 3 walking trials are in the results file):

| Sensors | Pelvis tilt | Hip, sagittal | Knee, sagittal | Ankle, sagittal | Pelvis, frontal | Hip, frontal |
|---|---|---|---|---|---|---|
| No sensors | 7.3 (-2.6 / 4.5) | 21.9 (+1.4 / 20.6) | 32.8 (+8.3 / 31.2) | 25.2 (-7.8 / 17.4) | 8.7 (-7.6 / 3.8) | 9.5 (-2.7 / 6.5) |
| Pelvis + thighs, noise-free | 0.4 (+0.0 / 0.3) | 2.1 (+0.4 / 2.1) | 44.8 (+16.8 / 41.1) | 32.0 (-9.6 / 28.0) | 0.4 (-0.1 / 0.3) | 0.7 (-0.2 / 0.6) |
| Pelvis + thighs, assumed noise | 3.8 (-0.1 / 3.0) | 5.8 (+0.7 / 4.8) | 45.0 (+17.0 / 41.1) | 32.0 (-8.9 / 28.2) | 4.1 (-0.5 / 3.0) | 6.0 (-0.0 / 4.6) |
| Pelvis + thighs + shanks, noise-free | 0.4 (+0.0 / 0.4) | 5.0 (-0.3 / 4.9) | 1.0 (+0.2 / 1.0) | 51.9 (-11.0 / 48.9) | 0.7 (-0.2 / 0.5) | 1.0 (-0.0 / 0.9) |
| Pelvis + thighs + shanks, assumed noise | 3.8 (-0.1 / 3.0) | 7.2 (+0.3 / 6.4) | 5.9 (+1.3 / 4.2) | 51.9 (-10.5 / 49.1) | 4.1 (-0.7 / 2.9) | 5.1 (+0.1 / 3.9) |

- **The prediction:**
  - **It passes for the knee: holds.** 15.6° with pelvis and thighs, 5.2° with the shanks added.
  - **The ankle stays above 10°: holds, and by far more than "stays".** It rises from 24.5° without sensors to
    43.5° with pelvis and thighs and 56.6° with the shanks, with a bias of -45°. With the shank fixed, the
    camera's wrong foot keypoints can only be met by turning the ankle.
  - **Walking is worse: holds in part.** In walking the knee is 5.9° and the hip 7.2°, slightly worse than without
    walking; the ankle is 51.9°, not worse. With shank sensors, walking's knee error falls from 45.0° (pelvis and
    thighs) to 5.9°.
- **What it means:** every segment given a sensor is fixed to about the noise level, and the camera's error moves to
  the next joint down. With sensors on five segments, the camera's markers add nothing to the sensed joints and
  make the ankle worse than no sensors at all. Either the feet need sensors too, or the foot keypoints need much
  less weight once the shank is sensed. Neither is tested here.

**This is the last planned analysis on LabValidation.**

**Post hoc (owner, 2026-11-17), changing no recorded figure: the ankle's bias and spread per subject.** Nothing was
rerun. The figures come from the part-2 aggregation's own per-trial output on the lab laptop; the committed results
file keeps only each trial's RMSE. Sagittal ankle, right and left averaged, pelvis + thighs + shanks; each figure is
the subject's mean over trials, in degrees. Figures: `validation/results/kin_camera_plus_imu_sim_shanks_posthoc_ankle.json`.

One camera, without walking:

| Subject | Trials | Noise-free: bias | Spread | Assumed noise: bias | Spread | Bias over the trials (noise) | No sensors: bias | Spread |
|---|---|---|---|---|---|---|---|---|
| 2 | 9 | -25.1 | 26.7 | -25.3 | 28.2 | -47.1 to -11.8 | -3.0 | 17.5 |
| 3 | 10 | -51.1 | 32.2 | -49.7 | 33.8 | -65.1 to -39.8 | -5.3 | 21.4 |
| 4 | 10 | -47.5 | 29.4 | -44.3 | 31.3 | -56.0 to -25.3 | -9.6 | 20.0 |
| 5 | 10 | -57.0 | 27.9 | -56.2 | 28.9 | -65.2 to -49.8 | -19.3 | 15.3 |
| 7 | 10 | -50.1 | 24.2 | -47.9 | 26.9 | -61.7 to -35.9 | -6.4 | 17.4 |
| 8 | 10 | -49.2 | 29.7 | -43.9 | 32.4 | -56.8 to -21.8 | -8.1 | 18.6 |
| 9 | 10 | -53.9 | 28.2 | -54.2 | 27.8 | -60.0 to -44.7 | -14.5 | 21.2 |
| 10 | 10 | -45.6 | 28.2 | -43.2 | 31.0 | -61.5 to -23.0 | -13.4 | 14.0 |
| 11 | 10 | -41.4 | 28.8 | -38.7 | 29.0 | -56.8 to -18.0 | -8.9 | 18.6 |

One camera, walking:

| Subject | Trials | Noise-free: bias | Spread | Assumed noise: bias | Spread | Bias over the trials (noise) | No sensors: bias | Spread |
|---|---|---|---|---|---|---|---|---|
| 2 | 6 | -17.1 | 48.4 | -16.2 | 49.1 | -22.8 to -12.8 | -12.5 | 19.8 |
| 3 | 6 | -19.3 | 52.4 | -20.4 | 52.0 | -23.9 to -16.5 | -5.2 | 15.6 |
| 4 | 6 | +0.8 | 48.4 | +2.1 | 48.8 | -11.3 to +6.7 | -2.5 | 18.8 |
| 5 | 6 | -18.2 | 49.5 | -17.8 | 49.4 | -21.4 to -16.5 | -9.7 | 17.3 |
| 7 | 6 | -11.2 | 44.9 | -9.7 | 45.5 | -21.4 to -1.2 | -8.9 | 19.3 |
| 8 | 6 | -15.0 | 46.5 | -13.9 | 47.0 | -25.7 to -2.1 | -12.1 | 17.6 |
| 9 | 6 | -4.4 | 47.8 | -4.2 | 47.8 | -18.5 to +7.6 | -10.1 | 14.8 |
| 10 | 6 | -4.7 | 51.8 | -4.8 | 51.9 | -15.9 to +2.0 | -5.0 | 17.9 |
| 11 | 6 | -10.1 | 50.1 | -9.7 | 50.2 | -15.9 to +0.2 | -4.8 | 16.1 |

- **Without walking it is both: a large offset and a large variable part.** The bias has the same sign in all nine
  subjects (−25° to −57°, and −39° or more in eight of them), and the spread is 27–34° in every subject. The bias
  is about 1.5 to 2 times the spread, except in subject 2, where they are equal. So removing a constant offset
  would not be enough: about 30° of spread would stay.
- **The offset is not constant within a subject either:** over a subject's trials the bias ranges by 15–35°.
- **In walking it is mostly variable:** the spread is 45–52° in every subject, against a bias of +2° to −20°.
- **The noise makes almost no difference:** the noise-free and assumed-noise figures agree within about 5°, so
  this error comes from the camera's foot keypoints, not from the sensors' noise.
- **Without sensors** the ankle's bias is −3° to −19° and its spread 14–21°: the shank sensors raise both.
- The augmenter route shows the same pattern with smaller numbers (bias −24° to −41°, spread 11–21°, without
  walking; in the results file).

