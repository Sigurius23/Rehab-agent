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
on them. ``kinect --person`` takes height, mass and segment lengths from here, and ``muscles`` sizes the leg
muscles from what the person model holds, best first: MRI/CT per muscle, a DXA scan per leg (rehabtwin/dxa.py),
age, sex, height and mass, height and mass (rehabtwin/capacity.py).

What this does not do: make a video-scaled model anatomical. Scale factors from video are Tier C evidence;
the layers record that, and only an imaging-personalised model with a signed provenance record supports
Tier A/B.
"""
from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

from . import tiers

FORMAT = "rehabtwin-person/1"
LAYERS = ("bone_geometry", "joint_centres", "surface_shape", "kinematics", "muscle", "soft_tissue", "bone_density")
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
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _measurement(value, source, measured=True, when=None):
    return {"value": float(value), "source": source, "measured": bool(measured), "measured_at": when or _now()}


SEXES = ("female", "male")
AGE_RANGE = (5.0, 110.0)


def _check_age_sex(age_years, sex):
    if age_years is not None and not AGE_RANGE[0] <= age_years <= AGE_RANGE[1]:
        raise PersonRefused(f"age {age_years} years: give the age in years")
    if sex is not None and sex not in SEXES:
        raise PersonRefused(f"sex {sex!r}: one of {SEXES} (as the reference data record it)")


def _set_age_sex(rec, age_years, sex):
    if age_years is not None:
        rec["anthropometrics"]["age_years"] = _measurement(age_years, "stated")
    if sex is not None:
        rec["sex"] = sex


def _as_datetime(text):
    t = datetime.fromisoformat(str(text))
    return t if t.tzinfo else t.replace(tzinfo=UTC)


def age_years(rec, at=None):
    """The person's age (years) at ``at`` (ISO date/time; default now): the stated age plus the time since, or None."""
    a = rec.get("anthropometrics", {}).get("age_years")
    if not a:
        return None
    t = _as_datetime(at) if at else datetime.now(UTC)
    return a["value"] + (t - _as_datetime(a["measured_at"])).total_seconds() / (365.25 * 86400)


def init(person_dir, person_ref, height_m=None, mass_kg=None, mass_source="measured", note=None, age_years=None,
         sex=None):
    """Start a person folder (refuses an existing one). ``age_years`` and ``sex`` size the leg muscles when no
    scan does (rehabtwin/capacity.py); the age is stored with its date and counts on from there."""
    d = Path(person_dir)
    if (d / "person.json").exists():
        raise PersonRefused(f"{d} already holds a person model; use 'person set' or 'person build' to update it")
    if mass_source not in ("measured", "assumed"):
        raise PersonRefused("mass_source must be 'measured' or 'assumed'")
    _check_age_sex(age_years, sex)
    rec = {"format": FORMAT, "person_ref": person_ref, "version": 0, "created_at": _now(),
           "anthropometrics": {}, "model": None, "segments": {}, "keypoint_segments": {},
           "layers": {k: {"status": "not modelled", "tier": None} for k in LAYERS}, "history": []}
    rec["layers"]["kinematics"] = {"status": "per session (not stored here)", "tier": None}
    if height_m:
        rec["anthropometrics"]["height_m"] = _measurement(height_m, "measured")
    if mass_kg:
        rec["anthropometrics"]["mass_kg"] = _measurement(mass_kg, mass_source, mass_source == "measured")
    _set_age_sex(rec, age_years, sex)
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
    for k in LAYERS:                     # folders made before a layer existed
        rec["layers"].setdefault(k, {"status": "not modelled", "tier": None})
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


def set_measurement(person_dir, height_m=None, mass_kg=None, mass_source="measured", age_years=None, sex=None):
    """Record a new height and/or mass (a person's mass changes during rehab; each value keeps its date), age, sex."""
    rec = load(person_dir)
    _check_age_sex(age_years, sex)
    if height_m:
        rec["anthropometrics"]["height_m"] = _measurement(height_m, "measured")
    if mass_kg:
        rec["anthropometrics"]["mass_kg"] = _measurement(mass_kg, mass_source, mass_source == "measured")
    _set_age_sex(rec, age_years, sex)
    said = [f"height {height_m} m" if height_m else "", f"mass {mass_kg} kg ({mass_source})" if mass_kg else "",
            f"age {age_years:g}" if age_years is not None else "", f"sex {sex}" if sex else ""]
    return save(person_dir, rec, "measurement: " + ", ".join(x for x in said if x))


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
    rec["layers"]["muscle"] = _muscle_layer(rec)
    return save(d, rec, f"model built from session {sess['session_id']}")


