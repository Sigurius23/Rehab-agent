#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors
# SPDX-License-Identifier: CERN-OHL-S-2.0
"""Quasi-static double support in a full measured posture, for the force-plate check (VALIDATION_PLAN.md, stage A).
Experimental.

compare_feet.py's posture-based task mirrors the right side onto the left and puts each foot's centre of pressure
under the centre of mass, so it cannot say how load is split between the feet. Here:
  - the subject's model, without muscles or actuators, gets the virtual sole on both feet with one contact law
    (sole_sim.add_to_osim; by default the assumed contact v1), replacing the model's own foot contact;
  - every coordinate is set from the measured inverse kinematics, left and right as measured. Coupled coordinates
    follow their CoordinateCouplerConstraint; nothing is mirrored;
  - the posture is held, except for four unknowns solved together: the pelvis height, the pelvis list (the whole
    body's sideways roll on its two soles) and both ankle angles, each ankle with an unknown torque standing for the
    ankle muscles (as in compare_feet.py). The equations:
      - the contact forces carry the body weight;
      - sideways: zero moment about the centre of mass about the forward axis. The body rests rigidly on both soles,
        so the split between the feet follows from where the measured posture puts the centre of mass between them
        and from the contact law;
      - forward: each foot's centre of pressure lies under the centre of mass along the forward axis (the
        convention of compare_feet.py's posture-based task). The total centre of pressure is therefore under the
        centre of mass, as quasi-static balance requires, and the forward check tests the body model's centre of
        mass, not the contact law (VALIDATION_PLAN.md, stage A);
  - the forward axis is the mean of the two feet's long axes (calcn x) on the floor, at the measured posture.

Why not a rigid body tipping forwards too: on soft contact, a passive rigid body's forward-backward equilibrium is
close to neutrally stable, and its Jacobian becomes nearly singular as the solve approaches it (tested on the
self-test model: condition number from 40 to 6e5, the solve stalls). Sideways the two feet, about 0.2 m apart,
make the roll several times stiffer than gravity's tipping moment, so that equilibrium is well conditioned.

At rest the smooth contact model has no friction, so the horizontal position and heading do not matter and stay as
measured. Solved, not simulated: the equilibrium is found by damped Newton, and its stability is not claimed. The
Newton starts in stages (pelvis height for support, then the roll by a bracketed search, then all four unknowns): a
start with one foot barely touching otherwise ended on another root or in the air (found 2026-11-06 on OpenCap
LabValidation's kinematics alone).

Quasi-static frames (the plan's rule, kinematics only): frames where the whole-body centre of mass, computed from the
inverse kinematics with the subject's model, accelerates at less than 0.1 m/s^2, in stretches of at least 0.2 s. The
centre-of-mass positions are low-pass filtered at 6 Hz first. Choices within that rule, fixed here before any force
data is opened: a 4th-order zero-lag Butterworth filter (2nd order, forwards and backwards); acceleration by central
differences of the filtered positions; its magnitude is the norm of the 3-D vector; a stretch is a run of consecutive
qualifying frames, and its duration is the number of frames times the frame interval.

Phase 1 of the plan reads kinematics only. The readers here refuse files whose names look like force data.

  python foot_models/double_support.py frames MODEL.osim IK.mot [IK.mot ...] -o frames.json
  python foot_models/double_support.py solve MODEL.osim SOLE_R SOLE_L IK.mot [IK.mot ...] --frames frames.json \
      -o out/ [--jobs 8] [--no-resume]

The solve treats every frame as one case (foot_models/case_store.py): its folder is named from a fingerprint of the
model, soles, inverse kinematics, frame, contact law, code and tool versions, and it counts as done only when its
completion record is written. Running the same command again reuses finished frames and repeats interrupted ones.
--jobs N solves N frames at once, each worker process with its own copy of the model. Frames are independent: each
starts from the measured posture, so the result does not depend on the order or the worker.
"""
import argparse
import hashlib
import json
import math
import os
import platform
import re
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
import compare_feet as CF  # noqa: E402
import sole_sim as SS  # noqa: E402

