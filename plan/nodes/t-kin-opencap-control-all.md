---
type: "test"
title: "Positive control on all subjects: OpenCap's own results against the motion capture"
status: "passed"
area: "pipeline"
parent: "[[kin-labvalidation]]"
expected: "For the primary configuration (HRNet, two cameras, all four activities), the mean absolute error over the 18 angles is within 2 degrees of the paper's 4.5 degrees: computed per trial, averaged over each subject's evaluated trials, then over the 10 subjects"
result: "Met (2026-11-10): primary configuration (HRNet, two cameras) 4.80 deg over the 18 angles, +0.30 from the paper's 4.5; all 10 subjects evaluated, 69 of 160 trials; walking almost never passes the clear-lag rule (1 of 60 evaluated)"
fresh: "yes"
record: "validation/results/kin_control_opencap_all_subjects.json"
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

**Extraction (2026-11-10, after this note was committed).** From `LabValidation_withoutVideos.zip`, into
`~/rehab-agent-data/datasets/opencap-labvalidation/` (outside the repository), with every file's sha256 in a
manifest: `video-ik/`, all 4,410 files under `OpenSimData/Video/**/IK` (1,440 `.mot`), and `mocap-ik/`, the 160
motion-capture IK `.mot` files. The laptop's earlier extraction held the motion capture of the squats only, so
comparing every trial needed the motion capture's IK too. Nothing under `Dynamics`, `ID` or `ForceData` was
extracted or opened.

**Result (2026-11-10): the expected result is met.** For the primary configuration (HRNet, two cameras), the mean
absolute error over the 18 angles is **4.80°**, +0.30° from the paper's 4.5°. It is computed per trial, averaged
over each subject's evaluated trials, then over the 10 subjects, with subject 2's `squats1` left out. All 10
subjects have evaluated trials. Figures: `validation/results/kin_control_opencap_all_subjects.json`; scripts:
`validation/runs/kin_control_opencap_all_subjects/`.

**The caveat: which trials are evaluated.** 69 of the primary configuration's 160 trials are evaluated; the other 91
have no clear lag peak, so they count as run but not evaluated. Walking almost never passes (1 of 60), and squats
and sit-to-stand pass in 8 of 20 trials each. Their motion repeats, so a lag one cycle away is nearly as good (median
ratio 1.22 among the trials not evaluated). Drop jumps pass in most trials and make up 52 of the 69. The pass rule
therefore rests mostly on drop jumps, not on the four activities evenly as the paper's figure does. The lags found
are near zero (median 0.01 s; 1,067 of 1,440 within ±0.05 s). The dataset's video results seem to be on the motion
capture's clock already, which would make the lag search unnecessary here. That is an observation, not part of the
rule.

Description, not part of the pass rule.

By estimator and camera count:

| Configuration | Run | Evaluated | Subjects evaluated | MAE over the 18 angles |
|---|---|---|---|---|
| HRNet 2-cameras | 160 | 69 | 10 | 4.80 |
| HRNet 3-cameras | 160 | 72 | 10 | 4.73 |
| HRNet 5-cameras | 160 | 77 | 10 | 4.52 |
| OpenPose default 2-cameras | 160 | 67 | 10 | 5.06 |
| OpenPose default 3-cameras | 160 | 64 | 10 | 5.00 |
| OpenPose default 5-cameras | 160 | 69 | 10 | 4.80 |
| OpenPose highAccuracy 2-cameras | 160 | 76 | 10 | 4.56 |
| OpenPose highAccuracy 3-cameras | 160 | 74 | 10 | 4.31 |
| OpenPose highAccuracy 5-cameras | 160 | 77 | 10 | 4.19 |

Primary configuration, by movement (subject-averaged):

| Movement | MAE | Subjects | Evaluated trials | Not evaluated |
|---|---|---|---|---|
| drop jump | 5.00 | 10 | 52 | 8 |
| sit-to-stand | 4.28 | 5 | 8 | 12 |
| squat | 4.08 | 6 | 8 | 12 |
| walking | 2.34 | 1 | 1 | 59 |

