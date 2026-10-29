# The person model: one body across sessions

**Status:** built and tested on synthetic sessions and on one real squat (OpenCap LabValidation subject 2;
results below). The bones it stores come from video, so they are Tier C until a person's model is checked
against imaging.

A digital twin is the same body in every session. Before this, every `process` run fitted the generic model
to that session's own frames. The bones then depended on the camera setup. These are segment lengths
(joint centre to joint centre, cm) of the models scaled from one real squat trial of one 1.96 m person,
processed with different camera subsets (`docs/validation-results.md` §4, all with the LSTM augmenter):

| Setup | thigh R | thigh L | shank R | hip width | upper arm R |
|---|---|---|---|---|---|
| 5 phones | 44.6 | 44.0 | 54.2 | 20.3 | 36.9 |
| 3 phones | 46.0 | 45.6 | 54.3 | 20.3 | 38.2 |
| 2 phones | 42.3 | 41.7 | 54.9 | 22.9 | 28.7 |
| 1 phone | 34.7 | 38.3 | 47.0 | 19.3 | 29.4 |

From one phone, the right thigh is 10 cm shorter than from five, and 3.6 cm shorter than the left. A progress
chart comparing sessions recorded with different setups would show these differences as change in the
person.

## What a person folder holds

```
PERSON/person.json    format rehabtwin-person/1 (schemas/person-model.schema.json), versioned
PERSON/model.osim     the person's model
PERSON/history/       every earlier person.json
```

`person.json` records each value with where it came from, and each twin layer (`docs/accuracy.md`) with
what fills it and its tier:

| Layer | Filled by | Tier |
|---|---|---|
| bone geometry | generic bones scaled per segment in one calibration session; or scaled to SKEL's joint centres for the person's body surface or height and mass (`person bones`); or an imaging-personalised model | C; B/A with a provenance record |
| joint centres | scaled with the bones; markers placed on the static frames | C; B/A from the personalised model |
| surface shape | SMPL-X body fitted to standing Kinect depth frames (`person shape`), checked against measured height and mass | C until checked against a scan |
| kinematics | per session (not stored) | per session's validation |
| muscle | Rajagopal leg muscles; force from measured volume and fat fraction where imaged (`person muscles`), else each leg's volume from a DXA scan (`person dxa`), from age, sex, height and mass, or from height and mass; trunk generic | C; B/A when all leg muscles are imaged |
| soft tissue | regional fat and lean mass from a DXA scan (`person dxa`), which also sets the segment masses; tissue deformation not modelled | B; A with a reviewed report |
| bone density | DXA or QCT result with its screening category (`person bone`) | B; A with a reviewed report |
| joint alignment | knee HKA, torsion and segment lengths from imaging or a clinician (`person alignment`); the camera's standing estimate is kept for screening only (`person screening`) | B; A with `approved_by`; clinical C/B. The camera estimate is never a tier of this layer |
| safety flags | a clinician's list (`person safety-flags`), recorded as given | not a tier: the clinician's record |

Measured height and body mass are stored with their dates. A mass entered as assumed is kept, marked
`measured: false`, and never used where a measured mass is required. Age (`--age-years`) is stored with the
date it was given and counts on from there; with sex (`--sex female|male`) it sizes the leg muscles when no
scan does (below).

## Workflow

```bash
# once: start the folder with measured height and mass
python -m rehabtwin person init people/P01 --person-ref P01 --height-m 1.80 --mass-kg 75

# calibration session: the best setup available (three phones + LSTM augmenter, or Kinect + phones)
python -m rehabtwin process calib_aug.npz out/calib --exercise squat --mass-kg 75 --height-m 1.80 --person-ref P01
python -m rehabtwin person build people/P01 out/calib

# every later session, any setup: the person's bones, this session's motion
python -m rehabtwin process phone_aug.npz out/s02 --exercise squat --person people/P01
python -m rehabtwin kinect C:\rec\s03 C:\rec\s03\mediapipe.npz s03_seq.npz --person people/P01

python -m rehabtwin person set people/P01 --mass-kg 73.5     # mass changes during rehab
python -m rehabtwin person show people/P01

# records from imaging and the clinician (see "Skeletal alignment" below)
python -m rehabtwin person alignment people/P01 P01_limb_alignment.json
python -m rehabtwin person safety-flags people/P01 P01_safety_flags.json
python -m rehabtwin person manifest people/P01 --out P01_manifest.json   # the twin manifest
```

`person build` refuses:
- a session of another person;
- a synthetic session;
- a session whose re-processing did not finish;
- an assumed body mass;
- a session that was itself processed with a person model.

### What `process --person` does

- It applies the stored per-body scale factors to the generic model with OpenSim's manual scaling instead
  of fitting new ones, and checks that the scaled model reproduces them (`qc.scaling`).
