"""Twin tier from evidence, not from a flag (docs/accuracy.md: "the tier travels with the data").

Tier C is the default. Tier B or A is only granted with a model-provenance record, a JSON file
that says which personalisation produced the subject model and who signed it off:

    {"tier": "A", "person_ref": "P-0042", "model": "imaging/P-0042_msk.osim",
     "model_sha256": "<sha256 of that .osim>",
     "evidence": "MRI 2026-09-14 -> segmentation -> msk-PIPE; joint centres reviewed",
     "approved_by": "Dr. X (treating clinician)", "date": "2026-09-20"}

The record must name the same person as the session, may not upgrade a synthetic sequence, and
its ``model_sha256`` must match the model the session config actually uses — so the evidence is
bound to the model, not to a file name. Only the tier it states (or lower) can be requested.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

TIERS = ("C", "B", "A")
REQUIRED = ("tier", "person_ref", "model", "model_sha256", "evidence", "approved_by")


class TierRefused(ValueError):
    pass


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def resolve(requested, person_ref, synthetic=False, provenance=None, model_path=None):
    """(tier, tier_source) for a session; raises TierRefused when the evidence does not support it."""
    requested = requested or "C"
    if requested not in TIERS:
        raise TierRefused(f"unknown tier {requested!r}")
    if requested == "C":
        return "C", {"tier": "C", "basis": "default: video/IMU on a statistical body"}
    if synthetic:
        raise TierRefused("synthetic sequences are Tier C by definition")
    if not provenance:
        raise TierRefused(f"Tier {requested} needs a model-provenance record (--model-provenance FILE); "
                          "see rehabtwin/tiers.py for its fields")
    path = Path(provenance)
    rec = json.loads(path.read_text())
    missing = [k for k in REQUIRED if not rec.get(k)]
    if missing:
        raise TierRefused(f"{path}: provenance record lacks {missing}")
    if rec["tier"] not in TIERS[1:]:
        raise TierRefused(f"{path}: tier must be 'A' or 'B', got {rec['tier']!r}")
    if TIERS.index(requested) > TIERS.index(rec["tier"]):
        raise TierRefused(f"{path} supports Tier {rec['tier']}, not {requested}")
    if rec["person_ref"] != person_ref:
        raise TierRefused(f"{path} is for {rec['person_ref']!r}, the session is {person_ref!r}")
    if model_path is None or sha256(model_path) != rec["model_sha256"]:
        raise TierRefused(f"{path}: model_sha256 does not match the model this session uses ({model_path}); "
                          "point the config's 'model' at the personalised .osim the record describes")
    return requested, {"tier": requested, "basis": "model-provenance record", "file": path.name,
                       "sha256": sha256(path), "model_sha256": rec["model_sha256"],
                       **{k: rec[k] for k in ("model", "evidence", "approved_by") if k in rec},
                       **({"date": rec["date"]} if rec.get("date") else {})}
