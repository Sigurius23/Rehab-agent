#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors
# SPDX-License-Identifier: CERN-OHL-S-2.0
"""Dynamic comparison of VALIDATION_PLAN.md stage A, amendment 4: muscle-driven MocoTrack of the squats in two arms
that differ only in the foot contact. Phase 1 (this file's solve and batch commands) never reads force data.

Arms (the same distributed subject model, with muscles, in both):
  A  our sole (EU 42, 15 mm spacing) on both feet with the assumed contact v1 (sole_sim.add_to_osim), placed by the
     OpenCap spheres it then replaces (amendment 1);
  B  OpenCap's six spheres per foot with OpenCap's contact parameters (foot_models/opencap_contacts.py, amendment 1).

Window (kinematics only, fixed 2026-11-06 before any solve): the dataset's pelvis height, low-pass filtered at 6 Hz
(4th-order zero-lag Butterworth); troughs with a prominence of at least half the trial's range; the first trough
with a standing frame (within 5 % of the range of the trial's highest point) on both sides, between it and the
neighbouring troughs or the trial's ends. The window runs from the last standing frame before that trough to the
first standing frame after it.

Tracking: MocoTrack of the dataset's inverse-kinematics coordinates (low-pass filtered at 6 Hz), muscles as
DeGrooteFregly2016 (tendons rigid, passive fibre forces ignored, active force-length curve widened 1.5x, as in
Moco's examples), reserve actuators on every coordinate without an actuator of its own. The coupled patellar
coordinates (knee_angle_*_beta) are not tracked; they follow their constraints. Per-coordinate weights
(SETTINGS["coordinate_weights"]) multiply the global tracking weight for a coordinate's value and speed. Settings are
in SETTINGS, versioned; a change is allowed only for convergence and tracking error (amendment 4), applies to both
arms, and is logged in foot_models/dynamic_settings_log.json.

Settings v3 (2026-11-09) adds two solver settings, the same rule in both arms:
  - Torque actuators: the trunk and arm coordinates are driven by the distributed model's own coordinate actuators
    (no muscles cross them). Each one's strength (optimal force) is, per subject, its peak inverse-dynamics torque
    over the subject's squat windows, from the recorded kinematics (filtered as tracked) with no external loads,
    rounded up to the next 10 Nm (torque_actuator_strengths). That needs the torques not to depend on the ground
    forces. It is checked for every model: by its structure (no contact, muscle or constraint links the bodies a
    coordinate moves to the rest; joint_subtree, check_no_ground_load), and numerically (the torques do not change
    when large contact forces act on the feet, while the ankle's do).
  - Initial guess: the tracked states, with the pelvis height shifted at each time point to the arm's own contact
    balance, where its feet carry the model's weight at rest (contact_balance_offsets).

Validity (amendment 4): the solver converged, and the pelvis residuals are within Hicks et al. (2015): the largest
residual force at most 5 % of the peak external force, the largest residual moment at most 1 % of the centre-of-mass
height (at the window's start) times that force. The external force is the model's own contact force (the sum of
both feet); force-plate data is never read here.

Each solve is one case of foot_models/case_store.py: resumable, fingerprinted by the models, the inverse
kinematics, the window, the settings, the code and the tool versions.

  python foot_models/dynamic_track.py window IK.mot
  python foot_models/dynamic_track.py build SUBJECT_CONTACTS.osim OUT_DIR          # writes arm A's model
  python foot_models/dynamic_track.py batch --subjects-dir MODELS --kinematics KIN -o OUT --jobs 6 --threads 4 \\
      [--only subject2:squats1] [--max-iterations N]
"""
import argparse
import hashlib
import json
import math
import os
import platform
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import get_context
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
import case_store as CS  # noqa: E402
import double_support as DS  # noqa: E402
import sole_sim as SS  # noqa: E402

SETTINGS_VERSION = 3            # history and reasons: foot_models/dynamic_settings_log.json
SETTINGS = dict(
    filter_hz=6.0, mesh_interval_s=0.02, states_tracking_weight=10.0, control_effort_weight=1.0,
    reserve_optimal_force_Nm_or_N=1.0, active_force_width_scale=1.5,
    convergence_tolerance=1e-2, constraint_tolerance=1e-3, max_iterations=3000,
    transcription="hermite-simpson", untracked=("knee_angle_r_beta", "knee_angle_l_beta"),
    coordinate_weights={"pelvis_tx": 100.0, "pelvis_ty": 100.0, "pelvis_tz": 100.0},   # value and speed; others 1
    torque_actuator_strength="peak_inverse_dynamics", torque_actuator_round_up_Nm=10.0,  # v3, see the docstring
    initial_guess="contact_balance")                                                   # v3
