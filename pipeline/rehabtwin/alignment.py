"""Skeletal alignment: the person's own standing geometry (twin layer ``joint_alignment``).

Lengths alone make every person a scaled copy of the generic skeleton. People differ in how their bones sit:
knock knees (genu valgum) or bow legs (genu varum), twisted femurs or shins, one leg longer. The generic
OpenSim knee bends about one axis and has no frontal-plane freedom of its own, so inverse kinematics of a valgus
knee has to put the difference somewhere else (hip adduction and rotation).

What the twin may do with each kind of evidence follows the anatomy audit (docs/accuracy.md): nothing internal
is inferred from cameras.

- **Camera estimate, screening only** (``measure``): every session's static frame gives, per side, the knee's
  frontal-plane angle between thigh and shank (+ valgus, the ``knee_fppa`` definition), the standing knee flexion
  (- hyperextension), leg length (hip to ankle centre), pelvic obliquity, shoulder height difference and each
  shoulder's reach from the midline. The joint centres behind it are themselves estimates (video keypoints, a
  marker augmenter), so the result is an **estimate**: it can't tell a bone shape from a habitual posture, and
  its uncertainty is not yet measured (it needs repeat sessions, ``rehabtwin progress``). It is used as the
  person's standing baseline for posture cues, and beyond ``SCREEN_KNEE_FRONTAL_DEG`` it holds that knee's cues
  with a prompt to get it checked by a professional (``screening_holds``). It never changes the model.
- **Limb alignment from imaging or a clinician** (``check_limb_alignment``), the twin manifest's
  ``limb_alignment`` block: per side ``mechanical_axis_hka_deg`` (deviation of the hip-knee-ankle axis from
  straight, + valgus), femoral anteversion, neck-shaft angle, tibial torsion, femur and tibia length, carrying
  angle, each with its ``source`` (EOS, CT, MRI, radiograph: Tier B, A when approved; clinical measurement: Tier
  C, B when approved). Only this personalises the model (``apply_to_model``): the knee joint's frame on the femur
  is turned about the femur's forward axis until the model's hip-knee-ankle angle in its default pose is the
  person's; the tibia, its markers, muscles and the foot follow. Torsion values are stored, not yet applied.
  A record that says the alignment is structural holds that knee's posture cues for a clinician-set target.
"""
from __future__ import annotations

import numpy as np

from .kinematics import _fppa

SIDES = ("r", "l")
# joint centre -> per side, marker groups in order of preference (a group's markers are averaged): SKEL joint
# centres, OpenCap/Pose2Sim LSTM markers (epicondyles and malleoli), SKEL skin markers, MediaPipe keypoints
CENTRES = {
    "hip": {"r": [["JC_femur_r"], ["RHJC_study"], ["RHip"]], "l": [["JC_femur_l"], ["LHJC_study"], ["LHip"]]},
    "knee": {"r": [["JC_tibia_r"], ["r_knee_study", "r_mknee_study"], ["RKNE", "RKNI"], ["RKnee"]],
             "l": [["JC_tibia_l"], ["L_knee_study", "L_mknee_study"], ["LKNE", "LKNI"], ["LKnee"]]},
    "ankle": {"r": [["JC_talus_r"], ["r_ankle_study", "r_mankle_study"], ["RANK", "RAKI"], ["RAnkle"]],
              "l": [["JC_talus_l"], ["L_ankle_study", "L_mankle_study"], ["LANK", "LAKI"], ["LAnkle"]]},
    "shoulder": {"r": [["r_shoulder_study"], ["RSHO"], ["RShoulder"]], "l": [["L_shoulder_study"], ["LSHO"], ["LShoulder"]]},
}
SCREEN_KNEE_FRONTAL_DEG = 6.0     # estimated standing knee angle beyond which cues are held (ours, not a norm)
UNCERTAINTY = "not yet measured (needs repeat sessions of the same person: rehabtwin progress)"
CHECK_PROMPT = "worth getting checked by a professional"
IMAGING = ("eos", "ct", "mri", "radiograph")
SOURCES = IMAGING + ("clinical-measurement",)          # twin manifest limb_side.source
# twin manifest limb_side fields and the values we accept (signs: + valgus, + anteversion, + external torsion)
LIMB_RANGES = {"mechanical_axis_hka_deg": (-30.0, 30.0), "femoral_anteversion_deg": (-30.0, 60.0),
               "neck_shaft_angle_deg": (90.0, 170.0), "tibial_torsion_deg": (-30.0, 60.0),
               "femur_length_mm": (250.0, 650.0), "tibia_length_mm": (200.0, 550.0), "carrying_angle_deg": (-20.0, 40.0)}
