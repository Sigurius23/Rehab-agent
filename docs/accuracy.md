# Accuracy — design priority #1

> **"Full accuracy of the human body in the digital twin" is the key requirement
> for this project.** Convenience (a phone camera and a plausible avatar) is
> explicitly *not* the goal. Every architectural choice is judged against this
> document, and every output of the twin must carry its measured error with it.

## What "full accuracy" actually means — 6 separate claims

A twin is not "accurate" or "inaccurate" in general. Each layer below is a
separate claim that must be separately built and separately validated:

| # | Layer | "Accurate" means | How it is obtained in this catalog | How it is verified |
|---|---|---|---|---|
| 1 | **Bone geometry** | This person's actual bone shapes, lengths and alignment — not a scaled average | MRI/CT → `TotalSegmentator` segmentation → patient bone meshes. TotalSegmentator robustly segments >100 anatomical structures in CT and MR images [1](https://github.com/wasserth/TotalSegmentator); custom classes via `nnU-Net` [1](https://github.com/MIC-DKFZ/nnUNet); clinician review/correction in `3D Slicer` [2](https://github.com/Slicer/Slicer/blob/main/Docs/user_guide/image_segmentation.md) | Dice / surface-distance vs expert-corrected segmentation in 3D Slicer |
| 2 | **Joint centres & axes** | Rotation centres/axes from this person's anatomy + functional movement, in mm | Patient-specific OpenSim models: `msk-PIPE` / thin-plate-spline MRI workflow / `msk-STAPLE` | Landmark/joint-centre error (mm) vs imaging |
| 3 | **Surface shape** | The external body surface, in mm, in a known pose | Tier A: imaging + scan registration. Lower tiers: `SHAPY`/`ECON` from photos (labelled lower accuracy) | Point-to-surface error vs 3D scan |
| 4 | **Kinematics** | Joint angles over time, in degrees, per plane | Tier A live: multi-camera + IMU fusion. Lower tiers: markerless video (`GVHMR`, OpenCap, Pose2Sim) | RMSE per joint **and per plane** vs a reference system |
| 5 | **Muscle geometry & state** | Muscle attachment points, paths, volumes/PCSA and activation for this person | Imaging-derived attachments (`msk-PIPE`), EMG-informed calibration (`CEINMS`) | Muscle volume error vs MRI; force/moment validation vs dynamometer/force plates where available |
| 6 | **Soft tissue / internal anatomy** | Tissue distribution that deforms plausibly | `HIT` (internal tissues), `SOFA` (FEM deformation) | Research-grade only — no clinical claims at this layer yet |

### Why generic scaling is not enough (the evidence that forces Tier A)

