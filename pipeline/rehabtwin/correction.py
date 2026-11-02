"""Correction view: "how this movement would look fixed", on the same model.

A clinician-authored correction spec (pipeline/configs/corrections/*.json)
changes selected joint-angle trajectories of a measured motion, e.g.

    {"coordinate": "hip_adduction_r", "mode": "mirror", "from": "hip_adduction_l"}
    {"coordinate": "hip_adduction_r", "mode": "clamp", "max": 2.0}
    {"coordinate": "L5_S1_Flex_Ext", "mode": "scale", "factor": 0.5}

and OpenSim IK re-solves the whole body so the result stays kinematically
consistent: corrected coordinates are tracked strongly, the rest of the
movement weakly, and the feet stay where they were (anchor tasks), so the
pelvis and other joints adapt the way a real body would have to. A spec can
``preserve`` chosen coordinates (higher weight than ``other``) so the change is
absorbed elsewhere, and name ``check_rules`` (a posture rule set) so the
corrected motion is checked for faults it removes and faults it introduces.

docs/accuracy.md red line: no corrected-posture *target* from a generic
skeleton. On a Tier-B/C body this module only runs with ``illustrative=True``,
and every output is labelled as an illustration, never a target.
"""
from __future__ import annotations

import json
from pathlib import Path
from xml.sax.saxutils import escape

import numpy as np

from .config import CONFIG_DIR
from .io_formats import Table, read_table, to_degrees, write_table, write_trc
from .filtering import lowpass
from .opensim_stage import _cwd, _osim

MODES = ("set", "clamp", "scale", "offset", "mirror")
ANCHOR_PREFIX = "ANCHOR_"


class CorrectionRefused(RuntimeError):
    pass


def load_spec(name_or_path):
    p = Path(name_or_path)
    if not p.suffix:
        p = CONFIG_DIR / "corrections" / f"{name_or_path}.json"
    spec = json.loads(p.read_text())
    spec["_path"] = str(p)
    for t in spec["targets"]:
        if t.get("mode") not in MODES:
            raise ValueError(f"{p}: unknown mode {t.get('mode')!r} (expected one of {MODES})")
    return spec


def apply_targets(table: Table, spec):
    """Target trajectories (deg) for the corrected coordinates: {coordinate: (T,)}."""
    out = {}
    for t in spec["targets"]:
        c = t["coordinate"]
        if not table.has(c):
            raise ValueError(f"coordinate {c!r} not in the motion")
        v = table.col(c).astype(float).copy()
        mode = t["mode"]
        if mode == "set":
            v[:] = t["value"]
        elif mode == "clamp":
            v = np.clip(v, t.get("min", -np.inf), t.get("max", np.inf))
        elif mode == "scale":
            ref = t.get("about", 0.0)
            v = ref + (v - ref) * t["factor"]
        elif mode == "offset":
            v = v + t["delta"]
        elif mode == "mirror":
            if not table.has(t["from"]):
                raise ValueError(f"mirror source {t['from']!r} not in the motion")
            v = table.col(t["from"]).astype(float).copy()
        out[c] = v
    return out


def _anchor_trajectories(model_path, table, anchors):
    """Ground positions of the anchor points (body origins) along the measured motion."""
    osim = _osim()
    model = osim.Model(str(model_path))
    state = model.initSystem()
    table = to_degrees(table, model)
    cs = model.getCoordinateSet()
    cols = [c for c in table.columns if cs.contains(c)]
    pos = np.zeros((len(table.time), len(anchors), 3))
    for f in range(len(table.time)):
        for c in cols:
            co = cs.get(c)
            v = table.data[f, table.columns.index(c)]
            co.setValue(state, np.radians(v) if co.getMotionType() == osim.Coordinate.Rotational else v, False)
        model.realizePosition(state)
        for k, a in enumerate(anchors):
            body, loc = a["body"], a.get("location", [0.0, 0.0, 0.0])
            p = model.getBodySet().get(body).findStationLocationInGround(state, osim.Vec3(*loc))
            pos[f, k] = [p.get(0), p.get(1), p.get(2)]
    return pos


