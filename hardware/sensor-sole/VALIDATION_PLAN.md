<!-- SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors -->
<!-- SPDX-License-Identifier: CERN-OHL-S-2.0 -->

# Validating the simulated sole against measurement: plan

**2026-11-04. A plan, not a result.** No data has been downloaded or analysed for it. Nothing has been bought,
and no one has been contacted.

There are three separate questions, in this order. A pass at one stage says nothing about the next.

| Stage | Question | What it can validate | What it cannot |
|---|---|---|---|
| **A. Force plate (priority)** | Does the current foot-to-ground model give the measured total ground force and centre of pressure? | The body model's centre of mass, the quasi-static assumption, and later a dynamic simulation's whole-foot force | How load is shared under the foot; anything inside a shoe |
| B. Regional plantar pressure (barefoot) | Does the model share the load between heel, arch, forefoot and toes as measured barefoot? | The foot model with the sole contact model, region by region | Contact through a sole or shoe |
| C. Foot–insole contact | Does the virtual sole, inside a shoe, read what a real in-shoe sensor reads? | The sole as a sensor, the footbed and the shoe layers | Nothing until those layers are modelled (they are not) |

## A. Force-plate comparison of the current foot-to-ground model

**Candidate datasets** (public; terms as read on 2026-11-04; re-check them before use):

