#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors
# SPDX-License-Identifier: CERN-OHL-S-2.0
"""POST HOC analysis of the force-plate check (VALIDATION_PLAN.md, stage A), defined on 2026-11-06 by the owner after
the force data had been seen. It is reported beside the pre-registered result
(foot_models/results_forceplate_2026-11-06.json), which stays as computed; nothing here replaces it.

1. Plate coverage. A trial is left out if the right or the left plate carries less than 1 % of body weight on
   average over that trial's quasi-static frames. The rule uses only the measured plate loads (the body weight is
   the model's mass times g, as in the pre-registered metrics), never the model's predictions. The three metrics
   and their pass/fail are then recomputed with forceplate_metrics.py's own per-frame functions, under the same
   thresholds and rule. A subject left with no frames is not evaluated (amendment 2), and a metric then passes
   only among the subjects evaluated, which is reported as such.
2. Body mass, per subject: the model's total mass; the mass recorded in the dataset (sessionMetadata.yaml, and the
   scale setup); and the plates' mean combined load over the static1 frames that the coverage rule keeps, divided
   by g. The plates' mean over the squat frames is given too, for subjects whose static1 is left out.

  python foot_models/forceplate_posthoc.py --record foot_models/forceplate_frames_2026-11-06.json --solve SOLVE \\
      --forces FORCES --kinematics KIN --models MODELS -o results_posthoc.json
"""
import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import forceplate_metrics as FM  # noqa: E402

COVERAGE_MIN_PCT_BW = 1.0
POST_HOC = "post hoc: defined on 2026-11-06 after the force data was seen; the pre-registered result stays as computed"


def coverage(right_N, left_N, body_weight_N, min_pct=COVERAGE_MIN_PCT_BW):
    """The plate-coverage rule for one trial: (kept, right % BW, left % BW), from the measured loads only."""
    r, l = 100.0 * float(np.mean(right_N)) / body_weight_N, 100.0 * float(np.mean(left_N)) / body_weight_N
    return (r >= min_pct and l >= min_pct), r, l


def recorded_mass(kin_subject):
    """The mass recorded in the dataset: sessionMetadata.yaml's mass_kg and the scale setup's <mass> (kg)."""
    meta = re.search(r"^mass_kg:\s*([0-9.]+)\s*$", (kin_subject / "sessionMetadata.yaml").read_text(), re.M)
    setup = next((kin_subject / "OpenSimData/Mocap/Model").glob("*_setup_scale.xml"))
    scale = re.search(r"<mass>\s*([0-9.eE+-]+)\s*</mass>", setup.read_text())
    return dict(session_metadata_kg=float(meta.group(1)) if meta else None, scale_setup_kg=float(scale.group(1)) if scale else None)


def model_mass_and_g(model_path):
    import opensim as osim
    m = osim.Model(str(model_path)); st = m.initSystem()
    g = m.getGravity()
    return m.getTotalMass(st), float(np.sqrt(sum(g.get(i) ** 2 for i in range(3))))


