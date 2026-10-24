"""Body shape from a depth sensor (layer 3, surface shape; Tier B): an SMPL-X body fitted to depth points.

A front-facing depth sensor (Kinect v1) sees the front of the body. ``fit_shape`` fits an SMPL-X-format body
model to the person's depth points from one or a few frames. It fits the 16 shape parameters (betas, shared
by all frames) and, per frame, the global orientation, the 21 body joints and the translation. Hands, jaw
and eyes stay at zero. Each term is divided by its expected error:

- **Depth:** each depth point against the model's depth along the same line of sight, where the sensor's
  error lies (a point the model does not cover: to the nearest visible model surface). Points are re-matched
  every outer iteration and robustly weighted. The error is the sensor's depth noise plus a few mm of model
  error. The nearest-surface distance alone, with noise along the line of sight, made bodies 6-8% too light.
- **Silhouette:** the model's visible surface outside the depth silhouette, in metres at its depth, with
  1 px tolerance for the pixels a sensor drops at edges.
- **Floor** (optional): no model vertex below the floor plane.
- **2D keypoints** (optional): the projected model joints, in pixels.
- **Measured height** (optional).
- **Priors:** N(0, 1) on the betas (the shape space's own scale) and a per-axis prior on the pose
  (``POSE_SD``; tight for the spine).

Fingers are not fitted (too small for the sensor) and are left out of the data and silhouette terms. The
betas are released coarse to fine (none, 4, 8, then 16): released all at once, high-order components and a
folded spine stood in for a heavy body's belly and chest, and an initial pose error was absorbed into shape.

It returns:
- betas and pose;
- the rest-pose height, and mass and BMI from the mesh volume at 1000 kg/m^3;
- joint positions and segment lengths;
- the front skin-to-joint distances that ``rehabtwin.kinect`` adds to a depth reading;
- the fit residuals.

Limits:
- **SMPL-X joints are not anatomical joint centres.** The model regresses them from its surface
  (``J_regressor``, learned from registered scans). Segment lengths between them are model quantities, with
  their own bias against anatomy (imaging), which this module does not measure.
- **The sensor sees the front only.** The back of the body comes from how the shape space links back and
  front, not from data, so mass and BMI carry that error.
- **Segmentation is the caller's job.** The points must be the person's pixels only.

Validated on synthetic BEDLAM2 bodies (``adapters/bedlam2.py shapefit``; docs/bedlam2.md, result 4).
``render_depth`` and ``kinect_v1_noise`` make the synthetic depth that the validation uses.
"""
from __future__ import annotations

import time

import numpy as np
from scipy import ndimage
from scipy.optimize import least_squares
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation

DENSITY = 1000.0                    # kg/m^3, as adapters/bedlam2.py: mass from volume is an estimate
# 2D keypoints fit_shape takes, in this order -> SMPL-X joint (the joints rehabtwin.kinect lifts)
KEYPOINTS = {"LHip": 1, "RHip": 2, "LKnee": 4, "RKnee": 5, "LAnkle": 7, "RAnkle": 8, "LShoulder": 16,
             "RShoulder": 17, "LElbow": 18, "RElbow": 19, "LWrist": 20, "RWrist": 21}
# segment -> (left, right) SMPL-X joint pairs
SEGMENTS = {"hip-knee": ((1, 4), (2, 5)), "knee-ankle": ((4, 7), (5, 8)), "shoulder-elbow": ((16, 18), (17, 19)),
            "elbow-wrist": ((18, 20), (19, 21))}
BODY_JOINTS = 21                    # SMPL-X joints 1..21 are fitted; jaw, eyes and fingers stay as given (zero)
# Pose prior SD (rad) per SMPL-X joint and local axis (x, y, z), 1.0 when not listed: about twice the SD
# across BEDLAM2's (AMASS) motion frames, where spine2 and spine3 flex by 9 and 5 deg SD and the spine
# twists and bends sideways by 3-5 deg. Left loose, the spine of a heavy body (far behind the skin seen from
# the front) folds into a zig-zag whose skinning bulges stand in for belly and chest shape. Ankles twist by
# ~7 deg: a turned-out foot is hip rotation, and a loose ankle let a foot turn backwards.
POSE_SD = {3: (0.3, 0.1, 0.1), 6: (0.15, 0.1, 0.1), 9: (0.1, 0.1, 0.1), 12: (0.3, 0.3, 0.2), 15: (0.3, 0.3, 0.2),
           13: (0.3, 0.3, 0.3), 14: (0.3, 0.3, 0.3), 10: (0.3, 0.3, 0.3), 11: (0.3, 0.3, 0.3),
           4: (1.0, 0.3, 0.3), 5: (1.0, 0.3, 0.3), 7: (0.5, 0.3, 0.3), 8: (0.5, 0.3, 0.3)}
ARMS_DOWN = {16: (0.0, 0.0, -1.2), 17: (0.0, 0.0, 1.2)}   # start with the arms hanging, not in the T-pose
KINECT_SD_COEFF = 1.5e-3            # depth SD = 1.5e-3 z^2 m (Khoshelham & Elberink 2012: ~4 cm at 5 m)
KINECT_FB_PXM = 0.075 * 580.0       # IR baseline x focal length (m px) of a Kinect v1: disparity = fb / z


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


