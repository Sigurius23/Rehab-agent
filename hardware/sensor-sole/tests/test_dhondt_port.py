#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors
# SPDX-License-Identifier: CERN-OHL-S-2.0
"""Verification of foot_models/dhondt_port.py against the original equations of D'Hondt et al. (2024).

  - The Natali (2010) plantar fascia law: the port's function against a reference written separately here from
    f_getPlantarFasciaStiffnessModelCasADiFunction.m, and against a value worked by hand.
  - The midtarsal ligament moment: the committed table against the paper's saved CasADi bspline
    (f_getMtjLigamentMoment_exp5), evaluated with CasADi (needs casadi and DHONDT_EXP5=<path to that file>).
  - OpenSim: the ported models' actual forces (fascia tension, midtarsal and MTP generalized forces) against the
    original equations over sweeps of angle and speed (needs opensim and DHONDT_NOMINAL_DIR=<folder with
    DHondt_2024_3-segment_foot_fixed_knee.osim and DHondt_2024_4-segment_foot_fixed_knee.osim>).
The models and the bspline are not in this repository: fetch them from
https://github.com/Lars-DHondt-KUL/3dpredictsim at commit e963f4a; the port checks their sha256.

  DHONDT_NOMINAL_DIR=... python tests/test_dhondt_port.py
"""
import hashlib
import math
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "foot_models"))
import dhondt_port as DP  # noqa: E402

try:
    import opensim as osim
except ImportError:
    osim = None
try:
    import casadi
except ImportError:
    casadi = None
NOMINAL_DIR = os.environ.get("DHONDT_NOMINAL_DIR")
EXP5 = os.environ.get("DHONDT_EXP5")


def natali_reference(l):
    """Written out again from the MATLAB source, step by step (mu, k, alpha in MPa; A0 in mm^2; F in N)."""
    ls, A0, nu = 0.146, 70.0, 0.4
    mu, k, alpha = 14.449, 254.02, 10.397
    lam = l / ls
    cauchy = mu * (lam * lam - 1.0 / lam) + (k / (2.0 * alpha)) * (math.exp(alpha * (lam * lam - 1.0)) - 1.0) * lam * lam
    area = A0 * lam ** (-0.8)
    smooth = (math.tanh((l - ls) * 4000.0 - 1.1) + 1.0) / 2.0
    return cauchy * area * smooth


class Equations(unittest.TestCase):
    def test_natali_transcription(self):
        for l in np.linspace(0.140, 0.170, 61):
            self.assertAlmostEqual(float(DP.natali2010_force(l)), natali_reference(float(l)), places=6)
        # by hand at l/ls = 1.0283: Cauchy stress 11.77 MPa, area 68.45 mm^2, smoothing ~1 -> about 806 N
        self.assertAlmostEqual(float(DP.natali2010_force(1.0283 * 0.146)), 806.0, delta=1.5)
        self.assertAlmostEqual(float(DP.natali2010_force(0.146)), 0.0, places=9)

    def test_falisse_passive_moment(self):
        K, th = DP.K_PASS["mtp"]
        q = 0.5
        expect = -0.9 * math.exp(14.87 * (q - 65 / 180 * math.pi)) + 0.18 * math.exp(-70.08 * (q - 0.0)) - 0.1 * 2.0
        self.assertAlmostEqual(float(DP.falisse_passive(q, 2.0, K, th)), expect, places=12)

    def test_table_knots_are_reference_samples(self):
        t = DP.table()
        ref = dict(zip(np.round(t["reference_deg"], 6), t["reference_Nm"]))
        for d, m in zip(np.round(t["knots_deg"], 6), t["knots_Nm"]):
            self.assertEqual(ref[d], m)
        self.assertEqual(t["source"]["sha256"], "7159a867c2c49d19a9e3ed2d7df229b70bbc2ddb753a6402302ae260762bd85b")

    def test_interpolation_error_against_the_reference(self):
        t = DP.table()
        q = np.radians(t["reference_deg"])
        err = np.abs(DP.mtj_ligament_moment(q) - np.asarray(t["reference_Nm"]))
        self.assertLess(err.max(), 0.15)                       # 0.5 deg knots; measured 0.09-0.13 N m
        self.assertTrue(DP.out_of_range(math.radians(31)) and not DP.out_of_range(math.radians(29.9)))


class Provenance(unittest.TestCase):
    """foot_models/PROVENANCE.json records the hashes needed to reproduce the port; they must agree with the code."""
    def test_recorded_hashes_agree_with_the_port(self):
        import json
        prov = json.loads((HERE / "foot_models" / "PROVENANCE.json").read_text())
        recorded = set(prov["dhondt"]["models"].values())
        self.assertEqual(recorded, set(DP.NOMINAL))
        self.assertEqual(prov["dhondt"]["saved_function"]["Polynomials/Fal_s1_mtjcf3_FK_sc_FDB2_MTc5/f_getMtjLigamentMoment_exp5"],
                         DP.table()["source"]["sha256"])
        self.assertEqual(prov["port"]["table_sha256"],
                         hashlib.sha256((HERE / "foot_models" / "dhondt2024_mtj_ligament_moment.json").read_bytes()).hexdigest())

    def test_committed_soles_match_the_recorded_hashes(self):
        import json
        soles = {k: v for k, v in json.loads((HERE / "foot_models" / "PROVENANCE.json").read_text())["soles"].items()
                 if k.startswith("sim/")}
        self.assertEqual(len(soles), 12)                       # 15, 10, 7.5, 5, 3.75, 2.5 mm; R and L
        for rel, want in soles.items():
            self.assertEqual(hashlib.sha256((HERE / rel).read_bytes()).hexdigest(), want, rel)


