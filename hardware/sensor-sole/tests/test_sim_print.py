#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors
# SPDX-License-Identifier: CERN-OHL-S-2.0
"""Tests for sole_sim.py (simulation export and readout) and sole_print.py (printed prototype), on a small
synthetic board, in seconds. The generator's Python with manifold3d.

  python tests/test_sim_print.py
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import sole_sim as SS  # noqa: E402


def board(side="R"):
    """A tiny board file: a 100 x 40 mm sole with a tail, two regions and a routing plan."""
    m = 1 if side == "R" else -1
    rect = lambda x0, z0, x1, z1: [[x0, m * z0], [x1, m * z0], [x1, m * z1], [x0, m * z1]]
    outline = [[0, m * -20], [45, m * -20], [45, m * -60], [55, m * -60], [55, m * -20], [100, m * -20],
               [100, m * 20], [0, m * 20]]
    if m < 0:
        outline = outline[::-1]
    regions = {"heel": dict(outline=rect(3, -17, 40, 17)), "toe1": dict(outline=rect(60, -17, 97, 17))}
    return dict(board_id=f"TEST {side} 0123456789", design_hash="0123456789" + "0" * 54, side=side,
                foot_length=100.0, ball_width=40.0, outline=outline, regions=regions,
                bend=dict(point=[70.0, 0.0], dir=[0.0, 1.0]),
                routing_plan={"heel": [[40.5, m * -10], [50, m * -10], [50, m * -18]],
                              "toe1": [[59.5, m * -10], [50, m * -10], [50, m * -18]]},
                tail=dict(end=[50.0, m * -60], dir=[0.0, m * -1.0], width=8.0),
                copper_routing=dict(pin_order=["COM", "heel", "toe1", "COM"]))


class Sim(unittest.TestCase):
    def sole(self, side="R"):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "b.board.json"; p.write_text(json.dumps(board(side)))
            return SS.export(p, spacing=10.0)

    def test_export_has_points_in_every_region_and_contact_order(self):
        s = self.sole()
        self.assertEqual(set(s["contact_points"]), {"heel", "toe1"})
        self.assertTrue(all(len(v) >= 2 for v in s["contact_points"].values()))
        self.assertEqual(s["contacts"], {"1": "COM", "2": "heel", "3": "toe1", "4": "COM"})
        self.assertIn("not verified", s["contacts_source"])

    def test_left_points_mirror_right(self):
        r, l = self.sole("R"), self.sole("L")
        for n in r["contact_points"]:
            a = sorted((x, z) for x, z in r["contact_points"][n])
            b = sorted((x, -z) for x, z in l["contact_points"][n])
            self.assertEqual(a, b)

    def test_readout_sums_regions_and_follows_the_sensor_model(self):
        s = self.sole()
        head = ["time"]
        cols = []
        for n, pts in s["contact_points"].items():
            for k in range(len(pts)):
                head += [f"force_sole_r_{n}_{k:02d}.Sphere.force.Y", f"force_sole_r_{n}_{k:02d}.HalfSpace.force.Y"]
                cols.append(n)
        t = np.array([0.0, 0.01])
        per = {"heel": 100.0, "toe1": 10.0}                      # N per sphere
        rows = []
        for ti in t:
            r = [ti]
            for n in cols:
                r += [per[n], -per[n]]
            rows.append(r)
        f = SS.region_forces(head, np.array(rows), s)
        self.assertAlmostEqual(f["heel"][0], 100.0 * len(s["contact_points"]["heel"]))
        self.assertAlmostEqual(f["toe1"][0], 10.0 * len(s["contact_points"]["toe1"]))
        cop, tot = SS.centre_of_pressure(f, s)
        self.assertAlmostEqual(tot[0], f["heel"][0] + f["toe1"][0])
        self.assertLess(cop[0][0], 50)                          # most load on the heel
        rd = SS.readings(f, dict(s, sensor_model=dict(s["sensor_model"], noise_fraction=0.0)))
        self.assertEqual(sorted(rd), [2, 3])                    # sense contacts only, in contact order
        full = 600e3 * s["regions"]["heel"]["area_mm2"] * 1e-6
        self.assertEqual(rd[2][0], round(min(f["heel"][0] / full, 1) * 4095))

    def test_missing_force_columns_fail(self):
        s = self.sole()
        with self.assertRaises(ValueError):
            SS.region_forces(["time", "something_else.force.Y"], np.zeros((2, 2)), s)


class Print(unittest.TestCase):
    def test_carrier_and_cover_are_watertight_with_one_hole_per_wire(self):
        import sole_print as SP
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "b.board.json"; p.write_text(json.dumps(board()))
            rep = SP.build(p, Path(d) / "out")
            c = rep["parts"]["carrier"]
            self.assertTrue(c["watertight"] and rep["parts"]["cover"]["watertight"])
            self.assertEqual(c["genus"], rep["wires"]["sense"] + rep["wires"]["common"])   # holes through the floor
            self.assertGreaterEqual(rep["layers"]["narrowest_wall_between_pockets_mm"], 0.8)
            self.assertTrue((Path(d) / "out" / "TEST_R_0123456789.carrier.stl").stat().st_size > 1000)


if __name__ == "__main__":
    unittest.main(verbosity=2)
