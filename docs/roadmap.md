# Roadmap

## Phase 0 — Meta-repo (this repo) ✅
Catalog the upstream repos (110 today), tier them, provide clone/list/validate tooling.

## Phase 1 — One honest end-to-end slice (weeks, not months) — 🟡 software done, measurement pending
Slice chosen: **video → SKEL → OpenSim** (`stacks/video-skel-opensim.md`, code in
`pipeline/`). It produces a scaled OpenSim model, joint angles, posture vs gravity,
QC, a validation report and an HTML report a clinician can open and disagree with.
- ✅ Back-end verified against synthetic truth (~1° joint angles, 0.35° trunk lean vs gravity).
- ✅ Real-video run (Pose2Sim demo): MediaPipe monocular fails every gate against 4 cameras →
  MediaPipe is a test front-end only (`docs/validation-results.md`).
- ⬜ HSMR/SKEL on the OpenCap LabValidation dataset vs marker mocap (needs the gated SKEL model + GPU).
- ⬜ One healthy volunteer, one exercise, recorded with the selected hardware and device gravity.
No patient data, no feedback generation yet.

Note: this Phase-1 slice is Tier C by construction (statistical body). The Tier-A
onboarding path (`docs/environments.md` install order: imaging → biomech) plugs into the
same back-end by swapping the OpenSim model in `pipeline/configs/`.

## Phase 2 — Measurement validation
Compare joint angles/ROM against a reference (goniometer, lab mocap, or OpenCap)
on scripted movements. Publish error per joint/movement inside this repo.
A repo graduates from `experimental`/`extended` to `core` only with a note here.

## Phase 3 — Clinician-authored feedback rules — 🟡 engine built, gated off until Phase 2 passes
`rehabtwin cues` (rule engine with faded feedback), `rehabtwin correct` (correction view) and
`rehabtwin muscles` (muscle effects) exist and run on recorded sessions. Below Tier A, or for
unvalidated joint/planes, they only produce labelled illustrations and `would_cue` logs.
Rule checks on measured outputs only (e.g. "knee flexion < target on 3/5 reps"),
clinician reviews/edits every patient-facing message. Log rule firings.

## Phase 4 — Simulation & assistance (optional track) — 🟡 first tools exist
`rehabtwin muscles` (estimated double-stance GRF → inverse dynamics → static optimisation)
gives muscle-group demand, weakness what-ifs and ideal-exo sizing (`--assist`). MyoSuite/SCONE
(predictive, RL) and Moco tracking with foot contact are the next fidelity steps.
MyoSuite/SCONE path: simulate muscle effort and assistive strategies in silico.
Nothing from this track reaches a patient without Phase 2-grade validation.

## Explicit non-goals (for now)
Diagnosis, automated treatment decisions, patient-facing unsupervised feedback,
and any use of gated model weights outside their license terms.
