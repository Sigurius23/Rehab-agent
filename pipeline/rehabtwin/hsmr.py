"""HSMR demo output -> MarkerSequence (numpy only; the SKEL forward pass is injected).

HSMR (IsshikiHugh/HSMR, CVPR 2025) regresses SKEL pose ``q`` (46) and shape
``betas`` (10) per detected person per frame, plus a weak-perspective camera
translation for a fixed 5000 px focal length. Its ``exp/run_demo.py`` dumps a
list (one entry per frame) of dicts with ``poses``, ``betas``, ``patch_cam_t``
and ``bbx_cs`` (one row per detected person).

This module turns that dump into the pipeline's file contract:

* picks one person and follows them (no silent identity switches: a frame
  whose best candidate jumps too far is marked invalid instead);
* recomputes full-image camera translations from ``patch_cam_t``/``bbx_cs``
  with HSMR's own formula, so an image-size override applies consistently;
* runs SKEL with one shape for the whole trial (median betas) and reads the
  105 BSM skin markers (SMPL2AddBiomechanics vertex ids) and 24 SKEL joints;
* adds the q = 0 neutral pose of the same body as the static trial.

The SKEL forward pass needs the license-gated SKEL model, so it is passed in
as ``skel_forward(poses (B,46), betas (B,10)) -> (skin_verts (B,6890,3), joints (B,24,3))``.
"""
from __future__ import annotations

import numpy as np

from .sequence import MarkerSequence
from .skel_names import SKEL_JOINT_NAMES

HSMR_FOCAL_PX = 5000.0
HSMR_PATCH_PX = 256.0


def hsmr_input_size(w, h, max_w=1920, max_h=1080, kp_mod=4):
    """Image size HSMR actually ran on (replicates lib/kits/hsmr_demo.load_inputs).

    Note: HSMR passes ``(MAX_IMG_H, -1)`` / ``(-1, MAX_IMG_W)`` to a function
    whose argument is ``(width, height)``; we reproduce that behaviour exactly
    because the detection boxes live in that resized image.
    """
    def align(v):
        return int(round(v / kp_mod) * kp_mod)

    def resize(w, h, tgt_w, tgt_h):
        nw = align(w * tgt_h / h) if tgt_w == -1 else align(tgt_w)
        nh = align(h * nw / w) if tgt_h == -1 else align(tgt_h)
        return nw, nh

    if h > max_h:
        w, h = resize(w, h, max_h, -1)
    if w > max_w:
        w, h = resize(w, h, -1, max_w)
    return w, h


def full_image_cam_t(patch_cam_t, bbx_cs, img_w, img_h, focal=HSMR_FOCAL_PX, patch=HSMR_PATCH_PX):
    """Camera translation in the full image (lib/kits/hsmr_demo.visualize_full_img)."""
    patch_cam_t = np.asarray(patch_cam_t, float)
    bbx_cs = np.asarray(bbx_cs, float)
    t = patch_cam_t.copy()
    t[:, 2] = patch_cam_t[:, 2] * patch / bbx_cs[:, 2]
    t[:, 1] += (bbx_cs[:, 1] - img_h / 2) / focal * t[:, 2]
    t[:, 0] += (bbx_cs[:, 0] - img_w / 2) / focal * t[:, 2]
    return t


def select_track(frames, max_jump=0.6, start="largest"):
    """Choose one detection per frame. Returns int array (-1 = no valid choice).

    Continuity cost is the centre distance in units of box size plus the
    relative size change; a best candidate above ``max_jump`` is rejected
    (marked -1) rather than switching people silently.
    """
    choice = np.full(len(frames), -1, dtype=int)
    prev = None
    for f, fr in enumerate(frames):
        boxes = np.asarray(fr.get("bbx_cs", np.zeros((0, 3))), float).reshape(-1, 3)
        if len(boxes) == 0:
            continue
        if prev is None:
            k = int(np.argmax(boxes[:, 2])) if start == "largest" else 0
            choice[f], prev = k, boxes[k]
            continue
        cost = (np.linalg.norm(boxes[:, :2] - prev[:2], axis=1) / prev[2]
                + np.abs(np.log(boxes[:, 2] / prev[2])))
        k = int(np.argmin(cost))
        if cost[k] <= max_jump:
            choice[f], prev = k, boxes[k]
    return choice


