"""Kinect v1 RGB-D front end: a KinectCapture recording + MediaPipe on its colour frames -> metric 3D keypoints.

Record on Windows with ``pipeline/capture/kinect_v1`` (Kinect for Windows SDK 1.8; ``docs/kinect-v1.md``), then

    python adapters/mediapipe_pose.py REC/colour/%06d.jpg --model pose_landmarker_heavy.task --out REC/mediapipe.npz
    python -m rehabtwin kinect REC REC/mediapipe.npz seq.npz --height-m 1.80

and ``augment`` / ``process`` as for any MediaPipe sequence.

Each keypoint is lifted with the depth registered to its colour pixel: the nearest surface in a small window
(floor pixels excluded), back-projected with the colour camera's nominal intrinsics, then moved along the
viewing ray by the distance from skin to joint centre (``surface_to_centre``: from height and BMI, fitted on
BEDLAM2 bodies).
Heels, toes and hand points are placed from the lifted ankle or wrist with MediaPipe's own offset
(``RELATIVE_TO``): from the front the heel is behind the foot, where the sensor cannot see. A keypoint whose depth
disagrees with MediaPipe's own 3D pose by more than ``max_inconsistency_m`` is left NaN, not guessed: the
depth there belongs to whatever is in front of the joint (a forearm across the hip). Gravity comes from a
floor plane fitted to the depth (RANSAC), cross-checked against the SDK's floor plane. Mirroring is decided
by comparing MediaPipe's left/right labels with the SDK skeleton's in the same image.

What it does not do: calibrate this unit (the nominal 531.15 px focal length; a few % focal error scales
lateral positions by the same few %), or see a joint the sensor cannot see. The surface-to-centre distances
come from unclothed SMPL-X bodies in a standing rest pose; clothing and deep flexion change them, which a
validation against another system measures.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from .mediapipe_front import POSE2SIM_MEDIAPIPE, unmirror_raw
from .sequence import MarkerSequence

FORMAT = "rehabtwin-kinect-v1/1"
W, H = 640, 480
SDK_JOINTS = ["HipCenter", "Spine", "ShoulderCenter", "Head", "ShoulderLeft", "ElbowLeft", "WristLeft", "HandLeft",
              "ShoulderRight", "ElbowRight", "WristRight", "HandRight", "HipLeft", "KneeLeft", "AnkleLeft", "FootLeft",
              "HipRight", "KneeRight", "AnkleRight", "FootRight"]
JOINT_STATES = {"NotTracked": 0, "Inferred": 1, "Tracked": 2}

# Skin to joint centre along the line of sight from the front: height * (a + b * (BMI - BMI_REF)). Fitted on
# 1,526 BEDLAM2 SMPL-X bodies (1.44-1.99 m, BMI 17.7-43.2; rest pose, minimal clothing; adapters/bedlam2.py
# offsets): residual SD <= 0.32 cm. Height alone left the hip 1.6 cm SD off, and up to 5.5 cm short above
# BMI 30. SMPL-X joints stand in for MediaPipe's keypoints; clothing adds to the distance. Face landmarks lie
# on the skin.
SURFACE_TO_CENTRE = {
    "Nose": (0.0, 0.0), "LEye": (0.0, 0.0), "REye": (0.0, 0.0),
    "LShoulder": (0.0251, 0.00057), "RShoulder": (0.0251, 0.00057), "LElbow": (0.0187, 0.00029),
    "RElbow": (0.0187, 0.00029), "LWrist": (0.0173, 0.00013), "RWrist": (0.0173, 0.00013),
    "LHip": (0.0659, 0.00169), "RHip": (0.0659, 0.00169), "LKnee": (0.0368, 0.00019), "RKnee": (0.0368, 0.00019),
    "LAnkle": (0.0230, 0.00015), "RAnkle": (0.0230, 0.00015),
}
BMI_REF = 25.0
# Not lifted: placed from the lifted ankle/wrist with MediaPipe's own 3D offset. From the front the heel is
# hidden behind the foot, so the depth at its pixel belongs to the foot's front; hand points are smaller
# than the depth's resolution at 2-3 m.
RELATIVE_TO = {"LHeel": "LAnkle", "RHeel": "RAnkle", "LBigToe": "LAnkle", "RBigToe": "RAnkle",
               "LPinky": "LWrist", "RPinky": "RWrist", "LIndex": "LWrist", "RIndex": "RWrist",
               "LThumb": "LWrist", "RThumb": "RWrist"}
DEFAULT_HEIGHT_M = 1.70


# The person's anatomy as a check on depth: a keypoint must lie at its segment's length from the segment's
# other end. In a deep squat seen from the front the thigh hides the hip, and depth puts the hip on the
# thigh: on BEDLAM2 squats only 64% of deep-squat hips were within 3 cm, and 24% were 3-20 cm off, too
# little for the 0.2 m pose check. The knee stays reliable (96%). Such a hip is placed on its own line of
# sight at thigh length from the knee. Keypoint -> the keypoint it is checked against.
SEGMENTS = {"LHip": "LKnee", "RHip": "RKnee"}
SEGMENT_TOL_M = 0.04


def surface_to_centre(name, height_m, bmi=None):
    """Skin-to-joint-centre distance (m) of keypoint ``name`` seen from the front (BMI_REF when unknown)."""
    a, b = SURFACE_TO_CENTRE[name]
    return height_m * (a + b * ((BMI_REF if bmi is None else bmi) - BMI_REF))
# MediaPipe BlazePose index -> SDK joint of the same anatomical side (for the mirroring check)
MIRROR_PAIRS = {11: "ShoulderLeft", 12: "ShoulderRight", 13: "ElbowLeft", 14: "ElbowRight", 15: "WristLeft",
                16: "WristRight", 23: "HipLeft", 24: "HipRight", 25: "KneeLeft", 26: "KneeRight",
                27: "AnkleLeft", 28: "AnkleRight"}


def intrinsics(meta):
    """(fx, fy, cx, cy) of the colour camera from a capture's meta (nominal unless calibrated)."""
    c = meta["colour"]
    return float(c["focal_px"]), float(c.get("focal_px_y", c["focal_px"])), float(c["cx"]), float(c["cy"])