class BodyModel:
    """An SMPL-X-format body model (the dict of arrays ``adapters/bedlam2.load_smplx`` returns): rest shape,
    regressed joints and linear blend skinning with pose correctives, batched over parameter sets so that a
    finite-difference Jacobian costs one call."""

    def __init__(self, model, n_betas=16):
        self.v_template = np.asarray(model["v_template"], float)
        self.shapedirs = np.asarray(model["shapedirs"], float)[:, :, :n_betas]
        self.n_betas = self.shapedirs.shape[2]
        self.posedirs = np.asarray(model["posedirs"], float)
        self.weights = np.asarray(model["weights"], float)
        self.faces = np.asarray(model["f"]).astype(np.int64)
        Jr = np.asarray(model["J_regressor"], float)
        self.J_template = Jr @ self.v_template
        self.J_dirs = np.einsum("jv,vck->jck", Jr, self.shapedirs)
        self.parents = np.asarray(model["kintree_table"])[0].astype(np.int64)
        self.parents[0] = -1
        self.n_joints = len(self.parents)

    def rest(self, betas):
        """(vertices (V,3), joints (J,3)) in the rest pose (y up), metres."""
        b = np.asarray(betas, float)
        return self.v_template + self.shapedirs @ b, self.J_template + self.J_dirs @ b

    def posed(self, betas, rots, trans, idx=None, offsets=None):
        """(vertices (B,n,3), joints (B,J,3)) for B parameter sets: betas (B,nb), joint rotations (B,J,3,3) in
        the SMPL-X convention (the root turns about the rest pelvis), trans (B,3). Only vertices ``idx`` (all
        when None). ``offsets`` (n,3) stand in for the pose correctives (computed from ``rots`` when None)."""
        betas, rots, trans = np.asarray(betas, float), np.asarray(rots, float), np.asarray(trans, float)
        B, nj = len(betas), self.n_joints
        idx = np.arange(len(self.v_template)) if idx is None else idx
        J = self.J_template + np.einsum("jck,bk->bjc", self.J_dirs, betas)
        G = np.zeros((B, nj, 4, 4))
        L = np.zeros((B, 4, 4))
        L[:, 3, 3] = 1.0
        for i, p in enumerate(self.parents):
            L[:, :3, :3] = rots[:, i]
            L[:, :3, 3] = J[:, i] - (J[:, p] if p >= 0 else 0.0)
            G[:, i] = L if p < 0 else G[:, p] @ L
        A = G[:, :, :3, :].copy()
        A[:, :, :, 3] -= np.einsum("bjik,bjk->bji", G[:, :, :3, :3], J)
        n = len(idx)                     # vertex-major (n, B, ...): one 2D matrix product does the blending
        T = (self.weights[idx] @ A.reshape(B, nj, 12).transpose(1, 0, 2).reshape(nj, B * 12)).reshape(n, B, 3, 4)
        nb, npd = self.shapedirs.shape[2], self.posedirs.shape[2]
        vp = self.v_template[idx][:, None] + (self.shapedirs[idx].reshape(3 * n, nb) @ betas.T).reshape(n, 3, B).transpose(0, 2, 1)
        if offsets is None:
            feat = (rots[:, 1:] - np.eye(3)).reshape(B, -1)
            offsets = (self.posedirs[idx].reshape(3 * n, npd) @ feat.T).reshape(n, 3, B).transpose(0, 2, 1)
        else:
            offsets = np.asarray(offsets)[:, None]
        vp = vp + offsets
        v = np.einsum("nbij,nbj->nbi", T[..., :3], vp) + T[..., 3] + trans[None]
        return v.transpose(1, 0, 2), G[:, :, :3, 3] + trans[:, None]


def body_measures(v, faces, density=DENSITY):
    """(height m, volume m^3, mass kg, BMI) of a closed mesh standing along +y (mass from volume)."""
    h = float(v[:, 1].max() - v[:, 1].min())
    a, b, c = v[faces[:, 0]], v[faces[:, 1]], v[faces[:, 2]]
    vol = abs(float(np.einsum("ij,ij->i", a, np.cross(b, c)).sum())) / 6.0
    return h, vol, vol * density, vol * density / h ** 2


def ray_hits(orig, direction, v, faces):
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


def front_offsets(v_rest, J_rest, faces):
    """Front skin-to-joint distance (m) of each KEYPOINTS joint in the rest pose: along +z (the model's front)
    from the joint to the first skin triangle, as ``adapters/bedlam2.py offsets`` measures it."""
    return {n: ray_hits(J_rest[j], np.array([0.0, 0.0, 1.0]), v_rest, faces) for n, j in KEYPOINTS.items()}


def segment_lengths(J_rest):
    """{segment: (left, right) length m} between SMPL-X joints (regressed joints, not anatomical centres)."""
    return {s: tuple(float(np.linalg.norm(J_rest[a] - J_rest[b])) for a, b in lr) for s, lr in SEGMENTS.items()}


# ---- synthetic depth --------------------------------------------------------------------------------------

