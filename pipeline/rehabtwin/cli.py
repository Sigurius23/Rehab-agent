"""Command line: ``python -m rehabtwin <command>``.

  process   SEQ.npz -> session folder (OpenSim model + IK, metrics, QC, session.json, report.html)
  validate  estimate .mot vs reference .mot -> validation-report.json
  synth     write a synthetic SKEL-like sequence with known truth
  selftest  synth -> process -> validate, exits non-zero if the round trip regresses
  mp-mono   raw MediaPipe dump (adapters/mediapipe_pose.py) -> monocular sequence .npz
  mp-multiview  raw MediaPipe dumps + Qualisys or OpenCap calibration (+ --sync) -> triangulated sequence .npz
  kinect    Kinect v1 recording (capture/kinect_v1) + MediaPipe dump of its colour frames -> depth-lifted sequence .npz
  person    init / set / build / attach / show: the persistent person model (bones, measurements, twin layers)
  augment   keypoint sequence -> + 43 anatomical markers (OpenCap LSTM via Pose2Sim) for mediapipe_lstm_pose2sim
  correct   session folder + correction spec -> corrected motion, correction.json, correction.html
  muscles   session folder -> estimated GRF, inverse dynamics, static optimisation (+ corrected / weakened what-ifs)
  cues      session folder + haptic rule set -> offline cue replay (gated; never drives hardware)
  lsl-simulate / lsl-live / lsl-listen   live cue loop over Lab Streaming Layer (pip install pylsl)
  vmc-posture   SlimeVR (VMC/OSC) skeleton -> live posture signals on LSL (pip install python-osc pylsl)
  suit-bridge   LSL cue markers -> SenseShift/bHaptics BLE payloads (dry run or BLE via bleak)
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

import numpy as np

from . import metrics as metrics_mod
from . import opensim_stage, records, report, validation
from .config import load_config, resolve
from .io_formats import read_table, to_degrees
from .kinematics import skeleton_positions
from .person import PersonRefused
from .sequence import MarkerSequence


def process(seq_path, out_dir, exercise="squat", config=None, mass_kg=None, height_m=None,
            reference=None, reference_system=None, person_ref=None, tier=None, video=None, max_lag_s=0.0,
            reference_model=None, reference_grade=None, model_provenance=None, started_at=None, person=None):
    """``person``: a person folder (rehabtwin/person.py). Its bones are used instead of scaling new ones,
    and its measured height and mass fill in what is not given."""
    from . import tiers
    started_at = records.parse_started_at(started_at) if started_at else None
    seq_path, out_dir = Path(seq_path), Path(out_dir)
    seq = MarkerSequence.load(seq_path)
    synthetic = bool(seq.meta.get("synthetic"))
    if reference and not synthetic and reference_grade is None:
        raise ValueError("a reference needs reference_grade ('marker-mocap' or 'markerless'): an unlabelled "
                         "reference must not be able to approve feedback")
    person_ref = person_ref or seq.meta.get("person_ref", "UNSPECIFIED")
    pinfo, mass_from = None, None
    if person:
        from . import person as person_mod
        pinfo = person_mod.for_session(person, None if person_ref == "UNSPECIFIED" else person_ref,
                                       synthetic=synthetic)
        person_ref = pinfo["person_ref"]
        height_m = height_m or pinfo["height_m"]
        if mass_kg is None and not (seq.meta.get("augmenter") or {}).get("mass_kg") and pinfo["mass_kg"]:
            mass_kg, mass_from = pinfo["mass_kg"], f"person model v{pinfo['version']}"
        if pinfo["model"]["kind"] == "personalised" and not model_provenance:
            model_provenance = pinfo["model"]["provenance_path"]
    person_cfg = (pinfo or {}).get("model", {}).get("config")
    cfg = load_config(config or (Path(person_cfg).stem if person_cfg else None)
                      or seq.meta.get("default_config", "skel105_pose2sim"))
    model_used = pinfo["model"]["path"] if pinfo and pinfo["model"]["kind"] == "personalised" else resolve(cfg["model"])
    # refuse before any work: the tier must be supported by evidence, not by a flag
    tier, tier_source = tiers.resolve(tier or seq.meta.get("tier", "C"), person_ref, synthetic, model_provenance,
                                      model_used)
    out_dir.mkdir(parents=True, exist_ok=True)
    kept = records.kept_started_at(records.read_session(out_dir / "session.json"), seq.meta, started_at)
    if kept:
        started_at = kept
        print(f"note: started_at {started_at} kept from the earlier processing", file=sys.stderr)

    def commit():
        # Unstamp before the first changed file: a run failing after scaling must leave what was derived
        # from the old files stale. A run refused before that (mass, nothing solvable) leaves the folder intact.
        if records.mark_reprocessing(out_dir / "session.json") and (out_dir / "index.html").exists():
            report.write_index(out_dir)
        if seq_path.resolve() != (out_dir / "skel_seq.npz").resolve():
            shutil.copy(seq_path, out_dir / "skel_seq.npz")

    stage = opensim_stage.run(seq, cfg, out_dir, mass_kg=mass_kg, height_m=height_m, on_commit=commit, person=pinfo)
    if mass_from:
        stage.qc["subject"]["mass_from"] = mass_from
    motion = max(stage.motions, key=lambda p: len(read_table(p).time))
    est = read_table(motion)
    trial = seq.times[seq.valid]
    trial_span = (float(trial[0]), float(trial[-1]))
    analysed = {"segment": stage.motions.index(motion) + 1, "of": len(stage.motions),
                "start_s": round(float(est.time[0]), 3), "stop_s": round(float(est.time[-1]), 3),
                "trial_s": round(trial_span[1] - trial_span[0], 3)}
    analysed["fraction"] = round((analysed["stop_s"] - analysed["start_s"]) / analysed["trial_s"], 3) \
        if analysed["trial_s"] > 0 else 1.0
    stage.qc["analysed_segment"] = analysed
    (out_dir / "qc.json").write_text(json.dumps(stage.qc, indent=2))
    if analysed["of"] > 1 or analysed["fraction"] < report.PARTIAL_TRIAL:
        print(f"note: {analysed['of']} solved segment(s); metrics and validation use "
              f"{analysed['start_s']}-{analysed['stop_s']} s ({analysed['fraction']:.0%} of the trial)", file=sys.stderr)
    pstamp = records.processing_stamp(stage.scaled_model, motion, tier, exercise)

    derived = metrics_mod.derived_signals(est, stage.scaled_model)
    skeleton = skeleton_positions(stage.scaled_model, est)
    val, ref_plot, ref_skeleton = None, None, None
    if reference:
        ref_tab = read_table(reference)
        ref_model = Path(reference_model) if reference_model else Path(reference).parent / "model_scaled.osim"
        ref_tab = to_degrees(ref_tab, ref_model if ref_model.exists() else None)
        if ref_model.exists():  # posture signals (inclination vs gravity, FPPA) can be validated too
            ref_skeleton = skeleton_positions(ref_model, ref_tab)
            ref_tab = metrics_mod.with_signals(ref_tab, metrics_mod.derived_signals(ref_tab, ref_model))
        cmp = validation.compare(metrics_mod.with_signals(est, derived), ref_tab, max_lag_s=max_lag_s,
                                 trial_span=trial_span)
        ref_plot = (ref_tab.time + cmp["lag_s"], {c: ref_tab.col(c) for c in ref_tab.columns})
        val = validation.report(cmp, person_ref, reference_system or str(reference), [exercise],
                                synthetic=synthetic, reference_grade=reference_grade or "synthetic")
        val["processing_id"] = pstamp["processing_id"]      # the feedback gate trusts no other processing's
        records.validate(val, "validation-report")
        records.write_json(out_dir / "validation-report.json", val)

    imputed_t = np.asarray(stage.qc["imputed_frames"], float) / seq.fps
    met, signals = metrics_mod.compute(est, stage.scaled_model, exercise, tier,
                                       allowed_joint_planes=(val or {}).get("feedback_allowed_joint_planes", ())
                                       if val and not val["synthetic"] else (),
                                       imputed_times=imputed_t,
                                       missing_times=np.asarray(stage.qc["missing_target_frames"], float) / seq.fps,
                                       validation_ref="validation-report.json" if val else None, derived=derived)
    records.write_json(out_dir / "metrics.json", met)
    outputs = {"model": stage.scaled_model.relative_to(out_dir), "motion": motion.relative_to(out_dir),
               "metrics": "metrics.json", "qc": "qc.json", "report": "report.html"}
    if val:
        outputs["validation_report"] = "validation-report.json"
    sess = records.session_record(seq, stage.qc, out_dir, tier, person_ref, video=video,
                                  config_name=Path(cfg["_path"]).name, outputs=outputs, validation_report=val,
                                  tier_source=tier_source, started_at=started_at)
    # derived results copy this id; index.html marks the ones from an earlier processing STALE
    sess["pipeline"].update(pstamp)
    if pinfo:
        sess["person_model"] = {**stage.qc["scaling"]["person_model"], "kind": pinfo["model"]["kind"],
                                "folder": str(Path(person).resolve())}
    records.validate(sess, "session")
    records.write_json(out_dir / "session.json", sess)
    report.write(out_dir / "report.html", sess, stage.qc, met, signals, est.time, val, ref_plot, skeleton, ref_skeleton)
    report.write_index(out_dir)
    return {"session": sess, "metrics": met, "qc": stage.qc, "validation": val, "motion": motion}


def run_correction(session_dir, spec_name, illustrative=False):
    """Correction view for a processed session (see rehabtwin/correction.py)."""
    from . import correction
    spec = correction.load_spec(spec_name)
    sess = json.loads((Path(session_dir) / "session.json").read_text())
    records.require_current(sess, "correct")
    from . import bone
    summary, measured, corrected, out = correction.correct(session_dir, spec, illustrative=illustrative)
    person_rec, _ = _person_record(Path(session_dir), sess)
    bone_status = ((person_rec or {}).get("bone_density") or {}).get("classification")
    summary["bone_density"], summary["bone_caveat"] = bone_status, bone.caveat(bone_status)
    model = Path(session_dir) / sess["pipeline"]["outputs"]["model"]
    sig_m = {c: measured.col(c) for c in measured.columns}
    sig_m.update(metrics_mod.derived_signals(measured, model))
    sig_c = {c: corrected.col(c) for c in corrected.columns}
    sig_c.update(metrics_mod.derived_signals(corrected, model))
    for k in ("knee_fppa_r", "knee_fppa_l", "torso.sagittal", "torso.frontal", "lumbar_total.sagittal"):
        if k in sig_m:
            summary.setdefault("derived_signals", {})[k] = {
                "measured_range": [round(float(np.min(sig_m[k])), 2), round(float(np.max(sig_m[k])), 2)],
                "corrected_range": [round(float(np.min(sig_c[k])), 2), round(float(np.max(sig_c[k])), 2)]}
    if spec.get("check_rules"):
        summary["rule_check"] = correction.rule_check(spec["check_rules"], measured.time, sig_m, corrected.time, sig_c)
    records.write_json(out / "correction.json", records.stamp(sess, summary))
    report.write_correction(out / "correction.html", summary, measured.time, sig_m, sig_c,
                            skeleton_positions(model, measured), skeleton_positions(model, corrected))
    report.write_index(session_dir)
    return summary, out


class AssumedMassRefused(ValueError):
    pass


def _session_mass(session_dir, allow_assumed_mass=False):
    """Body mass the session model was scaled to, from qc.json; refuse muscle/strength work on an assumed one.

    Ground forces are m (a_com + g), so every joint torque, muscle force, activation and N·m/kg scales
    with the mass: a silent config default must not pass as this person's numbers. Fails closed: a
    session without a recorded source counts as assumed.
    """
    qc = Path(session_dir) / "qc.json"
    subj = json.loads(qc.read_text()).get("subject", {}) if qc.exists() else {}
    bm = {"kg": subj.get("mass_kg"), "source": subj.get("mass_source", "unknown")}
    bm["assumed"] = bm["source"] not in opensim_stage.KNOWN_MASS_SOURCES
    if bm["assumed"] and not allow_assumed_mass:
        raise AssumedMassRefused(
            f"body mass {bm['source']} ({bm['kg']} kg): every force, torque and activation scales with it. "
            "Re-process with --mass-kg, or pass allow_assumed_mass=True (--allow-assumed-mass) for results "
            "labelled as resting on an assumed mass.")
    return bm


def _person_record(session_dir, sess, person=None):
    """(person.json, folder) of the session's person: ``person`` or the folder the session was processed with."""
    from . import person as person_mod
    folder = person or (sess.get("person_model") or {}).get("folder")
    if not folder:
        return None, None
    rec = person_mod.load(folder)
    if rec["person_ref"] != sess.get("person_ref"):
        raise person_mod.PersonRefused(f"person model {folder} is of {rec['person_ref']!r}, the session of "
                                       f"{sess.get('person_ref')!r}")
    return rec, Path(folder)


