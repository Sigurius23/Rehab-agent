#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors
# SPDX-License-Identifier: CERN-OHL-S-2.0
"""Checks of the dynamic comparison's kinematics-only window rule (foot_models/dynamic_track.py) and of its phase-2
metric functions (foot_models/dynamic_metrics.py) on synthetic data, written before any dynamic solution existed:
  - the window is the first squat repetition with standing on both sides; a trial that starts mid-descent skips to
    the next repetition; a trial with no complete repetition is refused;
  - the combined centre of pressure is force-weighted; H1 is the peak error as % of body weight; H2 is the forward
    RMS of the centre-of-pressure error as % of foot length, blind to sideways offsets;
  - the pilot gate (added with settings v2, 2026-11-08) needs both arms converged and tracking within the gate, with
    the current settings only; the settings log's last entry matches the code;
  - amendment 5 (2026-11-08): validity needs convergence, Hicks residuals and the gate's tracking limits, on every
    solve, so the flying v1 arm-B pilot solution is invalid; the contact penetration figure; evaluated counts per
    arm and A minus B only on trials evaluated in both;
  - amendment 6 (2026-11-08): the residual limits are taken on the recorded body weight, not on the solution's own
    peak external force, so the v1 arm-A pilot solution (limit 3.5 MN) fails them; the recorded mass is read and
    checked; the summary reports both limits; the pilot gate does not need the body weight;
  - settings v3 (2026-11-09), on the subject models when they are present: the trunk and arm actuators' strengths are
    their peak inverse-dynamics torques rounded up to 10 Nm, the same for both arms, and only from torques that do not
    depend on ground forces (a contact sphere on the trunk is refused; contact forces on the feet change no such
    torque); the solve's model refuses to be built without them; the initial guess's pelvis offset puts each arm at
    its own contact balance.
"""
import hashlib
import json
import math
import os
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "foot_models"))
import dynamic_summary as SM  # noqa: E402  (no OpenSim needed)
try:
    import numpy as np
    import scipy  # noqa: F401
    import dynamic_track as DT
    import dynamic_metrics as DM
    HAVE = True
except ImportError:
    HAVE = False
try:
    import opensim as osim
    osim.Logger.setLevelString("error")
    HAVE_OSIM = HAVE
except ImportError:
    HAVE_OSIM = False


def ik_file(d, ty, dt=0.01):
    p = Path(d) / "squats1.mot"
    rows = "".join(f"{i * dt:.4f}\t{v:.6f}\t0.0\n" for i, v in enumerate(ty))
    p.write_text(f"Coordinates\nversion=1\nnRows={len(ty)}\nnColumns=3\ninDegrees=yes\nendheader\ntime\tpelvis_ty\tknee_angle_r\n" + rows)
    return p


def squats(t, start_phase=0.0, n=3, period=2.5, depth=0.35, stand=0.5):
    """Pelvis height: standing 0.95 m, then n squats (cosine dips) separated by standing pauses."""
    y = np.full_like(t, 0.95)
    for k in range(n):
        a = stand + k * (period + stand) - start_phase
        m = (t >= a) & (t < a + period)
        y[m] = 0.95 - depth * 0.5 * (1 - np.cos(2 * math.pi * (t[m] - a) / period))
    return y


@unittest.skipUnless(HAVE, "needs the pipeline's Python")
class SquatWindow(unittest.TestCase):
    def test_first_complete_repetition(self):
        t = np.arange(0, 10, 0.01)
        with tempfile.TemporaryDirectory() as d:
            s, e, tr, info = DT.squat_window(ik_file(d, squats(t)))
        self.assertAlmostEqual(tr, 0.5 + 1.25, delta=0.02)               # the first trough
        self.assertTrue(0.4 < s < 1.0 and 2.5 < e < 3.1, (s, e))
        self.assertEqual(info["repetition"], 1)

    def test_a_trial_that_starts_mid_descent_uses_the_next_repetition(self):
        t = np.arange(0, 10, 0.01)
        with tempfile.TemporaryDirectory() as d:
            s, e, tr, info = DT.squat_window(ik_file(d, squats(t, start_phase=1.0)))
        self.assertEqual(info["repetition"], 2)
        self.assertGreater(s, tr - 1.25 - 0.3)

    def test_no_complete_repetition_is_refused(self):
        t = np.arange(0, 3, 0.01)
        y = 0.95 - 0.35 * 0.5 * (1 - np.cos(2 * math.pi * (t + 0.6) / 2.5))   # starts and ends inside one squat
        with tempfile.TemporaryDirectory() as d, self.assertRaises(ValueError):
            DT.squat_window(ik_file(d, y))


