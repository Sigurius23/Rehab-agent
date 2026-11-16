---
type: "test"
title: "Our back end on OpenCap's markers, against the motion capture"
status: "planned"
area: "pipeline"
parent: "[[kin-backend-markers]]"
expected: "Proposal: over the trials and lag rule of the zero-lag positive control, our back end's mean absolute error over the 18 angles is within 1.5 degrees of OpenCap's own IK on the same markers (4.57 degrees)"
source: "owner 2026-11-16"
updated: "2026-11-16"
---
# Our back end on OpenCap's markers, against the motion capture

The expected result above is a proposal (2026-11-16). Confirm or change it before the run.

- **Prediction, written first:** within 1.5° overall, but with constant biases at the pelvis and hip larger than OpenCap's, from the two models' different frame definitions (`docs/validation-results.md` section 4, point 4).
- Report RMSE, mean absolute error, bias and spread per angle, beside OpenCap's own figures for the same trials.
- Not fresh: LabValidation has been used for two fix rounds and four post-hoc analyses.
