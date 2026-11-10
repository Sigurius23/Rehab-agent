---
type: "idea"
title: "Build the phone-only route on what one camera measures well"
status: "new"
area: "pipeline"
serves:
  - "[[goal-measured-kinematics]]"
source: "video pilot of 2026-11-10 (docs/validation-results.md section 4b)"
updated: "2026-11-10"
---
# Build the phone-only route on what one camera measures well

With one camera (MediaPipe, no augmenter) in the pilot, pelvis tilt, lumbar flexion and hip flexion were each 27-30° off, with opposite biases. The trunk's inclination to gravity was within 5.7° and the knees within 8-9°. One trial, one subject, and a front end the roadmap already calls a test front end only.

If the monocular candidates ([[D-11]]) show the same pattern in the full run, the phone-only route would report segment inclinations and knee flexion, and leave the split between pelvis, spine and hip to routes that can observe it: more cameras, or an inertial sensor on the pelvis ([[suit-slimevr-validation]]). Muscle forces and joint loads need that split, so they would not come from one camera alone.
