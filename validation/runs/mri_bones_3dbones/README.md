# Skin-only skeletons against MRI bones (3DBones)

How close does a skeleton predicted from the body surface alone come to a person's bones? This bench scores the
skin-only predictions shipped with the 3DBones release (SKEL, SKEL-J, OSSO and HIT) against MRI-segmented bones on
its 36 test subjects. It also scores the release's SKEL-J fit to the MRI bones themselves, which is the floor for
that model on this ground truth. The result summary is `validation/results/mri_bones_3dbones.json`; what it means for
the person model is in `docs/person-model.md` (bones from body shape).

## The data is not in this repository

| Input | Where it comes from | Terms |
|---|---|---|
| `mri_bones_release_v2.zip` (3DBones: per-bone MRI point clouds, skin, SMPL and SKEL-J fits; skin-only predictions on the test split) | register on the 3DBones project site, 3dbones.is.tue.mpg.de | The release ships no licence file. It comes from the HIT MRI data at the Max Planck Institute for Intelligent Systems and is reported as non-commercial research use; read the terms when you register. |
| `skel_female.npz`, `skel_male.npz` | your SKEL download, converted with `python -I pipeline/adapters/body_model_files.py convert DOWNLOADS/ models_npz/` | MPI non-commercial research licence |
| `skeleton_model.npz` | your OSSO download, converted the same way | MPI non-commercial research licence (built on UK Biobank data) |

Nothing from the release enters this repository: not the meshes, not the predictions, not per-subject numbers or
subject ids. `run_bench.py` writes the per-subject rows to `$WORK`; only `summarize.py`'s aggregates are committed.

## Running it

```bash
export BONES3D_ZIP=/data/mri_bones_release_v2.zip MODELS_NPZ=/data/models_npz WORK=/data/work
python -I run_bench.py --selftest            # no data needed: the PLY reader and the distance code
python -I run_bench.py --workers 4           # about 20 min on 4 cores; writes $WORK/mri_bones_3dbones/subjects.json
python -I summarize.py $WORK/mri_bones_3dbones/subjects.json ../../results/mri_bones_3dbones.json
```

The same paths can be passed as `--release`, `--skel-dir`, `--osso-dir` and `--out`. Without the data, the script
says where to get it and exits with code 2. The scripts need numpy and scipy only. Every run checks the distance code
against brute force over all triangles on three subjects (0.04 mm at most so far). The release is read as bytes;
the per-subject pickles are never loaded.

## What it measures

- **Distance**, mm: the mean distance from each MRI bone point to the predicted skeleton, point to triangle, one way.
  *Same bone* measures to the predicted bone of that name (SKEL, SKEL-J, OSSO). *Any bone* measures to the nearest
  predicted bone, the only option for HIT and the floor mesh, which carry no bone labels. It is averaged over the femur,
  tibia–fibula, pelvis, humerus and radius–ulna, then over subjects. Paired Wilcoxon tests compare methods per subject,
  overall and per bone.
- **Body size and soft tissue**: the MRI SMPL fit's volume, and how deep the MRI bones lie below the MRI skin (all five
  bones, and the femur alone for the thigh). Stature is not available: the scans are taken with the arms overhead.
- **Length** of femur and tibia per side, prediction minus MRI, along each bone's long axis. Reported, but see below.

## Read the numbers with these

- **One cohort.** 36 adults from the HIT MRI data, scanned lying down with the arms overhead, so soft tissue sits
  differently than when standing. Bodies outside the cohort's range (body volume 49–131 L, mean bone depth 29–55 mm)
  are out of distribution for every method.
- **SKEL-J was trained on this cohort's training split; SKEL and OSSO were not.** Part of SKEL-J's edge may be fit to
  this cohort.
- **The SKEL column is the best case for `person bones`**, which fits SKEL to the person's body surface: it assumes a
  perfect surface. A phone or depth-camera surface will do worse, by an amount this bench does not measure.