@unittest.skipUnless(HAVE, "needs the pipeline's Python")
class Metrics(unittest.TestCase):
    def test_combined_cop_is_force_weighted(self):
        F_r = np.array([[0, 300.0, 0]]); F_l = np.array([[0, 100.0, 0]])
        p_r = np.array([[0.20, 0, 0.10]]); p_l = np.array([[0.00, 0, -0.10]])
        np.testing.assert_allclose(DM.combined_cop(F_r, p_r, F_l, p_l), [[0.15, 0.05]])

    def test_h1_and_h2(self):
        t = np.linspace(0, 1, 11)
        F = np.column_stack([0 * t, 700 + 70 * np.sin(math.pi * t), 0 * t])       # model peak 770 N
        cop = np.column_stack([0.1 + 0 * t, 0 * t])
        fwd = np.tile([1.0, 0.0], (len(t), 1))
        tf = np.linspace(0, 1, 2001)
        cols = {"R_ground_force_vy": 350 + 0 * tf, "L_ground_force_vy": 350 + 0 * tf,           # measured 700 N throughout
                "R_ground_force_px": 0.125 + 0 * tf, "L_ground_force_px": 0.125 + 0 * tf,        # 25 mm ahead
                "R_ground_force_pz": 0.2 + 0 * tf, "L_ground_force_pz": -0.2 + 0 * tf}           # sideways: ignored
        e = DM.trial_errors(t, F, cop, fwd, tf, cols, 700.0, 250.0)
        self.assertAlmostEqual(e["h1_peak_vertical_pct_bw"], 10.0, places=6)
        self.assertAlmostEqual(e["h2_cop_forward_rms_pct_foot_length"], 10.0, places=6)
        self.assertEqual(e["plate_coverage_pct_bw"], (50.0, 50.0))


MASSES = {"subject1": 70.0, "subject2": 78.2, "subject3": 63.5}      # synthetic recorded masses (kg)


def case(root, subject, trial, arm, version, converged=True, rot=2.0, trans=8.0, max_iterations=None, tag="x", hicks=True,
         resid=None, limits=(40.0, 4.0), com=1.0):
    """A synthetic finished case folder, as foot_models/case_store.py writes it. hicks: whether amendment 4's check
    passed; resid: the pelvis residuals (N, Nm), by default within both sets of limits, or far over them without hicks."""
    d = Path(root) / "cases" / f"{subject}_{trial}_{arm}" / f"{tag}{version}{arm}"
    d.mkdir(parents=True)
    key = dict(subject=subject, trial=trial, arm=arm, settings=dict(version=version), max_iterations=max_iterations,
               model_sha256="m", ik_sha256="i", code_sha256={})
    f, m = resid or ((1.0, 0.5) if hicks else (1.0, 50.0))
    (d / "case.json").write_text(json.dumps(dict(fingerprint=f"{tag}{version}{arm}", key=key, finished="now")))
    (d / "result.json").write_text(json.dumps(dict(converged=converged, valid=converged and hicks, status="s", iterations=1,
                                                   com_height_m=com, pelvis_residual_force_max_N=f, pelvis_residual_moment_max_Nm=m,
                                                   residual_force_limit_N=limits[0], residual_moment_limit_Nm=limits[1],
                                                   tracking_rms=dict(max_rotation_deg=rot, max_translation_mm=trans, worst="c"))))


# The v1 pilot's arm B (subject2 squats1, settings v1, case e0f292c4ae5fa8e2, 2026-11-06), as its result.json
# recorded it: converged, residuals within Hicks et al. (2015), so valid under amendment 4; but it leaves the floor.
V1_ARM_B = dict(subject="subject2", trial="squats1", arm="B", settings_version=1, converged=True, status="Solve_Succeeded",
                iterations=1168, valid_amendment4=True,
                solution_sha256="928adc541eea3239758cb38d103d0497e25fc2460660e42cc94589f1acc498c2",
                peak_external_force_N=780.69, com_height_m=0.3992, pelvis_residual_force_max_N=0.222, residual_force_limit_N=39.035,
                pelvis_residual_moment_max_Nm=0.09, residual_moment_limit_Nm=3.117,
                tracking_rms=dict(max_rotation_deg=50.465, mean_rotation_deg=4.782, max_translation_mm=672.537, worst="pelvis_tilt"))
