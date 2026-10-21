"""Progress across sessions: did the movement change, or is it within the error?

For every posture/joint signal the sessions share, the per-session value is the mean of the
rep peaks (metrics.json). A change between two sessions is judged twice:

* rep-to-rep: |Δ| > 1.96 · sqrt(sd₁²/n₁ + sd₂²/n₂) — larger than the scatter between reps;
* measurement: |Δ| > MDC95 = 1.96 · √2 · error, with *error* the joint × plane RMSE of each
  session's validation against a reference system (the larger of the two). RMSE includes
  bias that may cancel between sessions on the same setup, so this is conservative.

Without a non-synthetic validation for that joint × plane the measurement test cannot be made
and the verdict says so: a change can be consistent across reps and still be a tracking
artefact (lighting, clothing, camera placement). Front-end or tier changes between sessions
are flagged because the numbers are then not comparable.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

Z95 = 1.96
METHOD = ("Session value = mean of rep peaks. A change counts only if it exceeds the rep-to-rep scatter "
          "(1.96·sqrt(sd1²/n1 + sd2²/n2)) and the minimal detectable change from validation "
          "(MDC95 = 1.96·√2·RMSE vs a reference system, larger of the two sessions). Without a non-synthetic "
          "validation of that joint × plane the size of a change is not validated.")


def load(session_dir):
    d = Path(session_dir)
    sess = json.loads((d / "session.json").read_text())
    met = json.loads((d / "metrics.json").read_text())
    val = None
    if (d / "validation-report.json").exists():
        val = json.loads((d / "validation-report.json").read_text())
    return {"dir": str(d), "session_id": sess["session_id"], "started_at": sess["started_at"],
            "person_ref": sess.get("person_ref"),
            "tier": sess["twin_tier"], "front_end": sess["pipeline"]["front_end"], "exercise": met["exercise"],
            "n_reps": met["n_reps"], "summary": met["summary"], "validation": val}


def measurement_error(session, joint, plane):
    """Validated RMSE (deg) for joint × plane, or None (no validation, synthetic, or not covered)."""
    val = session["validation"]
    if not val or val.get("synthetic"):
        return None
    return val.get("kinematics_rmse_deg", {}).get(joint, {}).get(plane)


def judge(a, b, signal):
    """Change of ``signal`` from session a to b with its two detectability tests."""
    sa, sb = a["summary"].get(signal), b["summary"].get(signal)
    if not sa or not sb or sa["rep_peak_mean"] is None or sb["rep_peak_mean"] is None:
        return None
    delta = sb["rep_peak_mean"] - sa["rep_peak_mean"]
    out = {"from": sa["rep_peak_mean"], "to": sb["rep_peak_mean"], "change": round(delta, 2), "unit": sb["unit"],
           "joint": sb["joint"], "plane": sb["plane"]}
    if sa["rep_peak_sd"] is not None and sb["rep_peak_sd"] is not None and a["n_reps"] > 1 and b["n_reps"] > 1:
        thr = Z95 * np.sqrt(sa["rep_peak_sd"] ** 2 / a["n_reps"] + sb["rep_peak_sd"] ** 2 / b["n_reps"])
        out["rep_threshold"] = round(float(thr), 2)
        out["beyond_rep_scatter"] = bool(abs(delta) > thr)
    errs = [measurement_error(s, sb["joint"], sb["plane"]) for s in (a, b)]
    if all(e is not None for e in errs):
        mdc = Z95 * np.sqrt(2.0) * max(errs)
        out["mdc95"] = round(float(mdc), 2)
        out["beyond_measurement_error"] = bool(abs(delta) > mdc)
    if out.get("beyond_rep_scatter") is False:
        out["verdict"] = "within rep-to-rep scatter"
    elif "mdc95" not in out:
        out["verdict"] = ("consistent across reps; size not validated" if out.get("beyond_rep_scatter")
                          else "not enough reps to judge")
    elif out["beyond_measurement_error"]:
        out["verdict"] = "real change (beyond rep scatter and measurement error)"
    else:
        out["verdict"] = "within measurement error"
    return out


def compare(session_dirs, signals=None):
    """Chronological comparison of sessions (first → each later one, and consecutive steps)."""
    sessions = sorted((load(d) for d in session_dirs), key=lambda s: s["started_at"])
    if len(sessions) < 2:
        raise ValueError("progress needs at least two sessions")
    common = set.intersection(*(set(s["summary"]) for s in sessions))
    signals = [s for s in (signals or sorted(common)) if s in common]
    warnings = []
    if len({s["person_ref"] for s in sessions}) > 1:
        raise ValueError("progress compares one person's sessions; person_ref differs: "
                         + ", ".join(sorted(str(s["person_ref"]) for s in sessions)))
    for key in ("exercise", "front_end", "tier"):
        vals = {s[key] for s in sessions}
        if len(vals) > 1:
            warnings.append(f"{key} differs between sessions ({', '.join(sorted(vals))}): values are not directly comparable")
    first, last = sessions[0], sessions[-1]
    series = {sig: [{"session_id": s["session_id"], "started_at": s["started_at"], "mean": s["summary"][sig]["rep_peak_mean"],
                     "sd": s["summary"][sig]["rep_peak_sd"], "n_reps": s["n_reps"]} for s in sessions] for sig in signals}
    return {"sessions": [{k: s[k] for k in ("session_id", "started_at", "tier", "front_end", "exercise", "n_reps", "dir")}
                         for s in sessions],
            "warnings": warnings,
            "first_to_last": {sig: judge(first, last, sig) for sig in signals},
            "steps": [{"from": a["session_id"], "to": b["session_id"], "changes": {sig: judge(a, b, sig) for sig in signals}}
                      for a, b in zip(sessions, sessions[1:])],
            "series": series,
            "method": METHOD}
