"""Kinect v1 RGB-D front end on synthetic recordings (no sensor, no SDK): a sphere-swept body over a floor."""
import json
import os
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest

from rehabtwin import kinect
from rehabtwin.mediapipe_front import POSE2SIM_MEDIAPIPE, unmirror_raw

K = (531.15, 531.15, 320.0, 240.0)
HEIGHT = 1.75
CAPTURE_DIR = Path(__file__).resolve().parents[1] / "capture" / "kinect_v1"

# keypoint centres of a 1.75 m person facing the camera, 2.8 m away, camera 1 m above the floor and level
# (OpenCV axes: x right, y down, z forward; the person's left side is image right)
LEVEL = {
    "Nose": (0.0, -0.60, 2.70), "LEye": (0.03, -0.63, 2.72), "REye": (-0.03, -0.63, 2.72),
    "LShoulder": (0.19, -0.42, 2.80), "RShoulder": (-0.19, -0.42, 2.80),
    "LElbow": (0.24, -0.15, 2.80), "RElbow": (-0.24, -0.15, 2.80),
    "LWrist": (0.26, 0.10, 2.75), "RWrist": (-0.26, 0.10, 2.75),
    "LPinky": (0.27, 0.17, 2.75), "RPinky": (-0.27, 0.17, 2.75), "LIndex": (0.26, 0.18, 2.73),
    "RIndex": (-0.26, 0.18, 2.73), "LThumb": (0.24, 0.16, 2.72), "RThumb": (-0.24, 0.16, 2.72),
    "LHip": (0.10, 0.08, 2.80), "RHip": (-0.10, 0.08, 2.80), "LKnee": (0.11, 0.52, 2.78), "RKnee": (-0.11, 0.52, 2.78),
    "LAnkle": (0.12, 0.92, 2.82), "RAnkle": (-0.12, 0.92, 2.82),
    "LHeel": (0.12, 0.97, 2.87), "RHeel": (-0.12, 0.97, 2.87), "LBigToe": (0.14, 0.985, 2.66), "RBigToe": (-0.14, 0.985, 2.66),
}
BONES = [("LShoulder", "LElbow"), ("LElbow", "LWrist"), ("RShoulder", "RElbow"), ("RElbow", "RWrist"),
         ("LHip", "LKnee"), ("LKnee", "LAnkle"), ("RHip", "RKnee"), ("RKnee", "RAnkle")]
LIMB = ["LShoulder", "RShoulder", "LElbow", "RElbow", "LWrist", "RWrist", "LHip", "RHip", "LKnee", "RKnee",
        "LAnkle", "RAnkle"]
SDK_OF = {"LShoulder": "ShoulderLeft", "RShoulder": "ShoulderRight", "LElbow": "ElbowLeft", "RElbow": "ElbowRight",
          "LWrist": "WristLeft", "RWrist": "WristRight", "LHip": "HipLeft", "RHip": "HipRight",
          "LKnee": "KneeLeft", "RKnee": "KneeRight", "LAnkle": "AnkleLeft", "RAnkle": "AnkleRight"}


def _rot_x(deg):
    a = np.radians(deg)
    return np.array([[1, 0, 0], [0, np.cos(a), -np.sin(a)], [0, np.sin(a), np.cos(a)]])


def _radius(name):
    """Sphere radius of a keypoint: its skin-to-centre distance at BMI 25 (hands and feet: 2.5 cm)."""
    return kinect.surface_to_centre(name, HEIGHT) if name in kinect.SURFACE_TO_CENTRE else 0.014 * HEIGHT


