"""Synthetic sessions with known ground truth, generated from an OpenSim model.

Used to test the whole back-end (frames, gaps, filtering, scaling, IK,
metrics, validation) where the right answer is known exactly. A synthetic
session is always labelled ``synthetic`` and can never pass as patient data.

The generator:
1. scales the generic model by known per-segment factors (a "different body"),
2. drives it through an exercise with known joint angles,
3. reads out marker/joint-centre positions, projects them into an OpenCV
   camera frame like a monocular front-end would, and adds jitter/dropouts.
"""
from __future__ import annotations

import numpy as np

from .io_formats import write_table
from .opensim_stage import JC_PREFIX, _osim, prepare_model
from .sequence import MarkerSequence
from .skel_names import SKEL_POSE_PARAM_NAMES

DEFAULT_SUBJECT_SCALES = {
    "pelvis": 1.04, "sacrum": 1.04,
    "femur_r": 1.07, "patella_r": 1.07, "femur_l": 1.07, "patella_l": 1.07,
    "tibia_r": 1.05, "tibia_l": 1.05,
    "talus_r": 1.02, "calcn_r": 1.02, "toes_r": 1.02, "talus_l": 1.02, "calcn_l": 1.02, "toes_l": 1.02,
    "torso": 0.97, "lumbar1": 0.97, "lumbar2": 0.97, "lumbar3": 0.97, "lumbar4": 0.97, "lumbar5": 0.97,
    "Abdomen": 0.97, "head": 1.0,
    "humerus_r": 1.03, "humerus_l": 1.03, "ulna_r": 1.02, "radius_r": 1.02, "ulna_l": 1.02, "radius_l": 1.02,
    "hand_r": 1.0, "hand_l": 1.0,
}


def squat_motion(fps=30.0, duration_s=12.0, reps=3, depth_knee_deg=95.0, valgus_r_deg=6.0):
    """Joint-angle trajectories (deg) for a bodyweight squat with right-knee valgus.

    Starts with 1.5 s of quiet neutral stance (the protocol's static window).
    """
    t = np.arange(int(round(duration_s * fps))) / fps
    quiet = 1.5
    phase = np.clip((t - quiet) / (duration_s - quiet - 0.5), 0, 1)
    s = 0.5 * (1 - np.cos(2 * np.pi * reps * phase))  # 0..1 per rep
    s[t < quiet] = 0.0
    q = {
        "knee_angle_r": depth_knee_deg * s, "knee_angle_l": depth_knee_deg * s,
        "hip_flexion_r": 90.0 * s, "hip_flexion_l": 88.0 * s,
        "ankle_angle_r": 28.0 * s, "ankle_angle_l": 27.0 * s,
        "hip_adduction_r": valgus_r_deg * s, "hip_adduction_l": -1.0 * s,
        "hip_rotation_r": 5.0 * s, "hip_rotation_l": 0.0 * s,
        "pelvis_tilt": -20.0 * s, "pelvis_list": 1.5 * s, "pelvis_rotation": 3.0 * s,
        # Pose2Sim's lumbar couplers amplify L5_S1 ~7x over the five levels: -3 deg ~ -21 deg total
        "L5_S1_Flex_Ext": -3.0 * s, "L5_S1_Lat_Bending": 0.6 * s, "L5_S1_axial_rotation": 0.3 * s,
        "arm_flex_r": 70.0 * s, "arm_flex_l": 70.0 * s,
        "arm_add_r": -10.0 + 0 * s, "arm_add_l": -10.0 + 0 * s,
        "elbow_flex_r": 15.0 + 10.0 * s, "elbow_flex_l": 15.0 + 10.0 * s,
        "pro_sup_r": 80.0 + 0 * s, "pro_sup_l": 80.0 + 0 * s,
        "neck_flexion": 10.0 * s,
    }
    return t, q


