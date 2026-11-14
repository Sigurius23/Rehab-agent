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

**Result, HSMR (2026-11-13): no cell passes.** Run on Cam2's synced video, with the rules recorded before it ran.
Figures: the same results file, route `hsmr`.
- **Counts:** 144 run and 143 evaluated, from 9 subjects; nothing was refused or short.
- **One retry:** subject 2's `DJ3` failed once in HSMR's demo with a CUDA library error
  (`CUBLAS_STATUS_EXECUTION_FAILED`), during the owner's logout. It was retried once and succeeded; the retry is
  recorded.

Key cells, RMSE in degrees as above: the mean over subjects, the worst subject in brackets, then the lag-search
best case after the semicolon.

| Cell | HSMR (one camera) | MediaPipe, one camera | MediaPipe, five cameras with the augmenter |
|---|---|---|---|
| pelvis.sagittal | 7.1 (10.7); 6.3 | 14.7 (18.2); 14.0 | 14.4 (18.2); 13.9 |
| pelvis.frontal | 5.4 (6.6); 5.6 | 6.6 (9.2); 6.6 | 2.7 (3.8); 2.5 |
| hip_r.sagittal | 20.1 (22.2); 14.4 | 30.2 (35.5); 26.1 | 14.8 (21.0); 11.3 |
| hip_l.sagittal | 21.2 (24.0); 17.3 | 29.2 (33.5); 25.1 | 14.8 (21.5); 11.6 |
| hip_r.frontal | 7.8 (9.7); 7.7 | 6.7 (10.3); 6.5 | 4.4 (9.2); 4.2 |
| hip_l.frontal | 4.7 (5.5); 4.7 | 8.1 (9.2); 7.9 | 3.6 (5.2); 3.4 |
| knee_r.sagittal | 30.3 (38.1); 16.9 | 24.8 (28.9); 16.9 | 19.3 (29.9); 9.9 |
| knee_l.sagittal | 28.9 (35.4); 16.7 | 26.3 (30.8); 17.1 | 18.6 (27.9); 9.6 |
| ankle_r.sagittal | 14.9 (17.8); 14.2 | 20.5 (23.4); 17.5 | 14.5 (20.0); 11.1 |
| ankle_l.sagittal | 14.4 (16.9); 14.2 | 29.1 (33.4); 25.3 | 14.3 (18.5); 11.2 |
| lumbar.sagittal | 9.9 (16.7) | 22.2 (29.6) | 11.2 (14.8) |
| lumbar.frontal | 7.3 (9.9) | 12.0 (15.4) | 3.6 (7.5) |
| pelvis_segment.sagittal | 7.1 (10.7) | 14.4 (18.2) | 14.4 (18.0) |
| torso_segment.sagittal | 9.6 (13.5) | 14.5 (19.4) | 10.9 (14.7) |

**What it shows** (description, not the pass rule):
- **Better than MediaPipe from one camera at the pelvis, lumbar spine and hip.** HSMR's pelvis tilt (7.1°) and
  lumbar flexion (9.9°) are the lowest of any route, five cameras included.
- **Worse at the knee:** about 30° at lag 0. The lag-search best case is 17°, so much of that is timing, which the
  lag 0 rule counts in full.
- **The frontal pelvis does not pass** (5.4°, against 2.7° with five cameras).

**Fix round 1 of 2 under the stop rule (owner, 2026-11-14; recorded before the rerun).**
- **Change:** the `_syncdWithMocap` videos are documented as synced, so the multi-view routes take every camera's
  offset as 0: `mp-multiview` without `--sync`, and no start trim, so the reference is not shifted. This is
  justified by the dataset's documentation. Without `--sync`, `mp-multiview` pairs frame k across the cameras
  from frame 0.
- **Prediction:** subject 8 and most walking trials pass the multi-view stage. The lags are not predicted to change.
  The round-0 best lags vary in sign between routes on the same video, so they mostly reflect pose error.
- **Unchanged:** the pass rule, lag 0, the definition of a complete repetition, and the stop count.
- **Scope:** only the multi-view routes (five cameras, with and without the augmenter) are rerun, from the same
  MediaPipe dumps, and reported beside round 0.

**Fix round 1, result (2026-11-14): the stop count stays at 7.** Figures:
`validation/results/kin_benchmark_labvalidation_round1_multiview.json`. Round 0 is unchanged beside it.
- **The multi-view stage now passes on all 144 trials** (round 0: 89), including subject 8 and all 54 walking trials.
  The first half of the prediction holds.
- **Evaluated:**
  - five cameras: 85 → 88 (walking / squat / sit-to-stand / drop jump: 1 / 15 / 18 / 51 → 44 / 15 / 18 / 11);
  - with the augmenter: 84 → 42 (1 / 15 / 17 / 51 → 2 / 15 / 17 / 8).

  Walking now gets through on five cameras. The augmenter route loses most walking and drop-jump trials at IK
  ("no segment long enough to solve").
