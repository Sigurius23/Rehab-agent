#!/usr/bin/env python3
"""BEDLAM2 bodies as a testing ground across body types (data under its own licence: never commit it).

BEDLAM2 (Max Planck Institute for Intelligent Systems, non-commercial research licence, no redistribution)
ships per-sequence SMPL-X ground truth: 16 shape parameters and per-frame pose for ~1,500 bodies, sized XS
to 6XL. With the SMPL-X model "with removed head bun" (locked head; ``smplx_lockedhead_20230207.zip``, from
smpl-x.is.tue.mpg.de; its shape space differs from SMPL-X v1.1) the bodies can be rebuilt here.

    python adapters/bedlam2.py offsets --model SMPLX_NEUTRAL.npz --motions motions_npz_training/ --out offsets.json

measures, for every body in its rest pose, how far each joint centre lies behind the skin when seen from
the front: the distance ``rehabtwin.kinect`` has to add to a depth-sensor reading. It fits
``offset = height * (a + b * (BMI - 25))`` per joint and prints the table ``SURFACE_TO_CENTRE`` uses.

Only numeric arrays are read from the downloaded files (``allow_pickle=False``): the model's two pickled
dictionaries (``part2num``, ``joint2num``) are skipped.
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import re
import sys

import numpy as np

# SMPL-X joint indices (left, right) of the joints rehabtwin lifts from depth
JOINTS = {"Hip": (1, 2), "Knee": (4, 5), "Ankle": (7, 8), "Shoulder": (16, 17), "Elbow": (18, 19), "Wrist": (20, 21)}
FRONT = np.array([0.0, 0.0, 1.0])          # SMPL-X bodies face +z (y up)
DENSITY = 1000.0                           # kg/m^3: mass from volume is an estimate (body density ~985-1100)


def load_smplx(path):
    """The numeric arrays of an SMPL-X model .npz (object entries skipped, never unpickled)."""
    m = np.load(path, allow_pickle=False)
    out = {}
    for k in m.files:
        try:
            out[k] = m[k]
        except ValueError:          # pickled dicts (part2num, joint2num): not needed, not trusted
            continue
    return out


def rest_body(model, betas):
    """(vertices (V,3), joints (55,3)) of a body in the model's rest pose, metres."""
    b = np.asarray(betas, float)
    v = model["v_template"] + model["shapedirs"][:, :, :len(b)] @ b
    return v, model["J_regressor"] @ v


def body_stats(v, faces, density=DENSITY):
    """(height m, estimated mass kg, estimated BMI) of a closed mesh standing along +y."""
    h = float(v[:, 1].max() - v[:, 1].min())
    a, b, c = v[faces[:, 0]], v[faces[:, 1]], v[faces[:, 2]]
    vol = abs(float(np.einsum("ij,ij->i", a, np.cross(b, c)).sum())) / 6.0
    return h, vol * density, vol * density / h ** 2


def first_hit(orig, direction, v, faces):
    """Distance along the unit ray from ``orig`` to the first triangle it crosses (Moller-Trumbore), inf if none."""
    a, b, c = v[faces[:, 0]], v[faces[:, 1]], v[faces[:, 2]]
    e1, e2 = b - a, c - a
    p = np.cross(direction, e2)
    det = (e1 * p).sum(1)
    ok = np.abs(det) > 1e-12
    inv = np.where(ok, 1.0 / np.where(ok, det, 1.0), 0.0)
    s = orig - a
    u = (s * p).sum(1) * inv
    q = np.cross(s, e1)
    w = (q @ direction) * inv
    t = (e2 * q).sum(1) * inv
    hit = ok & (u >= 0) & (w >= 0) & (u + w <= 1) & (t > 1e-6)
    return float(t[hit].min()) if hit.any() else np.inf


def rodrigues(r):
    """Rotation matrices (..., 3, 3) of axis-angle vectors (..., 3)."""
    r = np.asarray(r, float)
    th = np.linalg.norm(r, axis=-1, keepdims=True)
    k = r / np.maximum(th, 1e-12)
    K = np.zeros(r.shape[:-1] + (3, 3))
    K[..., 0, 1], K[..., 0, 2], K[..., 1, 0] = -k[..., 2], k[..., 1], k[..., 2]
    K[..., 1, 2], K[..., 2, 0], K[..., 2, 1] = -k[..., 0], -k[..., 1], k[..., 0]
    s, c = np.sin(th)[..., None], np.cos(th)[..., None]
    return np.eye(3) + s * K + (1 - c) * K @ K