def _spheres(joints):
    """Each keypoint a sphere of its skin-to-centre radius (so lifting should land on its centre), bones as
    chains of spheres, a head and a trunk."""
    out = [(np.asarray(joints[n]), _radius(n)) for n in joints if _radius(n) > 0]
    for a, b in BONES:
        ra, rb = (_radius(n) for n in (a, b))
        for s in np.linspace(0.15, 0.85, 8):
            out.append(((1 - s) * np.asarray(joints[a]) + s * np.asarray(joints[b]), (1 - s) * ra + s * rb))
    sh = (np.asarray(joints["LShoulder"]) + joints["RShoulder"]) / 2
    hp = (np.asarray(joints["LHip"]) + joints["RHip"]) / 2
    for s in np.linspace(0.1, 0.65, 6):                        # trunk ends well above the hip joints
        out.append(((1 - s) * sh + s * hp + [0, 0, 0.04], 0.11))
    out.append((np.asarray(joints["Nose"]) + [0, -0.02, 0.11], 0.11))   # head, its front at the nose
    return out


def _render(spheres, planes, w=640, h=480):
    """Depth (mm) seen from the origin: spheres [(centre, r)] and planes [(n, d): n.x = d]."""
    fx, fy, cx, cy = K
    vv, uu = np.mgrid[0:h, 0:w] + 0.5
    rays = np.stack([(uu - cx) / fx, (vv - cy) / fy, np.ones_like(uu)], axis=-1)     # z = 1: t is the z depth
    a = (rays ** 2).sum(-1)
    z = np.full((h, w), np.inf)
    for c, r in spheres:
        b = rays @ c
        disc = b * b - a * (c @ c - r * r)
        t = (b - np.sqrt(np.maximum(disc, 0))) / a
        z = np.where((disc >= 0) & (t > 0) & (t < z), t, z)
    for n, d in planes:
        den = rays @ np.asarray(n, float)
        t = np.where(np.abs(den) > 1e-9, d / np.where(den == 0, 1, den), np.inf)
        z = np.where((t > 0) & (t < z), t, z)
    return np.where(np.isfinite(z), np.round(z * 1000), 0).astype(np.uint16)


def _project(p):
    fx, fy, cx, cy = K
    return np.array([fx * p[0] / p[2] + cx, fy * p[1] / p[2] + cy])


_DEPTH = {}


def _squat_pose():
    """LEVEL in a deep squat with both thighs pointing at the camera (thigh lengths kept)."""
    level = {n: np.asarray(p, float) for n, p in LEVEL.items()}
    out = dict(level)
    for side in "LR":
        hip, knee = level[f"{side}Hip"], level[f"{side}Knee"]
        k = np.array([knee[0], 0.55, 2.45])
        back = np.array([0.0, -0.12, 1.0])
        out[f"{side}Knee"], out[f"{side}Hip"] = k, k + np.linalg.norm(hip - knee) * back / np.linalg.norm(back)
    shift = (out["LHip"] + out["RHip"]) / 2 - (level["LHip"] + level["RHip"]) / 2
    for n, p in level.items():                                 # trunk, arms and head go down with the hips
        if not any(n.endswith(x) for x in ("Hip", "Knee", "Ankle", "Heel", "BigToe")):
            out[n] = p + shift
    return out


