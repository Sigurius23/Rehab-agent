#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors
# SPDX-License-Identifier: CERN-OHL-S-2.0
"""Tests for the first build's files: the coupon (coupon_print.py, needs the generator's Python with manifold3d)
and the bench logger's parsing and conversion (readout/log_bench.py, standard library only).

  python tests/test_coupon_readout.py
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE / "readout"))
import log_bench as LB  # noqa: E402

try:
    import manifold3d  # noqa: F401
    import ezdxf  # noqa: F401
    HAVE_GEN = True
except ImportError:
    HAVE_GEN = False


@unittest.skipUnless(HAVE_GEN, "needs the generator's Python with manifold3d and ezdxf")
class Coupon(unittest.TestCase):
    def test_coupon_passes_every_sole_check_with_four_cells_and_the_reference(self):
        import coupon_print as CP
        import sole_print as SP
        with tempfile.TemporaryDirectory() as d:
            b = Path(d) / "c.board.json"; b.write_text(json.dumps(CP.board()))
            rep = SP.build(b, Path(d) / "out")
            self.assertTrue(rep["checks"]["all_pass"], rep["checks"])
            self.assertEqual(set(rep["cells"]), set(CP.CELLS) | {"ref"})
            self.assertEqual(rep["wires"]["conductors"], 6)          # 4 cells, the reference, the common
            self.assertTrue(rep["bed"]["fits"])

    def test_the_coupons_id_follows_its_geometry(self):
        import coupon_print as CP
        a = CP.board()
        self.assertEqual(a["board_id"], CP.board()["board_id"])
        CP.CELLS["cell_s16"] = (6, 58, 23, 74)
        try:
            self.assertNotEqual(a["board_id"], CP.board()["board_id"])
        finally:
            CP.CELLS["cell_s16"] = (6, 58, 22, 74)


class Logger(unittest.TestCase):
    H = "H,fw=sole_bench 0.1,lines=3,settle_us=300,oversample=4,period_ms=10,rf_ohm=100000,rf_ref_ohm=200000,adc_bits=12\n"

    def test_header_and_frame_parse(self):
        h = LB.parse_header(self.H)
        self.assertEqual((h["lines"], h["rf_ohm"], h["fw"]), (3, 100000, "sole_bench 0.1"))
        f = LB.parse_frame("F,1000,2,950,620,700,620,1240,4095\n", 3)
        self.assertEqual((f["vbias"], f["ch"]), (620, [620, 1240, 4095]))

    def test_malformed_frames_are_skipped(self):
        self.assertIsNone(LB.parse_frame("F,1,2,3,4,5,6\n", 3))          # too short
        self.assertIsNone(LB.parse_frame("F,1,2,3,4,5,6,x,8\n", 3))
        out = list(LB.rows(["garbage\n", "F,1,0,0,620,620,620,620,620\n", self.H, "F,1,0,0\n",
                            "F,1000,0,0,620,620,620,1240,4095\n"]))
        self.assertEqual(len(out), 1)                                     # frames before a header are dropped

    def test_conductance_is_ratiometric(self):
        # Vout = Vbias (1 + Rf G): twice the bias at Rf 100 kOhm is G = 10 uS, whatever the counts' scale
        self.assertAlmostEqual(LB.conductance_us(1240, 620, 100000), 10.0)
        self.assertAlmostEqual(LB.conductance_us(2480, 1240, 100000), 10.0)
        self.assertEqual(LB.conductance_us(600, 620, 100000), 0.0)        # below the bias reads as no contact
        self.assertIsNone(LB.conductance_us(1000, 0, 100000))

    def test_rows_name_channels_use_each_rf_and_flag_saturation(self):
        _, r = next(LB.rows([self.H, "F,1000,0,0,620,1240,620,1240,4095\n"], names=["a", "b"]))
        self.assertAlmostEqual(r["b_uS"], 10.0)
        self.assertAlmostEqual(r["ref_uS"], 5.0)                          # the reference's own Rf, 200 kOhm
        self.assertIn("ch2", r)
        self.assertEqual(r["saturated"], "ch2")


if __name__ == "__main__":
    unittest.main(verbosity=2)