# The coordinates the distributed models drive with their own coordinate actuators (checked in torque_driven)
TORQUE_DRIVEN = ("lumbar_extension", "lumbar_bending", "lumbar_rotation") + tuple(
    f"{c}_{side}" for side in "rl" for c in ("arm_flex", "arm_add", "arm_rot", "elbow_flex", "pro_sup"))
TRIALS = ("squats1", "squatsAsym1")
SOLE_R = HERE.parent / "sim" / "EU42_R_636645a928.sole_sim.json"
SOLE_L = HERE.parent / "sim" / "EU42_L_40fe8e1d0c.sole_sim.json"
CODE_FILES = (HERE / "dynamic_track.py", HERE.parent / "sole_sim.py", HERE / "opencap_contacts.py")
PELVIS = ("pelvis_tilt", "pelvis_list", "pelvis_rotation", "pelvis_tx", "pelvis_ty", "pelvis_tz")


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# ------------------------------------------------------------------------------------------------ window
def squat_window(ik_path, cutoff_hz=6.0, prominence=0.5, standing=0.05):
    """The first complete squat repetition (see the module docstring): (start s, end s, trough s, details)."""
    from scipy.signal import butter, filtfilt, find_peaks
    t, names, d, _ = DS.load_mot(ik_path)
    y = d[:, names.index("pelvis_ty")]
    dt = float(np.median(np.diff(t)))
    b, a = butter(2, cutoff_hz / (0.5 / dt))
    ys = filtfilt(b, a, y)
    rng = float(ys.max() - ys.min())
    troughs, _ = find_peaks(-ys, prominence=prominence * rng)
    up = ys >= ys.max() - standing * rng
    edges = [0] + list(troughs) + [len(t) - 1]
    for k, i in enumerate(troughs):
        before = [j for j in range(edges[k], i) if up[j]]
        after = [j for j in range(i + 1, edges[k + 2] + 1) if up[j]]
        if before and after:
            return float(t[before[-1]]), float(t[after[0]]), float(t[i]), dict(
                range_m=round(rng, 4), depth_m=round(float(ys.max() - ys[i]), 4), troughs=len(troughs), repetition=k + 1)
    raise ValueError(f"{ik_path}: no complete squat repetition")


# ------------------------------------------------------------------------------------------------ models
def build_arm_a(contacts_model, out_dir):
    """Arm A: our sole on both feet with the assumed contact v1, replacing the OpenCap spheres."""
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    with_r, both = out_dir / "armA_with_R.osim", out_dir / "armA_sole.osim"
    meta_r = SS.add_to_osim(contacts_model, SOLE_R, with_r, contact=SS.ASSUMED_CONTACT_V1)
    meta_l = SS.add_to_osim(with_r, SOLE_L, both, contact=SS.ASSUMED_CONTACT_V1)
    return both, {"R": meta_r, "L": meta_l}


def contact_force_names(model_path):
    """The contact forces of each foot, as component paths: (right, left)."""
    import opensim as osim
    m = osim.Model(str(model_path)); m.finalizeConnections()
    right, left = [], []
    for i in range(m.getForceSet().getSize()):
        f = m.getForceSet().get(i)
        if f.getConcreteClassName() != "SmoothSphereHalfSpaceForce":
            continue
        sp = f.getSocket("sphere").getConnecteePath()
        n = f.getName()
        side = "r" if (n.startswith("force_sole_r") or n.endswith("_r")) else "l" if (n.startswith("force_sole_l") or n.endswith("_l")) else None
        if side is None:
            raise ValueError(f"{model_path}: contact force {n} ({sp}) has no side")
        (right if side == "r" else left).append(f.getAbsolutePathString())
    return right, left


# ------------------------------------------------------------------------------------------------ settings v3
def process_model(model_path, settings, strengths=None):
    """The model as the solve uses it: muscles as DeGrooteFregly2016 with rigid tendons, reserves, and, when the
    settings use them (v3), the torque actuators' strengths. Returns an initialised Model."""
    import opensim as osim
    mp = osim.ModelProcessor(str(model_path))
    mp.append(osim.ModOpIgnoreTendonCompliance())
    mp.append(osim.ModOpReplaceMusclesWithDeGrooteFregly2016())
    mp.append(osim.ModOpIgnorePassiveFiberForcesDGF())
    mp.append(osim.ModOpScaleActiveFiberForceCurveWidthDGF(settings["active_force_width_scale"]))
    mp.append(osim.ModOpAddReserves(settings["reserve_optimal_force_Nm_or_N"]))
    model = mp.process()
    if settings.get("torque_actuator_strength"):
        if strengths is None:
            raise ValueError(f"settings v{settings.get('version')} need the torque actuators' strengths")
        acts = torque_driven(model)
        if set(strengths) != set(acts):
            raise ValueError(f"{model_path}: strengths for {sorted(strengths)}, torque actuators on {sorted(acts)}")
        for coord, name in acts.items():
            osim.CoordinateActuator.safeDownCast(model.updForceSet().get(name)).set_optimal_force(float(strengths[coord]))
    model.initSystem()
    return model


