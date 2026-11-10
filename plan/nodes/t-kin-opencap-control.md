---
type: "test"
title: "Positive control: OpenCap's own result against the motion capture"
status: "planned"
area: "pipeline"
parent: "[[kin-labvalidation]]"
expected: "Proposal: through this pipeline's comparison, OpenCap's five-camera result on subject 2's squats1 has a mean absolute error over the lower-limb and trunk angles within 2 degrees of the 4.5 degrees its paper reports, with one clear lag"
source: "video pilot of 2026-11-10 (plan/nodes/t-kin-pilot.md)"
updated: "2026-11-10"
---
# Positive control: OpenCap's own result against the motion capture

The expected result above is a proposal (2026-11-10). Confirm or change it before the control runs.

It answers two questions the pilot left open:
- **Does the comparison tool reproduce a published number?** OpenCap's paper reports a mean absolute error of 4.5° against marker motion capture, over all its activities. If this tool gives a very different figure from OpenCap's own files, the tool is wrong somewhere: the lag, a coordinate's name or sign, or how the motion capture is read.
- **What is the bar?** OpenCap's result uses the same model as the motion capture, so its errors carry no difference between model definitions. The gap between its errors and the pipeline's shows how much of the pipeline's bias comes from its model.

It needs no videos and no GPU. OpenCap's result for the pilot's trial is already on the laptop, from the fixture. If the LabValidation copy also holds OpenCap's results for the other subjects and trials, the control extends to all of them; whether it does is to be checked on the laptop.

Not fresh for the pilot's trial: its lag against the motion capture has been looked at (0.417 s, clear), but no error. The paper's figure covers all activities, so a squat alone may differ; that is why the proposal allows 2°.
