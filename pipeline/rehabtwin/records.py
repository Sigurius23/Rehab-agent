"""Session records (schemas/session.schema.json) and schema validation."""
from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import __version__
from .config import REPO_ROOT, upstream_root

SCHEMAS = REPO_ROOT / "schemas"


def validate(doc, schema_name):
    """Raise if ``doc`` violates the named schema (needs the optional 'jsonschema' package)."""
    try:
        import jsonschema
    except ImportError:  # pragma: no cover
        return False
    schema = json.loads((SCHEMAS / f"{schema_name}.schema.json").read_text())
    jsonschema.validate(doc, schema)
    return True


def upstream_pins(slugs):
    pins = {}
    for slug in slugs:
        d = upstream_root() / slug
        if (d / ".git").exists():
            r = subprocess.run(["git", "-C", str(d), "rev-parse", "HEAD"], capture_output=True, text=True)
            if r.returncode == 0:
                pins[slug] = r.stdout.strip()
    return pins


def software_versions():
    out = {"rehabtwin": __version__, "python": platform.python_version()}
    try:
        import opensim
        out["opensim"] = opensim.GetVersion()
    except Exception:  # pragma: no cover
        pass
    import numpy
    import scipy
    out["numpy"], out["scipy"] = numpy.__version__, scipy.__version__
    return out


def parse_started_at(text):
    """Normalised ISO 8601 recording time; refuses a timestamp without UTC offset, which would order
    sessions recorded in different time zones (or across a DST change) wrongly."""
    try:
        dt = datetime.fromisoformat(str(text))
    except ValueError as e:
        raise ValueError(f"started_at {text!r} is not an ISO 8601 timestamp (e.g. 2026-10-21T09:30:00+02:00)") from e
    if dt.tzinfo is None:
        raise ValueError(f"started_at {text!r} needs a UTC offset (e.g. 2026-10-21T09:30:00+02:00 or ...Z)")
    return dt.isoformat()


def session_record(seq, qc, out_dir: Path, tier, person_ref, video=None, front_end=None, config_name=None,
                   outputs=None, validation_report=None, tier_source=None, started_at=None):
    """``started_at``: recording time (parse_started_at); without it and without one in the sequence
    metadata the processing time stands in, and started_at_source says so (progress warns)."""
    meta = seq.meta
    synthetic = bool(meta.get("synthetic", False))
    if started_at:
        when, when_source = started_at, "argument"
    elif meta.get("started_at"):
        when, when_source = meta["started_at"], "sequence metadata"
    else:
        when, when_source = datetime.now(timezone.utc).replace(microsecond=0).isoformat(), "processing time"
    rec = {
        "session_id": meta.get("session_id") or out_dir.name,
        "person_ref": person_ref,
        "started_at": when,
        "started_at_source": when_source,
        "synthetic": synthetic,
        "twin_tier": tier,
        "tier_source": tier_source or {"tier": tier, "basis": "unspecified"},
        "hardware": [{"device_id": "cam1", "type": "rgb-camera",
                      "serial_or_name": meta.get("camera", "unknown monocular camera")}],
        "streams": [],
        "calibration": {
            "intrinsics_source": meta.get("intrinsics_source", "unknown"),
            "extrinsics_file": "none (monocular); gravity from " + qc["frames"].get("up_source", "?"),
            "reprojection_error_px": None,
        },
        "sync": {"method": "single-stream", "max_offset_ms_after_correction": None},
        "accuracy_layers": accuracy_layers(tier, qc, validation_report, tier_source),
        "pipeline": {
            "front_end": front_end or meta.get("source", "unknown"),
            "back_end": "rehabtwin.opensim_stage (OpenSim scale + IK)",
            "config": config_name or qc.get("config", "?"),
            "software": software_versions(),
            "upstream_pins": {**meta.get("upstream_pins", {}),
                              **upstream_pins(["perfanalytics/pose2sim", "MarilynKeller/SKEL", "IsshikiHugh/HSMR",
                                               "MarilynKeller/SMPL2AddBiomechanics"])},
            "outputs": {k: str(v) for k, v in (outputs or {}).items()},
        },
    }
    if video:
        rec["streams"].append({"device_id": "cam1", "modality": "rgb", "file": str(video), "fps": seq.fps})
    rec["streams"].append({"device_id": "cam1", "modality": "skel-sequence" if seq.skel_poses is not None else "pose3d",
                           "file": "skel_seq.npz", "fps": seq.fps})
    return rec


