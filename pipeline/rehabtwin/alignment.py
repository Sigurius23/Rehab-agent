"""Skeletal alignment: the person's own standing geometry (twin layer ``joint_alignment``).

Lengths alone make every person a scaled copy of the generic skeleton. People differ in how their bones sit:
knock knees (genu valgum) or bow legs (genu varum), a knee that stands bent or hyperextended, one leg longer,
one hip or shoulder higher. The generic OpenSim knee bends about one axis and has no frontal-plane freedom of
its own, so inverse kinematics of a valgus knee has to put the difference somewhere else (hip adduction and
rotation), and a posture rule with a fixed valgus threshold coaches the person against their own skeleton.

This module:

- **measures** the standing alignment from a session's static frame (``measure``): per side the knee's
  frontal-plane angle between thigh and shank (+ valgus, the same definition as the ``knee_fppa`` signal), the
  standing knee flexion (- hyperextension), leg length (hip to ankle centre), pelvic obliquity, shoulder height
  difference and each shoulder's reach from the midline. From markers on the skin or predicted from video, so
  Tier C: it can't tell a structural deformity from a habitual posture.
- **checks** alignment records from a clinician or imaging (``check_record``): long-leg standing radiograph,
  EOS, CT or MRI (Tier B, A when approved), clinical examination (Tier C, B when approved). They may also say
  whether the alignment is structural and give torsion values, which are stored but not yet applied.
- **applies** the knee's frontal angle to a model (``apply_to_model``): the knee joint's frame on the femur is
  turned about the femur's forward axis until the model's thigh-shank angle in its default pose is the
  person's. The tibia, its markers, muscles and the foot follow. An imaging or clinical value is the
  mechanical axis (hip, knee and ankle joint centres) and is matched on the model's joint centres; a value
  measured on markers is matched on the model's own markers measured the same way, because skin markers sit
  off the joint centres (on the Pose2Sim model: about 0.7 deg more valgus, and 94 % of a tilt).
- **flags** joints where a posture cue must wait for a clinician (``structural_flags``): a record that says the
  alignment is structural, or a standing knee angle beyond ``SCREEN_KNEE_FRONTAL_DEG`` (a screening threshold of
  ours, not a diagnostic cut-off).
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
SCREEN_KNEE_FRONTAL_DEG = 6.0     # standing knee angle beyond which valgus cues wait for a clinician (ours, not a norm)
IMAGING = ("long-leg standing radiograph", "EOS", "CT", "MRI")
METHODS = IMAGING + ("clinical examination", "standing frame markers")
RANGES = {"knee_frontal_deg": (-30.0, 30.0), "knee_sagittal_deg": (-25.0, 40.0), "leg_length_m": (0.5, 1.3),
          "femoral_anteversion_deg": (-30.0, 60.0), "tibial_torsion_deg": (-30.0, 60.0)}
PER_SIDE = tuple(RANGES)
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
    out = {"method": "standing frame markers", "markers": {k: v for k, v in used.items() if v},
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


def tier_of(rec):
    m = rec["method"]
    if m in IMAGING:
        return "A" if rec.get("approved_by") else "B"
    if m == "clinical examination":
        return "B" if rec.get("approved_by") else "C"
    return "C"


def check_record(rec):
    """Refuse an alignment record with an unknown method, values out of range, or nothing to use. Returns the
    record's tier. Per-side values are {"r": .., "l": ..}; ``structural`` (bool) and ``diagnosis`` optional."""
    if rec.get("method") not in METHODS:
        raise ValueError(f"method {rec.get('method')!r}: one of {list(METHODS)}")
    if rec["method"] != "standing frame markers" and not rec.get("date"):
        raise ValueError("a clinical or imaging record needs its date")
    found = 0
    for key, (lo, hi) in RANGES.items():
        v = rec.get(key)
        if v is None:
            continue
        if not isinstance(v, dict) or not set(v) <= set(SIDES):
            raise ValueError(f"{key}: give {{'r': value, 'l': value}}")
        for s, x in v.items():
            if x is None:
                continue
            if not lo <= float(x) <= hi:
                raise ValueError(f"{key}.{s} = {x}: outside {lo} to {hi} (signs: + valgus, + flexion, + external)")
            found += 1
    if not found:
        raise ValueError(f"no alignment values: give at least one of {list(RANGES)}")
    if rec.get("knee_frontal_axis", "mechanical") != "mechanical":
        raise ValueError("knee_frontal_deg must be the mechanical axis (hip, knee and ankle joint centres); "
                         "convert an anatomical tibiofemoral angle before recording it")
    if "structural" in rec and not isinstance(rec["structural"], bool):
        raise ValueError("structural: true or false")
    if rec.get("structural") and rec["method"] == "standing frame markers":
        raise ValueError("markers on a standing person can't tell a structural deformity from a posture")
    return tier_of(rec)


def structural_flags(rec):
    """{joint_plane: reason} where posture cues must wait for a clinician-set target."""
    if not rec:
        return {}
    out = {}
    for s in SIDES:
        v = (rec.get("knee_frontal_deg") or {}).get(s)
        if rec.get("structural") and v is not None:
            out[f"knee_{s}.frontal"] = (f"structural knee alignment recorded ({rec.get('diagnosis') or 'no diagnosis given'}, "
                                        f"{v:+g} deg, {rec['method']} {rec.get('date', '')})".replace(" )", ")"))
        elif v is not None and abs(v) > SCREEN_KNEE_FRONTAL_DEG:
            out[f"knee_{s}.frontal"] = (f"standing knee angle {v:+g} deg ({rec['method']}) is beyond the "
                                        f"{SCREEN_KNEE_FRONTAL_DEG:g} deg screening threshold: may be structural")
    return out


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


def model_marker_knee_frontal(model, state, side):
    """The model's knee frontal angle measured on its own markers as ``measure`` measures a person."""
    ms = model.getMarkerSet()
    names = [ms.get(i).getName() for i in range(ms.getSize())]
    pts = []
    for n in names:
        p = ms.get(n).getLocationInGround(state)
        pts.append([p.get(i) for i in range(3)])
    return measure(names, pts)["knee_frontal_deg"][side]


def apply_to_model(model_path, out_path, knee_frontal_deg, match="joint_centres", tol_deg=0.05):
    """Turn each knee's frame on the femur about the femur's forward (x) axis until the model's default-pose
    knee frontal angle is ``knee_frontal_deg`` {side: deg}, on its joint centres (``match="joint_centres"``:
    imaging, clinical) or on its markers (``"markers"``: a value measured on markers). Returns {side:
    {"before_deg", "after_deg", "tilt_deg", "joint", "matched_on"}}."""
    if match not in ("joint_centres", "markers"):
        raise ValueError(f"match: 'joint_centres' or 'markers', not {match!r}")
    osim = _osim()
    model = osim.Model(str(model_path))
    angle = model_knee_frontal if match == "joint_centres" else model_marker_knee_frontal
    done = {}
    for s, target in knee_frontal_deg.items():
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
                   "joint": _knee_joint(model, s).getName(), "matched_on": match}
    model.finalizeConnections()
    model.printToXML(str(out_path))
    return done
