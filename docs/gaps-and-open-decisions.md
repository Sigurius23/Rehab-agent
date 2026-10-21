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
| D-08 | Original 70 repos' live metadata | Run `scripts/enrich_metadata.py --apply` with a GitHub token | Do before the first public release of this repo | Catalog polish |
| D-09 | SKEL/SMPL licensing for anything beyond research | SKEL, SMPL, HSMR weights and OpenCap Monocular are non-commercial; MediaPipe/OpenSim/Pose2Sim are permissive | Research use now; ask MPI-IS (ps-license@tue.mpg.de) before any commercial plan, or plan a permissive body model | Commercial use of `pipeline/` with the SKEL front-end |
| D-10 | Gravity reference for monocular captures | Phone IMU (ARKit/CoreMotion) vs floor-plane fit vs levelled tripod | Record the device gravity vector with every capture (`pipeline` uses it first); floor fit only as a cross-check | Any trunk/pelvis inclination number |
| D-11 | Monocular front-end choice | HSMR/SKEL (implemented adapter) vs WHAM-based OpenCap Monocular vs SAM4Dcap | Measure HSMR/SKEL on LabValidation; keep OpenCap Monocular's 4.8° MAE as the bar | Tier-C/B kinematics claims |

## Filled (2026-10-21 pipeline pass)
- ✅ First working slice: `pipeline/` (video → SKEL → OpenSim), 35 tests, synthetic selftest, real-video demo
- ✅ Measured results recorded in `docs/validation-results.md` (synthetic + monocular vs multi-view)
- ✅ Upstream issues found and handled: Pose2Sim `Markers_SKEL.xml` head markers in the wrong frame; HSMR demo resize (W, H) swap; HSMR `full_cam_t` dumped per image, not per person
- ✅ Doc inconsistency fixed: roadmap Phase 1 vs environments install order (both now point at the implemented slice + Tier-A swap)

## Known catalog limitations (accepted, recorded)
- Star/fork counts are orientation only and go stale; upstream READMEs win.
- Several upstream licenses are unclassified by the GitHub API (`NOASSERTION`)
  or undeclared — the per-repo `notes` say so; a deployment must compile its
  own NOTICE list (docs/safety-and-licensing.md).
- The private DAAPT repo remains unverifiable by anyone without access.
