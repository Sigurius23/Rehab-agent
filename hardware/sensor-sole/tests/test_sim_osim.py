#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors
# SPDX-License-Identifier: CERN-OHL-S-2.0
"""Tests for sole_sim.add_to_osim on small OpenSim feet built here: a multi-segment foot (calcn -> midfoot ->
toes), and a foot whose toes do not hang from calcn, which must be refused. Needs the opensim package (the
pipeline's Python); skipped without it. Runs in seconds.

  python tests/test_sim_osim.py
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import sole_sim as SS  # noqa: E402

try:
    import opensim as osim
except ImportError:                                           # the generator's Python has no OpenSim
    osim = None


def foot_model(path, toes_on_calcn_chain=True):
    """Ground -> calcn (free) -> midfoot (pin at x = 30 mm) -> toes (pin at x = 70 mm in calcn), right foot.
    Generic contact: a heel sphere on calcn (heel point x = 0, plantar plane y = -20 mm) and one on midfoot.
    With toes_on_calcn_chain False, the toes hang from a separate shank body instead."""
    m = osim.Model()
    m.setName("test_foot")
    g = m.getGround()
    body = lambda n: osim.Body(n, 0.5, osim.Vec3(0), osim.Inertia(1e-3, 1e-3, 1e-3))
    calcn, mid, toes, shank = body("calcn_r"), body("midfoot_r"), body("toes_r"), body("shank_r")
    for b in (calcn, mid, toes, shank):
        m.addBody(b)
    m.addJoint(osim.FreeJoint("ground_calcn", g, osim.Vec3(0, 0.05, 0), osim.Vec3(0), calcn, osim.Vec3(0), osim.Vec3(0)))
    m.addJoint(osim.WeldJoint("ground_shank", g, osim.Vec3(0, 0.5, 0), osim.Vec3(0), shank, osim.Vec3(0), osim.Vec3(0)))
    m.addJoint(osim.PinJoint("mtj_r", calcn, osim.Vec3(0.03, 0, 0), osim.Vec3(0), mid, osim.Vec3(0), osim.Vec3(0)))
    parent = mid if toes_on_calcn_chain else shank
    m.addJoint(osim.PinJoint("mtp_r", parent, osim.Vec3(0.04, 0, 0), osim.Vec3(0), toes, osim.Vec3(0), osim.Vec3(0)))
    floor = osim.ContactHalfSpace(osim.Vec3(0), osim.Vec3(0, 0, -1.5707963267949), g, "floor")
    m.addContactGeometry(floor)
    for name, frame, at in (("heel_r", calcn, (0.01, -0.01, 0)), ("mid_r", mid, (0.0, -0.01, 0))):
        sp = osim.ContactSphere(0.01, osim.Vec3(*at), frame, name)
        m.addContactGeometry(sp)
        f = osim.SmoothSphereHalfSpaceForce(f"contact_{name}", sp, floor)
        f.set_stiffness(1e6); f.set_dissipation(2.0)
        m.addForce(f)
    m.finalizeConnections()
    m.initSystem()
    m.printToXML(str(path))


@unittest.skipIf(osim is None, "needs the opensim package")
class MultiSegmentFoot(unittest.TestCase):
    def sole(self, d):
        """A simulation sole written directly (export needs shapely, which the pipeline's Python lacks): a heel
        region from x = 11.5 to 31.5 mm, so it spans the midtarsal joint at 30 mm, and a toe region; bend at 70 mm."""
        s = dict(format=SS.FORMAT, board_id="TEST R 0123456789", design_hash="0" * 64, side="R",
                 bend=dict(point=[70.0, 0.0], dir=[0.0, 1.0]), point_spacing_mm=10.0,
                 contact_points=dict(heel=[[x, z] for x in (11.5, 21.5, 31.5) for z in (-10.0, 0.0, 10.0)],
                                     toe1=[[x, 0.0] for x in (75.0, 85.0)]),
                 contacts={"1": "COM", "2": "heel", "3": "toe1", "4": "COM"})
        q = Path(d) / "s.sole_sim.json"; q.write_text(json.dumps(s))
        return s, q

    def test_points_go_on_the_segment_they_lie_under(self):
        with tempfile.TemporaryDirectory() as d:
            sole, sj = self.sole(d)
            model = Path(d) / "foot.osim"; foot_model(model)
            meta = SS.add_to_osim(model, sj, Path(d) / "out.osim")
            # the toe joint is 70 mm from the heel in the calcn frame, but 40 mm in the midfoot's: reading it from
            # its own parent frame, as the two-segment code did, scaled this sole by 0.57
            self.assertAlmostEqual(meta["scale"], 1.0, places=6)
            m = osim.Model(str(Path(d) / "out.osim")); st = m.initSystem(); m.realizePosition(st)
            calcn = m.getBodySet().get("calcn_r")
            left = [g.getName() for g in m.getContactGeometrySet() if g.getConcreteClassName() == "ContactSphere"
                    and not g.getName().startswith("sole_")]
            self.assertEqual(left, [])                                # generic contact gone from every segment
            seen = set()
            for g in m.getContactGeometrySet():
                if not g.getName().startswith("sole_"):
                    continue
                sp = osim.ContactSphere.safeDownCast(g)
                p = g.getFrame().findStationLocationInAnotherFrame(st, sp.get_location(), calcn)
                x, y = p.get(0), p.get(1)
                self.assertAlmostEqual(y - sp.getRadius(), -0.02, places=9)   # on the plantar plane
                body = g.getFrame().getName(); seen.add(body)
                region = g.getName().split("_")[2]
                if region.startswith("toe"):
                    self.assertEqual(body, "toes_r")
                else:
                    self.assertEqual(body, "midfoot_r" if x >= 0.03 else "calcn_r", (g.getName(), x))
            self.assertEqual(seen, {"calcn_r", "midfoot_r", "toes_r"})
            self.assertEqual(meta["foot_chain"], ["calcn_r", "midfoot_r", "toes_r"])
            self.assertEqual(meta["toe_joint"], "mtp_r")
            self.assertEqual(meta["replaced_generic_on"], ["calcn_r", "midfoot_r"])

    def test_toes_not_reached_from_calcn_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            _, sj = self.sole(d)
            model = Path(d) / "foot.osim"; foot_model(model, toes_on_calcn_chain=False)
            with self.assertRaises(SystemExit) as e:
                SS.add_to_osim(model, sj, Path(d) / "out.osim")
            self.assertIn("not reached from calcn_r", str(e.exception))
            self.assertFalse((Path(d) / "out.osim").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