def _scene(tilt_deg=8.0, occlude_right_hip=False, seed=0, squat=False):
    """(registered depth, MediaPipe-like raw frame dicts, SDK skeleton uv/state, true joints) for one frame."""
    R = _rot_x(tilt_deg)
    level = _squat_pose() if squat else {n: np.asarray(p, float) for n, p in LEVEL.items()}
    if occlude_right_hip:                    # right forearm across the hip, its wrist on the hip's line of sight
        h = level["RHip"]
        level["RWrist"] = h * (1 - 0.35 / np.linalg.norm(h))
        level["RElbow"] = level["RWrist"] + [-0.12, -0.2, 0.05]
        for n, d in (("RPinky", [0.05, 0.05, 0]), ("RIndex", [0.06, 0.05, -0.01]), ("RThumb", [0.03, 0.04, -0.02])):
            level[n] = level["RWrist"] + d
    joints = {n: R @ p for n, p in level.items()}
    floor_n = R @ np.array([0.0, 1.0, 0.0])                     # floor: level y = +1 m
    wall_n = R @ np.array([0.0, 0.0, 1.0])                      # back wall: level z = 4.5 m
    key = (tilt_deg, occlude_right_hip, squat)                  # a static pose: render each one once
    if key not in _DEPTH:
        _DEPTH[key] = _render(_spheres(joints), [(floor_n, 1.0), (wall_n, 4.5)])
    depth = _DEPTH[key]
    rng = np.random.default_rng(seed)
    shift = rng.normal(0, 0.05, 3)                             # MediaPipe's hip centre is not the true one
    xy = np.full((33, 2), np.nan)
    world = np.full((33, 3), np.nan)
    vis = np.zeros(33)
    hip = (joints["LHip"] + joints["RHip"]) / 2
    for n, i in POSE2SIM_MEDIAPIPE.items():
        xy[i] = _project(joints[n]) + rng.normal(0, 0.5, 2)
        world[i] = joints[n] - hip + shift + rng.normal(0, [0.01, 0.01, 0.02])   # MediaPipe depth is its weakest axis
        vis[i] = 0.99
    sk_uv = np.full((len(kinect.SDK_JOINTS), 2), np.nan)
    sk_state = np.zeros(len(kinect.SDK_JOINTS), int)
    for n, s in SDK_OF.items():
        j = kinect.SDK_JOINTS.index(s)
        sk_uv[j], sk_state[j] = np.round(_project(joints[n])), 2
    return depth, {"image_xy": xy, "world": world, "visibility": vis}, sk_uv, sk_state, joints, R


def _write_capture(d, depths, sk_uv, sk_state, frame_numbers=None, floor=(0.0, 0.0, 0.0, 0.0)):
    """A recording in KinectCapture's format (rehabtwin-kinect-v1/1), written without the C# tool."""
    d.mkdir(parents=True)
    T = len(depths)
    frame_numbers = list(range(100, 100 + T)) if frame_numbers is None else frame_numbers
    meta = {"format": kinect.FORMAT, "sensor_id": "SYNTH", "started_at": "2026-10-24T09:30:00.000Z", "fps": 30,
            "frames": T, "sensor_frames_missed": 0,
            "colour": {"width": 640, "height": 480, "focal_px": K[0], "cx": K[2], "cy": K[3],
                       "intrinsics_source": "synthetic"}}
    (d / "meta.json").write_text(json.dumps(meta))
    np.asarray(depths, "<u2").tofile(d / "depth_registered.u16")
    np.asarray(depths, "<u2").tofile(d / "depth_raw.u16")
    rows = [("frame,colour_frame_number,colour_timestamp_ms,depth_frame_number,depth_timestamp_ms,host_ms,"
             "accel_x,accel_y,accel_z,floor_a,floor_b,floor_c,floor_d,skeleton_id")]
    rows += [f"{t},{f},{33 * f},{f},{33 * f + 2},{33.3 * t},0,-1,0,{floor[0]},{floor[1]},{floor[2]},{floor[3]},1"
             for t, f in enumerate(frame_numbers)]
    (d / "frames.csv").write_text("\n".join(rows) + "\n")
    sk = ["frame,joint,state,x,y,z,u,v"]
    states = {v: k for k, v in kinect.JOINT_STATES.items()}
    for t in range(T):
        for j, name in enumerate(kinect.SDK_JOINTS):
            u, v = sk_uv[t][j]
            sk.append(f"{t},{name},{states[sk_state[t][j]]},0,0,2.8,{-1 if np.isnan(u) else int(u)},"
                      f"{-1 if np.isnan(v) else int(v)}")
    (d / "skeleton.csv").write_text("\n".join(sk) + "\n")
    return d


