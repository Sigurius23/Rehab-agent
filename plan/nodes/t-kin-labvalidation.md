---
type: "test"
title: "Per-joint error against LabValidation's motion capture"
status: "planned"
area: "pipeline"
parent: "[[kin-labvalidation]]"
expected: "Proposal: per route, joint and plane, the RMSE against the motion capture's inverse kinematics; a joint passes on a route if it is within docs/accuracy.md's target (sagittal at most 3 degrees, frontal at most 5) in every evaluated subject; transverse angles are reported only"
fresh: "yes"
updated: "2026-11-09"
---
# Per-joint error against LabValidation's motion capture

The expected result above is a proposal (2026-11-09). Confirm or change it before the full run.

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
