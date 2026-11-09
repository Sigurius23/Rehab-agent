---
type: "test"
title: "Pilot: one trial's video kinematics against its motion capture"
status: "planned"
area: "pipeline"
parent: "[[kin-labvalidation]]"
expected: "Proposal: on subject 2's squats1, the comparison runs end to end for all four routes, and the five-camera route with the augmenter has an error against the motion capture within 2 degrees of its error against OpenCap at every joint"
fresh: "no"
updated: "2026-11-09"
---
# Pilot: one trial's video kinematics against its motion capture

The expected result above is a proposal (2026-11-09). Confirm or change it before the pilot runs.

The routes are those of `examples/opencap_agreement.sh`: five cameras or one, with and without the augmenter. The
reference changes from OpenCap's markerless result to the trial's marker motion capture, read from the laptop's
LabValidation copy (`--reference-grade marker-mocap`).

The pilot checks two things before the full run:
- that the comparison works against a marker reference: alignment, coordinate names, a model scaled from markers;
- whether this trial's markerless reference was close to motion capture. If it misses by more than 2° somewhere,
  the agreement figures in `docs/validation-results.md` section 4 overstate the accuracy there.

Not fresh: the pipeline was developed on these videos.