- **Surface distance is not joint-centre error.** See the hip bench below.
- **Lengths cannot be validated here.** The MRI point clouds are 2.1 mm apart in-plane but 20 mm apart between slices,
  and the segmentations often stop short of the bone ends. The femoral head keeps its top in only 9 of 72 femurs.
  The skeleton fitted to the bones reaches a median 16 mm beyond the MRI tibia–fibula at the top and 25 mm at the
  bottom, while slicing alone accounts for about 10 mm. Every labelled method reads the tibia 30–39 mm longer
  than the MRI cloud and the femur 11–24 mm longer, all in the same direction. That is mostly the ground truth.
- **The predictions are the release's (both benches).** The methods were not re-run here. SKEL-J's same-bone distance (9.3 mm female,
  9.7 mm male) matches the figure the 3DBones paper reports, which checks the frames and the metric.

## Hip joint centres (`hip_centres.py`)

Surface distance does not say where a joint centre is, and OpenSim scaling runs on joint centres. This bench fits a
sphere to the femoral head and compares centres. Knee and ankle centres are not defined well enough on 20 mm slices,
so this is the hip only.

```bash
python -I hip_centres.py run            # same paths as run_bench.py; about 30 min; $WORK/mri_bones_3dbones/hip_subjects.json
python -I hip_centres.py summarize $WORK/mri_bones_3dbones/hip_subjects.json ../../results/mri_bones_3dbones_hip.json \
    --surface $WORK/mri_bones_3dbones/subjects.json      # adds the selection check
```

- **One extraction everywhere.** The same code fits the MRI femur, each prediction (SKEL, SKEL-J, OSSO; HIT has no
  bone labels) and the floor. Predicted femurs are first cut at the MRI's own slice planes and sampled on its pixel
  grid, so every centre comes from the same kind of points. Each mesh is also fitted unsliced: the slicing alone moves
  a centre by 0.6–0.7 mm on average (90th percentile 1.3 mm), so it is not what limits this bench. Fit residuals are
  reported per side.
- **Complete heads only.** A side is scored only if its MRI femur keeps the top of the head: a top slice at most
  25 mm across, with the fitted sphere reaching it. That holds for 9 of 72 sides (9 subjects). Elsewhere the top slice
  is a full cross-section (median 39 mm), and a centre fitted to what is left sits too low.
- **Are the 9 a fair sample?** Against the other 27 subjects, their body volume (median 72 L, range 52–112, against
  78 L, 49–131; p = 0.58), bone depth below the skin (p = 0.55) and share of women (6 of 9 against 16 of 27) do not
  differ detectably. Only the largest body (131 L) lies outside their range. Nine subjects would show only a large
  difference, though. If the complete heads do skew small, the predictor errors below are optimistic, since skin-only
  error grows with soft tissue.
- **The floor decides what this data can test.** On the 9 complete heads the skeleton fitted to the MRI bones lands
  10.2 mm from the MRI hip centre (90th percentile 13.5 mm), so this dataset cannot test the 5 mm joint-centre target.
- **Errors are split into anterior, medial and superior components**, and set against the floor femur's length (mean
  472 mm, not quantised by slices). The summary separates the mean bias, which a calibration fitted on separate data
  could remove, from the scatter around it, which no calibration could.

Results on the 9 complete heads, prediction minus MRI, mm:

| | distance, mean (90th pct) | % of femur length | anterior bias | medial bias | superior bias ± SD | scatter after bias |
|---|---|---|---|---|---|---|
| SKEL | 22.6 (35.9) | 4.8 | +4.7 | +6.9 | +4.3 ± 23.2 | 23.8 |
| SKEL-J | 21.8 (35.1) | 4.6 | +4.6 | +6.6 | +4.3 ± 22.7 | 22.8 |
| OSSO | 33.8 (43.3) | 7.2 | **+20.7** | +4.8 | +10.1 ± 24.6 | 25.1 |
| floor | 10.2 (13.5) | 2.2 | −3.4 | +6.1 | +5.1 ± 4.2 | 6.1 |