# The v1 pilot's arm A (case c985ed43f90eca0b, 2026-11-07), as its result.json recorded it: not converged, with the
# feet about half a metre into the floor, so its own peak external force (71 MN) gave residual limits of 3.5 MN and
# 352 kNm, which its residuals (2.7 N, 34.7 Nm) were within.
V1_ARM_A = dict(subject="subject2", trial="squats1", arm="A", settings_version=1, converged=False,
                status="Maximum_Iterations_Exceeded", iterations=3000, valid_amendment4=False,
                solution_sha256="e7a62e82c6e409005983f17d236f6baa750d04afbb0d0bb6ae77dc54e0de762b",
                peak_external_force_N=70886977.73, com_height_m=0.4962, pelvis_residual_force_max_N=2.735,
                residual_force_limit_N=3544348.886, pelvis_residual_moment_max_Nm=34.737, residual_moment_limit_Nm=351756.951,
                tracking_rms=dict(max_rotation_deg=90.902, mean_rotation_deg=23.881, max_translation_mm=571.689, worst="arm_flex_r"))
SUBJECT2_MASS_KG = 78.2                     # sessionMetadata.yaml and the scale setup
for _r in (V1_ARM_A, V1_ARM_B):
    _r["residuals"] = SM.residual_limits(_r, SUBJECT2_MASS_KG)
DYNAMIC_OUT = Path(os.environ.get("DYNAMIC_OUT", Path.home() / "rehab-agent-data/sensor-sole/forceplate/dynamic"))
V1_ARM_B_CASE = DYNAMIC_OUT / "cases/subject2_squats1_B/e0f292c4ae5fa8e2"
V1_ARM_A_CASE = DYNAMIC_OUT / "cases/subject2_squats1_A/c985ed43f90eca0b"


def row(subject, trial, arm, converged=True, hicks=True, rot=2.0, trans=8.0):
    r = dict(subject=subject, trial=trial, arm=arm, converged=converged, valid_amendment4=converged and hicks,
             status="s", iterations=1, tracking_rms=dict(max_rotation_deg=rot, max_translation_mm=trans, worst="c"),
             com_height_m=1.0, pelvis_residual_force_max_N=1.0, pelvis_residual_moment_max_Nm=0.5 if hicks else 50.0,
             residual_force_limit_N=40.0, residual_moment_limit_Nm=4.0)
    r["residuals"] = SM.residual_limits(r, 70.0)
    return r


