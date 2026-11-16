---
type: "step"
title: "Our back end on OpenCap's own markers"
status: "done"
area: "pipeline"
parent: "[[goal-measured-kinematics]]"
priority: "2"
source: "design review of 2026-11-16 (review/design-2026-11, REVIEW.md)"
updated: "2026-11-16"
---
# Our back end on OpenCap's own markers

Feed OpenCap's video-derived markers from the LabValidation zip (`MarkerData/Video`, the primary configuration: HRNet, two cameras) into this pipeline's back end: its model, scaling and IK. Compare with the motion capture's IK, as the positive control does ([[t-kin-opencap-control-all]]).

It separates the two sources of error. OpenCap's own IK on these markers is 4.57-4.80°. If ours is close, the MediaPipe routes' 14-19° comes from the front end, and replacing the front end is enough. If ours is far off, the model or the IK needs fixing first, whatever front end is used.

Needs only the marker files, which are in the zip already; no videos, no GPU. Read only `MarkerData/Video`, not the force data.

**Done (2026-11-16,** [[t-kin-backend-markers]]**):** 5.11° against OpenCap's 4.57° on the same markers and
trials. The back end is close to OpenCap's; the MediaPipe routes' error comes from the front end.

