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
- **Surface distance is not joint-centre error.** The bench does not say whether any method meets the joint-centre
  target in `docs/accuracy.md`.
- **Lengths cannot be validated here.** The MRI point clouds are 2.1 mm apart in-plane but 20 mm apart between slices.
  Every labelled method reads the tibia 30–39 mm longer than the MRI cloud and the femur 11–24 mm longer, all in the
  same direction, which points at the slicing and where the segmentation stops at least as much as at the methods.
- **The predictions are the release's.** The methods were not re-run here. SKEL-J's same-bone distance (9.3 mm female,
  9.7 mm male) matches the figure the 3DBones paper reports, which checks the frames and the metric.
