#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors
# SPDX-License-Identifier: CERN-OHL-S-2.0
"""Phase 2 of the dynamic comparison (VALIDATION_PLAN.md, amendment 4): the solved squats of arms A and B against the
force plates. Written in phase 1, before any dynamic solution existed; run only after the owner's "go".

Definitions, fixed with this file:
  - Model forces: each foot's contact forces, summed (opensim.createExternalLoadsTableForGait gives each foot's force
    and its centre of pressure on the floor, with the torque set to zero; checked on a smoke solution, 2026-11-06).
    The combined centre of pressure is the force-weighted mean of the two feet's, as for the plates.
  - Measured: the right and left plates (R_ground_*, L_ground_*), as distributed, linearly interpolated to the
    solution's time points; combined force and centre of pressure as in forceplate_metrics.py.
  - Forward axis: the model's, at each time point, from the solved posture: the mean of both calcn x axes on the floor.
  - H1 (per trial): |peak combined vertical force, model - peak, measured| over the window, as % of body weight.
  - H2 (per trial): RMS over the window of the combined centre of pressure, measured - model, along the forward
    axis, as % of the subject's mean foot length (forceplate_frames_2026-11-06.json).
  - Per subject: the mean over the subject's evaluated trials. A trial is evaluated when its solution is valid
    and both plates carry at least 1 % of body weight on average over the window (the plate-coverage rule).
    Valid, since amendments 5 and 6 (2026-11-08): converged, pelvis residuals within Hicks et al. 2015's limits
    taken on the recorded body weight (amendment 6; amendment 4 took them on the solution's own peak external force),
    and tracking within the pilot gate's limits (dynamic_summary.validity, applied to every solve).
  - Pass (arm A only): every evaluated subject within its threshold (H1 10 % of body weight, H2 15 % of foot
    length). Subjects without an evaluated trial are reported as not evaluated; invalid solves are never passing.
  - The results state how many subjects and trials were evaluated per arm (amendment 5, item 4; counts()).
  - Body weight: the recorded mass times g (primary), as the residual limits take it (dynamic_summary.subject_mass_kg
    times dynamic_summary.G); secondary, the plates' weight from the post-hoc body-mass analysis
    (results_forceplate_posthoc_2026-11-06.json, plates over the kept frames).
  - Arm B, and A minus B, with the same metrics: description only. A minus B only on trials evaluated in both
    arms (amendment 5, item 5; paired()).
"""
import json
import math
from pathlib import Path

import numpy as np

import dynamic_summary as SM

THRESHOLDS = dict(h1_peak_vertical_pct_bw=10.0, h2_cop_forward_rms_pct_foot_length=15.0)


def evaluated(solutions, covered):
    """The evaluated trials of each arm: {arm: sorted [(subject, trial)]}. solutions: dynamic_summary rows with the
    current settings; covered: {(subject, trial): bool}, the plate-coverage rule over the window (phase 2). A
    trial is evaluated when its solution is valid (amendment 5, recomputed here) and covered; a trial missing from
    `covered` is not evaluated."""
    seen, out = set(), {"A": [], "B": []}
    for r in solutions:
        k = (r["subject"], r["trial"], r["arm"])
        if k in seen:
            raise ValueError(f"more than one solve of {k}")
        seen.add(k)
        if SM.validity(r)[0] and covered.get(k[:2], False):
            out[r["arm"]].append(k[:2])
    return {arm: sorted(v, key=lambda st: (int(st[0][7:]), st[1])) for arm, v in out.items()}


def counts(ev):
    """Amendment 5, item 4: how many subjects and trials were evaluated per arm."""
    return {arm: dict(trials=len(v), subjects=len({s for s, _ in v})) for arm, v in ev.items()}


def paired(ev):
    """Amendment 5, item 5: the trials A minus B is computed on, those evaluated in both arms."""
    return sorted(set(ev["A"]) & set(ev["B"]), key=lambda st: (int(st[0][7:]), st[1]))


