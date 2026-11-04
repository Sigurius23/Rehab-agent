#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors
# SPDX-License-Identifier: CERN-OHL-S-2.0
"""Controlled comparison of foot models on the same virtual sole. Experimental.

Every model gets the same sole design through sole_sim.add_to_osim, which records the registration and its
residuals. Then a quasi-static standing task with the ankle torque solved:
  - the body above the ankles is held in a posture (standing, or a squat frame taken from kinematics), with the
    pelvis tilted so that both feet start level, and every joint locked except the ankles and, optionally, the
    foot joints (midtarsal, MTP);
  - each ankle gets an unknown torque, standing for the net action of the ankle muscles;
  - the pelvis height, both ankle angles, both ankle torques and the free foot joints are solved together so that
    every free coordinate is at rest and each foot's centre of pressure lies under the body's centre of mass.
That is quasi-static standing balance. The foot model then decides how each foot shares its load between heel,
arch, forefoot and toes. (Letting a passive rigid body settle does not work: on soft contact it is not
rotationally stable and tips over; and a whole-body tilt as the free rotation gives a meaningless equilibrium.)

What this is not:
  - foot-to-ground contact through a virtual sole, not the foot pressing on a sole inside a shoe;
  - passive below the ankle: muscles and actuators are removed; the solved ankle torque stands in for the ankle
    muscles, but nothing muscular supports the arch or holds the toes;
  - quasi-static postures, not a squat or walking movement;
  - not validated: agreement between simulations is not physical validation; a plausible load map is not proof.

  python foot_models/compare_feet.py MODEL.osim SOLE_R.sole_sim.json SOLE_L.sole_sim.json -o out/ \
      [--posture standing] [--free-foot] [--perturb key=value ...]
"""
import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
import sole_sim as SS  # noqa: E402
import dhondt_port as DP  # noqa: E402

STATUS = SS.STATUS + "; passive below the ankle (no muscles; ankle torque solved); quasi-static posture"
FOOT_COORDS = ("mtj_angle", "mtp_angle")
KEEP_FORCES = ("SmoothSphereHalfSpaceForce", "Ligament", "ExpressionBasedCoordinateForce", "CoordinateLimitForce")


def strip_model(model_in, model_out):
    """Copy of the model without muscles or actuators: only passive structures and contact remain."""
    import opensim as osim
    m = osim.Model(str(model_in))
    m.initSystem()                                     # removing forces before this crashes OpenSim 4.6
    fs = m.updForceSet()
    removed = {}
    for i in reversed(range(fs.getSize())):
        cls = fs.get(i).getConcreteClassName()
        if cls not in KEEP_FORCES:
            removed[cls] = removed.get(cls, 0) + 1
            fs.remove(i)
    m.finalizeConnections(); m.initSystem(); m.printToXML(str(model_out))
    return removed


def posture_from_mot(mot, t, names):
    """Joint angles (deg) at time t from an OpenSim .mot (inDegrees=yes), for the coordinates named."""
    lines = Path(mot).read_text().splitlines()
    i = next(k for k, ln in enumerate(lines) if ln.strip().lower() == "endheader")
    head = lines[i + 1].split("\t")
    data = np.array([[float(v) for v in ln.split("\t")] for ln in lines[i + 2:] if ln.strip()])
    if not any("indegrees=yes" in ln.replace(" ", "").lower() for ln in lines[:i]):
        raise SystemExit(f"{mot}: expected angles in degrees")
    k = int(np.argmin(abs(data[:, 0] - t)))
    return {n: float(data[k, head.index(n)]) for n in names if n in head}


SAGITTAL = ("hip_flexion_r", "knee_angle_r", "ankle_angle_r", "hip_flexion_l", "knee_angle_l", "ankle_angle_l",
            "lumbar_extension")


def map_posture(model, posture_deg):
    """Data angles (OpenCap / Rajagopal conventions, degrees) to this model's coordinates, with every adaptation
    recorded: knee flexion is negative in gait2392-style models (range up to about +10 deg), so the sign is flipped;
    a coordinate the model lacks (e.g. lumbar_extension in a model with a multi-level lumbar spine) is left at 0
    rather than spread over levels by guesswork; an angle outside the model's own range is kept but flagged, and
    the coordinate unclamped so the model can be assembled."""
    cs = model.getCoordinateSet()
    out, notes, outside = {}, [], []
    for n, v in posture_deg.items():
        if not cs.contains(n):
            notes.append(f"{n} = {v:.1f} deg: not in this model, left at 0")
            continue
        c = cs.get(n)
        if n.startswith("knee_angle") and c.getRangeMax() < 0.5 and c.getRangeMin() < -1.0:
            v = -v
            notes.append(f"{n}: flexion is negative in this model, sign flipped")
        if not (c.getRangeMin() - 1e-9 <= math.radians(v) <= c.getRangeMax() + 1e-9):
            outside.append(f"{n} = {v:.1f} deg (model range {math.degrees(c.getRangeMin()):.0f} to "
                           f"{math.degrees(c.getRangeMax()):.0f})")
            c.set_clamped(False)
        out[n] = v
    return out, notes, outside