STATUS = (SS.STATUS + "; quasi-static double support in the measured posture (pelvis height and list and both ankle "
          "angles solved, ankle torques standing for the ankle muscles); passive below the ankles")
UNKNOWNS = ("pelvis_ty", "pelvis_list", "ankle_angle_r", "ankle_angle_l")
QUASI_STATIC_RULE = dict(cutoff_hz=6.0, filter="Butterworth, 4th order zero-lag (2nd order forwards and backwards)",
                         max_acceleration_m_s2=0.1, acceleration="norm of the 3-D centre-of-mass acceleration, "
                         "central differences of the filtered positions", min_stretch_s=0.2)
# Files whose content decides a frame's result. A change to any of them invalidates every stored frame.
CODE_FILES = (HERE / "double_support.py", HERE / "compare_feet.py", HERE.parent / "sole_sim.py")
FORCE_NAME = re.compile(r"(grf|force|forceplate|force_plate|forcedata|analog|\.anc$|emg)", re.IGNORECASE)


def refuse_force_file(path):
    """Phase 1 reads kinematics only: stop on any file whose name or folder looks like force or analog data."""
    parts = Path(path).parts[-3:]
    if any(FORCE_NAME.search(p) for p in parts):
        raise PermissionError(f"{path}: looks like force or analog data; phase 1 reads kinematics only")


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_mot(path):
    """An OpenSim .mot/.sto of coordinates: (times, column names, values, in_degrees). Kinematics only."""
    refuse_force_file(path)
    lines = Path(path).read_text().splitlines()
    end = next(k for k, ln in enumerate(lines) if ln.strip().lower() == "endheader")
    in_degrees = any(ln.replace(" ", "").lower() == "indegrees=yes" for ln in lines[:end])
    head = lines[end + 1].split("\t")
    data = np.array([[float(v) for v in ln.split("\t")] for ln in lines[end + 2:] if ln.strip()])
    if head[0].strip().lower() != "time":
        raise ValueError(f"{path}: first column is {head[0]!r}, not time")
    return data[:, 0], [h.strip() for h in head[1:]], data[:, 1:], in_degrees


# ------------------------------------------------------------------------------------------------ posture
class Posture:
    """Applies measured coordinates to a model's state: rotational values converted from degrees if the file is in
    degrees, coupled coordinates from their couplers, and every adaptation recorded."""

    def __init__(self, model, names, in_degrees):
        import opensim as osim
        cs = model.getCoordinateSet()
        self.model, self.cs = model, cs
        self.couplers = []
        for c in model.getConstraintSet():
            cc = osim.CoordinateCouplerConstraint.safeDownCast(c)
            if cc:
                ind = cc.getIndependentCoordinateNames()
                self.couplers.append((cc.getDependentCoordinateName(), [ind.get(i) for i in range(ind.getSize())],
                                      cc.getFunction(), float(cc.getPropertyByName("scale_factor").toString())))
            else:
                raise SS.UnsupportedModel(f"constraint {c.getName()} ({c.getConcreteClassName()}) is not a coordinate "
                                          f"coupler: this posture code handles couplers only")
        dependent = {d for d, *_ in self.couplers}
        self.columns = []                                          # (column index, coordinate, factor)
        for k, n in enumerate(names):
            if cs.contains(n) and n not in dependent:
                c = cs.get(n)
                rot = c.getMotionType() == osim.Coordinate.Rotational
                self.columns.append((k, c, math.radians(1.0) if (rot and in_degrees) else 1.0))
        given = {c.getName() for _, c, _ in self.columns}
        self.not_in_model = [n for n in names if not cs.contains(n)]
        self.not_in_data = [c.getName() for c in cs if c.getName() not in given and c.getName() not in dependent]
        self.dependent_from_couplers = sorted(dependent)

    def apply(self, state, row):
        """Set every coordinate from one row; returns the coordinates outside the model's range (names)."""
        import opensim as osim
        outside = []
        for k, c, f in self.columns:
            v = float(row[k]) * f
            c.setValue(state, v, False)
            if not (c.getRangeMin() - 1e-9 <= v <= c.getRangeMax() + 1e-9):
                outside.append(c.getName())
        for dep, ind, fn, scale in self.couplers:
            x = osim.Vector(len(ind), 0.0)
            for i, n in enumerate(ind):
                x.set(i, self.cs.get(n).getValue(state))
            self.cs.get(dep).setValue(state, scale * fn.calcValue(x), False)
        for c in self.cs:
            c.setSpeedValue(state, 0.0)
        return outside


