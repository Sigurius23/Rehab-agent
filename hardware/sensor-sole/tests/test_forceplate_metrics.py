#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors
# SPDX-License-Identifier: CERN-OHL-S-2.0
"""Checks of foot_models/forceplate_metrics.py on synthetic frames, written before any measured value was computed:
zero errors when measurement and model agree; the vertical error as % of body weight; the share error in points;
the combined centre of pressure weighted by each foot's force and projected on the forward axis (a sideways
offset gives no forward error); predictions that differ from the recorded sha256 stop the run.
"""
import json
import math
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "foot_models"))
try:
    import forceplate_metrics as FM
    HAVE = True
except ImportError:
    HAVE = False

W = 700.0


def model(r_n=350.0, cop_r=(0.10, 0.10), cop_l=(0.10, -0.10), fwd=(1.0, 0.0)):
    return dict(body_weight_N=W, R=dict(vertical_N=r_n, cop_ground_m=list(cop_r)), L=dict(vertical_N=W - r_n, cop_ground_m=list(cop_l)),
                right_share_pct=100.0 * r_n / W, forward_axis=list(fwd))


def meas(r_n=350.0, l_n=350.0, cop_r=(0.10, 0.10), cop_l=(0.10, -0.10)):
    return dict(R=dict(vy=r_n, cop=cop_r), L=dict(vy=l_n, cop=cop_l))


@unittest.skipUnless(HAVE, "needs numpy")
class FrameErrors(unittest.TestCase):
    def test_agreement_gives_zero(self):
        e = FM.frame_errors(model(), meas(), 250.0)
        for k in FM.THRESHOLDS:
            self.assertAlmostEqual(e[k], 0.0, places=12)

    def test_vertical_error_in_percent_of_body_weight(self):
        e = FM.frame_errors(model(), meas(357.0, 357.0), 250.0)       # 14 N more than 700 N: +2 %
        self.assertAlmostEqual(e["vertical_force_pct_bw"], 2.0, places=10)

    def test_share_error_in_points(self):
        e = FM.frame_errors(model(r_n=385.0), meas(420.0, 280.0), 250.0)   # measured 60 %, model 55 %
        self.assertAlmostEqual(e["left_right_share_points"], 5.0, places=10)

    def test_combined_cop_is_force_weighted_and_projected_forward(self):
        # measured: right foot 20 mm ahead with 3/4 of the load -> combined 15 mm ahead; the model unchanged
        e = FM.frame_errors(model(), meas(525.0, 175.0, cop_r=(0.12, 0.10), cop_l=(0.10, -0.10)), 250.0)
        # model combined x = 0.10; measured combined x = (525*0.12 + 175*0.10)/700 = 0.115
        self.assertAlmostEqual(e["cop_forward_mm"], 15.0, places=9)
        self.assertAlmostEqual(e["cop_forward_pct_foot_length"], 6.0, places=9)

    def test_forward_axis_direction_and_sideways_offsets(self):
        f = (math.cos(math.radians(30)), math.sin(math.radians(30)))
        shift = lambda c, d: (c[0] + d * f[0], c[1] + d * f[1])
        side = lambda c, d: (c[0] - d * f[1], c[1] + d * f[0])
        e = FM.frame_errors(model(fwd=f), meas(cop_r=shift((0.10, 0.10), 0.01), cop_l=shift((0.10, -0.10), 0.01)), 200.0)
        self.assertAlmostEqual(e["cop_forward_mm"], 10.0, places=9)
        e = FM.frame_errors(model(fwd=f), meas(cop_r=side((0.10, 0.10), 0.01), cop_l=side((0.10, -0.10), 0.01)), 200.0)
        self.assertAlmostEqual(e["cop_forward_mm"], 0.0, places=9)


@unittest.skipUnless(HAVE, "needs numpy")
class Files(unittest.TestCase):
    def test_force_file_layout_and_interpolation(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "x_forces.mot"
            cols = ["time"] + [f"{s}_ground_{q}" for s in ("R", "L", "3") for q in
                               ("force_vx", "force_vy", "force_vz", "force_px", "force_py", "force_pz", "torque_x", "torque_y", "torque_z")]
            rows = [[0.0] + [1.0] * 27, [0.0005] + [3.0] * 27]
            p.write_text("name x\ndatacolumns 28\ndatarows 2\nrange 0 0.0005\nendheader\n" + "\t".join(cols) + "\n"
                         + "".join("\t".join(f"{v:.6f}" for v in r) + "\n" for r in rows))
            t, c = FM.load_forces(p)
            m = FM.measured_at(t, c, 0.00025)
            self.assertAlmostEqual(m["R"]["vy"], 2.0)
            self.assertAlmostEqual(m["plate3_vy"], 2.0)
            self.assertAlmostEqual(m["gap_s"], 0.00025)

    def test_changed_predictions_stop_the_run(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "solve" / "subject1").mkdir(parents=True)
            (d / "solve" / "subject1" / "double_support.json").write_text(json.dumps(dict(trials={})))
            rec = d / "record.json"
            rec.write_text(json.dumps(dict(subjects=dict(subject1=dict(double_support_sha256="0" * 64, foot_length_mm=dict(mean=250.0))))))
            with self.assertRaises(SystemExit):
                FM.evaluate(rec, d / "solve", d / "forces")


try:
    import forceplate_posthoc as PH
except ImportError:
    PH = None


@unittest.skipUnless(HAVE and PH, "needs numpy")
class PostHocCoverageRule(unittest.TestCase):
    """The post-hoc plate-coverage rule (measured loads only): a trial is left out if either plate carries less
    than 1 % of body weight on average."""

    def test_both_plates_loaded_is_kept(self):
        self.assertEqual(PH.coverage([350.0, 360.0], [340.0, 330.0], W)[0], True)

    def test_an_unloaded_plate_is_left_out(self):
        kept, r, l = PH.coverage([0.0, 2.0], [700.0, 698.0], W)
        self.assertFalse(kept)
        self.assertAlmostEqual(r, 100.0 * 1.0 / W)

    def test_the_threshold_is_one_percent_of_body_weight(self):
        self.assertTrue(PH.coverage([7.0], [693.0], W)[0])          # exactly 1 %: kept
        self.assertFalse(PH.coverage([6.9], [693.1], W)[0])


if __name__ == "__main__":
    unittest.main()
