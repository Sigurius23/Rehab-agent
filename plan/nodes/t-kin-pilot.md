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
lag equals its lag against OpenCap plus that 0.417 s, within 0.07 s.

**Alignment check (2026-11-10, before any error was computed).** The criterion fixed beforehand was met by the two
augmenter routes and missed by the two without it (five cameras 1.12, one camera 1.66). The competing minimum is one
squat repetition away. Independent evidence, alignment only: OpenCap's result against the motion capture has a clear
peak at 0.417 s (2.94), and every route's lag against the motion capture equals its lag against OpenCap plus
0.417 s, within 0.07 s.

**Decision (owner, 2026-11-10): option A.** The comparison runs with the pipeline's lag search unchanged (±4 s).
The two routes are reported as "no clear peak; the lag found agrees with the independent offset". The expected
result is judged on the five-camera route with the augmenter, whose peaks are clear against both references (3.39
and 13.7).

Recorded with it:
- The lag search minimises the error it reports, so every RMSE here is the route's best case.
- The two one-camera routes share one timeline, but their lags differ by 0.15 s (1.317 and 1.467 s). The augmenter
  route's lag comes from pieces covering at most 20 % of the trial, so its ratio does not make it the more reliable
  one.
- **Sensitivity analysis:** both one-camera routes are also compared at one shared lag: the five-camera-with-
  augmenter lag (0.483 s) plus Cam2's offset from the multi-view video sync. It is reported beside the primary
  result. It changes no pipeline code: a copy of the reference outside the repository with its time column shifted,
  and `--max-lag-s 0`.
- **Reading of the expected result:** per joint × plane cell present in both reports, |RMSE against motion capture −
  RMSE against OpenCap| ≤ 2.0°. The per-coordinate differences are listed beside it, and any coordinate over 2.0°
  inside a passing cell is named.
- **"Runs end to end"** means each route produces its validation report. A route whose gates are not-tested on
  coverage is reported as run but not evaluated. Both counts are given.
