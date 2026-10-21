"""Command line: ``python -m rehabtwin <command>``.

  process   SEQ.npz -> session folder (OpenSim model + IK, metrics, QC, session.json, report.html)
  validate  estimate .mot vs reference .mot -> validation-report.json
  synth     write a synthetic SKEL-like sequence with known truth
  selftest  synth -> process -> validate, exits non-zero if the round trip regresses
  mp-mono   raw MediaPipe dump (adapters/mediapipe_pose.py) -> monocular sequence .npz
  mp-multiview  synchronised raw MediaPipe dumps + Qualisys calibration -> triangulated sequence .npz
  correct   session folder + correction spec -> corrected motion, correction.json, correction.html
  muscles   session folder -> estimated GRF, inverse dynamics, static optimisation (+ corrected / weakened what-ifs)
  cues      session folder + haptic rule set -> offline cue replay (gated; never drives hardware)
  lsl-simulate / lsl-live / lsl-listen   live cue loop over Lab Streaming Layer (pip install pylsl)
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
    report.write_index(out_dir)
    return {"session": sess, "metrics": met, "qc": stage.qc, "validation": val, "motion": motion}


def run_correction(session_dir, spec_name, illustrative=False):
    """Correction view for a processed session (see rehabtwin/correction.py)."""
    from . import correction
    spec = correction.load_spec(spec_name)
    summary, measured, corrected, out = correction.correct(session_dir, spec, illustrative=illustrative)
    model = Path(session_dir) / json.loads((Path(session_dir) / "session.json").read_text())["pipeline"]["outputs"]["model"]
    sig_m = {c: measured.col(c) for c in measured.columns}
    sig_m.update(metrics_mod.derived_signals(measured, model))
    sig_c = {c: corrected.col(c) for c in corrected.columns}
    sig_c.update(metrics_mod.derived_signals(corrected, model))
    for k in ("knee_fppa_r", "knee_fppa_l", "torso.sagittal", "torso.frontal", "lumbar_total.sagittal"):
        if k in sig_m:
            summary.setdefault("derived_signals", {})[k] = {
                "measured_range": [round(float(np.min(sig_m[k])), 2), round(float(np.max(sig_m[k])), 2)],
                "corrected_range": [round(float(np.min(sig_c[k])), 2), round(float(np.max(sig_c[k])), 2)]}
    records.write_json(out / "correction.json", summary)
    report.write_correction(out / "correction.html", summary, measured.time, sig_m, sig_c,
                            skeleton_positions(model, measured), skeleton_positions(model, corrected))
    report.write_index(session_dir)
    return summary, out


def muscle_study(session_dir, rep=1, start=None, stop=None, correction=None, weaken=()):
    """Measured motion (+ corrected motion, + weakened variants) through GRF estimate → ID → SO."""
    from . import muscles
    session_dir = Path(session_dir)
    sess = json.loads((session_dir / "session.json").read_text())
    met = json.loads((session_dir / "metrics.json").read_text())
    model = session_dir / sess["pipeline"]["outputs"]["model"]
    motion = session_dir / sess["pipeline"]["outputs"]["motion"]
    if start is None or stop is None:
        if not met["reps"]:
            raise SystemExit("no reps in metrics.json; pass --start/--stop")
        r = met["reps"][rep - 1]
        start, stop = r["start_s"], r["stop_s"]
    exercise = met["exercise"] if met["exercise"] in muscles.VALID_EXERCISES else met["exercise"]
    out = session_dir / "muscles"
    runs = {"measured": muscles.run(model, motion, out, label="measured", exercise=exercise, start=start, stop=stop)}
    if correction:
        corrected = session_dir / "correction" / correction / "corrected.mot"
        if not corrected.exists():
            raise SystemExit(f"{corrected} missing; run 'rehabtwin correct {session_dir} --spec {correction} ...' first")
        runs[f"corrected: {correction}"] = muscles.run(model, corrected, out, label=f"corrected_{correction}",
                                                       exercise=exercise, start=start, stop=stop)
    for spec in weaken:
        group, factor = spec.split("=")
        lab = f"{group} at {float(factor) * 100:.0f}%"
        runs[lab] = muscles.run(model, motion, out, weaken={group: float(factor)}, label=f"weak_{group}_{factor}",
                                exercise=exercise, start=start, stop=stop)
    study = {"twin_tier": sess["twin_tier"], "runs": runs,
             "comparisons": {lab: muscles.compare(runs["measured"], r) for lab, r in runs.items() if lab != "measured"}}
    records.write_json(out / "study.json", study)
    report.write_muscles(out / "muscles.html", study)
    report.write_index(session_dir)
    return study, out


def cue_replay(session_dir, rules, motion=None):
    """Offline replay of a haptic rule set over a processed session (never drives hardware)."""
    import csv
    from . import feedback
    session_dir = Path(session_dir)
    sess = json.loads((session_dir / "session.json").read_text())
    spec = feedback.load_rules(rules)
    model = session_dir / sess["pipeline"]["outputs"]["model"]
    tab = read_table(Path(motion) if motion else session_dir / sess["pipeline"]["outputs"]["motion"])
    signals = {c: tab.col(c) for c in tab.columns}
    signals.update(metrics_mod.derived_signals(tab, model))
    val_path = session_dir / "validation-report.json"
    allowed = []
    if val_path.exists():
        val = json.loads(val_path.read_text())
        if not val.get("synthetic"):
            allowed = val.get("feedback_allowed_joint_planes", [])
    log, sent = feedback.replay(spec, tab.time, signals, tier=sess["twin_tier"], allowed_joint_planes=allowed)
    summ = feedback.summarise(spec, log, sent, sess["twin_tier"], allowed)
    out = session_dir / "feedback" / (spec["name"] + (f"__{Path(motion).parent.name}" if motion else ""))
    out.mkdir(parents=True, exist_ok=True)
    summ["motion"] = str(motion) if motion else sess["pipeline"]["outputs"]["motion"]
    result = {"summary": summ, "spec": {k: v for k, v in spec.items() if k != "_path"}, "log": log}
    records.write_json(out / "cues.json", result)
    with open(out / "commands.csv", "w", newline="") as fh:   # LSL-ready marker events
        w = csv.DictWriter(fh, fieldnames=["timestamp", "actuator", "pattern", "intensity", "duration_ms", "rule", "message"])
        w.writeheader()
        w.writerows(sent)
    report.write_cues(out / "cues.html", result, tab.time, signals)
    report.write_index(session_dir)
    return result, out


def _session_gate(session_dir):
    """(tier, allowed joint/planes) from a session's own records — the live loop has no bypass."""
    session_dir = Path(session_dir)
    sess = json.loads((session_dir / "session.json").read_text())
    allowed = []
    val_path = session_dir / "validation-report.json"
    if val_path.exists():
        val = json.loads(val_path.read_text())
        if not val.get("synthetic"):
            allowed = val.get("feedback_allowed_joint_planes", [])
    return sess, sess["twin_tier"], allowed


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
    co = sub.add_parser("correct", help="correction view for a processed session")
    co.add_argument("session")
    co.add_argument("--spec", required=True, help="name in pipeline/configs/corrections or a path")
    co.add_argument("--illustrative", action="store_true",
                    help="allow a labelled illustration on a Tier-B/C body (never a target, never for feedback)")
    mu = sub.add_parser("muscles", help="muscle effects: estimated GRF -> ID -> static optimisation")
    mu.add_argument("session")
    mu.add_argument("--rep", type=int, default=1, help="rep from metrics.json to analyse (default 1)")
    mu.add_argument("--start", type=float)
    mu.add_argument("--stop", type=float)
    mu.add_argument("--correction", help="also analyse correction/<spec>/corrected.mot")
    mu.add_argument("--weaken", action="append", default=[], metavar="GROUP=FACTOR",
                    help="what-if weakness, e.g. gluteus_medius_r=0.5 (repeatable)")
    cu = sub.add_parser("cues", help="offline replay of haptic posture-cue rules over a session")
    cu.add_argument("session")
    cu.add_argument("--rules", required=True, help="name in pipeline/configs/feedback or a path")
    cu.add_argument("--motion", help="replay another motion (e.g. correction/<spec>/corrected.mot)")
    ls = sub.add_parser("lsl-simulate", help="stream a session's posture signals over LSL (no hardware needed)")
    ls.add_argument("session")
    ls.add_argument("--rules", required=True)
    ls.add_argument("--speed", type=float, default=1.0)
    ll = sub.add_parser("lsl-live", help="live cue loop: LSL posture stream -> CueEngine -> LSL cue markers")
    ll.add_argument("--rules", required=True)
    ll.add_argument("--session", required=True, help="the subject's processed session: tier + validation gate the cues")
    ll.add_argument("--duration-s", type=float)
    ll.add_argument("--publish-would-cue", action="store_true", help="also publish blocked cues as diagnostics")
    lt = sub.add_parser("lsl-listen", help="print cue markers (stand-in for the suit firmware bridge)")
    lt.add_argument("--duration-s", type=float, default=30.0)
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
    elif a.cmd == "correct":
        from .correction import CorrectionRefused
        try:
            summary, out = run_correction(a.session, a.spec, a.illustrative)
        except CorrectionRefused as e:
            print(f"refused: {e}", file=sys.stderr)
            return 2
        print(json.dumps({"status": summary["status"], "admissible": summary["admissible"],
                          "derived_signals": summary.get("derived_signals"), "report": str(out / "correction.html")}, indent=1))
    elif a.cmd == "muscles":
        study, out = muscle_study(a.session, a.rep, a.start, a.stop, a.correction, a.weaken)
        for lab, cmp in study["comparisons"].items():
            top = sorted(cmp.items(), key=lambda kv: -abs(kv[1]["change"]))[:5]
            print(lab + ": " + ", ".join(f"{g} {v['base']:.2f}->{v['other']:.2f}" for g, v in top))
        print(f"report: {out / 'muscles.html'}")
    elif a.cmd == "cues":
        result, out = cue_replay(a.session, a.rules, a.motion)
        for rid, pr in result["summary"]["per_rule"].items():
            print(f"{rid:16s} violations {pr['violations']}  sent {pr['cues_sent']}  would {pr['would_cue']}  gate: {pr['gate'] or 'open'}")
        print(f"report: {out / 'cues.html'}")
    elif a.cmd == "lsl-simulate":
        from . import feedback, lsl_bridge
        sess, _, _ = _session_gate(a.session)
        spec = feedback.load_rules(a.rules)
        tab = read_table(Path(a.session) / sess["pipeline"]["outputs"]["motion"])
        derived = metrics_mod.derived_signals(tab, Path(a.session) / sess["pipeline"]["outputs"]["model"])
        sig = lsl_bridge.session_signals(tab, derived, [r["signal"] for r in spec["rules"]])
        print(f"streaming {len(sig)} signals x {len(tab.time)} samples as '{lsl_bridge.POSTURE_STREAM}'")
        lsl_bridge.stream_posture(tab.time, sig, speed=a.speed)
    elif a.cmd == "lsl-live":
        from . import feedback, lsl_bridge
        _, tier, allowed = _session_gate(a.session)
        eng = lsl_bridge.run_live(feedback.load_rules(a.rules), tier, allowed, a.duration_s,
                                  publish_would_cue=a.publish_would_cue)
        print(json.dumps([e for e in eng.log if "decision" in e], indent=1))
    elif a.cmd == "lsl-listen":
        from . import lsl_bridge
        for c in lsl_bridge.listen(a.duration_s):
            print(json.dumps(c))
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
