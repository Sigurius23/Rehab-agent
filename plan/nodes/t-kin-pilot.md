---
type: "test"
title: "Pilot: one trial's video kinematics against its motion capture"
status: "running"
area: "pipeline"
parent: "[[kin-labvalidation]]"
expected: "Proposal: on subject 2's squats1, the comparison runs end to end for all four routes, and the five-camera route with the augmenter has an error against the motion capture within 2 degrees of its error against OpenCap at every joint"
fresh: "no"
updated: "2026-11-10"
---
# Pilot: one trial's video kinematics against its motion capture

The expected result above was proposed on 2026-11-09 and approved by the owner as written on 2026-11-10, before the pilot ran.

The routes are those of `examples/opencap_agreement.sh`: five cameras or one, with and without the augmenter. The
reference changes from OpenCap's markerless result to the trial's marker motion capture, read from the laptop's
LabValidation copy (`--reference-grade marker-mocap`).

The pilot checks two things before the full run:
- that the comparison works against a marker reference: alignment, coordinate names, a model scaled from markers;
- whether this trial's markerless reference was close to motion capture. If it misses by more than 2° somewhere,
  the agreement figures in `docs/validation-results.md` section 4 overstate the accuracy there.

Not fresh: the pipeline was developed on these videos.

**Paused at the alignment check, 2026-11-10. No error has been computed.** On the lab laptop, outside the repository
(`~/rehab-agent-data/kinematics/pilot`, with `provenance.json` and the scripts):
- **Inputs:** the fixture is pinned to opencap-test-data commit 63546b7, with every file's sha256 recorded; Pose2Sim
  c6db0ca; MediaPipe 1.2.2 with `pose_landmarker_heavy.task`; rehabtwin at this branch, with OpenSim 4.6.
- **End to end:** all four routes ran, processed first without a reference. The one-camera route with the
  augmenter solved in five pieces; the longest covers 20 % of the trial.
- **Subject:** the fixture's metadata gives subject2, 78.2 kg and 1.96 m, the same as the LabValidation copy.
- **Alignment criterion,** fixed before the check: one clear peak means the best lag lies at least 0.2 s inside
  the ±4 s window, and every other local minimum more than 0.3 s away has at least twice the best's objective
  (the pipeline's own lag objective, `validation.best_lag`).

| Route, against motion capture | Best lag | Next minimum | Its ratio to the best | Clear peak |
|---|---|---|---|---|
| Five cameras | 0.483 s | −1.117 s | 1.12 | no |
| Five cameras, augmenter | 0.483 s | −1.117 s | 3.39 | yes |
| One camera | 1.317 s | 2.883 s | 1.66 | no |
| One camera, augmenter | 1.467 s | −0.017 s | 5.26 | yes |

Two routes have no clear peak, so the pilot stopped before any error was computed, as the brief says. Their
second minimum lies about one squat repetition from the best one. Added after the check failed, and alignment
only: OpenCap's own result against the motion capture has a clear peak at 0.417 s (ratio 2.94). Each route's best
lag equals its lag against OpenCap plus that 0.417 s, within 0.07 s. The owner decides how to go on.