def body_height(skin_verts_neutral):
    """Vertical extent of the neutral (q = 0) skin mesh in SKEL's y-up frame."""
    y = np.asarray(skin_verts_neutral)[:, 1]
    return float(y.max() - y.min())


def build_sequence(frames, skel_forward, fps, image_size, marker_vertex_ids: dict, gender="male",
                   height_m=None, per_frame_betas=False, max_jump=0.6, meta=None, batch=256):
    """Assemble a MarkerSequence (frame='opencv_camera') from an HSMR dump."""
    img_w, img_h = image_size
    choice = select_track(frames, max_jump=max_jump)
    T = len(frames)
    poses = np.full((T, 46), np.nan)
    betas = np.full((T, 10), np.nan)
    cam_t = np.full((T, 3), np.nan)
    for f, (fr, k) in enumerate(zip(frames, choice)):
        if k < 0:
            continue
        poses[f] = np.asarray(fr["poses"])[k]
        betas[f] = np.asarray(fr["betas"])[k]
        cam_t[f] = full_image_cam_t(np.asarray(fr["patch_cam_t"])[k:k + 1], np.asarray(fr["bbx_cs"])[k:k + 1],
                                    img_w, img_h)[0]
    valid = choice >= 0
    no_det = sum(1 for fr in frames if np.asarray(fr.get("bbx_cs", np.zeros((0, 3)))).size == 0)
    if not valid.any():
        raise ValueError("no person detected in any frame")
    beta_med = np.median(betas[valid], axis=0)
    names = list(marker_vertex_ids)
    vids = np.array([marker_vertex_ids[n] for n in names], dtype=int)

    markers = np.full((T, len(names), 3), np.nan)
    joints = np.full((T, len(SKEL_JOINT_NAMES), 3), np.nan)
    idx = np.flatnonzero(valid)
    for s in range(0, len(idx), batch):
        sl = idx[s:s + batch]
        b = betas[sl] if per_frame_betas else np.repeat(beta_med[None], len(sl), axis=0)
        verts, jts = skel_forward(poses[sl], b)
        markers[sl] = np.asarray(verts)[:, vids] + cam_t[sl, None]
        joints[sl] = np.asarray(jts) + cam_t[sl, None]
    v0, j0 = skel_forward(np.zeros((1, 46)), beta_med[None])
    static_m, static_j = np.asarray(v0)[0, vids], np.asarray(j0)[0]
    skel_h = body_height(np.asarray(v0)[0])
    scale = 1.0
    if height_m:
        # Monocular depth is ambiguous at the scale of the body; a measured
        # height fixes it. Scaling about the camera centre keeps the image fit.
        scale = float(height_m) / skel_h
        markers, joints, static_m, static_j = markers * scale, joints * scale, static_m * scale, static_j * scale
    m = {
        "source": "HSMR+SKEL",
        "skel_gender": gender,
        "intrinsics_source": f"assumed: HSMR fixed focal {HSMR_FOCAL_PX:g} px (uncalibrated)",
        "hsmr_image_size": [int(img_w), int(img_h)],
        "skel_height_m": round(skel_h, 4),
        "height_scale_applied": round(scale, 5),
        "height_source": "measured (user supplied)" if height_m else "SKEL betas from video (unvalidated)",
        "per_frame_betas": bool(per_frame_betas),
        "betas_median": beta_med.round(5).tolist(),
        "betas_sd": np.std(betas[valid], axis=0).round(5).tolist(),
        "frames_without_detection": no_det,
        "track_rejected_frames": int((~valid).sum()) - no_det,
        "tier": "C",
        "default_config": "skel105_pose2sim",
    }
    m.update(meta or {})
    return MarkerSequence(
        fps=fps, frame="opencv_camera", marker_names=names, markers=markers, valid=valid,
        joint_names=["JC_" + j for j in SKEL_JOINT_NAMES], joints=joints,
        static_markers=static_m, static_joints=static_j, skel_poses=poses, skel_betas=betas, meta=m,
    )
