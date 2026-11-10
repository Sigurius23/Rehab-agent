---
type: "test"
title: "Positive control: OpenCap's own result against the motion capture"
status: "running"
area: "pipeline"
parent: "[[kin-labvalidation]]"
expected: "Proposal: through this pipeline's comparison, OpenCap's five-camera result on subject 2's squats1 has a mean absolute error over the lower-limb and trunk angles within 2 degrees of the 4.5 degrees its paper reports, with one clear lag"
source: "video pilot of 2026-11-10 (plan/nodes/t-kin-pilot.md)"
updated: "2026-11-10"
---
# Positive control: OpenCap's own result against the motion capture

The expected result above was proposed on 2026-11-10 and approved by the owner before the control ran.

It answers two questions the pilot left open:
- **Does the comparison tool reproduce a published number?** OpenCap's paper reports a mean absolute error of 4.5° against marker motion capture, over all its activities. If this tool gives a very different figure from OpenCap's own files, the tool is wrong somewhere: the lag, a coordinate's name or sign, or how the motion capture is read.
- **What is the bar?** OpenCap's result uses the same model as the motion capture, so its errors carry no difference between model definitions. The gap between its errors and the pipeline's shows how much of the pipeline's bias comes from its model.

It needs no videos and no GPU. OpenCap's result for the pilot's trial is already on the laptop, from the fixture. If the LabValidation copy also holds OpenCap's results for the other subjects and trials, the control extends to all of them; whether it does is to be checked on the laptop.

Not fresh for the pilot's trial: its lag against the motion capture has been looked at (0.417 s, clear), but no error. The paper's figure covers all activities, so a squat alone may differ; that is why the proposal allows 2°.

**Lag, recorded before any error was computed (2026-11-10, lab laptop).** OpenCap's `squats1.mot` from the fixture
against the motion capture, aligned as `rehabtwin validate` aligns them (14 shared sagittal coordinates, ±4 s):
best lag 0.417 s, next local minimum at −1.183 s with 3.02 times the best's objective. The peak is clear by the
pilot's criterion (at least 0.2 s inside the window; every other minimum more than 0.3 s away at least twice the
best).

**Angle set, fixed before any error was computed.** "Lower-limb and trunk angles" are taken as 18 coordinates:
pelvis tilt, list and rotation; per side hip flexion, adduction and rotation, knee angle, ankle angle and subtalar
angle; lumbar extension, bending and rotation. A secondary figure leaves out the two subtalar angles (16), in case
the paper's set has none; the expected result is judged on the 18.