def pose_body(model, betas, pose, trans):
    """(vertices (V,3), joints (55,3)) of an SMPL-X body in one frame of an AMASS-format motion (y up, metres).

    Linear blend skinning with pose correctives. ``pose``: 165 axis-angle values (55 joints) as stored, i.e.
    hand poses taken as absolute (no hand mean added).
    """
    b = np.asarray(betas, float)
    vs = model["v_template"] + model["shapedirs"][:, :, :len(b)] @ b
    J = model["J_regressor"] @ vs
    R = rodrigues(np.asarray(pose, float).reshape(-1, 3))
    vp = vs + model["posedirs"] @ (R[1:] - np.eye(3)).reshape(-1)
    parent = model["kintree_table"][0].astype(np.int64)
    G = np.zeros((len(J), 4, 4))
    for i in range(len(J)):
        L = np.eye(4)
        L[:3, :3], L[:3, 3] = R[i], J[i] - (J[parent[i]] if i else 0.0)
        G[i] = L if i == 0 else G[parent[i]] @ L
    A = G.copy()
    A[:, :3, 3] -= np.einsum("nij,nj->ni", G[:, :3, :3], J)
    T = np.einsum("vn,nij->vij", model["weights"], A)
    v = np.einsum("vij,vj->vi", T[:, :3, :3], vp) + T[:, :3, 3] + trans
    return v, G[:, :3, 3] + trans


def knee_flexion_deg(J):
    """Mean left/right knee flexion (0 = straight) from SMPL-X joint positions."""
    out = []
    for hip, knee, ankle in ((1, 4, 7), (2, 5, 8)):
        u, w = J[hip] - J[knee], J[ankle] - J[knee]
        out.append(180.0 - np.degrees(np.arccos(np.clip(u @ w / np.linalg.norm(u) / np.linalg.norm(w), -1, 1))))
    return float(np.mean(out))


def facing(J):
    """Horizontal unit vector the body faces (y up): left hip minus right hip, crossed with up."""
    f = np.cross(J[1] - J[2], [0.0, 1.0, 0.0])
    f[1] = 0.0
    return f / np.linalg.norm(f)


def camera(position, target):
    """(centre, R world->OpenCV camera) for a camera at ``position`` looking at ``target`` (y up, no roll)."""
    z = np.asarray(target, float) - position
    z /= np.linalg.norm(z)
    x = np.cross([0.0, -1.0, 0.0], z)
    x /= np.linalg.norm(x)
    y = np.cross(z, x)
    return np.asarray(position, float), np.stack([x, y, z])


def first_hit_culled(C, R, K, v, faces, target):
    """``first_hit`` from camera centre C towards ``target``, testing only triangles whose image bounding box
    contains the target's pixel (K = fx, fy, cx, cy). Returns (distance to the target, distance to the hit)."""
    fx, fy, cx, cy = K
    pc = (v - C) @ R.T
    uv = np.stack([fx * pc[:, 0] / pc[:, 2] + cx, fy * pc[:, 1] / pc[:, 2] + cy], 1)
    tp = (target - C) @ R.T
    tu, tv = fx * tp[0] / tp[2] + cx, fy * tp[1] / tp[2] + cy
    fu, fv = uv[faces, 0], uv[faces, 1]
    cand = (fu.min(1) <= tu) & (fu.max(1) >= tu) & (fv.min(1) <= tv) & (fv.max(1) >= tv) & (pc[faces, 2].min(1) > 0)
    d = target - C
    dist = float(np.linalg.norm(d))
    return dist, first_hit(C, d / dist, v, faces[cand]) if cand.any() else np.inf


def body_ids(motion_dir):
    """{body id: one motion file} (motions are named <body id>_<motion id>.npz)."""
    out = {}
    for p in sorted(glob.glob(os.path.join(motion_dir, "*.npz"))):
        out.setdefault(os.path.basename(p).rsplit("_", 1)[0], p)
    return out


def measure_offsets(model, motion_dir):
    """Per body: height, BMI and the front skin-to-joint-centre distance of each JOINTS entry (mean of L/R)."""
    faces = model["f"].astype(int)
    rows = []
    for body, path in body_ids(motion_dir).items():
        v, J = rest_body(model, np.load(path, allow_pickle=False)["betas"])
        h, mass, bmi = body_stats(v, faces)
        rows.append({"body": body, "height_m": h, "mass_kg": mass, "bmi": bmi,
                     **{n: float(np.mean([first_hit(J[i], FRONT, v, faces) for i in lr])) for n, lr in JOINTS.items()}})
    return rows


def fit(rows, bmi_ref=25.0):
    """Per joint: offset = height * (a + b * (BMI - bmi_ref)), least squares, and the residual SD (m)."""
    H = np.array([r["height_m"] for r in rows])
    B = np.array([r["bmi"] for r in rows]) - bmi_ref
    out = {}
    for n in JOINTS:
        y = np.array([r[n] for r in rows])
        A = np.stack([H, H * B], axis=1)
        (a, b), *_ = np.linalg.lstsq(A, y, rcond=None)
        out[n] = {"a": round(float(a), 4), "b": round(float(b), 5), "residual_sd_m": round(float((y - A @ [a, b]).std()), 4),
                  "worst_m": round(float(np.abs(y - A @ [a, b]).max()), 4)}
    return out


# keypoints the Kinect path lifts from depth: rehabtwin.kinect name -> SMPL-X joint
LIFTED = {"LHip": 1, "RHip": 2, "LKnee": 4, "RKnee": 5, "LAnkle": 7, "RAnkle": 8, "LShoulder": 16, "RShoulder": 17,
          "LElbow": 18, "RElbow": 19, "LWrist": 20, "RWrist": 21}
