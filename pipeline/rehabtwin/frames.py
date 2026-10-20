"""Coordinate frames: camera -> gravity-aligned world -> OpenSim ground.

Posture lives in the gravity frame, so the up-vector is the single most
important calibration of a monocular session. Two estimates are offered and
both are recorded in QC:

* ``camera-level`` — assume the camera is upright and level (tripod, no roll/pitch)
* ``floor``        — fit a plane to the foot markers' lowest positions

Neither uses the subject's trunk to define "up": that would erase exactly the
lean we want to measure.
"""
from __future__ import annotations

import numpy as np

# OpenCV camera (y down, z forward) -> y-up camera-level world
R_CV_TO_YUP = np.diag([1.0, -1.0, -1.0])


def _unit(v):
    n = np.linalg.norm(v)
    if n < 1e-12:
        raise ValueError("zero-length vector")
    return v / n


def rotation_between(a, b):
    """Smallest rotation matrix taking unit vector a to unit vector b."""
    a, b = _unit(np.asarray(a, float)), _unit(np.asarray(b, float))
    v = np.cross(a, b)
    c = float(np.dot(a, b))
    if c < -1 + 1e-9:  # opposite: rotate 180 deg about any perpendicular axis
        axis = _unit(np.cross(a, [1.0, 0, 0]) if abs(a[0]) < 0.9 else np.cross(a, [0, 1.0, 0]))
        return 2 * np.outer(axis, axis) - np.eye(3)
    vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + vx + vx @ vx / (1 + c)


def apply(R, pts, t=None):
    out = np.asarray(pts, float) @ np.asarray(R).T
    return out if t is None else out + t


def estimate_floor_up(markers, names, foot_names, approx_up, lowest_fraction=0.2):
    """Fit the floor plane to foot markers when they are lowest along ``approx_up``.

    Returns (up_unit_vector, rms_residual_m, n_points). The sign is chosen to
    agree with ``approx_up``.
    """
    idx = [names.index(n) for n in foot_names if n in names]
    if len(idx) < 3:
        raise ValueError("need at least 3 foot markers for a floor fit")
    approx_up = _unit(np.asarray(approx_up, float))
    pts = []
    for i in idx:
        traj = markers[:, i, :]
        traj = traj[np.isfinite(traj).all(axis=1)]
        if len(traj) == 0:
            continue
        h = traj @ approx_up
        k = max(1, int(len(traj) * lowest_fraction))
        pts.append(traj[np.argsort(h)[:k]])
    if not pts:
        raise ValueError("no finite foot samples")
    pts = np.concatenate(pts)
    if len(pts) < 3:
        raise ValueError("not enough foot samples for a floor fit")
    centred = pts - pts.mean(axis=0)
    _, s, vt = np.linalg.svd(centred, full_matrices=False)
    normal = vt[-1]
    if np.dot(normal, approx_up) < 0:
        normal = -normal
    # A degenerate (collinear) foot cloud gives a meaningless normal.
    if s[1] < 1e-6 or s[1] / max(s[0], 1e-12) < 0.05:
        raise ValueError("foot markers are nearly collinear; floor plane undetermined")
    rms = float(np.sqrt(np.mean((centred @ normal) ** 2)))
    return normal, rms, len(pts)


def angle_deg(a, b):
    a, b = _unit(np.asarray(a, float)), _unit(np.asarray(b, float))
    return float(np.degrees(np.arccos(np.clip(np.dot(a, b), -1, 1))))


def to_opensim_ground(markers, names, up, right_pairs, floor_names=None):
    """Rigid transform world -> OpenSim ground (x forward, y up, z right).

    ``right_pairs`` are (right_marker, left_marker) name pairs whose median
    difference defines the subject's rightward direction (e.g. hips). The
    heading is fixed once for the whole trial — turning during the trial is
    then visible as pelvis_rotation, as in marker-based mocap.
    Returns (R, t) such that ground = R @ p + t.
    """
    up = _unit(np.asarray(up, float))
    diffs = []
    for r, l in right_pairs:
        if r in names and l in names:
            d = markers[:, names.index(r)] - markers[:, names.index(l)]
            diffs.append(d[np.isfinite(d).all(axis=1)])
    if not diffs or sum(len(d) for d in diffs) == 0:
        raise ValueError("no right/left marker pairs available to define heading")
    right = np.median(np.concatenate(diffs), axis=0)
    right = right - np.dot(right, up) * up
    z = _unit(right)
    y = up
    x = np.cross(y, z)
    R = np.stack([x, y, z])  # rows are the new axes expressed in the old frame
    rotated = apply(R, markers)
    finite = rotated[np.isfinite(rotated).all(axis=2)]
    t = np.zeros(3)
    # Put the floor at y = 0 and the trial's start near the origin.
    if floor_names:
        fidx = [names.index(n) for n in floor_names if n in names]
        fy = rotated[:, fidx, 1]
        fy = fy[np.isfinite(fy)]
        if len(fy):
            t[1] = -np.percentile(fy, 2)
    elif len(finite):
        t[1] = -np.percentile(finite[:, 1], 1)
    first = rotated[np.isfinite(rotated).all(axis=(1, 2))]
    if len(first):
        c = first[0].mean(axis=0)
        t[0], t[2] = -c[0], -c[2]
    return R, t


def kabsch(src, dst, with_scale=False):
    """Best rigid (optionally similarity) transform with dst ~= s * R @ src + t.

    Only rows finite in both point sets are used. Returns (R, t, s, rms).
    """
    src, dst = np.asarray(src, float), np.asarray(dst, float)
    ok = np.isfinite(src).all(axis=1) & np.isfinite(dst).all(axis=1)
    if ok.sum() < 3:
        raise ValueError("kabsch needs >= 3 corresponding points")
    a, b = src[ok], dst[ok]
    ca, cb = a.mean(axis=0), b.mean(axis=0)
    A, B = a - ca, b - cb
    U, S, Vt = np.linalg.svd(A.T @ B)
    d = np.sign(np.linalg.det(Vt.T @ U.T))
    D = np.diag([1.0, 1.0, d])
    R = Vt.T @ D @ U.T
    s = float((S * np.diag(D)).sum() / (A ** 2).sum()) if with_scale else 1.0
    t = cb - s * R @ ca
    res = b - (s * a @ R.T + t)
    return R, t, s, float(np.sqrt((res ** 2).sum(axis=1).mean()))