@unittest.skipIf(casadi is None or not EXP5, "needs casadi and DHONDT_EXP5")
class OriginalBspline(unittest.TestCase):
    def test_table_equals_the_saved_function(self):
        self.assertEqual(hashlib.sha256(Path(EXP5).read_bytes()).hexdigest(), DP.table()["source"]["sha256"])
        f = casadi.Function.load(EXP5)
        t = DP.table()
        for d, m in zip(t["reference_deg"], t["reference_Nm"]):
            self.assertAlmostEqual(float(f(math.radians(d))), m, places=9)


@unittest.skipIf(osim is None or not NOMINAL_DIR, "needs opensim and DHONDT_NOMINAL_DIR")
class PortedModels(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = Path(tempfile.mkdtemp())
        cls.src4 = Path(NOMINAL_DIR) / "DHondt_2024_4-segment_foot_fixed_knee.osim"
        cls.src3 = Path(NOMINAL_DIR) / "DHondt_2024_3-segment_foot_fixed_knee.osim"
        DP.port(cls.src4, cls.d / "p4.osim")
        DP.port(cls.src3, cls.d / "p3.osim")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.d, ignore_errors=True)

    def model(self, name):
        m = osim.Model(str(self.d / name)); s = m.initSystem()
        return m, s

    def test_midtarsal_ligaments_off_only_in_the_port(self):
        o = osim.Model(str(self.src4)); p, _ = self.model("p4.osim")
        for n in DP.MTJ_LIGAMENTS:
            for s in "rl":
                self.assertTrue(o.getForceSet().get(f"{n}_{s}").get_appliesForce())
                self.assertFalse(p.getForceSet().get(f"{n}_{s}").get_appliesForce())

    def test_fascia_tension_follows_natali(self):
        m, s = self.model("p4.osim")
        cs = m.getCoordinateSet()
        for side in "rl":
            L = osim.Ligament.safeDownCast(m.getForceSet().get(f"PlantarFascia_{side}"))
            worst = 0.0
            for qm in np.linspace(-0.2, 0.35, 12):
                for qp in np.linspace(-0.3, 0.6, 7):
                    cs.get(f"mtj_angle_{side}").setValue(s, qm, False); cs.get(f"mtp_angle_{side}").setValue(s, qp, False)
                    m.realizeDynamics(s)
                    l = L.getLength(s)
                    if l / 0.146 > DP.PF_CURVE_X[1]:
                        continue
                    want = natali_reference(l)
                    if l < 0.146:
                        # known difference: OpenSim's Ligament never pushes; the paper's smoothed law dips to
                        # -0.69 N within 0.9 mm below slack (an artefact of its tanh smoothing)
                        self.assertEqual(L.getTension(s), 0.0)
                        self.assertGreater(want, -0.7)
                        continue
                    worst = max(worst, abs(L.getTension(s) - want) / (0.05 + 2e-3 * abs(want)))
            self.assertLess(worst, 1.0, side)                  # within 0.05 N + 0.2 % (piecewise-linear curve)

    def test_midtarsal_generalized_force(self):
        m, s = self.model("p4.osim")
        t = DP.table(); K, th = DP.K_PASS["mtj"]
        for side in "rl":
            f = osim.ExpressionBasedCoordinateForce.safeDownCast(m.getForceSet().get(f"mtj_passive_{side}"))
            c = m.getCoordinateSet().get(f"mtj_angle_{side}")
            worst = 0.0
            for d, ref in zip(t["reference_deg"], t["reference_Nm"]):
                for qd in (0.0, 1.5):
                    q = math.radians(d)
                    c.setValue(s, q, False); c.setSpeedValue(s, qd); m.realizeDynamics(s)
                    want = ref + float(DP.falisse_passive(q, qd, K, th)) - (DP.DMT - 0.1) * qd
                    worst = max(worst, abs(f.getForceMagnitude(s) - want))
            self.assertLess(worst, 0.15, side)                 # against the paper's own bspline, -30..30 deg

    def test_mtp_generalized_force(self):
        for name, kind in (("p4.osim", "4-segment"), ("p3.osim", "3-segment")):
            m, s = self.model(name)
            k, dmp = DP.MTP_LINEAR[kind]; K, th = DP.K_PASS["mtp"]
            for side in "rl":
                f = osim.ExpressionBasedCoordinateForce.safeDownCast(m.getForceSet().get(f"mtp_passive_{side}"))
                c = m.getCoordinateSet().get(f"mtp_angle_{side}")
                for q in np.linspace(-0.35, 0.87, 25):
                    for qd in (0.0, -2.0):
                        c.setValue(s, q, False); c.setSpeedValue(s, qd); m.realizeDynamics(s)
                        want = -k * q - dmp * qd + float(DP.falisse_passive(q, qd, K, th))
                        self.assertAlmostEqual(f.getForceMagnitude(s), want, delta=1e-6 * max(1, abs(want)))

    def test_port_output_matches_the_recorded_hashes(self):
        import json
        if osim.__version__ != "4.6":
            self.skipTest(f"output hashes were recorded with OpenSim 4.6, this is {osim.__version__}")
        prov = json.loads((HERE / "foot_models" / "PROVENANCE.json").read_text())["port"]["outputs_sha256"]
        self.assertEqual(hashlib.sha256((self.d / "p4.osim").read_bytes()).hexdigest(), prov["4-segment ported"])
        self.assertEqual(hashlib.sha256((self.d / "p3.osim").read_bytes()).hexdigest(), prov["3-segment ported"])

    def test_other_files_are_refused(self):
        bad = self.d / "altered.osim"
        bad.write_bytes(self.src4.read_bytes() + b"\n")
        with self.assertRaises(SystemExit):
            DP.port(bad, self.d / "x.osim")
        self.assertFalse((self.d / "x.osim").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
