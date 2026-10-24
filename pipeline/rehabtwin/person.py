"""The person model: one persistent, versioned description of a person that every session uses.

A twin is the same body in every session. Without this, each ``process`` run re-fitted the generic model to
its own frames, so a person's thigh could change length between Monday and Thursday. A person folder holds
what is known about the person, where each value came from, and which twin layer (docs/accuracy.md) it fills:

    PERSON/person.json        format rehabtwin-person/1 (schemas/person-model.schema.json)
    PERSON/model.osim         the person's model: the generic model scaled in a calibration session, or an
                              imaging-personalised model with its provenance record (Tier A/B, rehabtwin/tiers.py)
    PERSON/history/           every earlier person.json

``process --person PERSON`` re-applies the stored per-body scale factors to the generic model (OpenSim manual
scaling) instead of fitting new ones, so the bones keep their lengths; only that session's markers are placed
on them. ``kinect --person`` takes height, mass and segment lengths from here, and ``muscles`` scales muscle
capacity to the person's measured height and mass (rehabtwin/capacity.py).

What this does not do: make a video-scaled model anatomical. Scale factors from video are Tier C evidence;
the layers record that, and only an imaging-personalised model with a signed provenance record supports
Tier A/B.
"""
from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from . import tiers

FORMAT = "rehabtwin-person/1"
LAYERS = ("bone_geometry", "joint_centres", "surface_shape", "kinematics", "muscle", "soft_tissue")
# joint-centre distances read from the model in its default pose: name -> (body, body), body origins
JOINT_SEGMENTS = {"thigh_r": ("femur_r", "tibia_r"), "thigh_l": ("femur_l", "tibia_l"),
                  "shank_r": ("tibia_r", "talus_r"), "shank_l": ("tibia_l", "talus_l"),
                  "upper_arm_r": ("humerus_r", "ulna_r"), "upper_arm_l": ("humerus_l", "ulna_l"),
                  "forearm_r": ("ulna_r", "hand_r"), "forearm_l": ("ulna_l", "hand_l"),
                  "hip_width": ("femur_r", "femur_l")}
# keypoint distances on the model's markers (what rehabtwin.kinect's segment check compares); a model without
# those markers (e.g. built with the LSTM-marker config) gives the joint-centre segment instead
KEYPOINT_SEGMENTS = ("LHip-LKnee", "RHip-RKnee")
KEYPOINT_FALLBACK = {"LHip-LKnee": "thigh_l", "RHip-RKnee": "thigh_r"}


class PersonRefused(ValueError):
    pass


def _now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _measurement(value, source, measured=True, when=None):
    return {"value": float(value), "source": source, "measured": bool(measured), "measured_at": when or _now()}


def init(person_dir, person_ref, height_m=None, mass_kg=None, mass_source="measured", note=None):
    """Start a person folder (refuses an existing one)."""
    d = Path(person_dir)
    if (d / "person.json").exists():
        raise PersonRefused(f"{d} already holds a person model; use 'person set' or 'person build' to update it")
    if mass_source not in ("measured", "assumed"):
        raise PersonRefused("mass_source must be 'measured' or 'assumed'")
    rec = {"format": FORMAT, "person_ref": person_ref, "version": 0, "created_at": _now(),
           "anthropometrics": {}, "model": None, "segments": {}, "keypoint_segments": {},
           "layers": {k: {"status": "not modelled", "tier": None} for k in LAYERS}, "history": []}
    rec["layers"]["kinematics"] = {"status": "per session (not stored here)", "tier": None}
    if height_m:
        rec["anthropometrics"]["height_m"] = _measurement(height_m, "measured")
    if mass_kg:
        rec["anthropometrics"]["mass_kg"] = _measurement(mass_kg, mass_source, mass_source == "measured")
    return save(d, rec, "created" + (f": {note}" if note else ""))