def torque_driven(model):
    """{coordinate: actuator name} of the model's own coordinate actuators (not the added reserves). They must be
    exactly TORQUE_DRIVEN, one actuator per coordinate."""
    import opensim as osim
    out = {}
    fs = model.getForceSet()
    for i in range(fs.getSize()):
        a = osim.CoordinateActuator.safeDownCast(fs.get(i))
        if a is None or a.getName().startswith("reserve_"):
            continue
        c = a.get_coordinate()
        if c in out:
            raise ValueError(f"two coordinate actuators on {c}: {out[c]}, {a.getName()}")
        out[c] = a.getName()
    if set(out) != set(TORQUE_DRIVEN):
        raise ValueError(f"torque-driven coordinates {sorted(out)}, expected {sorted(TORQUE_DRIVEN)}")
    return out


def round_up_strength(peak_Nm, step_Nm):
    """A strength from a peak torque: rounded up to the next multiple of step_Nm, at least step_Nm."""
    return float(max(step_Nm, step_Nm * math.ceil(abs(peak_Nm) / step_Nm - 1e-12)))


def joint_subtree(model, coord):
    """The bodies a coordinate moves: its joint's child body and every body joined further from the ground through it."""
    joints = model.getJointSet()
    children = {}
    for i in range(joints.getSize()):
        j = joints.get(i)
        children.setdefault(j.getParentFrame().findBaseFrame().getName(), []).append(j.getChildFrame().findBaseFrame().getName())
    top = model.getCoordinateSet().get(coord).getJoint().getChildFrame().findBaseFrame().getName()
    out, todo = set(), [top]
    while todo:
        b = todo.pop()
        if b not in out:
            out.add(b)
            todo += children.get(b, [])
    return out


def _path_bodies(force):
    """The bodies a muscle's path is attached to."""
    import opensim as osim
    pts = osim.GeometryPath.safeDownCast(osim.PathActuator.safeDownCast(force).getPath()).getPathPointSet()
    return {pts.get(i).getParentFrame().findBaseFrame().getName() for i in range(pts.getSize())}


def check_no_ground_load(model, coords=TORQUE_DRIVEN):
    """Raise unless the torque each coordinate needs comes from the bodies it moves alone: no contact sphere on them,
    no muscle between them and the rest, no constraint on them, and no force of another kind in the model.
    Returns {coordinate: sorted bodies it moves}."""
    import opensim as osim
    trees = {c: joint_subtree(model, c) for c in coords}
    fs = model.getForceSet()
    for i in range(fs.getSize()):
        f = fs.get(i)
        kind = f.getConcreteClassName()
        if kind == "SmoothSphereHalfSpaceForce":
            path = f.getSocket("sphere").getConnecteePath()
            sphere = osim.ContactGeometry.safeDownCast(f.getComponent(path) if not path.startswith("/") else model.getComponent(path))
            body = sphere.getFrame().findBaseFrame().getName()
            for c, tree in trees.items():
                if body in tree:
                    raise ValueError(f"contact {f.getName()} is on {body}, which {c} moves")
        elif kind == "CoordinateActuator":
            continue
        elif osim.PathActuator.safeDownCast(f) is not None:
            bodies = _path_bodies(f)
            for c, tree in trees.items():
                if bodies & tree and bodies - tree:
                    raise ValueError(f"muscle {f.getName()} crosses into the bodies {c} moves")
        else:
            raise ValueError(f"force {f.getName()} ({kind}) is not handled by the check")
    cons = model.getConstraintSet()
    for i in range(cons.getSize()):
        k = osim.CoordinateCouplerConstraint.safeDownCast(cons.get(i))
        if k is None:
            raise ValueError(f"constraint {cons.get(i).getName()} ({cons.get(i).getConcreteClassName()}) is not handled")
        ind = k.getIndependentCoordinateNames()
        for n in [ind.get(j) for j in range(ind.getSize())] + [k.getDependentCoordinateName()]:
            body = model.getCoordinateSet().get(n).getJoint().getChildFrame().findBaseFrame().getName()
            for c, tree in trees.items():
                if body in tree:
                    raise ValueError(f"constraint {k.getName()} acts on {n}, inside what {c} moves")
    return {c: sorted(t) for c, t in trees.items()}


def _u_index(model, state, coord):
    """The coordinate's place in the state's speed vector."""
    import opensim as osim
    keep = state.getU().to_numpy().copy()
    model.getCoordinateSet().get(coord).setSpeedValue(state, 1.0 + float(np.abs(keep).max(initial=0.0)))
    j = int(np.argmax(np.abs(state.getU().to_numpy() - keep)))
    state.setU(osim.Vector.createFromMat(keep))
    return j


