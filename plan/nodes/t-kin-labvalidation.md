---
type: "test"
title: "Per-joint error against LabValidation's motion capture"
status: "failed"
area: "pipeline"
parent: "[[kin-labvalidation]]"
expected: "Proposal: per route, joint and plane, the RMSE against the motion capture's inverse kinematics; a joint passes on a route if it is within docs/accuracy.md's target (sagittal at most 3 degrees, frontal at most 5) in every evaluated subject; transverse angles are reported only"
result: "Not met (2026-11-10): no sagittal cell is within 3 deg in every evaluated subject on any route; only the frontal pelvis passes (five cameras; with the augmenter also the frontal pelvis segment). 9 of 10 subjects have videos; at lag 0"
fresh: "yes"
record: "validation/results/kin_benchmark_labvalidation_pipeline_routes.json"
updated: "2026-11-10"
---
# Per-joint error against LabValidation's motion capture

The expected result above was proposed on 2026-11-09 and approved by the owner on 2026-11-10, before the full
run and before any of its videos were extracted. The proposed changes after the pilot (below) were approved with
it.

- **Evaluated:** a trial whose result passes the pipeline's own gates (coverage among them). The others are
  reported as not evaluated, never as passing. The counts are given per route.
- **Each error** is reported as RMSE, with its bias and its spread after the bias is removed. The time alignment
  is the pipeline's lag search, at most 4 s, fixed before any error is computed.
- **Fresh:** yes, except subject 2's `squats1`, which is the pilot's trial ([[t-kin-pilot]]) and is reported
  separately. The squat inverse kinematics was read by the sole's dynamic simulations, but no part of the video
  pipeline was built on it.
- **Prediction, written before the run:** the five-camera route with the augmenter misses 3° at the hip and the
  knee. Against OpenCap it showed 8.2° at hip flexion and 7.4° at the knee, mostly bias. The frontal angles of the
  pelvis and the hip pass. One camera misses most sagittal angles.

**Changes after the pilot (proposed 2026-11-10; approved by the owner 2026-11-10).** The pilot ([[t-kin-pilot]]) ran on one trial that
is not part of this test. Its lessons, for the owner to confirm before the full run:
- **Alignment: one lag per timeline, not per route.** The lag comes from a source that uses no route's error:
  the dataset's own synchronisation where it has one, otherwise the lag of OpenCap's result against the motion
  capture plus the video sync between the cameras. Every route on that timeline is compared at that lag. The
  pipeline's own lag search is reported beside it, as each route's best case.
- **Each error is given as RMSE, bias and spread,** per coordinate. The bias includes differences between the two
  models' definitions; the positive control ([[t-kin-opencap-control]]) shows how large those are.
- **Segment inclinations** (trunk and pelvis to gravity) are reported with the joint angles.
- **Prediction, revised after the pilot** (the first one stays above): with five cameras and the augmenter, no
  sagittal angle of the pelvis, hip, knee or ankle is within 3° in every subject; pelvis tilt and lumbar flexion
  miss by more than the hip and the knee; the frontal pelvis angle passes.

**How the approved alignment applies here (2026-11-10, before any video was extracted).** The dataset has its own
synchronisation. Every trial video exists as `<trial>_syncdWithMocap.avi`, and OpenCap's own results from this
dataset lie at zero lag against the motion capture ([[t-kin-opencap-control-all]]). So the full run uses the
`_syncdWithMocap` videos, and every route is compared at lag 0. The pipeline's lag search (±4 s) is reported
beside it as each route's best case. If a route's own processing shifts its timeline (the multi-view sync trims
frames at the start), that shift is taken from the route's own sync record, not from any error.

**Result, the pipeline's own routes (2026-11-10): the expected result is not met.** On the lab laptop, from the
dataset's `_syncdWithMocap` videos, 160 trials (10 subjects × 16), compared at lag 0. Figures:
`validation/results/kin_benchmark_labvalidation_pipeline_routes.json`; scripts:
`validation/runs/kin_benchmark_labvalidation_pipeline_routes/`. The readings are fixed in the aggregation script's
header, written before any figure was printed:
- a subject's cell RMSE is the mean over that subject's evaluated trials;
- a trial is evaluated when the route produced its validation report and its coverage is not short;
- subject 2's `squats1` is left out of the pass rule.

