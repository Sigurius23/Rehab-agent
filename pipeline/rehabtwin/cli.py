"""Command line: ``python -m rehabtwin <command>``.

  process   SEQ.npz -> session folder (OpenSim model + IK, metrics, QC, session.json, report.html)
  validate  estimate .mot vs reference .mot -> validation-report.json
  synth     write a synthetic SKEL-like sequence with known truth
  selftest  synth -> process -> validate, exits non-zero if the round trip regresses
  mp-mono   raw MediaPipe dump (adapters/mediapipe_pose.py) -> monocular sequence .npz
  mp-multiview  synchronised raw MediaPipe dumps + Qualisys calibration -> triangulated sequence .npz
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

import numpy as np

from . import metrics as metrics_mod
from . import opensim_stage, records, report, validation
from .config import load_config
from .io_formats import read_table
from .kinematics import skeleton_positions
from .sequence import MarkerSequence


def process(seq_path, out_dir, exercise="squat", config=None, mass_kg=None, height_m=None,
            reference=None, reference_system=None, person_ref=None, tier=None, video=None, max_lag_s=0.0,
            reference_model=None):
    seq_path, out_dir = Path(seq_path), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    seq = MarkerSequence.load(seq_path)
    cfg = load_config(config or seq.meta.get("default_config", "skel105_pose2sim"))
    if seq_path.resolve() != (out_dir / "skel_seq.npz").resolve():
        shutil.copy(seq_path, out_dir / "skel_seq.npz")
    stage = opensim_stage.run(seq, cfg, out_dir, mass_kg=mass_kg, height_m=height_m)
    if len(stage.motions) > 1:
        print(f"note: {len(stage.motions)} segments; metrics use the longest", file=sys.stderr)
    motion = max(stage.motions, key=lambda p: len(read_table(p).time))
    est = read_table(motion)
    tier = tier or seq.meta.get("tier", "C")
    person_ref = person_ref or seq.meta.get("person_ref", "UNSPECIFIED")

    derived = metrics_mod.derived_signals(est, stage.scaled_model)
    skeleton = skeleton_positions(stage.scaled_model, est)
    val, ref_plot, ref_skeleton = None, None, None
    if reference:
        ref_tab = read_table(reference)
        ref_model = Path(reference_model) if reference_model else Path(reference).parent / "model_scaled.osim"
        if ref_model.exists():  # posture signals (inclination vs gravity, FPPA) can be validated too
            ref_skeleton = skeleton_positions(ref_model, ref_tab)
            ref_tab = metrics_mod.with_signals(ref_tab, metrics_mod.derived_signals(ref_tab, ref_model))
        cmp = validation.compare(metrics_mod.with_signals(est, derived), ref_tab, max_lag_s=max_lag_s)
        ref_plot = (ref_tab.time + cmp["lag_s"], {c: ref_tab.col(c) for c in ref_tab.columns})
        val = validation.report(cmp, person_ref, reference_system or str(reference), [exercise],
                                synthetic=bool(seq.meta.get("synthetic")))
        records.validate(val, "validation-report")
        records.write_json(out_dir / "validation-report.json", val)

    imputed_t = np.asarray(stage.qc["imputed_frames"], float) / seq.fps
    met, signals = metrics_mod.compute(est, stage.scaled_model, exercise, tier,
                                       allowed_joint_planes=(val or {}).get("feedback_allowed_joint_planes", ())
                                       if val and not val["synthetic"] else (),
                                       imputed_times=imputed_t,
                                       validation_ref="validation-report.json" if val else None, derived=derived)
    records.write_json(out_dir / "metrics.json", met)
    outputs = {"model": stage.scaled_model.relative_to(out_dir), "motion": motion.relative_to(out_dir),
               "metrics": "metrics.json", "qc": "qc.json", "report": "report.html"}
    if val:
        outputs["validation_report"] = "validation-report.json"
    sess = records.session_record(seq, stage.qc, out_dir, tier, person_ref, video=video,
                                  config_name=Path(cfg["_path"]).name, outputs=outputs, validation_report=val)
    records.validate(sess, "session")
    records.write_json(out_dir / "session.json", sess)
    report.write(out_dir / "report.html", sess, stage.qc, met, signals, est.time, val, ref_plot, skeleton, ref_skeleton)
    return {"session": sess, "metrics": met, "qc": stage.qc, "validation": val, "motion": motion}


def _synth(out_dir, seed=0, **kw):
    from . import synthetic
    out_dir = Path(out_dir)
    cfg = load_config("skel105_pose2sim")
    seq, truth = synthetic.generate(cfg, out_dir / "truth", seed=seed, **kw)
    seq.meta.update({"person_ref": "SYNTHETIC-NOT-A-PATIENT", "tier": "C", "session_id": out_dir.name,
                     "default_config": "skel105_pose2sim"})
    seq.save(out_dir / "skel_seq.npz")
    return out_dir / "skel_seq.npz", truth["mot"], truth["model"]


# Regression limits for the synthetic round trip (deg). These guard the
# software, not the measurement — real accuracy comes from a real reference.
SELFTEST_LIMITS = {"knee_angle_r": 2.0, "knee_angle_l": 2.0, "hip_flexion_r": 2.5, "hip_flexion_l": 2.5,
                   "ankle_angle_r": 2.5, "ankle_angle_l": 2.5, "pelvis_tilt": 2.5, "hip_adduction_r": 2.0,
                   "L5_S1_Flex_Ext": 1.5, "torso.sagittal": 2.0, "torso.frontal": 2.0, "knee_fppa_r": 3.0}


def selftest(out_dir):
    seq_path, truth, truth_model = _synth(out_dir)
    res = process(seq_path, out_dir, exercise="squat", reference=truth, reference_model=truth_model,
                  reference_system="synthetic truth (rehabtwin.synthetic)")
    per = res["validation"]["per_coordinate"]
    failures = {c: per[c]["rmse_deg"] for c, lim in SELFTEST_LIMITS.items() if per[c]["rmse_deg"] > lim}
    return res, failures


def main(argv=None):
    ap = argparse.ArgumentParser(prog="rehabtwin", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("process", help="sequence -> OpenSim session folder")
    p.add_argument("sequence")
    p.add_argument("out")
    p.add_argument("--exercise", default="squat", choices=sorted(metrics_mod.load_exercises()))
    p.add_argument("--config", help="config name in pipeline/configs or a path")
    p.add_argument("--mass-kg", type=float)
    p.add_argument("--height-m", type=float)
    p.add_argument("--reference", help="reference .mot for validation (e.g. marker-mocap IK)")
    p.add_argument("--reference-system", help="what the reference is, for the report")
    p.add_argument("--max-lag-s", type=float, default=0.0, help="search a time offset for unsynchronised references")
    p.add_argument("--reference-model", help="OpenSim model of the reference (default: model_scaled.osim next to it); "
                                             "enables validation of trunk/pelvis inclination and knee FPPA")
    p.add_argument("--person-ref", help="pseudonymous subject reference (never a name)")
    p.add_argument("--tier", choices=["A", "B", "C"])
    p.add_argument("--video")
    v = sub.add_parser("validate", help="compare two .mot files")
    v.add_argument("estimate")
    v.add_argument("reference")
    v.add_argument("--out", default="validation-report.json")
    v.add_argument("--reference-system", default="unspecified reference")
    v.add_argument("--person-ref", default="UNSPECIFIED")
    v.add_argument("--movement", action="append", default=[])
    v.add_argument("--max-lag-s", type=float, default=0.0)
    v.add_argument("--synthetic", action="store_true")
    s = sub.add_parser("synth", help="write a synthetic sequence + truth")
    s.add_argument("out")
    s.add_argument("--seed", type=int, default=0)
    t = sub.add_parser("selftest", help="synthetic round trip")
    t.add_argument("out")
    m = sub.add_parser("mp-mono", help="MediaPipe raw dump -> monocular sequence")
    m.add_argument("raw")
    m.add_argument("out")
    m.add_argument("--focal-px", type=float, help="calibrated focal length; default assumes a 75 deg diagonal FOV")
    m.add_argument("--person-ref", default="UNSPECIFIED")
    m.add_argument("--gravity-up-cv", help="up direction in OpenCV camera coords 'x,y,z' (phone IMU / calibration)")
    m.add_argument("--gravity-source", default="user supplied")
    mv = sub.add_parser("mp-multiview", help="MediaPipe raw dumps + calibration -> triangulated sequence")
    mv.add_argument("raws", nargs="+", help="one raw dump per camera, in calibration camera order")
    mv.add_argument("--qca", required=True, help="Qualisys .qca.txt calibration")
    mv.add_argument("--out", required=True)
    mv.add_argument("--person-ref", default="UNSPECIFIED")
    a = ap.parse_args(argv)

    if a.cmd == "process":
        res = process(a.sequence, a.out, a.exercise, a.config, a.mass_kg, a.height_m, a.reference,
                      a.reference_system, a.person_ref, a.tier, a.video, a.max_lag_s, a.reference_model)
        print(json.dumps({"reps": res["metrics"]["n_reps"], "tier": res["metrics"]["tier"],
                          "ik_marker_rms_m": res["qc"]["ik"]["marker_rms_m"], "report": str(Path(a.out) / "report.html")}, indent=2))
    elif a.cmd == "validate":
        cmp = validation.compare(read_table(a.estimate), read_table(a.reference), max_lag_s=a.max_lag_s)
        rep = validation.report(cmp, a.person_ref, a.reference_system, a.movement, synthetic=a.synthetic)
        records.validate(rep, "validation-report")
        records.write_json(a.out, rep)
        print(json.dumps({"kinematics_rmse_deg": rep["kinematics_rmse_deg"], "approved_for": rep["approved_for"]}, indent=1))
    elif a.cmd == "synth":
        seq, truth, model = _synth(a.out, a.seed)
        print(f"wrote {seq}, {truth} and {model}")
    elif a.cmd in ("mp-mono", "mp-multiview"):
        from . import mediapipe_front as mf
        if a.cmd == "mp-mono":
            meta = {"person_ref": a.person_ref, "raw": str(a.raw)}
            if a.gravity_up_cv:
                meta.update(gravity_up_cv=[float(v) for v in a.gravity_up_cv.split(",")], gravity_source=a.gravity_source)
            seq = mf.monocular_sequence(dict(np.load(a.raw)), focal_px=a.focal_px, meta=meta)
        else:
            cams = mf.read_qca(a.qca)
            if len(cams) != len(a.raws):
                raise SystemExit(f"{len(a.raws)} dumps but {len(cams)} cameras in {a.qca}")
            seq, err = mf.multiview_sequence([dict(np.load(r)) for r in a.raws], cams,
                                             meta={"person_ref": a.person_ref, "raws": [str(r) for r in a.raws]})
        seq.save(a.out)
        print(json.dumps({"out": a.out, "frames": seq.n_frames, "valid": int(seq.valid.sum()),
                          **{k: seq.meta[k] for k in ("intrinsics_source", "reprojection_px_median") if k in seq.meta}}))
    elif a.cmd == "selftest":
        res, failures = selftest(a.out)
        per = res["validation"]["per_coordinate"]
        for c in SELFTEST_LIMITS:
            print(f"{c:18s} rmse {per[c]['rmse_deg']:.2f} deg (limit {SELFTEST_LIMITS[c]})")
        print(f"reps found: {res['metrics']['n_reps']} (expected 3)")
        if failures or res["metrics"]["n_reps"] != 3:
            print("SELFTEST FAILED", failures)
            return 1
        print("selftest OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