def _recording(tmp_path, T=12, mirrored_stream=False, occlude_from=None, squat_from=None, **kw):
    frames = [_scene(occlude_right_hip=occlude_from is not None and t >= occlude_from, seed=t,
                     squat=squat_from is not None and t >= squat_from, **kw) for t in range(T)]
    depths = np.stack([f[0] for f in frames])
    raws = [f[1] for f in frames]
    sk_uv = np.stack([f[2] for f in frames])
    sk_state = np.stack([f[3] for f in frames])
    raw = {"image_xy": np.stack([r["image_xy"] for r in raws]), "world": np.stack([r["world"] for r in raws]),
           "visibility": np.stack([r["visibility"] for r in raws]), "detected": np.ones(T, bool),
           "size": np.array([640, 480]), "fps": np.array(30.0)}
    if mirrored_stream:            # what a mirrored colour stream gives: image flipped, MediaPipe labels by appearance
        depths = depths[:, :, ::-1].copy()
        raw = unmirror_raw(raw)    # reflection is self-inverse: the true scene's dump reflected
        sk_uv = sk_uv.copy()
        sk_uv[..., 0] = 640 - sk_uv[..., 0]     # SDK labels stay anatomical, positions move with the image
    cap = kinect.read_capture(_write_capture(tmp_path / "rec", depths, sk_uv, sk_state))
    return cap, raw, frames


def test_lifted_keypoints_land_on_joint_centres_and_gravity_is_the_floor(tmp_path):
    cap, raw, frames = _recording(tmp_path)
    seq = kinect.rgbd_sequence(cap, raw, height_m=HEIGHT)
    assert seq.frame == "opencv_camera" and seq.valid.all() and not seq.meta["mirrored"]
    joints, R = frames[0][4], frames[0][5]
    for n in LIMB:
        err = np.linalg.norm(seq.markers[:, seq.marker_names.index(n)] - joints[n], axis=1)
        assert err.max() < 0.02, (n, err.max())
    for n, parent in kinect.RELATIVE_TO.items():   # lifted ankle/wrist + MediaPipe's own offset to it
        c, par = seq.marker_names.index(n), seq.marker_names.index(parent)
        mp = raw["world"][:, POSE2SIM_MEDIAPIPE[n]] - raw["world"][:, POSE2SIM_MEDIAPIPE[parent]]
        np.testing.assert_allclose(seq.markers[:, c], seq.markers[:, par] + mp, atol=1e-9)
        assert np.linalg.norm(seq.markers[:, c] - joints[n], axis=1).mean() < 0.04, n   # synthetic MediaPipe noise
    assert np.isfinite(seq.markers).all()
    up = R @ np.array([0.0, -1.0, 0.0])
    assert kinect.angle_deg(seq.meta["gravity_up_cv"], up) < 1.0
    assert seq.meta["gravity_source"].startswith("floor plane fitted to Kinect depth")
    assert abs(seq.meta["kinect"]["floor_fit"]["camera_height_m"] - 1.0) < 0.02
    assert seq.meta["started_at"] == "2026-10-24T09:30:00.000Z" and seq.meta["kinect"]["mirror_check"]["decision"] == "not-mirrored"
    # without the skin-to-centre offsets every point sits on the skin, centimetres in front of the joint
    flat = kinect.rgbd_sequence(cap, raw, height_m=1e-9)
    hip = seq.marker_names.index("LHip")
    assert np.linalg.norm(flat.markers[0, hip] - joints["LHip"]) > 0.07


def test_an_occluded_joint_is_left_empty_not_given_the_occluders_depth(tmp_path):
    cap, raw, frames = _recording(tmp_path, occlude_from=6)
    seq = kinect.rgbd_sequence(cap, raw, height_m=HEIGHT)
    r = seq.marker_names.index("RHip")
    assert np.isfinite(seq.markers[:6, r]).all() and np.isnan(seq.markers[6:, r]).all()
    assert seq.meta["kinect"]["depth_inconsistent_frames"]["RHip"] == 6
    wrist = seq.marker_names.index("RWrist")                   # the occluder itself is lifted fine
    assert np.linalg.norm(seq.markers[8, wrist] - frames[8][4]["RWrist"]) < 0.02
    assert seq.valid.all()


