---
type: "test"
title: "Per-joint error against LabValidation's motion capture"
status: "planned"
area: "pipeline"
parent: "[[kin-labvalidation]]"
expected: "Proposal: per route, joint and plane, the RMSE against the motion capture's inverse kinematics; a joint passes on a route if it is within docs/accuracy.md's target (sagittal at most 3 degrees, frontal at most 5) in every evaluated subject; transverse angles are reported only"
fresh: "yes"
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
