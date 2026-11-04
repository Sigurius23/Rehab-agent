#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors
# SPDX-License-Identifier: CERN-OHL-S-2.0
"""Regression tests for the generator (the generator's Python: numpy, scipy, shapely, matplotlib, ezdxf).

Fast tests (seconds):
  - fracture() on the comb that made it recurse forever (T1, synthetic foot, left side), and fracture() failing
    closed when no cut makes progress;
  - export_rings(): an outline that rounding to 0.1 um makes invalid is rebuilt without changing the copper by
    more than rounding; a neck thinner than the grid stops the export; valid outlines are written exactly as
    before.
Slow tests (minutes each; set SOLE_SLOW_TESTS=1):
  - T1 at EU 37, right foot: the routing conflict that left 3 clearance errors (odd crossings at two vias, the
    fine pass unable to separate ffp_med and toe1_tip) must not come back. A second, smaller squeeze that
    remains (mt3/mt4 at one corner) is recorded as an expected failure until it is fixed;
  - T1 on the mirrored synthetic foot: the board file must be written, with every outline valid.

  python tests/test_generator_regressions.py            # fast
  SOLE_SLOW_TESTS=1 python tests/test_generator_regressions.py
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import sole_gen as G  # noqa: E402
import shapely.ops  # noqa: E402
from shapely import wkt  # noqa: E402
from shapely.geometry import GeometryCollection, LineString, Polygon, box  # noqa: E402
from shapely.ops import unary_union  # noqa: E402

REAL_SPLIT = shapely.ops.split

FIXTURE = HERE / "tests" / "fixtures" / "t1_mirrored_comb.wkt"
SLOW = os.environ.get("SOLE_SLOW_TESTS") == "1"


def same_copper(a, b):
    """The exporter's rule: every separate piece of difference is rounding (nothing thicker than two grid steps)
    or a sliver no larger than the size fracture() drops."""
    d = a.symmetric_difference(b)
    return all(g.is_empty or g.buffer(-2 * G.EXPORT_GRID).is_empty or g.area <= G.SLIVER_MM2
               for g in getattr(d, "geoms", [d]))


class Fracture(unittest.TestCase):
    def test_mirrored_comb_splits_into_hole_free_pieces(self):
        poly = wkt.loads(FIXTURE.read_text())
        self.assertTrue(poly.is_valid)
        self.assertGreater(len(poly.interiors), 0)
        pieces = G.fracture(poly)
        self.assertTrue(pieces)
        self.assertTrue(all(not p.interiors for p in pieces))
        self.assertTrue(same_copper(unary_union(pieces), poly))

    def test_vertical_cut_without_progress_falls_back_to_another_cut(self):
        poly = wkt.loads(FIXTURE.read_text())

        def no_vertical(g, line):                     # the failure: a vertical cut returns the polygon unchanged
            (x0, y0), (x1, y1) = line.coords
            return REAL_SPLIT(g, line) if y0 == y1 else GeometryCollection([g])
        with mock.patch("shapely.ops.split", no_vertical):
            pieces = G.fracture(poly)
        self.assertTrue(all(not p.interiors for p in pieces))
        self.assertTrue(same_copper(unary_union(pieces), poly))

    def test_no_progress_fails_closed(self):
        poly = box(0, 0, 10, 10).difference(box(2, 2, 4, 4))
        with mock.patch("shapely.ops.split", lambda g, line: GeometryCollection([g])):
            with self.assertRaises(G.FractureError):
                G.fracture(poly)


class ExportPrecision(unittest.TestCase):
    def test_subgrid_slit_is_rebuilt_without_changing_copper(self):
        slit = Polygon([(0, 0), (5, 0), (5, 5), (2.00004, 5), (2.00004, 2), (2.0, 2), (2.0, 5), (0, 5)])
        self.assertTrue(slit.is_valid)
        self.assertFalse(Polygon(G._ring(slit.exterior)).is_valid)     # what rounding alone used to write
        rings, rebuilt, _ = G.export_rings(slit, [slit], "slit", connected=True)
        self.assertEqual(rebuilt, 1)
        self.assertTrue(all(Polygon(r).is_valid for r, _ in rings))
        self.assertTrue(same_copper(unary_union([Polygon(r) for r, _ in rings]), slit))

    def test_larger_difference_fails_closed(self):
        a = box(0, 0, 5, 5)
        with self.assertRaises(G.ExportGeometryError):           # a piece that lost 0.01 mm2 of copper
            G.export_rings(a, [box(0, 0, 5, 4.998)], "lost strip", connected=True)

    def test_subgrid_neck_fails_closed(self):
        bell = Polygon([(0, 0), (2, 0), (2, 0.99998), (3, 0.99998), (3, 0), (5, 0), (5, 2), (3, 2), (3, 1.00002),
                        (2, 1.00002), (2, 2), (0, 2)])
        self.assertTrue(bell.is_valid)
        with self.assertRaises(G.ExportGeometryError):
            G.export_rings(bell, [bell], "dumbbell", connected=True)

    def test_valid_outline_is_written_exactly_as_before(self):
        p = Polygon([(0.12345678, 0), (5, 0.00001), (5, 5), (0, 5)])
        rings, rebuilt, sliver = G.export_rings(p, [p], "plain", connected=True)
        self.assertEqual((rebuilt, sliver), (0, 0.0))
        self.assertEqual([r for r, _ in rings], [G._ring(p.exterior)])
        self.assertEqual(rings[0][1], list(p.representative_point().coords[0]))

    def test_mirrored_comb_exports_valid_connected_pads(self):
        poly = wkt.loads(FIXTURE.read_text())
        rings, _, _ = G.export_rings(poly, G.pad_pieces(poly), "mirrored comb", connected=True)
        self.assertTrue(all(Polygon(r).is_valid for r, _ in rings))


def run_candidate(args, out):
    py = sys.executable
    r = subprocess.run([py, str(HERE / "sole_candidate.py"), str(HERE / "candidates" / "T1" / "layout.json"),
                        *args, "--out", str(out)], capture_output=True, text=True, timeout=3600, cwd=HERE)
    if r.returncode != 0:
        raise AssertionError(r.stderr[-3000:])
    return json.loads(r.stdout[r.stdout.index("{"):])


@unittest.skipUnless(SLOW, "set SOLE_SLOW_TESTS=1 (minutes per test)")
class SlowRegressions(unittest.TestCase):
    _eu37 = {}

    def eu37(self):
        """T1 at EU 37, right foot, generated once for both tests below."""
        if not self._eu37:
            d = tempfile.mkdtemp()
            self._eu37["chk"] = run_candidate(["--size", "37", "--side", "R"], d)
            self._eu37["board"] = json.loads((Path(d) / "cand_T1_EU37_R.board.json").read_text())
        return self._eu37["chk"], self._eu37["board"]

    def test_t1_eu37_right_plan_is_planar(self):
        """The failure fixed here: vias with no clear cell sat beside the bundle, the plan kept 6 odd crossings
        and a jumper, and the fine pass left ffp_med and toe1_tip 0.007 mm apart (3 clearance errors)."""
        chk, _ = self.eu37()
        r = chk["routing"]
        self.assertEqual(r["planned_odd_crossings"], [])
        self.assertEqual(r["jumpers"], [])
        self.assertEqual(r["unresolved_crossings"], [])
        self.assertFalse({"ffp_med", "toe1_tip"} & set(r["maze_failed"]))
        self.assertTrue(chk["planarity_retry"] and chk["planarity_retry"][-1]["kept"])

    @unittest.expectedFailure
    def test_t1_eu37_right_fine_pass_is_clean(self):
        """Known open: with the plan planar, mt4 joins the bundle at its turn and the lanes there come out 0.255 mm
        apart against 0.27 mm (lane construction where a branch joins at a bend). Remove expectedFailure once
        fixed; the test then reports an unexpected success."""
        chk, board = self.eu37()
        self.assertEqual(chk["routing"]["maze_failed"], [])
        lanes = [LineString(v) for v in board["copper_routing"]["lanes"].values() if len(v) > 1]
        gap = min(a.distance(b) for i, a in enumerate(lanes) for b in lanes[i + 1:])
        c = board["contact"]
        self.assertGreaterEqual(gap, c["sense_w"] + c["clear"] - 1e-3)

    def test_t1_mirrored_synthetic_foot_exports(self):
        with tempfile.TemporaryDirectory() as d:
            run_candidate(["--foot", str(HERE / "person_example.json"), "--side", "L"], d)
            bj = json.loads((Path(d) / "cand_T1_person_example_L.board.json").read_text())
            rings = [q["pts"] for r in bj["regions"].values() for k in ("sense", "common") for q in r[k]]
            rings += bj["margin_keepout"] + [r["outline"] for r in bj["regions"].values()]
            self.assertTrue(all(Polygon(q).is_valid for q in rings))


if __name__ == "__main__":
    unittest.main(verbosity=2)
