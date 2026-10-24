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
import glob
import json
import os

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


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    of = sub.add_parser("offsets", help="skin-to-joint-centre distances over all bodies, fitted to height and BMI")
    of.add_argument("--model", required=True, help="SMPLX_NEUTRAL.npz of the locked-head (removed head bun) model")
    of.add_argument("--motions", required=True, help="motions_npz_training/ from b2_motions_npz_training.tar")
    of.add_argument("--out", required=True)
    a = ap.parse_args(argv)
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
