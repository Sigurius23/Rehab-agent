# Changelog

## Unreleased
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