def com_trajectory(model_path, mot_path):
    """Whole-body centre of mass (m, ground) at every frame of the inverse kinematics, with the model as given."""
    import opensim as osim
    t, names, data, deg = load_mot(mot_path)
    m = osim.Model(str(model_path))
    st = m.initSystem()
    p = Posture(m, names, deg)
    com = np.empty((len(t), 3))
    for i, row in enumerate(data):
        p.apply(st, row)
        m.realizePosition(st)
        c = m.calcMassCenterPosition(st)
        com[i] = [c.get(0), c.get(1), c.get(2)]
    return t, com, dict(not_in_model=p.not_in_model, not_in_data=p.not_in_data,
                        dependent_from_couplers=p.dependent_from_couplers)


def quasi_static(t, com, cutoff_hz=6.0, max_acc=0.1, min_stretch_s=0.2):
    """The plan's quasi-static frames (see the module docstring). Returns (mask, stretches [(start s, end s, n)],
    acceleration magnitude per frame)."""
    from scipy.signal import butter, filtfilt
    t = np.asarray(t, float); com = np.asarray(com, float)
    dt = float(np.median(np.diff(t)))
    if np.max(np.abs(np.diff(t) - dt)) > 0.01 * dt:
        raise ValueError("frames are not evenly spaced: cannot filter")
    b, a = butter(2, cutoff_hz / (0.5 / dt))
    pos = filtfilt(b, a, com, axis=0)
    acc = np.gradient(np.gradient(pos, dt, axis=0), dt, axis=0)
    mag = np.linalg.norm(acc, axis=1)
    ok = mag < max_acc
    mask = np.zeros(len(t), bool)
    stretches, i = [], 0
    while i < len(t):
        if ok[i]:
            j = i
            while j + 1 < len(t) and ok[j + 1]:
                j += 1
            n = j - i + 1
            if n * dt >= min_stretch_s - 1e-9:
                mask[i:j + 1] = True
                stretches.append((float(t[i]), float(t[j]), n))
            i = j + 1
        else:
            i += 1
    return mask, stretches, mag


