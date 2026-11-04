#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors
# SPDX-License-Identifier: CERN-OHL-S-2.0
"""Tests for sole_sim.add_to_osim on small OpenSim feet built here (experimental adapter):
  - a multi-segment foot (calcn -> midfoot -> toes), and a foot whose toes do not hang from calcn (refused);
  - negative controls for contact the adapter must not change silently: geometry used by another force type,
    geometry used by no force, non-sphere geometry, a half-space on the foot, contact parameters that differ,
    contact on the talus, and a two-coordinate joint in the foot chain. Each must be refused before anything is
    written;
  - a toe joint whose rotation axis is not its frame's z axis, and an oblique midtarsal boundary: the measured
    axes must be used;
  - the registration residual report and the sensitivity perturbations.
Needs the opensim package (the pipeline's Python); skipped without it. Runs in seconds.

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


def small_sole(d):
    """A simulation sole written directly (export needs shapely, which the pipeline's Python lacks): a heel
    region from x = 11.5 to 31.5 mm, so it spans the midtarsal joint at 30 mm, and a toe region; bend at 70 mm."""
    s = dict(format=SS.FORMAT, board_id="TEST R 0123456789", design_hash="0" * 64, side="R",
             bend=dict(point=[70.0, 0.0], dir=[0.0, 1.0]), point_spacing_mm=10.0,
             contact_points=dict(heel=[[x, z] for x in (11.5, 21.5, 31.5) for z in (-10.0, 0.0, 10.0)],
                                 toe1=[[x, 0.0] for x in (75.0, 85.0)]),
             contacts={"1": "COM", "2": "heel", "3": "toe1", "4": "COM"})
    q = Path(d) / "s.sole_sim.json"; q.write_text(json.dumps(s))
    return s, q


@unittest.skipIf(osim is None, "needs the opensim package")
class MultiSegmentFoot(unittest.TestCase):
    def sole(self, d):
        return small_sole(d)

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


def oblique_custom(name, parent, ploc, child, axis, coord):
    """A CustomJoint rotating about `axis` (in the parent frame) with unrotated frames, so the axis is not the
    frame's z axis."""
    import numpy as np
    a = np.asarray(axis, float); a = a / np.linalg.norm(a)
    t = np.cross(a, [0, 1, 0]); t = t / np.linalg.norm(t); u = np.cross(a, t)
    st = osim.SpatialTransform()
    for i, (ax, fn, cn) in enumerate(((a, osim.LinearFunction(1, 0), coord), (t, osim.Constant(0), None),
                                      (u, osim.Constant(0), None))):
        ta = st.updTransformAxis(i)
        if cn:
            names = osim.ArrayStr(); names.append(cn); ta.setCoordinateNames(names)
        ta.setAxis(osim.Vec3(*ax)); ta.set_function(fn)
    for i in range(3, 6):
        st.updTransformAxis(i).set_function(osim.Constant(0))
    return osim.CustomJoint(name, parent, osim.Vec3(*ploc), osim.Vec3(0), child, osim.Vec3(0), osim.Vec3(0), st)


def foot2(path, extra=None, mid_axis=(0, 0, 1), toe_axis=(0, 0, 1), toe_centre=(0.07, 0, 0), universal=False):
    """Ground -> talus (free) -> calcn (weld) -> midfoot (joint at x = 30 mm) -> toes (joint at toe_centre, in
    calcn), right foot. Contact: a heel sphere on calcn (heel point x = 0, plantar plane y = -20 mm), one on the
    midfoot, one on the toes 2 mm below that plane, all SmoothSphereHalfSpaceForces against a floor on ground.
    `extra` adds one arrangement the adapter must refuse."""
    m = osim.Model(); m.setName("test_foot2"); g = m.getGround()
    body = lambda n: osim.Body(n, 0.5, osim.Vec3(0), osim.Inertia(1e-3, 1e-3, 1e-3))
    talus, calcn, mid, toes = body("talus_r"), body("calcn_r"), body("midfoot_r"), body("toes_r")
    for b in (talus, calcn, mid, toes):
        m.addBody(b)
    m.addJoint(osim.FreeJoint("ground_talus", g, osim.Vec3(0, 0.08, 0), osim.Vec3(0), talus, osim.Vec3(0), osim.Vec3(0)))
    m.addJoint(osim.WeldJoint("subtalar_r", talus, osim.Vec3(0, -0.03, 0), osim.Vec3(0), calcn, osim.Vec3(0), osim.Vec3(0)))
    if universal:
        m.addJoint(osim.UniversalJoint("mtj_r", calcn, osim.Vec3(0.03, 0, 0), osim.Vec3(0), mid, osim.Vec3(0), osim.Vec3(0)))
    else:
        m.addJoint(oblique_custom("mtj_r", calcn, (0.03, 0, 0), mid, mid_axis, "mtj_angle_r"))
    loc = (toe_centre[0] - 0.03, toe_centre[1], toe_centre[2])
    m.addJoint(oblique_custom("mtp_r", mid, loc, toes, toe_axis, "mtp_angle_r"))
    floor = osim.ContactHalfSpace(osim.Vec3(0), osim.Vec3(0, 0, -1.5707963267949), g, "floor")
    m.addContactGeometry(floor)
    on_foot_hs = None
    if extra == "halfspace_on_foot":
        on_foot_hs = osim.ContactHalfSpace(osim.Vec3(0, -0.02, 0), osim.Vec3(0, 0, -1.5707963267949), calcn, "pad")
        m.addContactGeometry(on_foot_hs)
    spheres = [("heel_r", calcn, (0.01, -0.01, 0)), ("mid_r", mid, (0.0, -0.01, 0)),
               ("toe_r", toes, (0.0, -0.012, 0.0 if toe_centre[2] == 0 else -toe_centre[2]))]
    if extra == "talus_sphere":
        spheres.append(("talus_s", talus, (0.0, -0.02, 0)))
    for name, frame, at in spheres:
        sp = osim.ContactSphere(0.01, osim.Vec3(*at), frame, name)
        m.addContactGeometry(sp)
        hs = on_foot_hs if (on_foot_hs is not None and name == "mid_r") else floor
        f = osim.SmoothSphereHalfSpaceForce(f"contact_{name}", sp, hs)
        f.set_stiffness(2e6 if (extra == "stiffness" and name == "mid_r") else 1e6); f.set_dissipation(2.0)
        m.addForce(f)
    if extra == "hunt_crossley":
        ball = osim.ContactSphere(0.008, osim.Vec3(0.01, -0.012, 0), toes, "ball_hc"); m.addContactGeometry(ball)
        hc = osim.HuntCrossleyForce(); hc.setName("hc_toe_r"); hc.setStiffness(1e6); hc.setDissipation(1.0)
        hc.addGeometry("ball_hc"); hc.addGeometry("floor"); m.addForce(hc)
    if extra == "unused":
        m.addContactGeometry(osim.ContactSphere(0.005, osim.Vec3(0.03, -0.01, 0.02), calcn, "spare_sphere"))
    if extra == "ellipsoid":
        m.addContactGeometry(osim.ContactEllipsoid(osim.Vec3(0.02, 0.01, 0.01), osim.Vec3(0.02, -0.01, 0), osim.Vec3(0), calcn, "pad_ellipsoid"))
    m.finalizeConnections(); m.initSystem(); m.printToXML(str(path))


@unittest.skipIf(osim is None, "needs the opensim package")
class FailsClosed(unittest.TestCase):
    """Arrangements the adapter must refuse, before anything is written (each one was changed silently, or failed
    inside OpenSim, before the adapter checked its input)."""
    def run_case(self, expect, **kw):
        with tempfile.TemporaryDirectory() as d:
            _, sj = small_sole(d)
            model = Path(d) / "foot.osim"; foot2(model, **kw)
            with self.assertRaises(SS.UnsupportedModel) as e:
                SS.add_to_osim(model, sj, Path(d) / "out.osim")
            self.assertIn(expect, str(e.exception))
            self.assertFalse((Path(d) / "out.osim").exists())
            self.assertFalse((Path(d) / "out.sole_sim_meta.json").exists())

    def test_geometry_used_by_another_force_type(self):
        self.run_case("used by [('HuntCrossleyForce', 'hc_toe_r')]", extra="hunt_crossley")

    def test_geometry_used_by_no_force(self):
        self.run_case("'spare_sphere' on calcn_r is used by no force", extra="unused")

    def test_non_sphere_geometry_on_the_foot(self):
        self.run_case("ContactEllipsoid 'pad_ellipsoid' on calcn_r", extra="ellipsoid")

    def test_half_space_on_the_foot(self):
        self.run_case("half-space 'pad' is on calcn_r, not on ground", extra="halfspace_on_foot")

    def test_differing_contact_parameters(self):
        self.run_case("different parameter sets", extra="stiffness")

    def test_contact_on_the_talus(self):
        self.run_case("'talus_s' on talus_r, outside the calcn-to-toes chain", extra="talus_sphere")

    def test_two_coordinate_joint_in_the_chain(self):
        self.run_case("mtj_r in the foot chain has 2 coordinates", universal=True)

    def test_keep_generic_tolerates_unused_geometry(self):
        with tempfile.TemporaryDirectory() as d:
            _, sj = small_sole(d)
            model = Path(d) / "foot.osim"; foot2(model, extra="unused")
            meta = SS.add_to_osim(model, sj, Path(d) / "out.osim", keep_generic=True)
            self.assertEqual(meta["replaced_spheres"], [])          # nothing removed, so nothing to refuse


@unittest.skipIf(osim is None, "needs the opensim package")
class MeasuredAxes(unittest.TestCase):
    def test_toe_line_follows_the_measured_axis(self):
        """Toe joint at z = 20 mm rotating 30 deg off its frame's z axis: its line crosses z = 0 at x = 81.5 mm,
        not 70 mm. Reading the frame's z axis (the earlier code) gave a scale of 1.0 instead of 1.165."""
        with tempfile.TemporaryDirectory() as d:
            _, sj = small_sole(d)
            model = Path(d) / "foot.osim"
            foot2(model, toe_axis=(-0.5, 0, 0.8660254), toe_centre=(0.07, 0, 0.02))
            meta = SS.add_to_osim(model, sj, Path(d) / "out.osim")
            self.assertAlmostEqual(meta["scale"], (0.07 + 0.02 * 0.5 / 0.8660254) / 0.07, places=4)
            ax = meta["registration"]["mtp_axis"]
            self.assertAlmostEqual(ax[0], -0.5, places=3); self.assertAlmostEqual(ax[2], 0.866, places=3)
            self.assertAlmostEqual(meta["registration_residuals"]["toe_axis_from_z_deg"], -30.0, places=1)

    def test_segment_boundary_follows_an_oblique_axis(self):
        """Midtarsal axis 30 deg off z, through x = 30 mm: (35, +20) mm lies proximal of it and (25, -20) mm
        distal, the opposite of a straight line across the foot at x = 30 mm."""
        with tempfile.TemporaryDirectory() as d:
            s, _ = small_sole(d)
            s["contact_points"] = dict(heel=[[35.0, 20.0], [25.0, -20.0]], toe1=[[80.0, 0.0]])
            sj = Path(d) / "s2.json"; sj.write_text(json.dumps(s))
            model = Path(d) / "foot.osim"; foot2(model, mid_axis=(0.5, 0, 0.8660254))
            SS.add_to_osim(model, sj, Path(d) / "out.osim")
            m = osim.Model(str(Path(d) / "out.osim"))
            frame = {g.getName(): g.getFrame().getName() for g in m.getContactGeometrySet()}
            self.assertEqual(frame["sole_r_heel_00"], "calcn_r")
            self.assertEqual(frame["sole_r_heel_01"], "midfoot_r")


@unittest.skipIf(osim is None, "needs the opensim package")
class ResidualsAndPerturbation(unittest.TestCase):
    def test_residuals_report_the_model_contact_off_the_plane(self):
        with tempfile.TemporaryDirectory() as d:
            _, sj = small_sole(d)
            model = Path(d) / "foot.osim"; foot2(model)
            meta = SS.add_to_osim(model, sj, Path(d) / "out.osim")
            r = meta["registration_residuals"]
            self.assertEqual(r["generic_sphere_bottoms_vs_plane_mm"]["toes_r"], [-2.0])
            self.assertIn("experimental", meta["status"])
            self.assertEqual(sorted(meta["replaced_spheres"]), ["heel_r", "mid_r", "toe_r"])

    def test_lateral_shift_and_unknown_key(self):
        with tempfile.TemporaryDirectory() as d:
            _, sj = small_sole(d)
            model = Path(d) / "foot.osim"; foot2(model)
            SS.add_to_osim(model, sj, Path(d) / "a.osim")
            SS.add_to_osim(model, sj, Path(d) / "b.osim", perturb=dict(lateral_mm=5.0))
            ma, mb = osim.Model(str(Path(d) / "a.osim")), osim.Model(str(Path(d) / "b.osim"))
            za = ma.getContactGeometrySet().get("sole_r_heel_04")
            zb = mb.getContactGeometrySet().get("sole_r_heel_04")
            self.assertAlmostEqual(osim.ContactSphere.safeDownCast(zb).get_location().get(2) -
                                   osim.ContactSphere.safeDownCast(za).get_location().get(2), 0.005, places=9)
            with self.assertRaises(ValueError):
                SS.add_to_osim(model, sj, Path(d) / "c.osim", perturb=dict(shear=1.0))


@unittest.skipIf(osim is None, "needs the opensim package")
class AssumedContact(unittest.TestCase):
    def test_calibration_hits_the_target_force(self):
        c = SS.ASSUMED_CONTACT_V1
        r, target, depth = 0.0075, 22.5, 0.003
        E = SS.calibrate_stiffness(r, target, depth, c)
        m = osim.Model(); g = m.getGround()
        b = osim.Body("b", 1.0, osim.Vec3(0), osim.Inertia(1e-3)); m.addBody(b)
        m.addJoint(osim.SliderJoint("j", g, osim.Vec3(0), osim.Vec3(0, 0, 1.5707963267949), b, osim.Vec3(0),
                                    osim.Vec3(0, 0, 1.5707963267949)))
        hs = osim.ContactHalfSpace(osim.Vec3(0), osim.Vec3(0, 0, -1.5707963267949), g, "floor"); m.addContactGeometry(hs)
        sp = osim.ContactSphere(r, osim.Vec3(0), b, "s"); m.addContactGeometry(sp)
        f = osim.SmoothSphereHalfSpaceForce("c", sp, hs); f.set_stiffness(E)
        for k in ("dissipation", "static_friction", "dynamic_friction", "viscous_friction", "transition_velocity",
                  "constant_contact_force", "hertz_smoothing", "hunt_crossley_smoothing"):
            getattr(f, f"set_{k}")(c[k])
        m.addForce(f)
        st = m.initSystem(); q = m.getCoordinateSet().get(0)
        got = {}
        for d in (-0.002, 0.001, 0.003, 0.006):
            q.setValue(st, r - d); m.realizeDynamics(st)
            lab, val = f.getRecordLabels(), f.getRecordValues(st)
            got[d] = [val.get(i) for i in range(lab.size()) if lab.get(i).endswith(".Sphere.force.Y")][0]
        self.assertAlmostEqual(got[0.003], target, delta=1e-6 * target)
        self.assertAlmostEqual(got[0.006] / got[0.003], 2 ** 1.5, delta=0.01)       # Hertz exponent
        self.assertAlmostEqual(got[0.001] / got[0.003], (1 / 3) ** 1.5, delta=0.01)
        self.assertLess(got[-0.002], 1e-3 * target)                                 # nothing above the floor

    def test_same_law_whatever_the_model_contact(self):
        with tempfile.TemporaryDirectory() as d:
            _, sj = small_sole(d)
            soft, stiff = Path(d) / "soft.osim", Path(d) / "stiff.osim"
            foot2(soft)
            text = soft.read_text().replace("<stiffness>1000000</stiffness>", "<stiffness>10000000</stiffness>")
            self.assertIn("<stiffness>10000000</stiffness>", text)
            stiff.write_text(text)
            a = SS.add_to_osim(soft, sj, Path(d) / "a.osim", contact=SS.ASSUMED_CONTACT_V1)
            b = SS.add_to_osim(stiff, sj, Path(d) / "b.osim", contact=SS.ASSUMED_CONTACT_V1)
            self.assertEqual(a["stiffness_per_sphere"], b["stiffness_per_sphere"])
            self.assertEqual(a["contact_model"]["status"], "assumed, not measured")
            n1 = SS.add_to_osim(soft, sj, Path(d) / "n1.osim"); n2 = SS.add_to_osim(stiff, sj, Path(d) / "n2.osim")
            self.assertAlmostEqual(n2["stiffness_per_sphere"] / n1["stiffness_per_sphere"], 10.0, places=6)
            self.assertEqual(n1["contact_model"]["name"], "native")
            m = osim.Model(str(Path(d) / "a.osim"))
            f = osim.SmoothSphereHalfSpaceForce.safeDownCast(m.getForceSet().get("force_sole_r_heel_00"))
            self.assertEqual(f.get_hertz_smoothing(), 2000.0)
            self.assertEqual(f.get_constant_contact_force(), 1e-8)


if __name__ == "__main__":
    unittest.main(verbosity=2)