KINECT_K = (531.15, 531.15, 320.0, 240.0)
SETUPS = {"level 1.0 m": (1.0, False), "high 1.6 m, aimed at pelvis": (1.6, True)}


def visibility(model, motion_dir, mapping_csv, pattern="squat", distance_m=2.7, step=3, max_sequences=None,
               px_noise=3.0, pose_noise_m=0.03, caught_m=0.20, seed=0):
    """Per frame and keypoint of the matching motions: what a front-facing depth sensor would lift, before and
    after rehabtwin.kinect's segment-length check.

    The sensor stands ``distance_m`` in front of the body's mean facing direction. For each keypoint it takes
    the first surface on the line of sight and adds ``rehabtwin.kinect.surface_to_centre`` (this body's height
    and BMI). ``error_m`` is that point's signed error along the line of sight. Below zero means in front of
    the joint, i.e. the line of sight hit another body part first. Errors over ``caught_m`` count as dropped
    by the pose check. Then ``segment_lengths`` / ``constrain_segments`` run as in ``rgbd_sequence``, with
    MediaPipe-like noise: ``px_noise`` on the 2D keypoint, ``pose_noise_m`` per axis on its 3D pose.
    ``error_after_m`` is the distance to the joint afterwards (None: still empty).
    """
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))     # pipeline/ -> rehabtwin
    from rehabtwin.kinect import constrain_segments, segment_lengths, surface_to_centre
    faces = model["f"].astype(int)
    names = list(LIFTED)
    with open(mapping_csv) as fh:
        seqs = [r for r in csv.DictReader(fh) if re.search(pattern, r["motion_rel_fname"], re.IGNORECASE)]
    rng = np.random.default_rng(seed)
    fx, fy, cx, cy = KINECT_K
    out = []
    for r in seqs[:max_sequences]:
        path = os.path.join(motion_dir, f"{r['body_id']}_{r['motion_id']}.npz")
        if not os.path.exists(path):
            continue
        d = np.load(path, allow_pickle=False)
        betas, poses, trans = d["betas"].astype(float), d["poses"], d["trans"]
        v_rest, _ = rest_body(model, betas)
        h, _, bmi = body_stats(v_rest, faces)
        offsets = np.array([surface_to_centre(n, h, bmi) for n in names])
        frames = list(range(0, len(poses), step))
        posed = [pose_body(model, betas, poses[i], trans[i]) for i in frames]
        f = np.mean([facing(J) for _, J in posed], axis=0)
        f /= np.linalg.norm(f)
        pelvis = np.mean([J[0] for _, J in posed], axis=0)
        for setup, (cam_h, aim) in SETUPS.items():
            pos = np.array([pelvis[0], cam_h, pelvis[2]]) + distance_m * f
            C, R = camera(pos, np.array([pelvis[0], pelvis[1] if aim else cam_h, pelvis[2]]))
            F, n = len(frames), len(names)
            Jc = np.zeros((F, n, 3))
            P = np.full((F, n, 3), np.nan)
            err = np.full((F, n), np.nan)
            flex = np.zeros(F)
            for k, (v, J) in enumerate(posed):
                flex[k] = knee_flexion_deg(J)
                for q, name in enumerate(names):
                    Jc[k, q] = R @ (J[LIFTED[name]] - C)
                    dist, hit = first_hit_culled(C, R, KINECT_K, v, faces, J[LIFTED[name]])
                    err[k, q] = hit + offsets[q] - dist
                    P[k, q] = Jc[k, q] / dist * (hit + offsets[q])
            source = np.where(np.abs(err) <= caught_m, 1, 2)
            P[source == 2] = np.nan
            uv = np.stack([fx * Jc[..., 0] / Jc[..., 2] + cx, fy * Jc[..., 1] / Jc[..., 2] + cy], -1)
            uv = uv + rng.normal(0, px_noise, uv.shape)
            world = Jc + rng.normal(0, pose_noise_m, Jc.shape)
            lengths = segment_lengths(P, source, names)
            constrain_segments(P, source, uv, np.ones((F, n)), world, KINECT_K, lengths, names)
            after = np.linalg.norm(P - Jc, axis=2)
            for k, fi in enumerate(frames):
                for q, name in enumerate(names):
                    out.append({"body": r["body_id"], "motion": r["motion_rel_fname"], "frame": fi, "setup": setup,
                                "bmi": bmi, "knee_flexion_deg": float(flex[k]), "keypoint": name,
                                "error_m": float(err[k, q]), "placed": bool(source[k, q] == 4),
                                "error_after_m": None if np.isnan(after[k, q]) else float(after[k, q])})
    return out


DEPTH_BINS = (("standing (<30 deg knee)", 0, 30), ("mid (30-70)", 30, 70), ("deep (>70)", 70, 999))
BMI_BINS = (("BMI<25", 0, 25), ("25-30", 25, 30), (">30", 30, 99))