| Dataset | Content | Terms | Use |
|---|---|---|---|
| **OpenCap LabValidation** (Uhlrich et al. 2023), [simtk.org/projects/opencap](https://simtk.org/projects/opencap) | 10 people; squats, sit-to-stand, drop jumps, walking; marker motion capture, **ground reaction forces**, EMG of 10 muscles, video. Processed OpenSim models, inverse kinematics and dynamics. About 2.9 GB without videos | Apache-2.0, shown on the SimTK release | **First choice.** Squat and sit-to-stand with force plates, in the same OpenSim model family as the pipeline |
| dos Santos et al. (2017), *PeerJ* 5:e3626, figshare [10.6084/m9.figshare.4525082](https://doi.org/10.6084/m9.figshare.4525082) | 49 people, quiet standing; full-body kinematics and two force plates | Article CC BY 4.0; **data terms not yet confirmed** | Standing centre of pressure relative to the foot (markers on heel and toes) |
| Santos & Duarte (2016), PhysioNet [10.13026/C2WW2W](https://physionet.org/content/hbedb/1.0.0/) | 163 people, quiet standing, 60 s × 4 conditions; force, moments and centre of pressure at 100 Hz; no kinematics | ODC Attribution 1.0 | Standing force and sway only. No foot position, so no regional comparison |
| AddBiomechanics dataset ([addbiomechanics.org](https://addbiomechanics.org/download_data.html)) | 273 subjects, over 70 h of motion with measured ground forces, from many uploaded studies | CC BY 4.0; each dataset lists its uploaders to credit | Later: walking and other movements, many subjects |
| Grouvel et al. (2023), *Sci Data* [10.1038/s41597-023-02077-3](https://doi.org/10.1038/s41597-023-02077-3), data [Yareta](https://doi.org/10.26037/yareta:xkxgaw6ewjdhfntdhtj7upepxy) | 10 adults; walking, squats, knee flexion; markers, IMUs, three AMTI force plates (1,000 Hz) and two 16-sensor insoles (Moticon, 100 Hz) | Article CC BY 4.0; **data terms not yet confirmed** | Force plate here, and stage C later |

**Copy of OpenCap LabValidation used for stage A (noted 2026-11-06).** `LabValidation_withoutVideos.zip`,
3,029,832,907 bytes, sha256 `3290d485124fd12c85dd3bc9ee851f3a0530ad0ff58bc396973e665dd6d28187`.
- **Source:** the owner provided it from their Google Drive. It was originally downloaded from SimTK
  ([simtk.org/projects/opencap](https://simtk.org/projects/opencap), Downloads: release v0.1, file dated 2022-12-20).
- **Matches the SimTK listing** in name, size (2889 MB), date and licence (Apache 2.0 Use Agreement).
- **Complete:** 10 subjects with the same number of entries each (1,196), and no entry newer than 2022-12-20.
- **Not proven byte-identical to the release:** SimTK publishes no checksum.
- **Manifest** (every entry's name, size and CRC32, and the sha256 of each file read): kept with the data on the
  workstation, outside the repository.

**Not usable for this:** the squat already used in the comparison (OpenCap's `squats1_videoAndMocap.mot`). Its
example folder has no force-plate data. An earlier pipeline output in the scratch area named `measured_grf`
holds **estimated** forces: its own record says "quasi-static double stance".

**What can be compared, and how:**
1. **Quasi-static (first).** For each subject, take the measured kinematics, put the model in the posture, and
   solve quasi-static double support.
   - Compare the model's centre of pressure and vertical force with the force plates during quiet standing and
     the slowest part of the squat, where acceleration is small.
   - This tests the body model's centre of mass and the quasi-static assumption. The left/right split also
     depends on the frontal-plane posture and on how the feet's contact shares the load.
   - The total centre of pressure is set by the centre of mass, so the forward–backward check does **not** test
     the sole's contact model.
   - **New code is needed.** `compare_feet.py`'s posture-based task mirrors the right side onto the left and puts
     each foot's centre of pressure under the centre of mass, so it cannot test the left/right split. A
     double-support version that uses the full measured posture has to be written. It must be tested on the
     dataset's kinematics alone, before any force data is opened.
2. **Dynamic (second, separate).** A muscle-driven tracking simulation (OpenSim Moco) of the squat and
   sit-to-stand, with the sole as the foot contact. The predicted ground force and centre of pressure over time
   are compared with the force plates. This is a different experiment from the passive, prescribed-COP control
   in `FOOT_MODELS.md`, and it will be reported separately.

**Amendment 4, to item 2, the dynamic comparison (2026-11-06).** Decided by the owner before any dynamic simulation
was built or run. The text of item 2 above stays as written.
- **Design: two arms,** identical except for the foot contact:
  - **A:** our sole (15 mm spacing) with the assumed contact (v1);
  - **B:** OpenCap's six spheres per foot with OpenCap's contact parameters (the amendment 1 rule).

  Both arms use the same subject models (distributed, with muscles), the same tracking problem, the same settings
  and the same solver.
- **Task:** `squats1` and `squatsAsym1` for all 10 subjects. One window is simulated per trial: the first complete
  squat repetition, found from the pelvis height in the dataset's inverse kinematics (kinematics only).
  Sit-to-stand is left for later, because the chair carries part of the weight.
- **Tracking:** MocoTrack of the dataset's inverse-kinematics coordinates, muscle-driven, with reserve actuators.
  - The problem never sees force data: ground forces come only from the contact model.
  - Settings (weights, mesh, reserves, tolerances) may be changed only to reach convergence. That is judged by
    convergence and kinematic tracking error alone, never by force data. Every change applies to both arms and is
    logged.
- **A valid solution** has converged, and its pelvis residuals are within Hicks et al. (2015):
  - residual forces at most 5 % of the peak external force;
  - residual moments at most 1 % of the centre-of-mass height times that force.

  Invalid or non-converged solutions are reported as not evaluated, not as passing.
- **Plate coverage:** the post-hoc rule applies to this experiment from the start. A trial is left out if either
  plate carries less than 1 % of body weight on average.
- **Hypotheses for arm A** (pass/fail, with the quasi-static pass rule: every evaluated subject within):
  - **H1:** the error of the peak combined vertical force in the window, as a mean over the subject's trials, is at
    most 10 % of body weight.
  - **H2:** the RMS error of the combined forward–backward centre of pressure over the window, as a mean over the
    subject's trials, is at most 15 % of foot length.
- **Body weight:** from the recorded mass (primary); also reported against the plates' measured weight (secondary).
- **Arm B:** arm B against the plates, and A minus B, are reported with the same metrics, as description only.
- **Recorded with it:**
  - the squat force files were already opened for the quasi-static check, so this design is fixed before any
    dynamic result, but not before the force data was seen;
  - arm B is OpenCap's contact in this project's Moco setup, not a reproduction of OpenCap's own published
    simulations.
- **Phases:**
  1. Without force data: build both arms, pilot the tracking on one subject until it converges, and run all
     solves (resumable). Each solution's sha256, validity and tracking error are recorded and committed.
  2. Only after the owner's "go": compare with the plates as defined here.

**Amendment 5, to item 2, the dynamic comparison (2026-11-08).** Decided by the owner before any dynamic result was
compared with the force plates. Amendment 4 above stays as written; this changes its validity rule and its reporting.
- **Why:** with settings v1, arm B's pilot solution converged and had pelvis residuals within Hicks et al. (2015),
  yet it left the floor and flew (pelvis translation RMS 672 mm). Amendment 4 would have counted it as valid.
- **1. Validity** of a dynamic solution now also requires tracking, with the pilot gate's limits, over the window:
  - every tracked joint angle within 5° RMS;
  - every pelvis translation within 20 mm RMS.

  "Joint angle" is read as the pilot gate computes it: every tracked rotational coordinate, the pelvis's three
  rotations included. The untracked patellar couplers are left out. The earlier conditions stay: convergence, and
  pelvis residuals within Hicks et al. (2015).
- **2. Contact penetration:** each solve's maximum contact penetration is reported as a figure. That is the deepest
  any contact sphere reaches below the floor, over the solution's time points. It is not part of validity.
- **3. Every solve:** the validity check runs on every solve in the batch, not only the pilot.
- **4. Reporting:** invalid solves are reported as not evaluated, never as passing. The results state how many
  subjects and trials were evaluated per arm.
- **5. A minus B** is computed only on trials valid in both arms.
- **Unchanged:** the settings, the pilot gate (a check of the settings before the batch), the plate-coverage rule,
  H1, H2 and their thresholds.
- **In the code:**
  - `foot_models/dynamic_summary.py` applies items 1–3 to every solve, with the same tracking check as the pilot gate;
  - `foot_models/dynamic_metrics.py` applies items 4–5.

  The solver code (`dynamic_track.py`) is unchanged, so solves already running or finished are not redone.

**Amendment 6, to item 2, the dynamic comparison (2026-11-08).** Decided by the owner before any dynamic result was
compared with the force plates. Amendments 4 and 5 above stay as written; this changes the residual limits of the
validity rule.
- **1. Residual limits:** the pelvis residual limits use the subject's body weight, from the recorded mass, in place
  of the solution's own peak external force:
  - residual forces at most 5 % of body weight;
  - residual moments at most 1 % of the centre-of-mass height times body weight.
- **2. Reason:** the solution's own peak made the limit depend on the solution. With settings v1, arm A's pilot
  solution had its feet about half a metre into the floor, and its force limit came out at 3.5 MN. Body weight is
  known before the run and uses no force data. The new limits are slightly stricter than Hicks et al. (2015), because
  a squat's peak force exceeds body weight.
- **3. Reporting:** the summary reports each solve's residuals, the old limit and the new one.

  Read as: the recorded mass is `sessionMetadata.yaml`'s `mass_kg` (it agrees with the scale setup's in all 10
  subjects), times the models' gravity, 9.80665 m/s². The centre-of-mass height is unchanged from amendment 4: the
  solution's own, at the window's first time point.
- **Unchanged:** convergence and tracking (amendment 5), the penetration figure, amendment 5's reporting, the
  settings, the pilot gate, the plate-coverage rule, H1, H2 and their thresholds.
- **In the code:** `foot_models/dynamic_summary.py` applies the limits to every solve, and
  `foot_models/dynamic_metrics.py` selects with that validity. The solver code is unchanged, so solves already
  running or finished are not redone.

**Amendment 7, to item 2, the dynamic comparison: a stop rule (2026-11-09).** Decided by the owner after the
settings v2 pilot stopped, and before any dynamic result was compared with the force plates. Amendments 4–6 above
stay as written.
- **Stop rule:** if arm A fails the pilot gate under settings v3, the dynamic comparison stops there and the result
  is reported to the owner. No further settings version is tried. The rule is checked by 2026-11-11 and owned by
  the owner (`plan/nodes/sole-forceplate-dynamic.md`).
- **The owner's options then:**
  - an amendment to the contact itself;
  - reporting arm A as not solvable with the assumed contact (v1);
  - pausing the dynamic stage until the coupon test (the sensor film's measured response).
- **Recorded with it:** arm A did not converge in the v1 or the v2 pilot (3000 iterations each).
- **Unchanged:** the pilot gate (both arms must pass before the batch), validity (amendments 5 and 6), the
  plate-coverage rule, H1, H2 and their thresholds.

**Metrics and thresholds.** The quasi-static thresholds were **agreed on 2026-11-05, before any data was
downloaded or opened**, as a first attempt. They may be revised only before the force data is opened; a revision
after that is reported as one, beside the original result.

| Metric | Threshold | Status |
|---|---|---|
| Vertical force, quasi-static phases, RMS error | ≤ 5 % of body weight | Agreed |
| Centre of pressure, forward–backward, RMS error | ≤ 10 % of foot length (heel-to-toe marker distance) | Agreed |
| Left/right share of vertical force, RMS error | ≤ 5 percentage points | Agreed |
| Dynamic simulation, peak vertical force, error | ≤ 10 % of body weight | Proposed; to be agreed before the dynamic experiment |
| Dynamic simulation, centre-of-pressure path, RMS error | ≤ 15 % of foot length | Proposed; to be agreed before the dynamic experiment |

**How the quasi-static metrics are evaluated.** Written on 2026-11-05 with the thresholds, before any data was
opened:
- **Trials:** quiet-standing trials, if the dataset has them, and squats. Sit-to-stand is left out of the
  quasi-static check, because the chair carries part of the weight.
- **Quasi-static frames:** chosen from the kinematics alone, never from the forces. These are frames where the
  whole-body centre of mass, from the dataset's inverse kinematics and the subject's model, accelerates at less
  than 0.1 m/s² (positions low-pass filtered at 6 Hz), in stretches of at least 0.2 s.
- **Model:** each subject's scaled model from the dataset, as distributed, with the virtual sole and the assumed
  contact (v1). If the adapter refuses that model, stop and report; no workaround without the owner's decision.
- **Foot length:** the heel-to-toe marker distance in the subject's static trial. The marker names are taken from
  the dataset's documentation.
- **Left/right share:** evaluated only in trials where each foot is on its own plate.
- **Per subject:** each metric is the RMS error over all of that subject's quasi-static frames.
- **Pass rule:** a metric passes only if every subject is within its threshold. Each subject's value, the median
  and the range are reported, whether it passes or not.
- **Nothing is fitted** to the measured forces, so every subject is a test subject. If any parameter is later
  fitted, the subjects are split before that, and the fitted ones are reported apart.

**Amendment 1, to the "Model" rule (2026-11-06).** Decided by the owner before any force data was opened. The
rule above stays as first written.
- **Reason:** `sole_sim.py` refused every subject's distributed model
  (`OpenSimData/Mocap/Model/LaiArnoldModified2017_poly_withArms_weldHand_scaled.osim`). The models have no foot
  contact spheres, and the adapter finds the heel point and the plantar plane from them.
- **Change:** the distributed model is used unchanged, except that foot contact spheres are added by OpenCap's
  own rule, as `generate_model_with_contacts` in opencap-processing's `utilsProcessing.py` adds them (commit
  72b5416):
  - six spheres per foot, radius 0.032 m, on calcn and toes, at its reference locations;
  - the locations scaled by each foot body's geometry scale factors, with the height left unscaled;
  - one ground half-space, with that function's contact parameters.
  There is no patella-mass change and no other adjustment.
- **Effect:** the sole is then added as planned, with the assumed contact (v1), and it replaces these spheres.
  They only locate the sole, so OpenCap's contact parameters do not enter the results. Nothing is fitted to the
  measurements.

**Amendment 2, to the metrics, trials and pass rule (2026-11-06).** Decided by the owner before any force data was
opened. The rules above stay as written; this settles what they left open.
1. **Forward–backward centre of pressure:** the combined centre of pressure of both feet. The measured one (both
   plates together) is compared with the model's, along the model's forward axis, as a fraction of the subject's
   mean foot length (the mean of the left and right heel-to-toe distances). The model places each foot's forward
   centre of pressure under the centre of mass by convention, so per-foot values are not evaluated.
2. **Quiet standing:** inverse kinematics is run on each subject's `static1` trial from its markers, because the
   dataset has none for it. It uses the subject's distributed model and the same settings, marker set and
   weights as the dataset's own squat inverse kinematics, with no force data. The plan's frame rule is then
   applied to it as to the squats. The frames each subject gains are reported.
3. **Left/right share:** separate force channels per foot in the dataset's inverse-dynamics setup are taken to
   mean that each foot stood on its own plate.
4. **Subjects without quasi-static frames,** if any remain, are reported as not evaluated, not as passing.

**Amendment 3, to the vertical-force metric and the reporting (2026-11-06).** Decided by the owner before any force
data was opened. The rules above stay as written.
1. **Vertical force:** the metric uses the combined vertical force of both feet. The measured value is both plates
   together; the model's equals body weight by construction. This metric therefore tests only the body model's
   mass and the quasi-static assumption, not the foot model. Per-foot loading is covered by the left/right share
   metric, so per-foot vertical force is not evaluated.
2. **Secondary reporting** (descriptive, not pass/fail): each of the three metrics is also reported per subject for
   the `static1` frames and the squat frames separately. Pass/fail stays on the pooled per-subject values, as fixed
   above.

**Result of the quasi-static check (2026-11-06; `foot_models/results_forceplate_2026-11-06.json`).**
- **How it was computed:** as pre-registered in the rules and amendments 1–3 above, by
  `foot_models/forceplate_metrics.py`. Each subject's predictions were first checked against the sha256 pushed in
  9b4c934, before any force data was opened. Nothing was fitted or tuned.
- **Data:** 10 subjects, 6,142 quasi-static frames, all solved. The model uses the assumed contact (v1) and the EU 42
  sole scaled to each foot.

| Metric (pooled, per-subject RMS error) | Threshold | Median | Range | Subjects outside | Result |
|---|---|---|---|---|---|
| Vertical force, both feet combined | ≤ 5 % of body weight | 4.32 % | 0.39–47.24 % | 6, 9, 10 | **Fail** |
| Forward–backward centre of pressure, combined | ≤ 10 % of foot length | 2.85 % | 0.97–6.67 % | none | **Pass** |
| Left/right share of vertical force | ≤ 5 points | 7.67 | 0.91–56.42 | 2, 4, 5, 7, 9, 10 | **Fail** |

- **Plate assignment in `static1` (found after the data was opened).** Three subjects did not stand with one foot on
  each plate:
  - subjects 2 and 10: the right plate carries nothing, and the left carries 101 % and 94 % of body weight;
  - subject 9: the left plate carries nothing, and the plates together carry 52 %, so one foot stood off the plates.
  These trials give the largest errors: `static1` share errors of 56, 44 and 34 points (subjects 2, 10, 9), and
  subject 9's `static1` vertical error of 48 %.
  In every squat trial, both plates carry load. Amendment 2 inferred one plate per foot from the dataset's
  inverse-dynamics setups, and those exist only for the squats.
- **The result stands as computed,** with `static1` included. Any revision is the owner's to decide, and it would be
  reported beside this result.
- **Squats alone (descriptive; 7 subjects, as 2, 4 and 11 have no squat frames):**
  - vertical force 0.30–6.43 %, with 3 subjects outside (3, 6, 10);
  - centre of pressure 2.34–6.35 %;
  - share 1.85–5.84 points, with 2 subjects outside (7, 10).
  So without `static1`, the vertical force and the share would still fail.
- **What the passing metric tests.** The centre-of-pressure metric tests the body model's centre of mass, not the
  sole's contact law, as stage A says. In every subject the measured centre of pressure lies ahead of the model's,
  by 0.7–6.7 % of foot length on average (descriptive).
- **What the vertical force reflects.** Where both feet are on the plates, they weigh 4–6 % more than the model's
  body weight in subjects 3, 5, 6 and 8, and 6 % less in subject 10, in standing and squats alike. So this metric
  reflects the body model's mass, not the foot model.

**Post-hoc analysis (2026-11-06; `foot_models/results_forceplate_posthoc_2026-11-06.json`).**
- **Not pre-registered.** The owner defined it after the force data had been seen. It stands beside the result
  above, which stays as computed and remains the result of the pre-registered check.
- **Code:** `foot_models/forceplate_posthoc.py`, which reuses the per-frame functions of `forceplate_metrics.py`
  unchanged.

1. **Plate coverage.** A trial is left out if the right or the left plate carries less than 1 % of body weight on
   average over its quasi-static frames. The rule uses only the measured plate loads, never the model's
   predictions.
   - It removes three trials: the `static1` trials of subjects 2, 9 and 10, each with one plate at 0 %.
   - Every other trial has at least 34.9 % on each plate (the lowest is subject 7's asymmetric squat).
   - Subject 2 is then left without frames and is not evaluated (amendment 2). A metric can therefore pass only
     among the 9 subjects evaluated.

   | Metric (pooled, per-subject RMS error) | Threshold | Median | Range | Subjects outside | Post-hoc result | Pre-registered |
   |---|---|---|---|---|---|---|
   | Vertical force, combined | ≤ 5 % of body weight | 4.20 % | 0.39–5.98 % | 6, 10 | Fail | Fail |
   | Forward–backward centre of pressure, combined | ≤ 10 % of foot length | 3.20 % | 1.34–6.67 % | none | Pass among the 9 evaluated | Pass |
   | Left/right share | ≤ 5 points | 4.98 | 0.91–9.91 | 4, 5, 7, 10 | Fail | Fail |

2. **Body mass.** For every subject, the model's total mass equals the mass recorded in the dataset. The recorded
   mass is the same in `sessionMetadata.yaml` and in the scale setup.
   - Over the kept frames, the plates weigh subjects 3, 5, 6 and 8 4.2–6.0 % above that mass, subject 11 2.2 %
     above, and subject 7 within 0.4 %.
   - They weigh subjects 4 and 10 4.1 % and 5.9 % below it. Subject 10's figure is from its squats, because its
     `static1` is left out.
   - Subject 9 is weighed from its squats only, 0.9 % above.
   - **The vertical-force failures follow that gap.** In every evaluated subject, the vertical-force RMS error equals
     the gap between plate weight and recorded mass to within 0.1 points. The two subjects outside 5 % are the two
     whose plates weigh them more than 5 % off their recorded mass: subject 6 (+6.0 %) and subject 10 (−5.9 %).

3. **Why the left/right share fails** (a further post-hoc diagnostic, defined by the owner after the data was seen;
   `foot_models/results_forceplate_lateral_posthoc_2026-11-06.json`, from `foot_models/forceplate_lateral.py`).
   - **Frames:** those of the kept trials.
   - **Axis:** sideways, perpendicular to the model's forward axis in the floor plane.
   - **Method:** by the lever rule, a share error splits into two parts. One comes from the offset between the
     measured combined centre of pressure, which lies under the true centre of mass, and the model's centre of
     mass. That offset is the body model's or the inverse kinematics' error. The other part is a remainder, from
     where each foot's centre of pressure sits sideways in the model compared with the plates.
   - **The centre-of-mass offset is small:** 1.2–5.9 mm RMS across the 9 subjects. By the lever rule that is worth
     0.4–2.2 points of share.

   | Subject | Centre-of-mass offset (mm RMS) | Share error (points RMS) | From the offset | Remainder | Foot centre of pressure, model − measured (right / left, mm) |
   |---|---|---|---|---|---|
   | 4 | 1.15 | 8.46 | 0.43 | 8.81 | −35 / −10 |
   | 5 | 5.90 | 6.89 | 2.20 | 9.05 | −13 / −36 |
   | 7 | 3.92 | 9.91 | 1.09 | 10.52 | −10 / −43 |
   | 10 | 1.68 | 5.84 | 0.51 | 5.99 | +19 / +19 |

   (Sideways positions are positive towards the subject's right.)
   - **So the share failures in subjects 4, 5, 7 and 10 are not explained by the centre of mass.** The body model and
     the inverse kinematics put it within a few millimetres of where the plates do.
   - **The failures come from the foot side,** from where each foot's centre of pressure ends up sideways. This
     diagnostic cannot separate the possible causes:
     - the sole's placement on each foot (registration and scaling);
     - the inverse kinematics' foot positions;
     - the contact's sideways load split within each sole.
   - **A pattern, descriptive only:** in 6 of the 9 subjects, both feet's model centres of pressure lie to the left
     of the measured ones. That shifts the share while the centre of mass stays put.

**Protocol:**
- Every result names the dataset version and file hashes, the pipeline commit and the contact model (assumed v1
  or native).
- A result outside a threshold is reported as such, not re-tuned until it passes.
- The downloaded data stays on the workstation, outside the repository. Only aggregate results are committed.

**Practical:**
- The 2.9 GB download did not fit in the working environment used on 2026-11-04 (about 1.1 GB free).
- Stage A ran on the lab laptop (`workstation/README.md`) on 2026-11-06, with the owner's copy of the dataset (see
  "Copy of OpenCap LabValidation used for stage A" above). The data stays on that machine, outside the repository.

**Reference equipment, if the project later measures its own data** (listed only; nothing to buy or contact):
- **Laboratory force plates** (AMTI, Bertec, Kistler), as found in university gait laboratories.
- **Consumer balance boards.** Studies have compared them with laboratory plates for quiet-standing centre of
  pressure; that literature was not checked here. They are no substitute for a laboratory plate in dynamic
  tasks.

## B. Regional plantar pressure, barefoot (planned separately)

**Candidate datasets:**

| Dataset | Content | Terms | Notes |
|---|---|---|---|
| UNB StepUP-P150 (Larracy et al. 2025), *Sci Data* [10.1038/s41597-025-05792-1](https://doi.org/10.1038/s41597-025-05792-1) | 150 people, over 200,000 footsteps on a pressure walkway (240 × 720 sensors); barefoot and shod; several speeds | **Not yet confirmed** | Barefoot walking pressure maps. No synchronised kinematics |
| CAD WALK (Booth et al.), [Zenodo record](https://zenodo.org/records/3521486) | 55 healthy controls plus a patient set; footscan plates at 500 Hz | **Not yet confirmed** | Walking only |

**Not found:** a public dataset of static, barefoot standing pressure with synchronised kinematics.

**Method:**
- Register the measured pressure maps to the sole's 16 regions using the foot outline.
- Compare regional shares and the centre-of-pressure path across stance, for groups, not single steps.
- Because these datasets have no kinematics, compare against the controlled-loading results at matched centres
  of pressure. This is a comparison of patterns, not of a predicted movement.

**Before stage B means anything:** converge the contact spacing. The regional shares still change with it by
up to 7.9 points (`FOOT_MODELS.md`, section 5.3, a discretisation sensitivity).

**Reference equipment, for later own measurement:** pressure platforms (Novel emed, Tekscan MatScan, RSscan
footscan), as found in gait laboratories.

## C. Foot–insole contact (planned separately)

**Candidate data:**
- Grouvel et al. (2023): 16-sensor insoles, synchronised with force plates and motion capture; walking and
  squats.
- A treadmill study with force plates and in-shoe pressure under different insoles (Mendeley Data
  [10.17632/hfz543gjc7.1](https://doi.org/10.17632/hfz543gjc7.1)); terms **not yet confirmed**.

**Needs first, none of it done:**
- footbed and shoe layers in the simulation;
- the sole's own measured response (the coupon test);
- a way to compare a 16-sensor commercial insole's layout with the sole's 16 regions.

**Reference in-shoe systems** (listed only): Novel pedar, Tekscan F-Scan, Moticon OpenGo.