class Amendment5(unittest.TestCase):
    """Validity under amendment 5 (2026-11-08): convergence, Hicks residuals and the pilot gate's tracking limits."""

    @classmethod
    def setUpClass(cls):
        import dynamic_summary as SM
        cls.SM = SM

    def test_the_flying_v1_arm_b_solution_is_invalid(self):
        ok, why = self.SM.validity(V1_ARM_B)
        self.assertTrue(V1_ARM_B["valid_amendment4"])                     # amendment 4 accepted it
        self.assertFalse(ok)
        self.assertTrue(any("pelvis translation RMS 672.537" in w for w in why), why)
        self.assertTrue(any("rotation RMS 50.465" in w for w in why), why)
        self.assertFalse(self.SM.tracks(V1_ARM_B)[0])                     # the pilot gate's own check says the same

    @unittest.skipUnless((V1_ARM_B_CASE / "result.json").exists(), "needs the v1 pilot's case folder (DYNAMIC_OUT)")
    def test_the_recorded_v1_arm_b_case_is_invalid(self):
        rows = [r for r in self.SM.collect(DYNAMIC_OUT) if r["case"].endswith("e0f292c4ae5fa8e2")]
        self.assertEqual(len(rows), 1)
        r = rows[0]
        self.assertEqual(r["solution_sha256"], V1_ARM_B["solution_sha256"])
        self.assertEqual(r["tracking_rms"], V1_ARM_B["tracking_rms"])
        self.assertTrue(r["valid_amendment4"])
        self.assertFalse(r["valid"])
        self.assertTrue(r["residuals"]["amendment6"]["force_within"] and r["residuals"]["amendment6"]["moment_within"])

    def test_each_condition_is_needed(self):
        self.assertTrue(self.SM.validity(row("subject1", "squats1", "A"))[0])
        for bad, word in ((row("subject1", "squats1", "A", converged=False), "not converged"),
                          (row("subject1", "squats1", "A", hicks=False), "Hicks"),
                          (row("subject1", "squats1", "A", rot=5.01), "rotation RMS"),
                          (row("subject1", "squats1", "A", trans=20.01), "pelvis translation RMS")):
            ok, why = self.SM.validity(bad)
            self.assertFalse(ok)
            self.assertTrue(any(word in w for w in why), (word, why))
        self.assertTrue(self.SM.validity(row("subject1", "squats1", "A", rot=5.0, trans=20.0))[0])   # limits inclusive

    def test_every_collected_solve_gets_the_check(self):
        with tempfile.TemporaryDirectory() as d:
            case(d, "subject1", "squats1", "A", 2)
            case(d, "subject1", "squats1", "B", 2, trans=672.5)
            case(d, "subject3", "squatsAsym1", "A", 2, hicks=False)
            rows = self.SM.collect(d, masses=MASSES)
            s = self.SM.summarize(rows, 2)
        self.assertEqual([r["valid"] for r in rows], [True, False, False])
        self.assertEqual((s["valid"], s["valid_amendment4"]), (1, 2))
        self.assertEqual(s["per_arm"]["A"], dict(solves=2, converged=2, valid_trials=1, valid_subjects=1))
        self.assertEqual(s["valid_in_both_arms"], dict(trials=0, subjects=0))

    @unittest.skipUnless(HAVE, "needs the pipeline's Python")
    def test_penetration_on_a_synthetic_model(self):
        import opensim as osim

        def model(floor_orientation=(0, 0, -math.pi / 2)):
            m = osim.Model()
            b = osim.Body("b", 1.0, osim.Vec3(0), osim.Inertia(0.01))
            m.addBody(b)
            m.addJoint(osim.SliderJoint("j", m.getGround(), osim.Vec3(0), osim.Vec3(0, 0, math.pi / 2),
                                        b, osim.Vec3(0), osim.Vec3(0, 0, math.pi / 2)))      # the slider moves b along ground y
            m.addContactGeometry(osim.ContactHalfSpace(osim.Vec3(0), osim.Vec3(*floor_orientation), m.getGround(), "floor"))
            m.addContactGeometry(osim.ContactSphere(0.02, osim.Vec3(0.1, 0, 0), b, "s"))
            return m, m.initSystem()

        def states(m, st, heights):
            for i, h in enumerate(heights):
                st.setTime(0.1 * i); m.getCoordinateSet().get(0).setValue(st, h, False)
                yield st
        m, st = model()
        self.assertEqual(self.SM.max_penetration(m, states(m, st, (0.05, 0.01, 0.015))), (10.0, 0.1))
        self.assertEqual(self.SM.max_penetration(m, states(m, st, (0.05, 0.03))), (-10.0, 0.1))     # never in contact
        m, st = model(floor_orientation=(0, 0, 0))
        with self.assertRaises(ValueError):
            self.SM.max_penetration(m, states(m, st, (0.05,)))

    @unittest.skipUnless(HAVE and (V1_ARM_B_CASE / "solution.sto").exists(), "needs the v1 pilot's case folder (DYNAMIC_OUT)")
    def test_penetration_of_the_v1_arm_b_solution(self):
        rows = [r for r in self.SM.collect(DYNAMIC_OUT) if r["case"].endswith("e0f292c4ae5fa8e2")]
        self.SM.add_penetration(rows, DYNAMIC_OUT, DYNAMIC_OUT.parent / "models")
        self.assertGreaterEqual(rows[0]["max_penetration_mm"], 491.0)      # it starts with the feet ~0.49 m below the floor


