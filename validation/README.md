# Validation records

The scripts, logs and result summaries behind the numbers in `docs/`. They are kept here so that nothing depends on
a working folder that goes away. Everything in this folder can be rerun.

| Folder | What it holds |
|---|---|
| `audit/` | The claims audit of 2026-10-27, with code written only for it (no `rehabtwin` imports). |
| `runs/` | The run scripts of the experiments: SKEL bones on synthetic bodies, the OpenCap marker fix, person bones after the fix, the DXA squat, synthetic genu valgum, knee joint load, skin-only skeletons against MRI bones (`mri_bones_3dbones/`, with its own README). |
| `results/` | Result summaries: aggregate numbers only, as the docs quote them. |
| `tests/` | Full test-suite logs: the run with one failure, the run after the fix, the run with skeletal alignment (174 passed), and the run with knee joint load (182 passed). |
| `visuals/` | The audit page's 3D views: data preparation, the browser code, and a check of the browser's SKEL code against the Python reference. |

## Ground truth first

No bench result stands until its ground truth has had the same scrutiny as the predictor. A metric can be blind to a
flawed reference. The 3DBones surface bench measured from the MRI points to the predicted bones, one way only. So
femoral heads cut off in the MRI segmentation (63 of 72 failed the completeness check) never showed. The predictors'
"30–39 mm too long" tibias turned out to be segmentations stopping short of the bone ends. Both came to light only
when the raw extents were compared with the skeleton fitted to the bones (`runs/mri_bones_3dbones/`). Every bench
therefore states, before it ranks anything:

- **a floor:** the best the reference can resolve, such as a model fitted to it directly or repeat measurements;
- **the reference checked per case** for completeness and resolution, with failing cases excluded and counted;
- **whether the cases kept are a fair sample** of those excluded;
- **what the data can test:** a target looser than the floor is reported as untestable, not as passed or failed.

## The audit

`audit_a.py` (OpenSim environment) and `audit_b.py` (pandas environment) recompute each claim from the raw outputs.
`audit_*.log` hold their output; 29 of 30 claims matched. The one that didn't (the synthetic bodies' BMI range) is
corrected in the docs. `gen_page.py` builds the audit page from these files.

The fresh test run found one intermittent failure: the Kinect recorder's fake sensor could deliver two frames
swapped under load. `Race.cs` reproduces the mechanism and `race.log` holds its output (old logic 2–4 of 85 frames
out of order, new logic none). It was fixed in commit `8f82ac9`.

## Rerunning

The scripts read data and write outputs in a working folder, written `$WORK` in them. They also use `$REPO` (this
repository) and `$OPENCAP_CORE` (a clone of `opencap-org/opencap-core` for the generic LaiUhlrich2022 model).
`$BIO_PY` is the Python with OpenSim. What goes into `$WORK`:

| Data | Where it comes from | Licence |
|---|---|---|
| OpenCap subject 2 squat (videos, calibration, OpenCap's result) | `examples/opencap_agreement.sh` downloads it | public test data |
| NHANES 1999–2002 (DEMO, BMX, DXX, MSX) | `python adapters/nhanes_strength.py download` | public domain |
| MyoSegmenTUM thigh MRI | `python adapters/myosegmentum.py download` | open, see the paper |
| BEDLAM2 bodies and motions | your account on bedlam2.is.tue.mpg.de | non-commercial, no redistribution |
| SMPL 1.1.0, SKEL 1.1, STAR, OSSO | your accounts on the MPI sites (kept in your Drive) | non-commercial, no redistribution |
| 3DBones release v2 (MRI bones, skin, skin-only predictions) | registration on 3dbones.is.tue.mpg.de | no licence file in the release; reported non-commercial research use |

Convert the model downloads once with `python -I pipeline/adapters/body_model_files.py convert DOWNLOADS/ models_npz/`.
The licensed files and the large session folders (OpenSim models, motions, muscle studies) are not in this
repository.

## Results

| File | Source | Quoted in |
|---|---|---|
| `skel_bones_bedlam2.json` | `adapters/bedlam2_skel.py`: 45 synthetic bodies, per-body errors (no BEDLAM2 ids or shape parameters) | `docs/person-model.md`, bones from body shape |
| `opencap_marker_fix.json` | 5 camera setups × before/after the marker correction: RMSE per coordinate, marker fit, scale factors | `docs/validation-results.md` §4 |
| `opencap_person_bones_after_fix.json` | 3-, 2- and 1-phone sessions, own scaling vs the person's bones | `docs/person-model.md`, real video |
| `nhanes_strength.json`, `nhanes_fit_default.json` | `adapters/nhanes_strength.py analyse / fit-default` | `docs/person-model.md`, DXA and age-sex |
| `myosegmentum_summary.json` | `adapters/myosegmentum.py analyse`, summary only | `docs/person-model.md`, MyoSegmenTUM |
| `dxa_squat.json` | the OpenCap squat with leg muscle from height and mass, age and sex, and an illustrative DXA record | `docs/person-model.md`, on a real squat |
| `alignment_genu_valgum.json` | `runs/alignment_genu_valgum.py`: a synthetic subject with 10° / 7° knee valgus, processed on the generic knee, with the person's bones, and with a limb-alignment record of the true angles; the camera's standing estimate reported as screening only | `docs/person-model.md`, skeletal alignment |
| `joint_load_synthetic.json`, `joint_load_squat.json` | `runs/joint_load_squat.sh`: knee joint load and the fat, strength and combined scenarios on the synthetic squat and the OpenCap squat (illustrative DXA tables), with per-knee diagnostics | `docs/joint-load.md`, results |
| `mri_bones_3dbones.json` | `runs/mri_bones_3dbones/`: SKEL, SKEL-J, OSSO and HIT skeletons predicted from the skin, against MRI bones on the 36 3DBones test subjects, with the floor (SKEL-J fitted to the bones); aggregates and paired tests only, no subject ids | `docs/person-model.md`, bones from body shape |
| `mri_bones_3dbones_hip.json` | `runs/mri_bones_3dbones/hip_centres.py`: hip centres (femoral-head spheres) of the same predictions and the floor against MRI, on the 9 sides whose head is completely segmented; bias components, scatter, % of femur length, the segmentation-completeness evidence, whether the 9 are a fair sample | `docs/person-model.md`, bones from body shape |

## 3D views

`visuals/` builds the data for the audit page's 3D section:

- `prep_bodies.py` (OpenSim environment): SKEL bodies and bone meshes for the line-up, the height-and-BMI grid of
  shape parameters, and the two synthetic depth frames regenerated exactly as `adapters/bedlam2_skel.py` made them
  (it checks that the fit comes out the same as in the run).
- `prep_squat.py`: the OpenCap squat. Bone poses of our model after the marker fix, joint centres of ours before and
  after the fix and of OpenCap's result, joint angles, and camera 2's clip with its MediaPipe keypoints.
- `skelmath.js` is SKEL's rest-pose forward pass in JavaScript; `node test_skelmath.js OUT skelmath.js` compares it
  with the Python version (agreement to 0.03 mm on joints, bones and skin). `viz.js` draws the views with three.js.

The data they write contains SMPL and SKEL meshes, so it stays out of this repository.
