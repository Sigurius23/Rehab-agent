# Changelog

## Unreleased
- **Safety gates:**
  - Tier B/A only with a model-provenance record bound to the model by sha256 (`--model-provenance`).
  - `--reference-grade` is required with any reference.
  - The feedback gate needs a marker-mocap validation for the same person and exercise.
  - The live loop downgrades foreign or untagged posture streams to Tier C and refuses ambiguous LSL resolves.
  - `vmc-posture` listens on localhost by default and stops on stale data.
  - `suit-bridge` always ends all-off, with duration, intensity and on-time caps.
  - Unevaluated rules are reported.
  - Device what-ifs below Tier A need `--illustrative`.
- **Correctness fixes:**
  - `progress`:
    - Rep SDs are sample SDs, and rep scatter is judged with a Welch t-test.
    - A "real change" needs at least 2 reps per session, and MDC95 comes only from marker-mocap validations.
    - Sessions are ordered by the time-zone-aware recording time (`process --started-at`, `started_at_source`).
  - Motion tables written in radians (`inDegrees=no`) are converted to degrees on read.
  - `mp-multiview --sync`:
    - `--max-lag-s` sets the search window, and lags up to twice that are also checked.
    - It refuses window-edge lags, weak lags (r < 0.5) and lags beyond the window that correlate better.
    - Ambiguous lags are flagged, with per-camera diagnostics in the sequence meta.
  - Mirrored front-camera clips are un-mirrored (`mediapipe_pose.py --mirrored`, `mp-mono --mirrored`).
  - Gap filling:
    - Per-marker gaps are bridged only up to `max_gap_s`; longer ones stay NaN in the TRC.
    - Frames missing most IK targets are not solved (`qc.unsolved`).
    - The augmenter masks markers whose keypoints were missing for longer than that.
  - Derived results (corrections, muscles, strength, cues, validation report) carry the `processing_id`.
    `index.html` marks the ones from an earlier processing as STALE, and `muscles --strength` refuses a stale calibration.
  - Body mass:
    - `qc.json` records the mass and its source.
    - `muscles` and `strength` refuse an assumed mass unless `--allow-assumed-mass` is given.
    - `augment --mass-kg` carries over to `process` with its `--mass-source` (default `assumed`).
    - Device what-ifs on an assumed mass are labelled ILLUSTRATION ONLY even at Tier A.
    - Synthetic sessions use the generator's 72 kg.
  - Where the fixes meet:
    - Validation needs coverage. When gap splitting leaves only a fragment of the trial (< 80 % of the
      time both systems recorded), every gate is not-tested; `qc.analysed_segment` and the report say
      which segment the metrics cover.
    - `progress` sizes changes only with a validation the feedback gate would trust (current processing,
      marker mocap, same person and exercise, gate tested), says why it ignored one, and names reps
      with bridged or missing markers.
    - `process` refusals before the folder changes (mass, nothing solvable) leave the session stamped and
      `skel_seq.npz` intact; a re-processing keeps a recording time given with `--started-at`.
    - `muscles`, `strength`, `correct` and `progress` refuse a folder whose re-processing did not finish.
    - `process` refuses an augmented sequence masked with another gap limit than the config's
      (`augment --max-gap-s`).
    - `mp-multiview` records each camera's mirroring.
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
