---
type: "test"
title: "Our back end on OpenCap's markers, against the motion capture"
status: "running"
area: "pipeline"
parent: "[[kin-backend-markers]]"
expected: "Proposal: over the trials and lag rule of the zero-lag positive control, our back end's mean absolute error over the 18 angles is within 1.5 degrees of OpenCap's own IK on the same markers (4.57 degrees)"
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