class Amendment6(unittest.TestCase):
    """Amendment 6 (2026-11-08): the pelvis residual limits on the recorded body weight, not on the solution's own peak."""

    def test_v1_arm_a_fails_under_it(self):
        r = V1_ARM_A["residuals"]
        self.assertEqual((r["amendment4"]["force_limit_N"], r["amendment4"]["moment_limit_Nm"]), (3544348.886, 351756.951))
        self.assertTrue(r["amendment4"]["force_within"] and r["amendment4"]["moment_within"])   # its own peak let it through
        self.assertEqual(r["body_weight_N"], round(78.2 * 9.80665, 3))
        self.assertEqual((r["amendment6"]["force_limit_N"], r["amendment6"]["moment_limit_Nm"]),
                         (round(0.05 * 78.2 * 9.80665, 3), round(0.01 * 0.4962 * 78.2 * 9.80665, 3)))   # 38.344 N, 3.805 Nm
        self.assertTrue(r["amendment6"]["force_within"])
        self.assertFalse(r["amendment6"]["moment_within"])                                       # 34.737 Nm > 3.805 Nm
        ok, why = SM.residuals_within(V1_ARM_A)
        self.assertFalse(ok)
        self.assertEqual(why, ["pelvis residual moment 34.737 Nm over Hicks et al. (2015) on body weight, limit 3.805 Nm"])
        ok, why = SM.validity(V1_ARM_A)                       # every reason is listed: convergence, residuals, tracking
        self.assertFalse(ok)
        self.assertEqual(why[:2], ["not converged (Maximum_Iterations_Exceeded, 3000 iterations)",
                                   "pelvis residual moment 34.737 Nm over Hicks et al. (2015) on body weight, limit 3.805 Nm"])
        self.assertEqual(len(why), 4)

    @unittest.skipUnless((V1_ARM_A_CASE / "result.json").exists() and (SM.KINEMATICS / "subject2").exists(),
                         "needs the v1 pilot's case folder (DYNAMIC_OUT) and the dataset's kinematics (KIN)")
    def test_the_recorded_v1_arm_a_case_fails_under_it(self):
        rows = [r for r in SM.collect(DYNAMIC_OUT) if r["case"].endswith("c985ed43f90eca0b")]
        self.assertEqual(len(rows), 1)
        r = rows[0]
        self.assertEqual(r["solution_sha256"], V1_ARM_A["solution_sha256"])
        self.assertEqual(r["residuals"], V1_ARM_A["residuals"])                  # the recorded mass is subject 2's 78.2 kg
        self.assertFalse(r["valid"])
        self.assertTrue(any(w.startswith("pelvis residual moment 34.737 Nm") for w in r["invalid_because"]), r["invalid_because"])

    def test_the_limits_are_on_body_weight_and_inclusive(self):
        W = 70.0 * SM.G
        at = dict(com_height_m=0.9, pelvis_residual_force_max_N=0.05 * W, pelvis_residual_moment_max_Nm=0.01 * 0.9 * W,
                  residual_force_limit_N=1e6, residual_moment_limit_Nm=1e6)
        r = SM.residual_limits(at, 70.0)
        self.assertTrue(r["amendment6"]["force_within"] and r["amendment6"]["moment_within"])
        for k in ("pelvis_residual_force_max_N", "pelvis_residual_moment_max_Nm"):
            over = SM.residual_limits(dict(at, **{k: at[k] + 1e-6}), 70.0)
            self.assertFalse(over["amendment6"]["force_within"] and over["amendment6"]["moment_within"], k)
            self.assertTrue(over["amendment4"]["force_within"] and over["amendment4"]["moment_within"], k)
        # the solution's own peak, and the old limits taken on it, do not move the new limits
        other = SM.residual_limits(dict(at, peak_external_force_N=7e7, residual_force_limit_N=3.5e6), 70.0)
        self.assertEqual(other["amendment6"], r["amendment6"])
        self.assertFalse(SM.residuals_within(dict(at, residuals=None))[0])      # no body weight: not valid

    def test_the_recorded_mass_is_read_and_checked(self):
        with tempfile.TemporaryDirectory() as d:
            s = Path(d) / "subject7"
            (s / "OpenSimData/Mocap/Model").mkdir(parents=True); (s / "OpenSimData/Mocap/IK").mkdir(parents=True)
            (s / "sessionMetadata.yaml").write_text("height_m: 1.8\nmass_kg: 61.2\n")
            setup = s / "OpenSimData/Mocap/Model/x_setup_scale.xml"
            setup.write_text("<ScaleTool><mass>61.200000000000003</mass></ScaleTool>")
            (s / "OpenSimData/Mocap/IK/squats1.mot").write_text("ik")
            sha = hashlib.sha256(b"ik").hexdigest()
            self.assertEqual(SM.subject_mass_kg(d, "subject7", "squats1", sha), 61.2)
            with self.assertRaises(ValueError):                                  # not the kinematics the solve used
                SM.subject_mass_kg(d, "subject7", "squats1", "0" * 64)
            with self.assertRaises(ValueError):                                  # no such trial
                SM.subject_mass_kg(d, "subject7", "squatsAsym1", sha)
            setup.write_text("<ScaleTool><mass>62.0</mass></ScaleTool>")
            with self.assertRaises(ValueError):                                  # the two records disagree
                SM.subject_mass_kg(d, "subject7", "squats1", sha)

    def test_the_summary_reports_both_limits(self):
        with tempfile.TemporaryDirectory() as d:
            case(d, "subject1", "squats1", "A", 2)
            # tracks and passed amendment 4 on its own (high) peak, but its moment is over 1 % of COM height x body weight
            case(d, "subject1", "squats1", "B", 2, resid=(2.735, 34.737), limits=(3544348.886, 351756.951), com=0.4962)
            s = SM.summarize(SM.collect(d, masses=MASSES), 2)
        self.assertEqual((s["valid"], s["valid_amendment5"], s["valid_amendment4"]), (1, 2, 2))
        for r in s["solutions"]:
            for a in ("amendment4", "amendment6"):
                self.assertTrue({"force_limit_N", "moment_limit_Nm", "force_within", "moment_within"} <= set(r["residuals"][a]))
            self.assertEqual((r["residuals"]["force_N"], r["residuals"]["body_mass_kg"]), (r["pelvis_residual_force_max_N"], 70.0))
        self.assertEqual(s["per_arm"]["B"]["valid_trials"], 0)

    def test_the_pilot_gate_does_not_need_body_weight(self):
        with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as nokin:
            for a in "AB":
                case(d, "subject2", "squats1", a, 2)
            with self.assertRaises(ValueError):                                  # the summary stops without the masses
                SM.collect(d, kinematics=nokin)
            rows = SM.collect(d, kinematics=nokin, strict=False)
            ok, lines = SM.gate(rows, "subject2_squats1", 2)
        self.assertTrue(ok, lines)
        self.assertTrue(all("valid under amendments 5 and 6: no; body weight not read" in line for line in lines), lines)
        self.assertTrue(all(not r["valid"] for r in rows))


