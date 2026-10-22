"""Compare estimated joint angles against a reference (docs/validation-protocol.md step 5).

Outputs RMSE per joint and per plane, gate decisions against the project
targets in docs/accuracy.md, and the list of joint/planes that may be used
by feedback rules. Gates degrade claims, never standards: a failed
joint/plane is excluded from feedback, it does not get a looser threshold.
"""
from __future__ import annotations

from datetime import date

import numpy as np

from .kinematics import classify_signal as classify
from .io_formats import Table, to_degrees

# docs/accuracy.md "Project acceptance targets" (engineering targets, clinician to confirm)
TARGETS_DEG = {"sagittal": 3.0, "frontal": 5.0, "transverse": 5.0}


def _resample(ref: Table, times):
    out = np.full((len(times), len(ref.columns)), np.nan)
    inside = (times >= ref.time[0] - 1e-9) & (times <= ref.time[-1] + 1e-9)
    for j in range(len(ref.columns)):
        out[inside, j] = np.interp(times[inside], ref.time, ref.data[:, j])
    return out


def best_lag(est: Table, ref: Table, coords, max_lag_s, step_s=None):
    """Time shift (s) to add to the reference that best aligns ``coords`` (unsynchronised systems)."""
    if max_lag_s <= 0:
        return 0.0
    dt = step_s or float(np.median(np.diff(est.time)))
    best, best_lag_s = np.inf, 0.0
    for lag in np.arange(-max_lag_s, max_lag_s + dt / 2, dt):
        shifted = Table(ref.columns, ref.data, ref.time + lag)
        r = _resample(shifted, est.time)
        errs = []
        for c in coords:
            d = est.col(c) - r[:, ref.columns.index(c)]
            d = d[np.isfinite(d)]
            if len(d) > 10:
                errs.append(np.mean(d ** 2))
        if errs and np.mean(errs) < best:
            best, best_lag_s = np.mean(errs), float(lag)
    return best_lag_s


# Estimate signal -> reference coordinate when models differ. Pose2Sim spreads the
# lumbar spine over five levels; Rajagopal/Lai-Arnold models (e.g. the OpenCap
# LabValidation mocap IK) have one lumbar joint whose angle is the total.
DEFAULT_ALIASES = {
    "lumbar_total.sagittal": "lumbar_extension",
    "lumbar_total.frontal": "lumbar_bending",
    "lumbar_total.transverse": "lumbar_rotation",
}


def _apply_aliases(est: Table, ref: Table, aliases):
    """Copy reference columns under the estimate's names where only an alias exists."""
    extra = [(e, r) for e, r in aliases.items() if e in est.columns and e not in ref.columns and r in ref.columns]
    if not extra:
        return ref, []
    data = np.column_stack([ref.data] + [ref.col(r) for _, r in extra])
    return Table(ref.columns + [e for e, _ in extra], data, ref.time, ref.in_degrees, ref.header), extra


def compare(est: Table, ref: Table, max_lag_s=0.0, coords=None, aliases=None):
    """Per-coordinate error statistics of ``est`` against ``ref`` in degrees.

    Radian tables (``inDegrees=no``, e.g. a lab's SI-unit IK) are converted first: compared raw, an
    identical motion scored 72 deg RMSE. Only angular planes are compared, so the by-name split
    of ``to_degrees`` without a model is enough here.
    """
    est, ref = to_degrees(est), to_degrees(ref)
    ref, aliased = _apply_aliases(est, ref, DEFAULT_ALIASES if aliases is None else aliases)
    shared = [c for c in est.columns if c in ref.columns]
    angular = [c for c in shared if classify(c)[1] in ("sagittal", "frontal", "transverse")]
    if coords:
        angular = [c for c in angular if c in coords]
    if not angular:
        raise ValueError("no angular coordinates shared by estimate and reference")
    lag = best_lag(est, ref, [c for c in angular if classify(c)[1] == "sagittal"] or angular, max_lag_s)
    r = _resample(Table(ref.columns, ref.data, ref.time + lag), est.time)
    per = {}
    for c in angular:
        d = est.col(c) - r[:, ref.columns.index(c)]
        d = d[np.isfinite(d)]
        if len(d) < 2:
            continue
        joint, plane = classify(c)
        per[c] = {
            "joint": joint, "plane": plane, "n": int(len(d)),
            "rmse_deg": float(np.sqrt(np.mean(d ** 2))),
            "bias_deg": float(np.mean(d)),
            "rmse_offset_removed_deg": float(np.std(d)),
            "max_abs_deg": float(np.max(np.abs(d))),
            "reference_rom_deg": float(np.nanmax(r[:, ref.columns.index(c)]) - np.nanmin(r[:, ref.columns.index(c)])),
        }
    for e, r in aliased:
        if e in per:
            per[e]["reference_column"] = r
    return {"lag_s": lag, "coordinates": per}