- **The vertical error is scatter, not bias, and it belongs to the person.** All three predictors miss the hip in the
  same vertical direction by a similar amount in each subject (from 30 mm too low to 41 mm too high). The floor stays
  within about 11 mm vertically. Calibration would not remove this.
- **OSSO adds a consistent anterior offset** (+21 mm, SD 7). A calibration could remove it only if fitted on
  separate data and then scored here: fitting it on these 9 hips would fit the test set, and with SD 7 the result
  would look deceptively good. Even uncalibrated, the comparison is plain: OSSO's hip is
  worse than SKEL's in all 9 heads (p = 0.004) and worse than SKEL-J's in 8 (p = 0.008). SKEL-J and SKEL cannot be told
  apart (p = 0.36).
- **Nine hips from one cohort, lying down.** Read these as the size of the problem, not as a predictor's accuracy.
- **These hips stay held out.** They can check the joint centres of a predictor trained later on the 317 training
  subjects (with the 10 mm floor attached), provided nothing about them enters its training or calibration.

## Leg priors side by side (`leg_priors.py`)

No ground truth here decides between the leg priors, but how far they disagree about the same leg still matters:
where two differ by d, at least one is off by d/2 or more. This finds the hip, knee and ankle centres of every leg
with the same geometry on every mesh, from the dense bone surface. The hip is the femoral head sphere. The knee is the
midpoint of the femoral epicondyles, and the ankle the midpoint of the malleoli. The femur is its label's largest
piece, because OSSO's thigh part also holds the patella. These are not the joint centres SKEL itself regresses, which
`person bones` uses.

```bash
python -I leg_priors.py run           # same paths as run_bench.py; under a minute on 4 cores
python -I leg_priors.py summarize $WORK/mri_bones_3dbones/leg_subjects.json ../../results/mri_bones_3dbones_legs.json
```

Segment lengths on 72 legs, absolute difference, mean (90th percentile):

| | thigh | shank | hip width (36 pelves) |
|---|---|---|---|
| SKEL vs SKEL-J | 4.5 mm, 1.1 % (7.7 mm) | 2.5 mm, 0.6 % (5.4 mm) | level |
| SKEL vs OSSO | 12.9 mm, 3.0 % (29.2 mm, 6.9 %) | 12.5 mm, 3.1 % (18.0 mm, 4.5 %) | OSSO 8.7 mm wider |
| SKEL vs floor | 10.0 mm, 2.4 % (21.8 mm) | 12.9 mm, 3.1 % (26.9 mm) | SKEL 4.3 mm narrower |
| OSSO vs floor | 10.8 mm, 2.6 % (25.6 mm) | 13.7 mm, 3.5 % (25.7 mm) | OSSO 4.4 mm wider |

- **SKEL and SKEL-J are near-twins on lengths**, so the choice is between the SKEL family and OSSO.
- **SKEL against OSSO is part offset, part scatter.** OSSO's shank is 12 mm longer (±6 mm, p < 10⁻¹²) and its
  pelvis 9 mm wider, consistently. Those offsets could be calibrated, on separate data. Their thighs disagree by up to
  29 mm with no consistent sign, and that scatter cannot be calibrated.
- **Neither is closer to the skeleton fitted to the bones.** Both miss it by about 10–14 mm per segment; OSSO with
  less bias, SKEL with a little less scatter. The floor fills in where the MRI stops short, so it is a reference, not
  truth.
- **Centre positions are mostly pose.** SKEL's knee sits 29 mm (SD 7) anterior of OSSO's while their thigh lengths
  agree within 6 mm on average: each method poses its skeleton inside the lying body its own way. The world-frame
  disagreement is 24 mm at the hip, 31 mm at the knee and 24 mm at the ankle on average. Lengths and widths are what
  scaling uses.
