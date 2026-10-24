"""Body shape from depth (rehabtwin.shape) on toy geometry: no body model files, no licensed data."""
import importlib.util
from pathlib import Path

import numpy as np
import pytest

from rehabtwin import shape

K = (531.15, 531.15, 320.0, 240.0)


def _icosphere(subdiv=3):
    t = (1 + 5 ** 0.5) / 2
    v = [(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0), (0, -1, t), (0, 1, t), (0, -1, -t), (0, 1, -t),
         (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)]
    f = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6),
         (7, 1, 8), (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1)]
    v = [np.array(p, float) / np.linalg.norm(p) for p in v]
    for _ in range(subdiv):
        mid, nf = {}, []

        def m(i, j, mid=mid):
            key = (min(i, j), max(i, j))
            if key not in mid:
                p = v[i] + v[j]
                v.append(p / np.linalg.norm(p))
                mid[key] = len(v) - 1
            return mid[key]
        for a, b, c in f:
            ab, bc, ca = m(a, b), m(b, c), m(c, a)
            nf += [(a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca)]
        f = nf
    return np.array(v), np.array(f)


def _toy_model():
    """An SMPL-X-format toy: an ellipsoid 'body' (y up, facing +z) with a root and a 'head' joint, whose three
    shape directions stretch it along x, y and z by 10% per unit, and a bump on its front so that it has a
    facing direction."""
    u, f = _icosphere(3)
    v = u * [0.25, 0.85, 0.15]
    v[:, 2] += 0.05 * np.exp(-((u[:, 1] - 0.3) ** 2 + u[:, 0] ** 2) / 0.05) * (u[:, 2] > 0)   # chest bump
    v[:, 1] += 0.9
    top = v[:, 1] > 1.45
    Jr = np.stack([np.full(len(v), 1 / len(v)), top / top.sum()])
    w1 = np.clip((v[:, 1] - 1.3) / 0.2, 0, 1)
    centre = v.mean(0)
    sd = np.zeros((len(v), 3, 3))
    for k in range(3):
        sd[:, k, k] = 0.1 * (v[:, k] - centre[k])
    return {"v_template": v, "f": f.astype(np.uint32), "shapedirs": sd, "posedirs": np.zeros((len(v), 3, 9)),
            "J_regressor": Jr, "kintree_table": np.array([[2 ** 32 - 1, 0], [0, 1]], dtype=np.int64),
            "weights": np.stack([1 - w1, w1], 1)}


def _camera_view(bm, betas, yaw, trans, rng=None):
    """Points, keypoints and floor of the toy body facing a level camera 3 m away, turned by ``yaw``."""
    R_root = shape.rodrigues(np.array([0.0, yaw, 0.0]))
    rots = np.stack([R_root, np.eye(3)])[None]
    v, J = bm.posed(np.asarray(betas)[None], rots, np.asarray(trans)[None])
    to_cam = np.diag([1.0, -1.0, -1.0])            # body y up, facing +z -> camera y down, facing the camera
    eye = np.array([0.0, 1.0, 3.0])
    vc, Jc = (v[0] - eye) @ to_cam.T, (J[0] - eye) @ to_cam.T
    depth, _ = shape.render_depth(vc, bm.faces, K)
    mm = np.where(np.isfinite(depth), np.round(depth * 1000), 0).astype(np.uint16)
    up = to_cam @ np.array([0.0, 1.0, 0.0])
    floor_y = v[0][:, 1].min()
    pts = shape.depth_points(mm, K)
    kp = np.stack([K[0] * Jc[:, 0] / Jc[:, 2] + K[2], K[1] * Jc[:, 1] / Jc[:, 2] + K[3]], 1)
    return {"points": pts, "keypoints_uv": kp, "floor": (up, floor_y - eye[1])}


def test_posing_matches_the_bedlam2_reference_skinning():
    spec = importlib.util.spec_from_file_location("bedlam2_adapter", Path(__file__).resolve().parents[1] / "adapters" / "bedlam2.py")
    b2 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(b2)
    model = _toy_model()
    model["posedirs"] = np.random.default_rng(1).normal(0, 0.01, model["posedirs"].shape)   # correctives too
    bm = shape.BodyModel(model, n_betas=3)
    betas, pose, trans = np.array([0.5, -1.0, 2.0]), np.array([0.1, 0.4, -0.2, 0.3, 0.0, 0.5]), np.array([0.1, 0.0, -0.2])
    v_ref, J_ref = b2.pose_body(model, betas, pose, trans)
    v, J = bm.posed(betas[None], shape.rodrigues(pose.reshape(2, 3))[None], trans[None])
    np.testing.assert_allclose(v[0], v_ref, atol=1e-12)
    np.testing.assert_allclose(J[0], J_ref, atol=1e-12)
    v_sub, _ = bm.posed(betas[None], shape.rodrigues(pose.reshape(2, 3))[None], trans[None], idx=np.array([3, 7]))
    np.testing.assert_allclose(v_sub[0], v_ref[[3, 7]], atol=1e-12)