def _capacity_model(session_dir, sess, body_mass, use=True, person_rec=None):
    """(model, record): the session model with leg muscle capacity for this person (rehabtwin/capacity.py).

    From the person model, best first: measured volumes and fat fractions from muscle imaging; each leg's muscle
    from a DXA scan, whose regional masses also set the segment masses (rehabtwin/dxa.py); the age-and-sex model;
    the measured height and mass. Written to SESSION/capacity/; otherwise the session model and why it was not
    scaled."""
    from . import capacity
    from . import dxa as dxa_mod
    from . import person as person_mod
    model = session_dir / sess["pipeline"]["outputs"]["model"]
    qc = json.loads((session_dir / "qc.json").read_text())
    height = qc.get("subject", {}).get("height_m")
    p = person_rec or {}
    imaging, scan = p.get("muscle_imaging"), p.get("dxa")
    regression = not body_mass["assumed"] and bool(height)
    why = ("not requested (--generic-capacity)" if not use else
           "personalised model: its own muscle parameters"
           if qc.get("scaling", {}).get("method", "").startswith("person model: its personalised") else
           f"body mass {body_mass['source']}, not measured" if body_mass["assumed"] and not (imaging or scan) else
           "no height (process with --height-m or --person)" if not height and not (imaging or scan) else
           "session.json names no config (re-process)" if not sess["pipeline"].get("config") else None)
    if why:
        return model, {"scaled": False, "why_not": why}
    out = session_dir / "capacity"
    out.mkdir(exist_ok=True)
    cfg = load_config(Path(sess["pipeline"]["config"]).stem)
    age = person_mod.age_years(p, sess.get("started_at")) if p else None
    rec = capacity.scale_model(model, resolve(cfg["model"]), body_mass["kg"] if regression else None,
                               height if regression else None, out / "model_capacity.osim", imaging=imaging,
                               age_years=age, male=(p["sex"] == "male") if p.get("sex") else None,
                               dxa_leg_lean_kg=dxa_mod.leg_lean_kg(scan) if scan else None)
    rec = {"scaled": True, "model": "capacity/model_capacity.osim", **rec}
    if scan:
        rec["dxa"] = {k: scan[k] for k in ("method", "date", "approved_by", "sha256") if scan.get(k)}
        if scan["checks"]["distribution"]:
            from .opensim_stage import _osim
            m = _osim().Model(str(out / "model_capacity.osim"))
            rec["mass_distribution"] = dxa_mod.apply_mass_distribution(m, scan)
            m.finalizeConnections()
            m.printToXML(str(out / "model_capacity.osim"))
        else:
            rec["caveats"].append("Segment masses: the generic model's distribution (the DXA record lacks the full "
                                  "regional table: lean, fat and BMC of arms, legs, trunk and head).")
    if imaging or scan or rec.get("leg_source") == "anthropometry":
        rec["person_model"] = {"person_ref": person_rec["person_ref"], "version": person_rec["version"]}
    records.write_json(out / "capacity.json", records.stamp(sess, rec))
    return out / "model_capacity.osim", rec


