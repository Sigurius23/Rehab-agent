---
type: "step"
title: "One camera plus simulated orientation sensors on the pelvis and thighs"
status: "open"
area: "pipeline"
parent: "[[goal-measured-kinematics]]"
priority: "2"
source: "owner 2026-11-16, after t-twin-bet-scaled-model"
updated: "2026-11-16"
---
# One camera plus simulated orientation sensors on the pelvis and thighs

**Question:** can orientation sensors on the pelvis and thighs fix one camera's pelvis–hip error? This is simulated sensors only, so it is an upper bound for real ones.

It follows [[t-twin-bet-scaled-model]]: the person's own bones did not reduce one camera's hip and knee error, so the next candidate is an extra sensor. Nothing is bought or built for this; the sensors are computed from the motion capture. The test is [[t-kin-camera-plus-imu-sim]].