def summarise_visibility(rows, good_m=0.03, caught_m=0.20, key="error_m"):
    """Share of keypoint-frames within ``good_m``, wrong by up to ``caught_m`` (what the Kinect path's 0.2 m
    pose check cannot catch), or worse / empty, per setup, joint and squat depth. ``key``: ``error_m`` (depth
    alone) or ``error_after_m`` (after the segment-length check)."""
    out = {}
    for r in rows:
        joint = r["keypoint"][1:]
        for dname, lo, hi in DEPTH_BINS:
            if lo <= r["knee_flexion_deg"] < hi:
                for bname, blo, bhi in BMI_BINS + (("all", 0, 99),):
                    if blo <= r["bmi"] < bhi:
                        cell = out.setdefault(r["setup"], {}).setdefault(joint, {}).setdefault(dname, {}).setdefault(
                            bname, {"n": 0, "good": 0, "silent": 0, "caught": 0})
                        e = r.get(key)
                        e = np.inf if e is None else abs(e)
                        cell["n"] += 1
                        cell["good" if e <= good_m else "silent" if e <= caught_m else "caught"] += 1
    return out


def _rehabtwin():
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))     # pipeline/ -> rehabtwin


def synth_frame(model, betas, pose, trans, rng, distance_m=2.7, sensor_height_m=1.0, yaw_deg=0.0, px_noise=3.0,
                noise=None, floor_clear_m=0.02, focal_scale=1.0):
    """One depth frame of a posed body as a front-facing Kinect v1 would see it (floor at y = 0 or below).

    The sensor stands ``distance_m`` in front of the pelvis along the body's facing direction (turned by
    ``yaw_deg`` about the vertical), level at ``sensor_height_m``. Depth is the first surface per pixel
    (``shape.render_depth``) with the sensor's noise (``shape.kinect_v1_noise``, keyword arguments ``noise``).
    The person's pixels are known (as the SDK's player index would give them), minus those within
    ``floor_clear_m`` of the floor. 2D keypoints are the projected SMPL-X joints plus ``px_noise`` px.
    ``focal_scale``: the true focal length over the nominal one that back-projects the points."""
    _rehabtwin()
    from rehabtwin import shape
    v, J = pose_body(model, betas, pose, trans)
    f = facing(J)
    a = np.radians(yaw_deg)
    f = np.array([np.cos(a) * f[0] + np.sin(a) * f[2], 0.0, -np.sin(a) * f[0] + np.cos(a) * f[2]])
    eye = np.array([J[0, 0], sensor_height_m, J[0, 2]])
    C, R = camera(eye + distance_m * f, eye)
    vc, Jc = (v - C) @ R.T, (J - C) @ R.T
    fx, fy, cx, cy = KINECT_K
    K_true = (fx * focal_scale, fy * focal_scale, cx, cy)
    depth, _ = shape.render_depth(vc, model["f"].astype(np.int64), K_true)
    mm = shape.kinect_v1_noise(depth, rng, **(noise or {}))
    floor_y = min(0.0, float(v[:, 1].min()))                   # y = 0, or lower where a foot sinks below it
    up, offset = R @ np.array([0.0, 1.0, 0.0]), floor_y - C[1]  # up . p = offset (camera coordinates)
    pts = shape.depth_points(mm, KINECT_K)
    pts = pts[pts @ up - offset > floor_clear_m]
    jj = list(shape.KEYPOINTS.values())
    kp = np.stack([K_true[0] * Jc[jj, 0] / Jc[jj, 2] + cx, K_true[1] * Jc[jj, 1] / Jc[jj, 2] + cy], 1)
    return {"points": pts, "keypoints_uv": kp + rng.normal(0, px_noise, kp.shape) if px_noise else kp,
            "floor": (up, offset), "joints_cam": Jc, "depth_mm": mm, "camera": (C, R)}


SIZES = ("XS", "S", "M", "L", "XL", "2XL", "3XL", "4XL", "5XL")
FIT_BMI_BINS = (("BMI < 20", 0, 20), ("20-25", 20, 25), ("25-30", 25, 30), ("30-35", 30, 35), ("> 35", 35, 99))
PREFERRED = (re.compile(r"stand|a_?pose|t_?pose|idle", re.IGNORECASE), re.compile(r"walk", re.IGNORECASE))
# condition -> (synth_frame keyword arguments, fit options, frames). Conditions with the same synthesis
# and frames see the same noisy data, so their differences are paired.
SHAPE_CONDITIONS = {
    "main": ({}, {}, "A"),
    "measured height": ({}, {"height": True}, "A"),
    "no keypoints": ({}, {"keypoints": False}, "A"),
    "noise-free": ({"noise": {"sd_coeff": 0.0, "edge_drop": 0.0}, "px_noise": 0.0}, {}, "A"),
    "depth noise x2": ({"noise": {"sd_coeff": 3.0e-3}}, {}, "A"),
    "disparity steps + correlated noise": ({"noise": {"disparity_step_px": 0.125, "corr_px": 3.0}}, {}, "A"),
    "keypoints 8 px": ({"px_noise": 8.0}, {}, "A"),
    "turned 30 deg": ({"yaw_deg": 30.0}, {}, "A"),
    "focal length +2%": ({"focal_scale": 1.02}, {}, "A"),
    "second frame": ({}, {}, "B"),
    "two frames": ({}, {}, "AB"),
}