def render_depth(v_cam, faces, K, size=(640, 480)):
    """(z-depth (H,W) m, inf where empty; face index (H,W), -1 where empty) of a triangle mesh seen by a pinhole
    camera at the origin (OpenCV axes: x right, y down, z forward). Pixel (row i, column j) samples the ray
    through (j + 0.5, i + 0.5), the convention of ``rehabtwin.kinect``. Depth is the exact ray-plane hit,
    z-buffered. Triangles must lie in front of the camera (no near-plane clipping)."""
    fx, fy, cx, cy = K
    W, H = size
    depth = np.full(H * W, np.inf)
    fid = np.full(H * W, -1, np.int64)
    keep = np.flatnonzero((v_cam[faces, 2] > 1e-3).all(axis=1))
    a, b, c = (v_cam[faces[keep, k]] for k in range(3))
    P = np.stack([a, b, c], axis=1)
    pu = fx * P[..., 0] / P[..., 2] + cx
    pv = fy * P[..., 1] / P[..., 2] + cy
    j0 = np.clip(np.ceil(pu.min(1) - 0.5), 0, W).astype(np.int64)
    j1 = np.clip(np.floor(pu.max(1) - 0.5), -1, W - 1).astype(np.int64)
    i0 = np.clip(np.ceil(pv.min(1) - 0.5), 0, H).astype(np.int64)
    i1 = np.clip(np.floor(pv.max(1) - 0.5), -1, H - 1).astype(np.int64)
    nu, nv = np.maximum(j1 - j0 + 1, 0), np.maximum(i1 - i0 + 1, 0)
    cnt = nu * nv
    if cnt.sum() == 0:
        return depth.reshape(H, W), fid.reshape(H, W)
    t = np.repeat(np.arange(len(keep)), cnt)
    local = np.arange(cnt.sum()) - np.repeat(np.cumsum(cnt) - cnt, cnt)
    jj, ii = j0[t] + local % nu[t], i0[t] + local // nu[t]
    x, y = jj + 0.5, ii + 0.5
    ua, ub, uc, va, vb, vc = pu[t, 0], pu[t, 1], pu[t, 2], pv[t, 0], pv[t, 1], pv[t, 2]
    area = (ub - ua) * (vc - va) - (uc - ua) * (vb - va)
    w0 = (ub - x) * (vc - y) - (uc - x) * (vb - y)
    w1 = (uc - x) * (va - y) - (ua - x) * (vc - y)
    w2 = (ua - x) * (vb - y) - (ub - x) * (va - y)
    s = np.sign(area)
    inside = (area != 0) & (w0 * s >= 0) & (w1 * s >= 0) & (w2 * s >= 0)
    t, ii, jj, x, y = t[inside], ii[inside], jj[inside], x[inside], y[inside]
    n = np.cross(b - a, c - a)[t]
    d = np.stack([(x - cx) / fx, (y - cy) / fy, np.ones_like(x)], axis=1)
    z = (n * a[t]).sum(1) / (n * d).sum(1)          # ray-plane hit; the ray's z component is 1, so t is z
    pix = ii * W + jj
    order = np.lexsort((z, pix))
    first = np.r_[True, pix[order][1:] != pix[order][:-1]]
    sel = order[first]
    depth[pix[sel]], fid[pix[sel]] = z[sel], keep[t[sel]]
    return depth.reshape(H, W), fid.reshape(H, W)


def kinect_v1_noise(depth_m, rng, sd_coeff=KINECT_SD_COEFF, edge_px=2, edge_drop=0.5, jump_m=0.05, corr_px=0.0,
                    disparity_step_px=None, fb_pxm=KINECT_FB_PXM):
    """Depth (mm, uint16, 0 = no depth) a Kinect v1 would report for a clean z-depth image (m; inf or 0 = none).

    - random error N(0, (sd_coeff z^2)^2) (Khoshelham & Elberink 2012: it grows with z^2, ~4 cm at 5 m),
      spatially correlated over ``corr_px`` (Gaussian; 0 = independent pixels), at the same per-pixel SD;
    - ``disparity_step_px`` (e.g. 1/8): the sensor's disparity quantisation, depth steps of z^2 / fb * step
      (~2 cm at 2.7 m); the noise is then applied to disparity, where it is constant;
    - pixels within ``edge_px`` of a silhouette edge (an empty neighbour or a depth jump over ``jump_m``)
      dropped with probability ``edge_drop``;
    - rounded to mm, as the SDK reports it.
    """
    z = np.where(np.isfinite(depth_m) & (depth_m > 0), depth_m, 0.0)
    valid = z > 0
    e = rng.normal(0.0, 1.0, z.shape)
    if corr_px > 0:
        e = ndimage.gaussian_filter(e, corr_px)
        e /= e.std()
    if disparity_step_px:
        disp = np.where(valid, fb_pxm / np.where(valid, z, 1.0) + sd_coeff * fb_pxm * e, np.inf)
        disp = np.round(disp / disparity_step_px) * disparity_step_px
        zn = np.where(valid & (disp > 0), fb_pxm / np.where(disp > 0, disp, 1.0), 0.0)
    else:
        zn = np.where(valid, z + sd_coeff * z ** 2 * e, 0.0)
    edge = np.zeros_like(valid)
    zp = np.pad(z, 1)
    vp = np.pad(valid, 1)
    for di, dj in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        nb = zp[1 + di:1 + di + z.shape[0], 1 + dj:1 + dj + z.shape[1]]
        nbv = vp[1 + di:1 + di + z.shape[0], 1 + dj:1 + dj + z.shape[1]]
        edge |= valid & (~nbv | (np.abs(nb - z) > jump_m))
    if edge_px > 1:
        edge = ndimage.binary_dilation(edge, iterations=edge_px - 1) & valid
    drop = edge & (rng.random(z.shape) < edge_drop)
    mm = np.round(zn * 1000.0)
    return np.where(valid & ~drop & (mm > 0), np.clip(mm, 0, 65535), 0).astype(np.uint16)


def depth_points(depth_mm, K, mask=None):
    """Camera-coordinate points (N,3) m of the non-zero depth pixels (within ``mask``), at pixel centres."""
    fx, fy, cx, cy = K
    ok = depth_mm > 0 if mask is None else (depth_mm > 0) & mask
    i, j = np.nonzero(ok)
    z = depth_mm[i, j] / 1000.0
    return np.stack([(j + 0.5 - cx) / fx * z, (i + 0.5 - cy) / fy * z, z], axis=1)


# ---- fitting ----------------------------------------------------------------------------------------------

def closest_on_triangles(p, a, b, c):
    """(closest points (...,3), barycentric weights (...,3)) on triangles (a, b, c) to points p."""
    ab, ac, ap = b - a, c - a, p - a
    n = np.cross(ab, ac)
    nn = np.maximum((n * n).sum(-1), 1e-30)
    s = (np.cross(ap, ac) * n).sum(-1) / nn
    t = (np.cross(ab, ap) * n).sum(-1) / nn
    inside = (s >= 0) & (t >= 0) & (s + t <= 1)
    q = a + s[..., None] * ab + t[..., None] * ac
    best = np.where(inside, ((p - q) ** 2).sum(-1), np.inf)
    w = np.stack([1 - s - t, s, t], axis=-1)
    for i, j, x, y in ((0, 1, a, b), (1, 2, b, c), (2, 0, c, a)):
        e = y - x
        u = np.clip(((p - x) * e).sum(-1) / np.maximum((e * e).sum(-1), 1e-30), 0, 1)
        qe = x + u[..., None] * e
        d = ((p - qe) ** 2).sum(-1)
        better = d < best
        best = np.where(better, d, best)
        q = np.where(better[..., None], qe, q)
        we = np.zeros_like(w)
        we[..., i], we[..., j] = 1 - u, u
        w = np.where(better[..., None], we, w)
    return q, w