def load(person_dir):
    """person.json of a person folder, checked: format, and the stored model file is the one recorded."""
    d = Path(person_dir)
    p = d / "person.json"
    if not p.exists():
        raise PersonRefused(f"{d}: no person.json (create one with 'rehabtwin person init')")
    rec = json.loads(p.read_text())
    if rec.get("format") != FORMAT:
        raise PersonRefused(f"{p}: format {rec.get('format')!r}, expected {FORMAT!r}")
    m = rec.get("model")
    if m and tiers.sha256(d / m["file"]) != m["sha256"]:
        raise PersonRefused(f"{d / m['file']} changed since it was recorded in person.json (sha256 differs)")
    return rec


def save(person_dir, rec, event):
    """Write the next version of person.json; the previous one goes to history/."""
    d = Path(person_dir)
    d.mkdir(parents=True, exist_ok=True)
    p = d / "person.json"
    from . import records
    rec["version"] = rec.get("version", 0) + 1
    rec["updated_at"] = _now()
    rec["history"].append({"version": rec["version"], "at": rec["updated_at"], "event": event})
    records.validate(rec, "person-model")
    if p.exists():
        (d / "history").mkdir(exist_ok=True)
        shutil.copy(p, d / "history" / f"person_v{rec['version'] - 1:03d}.json")
    p.write_text(json.dumps(rec, indent=1))
    return rec


def set_measurement(person_dir, height_m=None, mass_kg=None, mass_source="measured"):
    """Record a new height and/or mass (a person's mass changes during rehab; each value keeps its date)."""
    rec = load(person_dir)
    if height_m:
        rec["anthropometrics"]["height_m"] = _measurement(height_m, "measured")
    if mass_kg:
        rec["anthropometrics"]["mass_kg"] = _measurement(mass_kg, mass_source, mass_source == "measured")
    return save(person_dir, rec, f"measurement: height {height_m} m, mass {mass_kg} kg ({mass_source})")


def model_lengths(model_path):
    """({joint segment: m}, {keypoint segment: m}) of a model in its default pose (body origins / markers)."""
    from .opensim_stage import _osim
    osim = _osim()
    model = osim.Model(str(model_path))
    state = model.initSystem()
    bodies = model.getBodySet()
    names = {bodies.get(i).getName() for i in range(bodies.getSize())}

    def origin(b):
        p = bodies.get(b).getPositionInGround(state)
        return [p.get(0), p.get(1), p.get(2)]

    def dist(a, b):
        return round(sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5, 4)
    joints = {k: dist(origin(a), origin(b)) for k, (a, b) in JOINT_SEGMENTS.items() if a in names and b in names}
    ms = model.getMarkerSet()
    markers = {ms.get(i).getName(): ms.get(i) for i in range(ms.getSize())}
    keys = {}
    for key in KEYPOINT_SEGMENTS:
        a, b = key.split("-")
        if a in markers and b in markers:
            pa, pb = (markers[n].getLocationInGround(state) for n in (a, b))
            keys[key] = dist([pa.get(i) for i in range(3)], [pb.get(i) for i in range(3)])
    return joints, keys


def _keypoint_segments(joints, keys, config=None):
    out = {k: {"length_m": v, "definition": f"model markers {k} after marker placement"} for k, v in keys.items()}
    for k, seg in KEYPOINT_FALLBACK.items():
        if k not in out and seg in joints:
            out[k] = {"length_m": joints[seg], "definition": f"joint centres ({seg}): the model has no {k} markers"}
    if config:
        for v in out.values():
            v["config"] = config
    return out


