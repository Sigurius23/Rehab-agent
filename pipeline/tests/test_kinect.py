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


def _spheres(joints):
    """Each keypoint a sphere of its skin-to-centre radius (so lifting should land on its centre), bones as
    chains of spheres, a head and a trunk."""
    out = [(np.asarray(joints[n]), kinect.SURFACE_TO_CENTRE.get(n, 0.014) * HEIGHT) for n in joints
           if kinect.SURFACE_TO_CENTRE.get(n, 1) > 0]
    for a, b in BONES:
        ra, rb = (kinect.SURFACE_TO_CENTRE[n] * HEIGHT for n in (a, b))
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


def _scene(tilt_deg=8.0, occlude_right_hip=False, seed=0):
    """(registered depth, MediaPipe-like raw frame dicts, SDK skeleton uv/state, true joints) for one frame."""
    R = _rot_x(tilt_deg)
    level = {n: np.asarray(p, float) for n, p in LEVEL.items()}
    if occlude_right_hip:                    # right forearm across the hip, its wrist on the hip's line of sight
        h = level["RHip"]
        level["RWrist"] = h * (1 - 0.35 / np.linalg.norm(h))
        level["RElbow"] = level["RWrist"] + [-0.12, -0.2, 0.05]
        for n, d in (("RPinky", [0.05, 0.05, 0]), ("RIndex", [0.06, 0.05, -0.01]), ("RThumb", [0.03, 0.04, -0.02])):
            level[n] = level["RWrist"] + d
    joints = {n: R @ p for n, p in level.items()}
    floor_n = R @ np.array([0.0, 1.0, 0.0])                     # floor: level y = +1 m
    wall_n = R @ np.array([0.0, 0.0, 1.0])                      # back wall: level z = 4.5 m
    key = (tilt_deg, occlude_right_hip)                         # a static pose: render each one once
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


def _recording(tmp_path, T=12, mirrored_stream=False, occlude_from=None, **kw):
    frames = [_scene(occlude_right_hip=occlude_from is not None and t >= occlude_from, seed=t, **kw) for t in range(T)]
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