def _project(P, K):
    fx, fy, cx, cy = K
    return np.stack([fx * P[..., 0] / P[..., 2] + cx, fy * P[..., 1] / P[..., 2] + cy], axis=-1)


def _upright(up):
    """Root rotation (body y up, z front) standing along ``up`` and facing the camera (camera coordinates)."""
    y = up / np.linalg.norm(up)
    z = np.array([0.0, 0.0, -1.0]) + y[2] * y
    z /= np.linalg.norm(z)
    return np.stack([np.cross(y, z), y, z], axis=1)


def _kabsch(src, dst):
    """Rotation R and offset c minimising |R src + c - dst|."""
    ms, md = src.mean(0), dst.mean(0)
    U, _, Vt = np.linalg.svd((src - ms).T @ (dst - md))
    D = np.diag([1.0, 1.0, np.sign(np.linalg.det(Vt.T @ U.T))])
    R = Vt.T @ D @ U.T
    return R, md - R @ ms


class _Frame:
    """One depth frame's observations, its pose state and the correspondences of the current outer iteration."""

    def __init__(self, obs, K, size, n_joints, kp_joints, closing_px):
        W, H = size
        self.points = np.asarray(obs["points"], float)
        if len(self.points) < 100:
            raise ValueError(f"only {len(self.points)} depth points: is the person in the depth image?")
        uv = _project(self.points, K)
        col = np.clip(np.floor(uv[:, 0]).astype(int), 0, W - 1)
        row = np.clip(np.floor(uv[:, 1]).astype(int), 0, H - 1)
        mask = np.zeros((H, W), bool)
        mask[row, col] = True
        if closing_px:                               # fill pixels the sensor dropped at the edges
            mask = ndimage.binary_closing(mask, iterations=closing_px) | mask
        self.dt = ndimage.distance_transform_edt(~mask)   # px from each pixel to the person's pixels
        self.depth_mm = np.zeros((H, W), np.uint16)
        self.depth_mm[row, col] = np.round(self.points[:, 2] * 1000).astype(np.uint16)
        kp = obs.get("keypoints_uv")
        nk = len(kp_joints)
        self.kp_uv = np.full((nk, 2), np.nan) if kp is None else np.asarray(kp, float).reshape(nk, 2)
        conf = obs.get("keypoint_conf")
        self.kp_w = np.ones(nk) if conf is None else np.asarray(conf, float)
        self.kp_w = np.where(np.isfinite(self.kp_uv).all(1), self.kp_w, 0.0)
        self.kp_uv = np.nan_to_num(self.kp_uv)
        self.lifted = None
        self.fixed = np.broadcast_to(np.eye(3), (n_joints, 3, 3)).copy()   # jaw, eyes, fingers: zero pose
        self.R0 = np.eye(3)


