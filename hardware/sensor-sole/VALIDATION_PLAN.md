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

**Protocol:**
- Every result names the dataset version and file hashes, the pipeline commit and the contact model (assumed v1
  or native).
- A result outside a threshold is reported as such, not re-tuned until it passes.
- The downloaded data stays on the workstation, outside the repository. Only aggregate results are committed.

**Practical:**
- The 2.9 GB download did not fit in the working environment used on 2026-11-04 (about 1.1 GB free). The lab
  workstation is the proposed place to run it (`workstation/README.md`); nothing has been downloaded yet.

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
