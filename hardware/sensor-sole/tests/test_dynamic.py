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
    arm and A minus B only on trials evaluated in both.
"""
import json
import math
import os
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "foot_models"))
try:
    import numpy as np
    import scipy  # noqa: F401
    import dynamic_track as DT
    import dynamic_metrics as DM
    HAVE = True
except ImportError:
    HAVE = False


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


def case(root, subject, trial, arm, version, converged=True, rot=2.0, trans=8.0, max_iterations=None, tag="x", hicks=True):
    """A synthetic finished case folder, as foot_models/case_store.py writes it."""
    d = Path(root) / "cases" / f"{subject}_{trial}_{arm}" / f"{tag}{version}{arm}"
    d.mkdir(parents=True)
    key = dict(subject=subject, trial=trial, arm=arm, settings=dict(version=version), max_iterations=max_iterations,
               model_sha256="m", ik_sha256="i", code_sha256={})
    (d / "case.json").write_text(json.dumps(dict(fingerprint=f"{tag}{version}{arm}", key=key, finished="now")))
    (d / "result.json").write_text(json.dumps(dict(converged=converged, valid=converged and hicks, status="s", iterations=1,
                                                   tracking_rms=dict(max_rotation_deg=rot, max_translation_mm=trans, worst="c"))))


# The v1 pilot's arm B (subject2 squats1, settings v1, case e0f292c4ae5fa8e2, 2026-11-06), as its result.json
# recorded it: converged, residuals within Hicks et al. (2015), so valid under amendment 4; but it leaves the floor.
V1_ARM_B = dict(subject="subject2", trial="squats1", arm="B", settings_version=1, converged=True, status="Solve_Succeeded",
                iterations=1168, valid_amendment4=True,
                solution_sha256="928adc541eea3239758cb38d103d0497e25fc2460660e42cc94589f1acc498c2",
                peak_external_force_N=780.69, pelvis_residual_force_max_N=0.222, residual_force_limit_N=39.035,
                pelvis_residual_moment_max_Nm=0.09, residual_moment_limit_Nm=3.117,
                tracking_rms=dict(max_rotation_deg=50.465, mean_rotation_deg=4.782, max_translation_mm=672.537, worst="pelvis_tilt"))
DYNAMIC_OUT = Path(os.environ.get("DYNAMIC_OUT", Path.home() / "rehab-agent-data/sensor-sole/forceplate/dynamic"))
V1_ARM_B_CASE = DYNAMIC_OUT / "cases/subject2_squats1_B/e0f292c4ae5fa8e2"


def row(subject, trial, arm, converged=True, hicks=True, rot=2.0, trans=8.0):
    return dict(subject=subject, trial=trial, arm=arm, converged=converged, valid_amendment4=converged and hicks,
                status="s", iterations=1, tracking_rms=dict(max_rotation_deg=rot, max_translation_mm=trans, worst="c"))


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
            rows = self.SM.collect(d)
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
            rows = [r for r in self.SM.collect(d) if r["max_iterations"] is None]
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
            s = self.SM.summarize(self.SM.collect(d), 2)
        self.assertEqual((s["solves"], s["within_pilot_gate"], len(s["superseded"])), (2, 2, 2))

    def test_settings_log_matches_the_code(self):
        log = json.loads((HERE / "foot_models" / "dynamic_settings_log.json").read_text())
        last = log["versions"][-1]
        self.assertEqual(last["version"], self.SM.settings_version())
        if HAVE:
            self.assertEqual(json.loads(json.dumps(last["settings"])), json.loads(json.dumps(DT.SETTINGS)))
            self.assertEqual(last["version"], DT.SETTINGS_VERSION)
        self.assertEqual({k: last["pilot_gate"][k] for k in self.SM.PILOT_GATE}, self.SM.PILOT_GATE)


if __name__ == "__main__":
    unittest.main()