def read_capture(rec_dir):
    """A KinectCapture recording as arrays (depth stays memory-mapped). Refuses another format or truncated files."""
    d = Path(rec_dir)
    meta = json.loads((d / "meta.json").read_text())
    if meta.get("format") != FORMAT:
        raise ValueError(f"{d}: format {meta.get('format')!r}, expected {FORMAT!r} (KinectCapture output)")
    frames = np.genfromtxt(d / "frames.csv", delimiter=",", names=True, dtype=float, ndmin=1)
    T = len(frames)
    if T == 0:
        raise ValueError(f"{d}: no recorded frames")
    out = {"dir": str(d), "meta": meta, "frames": frames, "T": T,
           "colour_pattern": str(d / "colour" / "%06d.jpg")}
    for key, name in (("depth", "depth_registered.u16"), ("depth_raw", "depth_raw.u16")):
        size = (d / name).stat().st_size
        if size != T * H * W * 2:
            raise ValueError(f"{d / name}: {size} bytes, expected {T} frames x {H}x{W} uint16 (truncated recording?)")
        out[key] = np.memmap(d / name, dtype="<u2", mode="r", shape=(T, H, W))
    xyz = np.full((T, len(SDK_JOINTS), 3), np.nan)
    uv = np.full((T, len(SDK_JOINTS), 2), np.nan)
    state = np.zeros((T, len(SDK_JOINTS)), int)
    sk = d / "skeleton.csv"
    if sk.exists():
        for line in sk.read_text().splitlines()[1:]:
            f, joint, st, x, y, z, u, v = line.split(",")
            i, j = int(f), SDK_JOINTS.index(joint)
            xyz[i, j], uv[i, j], state[i, j] = (float(x), float(y), float(z)), (float(u), float(v)), JOINT_STATES[st]
    out["skeleton"] = {"xyz": xyz, "uv": uv, "state": state}
    return out


def back_project(u, v, z, fx, fy, cx, cy):
    """Pixel (continuous coordinates) + depth (m) -> OpenCV camera point (x right, y down, z forward)."""
    return np.stack([(np.asarray(u) - cx) / fx * z, (np.asarray(v) - cy) / fy * z, np.asarray(z, float)], axis=-1)


