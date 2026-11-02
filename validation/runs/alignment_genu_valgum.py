"""Genu valgum, synthetic: does the person's alignment in the model track them better than the generic knee?
A synthetic subject whose skeleton stands with 10 deg (right) and 7 deg (left) of knee valgus squats. Processed
(a) on the generic model, (b) with the person's bones from a calibration session but the generic knee, (c) with
a limb-alignment record giving the true knee angles as imaging would (twin manifest limb_alignment). Errors
against the synthetic truth. The camera's standing estimate is reported as what it is: screening only, never
applied to the model.
    python -I run.py REPO OUT"""
import json
import shutil
import sys
from pathlib import Path

REPO, OUT = Path(sys.argv[1]), Path(sys.argv[2])
sys.path.insert(0, str(REPO / "pipeline"))
from rehabtwin import cli, person, synthetic                 # noqa: E402
from rehabtwin.config import load_config                     # noqa: E402

TRUE = {"r": 10.0, "l": 7.0}
SIGNALS = ["knee_fppa_r", "knee_fppa_l", "hip_adduction_r", "hip_adduction_l", "hip_rotation_r", "hip_rotation_l",
           "hip_flexion_r", "knee_angle_r", "knee_angle_l", "ankle_angle_r", "subtalar_angle_r", "pelvis_list"]
if OUT.exists():
    shutil.rmtree(OUT)
OUT.mkdir(parents=True)
cfg = load_config("skel105_pose2sim")
seqs = {}
for name, seed in (("calibration", 0), ("session", 1)):
    seq, truth = synthetic.generate(cfg, OUT / f"{name}_truth", seed=seed, knee_frontal_deg=TRUE)
    seq.meta.update({"person_ref": "SYNTHETIC-NOT-A-PATIENT", "tier": "C", "session_id": name, "default_config": "skel105_pose2sim"})
    seq.save(OUT / f"{name}.npz")
    seqs[name] = (OUT / f"{name}.npz", truth)
kw = lambda t: dict(reference=t["mot"], reference_model=t["model"], reference_system="synthetic truth")
cal = cli.process(seqs["calibration"][0], OUT / "calibration", **kw(seqs["calibration"][1]))
estimate = cal["qc"]["static_alignment"]
runs = {"generic knee": cli.process(seqs["session"][0], OUT / "generic", **kw(seqs["session"][1]))}
for label, how in (("person's bones, generic knee", "none"), ("limb alignment on record (true values, as imaging)", "record")):
    d = OUT / f"person_{how}"
    person.init(d, "SYNTHETIC-NOT-A-PATIENT")
    person.build_from_session(d, OUT / "calibration", allow_synthetic=True)
    person.set_alignment_screening(d, OUT / "calibration")
    if how == "record":
        (OUT / "limb_alignment.json").write_text(json.dumps({
            "measured_at": "2026-10-28", "note": "synthetic truth, not an image",
            "right": {"source": "radiograph", "mechanical_axis_hka_deg": TRUE["r"]},
            "left": {"source": "radiograph", "mechanical_axis_hka_deg": TRUE["l"]}}))
        person.set_limb_alignment(d, OUT / "limb_alignment.json")
    runs[label] = cli.process(seqs["session"][0], OUT / f"with_{how}", person=d, **kw(seqs["session"][1]))
res = {"true_knee_frontal_deg": TRUE,
       "camera_estimate_screening_only": {k: estimate[k] for k in ("status", "uncertainty", "knee_frontal_deg", "knee_sagittal_deg",
                                                                  "leg_length_difference_mm", "pelvic_obliquity_mm")},
       "runs": {}}
for label, r in runs.items():
    per = r["validation"]["per_coordinate"]
    al = r["qc"].get("alignment") or {}
    res["runs"][label] = {"marker_rms_mm": round(1000 * r["qc"]["ik"]["marker_rms_m"]["mean"], 1),
                          "rmse_deg": {s: per[s]["rmse_deg"] for s in SIGNALS if s in per},
                          "knee_in_model": (al.get("limb_alignment") or {}).get("knee"),
                          "cue_holds": al.get("holds")}
(OUT / "result.json").write_text(json.dumps(res, indent=1))
print(json.dumps(res, indent=1))
