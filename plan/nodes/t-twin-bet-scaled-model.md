---
type: "test"
title: "One camera with the personalised body, against the motion capture"
status: "failed"
area: "person-model"
parent: "[[twin-bet-scaled-model]]"
expected: "Proposal: if personalisation is what makes one camera good enough, the one-camera route's sagittal hip error at lag 0 falls by at least half and its knee error by at least a third, against the same route with the height-scaled body"
result: "Not met (2026-11-16): with the mocap-scaled body the one-camera route's sagittal hip error at lag 0 rises +8 % and its knee error +10 % (89 trials, 9 subjects); HSMR and the augmenter route change by under 1.3 deg"
fresh: "no"
record: "validation/results/kin_twin_bet_scaled_model.json"
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

**Result (2026-11-16): the expected result is not met. A personalised body does not make one camera good enough.**
With each subject's body scaled to their motion-capture model's segment lengths, the one-camera MediaPipe route's
sagittal hip error at lag 0 changes by +8 % and its knee error by +10 %; the expected result needed −50 % and
−33 %. Figures: `validation/results/kin_twin_bet_scaled_model.json`; scripts: `validation/runs/kin_twin_bet/`.
- **Counts:** all 144 trials with video ran on all three routes. The same trials are evaluated as before: 143
  for MediaPipe and HSMR, and 53 with the augmenter, which is refused or short on the same trials as before.
- **The twins differ from the usual bodies.** The thigh's scale factor against the generic model is, per subject,
  2: 1.22, 3: 1.02, 4: 0.98, 5: 1.10, 7: 1.00, 8: 0.93, 9: 1.06, 10: 0.95, 11: 1.07. The usual one-camera bodies were not metric at all: subject 2's round-0 body had a thigh factor of 1.02
  and feet at 0.49, because one camera's size is a guess.

Without walking, sagittal RMSE at lag 0 in degrees, usual body → twin (change):

| Route | Trials | Hip | Knee | Ankle | Pelvis tilt | Lumbar flexion |
|---|---|---|---|---|---|---|
| One camera (MediaPipe) | 89 | 34.5 → 37.1 (+2.7) | 21.2 → 23.3 (+2.1) | 24.5 → 33.2 (+8.7) | 19.2 → 17.4 (-1.8) | 27.0 → 24.6 (-2.4) |
| One camera, augmenter | 50 | 27.9 → 29.2 (+1.2) | 22.5 → 22.7 (+0.2) | 26.2 → 26.7 (+0.5) | 15.8 → 15.8 (-0.0) | 18.0 → 18.6 (+0.6) |
| HSMR | 89 | 20.4 → 20.4 (-0.0) | 20.2 → 20.3 (+0.1) | 15.8 → 15.7 (-0.1) | 8.9 → 8.6 (-0.3) | 11.0 → 12.7 (+1.7) |

Walking, separately:

| Route | Trials | Hip | Knee | Ankle | Pelvis tilt | Lumbar flexion |
|---|---|---|---|---|---|---|
| One camera (MediaPipe) | 54 | 21.9 → 22.4 (+0.6) | 32.8 → 31.4 (-1.3) | 25.3 → 32.1 (+6.9) | 7.4 → 9.8 (+2.5) | 14.3 → 8.7 (-5.6) |
| One camera, augmenter | 3 | 21.8 → 21.2 (-0.6) | 32.3 → 31.8 (-0.5) | 18.6 → 19.1 (+0.5) | 8.0 → 6.6 (-1.4) | 5.9 → 9.3 (+3.4) |
| HSMR | 54 | 19.9 → 20.2 (+0.2) | 41.1 → 40.6 (-0.6) | 12.0 → 11.5 (-0.5) | 3.9 → 6.7 (+2.8) | 9.9 → 15.9 (+6.0) |

Each figure is a mean over subjects of the subject's mean, over the trials evaluated in both runs, with subject 2's
`squats1` left out; hip, knee and ankle average right and left.
- **The prediction holds:** the hip and knee errors do not fall. They move by +2.7° and +2.1° on the judged
  route, and by at most 1.3° on HSMR and on the augmenter route. The lag-search best case moves the same way
  (in the results file), so timing does not hide a gain.
- **Mixed effects elsewhere on the plain MediaPipe route:** pelvis tilt and lumbar flexion fall by about 2°, and the
  ankle rises by 8.7°. With correct segment lengths, IK can no longer absorb keypoint error in the bone lengths.
- **What it means:** one camera's hip and knee error does not come from wrong segment lengths, so a finished
  twin's bones cannot rescue phone-only capture on their own. What the twin could still add (a pose prior, the
  person's own motion ranges, or a fused sensor) is not tested here.