def accuracy_layers(tier, qc, validation_report=None, tier_source=None):
    """What this session can honestly say about each docs/accuracy.md layer."""
    kin = "unvalidated"
    kin_err = "no reference comparison for this setup/movement (docs/validation-protocol.md step 5)"
    if validation_report and not validation_report.get("synthetic"):
        kin = "personalised" if validation_report.get("feedback_allowed_joint_planes") else "unvalidated"
        kin_err = f"see validation report; passing joint/planes: {', '.join(validation_report.get('feedback_allowed_joint_planes', [])) or 'none'}"
    ik = qc.get("ik", {}).get("marker_rms_m", {})
    scaling = qc.get("scaling", {})
    pm = scaling.get("person_model")
    if (tier_source or {}).get("basis") == "model-provenance record":
        how = "used as it is, segment masses scaled to this session's body mass" \
            if scaling.get("method", "").startswith("person model: its personalised") \
            else "model is still scaled by marker pairs in this pipeline"
        ev = f"per provenance record {tier_source['file']} ({tier_source.get('evidence', '')}); {how}"
        bones = {"status": "personalised", "error": ev}
        joints = {"status": "personalised" if tier == "A" else "generic", "error": ev}
    elif pm:
        ev = f"statistical skeleton scaled once in a calibration session (person model {pm['person_ref']} " \
             f"v{pm['version']}), the same bones every session; no imaging"
        bones = {"status": "generic", "error": ev}
        joints = {"status": "generic", "error": ev}
    else:
        bones = {"status": "generic", "error": "statistical skeleton (SKEL/OpenSim scaled), no imaging"}
        joints = {"status": "generic", "error": "regressed from body shape and scaled, not measured"}
    return {
        "bone_geometry": bones,
        "joint_centres": joints,
        "surface_shape": {"status": "unvalidated", "error": "estimated from video; no scan/tape comparison"},
        "kinematics": {"status": kin, "error": f"{kin_err}; IK marker RMS mean {ik.get('mean', '?')} m"},
        "muscle_geometry": {"status": "generic", "error": "generic Hill-type muscles, not personalised"},
    }


def write_json(path, doc):
    Path(path).write_text(json.dumps(doc, indent=2, default=_default) + "\n")
    return path


def _default(o):
    import numpy as np
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, Path):
        return str(o)
    raise TypeError(type(o))


# ------------------------------------------------------------- processing stamps

class StaleResult(ValueError):
    """A derived result (strength, correction, ...) describes an earlier processing of the session."""


