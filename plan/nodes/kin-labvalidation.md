---
type: "step"
title: "Video kinematics on OpenCap LabValidation against marker motion capture"
status: "open"
area: "pipeline"
parent: "[[goal-measured-kinematics]]"
priority: "1"
source: "docs/gaps-and-open-decisions.md G-01, D-04, D-11; docs/roadmap.md Phase 1"
updated: "2026-11-09"
---
# Video kinematics on OpenCap LabValidation against marker motion capture

The video front-ends on OpenCap LabValidation, against its marker-motion-capture inverse kinematics:
- the pipeline's routes (MediaPipe, five cameras or one, with and without the marker augmenter);
- the monocular candidates (HSMR/SKEL, OpenCap Monocular, SAM4Dcap), where their licences and files allow.

The thresholds are those of `docs/accuracy.md`, as a first attempt; their clinical adjustment is [[D-03]]. Feeds
[[D-11]].

**What it needs (2026-11-09):**
- **The videos.** The laptop's copy is `LabValidation_withoutVideos.zip`. The version with videos is a separate
  SimTK download, which the owner makes. Its size is to be checked on SimTK; this session cannot reach SimTK.
- **For HSMR:** the SKEL model files. They are licence-gated (an MPI-IS registration by the owner) and
  non-commercial ([[D-09]]). The other front-ends can start without them.
- **On the laptop:** the pipeline's environment and a MediaPipe environment (`examples/opencap_agreement.sh`).
  `workstation/setup.sh` does not install them yet.

**A one-trial pilot can run now** ([[t-kin-pilot]]). The videos of subject 2's `squats1` are public in
`opencap-test-data`, and that trial's motion capture is in the laptop's copy. The pipeline was developed on those
videos (`docs/validation-results.md` section 4), so the pilot is not fresh.

**Proposed stop rule (not yet agreed; the owner sets it):** stop and report if, after the pilot and at most two
rounds of fixes, the five-camera route gives a complete squat repetition through the pipeline's gates for fewer
than 8 of the 10 subjects. Check by 2026-12-07; owned by the owner.
