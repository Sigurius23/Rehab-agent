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
Kinect v1 ──► capture/kinect_v1 (Windows, SDK 1.8) ──► colour + registered depth
            └─► mediapipe_pose.py on colour/%06d.jpg ──► rehabtwin kinect (depth-lifted) ──► *_seq.npz
                                                    │
skel_seq.npz ──► rehabtwin process ─────────────────┘   [biomech env, CPU]
   1. camera → gravity → OpenSim ground   (device gravity > floor-plane fit > camera-level, all logged)
   2. gaps ≤ 0.2 s bridged and listed, longer gaps split segments (one marker's longer gap stays
      empty: IK has no target for it there; frames with targets for < 50 % of the IK marker weight,
      `ik.min_target_weight`, are not solved), 6 Hz zero-lag low-pass per finite stretch
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
python -m pytest tests -q                           # 49 tests (end-to-end ones skip without opensim/pose2sim/pylsl)
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

A mirrored front-camera ("selfie") clip swaps every left/right landmark silently. Pass
`--mirrored` to the adapter (or to `mp-mono` for a dump made without it); see the mirroring
check in `docs/hardware.md`. `mp-multiview` has no `--mirrored`: un-mirror each front-camera clip
at the adapter. Each camera's setting is kept in the sequence meta (`camera_mirroring`).

A Kinect v1 (Xbox 360) adds depth from one viewpoint: `capture/kinect_v1/KinectCapture.exe` records on
Windows, and `rehabtwin kinect` lifts the MediaPipe keypoints of its colour frames with the registered depth.
Gravity comes from the floor in the depth image; a mirrored stream is detected from the SDK skeleton's sides.
Setup, placement and the validation plan are in `docs/kinect-v1.md`. It has not run on a real sensor yet.

**One body across sessions.** By default every `process` run fits the generic model to its own frames, so a
person's bones change with the camera setup. A person folder keeps them (`docs/person-model.md`):

```bash
python -m rehabtwin person init people/P01 --person-ref P01 --height-m 1.80 --mass-kg 75
python -m rehabtwin person build people/P01 out/calib          # a processed calibration session (best setup)
python -m rehabtwin process phone_aug.npz out/s02 --exercise squat --person people/P01
```

`--person` applies the stored scale factors and checks the recording's size against them: one camera's
recording is scaled to the person, and a calibrated one more than 10 % off is refused. `session.json`
records the person model's version (`person_model`).

Several phones (OpenCap-style checkerboard calibration, unsynchronised starts) and OpenCap's LSTM
anatomical-marker augmenter, which the pelvis needs (validation-results §4):

```bash
python -m rehabtwin mp-multiview cam0.npz cam1.npz cam2.npz --sync --out multi_seq.npz \
    --opencap-calib Cam0/cameraIntrinsicsExtrinsics.pickle Cam1/... Cam2/...   # numpy-only unpickler
python -m rehabtwin augment multi_seq.npz multi_aug_seq.npz --height-m 1.80 --mass-kg 75 --mass-source measured   # pip install onnxruntime
python -m rehabtwin process multi_aug_seq.npz out/ --exercise squat --mass-kg 75 --height-m 1.80
```

`--sync` searches start offsets up to `--max-lag-s` (default 2 s) and also checks lags up to twice that.
It refuses (exit 2) when:
- a lag beyond the window correlates better than the best inside it. With repetitive movement, an alias one
  repetition inside the window can still exceed r = 0.5. Rerun with the suggested larger `--max-lag-s`.
- the hip-motion correlation (Pearson r) peaks below 0.5.
- the best lag sits at the end of the lags where the clips overlap by 1 s.

Offsets beyond twice `--max-lag-s` are not checked, so set it to the largest plausible offset. When the
runner-up peak, typically one repetition away, is within 0.15 of the best, `--sync` warns and records the
per-camera diagnostics under `sync` in the sequence meta. Start each recording with a jump. A clap does not
move the hips, but it lets you check the lags.