class _Fit:
    """The parameter vector [betas (when free); per frame: root delta (3), body joints (3 x nbj), trans (3)], its
    residuals and their batched finite-difference Jacobian."""

    def __init__(self, bm, frames, K, size, cfg):
        self.bm, self.frames, self.K, self.size, self.cfg = bm, frames, K, size, cfg
        self.nbj = min(BODY_JOINTS, bm.n_joints - 1)
        self.nq = 3 + 3 * self.nbj + 3
        self.kp_joints = np.asarray(cfg["keypoint_joints"], int)
        sd = [POSE_SD.get(j, (1.0,) * 3) if bm.n_joints == 55 else (1.0,) * 3 for j in range(1, self.nbj + 1)]
        self.pose_sd = np.ravel(sd)
        self.free_betas, self.stage, self.top, self.bot = False, "keypoints", 0, 0
        self.beta_sd = np.full(bm.n_betas, cfg["beta_sd"])
        # fingers are not fitted (zero pose; too small for the sensor): their faces and vertices are left out
        finger = bm.weights[:, 25:].sum(1) > 0.5 if bm.n_joints == 55 else np.zeros(len(bm.weights), bool)
        self.finger_v, self.finger_f = finger, finger[bm.faces].any(1)

    def rots(self, fr, Q):
        B = len(Q)
        R = np.broadcast_to(fr.fixed, (B,) + fr.fixed.shape).copy()
        R[:, 0] = rodrigues(Q[:, :3]) @ fr.R0
        R[:, 1:1 + self.nbj] = rodrigues(Q[:, 3:3 + 3 * self.nbj].reshape(B, self.nbj, 3))
        return R

    def match(self, fr, betas, Q, gate, rng):
        """Correspondences of one frame at the current estimate, held fixed in the next inner solve. A depth
        point whose pixel the posed model covers (its z-buffer) is compared with the model's depth along the
        same line of sight: the sensor's error lies along it. Other points (outside the model's silhouette, at
        a depth jump or a grazing face) go to the closest point on the model faces the sensor could see. Also:
        robust weights, silhouette and sole vertices, the pose correctives. Returns residual statistics."""
        bm, cfg = self.bm, self.cfg
        R = self.rots(fr, Q[None])
        v = bm.posed(betas[None], R, Q[None, -3:])[0][0]
        zbuf, fid = render_depth(v, bm.faces, self.K, self.size)
        p = fr.points_used
        sd_z = cfg["depth_sd"](p[:, 2])
        hit = fid[fr.pix_used[:, 0], fr.pix_used[:, 1]]
        dz = p[:, 2] - zbuf[fr.pix_used[:, 0], fr.pix_used[:, 1]]
        nrm = np.cross(v[bm.faces[hit, 1]] - v[bm.faces[hit, 0]], v[bm.faces[hit, 2]] - v[bm.faces[hit, 0]])
        cos = np.abs((nrm * p).sum(1)) / np.maximum(np.linalg.norm(nrm, axis=1) * np.linalg.norm(p, axis=1), 1e-12)
        ray = (hit >= 0) & (np.abs(dz) <= gate) & (cos > 0.15) & ~self.finger_f[np.maximum(hit, 0)]
        tri = bm.faces[np.unique(fid[fid >= 0])]
        k = min(8, len(tri))
        q_pts = p[~ray]
        nn = cKDTree(v[tri].mean(1)).query(q_pts, k=k)[1].reshape(len(q_pts), k)
        q, w = closest_on_triangles(q_pts[:, None], *(v[tri[nn, i]] for i in range(3)))
        d2 = ((q_pts[:, None] - q) ** 2).sum(-1)
        best = np.argmin(d2, axis=1)
        ar = np.arange(len(best))
        near_face, fr.near_bary, dist = tri[nn[ar, best]], w[ar, best], np.sqrt(d2[ar, best])
        on_finger = self.finger_v[near_face].any(1)
        n2 = np.cross(v[near_face[:, 1]] - v[near_face[:, 0]], v[near_face[:, 2]] - v[near_face[:, 0]])
        fr.near_normals = n2 / np.maximum(np.linalg.norm(n2, axis=1, keepdims=True), 1e-12)
        fr.ray_p, fr.near_p = p[ray], q_pts
        fr.ray_dir = p[ray] / p[ray, 2:3]
        sd_ray = np.sqrt(sd_z[ray] ** 2 + (cfg["model_sd_m"] / cos[ray]) ** 2)
        sd_near = np.sqrt(sd_z[~ray] ** 2 + cfg["model_sd_m"] ** 2)

        def weights(r, sd, g):                                   # Huber, linear beyond 2 SD; gated
            c = 2.0 * sd
            rob = np.where(np.abs(r) <= c, 1.0, np.sqrt(c / np.maximum(np.abs(r), 1e-12)))
            return np.where(np.abs(r) <= g, rob / sd, 0.0)
        # a point outside the model's silhouette is the person where the model is not: kept up to 15 cm away
        outside = hit[~ray] < 0
        w_ray = weights(dz[ray], sd_ray, gate)
        w_near = np.where(on_finger, 0.0, np.where(outside, weights(dist, sd_near, max(gate, 0.15)),
                                                    weights(dist, sd_near, gate)))
        used = int((w_ray > 0).sum() + (w_near > 0).sum())
        scale = np.sqrt(cfg["n_eff"] / max(used, 1))
        fr.w_ray, fr.w_near = w_ray * scale, w_near * scale
        sil = np.unique(tri)
        sil = sil[~self.finger_v[sil]]
        floor = fr.floor
        if floor is not None:                                     # the lowest cm cannot be told from the floor
            sil = sil[v[sil] @ floor[0] - floor[1] > cfg["floor_clear_m"]]
        if len(sil) > 3000:
            sil = rng.choice(sil, 3000, replace=False)
        sole = np.flatnonzero(v @ floor[0] - floor[1] < 0.03) if floor is not None else np.zeros(0, np.int64)
        ray_face = bm.faces[hit[ray]]
        fr.idx, inv = np.unique(np.r_[ray_face.ravel(), near_face.ravel(), sil, sole], return_inverse=True)
        o = np.cumsum([0, ray_face.size, near_face.size, len(sil), len(sole)])
        fr.ray_corr, fr.near_corr = inv[o[0]:o[1]].reshape(-1, 3), inv[o[1]:o[2]].reshape(-1, 3)
        fr.sil, fr.sole = inv[o[2]:o[3]], inv[o[3]:o[4]]
        fr.w_sil = np.sqrt(cfg["n_eff_sil"] / max(len(sil), 1)) / cfg["sil_sd_m"]
        fr.offsets = np.einsum("ncp,p->nc", bm.posedirs[fr.idx], (R[0, 1:] - np.eye(3)).ravel())
        vis = np.unique(tri)
        uv = _project(v[vis[~self.finger_v[vis]]], self.K) - 0.5
        H, W = fr.dt.shape
        out_px = ndimage.map_coordinates(fr.dt, [np.clip(uv[:, 1], 0, H - 1), np.clip(uv[:, 0], 0, W - 1)], order=1)
        rz = dz[ray][np.abs(dz[ray]) <= gate]
        return {"points": len(fr.points), "points_sampled": len(p), "fraction_line_of_sight": float(ray.mean()),
                "fraction_used": used / len(p), "gate_m": gate,
                "rms_depth_residual_mm": float(1000 * np.sqrt(np.mean(rz ** 2))) if len(rz) else None,
                "median_point_to_surface_mm": float(1000 * np.median(dist)) if len(dist) else None,
                "visible_model_outside_silhouette": float(np.mean(out_px > 1.0))}

    def frame_residuals(self, fr, betas, Q, stage):
        """(B, m) residuals of one frame for B parameter sets."""
        cfg, K = self.cfg, self.K
        v, J = self.bm.posed(betas, self.rots(fr, Q), Q[:, -3:], fr.idx, fr.offsets)
        out = []
        if stage == "surface":
            a, b, c = (v[:, fr.ray_corr[:, i]] for i in range(3))
            n = np.cross(b - a, c - a)
            z = (n * a).sum(-1) / (n * fr.ray_dir).sum(-1)           # model depth on the point's line of sight
            out.append(fr.w_ray * (fr.ray_p[:, 2] - z))
            m = (fr.near_bary[None, :, :, None] * v[:, fr.near_corr]).sum(2)
            out.append(fr.w_near * ((fr.near_p - m) * fr.near_normals).sum(-1))
            vs = v[:, fr.sil]
            uv = _project(vs, K) - 0.5                              # pixel centres at integer indices
            H, W = fr.dt.shape
            cu, cv = np.clip(uv[..., 0], 0, W - 1), np.clip(uv[..., 1], 0, H - 1)
            d = ndimage.map_coordinates(fr.dt, [cv.ravel(), cu.ravel()], order=1).reshape(cu.shape)
            d = d + np.hypot(uv[..., 0] - cu, uv[..., 1] - cv)       # beyond the image border
            out.append(fr.w_sil * np.maximum(d - 0.5 - cfg["sil_tol_px"], 0.0) * vs[..., 2] / K[0])  # 0.5: centre to edge
            if fr.floor is not None:
                up, off = fr.floor
                out.append(np.minimum(v[:, fr.sole] @ up - off, 0.0) / cfg["floor_sd_m"])
        kp = _project(J[:, self.kp_joints], K)
        out.append(((kp - fr.kp_uv) * (fr.kp_w[:, None] / cfg["keypoint_sd_px"])).reshape(len(Q), -1))
        if stage == "keypoints" and fr.lifted is not None:
            out.append(((J[:, self.kp_joints] - fr.lifted) * fr.lifted_w[:, None]).reshape(len(Q), -1))
        return np.concatenate(out, axis=1)

    def split(self, x):
        nb = self.bm.n_betas if self.free_betas else 0
        return (x[:nb] if self.free_betas else self.betas_fixed), x[nb:].reshape(len(self.frames), self.nq)

    def height(self, betas):
        """Rest-pose height with the current top and bottom vertices (linear in the betas)."""
        bm = self.bm
        return (bm.v_template[self.top, 1] - bm.v_template[self.bot, 1]
                + (bm.shapedirs[self.top, 1] - bm.shapedirs[self.bot, 1]) @ betas)

    def global_residuals(self, betas, Qs):
        cfg = self.cfg
        out = [Qs[:, 3:3 + 3 * self.nbj].ravel() / np.tile(self.pose_sd, len(Qs))]
        if self.free_betas:
            out.append(betas / self.beta_sd)
            if cfg["height_m"] is not None:
                out.append(np.array([(self.height(betas) - cfg["height_m"]) / cfg["height_sd_m"]]))
        return np.concatenate(out)

    def fun(self, x):
        betas, Qs = self.split(x)
        r = [self.frame_residuals(fr, betas[None], Q[None], self.stage)[0] for fr, Q in zip(self.frames, Qs)]
        return np.concatenate(r + [self.global_residuals(betas, Qs)])

    def jac(self, x, h=1e-6):
        """Forward differences, all perturbations of one frame in one batched posing call; priors analytic."""
        betas, Qs = self.split(x)
        nb = self.bm.n_betas if self.free_betas else 0
        F, nq = len(self.frames), self.nq
        blocks = []
        for f, (fr, Q) in enumerate(zip(self.frames, Qs)):
            bb = np.repeat(betas[None], 1 + nb + nq, 0)
            QQ = np.repeat(Q[None], 1 + nb + nq, 0)
            if nb:
                bb[1:1 + nb] += h * np.eye(nb)
            QQ[1 + nb:] += h * np.eye(nq)
            r = self.frame_residuals(fr, bb, QQ, self.stage)
            d = (r[1:] - r[0]).T / h
            Jf = np.zeros((r.shape[1], nb + F * nq))
            Jf[:, :nb] = d[:, :nb]
            Jf[:, nb + f * nq:nb + (f + 1) * nq] = d[:, nb:]
            blocks.append(Jf)
        g = np.zeros((len(self.global_residuals(betas, Qs)), nb + F * nq))
        row = 0
        for f in range(F):
            for k in range(3 * self.nbj):
                g[row, nb + f * nq + 3 + k] = 1.0 / self.pose_sd[k]
                row += 1
        if self.free_betas:
            g[row:row + nb, :nb] = np.diag(1.0 / self.beta_sd)
            row += nb
            if self.cfg["height_m"] is not None:
                g[row, :nb] = (self.bm.shapedirs[self.top, 1] - self.bm.shapedirs[self.bot, 1]) / self.cfg["height_sd_m"]
        return np.vstack(blocks + [g])