def standing_frames(bm, model, betas, motions, n=2, max_knee_deg=20.0, step=15):
    """Up to ``n`` near-standing frames of one body, each from another motion: [(path, frame, knee flexion,
    source motion)]. Knee flexion under ``max_knee_deg`` on average, lowest vertex within 2-3 cm of the floor.
    ``motions``: [(path, source name)], standing motions tried first, then walking, then the rest."""
    _rehabtwin()
    from rehabtwin import shape
    rank = [next((k for k, rx in enumerate(PREFERRED) if rx.search(name)), len(PREFERRED)) for _, name in motions]
    out = []
    for _, (path, name) in sorted(zip(rank, motions), key=lambda t: t[0]):
        d = np.load(path, allow_pickle=False)
        idx = np.arange(0, len(d["poses"]), step)
        R = shape.rodrigues(d["poses"][idx].reshape(len(idx), -1, 3))
        _, J = bm.posed(np.repeat(betas[None], len(idx), 0), R, d["trans"][idx], idx=np.zeros(0, np.int64),
                        offsets=np.zeros((0, 3)))
        for k, fi in enumerate(idx):
            flex = knee_flexion_deg(J[k])
            if flex < max_knee_deg:
                v, _ = pose_body(model, betas, d["poses"][fi], d["trans"][fi])
                if -0.02 < v[:, 1].min() < 0.03:
                    out.append((path, int(fi), flex, name))
                    break
        if len(out) == n:
            break
    return out


# The bodies looked at while developing rehabtwin.shape (one per size label, and the XS body whose
# arms-across-the-body frame broke an early version). The test split leaves them out.
DEVELOPMENT_BODIES = ("it_4324_XS", "nl_5562_XS", "it_4592_S", "nl_6228_M", "us_2526_L", "us_1253_XL", "us_2116_2XL",
                      "us_1459_3XL", "nl_6537_4XL", "nl_1079_5XL")


def pick_bodies(bm, model, motion_dir, mapping_csv, per_size=5, split="test", seed=0):
    """Bodies stratified by size label, each with near-standing frames. 'test': the first ``per_size`` per
    label of a seeded shuffle, DEVELOPMENT_BODIES left out. 'dev': DEVELOPMENT_BODIES."""
    with open(mapping_csv) as fh:
        rows = list(csv.DictReader(fh))
    motions = {}
    for r in rows:
        p = os.path.join(motion_dir, f"{r['body_id']}_{r['motion_id']}.npz")
        if os.path.exists(p):
            motions.setdefault(r["body_id"], []).append((p, r["motion_rel_fname"]))
    rng = np.random.default_rng(seed)
    out = []
    for size in SIZES:
        cand = rng.permutation(sorted(b for b in motions if b.rsplit("_", 1)[-1] == size))
        found = []
        for body in cand:
            if (body in DEVELOPMENT_BODIES) != (split == "dev"):
                continue
            betas = np.load(motions[body][0][0], allow_pickle=False)["betas"][:16].astype(float)
            frames = standing_frames(bm, model, betas, motions[body])
            if frames:
                found.append({"body": str(body), "size": size, "betas": betas, "frames": frames})
            if len(found) == per_size:
                break
        out += found
    return out


def segment_baseline(model, motion_dir, exclude):
    """Per segment, length = c0 + c1 height + c2 BMI (least squares) over all size-labelled bodies but
    ``exclude``: what height and mass alone predict. Returns {segment: (c0, c1, c2)}."""
    _rehabtwin()
    from rehabtwin import shape
    faces = model["f"].astype(np.int64)
    X, Y = [], {s: [] for s in shape.SEGMENTS}
    for body, path in body_ids(motion_dir).items():
        if body in exclude or body.rsplit("_", 1)[-1] not in SIZES:
            continue
        v, J = rest_body(model, np.load(path, allow_pickle=False)["betas"][:16])
        h, _, _, bmi = shape.body_measures(v, faces)
        X.append([1.0, h, bmi])
        for s, lr in shape.segment_lengths(J).items():
            Y[s].append(np.mean(lr))
    X = np.array(X)
    return {s: tuple(np.linalg.lstsq(X, np.array(y), rcond=None)[0].tolist()) for s, y in Y.items()}


_W = {}


def _shape_worker_init(model_path):
    _rehabtwin()
    from rehabtwin import shape
    _W["model"] = load_smplx(model_path)
    _W["bm"] = shape.BodyModel(_W["model"])


def _seed(*parts):
    import zlib
    return zlib.crc32("|".join(map(str, parts)).encode())