def look_at_camera(eye, target):
    """Rotation/translation ground -> OpenCV camera (x right, y down, z forward)."""
    eye, target = np.asarray(eye, float), np.asarray(target, float)
    z = target - eye
    z /= np.linalg.norm(z)
    up = np.array([0.0, 1.0, 0.0])
    x = np.cross(z, up)  # right in the image
    x /= np.linalg.norm(x)
    y = np.cross(z, x)  # down in the image
    R = np.stack([x, y, z])
    return R, -R @ eye


def generate(cfg, out_dir, fps=30.0, duration_s=12.0, seed=0, noise_m=0.004, drift_m=0.006, marker_offset_m=0.01,
             dropouts=((150, 153), (260, 262)), scales=None, motion=None,
             camera_eye=(2.6, 1.3, 1.6), camera_target=(0.0, 0.9, 0.0)):
    """Return (MarkerSequence in camera frame, truth dict with coordinate trajectories)."""
    osim = _osim()
    rng = np.random.default_rng(seed)
    out_dir.mkdir(parents=True, exist_ok=True)
    from .skel_names import SKEL_JOINT_NAMES
    jc_names = [JC_PREFIX + j for j in SKEL_JOINT_NAMES if j in cfg.get("joint_centre_markers", {})]
    data_names = _model_marker_names(cfg) | set(jc_names)
    generic, names, _ = prepare_model(cfg, out_dir, data_names)
    model = osim.Model(str(generic))
    state = model.initSystem()

    scale_set = osim.ScaleSet()
    for body, f in (scales or DEFAULT_SUBJECT_SCALES).items():
        if model.getBodySet().contains(body):
            sc = osim.Scale()
            sc.setSegmentName(body)
            sc.setScaleFactors(osim.Vec3(f, f, f))
            sc.setApply(True)
            scale_set.cloneAndAppend(sc)
    model.scale(state, scale_set, True, 72.0)
    # Subject-specific marker discrepancy: the subject's skin points are not
    # exactly where the generic marker set puts them (joint centres are exact).
    for i in range(model.getMarkerSet().getSize()):
        mk = model.updMarkerSet().get(i)
        if mk.getName().startswith(JC_PREFIX) or marker_offset_m <= 0:
            continue
        loc = mk.get_location()
        off = rng.normal(0, marker_offset_m / np.sqrt(3), 3)
        mk.set_location(osim.Vec3(loc.get(0) + off[0], loc.get(1) + off[1], loc.get(2) + off[2]))
    state = model.initSystem()
    true_model = out_dir / "truth_model.osim"
    model.printToXML(str(true_model))

    t, qdeg = motion if motion is not None else squat_motion(fps, duration_s)
    cs = model.getCoordinateSet()
    coord_names = [cs.get(i).getName() for i in range(cs.getSize())]
    T = len(t)
    marker_set = model.getMarkerSet()
    m_names = [marker_set.get(i).getName() for i in range(marker_set.getSize())]
    ground = np.zeros((T, len(m_names), 3))
    truth = np.zeros((T, len(coord_names)))
    for f in range(T):
        for i, cn in enumerate(coord_names):
            c = cs.get(i)
            if c.isConstrained(state) or c.getLocked(state):
                continue
            if cn in qdeg:
                v = qdeg[cn][f]
                c.setValue(state, np.radians(v) if c.getMotionType() == osim.Coordinate.Rotational else v, False)
            elif cn == "pelvis_ty":
                c.setValue(state, c.getDefaultValue(), False)
            else:
                c.setValue(state, c.getDefaultValue() if cn.startswith(("arm_", "pro_sup", "elbow")) else 0.0, False)
        # keep the feet planted: move the pelvis by however far the feet moved
        model.assemble(state)
        model.realizePosition(state)
        if f == 0:
            foot0 = _foot_anchor(model, state)
        drift_feet = _foot_anchor(model, state) - foot0
        for axis, cn in enumerate(("pelvis_tx", "pelvis_ty", "pelvis_tz")):
            c = cs.get(cn)
            c.setValue(state, c.getValue(state) - drift_feet[axis], False)
        model.realizePosition(state)
        for i in range(len(coord_names)):
            c = cs.get(i)
            v = c.getValue(state)
            truth[f, i] = np.degrees(v) if c.getMotionType() == osim.Coordinate.Rotational else v
        for k, mn in enumerate(m_names):
            p = marker_set.get(mn).getLocationInGround(state)
            ground[f, k] = [p.get(0), p.get(1), p.get(2)]

    # neutral static pose (q = 0, arms down) for scaling, like SKEL q = 0
    for i in range(cs.getSize()):
        c = cs.get(i)
        if not c.isConstrained(state) and not c.getLocked(state):
            c.setValue(state, 0.0 if c.getName() != "pelvis_ty" else c.getDefaultValue(), False)
    model.assemble(state)
    model.realizePosition(state)
    static = np.array([[marker_set.get(mn).getLocationInGround(state).get(k) for k in range(3)] for mn in m_names])

    # camera projection (positions only; a front-end gives 3D in camera frame)
    Rc, tc = look_at_camera(camera_eye, camera_target)
    cam = ground @ Rc.T + tc
    jitter = rng.normal(0, noise_m, cam.shape)
    phase = rng.uniform(0, 2 * np.pi, (1, cam.shape[1], 3))
    drift = drift_m * np.sin(2 * np.pi * 0.4 * t[:, None, None] + phase)
    cam = cam + jitter + drift
    valid = np.ones(T, bool)
    for a, b in dropouts:
        valid[a:b] = False
    cam[~valid] = np.nan

    is_jc = [n.startswith(JC_PREFIX) for n in m_names]
    mk_names = [n for n, j in zip(m_names, is_jc) if not j]
    jn = [n for n, j in zip(m_names, is_jc) if j]
    mk_idx = [i for i, j in enumerate(is_jc) if not j]
    jc_idx = [i for i, j in enumerate(is_jc) if j]
    skel_poses = np.zeros((T, len(SKEL_POSE_PARAM_NAMES)))
    for i, n in enumerate(SKEL_POSE_PARAM_NAMES):
        if n in coord_names and not n.startswith("pelvis_"):
            skel_poses[:, i] = np.radians(truth[:, coord_names.index(n)])
    skel_poses[~valid] = np.nan
    seq = MarkerSequence(
        fps=fps, frame="opencv_camera", marker_names=mk_names, markers=cam[:, mk_idx],
        valid=valid, joint_names=jn, joints=cam[:, jc_idx],
        static_markers=static[mk_idx], static_joints=static[jc_idx], skel_poses=skel_poses,
        meta={"source": "synthetic", "synthetic": True, "generator": "rehabtwin.synthetic.generate",
              "seed": seed, "noise_m": noise_m, "drift_m": drift_m, "marker_offset_m": marker_offset_m, "dropouts": [list(d) for d in dropouts],
              "scales": scales or DEFAULT_SUBJECT_SCALES, "camera_eye": list(camera_eye)},
    )
    write_table(out_dir / "truth.mot", coord_names, truth, t, in_degrees=True, name="synthetic_truth")
    return seq, {"time": t, "coord_names": coord_names, "coords": truth, "model": true_model,
                 "mot": out_dir / "truth.mot"}


def _model_marker_names(cfg):
    osim = _osim()
    from pathlib import Path
    from .config import resolve
    ms = osim.MarkerSet(str(resolve(cfg["marker_set"], Path(cfg["_path"]).parent)))
    return {ms.get(i).getName() for i in range(ms.getSize())}


def _foot_anchor(model, state):
    """Mean heel-body origin: kept fixed so the synthetic feet stay planted."""
    pts = []
    for b in ("calcn_r", "calcn_l"):
        p = model.getBodySet().get(b).getPositionInGround(state)
        pts.append([p.get(0), p.get(1), p.get(2)])
    return np.mean(pts, axis=0)