The LSTM gets gap-free input, but augmented markers are left empty in frames where one of their
keypoints was missing for more than 0.2 s (`meta.augmenter.frames_masked_input_gap`). Without the
lower-body markers IK has no leg targets, so `process` splits the trial there (`qc.unsolved`) instead
of holding the legs still; a knee occluded at the bottom of every rep can leave nothing to solve, in
which case the keypoint-only `mediapipe33_pose2sim` config still solves from the remaining keypoints.
Reps that overlap a weighted marker's missing span are flagged (`contains_missing_markers`).

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
Motion files may be in radians (`inDegrees=no`): every command converts them to degrees on read
(`io_formats.to_degrees`), using the model's coordinate types where a model is at hand and otherwise
names (`*_tx/_ty/_tz`, `Abs_t*` are metres; coupled `*_beta` stay as OpenSim writes them).

## Beyond measurement: correction view, muscle effects, haptic cues

Three commands work on a processed session folder. All three are gated by
`docs/accuracy.md`: on a Tier-B/C body they produce labelled illustrations or
replays and never targets or live cues.

```bash
# "how it would look fixed": clinician-authored changes, re-solved with the feet planted
python -m rehabtwin correct  SESSION --spec squat_knee_valgus_right --illustrative
# muscle effects: estimated GRF → inverse dynamics → static optimisation (+ what-ifs)
python -m rehabtwin muscles  SESSION --rep 1 --correction squat_knee_valgus_right --weaken gluteus_medius_r=0.5 \
                             --assist knee_angle_r=40:neg --passive knee_angle_r=60@20:pos
# --assist: ideal knee-extension exo, max 40 N·m; --passive: elastic band, 60 N·m/rad beyond 20° knee flexion
# variants run in parallel (--workers, default up to 4 processes) at ≤ 30 fps (--max-fps): a slow squat does not
# need 60 Hz static optimisation, and each variant is an independent problem
# double-stance exercises first re-solve IK with both feet held where they stood (--no-plant to skip): video
# kinematics let planted feet wander several cm, which the force estimate would differentiate twice
# haptic posture cues (suit Track 1): offline replay of a rule set, also over a corrected motion
python -m rehabtwin cues     SESSION --rules squat_posture [--motion SESSION/correction/<spec>/corrected.mot]
```

`muscles` and `strength` need the session's body mass: the ground forces are m (a_com + g), so every
torque, muscle force, activation and N·m/kg scales with it. A session processed without a measured mass
records `qc.json → subject.mass_source: "assumed default"` (config default, 70 kg) and both commands refuse
it (exit 2); `--allow-assumed-mass` runs anyway and labels the report "body mass assumed (70 kg)". Device
what-ifs (`--assist`, `--passive`) on an assumed mass are labelled ILLUSTRATION ONLY even at Tier A.
Synthetic sessions record the generator's mass as `"synthetic truth"`. `augment` needs a mass (an LSTM input)
and carries it over to `process` with `--mass-source` (default `assumed`; pass `measured` if the person was
weighed). `process` refuses a `--mass-kg` that differs from a measured augmenter mass by more than 0.5 kg.

Strength calibration from hand-held dynamometry (maximal isometric torques; template in
`configs/strength/example_hhd.json`, test actions and postures in `configs/strength_actions.json`):

```bash
python -m rehabtwin strength SESSION --tests my_hhd.json    # → SESSION/strength/ (model_strength.osim, strength.html)
python -m rehabtwin muscles  SESSION --rep 1 --strength --grf-sensitivity 0.15
```
For each test the model is posed as tested and its isometric moment at full activation is
computed per muscle; the test's prime movers (and synergists no other test owns) get one
max-isometric-force factor so the model reproduces the measured torque, all tests solved
jointly. The report lists each factor against the generic model and the limb symmetry index
(LSI < 90 % flagged). The trunk test is evaluated about L5/S1 alone (lumbar couplers removed
for that moment). `--grf-sensitivity` re-runs every variant with the right foot's share of
the load shifted by ± the given amount; a change (variant − measured, same split) is marked
robust only if it keeps its sign and stays ≥ 2 points of capacity under every split. Expect the
absolute activation levels to move far more than the changes (±0.15 moved right-quadriceps
peak demand between 37 % and 67 % on the synthetic squat).

Every muscle study reports **dynamic consistency**. It takes the residual the estimated ground forces leave on the
pelvis and expresses the moment as the centre-of-pressure shift that would explain it. Above 10 cm, or 10 % BW of
force, the report says the forces do not fit the motion and that every muscle number is unreliable. This is the
case for fast squats with arm swing, where segment angular momentum breaks the quasi-static estimate.

