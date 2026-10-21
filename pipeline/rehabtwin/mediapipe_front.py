"""MediaPipe Pose landmarks -> MarkerSequence (monocular or multi-view). numpy only.

Monocular: MediaPipe's world landmarks are metric but hip-centred (the global
position is dropped). The camera translation is recovered per frame by
linear least squares so that the 3D landmarks reproject onto the 2D
landmarks under a pinhole camera (rotation is identity because world
landmarks are camera-aligned). The focal length must be known or assumed;
the assumption is recorded.

Multi-view: 2D landmarks from calibrated, synchronised cameras are
triangulated (weighted DLT) — the classic markerless reference.
"""
from __future__ import annotations

import numpy as np

from .sequence import MarkerSequence

# Pose2Sim 'Mediapipe' marker names -> BlazePose landmark index
POSE2SIM_MEDIAPIPE = {
    "Nose": 0, "LEye": 2, "REye": 5, "LShoulder": 11, "RShoulder": 12, "LElbow": 13, "RElbow": 14,
    "LWrist": 15, "RWrist": 16, "LPinky": 17, "RPinky": 18, "LIndex": 19, "RIndex": 20, "LThumb": 21, "RThumb": 22,
    "LHip": 23, "RHip": 24, "LKnee": 25, "RKnee": 26, "LAnkle": 27, "RAnkle": 28,
    "LHeel": 29, "RHeel": 30, "LBigToe": 31, "RBigToe": 32,
}


def assumed_focal_px(w, h, diag_fov_deg=75.0):
    """Focal length for an uncalibrated phone/webcam: diagonal FOV assumption."""
    return float(np.hypot(w, h) / 2 / np.tan(np.radians(diag_fov_deg) / 2))


def solve_translation(X, uv, f, c, w=None):
    """Translation t minimising pinhole reprojection of (X + t) onto uv. X (N,3), uv (N,2)."""
    ok = np.isfinite(X).all(1) & np.isfinite(uv).all(1)
    if w is not None:
        ok &= w > 0
    if ok.sum() < 3:
        return np.full(3, np.nan)
    X, uv = X[ok], uv[ok]
    ww = np.ones(len(X)) if w is None else w[ok]
    du, dv = uv[:, 0] - c[0], uv[:, 1] - c[1]
    # f(X + tx) = du (Z + tz)  ->  f tx - du tz = du Z - f X   (same for y with dv)
    A = np.zeros((2 * len(X), 3))
    b = np.zeros(2 * len(X))
    A[0::2, 0], A[0::2, 2], b[0::2] = f, -du, du * X[:, 2] - f * X[:, 0]
    A[1::2, 1], A[1::2, 2], b[1::2] = f, -dv, dv * X[:, 2] - f * X[:, 1]
    sw = np.sqrt(np.repeat(ww, 2))
    t, *_ = np.linalg.lstsq(A * sw[:, None], b * sw, rcond=None)
    return t


def monocular_sequence(raw, focal_px=None, min_visibility=0.5, meta=None):
    """MarkerSequence (frame='opencv_camera') from one camera's raw MediaPipe dump."""
    w, h = (int(v) for v in raw["size"])
    f = focal_px or assumed_focal_px(w, h)
    c = (w / 2.0, h / 2.0)
    names = list(POSE2SIM_MEDIAPIPE)
    idx = [POSE2SIM_MEDIAPIPE[n] for n in names]
    world = np.asarray(raw["world"], float)[:, idx]
    uv = np.asarray(raw["image_xy"], float)[:, idx]
    vis = np.asarray(raw["visibility"], float)[:, idx]
    T = len(world)
    markers = np.full_like(world, np.nan)
    for k in range(T):
        wk = np.where(vis[k] >= min_visibility, vis[k], 0.0)
        t = solve_translation(world[k], uv[k], f, c, wk)
        markers[k] = world[k] + t
    low = vis < min_visibility
    markers[low] = np.nan
    valid = np.asarray(raw["detected"], bool) & np.isfinite(markers).all(axis=2).sum(axis=1).astype(bool)
    m = {"source": "MediaPipe Pose (monocular)", "intrinsics_source":
         f"{'calibrated' if focal_px else 'assumed (75 deg diagonal FOV)'} focal {f:.1f} px, principal point at image centre",
         "focal_px": f, "tier": "C", "default_config": "mediapipe33_pose2sim", "min_visibility": min_visibility}
    m.update(meta or {})
    return MarkerSequence(fps=float(raw["fps"]), frame="opencv_camera", marker_names=names, markers=markers,
                          valid=valid, meta=m)


# ------------------------------------------------------------- multi-view

class Camera:
    def __init__(self, name, K, dist, R, t, size):
        self.name, self.K, self.dist = name, np.asarray(K, float), np.asarray(dist, float)
        self.R, self.t, self.size = np.asarray(R, float), np.asarray(t, float), size

    @property
    def P(self):
        return self.K @ np.hstack([self.R, self.t[:, None]])

    def project(self, X):
        Xc = X @ self.R.T + self.t
        uv = Xc[..., :2] / Xc[..., 2:3]
        return uv * [self.K[0, 0], self.K[1, 1]] + [self.K[0, 2], self.K[1, 2]]

    def undistort(self, uv, iters=10):
        """Remove Brown radial/tangential distortion (k1, k2, p1, p2) from pixel points."""
        if not np.any(self.dist):
            return uv
        k1, k2, p1, p2 = self.dist[:4]
        fx, fy, cx, cy = self.K[0, 0], self.K[1, 1], self.K[0, 2], self.K[1, 2]
        xd = (uv[..., 0] - cx) / fx
        yd = (uv[..., 1] - cy) / fy
        x, y = xd.copy(), yd.copy()
        for _ in range(iters):
            r2 = x * x + y * y
            rad = 1 + k1 * r2 + k2 * r2 * r2
            dx = 2 * p1 * x * y + p2 * (r2 + 2 * x * x)
            dy = p1 * (r2 + 2 * y * y) + 2 * p2 * x * y
            x, y = (xd - dx) / rad, (yd - dy) / rad
        return np.stack([x * fx + cx, y * fy + cy], axis=-1)