# ------------------------------------------------------------------------------------------- equilibrium
class DoubleSupport:
    """The subject's model with the sole on both feet, ready to solve quasi-static double support per frame."""

    def __init__(self, model_in, sole_r, sole_l, work_dir, contact=SS.ASSUMED_CONTACT_V1, radius_mm=None):
        import opensim as osim
        work = Path(work_dir); work.mkdir(parents=True, exist_ok=True)
        stripped, with_r, with_both = work / "stripped.osim", work / "with_R.osim", work / "with_soles.osim"
        self.removed = CF.strip_model(model_in, stripped)
        self.meta = {"R": SS.add_to_osim(stripped, sole_r, with_r, radius_mm=radius_mm, contact=contact)}
        self.meta["L"] = SS.add_to_osim(with_r, sole_l, with_both, radius_mm=radius_mm, contact=contact)
        self.soles = {"R": json.loads(Path(sole_r).read_text()), "L": json.loads(Path(sole_l).read_text())}
        m = osim.Model(str(with_both))
        for c in m.getCoordinateSet():
            c.set_clamped(False)                       # measured values are applied as measured, and flagged
        self.m, self.st = m, m.initSystem()
        self.cs = m.getCoordinateSet()
        for n in UNKNOWNS:
            if not self.cs.contains(n):
                raise SS.UnsupportedModel(f"the model has no coordinate {n}: this double-support solve needs a free "
                                          f"pelvis and one ankle angle per side")
        self.weight = m.getTotalMass(self.st) * math.sqrt(sum(m.getGravity().get(i) ** 2 for i in range(3)))
        self.contacts = []                             # (force, sphere, radius, index of Sphere.force.X, side)
        for fo in m.getForceSet():
            if fo.getConcreteClassName() != "SmoothSphereHalfSpaceForce":
                continue
            ss = osim.SmoothSphereHalfSpaceForce.safeDownCast(fo)
            sp = osim.ContactSphere.safeDownCast(ss.getConnectee("sphere"))
            lab = fo.getRecordLabels()
            ix = next(i for i in range(lab.size()) if lab.get(i).endswith(".Sphere.force.X"))
            side = fo.getName()[len("force_sole_")].upper() if fo.getName().startswith("force_sole_") else None
            self.contacts.append((fo, sp, sp.getRadius(), ix, side))
        self.other_contacts = [fo.getName() for fo, *_, side in self.contacts if side is None]
        self.model_path, self.source_model = with_both, str(model_in)

    def _points(self):
        """Lowest point (m, ground) of every contact sphere and its side; needs the state realized to Position."""
        P, side = [], []
        for fo, sp, r, ix, s in self.contacts:
            c = sp.getFrame().findStationLocationInGround(self.st, sp.get_location())
            P.append([c.get(0), c.get(1) - r, c.get(2)])
            side.append(s)
        return np.array(P), np.array(side)

    def _contact(self):
        """Contact force (N) and contact point (m) of every sphere, in ground; needs the state realized to Dynamics."""
        F = []
        for fo, sp, r, ix, s in self.contacts:
            v = fo.getRecordValues(self.st)
            F.append([v.get(ix), v.get(ix + 1), v.get(ix + 2)])
        P, side = self._points()
        return np.array(F), P, side

    def _start(self, coords, x, fwd, ks, lo, hi):
        """Starting point for the solve, by geometry only: each sole levelled forwards with its ankle, the two soles
        levelled against each other with the pelvis list, then the body lowered until the lowest point is 3 mm into
        the floor. Without it, a foot that IK puts a little higher starts off the floor and the solve can end on one
        foot. The equations and their solutions are unchanged; the solve may still end anywhere within its bounds."""
        m, st = self.m, self.st

        def tilts(x):
            for c, v in zip(coords, x):
                c.setValue(st, float(v), False)
            m.realizePosition(st)
            P, _ = self._points()
            out = []
            for s in "RL":                                      # forward slope of each sole's lowest points
                Q = P[ks[s]]
                u = Q[:, [0, 2]] @ fwd[[0, 2]]
                out.append(np.polyfit(u, Q[:, 1], 1)[0])
            hR, hL = (np.mean(P[ks[s]][:, 1]) for s in "RL")
            return np.array(out + [hR - hL]), P
        for _ in range(4):
            g, _ = tilts(x)
            if np.abs(g).max() < 1e-5:
                break
            J = np.empty((3, 3)); idx = [2, 3, 1]               # ankle_r, ankle_l, list
            for j, k in enumerate(idx):
                e = np.zeros(4); e[k] = 1e-4
                J[:, j] = (tilts(x + e)[0] - g) / 1e-4
            step = np.linalg.lstsq(J, -g, rcond=None)[0]
            x = x.copy(); x[idx] += step
            x = np.clip(x, lo, hi)
        _, P = tilts(x)
        x = x.copy(); x[0] -= P[:, 1].min() + 0.003
        return x

    def solve(self, posture, row, tol=1e-6):
        """Quasi-static double support at one measured frame (see the module docstring)."""
        m, st, cs = self.m, self.st, self.cs
        outside = posture.apply(st, row)
        measured = [cs.get(n).getValue(st) for n in UNKNOWNS]
        m.realizePosition(st)
        P, side = self._points()
        low = {s: float(P[side == s][:, 1].min()) for s in "RL"}
        fwd = np.zeros(3)
        for s in "rl":                                   # the forward axis: the feet's long axes on the floor
            R = m.getBodySet().get(f"calcn_{s}").getTransformInGround(st).R()
            fwd += [R.get(0, 0), 0.0, R.get(2, 0)]
        fwd /= np.linalg.norm(fwd)
        coords = [cs.get(n) for n in UNKNOWNS]
        ks = {s: side == s for s in "RL"}
        width = np.array([0.0, 0.1, 0.35, 0.35])
        lo, hi = np.array(measured) - width, np.array(measured) + width
        x0 = self._start(coords, np.array(measured, float), fwd, ks, lo, hi)
        lo[0], hi[0] = x0[0] - 0.05, x0[0] + 0.05

        def resid(x):
            for c, v in zip(coords, x):
                c.setValue(st, float(v), False)
            m.realizeDynamics(st)
            com = m.calcMassCenterPosition(st)
            com = np.array([com.get(0), com.get(1), com.get(2)])
            F, P, _ = self._contact()
            M = np.cross(P - com, F).sum(axis=0)              # about the centre of mass; gravity adds none
            ahead = (P - com) @ fwd                            # each contact point's distance ahead of the centre of mass
            return np.array([(F[:, 1].sum() - self.weight) / self.weight,      # support
                             (M @ fwd) / (0.1 * self.weight),                  # sideways roll balanced
                             (F[ks["R"], 1] @ ahead[ks["R"]]) / (0.1 * self.weight),   # each foot's centre of pressure
                             (F[ks["L"], 1] @ ahead[ks["L"]]) / (0.1 * self.weight)])  # under the centre of mass

        h = np.array([1e-7, 1e-6, 1e-6, 1e-6])

        def newton(x, active, max_iter):
            """Damped Newton on the equations and unknowns listed in `active` (the others held)."""
            a = np.array(active)
            r = resid(x); calls = 1
            for k in range(max_iter):
                if np.abs(r[a]).max() < tol:
                    return x, r, k, calls
                J = np.empty((len(a), len(a)))
                for j, u in enumerate(a):
                    J[:, j] = (resid(x + np.eye(len(x))[u] * h[u])[a] - r[a]) / h[u]
                calls += len(a)
                dx = np.zeros(len(x)); dx[a] = -np.linalg.lstsq(J, r[a], rcond=None)[0]
                step = 1.0
                while step > 1e-6:
                    xn = np.clip(x + step * dx, lo, hi)
                    rn = resid(xn); calls += 1
                    if np.linalg.norm(rn[a]) < np.linalg.norm(r[a]):
                        break
                    step /= 2
                if step <= 1e-6:
                    return x, r, k, calls
                x, r = xn, rn
            return x, r, max_iter, calls

        # Staged start (2026-11-06, found on OpenCap LabValidation's kinematics alone): from the levelled start only
        # a few spheres may touch, and the full Newton could then end on another root (one foot on its toe tip, the
        # roll at its bound) or lift the body off the floor (which also zeroes the roll moment). So:
        #   1. the body is lowered until the soles carry the weight (pelvis height alone);
        #   2. the roll is balanced by a bracketed one-dimensional search over the list, between its bounds, with the
        #      height re-solved for support at each list (rolling to one side loads that foot, so the roll moment
        #      changes sign across the bracket);
        #   3. all four unknowns are solved together from there.
        # Only the path to the solution changes; the equations, unknowns and bounds do not.
        from scipy.optimize import brentq
        it = nfev = 0

        def supported(xi):
            nonlocal it, nfev
            xi, _, k, calls = newton(xi, (0,), 50)
            it += k; nfev += calls
            return xi

        x = supported(x0.copy())
        at = {}

        def roll(v):
            nonlocal nfev
            xi = x.copy(); xi[1] = v
            at[v] = supported(xi); nfev += 1
            return resid(at[v])[1]
        if roll(lo[1]) * roll(hi[1]) < 0:
            v = brentq(roll, lo[1], hi[1], xtol=1e-9)
            roll(v)
            x = at[v]
        x, r, k, calls = newton(x, (0, 1, 2, 3), 100)
        it += k; nfev += calls
        r = resid(x)
        F, P, side = self._contact()
        com = m.calcMassCenterPosition(st)
        com = [com.get(0), com.get(1), com.get(2)]
        labels, data, _ = CF._sole_forces(m, st)
        feet, total = {}, 0.0
        for s in "RL":
            k = side == s
            fy = float(F[k, 1].sum())
            cop = (F[k, 1] @ P[k][:, [0, 2]]) / fy if fy > 0 else np.array([np.nan, np.nan])
            c_sole, _ = SS.sphere_centre_of_pressure(labels, data, self.soles[s])
            feet[s] = dict(vertical_N=round(fy, 3), cop_ground_m=[round(float(v), 5) for v in cop],
                           cop_sole_mm=[round(float(v), 2) for v in c_sole[0]],
                           spheres_loaded=int((F[k, 1] > 1e-3 * self.weight / k.sum()).sum()),
                           lowest_point_before_solve_mm=round(1000 * low[s], 2))
            total += fy
            feet[s]["cop_ahead_of_com_mm"] = (round(1000 * float((np.append(cop, 0)[[0, 2, 1]] - com) @ fwd), 3)
                                              if fy > 0 else None)
        converged = bool(np.abs(r).max() < 1e-4)
        at_bounds = [u for u, v, a, b in zip(UNKNOWNS, x, lo, hi) if min(v - a, b - v) < 1e-9]
        delta = {"pelvis_ty_mm": round(1000 * (x[0] - measured[0]), 3)}
        delta.update({f"{u}_deg": round(math.degrees(v - w), 4) for u, v, w in zip(UNKNOWNS[1:], x[1:], measured[1:])})
        out = dict(body_weight_N=round(self.weight, 3), total_vertical_N=round(total, 3),
                   support_error_pct=round(100 * (total - self.weight) / self.weight, 4),
                   right_share_pct=round(100 * feet["R"]["vertical_N"] / total, 3) if total > 0 else None,
                   R=feet["R"], L=feet["L"], com_ground_m=[round(v, 5) for v in com],
                   forward_axis=[round(float(fwd[0]), 5), round(float(fwd[2]), 5)],
                   horizontal_contact_force_N=[round(float(F[:, 0].sum()), 4), round(float(F[:, 2].sum()), 4)],
                   solved_minus_measured=delta,
                   solver=dict(converged=converged, iterations=it, nfev=nfev, max_abs_residual=float(np.abs(r).max())),
                   at_bounds=at_bounds, outside_model_range=outside)
        out["solved"] = bool(converged and not at_bounds and abs(out["support_error_pct"]) < 0.5
                             and all(feet[s]["vertical_N"] > 0 for s in "RL"))
        return out

    def describe(self):
        return dict(status=STATUS, source_model=self.source_model, removed_forces=self.removed,
                    other_contact_forces=self.other_contacts, body_weight_N=round(self.weight, 3),
                    contact_model=self.meta["R"]["contact_model"], stiffness_per_sphere=self.meta["R"]["stiffness_per_sphere"],
                    soles={s: dict(board_id=self.soles[s]["board_id"], spacing_mm=self.soles[s]["point_spacing_mm"],
                                   scale=self.meta[s]["scale"], warning=self.meta[s]["warning"],
                                   spheres=self.meta[s]["spheres"], spheres_per_body=self.meta[s]["spheres_per_body"])
                           for s in "RL"})