def _coupled(model):
    import opensim as osim
    dep = set()
    for c in model.getConstraintSet():
        cc = osim.CoordinateCouplerConstraint.safeDownCast(c)
        if cc:
            dep.add(cc.getDependentCoordinateName())
    return dep


def build(model_in, sole_r, sole_l, out_dir, posture_deg=None, free_foot=False, perturb=None, radius_mm=None):
    """Model with both soles, held in the posture with the feet level: every coordinate locked except pelvis_tx,
    pelvis_ty, the ankles and (with free_foot) the foot joints; a CoordinateActuator on each ankle for the solved
    ankle torque. Returns (model path, sole metadata per side, removed forces)."""
    import opensim as osim
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    stripped = out_dir / "stripped.osim"
    removed = strip_model(model_in, stripped)
    meta = {}
    a = out_dir / "with_R.osim"; b = out_dir / "with_soles.osim"
    meta["R"] = SS.add_to_osim(stripped, sole_r, a, radius_mm=radius_mm, perturb=perturb)
    meta["L"] = SS.add_to_osim(a, sole_l, b, radius_mm=radius_mm, perturb=perturb)
    m = osim.Model(str(b))
    cs = m.getCoordinateSet()
    free = {"pelvis_tx", "pelvis_ty", "ankle_angle_r", "ankle_angle_l"}
    if free_foot:
        free |= {f"{c}_{s}" for c in FOOT_COORDS for s in "rl" if cs.contains(f"{c}_{s}")}
    posture, notes, outside = map_posture(m, dict(posture_deg or {}))
    dependent = _coupled(m)
    for i in range(cs.getSize()):
        c = cs.get(i)
        n = c.getName()
        if n in posture:
            c.setDefaultValue(math.radians(posture[n]))
        elif n not in ("pelvis_tx", "pelvis_ty", "pelvis_tz") and n not in dependent:
            c.setDefaultValue(0.0)
    st = m.initSystem(); m.realizePosition(st)
    _, pitch = _lowest_and_pitch(m, st)
    tilt = cs.get("pelvis_tilt")
    tilt.setDefaultValue(tilt.getDefaultValue() - pitch)                  # feet level at the start
    st = m.initSystem()                                                     # assemble the coupled coordinates
    for i in range(cs.getSize()):
        c = cs.get(i)
        if c.getName() in dependent:
            c.setDefaultValue(c.getValue(st))                               # follows its coupler; never locked
        c.setDefaultLocked(c.getName() not in free and c.getName() not in dependent)
    for s in "rl":
        act = osim.CoordinateActuator(f"ankle_angle_{s}")
        act.setName(f"ankle_torque_{s}"); act.setOptimalForce(1.0)
        m.addForce(act)
    path = out_dir / "task.osim"
    m.finalizeConnections(); m.initSystem(); m.printToXML(str(path))
    meta["posture"] = dict(applied_deg=posture, notes=notes, outside_model_range=outside)
    return path, meta, removed


def _lowest_and_pitch(m, st):
    import opensim as osim
    low = []
    for g in m.getContactGeometrySet():
        if g.getName().startswith("sole_"):
            sp = osim.ContactSphere.safeDownCast(g)
            p = g.getFrame().findStationLocationInGround(st, sp.get_location())
            low.append(p.get(1) - sp.getRadius())
    pitch = []
    for s in "rl":
        R = m.getBodySet().get(f"calcn_{s}").getTransformInGround(st).R()
        x_axis = np.array([R.get(0, 0), R.get(1, 0), R.get(2, 0)])          # calcn x axis in ground
        pitch.append(math.atan2(x_axis[1], math.hypot(x_axis[0], x_axis[2])))
    return min(low), float(np.mean(pitch))


def _sole_forces(m, st, prefix="force_sole_"):
    """Sphere force records in the layout sole_sim's readout functions expect, and each foot's centre of pressure
    and vertical force in ground."""
    import opensim as osim
    labels, values = ["time"], [0.0]
    cop = {s: [np.zeros(2), 0.0] for s in "rl"}
    for fo in m.getForceSet():
        if fo.getName().startswith(prefix):
            lab = fo.getRecordLabels(); val = fo.getRecordValues(st)
            fy = 0.0
            for i in range(lab.size()):
                labels.append(lab.get(i)); values.append(val.get(i))
                if lab.get(i).endswith(".Sphere.force.Y"):
                    fy = max(val.get(i), 0.0)
            ss = osim.SmoothSphereHalfSpaceForce.safeDownCast(fo)
            sp = osim.ContactSphere.safeDownCast(ss.getConnectee("sphere"))
            pg = sp.getFrame().findStationLocationInGround(st, sp.get_location())
            s = fo.getName()[len(prefix)]
            cop[s][0] += fy * np.array([pg.get(0), pg.get(2)]); cop[s][1] += fy
    return labels, np.array([values]), {s: (v[0] / v[1] if v[1] > 0 else np.array([np.nan, np.nan]), v[1])
                                         for s, v in cop.items()}


