#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors
# SPDX-License-Identifier: CERN-OHL-S-2.0
"""Checks of foot_models/static_ik.py's setup builder (no OpenSim needed): from a template inverse-kinematics setup,
only the settings are kept (marker tasks and weights, accuracy, constraint weight, time range); the model, marker
file and outputs are this run's and none of the template's paths survive; with a reference marker list, tasks for
markers it lacks are switched off and reported; a template element the builder does not know is refused; files named
like force data are refused.
"""
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "foot_models"))
try:
    import static_ik as SI
    HAVE = True
except ImportError:
    HAVE = False

TEMPLATE = """<?xml version="1.0" encoding="UTF-8" ?>
<OpenSimDocument Version="40000">
  <InverseKinematicsTool name="squats1">
    <results_directory>C:/elsewhere\\IK</results_directory>
    <model_file>C:/elsewhere\\model_scaled.osim</model_file>
    <constraint_weight>Inf</constraint_weight>
    <accuracy>1.0000000000000001e-05</accuracy>
    <time_range>-Inf Inf</time_range>
    <output_motion_file>C:/elsewhere\\squats1.mot</output_motion_file>
    <report_errors>true</report_errors>
    <IKTaskSet>
      <objects>
        <IKMarkerTask name="r_calc"><apply>true</apply><weight>10</weight></IKMarkerTask>
        <IKMarkerTask name="r_toe"><apply>true</apply><weight>5</weight></IKMarkerTask>
        <IKMarkerTask name="r_mankle"><apply>true</apply><weight>2</weight></IKMarkerTask>
        <IKMarkerTask name="C7"><apply>false</apply><weight>1</weight></IKMarkerTask>
      </objects>
      <groups />
    </IKTaskSet>
    <marker_file>C:/elsewhere\\squats1.trc</marker_file>
    <coordinate_file>Unassigned</coordinate_file>
    {extra}
  </InverseKinematicsTool>
</OpenSimDocument>
"""
TRC = ("PathFileType\t4\t(X/Y/Z)\tstatic1.trc\nDataRate\tCameraRate\tNumFrames\tNumMarkers\tUnits\n"
       "100\t100\t1\t{n}\tmm\nFrame#\tTime\t{names}\n\t\tX1\tY1\tZ1\n\n1\t0.0\t{values}\n")


def trc(path, names):
    path.write_text(TRC.format(n=len(names), names="\t\t\t".join(names), values="\t".join("0" for _ in range(3 * len(names)))))
    return path


@unittest.skipUnless(HAVE, "needs the pipeline's Python (numpy)")
class SetupFromTemplate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        self.template = self.d / "squats1_setup_ik.xml"
        self.template.write_text(TEMPLATE.format(extra=""))
        self.model = self.d / "model_scaled.osim"; self.model.write_text("<OpenSimDocument/>")
        self.static = trc(self.d / "static1.trc", ["r_calc", "r_toe", "r_mankle", "C7"])
        self.squat = trc(self.d / "squats1.trc", ["r_calc", "r_toe", "C7"])

    def tearDown(self):
        self.tmp.cleanup()

    def build(self, use_only=None, template=None):
        return SI.build_setup(template or self.template, self.model, self.static, self.d / "out", "static1", use_only)

    def test_settings_kept_paths_replaced(self):
        setup, rec = self.build()
        tool = ET.parse(setup).getroot().find("InverseKinematicsTool")
        self.assertEqual(tool.get("name"), "static1")
        self.assertEqual(tool.find("model_file").text, str(self.model.resolve()))
        self.assertEqual(tool.find("marker_file").text, str(self.static.resolve()))
        self.assertEqual(tool.find("output_motion_file").text, str((self.d / "out" / "static1.mot").resolve()))
        self.assertEqual((tool.find("accuracy").text, tool.find("constraint_weight").text, tool.find("time_range").text),
                         ("1.0000000000000001e-05", "Inf", "-Inf Inf"))
        self.assertNotIn("elsewhere", setup.read_text())
        self.assertEqual(rec["weights"], {"r_calc": 10.0, "r_toe": 5.0, "r_mankle": 2.0})   # C7 stays off
        self.assertEqual(rec["disabled_not_in_reference"], [])

    def test_markers_the_reference_lacks_are_switched_off(self):
        setup, rec = self.build(use_only=set(SI.trc_markers(self.squat)))
        self.assertEqual(rec["disabled_not_in_reference"], ["r_mankle"])
        self.assertEqual(rec["weights"], {"r_calc": 10.0, "r_toe": 5.0})
        tasks = {t.get("name"): t.find("apply").text for t in ET.parse(setup).getroot().iter("IKMarkerTask")}
        self.assertEqual(tasks, {"r_calc": "true", "r_toe": "true", "r_mankle": "false", "C7": "false"})

    def test_unknown_template_elements_are_refused(self):
        bad = self.d / "bad_setup_ik.xml"
        bad.write_text(TEMPLATE.format(extra="<external_loads_file>C:/forces.xml</external_loads_file>"))
        with self.assertRaises(ValueError):
            self.build(template=bad)

    def test_force_named_files_are_refused(self):
        forces = trc(self.d / "static1_forces.trc", ["r_calc"])
        with self.assertRaises(PermissionError):
            SI.build_setup(self.template, self.model, forces, self.d / "out", "x")

    def test_trc_marker_names(self):
        self.assertEqual(SI.trc_markers(self.static), ["r_calc", "r_toe", "r_mankle", "C7"])


if __name__ == "__main__":
    unittest.main()