@unittest.skipUnless(HAVE, "needs the pipeline's Python")
class Amendment5Reporting(unittest.TestCase):
    """Phase-2 selection (dynamic_metrics.py): evaluated trials per arm, and A minus B only on trials evaluated in both."""

    def test_evaluated_counts_and_pairs(self):
        sols = [row("subject1", "squats1", "A"), row("subject1", "squats1", "B"),                    # both valid
                row("subject1", "squatsAsym1", "A"), row("subject1", "squatsAsym1", "B", trans=672.5),  # B flies
                row("subject2", "squats1", "A"), row("subject2", "squats1", "B"),                    # not covered
                row("subject3", "squats1", "A", converged=False), row("subject3", "squats1", "B")]   # A not converged
        covered = {("subject1", "squats1"): True, ("subject1", "squatsAsym1"): True, ("subject2", "squats1"): False,
                   ("subject3", "squats1"): True}
        ev = DM.evaluated(sols, covered)
        self.assertEqual(ev["A"], [("subject1", "squats1"), ("subject1", "squatsAsym1")])
        self.assertEqual(ev["B"], [("subject1", "squats1"), ("subject3", "squats1")])
        self.assertEqual(DM.counts(ev), {"A": dict(trials=2, subjects=1), "B": dict(trials=2, subjects=2)})
        self.assertEqual(DM.paired(ev), [("subject1", "squats1")])

    def test_a_duplicate_solve_is_refused(self):
        with self.assertRaises(ValueError):
            DM.evaluated([row("subject1", "squats1", "A"), row("subject1", "squats1", "A")], {("subject1", "squats1"): True})


class PilotGate(unittest.TestCase):
    """The pilot gate of run_dynamic.sh (foot_models/dynamic_summary.py): convergence and tracking, current settings only."""

    @classmethod
    def setUpClass(cls):
        import dynamic_summary as SM
        cls.SM = SM

    def gate(self, build, version=2):
        with tempfile.TemporaryDirectory() as d:
            build(d)
            rows = [r for r in self.SM.collect(d, masses=MASSES) if r["max_iterations"] is None]
            return self.SM.gate(rows, "subject2_squats1", version)

    def test_both_arms_converged_and_tracking_pass(self):
        ok, lines = self.gate(lambda d: [case(d, "subject2", "squats1", a, 2) for a in "AB"])
        self.assertTrue(ok, lines)

    def test_a_converged_solution_that_does_not_track_fails(self):
        # v1's arm B: converged, but the pelvis 672 mm off and the pelvis tilt 50 deg off
        ok, lines = self.gate(lambda d: (case(d, "subject2", "squats1", "A", 2),
                                         case(d, "subject2", "squats1", "B", 2, rot=50.5, trans=672.5)))
        self.assertFalse(ok)
        self.assertIn("pelvis translation", lines[1])

    def test_not_converged_or_missing_fails(self):
        self.assertFalse(self.gate(lambda d: [case(d, "subject2", "squats1", a, 2, converged=(a == "B")) for a in "AB"])[0])
        self.assertFalse(self.gate(lambda d: case(d, "subject2", "squats1", "B", 2))[0])

    def test_earlier_settings_and_capped_smoke_tests_do_not_count(self):
        def build(d):
            for a in "AB":
                case(d, "subject2", "squats1", a, 1)                                  # an earlier version that passed
                case(d, "subject2", "squats1", a, 2, max_iterations=50, tag="smoke")   # a capped smoke test that passed
                case(d, "subject2", "squats1", a, 2, converged=False)                 # the current version, failing
        self.assertFalse(self.gate(build)[0])

    def test_summary_counts_the_current_version_and_lists_the_rest(self):
        with tempfile.TemporaryDirectory() as d:
            for a in "AB":
                case(d, "subject2", "squats1", a, 1, rot=50.0)
                case(d, "subject2", "squats1", a, 2)
            s = self.SM.summarize(self.SM.collect(d, masses=MASSES), 2)
        self.assertEqual((s["solves"], s["within_pilot_gate"], len(s["superseded"])), (2, 2, 2))

    def test_settings_log_matches_the_code(self):
        log = json.loads((HERE / "foot_models" / "dynamic_settings_log.json").read_text())
        last = log["versions"][-1]
        self.assertEqual(last["version"], self.SM.settings_version())
        if HAVE:
            self.assertEqual(json.loads(json.dumps(last["settings"])), json.loads(json.dumps(DT.SETTINGS)))
            self.assertEqual(last["version"], DT.SETTINGS_VERSION)
        self.assertEqual({k: last["pilot_gate"][k] for k in self.SM.PILOT_GATE}, self.SM.PILOT_GATE)


