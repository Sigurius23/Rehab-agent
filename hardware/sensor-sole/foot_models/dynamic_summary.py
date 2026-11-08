#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors
# SPDX-License-Identifier: CERN-OHL-S-2.0
"""Phase-1 record of the dynamic comparison (VALIDATION_PLAN.md, amendments 4 and 5): every finished solve's sha256,
validity, tracking error and maximum contact penetration, collected from the case folders of
foot_models/dynamic_track.py. No force data.

  python foot_models/dynamic_summary.py OUT_DIR -o foot_models/dynamic_solutions_<date>.json [--models-dir MODELS]
  python foot_models/dynamic_summary.py OUT_DIR --gate subject2_squats1     # the pilot gate; exit status 0 = pass

Validity (amendment 5, 2026-11-08), applied here to every solve:
  - converged, and the pelvis residuals within Hicks et al. (2015), as dynamic_track.check decided them when the
    solve finished (that is amendment 4's validity, kept as `valid_amendment4`);
  - and tracking within PILOT_GATE, by the same check (tracks) as the pilot gate: every tracked rotational
    coordinate (joint angles, the pelvis rotations included) within 5 deg RMS, every pelvis translation within
    20 mm RMS, over the window.
Maximum contact penetration (amendment 5, item 2) is reported for every solve; it is not part of validity.

The counts are over the current settings version (SETTINGS_VERSION in dynamic_track.py); solves with earlier
settings are listed apart, as superseded.

The pilot gate (run_dynamic.sh, before the batch) passes when, with the current settings, both arms of the pilot
converged and each tracks within PILOT_GATE. It is a check of the settings (amendment 4), unchanged by amendment 5.
"""
import argparse
import hashlib
import json
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
KEEP = ("converged", "status", "iterations", "solve_seconds", "solution_sha256", "window_s",
        "peak_external_force_N", "com_height_m", "pelvis_residual_force_max_N", "residual_force_limit_N",
        "pelvis_residual_moment_max_Nm", "residual_moment_limit_Nm", "tracking_rms")
# Settings log, version 2 (2026-11-08): a pilot solution must track the reference, not merely converge.
# Amendment 5 (2026-11-08): the same limits are part of every solution's validity.
PILOT_GATE = dict(max_rotation_rms_deg=5.0, max_translation_rms_mm=20.0)
ARM_B_MODEL = "LaiArnoldModified2017_poly_withArms_weldHand_scaled_contacts.osim"


def settings_version(track_py=HERE / "dynamic_track.py"):
    """SETTINGS_VERSION of dynamic_track.py, read from its source (no OpenSim import)."""
    m = re.search(r"^SETTINGS_VERSION\s*=\s*(\d+)", Path(track_py).read_text(), re.M)
    if not m:
        raise ValueError(f"{track_py}: no SETTINGS_VERSION")
    return int(m.group(1))


def tracks(row, gate=PILOT_GATE):
    """Whether a solution's tracking error is within the pilot gate's limits, and the reasons when it is not."""
    t = row.get("tracking_rms") or {}
    why = []
    if t.get("max_rotation_deg") is None or t["max_rotation_deg"] > gate["max_rotation_rms_deg"]:
        why.append(f"rotation RMS {t.get('max_rotation_deg')} deg ({t.get('worst')}) > {gate['max_rotation_rms_deg']}")
    if t.get("max_translation_mm") is None or t["max_translation_mm"] > gate["max_translation_rms_mm"]:
        why.append(f"pelvis translation RMS {t.get('max_translation_mm')} mm > {gate['max_translation_rms_mm']}")
    return not why, why


def validity(row, gate=PILOT_GATE):
    """Amendment 5: (valid, reasons). Converged, pelvis residuals within Hicks et al. (2015), and tracks()."""
    why = []
    if not row.get("converged"):
        why.append(f"not converged ({row.get('status')}, {row.get('iterations')} iterations)")
    elif not row.get("valid_amendment4"):
        why.append(f"pelvis residuals over Hicks et al. (2015): force {row.get('pelvis_residual_force_max_N')}/"
                   f"{row.get('residual_force_limit_N')} N, moment {row.get('pelvis_residual_moment_max_Nm')}/"
                   f"{row.get('residual_moment_limit_Nm')} Nm")
    why += tracks(row, gate)[1]
    return not why, why


def collect(out_dir):
    rows = []
    for rec_path in sorted(Path(out_dir).glob("cases/*/*/case.json")):
        rec = json.loads(rec_path.read_text())
        res_path = rec_path.parent / "result.json"
        if not res_path.exists():
            continue
        res = json.loads(res_path.read_text())
        k = rec["key"]
        row = dict(subject=k["subject"], trial=k["trial"], arm=k["arm"], settings_version=k["settings"]["version"],
                   max_iterations=k.get("max_iterations"), model_sha256=k["model_sha256"], ik_sha256=k["ik_sha256"],
                   code_sha256=k["code_sha256"], fingerprint=rec["fingerprint"], finished=rec["finished"],
                   case=rec_path.parent.relative_to(out_dir).as_posix(), settings=k["settings"],
                   valid_amendment4=bool(res.get("valid")), **{f: res.get(f) for f in KEEP})
        row["valid"], row["invalid_because"] = validity(row)
        rows.append(row)
    rows.sort(key=lambda r: (int(r["subject"][7:]), r["trial"], r["arm"], r["settings_version"]))
    return rows