def sample_depth(depth_mm, u, v, radius_px=4, min_pixels=5, foreground_mm=150.0, floor=None, K=None,
                 floor_clear_m=0.01):
    """Depth (m) of the nearest surface around (u, v), or NaN. The window straddles limb edges, so only
    values within ``foreground_mm`` of its near end count (the background behind a knee is not the knee).
    ``floor`` (up (3,), offset: up . p = offset on the floor, camera coordinates) drops floor pixels: near
    the feet the floor in front of them is nearer than the ankle and would otherwise win."""
    if not (np.isfinite(u) and np.isfinite(v)):
        return np.nan
    j, i = int(np.floor(u)), int(np.floor(v))
    i0, j0 = max(0, i - radius_px), max(0, j - radius_px)
    win = depth_mm[i0:i + radius_px + 1, j0:j + radius_px + 1].astype(float)
    keep = win > 0
    if floor is not None and keep.any():
        vv, uu = np.mgrid[i0:i0 + win.shape[0], j0:j0 + win.shape[1]] + 0.5
        pts = back_project(uu, vv, win / 1000.0, *K)
        keep &= pts @ floor[0] - floor[1] > floor_clear_m
    vals = win[keep]
    if len(vals) < min_pixels:
        return np.nan
    near = np.percentile(vals, 10)
    return float(np.median(vals[vals <= near + foreground_mm])) / 1000.0


def lift_frame(uv, visibility, world, depth_mm, K, offsets_m, min_visibility=0.5, max_inconsistency_m=0.20,
               floor=None, relative=()):
    """(points (N,3) m, source (N,)) for one frame: 1 = lifted from depth, 2 = depth inconsistent with the
    pose (occluded, left NaN), 3 = placed from its parent (``relative``: (child, parent) indices) with
    MediaPipe's 3D offset, 0 = not visible or no depth there (4, placed by segment length, is set later by
    ``constrain_segments``). ``floor``: see ``sample_depth``."""
    fx, fy, cx, cy = K
    N = len(uv)
    P = np.full((N, 3), np.nan)
    src = np.zeros(N, int)
    children = {c for c, _ in relative}
    for k in range(N):
        if visibility[k] < min_visibility or k in children:
            continue
        z = sample_depth(depth_mm, uv[k, 0], uv[k, 1], floor=floor, K=K)
        if not np.isfinite(z):
            continue
        s = back_project(uv[k, 0], uv[k, 1], z, fx, fy, cx, cy)
        P[k] = s + offsets_m[k] * s / np.linalg.norm(s)
        src[k] = 1
    # MediaPipe's world pose is hip-centred with camera-aligned axes: one translation puts it on the lifted
    # points, so a point far from it got its depth from something else. Fit, drop outliers, fit again.
    ok = (src == 1) & np.isfinite(world).all(axis=1)
    for _ in range(2):
        if ok.sum() < 4:
            break
        t = np.median(P[ok] - world[ok], axis=0)
        res = np.linalg.norm(P - (world + t), axis=1)
        ok = (src == 1) & np.isfinite(res) & (res <= max_inconsistency_m)
    if (src == 1).sum() >= 4 and ok.sum() >= 4:
        bad = (src == 1) & ~ok & np.isfinite(world).all(axis=1)
        P[bad], src[bad] = np.nan, 2
    for c, par in relative:
        if src[par] == 1 and visibility[c] >= min_visibility and np.isfinite(world[[c, par]]).all():
            P[c], src[c] = P[par] + world[c] - world[par], 3
    return P, src


def segment_lengths(markers, source, names, min_frames=10, side_on_deg=60.0):
    """{"LHip-LKnee": {...}} per SEGMENTS pair: the median length over frames where both ends were lifted from
    depth and the segment is seen side-on (at least ``side_on_deg`` to the line of sight), so neither end can
    hide behind the other. Pairs with fewer than ``min_frames`` such frames are left out."""
    out = {}
    for c, a in SEGMENTS.items():
        i, j = names.index(c), names.index(a)
        seg = markers[:, i] - markers[:, j]
        mid = (markers[:, i] + markers[:, j]) / 2
        with np.errstate(invalid="ignore"):
            cos = np.abs(np.einsum("ij,ij->i", seg, mid)) / (np.linalg.norm(seg, axis=1) * np.linalg.norm(mid, axis=1))
            ok = (source[:, i] == 1) & (source[:, j] == 1) & (cos <= np.cos(np.radians(side_on_deg)))
        if ok.sum() >= min_frames:
            out[f"{c}-{a}"] = {"length_m": round(float(np.median(np.linalg.norm(seg[ok], axis=1))), 4),
                               "frames": int(ok.sum()), "source": f"measured in side-on frames (>= {side_on_deg:g} deg)"}
    return out