- It checks the recording's size against the person's bones first (see "One phone needs its size fixed
  first" below): a single-camera recording is scaled to the person, and a calibrated one that disagrees by
  more than 10 % is refused.
- Markers are still placed on this session's static frames. Clothing and keypoint placement differ between
  sessions; the bones do not.
- Height and mass come from the person folder unless given. A mass the marker augmenter was run with takes
  precedence, because it is that day's.
- `session.json` records the person model version and the sha256 of its `person.json`
  (`person_model`), so a later rebuild of the person model is visible.

It refuses:
- another person's folder;
- a synthetic person with a real recording, or the other way round;
- a config whose generic model is not the one the scale factors belong to (by sha256).

### Imaging-personalised models (Tier B/A)

```bash
python -m rehabtwin person attach people/P01 P01_msk.osim --provenance P01_provenance.json
python -m rehabtwin process s04_aug.npz out/s04 --person people/P01 --tier A
```

The provenance record (`pipeline/rehabtwin/tiers.py`) must name the same person, and its `model_sha256`
must match the file. The personalised model is then used with unit scale factors; only its segment masses
follow the session's measured body mass, with the mass distribution kept. The session's tier comes from
the same record.

## Muscle capacity scaled to body size

OpenSim's scaling lengthens fibres and tendons with the bones but leaves every muscle's maximum isometric
force (Fmax) at the generic subject's value. A 55 kg, 1.60 m person and a 110 kg, 1.90 m person had the same
leg strength. `muscles` and `strength` now scale it (`pipeline/rehabtwin/capacity.py`):

    Fmax_person = Fmax_generic × (V_person / V_generic) × (lopt_generic / lopt_person)

- V is the total muscle volume of one leg from Handsfield et al. 2014 (MRI of 35 lower-limb muscles in 24
  young healthy adults): V ≈ 47 · mass · height + 1285 cm³ (kg, m). Each muscle keeps its share of it.
- lopt is the optimal fibre length, which scaling has already lengthened with the bones; dividing the volume
  by it gives the cross-section.
- The generic leg muscles (Rajagopal et al. 2016, also the Pose2Sim model's 80 leg muscles) were built from
  the same regression for a 75.3 kg, 1.70 m subject, which is the reference.
- The 238 trunk muscles and the arms come from other sources and keep generic forces.

When the person model holds age and sex, or a DXA scan, those replace this regression
([below](#leg-muscle-from-age-and-sex-or-from-a-dxa-scan)); the regression is what is left when nothing else is
known. It runs only when the session's mass is measured and its height known (`process --height-m` or `--person`).
It does not run on a personalised model, which carries its own muscle parameters. `--generic-capacity`
turns it off. `capacity/capacity.json` records the factors; reports say which capacity a result rests on.

In tests (`test_leg_capacity_scales_with_body_size`), the 55 kg, 1.60 m body gets weaker legs than the
generic model and the 110 kg, 1.90 m body stronger ones. Each scaled Fmax matches the formula to 1e-6, the
trunk is unchanged, and scaling a model twice is refused.

What it is and is not:
- **A population estimate, and a poor one for individuals.** On 15 healthy adults' thigh MRI it gave a third
  more quadriceps than measured, ±15 % between people, and the patients twice theirs (MyoSegmenTUM, below).
  It gives the leg the muscle an average young, healthy adult of this height and
  mass has. Age, training, disuse and injury are not in the regression, which matters in rehab.
- **Not reliable above BMI 30.** Extra body mass is then mostly fat, so the regression likely overestimates
  muscle; results say so.
- **A better base for dynamometry.** `strength` now calibrates the tested groups relative to the
  body-size-scaled model, and the untested muscles keep body-size capacities instead of generic ones.

## Surface shape from the Kinect

```bash
python -m rehabtwin person shape people/P01 C:\rec\calib01 C:\rec\calib01\mediapipe.npz --smplx-model SMPLX_NEUTRAL.npz
```

It fits an SMPL-X body (16 shape parameters, a pose per frame) to the person's depth pixels in up to two
standing frames, 1 s apart (`pipeline/rehabtwin/shape.py`; `docs/bedlam2.md`, result 4):
- **Standing frames:** knees within 20° of straight, all 12 keypoints seen.
- **The person's pixels:** the SDK player index, which the recorder now saves (`player_registered.u8`).
- **Floor:** fitted to the depth with the person's own pixels left out.
- **Checks:** the fit's height and mesh-volume mass are compared with the person's measured ones and stored
  with the result. A fit more than 3 cm or 10 % off, or with fit warnings, is refused.
- **Height:** it is left out of the fit so it can check it; `--use-height` uses it as a prior instead.

What it gives the twin: the body's surface (betas), segment lengths between SMPL-X joints, front
skin-to-joint distances, and a volume-based mass. On 45 synthetic BEDLAM2 bodies the fit got height within
±1.4 cm and mass within ±5.2 % on every body, from one frame. That is unclothed synthetic data fitted by the
model that made it, so it is a lower bound on the real error. The layer stays Tier C until a 3D scan or
tape measures of a real person check it. The SMPL-X model file is licensed separately and never enters
the repository; `person.json` records its name and sha256.

A smoke test of the whole chain (two BEDLAM2 bodies written as Kinect recordings, standing with arms down,
4 px keypoint noise) stored fits within −0.9 cm and −1.2 % (BMI 25) and −2.8 cm and −2.9 % (BMI 35) of the
true body. It caught one bug on the way: the floor fit had taken the standing legs for the floor and cut
most of the body away, until the person's pixels were left out of it.

## Bones from body shape (SKEL)

A calibration session measures bones from markers that video places on the skin. SKEL (Keller et al.,
SIGGRAPH Asia 2023) predicts them from the body itself. Its skin is SMPL, and its skeleton is the BSM
OpenSim model, a Rajagopal-based full-body model like ours. SKEL regresses the BSM joint centres linearly
from the SMPL body surface. `person bones` turns those joint centres into the person's per-body scale
factors (`pipeline/rehabtwin/skel_bones.py`):

```bash
python -I adapters/body_model_files.py convert DOWNLOADS/ models_npz/     # once: the pickles to plain arrays
python -m rehabtwin person set people/P01 --sex female                    # SKEL is female or male
python -m rehabtwin person shape people/P01 C:\rec\calib01 C:\rec\calib01\mediapipe.npz \
    --smpl-model models_npz/basicmodel_f_lbs_10_207_0_v1.1.0.npz            # SMPL of that sex, fitted to depth
python -m rehabtwin person bones people/P01 --skel-dir models_npz --smpl-dir models_npz
```

- **Body:** the person's SMPL surface from the Kinect (`--source shape`), or, without one, the SMPL body
  nearest the mean shape with their measured height and mass (`--source height-mass`).
- **Joint centres to scale factors:** the same groups as the video measurement set (femur and tibia per
  side, foot, pelvis depth/height and width, trunk height and shoulder width, upper arm, forearm). Each is a
  distance between SKEL joint centres over the same distance between the generic model's body origins.
- **Model:** with no session-built model, or with `--replace`, these factors become the person's model,
  with segment masses scaled to the measured mass. A session-built model is otherwise kept, and
  `skel_bones.vs_model_cm` records the difference per segment. An imaging model is never replaced.
- **Model files:** SMPL and SKEL are licensed separately (non-commercial research) and never enter the
  repository. They come as Python pickles, which can run code when loaded, so
  `adapters/body_model_files.py` reads them with an unpickler that only builds arrays and refuses
  anything else. Only the resulting `.npz` files are loaded.
- **SMPL-X fits don't carry over.** A fit made with `--smplx-model` can't be used: SMPL-X bodies carried
  over to SMPL through a surface correspondence came out 4–8 cm taller, so the surface is fitted with SMPL
  itself.

**What one depth frame gives** (`adapters/bedlam2_skel.py`; synthetic). The test used SMPL bodies with the
heights and BMIs of the 45 BEDLAM2 test bodies (17.7–42.5), 23 female and 22 male, each with its own
proportions; those changed their mass, so the bodies tested span BMI 17.4–44.3. Each was rendered standing in a BEDLAM2 motion frame, as a Kinect v1 2.7 m away sees it, and
fitted with SMPL. The table compares SKEL segment lengths from each source with the true body's, in cm:
bias / mean absolute error / worst.

| Source | thigh | shank | upper arm | forearm | hip width |
|---|---|---|---|---|---|
| one depth frame | +0.0 / 0.2 / 0.9 | −0.0 / 0.2 / 1.1 | +0.1 / 0.2 / 0.6 | +0.0 / 0.2 / 0.6 | −0.0 / 0.1 / 0.3 |
| one depth frame + measured height | +0.0 / 0.1 / 0.4 | +0.0 / 0.2 / 0.4 | +0.1 / 0.2 / 0.6 | +0.1 / 0.2 / 0.5 | −0.0 / 0.1 / 0.4 |
| height and mass | +0.1 / 0.4 / 1.3 | +0.1 / 0.5 / 1.5 | −0.0 / 0.3 / 0.9 | −0.0 / 0.3 / 1.1 | −0.0 / 0.2 / 0.5 |
| height only (SKEL template scaled) | +0.5 / 1.0 / 3.1 | +0.6 / 1.2 / 3.3 | +0.1 / 0.3 / 1.1 | +0.1 / 0.4 / 1.3 | −0.7 / 1.8 / 4.8 |

- **The chain adds little to SKEL's own error.** Fitted height was within 0.6 cm on average (worst 3.0 cm;
  1.1 cm with the measured height as a prior). No fit failed, and the BMI groups were alike (above BMI 35,
  thigh and shank 0.2 cm on average).
- **Height alone is not enough.** It misses hip width by up to 4.8 cm, and leg length by up to 3 cm above
  BMI 30.
- **Lower bound.** The truth bodies come from the model that fits them, unclothed, and their proportions
  vary only as much as SMPL's shape space allows. Real bodies, clothes and the sensor will add error.
- **Not checked against bone.** This measures the chain from sensor to SKEL, not whether SKEL's joint
  centres are where a person's are. That needs imaging (next).

**Against MRI bones: the 3DBones test subjects** (`validation/runs/mri_bones_3dbones/`). 36 adults (22 female,
14 male) with MRI-segmented bones. Each method's skeleton was predicted from the skin alone and shipped with the
release; we scored it, without re-running the method. The metric is the mean distance from the MRI bone points to the
predicted bone of the same name, in mm, over femur, tibia–fibula, pelvis, humerus and radius–ulna. The floor is SKEL-J
fitted to the MRI bones themselves (any bone, as it has no bone labels).

| | SKEL | SKEL-J | OSSO | floor |
|---|---|---|---|---|
| all five bones, female / male | 10.0 / 10.7 | 9.3 / 9.7 | 9.8 / 11.4 | 3.9 / 4.2 |
| femur / tibia–fibula / pelvis | 11.6 / 9.6 / 11.3 | 11.2 / 9.4 / 10.3 | 11.2 / 7.6 / 10.7 | 4.0 / 4.1 / 4.9 |
| worst single bone (pelvis for all three) | 22.7 | 21.8 | 19.6 | |

- **SKEL is what `person bones` uses, and this is its best case.** These SKEL bodies were fitted to the MRI skin,
  so the column assumes a perfect body surface; a depth or phone surface adds its own error.
- **Skin-only prediction is about twice the floor.** Inferring bones from the skin costs about 5 mm on average over
  what the model reaches when it sees the bones.
- **For the leg, OSSO is the strongest.** Its tibia is closer than SKEL's in 33 of 36 subjects and SKEL-J's in 34
  (p < 0.001); femur and pelvis are level with both. It is worse on the arm, which levels it with SKEL overall.
  SKEL-J is closer than SKEL on every bone (35 of 36 subjects overall), but it was trained on this cohort, and SKEL
  and OSSO were not.
- **Error grows with soft tissue.** Femur error rises with thigh depth below the skin (Spearman 0.66).
- **Not joint centres, not lengths.** Surface distance does not give joint-centre error. The MRI slices are 20 mm
  apart, so this data cannot check segment lengths: every method reads the tibia 30–39 mm longer than the MRI cloud,
  in the same direction. The cohort was scanned lying down with the arms overhead.

**On a real person: OpenCap subject 2** (1.96 m, 78.2 kg; sex not recorded, taken as male). There is no body
scan, so SKEL used height and mass. Joint-centre segment lengths, m:

| Segment | our 5 phones, before → after the marker correction | OpenCap's 5 phones | SKEL from height and mass | Winter's proportions |
|---|---|---|---|---|
| thigh | 0.446 / 0.440 → 0.444 / 0.438 | 0.437 / 0.440 | 0.471 | 0.480 |
| shank | **0.542 / 0.546** → 0.493 / 0.497 | 0.485 / 0.495 | 0.491 | 0.482 |
| upper arm | 0.369 | 0.358 | **0.313** | 0.365 |
| forearm | 0.289 | 0.299 | 0.297 | 0.286 |
| hip width | 0.203 → 0.188 | 0.201 | 0.162 | — |

- **None of these is bone.** The two video columns come from the same videos with different keypoint
  detectors.
- **The cross-check is what it is for.** Our shank was 5 cm longer than every other source. The cause was
  Pose2Sim's augmenter marker set, made for another model's bones, not this person; corrected in
  `mediapipe_lstm_pose2sim` (`docs/upstream-issues.md`, `docs/validation-results.md` §4). SKEL's upper arm is short against every
  other source here and on its own templates (0.16 × height, against about 0.17 for the OpenSim models
  and 0.19 in Winter's tables), so its arm lengths should not replace measured ones.
- **The layer stays Tier C:** a population prior from the body surface, not imaging.

## Skeletal alignment: the person's own knees, legs and shoulders

Segment lengths make every person a scaled copy of the generic skeleton. People also differ in how their bones
sit: knock knees (genu valgum) or bow legs (genu varum), a knee that stands bent or hyperextended, one leg
longer, one hip or shoulder higher. The generic OpenSim knee bends about one axis and has no sideways angle of
its own. So inverse kinematics of a valgus knee has to put the difference somewhere else (hip adduction and
rotation), and a posture rule with a fixed valgus threshold would coach the person against their own skeleton.
`rehabtwin/alignment.py` adds this layer (`joint_alignment`).

Two kinds of evidence, kept apart (the anatomy audit's red line, `docs/accuracy.md`: nothing internal is
inferred from cameras):

| | Camera estimate | Limb alignment |
|---|---|---|
| From | every session's standing frame | imaging or a clinician's measurement |
| Stored as | `qc.json` → `static_alignment`; `person.json` → `alignment_screening` | `person.json` → `limb_alignment` (twin manifest block) |
| Status | estimated; uncertainty not yet measured | measured, with its source and tier |
| Changes the model | never | yes: the knee's HKA angle in every session |
| Used for | the person's standing baseline for posture cues; a screening hold beyond 6° | the model; a structural record holds that knee's cues |

### The camera estimate (every session, screening only)

`process` measures the static frame and writes it to `qc.json` → `static_alignment`, marked
`"status": "estimated"` and `"uncertainty": "not yet measured ..."`:

| Value | Definition |
|---|---|
| `knee_frontal_deg` {r, l} | angle between thigh and shank in the frontal plane, from the hip, knee and ankle centres; + valgus. The same definition as the `knee_fppa` signal |
| `knee_sagittal_deg` {r, l} | standing knee flexion; − hyperextension |
| `leg_length_m` {r, l}, `leg_length_difference_mm` | hip centre to ankle centre |
| `pelvic_obliquity_mm` | right hip centre minus left, + right higher |
| `shoulder_height_difference_mm`, `shoulder_reach_m` {r, l} | acromion markers; reach is sideways from the mid-hip line |

The centres come from SKEL's joint centres when the front end gives them. Otherwise they come from the LSTM
augmenter's markers (midpoints of the epicondyle and malleolus markers, the hip joint centre), then SKEL skin
markers, then MediaPipe keypoints. Each of these is itself an estimate, and markers on a standing person can't
tell a bone shape from a habitual posture. Its uncertainty needs repeat sessions of the same person
(`rehabtwin progress`); until then it says "not yet measured". Change against the person's own baseline is what
it is used for.

`rehabtwin person screening PERSON --from-session SESSION` keeps a session's estimate in the person folder. The
`joint_alignment` layer stays "generic knee" with it: the estimate screens, it doesn't personalise.

### Limb alignment from imaging or a clinician

`rehabtwin person alignment PERSON alignment.json` takes the twin manifest's `limb_alignment` block
(`schemas/twin-manifest.schema.json`, `limb_side`), plus when and by whom:

```json
{"measured_at": "2026-09-01", "approved_by": "Dr. X", "structural": true, "diagnosis": "genu valgum",
 "right": {"source": "radiograph", "mechanical_axis_hka_deg": 9.0, "femoral_anteversion_deg": 18,
           "tibial_torsion_deg": 25, "femur_length_mm": 452},
 "left":  {"source": "radiograph", "mechanical_axis_hka_deg": 7.0}}
```

| `source` (per side) | Tier |
|---|---|
| `eos`, `ct`, `mri`, `radiograph` | B; A with `approved_by` |
| `clinical-measurement` | C; B with `approved_by` |
| a camera or marker estimate | refused: "screening only" |

- `mechanical_axis_hka_deg` is the deviation of the hip-knee-ankle axis from a straight leg, + valgus, −
  varus. A report that gives the angle around 180° (174°, say) is converted to the deviation (6°) with the
  direction the report states; a value outside ±30° is refused with that hint. An anatomical tibiofemoral angle
  (shafts, as a goniometer reads it) differs by several degrees and has to be converted first.
- Fields outside the manifest's `limb_side` are refused, as are values outside plausible ranges.
- The record's tier is its least-evidenced side. A record of a lower tier doesn't replace a higher one unless
  `--replace` is given.
- Only this record can say the alignment is `structural`.
- Torsion and segment lengths are stored and exported, not applied yet (see below).

### Into the model

Every session processed with `--person` turns each knee joint's frame on the femur about the femur's forward
axis. It stops when the model's hip-knee-ankle angle on its joint centres, in the default pose, is the
recorded HKA. The tibia, its markers, muscles and the foot follow. `qc.json` → `alignment.limb_alignment.knee`
records each knee's angle before and after, and the tilt. An imaging-personalised model is left as it is,
since its bones are already the person's. Leg-length differences come from the per-side scale factors (femur
and tibia scale separately on each side).

### Posture cues: the person's own standing, screening holds and safety flags

A rule with `"relative_to": "standing"` compares the signal's change from the person's standing value with its
threshold. The standing value is the signal on the session's static pose.

- The squat template's knee valgus rules use this: a cue comes at 10° of valgus beyond the person's standing knee
  angle, not at 10° absolute.
- Without a standing value such a rule isn't evaluated, and the cue summary says why.

Three things hold cues, each named in the cue summary (`screening_holds`, `safety_holds`, each rule's `gate`):

| Hold | When | Lifted by |
|---|---|---|
| Screening hold | the camera estimates a standing knee angle beyond 6° and no limb alignment is on record for that side. The reason ends "worth getting checked by a professional"; it never names an imaging test. 6° is our screening threshold, not a diagnostic cut-off | the treating clinician setting the rule's target (`"clinician_target": true`) |
| Structural alignment | a limb-alignment record says `structural` | the same |
| Clinician safety flag | an active flag in `person.json` → `safety_flags` covers the joint | only the clinician, by clearing the flag |

The screening and structural holds are in `qc.json` → `alignment.holds`; the safety holds are read from the
person folder each time cues are evaluated, so a flag recorded after a session already applies to its replay.

### Clinician safety flags

`rehabtwin person safety-flags PERSON flags.json` records the clinician's current list (the twin manifest's
`safety_flags`); the previous list stays in `history/`:

```json
[{"flag": "joint-instability", "body_region": "right knee", "status": "suspected",
  "set_by": "clinician", "set_at": "2026-10-20", "restrictions": ["no valgus loading"]}]
```

- `set_by` must be `clinician`. The twin never sets, infers or clears a flag.
- A flag is active unless its status is `cleared`: `suspected` and `not-assessed` restrict like `confirmed`
  (fail closed).
- `body_region` is free text matched by keyword and side ("right knee" → `knee_r`; "cervical spine" → neck and
  head; "whole body" → everything). A region nothing matches holds every joint, and the reason says so.
- The `restrictions` are text for people. The pipeline doesn't interpret them, so it holds the whole region:
  no posture cues there, and no assistance what-if (`muscles --assist/--passive`) at a joint in it.

Assistance what-ifs also follow bone quality (`person bone`): a clinician's `exo_torque_derating_factor`
(0 to 1, with `approved_by`) scales the assist torque and passive stiffness, and low bone density without such a
factor refuses them.

### The twin manifest

`rehabtwin person manifest PERSON --out manifest.json` writes the person model in the shared twin-manifest
format and checks it against `schemas/twin-manifest.schema.json`: each layer as personalised, unvalidated or
generic, with its tier; the `limb_alignment`, `muscle_parameters`, `bone_quality`, `safety_flags` and
`body_state` blocks; and `provenance` (person.json version and hash, and per block when and by whom). The camera
estimate is not a block in it (the layer's note says it is screening only). `person.json` stays the
record, with its full history.

### Tested (synthetic)

A synthetic subject whose skeleton stands with 10° (right) and 7° (left) of knee valgus, squatting
(`synthetic.generate(..., knee_frontal_deg=...)`, `validation/runs/alignment_genu_valgum.py`). One calibration
session builds the person model; another session of the same body is processed three ways. RMSE against the
synthetic truth (synthetic truth only, no clinical validation):

| Model | Knee FPPA R / L | Hip adduction R / L | Hip rotation R / L | Subtalar R | Marker fit |
|---|---|---|---|---|---|
| Generic knee | 6.7° / 4.5° | 1.8° / 1.3° | 3.6° / 3.2° | 14.2° | 14.0 mm |
| The person's bones, generic knee | 6.6° / 4.5° | 1.8° / 1.3° | 3.6° / 3.2° | 14.2° | 14.0 mm |
| Limb alignment on record (the true angles, as imaging would give them) | 0.8° / 0.6° | 0.5° / 0.5° | 0.8° / 1.2° | 1.0° | 8.4 mm |

- The generic knee puts knock knees into the hips and the feet: hip rotation off by 3–4° and the subtalar joint
  by 14°. Knee flexion is unaffected (under 1° either way).
- The person's bone lengths alone change nothing. The knee's angle does.
- Without a record, both knees get a screening hold (camera estimate +10° and +7°, beyond 6°); with the record,
  none (it isn't marked structural).
- The camera estimate equals the truth here (+10.0° / +7.0°) only because this synthetic front end gives exact
  joint centres. Video keypoints and augmented markers won't; that is why it stays screening only until repeat
  sessions measure its uncertainty.

### Not yet

- **Bone torsion** (femoral anteversion, tibial torsion): stored and exported, not applied. The Torsion Tool
  approach (Veerkamp et al. 2021) would twist the femur and tibia with their muscle attachments.
- **Shoulder girdle:** the model has no clavicle or scapula. Shoulder height and reach are estimated and stored
  only. Shoulder work needs a model with a moving scapula (Seth et al. 2016).
- **Spine:** curvature and scoliosis are not measured (manifest `spinopelvic_parameters` is imaging-only).
- **Foot:** foot posture is not measured.
- **The camera estimate's uncertainty:** needs repeat sessions of the same people.
- **Real validation:** needs people with long-leg imaging who are also recorded with the cameras.

## Muscle size, muscle quality and bone density from imaging

The regression above gives every person of one height and mass the same muscles. Imaging measures them:

```bash
python -m rehabtwin person muscles people/P01 P01_mri.json    # volume and/or fat fraction per muscle or group
python -m rehabtwin person bone people/P01 P01_dxa.json       # DXA T/Z-scores or QCT vBMD
python -m rehabtwin muscles out/s02 --person people/P01      # default: the folder the session was processed with
```

**Muscle size and quality** (`P01_mri.json`), from an MRI or CT segmentation (for example MuscleMap or
TotalSegmentator; map their labels onto these by each tool's own label definitions):

```json
{"method": "MRI 3 T 6-echo Dixon, MuscleMap segmentation", "date": "2026-09-14", "approved_by": "radiologist",
 "muscles": {"quadriceps_r": {"volume_cm3": 1980, "fat_fraction": 0.05},
             "quadriceps_l": {"volume_cm3": 1720, "fat_fraction": 0.09},
             "hamstrings_r": {"volume_cm3": 1010},
             "gluteus_maximus_r": {"fat_fraction": 0.07}}}
```

- **Labels:** groups (`quadriceps`, `hamstrings`, `adductors`, `adductor_magnus`, `gluteus_maximus`,
  `gluteus_medius`, `gluteus_minimus`, `iliopsoas`, `triceps_surae`, `gastrocnemius`, `anterior_leg`,
  `lateral_leg`, `deep_posterior_leg`), anatomical names (`vastus_lateralis`, `soleus`, ...) or model names
  (`vaslat`). Each needs a side suffix (`_r` or `_l`). Two labels covering the same muscle are refused.
- **Size:** each model muscle's force follows its contractile volume, Fmax = σ · V · q / lopt with
  σ = 60 N/cm² as in Rajagopal 2016. The model encodes the reference volumes it was built with
  (V_ref = Fmax · lopt / σ): 7,089 cm³ per leg against 7,304 cm³ from the Handsfield regression for the same
  subject, which checks the regression's units. A group volume is split among its model muscles by their
  reference shares.
- **Quality:** a fat fraction (MRI proton-density fat fraction, as a fraction 0–1) scales the contractile part,
  q = (1 − FF) / (1 − FF_healthy). FF_healthy is the young healthy level the generic muscles stand for: 2.6 %
  for the quadriceps and 5.4 % for the gluteal muscles (3 T water–fat MRI of 30 adults around 30 years,
  Eur Radiol Exp 2020, doi 10.1186/s41747-020-00162-5). No reference was found for the other groups; they use
  the quadriceps value. CT attenuation (`mean_hu`) is stored but not converted, since it depends on the
  scanner and protocol.
- Muscles without imaging take their leg's volume from the next source the person model has: a DXA scan,
  age and sex, or height and mass ([below](#leg-muscle-from-age-and-sex-or-from-a-dxa-scan)). They keep
  generic sizes when none is known. The geometry (paths, fibre and tendon lengths) stays the scaled generic model's, so measured size
  changes force, not shape.
- The muscle layer is Tier B, or A with `approved_by`, only when all 80 leg muscles are imaged; otherwise it
  stays C and its status says how many are.

**Bone density** (`P01_dxa.json`):

```json
{"method": "DXA (scanner model)", "date": "2026-09-01", "age_years": 62, "sex": "female", "postmenopausal": true,
 "sites": {"lumbar_spine_L1_L4": {"bmd_g_cm2": 0.86, "t_score": -2.1, "z_score": -0.6},
           "femoral_neck": {"bmd_g_cm2": 0.61, "t_score": -2.6, "z_score": -1.0}}}
```

- **Categories** (`pipeline/rehabtwin/bone.py`), with the lowest site counting:
  - DXA T-score for postmenopausal women and men aged 50 and over (WHO; ISCD official positions): ≤ −2.5
    osteoporosis, below −1.0 low bone mass.
  - DXA Z-score for younger people: ≤ −2.0 is below the expected range for age.
  - QCT spine vBMD (ACR): below 80 mg/cm³ osteoporosis, 80–120 low bone mass.
- **Refused:** raw Hounsfield units from an ordinary CT, since they are not a calibrated density. A woman's
  record without `postmenopausal` is also refused, since that decides which score applies.
- Bone density does not change the OpenSim model. It changes what the twin may suggest. Device what-ifs
  (`muscles --assist/--passive`) and corrections show it on the page when it is low, and say when it was
  never measured.
- These are screening categories from a measured report, not a diagnosis.

### Tested on real MRI and dynamometry: MyoSegmenTUM thigh

MyoSegmenTUM (Schlaeger et al. 2018, PLOS ONE) gives water–fat MRI of both thighs with manual masks for 15
healthy adults and 4 patients with neuromuscular disease. The healthy volunteers also have maximum isometric
knee-extension torque, seated with the hip at 90° and the knee at 60° and 90°. `pipeline/adapters/myosegmentum.py`
recomputes the muscle volumes from the masks, then predicts each person's torque with the model scaled to their
height and mass. The prediction is the isometric knee-extension moment at the same posture, with three sources
of leg capacity.

**The published volume table is wrong.** It counts mask voxels as 1 × 1 mm pixels (the scans' real spacing is
0.78–1.02 mm, per stack) and the patients' slices as 1 mm (really 4 mm). It also counts the slices where the
healthy volunteers' two stacks overlap twice. The adapter takes the geometry from each stack's DICOM and counts
each slice once. The healthy volunteers' quadriceps are then 0.65–0.70× the table's (sequence A) or 1.04×
(sequence B); the fat fractions in the table are right. Repeat scans of three volunteers agree to 2.2 %
(quadriceps volume, coefficient of variation).

**Muscle size:** the height-and-mass regression against measured volumes (15 healthy adults, both legs):

| Muscle group | measured / regression | spread between people (CV) | r |
|---|---|---|---|
| quadriceps | 0.75 | 15 % | 0.52 |
| hamstrings (lower ends below the scans) | 0.70 | 21 % | 0.57 |
| quadriceps, 4 patients | 0.49 | 24 % | 0.67 |

The regression gave these adults a third more quadriceps than they have. It cannot tell one person from another
better than ±15 %, and it gave the patients twice the muscle they have. People in rehab are the ones it fits
worst.

**Strength:** predicted against measured knee-extension torque. These are HV001–HV011, where the tables'
labels are unambiguous; for HV012–HV015 the paper says 60° on both legs, while the tables label the values
90°.

| Leg capacity from | 60°: measured / model | spread (CV) | r | 90°: measured / model | spread | r |
|---|---|---|---|---|---|---|
| generic subject | 0.90 | 17.5 % | 0.50 | 1.13 | 24.5 % | 0.41 |
| height-and-mass regression | 0.80 | 16.3 % | 0.44 | 0.98 | 19.1 % | 0.62 |
| MRI quadriceps volume + fat fraction | 1.12 | 9.9 % | 0.86 | 1.39 | 17.0 % | 0.76 |

- **Measured muscle size predicts strength:** with the MRI volume, the model's torque correlates with the
  dynamometer at r = 0.86 at 60° (0.44 with the regression), and the person-to-person error halves (16 % → 10 %).
- **The remaining bias** is the generic model's knee-angle dependence: the model loses more torque from 60° to
  90° than these people do. Dynamometry at the tested angles (`rehabtwin strength`) calibrates that.
- **With HV012–HV015 added** (read as 60°, different MRI sequence): r 0.67 against 0.57 for the regression.

**Muscle quality:** mean quadriceps fat fraction is 3.8 % in the healthy adults (1.0–7.0 %) and 13 % in the
patients (hamstrings 4 % and 26 %). The healthy reference used for q (2.6 %, another study's sequence) is 1.2
points lower than this one's. That moves q by about 1 %: the sequence matters less than the disease, which
moves it by 10–20 %.

Limits: 15 healthy adults, 12 men; one site and two sequences; the moment arms are the generic model's scaled to
height. The volumes are of the thigh between hip and kneecap.

## Leg muscle from age and sex, or from a DXA scan

A twin should work for anyone without a scan, and be as close as the data allow when there is one. Each leg's
muscle volume now comes from the best source the person model holds (`pipeline/rehabtwin/capacity.py`,
`dxa.py`):

| Source, best first | What it gives | Set with | Against measured knee strength |
|---|---|---|---|
| MRI/CT segmentation | volume and fat fraction per muscle or group | `person muscles` | r 0.86 (MyoSegmenTUM, 11 adults) |
| whole-body DXA scan | each leg's muscle; segment masses; regional fat; bone density if reported | `person dxa` | r 0.79, spread 22 % (NHANES, 2,104 adults) |
| age, sex, height and mass | the leg muscle an average person of that age, sex and size has | `person init/set --age-years --sex` | r 0.75, spread 24 % |
| height and mass | Handsfield 2014, young healthy adults | measured height and mass | r 0.65, spread 28 % |
| nothing measured | the generic subject's | — | — |

Every rung works on its own. `capacity/capacity.json` (`leg_source`), the report banner and each result's
caveat say which one a result rests on. Imaging still overrides per muscle; muscles it does not cover take their
leg's volume from the next rung. Within a leg, each muscle keeps its generic share.

```bash
python -m rehabtwin person set people/P01 --age-years 62 --sex female   # no scan: the age-and-sex default
python -m rehabtwin person dxa people/P01 P01_dxa_body.json             # a whole-body DXA scan
python -m rehabtwin muscles out/s02 --person people/P01
```

### The default without a scan: age, sex, height and mass

Leg lean mass (DXA lean soft tissue, mean of both legs) was fitted to age, (age − 50)², sex, height and mass,
with sex interactions, on 7,528 NHANES 1999–2002 adults aged 18–85 with a complete whole-body DXA
(`adapters/nhanes_strength.py fit-default` reproduces `capacity.LEG_LEAN_MODEL`). Trained on 1999–2000 alone,
it predicted the 2001–2002 adults' leg lean within 7.5 % on average: 7.5 % for ages 18–49, 7.6 % for 50+,
7.7 % above BMI 30, 8.0 % for women and 7.1 % for men. Leg lean then becomes muscle as with a scan (below).

Against the height-and-mass regression it gives:

| Person | leg muscle, age and sex | height and mass (Handsfield, in the model's volumes) | ratio |
|---|---|---|---|
| man 25 y, 1.70 m, 75.3 kg (the generic subject) | 6,039 cm³ | 7,089 cm³ | 0.85 |
| woman 25 y, 1.65 m, 60 kg | 4,123 cm³ | 5,763 cm³ | 0.72 |
| man 70 y, 1.75 m, 80 kg | 5,745 cm³ | 7,633 cm³ | 0.75 |
| woman 70 y, 1.62 m, 68 kg | 3,970 cm³ | 6,272 cm³ | 0.63 |

Handsfield's 24 young adults had more muscle than the general population, and the regression knows neither
sex nor age. On the MyoSegmenTUM thigh MRI the regression gave a third more quadriceps than measured
(measured / predicted 0.75); the age-and-sex model gives 0.93 (r 0.60 against 0.54). It cannot tell two
people of the same age, sex and size apart: the spread between them stays ±15 %.

### With a DXA scan: each leg measured

**Record** (`P01_dxa_body.json`): the regional table of a whole-body scan, in kg.

```json
{"method": "DXA Hologic Horizon A, whole body", "date": "2026-10-01", "approved_by": "radiologist",
 "regions": {"left_arm":  {"lean_kg": 3.0,  "fat_kg": 1.2,  "bmc_kg": 0.20},
             "right_arm": {"lean_kg": 3.2,  "fat_kg": 1.2,  "bmc_kg": 0.20},
             "left_leg":  {"lean_kg": 8.6,  "fat_kg": 3.5,  "bmc_kg": 0.50},
             "right_leg": {"lean_kg": 9.4,  "fat_kg": 3.4,  "bmc_kg": 0.50},
             "trunk":     {"lean_kg": 27.0, "fat_kg": 10.0, "bmc_kg": 0.80},
             "head":      {"lean_kg": 3.3,  "fat_kg": 1.0,  "bmc_kg": 0.50}},
 "bone_density": {"postmenopausal": true,
                  "sites": {"femoral_neck": {"bmd_g_cm2": 0.61, "t_score": -2.6, "z_score": -1.0}}}}
```

- **`lean_kg`** is lean soft tissue without bone mineral. Hologic tables also list "Lean + BMC"; subtract
  the BMC from it.
- **Leg lean is required.** The other regions are needed for the segment masses and fat.
- **`bone_density`** is optional. When present, it is classified like `person bone`, with the person's age
  at the scan and sex.
- **Refused:**
  - a method that is not DXA (a bioimpedance scale is not a DXA);
  - grams typed as kg;
  - a leg outside 2–25 kg lean;
  - regions that add up to more than 15 % away from the person's measured mass.

**Leg muscle per leg:** skeletal muscle of both legs = 0.78 × leg lean − 1.07 kg (McCarthy et al. 2023,
Sci Rep 13:2580). It comes from a Deming regression against whole-body MRI in 475 adults, with validation RMSE
0.95 kg and R² 0.91. It is applied per leg with half the intercept each, at a muscle density of 1.06 g/cm³.
A leg with more lean mass gets more muscle, so a side difference shows.

**Segment masses:** each region's share of the scanned mass (lean + fat + BMC) becomes the share of the model
bodies in that region:
- legs: femur, patella, tibia, talus, calcn, toes;
- arms: humerus, ulna, radius, hand;
- head;
- trunk: pelvis, lumbar vertebrae, torso.

The model's total mass stays the measured body mass, and within a region the bodies keep their relative masses.
Inertia scales with mass, but segment shapes and centres of mass stay the model's. A region whose mass would
change by more than ×2 either way is refused as a data error. This goes into the muscle model
(`capacity/model_capacity.osim`), where inverse dynamics, the ground-force estimate and static optimisation use
it. Kinematics do not depend on mass and are unchanged. A record with the legs only sizes the legs and keeps
the generic mass distribution, and the caveat says so.

**Layers:**
- Soft tissue becomes Tier B (A with `approved_by`): the regional fat is measured.
- Muscle stays Tier C. DXA measures each leg, not each muscle.

**Tested on NHANES 1999–2002** (`adapters/nhanes_strength.py analyse`). The data are public domain and stay
outside the repo. 2,104 adults aged 50+ had isokinetic knee extension at 60°/s and a whole-body DXA with no
region imputed. With the model scaled to a person's height, knee torque is proportional to the muscle volume
it is given. Each source is therefore compared with measured torque by correlation, and by the spread of
measured / predicted between people once the common bias is divided out:

| Group | n | height and mass r / spread | age and sex r / spread | DXA (that leg) r / spread |
|---|---|---|---|---|
| all | 2,104 | 0.65 / 28.0 % | 0.75 / 23.7 % | 0.79 / 22.3 % |
| women | 983 | 0.51 / 24.4 % | 0.56 / 23.5 % | 0.62 / 22.4 % |
| men | 1,121 | 0.51 / 24.3 % | 0.58 / 23.0 % | 0.65 / 21.5 % |
| age 65+ | 997 | 0.64 / 26.9 % | 0.72 / 23.5 % | 0.77 / 22.1 % |
| BMI ≥ 30 | 563 | 0.66 / 27.6 % | 0.75 / 23.6 % | 0.78 / 22.1 % |

- **Sex and age do most of the work.** Within one sex, where they cannot help, the scan adds the most:
  r 0.62 against 0.56 for women, 0.65 against 0.58 for men.
- **A statistical model as a fairer baseline** (trained on 1999–2000, tested on 2001–2002): test R² 0.66 from
  age, sex, height and mass, and 0.70 with the leg's DXA lean mass. Adding leg fat or the other leg adds nothing.

**On a real squat** (OpenCap subject 2, 1.96 m, 78.2 kg; `muscles --rep 2`): the same session run with each
rung. The DXA record is made up, not this person's scan: it is a functional check of how the scan reaches
the results, not a validation.

| Leg muscle from | leg muscle R / L | leg Fmax R / L | quadriceps mean activation R / L | knee moment, peak extension R |
|---|---|---|---|---|
| height and mass | 8,239 / 8,239 cm³ | 48.5 / 48.7 kN | 0.23 / 0.21 | 1.46 N·m/kg |
| age 27, male | 7,231 / 7,231 cm³ | 42.5 / 42.7 kN | 0.25 / 0.23 | 1.46 N·m/kg |
| illustrative DXA (right leg 1 kg more lean; trunk 45 % of the mass, the model's 51 %) | 8,031 / 7,295 cm³ | 47.2 / 43.1 kN | 0.23 / 0.23 | 1.29 N·m/kg |

- **Capacity alone** (rows 1–2) changes how hard the muscles work, not the joint moments.
- **The scan's mass distribution** also changes the moments. With less of the mass in the trunk, the right
  knee's peak extension moment drops 12 % and the hip's peak flexion moment 17 %.
- **Static optimisation** ran as before. The pelvis residual changed by 3 %.

**What a DXA scan does not make perfect.** With the scan, measured strength still spreads 22 % around the
prediction. The rest comes from what body composition does not see:
- muscle quality: intramuscular fat and fibre type;
- how hard the person can drive the muscle on the day;
- moment arms and the knee-angle curve, which stay the generic model's.

DXA also gives no bone geometry or joint centres (it is a 2-D projection), and no individual muscles: the
lean tissue of a region is about 70 % muscle in the legs. Two steps close more of the gap:
- per-muscle MRI, which brought the spread to 10 % on MyoSegmenTUM;
- dynamometry of the tested groups (`rehabtwin strength`), which measures the strength itself.

**Limits:**
- **The McCarthy equation** was developed in Caucasian adults (mean age about 50, BMI 26) on a Hologic
  QDR 4500A, the same scanner family as NHANES 1999–2002. Other scanners report lean mass a few percent
  differently, and other populations are untested.
- **Where the leg ends.** DXA's leg region is cut through the femoral neck, while the twin spreads the leg
  muscle over all 40 model muscles of a leg, hip muscles included. On MyoSegmenTUM, the measured quadriceps
  was 24.4 % of the leg muscle predicted for that person; it is 26.2 % in the model.
- **Who the reference data cover:** the age-and-sex model covers ages 18–85; outside that, height and mass
  are used and the caveat says so. Sex is the binary sex NHANES recorded.

## Verified

On synthetic sessions (`pipeline/tests/test_pipeline.py`):
- **Same bones across sessions:** a person built from one recording, then used on a second recording of
  the same body (other noise seed). The scale factors are identical (difference < 1e-4), and the joint-centre
  segment lengths match to 1 mm. Joint angles track as well as with scaling fitted to that recording: every
  coordinate is within 0.1° (measured: within 0.02°).
- **Personalised model:** a Tier B session from an attached model (the generator's truth model stands in
  for an imaging model). Unit scale factors, total mass 80.0 kg as measured, segment lengths unchanged. The
  same request without the person folder is refused at Tier B.

- **Recording size:** a synthetic recording shrunk to 85 % and marked single-camera is brought back by
  ×1.18 and tracks within 0.3° of fresh scaling. The same recording marked as calibrated is refused before
  anything is written.

On real video: see below.

## Real video: one phone with the bones from five

The person was built from the 5-phone session of OpenCap subject 2's `squats1` trial (MediaPipe +
LSTM augmenter, measured 1.96 m and 78.2 kg). The same trial's 3-phone, 2-phone and 1-phone recordings were
then processed with `--person`. The reference is OpenCap's own 5-camera result, so this is agreement with
another markerless system, not accuracy. It is also optimistic: the bones come from cameras that include
the three tested ones, whereas a real calibration session is a different recording. RMSE in degrees, both
runs from the current code (with the augmenter marker correction, `docs/validation-results.md` §4):

| Coordinate | 3 phones, own scaling | 3 phones, person's bones |
|---|---|---|
| pelvis tilt | 3.3 | 2.4 |
| hip flexion R / L | 9.4 / 8.0 | 7.9 / 6.5 |
| knee flexion R / L | 10.5 / 6.5 | 9.9 / 5.8 |
| ankle R / L | 7.3 / 4.4 | 7.7 / 4.8 |
| trunk lean (sagittal) | 3.5 | 3.2 |
| knee FPPA R / L | 8.6 / 8.9 | 8.8 / 9.2 |
| IK marker RMS | 2.08 cm | 2.16 cm |
| gates passed (not approving: markerless reference) | 8 | 9 (+ pelvis sagittal ≤ 3°) |

99.8 % of the trial was compared. With the person's bones, the sagittal pelvis, hip, knee and trunk angles
agree 0.3–1.5° better and the ankles 0.4–0.5° worse. Part of what changed between camera setups was the
bones, not the motion. (Before the marker correction the same comparison read pelvis tilt 6.7 → 5.2° and
hip flexion R 14.6 → 12.9°.)

**One phone needs its size fixed first.** The first version applied the person's bones to the single-phone
recording as it was. Knee RMSE went from 20° to 48° and the IK marker RMS from 2.5 to 6.8 cm: MediaPipe's
world landmarks are sized for an average body, so the recording was 17 % smaller than this 1.96 m person.
The bones did not fit and IK bent the joints to make them fit. `process --person` now compares the
recording's own segment scale with the person's (`qc.scaling.recording_scale`):

- **Front ends that only estimate scale** (one camera: MediaPipe monocular, HSMR) are brought to the
  person's size with one uniform factor about a point on the floor, which changes no joint angle. Here that
  factor was ×1.20. The segments ranged from 0.56 (foot) to 0.95 (hip width) of the person's, so the cloud is
  distorted, not just small.
- **Front ends that measure scale** (calibrated cameras, depth) are checked instead. The 2-phone recording
  measured 1.006 of the person's size, the 3-phone 1.000. A recording more than 10 % off is refused before
  anything is written: either another person's folder or a calibration fault.

With the rescale, the 1-phone session's IK marker RMS is 3.5 cm (2.3 cm with its own scaling, whose bones
bend to the distorted cloud). Pelvis tilt went from 15.5° to 14.5°, trunk lean from 12.4° to 8.7°, and knees
from 16.6 / 22.9° to 18.2 / 21.3°. Only 12.3 % of the trial could be compared (2-phone: 1.9 %), so every gate
there is not-tested. A single phone still fails on depth, not on bone length. The person model fixes the
bones; it does not make one camera see in depth. That is what the Kinect, or a LiDAR phone, adds.

One trial of one person: a mechanism shown, not a validated gain. The test that counts is a calibration
session and later sessions of the same person on different days.

Reproduce: `examples/person_model_opencap.sh` after `examples/opencap_agreement.sh`.

## What still needs data from outside

- **A real calibration session and repeat sessions of one person.** These measure how much a person
  model built in one session differs from one built in another, and whether a phone-only session with the
  person's bones agrees better with a reference.
- **Bone imaging to check SKEL's joint centres and lengths.** `person bones` (above) gives bones from body
  shape. The 3DBones bench (above) checks SKEL's bone surfaces against MRI, but not its joint centres, and its
  20 mm slices cannot check segment lengths. Lengths need DXA or radiograph lengths, or functional joint centres
  from marker motion capture (what OpenSim scaling uses); joint centres need imaging of the same people. OSSO, which
  infers the whole skeleton shape from the body, needs an old toolchain (Python 3.8, chumpy, the MPI mesh package);
  its model files are loaded and converted, but it is not run yet.
- **Muscle MRI and strength of people in rehab.** The MyoSegmenTUM test covers 15 healthy adults (above); the
  regression is furthest off for patients, and only 4 patients' scans, without strength, were available.
- **Imaging for Tier A.** `person attach` takes an MRI- or CT-personalised OpenSim model (e.g. from
  msk-PIPE or STAPLE) with a signed provenance record. Producing that model needs scans and clinician
  review; nothing in this repository makes one.
- **A strength measurement**, to check the capacity regression for the person it is used on.
- **A DXA scan and strength test of the same rehab patients.** NHANES tests the DXA rung on healthy adults
  aged 50+; whether it holds for people after injury or surgery, where one leg has wasted, is untested.
