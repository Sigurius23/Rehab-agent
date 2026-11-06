#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors
# SPDX-License-Identifier: CERN-OHL-S-2.0
"""Checks of foot_models/double_support.py on kinematics alone (no force data), before any force data is opened.

On the pipeline's two-segment self-test model (SELFTEST_MODEL; a left/right symmetric model), with the assumed
contact v1:
  - support equals body weight, and the total centre of pressure lies under the centre of mass, in symmetric,
    asymmetric and squat-like postures;
  - in a mirrored posture left and right are mirror images: a symmetric posture loads both feet equally, and
    mirroring an asymmetric posture swaps the feet's forces and centres of pressure. The left foot gets a mirrored
    copy of the right sole, so the check is of the solver, not of the two boards' small differences;
  - a synthetic sideways lean of the trunk shifts load to the side it leans to, and the opposite lean to the other;
  - from a start rolled so that one foot is off the floor, the solve reaches the same solution (the 2026-11-05
    solver did not, from 2 degrees on; found on OpenCap LabValidation's kinematics).
Runs: frames solved in parallel give the same results as one at a time; a second run reuses every finished frame;
a frame whose completion record is missing (an interrupted run) is solved again, and only that one; only the
selected frames are solved; a frame selection made from other inverse kinematics is refused.
Without the model: the quasi-static frame rule on synthetic centre-of-mass paths, and the refusal to read files
named like force data.
"""
import json
import math
import os
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "foot_models"))
try:
    import numpy as np
    import scipy  # noqa: F401
    import double_support as DS
    HAVE_NUMPY = True
except ImportError:
    HAVE_NUMPY = False
try:
    import opensim  # noqa: F401
    HAVE_OPENSIM = True
except ImportError:
    HAVE_OPENSIM = False
MODEL = os.environ.get("SELFTEST_MODEL")
SOLE_R = HERE / "sim" / "EU42_R_636645a928.sole_sim.json"
SOLE_L = HERE / "sim" / "EU42_L_40fe8e1d0c.sole_sim.json"
need_model = unittest.skipUnless(HAVE_NUMPY and HAVE_OPENSIM and MODEL and Path(MODEL or "").is_file(),
                                 "needs opensim, scipy and SELFTEST_MODEL")


@unittest.skipUnless(HAVE_NUMPY, "needs numpy and scipy")
class FrameRule(unittest.TestCase):
    """The plan's quasi-static rule: centre-of-mass acceleration below 0.1 m/s^2 after a 6 Hz low-pass, in
    stretches of at least 0.2 s."""
    dt = 0.01

    def test_still_body_is_quasi_static_throughout(self):
        t = np.arange(0, 2, self.dt)
        com = np.tile([0.1, 0.9, 0.0], (len(t), 1))
        mask, stretches, _ = DS.quasi_static(t, com)
        self.assertTrue(mask.all())
        self.assertEqual(len(stretches), 1)

    def test_accelerating_body_is_not(self):
        t = np.arange(0, 2, self.dt)
        com = np.column_stack([0.05 * np.sin(2 * math.pi * 1.0 * t), 0.9 + 0 * t, 0 * t])   # peak 2 m/s^2
        mask, _, mag = DS.quasi_static(t, com)
        self.assertFalse(mask[20:-20].any())
        self.assertGreater(mag.max(), 1.0)

    def test_short_still_stretches_are_dropped_and_long_ones_kept(self):
        # a 1 Hz sway (peak 2 m/s^2) that holds still twice, each time at a peak where its speed is zero: for
        # 0.12 s, then for 0.7 s. Only the long hold may give quasi-static frames.
        holds, p, left, t, x, windows = [(1.25, 0.12), (2.75, 0.7)], 0.0, 0.0, [], [], []
        for i in range(500):
            ti = i * self.dt
            if left <= 1e-12 and holds and p >= holds[0][0] - 1e-9:
                left = holds[0][1]; windows.append((ti, ti + left)); holds.pop(0)
            t.append(ti); x.append(0.05 * math.sin(2 * math.pi * p))
            if left > 1e-12:
                left -= self.dt
            else:
                p += self.dt
        t, x = np.array(t), np.array(x)
        mask, stretches, _ = DS.quasi_static(t, np.column_stack([x, 0.9 + 0 * t, 0 * t]))
        (s0, e0), (s1, e1) = windows
        self.assertFalse(mask[(t >= s0) & (t < e0)].any())
        self.assertTrue(stretches)
        for s, e, n in stretches:
            self.assertGreaterEqual(n * self.dt, 0.2 - 1e-9)
            self.assertTrue(s1 - 1e-9 <= s and e <= e1 + 1e-9, (s, e, windows))

    def test_uneven_frames_are_refused(self):
        t = np.array([0, 0.01, 0.02, 0.04, 0.05])
        with self.assertRaises(ValueError):
            DS.quasi_static(t, np.zeros((5, 3)))


