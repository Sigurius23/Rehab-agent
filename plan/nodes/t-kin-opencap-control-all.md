---
type: "test"
title: "Positive control on all subjects: OpenCap's own results against the motion capture"
status: "planned"
area: "pipeline"
parent: "[[kin-labvalidation]]"
expected: "For the primary configuration (HRNet, two cameras, all four activities), the mean absolute error over the 18 angles is within 2 degrees of the paper's 4.5 degrees: computed per trial, averaged over each subject's evaluated trials, then over the 10 subjects"
fresh: "yes"
source: "the owner, 2026-11-10, after [[t-kin-opencap-control]]"
updated: "2026-11-10"
---
# Positive control on all subjects: OpenCap's own results against the motion capture

Written and committed on 2026-11-10, before any of OpenCap's video results were extracted from the LabValidation
zip. The expected result above is the owner's, approved before this note was written.

**The primary configuration, from the paper** (Uhlrich et al. 2023, *PLOS Computational Biology* 19(10): e1011462,
Methods, "Validation results"):

> "The kinematic MAE for the two-camera HRNet setup, averaged across degrees of freedom and activities, was 4.5°
> (range = 1.7–10.3°) and 12.3 mm (range = 5–20.3 mm) for the 18 rotational and three translational degrees of
> freedom, respectively."

- **Pose estimator:** HRNet (Methods, "Kinematics and kinetics": the data "were estimated using the two 45° cameras
  and the HRNet pose detection algorithm").
- **Cameras:** two, the ±45° phones ("Unless otherwise noted, the validation results used only the two ±45°
  cameras"). In the zip this is `OpenSimData/Video/HRNet/2-cameras/IK`.
- **Activities:** all four (walking, squats, sit-to-stand, drop jumps), since the figure is averaged across
  activities. So the pass rule uses every trial of the primary configuration.
- **Angles:** the paper's 18 rotational degrees of freedom ("pelvis rotations [3], hips [2x3], knees [2x1], ankles
  [2x2], and lumbar [3]"). These are the same 18 as in [[t-kin-opencap-control]]: pelvis tilt, list and rotation;
  per side hip flexion, adduction and rotation, knee angle, ankle angle and subtalar angle; lumbar extension,
  bending and rotation.
- The paper averages across degrees of freedom and activities. The owner's rule averages per trial, then per
  subject, then over subjects, so the two can differ.

**Fixed before computing:**
- **Comparison:** each OpenCap IK result against the same subject's and trial's motion-capture IK, through the
  pipeline's comparison (`validation.compare`, as `rehabtwin validate --reference-grade marker-mocap` runs it).
- **One lag per trial,** searched over ±4 s. It must have a clear peak: the best lag at least 0.2 s inside the
  window, and every other local minimum more than 0.3 s away with at least twice the best's objective.
- **Evaluated:** a trial is evaluated when its lag has a clear peak and the comparison's coverage is not short
  (`validation.MIN_COVERAGE`). Otherwise it counts as run but not evaluated. A trial with a result but no
  motion capture counts as not run and is listed.
- **Per trial:** the mean absolute error over the 18 angles, all 18 required.
- **Subject 2's `squats1`** has been seen ([[t-kin-opencap-control]]). It is reported separately and left out of the
  pass rule.

**Reported as description, not part of the pass rule:** every other estimator and camera count; the figure per
movement and per subject; bias and spread per angle; run and evaluated counts.

**Prediction, written first:** squats are worse than the average over movements, and pelvis tilt and hip flexion
have opposite biases in at least 6 of the 10 subjects.

Only the `OpenSimData/Video/**/IK` files are extracted, outside the repository. The `Dynamics` folder and the force
data are not opened.