def _leg_basis(rec):
    """How muscles without per-muscle imaging get their leg's volume (rehabtwin/capacity.py), in words."""
    from . import capacity, dxa
    d = rec.get("dxa")
    if d:
        lean = dxa.leg_lean_kg(d)
        return (f"per leg from {d['method']} {d['date']} (leg lean right {lean['_r']:g} kg, left {lean['_l']:g} kg; "
                f"{capacity.LEG_SOURCES['dxa']})")
    if rec.get("anthropometrics", {}).get("age_years") and rec.get("sex"):
        return f"by {capacity.LEG_SOURCES['anthropometry']}"
    return "by measured height and mass (Handsfield 2014)"


def _muscle_layer(rec):
    from . import capacity
    im = rec.get("muscle_imaging")
    if not im:
        return {"status": f"generic Rajagopal leg muscles; volume {_leg_basis(rec)} when a session uses them, the "
                          "generic share per muscle within a leg (rehabtwin/capacity.py); trunk muscles generic",
                "tier": "C"}
    covered = len(capacity.check_imaging(im))
    size = sum(1 for e in im["muscles"].values() if e.get("volume_cm3") is not None)
    quality = sum(1 for e in im["muscles"].values() if e.get("fat_fraction") is not None)
    full = covered == 2 * len(capacity.LEG_MUSCLES)
    return {"status": f"{im['method']} {im['date']}: {size} volume and {quality} fat-fraction labels covering {covered} of "
                      f"{2 * len(capacity.LEG_MUSCLES)} leg muscles; the rest {_leg_basis(rec)}; trunk generic"
                      + ("" if im.get("approved_by") else "; not clinician-reviewed"),
            "tier": ("A" if im.get("approved_by") else "B") if full else "C"}


def _imaging_record(record_path, required=("method", "date")):
    rec = json.loads(Path(record_path).read_text())
    missing = [k for k in required if not rec.get(k)]
    if missing:
        raise PersonRefused(f"{record_path}: imaging record lacks {missing}")
    return {**rec, "sha256": tiers.sha256(record_path), "recorded_at": _now()}


def set_muscle_imaging(person_dir, record_path):
    """Measured muscle size and quality from MRI/CT segmentation: {"method", "date", "approved_by"?, "muscles":
    {label_side: {"volume_cm3", "fat_fraction"}}} with labels from rehabtwin.capacity (GROUPS, ALIASES)."""
    from . import capacity
    d = Path(person_dir)
    rec = load(d)
    im = _imaging_record(record_path)
    try:
        capacity.check_imaging(im)
    except ValueError as e:
        raise PersonRefused(f"{record_path}: {e}") from e
    if not im.get("muscles"):
        raise PersonRefused(f"{record_path}: no 'muscles'")
    rec["muscle_imaging"] = im
    rec["layers"]["muscle"] = _muscle_layer(rec)
    return save(d, rec, f"muscle imaging: {im['method']} {im['date']}")


def _with_person_age_sex(rec, b):
    """A bone-density record with the person's age at the scan and sex where the record does not give them."""
    b = dict(b)
    if b.get("age_years") is None and age_years(rec, b.get("date")) is not None:
        b["age_years"] = round(age_years(rec, b["date"]), 1)
    if not b.get("sex") and rec.get("sex"):
        b["sex"] = rec["sex"]
    return b


def _store_bone_density(rec, b, source):
    from . import bone
    try:
        b["classification"] = bone.classify(_with_person_age_sex(rec, b))
    except ValueError as e:
        raise PersonRefused(f"{source}: {e}") from e
    rec["bone_density"] = b
    c = b["classification"]
    rec["layers"]["bone_density"] = {"status": f"{b['method']} {b['date']}: {c['category']} at {c['site']} ({c['value']}; "
                                               f"{c['basis']})" + ("" if b.get("approved_by") else "; report not reviewed"),
                                     "tier": "A" if b.get("approved_by") else "B"}
    return c