def test_rendered_depth_is_the_analytic_depth_of_a_sphere():
    u, f = _icosphere(4)
    c, r = np.array([0.1, -0.05, 2.5]), 0.3
    depth, fid = shape.render_depth(u * r + c, f, K)
    fx, fy, cx, cy = K
    vv, uu = np.mgrid[0:480, 0:640] + 0.5
    d = np.stack([(uu - cx) / fx, (vv - cy) / fy, np.ones_like(uu)], -1)          # z = 1: t is the z depth
    a, b = (d ** 2).sum(-1), d @ c
    disc = b * b - a * (c @ c - r * r)
    z = np.where(disc >= 0, (b - np.sqrt(np.maximum(disc, 0))) / a, np.inf)
    both = np.isfinite(depth) & np.isfinite(z)
    # the mesh is inscribed in the sphere: never in front of it. Away from the rim (rays within 0.8 r of the
    # centre; at the rim the depth of a chord grows without bound) at most its sagitta behind, < 1 mm.
    assert (depth[both] - z[both]).min() > -1e-9
    inner = both & (np.sqrt(c @ c - b ** 2 / a) < 0.8 * r)
    assert (depth[inner] - z[inner]).max() < 1e-3 and inner.sum() > 0.5 * both.sum()
    assert abs(np.isfinite(depth).sum() / np.isfinite(z).sum() - 1) < 0.01
    assert ((fid >= 0) == np.isfinite(depth)).all()
    # a nearer triangle hides a farther one; depth is exact on a plane
    tri = np.array([[-1.0, -1.0, 2.0], [1.0, -1.0, 2.0], [0.0, 1.0, 2.0], [-1.0, -1.0, 3.0], [1.0, -1.0, 3.0], [0.0, 1.0, 3.0]])
    tri[:3, 2] += np.array([0.0, 0.2, 0.4])                                       # a slanted plane in front
    depth, fid = shape.render_depth(tri, np.array([[0, 1, 2], [3, 4, 5]]), K)
    assert set(np.unique(fid)) == {-1, 0}
    i, j = 240, 320
    p = np.array([(j + 0.5 - cx) / fx, (i + 0.5 - cy) / fy, 1.0])
    n = np.cross(tri[1] - tri[0], tri[2] - tri[0])
    assert depth[i, j] == pytest.approx((n @ tri[0]) / (n @ p), abs=1e-12)


def test_kinect_noise_grows_with_the_square_of_depth_and_drops_edges():
    rng = np.random.default_rng(0)
    for z in (2.0, 4.0):
        clean = np.full((480, 640), np.inf)
        clean[100:380, 150:490] = z
        mm = shape.kinect_v1_noise(clean, rng, edge_drop=0.0)
        inner = mm[110:370, 160:480].astype(float) / 1000.0
        assert (inner > 0).all() and (mm[np.isinf(clean)] == 0).all()
        assert inner.std() == pytest.approx(shape.KINECT_SD_COEFF * z ** 2, rel=0.03)
        assert abs(inner.mean() - z) < 3e-4
    clean = np.full((480, 640), np.inf)
    clean[100:380, 150:490] = 2.5
    edge = np.zeros((480, 640), bool)
    edge[100:380, 150:490] = True
    edge[102:378, 152:488] = False                                               # the 2 px edge band
    for p in (1.0, 0.5):
        dropped = shape.kinect_v1_noise(clean, rng, edge_drop=p) == 0
        assert not dropped[102:378, 152:488].any()
        assert dropped[edge].mean() == pytest.approx(p, abs=0.03)
    # a depth jump inside the person is an edge too (an arm in front of the trunk): 2 px on either side
    clean[200:260, 300:340] = 2.2
    dropped = shape.kinect_v1_noise(clean, rng, edge_drop=1.0) == 0
    assert dropped[198:202, 320].all() and not dropped[197, 320] and not dropped[202:258, 320].any()
    # disparity quantisation: depth comes in steps of z^2 / fb * step (about 2 cm at 2.7 m)
    clean[:] = np.inf
    clean[100:380, 150:490] = np.linspace(2.6, 2.8, 340)[None]
    levels = np.unique(shape.kinect_v1_noise(clean, rng, sd_coeff=0.0, edge_drop=0.0, disparity_step_px=0.125)[clean < 3]) / 1000.0
    np.testing.assert_allclose(np.diff(levels), levels[:-1] ** 2 / shape.KINECT_FB_PXM * 0.125, atol=1.5e-3)   # mm rounding
    # spatially correlated noise keeps the per-pixel SD
    mm = shape.kinect_v1_noise(np.where(np.isfinite(clean), 2.0, np.inf), rng, edge_drop=0.0, corr_px=3.0)
    assert mm[110:370, 160:480].std() / 1000 == pytest.approx(shape.KINECT_SD_COEFF * 4.0, rel=0.25)