def test_a_mirrored_stream_is_detected_and_undone(tmp_path):
    cap, raw, frames = _recording(tmp_path, mirrored_stream=True)
    seq = kinect.rgbd_sequence(cap, raw, height_m=HEIGHT)
    assert seq.meta["mirrored"] and seq.meta["kinect"]["mirror_check"]["decision"] == "mirrored"
    joints = frames[0][4]
    for n in ("LHip", "RKnee", "LWrist"):                       # true sides and true geometry again
        assert np.linalg.norm(seq.markers[0, seq.marker_names.index(n)] - joints[n]) < 0.02, n
    with pytest.raises(ValueError, match="cannot tell whether the colour stream is mirrored"):
        no_skeleton = dict(cap, skeleton={**cap["skeleton"], "state": np.zeros_like(cap["skeleton"]["state"])})
        kinect.rgbd_sequence(no_skeleton, raw)
    assert kinect.rgbd_sequence(dict(cap, skeleton={**cap["skeleton"], "state": np.zeros_like(cap["skeleton"]["state"])}),
                                raw, mirrored=True).meta["mirrored"]


def test_capture_reader_refuses_truncated_or_foreign_recordings(tmp_path):
    cap, raw, _ = _recording(tmp_path, T=3)
    d = Path(cap["dir"])
    with pytest.raises(ValueError, match="MediaPipe dump has 2 frames"):
        kinect.rgbd_sequence(cap, {k: (v[:2] if k not in ("size", "fps") else v) for k, v in raw.items()})
    (d / "depth_registered.u16").write_bytes((d / "depth_registered.u16").read_bytes()[:-2])
    with pytest.raises(ValueError, match="truncated"):
        kinect.read_capture(d)
    meta = json.loads((d / "meta.json").read_text())
    (d / "meta.json").write_text(json.dumps({**meta, "format": "something-else"}))
    with pytest.raises(ValueError, match="format"):
        kinect.read_capture(d)


def test_kinect_cli_writes_a_sequence_the_pipeline_reads(tmp_path, capsys):
    from rehabtwin import cli
    from rehabtwin.sequence import MarkerSequence
    cap, raw, _ = _recording(tmp_path, T=12)
    np.savez(tmp_path / "mp.npz", **raw)
    assert cli.main(["kinect", cap["dir"], str(tmp_path / "mp.npz"), str(tmp_path / "seq.npz"), "--height-m", "1.75",
                     "--person-ref", "P1"]) in (None, 0)
    seq = MarkerSequence.load(tmp_path / "seq.npz")
    assert seq.meta["person_ref"] == "P1" and seq.meta["default_config"] == "mediapipe33_pose2sim"
    assert json.loads(capsys.readouterr().out)["valid"] == 12
    bad = {**raw, "image_xy": raw["image_xy"][:2], "visibility": raw["visibility"][:2], "world": raw["world"][:2],
           "detected": raw["detected"][:2]}
    np.savez(tmp_path / "bad.npz", **bad)
    assert cli.main(["kinect", cap["dir"], str(tmp_path / "bad.npz"), str(tmp_path / "x.npz")]) == 2
    assert "refused: MediaPipe dump has 2 frames" in capsys.readouterr().err