def _reference(model, ik_path, settings):
    """The tracked reference (radians, filtered as tracked): (times, {coordinate: values})."""
    import opensim as osim
    tp = osim.TableProcessor(str(ik_path)); tp.append(osim.TabOpConvertDegreesToRadians())
    tp.append(osim.TabOpLowPassFilter(settings["filter_hz"])); tp.append(osim.TabOpUseAbsoluteStateNames())
    ref = tp.process(model)
    labs = set(ref.getColumnLabels())
    cs = model.getCoordinateSet()
    q = {}
    for i in range(cs.getSize()):
        lab = cs.get(i).getAbsolutePathString() + "/value"
        if lab in labs:
            q[cs.get(i).getName()] = ref.getDependentColumn(lab).to_numpy()
    return np.array(ref.getIndependentColumn()), q


def _spheres(model):
    import opensim as osim
    fs = model.getForceSet()
    return [osim.SmoothSphereHalfSpaceForce.safeDownCast(fs.get(i)) for i in range(fs.getSize())
            if fs.get(i).getConcreteClassName() == "SmoothSphereHalfSpaceForce"]


def _sphere_force_y(force, state):
    """The vertical force of the floor on a contact sphere's body (N)."""
    labels = force.getRecordLabels()
    want = force.getName() + ".Sphere.force.Y"
    for i in range(labels.getSize()):
        if labels.get(i) == want:
            return force.getRecordValues(state).get(i)
    raise ValueError(f"{force.getName()}: no record {want}")


def inverse_dynamics_torques(model, ik_path, window, settings, coords=TORQUE_DRIVEN, lower_m=0.03):
    """Inverse dynamics of the recorded kinematics at each frame of the window, with no force of the model applied
    (gravity and the motion only): ({coordinate: torques (Nm)}, check). Speeds and accelerations are central
    differences of the filtered coordinates on their own time points. The numerical check, at three frames: with the
    pelvis lowered by lower_m and only the contact forces applied, the torques at coords must not change, while the
    ankle's must."""
    import opensim as osim
    t, q = _reference(model, ik_path, settings)
    keep = (t >= window[0] - 1e-9) & (t <= window[1] + 1e-9)
    t = t[keep]
    q = {c: v[keep] for c, v in q.items()}
    u = {c: np.gradient(v, t) for c, v in q.items()}
    ud = {c: np.gradient(v, t) for c, v in u.items()}
    models = dict(bare=model.clone(), contact=model.clone())
    for name, m in models.items():
        fs = m.updForceSet()
        for i in range(fs.getSize()):
            fs.get(i).set_appliesForce(name == "contact" and fs.get(i).getConcreteClassName() == "SmoothSphereHalfSpaceForce")
    states = {n: m.initSystem() for n, m in models.items()}
    index = {n: {c: _u_index(m, states[n], c) for c in q} for n, m in models.items()}
    solvers = {n: osim.InverseDynamicsSolver(m) for n, m in models.items()}
    weight = model.getTotalMass(states["bare"]) * abs(model.getGravity().get(1))

    def tau(n, k, dy=0.0):
        m, st, ix = models[n], states[n], index[n]
        U, UD = np.zeros(st.getNU()), np.zeros(st.getNU())
        for c in q:
            m.getCoordinateSet().get(c).setValue(st, float(q[c][k] + (dy if c == "pelvis_ty" else 0.0)), False)
            U[ix[c]], UD[ix[c]] = u[c][k], ud[c][k]
        st.setU(osim.Vector.createFromMat(U))
        m.realizeVelocity(st)
        v = solvers[n].solve(st, osim.Vector.createFromMat(UD))
        return {c: v.get(ix[c]) for c in list(coords) + ["ankle_angle_r"]}

    out = {c: [] for c in coords}
    check = dict(max_change_Nm=0.0, ankle_change_Nm=[], contact_force_bw=[])
    probe = set(int(k) for k in np.linspace(0, len(t) - 1, 3))
    for k in range(len(t)):
        a = tau("bare", k)
        for c in coords:
            out[c].append(a[c])
        if k in probe:
            b0, b = tau("bare", k, -lower_m), tau("contact", k, -lower_m)
            models["contact"].realizeDynamics(states["contact"])
            check["contact_force_bw"].append(round(sum(_sphere_force_y(f, states["contact"]) for f in _spheres(models["contact"])) / weight, 2))
            check["max_change_Nm"] = max(check["max_change_Nm"], max(abs(b[c] - b0[c]) for c in coords))
            check["ankle_change_Nm"].append(round(abs(b["ankle_angle_r"] - b0["ankle_angle_r"]), 2))
    return {c: np.array(v) for c, v in out.items()}, check


