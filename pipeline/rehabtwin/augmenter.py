"""Anatomical-marker augmentation for sparse video keypoints (OpenCap's LSTM, via Pose2Sim).

Video keypoints (MediaPipe, OpenPose, ...) put two points on the pelvis — the hips —
which fix its left-right axis but not its tilt. With the trunk held only by the shoulders,
inverse kinematics can then trade pelvis tilt against hip flexion and lumbar flexion freely:
on a real 5-camera squat (docs/validation-results.md) it settled on ~95° pelvis tilt with
56° lumbar *extension*. OpenCap (Uhlrich et al. 2023) solves this with an LSTM that predicts
43 anatomical markers (ASIS/PSIS, femoral epicondyles, malleoli, ...) from 15 + 7 keypoints,
the subject's height and mass. Pose2Sim ships that model as ONNX; this module runs it from
the Pose2Sim clone (``upstream_root()``), so no weights are copied here.

Inputs must be metric and y-up (``yup_world``; a camera-frame sequence is first rotated with
its recorded gravity vector). MediaPipe has no small toe, so it is synthesised the way Pose2Sim
does (``common.add_smalltoe_data``). The augmenter was trained on OpenPose-style keypoints;
MediaPipe's hip landmarks sit differently, which is one more reason the output is Tier C until
validated against marker mocap.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from .config import resolve
from .filtering import interpolate_gaps
from .frames import apply, rotation_between
from .sequence import MarkerSequence

MODEL_DIR = "upstream:perfanalytics/pose2sim/Pose2Sim/MarkerAugmenter/LSTM"
FEATURES = {
    "lower": ["Neck", "RShoulder", "LShoulder", "RHip", "LHip", "RKnee", "LKnee", "RAnkle", "LAnkle",
              "RHeel", "LHeel", "RSmallToe", "LSmallToe", "RBigToe", "LBigToe"],
    "upper": ["Neck", "RShoulder", "LShoulder", "RElbow", "LElbow", "RWrist", "LWrist"],
}
RESPONSES = {
    "lower": ["r.ASIS_study", "L.ASIS_study", "r.PSIS_study", "L.PSIS_study", "r_knee_study", "r_mknee_study",
              "r_ankle_study", "r_mankle_study", "r_toe_study", "r_5meta_study", "r_calc_study", "L_knee_study",
              "L_mknee_study", "L_ankle_study", "L_mankle_study", "L_toe_study", "L_calc_study", "L_5meta_study",
              "r_shoulder_study", "L_shoulder_study", "C7_study", "r_thigh1_study", "r_thigh2_study", "r_thigh3_study",
              "L_thigh1_study", "L_thigh2_study", "L_thigh3_study", "r_sh1_study", "r_sh2_study", "r_sh3_study",
              "L_sh1_study", "L_sh2_study", "L_sh3_study", "RHJC_study", "LHJC_study"],
    "upper": ["r_lelbow_study", "r_melbow_study", "r_lwrist_study", "r_mwrist_study", "L_lelbow_study",
              "L_melbow_study", "L_lwrist_study", "L_mwrist_study"],
}


def _unit(v):
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-9)


def keypoint_features(pts):
    """Add Neck (mid-shoulders), midHip and the small toes to a {name: (T, 3)} dict (y-up, metres)."""
    out = dict(pts)
    out["Neck"] = (pts["RShoulder"] + pts["LShoulder"]) / 2
    out["midHip"] = (pts["RHip"] + pts["LHip"]) / 2
    right = _unit(pts["RHip"] - pts["LHip"])
    for s, sign in (("R", 1.0), ("L", -1.0)):
        if f"{s}SmallToe" in pts:
            continue
        toe, heel = pts[f"{s}BigToe"], pts[f"{s}Heel"]
        length = np.linalg.norm(toe - heel, axis=1, keepdims=True)
        # Pose2Sim rule: half a foot length lateral, a fifth of it back towards the heel
        out[f"{s}SmallToe"] = toe + sign * 0.5 * length * right - 0.2 * length * _unit(toe - heel)
    return out


def predict(pts, height_m, mass_kg, part, version="v0.3"):
    """Run one augmenter (``part`` = 'lower' | 'upper'). Returns {marker: (T, 3)}."""
    import onnxruntime as ort
    d = Path(resolve(f"{MODEL_DIR}/{version}_{part}"))
    ref = pts["midHip"]
    x = np.concatenate([(pts[f] - ref) / height_m for f in FEATURES[part]], axis=1)
    x = np.concatenate([x, np.full((len(x), 1), height_m), np.full((len(x), 1), mass_kg)], axis=1)
    x = (x - np.load(d / "mean.npy", allow_pickle=False)) / np.load(d / "std.npy", allow_pickle=False)
    sess = ort.InferenceSession(str(d / "model.onnx"), providers=["CPUExecutionProvider"])
    y = sess.run(None, {sess.get_inputs()[0].name: x[None].astype(np.float32)})[0][0]
    y = y.reshape(len(x), -1, 3) * height_m + ref[:, None, :]
    return {n: y[:, k] for k, n in enumerate(RESPONSES[part])}


def augment(seq: MarkerSequence, height_m, mass_kg, version="v0.3", config="mediapipe_lstm_pose2sim", max_gap_s=0.2,
            mass_source="assumed"):
    """Sequence with the 43 augmented markers appended (frame ``yup_world``).

    ``mass_kg`` is an LSTM input, so it is needed even when nobody weighed the person; ``mass_source``
    ('measured' or 'assumed') records which, and ``process`` carries both over (only a measured one
    lets muscle and strength work run without --allow-assumed-mass).

    The LSTM needs dense input, so every gap is interpolated before it runs, but a part's
    outputs are NaN wherever one of its inputs was missing for longer than ``max_gap_s``
    (the stage's bridging limit): a marker predicted from a frozen keypoint is not data. The
    stage does not solve frames left without most of the IK marker weight (lower part masked).
    Frames predicted from bridged (short-gap) inputs are listed in meta for the stage's QC.
    """
    if mass_source not in ("measured", "assumed"):
        raise ValueError(f"mass_source must be 'measured' or 'assumed', got {mass_source!r}")
    X = np.asarray(seq.markers, float)
    meta = dict(seq.meta)
    if seq.frame == "opencv_camera":
        up = meta.get("gravity_up_cv")
        if up is None:
            raise ValueError("camera-frame sequence without meta['gravity_up_cv']: the augmenter needs y-up input")
        X = apply(rotation_between(up, [0.0, 1.0, 0.0]), X)
        meta["augmenter_rotated_from"] = "opencv_camera via gravity_up_cv"
    elif seq.frame != "yup_world":
        raise ValueError(f"augmenter needs a metric y-up sequence, got frame {seq.frame!r}")
    valid = seq.valid if seq.valid is not None else np.isfinite(X).all(axis=(1, 2))
    Xi = interpolate_gaps(X)     # the LSTM runs over the whole sequence; gap frames stay invalid below
    pts = keypoint_features({n: Xi[:, k] for k, n in enumerate(seq.marker_names)})
    missing = sorted({f for p in FEATURES.values() for f in p} - set(pts))
    if missing:
        raise ValueError(f"augmenter inputs missing from the sequence: {missing}")
    # raw inputs and inputs with only bridgeable gaps filled; NaN propagates into Neck, midHip and the toes
    feats = [keypoint_features({n: A[:, k] for k, n in enumerate(seq.marker_names)})
             for A in (X, interpolate_gaps(X, int(round(max_gap_s * seq.fps))))]
    new, masked, bridged = {}, {}, np.zeros(len(X), bool)
    for part in ("lower", "upper"):
        gone = [~np.isfinite(np.stack([d[f] for f in FEATURES[part] + ["midHip"]], axis=1)).all(axis=(1, 2))
                for d in feats]
        lost = gone[1]
        bridged |= gone[0] & ~lost
        for n, v in predict(pts, height_m, mass_kg, part, version).items():
            new[n] = np.where(lost[:, None], np.nan, v)
        masked[part] = int((lost & valid).sum())
    names = list(seq.marker_names) + list(new)
    out = np.concatenate([X, np.stack([new[n] for n in new], axis=1)], axis=1)
    out[~valid] = np.nan
    meta.update(default_config=config, augmenter={
        "model": f"OpenCap LSTM marker augmenter {version} (Uhlrich et al. 2023, Apache-2.0) via Pose2Sim ONNX",
        "height_m": height_m, "mass_kg": mass_kg, "mass_source": mass_source, "synthesised_inputs": ["Neck", "midHip", "RSmallToe", "LSmallToe"],
        "max_gap_s": max_gap_s, "frames_masked_input_gap": masked,
        "imputed_input_frames": seq.frame_index[bridged & valid].tolist()})  # the stage lists these as imputed
    return MarkerSequence(fps=seq.fps, marker_names=names, markers=out, frame="yup_world", valid=valid,
                          frame_index=seq.frame_index, meta=meta)