def processing_stamp(model, motion, tier, exercise):
    """``pipeline.processing_id`` + ``processed_at`` for session.json.

    Derived results (validation, correction, strength, muscles, cues) copy the id they were computed
    from, so after re-processing (new mass, tier, motion or exercise: reps and foot planting follow it)
    the folder can tell which of them no longer describe it. A content hash, not a random id:
    re-processing to the same model, motion, tier and exercise keeps them current.
    """
    h = hashlib.sha256()
    for p in (model, motion):
        b = Path(p).read_bytes()
        h.update(len(b).to_bytes(8, "little") + b)
    h.update(f"{tier}\0{exercise}".encode())
    return {"processing_id": h.hexdigest()[:16],
            "processed_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat()}


def read_session(session_json):
    """An existing session.json, or None (missing or unreadable)."""
    p = Path(session_json)
    try:
        return json.loads(p.read_text()) if p.exists() else None
    except ValueError:
        return None


def kept_started_at(prev, meta, started_at):
    """The recording time a re-processing keeps from the folder's earlier session.json (``prev``) when
    neither ``--started-at`` nor the sequence gives one; None otherwise. Re-processing is what the stale
    and mass refusals ask for, and processing time in its place would reorder ``progress``."""
    if started_at or meta.get("started_at") or not prev or prev.get("started_at_source") != "argument":
        return None
    return prev.get("started_at")


def mark_reprocessing(session_json):
    """Drop the stamp of an existing session.json before ``process`` rewrites the folder's model and motion.

    A re-processing that fails half-way (after scaling, before the new session.json) must not leave the
    old stamp vouching for files that have already changed: everything derived then reads as stale.
    """
    p = Path(session_json)
    if not p.exists():
        return None
    try:
        sess = json.loads(p.read_text())
    except ValueError:          # unreadable: it vouches for nothing, and process() replaces it
        return None
    pl = sess.setdefault("pipeline", {})
    pl.pop("processing_id", None)
    pl["reprocessing_started_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    return write_json(p, sess)


def stamp(sess, doc, stale_inputs=()):
    """Record in derived ``doc`` the processing it was computed from (and stale inputs it was built on)."""
    doc["processing_id"] = (sess.get("pipeline") or {}).get("processing_id")
    if stale_inputs:
        doc["stale_inputs"] = list(stale_inputs)
    return doc


def stale_reason(sess, doc):
    """Why derived record ``doc`` does not describe the session's current processing (None if it does).

    Fails closed: a session or record without a stamp predates stamps and cannot be shown to match.
    """
    pl = sess.get("pipeline") or {}
    cur, got = pl.get("processing_id"), doc.get("processing_id")
    if cur and got == cur:
        return f"built on stale {', '.join(doc['stale_inputs'])}" if doc.get("stale_inputs") else None
    if not cur and pl.get("reprocessing_started_at"):
        return (f"the re-processing started {pl['reprocessing_started_at']} did not finish, so the folder's "
                "model and motion match no record")
    if not cur:
        return "session.json predates processing stamps, so nothing derived can be shown to match it"
    if not got:
        return "computed before processing stamps"
    return f"computed from processing {got}, the session is now {cur}"


def validation_problem(sess, val):
    """Why validation report ``val`` cannot vouch for session ``sess`` (None if it can).

    Shared by the feedback gate and ``progress``: only a report of the session's current processing
    (listed in its outputs, same processing_id), graded against marker-mocap, for the same person.
    Fails closed: a report without a grade or a stamp predates them and counts as unknown.
    """
    if "validation_report" not in (sess.get("pipeline") or {}).get("outputs", {}):   # re-processed without one
        return "the current processing has no validation report"
    why = stale_reason(sess, val)
    if why:
        return f"validation report is stale ({why})"
    if val.get("synthetic"):
        return "validation is synthetic"
    if val.get("reference_grade") != "marker-mocap":
        return f"validation reference grade is {val.get('reference_grade', 'unknown')!r}, not marker-mocap"
    if val.get("person_ref") != sess.get("person_ref"):
        return f"validation is for {val.get('person_ref')!r}, session is {sess.get('person_ref')!r}"
    return None


def require_current(sess, what):
    """Refuse ``what`` on a folder whose re-processing did not finish: its model and motion (and qc.json)
    may already be the new ones while metrics.json and the records still describe the old processing."""
    pl = sess.get("pipeline") or {}
    if not pl.get("processing_id") and pl.get("reprocessing_started_at"):
        raise StaleResult(f"{what}: the re-processing started {pl['reprocessing_started_at']} did not finish, so "
                          "the folder's model, motion and records do not belong together; re-run 'rehabtwin process' "
                          "into this folder first")


def rerun_hint(sess, rerun):
    """What fixes a stale result: re-running ``rerun`` — after a (finished) ``process`` when the session has
    no current stamp, since a result stamped against an unstamped session stays stale."""
    if (sess.get("pipeline") or {}).get("processing_id"):
        return f"re-run {rerun}"
    return f"re-run 'rehabtwin process' into this folder first (session.json has no current stamp), then re-run {rerun}"


def warn_if_stale(sess, doc, what):
    """Warn (stderr) when a consumer uses a stale derived input it can still run with; returns the reason."""
    why = stale_reason(sess, doc)
    if why:
        print(f"warning: {what} is stale ({why}); {rerun_hint(sess, 'it on the current processing')}",
              file=sys.stderr)
    return why
