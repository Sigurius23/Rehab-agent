# Gaps register & open decisions

## Filled (2026-10-21 gap pass)
- ✅ All 4 `needs-review` repos resolved from upstream READMEs (MyoBack,
  MASS, mass-dart-exo — exo specifics still undocumented upstream, RC-SMPL)
- ✅ Hardware-calibration support repos added: `kalibr`, `apriltag`, `Meshroom` (108 repos total)
- ✅ CI (`.github/workflows/validate.yml`): catalog validation + unit tests + generated-file drift check
- ✅ Tests (`tests/test_catalog.py`, stdlib unittest)
- ✅ Schemas (`schemas/`) + synthetic example session (`examples/`)
- ✅ Validation protocol as an executable checklist (`docs/validation-protocol.md`)
- ✅ Per-stack environment isolation (`docs/environments.md`)
- ✅ Live-metadata refresh tooling (`scripts/enrich_metadata.py`) and
  reproducible-clone pinning (`scripts/record_pins.py` → `catalog/pins.json`)
- ✅ CHANGELOG + issue templates

## Still open — not fillable from this repo alone

| ID | Decision / gap | Options | Recommendation | Blocks |
|---|---|---|---|---|
| D-01 | iPhone: fixed tripod viewpoint or moving main camera? | Fixed (assumed in hardware.md) vs handheld ARKit-pose fusion | Fixed for clinic; moving only as extra viewpoint | Live-pipeline design |
| D-02 | MRI/CT access pathway for Tier-A onboarding | Hospital partner, private scan referral, research scanner time | Partner pathway + ethics approval before any patient twin | Tier A entirely |
| D-03 | Clinical acceptance thresholds sign-off | Adopt accuracy.md targets as-is vs clinician-adjusted per movement/population | Clinician reviews per movement before Phase 2 ends | Any feedback claim |
| D-04 | Ground-truth reference for kinematics validation | Rented marker-mocap lab days vs collaborating gait lab; **public OpenCap LabValidation dataset** (video + marker mocap IK, squats/STS/walking/DJ) | Start with LabValidation now (free, `docs/validation-results.md`), then a gait-lab collaboration for our own hardware/movements | Validation protocol step 5 |
| D-05 | Exoskeleton safety ownership | Named responsible engineer + risk assessment process | Must exist before Track-2 hardware is powered near a person | Exo Track 2 |
| D-06 | Patient-facing surface | Phone app (matches iPhone hardware) vs clinician-led tablet vs web | Phone-first, clinician-reviewed outputs only (roadmap Phase 3) | Phase 3 |
| D-07 | Data jurisdiction & retention for RGB-D health data | Local-only processing vs cloud mocap services | Local-only by default (hardware.md privacy note) | Any real recording |
| D-08 | Original 70 repos' live metadata | ~~Run `scripts/enrich_metadata.py --apply` with a GitHub token~~ **Done 2026-10-28** (anonymous API: repos 1–52 + gap entries refreshed; licenses for all 115 verified (7 repos added since, fully documented at entry); documentation standard enforced by validator/tests). Re-run with `GITHUB_TOKEN` before public release to refresh stars/forks again | Before the first public release of this repo | Catalog polish |
| D-09 | SKEL/SMPL licensing for anything beyond research | SKEL, SMPL, HSMR weights and OpenCap Monocular are non-commercial; MediaPipe/OpenSim/Pose2Sim are permissive | Research use now; ask MPI-IS (ps-license@tue.mpg.de) before any commercial plan, or plan a permissive body model | Commercial use of `pipeline/` with the SKEL front-end |
| D-10 | Gravity reference for monocular captures | Phone IMU (ARKit/CoreMotion) vs floor-plane fit vs levelled tripod | Record the device gravity vector with every capture (`pipeline` uses it first); floor fit only as a cross-check | Any trunk/pelvis inclination number |
| D-11 | Monocular front-end choice | HSMR/SKEL (implemented adapter) vs WHAM-based OpenCap Monocular vs SAM4Dcap | Measure HSMR/SKEL on LabValidation; keep OpenCap Monocular's 4.8° MAE as the bar | Tier-C/B kinematics claims |

## Filled (2026-10-21 pipeline pass)
- ✅ First working slice: `pipeline/` (video → SKEL → OpenSim), 35 tests, synthetic selftest, real-video demo
- ✅ Measured results recorded in `docs/validation-results.md` (synthetic + monocular vs multi-view)
- ✅ Upstream issues found and handled: Pose2Sim `Markers_SKEL.xml` head markers in the wrong frame; HSMR demo resize (W, H) swap (drafted reports in `docs/upstream-issues.md`)
- ✅ Doc inconsistency fixed: roadmap Phase 1 vs environments install order (both now point at the implemented slice + Tier-A swap)