def _sides(d):
    """{"Hip": mean of LHip and RHip, ...}"""
    return {g: float(np.mean([d[f"L{g}"], d[f"R{g}"]])) for g in JOINTS}


def shapefit_body(item, conditions=None):
    """All conditions of one body (``pick_bodies`` entry): per condition the fitted and true height, mass,
    BMI, segment lengths, skin-to-joint offsets (and the height+BMI baseline's), joint errors, runtime."""
    _rehabtwin()
    from rehabtwin import shape
    from rehabtwin.kinect import back_project, sample_depth, surface_to_centre
    model, bm = _W["model"], _W["bm"]
    betas = item["betas"]
    vt, Jt = bm.rest(betas)
    h, _, mass, bmi = shape.body_measures(vt, bm.faces)
    true_off = shape.front_offsets(vt, Jt, bm.faces)
    true_seg = {s: float(np.mean(lr)) for s, lr in shape.segment_lengths(Jt).items()}
    picks = dict(zip("AB", item["frames"]))
    rows = []
    for cname, (synth_kw, opts, labels) in (conditions or SHAPE_CONDITIONS).items():
        if any(lab not in picks for lab in labels):
            continue
        obs = []
        for lab in labels:
            path, fi, _, _ = picks[lab]
            d = np.load(path, allow_pickle=False)
            rng = np.random.default_rng(_seed(item["body"], lab, json.dumps(synth_kw, sort_keys=True)))
            obs.append(synth_frame(model, betas, d["poses"][fi], d["trans"][fi], rng, **synth_kw))
        height = h + np.random.default_rng(_seed(item["body"], "height")).normal(0, 0.005) if opts.get("height") else None
        frames = [{"points": o["points"], "floor": o["floor"],
                   "keypoints_uv": o["keypoints_uv"] if opts.get("keypoints", True) else None} for o in obs]
        try:
            res = shape.fit_shape(bm, frames, KINECT_K, height_m=height)
        except (ValueError, IndexError, np.linalg.LinAlgError) as e:    # a failed fit is a result too
            rows.append({"body": item["body"], "size": item["size"], "condition": cname, "bmi_true": bmi,
                         "error": f"{type(e).__name__}: {e}"})
            continue
        J = np.array(res["frames"][0]["joints"])
        jerr, lift = {}, {}
        for n, j in shape.KEYPOINTS.items():
            jerr[n] = float(np.linalg.norm(J[j] - obs[0]["joints_cam"][j]))
            u, v = obs[0]["keypoints_uv"][list(shape.KEYPOINTS).index(n)]
            z = sample_depth(obs[0]["depth_mm"], u, v)
            if np.isfinite(z):                     # the Kinect path: first surface + offset from true height, BMI
                s = back_project(u, v, z, *KINECT_K)
                lift[n] = float(np.linalg.norm(s * (1 + surface_to_centre(n, h, bmi) / np.linalg.norm(s))
                                               - obs[0]["joints_cam"][j]))
        rows.append({"body": item["body"], "size": item["size"], "condition": cname,
                     "frames": [{"motion": picks[lab][3], "frame": picks[lab][1],
                                 "knee_flexion_deg": round(picks[lab][2], 1)} for lab in labels],
                     "height_true_m": h, "mass_true_kg": mass, "bmi_true": bmi, "height_given_m": height,
                     "height_fit_m": res["height_m"], "mass_fit_kg": res["mass_kg"], "bmi_fit": res["bmi"],
                     "betas_true": betas.tolist(), "betas_fit": res["betas"],
                     "segments_true_m": true_seg,
                     "segments_fit_m": {s: float(np.mean(lr)) for s, lr in res["segment_lengths_m"].items()},
                     "offsets_true_m": _sides(true_off), "offsets_fit_m": _sides(res["surface_to_centre_m"]),
                     "offsets_baseline_m": _sides({n: surface_to_centre(n, h, bmi) for n in shape.KEYPOINTS}),
                     "joint_error_m": jerr, "lift_error_m": lift, "runtime_s": res["fit"]["runtime_s"],
                     "warnings": res["fit"]["warnings"],
                     "outer_iterations": res["fit"]["outer_iterations"],
                     "residuals": [f["residuals"] for f in res["frames"]]})
    return rows