# ------------------------------------------------------------------------------------------------- CLI
def cmd_frames(a):
    out = dict(rule=QUASI_STATIC_RULE, model=Path(a.model).name, model_sha256=sha256(a.model), trials={})
    for mot in a.ik:
        t, com, info = com_trajectory(a.model, mot)
        mask, stretches, mag = quasi_static(t, com)
        out["trials"][Path(mot).name] = dict(ik_sha256=sha256(mot), frames=int(len(t)), quasi_static_frames=int(mask.sum()),
                                             frame_interval_s=round(float(np.median(np.diff(t))), 6),
                                             stretches_s=[[round(s, 4), round(e, 4), n] for s, e, n in stretches],
                                             posture=info)
    Path(a.o).write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: (v["frames"], v["quasi_static_frames"]) for k, v in out["trials"].items()}))


_CACHE = {}          # per process: the models built and the inverse kinematics read, reused across frames


def _built(model, sole_r, sole_l, work_root):
    k = ("model", model, sole_r, sole_l)
    if k not in _CACHE:
        _CACHE[k] = DoubleSupport(model, sole_r, sole_l, Path(work_root) / f"model-{os.getpid()}")
    return _CACHE[k]


def _read_ik(ds, path):
    k = ("ik", id(ds), path)
    if k not in _CACHE:
        t, names, data, deg = load_mot(path)
        _CACHE[k] = (t, data, Posture(ds.m, names, deg))
    return _CACHE[k]


