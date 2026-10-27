# Validation records

The scripts, logs and result summaries behind the numbers in `docs/`. They are kept here so that nothing depends on
a working folder that goes away. Everything in this folder can be rerun.

| Folder | What it holds |
|---|---|
| `audit/` | The claims audit of 2026-10-27, with code written only for it (no `rehabtwin` imports). |
| `runs/` | The run scripts of the experiments: SKEL bones on synthetic bodies, the OpenCap marker fix, person bones after the fix, the DXA squat. |
| `results/` | Result summaries: aggregate numbers only, as the docs quote them. |
| `tests/` | Full test-suite logs: the run with one failure, and the run after the fix. |

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
