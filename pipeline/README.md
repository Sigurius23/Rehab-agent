# rehabtwin — the video → SKEL → OpenSim slice

First working code in this meta-repo: it turns a front-end's 3D output (HSMR/SKEL,
MediaPipe, or a synthetic generator) into a **scaled OpenSim model, joint angles,
posture metrics, QC, a validation report and a clinician-readable HTML report**.
Every stage writes files (`docs/architecture.md` contract) and every number
carries its tier and validation status (`docs/accuracy.md`).

```
video ──► HSMR (SKEL q, betas, camera)            [hsmr env, GPU, gated SKEL model]
            └─► adapters/hsmr_to_skelseq.py ──► skel_seq.npz   (105 SKEL skin markers + 24 joints + q=0 static)
video ──► MediaPipe Pose (non-gated, Tier C)       [twin-live env]
            └─► adapters/mediapipe_pose.py ──► rehabtwin mp-mono / mp-multiview ──► *_seq.npz
                                                    │
skel_seq.npz ──► rehabtwin process ─────────────────┘   [biomech env, CPU]
   1. camera → gravity → OpenSim ground   (device gravity > floor-plane fit > camera-level, all logged)
   2. gaps ≤ 0.2 s bridged and listed, longer gaps split segments, 6 Hz zero-lag low-pass
   3. ScaleTool (SKEL joint-centre pairs) → static IK (soft-pinned q = 0) → explicit marker placement
   4. InverseKinematicsTool → ik.mot (+ marker errors)
   5. metrics: reps, per-rep peaks/ROM, trunk & pelvis inclination vs gravity, knee FPPA, L/R asymmetry
   6. optional validation vs a reference .mot (RMSE per joint *and* plane, gates from docs/accuracy.md)
   7. session.json (schema-valid), qc.json, metrics.json, report.html
```

## Install (three isolated environments — `docs/environments.md`)

```bash
# biomech: the back-end (CPU is enough). OpenSim 4.6 ships pip wheels for Linux/macOS/Windows, py3.11–3.13.
python3 -m venv ~/.venvs/biomech && ~/.venvs/biomech/bin/pip install -e "pipeline[test]"
python3 scripts/clone.py --only perfanalytics/pose2sim          # OpenSim model + marker sets (BSD-3)

# hsmr: the SKEL front-end (GPU). Follow upstream docs/SETUP.md, then download the gated assets yourself:
python3 scripts/clone.py --only IsshikiHugh/HSMR,MarilynKeller/SMPL2AddBiomechanics
#   - SKEL v1.1.1 model: register at https://skel.is.tue.mpg.de (non-commercial research licence)
#   - HSMR checkpoint + regressors: see upstream docs/SETUP.md (HuggingFace)

# twin-live: the non-gated MediaPipe front-end
python3 -m venv ~/.venvs/twin-live && ~/.venvs/twin-live/bin/pip install mediapipe opencv-python numpy
# headless Linux also needs: apt-get install libegl1 libgles2
# model: https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_heavy/float16/latest/pose_landmarker_heavy.task
```

## Quick start

```bash
cd pipeline
python -m rehabtwin selftest /tmp/rt_selftest       # synthetic squat with known truth, ~1 min, exits 1 on regression
python -m pytest tests -q                           # 35 tests (end-to-end ones skip without opensim/pose2sim)
```

### Real video through HSMR + SKEL (the target path)

```bash
# 1. in the hsmr env (GPU)
cd upstream/IsshikiHugh/HSMR
python exp/run_demo.py --input_path squat.mp4 --output_path hsmr_out --ignore_skel
python ../../../pipeline/adapters/hsmr_to_skelseq.py --hsmr-npy hsmr_out/HSMR-squat.npy --video squat.mp4 \
    --skel-model-dir data_inputs/body_models/skel --out sessions/P001_squat/skel_seq.npz \
    --person-ref P001 --height-m 1.78        # measured height fixes monocular scale (recommended)

# 2. in the biomech env (CPU)
cd pipeline
python -m rehabtwin process ../sessions/P001_squat/skel_seq.npz ../sessions/P001_squat --exercise squat --mass-kg 74
open ../sessions/P001_squat/report.html
```

Phone captures should also record the **gravity vector** (ARKit/CoreMotion). Pass it
in OpenCV camera coordinates as `meta["gravity_up_cv"]` (or `mp-mono --gravity-up-cv`);
it outranks every image-based estimate, which matters for any trunk-lean number.

### Real video through MediaPipe (runs anywhere, Tier C)

```bash
python adapters/mediapipe_pose.py clip.mp4 --model pose_landmarker_heavy.task --out clip_mp.npz   # twin-live env
python -m rehabtwin mp-mono clip_mp.npz clip_seq.npz [--focal-px F] [--gravity-up-cv x,y,z]       # biomech env
python -m rehabtwin process clip_seq.npz out/ --config mediapipe33_pose2sim --exercise sit_to_stand
```