@unittest.skipUnless(HAVE_NUMPY, "needs numpy and scipy")
class KinematicsOnly(unittest.TestCase):
    def test_force_files_are_refused(self):
        for name in ("squats1_forces.mot", "GRF_squat.mot", "ForceData/squats1.mot", "squat.anc", "emg_squat.mot"):
            with self.subTest(name=name), self.assertRaises(PermissionError):
                DS.load_mot(Path("/nonexistent") / name)

    def test_ik_files_are_read(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "squats1.mot"
            p.write_text("Coordinates\nversion=1\nnRows=2\nnColumns=3\ninDegrees=yes\nendheader\n"
                         "time\tknee_angle_r\tpelvis_ty\n0.00\t10.0\t0.9\n0.01\t11.0\t0.9\n")
            t, names, data, deg = DS.load_mot(p)
            self.assertTrue(deg)
            self.assertEqual(names, ["knee_angle_r", "pelvis_ty"])
            self.assertEqual(data.shape, (2, 2))


def mirrored_left_sole(path_r, out):
    """The right sole mirrored into an exact left one. Sole files give z to the right on both feet, so a left sole
    is the right one with z negated (as the committed EU 42 pair's centroids, areas and bend line are)."""
    s = json.loads(Path(path_r).read_text())
    mz = lambda pts: [[x, -z] for x, z in pts]
    s["side"] = "L"
    s["board_id"] = s["board_id"].replace(" R ", " L ") + " (test: mirror of the right sole)"
    s["contact_points"] = {n: mz(p) for n, p in s["contact_points"].items()}
    for reg in s["regions"].values():
        reg["outline"] = mz(reg["outline"])
        reg["centroid"] = [reg["centroid"][0], -reg["centroid"][1]]
    s["bend"] = dict(point=[s["bend"]["point"][0], -s["bend"]["point"][1]], dir=[s["bend"]["dir"][0], -s["bend"]["dir"][1]])
    Path(out).write_text(json.dumps(s))
    return out


@need_model
class DoubleSupportOnTheSelfTestModel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        d = Path(cls.tmp.name)
        cls.ds = DS.DoubleSupport(MODEL, SOLE_R, mirrored_left_sole(SOLE_R, d / "L_mirror.sole_sim.json"), d / "mirror")
        dep = {c for c, *_ in DS.Posture(cls.ds.m, [], True).couplers}
        cls.names = [c.getName() for c in cls.ds.cs if c.getName() not in dep]
        cls.ty0 = cls.ds.cs.get("pelvis_ty").getDefaultValue()

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def solve(self, ds=None, **deg):
        """Solve a synthetic posture (degrees). As in measured standing and squats, and as compare_feet.build does,
        the pelvis tilt is set so that the feet start level; the solve then adjusts the ankles."""
        ds = ds or self.ds
        names = [c.getName() for c in ds.cs if c.getName() in self.names]
        posture = DS.Posture(ds.m, names, True)
        deg = dict(deg)
        row = lambda: [deg.get(n, self.ty0 if n == "pelvis_ty" else 0.0) for n in names]
        posture.apply(ds.st, row()); ds.m.realizePosition(ds.st)
        pitch = []
        for s in "rl":
            R = ds.m.getBodySet().get(f"calcn_{s}").getTransformInGround(ds.st).R()
            pitch.append(math.degrees(math.atan2(R.get(1, 0), math.hypot(R.get(0, 0), R.get(2, 0)))))
        deg["pelvis_tilt"] = deg.get("pelvis_tilt", 0.0) - sum(pitch) / 2
        r = ds.solve(posture, row())
        self.assertTrue(r["solved"], r)
        return r

    # Postures that keep the centre of mass over the middle of the feet, as a person standing or squatting does
    # (with the feet levelled: standing near 50 % of the heel-to-toe span, the squat near 46 %). The model's
    # default pose puts it near the heels, where no rigid equilibrium is well defined.
    STAND = dict(ankle_angle_r=5, ankle_angle_l=5)
    SQUAT = dict(hip_flexion_r=50, hip_flexion_l=50, knee_angle_r=60, knee_angle_l=60, ankle_angle_r=25,
                 ankle_angle_l=25, L5_S1_Flex_Ext=-10)
    ASYM = dict(hip_flexion_r=8, hip_flexion_l=2, knee_angle_r=10, knee_angle_l=3, ankle_angle_r=6, ankle_angle_l=4,
                hip_adduction_r=-2, hip_adduction_l=1, pelvis_list=1.0, L5_S1_Lat_Bending=3)

    @staticmethod
    def mirror(p):
        out = {}
        for n, v in p.items():
            if n.endswith("_r"):
                out[n[:-2] + "_l"] = v
            elif n.endswith("_l"):
                out[n[:-2] + "_r"] = v
            elif n in ("pelvis_list", "pelvis_rotation", "pelvis_tz", "L5_S1_Lat_Bending", "L5_S1_axial_rotation"):
                out[n] = -v
            else:
                out[n] = v
        return out

    def assert_supported(self, r):
        self.assertLess(abs(r["support_error_pct"]), 0.01)
        tot = r["R"]["vertical_N"] + r["L"]["vertical_N"]
        cop = [(r["R"]["vertical_N"] * r["R"]["cop_ground_m"][i] + r["L"]["vertical_N"] * r["L"]["cop_ground_m"][i]) / tot
               for i in range(2)]
        self.assertAlmostEqual(cop[0], r["com_ground_m"][0], delta=5e-4)     # under the centre of mass
        self.assertAlmostEqual(cop[1], r["com_ground_m"][2], delta=5e-4)
        # the split between the feet is the lever rule about the centre of mass, across the forward axis
        fx, fz = r["forward_axis"]
        side = lambda p: -fz * p[0] + fx * p[1]
        lever = 100 * (side([r["com_ground_m"][0], r["com_ground_m"][2]]) - side(r["L"]["cop_ground_m"])) / (
            side(r["R"]["cop_ground_m"]) - side(r["L"]["cop_ground_m"]))
        self.assertAlmostEqual(r["right_share_pct"], lever, delta=0.02)

    def test_support_equals_body_weight(self):
        for name, p in (("standing", self.STAND), ("squat-like", self.SQUAT), ("asymmetric", self.ASYM)):
            with self.subTest(posture=name):
                r = self.solve(**p)
                self.assertAlmostEqual(r["body_weight_N"], 70.0 * 9.80665, places=2)
                self.assert_supported(r)
                for k in ("pelvis_list_deg", "ankle_angle_r_deg", "ankle_angle_l_deg"):
                    self.assertLess(abs(r["solved_minus_measured"][k]), 3.0, (k, r["solved_minus_measured"]))
                for s in "RL":                                               # each foot under the centre of mass
                    self.assertLess(abs(r[s]["cop_ahead_of_com_mm"]), 0.5)

    def test_support_with_the_real_left_sole(self):
        ds = DS.DoubleSupport(MODEL, SOLE_R, SOLE_L, Path(self.tmp.name) / "real")
        self.assert_supported(self.solve(ds, **self.SQUAT))

    def test_symmetric_posture_loads_both_feet_equally(self):
        for name, p in (("standing", self.STAND), ("squat-like", self.SQUAT)):
            with self.subTest(posture=name):
                r = self.solve(**p)
                # 50 % but for the self-test model's own asymmetry: its centre of mass is 0.03 mm right of the
                # midline in these postures, worth about 0.016 points by the lever rule (checked in assert_supported)
                self.assert_supported(r)
                self.assertAlmostEqual(r["right_share_pct"], 50.0, delta=0.05)
                self.assertAlmostEqual(r["R"]["cop_sole_mm"][0], r["L"]["cop_sole_mm"][0], delta=0.05)
                self.assertAlmostEqual(r["R"]["cop_sole_mm"][1], -r["L"]["cop_sole_mm"][1], delta=0.05)   # z mirrored
                self.assertAlmostEqual(r["R"]["cop_ground_m"][1], -r["L"]["cop_ground_m"][1], delta=5e-5)

    def test_mirrored_posture_swaps_the_feet(self):
        a, b = self.solve(**self.ASYM), self.solve(**self.mirror(self.ASYM))
        self.assertGreater(abs(a["right_share_pct"] - 50.0), 0.5)          # the posture does load one foot more
        for s, o in (("R", "L"), ("L", "R")):
            self.assertAlmostEqual(a[s]["vertical_N"], b[o]["vertical_N"], delta=5e-4 * a["body_weight_N"])
            self.assertAlmostEqual(a[s]["cop_sole_mm"][0], b[o]["cop_sole_mm"][0], delta=0.05)
            self.assertAlmostEqual(a[s]["cop_sole_mm"][1], -b[o]["cop_sole_mm"][1], delta=0.05)

    def test_sideways_lean_shifts_load_to_that_side(self):
        base = self.solve(**self.STAND)
        right_is_plus_z = base["R"]["cop_ground_m"][1] > base["L"]["cop_ground_m"][1]
        for lean in (8.0, -8.0):
            with self.subTest(lean=lean):
                r = self.solve(**self.STAND, L5_S1_Lat_Bending=lean)
                dz = r["com_ground_m"][2] - base["com_ground_m"][2]
                self.assertGreater(abs(dz), 0.005)                           # the lean moves the centre of mass
                towards_right = (dz > 0) == right_is_plus_z
                shift = r["right_share_pct"] - base["right_share_pct"]
                self.assertGreater(shift if towards_right else -shift, 2.0, (lean, dz, shift))
        a, b = self.solve(**self.STAND, L5_S1_Lat_Bending=8.0), self.solve(**self.STAND, L5_S1_Lat_Bending=-8.0)
        self.assertAlmostEqual(a["right_share_pct"] - 50.0, 50.0 - b["right_share_pct"], delta=0.05)

    def test_a_start_with_one_foot_off_the_floor_reaches_the_same_solution(self):
        # On OpenCap LabValidation's kinematics, starts where one foot barely touched ended on another root (one foot
        # on its toe tip, the roll at its bound) or in the air. The staged start fixes that; the solver committed on
        # 2026-11-05 fails this test from 2 degrees on, which is its negative control.
        ref = self.solve(**self.ASYM)
        start = self.ds._start
        try:
            for tilt in (2.0, -2.0, 4.0, -4.0):
                self.ds._start = lambda *a, tilt=tilt, **k: start(*a, **k) + np.array([0.0, math.radians(tilt), 0.0, 0.0])
                with self.subTest(tilt=tilt):
                    r = self.solve(**self.ASYM)
                    for s in "RL":
                        self.assertAlmostEqual(r[s]["vertical_N"], ref[s]["vertical_N"], delta=0.01)
        finally:
            del self.ds._start


@need_model
class ResumableParallelRuns(unittest.TestCase):
    """run_solve on a synthetic standing trial of the self-test model: four frames, three of them selected."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        d = cls.d = Path(cls.tmp.name)
        ds = DS.DoubleSupport(MODEL, SOLE_R, SOLE_L, d / "levelling")
        dep = {c for c, *_ in DS.Posture(ds.m, [], True).couplers}
        names = [c.getName() for c in ds.cs if c.getName() not in dep]
        posture = DS.Posture(ds.m, names, True)
        ty0 = ds.cs.get("pelvis_ty").getDefaultValue()
        rows = []
        for k, ankle in enumerate((5.0, 5.5, 6.0, 6.5)):
            deg = dict(ankle_angle_r=ankle, ankle_angle_l=ankle)
            row = lambda: [deg.get(n, ty0 if n == "pelvis_ty" else 0.0) for n in names]
            posture.apply(ds.st, row()); ds.m.realizePosition(ds.st)
            pitch = [math.degrees(math.atan2(R.get(1, 0), math.hypot(R.get(0, 0), R.get(2, 0))))
                     for R in (ds.m.getBodySet().get(f"calcn_{s}").getTransformInGround(ds.st).R() for s in "rl")]
            deg["pelvis_tilt"] = -sum(pitch) / 2                         # the feet start level, as in the tests above
            rows.append([0.01 * k] + row())
        cls.ik = d / "stand1.mot"
        cls.ik.write_text("Coordinates\nversion=1\nnRows=4\nnColumns=%d\ninDegrees=yes\nendheader\n" % (len(names) + 1)
                          + "\t".join(["time"] + names) + "\n"
                          + "".join("\t".join(f"{v:.10g}" for v in r) + "\n" for r in rows))
        cls.frames = d / "frames.json"
        cls.frames.write_text(json.dumps(dict(trials={"stand1.mot": dict(ik_sha256=DS.sha256(cls.ik),
                                                                            stretches_s=[[0.0, 0.02, 3]])})))
        cls.serial = DS.run_solve(MODEL, SOLE_R, SOLE_L, [cls.ik], cls.frames, d / "serial", jobs=1)
        cls.parallel = DS.run_solve(MODEL, SOLE_R, SOLE_L, [cls.ik], cls.frames, d / "parallel", jobs=2)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def solved_frames(self, res):
        return res["trials"]["stand1.mot"]["frames"]

    def test_only_the_selected_frames_are_solved(self):
        self.assertEqual([r["time"] for r in self.solved_frames(self.serial)], [0.0, 0.01, 0.02])
        self.assertEqual(self.serial["trials"]["stand1.mot"]["solved"], 3)

    def test_parallel_equals_serial(self):
        self.assertEqual(self.parallel["run"]["computed"], 3)
        self.assertEqual(self.solved_frames(self.parallel), self.solved_frames(self.serial))

    def test_second_run_reuses_and_an_interrupted_frame_is_repeated(self):
        out = self.d / "parallel"
        again = DS.run_solve(MODEL, SOLE_R, SOLE_L, [self.ik], self.frames, out, jobs=2)
        self.assertEqual((again["run"]["reused_from_earlier_run"], again["run"]["computed"]), (3, 0))
        self.assertEqual(self.solved_frames(again), self.solved_frames(self.serial))
        records = sorted((out / "cases" / "stand1").glob("*/case.json"))
        self.assertEqual(len(records), 3)
        records[1].unlink()                                              # as if the run stopped in that frame
        resumed = DS.run_solve(MODEL, SOLE_R, SOLE_L, [self.ik], self.frames, out, jobs=1)
        self.assertEqual((resumed["run"]["reused_from_earlier_run"], resumed["run"]["computed"]), (2, 1))
        self.assertEqual(self.solved_frames(resumed), self.solved_frames(self.serial))

    def test_frames_from_other_kinematics_are_refused(self):
        other = self.d / "other_frames.json"
        other.write_text(json.dumps(dict(trials={"stand1.mot": dict(ik_sha256="0" * 64, stretches_s=[[0.0, 0.02, 3]])})))
        with self.assertRaises(ValueError):
            DS.run_solve(MODEL, SOLE_R, SOLE_L, [self.ik], other, self.d / "refused", jobs=1)


if __name__ == "__main__":
    unittest.main()