def summarise_shapefit(rows, seg_coef):
    """Per condition and BMI group (and 'all'): mean (bias), SD and mean absolute error of each quantity, and
    the height+mass baselines (segment lengths from ``seg_coef``, offsets from ``surface_to_centre``)."""
    def stats(x):
        x = np.asarray(x, float)
        return {"n": len(x), "bias": float(x.mean()), "sd": float(x.std()), "mae": float(np.abs(x).mean()),
                "max_abs": float(np.abs(x).max())}
    out = {}
    for cond in dict.fromkeys(r["condition"] for r in rows):
        for gname, lo, hi in FIT_BMI_BINS + (("all", 0, 99),):
            g = [r for r in rows if r["condition"] == cond and lo <= r["bmi_true"] < hi]
            failed = [r["body"] for r in g if "error" in r]
            g = [r for r in g if "error" not in r]
            if not g:
                continue
            seg = {s: stats([100 * (r["segments_fit_m"][s] - r["segments_true_m"][s]) for r in g]) for s in seg_coef}
            seg_base = {s: stats([100 * (c[0] + c[1] * r["height_true_m"] + c[2] * r["bmi_true"] - r["segments_true_m"][s])
                                  for r in g]) for s, c in seg_coef.items()}
            off = {j: stats([100 * (r["offsets_fit_m"][j] - r["offsets_true_m"][j]) for r in g]) for j in JOINTS}
            off_base = {j: stats([100 * (r["offsets_baseline_m"][j] - r["offsets_true_m"][j]) for r in g]) for j in JOINTS}
            out.setdefault(cond, {})[gname] = {
                "bodies": len(g), "failed": failed, "flagged": [r["body"] for r in g if r["warnings"]], "bmi_range": [round(min(r["bmi_true"] for r in g), 1), round(max(r["bmi_true"] for r in g), 1)],
                "height_cm": stats([100 * (r["height_fit_m"] - r["height_true_m"]) for r in g]),
                "mass_pct": stats([100 * (r["mass_fit_kg"] / r["mass_true_kg"] - 1) for r in g]),
                "bmi": stats([r["bmi_fit"] - r["bmi_true"] for r in g]),
                "segment_cm": seg, "segment_baseline_cm": seg_base,
                "segment_mae_cm": float(np.mean([v["mae"] for v in seg.values()])),
                "segment_baseline_mae_cm": float(np.mean([v["mae"] for v in seg_base.values()])),
                "offset_cm": off, "offset_baseline_cm": off_base,
                "offset_mae_cm": float(np.mean([v["mae"] for v in off.values()])),
                "offset_baseline_mae_cm": float(np.mean([v["mae"] for v in off_base.values()])),
                "joint_error_cm_median": float(100 * np.median([np.mean(list(r["joint_error_m"].values())) for r in g])),
                "lift_error_cm_median": float(100 * np.median([np.mean(list(r["lift_error_m"].values())) for r in g])),
                "runtime_s_median": float(np.median([r["runtime_s"] for r in g])),
                "runtime_s_max": float(np.max([r["runtime_s"] for r in g]))}
    return out


def print_shapefit(summary):
    for cond, groups in summary.items():
        print(f"\n{cond}")
        print(f"  {'group':9s} {'n':>2s} {'height cm':>12s} {'mass %':>12s} {'BMI':>11s} {'seg MAE cm':>14s} "
              f"{'offset MAE cm':>14s} {'joints cm':>11s} {'s':>4s}")
        for g, s in groups.items():
            print(f"  {g:9s} {s['bodies']:2d} {s['height_cm']['bias']:+5.1f} ± {s['height_cm']['sd']:4.1f} "
                  f"{s['mass_pct']['bias']:+5.1f} ± {s['mass_pct']['sd']:4.1f} {s['bmi']['bias']:+4.1f} ± {s['bmi']['sd']:4.1f} "
                  f"{s['segment_mae_cm']:5.2f} ({s['segment_baseline_mae_cm']:4.2f}) "
                  f"{s['offset_mae_cm']:5.2f} ({s['offset_baseline_mae_cm']:4.2f}) "
                  f"{s['joint_error_cm_median']:4.1f} ({s['lift_error_cm_median']:3.1f}) {s['runtime_s_median']:4.0f}")