`examples/pose2sim_demo.sh` reproduces the real-data validation in
`docs/validation-results.md` (single camera vs 4-camera triangulation).

### Validation against a reference

```bash
python -m rehabtwin process seq.npz out/ --reference mocap_ik.mot --reference-system "Vicon + OpenSim IK, lab X" \
    --max-lag-s 0.5                         # unsynchronised systems: search a time offset
python -m rehabtwin validate out/opensim/ik.mot mocap_ik.mot --out validation-report.json
```

The recommended first reference is the public **OpenCap LabValidation** dataset
(10 subjects; squats, sit-to-stand, walking, drop jumps; synchronised phone video,
marker mocap and its OpenSim IK, see `docs/validation-results.md`). Pose2Sim's
5-level lumbar spine is compared with single-lumbar-joint models through
`lumbar_total.* → lumbar_extension/bending/rotation` aliases.

## Outputs (one folder per session)

| File | Content |
|---|---|
| `skel_seq.npz` | the front-end output (file contract: `rehabtwin/sequence.py`) |
| `opensim/model_scaled.osim` | subject model (Pose2Sim full body, 318 muscles, 5 lumbar levels) |
| `opensim/ik.mot`, `ik_ik_marker_errors.sto` | joint angles (deg) and per-frame marker residuals |
| `opensim/*_setup.xml`, `markers_*.trc`, `scale_factors.xml` | every OpenSim input, re-runnable in the OpenSim GUI |
| `qc.json` | frames/gravity source, floor fit, gaps and imputed frames, scale factors, marker placement, IK residuals |
| `metrics.json` | reps and per-rep values; every signal labelled with joint, plane, validated, feedback_eligible |
| `validation-report.json` | RMSE per joint × plane, gates, `approved_for` (`schemas/validation-report.schema.json`) |
| `session.json` | provenance, tier, accuracy layers, upstream commit pins (`schemas/session.schema.json`) |
| `report.html` | self-contained charts (reference dashed when present), per-rep table, gates |

## Design decisions worth knowing

- **Markers, not angle copying.** SKEL's 46 pose parameters share names with OpenSim
  coordinates for the legs, but spine (3 joints) and shoulders (scapula + 3-DoF) do not
  map 1:1. The stage fits IK on SKEL's own skin vertices (the BSM marker set from
  SMPL2AddBiomechanics) plus 12 anatomical joint centres. `qc.json → skel_vs_ik` reports
  how far SKEL's own angles are from the IK solution, per shared coordinate.
- **SKEL q = 0 is the static trial.** The neutral pose of the subject's own SKEL body
  gives a perfect, noise-free static trial; legs and spine are soft-pinned to 0 during
  the static solve, arms are left free.
- **Joint-centre pairs scale the pelvis and torso.** Skin-marker pairs inherit
  marker-set discrepancies (a 4 % pelvis error in the synthetic test).
- **Own marker placement.** OpenSim's MarkerPlacer converged to a 4.4° wrong static
  pelvis tilt and baked it into every frame; the explicit placement (static IK, then
  move free markers ≤ 5 cm, logged) removed the bias.
- **Gravity is measured, never inferred from the trunk.** Priority: device gravity →
  floor-plane fit (RANSAC, sole-height corrected, needs both feet down at some point)
  → camera-level assumption. The chosen source is in `qc.json` and the report header.
- **Claims follow the tier.** Monocular video is Tier C: `feedback_eligible` is false
  for every number; a synthetic validation never approves anything; a validation in
  which no joint/plane meets its target approves nothing.

## Known upstream issues handled here (drafted reports: `docs/upstream-issues.md`)

- Pose2Sim `Markers_SKEL.xml`: the 7 head markers carry torso-frame coordinates (top of
  head ≈ 0.5 m too high). Re-expressed via `marker_fixes` in `configs/skel105_pose2sim.json`.
- HSMR demo resize passes `(MAX_IMG_H, -1)` to a function expecting `(width, height)` — a
  3840×2160 video is processed at 1080×608 rather than 1920×1080.
  `rehabtwin.hsmr.hsmr_input_size` replicates it; override with `--image-size`.
- The adapter recomputes full-image camera translations from `patch_cam_t` and `bbx_cs`
  (same formula as HSMR's renderer), so it only depends on the per-person dump keys and
  honours `--image-size`.

## Licences

This code: MIT (repo licence). It reads, at run time and from your own downloads,
assets under other terms: Pose2Sim models (BSD-3), SKEL/BSM and the SMPL2AddBiomechanics
marker map (MPI-IS, non-commercial research), HSMR (see upstream), MediaPipe (Apache-2.0).
Nothing gated is copied into this repository.