def _capacity_summary(rec):
    return {k: rec[k] for k in ("scaled", "why_not", "method", "subject", "volume_ratio", "leg_source",
                                "leg_source_text", "leg_muscle_cm3", "factor_min", "factor_median", "factor_max",
                                "leg_fmax_N", "sources", "imaging", "dxa", "mass_distribution", "caveats") if k in rec}


def _muscle_source(cap):
    if not cap["scaled"]:
        return "generic (scaled literature muscle parameters)"
    leg = {"dxa": "DXA-calibrated leg muscle (per-leg lean mass)",
           "anthropometry": "body-size scaled by age, sex, height and mass (NHANES DXA model)",
           "regression": "body-size scaled (Handsfield 2014 regression)",
           "generic": "generic leg sizes"}[cap.get("leg_source", "regression")]
    return f"measured muscle imaging + {leg}" if cap.get("imaging") else leg


def strength_calibration(session_dir, tests_file, allow_assumed_mass=False, capacity=True, person=None):
    """Dynamometer torques → strength-calibrated copy of the session model (SESSION/strength/)."""
    from . import strength
    session_dir = Path(session_dir)
    sess = json.loads((session_dir / "session.json").read_text())
    records.require_current(sess, "strength")      # qc.json's mass may already be the new processing's
    body_mass = _session_mass(session_dir, allow_assumed_mass)
    spec = json.loads(Path(tests_file).read_text())
    out = session_dir / "strength"
    # untested muscles keep body-size capacities, and the tested groups' factors are relative to them
    base, cap = _capacity_model(session_dir, sess, body_mass, capacity, _person_record(session_dir, sess, person)[0])
    rec = strength.calibrate(base, spec["tests"], out)
    rec.update({k: spec[k] for k in ("device", "protocol", "tester", "date") if k in spec})
    rec["capacity"] = _capacity_summary(cap)
    rec["model"], rec["body_mass"] = sess["pipeline"]["outputs"]["model"], body_mass
    records.write_json(out / "strength.json", records.stamp(sess, rec))
    report.write_strength(out / "strength.html", rec, sess["twin_tier"])
    report.write_index(session_dir)
    return rec, out


