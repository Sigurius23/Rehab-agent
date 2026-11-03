# Changelog

## Unreleased
- **Sensor sole, open hardware** (`hardware/sensor-sole/`, CERN-OHL-S-2.0). It is a pressure-sensing sole for
  five-toe barefoot shoes, designed for a Vibram FiveFingers EU 42. The generator can produce other sizes and
  personal outlines; fit has not been demonstrated at any size. Design only: nothing has been fabricated or
  measured.
  - `sole_gen.py` builds the sole from a foot spec:
    - the outline with five toe tabs;
    - 16 sensing regions anchored to anatomy (Voronoi tiles; 78–83 % of the sole outline across EU 36–47 in
      the layout-only sweep, a geometric figure);
    - interdigitated electrode combs;
    - a routing plan along region seams, with bundles carved at their true width;
    - a flat tail and checks (fit, clearances, vias outside the toe-joint bend zone, connected combs).
  - It exports SVG, DXF (KiCad layers) and JSON.
  - A layout-only sweep over EU 36–47 passed the layout checks. That sweep predates copper routing; see the
    copper results below.
  - **Copper routing and KiCad export.** `sole_route.py` routes real copper: sense lines on B.Cu as a planar
    tree, a negotiated fine-grid pass, the common net on F.Cu, vias, stubs and jumpers. `kicad_export.py`
    writes KiCad 7 boards with the design rules in the `.kicad_pro`.
  - **`verify_board.py`** checks each board:
    - DRC with the project rules;
    - the region-to-contact map, traced through the physical copper without trusting net names;
    - physical contact numbering;
    - coverlay openings;
    - provenance (the generator hashes in the title block).
    `make_fab.sh` writes Gerbers only if the check passes.
  - **Fixes from the review:**
    - toe2's line split its comb. By geometric estimate, its combs interleaved over 38 % of its tile (47 % of
      its region outline). Toe vias now sit at the tab base, which brings it to 76 % (85 %). This is a
      geometric estimate, not a measured sensitivity.
    - The left board's contact pads were numbered opposite to the physical order. Both feet are now numbered
      physically, with one channel map per side.
    - Coverlay opened per comb piece would have left uncuttable 0.2 mm webs between fingers. There is now one
      opening per region, notched where tracks land.
    - The source stamp is taken when the generator starts.
  - **Lane planner fixed for other sizes and personal feet**, without relaxing any rule. Four changes, each
    found by measuring the plan and the fine-grid pass:
    - vias kept off and clear of the trunk;
    - the fine-grid pass kept within 3 mm of the plan and out of the 2 mm edge margin;
    - a fillet per lane at turns;
    - 5 mm fillets and a clear area at the tail root.
  - **Results.** All eight checked boards pass `verify_board.py`: EU 37, EU 42, EU 46 and the 14-region
    personalised example, each right and left. Each needs 16–18 vias and no jumpers, and the fine-grid pass
    settles in one round. Before the fixes, EU 37 and EU 46 failed on clearance, and the personalised foot
    had seven sense lines shorted in two groups. Passing the checks is not a release for fabrication.
  - **Checker** (`verify_board.py`):
    - fails closed on the DRC report (`tests/test_verify_drc.py`);
    - lists the library warnings one per generated footprint;
    - measures comb copper under coverlay from the pad geometry, per region;
    - checks against the configuration written on the board;
    - ties each channel map to the board's sha256 and the ID printed on its tail.
    `make_fab.sh` marks its output NOT-RELEASED.
  - **Identity, reproducibility and checker confidence** (`VERIFICATION.md`):
    - **Design IDs.** The printed ID is now `<label> <side> <first 10 hex of the design hash>`. The old ID
      (size or foot file, side, git revision) was shared by different inputs: a measured foot and a heel-exit
      sole printed the same ID as the default EU 42.
    - **Reproducible export.** KiCad's UUIDs are seeded from the design hash. EU 37 R and the personal example L,
      regenerated from the recorded commit in a clean worktree, are byte-identical to the committed boards.
    - **Deployed maps.** `channel_map.py` resolves a printed ID to exactly one intact map for the right foot,
      and refuses anything else (CI tests). Maps for passing boards are in `maps/`.
    - **All eight boards committed**, with provenance: inputs, run-start generator hashes, tool versions,
      project rules, file hashes and checker version (`kicad/MANIFEST.json`).
    - **Negative controls** for the checker (`tests/test_verify_negative.py`).
    - **Copper-free margin** as DRC keep-outs on the board.
    - **Geometry risks quantified:**
      - tightest via clearance 0.189 mm (rule 0.15);
      - the synthetic foot's 8.7 mm stub;
      - EU 46's 0.43 mm² of F.Cu-over-B.Cu crossings in the bend zone;
      - the tail-root widening, 16 mm wide 1 mm past the sole edge.
  - `FABRICATION.md` compares the assumptions with two fabricators' published flex capabilities. It lists the
    open questions and a draft enquiry, which has not been sent. Nothing is released for fabrication.
  - `DESIGN.md` covers the fit, layer stack, pod electronics (prototype on a XIAO nRF52840 Sense), data
    integration over LSL, the calibration and validation plan, and the open decisions.
  - `COMPARISON.md` sets the sole against OpenGo and three open insoles, keeping documented features apart from
    measured performance. It covers four OpenGo validation studies:
    - three on 13-sensor insoles;
    - McNeese et al. 2026 on 16-sensor insoles (10 healthy adults, submaximal jumps, values at peak force only).
      Hardware revision and firmware are not stated, so its match to the product sold now is unconfirmed.
    Our sole is untested for physical sensing, fit and durability. A table sets out what data each system gives
    a digital twin. Two GRFMS entries were corrected against the paper: its reference was force
    platforms, not motion capture, and it does use radio.
  - `DESIGN.md`, section 9: proposed additions, as a plan only. The 16-region sole stays the baseline.
    - a higher-resolution candidate in parallel, with what 32 regions would cost in contacts, tail width and
      routing;
    - readout requirements for more channels;
    - partial-loading and moisture tests;
    - a calibration record per sole;
    - camera synchronisation to measure;
    - five-toe mechanical requirements (the toe slits end in a 1.0 mm radius at EU 37, 42 and 46);
    - validating both candidates the same way.
