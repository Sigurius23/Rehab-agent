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
    (converged, pelvis residuals within Hicks et al. 2015) and both plates carry at least 1 % of body weight on
    average over the window (the plate-coverage rule).
  - Pass (arm A only): every evaluated subject within its threshold (H1 10 % of body weight, H2 15 % of foot
    length). Subjects without an evaluated trial are reported as not evaluated.
  - Body weight: the recorded mass times g (primary); secondary, the plates' weight from the post-hoc body-mass
    analysis (results_forceplate_posthoc_2026-11-06.json, plates over the kept frames).
  - Arm B, and A minus B, with the same metrics: description only.
"""
import json
import math
from pathlib import Path

import numpy as np

THRESHOLDS = dict(h1_peak_vertical_pct_bw=10.0, h2_cop_forward_rms_pct_foot_length=15.0)


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
    mp = osim.ModelProcessor(str(model_path))
    mp.append(osim.ModOpIgnoreTendonCompliance()); mp.append(osim.ModOpReplaceMusclesWithDeGrooteFregly2016())
    mp.append(osim.ModOpIgnorePassiveFiberForcesDGF())
    mp.append(osim.ModOpScaleActiveFiberForceCurveWidthDGF(DT.SETTINGS["active_force_width_scale"]))
    mp.append(osim.ModOpAddReserves(DT.SETTINGS["reserve_optimal_force_Nm_or_N"]))
    model = mp.process(); model.initSystem()
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