def evaluate(record, solve_root, forces_root, kin_root, models_root):
    rec = json.loads(Path(record).read_text())
    trials, subjects, masses = {}, {}, {}
    for s, v in rec["subjects"].items():
        pred = Path(solve_root) / s / "double_support.json"
        if FM.sha256(pred) != v["double_support_sha256"]:
            raise SystemExit(f"{s}: predictions differ from the committed sha256; stopping")
        sol = json.loads(pred.read_text())
        W, L = sol["body_weight_N"], v["foot_length_mm"]["mean"]
        errs = {"static1": [], "squats": []}
        loads = {"static1": [], "squats": []}
        trials[s] = {}
        for trial, t in sol["trials"].items():
            if not t["frames"]:
                continue
            tf, cols = FM.load_forces(Path(forces_root) / s / "ForceData" / trial.replace(".mot", "_forces.mot"))
            meas = [FM.measured_at(tf, cols, r["time"]) for r in t["frames"]]
            kept, rp, lp = coverage([m["R"]["vy"] for m in meas], [m["L"]["vy"] for m in meas], W)
            trials[s][trial[:-4]] = dict(frames=len(meas), right_plate_pct_bw=round(rp, 2), left_plate_pct_bw=round(lp, 2), kept=kept)
            if not kept:
                continue
            part = "static1" if trial in FM.STATIC else "squats"
            for r, m in zip(t["frames"], meas):
                errs[part].append(FM.frame_errors(dict(r, body_weight_N=W), m, L))
                loads[part].append(m["R"]["vy"] + m["L"]["vy"])
        pooled = errs["static1"] + errs["squats"]
        summ = lambda es: None if not es else dict(frames=len(es), **{k: round(FM.rms([e[k] for e in es]), 4) for k in FM.THRESHOLDS})
        subjects[s] = (dict(evaluated=False, note="no frames left after the coverage rule: not evaluated (amendment 2)") if not pooled else
                       dict(evaluated=True, pooled=summ(pooled), static1=summ(errs["static1"]), squats=summ(errs["squats"])))
        model_kg, g = model_mass_and_g(Path(models_root) / s / "LaiArnoldModified2017_poly_withArms_weldHand_scaled_contacts.osim")
        rm = recorded_mass(Path(kin_root) / s)
        plate = lambda xs: round(float(np.mean(xs)) / g, 2) if xs else None
        ref = rm["session_metadata_kg"]
        masses[s] = dict(model_kg=round(model_kg, 3), recorded_kg=rm, g_m_s2=g,
                         plates_static1_kg=plate(loads["static1"]), plates_squats_kg=plate(loads["squats"]),
                         plates_static1_minus_recorded_pct=(round(100 * (plate(loads["static1"]) - ref) / ref, 2) if loads["static1"] else None),
                         plates_squats_minus_recorded_pct=(round(100 * (plate(loads["squats"]) - ref) / ref, 2) if loads["squats"] else None))
    metrics = {}
    for k, thr in FM.THRESHOLDS.items():
        vals = {s: v["pooled"][k] for s, v in subjects.items() if v["evaluated"]}
        metrics[k] = dict(threshold=thr, per_subject_pooled={s: round(x, 2) for s, x in vals.items()},
                          median=round(float(np.median(list(vals.values()))), 2), range=[round(min(vals.values()), 2), round(max(vals.values()), 2)],
                          outside_threshold=[s for s, x in vals.items() if x > thr],
                          not_evaluated=[s for s, v in subjects.items() if not v["evaluated"]],
                          every_evaluated_subject_within=all(x <= thr for x in vals.values()),
                          descriptive_static1={s: (v["static1"][k] if v["static1"] else None) for s, v in subjects.items() if v["evaluated"]},
                          descriptive_squats={s: (v["squats"][k] if v["squats"] else None) for s, v in subjects.items() if v["evaluated"]})
    removed = [f"{s} {t}" for s, ts in trials.items() for t, x in ts.items() if not x["kept"]]
    return dict(post_hoc=POST_HOC, coverage_rule=f"leave out a trial if either plate carries < {COVERAGE_MIN_PCT_BW} % of body weight on average over its quasi-static frames",
                removed_trials=removed, trials=trials, metrics=metrics, subjects=subjects, body_mass=masses)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for k in ("record", "solve", "forces", "kinematics", "models"):
        ap.add_argument(f"--{k}", required=True)
    ap.add_argument("-o", required=True)
    a = ap.parse_args()
    res = evaluate(a.record, a.solve, a.forces, a.kinematics, a.models)
    Path(a.o).write_text(json.dumps(res, indent=1) + "\n")
    print("removed:", res["removed_trials"])
    for k, m in res["metrics"].items():
        print(f"{k}: median {m['median']}, range {m['range']}, outside {m['outside_threshold']}, not evaluated {m['not_evaluated']}, "
              f"every evaluated within: {m['every_evaluated_subject_within']}")


if __name__ == "__main__":
    main()