def muscle_study(session_dir, rep=1, start=None, stop=None, correction=None, weaken=(), assist=(), view_3d=True,
                 grf_sensitivity=0.0, use_strength=False, passive=(), workers=None, max_fps=30.0, plant=True,
                 illustrative=False, allow_assumed_mass=False, capacity=True, person=None):
    """Measured motion (+ corrected motion, + weakened variants) through GRF estimate → ID → SO.

    ``capacity``: scale leg muscle capacity to the measured height and mass (rehabtwin/capacity.py)."""
    from . import muscles
    session_dir = Path(session_dir)
    sess = json.loads((session_dir / "session.json").read_text())
    records.require_current(sess, "muscles")       # qc.json's mass may already be the new processing's
    if (assist or passive) and sess["twin_tier"] != "A" and not illustrative:
        from .correction import CorrectionRefused
        raise CorrectionRefused(
            f"twin tier {sess['twin_tier']}: docs/accuracy.md forbids assistance profiles from an unvalidated tier. "
            "Re-run with illustrative=True (--illustrative) for a labelled design-space bound, not a device profile.")
    body_mass = _session_mass(session_dir, allow_assumed_mass)
    met = json.loads((session_dir / "metrics.json").read_text())
    from . import bone
    person_rec, _ = _person_record(session_dir, sess, person)
    model, cap = _capacity_model(session_dir, sess, body_mass, capacity and not use_strength, person_rec)
    muscle_model = {"source": _muscle_source(cap), "capacity": _capacity_summary(cap)}
    bone_status = ((person_rec or {}).get("bone_density") or {}).get("classification")
    if use_strength:
        model = session_dir / "strength" / "model_strength.osim"
        if not model.exists():
            raise SystemExit(f"{model} missing; run 'rehabtwin strength {session_dir} --tests FILE' first")
        st = json.loads((session_dir / "strength" / "strength.json").read_text())
        why = records.stale_reason(sess, st)
        if why:     # capacities fitted on an earlier model (other mass/scaling) must not drive this one
            raise records.StaleResult(f"strength/strength.json is stale ({why}); " + records.rerun_hint(
                sess, f"'rehabtwin strength {session_dir} --tests FILE'") + " before --strength")
        muscle_model = {"source": "strength-calibrated (dynamometry)", "tests": [t["action"] for t in st["tests"]],
                        "calibrated_muscles": st["calibrated_muscles"], "symmetry": st["symmetry"],
                        "capacity": st.get("capacity", {"scaled": False, "why_not": "calibrated before capacity scaling"})}
    motion = session_dir / sess["pipeline"]["outputs"]["motion"]
    if start is None or stop is None:
        if not met["reps"]:
            raise SystemExit("no reps in metrics.json; pass --start/--stop")
        r = met["reps"][rep - 1]
        start, stop = r["start_s"], r["stop_s"]
    exercise = met["exercise"] if met["exercise"] in muscles.VALID_EXERCISES else met["exercise"]
    out = session_dir / "muscles"
    # every variant: (label, output folder, motion, extra muscles.run arguments)
    variants = [("measured", "measured", motion, {})]
    stale_inputs = []
    if correction:
        corrected = session_dir / "correction" / correction / "corrected.mot"
        if not corrected.exists():
            raise SystemExit(f"{corrected} missing; run 'rehabtwin correct {session_dir} --spec {correction} ...' first")
        cj = corrected.parent / "correction.json"
        if cj.exists() and records.warn_if_stale(sess, json.loads(cj.read_text()), f"correction/{correction}"):
            stale_inputs.append(f"correction/{correction}")
        variants.append((f"corrected: {correction}", f"corrected_{correction}", corrected, {}))
    for spec in weaken:
        group, factor = spec.split("=")
        variants.append((f"{group} at {float(factor) * 100:.0f}%", f"weak_{group}_{factor}", motion,
                         {"weaken": {group: float(factor)}}))
    for spec in assist:
        coord, torque, lo, hi = muscles.parse_assist(spec)
        variants.append((f"ideal exo {coord} <= {torque:g} N·m" + ("" if (lo, hi) == (-1.0, 1.0) else f" ({spec.split(':')[1]})"),
                         f"exo_{spec.replace('=', '_').replace(':', '_')}", motion, {"assist": [spec]}))
    for spec in passive:
        coord, k, q0, direction = muscles.parse_passive(spec)
        variants.append((f"passive spring {coord} {k:g} N·m/rad from {q0:g}° ({direction})",
                         f"passive_{coord}_{k:g}_{q0:g}_{direction}", motion, {"passive": [spec]}))
    prior = {}
    if plant and exercise in muscles.VALID_EXERCISES:
        # double-stance exercise: hold both feet where they stood before differentiating anything
        from .correction import plant_feet
        planted = {}
        for _, folder, mot, _ in variants:
            if str(mot) not in planted:
                planted[str(mot)], prior[folder] = plant_feet(model, mot, out / "kinematics" / folder,
                                                              start=start - 0.5, stop=stop + 0.5)
        variants = [(lab, folder, planted[str(mot)], kw) for lab, folder, mot, kw in variants]
    used = {lab: mot for lab, _, mot, _ in variants}     # motion each variant moved with (3D muscle view)

    biases = [0.0] + ([grf_sensitivity, -grf_sensitivity] if grf_sensitivity else [])
    jobs = [(b, lab, dict(model_path=model, motion_path=mot, out_dir=out, label=folder + (f"_grf{b:+.2f}" if b else ""),
                          exercise=exercise, start=start, stop=stop, grf_share_bias=b, max_fps=max_fps,
                          muscle_model=muscle_model, **kw))
            for b in biases for lab, folder, mot, kw in variants]
    workers = min(len(jobs), workers or max(1, min(4, os.cpu_count() or 1)))
    if workers > 1:
        # variants are independent static-optimisation problems: one process each (OpenSim is single-threaded here)
        import multiprocessing
        from concurrent.futures import ProcessPoolExecutor
        with ProcessPoolExecutor(workers, mp_context=multiprocessing.get_context("spawn")) as pool:
            futures = [pool.submit(muscles.run, **kw) for _, _, kw in jobs]
            results = [f.result() for f in futures]
    else:
        results = [muscles.run(**kw) for _, _, kw in jobs]
    by_bias = {}
    for (b, lab, _), r in zip(jobs, results):
        by_bias.setdefault(b, {})[lab] = r
    runs = by_bias[0.0]
    study = {"twin_tier": sess["twin_tier"], "muscle_model": muscle_model, "body_mass": body_mass,
             "kinematics_prior": prior, "runs": runs, "bone_density": bone_status,
             "bone_caveat": bone.caveat(bone_status) if (assist or passive) else None,
             "devices_status": (None if not (assist or passive)
                                else "ILLUSTRATION ONLY - design-space bound on a generic body, not an assistance profile"
                                if sess["twin_tier"] != "A" else
                                f"ILLUSTRATION ONLY - device torques rest on an assumed body mass ({body_mass['kg']} kg, "
                                f"{body_mass['source']}), not an assistance profile" if body_mass["assumed"] else "target"),
             "comparisons": {lab: muscles.compare(runs["measured"], r) for lab, r in runs.items() if lab != "measured"}}
    if grf_sensitivity:
        # The left/right load split is the least certain input. Re-run every variant with the right
        # foot's share shifted both ways: a change is robust only if it keeps its sign and size under
        # every split (paired: variant and measured always share the same split).
        shifted = {b: by_bias[b] for b in (grf_sensitivity, -grf_sensitivity)}
        split_runs = {"measured": runs["measured"], **{f"right share {b:+.2f}": r["measured"] for b, r in shifted.items()}}
        study["grf_sensitivity"] = {"right_share_bias": grf_sensitivity, "bands": muscles.grf_bands(split_runs),
                                    "min_change": muscles.MIN_ROBUST_CHANGE}
        for lab, cmp in study["comparisons"].items():
            alt = [muscles.compare(r["measured"], r[lab]) for r in shifted.values()]
            for g, v in cmp.items():
                changes = [v["change"]] + [a[g]["change"] for a in alt if g in a]
                v["change_range_over_grf_split"] = [min(changes), max(changes)]
                v["robust_to_grf_split"] = muscles.robust_to_grf(changes)
    records.write_json(out / "study.json", records.stamp(sess, study, stale_inputs))
    view = muscles.view_data(model, {lab: out / r["label"] for lab, r in runs.items()},
                             {lab: used.get(lab, motion) for lab in runs}, start, stop) if view_3d else None
    report.write_muscles(out / "muscles.html", study, view)
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
    cj = Path(motion).parent / "correction.json" if motion else None      # replaying a corrected motion
    stale_inputs = [f"correction/{cj.parent.name}"] if cj and cj.exists() and records.warn_if_stale(
        sess, json.loads(cj.read_text()), f"correction/{cj.parent.name}") else []
    tab = to_degrees(read_table(Path(motion) if motion else session_dir / sess["pipeline"]["outputs"]["motion"]), model)
    signals = {c: tab.col(c) for c in tab.columns}
    signals.update(metrics_mod.derived_signals(tab, model))
    _, tier, allowed, gate_closed = _session_gate(session_dir, spec)
    log, sent = feedback.replay(spec, tab.time, signals, tier=tier, allowed_joint_planes=allowed)
    summ = feedback.summarise(spec, log, sent, tier, allowed)
    summ["validation_gate"] = gate_closed or "open"
    out = session_dir / "feedback" / (spec["name"] + (f"__{Path(motion).parent.name}" if motion else ""))
    out.mkdir(parents=True, exist_ok=True)
    summ["motion"] = str(motion) if motion else sess["pipeline"]["outputs"]["motion"]
    result = {"summary": summ, "spec": {k: v for k, v in spec.items() if k != "_path"}, "log": log}
    records.write_json(out / "cues.json", records.stamp(sess, result, stale_inputs))
    with open(out / "commands.csv", "w", newline="") as fh:   # LSL-ready marker events
        w = csv.DictWriter(fh, fieldnames=["timestamp", "actuator", "pattern", "intensity", "duration_ms", "rule", "message"])
        w.writeheader()
        w.writerows(sent)
    report.write_cues(out / "cues.html", result, tab.time, signals)
    report.write_index(session_dir)
    return result, out