def build_from_session(person_dir, session_dir, allow_synthetic=False):
    """Take a processed calibration session's scaled model as this person's model (new person.json version).

    Stores the model, its per-body scale factors and the generic model they apply to (by sha256), its
    joint-centre and keypoint segment lengths, and the session's measured height and mass. Refuses a session
    of another person, a session whose re-processing did not finish, and an assumed body mass. A synthetic
    session only with ``allow_synthetic`` (tests); the person model is then marked synthetic, and only
    synthetic sequences can use it.
    """
    from . import records
    from .config import load_config, resolve
    from .opensim_stage import KNOWN_MASS_SOURCES
    d, s = Path(person_dir), Path(session_dir)
    rec = load(d)
    sess = json.loads((s / "session.json").read_text())
    records.require_current(sess, "person build")
    if sess.get("person_ref") != rec["person_ref"]:
        raise PersonRefused(f"session {s} is of {sess.get('person_ref')!r}, the person model of {rec['person_ref']!r}")
    if sess.get("synthetic") and not allow_synthetic:
        raise PersonRefused("a synthetic session is not a person")
    qc = json.loads((s / "qc.json").read_text())
    subj = qc.get("subject", {})
    if subj.get("mass_source") not in KNOWN_MASS_SOURCES:
        raise PersonRefused(f"session mass is {subj.get('mass_source', 'unknown')}: a person model needs a measured "
                            "mass (process with --mass-kg)")
    if qc.get("scaling", {}).get("person_model"):
        raise PersonRefused(f"session {s} was itself processed with a person model: build from a calibration session")
    factors = qc.get("scale_factors")
    if not factors:
        raise PersonRefused(f"{s / 'qc.json'} has no scale factors to build a person model from")
    cfg = load_config(Path(sess["pipeline"]["config"]).stem)
    model_src = s / sess["pipeline"]["outputs"]["model"]
    shutil.copy(model_src, d / "model.osim")
    joints, keys = model_lengths(d / "model.osim")
    rec["synthetic"] = bool(sess.get("synthetic"))
    rec["model"] = {"kind": "scaled-generic", "file": "model.osim", "sha256": tiers.sha256(d / "model.osim"),
                    "generic_model": cfg["model"], "generic_model_sha256": tiers.sha256(resolve(cfg["model"])),
                    "scale_set": factors, "config": sess["pipeline"]["config"],
                    "built_from": {"session_id": sess["session_id"], "processing_id": sess["pipeline"].get("processing_id"),
                                   "front_end": sess["pipeline"].get("front_end")}}
    rec["segments"] = {k: {"length_m": v, "definition": "body origins (joint centres) in the default pose"}
                       for k, v in joints.items()}
    rec["keypoint_segments"] = _keypoint_segments(joints, keys, sess["pipeline"]["config"])
    rec["anthropometrics"]["mass_kg"] = _measurement(subj["mass_kg"], f"session {sess['session_id']} ({subj['mass_source']})")
    if subj.get("height_m"):
        rec["anthropometrics"]["height_m"] = _measurement(subj["height_m"], f"session {sess['session_id']}")
    src = f"generic bones scaled per segment from session {sess['session_id']} ({sess['pipeline'].get('front_end')})"
    rec["layers"]["bone_geometry"] = {"status": src, "tier": "C"}
    rec["layers"]["joint_centres"] = {"status": "scaled with the bones, markers placed on the static frames; "
                                                "not checked against imaging", "tier": "C"}
    rec["layers"]["muscle"] = {"status": "generic Rajagopal leg muscles; capacity scaled to measured height and mass "
                                         "when a session uses them (rehabtwin/capacity.py); trunk muscles generic",
                               "tier": "C"}
    return save(d, rec, f"model built from session {sess['session_id']}")