FORCEPLATE_MODELS = Path(os.environ.get("FORCEPLATE_MODELS", Path.home() / "rehab-agent-data/sensor-sole/forceplate/models"))
KIN_ROOT = Path(os.environ.get("KIN", Path.home() / "rehab-agent-data/datasets/opencap-labvalidation/kinematics/LabValidation_withoutVideos"))
ARM_B_S2 = FORCEPLATE_MODELS / "subject2" / "LaiArnoldModified2017_poly_withArms_weldHand_scaled_contacts.osim"
ARM_A_S2 = DYNAMIC_OUT / "models" / "subject2" / "armA_sole.osim"
IK_S2 = {t: KIN_ROOT / "subject2" / "OpenSimData/Mocap/IK" / f"{t}.mot" for t in ("squats1", "squatsAsym1")}
HAVE_S2 = HAVE_OSIM and ARM_B_S2.exists() and ARM_A_S2.exists() and all(p.exists() for p in IK_S2.values())


@unittest.skipUnless(HAVE, "needs the pipeline's Python")
class SettingsV3Rules(unittest.TestCase):
    """Settings v3 (2026-11-09) without the subject models."""

    def test_strengths_round_up_to_the_next_10_nm(self):
        r = lambda x: DT.round_up_strength(x, 10.0)
        self.assertEqual([r(258.337), r(250.0), r(16.1), r(0.2), r(0.0), r(-40.6)], [260.0, 250.0, 20.0, 10.0, 10.0, 50.0])

    def test_the_settings_say_so(self):
        self.assertEqual((DT.SETTINGS_VERSION, DT.SETTINGS["torque_actuator_strength"], DT.SETTINGS["torque_actuator_round_up_Nm"],
                          DT.SETTINGS["initial_guess"], DT.SETTINGS["mesh_interval_s"]),
                         (3, "peak_inverse_dynamics", 10.0, "contact_balance", 0.02))
        self.assertEqual(len(DT.TORQUE_DRIVEN), 13)