MANIFEST_SIDES = {"right": "r", "left": "l"}
KNEE_JOINT_CHILD = "tibia"         # the knee is the joint whose child is tibia_<side>


def _centre(index, pts, part, side):
    for group in CENTRES[part][side]:
        if all(n in index for n in group):
            p = np.mean([pts[index[n]] for n in group], axis=0)
            if np.all(np.isfinite(p)):
                return p, group
    return None, None


def measure(names, pts, up=(0.0, 1.0, 0.0)):
    """Standing alignment from one static pose: ``names`` (N,) and ``pts`` (N, 3) in a frame with ``up``
    vertical (metres). Needs hip, knee and ankle centres on both sides; shoulders are optional."""
    index = {n: i for i, n in enumerate(names)}
    pts = np.asarray(pts, float)
    c, used = {}, {}
    for part in CENTRES:
        for s in SIDES:
            c[part, s], used[f"{part}_{s}"] = _centre(index, pts, part, s)
    missing = [f"{p}_{s}" for p in ("hip", "knee", "ankle") for s in SIDES if c[p, s] is None]
    if missing:
        raise ValueError(f"standing alignment needs hip, knee and ankle centres; no markers for {missing}")
    up = np.asarray(up, float) / np.linalg.norm(up)
    across = c["hip", "r"] - c["hip", "l"]
    right = across - (across @ up) * up
    right /= np.linalg.norm(right)
    fwd = np.cross(up, right)          # kinematics: right = fwd x up
    out = {"method": "standing frame markers", "status": "estimated", "uncertainty": UNCERTAINTY,
           "markers": {k: v for k, v in used.items() if v},
           "knee_frontal_deg": {}, "knee_sagittal_deg": {}, "leg_length_m": {}}
    for s in SIDES:
        hip, knee, ankle = c["hip", s], c["knee", s], c["ankle", s]
        out["knee_frontal_deg"][s] = round(float(_fppa(hip, knee, ankle, fwd, up, right, s)), 2)
        out["knee_sagittal_deg"][s] = round(_knee_sagittal(hip, knee, ankle, fwd, up), 2)
        out["leg_length_m"][s] = round(float(np.linalg.norm(hip - ankle)), 4)
    out["leg_length_difference_mm"] = round(1000 * (out["leg_length_m"]["r"] - out["leg_length_m"]["l"]), 1)
    out["pelvic_obliquity_mm"] = round(1000 * float((c["hip", "r"] - c["hip", "l"]) @ up), 1)   # + right hip higher
    if c["shoulder", "r"] is not None and c["shoulder", "l"] is not None:
        mid = (c["hip", "r"] + c["hip", "l"]) / 2
        out["shoulder_height_difference_mm"] = round(1000 * float((c["shoulder", "r"] - c["shoulder", "l"]) @ up), 1)
        out["shoulder_reach_m"] = {"r": round(float((c["shoulder", "r"] - mid) @ right), 4),
                                   "l": round(float((mid - c["shoulder", "l"]) @ right), 4)}
    return out


def _knee_sagittal(hip, knee, ankle, fwd, up):
    """Standing knee angle in the sagittal plane (deg): 0 straight, + flexed (knee ahead of the hip-ankle line),
    - hyperextended."""
    def proj(p):
        return np.array([p @ fwd, p @ up])
    thigh, shank = proj(knee) - proj(hip), proj(ankle) - proj(knee)
    return -float(np.degrees(np.arctan2(thigh[0] * shank[1] - thigh[1] * shank[0], thigh @ shank)))


