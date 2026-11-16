---
type: "step"
title: "Test the central bet: does a personalised model make one camera good enough?"
status: "done"
area: "person-model"
parent: "[[goal-twin-layers]]"
priority: "2"
source: "design review of 2026-11-16 (review/design-2026-11, REVIEW.md)"
updated: "2026-11-16"
---
# Test the central bet: does a personalised model make one camera good enough?

The goal assumes that once the twin exists, a phone alone is enough. Nothing has tested that: every one-camera result so far used a body scaled from height, and missed by 15-30° at the hip ([[t-kin-labvalidation]]).

On data we already have: rerun the one-camera routes' IK with each subject's body scaled from their motion-capture static trial, as the stand-in for a finished twin, in place of the height-scaled body. The pipeline's own model is used, so only the personalisation changes. HSMR is included where its adapter can take a given model.

If the hip and knee errors don't fall sharply, phone-only capture needs a different design, whatever the twin holds.

**Done (2026-11-16,** [[t-twin-bet-scaled-model]]**):** the expected result is not met. With the mocap-scaled body the
one-camera hip and knee errors do not fall (MediaPipe +2.7° and +2.1°; HSMR within 0.2°). Phone-only capture needs
a different design from "the same route with better bones"; that is the owner's to decide.