def _model_with_anchors(model_path, anchors, out_path):
    osim = _osim()
    model = osim.Model(str(model_path))
    for a in anchors:
        mk = osim.Marker(ANCHOR_PREFIX + a["name"], model.getBodySet().get(a["body"]),
                         osim.Vec3(*a.get("location", [0.0, 0.0, 0.0])))
        model.addMarker(mk)
    model.finalizeConnections()
    model.initSystem()
    model.printToXML(str(out_path))


def correct(session_dir, spec, illustrative=False, motion=None, model=None):
    """Write ``<session>/correction/<spec name>/`` and return its summary dict."""
    osim = _osim()
    session_dir = Path(session_dir)
    sess = json.loads((session_dir / "session.json").read_text())
    tier = sess["twin_tier"]
    if tier != "A" and not illustrative:
        raise CorrectionRefused(
            f"twin tier {tier}: docs/accuracy.md forbids corrected-posture targets on a generic skeleton. "
            "Re-run with illustrative=True (--illustrative) to produce a labelled illustration that may not "
            "be used as a target or for feedback.")
    motion = Path(motion or session_dir / sess["pipeline"]["outputs"]["motion"])
    model = Path(model or session_dir / sess["pipeline"]["outputs"]["model"])
    out = session_dir / "correction" / spec["name"]
    out.mkdir(parents=True, exist_ok=True)
    measured = to_degrees(read_table(motion), model)     # spec values and target.mot are degrees

    # 1. target trajectories for every coordinate (corrected ones replaced)
    targets = apply_targets(measured, spec)
    m = osim.Model(str(model))
    state = m.initSystem()
    cs = m.getCoordinateSet()
    free = set(spec.get("free", []))
    w = spec.get("weights", {})
    tracked = []
    for c in measured.columns:
        if not cs.contains(c):
            continue
        co = cs.get(c)
        if co.isConstrained(state) or co.getLocked(state) or c in free:
            continue
        tracked.append(c)
    data = np.column_stack([targets.get(c, measured.col(c)) for c in tracked])
    write_table(out / "target.mot", tracked, data, measured.time, in_degrees=True, name="correction_target")

    # 2. anchors: the feet stay where they were measured
    anchors = spec.get("anchors", [])
    anchor_names = [ANCHOR_PREFIX + a["name"] for a in anchors]
    _model_with_anchors(model, anchors, out / "model_with_anchors.osim")
    write_trc(out / "anchors.trc", anchor_names, _anchor_trajectories(model, measured, anchors), measured.time)

    # 3. IK: anchors (strong) + corrected coordinates (strong) + everything else (weak)
    tasks = [f'<IKMarkerTask name="{escape(n)}"><apply>true</apply><weight>{w.get("anchor", 100.0)}</weight></IKMarkerTask>'
             for n in anchor_names]
    for c in tracked:
        if c in targets:
            wt = w.get("target", 50.0)
        elif cs.get(c).getMotionType() == osim.Coordinate.Translational:
            # metres, not radians: an untracked pelvis translation lets IK jitter sideways
            wt = w.get("translation", 100.0)
        else:
            wt = spec.get("preserve", {}).get(c, w.get("other", 1.0))
        tasks.append(f'<IKCoordinateTask name="{escape(c)}"><apply>true</apply><weight>{wt}</weight>'
                     "<value_type>from_file</value_type></IKCoordinateTask>")
    t0, t1 = measured.time[0], measured.time[-1]
    (out / "ik_setup.xml").write_text(f"""<?xml version="1.0" encoding="UTF-8" ?>
<OpenSimDocument Version="40500">
<InverseKinematicsTool name="corrected">
<results_directory>.</results_directory>
<model_file>model_with_anchors.osim</model_file>
<constraint_weight>Inf</constraint_weight>
<accuracy>1e-5</accuracy>
<IKTaskSet><objects>{"".join(tasks)}</objects><groups/></IKTaskSet>
<marker_file>anchors.trc</marker_file>
<coordinate_file>target.mot</coordinate_file>
<time_range> {t0} {t1}</time_range>
<report_errors>true</report_errors>
<output_motion_file>corrected.mot</output_motion_file>
<report_marker_locations>false</report_marker_locations>
</InverseKinematicsTool>
</OpenSimDocument>
""")
    with _cwd(out):
        if not osim.InverseKinematicsTool(str(out / "ik_setup.xml")).run():
            raise RuntimeError(f"correction IK failed ({out / 'ik_setup.xml'})")
    raw = read_table(out / "corrected.mot")
    # same smoothing as every measured motion (6 Hz zero-lag) before anyone differentiates it
    fps = 1.0 / float(np.median(np.diff(raw.time)))
    smooth = lowpass(raw.data, fps, spec.get("cutoff_hz", 6.0))
    write_table(out / "corrected_unfiltered.mot", raw.columns, raw.data, raw.time, raw.in_degrees, name="corrected_unfiltered")
    write_table(out / "corrected.mot", raw.columns, smooth, raw.time, raw.in_degrees, name="corrected")
    corrected = read_table(out / "corrected.mot")

    # 4. what changed, and is the result physically admissible?
    changes, compensations = {}, {}
    for c in corrected.columns:
        # constrained coordinates (coupled lumbar levels, patella) just follow their drivers
        if not measured.has(c) or c in free or (c not in tracked and c not in targets):
            continue
        d = corrected.col(c) - measured.col(c)
        if c in targets:
            changes[c] = {"max_abs_change_deg": round(float(np.max(np.abs(d))), 2),
                          "target_tracking_rmse_deg": round(float(np.sqrt(np.mean((corrected.col(c) - targets[c]) ** 2))), 2)}
        elif np.max(np.abs(d)) > spec.get("compensation_report_deg", 2.0):
            # what the rest of the body had to do to make the requested change with the feet planted
            compensations[c] = {"max_abs_change_deg": round(float(np.max(np.abs(d))), 2),
                                "mean_change_deg": round(float(np.mean(d)), 2)}
    # Range of motion: only what the correction introduces or worsens counts against it. A measured
    # motion can already leave a model's range (e.g. shoulder flexion > 90° in the Pose2Sim model).
    limits, pre_existing = [], []
    for c in corrected.columns:
        if not cs.contains(c):
            continue
        co = cs.get(c)
        rot = co.getMotionType() == osim.Coordinate.Rotational
        lo, hi = co.getRangeMin(), co.getRangeMax()
        if rot:
            lo, hi = np.degrees(lo), np.degrees(hi)

        def over(v):
            return float(max(np.max(v - hi), np.max(lo - v), 0.0))
        oc = over(corrected.col(c))
        om = over(measured.col(c)) if measured.has(c) else 0.0
        entry = {"coordinate": c, "exceeds_range_by": round(oc, 2), "measured_exceeds_by": round(om, 2),
                 "range": [round(lo, 1), round(hi, 1)]}
        if oc > om + 0.5:
            limits.append(entry)
        elif om > 0.5:
            pre_existing.append(entry)
    # feet drift of the final (filtered) motion, by forward kinematics against the measured anchors
    drift = np.linalg.norm(_anchor_trajectories(model, corrected, anchors) - _anchor_trajectories(model, measured, anchors),
                           axis=2)
    rms = np.sqrt(np.mean(drift ** 2, axis=1))
    anchor_err = {"marker_rms_m": {"mean": round(float(rms.mean()), 4), "p95": round(float(np.percentile(rms, 95)), 4),
                                   "max": round(float(rms.max()), 4), "max_single_point": round(float(drift.max()), 4)}}
    summary = {
        "spec": spec["name"],
        "spec_file": Path(spec["_path"]).name,
        "spec_author": spec.get("author", "unspecified"),
        "rationale": spec.get("rationale", ""),
        "twin_tier": tier,
        "status": "target" if tier == "A" else "ILLUSTRATION ONLY - generic skeleton; not a target, not for feedback",
        "measured_motion": str(motion.relative_to(session_dir)),
        "corrected_motion": str((out / "corrected.mot").relative_to(session_dir)),
        "changes": changes,
        "compensations": compensations,
        "range_of_motion_violations": limits,
        "range_exceeded_in_measured_motion": pre_existing,
        "feet_anchor_drift_m": anchor_err["marker_rms_m"],
        "admissible": bool(not limits and anchor_err["marker_rms_m"]["max"] < spec.get("max_feet_drift_m", 0.02)),
        "admissible_rule": f"no range-of-motion violation introduced or worsened by the correction and per-frame feet "
                           f"drift (RMS over anchors) < {spec.get('max_feet_drift_m', 0.02)} m",
    }
    (out / "correction.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary, measured, corrected, out


def rule_check(rules, time_m, sig_m, time_c, sig_c, standing=None):
    """Posture-rule violations of the measured vs the corrected motion (gating ignored: this is a check).
    ``standing``: the person's standing values, for rules relative to them (rehabtwin/feedback.py)."""
    from . import feedback
    spec = feedback.load_rules(rules)
    count = {}
    for label, t, sig in (("measured", time_m, sig_m), ("corrected", time_c, sig_c)):
        log, _ = feedback.replay(spec, t, sig, tier="A", allowed_joint_planes=[r["joint_plane"] for r in spec["rules"]],
                                 baselines=standing)
        for r in spec["rules"]:
            ends = [e for e in log if e.get("rule") == r["id"] and e.get("event") == "violation_end"]
            n = sum(1 for e in log if e.get("rule") == r["id"] and "decision" in e)
            count.setdefault(r["id"], {})[label] = {"violations": n, "worst": (max(ends, key=lambda e: abs(e["peak"]))["peak"]
                                                                               if ends else None)}
    return {"rules": spec["name"],
            "per_rule": count,
            "removed": sorted(k for k, v in count.items() if v["measured"]["violations"] and not v["corrected"]["violations"]),
            "introduced": sorted(k for k, v in count.items() if v["corrected"]["violations"] and not v["measured"]["violations"]),
            "note": "Rules replayed without the tier/validation gate: a check of the motion, not of feedback."}



FOOT_ANCHORS = [{"name": "heel_r", "body": "calcn_r"}, {"name": "toes_r", "body": "toes_r"},
                {"name": "midfoot_r", "body": "calcn_r", "location": [0.1, 0.0, 0.04]},
                {"name": "heel_l", "body": "calcn_l"}, {"name": "toes_l", "body": "toes_l"},
                {"name": "midfoot_l", "body": "calcn_l", "location": [0.1, 0.0, -0.04]}]


def plant_feet(model_path, motion_path, out_dir, start=None, stop=None, anchors=FOOT_ANCHORS,
               anchor_weight=1000.0, other_weight=0.01, translation_weight=0.1, cutoff_hz=6.0):
    """Double-stance prior: re-solve IK with both feet held at their median position over [start, stop].

    Video kinematics let planted feet wander (OpenCap's own squat IK: ~12 cm/s median calcaneus speed,
    9 cm excursion), and the quasi-static ground-force estimate differentiates the centre of mass twice.
    For exercises done without moving the feet, the feet are anchored where they stood and every
    coordinate is tracked weakly, so the rest of the body keeps its measured motion as far as the
    planted feet allow (real 5-camera squat: feet 5.6 cm -> 0.9 cm excursion for a 0.3° mean change
    in joint angles). Returns (planted motion path, qc dict).
    """
    osim = _osim()
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    measured = to_degrees(read_table(motion_path), model_path)     # target.mot is written in degrees
    t0 = measured.time[0] if start is None else start
    t1 = measured.time[-1] if stop is None else stop
    keep = (measured.time >= t0 - 1e-9) & (measured.time <= t1 + 1e-9)
    measured = Table(measured.columns, measured.data[keep], measured.time[keep], measured.in_degrees, measured.header)
    traj = _anchor_trajectories(model_path, measured, anchors)
    fixed = np.repeat(np.median(traj, axis=0)[None], len(measured.time), axis=0)
    names = [ANCHOR_PREFIX + a["name"] for a in anchors]
    _model_with_anchors(model_path, anchors, out / "model_with_anchors.osim")
    write_trc(out / "anchors.trc", names, fixed, measured.time)
    m = osim.Model(str(model_path))
    state = m.initSystem()
    cs = m.getCoordinateSet()
    tracked = [c for c in measured.columns if cs.contains(c) and not cs.get(c).isConstrained(state)
               and not cs.get(c).getLocked(state)]
    write_table(out / "target.mot", tracked, np.column_stack([measured.col(c) for c in tracked]), measured.time,
                in_degrees=True, name="plant_target")
    tasks = [f'<IKMarkerTask name="{escape(n)}"><apply>true</apply><weight>{anchor_weight}</weight></IKMarkerTask>'
             for n in names]
    tasks += [f'<IKCoordinateTask name="{escape(c)}"><apply>true</apply><weight>'
              f'{translation_weight if cs.get(c).getMotionType() == osim.Coordinate.Translational else other_weight}'
              "</weight><value_type>from_file</value_type></IKCoordinateTask>" for c in tracked]
    (out / "ik_setup.xml").write_text(f"""<?xml version="1.0" encoding="UTF-8" ?>
<OpenSimDocument Version="40500"><InverseKinematicsTool name="planted"><results_directory>.</results_directory>
<model_file>model_with_anchors.osim</model_file><constraint_weight>Inf</constraint_weight><accuracy>1e-5</accuracy>
<IKTaskSet><objects>{"".join(tasks)}</objects><groups/></IKTaskSet><marker_file>anchors.trc</marker_file>
<coordinate_file>target.mot</coordinate_file><time_range> {measured.time[0]} {measured.time[-1]}</time_range>
<report_errors>false</report_errors><output_motion_file>planted_unfiltered.mot</output_motion_file>
<report_marker_locations>false</report_marker_locations></InverseKinematicsTool></OpenSimDocument>
""")
    with _cwd(out):
        if not osim.InverseKinematicsTool(str(out / "ik_setup.xml")).run():
            raise RuntimeError(f"planted-feet IK failed ({out / 'ik_setup.xml'})")
    raw = read_table(out / "planted_unfiltered.mot")
    fps = 1.0 / float(np.median(np.diff(raw.time)))
    write_table(out / "planted.mot", raw.columns, lowpass(raw.data, fps, cutoff_hz), raw.time, raw.in_degrees, name="planted")
    planted = read_table(out / "planted.mot")
    after = _anchor_trajectories(model_path, planted, anchors)
    change = {c: float(np.sqrt(np.mean((planted.col(c) - measured.col(c)) ** 2)))
              for c in tracked if planted.has(c) and cs.get(c).getMotionType() == osim.Coordinate.Rotational}
    worst = sorted(change.items(), key=lambda kv: -kv[1])[:5]

    def drift(p):
        return round(float(np.max(np.linalg.norm(p - np.median(p, axis=0), axis=2))), 4)
    qc = {"method": "IK re-solve with both feet anchored at their median position (double-stance prior)",
          "feet_max_excursion_m": {"measured": drift(traj), "planted": drift(after)},
          "coordinate_rms_change_deg": {"mean": round(float(np.mean(list(change.values()))), 2),
                                        "largest": {c: round(v, 2) for c, v in worst}}}
    return out / "planted.mot", qc
