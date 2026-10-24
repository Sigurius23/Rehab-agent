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
| surface shape | not built yet (body shape from depth is in progress) | — |
| kinematics | per session (not stored) | per session's validation |
| muscle | Rajagopal leg muscles, capacity scaled to measured height and mass; trunk generic | C |
| soft tissue | not modelled | — |

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
- **Imaging for Tier A.** `person attach` takes an MRI- or CT-personalised OpenSim model (e.g. from
  msk-PIPE or STAPLE) with a signed provenance record. Producing that model needs scans and clinician
  review; nothing in this repository makes one.
- **A strength measurement**, to check the capacity regression for the person it is used on.
