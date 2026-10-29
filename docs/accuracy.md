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

## Anatomy-audit integration (2026-10-28, Batches 1–8 → schema)

The 202-issue anatomy audit (`anatomy-issues-checklist.md`,
`anatomy-audit-batch1..8`) is now folded into the twin manifest
(`schemas/twin-manifest.schema.json`). Each mechanism below names the
manifest block that carries it; all blocks are imaging- or
clinician-sourced — none may be populated from camera/LiDAR inference.

| Mechanism (audit batches) | Manifest block | Rule |
|---|---|---|
| Spinopelvic parameter layer (Batch 1) | `spinopelvic_parameters` | PI/PT/SS/LL/TK/SVA from EOS/CT/MRI only |
| Bony torsion & alignment — femoral anteversion, neck-shaft, tibial torsion, HKA, segment lengths, carrying angle (Batches 2/6) | `limb_alignment` | Imaging-measured (Torsion-Tool class); personalises joint axes |
| Muscle-parameter pipeline — weakness / contracture / reflex-gain as three separately fitted groups (Batches 4/7) | `muscle_parameters` | MRI volumes + fat fraction + strength; reflex gains only from instrumented spasticity assessment, never video |
| Bone quality (Batch 6) | `bone_quality` | DXA/QCT/clinical; `exo_torque_derating_factor` is a safety input (D-05) |
| Implants, limb prostheses, orthoses (Batches 2/4/6/8) | `devices_and_prostheses` | Device modelled as body segments with ROM envelope |
| Safety flags & representability (Batches 6/8) | `safety_flags` | Clinician-set only (atlantoaxial instability, bone fragility, unrepresentable anatomy e.g. syndactyly); the twin never sets/clears them |
| Time-varying body state (Batch 4) | `body_state` | Pregnancy trimester parameter sets; older-adult muscle parameters |
| Breathing layer (breathing programme) | `breathing` in `schemas/session.schema.json` | Diaphragm labelled `inferred` unless ultrasound-measured; asynchrony = screening flag (D-03) |

Audit honesty labels that bind all tiers: scapula pose is
**model-inferred, never measured** (Batch 3); hands the parametric
model cannot represent must be flagged, not silently drawn (Batch 6);
Janda-type patterns are **labels over measured metrics, not
diagnoses** (Batch 4).

## Where `pipeline/` stands per layer

The person model (`docs/person-model.md`) records this per person; `person show` prints it.

| # | Layer | Built | Tier today | Missing for the next tier |
|---|---|---|---|---|
| 1 | Bone geometry | generic bones scaled once in a calibration session and reused (`person build`, `process --person`); or scaled to SKEL's joint centres for the person's SMPL surface or height and mass (`person bones`, `skel_bones.py`; one synthetic depth frame: within 1.1 cm of the true body's SKEL bones); an imaging model can be attached with its provenance record (`person attach`) | C | imaging → personalised model (msk-PIPE/STAPLE); imaging of the same people to check SKEL's joint centres |
| 2 | Joint centres | scaled with the bones; markers placed per session | C | imaging, or functional joint-centre calibration |
| 3 | Surface shape | SMPL-X fitted to standing Kinect depth frames (`person shape`, `shape.py`), checked against measured height and mass; synthetic BEDLAM2: height ±1.4 cm, mass ±5.2 % | C | a 3D scan or tape measurements of a real person to measure its error |
| 4 | Kinematics | per session, validated per joint × plane against a reference | per validation | marker mocap for the person and exercise |
| 5 | Muscle | Rajagopal leg muscles: force from MRI/CT volume and fat fraction where imaged (`person muscles`), else each leg's volume from a DXA scan (`person dxa`), from age, sex, height and mass, or from height and mass (`capacity.py`); dynamometry for tested groups (`strength`) | C (B/A once all leg muscles are imaged) | imaged muscle geometry (attachments, paths); EMG calibration (CEINMS). Tested on 15 adults' thigh MRI + dynamometry: measured volume r = 0.86 with strength, the regression 0.44 (`docs/person-model.md`) |
| 6 | Soft tissue | regional fat and lean mass from a whole-body DXA (`person dxa`, `dxa.py`); sets the segment masses of the muscle model | B with a DXA scan (A reviewed); — without | tissue deformation (research-grade only) |
| — | Bone density | DXA/QCT result and screening category (`person bone`, `bone.py`); shown on device and correction what-ifs; a clinician's `exo_torque_derating_factor` scales assistance what-ifs, and low density without one refuses them | measured | not in the OpenSim model; bone strength and fracture risk are not modelled |
| — | Joint alignment | manifest `limb_alignment` from imaging or a clinician (`person alignment`, `alignment.py`): knee HKA put into every session's model (synthetic genu valgum, synthetic truth only, no clinical validation: knee FPPA RMSE 6.7° → 0.8°); torsion and lengths stored. Standing frame estimated from the camera every session: screening only, never written to `limb_alignment` or the model | B/A from imaging; C clinical; camera estimate: estimated, uncertainty not yet measured | Torsion Tool (femur/tibia twist with muscle attachments); repeat sessions to measure the camera estimate's uncertainty; a real imaging comparison |
| — | Knee joint load | OpenSim Joint Reaction on the muscle stage (`joint-load`, `joint_load.py`): tibiofemoral compression per knee and what-ifs within one person (fat change from the DXA regional table, stronger groups); every peak carries whether it can be trusted (muscles at capacity, reserve share, the in-vivo band) | C: within-person changes only, never absolute | measured ground forces; contact points from imaging for a medial/lateral split; a patellar tendon that carries less than the full quadriceps force in deep flexion |
| — | Safety flags | manifest `safety_flags` recorded as the clinician gives them (`person safety-flags`, `safety.py`); active unless cleared; hold posture cues and assistance what-ifs over the whole flagged region | clinician record | — (the twin never sets, infers or clears one) |

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
- No powered assistance at a joint covered by an active `safety_flags`
  entry beyond its recorded restrictions; bone-quality derating
  (`bone_quality.exo_torque_derating_factor`) always applies. The pipeline
  doesn't interpret the restrictions text: it holds every posture cue and
  assistance what-if in the flagged region, and treats `suspected` and
  `not-assessed` like `confirmed` (fail closed).
- A camera estimate of standing alignment is labelled *estimated*, with
  "uncertainty not yet measured" until repeat sessions of the same person
  measure it; change against the person's own baseline is the primary signal.
  Beyond the screening threshold the prompt is "worth getting checked by a
  professional": a prompt never names an imaging test. Provenance (modality
  and date, e.g. "radiograph 2026-09-01") belongs in clinician-facing outputs
  (`qc.json`, cue summaries, reports); patient-facing text shows only the
  constant prompt (`alignment.CHECK_PROMPT`).
- A number from a synthetic test carries its caveat wherever it is quoted
  (synthetic truth, no clinical validation).
- No internal anatomy (bone shape, joint space, muscle quality,
  ligament state, neural drive, spasticity grade) inferred from
  camera/LiDAR — the anatomy audit's standing negative result.
- If a layer has not been validated for a given person, the twin must *display
  that gap* ("muscle layer: generic, not yet personalised") instead of hiding it.