def place_on_ray(u, v, anchor, length, predicted, K):
    """Point on the line of sight through pixel (u, v) at ``length`` from ``anchor`` (camera coordinates).
    Of the two such points, the one nearer ``predicted`` (the farther one if that is unknown). When the line
    passes farther than ``length`` from the anchor, its closest approach."""
    d = back_project(u, v, 1.0, *K)
    d = d / np.linalg.norm(d)
    b = float(d @ anchor)
    disc = b * b - float(anchor @ anchor) + length ** 2
    if disc < 0:
        return b * d
    roots = (b - np.sqrt(disc), b + np.sqrt(disc))
    if np.isfinite(predicted).all():
        t = min(roots, key=lambda r: abs(r - float(d @ predicted)))
    else:
        t = roots[1]
    return t * d


def constrain_segments(markers, source, uv, visibility, world, K, lengths, names, tol_m=SEGMENT_TOL_M,
                       min_visibility=0.5):
    """Re-place, in place, every SEGMENTS keypoint whose distance to its reliable anchor is off its length by
    more than ``tol_m`` (or that got no depth): on its own line of sight at that length (``place_on_ray``),
    choosing the side MediaPipe's pose predicts. Marks them source 4; returns frames re-placed per keypoint."""
    placed = {}
    for c, a in SEGMENTS.items():
        key = f"{c}-{a}"
        if key not in lengths:
            continue
        i, j = names.index(c), names.index(a)
        L = lengths[key]["length_m"]
        for t in range(len(markers)):
            if source[t, j] != 1 or visibility[t, i] < min_visibility or not np.isfinite(uv[t, i]).all():
                continue
            if source[t, i] == 1 and abs(np.linalg.norm(markers[t, i] - markers[t, j]) - L) <= tol_m:
                continue
            pred = markers[t, j] + world[t, i] - world[t, j]
            markers[t, i] = place_on_ray(uv[t, i, 0], uv[t, i, 1], markers[t, j], L, pred, K)
            source[t, i] = 4
            placed[c] = placed.get(c, 0) + 1
    return placed


def floor_up(depth_mm, K, rng, stride=4, iters=200, tol_m=0.02, min_inlier_frac=0.15):
    """Up direction (OpenCV camera coordinates) of the floor plane in the lower image, or None."""
    fx, fy, cx, cy = K
    vv, uu = np.mgrid[int(H * 0.55):H:stride, 0:W:stride]
    z = depth_mm[vv, uu].astype(float) / 1000.0
    m = z > 0
    if m.sum() < 200:
        return None
    pts = back_project(uu[m] + 0.5, vv[m] + 0.5, z[m], fx, fy, cx, cy)
    best, best_n = None, 0
    for _ in range(iters):
        a, b, c = pts[rng.choice(len(pts), 3, replace=False)]
        n = np.cross(b - a, c - a)
        if np.linalg.norm(n) < 1e-9:
            continue
        n /= np.linalg.norm(n)
        if abs(n[1]) < np.cos(np.radians(45)):       # a floor seen by a roughly level camera, not a wall
            continue
        inl = np.abs((pts - a) @ n) < tol_m
        if inl.sum() > best_n:
            best, best_n = inl, inl.sum()
    if best is None or best_n < min_inlier_frac * len(pts):
        return None
    q = pts[best]                                     # least-squares refit on the inliers
    n = np.linalg.svd(q - q.mean(axis=0), full_matrices=False)[2][-1]     # not the (N, N) U of a full SVD
    n = -n if n[1] > 0 else n                         # up points to camera -y
    return {"up_cv": n, "offset_m": float(q.mean(axis=0) @ n), "inlier_fraction": round(float(best_n / len(pts)), 3),
            "camera_height_m": round(float(abs(q.mean(axis=0) @ n)), 3)}


def sdk_floor_up_cv(frames):
    """The SDK's floor plane normal (skeleton space: x left, y up, z out) in OpenCV camera coordinates, or None."""
    abc = np.stack([frames["floor_a"], frames["floor_b"], frames["floor_c"]], axis=1)
    abc = abc[np.isfinite(abc).all(axis=1) & (np.abs(abc[:, 1]) > 0.1)]
    if not len(abc):
        return None
    n = np.median(abc, axis=0) * [-1.0, -1.0, 1.0]
    return n / np.linalg.norm(n)


def angle_deg(a, b):
    return float(np.degrees(np.arccos(np.clip(np.dot(a, b) / np.linalg.norm(a) / np.linalg.norm(b), -1, 1))))


