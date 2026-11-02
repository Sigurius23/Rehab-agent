"""Clinician safety flags (twin manifest ``safety_flags``, docs/accuracy.md red lines).

A safety flag restricts what the twin does at a body region: no posture cues there, no assistance what-ifs there.
Only a clinician sets or clears one; the twin records the clinician's list as given (``check_flags``) and obeys
it. It never infers, sets or clears a flag itself.

- A flag is **active** unless its status is ``cleared``: ``suspected`` and ``not-assessed`` restrict as
  ``confirmed`` does (fail closed: an unassessed atlantoaxial instability is not a safe neck).
- ``body_region`` is free text ("right knee", "cervical spine", "whole body"). It is matched to the pipeline's
  joints by keyword and side. A region no keyword matches holds **every** joint, with the reason saying so.
- The recorded ``restrictions`` are text for the clinician; the twin doesn't interpret them, so it holds the
  whole region rather than guess what is still allowed.
"""
from __future__ import annotations

FLAGS = ("atlantoaxial-instability", "bone-fragility", "joint-instability", "post-surgical-restriction",
         "unrepresentable-anatomy", "other")
STATUSES = ("confirmed", "suspected", "cleared", "not-assessed")
ALL = "*"
# region keyword -> joint keys (prefixes) as rehabtwin.kinematics.classify_signal names them
REGION_JOINTS = {
    "knee": ("knee",), "hip": ("hip", "pelvis"), "pelvis": ("pelvis", "hip"), "ankle": ("ankle", "subtalar", "mtp"),
    "foot": ("ankle", "subtalar", "mtp"), "toe": ("mtp",),
    "lumbar": ("lumbar", "pelvis"), "thoracic": ("torso", "lumbar"), "trunk": ("torso", "lumbar", "pelvis"),
    "spine": ("lumbar", "torso", "pelvis", "neck", "head"), "back": ("lumbar", "torso", "pelvis"),
    "neck": ("neck", "head"), "cervical": ("neck", "head"), "atlantoaxial": ("neck", "head"), "head": ("neck", "head"),
    "shoulder": ("shoulder",), "arm": ("shoulder", "elbow", "forearm", "wrist"), "elbow": ("elbow",),
    "forearm": ("forearm",), "wrist": ("wrist",), "hand": ("wrist",),
    "leg": ("hip", "knee", "ankle", "subtalar", "mtp"), "whole body": (ALL,), "systemic": (ALL,), "all joints": (ALL,),
}
LEVELS = ("cervical", "atlantoaxial", "neck", "thoracic", "lumbar")       # named spine levels narrow "spine"
SIDES = {"right": "_r", "left": "_l"}


def check_flags(flags):
    """Refuse a safety-flag list that isn't a clinician's record in the twin-manifest format. Returns the list."""
    if isinstance(flags, dict):
        flags = flags.get("safety_flags", [flags])
    if not isinstance(flags, list) or not flags:
        raise ValueError("give a list of safety flags (twin manifest 'safety_flags')")
    for k, f in enumerate(flags):
        where = f"safety flag {k + 1}"
        missing = [x for x in ("flag", "status", "set_by", "set_at", "body_region") if not f.get(x)]
        if missing:
            raise ValueError(f"{where}: missing {missing}")
        if f["flag"] not in FLAGS:
            raise ValueError(f"{where}: flag {f['flag']!r}, one of {list(FLAGS)}")
        if f["status"] not in STATUSES:
            raise ValueError(f"{where}: status {f['status']!r}, one of {list(STATUSES)}")
        if f["set_by"] != "clinician":
            raise ValueError(f"{where}: set_by must be 'clinician' - the twin never sets or clears a safety flag")
        restrictions = f.get("restrictions", [])
        if not (isinstance(restrictions, list) and all(isinstance(x, str) for x in restrictions)):
            raise ValueError(f"{where}: restrictions is a list of strings")
    return flags


def active(flags):
    return [f for f in flags or () if f.get("status") != "cleared"]


def region_joints(region):
    """(joint-key prefixes or (ALL,), side suffix or None, matched?) for a free-text body region."""
    text = region.lower().replace("-", " ").replace("_", " ")
    keys = [k for k in REGION_JOINTS if k in text]
    if any(k in keys for k in LEVELS):                 # "cervical spine" is the neck, not the whole spine
        keys = [k for k in keys if k not in ("spine", "back")]
    prefixes = [j for k in keys for j in REGION_JOINTS[k]]
    side = next((suffix for word, suffix in SIDES.items() if word in text and not ("both" in text or "bilateral" in text)), None)
    if not prefixes:
        return (ALL,), None, False
    return tuple(dict.fromkeys(prefixes)), side, True


def covers(flag, joint):
    """Does an active flag's region include ``joint`` (e.g. 'knee_r', 'torso_segment', 'lumbar')?"""
    prefixes, side, _ = region_joints(flag["body_region"])
    if ALL in prefixes:
        return True
    if not joint.startswith(prefixes):
        return False
    lateral = joint.endswith(("_r", "_l"))
    return side is None or not lateral or joint.endswith(side)


def reason(flag):
    _, _, matched = region_joints(flag["body_region"])
    text = (f"clinician safety flag '{flag['flag']}' ({flag['status']}, set {flag['set_at']}) at "
            f"{flag['body_region']}" + (f": {'; '.join(flag['restrictions'])}" if flag.get("restrictions") else ""))
    return text if matched else text + " (region not recognised, so every joint is held)"


def holds(flags, joints):
    """{joint: reason} for the joints (e.g. a rule set's) that active flags cover."""
    out = {}
    for j in joints:
        for f in active(flags):
            if covers(f, j):
                out.setdefault(j, reason(f))
    return out
