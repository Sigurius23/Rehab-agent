---
type: "step"
title: "SlimeVR posture signals against motion capture"
status: "open"
area: "suit"
parent: "[[goal-measured-kinematics]]"
priority: "2"
source: "docs/gaps-and-open-decisions.md G-05"
updated: "2026-11-17"
---
# SlimeVR posture signals against motion capture

The same protocol as for video: per joint and plane, IMU against motion capture.

**2026-11-17:** the simulated tests support one camera plus sensors on the pelvis, thighs and shanks as an upper
bound ([[t-kin-camera-plus-imu-sim-shanks]]). The proposed order is a research sensor first (Movella DOT), then
SlimeVR trackers against it, with no motion capture of our own: two phones on OpenCap's setup as the reference.
Which trackers to buy: [[d-imu-trackers]].
