# Changelog

## Unreleased
- **Hip joint centres from the skin against MRI** (`validation/runs/mri_bones_3dbones/hip_centres.py`,
  `docs/person-model.md`):
  - A sphere fitted to the femoral head the same way for the MRI femur, SKEL, SKEL-J, OSSO and the floor. Predicted
    femurs are cut at the MRI's slice planes first; the slicing alone moves a centre by under 1.3 mm.
  - The 3DBones segmentations are incomplete at the bone ends. Only 9 of 72 femoral heads keep their top, and the
    tibia–fibula ends fall a median 16 and 25 mm short of the skeleton fitted to the bones. That, more than the
    20 mm slicing, is why every method read the tibia 30–39 mm long. Only the 9 complete heads are scored.
  - Floor 10.2 mm, so this data cannot test the 5 mm joint-centre target. SKEL 22.6 mm, SKEL-J 21.8 mm, OSSO 33.8 mm
    (worse than SKEL in all 9, with a +21 mm anterior offset). The skin-only error is mostly vertical scatter that all
    three predictors share per person (SD about 23 mm), not a bias that calibration would remove.
  - The 9 complete-head subjects do not differ detectably from the other 27 in body volume, bone depth or sex.
    Any calibration of OSSO's anterior offset must be fitted on separate data; these hips stay held out.
  - `validation/README.md`: ground truth first. A bench states its floor, the reference's completeness per case,
    whether the cases kept are a fair sample, and what the data can test, before it ranks predictors.
