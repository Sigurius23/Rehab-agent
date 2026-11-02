# Stack: video → SKEL → OpenSim (implemented — `pipeline/`)

The first stack in this repo with working code. A single video (or several calibrated
ones) becomes a scaled OpenSim model, joint angles, posture metrics against gravity, and a
validation report. Usage, outputs and design decisions: [`pipeline/README.md`](../pipeline/README.md).
Measured results: [`docs/validation-results.md`](../docs/validation-results.md).

```
                ┌─ HSMR (IsshikiHugh/HSMR) ─ SKEL q, betas, camera ─┐   gated: SKEL model (MPI-IS)
video ──────────┤                                                   ├─► skel_seq.npz / *_seq.npz
                └─ MediaPipe Pose (non-gated, Tier C) ──────────────┘   (file contract, rehabtwin/sequence.py)
                                   │
            SKEL skin markers (SMPL2AddBiomechanics BSM map) + SKEL joint centres + q=0 static
                                   │
   gravity: device IMU ▸ floor-plane fit ▸ camera-level   (logged in qc.json)
                                   │
   Pose2Sim full-body OpenSim model (perfanalytics/pose2sim, BSD-3)
     ScaleTool ─► static IK (soft-pinned q=0) ─► marker placement ─► IK  (opensim-org/opensim-core 4.6, pip)
                                   │
   metrics (reps, trunk/pelvis vs gravity, knee FPPA) ─► validation vs reference ─► session.json + report.html
```

| Step | Repo | Status |
|---|---|---|
| Video → SKEL | `IsshikiHugh/HSMR` + `MarilynKeller/SKEL` | adapter written and tested with an emulated HSMR dump; needs the gated SKEL model + GPU to run for real |
| Skin-marker map | `MarilynKeller/SMPL2AddBiomechanics` (`bsm_markers.yaml`) | read at run time, never copied |
| OpenSim model + marker sets | `perfanalytics/pose2sim` | used as is, with one recorded fix (head markers) |
| Scale / IK | `opensim-org/opensim-core` | pip wheel 4.6, CPU |
| Non-gated test front-end | `google-ai-edge/mediapipe` | runs; Tier C; failed all gates against 4 cameras (see results) |
| Monocular benchmark to beat | `utahmobl/opencap-monocular` | 4.8° MAE vs marker mocap (preprint); PolyForm non-commercial |
| First real reference | OpenCap LabValidation dataset (SimTK) | to do: closes D-04 for kinematics |

Clone what the stack needs:
`python3 scripts/clone.py --only perfanalytics/pose2sim,IsshikiHugh/HSMR,MarilynKeller/SKEL,MarilynKeller/SMPL2AddBiomechanics,utahmobl/opencap-monocular`

Tier: monocular video on a statistical body is **Tier C** (`docs/accuracy.md`). This stack
produces the measurements and the evidence. It does not license corrections. Feeding it a
Tier-A personalised model (`stacks/digital-twin.md`) is a configuration change: swap the
model in `pipeline/configs/*.json`.
