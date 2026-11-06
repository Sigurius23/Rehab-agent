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
Moco's examples), reserve actuators on every coordinate. The coupled patellar coordinates (knee_angle_*_beta) are
not tracked; they follow their constraints. Settings are in SETTINGS, versioned; a change is allowed only for
convergence and tracking error (amendment 4), applies to both arms, and is logged in
foot_models/dynamic_settings_log.json.

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

SETTINGS_VERSION = 1
SETTINGS = dict(
    filter_hz=6.0, mesh_interval_s=0.04, states_tracking_weight=10.0, control_effort_weight=1.0,
    reserve_optimal_force_Nm_or_N=1.0, active_force_width_scale=1.5,
    convergence_tolerance=1e-2, constraint_tolerance=1e-3, max_iterations=3000,
    transcription="hermite-simpson", untracked=("knee_angle_r_beta", "knee_angle_l_beta"))
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


# ------------------------------------------------------------------------------------------------ solve
def track(model_path, ik_path, window, settings, out_dir, threads=1, max_iterations=None):
    """One MocoTrack solve. Writes solution.sto and result.json in out_dir; returns the result."""
    import opensim as osim
    out_dir = Path(out_dir)
    osim.Logger.removeFileSink(); osim.Logger.addFileSink(str(out_dir / "opensim.log"))
    mp = osim.ModelProcessor(str(model_path))
    mp.append(osim.ModOpIgnoreTendonCompliance())
    mp.append(osim.ModOpReplaceMusclesWithDeGrooteFregly2016())
    mp.append(osim.ModOpIgnorePassiveFiberForcesDGF())
    mp.append(osim.ModOpScaleActiveFiberForceCurveWidthDGF(settings["active_force_width_scale"]))
    mp.append(osim.ModOpAddReserves(settings["reserve_optimal_force_Nm_or_N"]))
    tr = osim.MocoTrack()
    tr.setName("track")
    tr.setModel(mp)
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
    model = mp.process(); model.initSystem()
    for name in settings["untracked"]:
        if model.getCoordinateSet().contains(name):
            path = model.getCoordinateSet().get(name).getAbsolutePathString()
            weights.cloneAndAppend(osim.MocoWeight(path + "/value", 0.0))
            weights.cloneAndAppend(osim.MocoWeight(path + "/speed", 0.0))
    tr.set_states_weight_set(weights)
    study = tr.initialize()
    solver = osim.MocoCasADiSolver.safeDownCast(study.updSolver())
    solver.set_optim_convergence_tolerance(settings["convergence_tolerance"])
    solver.set_optim_constraint_tolerance(settings["constraint_tolerance"])
    solver.set_optim_max_iterations(int(max_iterations or settings["max_iterations"]))
    solver.set_transcription_scheme(settings["transcription"])
    solver.set_parallel(int(threads))
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
                         threads=spec["threads"], max_iterations=spec["max_iterations"])
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
        for trial in TRIALS:
            if only and f"{s}:{trial}" not in only and s not in only:
                continue
            ik = Path(kin_root) / s / "OpenSimData/Mocap/IK" / f"{trial}.mot"
            w = squat_window(ik)
            for arm in arms:
                model = contacts if arm == "B" else arm_a
                if arm == "A" and not model.exists():
                    build_arm_a(contacts, model.parent)
                key = dict(arm=arm, subject=s, trial=trial, model_sha256=sha256(model), ik_sha256=sha256(ik),
                           window_s=[round(w[0], 4), round(w[1], 4)], settings=dict(SETTINGS, version=SETTINGS_VERSION),
                           max_iterations=max_iterations, code_sha256=code, versions=versions)
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
