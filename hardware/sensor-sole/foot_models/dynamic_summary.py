#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors
# SPDX-License-Identifier: CERN-OHL-S-2.0
"""Phase-1 record of the dynamic comparison (VALIDATION_PLAN.md, amendment 4): every finished solve's sha256,
validity and tracking error, collected from the case folders of foot_models/dynamic_track.py. No force data.

  python foot_models/dynamic_summary.py OUT_DIR -o foot_models/dynamic_solutions_<date>.json
"""
import argparse
import json
import time
from pathlib import Path

KEEP = ("converged", "valid", "status", "iterations", "solve_seconds", "solution_sha256", "window_s",
        "peak_external_force_N", "com_height_m", "pelvis_residual_force_max_N", "residual_force_limit_N",
        "pelvis_residual_moment_max_Nm", "residual_moment_limit_Nm", "tracking_rms")


def collect(out_dir):
    rows = []
    for rec_path in sorted(Path(out_dir).glob("cases/*/*/case.json")):
        rec = json.loads(rec_path.read_text())
        res_path = rec_path.parent / "result.json"
        if not res_path.exists():
            continue
        res = json.loads(res_path.read_text())
        k = rec["key"]
        rows.append(dict(subject=k["subject"], trial=k["trial"], arm=k["arm"], settings_version=k["settings"]["version"],
                         max_iterations=k.get("max_iterations"), model_sha256=k["model_sha256"], ik_sha256=k["ik_sha256"],
                         code_sha256=k["code_sha256"], fingerprint=rec["fingerprint"], finished=rec["finished"],
                         **{f: res.get(f) for f in KEEP}))
    rows.sort(key=lambda r: (int(r["subject"][7:]), r["trial"], r["arm"], r["settings_version"]))
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out_dir"); ap.add_argument("-o", required=True)
    a = ap.parse_args()
    rows = [r for r in collect(a.out_dir) if r["max_iterations"] is None]      # smoke tests with capped iterations are not results
    by = lambda f: sum(1 for r in rows if r[f])
    summary = dict(what="Dynamic comparison, phase 1 (no force data): the solves of both arms, each with its solution's sha256, validity "
                        "(convergence and Hicks et al. 2015 pelvis residuals) and tracking error. VALIDATION_PLAN.md, amendment 4.",
                   written=time.strftime("%Y-%m-%dT%H:%M:%S%z"), solves=len(rows), converged=by("converged"), valid=by("valid"),
                   per_arm={arm: dict(solves=sum(1 for r in rows if r["arm"] == arm),
                                      converged=sum(1 for r in rows if r["arm"] == arm and r["converged"]),
                                      valid=sum(1 for r in rows if r["arm"] == arm and r["valid"])) for arm in "AB"},
                   solutions=rows)
    Path(a.o).write_text(json.dumps(summary, indent=1) + "\n")
    print(json.dumps({k: summary[k] for k in ("solves", "converged", "valid", "per_arm")}))


if __name__ == "__main__":
    main()