def torque_actuator_strengths(model_paths, trials, settings):
    """Settings v3: per subject, each torque actuator's strength (Nm), the same for all the given models (the arms).
    trials: [(ik_path, window)] of the subject. Each model is checked (check_no_ground_load and the numerical check
    of inverse_dynamics_torques), and the peaks must agree between the models. Returns dict(strengths_Nm, peak_Nm,
    check)."""
    peaks, checks = [], []
    for mp in model_paths:
        model = process_model(mp, dict(settings, torque_actuator_strength=None))
        torque_driven(model)
        check_no_ground_load(model)
        pk = {c: 0.0 for c in TORQUE_DRIVEN}
        for ik, w in trials:
            taus, chk = inverse_dynamics_torques(model, ik, w, settings)
            if chk["max_change_Nm"] > 1e-6:
                raise ValueError(f"{mp}: the torque-driven coordinates' torques change with the ground force "
                                 f"({chk['max_change_Nm']:.3g} Nm)")
            if min(chk["ankle_change_Nm"]) < 1.0:
                raise ValueError(f"{mp}: the numerical check has no effect at the ankle ({chk['ankle_change_Nm']})")
            checks.append(dict(model=Path(mp).name, ik=Path(ik).name, **chk))
            for c in TORQUE_DRIVEN:
                pk[c] = max(pk[c], float(np.abs(taus[c]).max()))
        peaks.append(pk)
    for other in peaks[1:]:
        for c in TORQUE_DRIVEN:
            if abs(other[c] - peaks[0][c]) > 1e-6 * max(1.0, peaks[0][c]):
                raise ValueError(f"{c}: the peak torque differs between the models ({peaks[0][c]} vs {other[c]} Nm)")
    step = settings["torque_actuator_round_up_Nm"]
    return dict(strengths_Nm={c: round_up_strength(peaks[0][c], step) for c in TORQUE_DRIVEN},
                peak_Nm={c: round(peaks[0][c], 3) for c in TORQUE_DRIVEN}, check=checks)


def contact_balance_offsets(model, traj, bracket_m=0.1, iterations=48):
    """Settings v3's initial guess: for each time point of a MocoTrajectory, the pelvis-height offset (m) at which the
    model's contact forces, at rest in that posture, carry the model's weight. From the model alone."""
    cs = model.getCoordinateSet()
    st = model.initSystem()
    names = set(traj.getStateNames())
    vals = {}
    for i in range(cs.getSize()):
        lab = cs.get(i).getAbsolutePathString() + "/value"
        if lab in names:
            vals[cs.get(i).getName()] = traj.getStateMat(lab)
        cs.get(i).setSpeedValue(st, 0.0)
    spheres = _spheres(model)
    weight = model.getTotalMass(st) * abs(model.getGravity().get(1))

    def force(k, dy):
        for c, v in vals.items():
            cs.get(c).setValue(st, float(v[k] + (dy if c == "pelvis_ty" else 0.0)), False)
        model.realizeDynamics(st)
        return sum(_sphere_force_y(f, st) for f in spheres)

    out = np.zeros(traj.getNumTimes())
    for k in range(traj.getNumTimes()):
        lo, hi = -bracket_m, bracket_m                      # the force falls as the pelvis rises
        if not force(k, lo) > weight > force(k, hi):
            raise ValueError(f"time point {k}: no pelvis offset within +-{bracket_m} m carries the model's weight")
        for _ in range(iterations):
            mid = 0.5 * (lo + hi)
            lo, hi = (mid, hi) if force(k, mid) > weight else (lo, mid)
        out[k] = 0.5 * (lo + hi)
    return out


def shift_guess(traj, offsets):
    """The trajectory, in place, with pelvis_ty moved by offsets (m) and its speed by their time derivative."""
    import opensim as osim
    t = np.array(traj.getTimeMat())
    value = next(n for n in traj.getStateNames() if n.endswith("/pelvis_ty/value"))
    speed = value[:-len("value")] + "speed"
    traj.setState(value, osim.Vector.createFromMat(traj.getStateMat(value) + offsets))
    traj.setState(speed, osim.Vector.createFromMat(traj.getStateMat(speed) + np.gradient(offsets, t)))
    return traj


