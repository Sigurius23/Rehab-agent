#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors
# SPDX-License-Identifier: CERN-OHL-S-2.0
"""Phase-1 record of the dynamic comparison (VALIDATION_PLAN.md, amendment 4): every finished solve's sha256,
validity and tracking error, collected from the case folders of foot_models/dynamic_track.py. No force data.

  python foot_models/dynamic_summary.py OUT_DIR -o foot_models/dynamic_solutions_<date>.json
  python foot_models/dynamic_summary.py OUT_DIR --gate subject2_squats1     # the pilot gate; exit status 0 = pass

The counts are over the current settings version (SETTINGS_VERSION in dynamic_track.py); solves with earlier
settings are listed apart, as superseded.

The pilot gate (run_dynamic.sh, before the batch) passes when, with the current settings, both arms of the pilot
converged and each tracks within PILOT_GATE. It is a check of the settings, judged by convergence and kinematic
tracking error alone (amendment 4); it is not part of a solution's validity.
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
KEEP = ("converged", "valid", "status", "iterations", "solve_seconds", "solution_sha256", "window_s",
        "peak_external_force_N", "com_height_m", "pelvis_residual_force_max_N", "residual_force_limit_N",
        "pelvis_residual_moment_max_Nm", "residual_moment_limit_Nm", "tracking_rms")
# Settings log, version 2 (2026-11-08): a pilot solution must track the reference, not merely converge.
PILOT_GATE = dict(max_rotation_rms_deg=5.0, max_translation_rms_mm=20.0)


def settings_version(track_py=HERE / "dynamic_track.py"):
    """SETTINGS_VERSION of dynamic_track.py, read from its source (no OpenSim import)."""
    m = re.search(r"^SETTINGS_VERSION\s*=\s*(\d+)", Path(track_py).read_text(), re.M)
    if not m:
        raise ValueError(f"{track_py}: no SETTINGS_VERSION")
    return int(m.group(1))


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


def tracks(row, gate=PILOT_GATE):
    """Whether a solution's tracking error is within the pilot gate, and the reasons when it is not."""
    t = row.get("tracking_rms") or {}
    why = []
    if t.get("max_rotation_deg") is None or t["max_rotation_deg"] > gate["max_rotation_rms_deg"]:
        why.append(f"rotation RMS {t.get('max_rotation_deg')} deg ({t.get('worst')}) > {gate['max_rotation_rms_deg']}")
    if t.get("max_translation_mm") is None or t["max_translation_mm"] > gate["max_translation_rms_mm"]:
        why.append(f"pelvis translation RMS {t.get('max_translation_mm')} mm > {gate['max_translation_rms_mm']}")
    return not why, why


def gate(rows, group, version, gate=PILOT_GATE):
    """(passed, lines) for the pilot group "subjectN_trial", both arms, current settings, uncapped solves only."""
    lines, ok = [], True
    for arm in "AB":
        cand = [r for r in rows if f"{r['subject']}_{r['trial']}" == group and r["arm"] == arm
                and r["settings_version"] == version and r["max_iterations"] is None]
        if not cand:
            ok = False; lines.append(f"arm {arm}: no finished solve with settings v{version}")
            continue
        r = cand[-1]
        good, why = tracks(r, gate)
        if not r["converged"]:
            why.insert(0, f"not converged ({r['status']}, {r['iterations']} iterations)")
        ok = ok and bool(r["converged"]) and good
        lines.append(f"arm {arm}: " + ("pass" if r["converged"] and good else "fail: " + "; ".join(why)))
    return ok, lines


def summarize(rows, version):
    current = [r for r in rows if r["settings_version"] == version]
    by = lambda f: sum(1 for r in current if r[f])
    return dict(what="Dynamic comparison, phase 1 (no force data): the solves of both arms, each with its solution's sha256, validity "
                     "(convergence and Hicks et al. 2015 pelvis residuals) and tracking error. VALIDATION_PLAN.md, amendment 4.",
                written=time.strftime("%Y-%m-%dT%H:%M:%S%z"), settings_version=version, pilot_gate=PILOT_GATE,
                solves=len(current), converged=by("converged"), valid=by("valid"),
                within_pilot_gate=sum(1 for r in current if tracks(r)[0]),
                per_arm={arm: dict(solves=sum(1 for r in current if r["arm"] == arm),
                                   converged=sum(1 for r in current if r["arm"] == arm and r["converged"]),
                                   valid=sum(1 for r in current if r["arm"] == arm and r["valid"])) for arm in "AB"},
                solutions=current,
                superseded=[r for r in rows if r["settings_version"] != version])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out_dir"); ap.add_argument("-o"); ap.add_argument("--gate", metavar="GROUP")
    a = ap.parse_args()
    version = settings_version()
    rows = [r for r in collect(a.out_dir) if r["max_iterations"] is None]      # smoke tests with capped iterations are not results
    if a.gate:
        ok, lines = gate(rows, a.gate, version)
        for line in lines:
            print(f"pilot gate, settings v{version}, {line}")
        sys.exit(0 if ok else 1)
    if not a.o:
        ap.error("-o is required without --gate")
    summary = summarize(rows, version)
    Path(a.o).write_text(json.dumps(summary, indent=1) + "\n")
    print(json.dumps({k: summary[k] for k in ("settings_version", "solves", "converged", "valid", "within_pilot_gate", "per_arm")}))


if __name__ == "__main__":
    main()