- **Flaky live-chain test fixed** (`test_live_chain_posture_to_suit_payloads`). It had failed in CI on nearly every
  run since 2026-10-24, and once in a local full-suite run.
  - The engine sent its cue correctly, but the suit bridge sometimes had not yet connected to the cue stream. LSL
    drops what is pushed before a listener connects, and finding a new stream takes a resolver round, about 0.5 s
    or longer under load. Timed locally, the bridge connected only about 0.12 s before the first cue.
  - `run_live` has a new `wait_for_cue_consumer_s` option (default 0, so behaviour is unchanged). It waits for a
    listener on the cue stream before reading posture.
  - The test now chains the links: the engine waits for the bridge, and the replay waits up to 30 s for the engine.
  - With the suit bridge started 3 s late, the old chain failed 3 of 3 runs and the new one passed 3 of 3. The test
    passed 10 of 10 runs with all four cores busy.
- **Catalog stars and forks for the foot repos (#118–#136).** The GitHub API is still not open to this session, so 16
  of the 19 pending snapshots were filled from the ecosyste.ms mirror of GitHub metadata. Each entry's notes give the
  mirror's sync date, which ranges from 2023-05-01 to 2026-11-01.
  - The mirror's primary language agrees with the clone-based estimate for 15 of the 16. For
    DuduPiglet/insole-3Designer it reports none, and the catalog keeps Python from the clone.
  - DuduPiglet/insole-3Designer is a fork of Polycron/orthotic-3D-insoles, which has no licence file either.
  - MiniDraco/footscan, JoshKirk800/insole-pipeline and ishaanko/archy are not in the mirror. Their snapshots stay
    null and are stated as pending (`SNAPSHOT_PENDING` in `scripts/validate_catalog.py`).
  - Licences were not changed. The mirror's licence field agrees with the licence files read from the clones. It
    reports "other" for colmap and StandardCyborgCocoa, whose licence files are custom or set per subdirectory.
- **3DBones licence status recorded exactly.**
  - The project's licence page displays "License Text" but contains no licence text (checked by the project owner,
    2026-11-02), and no licence file was found in the release.
  - Until written terms are obtained: internal research benchmarking only, no redistribution, no product training.
  - `run_bench.py`'s data message still mentions "non-commercial research terms". That code string is left
    unchanged and is flagged in the impact assessment.