**Subject 6 shared no videos** (the dataset's README: "This participant chose not to share their videos
publicly"), so 144 trials were run per route, from 9 subjects.

| Route | Run | Evaluated | Subjects | Evaluated: walking / squat / sit-to-stand / drop jump | Passing cells |
|---|---|---|---|---|---|
| Five cameras | 144 | 85 | 9 | 1 / 15 / 18 / 51 | pelvis.frontal |
| Five cameras, augmenter | 144 | 84 | 9 | 1 / 15 / 17 / 51 | pelvis.frontal, pelvis_segment.frontal |
| One camera | 144 | 143 | 9 | 54 / 17 / 18 / 54 | none |
| One camera, augmenter | 144 | 53 | 8 | 3 / 8 / 8 / 34 | none |

Why trials were not evaluated:
- **Five cameras:** the multi-view sync refused 55 trials (53 of them walking). It found no reliable common hip
  motion between the cameras, or the best lag lay at the edge of its window. Two more were refused at processing,
  and one or two had short coverage.
- **One camera with the augmenter:** 53 were refused (no segment long enough to solve, mostly walking), and 38 had
  short coverage.

Key cells, RMSE in degrees: the mean over subjects, then the worst subject in brackets, then the lag-search best
case after the semicolon.

| Cell | Five cameras | Five cameras, augmenter | One camera | One camera, augmenter |
|---|---|---|---|---|
| pelvis.sagittal | 22.6 (28.0); 21.4 | 14.4 (18.2); 13.9 | 14.7 (18.2); 14.0 | 15.4 (25.1); 15.4 |
| pelvis.frontal | 2.6 (3.4); 2.4 | 2.7 (3.8); 2.5 | 6.6 (9.2); 6.6 | 6.4 (10.9); 6.4 |
| hip_r.sagittal | 26.5 (35.3); 22.6 | 14.8 (21.0); 11.3 | 30.2 (35.5); 26.1 | 27.7 (32.8); 25.1 |
| hip_l.sagittal | 26.1 (34.4); 22.5 | 14.8 (21.5); 11.6 | 29.2 (33.5); 25.1 | 27.5 (30.9); 23.5 |
| hip_r.frontal | 3.9 (9.7); 3.7 | 4.4 (9.2); 4.2 | 6.7 (10.3); 6.5 | 5.3 (7.3); 5.2 |
| hip_l.frontal | 3.4 (5.4); 3.2 | 3.6 (5.2); 3.4 | 8.1 (9.2); 7.9 | 7.0 (9.9); 7.2 |
| knee_r.sagittal | 19.6 (29.0); 9.7 | 19.3 (29.9); 9.9 | 24.8 (28.9); 16.9 | 22.4 (27.4); 18.5 |
| knee_l.sagittal | 19.2 (27.2); 9.3 | 18.6 (27.9); 9.6 | 26.3 (30.8); 17.1 | 23.5 (28.8); 18.6 |
| ankle_r.sagittal | 13.6 (20.2); 8.8 | 14.5 (20.0); 11.1 | 20.5 (23.4); 17.5 | 19.8 (28.3); 19.8 |
| ankle_l.sagittal | 13.4 (18.6); 8.5 | 14.3 (18.5); 11.2 | 29.1 (33.4); 25.3 | 32.1 (40.7); 27.2 |
| lumbar.sagittal | 36.2 (43.4) | 11.2 (14.8) | 22.2 (29.6) | 17.4 (26.8) |
| lumbar.frontal | 3.4 (5.4) | 3.6 (7.5) | 12.0 (15.4) | 7.2 (12.4) |
| pelvis_segment.sagittal | 23.6 (30.3) | 14.4 (18.0) | 14.4 (18.2) | 15.2 (24.8) |
| torso_segment.sagittal | 18.5 (23.2) | 10.9 (14.7) | 14.5 (19.4) | 13.5 (15.7) |

The full table for every cell, with bias and spread per coordinate, is in the results file.

**What the figures show** (description, not the pass rule):
- **Lag 0 against the lag search.** The errors at lag 0 are well above the lag-search best case, notably at the
  knee (about 19° against 10° with five cameras). The best lags are small (median about −0.05 s for drop jumps
  and sit-to-stand), but fast movements turn even 0.05–0.1 s of offset into many degrees. A few trials lock onto
  an alias several seconds away. The approved alignment is lag 0; the best case is each route's lower bound.
- **The multi-view sync on synced videos.** It still finds offsets between cameras of up to a few frames, and it
  trims the start accordingly. That trim is the only shift applied.
- **The predictions.**
  - The first: "misses 3° at the hip and the knee" holds. "The frontal angles of the pelvis and the hip pass"
    holds for the pelvis, not for the hip. "One camera misses most sagittal angles" holds; it misses all of them.
  - The revised one: no sagittal pelvis, hip, knee or ankle angle is within 3° in every subject, which holds.
    Pelvis tilt and lumbar flexion miss by more than the hip and the knee, which does not hold: with five cameras
    and the augmenter, 14.4° and 11.2° against 14.8° and 18.6°. The frontal pelvis angle passes, which holds.

**Stop rule** ([[kin-labvalidation]]: fewer than 8 of 10 subjects with a complete squat repetition through the
gates on the five-camera route, after at most two rounds of fixes, by 2026-12-07). Before any fix, the count is
7 subjects on both five-camera routes (3, 4, 5, 7, 9, 10, 11). The others:
- subject 6 has no videos;
- subject 8's squats were refused at the camera sync (Cam4's hip-motion correlation 0.32, against the 0.5
  required);
- subject 2's squats ran, but every repetition contains imputed frames, so none is complete under the reading
  fixed beforehand.

With subject 6 unable to count, 8 subjects means 8 of the 9 with videos.

**HSMR as the next route (owner, 2026-11-12, before HSMR ran on any trial that is part of this test).** HSMR is
judged by the same rules as the pipeline's routes:
- the expected result as approved;
- per joint × plane, the RMSE against the motion capture at lag 0, since HSMR runs on the same synced Cam2 video
  as the one-camera routes, and frame k is motion-capture time k/60;
- the same evaluated rule, and the same readings as `bench_aggregate.py`;
- the lag search reported beside as the best case;
- subject 2's `squats1` left out of the pass rule (it is the smoke-test trial).

The stop rule concerns the five-camera route and does not change. HSMR runs with `--rec_bs 32 --max_instances 1`
and the local mesh-batch patch ([[kin-labvalidation]]).