def processed_model(model_path, settings=None):
    """The model as the solve used it (dynamic_track.track's ModelProcessor), from the solve's settings."""
    import opensim as osim
    if settings is None:
        import dynamic_track as DT
        settings = DT.SETTINGS
    mp = osim.ModelProcessor(str(model_path))
    mp.append(osim.ModOpIgnoreTendonCompliance()); mp.append(osim.ModOpReplaceMusclesWithDeGrooteFregly2016())
    mp.append(osim.ModOpIgnorePassiveFiberForcesDGF())
    mp.append(osim.ModOpScaleActiveFiberForceCurveWidthDGF(settings["active_force_width_scale"]))
    mp.append(osim.ModOpAddReserves(settings["reserve_optimal_force_Nm_or_N"]))
    model = mp.process(); model.initSystem()
    return model


def combined_cop(F_r, p_r, F_l, p_l):
    """Force-weighted centre of pressure (x, z) of two feet: forces n x 3, points n x 3."""
    w = F_r[:, 1] + F_l[:, 1]
    return np.column_stack([(F_r[:, 1] * p_r[:, i] + F_l[:, 1] * p_l[:, i]) / w for i in (0, 2)])


def trial_errors(t_model, F_model, cop_model, fwd, t_force, meas_cols, weight_N, foot_length_mm):
    """H1 and H2 of one trial. F_model: combined force (n x 3); cop_model (n x 2, m); fwd (n x 2, unit)."""
    at = lambda c: np.interp(t_model, t_force, meas_cols[c])
    rN, lN = at("R_ground_force_vy"), at("L_ground_force_vy")
    fm = rN + lN
    cop_m = np.column_stack([(rN * at(f"R_ground_force_p{a}") + lN * at(f"L_ground_force_p{a}")) / fm for a in "xz"])
    h1 = 100.0 * abs(float(F_model[:, 1].max()) - float(fm.max())) / weight_N
    d = np.sum((cop_m - cop_model) * fwd, axis=1)
    h2 = 100.0 * 1000.0 * float(np.sqrt(np.mean(d ** 2))) / foot_length_mm
    coverage = (100.0 * float(rN.mean()) / weight_N, 100.0 * float(lN.mean()) / weight_N)
    return dict(h1_peak_vertical_pct_bw=h1, h2_cop_forward_rms_pct_foot_length=h2, plate_coverage_pct_bw=coverage,
                peak_model_N=float(F_model[:, 1].max()), peak_measured_N=float(fm.max()))


def model_forces(model_path, solution_path):
    """(times, combined force n x 3, combined centre of pressure n x 2, forward axis n x 2) of a solution."""
    import opensim as osim
    import dynamic_track as DT
    model = processed_model(model_path)
    sol = osim.MocoTrajectory(str(solution_path))
    right, left = DT.contact_force_names(model_path)
    grf = osim.createExternalLoadsTableForGait(model, sol, right, left)
    col = lambda n: grf.getDependentColumn(n).to_numpy()
    Fs = {s: np.column_stack([col(f"ground_force_{s}_v{a}") for a in "xyz"]) for s in "rl"}
    Ps = {s: np.column_stack([col(f"ground_force_{s}_p{a}") for a in "xyz"]) for s in "rl"}
    traj = sol.exportToStatesTrajectory(model)
    fwd = []
    for i in range(traj.getSize()):
        st = traj.get(i); model.realizePosition(st)
        v = np.zeros(2)
        for s in "rl":
            R = model.getBodySet().get(f"calcn_{s}").getTransformInGround(st).R()
            v += [R.get(0, 0), R.get(2, 0)]
        fwd.append(v / np.linalg.norm(v))
    return np.array(sol.getTimeMat()), Fs["r"] + Fs["l"], combined_cop(Fs["r"], Ps["r"], Fs["l"], Ps["l"]), np.array(fwd)
