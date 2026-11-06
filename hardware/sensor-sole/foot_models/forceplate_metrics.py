#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors
# SPDX-License-Identifier: CERN-OHL-S-2.0
"""Phase 2 of VALIDATION_PLAN.md stage A: the three quasi-static metrics against the force plates, as the plan and
its amendments 1-3 define them. Nothing here is fitted or tuned; the model's predictions are read as committed.

Before anything is computed, each subject's predictions (double_support.json) must match the sha256 recorded in the
phase-1 record (foot_models/forceplate_frames_2026-11-06.json); a mismatch stops the run.

Per quasi-static frame (the frames of the phase-1 record; every one was solved):
  - measured: the right and left plates' channels (R_ground_*, L_ground_*, the ones the dataset's inverse-dynamics
    setup applies to the feet), as distributed, at the frame's time. The 100 Hz frame times fall on 2000 Hz force
    samples; linear interpolation is used and the largest time gap is reported. The third plate's channels (3_*) are
    not part of the metrics; their load is reported.
  - vertical force (amendment 3): combined vertical force of both feet, measured minus model, as % of the body
    weight. The body weight is the model's (its mass times g), and the model's combined force equals it by
    construction, so this tests only the body model's mass and the quasi-static assumption.
  - forward-backward centre of pressure (amendment 2): the combined centre of pressure of both feet, measured minus
    model, along the model's forward axis (per frame, as solved), as % of the subject's mean foot length (the mean
    of the left and right heel-to-toe marker distances in the static trial).
  - left/right share: the right foot's share of the combined vertical force, measured minus model, in percentage
    points (amendment 2: separate channels per foot taken as one plate per foot).
Per subject: the RMS of each error over all of the subject's quasi-static frames (pooled: static1 and squats), and,
descriptively only (amendment 3), over the static1 frames and over the squat frames. Subjects without frames would
be reported as not evaluated (amendment 2). Pass rule: a metric passes only if every subject's pooled value is within
its threshold; each subject's value, the median and the range are reported either way.

  python foot_models/forceplate_metrics.py --record foot_models/forceplate_frames_2026-11-06.json \\
      --solve SOLVE_ROOT --forces FORCES_ROOT -o results.json
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np

THRESHOLDS = dict(vertical_force_pct_bw=5.0, cop_forward_pct_foot_length=10.0, left_right_share_points=5.0)
SQUATS = ("squats1.mot", "squatsAsym1.mot")
STATIC = ("static1.mot",)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_forces(path):
    """A force .mot as distributed: (times, {column: values})."""
    lines = Path(path).read_text().splitlines()
    end = next(k for k, ln in enumerate(lines) if ln.strip().lower() == "endheader")
    head = [h.strip() for h in lines[end + 1].split("\t") if h.strip()]
    data = np.array([[float(v) for v in ln.split()] for ln in lines[end + 2:] if ln.strip()])
    if head[0].lower() != "time" or data.shape[1] != len(head):
        raise ValueError(f"{path}: unexpected layout")
    return data[:, 0], {h: data[:, i] for i, h in enumerate(head)}


def measured_at(t_force, cols, t):
    """Measured right/left vertical force (N) and centre of pressure (x, z; m) at time t, and the third plate's
    vertical force, by linear interpolation; with the gap to the nearest force sample (s)."""
    at = lambda c: float(np.interp(t, t_force, cols[c]))
    out = {s: dict(vy=at(f"{s}_ground_force_vy"), cop=(at(f"{s}_ground_force_px"), at(f"{s}_ground_force_pz"))) for s in "RL"}
    out["plate3_vy"] = at("3_ground_force_vy") if "3_ground_force_vy" in cols else None
    out["gap_s"] = float(np.min(np.abs(t_force - t)))
    return out


def frame_errors(model, meas, foot_length_mm):
    """The three errors of one frame (see the module docstring)."""
    mr, ml = model["R"]["vertical_N"], model["L"]["vertical_N"]
    fm = meas["R"]["vy"] + meas["L"]["vy"]
    w = model["body_weight_N"]
    vertical = 100.0 * (fm - (mr + ml)) / w
    share = 100.0 * meas["R"]["vy"] / fm - model["right_share_pct"]
    cop_m = np.array([(meas["R"]["vy"] * meas["R"]["cop"][i] + meas["L"]["vy"] * meas["L"]["cop"][i]) / fm for i in range(2)])
    cop_p = np.array([(mr * model["R"]["cop_ground_m"][i] + ml * model["L"]["cop_ground_m"][i]) / (mr + ml) for i in range(2)])
    fwd = np.array(model["forward_axis"], float); fwd /= np.linalg.norm(fwd)
    cop_fwd_mm = 1000.0 * float((cop_m - cop_p) @ fwd)
    return dict(vertical_force_pct_bw=vertical, cop_forward_pct_foot_length=100.0 * cop_fwd_mm / foot_length_mm,
                left_right_share_points=share, cop_forward_mm=cop_fwd_mm)


def rms(v):
    return float(math.sqrt(sum(x * x for x in v) / len(v))) if v else None


def evaluate(record, solve_root, forces_root):
    rec = json.loads(Path(record).read_text())
    subjects, checks = {}, {}
    for s, v in rec["subjects"].items():
        pred = Path(solve_root) / s / "double_support.json"
        if sha256(pred) != v["double_support_sha256"]:
            raise SystemExit(f"{s}: predictions differ from the committed sha256; stopping")
        sol = json.loads(pred.read_text())
        L = v["foot_length_mm"]["mean"]
        errs = {"static1": [], "squats": []}
        gaps, plate3, totals = [], [], []
        for trial, t in sol["trials"].items():
            if not t["frames"]:
                continue
            tf, cols = load_forces(Path(forces_root) / s / "ForceData" / trial.replace(".mot", "_forces.mot"))
            for r in t["frames"]:
                if not r["solved"]:
                    raise SystemExit(f"{s} {trial} t={r['time']}: an unsolved frame; the record says all were solved")
                m = measured_at(tf, cols, r["time"])
                e = frame_errors(dict(r, body_weight_N=sol["body_weight_N"]), m, L)
                errs["static1" if trial in STATIC else "squats"].append(e)
                gaps.append(m["gap_s"]); totals.append(m["R"]["vy"] + m["L"]["vy"])
                if m["plate3_vy"] is not None:
                    plate3.append(abs(m["plate3_vy"]))
        pooled = errs["static1"] + errs["squats"]
        if not pooled:
            subjects[s] = dict(evaluated=False, note="no quasi-static frames: not evaluated (amendment 2)")
            continue
        summ = lambda es: None if not es else dict(frames=len(es), **{k: round(rms([e[k] for e in es]), 4) for k in THRESHOLDS},
                                                   mean_signed={k: round(float(np.mean([e[k] for e in es])), 4) for k in (*THRESHOLDS, "cop_forward_mm")})
        subjects[s] = dict(evaluated=True, body_weight_N=sol["body_weight_N"], mean_foot_length_mm=L,
                           pooled=summ(pooled), static1=summ(errs["static1"]), squats=summ(errs["squats"]),
                           predictions_sha256=v["double_support_sha256"])
        checks[s] = dict(max_time_gap_s=max(gaps), plate3_max_abs_vertical_N=round(max(plate3), 3) if plate3 else None,
                         measured_combined_vertical_mean_N=round(float(np.mean(totals)), 2))
    metrics = {}
    for k, thr in THRESHOLDS.items():
        vals = {s: v["pooled"][k] for s, v in subjects.items() if v["evaluated"]}
        metrics[k] = dict(threshold=thr, per_subject=vals, median=round(float(np.median(list(vals.values()))), 4),
                          range=[min(vals.values()), max(vals.values())],
                          within_threshold=sorted((s for s, x in vals.items() if x <= thr), key=lambda n: int(n[7:])),
                          outside_threshold=sorted((s for s, x in vals.items() if x > thr), key=lambda n: int(n[7:])),
                          passes=all(x <= thr for x in vals.values()) and len(vals) == len(subjects),
                          descriptive={part: {s: (v[part][k] if v[part] else None) for s, v in subjects.items() if v["evaluated"]}
                                       for part in ("static1", "squats")})
    return dict(metrics=metrics, subjects=subjects, checks=checks)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--record", required=True); ap.add_argument("--solve", required=True)
    ap.add_argument("--forces", required=True); ap.add_argument("-o", required=True)
    a = ap.parse_args()
    res = evaluate(a.record, a.solve, a.forces)
    Path(a.o).write_text(json.dumps(res, indent=1) + "\n")
    for k, m in res["metrics"].items():
        print(f"{k}: median {m['median']}, range {m['range']}, threshold {m['threshold']}, "
              f"{'PASS' if m['passes'] else 'FAIL'} (outside: {m['outside_threshold']})")


if __name__ == "__main__":
    main()