# ------------------------------------------------------------------------------------------------ solve
def tracking_study(model, model_path, ik_path, window, settings, threads=1, max_iterations=None):
    """The MocoTrack study of one solve and its solver, set up from the settings: (study, solver)."""
    import opensim as osim
    tr = osim.MocoTrack()
    tr.setName("track")
    tr.setModel(osim.ModelProcessor(model))
    tp = osim.TableProcessor(str(ik_path))
    tp.append(osim.TabOpConvertDegreesToRadians())          # the .mot is in degrees; MocoTrack does not convert it
    tp.append(osim.TabOpLowPassFilter(settings["filter_hz"]))
    tp.append(osim.TabOpUseAbsoluteStateNames())
    tr.setStatesReference(tp)
    tr.set_states_global_tracking_weight(settings["states_tracking_weight"])
    tr.set_allow_unused_references(True)
    tr.set_track_reference_position_derivatives(True)
    tr.set_apply_tracked_states_to_guess(True)
    tr.set_initial_time(window[0]); tr.set_final_time(window[1])
    tr.set_mesh_interval(settings["mesh_interval_s"])
    tr.set_control_effort_weight(settings["control_effort_weight"])
    weights = osim.MocoWeightSet()
    per_coord = {name: 0.0 for name in settings["untracked"]}
    per_coord.update(settings.get("coordinate_weights", {}))
    for name, w in per_coord.items():
        if not model.getCoordinateSet().contains(name):
            raise ValueError(f"{model_path}: no coordinate {name} for a tracking weight")
        path = model.getCoordinateSet().get(name).getAbsolutePathString()
        weights.cloneAndAppend(osim.MocoWeight(path + "/value", float(w)))
        weights.cloneAndAppend(osim.MocoWeight(path + "/speed", float(w)))
    tr.set_states_weight_set(weights)
    study = tr.initialize()
    solver = osim.MocoCasADiSolver.safeDownCast(study.updSolver())
    solver.set_optim_convergence_tolerance(settings["convergence_tolerance"])
    solver.set_optim_constraint_tolerance(settings["constraint_tolerance"])
    solver.set_optim_max_iterations(int(max_iterations or settings["max_iterations"]))
    solver.set_transcription_scheme(settings["transcription"])
    solver.set_parallel(int(threads))
    return study, solver


def guess_at_contact_balance(model, study, solver, out_dir):
    """Settings v3: replace the solver's guess (the tracked states, as MocoTrack set them) by the same states with the
    pelvis at the model's own contact balance. Writes guess_tracked_states.sto and guess.sto; returns the offsets (m)."""
    import opensim as osim
    out_dir = Path(out_dir)
    g = solver.getGuess()
    times = np.array(g.getTimeMat())
    g.write(str(out_dir / "guess_tracked_states.sto"))
    guess = osim.MocoTrajectory(str(out_dir / "guess_tracked_states.sto"))
    guess.setTime(osim.Vector.createFromMat(times))          # the file rounds the times; the solver needs them exact
    off = contact_balance_offsets(model, guess)
    shift_guess(guess, off)
    solver.resetProblem(study.getProblem())                  # the study initialize() returns is a copy
    solver.setGuess(guess)
    guess.write(str(out_dir / "guess.sto"))
    return off


def track(model_path, ik_path, window, settings, out_dir, threads=1, max_iterations=None, strengths=None):
    """One MocoTrack solve. Writes solution.sto and result.json in out_dir; returns the result. strengths: the
    torque actuators' strengths (settings v3, torque_actuator_strengths)."""
    import opensim as osim
    out_dir = Path(out_dir)
    osim.Logger.removeFileSink(); osim.Logger.addFileSink(str(out_dir / "opensim.log"))
    model = process_model(model_path, settings, strengths)
    study, solver = tracking_study(model, model_path, ik_path, window, settings, threads, max_iterations)
    extra = {}
    if settings.get("torque_actuator_strength"):
        extra["torque_actuator_strengths_Nm"] = dict(strengths)
    if settings.get("initial_guess") == "contact_balance":
        off = guess_at_contact_balance(model, study, solver, out_dir)
        extra["initial_guess_pelvis_offset_mm"] = dict(min=round(1000 * float(off.min()), 3),
                                                      median=round(1000 * float(np.median(off)), 3),
                                                      max=round(1000 * float(off.max()), 3), time_points=len(off))
    elif settings.get("initial_guess") not in (None, "tracked_states"):
        raise ValueError(f"initial_guess {settings.get('initial_guess')!r}")
    t0 = time.time()
    sol = study.solve()
    seconds = time.time() - t0
    converged = bool(sol.success())
    sol.unseal()
    path = out_dir / "solution.sto"
    sol.write(str(path))
    res = dict(converged=converged, status=sol.getStatus(), iterations=int(sol.getNumIterations()), solve_seconds=round(seconds, 1),
               objective=float(sol.getObjective()), solution_sha256=sha256(path), window_s=list(window))
    res.update(check(model, sol, ik_path, settings, model_path))
    res.update(extra)
    (out_dir / "result.json").write_text(json.dumps(res, indent=1) + "\n")
    return res


