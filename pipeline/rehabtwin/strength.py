"""Strength calibration: hand-held dynamometry → personalised muscle capacities.

A generic OpenSim muscle set encodes literature strength, not this person's. Maximal
isometric joint torques measured with a dynamometer (hip abduction, knee extension, ...)
fix that for the muscles that produce them: for each test the model is put in the test
posture, every muscle's isometric moment at full activation is computed, and the test's
prime movers (``configs/strength_actions.json``) get one common max-isometric-force factor
so the model reproduces the measured torque. Synergists calibrated by another test enter
with their own factor, the remaining synergists follow the test they contribute most to,
and the tests are solved jointly by Gauss-Seidel iteration.

This is the evidence ``docs/accuracy.md`` asks for before saying a muscle group is weak:
a measured torque, a limb symmetry index (weaker / stronger side), never body shape alone.
Muscle geometry (attachments, paths) stays generic unless the model is Tier A.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np

from .config import CONFIG_DIR
from .opensim_stage import _osim

ACTIONS_FILE = CONFIG_DIR / "strength_actions.json"
LSI_FLAG = 90.0     # % — a common clinical threshold for between-limb asymmetry


def load_actions(path=ACTIONS_FILE):
    return {k: v for k, v in json.loads(Path(path).read_text()).items() if not k.startswith("_")}


def expand(action, side, actions):
    """Concrete coordinate / sign / prime-mover regex / default posture for ``action`` on ``side``."""
    a = actions[action]
    sub = (lambda x: x.replace("{s}", side)) if side else (lambda x: x)
    return {"coordinate": sub(a["coordinate"]), "sign": a["sign"], "muscles": sub(a["muscles"]),
            "posture": {sub(c): v for c, v in a.get("default_posture", {}).items()}}


def _decoupled(model, pattern):
    """Copy of ``model`` without the coupler constraints whose dependent coordinate matches ``pattern``.

    The lumbar levels of the Pose2Sim/Christophy spine are coupled to L5_S1; a moment arm about the
    coupled L5_S1 coordinate sums every level (~7x), whereas a trunk dynamometer measures the
    torque about the L5/S1 joint alone.
    """
    osim = _osim()
    m = model.clone()
    cs = m.updConstraintSet()
    for i in reversed(range(cs.getSize())):
        c = osim.CoordinateCouplerConstraint.safeDownCast(cs.get(i))
        if c is not None and re.match(pattern, c.getDependentCoordinateName()):
            cs.remove(i)
    m.finalizeConnections()
    return m


def parse_test(test, actions):
    """{"action": "hip_abduction_r", "torque_Nm": 85} (or force_N + lever_arm_m) -> resolved test dict."""
    name = test["action"]
    m = re.match(r"^(.*)_([rl])$", name)
    base, side = (m.group(1), m.group(2)) if m and m.group(1) in actions else (name, "")
    if base not in actions:
        raise ValueError(f"unknown strength action {name!r}; known: {sorted(actions)} (+ _r/_l)")
    t = expand(base, side, actions)
    t["decouple"] = actions[base].get("decouple")
    if "torque_Nm" in test:
        torque = float(test["torque_Nm"])
    elif "force_N" in test and "lever_arm_m" in test:
        torque = float(test["force_N"]) * float(test["lever_arm_m"])
    else:
        raise ValueError(f"{name}: give torque_Nm, or force_N and lever_arm_m")
    t["posture"].update(test.get("posture_deg", {}))
    t.update(action=name, base=base, side=side, measured_Nm=abs(torque))
    return t


def isometric_moments(model, test):
    """{muscle: moment (N·m)} at full activation in the test posture, for muscles acting in the tested direction."""
    osim = _osim()
    if test.get("decouple"):
        model = _decoupled(model, test["decouple"])
    state = model.initSystem()
    cs = model.getCoordinateSet()
    for c, v in test["posture"].items():
        co = cs.get(c)
        co.setValue(state, np.radians(v) if co.getMotionType() == osim.Coordinate.Rotational else v, False)
    model.assemble(state)
    model.realizePosition(state)
    ms = model.getMuscles()
    for i in range(ms.getSize()):
        ms.get(i).setActivation(state, 1.0)
    model.equilibrateMuscles(state)
    model.realizeDynamics(state)
    coord = cs.get(test["coordinate"])
    out = {}
    for i in range(ms.getSize()):
        mu = ms.get(i)
        r = mu.computeMomentArm(state, coord)
        if abs(r) < 1e-4:
            continue
        tq = r * mu.getTendonForce(state) * test["sign"]
        if tq > 0:
            out[mu.getName()] = tq
    return out


def calibrate(model_path, tests, out_dir, actions=None, iterations=20, bounds=(0.1, 3.0)):
    """Fit per-test max-isometric-force factors; write ``model_strength.osim`` and ``strength.json``."""
    osim = _osim()
    actions = actions or load_actions()
    tests = [parse_test(t, actions) for t in tests]
    model = osim.Model(str(model_path))
    fs = model.updForceSet()
    for i in reversed(range(fs.getSize())):        # contact spheres are irrelevant here
        if "SmoothSphereHalfSpaceForce" in fs.get(i).getConcreteClassName():
            fs.remove(i)
    moments = [isometric_moments(model, t) for t in tests]
    prime = [[m for m in mom if re.match(t["muscles"], m)] for t, mom in zip(tests, moments)]
    for t, p in zip(tests, prime):
        if not p:
            raise ValueError(f"{t['action']}: no prime mover matching {t['muscles']!r} acts in the tested direction")
    # Synergists that are no test's prime mover would otherwise keep generic strength and soak up the
    # measured torque; each joins the test it contributes the largest share to.
    is_prime = {m for p in prime for m in p}
    secondary = [[] for _ in tests]
    for m in sorted({m for mom in moments for m in mom} - is_prime):
        j = max(range(len(tests)), key=lambda j: moments[j].get(m, 0.0) / sum(moments[j].values()))
        secondary[j].append(m)
    prime = [p + sec for p, sec in zip(prime, secondary)]
    factor = {}
    for _ in range(iterations):
        change = 0.0
        for j, (t, mom, p) in enumerate(zip(tests, moments, prime)):
            other = sum(factor.get(m, 1.0) * v for m, v in mom.items() if m not in p)
            k = (t["measured_Nm"] - other) / sum(mom[m] for m in p)
            k = float(np.clip(k, *bounds))
            for m in p:
                change = max(change, abs(factor.get(m, 1.0) - k))
                factor[m] = k
        if change < 1e-6:
            break
    results = []
    for t, mom, p, sec in zip(tests, moments, prime, secondary):
        generic = sum(mom.values())
        fitted = sum(factor.get(m, 1.0) * v for m, v in mom.items())
        k = factor[p[0]]
        results.append({"action": t["action"], "coordinate": t["coordinate"], "posture_deg": t["posture"],
                        "measured_Nm": round(t["measured_Nm"], 2), "generic_model_Nm": round(generic, 2),
                        "calibrated_model_Nm": round(fitted, 2), "factor": round(k, 3),
                        "at_bound": bool(k <= bounds[0] + 1e-9 or k >= bounds[1] - 1e-9),
                        "prime_movers": sorted(m for m in p if m not in sec),
                        "synergists_scaled_with_this_test": sorted(sec),
                        "scaled_share_of_generic": round(sum(mom[m] for m in p) / generic, 3)})
    ms = model.updMuscles()
    for m, k in factor.items():
        mu = ms.get(m)
        mu.setMaxIsometricForce(mu.getMaxIsometricForce() * k)
    model.finalizeConnections()
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    model.printToXML(str(out_dir / "model_strength.osim"))
    state = model.initSystem()
    mass = model.getTotalMass(state)
    record = {"model": str(model_path), "body_mass_kg": round(mass, 2), "tests": results,
              "symmetry": symmetry(results), "muscle_factors": {m: round(k, 3) for m, k in sorted(factor.items())},
              "calibrated_muscles": len(factor), "total_muscles": model.getMuscles().getSize(),
              "notes": ["Generic muscle geometry; only max isometric forces of the tested prime movers changed.",
                        "Moments at full activation of agonists only; antagonist co-contraction during the test "
                        "would make the measured torque underestimate agonist strength.",
                        "Factors at a bound (see at_bound) mean the measurement and model disagree beyond "
                        "physiology: check posture, lever arm and units before trusting them."]}
    (out_dir / "strength.json").write_text(json.dumps(record, indent=2) + "\n")
    return record


def symmetry(results):
    """Limb symmetry index per action measured on both sides: weaker / stronger x 100."""
    by = {}
    for r in results:
        m = re.match(r"^(.*)_([rl])$", r["action"])
        if m:
            by.setdefault(m.group(1), {})[m.group(2)] = r["measured_Nm"]
    out = {}
    for a, s in by.items():
        if set(s) == {"r", "l"}:
            lsi = 100.0 * min(s.values()) / max(s.values())
            out[a] = {"right_Nm": s["r"], "left_Nm": s["l"], "lsi_pct": round(lsi, 1),
                      "weaker_side": "r" if s["r"] < s["l"] else "l" if s["l"] < s["r"] else None,
                      "flag": lsi < LSI_FLAG}
    return out
