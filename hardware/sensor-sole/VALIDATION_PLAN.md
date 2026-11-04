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

**Not usable for this:** the squat already used in the comparison (OpenCap's `squats1_videoAndMocap.mot`). Its
example folder has no force-plate data. An earlier pipeline output in the scratch area named `measured_grf`
holds **estimated** forces: its own record says "quasi-static double stance".

**What can be compared, and how:**
1. **Quasi-static (first).** For each subject, take the measured kinematics, put the pipeline's model in the
   posture, and use the posture-based balance task (`compare_feet.py`).
   - Compare the model's centre of pressure and vertical force with the force plates during quiet standing and
     the slowest part of the squat, where acceleration is small.
   - This tests the body model's centre of mass and the quasi-static assumption.
   - The centre of pressure is set by the centre of mass, so this does **not** test the sole's contact model.
2. **Dynamic (second, separate).** A muscle-driven tracking simulation (OpenSim Moco) of the squat and
   sit-to-stand, with the sole as the foot contact. The predicted ground force and centre of pressure over time
   are compared with the force plates. This is a different experiment from the passive, prescribed-COP control
   in `FOOT_MODELS.md`, and it will be reported separately.

**Metrics and thresholds,** to be agreed before any data is opened (proposed values):

| Metric | Proposed threshold |
|---|---|
| Vertical force, quasi-static phases, RMS error | ≤ 5 % of body weight |
| Centre of pressure, forward–backward, RMS error | ≤ 10 % of foot length (heel-to-toe marker distance) |
| Left/right share of vertical force, RMS error | ≤ 5 percentage points |
| Dynamic simulation, peak vertical force, error | ≤ 10 % of body weight |
| Dynamic simulation, centre-of-pressure path, RMS error | ≤ 15 % of foot length |

**Protocol:**
- Subjects split before any tuning; nothing tuned on the test subjects.
- Every result names the dataset version and file hashes, the pipeline commit and the contact model (assumed v1
  or native).
- A result outside a threshold is reported as such, not re-tuned until it passes.

**Practical:**
- The 2.9 GB download did not fit in the working environment used on 2026-11-04 (about 1.1 GB free). Where to
  run it is still to be decided.

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
