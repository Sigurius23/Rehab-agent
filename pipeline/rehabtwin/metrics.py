"""Rep segmentation and per-rep movement metrics from an IK motion.

Every number carries its claim label (docs/accuracy.md): the twin tier that
produced it and whether its joint/plane passed validation. Only Tier-A,
validated numbers are marked ``feedback_eligible``; everything else is
screening information.
"""
from __future__ import annotations

import json
import re

import numpy as np
from scipy.signal import find_peaks

from .config import CONFIG_DIR
from .io_formats import Table, to_degrees
from .kinematics import classify_signal, segment_orientations


def load_exercises():
    data = json.loads((CONFIG_DIR / "exercises.json").read_text())
    return {k: v for k, v in data.items() if not k.startswith("_")}


def derived_signals(table: Table, model_path):
    """Body inclinations vs gravity, knee FPPA and total lumbar angles, keyed like 'torso.sagittal'."""
    table = to_degrees(table, model_path)      # lumbar totals sum raw columns
    orient, fppa = segment_orientations(model_path, table)
    sig = {}
    for body, d in orient.items():
        sig[f"{body}.sagittal"] = d["sagittal_deg"]
        sig[f"{body}.frontal"] = d["frontal_deg"]
    sig["knee_fppa_r"], sig["knee_fppa_l"] = fppa["r"], fppa["l"]
    for kind, plane in (("Flex_Ext", "sagittal"), ("Lat_Bending", "frontal"), ("axial_rotation", "transverse")):
        cols = [c for c in table.columns if re.match(rf"^L\d_.*{kind}$", c)]
        if cols:
            sig[f"lumbar_total.{plane}"] = np.sum([table.col(c) for c in cols], axis=0)
    return sig


def describe_signal(name):
    """(joint, plane, unit, meaning) for coordinates and derived signals."""
    joint, plane = classify_signal(name)
    if name.startswith("lumbar_total."):
        meaning = "sum of lumbar-level angles"
    elif "." in name:
        meaning = {"sagittal": "forward lean vs vertical (+ forward)",
                   "frontal": "sideways lean vs vertical (+ to subject's right)"}[plane]
    elif name.startswith("knee_fppa_"):
        meaning = "knee frontal-plane projection angle (+ valgus)"
    else:
        meaning = "OpenSim coordinate"
    return joint, plane, "deg", meaning


def with_signals(table: Table, signals: dict) -> Table:
    """``table`` plus derived signals as extra columns (for validation of posture signals)."""
    table = to_degrees(table)      # the signals are degrees: a radian flag would be applied to them too
    names = [n for n in signals if n not in table.columns]
    data = np.column_stack([table.data] + [np.asarray(signals[n], float) for n in names]) if names else table.data
    return Table(table.columns + names, data, table.time, table.in_degrees, table.header)


def segment_reps(signal, fps, min_prominence_deg, min_rep_s):
    """Peaks of ``signal`` and the rep windows around them: [(start, peak, stop)]."""
    sig = np.asarray(signal, float)
    peaks, _ = find_peaks(sig, prominence=min_prominence_deg, distance=max(1, int(min_rep_s * fps)))
    reps = []
    for k, p in enumerate(peaks):
        lo = peaks[k - 1] if k > 0 else 0
        hi = peaks[k + 1] if k + 1 < len(peaks) else len(sig) - 1
        start = lo + int(np.argmin(sig[lo:p + 1]))
        stop = p + int(np.argmin(sig[p:hi + 1]))
        reps.append((int(start), int(p), int(stop)))
    return reps


def compute(table: Table, model_path, exercise="squat", tier="C", allowed_joint_planes=(),
            imputed_times=(), validation_ref=None, derived=None):
    """Per-rep metrics + session summary (dict ready for metrics.json)."""
    prof = load_exercises()[exercise]
    table = to_degrees(table, model_path)
    fps = 1.0 / float(np.median(np.diff(table.time)))
    signals = {c: table.col(c) for c in table.columns}
    signals.update(derived if derived is not None else derived_signals(table, model_path))
    key = [k for k in prof["key"] if k in signals]
    drivers = [d for d in prof.get("driver", []) if d in signals]
    reps = []
    if drivers:
        drive = np.mean([signals[d] for d in drivers], axis=0)
        reps = segment_reps(drive, fps, prof["min_prominence_deg"], prof["min_rep_s"])
    imputed = np.asarray(sorted(imputed_times), float)

    def label(name):
        joint, plane, unit, meaning = describe_signal(name)
        validated = f"{joint}.{plane}" in set(allowed_joint_planes)
        return {"joint": joint, "plane": plane, "unit": unit, "meaning": meaning, "validated": validated,
                "feedback_eligible": bool(tier == "A" and validated)}

    rep_out = []
    for i, (a, p, b) in enumerate(reps):
        t0, tp, t1 = table.time[a], table.time[p], table.time[b]
        touches_imputed = bool(len(imputed) and ((imputed >= t0) & (imputed <= t1)).any())
        vals = {}
        for k in key:
            s = signals[k][a:b + 1]
            vals[k] = {"at_peak": round(float(signals[k][p]), 2), "max": round(float(s.max()), 2),
                       "min": round(float(s.min()), 2), "rom": round(float(s.max() - s.min()), 2)}
        asym = {}
        for k in key:
            if k.endswith("_r") and k[:-2] + "_l" in vals:
                r, l = vals[k]["at_peak"], vals[k[:-2] + "_l"]["at_peak"]
                asym[k[:-2]] = {"r_minus_l_at_peak": round(r - l, 2)}
        rep_out.append({"rep": i + 1, "start_s": round(float(t0), 3), "peak_s": round(float(tp), 3),
                        "stop_s": round(float(t1), 3), "duration_s": round(float(t1 - t0), 3),
                        "contains_imputed_frames": touches_imputed, "values": vals, "asymmetry": asym})

    summary = {}
    for k in key:
        s = signals[k]
        peaks = [r["values"][k]["at_peak"] for r in rep_out]
        summary[k] = {**label(k), "session_min": round(float(s.min()), 2), "session_max": round(float(s.max()), 2),
                      "rep_peak_mean": round(float(np.mean(peaks)), 2) if peaks else None,
                      "rep_peak_sd": round(float(np.std(peaks)), 2) if len(peaks) > 1 else None}
    return {
        "exercise": exercise,
        "tier": tier,
        "claims": _claims(tier),
        "validation_report": validation_ref,
        "n_reps": len(rep_out),
        "rep_driver": drivers,
        "reps": rep_out,
        "summary": summary,
    }, signals


def _claims(tier):
    return {
        "A": "Imaging-personalised twin: validated joint/planes may drive feedback (clinician-reviewed).",
        "B": "Scan/photo-personalised: progress visualisation and gross screening only; every number carries Tier-B error.",
        "C": "Video/IMU on a statistical body: adherence, rep counting and gross movement review only. No anatomical or corrective claims.",
    }[tier]