def _session_gate(session_dir, spec=None):
    """(session, tier, allowed joint/planes, why closed) from a session's own records — no bypass.

    Feedback joint/planes are only taken from a validation report of the session's current processing
    (its processing_id), marker-mocap graded, not synthetic, for the same person, covering the rule set's
    exercise. Anything else closes the gate (fail closed: a report without a grade or a stamp predates
    them and counts as unknown).
    """
    session_dir = Path(session_dir)
    sess = json.loads((session_dir / "session.json").read_text())
    val_path = session_dir / "validation-report.json"
    if not val_path.exists():
        return sess, sess["twin_tier"], [], "no validation report"
    val = json.loads(val_path.read_text())
    why = records.validation_problem(sess, val)
    if not why and spec is not None and spec.get("exercise") not in val.get("movements", []):
        why = f"rule set exercise {spec.get('exercise')!r} not among validated movements {val.get('movements')}"
    allowed = [] if why else val.get("feedback_allowed_joint_planes", [])
    return sess, sess["twin_tier"], allowed, why


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


def person_shape(a):
    """``person shape``: fit the body surface to a recording's standing frames and store it in the person model."""
    from . import kinect, shape, tiers
    from . import person as person_mod
    rec = person_mod.load(a.folder)
    cap = kinect.read_capture(a.recording)
    frames, info = kinect.shape_frames(cap, dict(np.load(a.mediapipe)),
                                       True if a.mirrored else False if a.not_mirrored else "auto",
                                       frames=[int(f) for f in a.frames.split(",")] if a.frames else None)
    height = rec["anthropometrics"].get("height_m", {})
    print(f"fitting {len(frames)} frame(s) {info['frames']} ({', '.join(map(str, info['person_points']))} person points)",
          file=sys.stderr)
    fit = shape.fit_shape(shape.load_model(a.smplx_model), frames, info["K"], floor=info["floor"],
                          height_m=height.get("value") if a.use_height and height.get("measured") else None)
    source = {"recording": Path(a.recording).name, "frames": info["frames"], "mirrored": info["mirrored"],
              "body_model": {"file": Path(a.smplx_model).name, "sha256": tiers.sha256(a.smplx_model)},
              "runtime_s": fit["fit"]["runtime_s"]}
    return person_mod.set_surface_shape(a.folder, fit, source)