- **Skin-only skeletons against MRI bones** (`validation/runs/mri_bones_3dbones/`, `docs/person-model.md`):
  - The skin-only predictions shipped with the 3DBones release (SKEL, SKEL-J, OSSO, HIT) scored against MRI-segmented
    bones on its 36 test subjects, with SKEL-J fitted to the bones as the floor. Same-bone distance, female / male:
    SKEL 10.0 / 10.7 mm, SKEL-J 9.3 / 9.7 mm (the paper's figure, which checks the frames and the metric), OSSO
    9.8 / 11.4 mm; floor 3.9 / 4.2 mm. OSSO's tibia is the closest of the three (p < 0.001); femur and pelvis level.
  - The SKEL column is `person bones`' best case (a perfect body surface). Surface distance is not joint-centre
    error, and the MRI's 20 mm slices cannot check segment lengths: both still need other ground truth.
  - The release's data, meshes and subject ids stay out of the repository; the scripts say where to get the data
    and stop without a traceback when it is missing (`--selftest` runs without it).
- **Knee joint load, the first slice of the load model** (`docs/joint-load.md`, `rehabtwin/joint_load.py`,
  `rehabtwin joint-load`):
  - OpenSim Joint Reaction on the muscle stage: tibiofemoral compression per knee (peak in N and ×BW, flexion
    at the peak, impulse), shear, patellofemoral force. A test pins frames and signs: with ideal torque
    actuators instead of muscles the reaction is the leg's ground force less the shank and foot weight.
  - Scenarios within one person on the same motion: fat change from the DXA regional table (no body-weight
    slider; spread by each region's fat, labelled as an assumption), stronger muscle groups (reported as effort,
    with the load change shown as it comes out), both. Every scenario re-run under a ±0.10 ground-force split.
    Messier et al. 2005 (about 4:1 in walking) quoted beside the fat scenario, never as output.
  - Per-knee diagnostics: muscles at capacity, reserve share, ground-force fit at the peak, compression by source
    (closes to < 1 N on the synthetic squat), quadriceps moment arm, peak against the instrumented-implant band
    (Bergmann et al. 2014: 4.3 BW). A knee's change, and its effort, are stated only when it is reportable; the
    impulse only when the whole rep holds.
  - Synthetic squat (synthetic truth only, no clinical validation; illustrative DXA): left knee reportable, fat
    −5 kg −6.9 % (body mass −6.9 %), left quadriceps at 120 % +3.9 % with effort 44 → 38 %; right knee not
    reportable (vastus lateralis at capacity). Real OpenCap squat: neither knee reportable (ground forces don't
    fit at the peak, 4–5 muscles at capacity), so no change is stated.
- **Review follow-ups:** catalog now 117 repos (G-06 closed: `utahmobl/opencap-monocular`, PolyForm Noncommercial
  1.0.0 per its LICENSE file; `davidpagnon/Sports2D`, BSD-3-Clause). `docs/validation-results.md` opens with the
  "synthetic results, no clinical validation" caveat. A test pins that the twin manifest carries safety flags and
  anatomy blocks only from records (no placeholder `not-assessed` entries). Provenance is for clinician-facing
  outputs; patient-facing text shows only the constant check prompt. Merged HarmannBitte `b69f6d8`.
- **Skeletal alignment: the person's own knees, legs and shoulders** (`docs/person-model.md`,
  `rehabtwin/alignment.py`, `rehabtwin person alignment`):
  - Every session estimates its standing frame from the camera (`qc.json` → `static_alignment`): knee frontal
    angle (+ valgus), standing knee flexion, leg lengths, pelvic obliquity, shoulder height and reach. Labelled
    estimated, uncertainty not yet measured; screening only, never applied to the model
    (`person screening` keeps it).
  - Limb alignment from imaging or a clinician in the twin manifest's `limb_alignment` format (`person
    alignment`): per side `mechanical_axis_hka_deg` (deviation from straight, + valgus), torsion, neck-shaft,
    segment lengths, carrying angle, each with its `source` (EOS/CT/MRI/radiograph: B, A approved; clinical
    measurement: C, B approved). A camera source is refused. Only this record can say the alignment is
    structural.
  - Sessions with `--person` turn each knee joint's frame on the femur so the model's hip-knee-ankle angle on its
    joint centres is the recorded one.
  - Synthetic genu valgum (10° / 7°; synthetic truth only, no clinical validation): with a limb-alignment record
    of the true angles, knee FPPA error 6.7° → 0.8°, hip rotation 3.6° → 0.8°, subtalar 14.2° → 1.0°, marker fit
    14.0 → 8.4 mm. The person's bone lengths alone changed nothing.
  - Posture rules can be `"relative_to": "standing"`: the squat template's knee valgus cue is now 10° beyond the
    person's standing knee angle. `cues` and `lsl-live` take the standing values from the session's static
    pose.
- **One contract with the anatomy audit** (`docs/accuracy.md` red lines, `docs/person-model.md`):
  - Screening holds: a camera-estimated standing knee angle beyond 6° (where no limb alignment is on record)
    holds that knee's cues for a clinician-set target, with the prompt "worth getting checked by a
    professional". Prompts never name an imaging test. A structural record holds the same way.
  - Clinician safety flags (`person safety-flags`, `rehabtwin/safety.py`): recorded only with `set_by:
    clinician`; active unless cleared (suspected and not-assessed hold too); the whole flagged region gets no
    posture cues and no assistance what-ifs. An unrecognised region holds every joint.
  - Assistance what-ifs follow bone quality: a clinician's `exo_torque_derating_factor` scales assist torque and
    passive stiffness; low bone density without one refuses them.
  - `person manifest` exports the person model as a twin manifest, checked against the schema, with provenance
    per block. The person schema's `alignment` block is replaced by `limb_alignment`, `alignment_screening` and
    `safety_flags`.
- **Kinect v1 depth viewpoint** (`docs/kinect-v1.md`; not yet run on a real sensor):
  - `pipeline/capture/kinect_v1`: a Windows recorder (Kinect for Windows SDK 1.8, built with Windows' own C#
    compiler). It writes colour, depth registered to the colour grid, raw depth, the SDK skeleton, floor plane
    and accelerometer.
  - `rehabtwin kinect`: lifts MediaPipe keypoints with that depth, leaves occluded joints empty, takes gravity
    from the floor in the depth, and detects a mirrored stream from the SDK skeleton.
  - Tested on rendered synthetic recordings, and the recorder against a fake sensor under Mono.
- **BEDLAM2 as a body-type testing ground** (`docs/bedlam2.md`, `pipeline/adapters/bedlam2.py`; the data
  stays outside the repo): on 1,526 SMPL-X bodies (BMI 17.7–43.2), the skin-to-joint-centre distance the
  Kinect path adds grows with BMI, not just height. It is now height × (a + b × (BMI − 25)), with residual
  SD ≤ 0.32 cm (height alone: hip 1.6 cm SD, up to 5.5 cm short above BMI 30). `rehabtwin kinect --mass-kg`
  provides the BMI.
  - Squat visibility (32 squats, BMI 19.5–42.1, virtual front-facing Kinect): knees and ankles are lifted
    within 3 cm in ≥ 90% of frames at every depth. In deep squats only 64% of hips are, because the thigh
    hides the hip; 24% are wrong by 3–20 cm, which the 0.2 m check cannot catch, and 38% above BMI 30.
  - Segment-length check (`kinect.SEGMENTS`, `--segment-lengths`): a hip not at the person's thigh length
    from its knee is placed on its own line of sight at that length. With MediaPipe-like noise, deep-squat
    hips within 3 cm go from 64% to 81%, and those more than 10 cm off from 15% to 2%.
- **Person model** (`docs/person-model.md`, `rehabtwin person init/set/build/attach/show`): one versioned folder per
  person with their bones, dated measured height and mass, and what fills each twin layer at which tier.
  - `person build` takes a calibration session's scaled model. `process --person` re-applies its per-body scale
    factors instead of fitting new ones; markers are still placed per session. `kinect --person` takes height,
    mass and thigh lengths from it. `person attach` takes an imaging-personalised model with its provenance
    record (Tier B/A), used unscaled with masses following the measured body mass.
  - A recording's size is checked against the person's bones. A single-camera recording, whose size is a guess,
    is scaled to the person; a calibrated one more than 10 % off is refused.
  - Real video (OpenCap subject 2, one squat trial): the camera setup alone moved the right thigh between
    34.7 and 46.0 cm. With the 5-phone session's bones, the 3-phone session's sagittal pelvis, hip and trunk
    agreement improved by 0.4–1.8°, ankles 0.2–0.5° worse. Without the size check, the bones made the 1-phone
    session worse (knee 20° → 48°).
- **Muscle capacity scaled to body size** (`rehabtwin/capacity.py`): `muscles` and `strength` scale the 80 leg
  muscles' maximum force with the Handsfield 2014 limb muscle volume (from measured height and mass) over fibre
  length. Previously every body had the generic subject's leg strength. Trunk muscles stay generic. It needs a
  measured mass and a height; `--generic-capacity` turns it off; BMI > 30 is flagged as likely overestimated.
  `strength` calibrates on top of it.
- **Body surface from the Kinect** (`rehabtwin person shape`, `rehabtwin/shape.py`, `docs/bedlam2.md` result 4):
  an SMPL-X body fitted to the person's depth pixels in standing frames. On 45 synthetic BEDLAM2 bodies,
  one frame gives height within ±1.4 cm and mass within ±5.2 %, and segment lengths about 3× closer than
  height and BMI predict.
  - The recorder now saves the SDK player index (`player_registered.u8`) to tell the person from the room.
  - Fits are checked against measured height and mass before the person model takes them. The layer stays
    Tier C until a scan of a real person checks it.
- **Muscle size, muscle quality and bone density from imaging** (`rehabtwin person muscles` / `person bone`):
  - MRI/CT muscle volumes and MRI fat fractions per muscle or group replace the height-and-mass regression
    where they measure: Fmax = σ·V·q/lopt, with the model's own reference volumes (7,089 cm³ per leg, 97 %
    of the regression's, which checks its units).
  - Fat fraction scales the contractile part against healthy young muscle (quadriceps 2.6 %, gluteal 5.4 %).
  - DXA T/Z-scores or QCT vBMD get the standard screening category. Device and correction what-ifs show low
    or unmeasured bone density. Raw CT Hounsfield units are refused as a bone density.
  - Tested on MyoSegmenTUM thigh MRI with dynamometry (`adapters/myosegmentum.py`, `docs/person-model.md`):
    with measured quadriceps volume and fat fraction, predicted knee-extension torque correlates with the
    dynamometer at r = 0.86 (the height-and-mass regression 0.44), and the person-to-person error halves
    (16 % → 10 %). The regression gave these adults a third more quadriceps than measured and the patients
    twice theirs. The database's own volume table is wrong (1 mm pixels, overlapping slices counted twice);
    the adapter recomputes the volumes from the masks with the DICOM geometry (`docs/upstream-issues.md`).
- **Augmenter markers corrected for the Pose2Sim model** (`mediapipe_lstm_pose2sim`; `docs/validation-results.md`
  §4 point 6, `docs/upstream-issues.md`).
  - The problem: Pose2Sim's `Markers_LSTM.xml` reuses OpenCap's LaiUhlrich2022 marker locations on a model
    whose tibia is 3 cm longer and whose hip joints sit 2 cm elsewhere. The malleolus markers sat 4.5 cm above
    the ankle, and scaling made the shank 10 % too long: 0.54 m on OpenCap subject 2, against 0.49 m from
    OpenCap, SKEL and Winter's proportions.
  - The fix: new config options `marker_rescale` (move markers along their body by the bone-length ratio) and
    `marker_to_joint` (put a joint-centre marker on the joint).
  - The result against OpenCap's IK, 5 phones: pelvis tilt 6.0° → 2.8°, lumbar 7.1° → 3.9°, hip flexion
    13.9° → 8.2°, knee 9.3° → 7.4°; ankle 4.9° → 5.4°; IK marker RMS 2.36 → 2.07 cm. 3 phones alike. One
    phone mixed.
- **Bones from body shape (SKEL)** (`rehabtwin person bones`, `pipeline/rehabtwin/skel_bones.py`,
  `docs/person-model.md`): SKEL's anatomical joint centres for the person's body become the person's
  per-body scale factors. The body is an SMPL surface fitted to Kinect depth (`person shape --smpl-model`),
  or the SMPL body of their measured height and mass. The groups are the video measurement set's.
  - Without a session-built model they become the person's model; otherwise they are stored next to it with
    the difference per segment.
  - Synthetic test (`adapters/bedlam2_skel.py`): on 45 bodies with BMI 17–44, SKEL bones from one depth frame
    were within 0.2 cm of the true body's on average (worst 1.1 cm; 0.4 cm with the measured height). From
    height and mass alone: 0.4–0.5 cm; from height alone: up to 4.8 cm (hip width). That is the chain's
    error against SKEL, not against bone.
  - On OpenCap subject 2, SKEL and OpenCap's own result put the shank at 0.49 m, ours at 0.54 m (see the
    marker fix below). SKEL's upper arm is short against every other source.
  - `adapters/body_model_files.py` converts the SMPL/SKEL/OSSO downloads (Python pickles) to plain arrays
    with an unpickler that only builds arrays and refuses anything else.
  - `person shape --smpl-model` fits SMPL (SKEL's skin) instead of SMPL-X.
- **Leg muscle from age and sex, or from a DXA scan** (`rehabtwin person set --age-years --sex`,
  `person dxa`; `docs/person-model.md`): each leg's muscle volume comes from the best source the person model
  holds. In order: MRI/CT per muscle, a whole-body DXA per leg, age, sex, height and mass, then height and mass.
  Reports and `capacity.json` (`leg_source`) say which.
  - Without a scan: leg lean mass from age, sex, height and mass, fitted on 7,528 NHANES 1999–2002 adults
    (7.5 % mean error on the held-out cycle; `adapters/nhanes_strength.py fit-default`). It gives a
    70-year-old woman 0.63× and the generic young man 0.85× the Handsfield volume. On MyoSegmenTUM, measured /
    predicted quadriceps goes from 0.75 to 0.93.
  - With DXA: each leg's muscle from its lean mass (0.78 × lean − 1.07 kg for both legs, McCarthy 2023,
    against whole-body MRI). Segment masses of the muscle model follow the scan's regional masses, with the
    total kept. Regional fat fills the soft-tissue layer (Tier B), and a `bone_density` part is classified
    as by `person bone`. Records in grams, of another body (more than 15 % off the measured mass), or not
    from a DXA are refused.
  - Against NHANES knee-extension strength (2,104 adults aged 50+), the correlation goes from 0.65 (height
    and mass) to 0.75 (age and sex) and 0.79 (DXA). The person-to-person spread goes from 28 % to 24 % and
    22 %: a scan narrows the estimate but does not measure strength (`rehabtwin strength` does).
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
- Joint load & stress scenario model designed: `docs/design-joint-load-stress-model.md` (OpenSim Joint-Reaction pipeline, Messier-anchored fat scenarios, honest muscle-effort/stability outputs) + illustrative demo `examples/joint-load-demo/index.html`
- **Anatomy-audit integration pass**: audit mechanisms folded into `schemas/twin-manifest.schema.json` (spinopelvic parameters, limb alignment/torsion, muscle parameters with separate weakness/contracture/reflex-gain groups, bone quality + exo derating, devices/prostheses, clinician-only safety flags, body state), `breathing` block added to `schemas/session.schema.json` and the synthetic example, integration table + red lines in `docs/accuracy.md`, manifest contract in `docs/architecture.md`; new schema test (12 tests)
- **Anatomy audit COMPLETE (202/202)**: Batch 8 (niche spine + cross-cutting, 13 issues), `docs/anatomy-audit-batch8-niche-spine-crosscutting.md`, with five-mechanism closing synthesis
- Anatomy audit Batch 7 (neuromotor NM-01…NM-15) completed: `docs/anatomy-audit-batch7-neuromotor.md` (189/202 researched)
- Anatomy audit Batch 6 (arm/hand + bone/joint, 22 issues) completed: `docs/anatomy-audit-batch6-armhand-bonejoint.md` (174/202 researched; MS-03 formally closed)
- Anatomy audit Batch 5 (head/neck + chest remainder, 20 issues) completed: `docs/anatomy-audit-batch5-headneck-chest.md` (151/202 researched)
- Added 7 previously research-note-only repos to the catalog (IDs 109–115: Motion-X, LODGE, ChoreoMaster, MotoricaDanceDataset, 3dpredictsim, Synergy-Based-Foot-Model, Foot3D) with full documentation-standard metadata; catalog now 115 repos
- Full repo-documentation pass: licenses + license provenance for all 108 catalog repos (and fat-distribution models), live metadata refresh for repos 1–52 + gap entries, expanded generated catalog with per-repo detail sections, documentation standard now enforced by validator and tests
- Anatomy audit Batch 4 (whole-body/muscle, 32 issues) completed: `docs/anatomy-audit-batch4-wholebody-muscle.md` (131/202 researched; muscle-parameter pipeline finding)
- Anatomy audit Batch 3 (shoulder SH-01…SH-15) completed: `docs/anatomy-audit-batch3-shoulder.md` (99/202 researched; scapula = model-inferred rule)
- Anatomy audit Batch 2 (hip/knee/foot, 57 issues) completed: `docs/anatomy-audit-batch2-hip-knee-foot.md` (84/202 researched; Torsion Tool adoption identified)
- Anatomy audit Batch 1 (spine SP-02…SP-19) completed: `docs/anatomy-audit-batch1-spine.md`, checklist statuses updated (27/202 researched)
- Master anatomy-issues checklist (`docs/anatomy-issues-checklist.md`): 202 posture/movement-relevant anatomical issues in 13 groups (incl. niche/rare layer) with per-issue model-audit status
- Research note on breathing tracking: diaphragm→rib-cage/abdominal mechanics, OEP/RIP/depth-camera tracking, diaphragm ultrasound (`docs/research-breathing-tracking.md`)
- Research note on detailed anatomy models: foot arch/flat feet, articulated spine bending, ribcage/diaphragm breathing (`docs/research-detailed-anatomy-models.md`)
- Fat-measurement reference notes (`fat-distribution/measurement-notes.md`): method hierarchy, twin metrics, LiDAR conclusiveness
- Research note on dance→3D mapping and motion data beyond squats (`docs/research-dance-3d-motion.md`)
- New separate `fat-distribution/` folder: 12 fat/adipose-distribution models (8 code repos, 2 paper-only, 2 closed references) with Tier A/B usage rules
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