Primary configuration, per subject: 2: 4.91°, 3: 3.68°, 4: 4.56°, 5: 4.28°, 6: 3.54°, 7: 4.62°, 8: 4.54°, 9: 5.63°, 10: 6.60°, 11: 5.61°.

Primary configuration, per angle (each a mean over subjects of the subject's mean; spread is the SD of the
difference):

| Angle | MAE | Bias | Spread |
|---|---|---|---|
| pelvis_tilt | 6.80 | -6.09 | 3.41 |
| pelvis_list | 2.14 | +0.40 | 1.83 |
| pelvis_rotation | 3.31 | -1.84 | 2.38 |
| hip_flexion_r | 5.87 | +3.81 | 4.01 |
| hip_adduction_r | 2.70 | -0.07 | 2.46 |
| hip_rotation_r | 4.24 | +2.28 | 3.24 |
| knee_angle_r | 4.22 | -2.18 | 4.21 |
| ankle_angle_r | 6.69 | +4.89 | 5.57 |
| subtalar_angle_r | 5.22 | +2.20 | 4.34 |
| hip_flexion_l | 5.66 | +3.37 | 4.15 |
| hip_adduction_l | 2.65 | -0.39 | 2.37 |
| hip_rotation_l | 3.55 | -0.41 | 3.37 |
| knee_angle_l | 4.64 | -1.89 | 4.69 |
| ankle_angle_l | 7.39 | +5.99 | 5.63 |
| subtalar_angle_l | 5.15 | -2.74 | 4.20 |
| lumbar_extension | 8.34 | +6.62 | 4.72 |
| lumbar_bending | 2.85 | -0.36 | 2.27 |
| lumbar_rotation | 4.93 | +2.93 | 4.12 |

**The prediction is met as stated, on thin ground.** Squats (4.08°) are worse than the average over movements
(3.92°), but that average includes walking from a single evaluated trial (2.34°). Pelvis tilt and hip flexion
have opposite biases in 10 of 10 subjects: pelvis tilt negative, hip flexion positive, the reverse of the signs in
OpenCap's result in the fixture ([[t-kin-opencap-control]]).

**Subject 2's `squats1`, separately (left out of the pass rule):** in the zip, every configuration's lag is 0.00 s
with no clear peak (ratio 1.19–1.66), so it is not evaluated under the rule. Its MAE at that lag would be
4.65° for HRNet with two cameras and 6.05° for OpenPose default with five cameras. The fixture's OpenCap result for
the same trial was 0.417 s off the motion capture and gave 6.32° ([[t-kin-opencap-control]]), so the fixture's
file and the zip's are on different clocks.

**Post hoc, not pre-registered (owner, 2026-11-10, after the result above): the same comparison at zero lag.**
There is no lag search and no clear-peak rule. A trial is evaluated when its coverage is not short and all 18
angles exist. It does not replace the result above. Figures: `validation/results/kin_control_opencap_all_subjects_zerolag_posthoc.json`.
- **Counts:** every result is evaluated: 160 run per configuration, 159 in the averages, with subject 2's `squats1`
  apart. The 645 results evaluated before change by a median of 0.05° (at most 1.43°), since their lags were
  near zero.
- **Primary configuration (HRNet, two cameras):** 4.57°, +0.07° from the paper's 4.5°.
- **Per movement:** drop jump 5.14° (60 trials), sit-to-stand 4.67° (20 trials), squat 4.10° (19 trials), walking 4.13° (60 trials).
- **Per configuration:** HRNet 2-cameras 4.57°, HRNet 3-cameras 4.52°, HRNet 5-cameras 4.39°, OpenPose default 2-cameras 4.88°, OpenPose default 3-cameras 4.95°, OpenPose default 5-cameras 4.72°, OpenPose highAccuracy 2-cameras 4.53°, OpenPose highAccuracy 3-cameras 4.29°, OpenPose highAccuracy 5-cameras 4.19°.
- **The prediction's first part fails at zero lag:** squats (4.10°) are better than the average over movements
  (4.51°). Pelvis tilt and hip flexion still have opposite biases in 10 of 10 subjects.
- **Subject 2's `squats1`** at zero lag: 4.65° for HRNet with two cameras.
