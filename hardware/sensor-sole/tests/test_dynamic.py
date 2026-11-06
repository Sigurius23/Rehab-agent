#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors
# SPDX-License-Identifier: CERN-OHL-S-2.0
"""Checks of the dynamic comparison's kinematics-only window rule (foot_models/dynamic_track.py) and of its phase-2
metric functions (foot_models/dynamic_metrics.py) on synthetic data, written before any dynamic solution existed:
  - the window is the first squat repetition with standing on both sides; a trial that starts mid-descent skips to
    the next repetition; a trial with no complete repetition is refused;
  - the combined centre of pressure is force-weighted; H1 is the peak error as % of body weight; H2 is the forward
    RMS of the centre-of-pressure error as % of foot length, blind to sideways offsets.
"""
import math
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


if __name__ == "__main__":
    unittest.main()