- **Hip summary note reworded** (`hip_centres.py`, `validation/results/mri_bones_3dbones_hip.json`). The nine
  complete hips are now described as a development check that has informed the work, not a pristine test set.
  - The summary was regenerated from the original per-subject output of 2026-10-29.
  - Before the change, the unmodified script reproduced the committed summary byte for byte.
  - After it, the only difference is that note: no number and no case selection changed.
- **Documentation corrections:**
  - The leg-model downstream results are limited to the tested synthetic squat.
  - The split sensitivity is quoted for both knees: right about ±18 %, not reportable in the illustrative-DXA run;
    left about ±26–27 %, reportable.
  - The nine complete MRI hips have informed this work and are described as a development check, not a pristine
    test set.
  - Calibrations are to be judged on data that has not shaped the work. No code, schema or results changed.
- **Foot models are candidates, not adoptions** (`docs/research-detailed-anatomy-models.md`, catalog #113–#115): the
  four-segment arch foot and the synergy-based foot enter a comparison and validation; selection follows that work.
  3dpredictsim (MIT; its `four-segment_foot_model` branch is newer than master) and PredSim (AGPL-3.0, now catalog
  #136) keep separate licences, and each model asset and dependency is checked on its own. The synergy model has no
  licence file. Catalog: 136 repos.
- **Catalog: 135 repos.** 18 foot-personalisation repositories added (ids 118–135): foot capture and reconstruction
  (FOCUS, FOUND, FIND, AR_footcapture, StandardCyborgCocoa, OpenScan3, SynFoot, FootScan), insole and shoe design
  (insole-pipeline, insole-3Designer, both OpenShoeDesigners, archy, SoleFit) and general reconstruction and mesh tools
  (COLMAP, OpenMVS, MeshLab, PyMeshLab). Licences were read from each repository's licence file in a git clone on
  2026-11-02. The GitHub API was not reachable then, so stars and forks are null and say so in each entry's notes; the
  validator and test accept that only when stated (`scripts/enrich_metadata.py` fills them where the API is
  reachable). Meshroom's licence corrected to MPL-2.0 (`LICENSE-MPL2.md`, missed by the earlier check). Foot3D's
  notes now say its dataset comes by request form with no data licence in the README.
- **Leg-bone models compared** (`validation/runs/mri_bones_3dbones/leg_priors.py`, `validation/runs/leg_prior_downstream.py`,
  `docs/joint-load.md`):
  - SKEL, SKEL-J and OSSO on the same 72 MRI legs, with the same geometry on every mesh. SKEL and SKEL-J agree
    within about 1 %. SKEL against OSSO: about 3 % per segment (OSSO's shank 12 mm longer and pelvis 9 mm wider,
    consistently; thighs up to 29 mm apart either way). Neither is closer to the skeleton fitted to the bones.
  - Put into the synthetic squat: the OSSO-typical differences move the absolute peak knee compression by 12–14 %.
    The within-person changes (fat −5 kg, quadriceps at 120 %) move by at most 1 percentage point and keep their sign.
    Knee angle error rises by at most 0.2°; pelvis tilt and hip flexion take the error (up to 2.5°). Marker fit
    notices a wrong thigh (up to +2 mm RMS) but not a wrong hip width.
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