def set_bone_density(person_dir, record_path):
    """A DXA or QCT result: {"method": "DXA ...", "date", "age_years", "sex", "postmenopausal"?, "approved_by"?,
    "sites": {site: {"bmd_g_cm2", "t_score", "z_score"} | {"vbmd_mg_cm3"}}} (rehabtwin/bone.py). Age and sex
    default to the person model's."""
    d = Path(person_dir)
    rec = load(d)
    b = _imaging_record(record_path)
    c = _store_bone_density(rec, b, record_path)
    return save(d, rec, f"bone density: {b['method']} {b['date']} ({c['category']})")


def set_dxa(person_dir, record_path):
    """A whole-body DXA scan's regional table (rehabtwin/dxa.py): leg muscle per leg, segment mass distribution and
    regional fat, and bone density when the record has a ``bone_density`` part. Checked against the person's
    measured mass (refused beyond 15 %)."""
    from . import dxa
    d = Path(person_dir)
    rec = load(d)
    x = _imaging_record(record_path)
    mass = rec["anthropometrics"].get("mass_kg", {})
    try:
        x["checks"] = dxa.check(x, mass["value"] if mass.get("measured") else None)
    except ValueError as e:
        raise PersonRefused(f"{record_path}: {e}") from e
    reviewed = "" if x.get("approved_by") else "; report not reviewed"
    if x["checks"]["distribution"]:
        x["fat"] = dxa.fat_summary(x)
        f = x["fat"]
        rec["layers"]["soft_tissue"] = {
            "status": f"{x['method']} {x['date']}: body fat {f['total']['fat_pct']:g} %, legs {f['right_leg']['fat_pct']:g} / "
                      f"{f['left_leg']['fat_pct']:g} %, arms {f['right_arm']['fat_pct']:g} / {f['left_arm']['fat_pct']:g} %, "
                      f"trunk {f['trunk']['fat_pct']:g} % (right / left); regional mass sets segment masses; tissue "
                      "deformation not modelled" + reviewed, "tier": "A" if x.get("approved_by") else "B"}
    bd = x.pop("bone_density", None)
    rec["dxa"] = x
    rec["layers"]["muscle"] = _muscle_layer(rec)
    event = f"DXA: {x['method']} {x['date']}"
    if bd:
        b = {"method": x["method"], "date": x["date"], **{k: x[k] for k in ("approved_by", "age_years", "sex",
                                                                            "postmenopausal") if x.get(k) is not None},
             **bd, "sha256": x["sha256"], "recorded_at": x["recorded_at"], "from": "dxa record"}
        event += f", bone density {_store_bone_density(rec, b, record_path)['category']}"
    return save(d, rec, event)


SHAPE_HEIGHT_TOL_M, SHAPE_MASS_TOL = 0.03, 0.10      # beyond these the fit disagrees with the person's measurements


