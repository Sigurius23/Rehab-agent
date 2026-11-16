---
type: "test"
title: "Our back end on OpenCap's markers, against the motion capture"
status: "passed"
area: "pipeline"
parent: "[[kin-backend-markers]]"
expected: "Proposal: over the trials and lag rule of the zero-lag positive control, our back end's mean absolute error over the 18 angles is within 1.5 degrees of OpenCap's own IK on the same markers (4.57 degrees)"
result: "Met (2026-11-16): 5.11 deg over the 18 angles, +0.54 from OpenCap's own IK on the same 159 trials (4.57); all 160 trials evaluated"
fresh: "no"
record: "validation/results/kin_backend_markers.json"
source: "owner 2026-11-16"
updated: "2026-11-16"
---
# Our back end on OpenCap's markers, against the motion capture

The expected result above was approved by the owner on 2026-11-16, as written, before the run.

- **Prediction, written first:** within 1.5° overall, but with constant biases at the pelvis and hip larger than OpenCap's, from the two models' different frame definitions (`docs/validation-results.md` section 4, point 4).
- Report RMSE, mean absolute error, bias and spread per angle, beside OpenCap's own figures for the same trials.
- Not fresh: LabValidation has been used for two fix rounds and four post-hoc analyses.

**Method, written and committed before the run (2026-11-16).** No pipeline code is changed.
- **Input:** from `LabValidation_withoutVideos.zip`, only `MarkerData/Video/HRNet/2-cameras/*.trc` (170 files: 160
  trials and 10 static), extracted outside the repository with a sha256 manifest. Each file also holds the motion
  capture's markers and `_offsetRemoved` copies that were shifted using the motion capture; neither is used.
- **Marker mapping:** the 43 `*_study` markers, which are OpenCap's augmenter output. They carry the same names as
  the pipeline's augmenter route (`configs/mediapipe_lstm_pose2sim.json`, marker set `Markers_LSTM.xml` with the
  pipeline's marker corrections), so no renaming is needed. Millimetres become metres; the frame is `yup_world`.
- **Adapter:** `validation/runs/kin_backend_markers/trc_to_seq.py` writes a `MarkerSequence` at the file's own rate
  (100 Hz), with frame k at k/100 s on the file's clock.
- **Entry point:** `rehabtwin process <seq> <out> --config mediapipe_lstm_pose2sim --exercise squat --mass-kg <m>
  --height-m <h>`, with mass and height from the subject's `sessionMetadata.yaml`. Scaling is the pipeline's own
  for this route: marker-pair measurements from the trial's static frames, with the given height and mass. Model:
  the Pose2Sim full-body model; IK with the route's weights. The comparison uses `--reference` (the
  motion-capture IK and its model), `--reference-grade marker-mocap` and `--max-lag-s 0`.
- **Rules, as in the zero-lag positive control** ([[t-kin-opencap-control-all]]):
  - lag 0;
  - a trial is evaluated when the route produced its IK over enough of the trial (coverage not short) and all 18
    angles exist;
  - the mean absolute error over the 18 angles is taken per trial, then averaged over each subject's evaluated
    trials, then over the subjects;
  - subject 2's `squats1` is left out and reported apart.
- **The 18 angles in this model:** the same names as the reference, except the lumbar angles, which are the
  model's totals over its lumbar levels (`lumbar_total.*`), as the pipeline's comparison maps them.
- **Beside it:** OpenCap's own IK for the same configuration, from the zero-lag control's per-trial figures, over
  all its trials (4.57°) and over exactly the trials evaluated here.
- **Tested once before this commit:** subject 2's `squats1` (the seen trial), without a reference. It solved as one
  segment with five repetitions; no error was computed.

**Result (2026-11-16): the expected result is met.** On OpenCap's markers, this pipeline's back end gives a mean
absolute error of **5.11°** over the 18 angles. OpenCap's own IK on the same 159 trials gives 4.57°, so
the difference is +0.54° (allowed ±1.5°). Figures: `validation/results/kin_backend_markers.json`; scripts:
`validation/runs/kin_backend_markers/`.
- **Counts:** 160 run and 160 evaluated, each solved as one segment; 159 in the average, with subject 2's `squats1`
  apart (5.74° against OpenCap's 4.65°).
- **One fix to the adapter during the run:** 12 files start after 0 s, and the adapter's check for a start at 0
  stopped them. It now numbers frames from the file's own first time, which is what the method says (the file's
  clock). The other 148 trials are unaffected, and no pipeline code changed.