def _lift_keypoints(fr, K, names, height_m):
    """3D keypoints from the frame's own depth (``rehabtwin.kinect``'s lifting at BMI 25): for the start only."""
    from .kinect import SURFACE_TO_CENTRE, back_project, sample_depth, surface_to_centre
    out = np.full((len(names), 3), np.nan)
    for k, n in enumerate(names):
        if fr.kp_w[k] <= 0:
            continue
        z = sample_depth(fr.depth_mm, fr.kp_uv[k, 0], fr.kp_uv[k, 1])
        if np.isfinite(z):
            s = back_project(fr.kp_uv[k, 0], fr.kp_uv[k, 1], z, *K)
            off = surface_to_centre(n, height_m) if n in SURFACE_TO_CENTRE else 0.0
            out[k] = s + off * s / np.linalg.norm(s)
    return out


def _start(fit, fr, q, up, kp_names, height_m):
    """Root rotation (``fr.R0``) and translation of one frame before fitting: upright along ``up`` facing the
    camera, then rigidly onto the keypoints lifted with depth when at least 4 are; else the pelvis 8 cm
    behind the median depth point."""
    bm = fit.bm
    fr.R0 = _upright(up)
    Jt = bm.posed(np.zeros((1, bm.n_betas)), fit.rots(fr, q[None]), np.zeros((1, 3)), idx=np.zeros(0, np.int64),
                  offsets=np.zeros((0, 3)))[1][0]
    kj = fit.kp_joints
    fr.lifted = _lift_keypoints(fr, fit.K, kp_names, height_m or 1.70) if fr.kp_w.sum() > 0 else None
    ok = np.isfinite(fr.lifted).all(1) if fr.lifted is not None else np.zeros(len(kj), bool)
    if ok.sum() >= 4:
        R, c = _kabsch(Jt[kj][ok], fr.lifted[ok])
        if (R @ fr.R0[:, 1]) @ up > 0.5:                 # keep only a plausible, upright rigid fit
            fr.R0 = R @ fr.R0
            q[-3:] = c + R @ Jt[0] - Jt[0]                 # posed = R (Jt - J0) + J0 + t  ==  R Jt + c
        else:
            q[-3:] = fr.lifted[ok].mean(0) - Jt[kj][ok].mean(0)
        fr.lifted_w = np.where(ok, 1.0 / 0.05, 0.0)       # 5 cm: the lifted keypoints are rough
        fr.lifted = np.nan_to_num(fr.lifted)
    else:
        q[-3:] = np.median(fr.points, axis=0) + [0.0, 0.0, 0.08] - Jt[0]
        fr.lifted = None
    return q


