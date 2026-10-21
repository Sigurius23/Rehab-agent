"""Joint-angle bookkeeping: which coordinate is which joint and which plane.

Planes are reported separately and never averaged together — the accuracy
targets in docs/accuracy.md are per joint *and* per plane.
"""
from __future__ import annotations

import re

import numpy as np

PLANES = ("sagittal", "frontal", "transverse")

# (regex on coordinate name, joint label template, plane)
_RULES = [
    (r"^pelvis_tilt$", "pelvis", "sagittal"),
    (r"^pelvis_list$", "pelvis", "frontal"),
    (r"^pelvis_rotation$", "pelvis", "transverse"),
    (r"^pelvis_t[xyz]$", "pelvis", "translation"),
    (r"^hip_flexion_([rl])$", "hip_{0}", "sagittal"),
    (r"^hip_adduction_([rl])$", "hip_{0}", "frontal"),
    (r"^hip_rotation_([rl])$", "hip_{0}", "transverse"),
    (r"^knee_angle_([rl])$", "knee_{0}", "sagittal"),
    (r"^knee_angle_([rl])_beta$", "patella_{0}", "coupled"),
    (r"^ankle_angle_([rl])$", "ankle_{0}", "sagittal"),
    (r"^subtalar_angle_([rl])$", "subtalar_{0}", "frontal"),
    (r"^mtp_angle_([rl])$", "mtp_{0}", "sagittal"),
    (r"^(L\d_[ST]?\d*)_?Flex_Ext$", "lumbar", "sagittal"),
    (r"^(L\d_[ST]?\d*)_?Lat_Bending$", "lumbar", "frontal"),
    (r"^(L\d_[ST]?\d*)_?axial_rotation$", "lumbar", "transverse"),
    (r"^lumbar_extension$", "lumbar", "sagittal"),
    (r"^lumbar_bending$", "lumbar", "frontal"),
    (r"^lumbar_rotation$", "lumbar", "transverse"),
    (r"^neck_flexion$", "neck", "sagittal"),
    (r"^neck_bending$", "neck", "frontal"),
    (r"^neck_rotation$", "neck", "transverse"),
    (r"^arm_flex_([rl])$", "shoulder_{0}", "sagittal"),
    (r"^arm_add_([rl])$", "shoulder_{0}", "frontal"),
    (r"^arm_rot_([rl])$", "shoulder_{0}", "transverse"),
    (r"^elbow_flex_([rl])$", "elbow_{0}", "sagittal"),
    (r"^pro_sup_([rl])$", "forearm_{0}", "transverse"),
    (r"^wrist_flex_([rl])$", "wrist_{0}", "sagittal"),
    (r"^wrist_dev_([rl])$", "wrist_{0}", "frontal"),
    (r"^Abs_", "abdomen", "coupled"),
]


def classify(coord):
    """Return (joint, plane) for an OpenSim coordinate name, or (None, None)."""
    for pat, joint, plane in _RULES:
        m = re.match(pat, coord)
        if m:
            return joint.format(*m.groups()), plane
    return None, None


def classify_signal(name):
    """(joint, plane) for coordinates and derived signals ('torso.sagittal', 'knee_fppa_r', 'lumbar_total.frontal')."""
    if "." in name:
        body, plane = name.split(".", 1)
        return ("lumbar" if body == "lumbar_total" else f"{body}_segment"), plane
    if name.startswith("knee_fppa_"):
        return f"knee_{name[-1]}", "frontal"
    return classify(name)


def primary_lumbar(columns):
    """The lumbar coordinate that carries the trunk motion (L5_S1 in Pose2Sim, lumbar_* in Rajagopal)."""
    for c in ("L5_S1_Flex_Ext", "lumbar_extension"):
        if c in columns:
            return c
    return None


def segment_orientations(model_path, table, bodies=("torso", "pelvis", "head")):
    """Inclination of body long axes relative to gravity, in the pelvis heading frame.

    Returns {body: {"sagittal_deg": (T,), "frontal_deg": (T,)}} where sagittal
    is forward lean (+, atan2 in the heading plane) and frontal is the lateral
    inclination of the long axis (+ to the subject's right, asin of its
    sideways component).
    Also returns knee frontal-plane projection angles from joint centres.
    """
    import opensim as osim
    osim.Logger.setLevelString("error")
    model = osim.Model(str(model_path))
    state = model.initSystem()
    cs = model.getCoordinateSet()
    cols = [c for c in table.columns if cs.contains(c)]
    present = [b for b in bodies if model.getBodySet().contains(b)]
    out = {b: {"sagittal_deg": np.zeros(len(table.time)), "frontal_deg": np.zeros(len(table.time))} for b in present}
    fppa = {s: np.zeros(len(table.time)) for s in ("r", "l")}
    for f in range(len(table.time)):
        for c in cols:
            coord = cs.get(c)
            v = table.data[f, table.columns.index(c)]
            if coord.getMotionType() == osim.Coordinate.Rotational and table.in_degrees:
                v = np.radians(v)
            coord.setValue(state, v, False)
        model.realizePosition(state)
        Rp = _rot(model.getBodySet().get("pelvis").getTransformInGround(state))
        fwd = Rp[:, 0].copy()
        fwd[1] = 0.0
        fwd /= np.linalg.norm(fwd)
        up = np.array([0.0, 1.0, 0.0])
        right = np.cross(fwd, up)
        for b in present:
            axis = _rot(model.getBodySet().get(b).getTransformInGround(state))[:, 1]
            out[b]["sagittal_deg"][f] = np.degrees(np.arctan2(axis @ fwd, axis @ up))
            # lateral component only, so it stays defined when the trunk bends past horizontal
            out[b]["frontal_deg"][f] = np.degrees(np.arcsin(np.clip(axis @ right, -1.0, 1.0)))
        for s in ("r", "l"):
            hip, knee, ankle = (_origin(model, state, f"{n}_{s}") for n in ("femur", "tibia", "talus"))
            fppa[s][f] = _fppa(hip, knee, ankle, fwd, up, right, s)
    return out, fppa


def _rot(transform):
    R = transform.R()
    return np.array([[R.get(i, j) for j in range(3)] for i in range(3)])


def _origin(model, state, body):
    p = model.getBodySet().get(body).getPositionInGround(state)
    return np.array([p.get(0), p.get(1), p.get(2)])


def _fppa(hip, knee, ankle, fwd, up, right, side):
    """Knee frontal-plane projection angle (deg): 0 = straight; + = valgus (knee medial).

    Hip, knee and ankle centres are projected onto the frontal plane; the
    angle is the deviation of the knee from the hip-ankle line, signed so that
    medial knee displacement (valgus) is positive for both legs.
    """
    def proj(p):
        return np.array([p @ right, p @ up])
    h, k, a = proj(hip), proj(knee), proj(ankle)
    thigh, shank = k - h, a - k
    ang = np.degrees(np.arctan2(thigh[0] * shank[1] - thigh[1] * shank[0], thigh @ shank))
    # A medially displaced right knee bends the chain counter-clockwise when
    # viewed from the front (x = subject's right); mirror for the left leg.
    return ang if side == "r" else -ang
