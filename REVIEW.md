<!-- SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors -->
<!-- SPDX-License-Identifier: MIT -->

# Design review, 2026-11-16

An outside review of the project, by a fresh agent session on the lab laptop, working on the local branch
`feat/sensor-sole` at `cbed174`. It changed nothing. The brief left the owner's budget, laptop time and commercial
intent blank, so the reviewer assumed all three undecided. Kept here as written; what the project does with it is
in `plan/` (commit `b216334` on branch `review-followups`).

**Summary.** The numbers in the notes are honest, but the project is building the wrong things: on the same data,
OpenCap's own output is about three times closer to motion capture than any route built here, and the sole work
rests on no measurement at all.

## What was checked

Every headline figure tested in the notes matches its file in `validation/results/`:
- Pilot: 26 of 36 cells differ, 20 of them larger against motion capture.
- Control: 6.32° on one trial; 4.80° on all subjects from 69 of 160 trials; 4.57° at zero lag.
- Benchmark: the run and evaluated counts, the passing cells, and the stop count of 7 in rounds 0, 1 and 2.
- Force plate: centre-of-pressure median 2.85 %, vertical 4.32 %, share 7.67 points.

## 1. Where the architecture is wrong for the goal

- **The central bet is untested** (inferred). "Phone-only once the twin exists" assumes a personalised model makes
  one camera good enough. Nothing in `plan/` tests that. Every one-camera result used a generic or height-scaled
  body, and missed by 15–30° at the hip (`t-kin-labvalidation`).
- **It is an offline batch pipeline** (checked). HSMR takes about 7 minutes for 8 seconds of video, and `process`
  about 20 seconds. `docs/architecture.md` has no real-time path, yet the goal drives feedback, a suit and an
  exoskeleton.
- **"Windows first" is absent** (checked). The only Windows material is `docs/kinect-v1.md`. Everything measured ran
  on Ubuntu with a CUDA build chain.
- **Timing is not solved** (checked). The two post-hoc checks show neither frame order nor timestamps aligns the
  videos with the motion capture. At lag 0 the knee error is roughly double the best case.

## 2. What to replace with existing tools

- **Multi-camera:** use OpenCap's pipeline (opencap-core) or Pose2Sim with HRNet or RTMPose, not MediaPipe
  triangulation.
  - Checked: `kin_control_opencap_all_subjects*.json` gives OpenCap 4.2–5.1° mean absolute error on this dataset,
    and two cameras are enough (4.57°).
  - Checked: the routes built here give 11–36° RMSE on sagittal cells.
  - The metrics differ (mean absolute error against RMSE), but not by a factor of three.
- **Phone-only:** choose none yet. The benchmark supports only trunk lean and frontal pelvis from one camera. HSMR is
  best at pelvis tilt (7°) and worst at the knee.
- **Licences** (checked in the clones): SKEL, SMPL and OpenCap Monocular are non-commercial, and SAM4Dcap has no
  licence. If the project might go commercial, HSMR and OpenCap Monocular are dead ends.
- **Sole:** buy a validated insole before designing one. `hardware/sensor-sole/README.md` says nothing has been
  fabricated or measured.

## 3. Conclusions the data doesn't support

- `docs/validation-results.md` section 4 still says the augmenter "fixes" the pelvis and that the data "supports"
  three phones 40° apart. `docs/hardware.md` line 63 repeats this. That was agreement with OpenCap on one trial;
  section 4b and the benchmark contradict it.
- "Back-end verified" (`docs/roadmap.md`) rests on synthetic data with 105 dense markers.
- The benchmark headline is mostly drop jumps: 51 of the 84 evaluated five-camera trials.
  - Squat-only is much better. Computed by the reviewer from the round-2 file, post hoc: with five cameras and the
    augmenter, the knee is 11.5° at lag 0 and 5.3° at the best case.
  - The notes don't say this.
- `t-fp-cop` "passed" says nothing about the sole. `VALIDATION_PLAN.md` line 50 admits the centre of pressure is
  set by the centre of mass.
- The 3° target for every subject is stricter than the published validated tool achieves, so "failed" was close to
  certain in advance (inferred).
- LabValidation is no longer fresh. Two fix rounds and four post-hoc analyses have used it.

## 4. What is over-built, and what to stop

Checked sizes: 34,500 lines of Python, 171 plan notes, 38 items waiting on the owner, a 110-repo catalogue, and no
recording of the owner's own.
- Stop the sole work: the eight KiCad boards, the foot-model comparison, the spacing study and the Moco work. All
  rest on an assumed contact law.
- Stop the downstream modules: cues, the suit bridge, exoskeleton sizing, muscles and joint load. They are gated
  behind a validation that failed.
- Stop post-hoc analysis of this dataset.

## 5. Three highest-value next steps

1. Run the back end on OpenCap's own markers. They are in the zip under `MarkerData/Video`. This separates
   pose-detector error from model and IK error in about a day.
2. Test the central bet on existing data. Rerun one-camera IK with each subject's motion-capture-scaled model as "the
   twin". If the hip error doesn't drop sharply, phone-only needs a different design.
3. Record one person yourself, on Windows. Use phones with a jump or clap for sync, plus one reference. Decide
   commercial or not first, because that fixes the front-end choice.