def mirror_vote(raw, skeleton, min_visibility=0.5, decisive=0.8):
    """Does MediaPipe label sides like the SDK skeleton (whose labels are anatomical)? A mirrored colour
    stream makes MediaPipe call the person's right side 'left' while the SDK still says right."""
    xy, vis = np.asarray(raw["image_xy"], float), np.asarray(raw["visibility"], float)
    same = swapped = 0
    lr = [(11, 12), (13, 14), (15, 16), (23, 24), (25, 26), (27, 28)]
    for t in range(min(len(xy), len(skeleton["uv"]))):
        d_same = d_swap = 0.0
        n = 0
        for a, b in lr:
            ja, jb = SDK_JOINTS.index(MIRROR_PAIRS[a]), SDK_JOINTS.index(MIRROR_PAIRS[b])
            if min(vis[t, a], vis[t, b]) < min_visibility or min(skeleton["state"][t, ja], skeleton["state"][t, jb]) < 2:
                continue
            ua, ub = skeleton["uv"][t, ja], skeleton["uv"][t, jb]
            d_same += np.linalg.norm(xy[t, a] - ua) + np.linalg.norm(xy[t, b] - ub)
            d_swap += np.linalg.norm(xy[t, a] - ub) + np.linalg.norm(xy[t, b] - ua)
            n += 1
        if n >= 2 and abs(d_same - d_swap) > 10.0 * n:      # sideways views (both sides at one spot) do not vote
            same += d_same < d_swap
            swapped += d_swap < d_same
    total = same + swapped
    decision = ("undecided" if total < 10 else "not-mirrored" if same >= decisive * total
                else "mirrored" if swapped >= decisive * total else "undecided")
    return {"decision": decision, "frames_same": int(same), "frames_swapped": int(swapped)}


