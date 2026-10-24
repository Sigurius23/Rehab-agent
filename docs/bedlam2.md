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

## Next experiments

1. **Posed squats, bending and sitting:** which keypoints a front-facing depth sensor can see during the
   movement, per body type.
2. **MediaPipe on the rendered videos** of the static-camera jobs: keypoint error against the ground truth,
   by BMI and clothing.
3. **OpenSim scaling and IK** on markers placed on the SMPL-X surface: segment lengths and joint angles
   against the body's own, from small to large bodies.