def equilibrium(model_path, sole_r, sole_l, tol=1e-6, cop_target=None):
    """Quasi-static standing with the ankle torque solved (see the module docstring).

    Unknowns: pelvis height, both ankle angles, both ankle torques, and the free foot joints. Equations: zero
    acceleration of every one of those coordinates at rest, and each foot's centre of pressure (forward) under the
    centre of mass. Damped Newton with a finite-difference Jacobian. At rest the smooth contact model has no
    friction and the floor normal is vertical, so the forward position does not matter and is left at the start.

    cop_target (fraction): instead of under the centre of mass, each foot's centre of pressure is put at this
    fraction of its sole's heel-to-bend-line length (sole frame). The body is then held at the pelvis (its locked
    tilt takes the remaining moment): a controlled loading of the foot at the same centre of pressure for every
    foot model, not balance."""
    import opensim as osim
    m = osim.Model(str(model_path))
    st = m.initSystem(); m.realizePosition(st)
    cs = m.getCoordinateSet()
    ty = cs.get("pelvis_ty")
    low, _ = _lowest_and_pitch(m, st)
    ty.setValue(st, ty.getValue(st) - low - 0.003, False)                  # a few mm of contact to start from
    acts = [osim.CoordinateActuator.safeDownCast(m.getForceSet().get(f"ankle_torque_{s}")) for s in "rl"]
    for a in acts:
        a.overrideActuation(st, True)
    names = ["pelvis_ty", "ankle_angle_r", "ankle_angle_l"] + [f"{c}_{s}" for c in FOOT_COORDS for s in "rl"
                                                               if cs.contains(f"{c}_{s}") and not cs.get(f"{c}_{s}").getDefaultLocked()]
    coords = [cs.get(n) for n in names]
    for c in cs:
        c.setSpeedValue(st, 0.0)
    nq = len(coords)
    x0 = np.concatenate([[c.getValue(st) for c in coords], [0.0, 0.0]])

    def apply(x):
        for c, v in zip(coords, x[:nq]):
            c.setValue(st, float(v), False)
        for a, v in zip(acts, x[nq:]):
            a.setOverrideActuation(st, float(v))
        m.realizeAcceleration(st)

    soles = {s: json.loads(Path(sj).read_text()) for s, sj in (("r", sole_r), ("l", sole_l))}
    target_mm = None
    if cop_target is not None:
        target_mm = {}
        for s, so in soles.items():
            bp, bd = np.asarray(so["bend"]["point"], float), np.asarray(so["bend"]["dir"], float)
            target_mm[s] = cop_target * (bp[0] - bp[1] * bd[0] / bd[1])         # bend line at z = 0

    def resid(x):
        apply(x)
        acc = [c.getAccelerationValue(st) for c in coords]
        if target_mm is None:
            _, _, cop = _sole_forces(m, st)
            com = m.calcMassCenterPosition(st).get(0)
            return np.array(acc + [100.0 * (cop["r"][0][0] - com), 100.0 * (cop["l"][0][0] - com)])
        labels, data, _ = _sole_forces(m, st)
        e = [(SS.sphere_centre_of_pressure(labels, data, soles[s])[0][0][0] - target_mm[s]) / 10.0 for s in "rl"]
        return np.array(acc + e)
    lo = x0 + np.array([-0.05, -0.35, -0.35] + [-0.7] * (nq - 3) + [-400, -400])
    hi = x0 + np.array([0.05, 0.35, 0.35] + [0.7] * (nq - 3) + [400, 400])
    x, nfev, it = x0.copy(), 0, 0
    r = resid(x); nfev += 1
    for it in range(200):
        if np.abs(r).max() < tol:
            break
        J = np.empty((len(x), len(x)))
        for j in range(len(x)):
            h = 1e-6 if j < nq else 1e-3
            J[:, j] = (resid(x + np.eye(len(x))[j] * h) - r) / h
        nfev += len(x)
        dx = -np.linalg.lstsq(J, r, rcond=None)[0]
        step = 1.0
        while step > 1e-6:
            xn = np.clip(x + step * dx, lo, hi)
            rn = resid(xn); nfev += 1
            if np.linalg.norm(rn) < np.linalg.norm(r):
                break
            step /= 2
        if step <= 1e-6:
            break
        x, r = xn, rn
    r = resid(x)
    weight = m.getTotalMass(st) * 9.81
    labels, data, cop = _sole_forces(m, st)
    com = m.calcMassCenterPosition(st)
    out = dict(status=STATUS, method=("quasi-static standing, ankle torque solved (damped Newton)" if cop_target is None
                                      else f"controlled loading: centre of pressure at {cop_target:.2f} of heel-to-bend "
                                           f"length, ankle torque solved, body held at the pelvis"),
               cop_target_fraction=cop_target, cop_target_sole_mm=target_mm,
               body_weight_N=round(weight, 2),
               solver=dict(converged=bool(np.abs(r).max() < 1e-4), iterations=it, nfev=nfev,
                           max_abs_residual=float(np.abs(r).max())),
               ankle_torque_Nm={s: round(float(v), 2) for s, v in zip("rl", x[nq:])},
               com_minus_cop_mm={s: [round(1000 * (com.get(0) - cop[s][0][0]), 3), round(1000 * (com.get(2) - cop[s][0][1]), 1)]
                                 for s in "rl"})
    tot = 0.0
    for side, sj in (("R", sole_r), ("L", sole_l)):
        sole = json.loads(Path(sj).read_text())
        f = SS.region_forces(labels, data, sole)
        c, tt = SS.sphere_centre_of_pressure(labels, data, sole)
        out[side] = dict(total_N=round(float(tt[0]), 2), cop_sole_mm=[round(float(v), 1) for v in c[0]],
                         regions_N={n: round(float(v[0]), 2) for n, v in f.items()},
                         regions_pct_of_foot={n: round(100 * float(v[0]) / float(tt[0]), 2) for n, v in f.items()})
        tot += float(tt[0])
    out["total_N"] = round(tot, 2)
    out["support_error_pct"] = round(100 * (tot - weight) / weight, 3)
    out["angles_deg"] = {n: round(math.degrees(c.getValue(st)), 3) for n, c in zip(names, coords) if n != "pelvis_ty"}
    out["at_bounds"] = [n for n, v, a, b in zip(names + ["ankle_torque_r", "ankle_torque_l"], x, lo, hi) if min(v - a, b - v) < 1e-6]
    out["solved"] = bool(out["solver"]["converged"] and abs(out["support_error_pct"]) < 0.5 and not out["at_bounds"])
    mtj = [math.radians(out["angles_deg"][f"mtj_angle_{s}"]) for s in "rl" if f"mtj_angle_{s}" in out["angles_deg"]]
    out["mtj_outside_paper_range"] = bool(any(DP.out_of_range(q) for q in mtj))
    return out