- **Drop jumps got worse.** With the offsets at 0, the median reprojection error rose from 4.7 to 11.1 px and the
  valid frames fell from 100 % to 77 %, so drop jumps mostly failed on coverage. On squats and sit-to-stand the
  reprojection error rose from about 4.6 to 5.7 px. The round-0 sync's offsets (median largest 6–9 frames)
  therefore improved the triangulation. The `_syncdWithMocap` videos are not frame-exact between cameras when read
  frame by frame.
- **Passing cells:** five cameras none (round 0: frontal pelvis); with the augmenter the frontal pelvis and the
  frontal pelvis segment, as before.
- **Mean RMSE over subjects, round 0 → round 1, at lag 0:**

| Cell | Five cameras | Five cameras, augmenter |
|---|---|---|
| pelvis.sagittal | 22.6 → 19.2 | 14.4 → 10.9 |
| pelvis.frontal | 2.6 → 3.8 | 2.7 → 2.4 |
| hip_r.sagittal | 26.5 → 28.4 | 14.8 → 12.6 |
| hip_l.sagittal | 26.1 → 28.4 | 14.8 → 13.0 |
| knee_r.sagittal | 19.6 → 22.3 | 19.3 → 12.5 |
| knee_l.sagittal | 19.2 → 24.3 | 18.6 → 12.2 |
| ankle_r.sagittal | 13.6 → 11.4 | 14.5 → 9.3 |
| ankle_l.sagittal | 13.4 → 11.7 | 14.3 → 9.5 |
| lumbar.sagittal | 36.2 → 30.2 | 11.2 → 9.8 |

  With the augmenter, the sagittal errors fell (the knee from about 19° to 12°), but on fewer and different trials:
  42 evaluated, mostly squats and sit-to-stand.
- **Lags:** on squats, sit-to-stand and drop jumps the median best lag moved by at most about 2.5 frames, in line
  with the prediction. Walking, newly evaluated, has a median best lag of −16 to −20 frames, which round 0 could
  not show.
- **Stop count: 7** on both routes (3, 4, 5, 7, 9, 10, 11). Subject 8's `squats1` is still refused at
  IK, and every repetition of its `squatsAsym1` contains imputed frames. Subject 2's repetitions all contain imputed
  frames, as before. One round of fixes is left, by 2026-12-07.

**Post hoc: HSMR's lag (2026-11-14).** This was looked into after the results; nothing in the pipeline was changed.
- **The cause is the video decoding, not the adapter or the processing.** Many `_syncdWithMocap` videos have a
  timestamp gap at the start. Their container lists more frames than are stored: 0–11 more, median 6, the same
  number on all five cameras of a trial.
  - OpenCV, which the MediaPipe adapter uses, reads the stored frames one after another.
  - imageio's FFmpeg reader, which HSMR's demo uses, keeps a constant frame rate and fills the gap with
    duplicated frames.

  On subject 10's `DJ1`, for example, the container lists 149 frames and 138 are stored. imageio returns 149,
  with 11 duplicates at the start, so from there on each HSMR frame is 11 frames later than the same picture in
  MediaPipe.
- **Across 57 trials other than walking,** HSMR's best lag minus MediaPipe's equals the gap: slope 0.99 per frame,
  r = 0.97. The adapter sets time as frame/fps, and processing filters with a zero-lag Butterworth (`filtfilt`),
  the same for both routes.
- **Which clock the motion capture follows is not settled.** HSMR's lag rises with the gap (slope 0.40) and
  MediaPipe's falls with it (−0.59), both only weakly (r = 0.28 and −0.40). At gap 0 both are within about 2–3
  frames of lag 0.
- **Within each trial the cameras share one gap,** so it does not explain the camera offsets that the round-0
  multi-view sync found.
- **Possible fixes, for the owner to decide:**
  - read HSMR's input frames with the same decoder as MediaPipe;
  - or drop the gap-filling duplicates;
  - or settle first which clock the motion capture follows.

**Fix round 2 of 2 (owner, 2026-11-14; recorded before the rerun).**
- **Multi-view:** back to round 0's `--sync` offsets, since round 1 showed they are real: the reprojection error
  rose at offset 0. The routes are rerun from the same MediaPipe dumps with round 0's settings.
- **HSMR:** it reads exactly the frames stored in each video, the frames OpenCV returns, so the duplicated gap
  frames are gone. This is justified by the frame counts, not by any error. HSMR's and the pipeline's code are
  unchanged. Instead, each Cam2 video's stored frames, read with OpenCV in order, are copied losslessly (FFV1, same
  fps) to a temporary video, and HSMR and the adapter run on that copy. Before each run, a check confirms that
  HSMR's reader (imageio/FFmpeg) returns the same number of frames, pixel-identical to OpenCV's. Tested on
  subject 10's `DJ1`: 149 frames listed, 138 stored; the copy reads back as 138, identical.
- **Prediction:** HSMR's best lag on squats, sit-to-stand and drop jumps moves within ±2 frames of MediaPipe's, and
  its knee error at lag 0 falls toward its best case. The stop count stays at 7, because subjects 2 and 8 fail on
  imputed frames.
- **Unchanged:** the pass rule, lag 0, the definition of a complete repetition, and the stop count.
- **Reported:** HSMR and the multi-view routes, beside rounds 0 and 1, with the stop count.

