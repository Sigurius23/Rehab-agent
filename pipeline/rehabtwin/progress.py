"""Progress across sessions: did the movement change, or is it within the error?

For every posture/joint signal the sessions share, the per-session value is the mean of the
rep peaks (metrics.json). A change between two sessions is judged twice:

* rep-to-rep (Welch t-test, two-sided 5 %): |Δ| > t₀.₉₇₅(ν) · sqrt(s₁²/n₁ + s₂²/n₂), s the sample
  SD of the rep peaks and ν the Welch–Satterthwaite df. With 3 reps per session ν ≤ 4 and t ≥ 2.8:
  the normal 1.96 would call ~12 % of unchanged sessions "beyond rep scatter", Welch ~3.5 %
  (slightly conservative, and robust to the scatter differing between days). Needs ≥ 2 reps in
  both sessions; otherwise no change is called real;
* measurement: |Δ| > MDC95 = 1.96 · √2 · error, with *error* the joint × plane RMSE of each
  session's validation against marker-based motion capture (the larger of the two). RMSE includes
  bias that may cancel between sessions on the same setup, so this is conservative.

Without a marker-mocap validation for that joint × plane the measurement test cannot be made
and the verdict says so: a change can be consistent across reps and still be a tracking
artefact (lighting, clothing, camera placement). Agreement with another markerless system or a
synthetic round trip does not size a change. Front-end or tier changes between sessions are
flagged because the numbers are then not comparable, and so is an order of sessions that rests
on processing time rather than recording time.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.stats import t as student_t

Z95 = 1.96
RECORDED = ("argument", "sequence metadata")     # started_at sources that are recording time
METHOD = ("Session value = mean of rep peaks. A change counts only if it exceeds the rep-to-rep scatter "
          "(Welch t-test: t0.975(Welch–Satterthwaite df)·sqrt(s1²/n1 + s2²/n2), s = sample SD, ≥ 2 reps per "
          "session) and the minimal detectable change from validation (MDC95 = 1.96·√2·RMSE vs marker-based "
          "motion capture, larger of the two sessions). Without a marker-mocap validation of that joint × plane "
          "the size of a change is not validated.")


def load(session_dir):
    d = Path(session_dir)
    sess = json.loads((d / "session.json").read_text())
    met = json.loads((d / "metrics.json").read_text())
    val = None
    if (d / "validation-report.json").exists():
        val = json.loads((d / "validation-report.json").read_text())
    return {"dir": str(d), "session_id": sess["session_id"], "started_at": sess["started_at"],
            "started_at_source": sess.get("started_at_source"), "person_ref": sess.get("person_ref"),
            "tier": sess["twin_tier"], "front_end": sess["pipeline"]["front_end"], "exercise": met["exercise"],
            "n_reps": met["n_reps"], "summary": met["summary"], "validation": val}


def measurement_error(session, joint, plane):
    """Validated RMSE (deg) for joint × plane, or None (no validation, not marker-mocap, or not covered).

    Only a marker-mocap reference measures error; agreement with a markerless system shares its
    failure modes and a synthetic round trip tests the software, so neither may size a change.
    """
    val = session["validation"]
    if not val or val.get("synthetic") or val.get("reference_grade") != "marker-mocap":
        return None
    return val.get("kinematics_rmse_deg", {}).get(joint, {}).get(plane)


def rep_threshold(sd1, n1, sd2, n2, alpha=0.05):
    """Welch t-test threshold on |mean₂ − mean₁| from sample SDs; the 1.96 of a z-test is far too
    small at a few reps (3 reps each: ν ≤ 4 → t ≥ 2.78)."""
    v1, v2 = sd1 ** 2 / n1, sd2 ** 2 / n2
    den = v1 ** 2 / (n1 - 1) + v2 ** 2 / (n2 - 1)
    df = (v1 + v2) ** 2 / den if den > 0 else n1 + n2 - 2     # both SDs 0: threshold is 0 whatever the df
    return float(student_t.ppf(1 - alpha / 2, df) * np.sqrt(v1 + v2))


def judge(a, b, signal):
    """Change of ``signal`` from session a to b with its two detectability tests."""
    sa, sb = a["summary"].get(signal), b["summary"].get(signal)
    if not sa or not sb:
        return None
    out = {"from": sa["rep_peak_mean"], "to": sb["rep_peak_mean"], "change": None, "unit": sb["unit"],
           "joint": sb["joint"], "plane": sb["plane"]}
    if sa["rep_peak_mean"] is None or sb["rep_peak_mean"] is None:
        out["verdict"] = "no reps"
        return out
    delta = sb["rep_peak_mean"] - sa["rep_peak_mean"]
    out["change"] = round(delta, 2)
    if sa["rep_peak_sd"] is not None and sb["rep_peak_sd"] is not None and a["n_reps"] >= 2 and b["n_reps"] >= 2:
        thr = rep_threshold(sa["rep_peak_sd"], a["n_reps"], sb["rep_peak_sd"], b["n_reps"])
        out["rep_threshold"] = round(thr, 2)
        out["beyond_rep_scatter"] = bool(abs(delta) > thr)
    errs = [measurement_error(s, sb["joint"], sb["plane"]) for s in (a, b)]
    if all(e is not None for e in errs):
        mdc = Z95 * np.sqrt(2.0) * max(errs)
        out["mdc95"] = round(float(mdc), 2)
        out["beyond_measurement_error"] = bool(abs(delta) > mdc)
    if "beyond_rep_scatter" not in out:    # 1 rep: no scatter, so nothing about the change can be called real
        out["verdict"] = "not enough reps to judge (needs ≥ 2 per session)"
    elif out["beyond_rep_scatter"] is False:
        out["verdict"] = "within rep-to-rep scatter"
    elif "mdc95" not in out:
        out["verdict"] = "consistent across reps; size not validated"
    elif out["beyond_rep_scatter"] is True and out["beyond_measurement_error"]:
        out["verdict"] = "real change (beyond rep scatter and measurement error)"
    else:
        out["verdict"] = "within measurement error"
    return out


def _when(session):
    """started_at as an aware datetime (naive ones are read as UTC) so offsets order correctly."""
    try:
        dt = datetime.fromisoformat(session["started_at"])
    except ValueError as e:
        raise ValueError(f"{session['dir']}: started_at {session['started_at']!r} is not an ISO timestamp") from e
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def compare(session_dirs, signals=None):
    """Chronological comparison of sessions (first → each later one, and consecutive steps)."""
    sessions = sorted((load(d) for d in session_dirs), key=_when)
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
    unrecorded = [s["session_id"] for s in sessions if s["started_at_source"] not in RECORDED]
    if unrecorded:
        warnings.append(f"started_at of {', '.join(unrecorded)} is processing time, not recording time: the session "
                        "order may be wrong (pass --started-at to 'rehabtwin process')")
    first, last = sessions[0], sessions[-1]
    series = {sig: [{"session_id": s["session_id"], "started_at": s["started_at"], "mean": s["summary"][sig]["rep_peak_mean"],
                     "sd": s["summary"][sig]["rep_peak_sd"], "n_reps": s["n_reps"]} for s in sessions] for sig in signals}
    return {"sessions": [{k: s[k] for k in ("session_id", "started_at", "started_at_source", "tier", "front_end",
                                            "exercise", "n_reps", "dir")}
                         for s in sessions],
            "warnings": warnings,
            "first_to_last": {sig: judge(first, last, sig) for sig in signals},
            "steps": [{"from": a["session_id"], "to": b["session_id"], "changes": {sig: judge(a, b, sig) for sig in signals}}
                      for a, b in zip(sessions, sessions[1:])],
            "series": series,
            "method": METHOD}