def check(model, sol, ik_path, settings, model_path):
    """Validity (pelvis residuals, Hicks et al. 2015) and tracking error of a solution, from the model alone."""
    import opensim as osim
    right, left = contact_force_names(model_path)
    grf = osim.createExternalLoadsTableForGait(model, sol, right, left)
    cols = list(grf.getColumnLabels())
    F = lambda side: np.column_stack([grf.getDependentColumn(f"ground_force_{side}_v{a}").to_numpy() for a in "xyz"])
    total = F("r") + F("l")
    peak = float(np.max(np.linalg.norm(total, axis=1)))
    traj = sol.exportToStatesTrajectory(model)
    st = traj.get(0); model.realizePosition(st)
    com_h = float(model.calcMassCenterPosition(st).get(1))
    time_ = sol.getTimeMat()
    resid = {}
    for name in sol.getControlNames():
        leaf = name.split("/")[-1]
        for p in PELVIS:
            if leaf.startswith("reserve") and leaf.endswith(p):
                act = osim.CoordinateActuator.safeDownCast(model.getComponent(name))
                resid[p] = float(np.max(np.abs(sol.getControlMat(name)))) * act.getOptimalForce()
    rf = max(resid.get(p, 0.0) for p in ("pelvis_tx", "pelvis_ty", "pelvis_tz"))
    rm = max(resid.get(p, 0.0) for p in ("pelvis_tilt", "pelvis_list", "pelvis_rotation"))
    force_lim, moment_lim = 0.05 * peak, 0.01 * com_h * peak
    # tracking error against the filtered reference, at the solution's times
    tp = osim.TableProcessor(str(ik_path)); tp.append(osim.TabOpConvertDegreesToRadians())
    tp.append(osim.TabOpLowPassFilter(settings["filter_hz"])); tp.append(osim.TabOpUseAbsoluteStateNames())
    ref = tp.process(model)
    rt = np.array(ref.getIndependentColumn())
    errs = {}
    for lab in ref.getColumnLabels():
        if not lab.endswith("/value") or lab not in list(sol.getStateNames()):
            continue
        coord = lab.split("/")[-2]
        if coord in settings["untracked"]:
            continue
        r = np.interp(time_, rt, ref.getDependentColumn(lab).to_numpy())
        e = sol.getStateMat(lab) - r
        c = model.getCoordinateSet().get(coord)
        k = 1000.0 if c.getMotionType() == osim.Coordinate.Translational else math.degrees(1.0)
        errs[coord] = float(np.sqrt(np.mean(e ** 2))) * k
    rot = {c: v for c, v in errs.items() if c not in ("pelvis_tx", "pelvis_ty", "pelvis_tz")}
    trans = {c: v for c, v in errs.items() if c in ("pelvis_tx", "pelvis_ty", "pelvis_tz")}
    valid = bool(sol.success()) and rf <= force_lim and rm <= moment_lim
    return dict(valid=valid, peak_external_force_N=round(peak, 2), com_height_m=round(com_h, 4),
                pelvis_residual_force_max_N=round(rf, 3), pelvis_residual_moment_max_Nm=round(rm, 3),
                residual_force_limit_N=round(force_lim, 3), residual_moment_limit_Nm=round(moment_lim, 3),
                tracking_rms=dict(max_rotation_deg=round(max(rot.values()), 3), mean_rotation_deg=round(float(np.mean(list(rot.values()))), 3),
                                  max_translation_mm=round(max(trans.values()), 3) if trans else None,
                                  worst=max(rot, key=rot.get)),
                grf_columns=len(cols))


# ------------------------------------------------------------------------------------------------ batch
def _case(spec):
    """One solve as one case, in this process or a worker."""
    store = CS.CaseStore(spec["root"], resume=spec["resume"])
    fn = lambda d: track(spec["model"], spec["ik"], spec["key"]["window_s"], spec["key"]["settings"], d,
                         threads=spec["threads"], max_iterations=spec["max_iterations"],
                         strengths=spec["key"].get("torque_actuator_strengths_Nm"))
    result, rec, reused = store.run(spec["group"], spec["key"], fn)
    return spec["label"], result, rec, reused


