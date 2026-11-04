#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors
# SPDX-License-Identifier: CERN-OHL-S-2.0
"""Checks of the experimental foot-model comparison (foot_models/compare_feet.py, synergy_kinematics.py).

  - Internal control: D'Hondt's 3- and 4-segment models with the foot joints locked are the same rigid foot, so
    they must give the same regional loads at the same prescribed centre of pressure; the support must equal the
    body weight and the centre of pressure must sit at its target.
  - Posture mapping: knee flexion sign flipped for gait2392-style knees; angles outside a model's range flagged.
  - Synergy foot: ankle flexion (gain 1) moves nothing under the sole relative to the calcaneus; gain 5 turns all
    five toes by the same angle (they are coupled); the heel regions lie under the calcaneus.
Needs opensim, and DHONDT_NOMINAL_DIR and/or SYNERGY_MODEL (path to synergy_foot_r.osim); skipped otherwise.
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "foot_models"))
sys.path.insert(0, str(HERE))
try:
    import opensim as osim
    import compare_feet as CF
    import dhondt_port as DP
    import synergy_kinematics as SK
except ImportError:
    osim = None
NOMINAL = os.environ.get("DHONDT_NOMINAL_DIR")
SYNERGY = os.environ.get("SYNERGY_MODEL")
SOLE_R = HERE / "sim" / "EU42_R_636645a928.sole_sim.json"
SOLE_L = HERE / "sim" / "EU42_L_40fe8e1d0c.sole_sim.json"


@unittest.skipIf(osim is None or not NOMINAL, "needs opensim and DHONDT_NOMINAL_DIR")
class Harness(unittest.TestCase):
    def test_rigid_three_and_four_segment_feet_agree(self):
        for contact in (CF.SS.ASSUMED_CONTACT_V1, None):
            with self.subTest(contact=contact and contact["name"]):
                self._rigid_agree(contact)

    def _rigid_agree(self, contact):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            res = {}
            for k in ("3", "4"):
                ported = d / f"p{k}.osim"
                DP.port(Path(NOMINAL) / f"DHondt_2024_{k}-segment_foot_fixed_knee.osim", ported)
                res[k] = CF.run(ported, SOLE_R, SOLE_L, d / k, None, False, cop_target=0.45, contact=contact)
                self.assertEqual(res[k]["contact_model"]["name"], contact["name"] if contact else "native")
            for k, r in res.items():
                self.assertTrue(r["solved"], k)
                self.assertLess(abs(r["support_error_pct"]), 0.1)
                self.assertAlmostEqual(r["R"]["cop_sole_mm"][0], r["cop_target_sole_mm"]["r"], delta=0.05)
            for n, v in res["3"]["R"]["regions_pct_of_foot"].items():
                self.assertAlmostEqual(v, res["4"]["R"]["regions_pct_of_foot"][n], delta=0.01, msg=n)

    def test_posture_mapping(self):
        m = osim.Model(str(Path(NOMINAL) / "DHondt_2024_4-segment_foot_fixed_knee.osim"))
        applied, notes, outside = CF.map_posture(m, {"knee_angle_r": 30.0, "hip_flexion_r": 80.0, "lumbar_extension": -10.0})
        self.assertEqual(applied["knee_angle_r"], -30.0)
        self.assertTrue(any("sign flipped" in n for n in notes))
        self.assertTrue(any(o.startswith("hip_flexion_r = 80.0") for o in outside))
        self.assertFalse(any(o.startswith("lumbar") for o in outside))


@unittest.skipIf(osim is None or not SYNERGY, "needs opensim and SYNERGY_MODEL")
class Synergy(unittest.TestCase):
    def test_kinematic_checks(self):
        r = SK.analyse(SYNERGY, SOLE_R)
        g1 = r["sweeps"]["synergy_gain_1"]["full coordinate range"]
        self.assertEqual(max(g1["max_region_motion_vs_calcaneus_mm"].values()), 0.0)
        toes = set(r["sweeps"]["synergy_gain_5"]["full coordinate range"]["max_toe_rotation_vs_metatarsal_deg"].values())
        self.assertEqual(len(toes), 1)                         # all five toes turn together
        self.assertGreater(toes.pop(), 10.0)
        for n in ("heel_post", "heel_med"):
            self.assertEqual(set(r["region_to_bones"][n]), {"CA_r"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