def person_command(a):
    from . import person as person_mod
    try:
        if a.person_cmd == "init":
            rec = person_mod.init(a.folder, a.person_ref, a.height_m, a.mass_kg, a.mass_source, age_years=a.age_years,
                                  sex=a.sex)
        elif a.person_cmd == "set":
            rec = person_mod.set_measurement(a.folder, a.height_m, a.mass_kg, a.mass_source, a.age_years, a.sex)
        elif a.person_cmd == "build":
            rec = person_mod.build_from_session(a.folder, a.session)
        elif a.person_cmd == "attach":
            rec = person_mod.attach_personalised_model(a.folder, a.model, a.provenance)
        elif a.person_cmd == "muscles":
            rec = person_mod.set_muscle_imaging(a.folder, a.record)
        elif a.person_cmd == "bone":
            rec = person_mod.set_bone_density(a.folder, a.record)
        elif a.person_cmd == "dxa":
            rec = person_mod.set_dxa(a.folder, a.record)
        elif a.person_cmd == "shape":
            rec = person_shape(a)
        else:
            rec = person_mod.load(a.folder)
    except (ValueError, FileNotFoundError) as e:     # includes PersonRefused and records.StaleResult
        print(f"refused: {e}", file=sys.stderr)
        return 2
    print(person_mod.summary(rec))
    return 0


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
    p.add_argument("--reference-grade", choices=["marker-mocap", "markerless"],
                   help="markerless = another video system (agreement only; approves nothing)")
    p.add_argument("--max-lag-s", type=float, default=0.0, help="search a time offset for unsynchronised references")
    p.add_argument("--reference-model", help="OpenSim model of the reference (default: model_scaled.osim next to it); "
                                             "enables validation of trunk/pelvis inclination and knee FPPA")
    p.add_argument("--person-ref", help="pseudonymous subject reference (never a name)")
    p.add_argument("--tier", choices=["A", "B", "C"], help="B/A need --model-provenance (default C)")
    p.add_argument("--model-provenance", help="JSON record that grants Tier B/A for this person and model (rehabtwin/tiers.py)")
    p.add_argument("--video")
    p.add_argument("--person", help="person folder (rehabtwin person init/build): use the person's bones instead of "
                                    "scaling new ones; their measured height and mass fill in what is not given")
    p.add_argument("--started-at", help="recording time, ISO 8601 with UTC offset (e.g. 2026-10-21T09:30:00+02:00); "
                                        "orders sessions in 'progress' (default: processing time, flagged there)")
    v = sub.add_parser("validate", help="compare two .mot files")
    v.add_argument("estimate")
    v.add_argument("reference")
    v.add_argument("--out", default="validation-report.json")
    v.add_argument("--reference-system", default="unspecified reference")
    v.add_argument("--person-ref", default="UNSPECIFIED")
    v.add_argument("--movement", action="append", default=[])
    v.add_argument("--max-lag-s", type=float, default=0.0)
    v.add_argument("--synthetic", action="store_true")
    v.add_argument("--reference-grade", choices=["marker-mocap", "markerless"],
                   help="required unless --synthetic: only marker-mocap can approve feedback")
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
    m.add_argument("--mirrored", action="store_true",
                   help="clip is a mirrored front-camera (selfie) recording dumped without the adapter's --mirrored")
    mv = sub.add_parser("mp-multiview", help="MediaPipe raw dumps + calibration -> triangulated sequence")
    mv.add_argument("raws", nargs="+", help="one raw dump per camera, in calibration camera order")
    cal = mv.add_mutually_exclusive_group(required=True)
    cal.add_argument("--qca", help="Qualisys .qca.txt calibration (lab z-up)")
    cal.add_argument("--opencap-calib", nargs="+", metavar="PICKLE",
                     help="OpenCap cameraIntrinsicsExtrinsics.pickle per camera, same order as the dumps (board y-down)")
    mv.add_argument("--sync", action="store_true",
                    help="estimate per-camera frame offsets from hip motion (unsynchronised phones)")
    mv.add_argument("--max-lag-s", type=float, default=2.0,
                    help="--sync search window, s: largest plausible start offset between phones (lags up to twice it "
                         "are checked; refused if one of those beats the window's best)")
    mv.add_argument("--out", required=True)
    mv.add_argument("--person-ref", default="UNSPECIFIED")
    kn = sub.add_parser("kinect", help="Kinect v1 recording + MediaPipe dump of its colour frames -> depth-lifted sequence")
    kn.add_argument("recording", help="KinectCapture output folder (docs/kinect-v1.md)")
    kn.add_argument("mediapipe", help="adapters/mediapipe_pose.py dump of RECORDING/colour/%%06d.jpg")
    kn.add_argument("out")
    kn.add_argument("--height-m", type=float, help="standing height; scales the skin-to-joint-centre offsets (default 1.70)")
    kn.add_argument("--mass-kg", type=float, help="body mass: with --height-m gives the BMI the offsets grow with "
                                                  "(default: BMI 25 assumed)")
    kn.add_argument("--person-ref", default="UNSPECIFIED")
    kn.add_argument("--person", help="person folder: height, mass and segment lengths from the person model "
                                     "(explicit options win)")
    kn.add_argument("--segment-lengths", help="JSON of known segment lengths in m, e.g. {\"LHip-LKnee\": 0.43} from "
                                              "the person's model (default: measured in this recording)")
    km = kn.add_mutually_exclusive_group()
    km.add_argument("--mirrored", action="store_true", help="the colour stream is mirrored (default: decided from the "
                                                            "SDK skeleton's left/right labels)")
    km.add_argument("--not-mirrored", action="store_true", help="the colour stream is not mirrored")
    pe = sub.add_parser("person", help="the persistent person model every session of a person uses")
    psub = pe.add_subparsers(dest="person_cmd", required=True)
    pi = psub.add_parser("init", help="start a person folder")
    pi.add_argument("folder")
    pi.add_argument("--person-ref", required=True, help="pseudonymous subject reference (never a name)")
    pset = psub.add_parser("set", help="record a new measured height and/or body mass, age or sex")
    pset.add_argument("folder")
    for q in (pi, pset):
        q.add_argument("--height-m", type=float)
        q.add_argument("--mass-kg", type=float)
        q.add_argument("--mass-source", choices=["measured", "assumed"], default="measured")
        q.add_argument("--age-years", type=float, help="age today (stored with the date; counts on from there)")
        q.add_argument("--sex", choices=["female", "male"],
                       help="with the age, sizes the leg muscles when no scan does (NHANES DXA reference data)")
    pb = psub.add_parser("build", help="take a processed calibration session's scaled model as the person's bones")
    pb.add_argument("folder")
    pb.add_argument("session")
    pa = psub.add_parser("attach", help="use an imaging-personalised model with its provenance record (Tier B/A)")
    pa.add_argument("folder")
    pa.add_argument("model")
    pa.add_argument("--provenance", required=True, help="model-provenance record (rehabtwin/tiers.py)")
    pmu = psub.add_parser("muscles", help="measured muscle size and quality (MRI/CT segmentation: volume, fat fraction)")
    pmu.add_argument("folder")
    pmu.add_argument("record", help="JSON: method, date, muscles {label_side: {volume_cm3, fat_fraction}} "
                                    "(docs/person-model.md)")
    pbo = psub.add_parser("bone", help="bone density (DXA T/Z-scores or QCT vBMD) -> screening category")
    pbo.add_argument("folder")
    pbo.add_argument("record", help="JSON: method, date, age_years, sex, postmenopausal, sites (docs/person-model.md)")
    pdx = psub.add_parser("dxa", help="whole-body DXA regional table: leg muscle per leg, segment masses, fat, "
                                      "bone density")
    pdx.add_argument("folder")
    pdx.add_argument("record", help="JSON: method, date, regions {left_leg: {lean_kg, fat_kg, bmc_kg}, ...}, "
                                    "bone_density? (docs/person-model.md)")
    psp = psub.add_parser("shape", help="body surface: SMPL-X fitted to standing frames of a Kinect recording")
    psp.add_argument("folder")
    psp.add_argument("recording", help="KinectCapture folder with player_registered.u8")
    psp.add_argument("mediapipe", help="adapters/mediapipe_pose.py dump of RECORDING/colour/%%06d.jpg")
    psp.add_argument("--smplx-model", required=True, help="SMPL-X .npz (licensed separately; stays outside the repo)")
    psp.add_argument("--frames", help="comma-separated frame numbers (default: up to 2 standing frames, 1 s apart)")
    psp.add_argument("--use-height", action="store_true",
                     help="fit with the measured height as a prior (then the height no longer checks the fit)")
    psm = psp.add_mutually_exclusive_group()
    psm.add_argument("--mirrored", action="store_true")
    psm.add_argument("--not-mirrored", action="store_true")
    psh = psub.add_parser("show", help="what the person model holds, per twin layer")
    psh.add_argument("folder")
    au = sub.add_parser("augment", help="add OpenCap's LSTM anatomical markers to a keypoint sequence (pip install onnxruntime)")
    au.add_argument("sequence")
    au.add_argument("out")
    au.add_argument("--height-m", type=float, required=True)
    au.add_argument("--mass-kg", type=float, required=True, help="body mass (an LSTM input); see --mass-source")
    au.add_argument("--mass-source", choices=("measured", "assumed"), default="assumed",
                    help="'measured' if the person was weighed; an assumed mass carries over to process as assumed, "
                         "so muscles/strength refuse it without --allow-assumed-mass (default: assumed)")
    au.add_argument("--max-gap-s", type=float, default=0.2,
                    help="mask outputs over input gaps longer than this; must equal the process config's "
                         "filter.max_gap_s (0.2 s in the shipped configs)")
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
    mu.add_argument("--assist", action="append", default=[], metavar="COORD=NM[:pos|neg]",
                    help="ideal assistive device, e.g. knee_angle_r=40:neg (extension only); trunk: "
                         "lumbar_total_extension=30:pos (physical N·m between pelvis and thorax); repeatable")
    mu.add_argument("--no-3d", action="store_true", help="skip the 3D muscle view (smaller report)")
    mu.add_argument("--illustrative", action="store_true",
                    help="allow --assist/--passive below Tier A as a labelled design-space bound (never a device profile)")
    mu.add_argument("--strength", action="store_true", help="use the strength-calibrated model (rehabtwin strength)")
    mu.add_argument("--person", help="person folder whose muscle imaging and bone density to use (default: the one "
                                     "the session was processed with)")
    mu.add_argument("--generic-capacity", action="store_true",
                    help="keep the generic subject's muscle forces (default: leg capacity scaled to measured height and mass)")
    mu.add_argument("--workers", type=int, help="parallel static-optimisation processes (default: up to 4)")
    mu.add_argument("--no-plant", action="store_true",
                    help="use the measured motion as is (default for double-stance exercises: feet held where they stood)")
    mu.add_argument("--max-fps", type=float, default=30.0, help="analyse at most this frame rate (default 30)")
    mu.add_argument("--passive", action="append", default=[], metavar="COORD=K[@Q0][:pos|neg]",
                    help="passive one-sided spring/elastic, e.g. knee_angle_r=40@10:pos (N·m/rad, slack until 10° "
                         "flexion); back elastic resisting trunk flexion: lumbar_total_extension=60@0:neg; repeatable")
    mu.add_argument("--allow-assumed-mass", action="store_true",
                    help="run although the session's body mass is assumed, not measured (report labelled as assumed mass)")
    mu.add_argument("--grf-sensitivity", type=float, default=0.0, metavar="SHARE",
                    help="also re-run with the right foot's load share shifted by +/-SHARE (e.g. 0.15) and flag "
                         "which changes are larger than the band that GRF split alone causes")
    stp = sub.add_parser("strength", help="calibrate muscle capacities from dynamometer joint torques")
    stp.add_argument("session")
    stp.add_argument("--tests", required=True, help="JSON with measured isometric torques (see configs/strength/)")
    stp.add_argument("--person", help="person folder whose muscle imaging to use (default: the session's)")
    stp.add_argument("--generic-capacity", action="store_true",
                     help="calibrate on the generic subject's muscle forces instead of body-size scaled ones")
    stp.add_argument("--allow-assumed-mass", action="store_true",
                     help="run although the session's body mass is assumed, not measured (report labelled as assumed mass)")
    pg = sub.add_parser("progress", help="compare sessions: which changes beat rep scatter and measurement error")
    pg.add_argument("sessions", nargs="+")
    pg.add_argument("--out", required=True, help="folder for progress.json / progress.html")
    pg.add_argument("--signals", nargs="*", help="limit to these signals (default: all shared)")
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
    vp = sub.add_parser("vmc-posture", help="SlimeVR VMC skeleton -> LSL posture stream for lsl-live")
    vp.add_argument("--port", type=int, default=39539, help="UDP port SlimeVR sends VMC to")
    vp.add_argument("--rate-hz", type=float, default=60.0)
    vp.add_argument("--duration-s", type=float)
    vp.add_argument("--print", action="store_true", help="also print the signals once per second")
    vp.add_argument("--host", default="127.0.0.1",
                    help="address to listen on (default localhost; 0.0.0.0 exposes posture input to the network)")
    sb = sub.add_parser("suit-bridge", help="LSL cue markers -> haptic suit payloads")
    sb.add_argument("--mapping", default="suit_bhaptics", help="name in pipeline/configs/feedback or a path")
    sb.add_argument("--ble", action="append", default=[], metavar="DEVICE=ADDRESS",
                    help="BLE address per mapped device (e.g. vest=AA:BB:CC:DD:EE:FF); omit for a dry run")
    sb.add_argument("--duration-s", type=float)
    sb.add_argument("--log", help="write the dry-run payload log to this JSON file")
    a = ap.parse_args(argv)

    if a.cmd == "process":
        try:
            res = process(a.sequence, a.out, a.exercise, a.config, a.mass_kg, a.height_m, a.reference,
                          a.reference_system, a.person_ref, a.tier, a.video, a.max_lag_s, a.reference_model,
                          a.reference_grade, a.model_provenance, started_at=a.started_at, person=a.person)
        except ValueError as e:      # includes tiers.TierRefused and person.PersonRefused
            print(f"refused: {e}", file=sys.stderr)
            return 2
        print(json.dumps({"reps": res["metrics"]["n_reps"], "tier": res["metrics"]["tier"],
                          "ik_marker_rms_m": res["qc"]["ik"]["marker_rms_m"], "report": str(Path(a.out) / "report.html")}, indent=2))
    elif a.cmd == "validate":
        if not a.synthetic and not a.reference_grade:
            raise SystemExit("--reference-grade is required (marker-mocap or markerless)")
        cmp = validation.compare(read_table(a.estimate), read_table(a.reference), max_lag_s=a.max_lag_s)
        rep = validation.report(cmp, a.person_ref, a.reference_system, a.movement, synthetic=a.synthetic,
                                reference_grade=a.reference_grade or "synthetic")
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
            try:
                seq = mf.monocular_sequence(dict(np.load(a.raw)), focal_px=a.focal_px, meta=meta, mirrored=a.mirrored)
            except ValueError as e:      # e.g. --mirrored on a dump the adapter already un-mirrored
                print(f"refused: {e}", file=sys.stderr)
                return 2
        else:
            if a.qca:
                cams, up, source = mf.read_qca(a.qca), "z", "Qualisys calibration file"
            else:
                cams, up, source = mf.read_opencap_calibration(a.opencap_calib), "-y", "OpenCap calibration (checkerboard)"
            if len(cams) != len(a.raws):
                raise SystemExit(f"{len(a.raws)} dumps but {len(cams)} cameras in the calibration")
            raws = [dict(np.load(r)) for r in a.raws]
            meta = {"person_ref": a.person_ref, "raws": [str(r) for r in a.raws]}
            if a.sync:
                try:
                    lags, peaks, diag = mf.sync_lags(raws, max_lag_s=a.max_lag_s, return_diagnostics=True)
                except ValueError as e:
                    print(f"refused: {e}", file=sys.stderr)
                    return 2
                warnings = [d["warning"] for d in diag if d and d["warning"]]
                for w in warnings:
                    print(f"warning: {w}", file=sys.stderr)
                raws, start = mf.apply_lags(raws, lags)
                meta.update(sync={"method": "hip vertical velocity cross-correlation (Pearson r per lag)", "lags_frames": lags,
                                  "peak_correlation": peaks, "reference_start_frame": start, "max_lag_s": a.max_lag_s,
                                  "diagnostics": diag, "warnings": warnings})
                print(json.dumps({"sync_lags_frames": lags, "peak_correlation": peaks}))
            seq, err = mf.multiview_sequence(raws, cams, up_axis=up, meta=meta, intrinsics_source=source)
        seq.save(a.out)
        print(json.dumps({"out": a.out, "frames": seq.n_frames, "valid": int(seq.valid.sum()),
                          **{k: seq.meta[k] for k in ("intrinsics_source", "reprojection_px_median") if k in seq.meta}}))
    elif a.cmd == "kinect":
        from . import kinect
        try:
            height, mass, ref = a.height_m, a.mass_kg, a.person_ref
            lengths = json.loads(Path(a.segment_lengths).read_text()) if a.segment_lengths else None
            meta = {"raw": str(a.mediapipe)}
            if a.person:
                from . import person as person_mod
                pinfo = person_mod.for_session(a.person, None if ref == "UNSPECIFIED" else ref)
                ref, height, mass = pinfo["person_ref"], height or pinfo["height_m"], mass or pinfo["mass_kg"]
                lengths = lengths or pinfo["keypoint_segments"] or None
                meta["person_model"] = {k: pinfo[k] for k in ("person_ref", "version", "sha256")}
            cap = kinect.read_capture(a.recording)
            seq = kinect.rgbd_sequence(cap, dict(np.load(a.mediapipe)), height,
                                       True if a.mirrored else False if a.not_mirrored else "auto",
                                       meta={"person_ref": ref, **meta}, mass_kg=mass, segment_lengths_m=lengths)
        except ValueError as e:
            print(f"refused: {e}", file=sys.stderr)
            return 2
        seq.save(a.out)
        k = seq.meta["kinect"]
        print(json.dumps({"out": a.out, "frames": seq.n_frames, "valid": int(seq.valid.sum()),
                          "mirrored": seq.meta["mirrored"], "gravity_source": seq.meta.get("gravity_source"),
                          "lifted_fraction_median": float(np.median(list(k["lifted_fraction"].values()))),
                          "depth_inconsistent_frames": k["depth_inconsistent_frames"],
                          "placed_by_segment_length_frames": k["placed_by_segment_length_frames"],
                          "segments_without_length": k["segments_without_length"]}))
    elif a.cmd == "person":
        return person_command(a)
    elif a.cmd == "augment":
        from .augmenter import augment
        seq = augment(MarkerSequence.load(a.sequence), a.height_m, a.mass_kg, max_gap_s=a.max_gap_s,
                      mass_source=a.mass_source)
        seq.save(a.out)
        print(json.dumps({"out": a.out, "markers": len(seq.marker_names), "frames": seq.n_frames,
                          "default_config": seq.meta["default_config"]}))
    elif a.cmd == "correct":
        from .correction import CorrectionRefused
        try:
            summary, out = run_correction(a.session, a.spec, a.illustrative)
        except (CorrectionRefused, records.StaleResult, PersonRefused) as e:
            print(f"refused: {e}", file=sys.stderr)
            return 2
        print(json.dumps({"status": summary["status"], "admissible": summary["admissible"],
                          "derived_signals": summary.get("derived_signals"), "report": str(out / "correction.html")}, indent=1))
    elif a.cmd == "muscles":
        from .correction import CorrectionRefused
        try:
            study, out = muscle_study(a.session, a.rep, a.start, a.stop, a.correction, a.weaken, a.assist, not a.no_3d,
                                      a.grf_sensitivity, a.strength, a.passive, a.workers, a.max_fps, not a.no_plant,
                                      a.illustrative, a.allow_assumed_mass, not a.generic_capacity, a.person)
        except (CorrectionRefused, AssumedMassRefused, records.StaleResult, PersonRefused) as e:
            print(f"refused: {e}", file=sys.stderr)
            return 2
        for lab, cmp in study["comparisons"].items():
            top = sorted(cmp.items(), key=lambda kv: -abs(kv[1]["change"]))[:5]
            print(lab + ": " + ", ".join(f"{g} {v['base']:.2f}->{v['other']:.2f}" for g, v in top))
        print(f"report: {out / 'muscles.html'}")
    elif a.cmd == "strength":
        try:
            rec, out = strength_calibration(a.session, a.tests, a.allow_assumed_mass, not a.generic_capacity, a.person)
        except (AssumedMassRefused, records.StaleResult, PersonRefused) as e:
            print(f"refused: {e}", file=sys.stderr)
            return 2
        for t in rec["tests"]:
            print(f"{t['action']:24s} measured {t['measured_Nm']:7.1f} N·m  generic model {t['generic_model_Nm']:7.1f}  "
                  f"factor {t['factor']:.2f}{'  AT BOUND' if t['at_bound'] else ''}")
        for act, v in rec["symmetry"].items():
            print(f"LSI {act}: {v['lsi_pct']}% (weaker: {v['weaker_side']}){'  < 90 %' if v['flag'] else ''}")
        print(f"report: {out / 'strength.html'}")
    elif a.cmd == "progress":
        from . import progress
        try:
            prog = progress.compare(a.sessions, a.signals)
        except ValueError as e:      # e.g. a started_at that is not an ISO timestamp
            print(f"refused: {e}", file=sys.stderr)
            return 2
        out = Path(a.out)
        out.mkdir(parents=True, exist_ok=True)
        records.write_json(out / "progress.json", prog)
        report.write_progress(out / "progress.html", prog)
        for w in prog["warnings"]:
            print("WARNING:", w)
        for sig, j in prog["first_to_last"].items():
            if j and j["change"] is None:
                print(f"{sig:24s} {j['verdict']}")
            elif j:
                print(f"{sig:24s} {j['from']:7.1f} -> {j['to']:7.1f}  ({j['change']:+.1f})  {j['verdict']}")
        print(f"report: {out / 'progress.html'}")
    elif a.cmd == "cues":
        result, out = cue_replay(a.session, a.rules, a.motion)
        for rid, pr in result["summary"]["per_rule"].items():
            print(f"{rid:16s} violations {pr['violations']}  sent {pr['cues_sent']}  would {pr['would_cue']}  gate: {pr['gate'] or 'open'}")
        print(f"report: {out / 'cues.html'}")
    elif a.cmd == "lsl-simulate":
        from . import feedback, lsl_bridge
        sess, _, _, _ = _session_gate(a.session)
        spec = feedback.load_rules(a.rules)
        tab = to_degrees(read_table(Path(a.session) / sess["pipeline"]["outputs"]["motion"]),
                         Path(a.session) / sess["pipeline"]["outputs"]["model"])
        derived = metrics_mod.derived_signals(tab, Path(a.session) / sess["pipeline"]["outputs"]["model"])
        sig = lsl_bridge.session_signals(tab, derived, [r["signal"] for r in spec["rules"]])
        print(f"streaming {len(sig)} signals x {len(tab.time)} samples as '{lsl_bridge.POSTURE_STREAM}'")
        lsl_bridge.stream_posture(tab.time, sig, speed=a.speed, session_id=sess["session_id"],
                                  front_end=sess["pipeline"]["front_end"])
    elif a.cmd == "lsl-live":
        from . import feedback, lsl_bridge
        spec = feedback.load_rules(a.rules)
        sess, tier, allowed, why = _session_gate(a.session, spec)
        if why:
            print(f"feedback gate closed: {why}", file=sys.stderr)
        eng = lsl_bridge.run_live(spec, tier, allowed, a.duration_s, publish_would_cue=a.publish_would_cue,
                                  expect_session=sess["session_id"], expect_front_end=sess["pipeline"]["front_end"])
        print(json.dumps([e for e in eng.log if "decision" in e], indent=1))
    elif a.cmd == "lsl-listen":
        from . import lsl_bridge
        for c in lsl_bridge.listen(a.duration_s):
            print(json.dumps(c))
    elif a.cmd == "vmc-posture":
        from . import vmc
        last = [0.0]

        def show(t, sig):
            if a.print and t - last[0] >= 1.0:
                last[0] = t
                print(json.dumps({k: round(v, 1) for k, v in sig.items()}))
        print(f"listening for VMC on udp/{a.port}; publishing LSL stream 'rehabtwin_posture' ({', '.join(vmc.SIGNALS)})")
        if a.host not in ("127.0.0.1", "localhost", "::1"):
            print(f"warning: listening on {a.host}: any host that can reach udp/{a.port} can inject posture",
                  file=sys.stderr)
        vmc.serve(a.port, a.rate_hz, a.duration_s, publish_lsl=True, on_signals=show, host=a.host)
    elif a.cmd == "suit-bridge":
        from . import suit
        driver = suit.SuitDriver(a.mapping)
        if a.ble:
            transport = suit.BleTransport(dict(x.split("=", 1) for x in a.ble), devices=list(driver.layouts))
        else:
            transport = suit.DryRunTransport()
            print("dry run: payloads are logged, nothing is written to hardware")
        suit.run_bridge(driver, transport, a.duration_s)
        if isinstance(transport, suit.DryRunTransport):
            for e in transport.log:
                print(json.dumps(e))
            if a.log:
                Path(a.log).write_text(json.dumps(transport.log, indent=1))
        if driver.rejected:
            print(f"warning: {len(driver.rejected)} cues dropped by the on-time share cap", file=sys.stderr)
        if driver.unknown:
            print(f"warning: cues for unmapped actuators ignored: {sorted(driver.unknown)}", file=sys.stderr)
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
