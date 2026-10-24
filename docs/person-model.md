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
| bone geometry | generic bones scaled per segment in one calibration session; or an imaging-personalised model | C; B/A with a provenance record |
| joint centres | scaled with the bones; markers placed on the static frames | C; B/A from the personalised model |
| surface shape | SMPL-X body fitted to standing Kinect depth frames (`person shape`), checked against measured height and mass | C until checked against a scan |
| kinematics | per session (not stored) | per session's validation |
| muscle | Rajagopal leg muscles; force from measured volume and fat fraction where imaged (`person muscles`), else scaled to measured height and mass; trunk generic | C; B/A when all leg muscles are imaged |
| soft tissue | not modelled | — |
| bone density | DXA or QCT result with its screening category (`person bone`) | B; A with a reviewed report |

Measured height and body mass are stored with their dates. A mass entered as assumed is kept, marked
`measured: false`, and never used where a measured mass is required.

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

It runs only when the session's mass is measured and its height known (`process --height-m` or `--person`).
It does not run on a personalised model, which carries its own muscle parameters. `--generic-capacity`
turns it off. `capacity/capacity.json` records the factors; reports say which capacity a result rests on.

In tests (`test_leg_capacity_scales_with_body_size`), the 55 kg, 1.60 m body gets weaker legs than the
generic model and the 110 kg, 1.90 m body stronger ones. Each scaled Fmax matches the formula to 1e-6, the
trunk is unchanged, and scaling a model twice is refused.

What it is and is not:
- **A population estimate.** It gives the leg the muscle an average young, healthy adult of this height and
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
- Muscles without imaging keep the height-and-mass regression, or generic sizes when the mass is not
  measured. The geometry (paths, fibre and tendon lengths) stays the scaled generic model's, so measured size
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

**Not validated yet.** The open MRI sets would test this against real people:
- MyoSegmenTUM–Thigh (osf.io/svwa7): water–fat thigh MRI with manual quadriceps, hamstrings, sartorius and
  gracilis masks for 15 healthy adults and 4 with neuromuscular disease. It would test how far the
  regression is from each person's measured muscles, and how far fat fraction separates the patients.
- TotalSegmentator's CT set (Zenodo): for the segmentation step.

Neither is reachable from this environment: osf.io, files.osf.io and zenodo.org are not on the network
allow-list.

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
runs from the current code:

| Coordinate | 3 phones, own scaling | 3 phones, person's bones |
|---|---|---|
| pelvis tilt | 6.7 | 5.2 |
| hip flexion R / L | 14.6 / 13.3 | 12.9 / 11.5 |
| knee flexion R / L | 12.0 / 8.1 | 11.4 / 7.4 |
| ankle R / L | 6.5 / 4.6 | 7.0 / 4.8 |
| trunk lean (sagittal) | 3.2 | 2.8 |
| knee FPPA R / L | 8.9 / 8.6 | 9.0 / 9.0 |
| IK marker RMS | 2.35 cm | 2.27 cm |
| gates passed (not approving: markerless reference) | 8 | 9 (+ trunk sagittal ≤ 3°) |

99.8 % of the trial was compared. With the person's bones, the sagittal pelvis, hip and trunk angles agree
0.4–1.8° better and the ankles 0.2–0.5° worse. Part of what changed between camera setups was the bones,
not the motion.

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

With the rescale, the 1-phone session's IK marker RMS is 3.4 cm (2.5 cm with its own scaling, whose bones
bend to the distorted cloud). Pelvis tilt went from 13.4° to 12.1°, trunk lean from 13.4° to 9.2°, and knees
from 19.7 / 26.2° to 21.0 / 24.2°. Only 12.5 % of the trial could be compared (2-phone: 1.9 %), so every gate
there is not-tested. A single phone still fails on depth, not on bone length. The person model fixes the
bones; it does not make one camera see in depth. That is what the Kinect, or a LiDAR phone, adds.

One trial of one person: a mechanism shown, not a validated gain. The test that counts is a calibration
session and later sessions of the same person on different days.

Reproduce: `examples/person_model_opencap.sh` after `examples/opencap_agreement.sh`.

## What still needs data from outside

- **A real calibration session and repeat sessions of one person.** These measure how much a person
  model built in one session differs from one built in another, and whether a phone-only session with the
  person's bones agrees better with a reference.
- **Skeleton from body shape (SKEL/OSSO).** These fit anatomical bones inside a measured body surface
  instead of scaling generic ones. Their model files need registration on the authors' sites, so the user
  has to download them; the code to use them is not written yet.
- **Muscle MRI from real people** to test the regression and the fat-fraction scaling (above).
- **Imaging for Tier A.** `person attach` takes an MRI- or CT-personalised OpenSim model (e.g. from
  msk-PIPE or STAPLE) with a signed provenance record. Producing that model needs scans and clinician
  review; nothing in this repository makes one.
- **A strength measurement**, to check the capacity regression for the person it is used on.
