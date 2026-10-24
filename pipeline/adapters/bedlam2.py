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


def visibility(model, motion_dir, mapping_csv, pattern="squat", distance_m=2.7, step=3, max_sequences=None):
    """Per frame and keypoint of the matching motions: what a front-facing depth sensor would lift.

    The sensor stands ``distance_m`` in front of the body's mean facing direction. For each keypoint it takes
    the first surface on the line of sight and adds ``rehabtwin.kinect.surface_to_centre`` (this body's height
    and BMI). ``error_m`` > 0: the lifted point lies behind the joint, < 0: in front of it. A large negative
    error means the line of sight hit another body part first.
    """
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))     # pipeline/ -> rehabtwin
    from rehabtwin.kinect import surface_to_centre
    faces = model["f"].astype(int)
    with open(mapping_csv) as fh:
        seqs = [r for r in csv.DictReader(fh) if re.search(pattern, r["motion_rel_fname"], re.IGNORECASE)]
    out = []
    for r in seqs[:max_sequences]:
        path = os.path.join(motion_dir, f"{r['body_id']}_{r['motion_id']}.npz")
        if not os.path.exists(path):
            continue
        d = np.load(path, allow_pickle=False)
        betas, poses, trans = d["betas"].astype(float), d["poses"], d["trans"]
        v_rest, _ = rest_body(model, betas)
        h, _, bmi = body_stats(v_rest, faces)
        frames = range(0, len(poses), step)
        posed = [pose_body(model, betas, poses[i], trans[i]) for i in frames]
        f = np.mean([facing(J) for _, J in posed], axis=0)
        f /= np.linalg.norm(f)
        pelvis = np.mean([J[0] for _, J in posed], axis=0)
        for setup, (cam_h, aim) in SETUPS.items():
            pos = np.array([pelvis[0], cam_h, pelvis[2]]) + distance_m * f
            C, R = camera(pos, np.array([pelvis[0], pelvis[1] if aim else cam_h, pelvis[2]]))
            for fi, (v, J) in zip(frames, posed):
                flex = knee_flexion_deg(J)
                for name, j in LIFTED.items():
                    dist, hit = first_hit_culled(C, R, KINECT_K, v, faces, J[j])
                    err = hit + surface_to_centre(name, h, bmi) - dist
                    out.append({"body": r["body_id"], "motion": r["motion_rel_fname"], "frame": fi, "setup": setup,
                                "bmi": bmi, "knee_flexion_deg": flex, "keypoint": name, "error_m": err})
    return out


DEPTH_BINS = (("standing (<30 deg knee)", 0, 30), ("mid (30-70)", 30, 70), ("deep (>70)", 70, 999))
BMI_BINS = (("BMI<25", 0, 25), ("25-30", 25, 30), (">30", 30, 99))


def summarise_visibility(rows, good_m=0.03, caught_m=0.20):
    """Share of keypoint-frames lifted within ``good_m``, wrong by up to ``caught_m`` (what the Kinect path's
    0.2 m consistency check cannot catch), or worse (left empty by that check), per setup, joint and squat depth."""
    out = {}
    for r in rows:
        joint = r["keypoint"][1:]
        for dname, lo, hi in DEPTH_BINS:
            if lo <= r["knee_flexion_deg"] < hi:
                for bname, blo, bhi in BMI_BINS + (("all", 0, 99),):
                    if blo <= r["bmi"] < bhi:
                        cell = out.setdefault(r["setup"], {}).setdefault(joint, {}).setdefault(dname, {}).setdefault(
                            bname, {"n": 0, "good": 0, "silent": 0, "caught": 0})
                        e = abs(r["error_m"])
                        cell["n"] += 1
                        cell["good" if e <= good_m else "silent" if e <= caught_m else "caught"] += 1
    return out


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
    a = ap.parse_args(argv)
    if a.cmd == "visibility":
        rows = visibility(load_smplx(a.model), a.motions, a.mapping, a.pattern, step=a.step)
        with open(a.out, "w") as fh:
            json.dump({"rows": rows, "summary": summarise_visibility(rows)}, fh)
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