# ------------------------------------------------------------------------------------------------ penetration
def max_penetration(model, states):
    """Amendment 5, item 2: the deepest any contact sphere reaches below the floor over the states, in mm (negative:
    never in contact), and the time it happens. The floor must be the models' one half-space on ground at the origin,
    normal +y (OpenCap's placement); anything else is refused."""
    import opensim as osim
    cg = model.getContactGeometrySet()
    geoms = [cg.get(i) for i in range(cg.getSize())]
    floors = [osim.ContactHalfSpace.safeDownCast(g) for g in geoms if g.getConcreteClassName() == "ContactHalfSpace"]
    spheres = [osim.ContactSphere.safeDownCast(g) for g in geoms if g.getConcreteClassName() == "ContactSphere"]
    if len(floors) != 1 or not spheres:
        raise ValueError(f"expected one floor half-space and contact spheres, found {len(floors)} and {len(spheres)}")
    f = floors[0]
    loc, ori = f.get_location(), f.get_orientation()
    if (f.getFrame().getAbsolutePathString() != "/ground" or max(abs(loc.get(i)) for i in range(3)) > 1e-9
            or max(abs(ori.get(i) - v) for i, v in enumerate((0.0, 0.0, -1.5707963267948966))) > 1e-6):
        raise ValueError("the floor is not the half-space on ground at the origin with normal +y")
    best, at = -float("inf"), None
    for st in states:
        model.realizePosition(st)
        for s in spheres:
            d = s.getRadius() - s.getFrame().findStationLocationInGround(st, s.get_location()).get(1)
            if d > best:
                best, at = d, st.getTime()
    return round(1000.0 * best, 2), round(at, 4)


def model_path(out_dir, models_dir, row):
    s = row["subject"]
    return Path(out_dir) / "models" / s / "armA_sole.osim" if row["arm"] == "A" else Path(models_dir) / s / ARM_B_MODEL


def add_penetration(rows, out_dir, models_dir):
    """Each row's maximum contact penetration, from its solution and its model (checked against the solve's sha256)."""
    import opensim as osim
    import dynamic_metrics as DM
    osim.Logger.setLevelString("error")
    for r in rows:
        r["max_penetration_mm"] = r["max_penetration_time_s"] = None
        m = model_path(out_dir, models_dir, r)
        sol = Path(out_dir) / r["case"] / "solution.sto"
        if not m.exists() or hashlib.sha256(m.read_bytes()).hexdigest() != r["model_sha256"] or not sol.exists():
            r["penetration_note"] = "model or solution missing, or the model changed since the solve"
            print(f"warning: {r['subject']} {r['trial']} arm {r['arm']}: {r['penetration_note']}", file=sys.stderr)
            continue
        model = DM.processed_model(m, r["settings"])
        traj = osim.MocoTrajectory(str(sol)).exportToStatesTrajectory(model)
        r["max_penetration_mm"], r["max_penetration_time_s"] = max_penetration(model, [traj.get(i) for i in range(traj.getSize())])
    return rows


# ------------------------------------------------------------------------------------------------ gate and summary
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
        lines.append(f"arm {arm}: " + ("pass" if r["converged"] and good else "fail: " + "; ".join(why))
                     + f" (valid under amendment 5: {'yes' if r['valid'] else 'no'})")
    return ok, lines


def summarize(rows, version):
    current = [r for r in rows if r["settings_version"] == version]
    keys = [(r["subject"], r["trial"], r["arm"]) for r in current]
    if len(keys) != len(set(keys)):
        raise ValueError("more than one solve of a trial and arm with the current settings")
    by = lambda f: sum(1 for r in current if r[f])
    valid = {arm: [r for r in current if r["arm"] == arm and r["valid"]] for arm in "AB"}
    both = sorted({(r["subject"], r["trial"]) for r in valid["A"]} & {(r["subject"], r["trial"]) for r in valid["B"]})
    return dict(what="Dynamic comparison, phase 1 (no force data): the solves of both arms, each with its solution's sha256, validity "
                     "(amendment 5: convergence, Hicks et al. 2015 pelvis residuals and tracking), tracking error and maximum contact "
                     "penetration. VALIDATION_PLAN.md, amendments 4 and 5. Evaluated trials (validity and plate coverage) come in phase 2.",
                written=time.strftime("%Y-%m-%dT%H:%M:%S%z"), settings_version=version, pilot_gate=PILOT_GATE,
                validity_limits=dict(PILOT_GATE, residuals="Hicks et al. 2015: force <= 5 % of peak external force, "
                                     "moment <= 1 % of COM height times that force"),
                solves=len(current), converged=by("converged"), valid=by("valid"), valid_amendment4=by("valid_amendment4"),
                within_pilot_gate=sum(1 for r in current if tracks(r)[0]),
                per_arm={arm: dict(solves=sum(1 for r in current if r["arm"] == arm),
                                   converged=sum(1 for r in current if r["arm"] == arm and r["converged"]),
                                   valid_trials=len(valid[arm]),
                                   valid_subjects=len({r["subject"] for r in valid[arm]})) for arm in "AB"},
                valid_in_both_arms=dict(trials=len(both), subjects=len({s for s, _ in both})),
                solutions=current,
                superseded=[r for r in rows if r["settings_version"] != version])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out_dir"); ap.add_argument("-o"); ap.add_argument("--gate", metavar="GROUP")
    ap.add_argument("--models-dir", help="the subjects' arm-B models (default: OUT_DIR/../models)")
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
    sys.path.insert(0, str(HERE))
    add_penetration(rows, a.out_dir, a.models_dir or Path(a.out_dir).resolve().parent / "models")
    summary = summarize(rows, version)
    Path(a.o).write_text(json.dumps(summary, indent=1) + "\n")
    print(json.dumps({k: summary[k] for k in ("settings_version", "solves", "converged", "valid", "valid_amendment4",
                                              "within_pilot_gate", "per_arm", "valid_in_both_arms")}))


if __name__ == "__main__":
    main()
