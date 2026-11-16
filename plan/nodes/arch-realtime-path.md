---
type: "step"
title: "A real-time path from capture to cue"
status: "open"
area: "cues"
parent: "[[pillar-act]]"
priority: "2"
source: "design review of 2026-11-16 (review/design-2026-11, REVIEW.md)"
updated: "2026-11-16"
---
# A real-time path from capture to cue

Feedback, the suit and the exoskeleton need answers while the person moves. The pipeline is offline: HSMR takes about 7 minutes for 8 seconds of video, and `process` about 20 seconds (design review). `docs/architecture.md` has no real-time path.

First: measure the current end-to-end latency per stage, and decide which signals a live cue needs. A latency target is the owner's to set ([[d-budget-and-time]] covers the hardware it implies).