`muscles.html` includes a **3D muscle view**: each muscle's line of action (OpenSim path, wrapping
included) on the moving model, coloured by its static-optimisation activation or by the change
against the measured run, with line width ∝ √(max isometric force), so a weakened group draws
thinner. Pick the variant (measured / corrected / weakened / exo); hover a muscle for its numbers.
`--no-3d` leaves it out.

Progress over time, for one person's sessions of the same exercise:

```bash
python -m rehabtwin progress SESSION_WEEK1 SESSION_WEEK4 SESSION_WEEK8 --out progress/
```
Per signal the session value is the mean of the rep peaks. A change is called **real** only if it
exceeds both the rep-to-rep scatter (Welch t-test on the sample SDs, ≥ 2 reps in each session) and
the minimal detectable change from that joint × plane's validation (MDC95 = 1.96·√2·RMSE vs
marker-based motion capture). Only a validation the feedback gate would also trust counts: marker
mocap, of the session's current processing, same person and exercise, with that joint × plane's gate
tested. Without one (a markerless or synthetic reference does not count) the verdict is "consistent
across reps; size not validated", and progress says why a report on disk was not used: a lighting,
clothing or camera change can produce a consistent shift too. Reps that include bridged or missing
markers are named. Sessions of different people, and folders whose re-processing did not finish,
are refused; a front-end or tier change between sessions is flagged. Sessions are ordered by
`started_at`: pass the recording time to `process --started-at 2026-10-21T09:30:00+02:00` (a
re-processing keeps it), otherwise the processing time stands in and progress warns that the order
may be wrong.

Live loop over Lab Streaming Layer (`pip install -e "pipeline[live]"`), the same engine in real time:

```bash
python -m rehabtwin lsl-live --rules squat_posture --session SESSION   # posture stream in → cue markers out
python -m rehabtwin lsl-simulate SESSION --rules squat_posture --speed 1  # stand-in for the IMU suit
python -m rehabtwin lsl-listen                                          # stand-in for the suit firmware bridge
```
The live loop reads tier and validation from `SESSION` (there is no override flag). The
simulator stamps samples on the recording's own timeline, so rule durations behave the
same at any replay speed.

Feedback gate (offline replay and live loop alike), which fails closed:
- The session must be Tier A.
- Its validation report must be graded `marker-mocap`, not synthetic, for the same `person_ref`, and
  list the rule set's exercise.
- Live, the posture stream must carry the session's id and front end in its LSL tags. Otherwise the
  loop runs at Tier C and nothing is sent: an IMU stream cannot borrow a video session's approval.
- Two streams with the same name are refused rather than guessed.
- LSL streams are visible to the whole local network, so run the live loop on a trusted network.

With an IMU suit, SlimeVR-Server's VMC output (Settings → OSC → VMC, port 39539) replaces the
simulator:
`python -m rehabtwin vmc-posture --print`. It listens on localhost only unless you pass `--host`, and stops
publishing 0.5 s after the last VMC packet, so a dropped tracker cannot freeze a pose. It rebuilds global joint positions from the VMC
bone stream (Unity left-handed → right-handed, forward kinematics over the humanoid hierarchy)
and publishes `torso.sagittal/frontal`, `knee_angle_r/l`, `knee_fppa_r/l` and an approximate
`lumbar_total.sagittal` with the same names the video pipeline uses, so one rule set covers
both. IMU yaw drifts, so no transverse-plane signals are offered, and the suit stays Tier C
until it has been validated against a reference like any other front-end.

The last hop drives the suit: `python -m rehabtwin suit-bridge [--ble vest=AA:BB:…]` reads the
cue markers and writes bHaptics-protocol payloads to SenseShift firmware (ESP32 DIY vest and
sleeves). The vest takes 20 bytes with one 4-bit intensity per motor; sleeves take one byte
per motor. The mapping from rule actuators to motors is in `configs/feedback/suit_bhaptics.json`,
and motor layouts are parsed from your SenseShift clone at run time (GPL-3.0, not copied).
Without `--ble` it is a dry run that logs the payloads.