- **Per movement, ours against OpenCap's:** walking 5.07° against 4.13°, squat 4.15° against 4.10°, sit-to-stand 5.21° against 4.67°, drop jump 5.43° against 5.14°.
- **Per subject, ours:** 2: 6.0°, 3: 5.2°, 4: 4.5°, 5: 4.7°, 6: 5.2°, 7: 5.1°, 8: 4.8°, 9: 5.3°, 10: 4.9°, 11: 5.3°.

| Angle | Ours: MAE | RMSE | Bias | Spread | OpenCap's IK: MAE | Bias | Spread |
|---|---|---|---|---|---|---|---|
| pelvis_tilt | 6.02 | 6.8 | +2.9 | 3.6 | 6.21 | -4.6 | 3.3 |
| pelvis_list | 2.61 | 3.0 | +0.5 | 1.8 | 2.14 | -0.4 | 1.7 |
| pelvis_rotation | 2.86 | 3.4 | -0.8 | 2.5 | 2.96 | -1.2 | 2.4 |
| hip_flexion_r | 7.07 | 8.0 | -4.2 | 4.4 | 5.70 | +3.3 | 3.7 |
| hip_adduction_r | 2.84 | 3.3 | -0.1 | 2.4 | 2.66 | +0.6 | 2.4 |
| hip_rotation_r | 4.42 | 5.1 | +1.9 | 3.3 | 4.01 | +2.1 | 3.2 |
| knee_angle_r | 5.59 | 6.3 | +0.7 | 4.3 | 3.88 | -0.7 | 3.7 |
| ankle_angle_r | 5.49 | 6.7 | +3.0 | 5.1 | 5.46 | +3.3 | 5.1 |
| subtalar_angle_r | 6.31 | 7.3 | +1.8 | 4.6 | 5.43 | +0.2 | 4.6 |
| hip_flexion_l | 7.33 | 8.3 | -5.1 | 4.7 | 5.84 | +3.4 | 4.1 |
| hip_adduction_l | 3.27 | 3.8 | -2.3 | 2.3 | 2.66 | -0.9 | 2.3 |
| hip_rotation_l | 4.06 | 4.8 | -1.0 | 3.4 | 4.10 | +1.3 | 3.5 |
| knee_angle_l | 5.14 | 5.9 | +0.1 | 4.4 | 3.98 | -0.2 | 3.9 |
| ankle_angle_l | 6.84 | 8.0 | +5.9 | 4.8 | 6.12 | +4.9 | 4.7 |
| subtalar_angle_l | 5.08 | 6.0 | +0.4 | 4.4 | 5.73 | -2.9 | 4.8 |
| lumbar_extension | 9.27 | 10.5 | -6.5 | 5.7 | 7.88 | +5.3 | 4.5 |
| lumbar_bending | 3.30 | 3.9 | +0.9 | 3.0 | 3.21 | +0.7 | 2.7 |
| lumbar_rotation | 4.44 | 5.4 | +2.6 | 3.8 | 4.27 | +2.1 | 3.6 |

Each figure is a mean over subjects of the subject's mean over trials. Spread is the SD of the difference.
- **The prediction holds in part.** Overall the two are within 1.5°. The constant bias is larger than OpenCap's at
  the hip (flexion −4.2° and −5.1°, against +3.3° and +3.4°) and at the lumbar spine (−6.5° against +5.3°), but
  smaller at the pelvis (tilt +2.9° against −4.6°). The two back ends' biases have opposite signs at the pelvis,
  hip and lumbar spine.
- **Where ours is worse:** hip flexion (7.1–7.3° against 5.7–5.8°), the knee (5.1–5.6° against 3.9–4.0°) and
  lumbar extension (9.3° against 7.9°). The spreads are close, so the gap is mostly bias.
- **What it means:** the back end (model, scaling and IK) is not what puts the MediaPipe routes at 11–36°
  ([[t-kin-labvalidation]]). Given good markers it is within about half a degree of OpenCap's own IK, so the
  error comes from the front end: the keypoints, the triangulation and the augmenter's input.

