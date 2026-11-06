#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors
# SPDX-License-Identifier: CERN-OHL-S-2.0
"""POST HOC diagnostic of the left/right share failure in the force-plate check (VALIDATION_PLAN.md, stage A),
defined by the owner on 2026-11-06 after the force data had been seen. It is reported beside the pre-registered result
and the earlier post-hoc analysis, which stay as computed.

In quasi-static double support, the combined centre of pressure lies under the centre of mass. The right foot's
share then follows the lever rule along the sideways axis: share = (combined COP - left COP) / (right COP - left COP).
So a share error has two parts:
  - the offset between the measured combined centre of pressure (under the true centre of mass) and the model's
    centre of mass, sideways: an error of the body model or its inverse kinematics. Its lever-rule share error is
    100 * offset / (the measured sideways distance between the feet's centres of pressure);
  - the rest: where each foot's own centre of pressure sits sideways in the model compared with the plates, which is
    where the foot contact's load split enters.

Frames: those of the trials the post-hoc plate-coverage rule keeps (forceplate_posthoc.coverage). Axes: the model's
forward axis per frame, and the sideways axis perpendicular to it in the floor plane, pointing to the right foot.

  python foot_models/forceplate_lateral.py --record foot_models/forceplate_frames_2026-11-06.json --solve SOLVE \\
      --forces FORCES -o results_lateral.json
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import forceplate_metrics as FM  # noqa: E402
import forceplate_posthoc as PH  # noqa: E402

POST_HOC = "post hoc: defined on 2026-11-06 after the force data was seen; the earlier results stay as computed"


def sideways(model, meas):
    """One frame, along the sideways axis (m; positive towards the right foot): the measured combined centre of
    pressure, the model's centre of mass, each foot's measured and modelled centre of pressure, and the shares (%)."""
    f = np.array(model["forward_axis"], float); f /= np.linalg.norm(f)
    lat = np.array([-f[1], f[0]])                                   # (x, z): perpendicular to forward, in the floor
    rN, lN = meas["R"]["vy"], meas["L"]["vy"]
    mr, ml = np.array(meas["R"]["cop"]), np.array(meas["L"]["cop"])
    cop = (rN * mr + lN * ml) / (rN + lN)
    com = np.array([model["com_ground_m"][0], model["com_ground_m"][2]])
    pr, pl = np.array(model["R"]["cop_ground_m"]), np.array(model["L"]["cop_ground_m"])
    out = dict(cop=float(cop @ lat), com=float(com @ lat), meas_R=float(mr @ lat), meas_L=float(ml @ lat),
               model_R=float(pr @ lat), model_L=float(pl @ lat),
               share_meas=100.0 * rN / (rN + lN), share_model=float(model["right_share_pct"]))
    if out["meas_R"] <= out["meas_L"]:
        raise ValueError("the right foot's measured centre of pressure is not to the right of the left's")
    out["separation"] = out["meas_R"] - out["meas_L"]
    out["offset"] = out["cop"] - out["com"]
    out["share_error"] = out["share_meas"] - out["share_model"]
    out["share_error_from_offset"] = 100.0 * out["offset"] / out["separation"]
    return out


def evaluate(record, solve_root, forces_root):
    rec = json.loads(Path(record).read_text())
    subjects = {}
    for s, v in rec["subjects"].items():
        pred = Path(solve_root) / s / "double_support.json"
        if FM.sha256(pred) != v["double_support_sha256"]:
            raise SystemExit(f"{s}: predictions differ from the committed sha256; stopping")
        sol = json.loads(pred.read_text())
        rows = []
        for trial, t in sol["trials"].items():
            if not t["frames"]:
                continue
            tf, cols = FM.load_forces(Path(forces_root) / s / "ForceData" / trial.replace(".mot", "_forces.mot"))
            meas = [FM.measured_at(tf, cols, r["time"]) for r in t["frames"]]
            if not PH.coverage([m["R"]["vy"] for m in meas], [m["L"]["vy"] for m in meas], sol["body_weight_N"])[0]:
                continue
            rows += [sideways(r, m) for r, m in zip(t["frames"], meas)]
        if not rows:
            subjects[s] = dict(evaluated=False, note="no kept trials (post-hoc plate-coverage rule)")
            continue
        a = lambda k: np.array([r[k] for r in rows])
        rms = lambda x: float(np.sqrt(np.mean(np.square(x))))
        err, pred_err = a("share_error"), a("share_error_from_offset")
        resid = err - pred_err
        subjects[s] = dict(
            evaluated=True, frames=len(rows),
            sideways_offset_mm=dict(rms=round(1000 * rms(a("offset")), 2), mean=round(1000 * float(a("offset").mean()), 2)),
            foot_separation_mm=round(1000 * float(a("separation").mean()), 1),
            share_error_points=dict(rms=round(rms(err), 2), mean=round(float(err.mean()), 2)),
            share_error_from_offset_points=dict(rms=round(rms(pred_err), 2), mean=round(float(pred_err.mean()), 2)),
            remainder_points=dict(rms=round(rms(resid), 2), mean=round(float(resid.mean()), 2)),
            foot_cop_sideways_model_minus_measured_mm=dict(
                right=round(1000 * float((a("model_R") - a("meas_R")).mean()), 2),
                left=round(1000 * float((a("model_L") - a("meas_L")).mean()), 2),
                separation=round(1000 * float(((a("model_R") - a("model_L")) - a("separation")).mean()), 2)))
    return dict(post_hoc=POST_HOC, subjects=subjects)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for k in ("record", "solve", "forces"):
        ap.add_argument(f"--{k}", required=True)
    ap.add_argument("-o", required=True)
    a = ap.parse_args()
    res = evaluate(a.record, a.solve, a.forces)
    Path(a.o).write_text(json.dumps(res, indent=1) + "\n")
    print("subject   frames  offset mm (rms, mean)  sep mm | share err (rms, mean) | from offset (rms, mean) | remainder (rms, mean) | foot COP model-meas R, L mm")
    for s, v in res["subjects"].items():
        if not v["evaluated"]:
            print(f"{s:9s} not evaluated"); continue
        o, e, p, q, fc = v["sideways_offset_mm"], v["share_error_points"], v["share_error_from_offset_points"], v["remainder_points"], v["foot_cop_sideways_model_minus_measured_mm"]
        print(f"{s:9s} {v['frames']:6d}  {o['rms']:6.2f} {o['mean']:+7.2f}   {v['foot_separation_mm']:6.1f} | {e['rms']:5.2f} {e['mean']:+6.2f} | "
              f"{p['rms']:5.2f} {p['mean']:+6.2f} | {q['rms']:5.2f} {q['mean']:+6.2f} | {fc['right']:+6.1f} {fc['left']:+6.1f}")


if __name__ == "__main__":
    main()