def solve_frame(spec):
    """One frame as one case, in this process or a worker. Returns (trial, frame index, result, seconds, reused)."""
    def fn(d):
        ds = _built(spec["model"], spec["sole_r"], spec["sole_l"], spec["work"])
        t, data, posture = _read_ik(ds, spec["ik"])
        i = spec["key"]["frame"]
        r = ds.solve(posture, data[i], tol=spec["key"]["tol"])
        r["time"] = round(float(t[i]), 4)
        (d / "result.json").write_text(json.dumps(r, indent=1) + "\n")
    result, rec, reused = CS.CaseStore(spec["root"], resume=spec["resume"]).run(spec["group"], spec["key"], fn)
    return spec["trial"], spec["key"]["frame"], result, rec["seconds"], reused


def log_opensim_to(path):
    """This process's OpenSim log to `path` (as run_comparison.py does; one file per process)."""
    import opensim
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    opensim.Logger.removeFileSink()
    opensim.Logger.addFileSink(str(path))


def _worker_start(log_dir):
    log_opensim_to(Path(log_dir) / f"worker-{os.getpid()}.log")


def run_solve(model, sole_r, sole_l, iks, frames_file, out, jobs=1, resume=True, contact=SS.ASSUMED_CONTACT_V1, tol=1e-6):
    """Solve every selected frame of every trial; writes out/double_support.json and returns it."""
    import opensim
    import scipy
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    log_dir = out / "opensim_logs" / f"{time.strftime('%Y%m%d-%H%M%S')}-{os.getpid()}"
    log_opensim_to(log_dir / "main.log")
    model, sole_r, sole_l = str(model), str(sole_r), str(sole_l)
    work = out / "work"
    ds = DoubleSupport(model, sole_r, sole_l, work / "main", contact=contact)    # refuses an unsupported model here
    _CACHE[("model", model, sole_r, sole_l)] = ds
    sel = json.loads(Path(frames_file).read_text())
    versions = dict(python=platform.python_version(), opensim=opensim.__version__, numpy=np.__version__,
                    scipy=scipy.__version__)
    common = dict(model_sha256=sha256(model), sole_r_sha256=sha256(sole_r), sole_l_sha256=sha256(sole_l),
                  contact=contact, unknowns=list(UNKNOWNS), tol=tol, versions=versions,
                  code_sha256={str(Path(f).relative_to(HERE.parent)): sha256(f) for f in CODE_FILES})
    specs, trials = [], {}
    for ik in map(str, iks):
        name, ik_sha = Path(ik).name, sha256(ik)
        chosen = sel["trials"][name]
        if chosen["ik_sha256"] != ik_sha:
            raise ValueError(f"{ik}: not the inverse kinematics the frames were selected from (sha256 differs)")
        t, _, _ = _read_ik(ds, ik)
        keep = [i for i, ti in enumerate(t) if any(s - 1e-9 <= ti <= e + 1e-9 for s, e, _ in chosen["stretches_s"])]
        trials[name] = dict(ik=name, ik_sha256=ik_sha, frames={})
        for i in keep:
            specs.append(dict(root=str(out / "cases"), resume=resume, group=Path(ik).stem, trial=name, model=model,
                              sole_r=sole_r, sole_l=sole_l, work=str(work), ik=ik,
                              key=dict(common, ik_sha256=ik_sha, frame=i, time=round(float(t[i]), 6))))
    t0, reused, seconds = time.time(), 0, 0.0

    def collect(trial, i, result, sec, was_reused):
        nonlocal reused, seconds
        trials[trial]["frames"][i] = result
        reused += was_reused
        seconds += sec
    if jobs <= 1 or not specs:
        for spec in specs:
            collect(*solve_frame(spec))
    else:
        # spawn: each worker starts its own interpreter and OpenSim; fork after OpenSim has loaded is not safe
        with ProcessPoolExecutor(max_workers=jobs, mp_context=get_context("spawn"), initializer=_worker_start,
                                 initargs=(str(log_dir),)) as pool:
            for fut in as_completed([pool.submit(solve_frame, spec) for spec in specs]):
                collect(*fut.result())
        for f in log_dir.glob("worker-*.log"):          # drop the logs of workers that said nothing
            if f.stat().st_size == 0:
                f.unlink()
    for tr in trials.values():
        tr["frames"] = [tr["frames"][i] for i in sorted(tr["frames"])]
        tr["solved"] = sum(r["solved"] for r in tr["frames"])
    res = dict(ds.describe(), frames_file_sha256=sha256(frames_file), trials=trials,
               run=dict(frames=len(specs), reused_from_earlier_run=reused, computed=len(specs) - reused, jobs=jobs,
                        wall_seconds=round(time.time() - t0, 1), case_seconds=round(seconds, 1),
                        case_folders="cases/<trial>/<fingerprint>, as in foot_models/case_store.py",
                        opensim_logs=str(log_dir.relative_to(out))))
    (out / "double_support.json").write_text(json.dumps(res, indent=1) + "\n")
    return res


def cmd_solve(a):
    res = run_solve(a.model, a.sole_r, a.sole_l, a.ik, a.frames, a.o, jobs=a.jobs, resume=not a.no_resume)
    for name, tr in res["trials"].items():
        print(f"{name}: {len(tr['frames'])} frames, {tr['solved']} solved")
    r = res["run"]
    print(f"done: {r['computed']} computed, {r['reused_from_earlier_run']} reused, {r['wall_seconds']} s")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("frames"); f.add_argument("model"); f.add_argument("ik", nargs="+"); f.add_argument("-o", required=True)
    s = sub.add_parser("solve"); s.add_argument("model"); s.add_argument("sole_r"); s.add_argument("sole_l")
    s.add_argument("ik", nargs="+"); s.add_argument("--frames", required=True); s.add_argument("-o", required=True)
    s.add_argument("--jobs", type=int, default=1, help="frames solved at once, each in its own process (default 1)")
    s.add_argument("--no-resume", action="store_true", help="recompute every frame, even finished ones")
    a = ap.parse_args()
    {"frames": cmd_frames, "solve": cmd_solve}[a.cmd](a)


if __name__ == "__main__":
    main()