def by_joint_plane(per_coord):
    """Collapse coordinates to joint x plane (max over coordinates of a joint/plane)."""
    out = {}
    for c, s in per_coord.items():
        cell = out.setdefault(s["joint"], {})
        cell[s["plane"]] = max(cell.get(s["plane"], 0.0), round(s["rmse_deg"], 3))
    return out


def gate(kin_rmse, targets=TARGETS_DEG, min_rom_deg=5.0, per_coord=None):
    """Gate each joint/plane against its target; joints with too little motion are 'not-tested'."""
    gates, allowed = {}, []
    rom = {}
    for s in (per_coord or {}).values():
        key = (s["joint"], s["plane"])
        rom[key] = max(rom.get(key, 0.0), s["reference_rom_deg"])
    for joint, planes in sorted(kin_rmse.items()):
        for plane, val in planes.items():
            key = f"{joint}.{plane}_rmse_le_{targets[plane]:g}deg"
            if rom.get((joint, plane), np.inf) < min_rom_deg:
                gates[key] = "not-tested"
                continue
            ok = val <= targets[plane]
            gates[key] = "pass" if ok else "fail"
            if ok:
                allowed.append(f"{joint}.{plane}")
    return gates, allowed


REFERENCE_GRADES = ("marker-mocap", "markerless", "synthetic")


def report(cmp, person_ref, reference_system, movements, synthetic=False, extra=None, reference_grade="marker-mocap"):
    """A validation-report (schemas/validation-report.schema.json).

    ``reference_grade``: what the reference is. Only marker-based motion capture can approve a use;
    agreement with another markerless system ("markerless") bounds the error but licenses nothing.
    """
    if reference_grade not in REFERENCE_GRADES:
        raise ValueError(f"reference_grade must be one of {REFERENCE_GRADES}")
    grade = "synthetic" if synthetic else reference_grade
    kin = by_joint_plane(cmp["coordinates"])
    gates, allowed = gate(kin, per_coord=cmp["coordinates"])
    if grade == "markerless":
        allowed = []
    if grade != "marker-mocap" or not allowed:
        # A synthetic round trip licenses nothing clinically, and a validation
        # where no joint/plane met its target licenses nothing beyond what the
        # tier already allows (Tier C: adherence and rep counting, no angles).
        approved = []
    elif all(v != "fail" for v in gates.values()):
        approved = ["screening", "posture-feedback"]
    else:
        approved = ["screening"]
    rep = {
        "person_ref": person_ref,
        "date": date.today().isoformat(),
        "reference_system": reference_system,
        "movements": list(movements),
        "kinematics_rmse_deg": kin,
        "gates": gates,
        "approved_for": approved,
        "feedback_allowed_joint_planes": allowed,
        "synthetic": bool(synthetic),
        "reference_grade": grade,
        "time_lag_applied_s": cmp["lag_s"],
        "per_coordinate": {c: {k: (round(v, 3) if isinstance(v, float) else v) for k, v in s.items()}
                           for c, s in cmp["coordinates"].items()},
        "targets_deg": TARGETS_DEG,
        "notes": {"synthetic": "Synthetic round trip: tests the software, not the measurement. No clinical use.",
                  "markerless": "Agreement with another markerless system, which has its own error against marker "
                                "mocap: the RMSE here is not this pipeline's accuracy and approves nothing.",
                  "marker-mocap": "Targets are project engineering targets (docs/accuracy.md); clinician sign-off "
                                  "pending."}[grade],
    }
    if extra:
        rep.update(extra)
    return rep
