---
type: "test"
title: "Pilot: one trial's video kinematics against its motion capture"
status: "failed"
area: "pipeline"
parent: "[[kin-labvalidation]]"
expected: "Proposal: on subject 2's squats1, the comparison runs end to end for all four routes, and the five-camera route with the augmenter has an error against the motion capture within 2 degrees of its error against OpenCap at every joint"
result: "Not met (2026-11-10): all four routes ran end to end (4 run, 3 evaluated); for five cameras with the augmenter, 26 of 36 joint x plane cells differ by more than 2 deg between the errors against motion capture and against OpenCap (20 larger against motion capture, 6 smaller)"
fresh: "no"
record: "validation/results/kin_pilot_opencap_subject2_squats1.json"
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

**Result (2026-11-10): the expected result is not met.** The figures are in
`validation/results/kin_pilot_opencap_subject2_squats1.json`; the run scripts are in
`validation/runs/kin_pilot_opencap_subject2_squats1/`. Every RMSE is after the lag search, so it is the route's best
case.
- **End to end:** all four routes produced their validation reports against both references (4 run). The one-camera
  route with the augmenter is not evaluated: its gates are not-tested on coverage (8.8 % of the
  time both systems recorded was compared). So 3 routes are evaluated against each reference.
- **Lags** against motion capture and OpenCap: five cameras 0.483 and 0.050 s;
  five cameras with the augmenter 0.483 and 0.067 s; one camera 1.317 and
  0.900 s; one camera with the augmenter 1.467 and 0.983 s. These are the same as in the alignment check.
  The five-camera route without the augmenter and the one-camera route have no clear peak; the lag found agrees with
  the independent offset.
- **The expected result, five cameras with the augmenter:** 26 of 36 cells differ by more than 2°.
  In 20 of them the error against motion capture is the larger, so the agreement with OpenCap understates the error
  there; in 6 it is the smaller. Two of the 26 are the toe (mtp) cells, which the gates leave not-tested (reference
  range 3°). No coordinate is over 2° inside a passing cell.

| Cell (joint.plane) | RMSE against motion capture | Bias | Spread | RMSE against OpenCap | Difference | Within 2° | Gate |
|---|---|---|---|---|---|---|---|
| ankle_l.sagittal | 9.66 | -6.78 | 6.88 | 5.29 | +4.37 | **no** | fail |
| ankle_r.sagittal | 6.53 | -5.84 | 2.91 | 5.37 | +1.16 | yes | fail |
| elbow_l.sagittal | 11.95 | 9.09 | 7.76 | 10.98 | +0.97 | yes | fail |
| elbow_r.sagittal | 12.39 | 9.35 | 8.13 | 9.13 | +3.27 | **no** | fail |
| forearm_l.transverse | 24.91 | -24.05 | 6.51 | 9.87 | +15.04 | **no** | fail |
| forearm_r.transverse | 25.05 | -24.35 | 5.88 | 17.05 | +8.01 | **no** | fail |
| hip_l.frontal | 4.60 | 0.67 | 4.55 | 5.41 | -0.81 | yes | pass |
| hip_l.sagittal | 7.94 | -1.49 | 7.80 | 7.90 | +0.04 | yes | fail |
| hip_l.transverse | 4.04 | -3.02 | 2.68 | 6.94 | -2.90 | **no** | pass |
| hip_r.frontal | 7.24 | -5.23 | 5.01 | 2.85 | +4.39 | **no** | fail |
| hip_r.sagittal | 4.34 | -0.93 | 4.24 | 8.19 | -3.85 | **no** | fail |
| hip_r.transverse | 9.11 | -6.08 | 6.78 | 6.92 | +2.19 | **no** | fail |
| knee_l.frontal | 5.93 | 2.23 | 5.50 | 9.61 | -3.68 | **no** | fail |
| knee_l.sagittal | 4.11 | 3.22 | 2.55 | 7.11 | -3.01 | **no** | fail |
| knee_r.frontal | 22.94 | -16.63 | 15.80 | 5.24 | +17.70 | **no** | fail |
| knee_r.sagittal | 7.27 | 6.25 | 3.70 | 7.43 | -0.16 | yes | fail |
| lumbar.frontal | 5.81 | 5.00 | 2.96 | 5.56 | +0.25 | yes | fail |
| lumbar.sagittal | 9.18 | -0.80 | 9.14 | 3.92 | +5.26 | **no** | fail |
| lumbar.transverse | 6.63 | -6.15 | 2.48 | 5.11 | +1.52 | yes | fail |
| mtp_l.sagittal | 7.47 | 7.47 | 0.24 | 0.00 | +7.47 | **no** | not-tested |
| mtp_r.sagittal | 7.47 | 7.47 | 0.24 | 0.00 | +7.47 | **no** | not-tested |
| pelvis.frontal | 3.03 | 0.75 | 2.93 | 2.63 | +0.40 | yes | pass |
| pelvis.sagittal | 9.18 | 6.00 | 6.95 | 2.81 | +6.38 | **no** | fail |
| pelvis.transverse | 5.76 | 5.52 | 1.65 | 3.60 | +2.16 | **no** | fail |
| pelvis_segment.frontal | 6.80 | 3.98 | 5.51 | 3.96 | +2.84 | **no** | fail |
| pelvis_segment.sagittal | 8.73 | -5.59 | 6.71 | 2.88 | +5.85 | **no** | fail |
| shoulder_l.frontal | 5.98 | -5.35 | 2.67 | 8.04 | -2.06 | **no** | fail |
| shoulder_l.sagittal | 8.59 | -7.12 | 4.82 | 4.44 | +4.15 | **no** | fail |
| shoulder_l.transverse | 3.99 | -2.51 | 3.10 | 3.52 | +0.46 | yes | pass |
| shoulder_r.frontal | 8.93 | -8.60 | 2.40 | 11.26 | -2.32 | **no** | fail |
| shoulder_r.sagittal | 8.49 | -6.66 | 5.27 | 5.20 | +3.30 | **no** | fail |
| shoulder_r.transverse | 4.23 | -0.41 | 4.21 | 3.96 | +0.27 | yes | pass |
| subtalar_l.frontal | 16.83 | -15.27 | 7.08 | 13.76 | +3.07 | **no** | fail |
| subtalar_r.frontal | 11.81 | -11.54 | 2.54 | 7.12 | +4.69 | **no** | fail |
| torso_segment.frontal | 8.74 | 7.68 | 4.17 | 2.54 | +6.21 | **no** | fail |
| torso_segment.sagittal | 5.94 | -4.96 | 3.26 | 2.56 | +3.37 | **no** | fail |

Spread is the SD of the difference; bias and spread are those of the cell's worst coordinate. The cell's RMSE is the
maximum over its coordinates. Per-coordinate figures for every route are in the results file.
- **Sensitivity, the one-camera routes at one shared lag** (1.333 s: the five-camera-with-augmenter lag plus Cam2's
  0.85 s from the multi-view sync, 46 frames of lag and 5 frames trimmed at the start): the route without the augmenter
  changes by at most 0.30° in any cell. The route with the augmenter changes by up to 19.9° (hip_l.sagittal), and it
  is not evaluated on coverage either way.
- **Gates against docs/accuracy.md's targets** (description only; the full run judges them): five cameras with
  the augmenter 5 pass, 29 fail, 2 not-tested; five cameras 5, 29, 2; one camera 1, 33, 2.