def _side_tier(source, approved):
    if source in IMAGING:
        return "A" if approved else "B"
    return "B" if approved else "C"


def check_limb_alignment(rec):
    """Refuse a limb-alignment record that isn't imaging or clinical, has values out of range, or has nothing to
    use. Format: the twin manifest's ``limb_alignment`` ({"right": {...}, "left": {...}}, each side with its
    ``source``), plus ``measured_at``, and optionally ``approved_by``, ``structural``, ``diagnosis``. Returns the
    record's tier (its least-evidenced side)."""
    if not rec.get("measured_at"):
        raise ValueError("measured_at: the date of the imaging or examination")
    sides = [k for k in MANIFEST_SIDES if k in rec]
    if not sides:
        raise ValueError("give 'right' and/or 'left' (twin manifest limb_side)")
    found, ranks = 0, []
    for side in sides:
        v = rec[side]
        source = v.get("source", rec.get("source"))
        if source not in SOURCES:
            raise ValueError(f"{side}.source {source!r}: one of {list(SOURCES)} - camera estimates are screening only "
                             "and never limb alignment")
        unknown = set(v) - set(LIMB_RANGES) - {"source"}
        if unknown:
            raise ValueError(f"{side}: unknown fields {sorted(unknown)} (twin manifest limb_side: {sorted(LIMB_RANGES)})")
        for key, (lo, hi) in LIMB_RANGES.items():
            x = v.get(key)
            if x is None:
                continue
            if not lo <= float(x) <= hi:
                hint = (" (give the deviation from a straight leg, + valgus, not the 180-degree angle)"
                        if key == "mechanical_axis_hka_deg" else "")
                raise ValueError(f"{side}.{key} = {x}: outside {lo:g} to {hi:g}{hint}")
            found += 1
        ranks.append(_side_tier(source, rec.get("approved_by")))
    if not found:
        raise ValueError(f"no alignment values: give at least one of {list(LIMB_RANGES)}")
    if "structural" in rec and not isinstance(rec["structural"], bool):
        raise ValueError("structural: true or false")
    return min(ranks, key="CBA".index)


def knee_hka(rec):
    """{side: mechanical-axis HKA deviation (deg, + valgus)} of a limb-alignment record."""
    return {s: rec[k]["mechanical_axis_hka_deg"] for k, s in MANIFEST_SIDES.items()
            if k in rec and rec[k].get("mechanical_axis_hka_deg") is not None}


def structural_holds(rec):
    """{joint_plane: reason}: knees whose recorded alignment a clinician or imaging calls structural."""
    if not rec or not rec.get("structural"):
        return {}
    out = {}
    for side, s in MANIFEST_SIDES.items():
        v = (rec.get(side) or {}).get("mechanical_axis_hka_deg")
        if v is not None:
            source = rec[side].get("source", rec.get("source"))
            diagnosis = rec.get("diagnosis") or "no diagnosis given"
            out[f"knee_{s}.frontal"] = (f"structural knee alignment on record ({diagnosis}, {v:+g} deg, {source} "
                                        f"{rec['measured_at']})")
    return out


def screening_holds(estimate, recorded=None):
    """{joint_plane: reason}: knees whose camera-estimated standing angle is beyond the screening threshold and
    that have no imaging or clinical value on record (that record knows better than the camera)."""
    if not estimate or "knee_frontal_deg" not in estimate:
        return {}
    known = knee_hka(recorded or {})
    return {f"knee_{s}.frontal": (f"standing knee angle estimated at {v:+g} deg from the camera (uncertainty "
                                  f"{UNCERTAINTY.split(' (')[0]}), beyond the {SCREEN_KNEE_FRONTAL_DEG:g} deg screening "
                                  f"threshold: {CHECK_PROMPT}")
            for s, v in estimate["knee_frontal_deg"].items() if abs(v) > SCREEN_KNEE_FRONTAL_DEG and s not in known}