def test_closest_point_on_a_triangle_matches_dense_sampling():
    rng = np.random.default_rng(3)
    a, b, c = rng.normal(size=(3, 3))
    s, t = np.meshgrid(np.linspace(0, 1, 401), np.linspace(0, 1, 401))
    ok = s + t <= 1
    dense = a + s[ok, None] * (b - a) + t[ok, None] * (c - a)
    p = rng.normal(size=(50, 3)) * 2
    q, w = shape.closest_on_triangles(p, a, b, c)
    for k in range(len(p)):
        assert np.linalg.norm(p[k] - q[k]) <= np.linalg.norm(dense - p[k], axis=1).min() + 1e-9
        assert np.linalg.norm(p[k] - q[k]) >= np.linalg.norm(dense - p[k], axis=1).min() - 5e-3
    np.testing.assert_allclose(w @ np.stack([a, b, c]), q, atol=1e-12)
    assert (w >= -1e-12).all() and np.allclose(w.sum(1), 1)


def test_fit_recovers_known_shape_from_noise_free_depth():
    bm = shape.BodyModel(_toy_model(), n_betas=3)
    true = np.array([0.8, -0.5, 0.6])
    frames = [_camera_view(bm, true, yaw, [0.05, 0.0, -0.1]) for yaw in (0.25, -0.35)]
    fit = shape.fit_shape(bm, frames, K, keypoint_joints=[0, 1], keypoint_names=["Root", "Top"],
                          depth_sd=lambda z: 0.002 + 0 * z, model_sd_m=0.001, beta_sd=10.0)
    np.testing.assert_allclose(fit["betas"], true, atol=0.03)
    h_true = shape.body_measures(bm.rest(true)[0], bm.faces)[0]
    assert fit["height_m"] == pytest.approx(h_true, abs=0.003)
    assert len(fit["frames"]) == 2 and fit["tier"] == "B" and "not anatomical" in fit["joints_note"]
    for f in fit["frames"]:
        assert f["residuals"]["rms_depth_residual_mm"] < 2.0
    # one frame and a measured height: the height term holds the stretch along y
    one = shape.fit_shape(bm, frames[:1], K, keypoint_joints=[0, 1], keypoint_names=["Root", "Top"],
                          depth_sd=lambda z: 0.002 + 0 * z, model_sd_m=0.001, beta_sd=10.0, height_m=h_true)
    assert one["height_m"] == pytest.approx(h_true, abs=0.002)
    np.testing.assert_allclose(one["betas"], true, atol=0.05)


def test_body_measures_of_a_sphere_and_segment_and_offset_helpers():
    u, f = _icosphere(4)
    h, vol, mass, bmi = shape.body_measures(u * 0.5, f)
    assert h == pytest.approx(1.0, abs=1e-9) and vol == pytest.approx(4 / 3 * np.pi * 0.125, rel=0.01)
    assert mass == pytest.approx(vol * 1000) and bmi == pytest.approx(mass)
    J = np.zeros((55, 3))
    J[1], J[4], J[7] = [0.1, 1.0, 0], [0.1, 0.55, 0], [0.1, 0.1, 0]
    J[2], J[5], J[8] = [-0.1, 1.0, 0], [-0.1, 0.5, 0], [-0.1, 0.1, 0]
    seg = shape.segment_lengths(J)
    assert seg["hip-knee"] == pytest.approx((0.45, 0.5)) and seg["knee-ankle"] == pytest.approx((0.45, 0.4))
    # front skin-to-joint distance: a joint at a sphere's centre lies one radius behind its front
    off = shape.front_offsets(u * 0.2, np.zeros((55, 3)), f)
    assert off["LHip"] == pytest.approx(0.2, abs=0.001)