## Filled (2026-10-21 second pass)
- ✅ Correction view (`rehabtwin correct`): clinician specs, planted-feet IK, compensations, ROM check; illustration-only below Tier A
- ✅ Muscle effects (`rehabtwin muscles`): GRF estimate, ID, static optimisation, weakness and ideal-exo what-ifs
- ✅ Haptic loop end to end in software: SlimeVR VMC → posture → gated CueEngine (faded feedback) → LSL → SenseShift BLE payloads
- ⚠️ Found: the Pose2Sim/Rajagopal knee has no independent tibial rotation, so hip-rotation corrections with planted feet move the foot (~2 cm) — matters for any knee-valgus correction claim

## Filled (2026-10-21 third pass)
- ✅ 3D muscle view in `muscles.html`: muscle paths on the moving model, coloured by activation or change vs measured
- ✅ Strength calibration (`rehabtwin strength`): dynamometer torques → per-test muscle capacity factors, limb
  symmetry index; `muscles --strength` simulates with them. First evidence path for a "weak muscle group" statement
  that `accuracy.md` allows (measured strength, not body shape)
- ✅ GRF uncertainty made visible (`muscles --grf-sensitivity 0.15`): every variant is re-run under shifted left/right
  load splits and a change counts as robust only if it keeps its sign and size under all of them. On the synthetic
  squat, ±0.15 moves right-quadriceps peak demand between 37 % and 67 % — absolute muscle numbers are far less
  certain than paired what-if differences
- ✅ Progress over sessions (`rehabtwin progress`): a change is "real" only beyond rep scatter and the validated MDC95
- ✅ Muscle studies hold the feet where they stood (planted-feet IK prior) and report dynamic consistency; on the
  real OpenCap squat the quasi-static forces fail it (56 cm CoP-shift residual), so the report marks muscle numbers
  unreliable — measured ground forces are required beyond slow squats (G-02)
- ✅ Passive elastic support what-if (`muscles --passive knee_angle_r=60@20:pos`) next to the ideal exo bound
- ✅ First real-video numbers (`docs/validation-results.md` §4): MediaPipe 5-camera and 1-camera vs OpenCap on a public
  LabValidation squat; phone sync, OpenCap calibration, and OpenCap's LSTM marker augmenter (`rehabtwin augment`)
- ⚠️ Found: with sparse keypoints the pelvis tilt / hip flexion / lumbar split is unobservable (IK reached 95° pelvis
  tilt); the augmenter fixes it. Monocular capture should not drive pelvis, hip-flexion or lumbar signals
- ⚠️ Evaluated and rejected for G-02: total external wrench from full-body inverse dynamics distributed over the
  model's 12 foot-contact spheres (min-norm, f_y ≥ 0). Physically exact in principle, but the second derivatives of
  video-grade kinematics drive the right-foot share between 5 % and 70 % within one second on the synthetic squat;
  the quasi-static centre-of-mass split stays the default.

## Still open after the second pass
| ID | Gap | Why it matters | Next step |
|---|---|---|---|
| G-01 | No measured accuracy against marker mocap yet (HSMR/SKEL or MediaPipe) | Every Tier-C/B claim in `pipeline/` | Agreement with OpenCap is measured (validation-results §4: 5 cams + augmenter within 2.5–6° on trunk/pelvis/FPPA). Next: the same run against LabValidation mocap IK (SimTK download, blocked from the build network) |
| G-02 | Ground forces are estimated, not measured | Muscle/exo numbers | Force plates or pressure insoles in the validation session; until then report `--grf-sensitivity` bands. Contact-model tracking (Moco) inherits the same kinematic noise (see third pass) |
| G-03 | No Tier-A subject | Corrections and cues stay illustrations | D-02 imaging pathway; personalised `.osim` drops into `pipeline/configs` |
| G-04 | Physical BLE write to SenseShift untested | Suit Track 1 | One ESP32 + vibration motors bench test with `suit-bridge --ble` |
| G-05 | SlimeVR posture signals unvalidated | Live cues | Same validation protocol as video (per joint × plane), IMU vs mocap |
| G-06 | `utahmobl/opencap-monocular` and `davidpagnon/Sports2D` were used by `pipeline/` but not catalogued | The catalog's documentation standard needs live stars/forks, which the pipeline session's network could not fetch | **Done 2026-10-28**: catalog IDs 116–117, stars/forks fetched by the HarmannBitte session. Licences from the repo-root LICENSE files: PolyForm Noncommercial 1.0.0 for OpenCap Monocular (re-checked at e2d0b14; the API says NOASSERTION and the paper Apache-2.0, neither matches the file; it also needs SMPL weights) and BSD-3-Clause for Sports2D |

## Known catalog limitations (accepted, recorded)
- Star/fork counts are orientation only and go stale; upstream READMEs win.
- Several upstream licenses are unclassified by the GitHub API (`NOASSERTION`)
  or undeclared — the per-repo `notes` say so; a deployment must compile its
  own NOTICE list (docs/safety-and-licensing.md).
- The private DAAPT repo remains unverifiable by anyone without access.