# ---------------------------------------------------------------- the model

def _osim():
    from .opensim_stage import _osim as o
    return o()


def _knee_joint(model, side):
    js = model.getJointSet()
    for i in range(js.getSize()):
        j = js.get(i)
        if j.getChildFrame().findBaseFrame().getName() == f"{KNEE_JOINT_CHILD}_{side}":
            return j
    raise ValueError(f"no joint with child body {KNEE_JOINT_CHILD}_{side} in the model")


def model_knee_frontal(model, state, side):
    """The model's thigh-shank angle in the frontal plane (deg, + valgus) from its joint centres (body origins),
    with the pelvis frame as the reference (its default pose: x forward, y up)."""
    bodies = model.getBodySet()

    def origin(b):
        p = bodies.get(b).getPositionInGround(state)
        return np.array([p.get(i) for i in range(3)])
    R = bodies.get("pelvis").getTransformInGround(state).R()
    fwd = np.array([R.get(0, 0), 0.0, R.get(2, 0)])
    fwd /= np.linalg.norm(fwd)
    up = np.array([0.0, 1.0, 0.0])
    return float(_fppa(origin(f"femur_{side}"), origin(f"tibia_{side}"), origin(f"talus_{side}"), fwd, up,
                       np.cross(fwd, up), side))


def _rx(a):
    c, s = np.cos(a), np.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def _euler_xyz(R):
    """Body-fixed X-Y-Z angles (OpenSim's frame orientation) of a rotation matrix."""
    return [float(np.arctan2(-R[1, 2], R[2, 2])), float(np.arcsin(np.clip(R[0, 2], -1, 1))),
            float(np.arctan2(-R[0, 1], R[0, 0]))]


def _rot_xyz(a):
    ca, sa = np.cos(a), np.sin(a)
    rx = np.array([[1, 0, 0], [0, ca[0], -sa[0]], [0, sa[0], ca[0]]])
    ry = np.array([[ca[1], 0, sa[1]], [0, 1, 0], [-sa[1], 0, ca[1]]])
    rz = np.array([[ca[2], -sa[2], 0], [sa[2], ca[2], 0], [0, 0, 1]])
    return rx @ ry @ rz


def apply_to_model(model_path, out_path, hka_deg, tol_deg=0.05):
    """Turn each knee's frame on the femur about the femur's forward (x) axis until the model's default-pose
    hip-knee-ankle angle on its joint centres is ``hka_deg`` {side: deg, + valgus} (from a limb-alignment record).
    Returns {side: {"before_deg", "after_deg", "tilt_deg", "joint"}}."""
    osim = _osim()
    model = osim.Model(str(model_path))
    angle = model_knee_frontal
    done = {}
    for s, target in hka_deg.items():
        if target is None:
            continue
        frame = osim.PhysicalOffsetFrame.safeDownCast(_knee_joint(model, s).getParentFrame())
        o = frame.get_orientation()
        R0 = _rot_xyz(np.array([o.get(i) for i in range(3)]))

        def angle_at(tilt, frame=frame, R0=R0, s=s):
            frame.set_orientation(osim.Vec3(*_euler_xyz(_rx(tilt) @ R0)))
            return angle(model, model.initSystem(), s)
        before, probe = angle_at(0.0), np.radians(0.5)
        slope = (angle_at(probe) - before) / probe          # near +-1: the angle follows the tilt
        tilt = (target - before) / slope
        for _ in range(6):
            now = angle_at(tilt)
            if abs(now - target) < tol_deg:
                break
            tilt += (target - now) / slope
        else:
            raise RuntimeError(f"knee_{s}: reached {now:.2f} deg, not {target:g}")
        done[s] = {"before_deg": round(before, 2), "after_deg": round(now, 2), "tilt_deg": round(float(np.degrees(tilt)), 2),
                   "joint": _knee_joint(model, s).getName()}
    model.finalizeConnections()
    model.printToXML(str(out_path))
    return done
