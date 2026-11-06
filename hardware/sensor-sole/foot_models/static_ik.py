#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors
# SPDX-License-Identifier: CERN-OHL-S-2.0
"""Inverse kinematics of a trial from its markers, with the settings of another trial's inverse-kinematics setup
(VALIDATION_PLAN.md, stage A, amendment 2: the quiet-standing trial static1, with the dataset's own squat settings).

From the template setup, only the settings are kept: the marker tasks and their weights, the accuracy, the
constraint weight and the time range. The model, marker file and outputs are this run's, and the template's own
paths are never used. A template element this file does not know is refused, so nothing else is carried over.

With --same-markers-as REF.trc, a marker task is applied only if that marker is in REF.trc: the reference trial's
inverse kinematics could only use the markers it had. (OpenCap LabValidation's static trials carry four medial
knee and ankle markers that the squat recordings lack, so the squats' inverse kinematics never used them.)

Markers and models only: the readers here refuse files whose names look like force data.

  python foot_models/static_ik.py TEMPLATE_setup_ik.xml MODEL.osim TRIAL.trc OUT_DIR [--same-markers-as REF.trc]
"""
import argparse
import hashlib
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from double_support import refuse_force_file  # noqa: E402

# Elements of an InverseKinematicsTool setup: those whose value is kept, and those this run sets.
KEPT = {"constraint_weight", "accuracy", "time_range", "report_errors", "IKTaskSet"}
SET = {"results_directory", "input_directory", "model_file", "marker_file", "coordinate_file",
       "output_motion_file", "report_marker_locations"}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def trc_markers(path):
    """Marker names of a .trc file (its fourth line)."""
    refuse_force_file(path)
    names = Path(path).read_text().splitlines()[3].split("\t")[2:]
    return [n.strip() for n in names if n.strip()]


def build_setup(template, model, trc, out_dir, name, use_only=None):
    """Write out_dir/<name>_setup_ik.xml from the template's settings. Returns (setup path, record)."""
    refuse_force_file(template); refuse_force_file(trc)
    tree = ET.parse(str(template))
    tool = tree.getroot().find("InverseKinematicsTool")
    if tool is None:
        raise ValueError(f"{template}: no InverseKinematicsTool")
    unknown = sorted({c.tag for c in tool} - KEPT - SET)
    if unknown:
        raise ValueError(f"{template}: elements not handled, refusing to carry them over: {unknown}")
    out_dir = Path(out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    tool.set("name", name)
    values = dict(results_directory=str(out_dir), model_file=str(Path(model).resolve()),
                  marker_file=str(Path(trc).resolve()), coordinate_file="Unassigned",
                  output_motion_file=str(out_dir / f"{name}.mot"), report_errors="true",
                  report_marker_locations="false")
    for tag in ("input_directory",):
        for e in tool.findall(tag):
            tool.remove(e)
    for tag, v in values.items():
        e = tool.find(tag)
        if e is None:
            e = ET.SubElement(tool, tag)
        e.text = v
    applied, disabled = [], []
    for task in tool.find("IKTaskSet").find("objects"):
        if task.tag != "IKMarkerTask":
            continue
        ap = task.find("apply")
        on = ap is None or ap.text.strip().lower() == "true"
        if on and use_only is not None and task.get("name") not in use_only:
            if ap is None:
                ap = ET.SubElement(task, "apply")
            ap.text = "false"
            on = False
            disabled.append(task.get("name"))
        if on:
            applied.append((task.get("name"), float(task.find("weight").text)))
    setup = out_dir / f"{name}_setup_ik.xml"
    tree.write(str(setup), xml_declaration=True, encoding="UTF-8")
    rec = dict(template=str(template), template_sha256=sha256(template), model=str(model), model_sha256=sha256(model),
               markers=str(trc), markers_sha256=sha256(trc), setup=str(setup),
               settings={t: tool.find(t).text for t in ("constraint_weight", "accuracy", "time_range")},
               marker_tasks_applied=len(applied), weights=dict(applied), disabled_not_in_reference=disabled)
    return setup, rec


def marker_errors(sto):
    """Summary of OpenSim's *_ik_marker_errors.sto: RMS and maximum marker error (m) over the frames."""
    lines = Path(sto).read_text().splitlines()
    end = next(k for k, ln in enumerate(lines) if ln.strip().lower() == "endheader")
    head = lines[end + 1].split("\t")
    rows = [[float(v) for v in ln.split("\t")] for ln in lines[end + 2:] if ln.strip()]
    col = {h.strip(): [r[i] for r in rows] for i, h in enumerate(head)}
    return dict(frames=len(rows), rms_mean_m=sum(col["marker_error_RMS"]) / len(rows), rms_max_m=max(col["marker_error_RMS"]),
                max_m=max(col["marker_error_max"]))


def run(template, model, trc, out_dir, name=None, same_markers_as=None):
    import opensim as osim
    name = name or Path(trc).stem
    use_only = set(trc_markers(same_markers_as)) if same_markers_as else None
    setup, rec = build_setup(template, model, trc, out_dir, name, use_only)
    osim.InverseKinematicsTool(str(setup)).run()
    rec.update(output=str(Path(out_dir) / f"{name}.mot"), output_sha256=sha256(Path(out_dir) / f"{name}.mot"),
               opensim=osim.__version__, marker_errors=marker_errors(Path(out_dir) / f"{name}_ik_marker_errors.sto"))
    if same_markers_as:
        rec.update(same_markers_as=str(same_markers_as), same_markers_as_sha256=sha256(same_markers_as))
    (Path(out_dir) / f"{name}_ik.json").write_text(json.dumps(rec, indent=1) + "\n")
    return rec


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("template"); ap.add_argument("model"); ap.add_argument("trc"); ap.add_argument("out_dir")
    ap.add_argument("--name"); ap.add_argument("--same-markers-as", metavar="REF.trc")
    a = ap.parse_args()
    rec = run(a.template, a.model, a.trc, a.out_dir, a.name, a.same_markers_as)
    print(json.dumps({k: rec[k] for k in ("output", "marker_tasks_applied", "disabled_not_in_reference", "marker_errors")}))


if __name__ == "__main__":
    main()
