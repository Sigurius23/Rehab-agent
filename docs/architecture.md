# Architecture — Rehab Agent pipeline

## Design principle
No single repo in the catalog is a rehab agent. The agent is the **composition**:
a capture front-end, a body/skeleton reconstruction layer, a biomechanics layer,
and a feedback layer — with auditable intermediate files at every boundary so a
clinician (or a test) can inspect what the system believed at each step.

## Stages, inputs, outputs

| # | Stage | Typical inputs | Auditable outputs | Catalog repos (examples) |
|---:|---|---|---|---|
| 1 | Capture | webcam/phone video, RGB-D, 6×IMU | raw video, IMU streams, calibration | freemocap, opencap-core, record3d, scanner, TransPose |
| 2 | Pose / mocap | video, IMU | 2D keypoints, 3D joints, joint orientations | pose2sim, mamma, PIP/PNP, ViDiHand |
| 3 | Body model | 3D joints, images | SMPL/SMPL-X params (pose/shape), meshes | smplx, smplify-x, mmhuman3d, STAR, SUPR |
| 4 | Skeleton | SMPL params, meshes | biomechanical skeleton, joint centres/axes | SKEL, OSSO, HSMR, SKEL-CF, HIT |
| 5 | Biomechanics | skeleton + motion (+ forces) | joint angles, moments, muscle forces (`.mot`/`.sto`) | opensim-core, AddBiomechanics, pose2sim, SMPL2AddBiomechanics, nimblephysics |
| 6 | Muscle sim | OpenSim/MuJoCo model + task | muscle activations, assistance policies | myosuite, myo_sim, scone-*, musclemimic, PHC |
| 7 | Control / RL | sim + reward/task | control policies, exoskeleton assistance | depRL, loco-mujoco, sconegym, exo-plore |
| 8 | Visualisation | any stage output | reviewable 3D session, overlays, reports | aitviewer-skel, opencap-viewer, MuSkeMo, mpfb2 |

## Non-negotiable contracts
- **Every stage writes files, not just tensors** (video, keypoints JSON, SMPL `.npz`,
  OpenSim `.trc/.mot/.osim`) so results are reproducible and clinically reviewable.
- **Units, coordinate frames and joint definitions are recorded per file.** Most
  integration failures in this stack are frame/unit mismatches (SMPL vs OpenSim).
- **No stage silently imputes missing joints.** Missing/occluded data is flagged;
  rehab feedback on fabricated motion is a safety bug, not a feature.

## Two front-ends, one back-end
Camera (FreeMoCap/OpenCap/Pose2Sim) and IMU (TransPose/PIP/PNP/OpenSimLive) paths
converge at Stage 4–5: once you have a skeleton moving in OpenSim, assessment,
simulation and visualisation are shared. Pick the front-end per setting
(clinic = cameras, home = IMU) without rebuilding the back-end.

## Where an LLM/agent layer belongs
Only *after* Stage 5 outputs exist: summarising measured ROM/gait/torque trends,
turning clinician-authored exercise rules into checks, and drafting (never
auto-sending) patient feedback. The agent must cite the measurement file behind
every claim it makes.

## Implemented so far (`pipeline/`, package `rehabtwin`)

| Stage | Module / command | Notes |
|---|---|---|
| 1–2 Capture, pose | `adapters/hsmr_to_skelseq.py` (HSMR + SKEL), `adapters/mediapipe_pose.py` + `mp-mono` / `mp-multiview`, `vmc-posture` (SlimeVR) | file contract: `rehabtwin/sequence.py` (`skel_seq.npz`) |
| 3–4 Body model, skeleton | SKEL skin markers + joint centres → OpenSim scaling (`opensim_stage.py`) | Pose2Sim full-body model, 318 muscles |
| Person model | `person` (`person.py`): the person's bones, measurements and twin layers across sessions; `process --person`, `kinect --person` | `docs/person-model.md`; `schemas/person-model.schema.json` |
| 5 Biomechanics | `process` (gravity, gaps, filtering, scale, static IK, marker placement, IK), `muscles` (estimated GRF, ID) | QC in `qc.json`; validation per joint × plane |
| 6 Muscle sim | `muscles` (static optimisation; weakness and ideal-exo what-ifs), leg capacity scaled to body size (`capacity.py`) | Tier-labelled what-ifs |
| 7 Control / assistance | `muscles --assist` (ideal assistive device sizing) | upper bound; assist-as-needed caveat |
| 8 Visualisation | `report.html`, `correction.html`, `muscles.html`, `cues.html`, `index.html` (3D replay, charts) | self-contained HTML |
| Feedback | `correct` (correction view), `cues` / `lsl-live` / `suit-bridge` (haptic loop) | gated: Tier A + validated joint/plane only |

Every command writes files next to the session (the contract above). The LLM/agent
layer is still deliberately absent: it belongs after Stage-5 outputs have been validated
(Phase 2 in `docs/roadmap.md`).

