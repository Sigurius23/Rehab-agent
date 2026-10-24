# BEDLAM2 as a testing ground across body types

[BEDLAM2](https://bedlam2.is.tue.mpg.de/) (Max Planck Institute for Intelligent Systems) is a synthetic
dataset of about 1,500 bodies, sized XS to 6XL, performing motions taken from motion-capture libraries
(AMASS). Videos of them are rendered, with exact ground truth. We use it to test the pipeline on body types
our own recordings cannot cover yet.

**Licence:** non-commercial scientific research only, and no redistribution. **None of the data goes into
this repository.** Commercial use needs a licence from ps-licensing@tue.mpg.de.

## What we use

| File (from the BEDLAM2 and SMPL-X download pages) | Used for |
|---|---|
| `b2_motions_npz_training.tar` (2.7 GB) | per-sequence body shape (16 parameters) and per-frame pose of every training body |
| `b2_bedlam2amass_motion_training.csv` | the source motion of each sequence, e.g. SOMA `squat_001`: finds squats, bending, sitting |
| `bedlam2_render_database-*.zip` (SQLite), `B2RenderStatus.csv`, `readme_b2_release.txt` | choosing render jobs: camera motion, depth, single person, test set |
| `smplx_lockedhead_20230207.zip`, file `SMPLX_NEUTRAL.npz` | the SMPL-X model "with removed head bun". BEDLAM2's shapes only fit this version, not v1.1 |

Later, for the video and depth paths, we need the MP4s and depth of the static-camera render jobs. The
candidates are `20241114_1_4619_hdri` (front ±60°, 3,942 single-person training sequences) and
`20241204_1_2120_hdri` (front ±90°, 1,649 sequences). Use only camera ground truth with
`gt_centersubframe` in its name (`readme_b2_release.txt`).

## Body types covered

1,526 bodies: 1.44–1.99 m tall, estimated BMI 17.7–43.2. Mass is estimated from mesh volume at
1,000 kg/m³, so BMI is approximate. The median estimated BMI by size label:

| XS | S | M | L | XL | 2XL | 3XL | 4XL | 5XL |
|---|---|---|---|---|---|---|---|---|
| 18.4 | 19.5 | 21.2 | 24.1 | 27.5 | 28.8 | 32.7 | 37.2 | 40.7 |

## Result 1: skin-to-joint-centre distance (Kinect path)

The Kinect path measures skin and adds the distance from skin to joint centre along the line of sight.
Seen from the front, in each body's standing rest pose (`python adapters/bedlam2.py offsets --model
SMPLX_NEUTRAL.npz --motions motions_npz_training/ --out offsets.json`, about 2 minutes):

| Joint | BMI < 22 | 22–30 | > 30 | Earlier height-only guess |
|---|---|---|---|---|
| Hip | 10.0 cm | 11.5 cm | 14.0 cm | ~8.6 cm |
| Knee | 6.1 cm | 6.3 cm | 6.5 cm | ~4.8 cm |
| Ankle | 3.8 cm | 4.0 cm | 4.1 cm | ~3.4 cm |
| Shoulder | 3.7 cm | 4.3 cm | 5.2 cm | ~5.7 cm |
| Elbow | 2.9 cm | 3.3 cm | 3.7 cm | ~3.4 cm |
| Wrist | 2.8 cm | 3.0 cm | 3.1 cm | ~2.4 cm |

`height × (a + b × (BMI − 25))` fits every joint within 0.32 cm residual SD (worst body 1.5 cm). Height
alone leaves the hip 1.6 cm SD off. `rehabtwin/kinect.py` now uses this fit.

Limits:
- SMPL-X joints stand in for MediaPipe's keypoints.
- The bodies wear no clothes, and clothing adds to the distance.
- In deep flexion the line of sight to a joint can pass through another segment (the thigh in front of the
  hip at the bottom of a squat seen from the front). The next experiment measures that on the posed squats.

## Result 2: what a front-facing depth sensor gets right during squats

`python adapters/bedlam2.py visibility --model SMPLX_NEUTRAL.npz --motions motions_npz_training/ --mapping
b2_bedlam2amass_motion_training.csv --out squat_visibility.json` (about 11 minutes):
- **Motions:** all 32 squat sequences (SOMA and MoSh squats), on 32 bodies with BMI 19.5–42.1, posed with
  SMPL-X skinning.
- **Sensor:** a virtual Kinect 2.7 m in front of the person. Either level at 1.0 m, or at 1.6 m aimed at the
  pelvis.
- **Per keypoint, every 3rd frame:** the first surface on the line of sight plus the skin-to-joint distance
  of `rehabtwin/kinect.py`, compared with the true joint.

The 2D keypoint is exact here (no MediaPipe error), so this is the best case for the depth step alone.

% of keypoint-frames **correct** (within 3 cm) / **silently wrong** (3–20 cm: too small for the 0.2 m
consistency check to catch) / **caught** (over 20 cm: left empty). Level sensor at 1.0 m:

| Joint | Standing (knee < 30°) | Mid (30–70°) | Deep (> 70°) |
|---|---|---|---|
| Hip | 99 / 1 / 0 | 91 / 8 / 1 | **64 / 24 / 12** |
| Knee | 99 / 0 / 0 | 98 / 1 / 1 | 96 / 3 / 1 |
| Ankle | 99 / 1 / 0 | 93 / 7 / 0 | 90 / 9 / 1 |
| Shoulder | 77 / 11 / 13 | 48 / 25 / 27 | 67 / 19 / 14 |
| Elbow | 73 / 26 / 1 | 44 / 53 / 3 | 39 / 51 / 11 |
| Wrist | 78 / 21 / 0 | 55 / 42 / 3 | 53 / 43 / 4 |

- **Knees and ankles** are reliable at every depth.
- **Hips** are reliable standing, but in a deep squat the thigh lies in front of the hip on the line of
  sight. Errors are negative: the lifted hip lands on the thigh.
  - **Above BMI 30**, deep-squat hips are 57 / 38 / 5: thigh and belly sit closer to the hip, so the error
    falls below the 0.2 m check.
  - **The 1.6 m sensor** does worse on hips (deep: 50 / 29 / 21), though better on shoulders.
- **Arms:** these squats are done with the arms held forward. The wrist is a median 15 cm ahead of the
  shoulder, and more than 25 cm ahead in 36% of frames. So forearms and hands often hide the elbows and
  shoulders. Arms hanging down will do better; the posture profile needs its own check.

What it means for the Kinect path:
- **Hips:** in deep flexion they should not be taken from depth. A candidate fix: place the hip on its own
  line of sight at the thigh length (measured in standing frames) from the knee, which stays reliable.
- **The 0.2 m check cannot catch thigh occlusion.** Whether a tighter one is safe depends on MediaPipe's real
  3D error, which the rendered videos will measure.

## Result 3: the person's thigh length puts the hidden hip back

`rehabtwin/kinect.py` now checks every hip against the person's thigh length. The length is either measured
in frames where the thigh is seen side-on (both ends lifted, at least 60° to the line of sight) or given
from the person's model (`--segment-lengths`). A hip more than 4 cm off that length from its knee is placed
on its own line of sight at thigh length from the knee. Of the two such points, it takes the one MediaPipe's
pose predicts.

The same squats run through the same code (`visibility` above), with MediaPipe-like noise: 3 px on the
hip's 2D keypoint and 3 cm per axis on its 3D pose. Deep-squat hips, before → after:

| Sensor | Correct (≤ 3 cm) | 3–20 cm | > 20 cm or empty | > 5 cm | > 10 cm | Median error after |
|---|---|---|---|---|---|---|
| Level, 1.0 m | 64% → 81% | 24% → 18% | 12% → 1% | 26% → 7% | 15% → 2% | 1.5 cm |
| High, 1.6 m | 50% → 69% | 29% → 31% | 21% → 1% | 41% → 15% | 32% → 4% | 1.6 cm |

- **Larger bodies gain most.** Above BMI 30, level sensor: 57% → 76% correct.
- **The other joints are unaffected.** Standing hips are re-placed in only 10 of 2,986 frames, and knees and
  ankles don't change.
- **What remains is small.** The 3–20 cm band is now mostly just over 3 cm (median 4.1 cm).

The thigh length is a property of the person, not of the recording. The `--segment-lengths` hook lets it
come from the person's model once that model exists.

## Result 4: body shape from one depth frame

`rehabtwin/shape.py` fits an SMPL-X body to what a front-facing depth sensor sees. This is the twin's
surface-shape layer (layer 3 in `docs/accuracy.md`) at Tier B. It fits 16 shape parameters, shared by all
frames, and per frame the body's orientation, its 21 body joints and its position. Hands, jaw and eyes
stay at zero. Its terms:

- **Depth:** each depth point against the model's depth on the same line of sight.
- **Silhouette:** the model must not stick out of the depth silhouette.
- **Floor:** no part of the model below the floor.
- **Inputs if given:** 2D keypoints, and the measured height.
- **Priors:** on shape and pose.

It returns:
- the shape and pose;
- rest-pose height, and mass and BMI from the mesh volume (1,000 kg/m³);
- the joints and four segment lengths;
- the skin-to-joint offsets of the Kinect path;
- the fit residuals, and warnings for fits not to trust.

`python adapters/bedlam2.py shapefit --model SMPLX_NEUTRAL.npz --motions motions_npz_training/ --mapping
b2_bedlam2amass_motion_training.csv --jobs 4 --out shapefit.json` (about 50 minutes on 4 cores):

- **Bodies:** 45, five per size label XS–5XL: 1.52–1.87 m, BMI 17.7–42.5. The 10 bodies used while
  developing the fit (`DEVELOPMENT_BODIES`) are left out.
- **Frame:** one near-standing frame per body (knee flexion < 20°, median 15°; feet on the floor). It comes
  from standing motions if the body has one, else walking, else any other motion.
- **Sensor:** a virtual Kinect v1 2.7 m in front of the person, level at 1.0 m, 640 × 480 with the nominal
  intrinsics. Depth is the first surface per pixel, with:
  - random error of SD 1.5·10⁻³·z² (1.1 cm at 2.7 m; Khoshelham & Elberink 2012);
  - rounding to mm;
  - half the pixels within 2 px of an edge dropped.
- **Segmentation:** the person's pixels are known, as the SDK's player index would give them, minus those
  within 2 cm of the floor.
- **Keypoints:** the 12 SMPL-X joints of the Kinect path, projected, plus 3 px noise.

Main condition, by BMI. Values are bias ± SD over bodies, and MAE for the last three columns:

| BMI | Bodies | Height | Mass | BMI | Segment lengths: fit / from height + BMI | Skin-to-joint offsets: fit / from height + BMI | Joint centres: fit / Kinect lift |
|---|---|---|---|---|---|---|---|
| < 20 | 11 | −0.3 ± 0.4 cm | +1.0 ± 1.7% | +0.2 ± 0.3 | 0.23 / 0.37 cm | 0.04 / 0.10 cm | 0.6 / 2.4 cm |
| 20–25 | 6 | −0.5 ± 0.2 cm | −0.9 ± 1.1% | −0.1 ± 0.3 | 0.17 / 0.59 cm | 0.04 / 0.12 cm | 0.6 / 2.1 cm |
| 25–30 | 10 | −0.0 ± 0.5 cm | −1.2 ± 1.5% | −0.3 ± 0.4 | 0.14 / 0.57 cm | 0.05 / 0.16 cm | 0.7 / 2.3 cm |
| 30–35 | 6 | +0.3 ± 0.4 cm | −0.8 ± 1.1% | −0.4 ± 0.4 | 0.27 / 0.73 cm | 0.05 / 0.20 cm | 0.7 / 2.5 cm |
| > 35 | 12 | +0.3 ± 0.7 cm | −2.2 ± 1.6% | −1.0 ± 0.5 | 0.20 / 0.63 cm | 0.08 / 0.17 cm | 0.7 / 2.5 cm |
| All | 45 | −0.0 ± 0.6 cm | −0.9 ± 1.9% | −0.4 ± 0.6 | 0.20 / 0.56 cm | 0.06 / 0.15 cm | 0.6 / 2.4 cm |

How to read the columns:
- **Segment lengths:** hip–knee, knee–ankle, shoulder–elbow and elbow–wrist between SMPL-X joints. They
  are compared with what height and BMI alone predict: a linear fit on the ~1,400 other BEDLAM2 bodies.
- **Skin-to-joint offsets:** measured on the fitted body, compared with `rehabtwin.kinect.surface_to_centre`
  given the true height and BMI.
- **Joint centres:** the 3D error of the 12 keypoints in this frame, median over bodies. The Kinect lift is
  the depth at the keypoint plus `surface_to_centre`.

What the table shows:
- **Height and mass without a stadiometer or scale:** height within ±1.4 cm and mass within ±5.2% on every
  body.
- **Bodies above BMI 35 come out 2% light.** The fit is just as light without noise (−2.3%). The sensor
  does not see the back, and the shape prior pulls it towards an average body.
- **Segment lengths are 3× closer than height and BMI predict:** 0.2 vs 0.6 cm MAE, 0.7 cm at worst. Per
  segment: hip–knee 0.17 vs 0.66, knee–ankle 0.23 vs 0.78, shoulder–elbow 0.18 vs 0.36, elbow–wrist 0.22
  vs 0.45 cm.
- **The skin-to-joint offsets gain little.** Height and BMI already give them to 1.5 mm (hip 2.5 mm); the
  fitted shape gives 0.6 mm (hip 1.7 mm). Clothing and the joint definition matter more.
- **Joint centres are 4× closer than the Kinect lift** in these standing frames. This is the best case:
  the model that made the data is the model that fits it.
- **A measured height adds little.** Given with 5 mm noise, the height error drops from ±0.6 to ±0.4 cm,
  while mass (−0.6 ± 2.1%) and segment lengths (0.18 cm) barely change.

Sensitivity, all 45 bodies. "Bad" means height off by more than 3 cm or mass by more than 10%. Runtime is
per fit on one core of a shared 4-core machine:

| Condition | Height | Mass | Segments (MAE) | Bad / flagged | Runtime median (max) |
|---|---|---|---|---|---|
| Main (above) | −0.0 ± 0.6 cm | −0.9 ± 1.9% | 0.20 cm | 0 / 0 | 19 s (28 s) |
| Measured height (±5 mm) | +0.0 ± 0.4 cm | −0.6 ± 2.1% | 0.18 cm | 0 / 0 | 19 s (30 s) |
| No noise (sensor, keypoints) | −0.0 ± 0.4 cm | −0.5 ± 1.7% | 0.12 cm | 0 / 0 | 22 s (38 s) |
| Depth noise × 2 | −0.2 ± 0.8 cm | −2.5 ± 2.5% | 0.28 cm | 0 / 0 | 16 s (30 s) |
| Disparity steps (1/8 px) + correlated noise (3 px) | −0.3 ± 0.8 cm | −1.7 ± 3.5% | 0.29 cm | 0 / 0 | 18 s (29 s) |
| Keypoints 8 px | +0.1 ± 1.4 cm | +0.6 ± 4.2% | 0.45 cm | 1 / 1 | 18 s (34 s) |
| No keypoints | +0.3 ± 0.9 cm | −0.9 ± 2.3% | 0.23 cm | 2 / 3 | 17 s (35 s) |
| Person turned 30° | −0.0 ± 0.9 cm | +0.5 ± 3.5% | 0.23 cm | 1 / 1 | 18 s (41 s) |
| Focal length 2% off | +1.9 ± 0.7 cm | +3.9 ± 1.7% | 0.30 cm | 3 / 0 | 17 s (29 s) |
| Another near-standing frame (41 bodies) | +0.2 ± 1.4 cm | −0.8 ± 2.8% | 0.19 cm | 1 / 1 | 18 s (38 s) |
| Both frames together (41 bodies) | −0.0 ± 0.4 cm | −1.0 ± 1.4% | 0.15 cm | 0 / 0 | 55 s (94 s) |

- **Pose:** the same body in two different frames differs by 1.4 cm SD in height and 2.1% in mass. One
  2XL frame came out 8.1 cm too tall, with a warning. Fitting both frames together is the most consistent
  condition.
- **Noise:** doubling it costs mass first (−2.5%, −4.6% above BMI 35). The sensor's real disparity steps
  and correlated noise widen the mass spread to ±3.5%.
- **The focal length must be calibrated.** A 2% error scales the body 2% (+1.9 cm, +3.9% mass), and no
  check inside the fit can see it. The other unflagged bad fit, without keypoints, was 3.9 cm too tall.
- **Warnings:** 8 of 487 fits were bad, and 4 of those were flagged. 2 good fits were flagged too. The
  warning that fired was "under 90% of depth points on the model along their line of sight".

Problems found while developing the fit, on the 10 development bodies:
- **Error direction:** the nearest-surface distance alone, with noise along the line of sight, made a
  body 8% too light. Depth is now compared along the line of sight.
- **Edge pixels:** the dropped pixels cost about 3% of mass until the silhouette got 1 px of tolerance.
- **Shape freed too early:** a 5XL body came out 6 cm too tall. High-order shape parameters and a
  zig-zag spine stood in for its belly and chest. The shape is now released coarse to fine, and the spine
  has a tight prior.
- **Fingers:** not fitted, but still matched to data, they cost up to 4% of mass. They are now left out.
- **A forearm across the belly** put the start 13 cm off (depth at the hip pixel was the forearm). The
  body came out 23 cm too tall. Such keypoints are now dropped from the start.
- **Split:** a first test split overlapped the development bodies. The test set above leaves them out.

Limits (Tier B, labelled with these errors):
- **Synthetic, unclothed and noise-modelled.** The data come from the same SMPL-X shape space as the fit,
  so these errors are a lower bound. Real people are not exactly in that space, and clothing and hair add
  to the surface.
- **Not modelled:**
  - the sensor: flying pixels at edges, the projector's shadow and depth registered onto the colour image;
  - segmentation: the recorder does not yet save the SDK's player index;
  - keypoints: MediaPipe's keypoints are not SMPL-X joints, which adds its own bias.
- **Mass is the mesh volume at 1,000 kg/m³**, compared with the same quantity. Real body density
  (985–1,100 kg/m³) and a scale differ.
- **SMPL-X joints are regressed from the surface**, not anatomical joint centres, so these segment lengths
  are not bone lengths (layer 2 needs imaging).
- **The front view leaves the back to the prior.** Heavy bodies come out 2% light, and a turn towards
  the sensor (a second view) is not tested yet.

## Next experiments

1. **MediaPipe on the rendered videos** of the static-camera jobs: keypoint error against the ground truth,
   by BMI and clothing.
2. **OpenSim scaling and IK** on markers placed on the SMPL-X surface: segment lengths and joint angles
   against the body's own, from small to large bodies.
