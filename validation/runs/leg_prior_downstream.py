"""Does the choice of leg prior matter downstream? (validation/runs/mri_bones_3dbones/leg_priors.py measured how far
SKEL and OSSO disagree about the same person's thigh, shank and hip width; this puts disagreements of that size into
the twin.)

The synthetic squat person (SYNTHETIC-NOT-A-PATIENT) is copied with its thigh, shank or hip width scaled by the
SKEL-vs-OSSO disagreement: the typical one (OSSO's mean offset) and the 90th-percentile thigh and shank ones. Each copy
is processed on the same synthetic markers (IK with those bones), checked against the synthetic truth, and run through
the muscle stage with knee joint load and a +/-0.10 ground-force split.

    python -I leg_prior_downstream.py REPO OUT

The factors come from validation/results/mri_bones_3dbones_legs.json.

Writes OUT/leg_prior_downstream.json: per variant, joint-angle error against the truth, marker fit, knee load and its
reportability. Synthetic truth only: it measures how much a bone error of this size moves the outputs, not which
prior is right."""
import json
import shutil
import sys
from pathlib import Path

ANGLES = ("knee_angle_r", "knee_angle_l", "hip_flexion_r", "hip_flexion_l", "ankle_angle_r", "ankle_angle_l",
          "pelvis_tilt", "hip_adduction_r", "knee_fppa_r")


def variants(legs):
    """Scale multipliers from the SKEL-vs-OSSO comparison: OSSO's mean offset, and the 90th-percentile thigh and shank
    disagreements in either direction (the thigh disagreement has no consistent sign)."""
    p, seg = legs["pairs"]["skel - osso"], legs["segments_mm"]["skel"]
    typical = {k: round(1 - p[f"{k}_length"]["difference_mm"]["mean"] / seg[k]["mean"], 4) for k in ("thigh", "shank")}
    typical["hip_width"] = round(1 - p["hip_width"]["difference_mm"]["mean"] / seg["hip_width"]["mean"], 4)
    th, sh = p["thigh_length"]["abs_difference_pct"]["p90"] / 100, p["shank_length"]["abs_difference_pct"]["p90"] / 100
    return {"base": {}, "osso_typical": typical, "thigh_plus_p90": {"thigh": round(1 + th, 4)},
            "thigh_minus_p90": {"thigh": round(1 - th, 4)}, "shank_plus_p90": {"shank": round(1 + sh, 4)},
            "shank_minus_p90": {"shank": round(1 - sh, 4)}}


def scaled(scale_set, change):
    """The person's per-body factors with the thigh (femur, patella), shank (tibia) or hip width (pelvis Z) scaled."""
    out = {b: list(f) for b, f in scale_set.items()}
    for body, f in out.items():
        if body.startswith(("femur_", "patella_")) and "thigh" in change:
            out[body] = [round(x * change["thigh"], 5) for x in f]
        if body.startswith("tibia_") and "shank" in change:
            out[body] = [round(x * change["shank"], 5) for x in f]
        if body == "pelvis" and "hip_width" in change:
            out[body] = [f[0], f[1], round(f[2] * change["hip_width"], 5)]
    return out


def main():
    repo, out = Path(sys.argv[1]), Path(sys.argv[2])
    sys.path.insert(0, str(repo / "pipeline"))
    from rehabtwin import cli, person, skel_bones, tiers
    from rehabtwin.config import resolve
    legs = json.loads((repo / "validation/results/mri_bones_3dbones_legs.json").read_text())
    calib = out / "calibration"
    if not (calib / "session.json").exists():
        cli.selftest(calib)
    seq_path = calib / "skel_seq.npz"
    truth_mot, truth_model = calib / "truth" / "truth.mot", calib / "truth" / "truth_model.osim"
    sess = json.loads((calib / "session.json").read_text())
    qc = json.loads((calib / "qc.json").read_text())
    base = out / "person_calibration"          # the source; each variant (base included) gets its own copy
    shutil.rmtree(base, ignore_errors=True)
    person.init(base, sess["person_ref"], mass_kg=qc["subject"]["mass_kg"], height_m=qc["subject"].get("height_m"))
    person.build_from_session(base, calib, allow_synthetic=True)
    rec0 = person.load(base)
    generic = resolve(rec0["model"]["generic_model"])
    results = {"note": __doc__.split("\n\n")[1].replace("\n", " "), "variants": {}}
    for name, change in variants(legs).items():
        pdir, sdir = out / f"person_{name}", out / name
        shutil.rmtree(pdir, ignore_errors=True)
        shutil.rmtree(sdir, ignore_errors=True)
        shutil.copytree(base, pdir)
        if change:
            rec = person.load(pdir)
            factors = scaled(rec["model"]["scale_set"], change)
            skel_bones.scale_model(generic, factors, rec["anthropometrics"]["mass_kg"]["value"], pdir / "model.osim")
            rec["model"].update(scale_set=factors, sha256=tiers.sha256(pdir / "model.osim"))
            person.save(pdir, rec, f"leg prior variant {name}: {change}")
        res = cli.process(seq_path, sdir, exercise="squat", reference=truth_mot, reference_model=truth_model,
                          reference_system="synthetic truth (rehabtwin.synthetic)", person=pdir)
        study, _ = cli.muscle_study(sdir, view_3d=False, person=pdir, joint_load=True, grf_sensitivity=0.10)
        per = res["validation"]["per_coordinate"]
        jl = study["joint_load"]
        sqc = json.loads((sdir / "qc.json").read_text())
        results["variants"][name] = {
            "change": change, "angle_rmse_vs_truth_deg": {c: per[c]["rmse_deg"] for c in ANGLES if c in per},
            "marker_rms_mm": {k: round(1000 * v, 2) for k, v in sqc["ik"]["marker_rms_m"].items()},
            "knee_load": jl["baseline"], "diagnostics": jl.get("baseline_diagnostics"),
            "band_over_grf_split": jl.get("baseline_band_over_grf_split")}
        (out / "leg_prior_downstream.json").write_text(json.dumps(results, indent=1, default=str))
        print(name, "done", flush=True)


if __name__ == "__main__":       # the study's worker processes import this file again
    main()