The bridge is fail-safe. SenseShift holds a motor at its last level, so every exit (end of
`--duration-s`, Ctrl-C, an error) sends an acknowledged all-off frame before disconnecting. Each cue
is capped:
- at most 1 s long;
- at most 0.8 intensity;
- at most 30 % on-time per actuator over 10 s.

A mapping's `limits` may lower these caps, never raise them. `--ble` names that are not devices in
the mapping are refused.

```
SlimeVR ─VMC─► vmc-posture ─LSL─► lsl-live (CueEngine, gated) ─LSL─► suit-bridge ─BLE─► SenseShift vest/sleeves
```
The chain is covered by a test from posture stream to payload bytes. The one remaining
untested step is a physical BLE write.

| Command | What it does | Guard rails |
|---|---|---|
| `correct` | Spec modes `set / clamp / scale / offset / mirror` (e.g. right hip follows the left). OpenSim IK tracks the changed coordinates strongly and the rest weakly, keeping 3 anchor points per foot in place. Reports requested changes, the **compensations** elsewhere, range-of-motion violations and feet drift (`admissible`). | Refused below Tier A without `--illustrative`; then every output says ILLUSTRATION ONLY. Specs ship as TEMPLATEs for a clinician to author. |
| `muscles` | Ground forces from whole-body Newton (F = m(a_com + g)), split between the feet by the centre of mass and placed by moment balance. Then OpenSim inverse dynamics and static optimisation on the 318-muscle model, with group activation as a fraction of capacity, joint moments (N·m/kg), and measured vs corrected vs weakened. | Valid only for slow double-stance exercises (`grf.feet_planted`, `valid_exercise`). Pelvis residuals and reserve-torque use are reported. Leg muscle capacity is scaled to the measured height and mass (Handsfield 2014 regression, `capacity/`; `--generic-capacity` for the generic subject's). Phrased as a what-if, never as a claim about the person's muscles. |
| `muscles --assist` | **Ideal assistive device** (exoskeleton what-if, after Dembia et al. 2017): a torque actuator at a joint, capped at the device's max torque (optionally one direction only), that the optimiser uses as it sees fit. Reports the device torque profile (peak, mean, time at cap) and which muscles it offloads. | An upper bound on the benefit (massless, instantaneous, optimal control). Offloading a muscle also removes the training stimulus, so the caveat recommends assist-as-needed. |
| `cues` | Streaming `CueEngine` (same code for offline replay and a live suit): threshold with hysteresis, minimum duration, per-actuator refractory period, **faded feedback** (cue share falls from 100 % to ~33 % over the first violations). Writes `cues.json`, LSL-ready `commands.csv`, `cues.html`. | A cue is *sent* only on a Tier-A twin and only for joint/planes listed in a non-synthetic validation report; otherwise it is logged as `would_cue` with the reason. |

Synthetic check (right-knee valgus squat). These numbers come from a run scaled to the former 70 kg
default; synthetic sessions now record the generator's 72 kg, so forces and moments in N·m come out
about 3 % higher and activations shift slightly:
- **Correction:** the valgus correction takes the right-knee frontal-plane projection angle from 23.8° to
  0.7°. The body compensates with pelvis list 3.3° and left hip adduction 2.6°.
- **Feet:** the right foot has to turn by up to 3 cm at the toes (per-frame drift 2.1 cm, just over the
  2 cm admissibility rule). The model's knee has no independent tibial rotation, so a change in hip
  rotation with a planted foot must come out at the foot. That is a model limitation worth knowing
  before trusting any knee-rotation correction.
- **Cues:** the rules fire 3 times on the measured motion and 0 times on the corrected one.
- **Muscles:** static optimisation on rep 1 gives a 1.13 BW peak vertical force and a 1.18 N·m/kg knee
  extension moment, with quadriceps and gluteus maximus carrying the movement. The corrected motion
  raises right gluteus medius demand from 12 % to 18 % of capacity: holding the knee out costs hip
  abductor work. A what-if with the right quadriceps at 60 % raises their demand from 52 % to 77 %,
  with gluteus maximus +23 % and less hamstring co-activation.
- **Ideal exo:** a 40 N·m knee-extension device sits at its cap for 51 % of the rep and lowers
  right quadriceps demand from 52 % to 32 %. The knee moment peaks near 83 N·m for the 70 kg
  run, so 40 N·m cannot carry it alone. A 40 N·m hip-extension device lowers gluteus maximus
  from 46 % to 25 % and halves hamstring demand.

Implementation notes learned the hard way: corrected motions are low-pass filtered like
measured ones, and pelvis translations are tracked rather than left free. A free pelvis
let IK jitter 6.6 cm sideways, and static optimisation then "needed" 70 N·m reserve torques.

## Outputs (one folder per session)

| File | Content |
|---|---|
| `skel_seq.npz` | the front-end output (file contract: `rehabtwin/sequence.py`) |
| `opensim/model_scaled.osim` | subject model (Pose2Sim full body, 318 muscles, 5 lumbar levels) |
| `opensim/ik.mot`, `ik_ik_marker_errors.sto` | joint angles (deg) and per-frame marker residuals |
| `opensim/*_setup.xml`, `markers_*.trc`, `scale_factors.xml` | every OpenSim input, re-runnable in the OpenSim GUI |
| `qc.json` | frames/gravity source, floor fit, gaps and imputed frames (any marker bridged), per-marker bridged/missing spans and coverage (`imputed_by_marker`), frames a weighted marker had no target (`missing_target_frames`), frames not solved (`unsolved`), body mass and its source (`measured` from `--mass-kg` or `augment --mass-source measured`, `synthetic truth`, else assumed), scale factors, marker placement, IK residuals |
| `metrics.json` | reps and per-rep values; every signal labelled with joint, plane, validated, feedback_eligible |
| `validation-report.json` | RMSE per joint × plane, gates, `approved_for` (`schemas/validation-report.schema.json`) |
| `session.json` | provenance, tier, accuracy layers, upstream commit pins (`schemas/session.schema.json`) |
| `report.html` | self-contained charts (reference dashed when present), per-rep table, gates |
| `correction/<spec>/` | `corrected.mot`, `correction.json`, `correction.html` (measured vs corrected 3D replay) |
| `progress/` (`--out`) | `progress.json` (verdicts per signal, series), `progress.html` (trend per signal) |
| `capacity/` | `model_capacity.osim`, `capacity.json`: leg muscle forces scaled to the measured height and mass (`muscles`, `strength`) |
| `strength/` | `model_strength.osim`, `strength.json` (factors, LSI), `strength.html` |
| `muscles/` | per variant: `grf.mot`, `inverse_dynamics.sto`, static-optimisation activations/forces, `muscles.json`; `study.json`, `muscles.html` |
| `feedback/<rules>/` | `cues.json` (event log + summary), `commands.csv` (actuator events), `cues.html` |

Re-processing into an existing folder rewrites `session.json` with a new `pipeline.processing_id`
(hash of scaled model + motion + tier + exercise). Validation, correction, strength, muscle and cue
results store the id they were computed from; `index.html` keeps a mismatching one listed but marks
it **STALE**, `muscles --strength` refuses a stale `strength.json`, and a muscle study or cue replay
of a stale correction warns and is itself marked stale. The feedback gate (`cues`, `lsl-live`) only
trusts the `validation-report.json` that `process --reference` wrote for the current processing:
one left over from an earlier run (or copied in from `rehabtwin validate`) closes it. `process`
removes the old stamp before it rewrites the model, so a run that fails half-way leaves everything
derived stale; sessions processed before stamps existed need one `process` run before
`strength`/`muscles --strength`.

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
- **Claims follow the tier, and the tier follows evidence.** Every session is Tier C unless `process`
  gets `--tier B|A --model-provenance FILE`. That JSON record (fields in `rehabtwin/tiers.py`) names
  the person, the personalised model with its sha256, the evidence and the approver. It is refused
  for synthetic input, for another person, or for a model other than the one the config uses, and
  the session records why it has its tier (`tier_source`).
- Monocular video is Tier C: `feedback_eligible` is false for every number.
- A reference must be graded (`--reference-grade marker-mocap|markerless`); only marker-mocap
  can approve anything.
- A synthetic validation never approves anything, and neither does a validation in which no
  joint/plane meets its target.
- `muscles --assist/--passive` on a Tier-B/C body needs `--illustrative` and is labelled a
  design-space bound, not an assistance profile.

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