def set_surface_shape(person_dir, fit, source):
    """Store a body-shape fit (``rehabtwin.shape.fit_shape`` on this person's depth frames) as the surface layer.

    The fit's height and mesh-volume mass are checked against the person's measured height and mass (when the fit
    did not use the height): a fit that disagrees by more than 3 cm or 10 % is refused, as is one with warnings.
    ``source``: where the frames came from (recording, frames, body model file and sha256).
    """
    d = Path(person_dir)
    rec = load(d)
    if fit["fit"]["warnings"]:
        raise PersonRefused("the shape fit has warnings, not stored: " + "; ".join(fit["fit"]["warnings"])
                            + ". Record a moment standing still, facing the sensor, arms slightly away from the body")
    a, checks = rec["anthropometrics"], {}
    if a.get("height_m", {}).get("measured") and fit["fit"].get("height_given_m") is None:
        dh = fit["height_m"] - a["height_m"]["value"]
        checks["height_m"] = {"fit": round(fit["height_m"], 3), "measured": a["height_m"]["value"], "difference": round(dh, 3)}
        if abs(dh) > SHAPE_HEIGHT_TOL_M:
            raise PersonRefused(f"the fitted body is {dh * 100:+.1f} cm from the measured height: not stored (check the "
                                "focal length, the frames and that the person stood upright)")
    if a.get("mass_kg", {}).get("measured"):
        dm = fit["mass_kg"] / a["mass_kg"]["value"] - 1
        checks["mass_kg"] = {"fit_from_volume": round(fit["mass_kg"], 1), "measured": a["mass_kg"]["value"],
                             "difference": round(dm, 3)}
        if abs(dm) > SHAPE_MASS_TOL:
            raise PersonRefused(f"the fitted body's volume gives {fit['mass_kg']:.1f} kg, {dm:+.0%} from the measured "
                                f"{a['mass_kg']['value']:g} kg: not stored (loose clothing, segmentation or pose?)")
    rec["surface_shape"] = {
        "method": "SMPL-X fitted to Kinect v1 depth points (rehabtwin/shape.py)", "source": source, "fitted_at": _now(),
        "betas": [round(float(b), 5) for b in fit["betas"]], "height_m": round(fit["height_m"], 4),
        "volume_m3": round(fit["volume_m3"], 5), "mass_kg_from_volume": round(fit["mass_kg"], 2),
        "bmi_from_volume": round(fit["bmi"], 2), "segment_lengths_m": fit.get("segment_lengths_m"),
        "surface_to_centre_m": fit.get("surface_to_centre_m"), "checks": checks,
        "frames": [{"residuals": f["residuals"], "transl": f["transl"]} for f in fit["frames"]],
        "validated": "on synthetic BEDLAM2 bodies only (docs/bedlam2.md, result 4); not against a scan of this person",
        "joints_note": fit.get("joints_note")}
    said = "; ".join(f"{k} {v['difference']:+g} vs measured" for k, v in checks.items()) or "no measured height or mass to check"
    rec["layers"]["surface_shape"] = {
        "status": f"SMPL-X fitted to {len(fit['frames'])} Kinect depth frame(s) ({source.get('recording')}); {said}; "
                  "error measured on synthetic bodies only, not against a scan of this person", "tier": "C"}
    return save(d, rec, f"surface shape from {source.get('recording')}")


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
    lines = [f"{rec['person_ref']}  person model v{rec['version']}" + ("  (SYNTHETIC)" if rec.get("synthetic") else "")
             + (f"  {rec['sex']}" if rec.get("sex") else "")
             + (f", {age_years(rec):.0f} years" if age_years(rec) is not None else "")]
    for k, m in rec["anthropometrics"].items():
        lines.append(f"  {k:9s} {m['value']:g}  {m['source']}{'' if m['measured'] else ' (NOT measured)'}  {m['measured_at']}")
    m = rec.get("model")
    lines.append(f"  model     {m['kind']} {m['file']}" + (f" (Tier {m['tier']})" if m.get("tier") else
                                                          f" from session {m['built_from']['session_id']}")
                 if m else "  model     none yet")
    for k, v in rec.get("segments", {}).items():
        lines.append(f"  {k:12s} {v['length_m']:.3f} m")
    if rec.get("muscle_imaging"):
        im = rec["muscle_imaging"]
        lines.append(f"  muscles   {im['method']} {im['date']}: " + ", ".join(
            f"{k} {e['volume_cm3']:g} cm³" if e.get("volume_cm3") is not None else k for k, e in im["muscles"].items()))
        ff = {k: e["fat_fraction"] for k, e in im["muscles"].items() if e.get("fat_fraction") is not None}
        if ff:
            lines.append("  fat       " + ", ".join(f"{k} {v * 100:.1f} %" for k, v in ff.items()))
    if rec.get("dxa"):
        x, lean = rec["dxa"], rec["dxa"]["regions"]
        lines.append(f"  DXA       {x['method']} {x['date']}: leg lean R {lean['right_leg']['lean_kg']:g} kg, "
                     f"L {lean['left_leg']['lean_kg']:g} kg" + (f"; body fat {x['fat']['total']['fat_pct']:g} %, "
                                                              f"scanned {x['checks']['mass_kg']:g} kg" if x.get("fat") else ""))
    if rec.get("surface_shape"):
        sh = rec["surface_shape"]
        lines.append(f"  shape     SMPL-X fit: height {sh['height_m']:.3f} m, volume mass {sh['mass_kg_from_volume']:g} kg, "
                     f"BMI {sh['bmi_from_volume']:g}" + "".join(f"; {k} {v['difference']:+g}" for k, v in sh["checks"].items()))
    if rec.get("bone_density"):
        c = rec["bone_density"]["classification"]
        lines.append(f"  bone      {c['category']} at {c['site']} ({c['value']}), {c['method']} {c['date']}")
    lines.append("  layers:")
    for k, v in rec["layers"].items():
        lines.append(f"    {k:14s} {('Tier ' + v['tier']) if v.get('tier') else '-':7s} {v['status']}")
    return "\n".join(lines)
