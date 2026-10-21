# Changelog

## Unreleased
- `rehabtwin correct`: correction view (clinician specs, planted-feet IK, compensations, ROM check, Tier gating)
- `rehabtwin muscles`: estimated double-stance GRF → inverse dynamics → static optimisation; corrected and
  weakened what-ifs; muscles.html
- `rehabtwin cues`: haptic posture-cue rule engine (hysteresis, refractory, faded feedback, Tier/validation gate)
- Live loop: `lsl-live`/`lsl-simulate`/`lsl-listen` (LSL) and `vmc-posture` (SlimeVR VMC → posture signals)
- `suit-bridge`: cue markers → SenseShift/bHaptics BLE payloads (layouts parsed from the GPL firmware at run time)
- `muscles --assist`: ideal assistive device (exo sizing upper bound), e.g. `knee_angle_r=40:neg`
- `muscles`: planted-feet IK prior for double-stance exercises (`--no-plant`), dynamic-consistency verdict from
  pelvis residuals; real-squat chain documented (validation-results §5)
- `muscles`: variants (and GRF-split re-runs) in parallel processes, analysis capped at 30 fps; correction
  admissibility counts only range violations the correction causes
- Real-video agreement vs OpenCap (5 phones + 1 phone, public LabValidation squat): `rehabtwin augment` (OpenCap
  LSTM via Pose2Sim ONNX), `mp-multiview --opencap-calib --sync`, `mediapipe_lstm_pose2sim` config,
  `examples/opencap_agreement.sh`, `reference_grade` in validation reports
- `rehabtwin progress`: session-to-session change per signal against rep scatter and validated MDC95
- `muscles --passive`: one-sided elastic support what-if (e.g. knee band), alongside the ideal exo
- `rehabtwin strength`: dynamometer torques → strength-calibrated model (per-test capacity factors, LSI);
  `muscles --strength`; `muscles --grf-sensitivity` robustness bands for the GRF split
- 3D muscle view in `muscles.html`: activation-coloured muscle paths per variant, change-vs-measured mode,
  capacity-scaled widths; 3D replays now view from above (camera pitch sign fixed)
- `examples/synthetic_demo.sh`: every command on the synthetic squat; `docs/architecture.md` stage → module map
- **First working slice — `pipeline/` (rehabtwin): video → SKEL → OpenSim.**
  HSMR/SKEL adapter, MediaPipe front-end (mono + calibrated multi-view), gravity
  (device ▸ floor fit ▸ camera-level), OpenSim scale/static IK/marker placement/IK,
  rep and posture metrics, validation per joint × plane, schema-valid session records,
  HTML report; synthetic selftest; 35 tests; CI job
- `docs/validation-results.md`: synthetic round trip (~1°) and real-video monocular vs
  4-camera result (MediaPipe monocular fails all gates)
- `stacks/video-skel-opensim.md`; catalog +2 (utahmobl/opencap-monocular, davidpagnon/Sports2D) → 110 repos
- Schemas: monocular sessions (null reprojection, single-stream sync), pipeline provenance,
  synthetic flag and feedback_allowed_joint_planes on validation reports
- Gaps D-09 (licensing), D-10 (gravity), D-11 (monocular front-end); D-04 points at OpenCap LabValidation
- Gap pass: resolved all `needs-review` entries; added kalibr, apriltag, Meshroom (108 repos)
- CI, unit tests, schemas + synthetic example, validation protocol, environment isolation
- Metadata enrichment (`scripts/enrich_metadata.py`) and clone pinning (`scripts/record_pins.py`, `catalog/pins.json`)

## 2026-10-21 — Hardware lock
- Selected hardware fixed: RGB cameras + iPhone LiDAR + optional RealSense D455 (`docs/hardware.md`)
- Added `realsenseai/librealsense` (105 repos)

## 2026-10-21 — Accuracy first
- Anatomical accuracy made design priority #1 (`docs/accuracy.md`, Tier A/B/C claim rules)
- Added medical-imaging personalisation repos (104 repos)

## 2026-10-21 — Digital-twin expansion
- Added 28 repos: personalisation, live tracking, correction, CEINMS/SOFA, haptic/exo hardware (98 repos)

## 2026-10-21 — Initial meta-repo
- Catalog of the original 70 repos with tiers, categories, clone/list/validate tooling