@pytest.mark.skipif(not (shutil.which("mcs") and shutil.which("mono")), reason="needs Mono (mcs + mono)")
def test_csharp_recorder_output_reads_back(tmp_path):
    """KinectCapture.cs against the SDK stub's fake sensor: the C# writer and this reader agree on the format."""
    stub, exe = tmp_path / "Microsoft.Kinect.dll", tmp_path / "KinectCapture.exe"
    for args in (["-target:library", f"-out:{stub}", str(CAPTURE_DIR / "api_stub" / "MicrosoftKinectStub.cs")],
                 ["-warnaserror+", f"-r:{stub}", "-r:System.Drawing.dll", f"-out:{exe}", str(CAPTURE_DIR / "KinectCapture.cs")]):
        subprocess.run(["mcs", "-langversion:5", *args], check=True, capture_output=True)   # C# 5: Windows' own csc
    rec = tmp_path / "rec"
    run = subprocess.run(["mono", str(exe), str(rec), "--seconds", "1.5", "--countdown", "0"], capture_output=True,
                         text=True, timeout=60, check=False, env={**os.environ, "REHABTWIN_FAKE_KINECT": "1"})
    assert run.returncode == 0, run.stderr
    cap = kinect.read_capture(rec)
    T = cap["T"]
    assert T >= 20 and cap["meta"]["frames"] == T and len(list((rec / "colour").glob("*.jpg"))) == T
    assert (rec / "colour" / "000000.jpg").read_bytes()[:2] == b"\xff\xd8"
    raw_d, reg = np.asarray(cap["depth_raw"][0]), np.asarray(cap["depth"][0])
    assert (raw_d[:, :4] == 0).all() and (raw_d[:, 4:] > 0).all()
    np.testing.assert_array_equal(reg[:, 8 + 4:], raw_d[:, 4:-8])     # the fake registers depth 8 px to the right
    assert (reg[:, :12] == 0).all()
    gaps = np.diff(cap["frames"]["colour_frame_number"])
    assert set(gaps) <= {1, 2} and 2 in gaps and cap["meta"]["sensor_frames_missed"] == int((gaps - 1).sum())
    assert (cap["skeleton"]["state"] == 2).all()
    hc = kinect.SDK_JOINTS.index("HipCenter")
    np.testing.assert_allclose(cap["skeleton"]["uv"][0, hc], [round(320 + 531.15 * 0.1 / 2.5), round(240 - 531.15 * 0.8 / 2.5)])
    assert kinect.angle_deg(kinect.sdk_floor_up_cv(cap["frames"]), [0, -0.98, -0.2]) < 0.1


def test_skin_to_centre_grows_with_bmi_and_is_recorded(tmp_path):
    lean, heavy = (kinect.surface_to_centre("LHip", 1.75, bmi) for bmi in (19.0, 38.0))
    assert heavy - lean == pytest.approx(1.75 * 0.00169 * 19, abs=1e-6) and heavy - lean > 0.05
    assert kinect.surface_to_centre("LKnee", 1.75) == pytest.approx(1.75 * 0.0368)       # BMI 25 when unknown
    assert kinect.surface_to_centre("Nose", 1.75, 40.0) == 0.0                          # face landmarks: on the skin
    cap, raw, _ = _recording(tmp_path, T=12)
    k = kinect.rgbd_sequence(cap, raw, height_m=1.75, mass_kg=95.0).meta["kinect"]
    assert k["bmi_for_offsets"] == pytest.approx(31.0, abs=0.05) and k["bmi_source"].startswith("--mass-kg")
    assert k["surface_to_centre_m"]["LHip"] == pytest.approx(kinect.surface_to_centre("LHip", 1.75, 95 / 1.75 ** 2), abs=1e-4)
    assert kinect.rgbd_sequence(cap, raw, height_m=1.75).meta["kinect"]["bmi_source"].startswith("assumed 25")