def _unit_floor(floor):
    """(unit normal pointing up (camera -y for a level sensor), offset) of a floor plane n . p = offset."""
    if floor is None:
        return None
    n, off = np.asarray(floor[0], float), float(floor[1])
    n, off = n / np.linalg.norm(n), off / np.linalg.norm(n)
    return (-n, -off) if n[1] > 0 else (n, off)


def fit_shape(model, frames, K, size=(640, 480), height_m=None, height_sd_m=0.005, floor=None, n_betas=16,
              keypoint_sd_px=3.0, beta_sd=1.0, depth_sd=None, model_sd_m=0.004, n_eff=300, sil_sd_m=0.005,
              n_eff_sil=100, sil_tol_px=1.0, floor_sd_m=0.005, floor_clear_m=0.02, outer=25, inner_nfev=8,
              tol=5e-3, max_points=4000, closing_px=2, keypoint_joints=None, keypoint_names=None, init=None,
              beta_schedule=((0, 0), (1, 4), (3, 8), (5, None)), seed=0):
    """Fit an SMPL-X body (shared betas, a pose per frame) to a person's depth points.

    ``model``: a BodyModel, or the model's arrays (``adapters/bedlam2.load_smplx``). ``frames``: one dict per
    depth frame of the same person, in that frame's camera coordinates (OpenCV axes, metres):
      - ``points`` (N,3): the person's depth pixels back-projected at pixel centres (``depth_points``) with
        intrinsics ``K`` = (fx, fy, cx, cy) on an image of ``size`` (W, H). The silhouette is rebuilt from
        them, so pass every person pixel with depth, not a subsample.
      - optional ``keypoints_uv`` (12,2) in KEYPOINTS order (NaN = missing), ``keypoint_conf`` (12,), ``floor``.
    ``height_m``: measured standing height (SD ``height_sd_m``), compared with the rest-pose mesh height.
    ``floor``: (up (3,), offset), up . p = offset on the floor (as ``rehabtwin.kinect.floor_up``), for every
    frame without its own ``floor`` entry. It keeps the model above the floor, and the silhouette term then
    ignores the model's lowest ``floor_clear_m``, which a segmentation cannot tell from the floor.
    ``depth_sd(z)``: the sensor's depth SD (m); default Kinect v1.
    ``n_eff``: how many independent observations the depth points count as. A Kinect v1 matches its pattern
    over ~9x9 px windows, so ~16k person pixels carry a few hundred independent errors; this sets their
    weight against the keypoints and priors (at 1000, betas ran to +-6 SD to absorb a wrong arm pose). ``init``: start from an earlier
    result (its ``betas`` and per frame ``global_orient``, ``body_pose``, ``transl``) instead of the keypoints.
    ``beta_schedule``: (outer iteration, number of betas free from then on; None = all): the first iteration
    aligns pose and translation with the mean shape before any shape is fitted. The fit stops when
    the cost fell by less than ``tol`` (relative) over two outer iterations, at most ``outer``.

    Returns a dict: ``betas``; ``height_m``, ``volume_m3``, ``mass_kg``, ``bmi`` (rest pose, mesh volume at
    1000 kg/m^3); ``rest_joints``; ``segment_lengths_m`` {segment: (left, right)}; ``surface_to_centre_m``
    {keypoint: front skin-to-joint distance}; ``frames``, one per frame: global_orient (axis-angle, camera
    coordinates), body_pose (21,3), transl, joints (J,3) in camera coordinates, residuals; ``fit`` (runtime,
    iterations, ``warnings``). The SMPL-X joints are regressed from the surface, not anatomical joint centres.

    ``fit.warnings`` flags fits not to trust: a beta beyond +-4 SD (outside the range of real body shapes;
    the shape absorbed a wrong pose), under 90% of the depth points on the model along their line of sight
    (pose or segmentation wrong), or no convergence.
    """
    t_start = time.time()
    bm = model if isinstance(model, BodyModel) else BodyModel(model, n_betas)
    kp_joints = list(KEYPOINTS.values()) if keypoint_joints is None else list(keypoint_joints)
    kp_names = list(KEYPOINTS) if keypoint_names is None else list(keypoint_names)
    cfg = {"keypoint_joints": kp_joints, "keypoint_sd_px": keypoint_sd_px, "beta_sd": beta_sd, "height_m": height_m,
           "height_sd_m": height_sd_m, "floor_sd_m": floor_sd_m, "floor_clear_m": floor_clear_m,
           "depth_sd": depth_sd or (lambda z: KINECT_SD_COEFF * z ** 2), "model_sd_m": model_sd_m, "n_eff": n_eff,
           "sil_sd_m": sil_sd_m, "n_eff_sil": n_eff_sil, "sil_tol_px": sil_tol_px}
    rng = np.random.default_rng(seed)
    frs = [_Frame(o, K, size, bm.n_joints, kp_joints, closing_px) for o in frames]
    fit = _Fit(bm, frs, K, size, cfg)
    fit.betas_fixed = np.zeros(bm.n_betas)
    Qs = np.zeros((len(frs), fit.nq))
    for f, (fr, o) in enumerate(zip(frs, frames)):
        fr.floor = _unit_floor(o.get("floor", floor))
        up = np.array([0.0, -1.0, 0.0]) if fr.floor is None else fr.floor[0]
        fr.points_used = fr.points[rng.choice(len(fr.points), min(max_points, len(fr.points)), replace=False)]
        uv = _project(fr.points_used, K)
        fr.pix_used = np.stack([np.clip(np.floor(uv[:, 1]).astype(int), 0, size[1] - 1),
                                np.clip(np.floor(uv[:, 0]).astype(int), 0, size[0] - 1)], axis=1)
        fr.idx, fr.offsets = np.zeros(0, np.int64), np.zeros((0, 3))
        if bm.n_joints == 55:
            for j, r in ARMS_DOWN.items():
                Qs[f, 3 * j:3 * j + 3] = r
        if init is None:
            Qs[f] = _start(fit, fr, Qs[f], up, kp_names, height_m)
        else:                                             # warm start from an earlier result
            fi = init["frames"][f]
            fr.R0 = Rotation.from_rotvec(fi["global_orient"]).as_matrix()
            Qs[f, 3:-3], Qs[f, -3:] = np.ravel(fi["body_pose"])[:3 * fit.nbj], fi["transl"]
            fr.lifted = None
    if any(fr.lifted is not None for fr in frs):          # stage 1: pose onto the keypoints, mean shape
        Qs = least_squares(fit.fun, Qs.ravel(), jac=fit.jac, method="lm", max_nfev=30).x.reshape(Qs.shape)
        refit = False
        for fr, Q in zip(frs, Qs):                        # a keypoint whose depth belongs to whatever is in
            if fr.lifted is None:                         # front of it (a forearm across the hip) is dropped
                continue
            J = bm.posed(np.zeros((1, bm.n_betas)), fit.rots(fr, Q[None]), Q[None, -3:], idx=np.zeros(0, np.int64),
                         offsets=np.zeros((0, 3)))[1][0]
            far = (np.linalg.norm(J[fit.kp_joints] - fr.lifted, axis=1) > 0.10) & (fr.lifted_w > 0)
            fr.lifted_w[far], refit = 0.0, refit or far.any()
        if refit:
            Qs = least_squares(fit.fun, Qs.ravel(), jac=fit.jac, method="lm", max_nfev=30).x.reshape(Qs.shape)
    fit.free_betas, fit.stage = True, "surface"
    x = np.r_[fit.betas_fixed if init is None else np.asarray(init["betas"], float)[:bm.n_betas], Qs.ravel()]
    if init is not None:
        beta_schedule = ((0, None),)
    history = []
    for it in range(outer):                               # stage 2: everything, correspondences re-matched
        betas, Qs = fit.split(x)
        active = [n for start, n in beta_schedule if it >= start][-1]
        active = bm.n_betas if active is None else active
        fit.beta_sd = np.where(np.arange(bm.n_betas) < active, beta_sd, 1e-3)   # coarse to fine: others held
        vr = bm.rest(betas)[0]
        fit.top, fit.bot = int(np.argmax(vr[:, 1])), int(np.argmin(vr[:, 1]))
        for fr, Q in zip(frs, Qs):
            fit.match(fr, betas, Q, 0.10 if it < 2 else 0.05, rng)
        res = least_squares(fit.fun, x, jac=fit.jac, method="lm", max_nfev=inner_nfev)
        step = float(np.abs(res.x - x).max())
        x = res.x
        history.append({"iteration": it, "cost": float(res.cost), "max_step": step})
        c = [h["cost"] for h in history]
        if it >= max(start for start, _ in beta_schedule) + 2 and c[-3] - c[-1] < tol * c[-1]:
            break                                         # converged: under tol relative decrease in 2 iterations
    betas, Qs = fit.split(x)
    vr, Jr = bm.rest(betas)
    h, vol, mass, bmi = body_measures(vr, bm.faces)
    out_frames = []
    for fr, Q in zip(frs, Qs):
        stats = fit.match(fr, betas, Q, 0.05, rng)
        R = fit.rots(fr, Q[None])
        J = bm.posed(betas[None], R, Q[None, -3:], idx=np.zeros(0, np.int64), offsets=np.zeros((0, 3)))[1][0]
        ok = fr.kp_w > 0
        stats["keypoint_rms_px"] = float(np.sqrt(np.mean((_project(J[kp_joints], K) - fr.kp_uv)[ok] ** 2))) if ok.any() else None
        out_frames.append({"global_orient": Rotation.from_matrix(R[0, 0]).as_rotvec().tolist(),
                           "body_pose": Q[3:3 + 3 * fit.nbj].reshape(-1, 3).tolist(), "transl": Q[-3:].tolist(),
                           "joints": J.tolist(), "residuals": stats})
    warnings = []
    if np.abs(betas).max() > 4.0:
        warnings.append(f"a shape parameter at {np.abs(betas).max():.1f} SD: the shape may stand in for a wrong pose")
    for k, f in enumerate(out_frames):
        if f["residuals"]["fraction_line_of_sight"] < 0.9:
            warnings.append(f"frame {k}: {f['residuals']['fraction_line_of_sight']:.0%} of the depth points lie on the "
                            "model along their line of sight: pose or segmentation wrong?")
    if len(history) == outer:
        warnings.append(f"not converged in {outer} outer iterations")
    out = {"betas": betas.tolist(), "height_m": h, "volume_m3": vol, "mass_kg": mass, "bmi": bmi,
           "rest_joints": Jr.tolist(), "frames": out_frames,
           "fit": {"outer_iterations": len(history), "runtime_s": round(time.time() - t_start, 2), "history": history,
                   "height_given_m": height_m, "frames": len(frs), "warnings": warnings},
           "tier": "B", "joints_note": "SMPL-X joints, regressed from the fitted surface: not anatomical joint centres"}
    if bm.n_joints == 55:
        out["segment_lengths_m"] = segment_lengths(Jr)
        out["surface_to_centre_m"] = front_offsets(vr, Jr, bm.faces)
    return out