def plan(subjects_dir, kin_root, out, arms=("A", "B"), only=None, max_iterations=None, threads=1, resume=True):
    import opensim
    versions = dict(python=platform.python_version(), opensim=opensim.__version__, numpy=np.__version__)
    code = {str(Path(f).relative_to(HERE.parent)): sha256(f) for f in CODE_FILES}
    specs = []
    for sdir in sorted(Path(subjects_dir).glob("subject*"), key=lambda p: int(p.name[7:])):
        s = sdir.name
        contacts = sdir / "LaiArnoldModified2017_poly_withArms_weldHand_scaled_contacts.osim"
        arm_a = Path(out) / "models" / s / "armA_sole.osim"
        chosen = [trial for trial in TRIALS if not only or f"{s}:{trial}" in only or s in only]
        if not chosen:
            continue
        iks = {trial: Path(kin_root) / s / "OpenSimData/Mocap/IK" / f"{trial}.mot" for trial in TRIALS}
        windows = {trial: squat_window(ik) for trial, ik in iks.items()}
        if "A" in arms and not arm_a.exists():
            build_arm_a(contacts, arm_a.parent)
        strengths = None
        if SETTINGS.get("torque_actuator_strength"):        # per subject, from all its trials, whatever is solved
            ts = torque_actuator_strengths([contacts] + ([arm_a] if arm_a.exists() else []),
                                           [(iks[t], windows[t][:2]) for t in TRIALS], SETTINGS)
            strengths = ts["strengths_Nm"]
            worst = max(c["max_change_Nm"] for c in ts["check"])
            print(f"{s}: torque actuators (Nm) {strengths}; peak inverse-dynamics torques (Nm) {ts['peak_Nm']}; "
                  f"largest change with contact forces on the feet {worst:.2g} Nm", flush=True)
        for trial in chosen:
            ik, w = iks[trial], windows[trial]
            for arm in arms:
                model = contacts if arm == "B" else arm_a
                key = dict(arm=arm, subject=s, trial=trial, model_sha256=sha256(model), ik_sha256=sha256(ik),
                           window_s=[round(w[0], 4), round(w[1], 4)], settings=dict(SETTINGS, version=SETTINGS_VERSION),
                           max_iterations=max_iterations, code_sha256=code, versions=versions)
                if strengths is not None:
                    key["torque_actuator_strengths_Nm"] = strengths
                specs.append(dict(root=str(Path(out) / "cases"), resume=resume, group=f"{s}_{trial}_{arm}", key=key,
                                  model=str(model), ik=str(ik), threads=threads, max_iterations=max_iterations,
                                  label=f"{s} {trial} arm {arm}"))
    return specs


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    w = sub.add_parser("window"); w.add_argument("ik", nargs="+")
    b = sub.add_parser("build"); b.add_argument("contacts_model"); b.add_argument("out_dir")
    r = sub.add_parser("batch")
    r.add_argument("--subjects-dir", required=True); r.add_argument("--kinematics", required=True); r.add_argument("-o", required=True)
    r.add_argument("--jobs", type=int, default=1); r.add_argument("--threads", type=int, default=1)
    r.add_argument("--only", nargs="*"); r.add_argument("--arms", nargs="*", default=["A", "B"])
    r.add_argument("--max-iterations", type=int); r.add_argument("--no-resume", action="store_true")
    a = ap.parse_args()
    if a.cmd == "window":
        for ik in a.ik:
            print(ik, squat_window(ik))
        return
    if a.cmd == "build":
        print(build_arm_a(a.contacts_model, a.out_dir)[0])
        return
    out = Path(a.o); out.mkdir(parents=True, exist_ok=True)
    specs = plan(a.subjects_dir, a.kinematics, out, a.arms, a.only, a.max_iterations, a.threads, not a.no_resume)
    print(f"{len(specs)} solves, {a.jobs} at a time, {a.threads} threads each", flush=True)
    rows = {}

    def show(label, res, rec, reused):
        rows[label] = dict(res, seconds=rec["seconds"], reused=reused)
        print(f"{time.strftime('%H:%M:%S')} {label}: converged={res['converged']} valid={res['valid']} iterations={res['iterations']} "
              f"{res['solve_seconds']} s, tracking max {res['tracking_rms']['max_rotation_deg']} deg, residual F {res['pelvis_residual_force_max_N']}/"
              f"{res['residual_force_limit_N']} N, M {res['pelvis_residual_moment_max_Nm']}/{res['residual_moment_limit_Nm']} Nm"
              f"{' (reused)' if reused else ''}", flush=True)
    if a.jobs <= 1:
        for spec in specs:
            show(*_case(spec))
    else:
        with ProcessPoolExecutor(max_workers=a.jobs, mp_context=get_context("spawn")) as pool:
            futs = {pool.submit(_case, spec): spec["label"] for spec in specs}
            for fut in as_completed(futs):
                try:
                    show(*fut.result())
                except Exception as e:                       # a failed case is reported, the others go on
                    rows[futs[fut]] = dict(error=f"{type(e).__name__}: {e}")
                    print(f"{time.strftime('%H:%M:%S')} {futs[fut]}: ERROR {type(e).__name__}: {e}", flush=True)
    (out / f"batch_{time.strftime('%Y%m%d-%H%M%S')}.json").write_text(json.dumps(rows, indent=1) + "\n")
    print("done", flush=True)


if __name__ == "__main__":
    main()