def attach_personalised_model(person_dir, model_path, provenance_path):
    """Use an imaging-personalised model (with its signed provenance record) as this person's model."""
    d = Path(person_dir)
    rec = load(d)
    prov = json.loads(Path(provenance_path).read_text())
    missing = [k for k in tiers.REQUIRED if not prov.get(k)]
    if missing:
        raise PersonRefused(f"{provenance_path}: provenance record lacks {missing}")
    if prov["person_ref"] != rec["person_ref"]:
        raise PersonRefused(f"provenance is for {prov['person_ref']!r}, the person model of {rec['person_ref']!r}")
    if tiers.sha256(model_path) != prov["model_sha256"]:
        raise PersonRefused(f"{model_path} is not the model the provenance record describes (sha256 differs)")
    shutil.copy(model_path, d / "model.osim")
    shutil.copy(provenance_path, d / "provenance.json")
    joints, keys = model_lengths(d / "model.osim")
    rec["synthetic"] = False
    rec["model"] = {"kind": "personalised", "file": "model.osim", "sha256": prov["model_sha256"],
                    "provenance": "provenance.json", "tier": prov["tier"], "evidence": prov["evidence"]}
    rec["segments"] = {k: {"length_m": v, "definition": "body origins (joint centres) in the default pose"}
                       for k, v in joints.items()}
    rec["keypoint_segments"] = _keypoint_segments(joints, keys)
    rec["layers"]["bone_geometry"] = {"status": f"personalised: {prov['evidence']}", "tier": prov["tier"]}
    rec["layers"]["joint_centres"] = {"status": f"from the personalised model ({prov['approved_by']})", "tier": prov["tier"]}
    return save(d, rec, f"personalised model attached (Tier {prov['tier']})")


def for_session(person_dir, person_ref=None, synthetic=False):
    """What ``process`` needs from a person folder. Refuses another person's (``person_ref`` None: the
    sequence names nobody, so the folder's person is taken), and mixing synthetic and real data."""
    d = Path(person_dir)
    rec = load(d)
    if person_ref is not None and rec["person_ref"] != person_ref:
        raise PersonRefused(f"person model {d} is of {rec['person_ref']!r}, the session is of {person_ref!r}")
    if bool(rec.get("synthetic")) != bool(synthetic):
        raise PersonRefused(f"person model {d} is {'synthetic' if rec.get('synthetic') else 'of a real person'}, "
                            f"the sequence is {'synthetic' if synthetic else 'real'}")
    if not rec.get("model"):
        raise PersonRefused(f"person model {d} has no model yet: 'rehabtwin person build {d} --from-session SESSION'")
    m = dict(rec["model"])
    m["path"] = str((d / m["file"]).resolve())
    if m["kind"] == "personalised":
        m["provenance_path"] = str((d / m["provenance"]).resolve())
    a = rec["anthropometrics"]
    return {"person_ref": rec["person_ref"], "version": rec["version"], "sha256": tiers.sha256(d / "person.json"),
            "model": m, "height_m": a.get("height_m", {}).get("value"),
            "mass_kg": a["mass_kg"]["value"] if a.get("mass_kg", {}).get("measured") else None,
            "keypoint_segments": {k: v["length_m"] for k, v in rec.get("keypoint_segments", {}).items()}}


def summary(rec):
    """Plain-text overview of a person.json: measurements, model, segment lengths and each twin layer."""
    lines = [f"{rec['person_ref']}  person model v{rec['version']}" + ("  (SYNTHETIC)" if rec.get("synthetic") else "")]
    for k, m in rec["anthropometrics"].items():
        lines.append(f"  {k:9s} {m['value']:g}  {m['source']}{'' if m['measured'] else ' (NOT measured)'}  {m['measured_at']}")
    m = rec.get("model")
    lines.append(f"  model     {m['kind']} {m['file']}" + (f" (Tier {m['tier']})" if m.get("tier") else
                                                          f" from session {m['built_from']['session_id']}")
                 if m else "  model     none yet")
    for k, v in rec.get("segments", {}).items():
        lines.append(f"  {k:12s} {v['length_m']:.3f} m")
    lines.append("  layers:")
    for k, v in rec["layers"].items():
        lines.append(f"    {k:14s} {('Tier ' + v['tier']) if v.get('tier') else '-':7s} {v['status']}")
    return "\n".join(lines)