def symmetric(posture_deg):
    """Right-side angles on both sides, so left and right feet see the same posture."""
    out = dict(posture_deg)
    for n, v in posture_deg.items():
        if n.endswith("_r"):
            out[n[:-2] + "_l"] = v
    return out


def run(model_in, sole_r, sole_l, out_dir, posture_deg=None, free_foot=False, perturb=None, label="", radius_mm=None,
        keep_models=False, cop_target=None):
    path, meta, removed = build(model_in, sole_r, sole_l, out_dir, posture_deg, free_foot, perturb, radius_mm)
    res = equilibrium(path, sole_r, sole_l, cop_target=cop_target)
    if not keep_models:                                  # the models can be rebuilt from the inputs; keep disk free
        for f in Path(out_dir).glob("*.osim"):
            f.unlink()
    res.update(label=label, model=str(model_in), free_foot=free_foot, posture_deg=posture_deg, perturbation=perturb or {},
               posture_applied=meta["posture"],
               removed_forces=removed,
               registration={s: dict(scale=meta[s]["scale"], scale_used=meta[s]["scale_used"],
                                     spheres_per_body=meta[s]["spheres_per_body"],
                                     residuals=meta[s]["registration_residuals"]) for s in "RL"})
    (Path(out_dir) / "result.json").write_text(json.dumps(res, indent=1) + "\n")
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("model"); ap.add_argument("sole_r"); ap.add_argument("sole_l"); ap.add_argument("-o", required=True)
    ap.add_argument("--mot", help="kinematics (.mot, degrees) to take a sagittal posture from")
    ap.add_argument("--time", type=float, default=0.0, help="time in --mot")
    ap.add_argument("--free-foot", action="store_true", help="leave mtj and mtp free (otherwise locked at 0)")
    ap.add_argument("--perturb", action="append", default=[], metavar="KEY=VALUE")
    a = ap.parse_args()
    posture = posture_from_mot(a.mot, a.time, SAGITTAL) if a.mot else {}
    pert = {k: float(v) for k, v in (kv.split("=", 1) for kv in a.perturb)}
    print(json.dumps(run(a.model, a.sole_r, a.sole_l, a.o, posture, a.free_foot, pert), indent=1))


if __name__ == "__main__":
    main()
