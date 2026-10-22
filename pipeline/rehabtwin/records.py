"""Session records (schemas/session.schema.json) and schema validation."""
from __future__ import annotations

import json
import platform
import subprocess
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


def session_record(seq, qc, out_dir: Path, tier, person_ref, video=None, front_end=None, config_name=None,
                   outputs=None, validation_report=None, tier_source=None):
    meta = seq.meta
    synthetic = bool(meta.get("synthetic", False))
    rec = {
        "session_id": meta.get("session_id") or out_dir.name,
        "person_ref": person_ref,
        "started_at": meta.get("started_at") or datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
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
    if (tier_source or {}).get("basis") == "model-provenance record":
        ev = f"per provenance record {tier_source['file']} ({tier_source.get('evidence', '')}); model is still " \
             "scaled by marker pairs in this pipeline"
        bones = {"status": "personalised", "error": ev}
        joints = {"status": "personalised" if tier == "A" else "generic", "error": ev}
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
