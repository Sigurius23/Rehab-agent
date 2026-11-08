---
type: "step"
title: "Boards and the self-test model rebuild identically on another machine"
status: "open"
area: "sole"
parent: "[[goal-sensor-sole]]"
priority: "2"
source: "hardware/sensor-sole/foot_models/PROVENANCE.json (soles, two_segment)"
updated: "2026-11-08"
---
# Boards and the self-test model rebuild identically on another machine

`VERIFICATION.md` says the boards regenerate byte for byte; that was shown on one machine only. On the lab laptop
the regenerated EU 42 boards have other design hashes (R 82647223b9, L 553b446206), and the two-segment
self-test model has another hash (`foot_models/PROVENANCE.json`). None of the finished studies depended on it.