def read_qca(path):
    """Qualisys .qca.txt calibration -> [Camera] (follows Pose2Sim calibration.calib_qca_fun)."""
    import xml.etree.ElementTree as ET
    root = ET.parse(path).getroot()
    cams = []
    for cam in root.findall("cameras/camera"):
        fov = cam.find("fov_video").attrib
        left, top = float(fov["left"]), float(fov["top"])
        size = (float(fov["right"]) - left + 1, float(fov["bottom"]) - top + 1)
        it = cam.find("intrinsic").attrib
        K = np.array([[float(it["focalLengthU"]) / 64, 0, float(it["centerPointU"]) / 64 - left],
                      [0, float(it["focalLengthV"]) / 64, float(it["centerPointV"]) / 64 - top], [0, 0, 1]])
        dist = np.array([float(it[k]) / 64 for k in ("radialDistortion1", "radialDistortion2",
                                                     "tangentalDistortion1", "tangentalDistortion2")])
        tr = cam.find("transform").attrib
        M = np.array([[float(tr[f"r{i}{j}"]) for j in (1, 2, 3)] for i in (1, 2, 3)])
        pos = np.array([float(tr[k]) for k in ("x", "y", "z")]) / 1000.0
        # Pose2Sim reads r11..r33 by column (M.T) and then transposes it for the
        # world->camera direction, so the net rotation is M; Qualisys cameras
        # also look along -z, hence the extra pi rotation about x.
        R = M
        t = -R @ pos
        Rx = np.diag([1.0, -1.0, -1.0])
        cams.append(Camera(cam.attrib.get("serial"), K, dist, Rx @ R, Rx @ t, size))
    return sorted(cams, key=lambda c: c.name)


def triangulate(cams, uv, weights, min_weight=0.5, min_views=2):
    """Weighted DLT. uv (C,T,N,2) pixels, weights (C,T,N). Returns (X (T,N,3), reproj_px (T,N), n_views (T,N))."""
    C, T, N, _ = uv.shape
    und = np.stack([cams[c].undistort(uv[c]) for c in range(C)])
    Ps = [c.P for c in cams]
    X = np.full((T, N, 3), np.nan)
    err = np.full((T, N), np.nan)
    nv = np.zeros((T, N), int)
    for t in range(T):
        for n in range(N):
            use = [c for c in range(C) if weights[c, t, n] >= min_weight and np.isfinite(und[c, t, n]).all()]
            nv[t, n] = len(use)
            if len(use) < min_views:
                continue
            rows = []
            for c in use:
                u, v = und[c, t, n]
                wgt = weights[c, t, n]
                rows.append(wgt * (u * Ps[c][2] - Ps[c][0]))
                rows.append(wgt * (v * Ps[c][2] - Ps[c][1]))
            _, _, vt = np.linalg.svd(np.asarray(rows))
            Xh = vt[-1]
            X[t, n] = Xh[:3] / Xh[3]
            err[t, n] = np.mean([np.linalg.norm(cams[c].project(X[t, n]) - und[c, t, n]) for c in use])
    return X, err, nv


def multiview_sequence(raws, cams, up_axis="z", min_visibility=0.5, max_reproj_px=25.0, meta=None):
    """MarkerSequence (frame='yup_world') from synchronised raw dumps + calibration."""
    names = list(POSE2SIM_MEDIAPIPE)
    idx = [POSE2SIM_MEDIAPIPE[n] for n in names]
    T = min(len(r["image_xy"]) for r in raws)
    uv = np.stack([np.asarray(r["image_xy"], float)[:T, idx] for r in raws])
    w = np.stack([np.asarray(r["visibility"], float)[:T, idx] for r in raws])
    X, err, nv = triangulate(cams, uv, w, min_weight=min_visibility)
    X[err > max_reproj_px] = np.nan
    if up_axis == "z":  # lab z-up -> y-up (x, y, z) -> (x, z, -y)
        X = X @ np.array([[1, 0, 0], [0, 0, 1], [0, -1, 0]]).T
    valid = np.isfinite(X).all(axis=2).sum(axis=1) >= 12
    m = {"source": f"MediaPipe Pose, {len(cams)}-camera DLT triangulation", "tier": "C",
         "default_config": "mediapipe33_pose2sim", "reprojection_px_median": float(np.nanmedian(err)),
         "reprojection_px_p95": float(np.nanpercentile(err, 95)), "intrinsics_source": "Qualisys calibration file",
         "cameras": [c.name for c in cams]}
    m.update(meta or {})
    return MarkerSequence(fps=float(raws[0]["fps"]), frame="yup_world", marker_names=names, markers=X,
                          valid=valid, meta=m), err