@unittest.skipUnless(HAVE_S2, "needs OpenSim, subject2's models (both arms) and its kinematics")
class SettingsV3OnSubject2(unittest.TestCase):
    """Settings v3 on subject2's distributed model (arm B) and its arm-A model."""

    @classmethod
    def setUpClass(cls):
        cls.settings = dict(DT.SETTINGS, torque_actuator_strength=None)
        cls.model = DT.process_model(ARM_B_S2, cls.settings)
        cls.windows = {t: DT.squat_window(p)[:2] for t, p in IK_S2.items()}

    def test_the_torque_actuators_are_the_trunk_and_the_arms(self):
        acts = DT.torque_driven(self.model)
        self.assertEqual(set(acts), set(DT.TORQUE_DRIVEN))
        trees = DT.check_no_ground_load(self.model)
        self.assertEqual(set(trees["lumbar_extension"]), {"torso", "humerus_r", "ulna_r", "radius_r", "hand_r",
                                                          "humerus_l", "ulna_l", "radius_l", "hand_l"})
        self.assertEqual(set(trees["arm_flex_l"]), {"humerus_l", "ulna_l", "radius_l", "hand_l"})
        self.assertEqual(set(DT.check_no_ground_load(DT.process_model(ARM_A_S2, self.settings))), set(DT.TORQUE_DRIVEN))

    def test_a_contact_sphere_on_the_trunk_is_refused(self):
        m = osim.Model(str(ARM_B_S2))
        floor = osim.ContactHalfSpace.safeDownCast(m.getContactGeometrySet().get("floor"))
        sp = osim.ContactSphere(0.03, osim.Vec3(0, 0, 0), m.getBodySet().get("torso"), "on_the_trunk")
        m.addContactGeometry(sp)
        f = osim.SmoothSphereHalfSpaceForce("force_on_the_trunk", sp, floor)
        m.addForce(f); m.finalizeConnections(); m.initSystem()
        with self.assertRaisesRegex(ValueError, "on_the_trunk is on torso, which lumbar_extension moves"):
            DT.check_no_ground_load(m)

    def test_contact_forces_on_the_feet_change_no_trunk_or_arm_torque(self):
        for path in (ARM_B_S2, ARM_A_S2):
            taus, chk = DT.inverse_dynamics_torques(DT.process_model(path, self.settings), IK_S2["squats1"],
                                                    self.windows["squats1"], DT.SETTINGS)
            self.assertLess(chk["max_change_Nm"], 1e-9)
            self.assertGreater(min(chk["ankle_change_Nm"]), 1.0)          # the check does reach the legs
            self.assertGreater(min(chk["contact_force_bw"]), 1.0)
            self.assertEqual(set(taus), set(DT.TORQUE_DRIVEN))

    def test_strengths_are_the_peaks_rounded_up_and_the_same_for_both_arms(self):
        trials = [(IK_S2[t], self.windows[t]) for t in ("squats1", "squatsAsym1")]
        ts = DT.torque_actuator_strengths([ARM_B_S2, ARM_A_S2], trials, DT.SETTINGS)
        for c in DT.TORQUE_DRIVEN:
            s, pk = ts["strengths_Nm"][c], ts["peak_Nm"][c]
            self.assertEqual(s % 10.0, 0.0)
            self.assertTrue(max(10.0, pk) <= s < max(10.0, pk) + 10.0 + 1e-9, (c, s, pk))
        self.assertEqual(max(ts["strengths_Nm"], key=ts["strengths_Nm"].get), "lumbar_extension")
        self.assertEqual(len(ts["check"]), 4)                            # two models, two trials

    def test_the_solve_model_needs_the_strengths_and_takes_them(self):
        with self.assertRaisesRegex(ValueError, "need the torque actuators' strengths"):
            DT.process_model(ARM_B_S2, dict(DT.SETTINGS, version=3))
        strengths = {c: 10.0 * (k + 1) for k, c in enumerate(DT.TORQUE_DRIVEN)}
        m = DT.process_model(ARM_B_S2, DT.SETTINGS, strengths)
        for c, name in DT.torque_driven(m).items():
            self.assertEqual(osim.CoordinateActuator.safeDownCast(m.getForceSet().get(name)).getOptimalForce(), strengths[c])
        with self.assertRaisesRegex(ValueError, "strengths for"):
            DT.process_model(ARM_B_S2, DT.SETTINGS, {c: 10.0 for c in DT.TORQUE_DRIVEN[1:]})

    def test_the_guess_starts_each_arm_at_its_own_contact_balance(self):
        settings = dict(DT.SETTINGS, version=3)
        for path, band_mm in ((ARM_B_S2, (-40.0, -5.0)), (ARM_A_S2, (-25.0, 5.0))):
            strengths = {c: 10.0 for c in DT.TORQUE_DRIVEN}
            m = DT.process_model(path, settings, strengths)
            here = os.getcwd()
            with tempfile.TemporaryDirectory() as d:
                os.chdir(d)                                  # MocoTrack writes its tracked states to the working directory
                try:
                    study, solver = DT.tracking_study(m, path, IK_S2["squats1"], self.windows["squats1"], settings)
                finally:
                    os.chdir(here)
                name = next(n for n in solver.getGuess().getStateNames() if n.endswith("/pelvis_ty/value"))
                before = solver.getGuess().getStateMat(name).copy()
                off = DT.guess_at_contact_balance(m, study, solver, d)
                self.assertTrue((Path(d) / "guess.sto").exists())
            g = solver.getGuess()
            np.testing.assert_allclose(g.getStateMat(name), before + off, atol=1e-12)
            self.assertTrue(band_mm[0] < 1000 * off.min() <= 1000 * off.max() < band_mm[1], (path.name, off.min(), off.max()))
            st = m.initSystem(); cs = m.getCoordinateSet(); W = m.getTotalMass(st) * 9.80665
            labels = set(g.getStateNames())
            for k in np.linspace(0, g.getNumTimes() - 1, 5).astype(int):
                for i in range(cs.getSize()):
                    lab = cs.get(i).getAbsolutePathString() + "/value"
                    if lab in labels:
                        cs.get(i).setValue(st, float(g.getStateMat(lab)[k]), False)
                    cs.get(i).setSpeedValue(st, 0.0)
                m.realizeDynamics(st)
                self.assertAlmostEqual(sum(DT._sphere_force_y(f, st) for f in DT._spheres(m)) / W, 1.0, places=6)

if __name__ == "__main__":
    unittest.main()
