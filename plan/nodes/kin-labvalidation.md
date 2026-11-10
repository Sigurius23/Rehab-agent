---
type: "step"
title: "Video kinematics on OpenCap LabValidation against marker motion capture"
status: "open"
area: "pipeline"
parent: "[[goal-measured-kinematics]]"
priority: "1"
source: "docs/gaps-and-open-decisions.md G-01, D-04, D-11; docs/roadmap.md Phase 1"
updated: "2026-11-10"
---
# Video kinematics on OpenCap LabValidation against marker motion capture

The video front-ends on OpenCap LabValidation, against its marker-motion-capture inverse kinematics:
- the pipeline's routes (MediaPipe, five cameras or one, with and without the marker augmenter);
- the monocular candidates (HSMR/SKEL, OpenCap Monocular, SAM4Dcap), where their licences and files allow.

The thresholds are those of `docs/accuracy.md`, as a first attempt; their clinical adjustment is [[D-03]]. Feeds
[[D-11]].

**What it needs (2026-11-09, laptop line updated 2026-11-10):**
- **The videos.** The laptop's copy is `LabValidation_withoutVideos.zip`. The version with videos is a separate
  SimTK download, which the owner makes. Its size is to be checked on SimTK; this session cannot reach SimTK.
- **For HSMR:** the SKEL model files. They are licence-gated (an MPI-IS registration by the owner) and
  non-commercial ([[D-09]]). The other front-ends can start without them.
- **On the laptop:** the pipeline's environment and a MediaPipe environment. Both were set up for the pilot, and
  their versions are in the pilot's results file. `workstation/setup.sh` does not install them yet.

**The pilot ran on 2026-11-10** ([[t-kin-pilot]]; `docs/validation-results.md` section 4b). Its expected result
was not met: for five cameras with the augmenter, the error against motion capture differs from the error against
OpenCap by more than 2° in 26 of 36 cells, mostly larger. What it changes for the full run:
- **Alignment.** A lag search per route is fragile on repeated movements: two routes had no clear peak, and two
  routes on one timeline got lags 0.15 s apart. The full run uses one lag per timeline ([[t-kin-labvalidation]]).
- **The bar.** OpenCap's own result has not been compared with the motion capture in this tool. That comparison
  comes first ([[t-kin-opencap-control]]). It needs no videos.
- **Follow-ups:** [[idea-fppa-deep-flexion]], [[idea-one-camera-robust-signals]] and the approval label
  ([[d-feature-release-rule]]).

**Proposed stop rule (not yet agreed; the owner sets it):** stop and report if, after the pilot and at most two
rounds of fixes, the five-camera route gives a complete squat repetition through the pipeline's gates for fewer
than 8 of the 10 subjects. Check by 2026-12-07; owned by the owner.