Published MRI-based personalisation work found that generic-scaled models can
misplace joint centres by centimetres — in one reported individual the
generic-scaled knee centre sat **30–35 mm** above where the person's MRI femur
length allowed it to be — and that imaging-based geometry materially changes
estimated joint loading [2](https://pmc.ncbi.nlm.nih.gov/articles/PMC13029800/).
A posture/muscle product built on a skeleton that is centimetres wrong in
places is a visualisation, not a twin. Hence:

## Accuracy tiers — and what each tier is *allowed* to claim

| Tier | Construction | Permitted uses |
|---|---|---|
| **A — Imaging-personalised (THE target)** | MRI/CT segmentation → patient bones/joints/muscle attachments → personalised OpenSim model → functional joint calibration → live tracking registered to that model | Posture correction, muscle-effect simulation, exercise prescription support, haptic/exo assistance targets |
| **B — Scan/photo-personalised** | 3D body scan or photos (`SHAPY`/`ECON`) → SMPL-X shape → `SKEL`/`OSSO` skeleton → scaled OpenSim | Progress visualisation, gross posture screening — **every number labelled with Tier-B error** |
| **C — Video/IMU only** | Markerless video or IMU suit, generic model | Session adherence, rep counting, gross movement review. **No anatomical claims.** |

Rules:
1. **The tier travels with the data.** Every session file, chart and patient-facing
   statement records which tier produced it.
2. **No Tier-C number may drive a correction, a muscle-underdevelopment claim,
   or exoskeleton torque.** Ever.
3. "Full accuracy" marketing language may only be used for Tier-A outputs that
   passed the validation gates below.

## Why live tracking also needs an accuracy budget

Even the best-studied markerless path is not error-free: OpenCap reported a
mean absolute joint-angle error of **4.5°** against marker-based motion capture
and force plates [8](https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1011462)
— respectable for screening, but validation reviews report much larger errors
in harder planes, e.g. trunk transverse-plane RMSE around **14–19°** [4](https://pmc.ncbi.nlm.nih.gov/articles/PMC13468529/).
Posture lives exactly in those hard planes. Therefore:

- Per-joint, per-plane error must be measured **on our own setup, on the
  movements we actually prescribe**, before any feedback rule uses that joint/plane.
- Transverse-plane trunk/hip-rotation feedback from a single camera is
  **prohibited until validated** on our pipeline.
- Even the reference standard has limits (skin-marker artefact vs bone can
  reach ~8° RMSE at the knee [8](https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1011462)) —
  so the goal is a *quantified, small, known* error, not a claim of zero error.

## Project acceptance targets (engineering targets, not clinical standards)

To be confirmed with the clinical lead and proven per movement before use:

| Quantity | Tier-A target |
|---|---|
| Joint-centre location vs imaging | ≤ 5 mm |
| Bone surface (segmentation vs expert-corrected) | ≤ 2 mm mean surface distance |
| Primary (sagittal) joint angles vs reference | ≤ 3° RMSE |
| Frontal-plane joint angles vs reference | ≤ 5° RMSE |
| Transverse-plane angles | reported separately; no feedback use until ≤ 5° RMSE is demonstrated |
| Muscle volume vs MRI segmentation | ≤ 10 % per major muscle group |

## Tier-A onboarding pipeline (per person, once + periodic refresh)

```
MRI/CT (DICOM)
  → 3D Slicer (import, clinician review station)
  → TotalSegmentator (bones/muscles/organs) [+ nnU-Net for custom structures]
  → patient bone/muscle meshes (+ Scalismo shape-model fitting if imaging is sparse)
  → msk-PIPE / TPS-MRI workflow / msk-STAPLE → personalised OpenSim .osim
      (patient joint centres/axes, muscle attachments, wrapping, segment inertials)
  → functional calibration movements (joint axes refined from motion)
  → CEINMS calibration (if EMG collected: per-person muscle parameters)
  → twin registered: live capture (multi-cam EasyMocap/Pose2Sim + SlimeVR/IMU via LSL)
      is solved against THIS model, not against a generic SMPL body
  → validation report stored with the twin (errors per layer above)
```

Repos: [TotalSegmentator](https://github.com/wasserth/TotalSegmentator) ·
[nnU-Net](https://github.com/MIC-DKFZ/nnUNet) ·
[3D Slicer](https://github.com/Slicer/Slicer) ·
[Scalismo](https://github.com/unibas-gravis/scalismo) — a library for statistical shape modelling and model-based image analysis [1](https://github.com/unibas-gravis/scalismo) ·
[msk-PIPE](https://github.com/PatrikMrnka/msk-PIPE) — an automated pipeline that converts CT/MRI scans into parameterised OpenSim models through segmentation, meshing and muscle-attachment extraction [6](https://github.com/PatrikMrnka/msk-PIPE)

## Where `pipeline/` stands per layer

The person model (`docs/person-model.md`) records this per person; `person show` prints it.

| # | Layer | Built | Tier today | Missing for the next tier |
|---|---|---|---|---|
| 1 | Bone geometry | generic bones scaled once in a calibration session and reused (`person build`, `process --person`); an imaging model can be attached with its provenance record (`person attach`) | C | imaging → personalised model (msk-PIPE/STAPLE); or SKEL/OSSO bones fitted inside a measured surface (needs their registered model files) |
| 2 | Joint centres | scaled with the bones; markers placed per session | C | imaging, or functional joint-centre calibration |
| 3 | Surface shape | not built yet (body shape from depth is in progress) | — | a 3D scan or tape measurements of the person to measure its error |
| 4 | Kinematics | per session, validated per joint × plane against a reference | per validation | marker mocap for the person and exercise |
| 5 | Muscle | Rajagopal leg muscles, capacity scaled to measured height and mass (`capacity.py`); dynamometry for tested groups (`strength`) | C | muscle volumes from MRI; EMG calibration (CEINMS) |
| 6 | Soft tissue | not modelled | — | — |

## Red lines

- No muscle "underdevelopment" statement from surface shape (SMPL betas) alone —
  it requires Tier-A muscle geometry and/or strength/EMG evidence. Strength
  evidence can be added today with `rehabtwin strength` (dynamometer torques →
  calibrated capacities + limb symmetry index); it supports "weaker in this test"
  and a capacity-scaled simulation, not a statement about muscle size. Body-size capacity scaling
  (`capacity.py`) is a population regression from height and mass, not evidence about this person.
- No "corrected posture" target generated from a generic skeleton; correction
  targets are computed on the patient's own joint geometry and range limits.
- No exoskeleton assistance profile derived from an unvalidated tier (`muscles --assist/--passive`
  below Tier A only runs with `--illustrative` and is labelled a design-space bound).
- The tier is granted by evidence, not by a flag: Tier B/A needs a model-provenance record bound to
  the session's person and model (`rehabtwin/tiers.py`); only marker-mocap validations open feedback.
- If a layer has not been validated for a given person, the twin must *display
  that gap* ("muscle layer: generic, not yet personalised") instead of hiding it.
