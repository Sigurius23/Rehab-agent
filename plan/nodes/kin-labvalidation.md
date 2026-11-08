---
type: "step"
title: "Video kinematics on OpenCap LabValidation against marker motion capture"
status: "open"
area: "pipeline"
parent: "[[goal-measured-kinematics]]"
priority: "1"
source: "docs/gaps-and-open-decisions.md G-01, D-04, D-11; docs/roadmap.md Phase 1"
updated: "2026-11-08"
---
# Video kinematics on OpenCap LabValidation against marker motion capture

HSMR/SKEL (and the other front-ends) on OpenCap LabValidation, against its marker-motion-capture inverse
kinematics. Newly possible: the dataset is on the lab workstation (2026-11-06) and it has a GPU. Still needs the
gated SKEL model files (licensed, non-commercial: [[D-09]]). The thresholds are those of `docs/accuracy.md`,
confirmed by [[D-03]]; write the test's expected result before running it. Feeds [[D-11]].