def _bedlam2_adapter():
    import importlib.util
    spec = importlib.util.spec_from_file_location("bedlam2_adapter", Path(__file__).resolve().parents[1] / "adapters" / "bedlam2.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _icosphere(r, subdiv=3):
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
    return np.array(v) * r, np.array(f)


def test_bedlam2_adapter_geometry_on_known_shapes(tmp_path):
    b2 = _bedlam2_adapter()
    v, f = _icosphere(0.5)
    h, mass, _ = b2.body_stats(v, f)
    assert h == pytest.approx(1.0, abs=1e-6) and mass == pytest.approx(4 / 3 * np.pi * 0.125 * 1000, rel=0.02)
    assert b2.first_hit(np.zeros(3), np.array([0, 0, 1.0]), v, f) == pytest.approx(0.5, abs=0.005)
    assert b2.first_hit(np.array([0, 0, 0.3]), np.array([0, 0, 1.0]), v, f) == pytest.approx(0.2, abs=0.005)
    assert b2.first_hit(np.array([0, 0, 2.0]), np.array([0, 0, 1.0]), v, f) == np.inf
    # a model file's pickled entries are skipped, never unpickled
    np.savez(tmp_path / "m.npz", v_template=v, f=f, joint2num=np.array({"pelvis": 0}, dtype=object))
    m = b2.load_smplx(tmp_path / "m.npz")
    assert set(m) == {"v_template", "f"}
    # the fit recovers offset = height * (a + b * (BMI - 25)) exactly from bodies built that way
    rows = [{"height_m": hh, "bmi": bb, **{n: hh * (0.05 + 0.002 * (bb - 25)) for n in b2.JOINTS}}
            for hh, bb in ((1.5, 19.0), (1.7, 25.0), (1.9, 31.0), (1.6, 40.0))]
    c = b2.fit(rows)["Hip"]
    assert c["a"] == pytest.approx(0.05, abs=1e-4) and c["b"] == pytest.approx(0.002, abs=1e-5) and c["residual_sd_m"] < 1e-6



def test_bedlam2_posing_and_line_of_sight_on_a_toy_body():
    b2 = _bedlam2_adapter()
    # two joints: root at the origin, child 1 m up; one vertex on each, the child's 1 m above it
    model = {"v_template": np.array([[0.0, 0, 0], [0, 2.0, 0]]), "shapedirs": np.zeros((2, 3, 1)),
             "posedirs": np.zeros((2, 3, 9)), "J_regressor": np.array([[1.0, 0], [0.5, 0.5]]),
             "kintree_table": np.array([[2 ** 32 - 1, 0], [0, 1]], dtype=np.uint32), "weights": np.array([[1.0, 0], [0, 1.0]])}
    v, J = b2.pose_body(model, [0.0], np.zeros(6), np.zeros(3))
    np.testing.assert_allclose(v, model["v_template"], atol=1e-12)
    v, J = b2.pose_body(model, [0.0], [0, 0, 0, 0, 0, np.pi / 2], [1.0, 0, 0])   # child +90 deg about z, body moved 1 m
    np.testing.assert_allclose(J, [[1, 0, 0], [1, 1, 0]], atol=1e-12)
    np.testing.assert_allclose(v, [[1, 0, 0], [0, 1, 0]], atol=1e-12)
    v, J = b2.pose_body(model, [0.0], [0, 0, np.pi / 2, 0, 0, 0], [0, 0, 0])     # root +90 deg about z: everything turns
    np.testing.assert_allclose(v, [[0, 0, 0], [-2, 0, 0]], atol=1e-12)
    # a camera 3 m in front, looking back: a sphere's centre lies one radius behind the surface it sees
    sv, sf = _icosphere(0.3)
    C, R = b2.camera(np.array([0, 0, 3.0]), np.zeros(3))
    np.testing.assert_allclose(R @ np.array([0, 0, -1.0]), [0, 0, 1], atol=1e-12)      # optical axis towards the target
    np.testing.assert_allclose(R @ np.array([0, -1.0, 0]), [0, 1, 0], atol=1e-12)      # image y down
    for target in (np.zeros(3), np.array([0.1, -0.05, 0.0])):
        dist, hit = b2.first_hit_culled(C, R, b2.KINECT_K, sv, sf, target)
        d = (target - C) / np.linalg.norm(target - C)
        assert hit == pytest.approx(b2.first_hit(C, d, sv, sf), abs=1e-9) and dist - hit > 0.25
    J = np.zeros((22, 3))
    J[1], J[2], J[4], J[5], J[7], J[8] = [0.1, 1, 0], [-0.1, 1, 0], [0.1, 0.5, 0.2], [-0.1, 0.5, 0.2], [0.1, 0, 0], [-0.1, 0, 0]
    np.testing.assert_allclose(b2.facing(J), [0, 0, 1], atol=1e-12)                   # left hip at +x: facing +z
    assert 40 < b2.knee_flexion_deg(J) < 50


def test_a_hip_hidden_behind_the_thigh_is_placed_at_thigh_length_from_the_knee(tmp_path):
    """Deep squat facing the sensor: depth at the hip's pixel is the thigh. The person's thigh length (measured
    standing, side-on) puts the hip back on its own line of sight behind the knee."""
    cap, raw, frames = _recording(tmp_path, T=16, squat_from=10)
    seq = kinect.rgbd_sequence(cap, raw, height_m=HEIGHT)
    k = seq.meta["kinect"]
    for side in "LR":
        hip, knee = seq.marker_names.index(f"{side}Hip"), seq.marker_names.index(f"{side}Knee")
        L = np.linalg.norm(frames[0][4][f"{side}Hip"] - frames[0][4][f"{side}Knee"])
        assert k["segment_lengths"][f"{side}Hip-{side}Knee"]["length_m"] == pytest.approx(L, abs=0.02)
        assert k["segment_lengths"][f"{side}Hip-{side}Knee"]["frames"] == 10           # the standing frames
        err = np.linalg.norm(seq.markers[:, hip] - np.stack([f[4][f"{side}Hip"] for f in frames]), axis=1)
        assert err[:10].max() < 0.02 and err[10:].max() < 0.03, (side, err.round(3))
        assert np.linalg.norm(seq.markers[12, knee] - frames[12][4][f"{side}Knee"]) < 0.02
        assert k["placed_by_segment_length_frames"][f"{side}Hip"] == 6
    # depth alone puts a deep-squat hip on the thigh, or drops it as inconsistent with the pose
    names = list(POSE2SIM_MEDIAPIPE)
    idx = [POSE2SIM_MEDIAPIPE[n] for n in names]
    offsets = np.array([kinect.surface_to_centre(n, HEIGHT) if n in kinect.SURFACE_TO_CENTRE else 0.0 for n in names])
    P, src = kinect.lift_frame(raw["image_xy"][12][idx], raw["visibility"][12][idx], raw["world"][12][idx],
                               np.asarray(cap["depth"][12]), K, offsets)
    lhip = names.index("LHip")
    assert src[lhip] == 2 or np.linalg.norm(P[lhip] - frames[12][4]["LHip"]) > 0.1
    given = kinect.rgbd_sequence(cap, raw, height_m=HEIGHT, segment_lengths_m={"LHip-LKnee": 0.44, "RHip-RKnee": 0.44})
    assert given.meta["kinect"]["segment_lengths"]["LHip-LKnee"]["source"].startswith("given")
    with pytest.raises(ValueError, match="not one of"):
        kinect.rgbd_sequence(cap, raw, height_m=HEIGHT, segment_lengths_m={"LKnee-LAnkle": 0.4})
    # a standing recording needs no re-placing
    cap2, raw2, _ = _recording(tmp_path / "standing", T=12)
    assert kinect.rgbd_sequence(cap2, raw2, height_m=HEIGHT).meta["kinect"]["placed_by_segment_length_frames"] == {}


def test_place_on_ray_picks_the_side_the_pose_predicts():
    K = (500.0, 500.0, 320.0, 240.0)
    knee, hip = np.array([0.1, 0.5, 2.5]), np.array([0.1, 0.45, 2.94])
    L = np.linalg.norm(hip - knee)
    uv = (K[0] * hip[0] / hip[2] + K[2], K[1] * hip[1] / hip[2] + K[3])
    np.testing.assert_allclose(kinect.place_on_ray(*uv, knee, L, hip + 0.03, K), hip, atol=1e-9)
    near = kinect.place_on_ray(*uv, knee, L, knee - [0, 0, 0.4], K)          # the pose says "in front"
    assert near[2] < knee[2] and np.linalg.norm(near - knee) == pytest.approx(L)
    far = kinect.place_on_ray(*uv, knee, L, np.full(3, np.nan), K)            # no pose: behind the anchor
    np.testing.assert_allclose(far, hip, atol=1e-9)
    miss = kinect.place_on_ray(*uv, knee, 0.01, hip, K)                        # line farther than L: closest approach
    d = hip / np.linalg.norm(hip)
    np.testing.assert_allclose(miss, (d @ knee) * d, atol=1e-9)

