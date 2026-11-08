---
type: "step"
title: "BLE write to SenseShift on a bench ESP32"
status: "open"
area: "suit"
parent: "[[goal-haptic-suit]]"
priority: "2"
source: "docs/gaps-and-open-decisions.md G-04"
updated: "2026-11-08"
---
# BLE write to SenseShift on a bench ESP32

One ESP32 with vibration motors and `suit-bridge --ble`. Needs the hardware ([[d-suit-bench-hardware]]). A
possible expected result, to confirm before the test: every cue drives the intended motor, in order, none lost
over 100 cues.
