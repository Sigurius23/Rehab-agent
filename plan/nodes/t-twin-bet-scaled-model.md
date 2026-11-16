---
type: "test"
title: "One camera with the personalised body, against the motion capture"
status: "running"
area: "person-model"
parent: "[[twin-bet-scaled-model]]"
expected: "Proposal: if personalisation is what makes one camera good enough, the one-camera route's sagittal hip error at lag 0 falls by at least half and its knee error by at least a third, against the same route with the height-scaled body"
source: "owner 2026-11-16"
updated: "2026-11-16"
---
# One camera with the personalised body, against the motion capture

The expected result above was approved by the owner on 2026-11-16, as written, before the run.

- **Prediction, written first:** it does not. The errors fall by less than 3°, because one camera's hip error is depth ambiguity in the detector, not wrong segment lengths. If that holds, the twin cannot rescue phone-only capture on its own.
- Same trials, lag 0 and evaluation rules as the benchmark; walking reported separately.
- Not fresh: see [[t-kin-backend-markers]].

**Method, written and committed before the run (2026-11-16).** No pipeline code is changed.
- **The stand-in twin** (`validation/runs/kin_twin_bet/make_person.py`): per subject, per-body scale factors that
  make the pipeline's generic model (the Pose2Sim full-body model, the same for all three routes) match the
  segment lengths of the subject's motion-capture-scaled model (`OpenSimData/Mocap/Model`, already on the laptop;
  nothing else is extracted).
  - Segment lengths are distances between body origins (joint centres) in each model's default pose: thigh, shank,
    foot (calcn to toes), upper arm and forearm per side; hip width (femur to femur); trunk (midpoint of the hips to
    midpoint of the shoulders).
  - Each generic body gets one uniform factor, the mocap length over the generic length of its segment: femur and
    patella from the thigh; tibia from the shank; talus, calcn and toes from the foot; humerus from the upper arm;
    ulna, radius and hand from the forearm; pelvis and sacrum from the hip width; the lumbar bodies, torso, head and
    abdomen from the trunk. The factors are recorded per subject.
- **How the body is fixed:** through the pipeline's own person model. `rehabtwin person init` and `person build`
  (from the subject's round-0 one-camera session) make a valid person folder for the same generic model. Then the
  adapter replaces only `model.scale_set` in its `person.json` with the factors above. `rehabtwin process --person`
  applies exactly those factors in place of scaling a new body. For one camera it also resizes the recording
  uniformly to the person's size, which changes no joint angle (the pipeline's own behaviour with a person model).
- **Routes:**
  - one-camera MediaPipe, without and with the augmenter, from round 0's `mono_seq.npz` and `mono_aug_seq.npz`
    (made from the round-0 MediaPipe dumps), with round 0's settings plus `--person`;
  - HSMR, from round 2's `skel_seq.npz` (stored frames), with `--config skel105_pose2sim --person`. HSMR is
    included because its `process` step takes a person model without any code change. HSMR itself is not rerun.
- **Comparison:** at lag 0 with the motion-capture IK, with the benchmark's evaluation rules and readings
  (`bench_aggregate.py`), walking reported separately. The baseline for each route is its own earlier run with the
  pipeline's usual body: round 0 for MediaPipe, round 2 for HSMR.
- **The figure judged:** per route, over the trials evaluated in both runs, without walking and without
  subject 2's `squats1`: the sagittal hip and knee RMSE (right and left averaged), as a mean over subjects of the
  subject's mean. The expected result needs the hip to fall by at least half and the knee by at least a third. It
  is judged on the one-camera MediaPipe route without the augmenter; the other two routes are reported beside it.
- **Tested once before this commit:** subject 2's `squats1` (the seen trial), without a reference: the MediaPipe
  route and HSMR both ran with the twin's factors (thigh 1.22, shank 1.15–1.17, trunk 1.00 for this 1.96 m subject).
  No error was computed.