def rgbd_sequence(capture, raw, height_m=None, mirrored="auto", min_visibility=0.5, max_inconsistency_m=0.20,
                  meta=None, seed=0, mass_kg=None, segment_lengths_m=None):
    """MarkerSequence (frame 'opencv_camera', metres) of the 25 Pose2Sim keypoints from a capture + MediaPipe dump.

    ``mirrored``: 'auto' (decide from the SDK skeleton, refuse when it cannot), True or False.
    ``height_m`` and ``mass_kg`` set the skin-to-joint-centre distances (``surface_to_centre``).
    ``segment_lengths_m``: known lengths for SEGMENTS pairs ({"LHip-LKnee": 0.43}, e.g. the person's model);
    pairs not given are measured from this recording's side-on frames.
    """
    T = capture["T"]
    if len(raw["image_xy"]) != T:
        raise ValueError(f"MediaPipe dump has {len(raw['image_xy'])} frames, the recording {T}: run the adapter "
                         f"on {capture['colour_pattern']}")
    if tuple(int(v) for v in np.ravel(raw["size"])) != (W, H):
        raise ValueError(f"MediaPipe dump is {tuple(np.ravel(raw['size']))}, Kinect colour is {(W, H)}")
    vote = mirror_vote(raw, capture["skeleton"], min_visibility)
    if mirrored == "auto":
        if vote["decision"] == "undecided":
            raise ValueError(f"cannot tell whether the colour stream is mirrored ({vote}): face the sensor for part "
                             "of the recording, or pass mirrored=True/False (--mirrored / --not-mirrored)")
        mirrored = vote["decision"] == "mirrored"
    if mirrored:
        raw = unmirror_raw(raw)
    K = intrinsics(capture["meta"])
    height = float(height_m) if height_m else DEFAULT_HEIGHT_M
    bmi = float(mass_kg) / height ** 2 if mass_kg and height_m else None
    names = list(POSE2SIM_MEDIAPIPE)
    idx = [POSE2SIM_MEDIAPIPE[n] for n in names]
    offsets = np.array([surface_to_centre(n, height, bmi) if n in SURFACE_TO_CENTRE else 0.0 for n in names])
    relative = [(names.index(c), names.index(p)) for c, p in RELATIVE_TO.items()]
    uv = np.asarray(raw["image_xy"], float)[:, idx]
    vis = np.asarray(raw["visibility"], float)[:, idx]
    world = np.asarray(raw["world"], float)[:, idx]
    detected = np.asarray(raw.get("detected", np.isfinite(uv).all(axis=(1, 2))), bool)

    def depth(t):
        img = np.asarray(capture["depth"][t])
        return img[:, ::-1] if mirrored else img

    rng = np.random.default_rng(seed)
    fits = [f for f in (floor_up(depth(t), K, rng) for t in np.linspace(0, T - 1, min(T, 10)).astype(int)) if f]
    floor = None
    if fits:
        up = np.median([f["up_cv"] for f in fits], axis=0)
        floor = (up / np.linalg.norm(up), float(np.median([f["offset_m"] for f in fits])))

    markers = np.full((T, len(names), 3), np.nan)
    source = np.zeros((T, len(names)), int)
    for t in range(T):
        if detected[t]:
            markers[t], source[t] = lift_frame(uv[t], vis[t], world[t], depth(t), K, offsets, min_visibility,
                                               max_inconsistency_m, floor, relative)
    lengths = segment_lengths(markers, source, names)
    for key, length in (segment_lengths_m or {}).items():
        if key not in {f"{c}-{a}" for c, a in SEGMENTS.items()}:
            raise ValueError(f"segment {key!r} is not one of {sorted(f'{c}-{a}' for c, a in SEGMENTS.items())}")
        lengths[key] = {"length_m": float(length), "source": "given (the person's model)"}
    placed = constrain_segments(markers, source, uv, vis, world, K, lengths, names, min_visibility=min_visibility)
    valid = detected & (np.isfinite(markers).all(axis=2).sum(axis=1) >= 12)
    m = {"source": "Kinect v1 RGB-D + MediaPipe Pose (keypoints lifted with registered depth)", "metric_scale": True,
         "intrinsics_source": capture["meta"]["colour"].get("intrinsics_source", "unspecified"),
         "focal_px": K[0], "tier": "C", "default_config": "mediapipe33_pose2sim", "min_visibility": min_visibility,
         "camera_facing": "front", "mirrored": bool(mirrored),
         "kinect": {"recording": capture["dir"], "sensor_id": capture["meta"].get("sensor_id"),
                    "sensor_frames_missed": capture["meta"].get("sensor_frames_missed"),
                    "mirror_check": vote, "height_m_for_offsets": height,
                    "height_source": "argument" if height_m else f"default {DEFAULT_HEIGHT_M} m (pass --height-m)",
                    "bmi_for_offsets": round(bmi, 1) if bmi else None,
                    "bmi_source": "--mass-kg / --height-m^2" if bmi else f"assumed {BMI_REF:g} (pass --mass-kg and --height-m)",
                    "surface_to_centre_m": {n: round(float(o), 4) for n, o in zip(names, offsets) if n in SURFACE_TO_CENTRE},
                    "placed_relative_to": RELATIVE_TO,
                    "lifted_fraction": {n: round(float((source[:, k] == 1).mean()), 3) for k, n in enumerate(names)
                                        if n not in RELATIVE_TO},
                    "depth_inconsistent_frames": {n: int((source[:, k] == 2).sum()) for k, n in enumerate(names)
                                                  if (source[:, k] == 2).any()},
                    "max_inconsistency_m": max_inconsistency_m,
                    "segment_lengths": lengths, "segment_tolerance_m": SEGMENT_TOL_M,
                    "placed_by_segment_length_frames": placed,
                    "segments_without_length": sorted(f"{c}-{a}" for c, a in SEGMENTS.items() if f"{c}-{a}" not in lengths)}}
    if capture["meta"].get("started_at"):
        m["started_at"] = capture["meta"]["started_at"]
    if fits:
        ups = np.array([f["up_cv"] for f in fits])
        up = floor[0]
        m.update(gravity_up_cv=up.tolist(), gravity_source="floor plane fitted to Kinect depth (RANSAC)")
        m["kinect"]["floor_fit"] = {"frames": len(fits), "spread_deg": round(max(angle_deg(u, up) for u in ups), 2),
                                    "camera_height_m": float(np.median([f["camera_height_m"] for f in fits])),
                                    "inlier_fraction": float(np.median([f["inlier_fraction"] for f in fits]))}
    sdk_up = sdk_floor_up_cv(capture["frames"])      # skeleton space is not mirrored with the images: no flip
    if sdk_up is not None:
        m["kinect"]["sdk_floor_up_cv"] = sdk_up.round(4).tolist()
        if "gravity_up_cv" in m:
            m["kinect"]["sdk_floor_angle_to_depth_floor_deg"] = round(angle_deg(sdk_up, m["gravity_up_cv"]), 2)
        else:
            m.update(gravity_up_cv=sdk_up.tolist(), gravity_source="Kinect SDK floor plane")
    m.update(meta or {})
    frame_no = capture["frames"]["colour_frame_number"].astype(int)
    return MarkerSequence(fps=float(capture["meta"].get("fps", 30)), frame="opencv_camera", marker_names=names,
                          markers=markers, valid=valid, frame_index=frame_no - frame_no[0], meta=m)