def shapefit(model_path, motion_dir, mapping_csv, per_size=5, split="test", jobs=1, conditions=None, seed=0,
             partial=None):
    """Validation of ``rehabtwin.shape.fit_shape`` on BEDLAM2 bodies: rows, summary and settings. Each body's
    rows are appended to ``partial`` (JSON lines) as they come; bodies already there are not fitted again."""
    _rehabtwin()
    from rehabtwin import shape
    model = load_smplx(model_path)
    bm = shape.BodyModel(model)
    items = pick_bodies(bm, model, motion_dir, mapping_csv, per_size, split, seed)
    seg_coef = segment_baseline(model, motion_dir, exclude={it["body"] for it in items} | set(DEVELOPMENT_BODIES))
    conds = {c: SHAPE_CONDITIONS[c] for c in conditions} if conditions else SHAPE_CONDITIONS
    rows = []
    if partial and os.path.exists(partial):
        with open(partial) as fh:
            rows = [json.loads(line) for line in fh if line.strip()]
        rows = [r for r in rows if r["body"] in {it["body"] for it in items} and r["condition"] in conds]
    done = {r["body"] for r in rows}
    items = [it for it in items if it["body"] not in done]
    print(f"{len(items)} bodies to fit ({split}, {len(done)} done before), {len(conds)} conditions, {jobs} jobs",
          flush=True)

    def keep(rs):
        rows.extend(rs)
        if partial:
            with open(partial, "a") as fh:
                fh.writelines(json.dumps(r) + "\n" for r in rs)
    if jobs > 1:
        import functools
        import multiprocessing as mp
        for var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
            os.environ.setdefault(var, "1")          # one BLAS thread per worker; read by the spawned workers
        with mp.get_context("spawn").Pool(jobs, _shape_worker_init, (model_path,)) as pool:
            for k, rs in enumerate(pool.imap_unordered(functools.partial(shapefit_body, conditions=conds), items)):
                keep(rs)
                print(f"  {k + 1}/{len(items)} {rs[0]['body'] if rs else ''}", flush=True)
    else:
        _W["model"], _W["bm"] = model, bm
        for k, it in enumerate(items):
            keep(shapefit_body(it, conds))
            print(f"  {k + 1}/{len(items)} {it['body']}", flush=True)
    settings = {"split": split, "per_size": per_size, "seed": seed, "sensor": "2.7 m in front, level at 1.0 m",
                "intrinsics": KINECT_K, "conditions": {c: [v[0], v[1], v[2]] for c, v in conds.items()},
                "segment_baseline": {"model": "c0 + c1 height + c2 BMI", "coef": seg_coef,
                                     "fitted_on": "size-labelled BEDLAM2 bodies outside this split and "
                                                  "DEVELOPMENT_BODIES"},
                "offset_baseline": "rehabtwin.kinect.surface_to_centre(true height, true BMI)"}
    return {"rows": rows, "summary": summarise_shapefit(rows, seg_coef), "settings": settings}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    of = sub.add_parser("offsets", help="skin-to-joint-centre distances over all bodies, fitted to height and BMI")
    of.add_argument("--model", required=True, help="SMPLX_NEUTRAL.npz of the locked-head (removed head bun) model")
    of.add_argument("--motions", required=True, help="motions_npz_training/ from b2_motions_npz_training.tar")
    of.add_argument("--out", required=True)
    vi = sub.add_parser("visibility", help="what a front-facing depth sensor lifts, frame by frame, on matching motions")
    vi.add_argument("--model", required=True)
    vi.add_argument("--motions", required=True)
    vi.add_argument("--mapping", required=True, help="b2_bedlam2amass_motion_training.csv")
    vi.add_argument("--pattern", default="squat", help="regex on the source motion file name")
    vi.add_argument("--step", type=int, default=3, help="every n-th frame (30 fps)")
    vi.add_argument("--out", required=True)
    sf = sub.add_parser("shapefit", help="body shape from one synthetic Kinect v1 depth frame, per BMI group")
    sf.add_argument("--model", required=True)
    sf.add_argument("--motions", required=True)
    sf.add_argument("--mapping", required=True, help="b2_bedlam2amass_motion_training.csv")
    sf.add_argument("--per-size", type=int, default=5, help="test bodies per size label XS..5XL")
    sf.add_argument("--split", choices=("test", "dev"), default="test", help="dev: the bodies used in development")
    sf.add_argument("--conditions", nargs="*", choices=list(SHAPE_CONDITIONS), help="default: all")
    sf.add_argument("--jobs", type=int, default=1)
    sf.add_argument("--out", required=True, help="JSON; rows also go to OUT.partial.jsonl as they come, and a "
                    "rerun skips the bodies already there")
    a = ap.parse_args(argv)
    if a.cmd == "shapefit":
        res = shapefit(a.model, a.motions, a.mapping, a.per_size, a.split, a.jobs, a.conditions,
                       partial=a.out + ".partial.jsonl")
        with open(a.out, "w") as fh:
            json.dump(res, fh)
        print_shapefit(res["summary"])
        print("columns: bias ± SD; segment and offset MAE: fit (height+mass baseline); joints: median of the "
              "per-body mean 3D error, fit (Kinect-path lift)")
        return
    if a.cmd == "visibility":
        rows = visibility(load_smplx(a.model), a.motions, a.mapping, a.pattern, step=a.step)
        with open(a.out, "w") as fh:
            json.dump({"rows": rows, "summary": summarise_visibility(rows),
                       "summary_after": summarise_visibility(rows, key="error_after_m")}, fh)
        print(f"{len(rows)} keypoint-frames from {len({(r['body'], r['motion']) for r in rows})} sequences -> {a.out}")
        return
    rows = measure_offsets(load_smplx(a.model), a.motions)
    res = {"bodies": len(rows), "fit": fit(rows), "per_body": rows,
           "method": "rest pose, rays from each SMPL-X joint along +z (front) to the first skin triangle; "
                     f"mass = volume x {DENSITY:g} kg/m^3"}
    with open(a.out, "w") as fh:
        json.dump(res, fh, indent=1)
    H = [r["height_m"] for r in rows]
    B = [r["bmi"] for r in rows]
    print(f"{len(rows)} bodies, height {min(H):.2f}-{max(H):.2f} m, est. BMI {min(B):.1f}-{max(B):.1f}")
    for n, c in res["fit"].items():
        print(f"{n:9s} a={c['a']:.4f} b={c['b']:+.5f}/BMI  residual SD {100 * c['residual_sd_m']:.2f} cm")


if __name__ == "__main__":
    main()
