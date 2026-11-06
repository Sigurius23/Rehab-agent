#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors
# SPDX-License-Identifier: CERN-OHL-S-2.0
"""Checks of foot_models/opencap_contacts.py (foot contact spheres by OpenCap's own rule), on the pipeline's self-test
model with its own foot contact removed (SELFTEST_MODEL):
  - twelve spheres of radius 0.032 m at the rule's locations: x and z scaled by the body's geometry scale factors
    over the reference 0.913924, y (the height) not scaled; one ground half-space; the rule's contact parameters;
  - nothing else in the model changes (body masses, coordinates);
  - a model that already has contact geometry is refused;
  - the comparison used against OpenCap's own function finds a moved sphere, a changed stiffness and a changed
    body mass (its negative controls), and finds nothing between a model and itself.
With OPENCAP_UTILS set to opencap-processing's utilsProcessing.py at commit 72b5416: OpenCap's function and this
file give the same model (locations to 1e-9 m).
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "foot_models"))
try:
    import opensim as osim
    import opencap_contacts as OC
    HAVE_OPENSIM = True
except ImportError:
    HAVE_OPENSIM = False
MODEL = os.environ.get("SELFTEST_MODEL")
UTILS = os.environ.get("OPENCAP_UTILS")
need_model = unittest.skipUnless(HAVE_OPENSIM and MODEL and Path(MODEL or "").is_file(), "needs opensim and SELFTEST_MODEL")


def without_contact(model_in, out):
    """The model with every contact force and contact geometry removed (edited as XML: removing components through
    the API and then reconnecting crashes OpenSim 4.6)."""
    import xml.etree.ElementTree as ET
    tree = ET.parse(str(model_in))
    model = tree.getroot().find("Model")
    for set_name, kinds in (("ForceSet", ("SmoothSphereHalfSpaceForce", "HuntCrossleyForce", "ElasticFoundationForce")),
                            ("ContactGeometrySet", None)):
        objects = model.find(set_name).find("objects")
        for child in list(objects):
            if kinds is None or child.tag in kinds:
                objects.remove(child)
    tree.write(str(out), xml_declaration=True, encoding="UTF-8")
    osim.Model(str(out)).initSystem()                                   # still a valid model
    return out


def edited(model_in, out, fn):
    m = osim.Model(str(model_in))
    fn(m)
    m.finalizeConnections()
    m.initSystem()
    m.printToXML(str(out))
    return out


@need_model
class OpenCapContactRule(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        d = Path(cls.tmp.name)
        cls.bare = without_contact(MODEL, d / "selftest_scaled.osim")       # the "_scaled" name OpenCap's function needs
        cls.out = d / "selftest_contacts.osim"
        cls.rec = OC.add_contacts(cls.bare, cls.out)
        cls.geo, cls.forces, cls.masses = OC.read_contacts(cls.out)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_spheres_at_the_rules_locations(self):
        spheres = {n: g for n, g in self.geo.items() if g["kind"] == "ContactSphere"}
        self.assertEqual(sorted(spheres), sorted(OC.REFERENCE_SPHERES))
        m = osim.Model(str(self.bare))
        for n, (radius, loc, body) in OC.REFERENCE_SPHERES.items():
            g = m.getBodySet().get(body).get_attached_geometry(0).get_scale_factors()
            want = (loc[0] * g.get(0) / OC.REFERENCE_SCALE, loc[1], loc[2] * g.get(2) / OC.REFERENCE_SCALE)
            with self.subTest(sphere=n):
                self.assertEqual(spheres[n]["frame"], body)
                self.assertEqual(spheres[n]["radius"], 0.032)
                for a, b in zip(spheres[n]["location"], want):
                    self.assertAlmostEqual(a, b, delta=1e-12)
                self.assertEqual(spheres[n]["location"][1], -0.01)               # the height is not scaled

    def test_half_space_and_contact_parameters(self):
        hs = self.geo["floor"]
        self.assertEqual((hs["kind"], hs["frame"]), ("ContactHalfSpace", "ground"))
        self.assertEqual(hs["location"], [0.0, 0.0, 0.0])
        self.assertAlmostEqual(hs["orientation"][2], -1.5707963267948966, delta=1e-15)
        self.assertEqual(len(self.forces), 12)
        for name, f in self.forces.items():
            with self.subTest(force=name):
                self.assertEqual(name, "SmoothSphereHalfSpaceForce_" + f["sphere"].rsplit("/", 1)[-1])
                self.assertTrue(f["half_space"].endswith("floor"))
                for k, v in OC.CONTACT.items():
                    self.assertEqual(f[k], v)

    def test_nothing_else_changes(self):
        _, _, before = OC.read_contacts(self.bare)
        self.assertEqual(self.masses, before)
        a, b = osim.Model(str(self.bare)), osim.Model(str(self.out))
        self.assertEqual([c.getName() for c in a.getCoordinateSet()], [c.getName() for c in b.getCoordinateSet()])

    def test_a_model_with_contact_is_refused(self):
        with self.assertRaises(ValueError):
            OC.add_contacts(MODEL, Path(self.tmp.name) / "twice.osim")

    def test_comparison_finds_differences(self):
        d = Path(self.tmp.name)
        self.assertEqual(OC.compare(self.out, self.out), [])

        def move(m):
            sp = osim.ContactSphere.safeDownCast(m.getContactGeometrySet().get("s3_r"))
            v = sp.get_location(); sp.set_location(osim.Vec3(v.get(0) + 1e-8, v.get(1), v.get(2)))

        def stiffer(m):
            osim.SmoothSphereHalfSpaceForce.safeDownCast(m.getForceSet().get("SmoothSphereHalfSpaceForce_s2_l")).set_stiffness(1e6 + 1)

        def heavier(m):
            b = m.getBodySet().get("toes_r"); b.setMass(b.getMass() + 1e-6)
        for name, fn in (("moved sphere", move), ("stiffness", stiffer), ("body mass", heavier)):
            with self.subTest(change=name):
                self.assertNotEqual(OC.compare(self.out, edited(self.out, d / f"{name}.osim", fn)), [])

    @unittest.skipUnless(UTILS and Path(UTILS or "").is_file(), "needs OPENCAP_UTILS (opencap-processing's utilsProcessing.py at 72b5416)")
    def test_opencaps_function_gives_the_same_model(self):
        with tempfile.TemporaryDirectory() as w:
            theirs = OC.run_opencap_function(UTILS, self.bare, w)
            self.assertEqual(OC.compare(self.out, theirs), [])


if __name__ == "__main__":
    unittest.main()
