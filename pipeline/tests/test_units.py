"""Fast unit tests (numpy/scipy only). Run: python -m pytest pipeline/tests -q"""
import time

import numpy as np
import pytest

from rehabtwin import correction, feedback, filtering, frames, hsmr, opensim_stage, validation
from rehabtwin.io_formats import Table, read_table, read_trc, write_table, write_trc
from rehabtwin.kinematics import _fppa, classify
from rehabtwin.metrics import segment_reps
from rehabtwin.sequence import MarkerSequence


def rot_y(deg):
    a = np.radians(deg)
    return np.array([[np.cos(a), 0, np.sin(a)], [0, 1, 0], [-np.sin(a), 0, np.cos(a)]])


def rot_x(deg):
    a = np.radians(deg)
    return np.array([[1, 0, 0], [0, np.cos(a), -np.sin(a)], [0, np.sin(a), np.cos(a)]])


# ------------------------------------------------------------- io formats

def test_trc_roundtrip_with_missing(tmp_path):
    m = np.random.default_rng(0).normal(size=(5, 3, 3))
    m[2, 1] = np.nan
    write_trc(tmp_path / "a.trc", ["A", "B", "C"], m, np.arange(5) / 50)
    names, back, t, units = read_trc(tmp_path / "a.trc")
    assert names == ["A", "B", "C"] and units == "m"
    assert np.allclose(t, np.arange(5) / 50)
    assert np.isnan(back[2, 1]).all()
    assert np.allclose(back[np.isfinite(back)], m[np.isfinite(m)], atol=1e-6)


def test_mot_roundtrip(tmp_path):
    data = np.arange(12.0).reshape(4, 3)
    write_table(tmp_path / "a.mot", ["x", "y", "z"], data, np.arange(4) * 0.1)
    tab = read_table(tmp_path / "a.mot")
    assert tab.columns == ["x", "y", "z"] and tab.in_degrees
    assert np.allclose(tab.data, data) and np.allclose(tab.col("y"), data[:, 1])


# --------------------------------------------------------------- sequence

def test_sequence_roundtrip_and_checks(tmp_path):
    seq = MarkerSequence(fps=30, marker_names=["a", "b"], markers=np.zeros((4, 2, 3)), frame="yup_world",
                         joint_names=["JC_x"], joints=np.ones((4, 1, 3)), meta={"synthetic": True})
    seq.save(tmp_path / "s.npz")
    back = MarkerSequence.load(tmp_path / "s.npz")
    assert back.marker_names == ["a", "b"] and back.meta["synthetic"] and back.joints.shape == (4, 1, 3)
    assert np.allclose(back.times, np.arange(4) / 30)
    with pytest.raises(ValueError):
        MarkerSequence(fps=30, marker_names=["a"], markers=np.zeros((4, 2, 3)), frame="yup_world")
    with pytest.raises(ValueError):
        MarkerSequence(fps=30, marker_names=["a", "b"], markers=np.zeros((4, 2, 3)), frame="lab")


# ----------------------------------------------------------------- frames

def test_rotation_between_and_kabsch():
    a, b = np.array([0.2, 1.0, -0.1]), np.array([0.0, 1.0, 0.0])
    R = frames.rotation_between(a, b)
    assert np.allclose(R @ (a / np.linalg.norm(a)), b, atol=1e-9)
    assert np.allclose(frames.rotation_between(b, -b) @ b, -b)
    pts = np.random.default_rng(1).normal(size=(20, 3))
    Rt = rot_y(33) @ rot_x(-12)
    R2, t2, _, rms = frames.kabsch(pts, pts @ Rt.T + [1, 2, 3])
    assert np.allclose(R2, Rt, atol=1e-9) and np.allclose(t2, [1, 2, 3]) and rms < 1e-9


def test_floor_fit_recovers_camera_pitch():
    rng = np.random.default_rng(2)
    # feet on a y = 0 floor, spread over a 30 x 40 cm area, then a camera pitched by 8 deg
    feet = np.stack([rng.uniform(-0.15, 0.15, 200), np.zeros(200), rng.uniform(-0.2, 0.2, 200)], axis=1)
    pts = (feet @ rot_x(8).T).reshape(50, 4, 3)
    up, rms, n = frames.estimate_floor_up(pts, ["a", "b", "c", "d"], ["a", "b", "c", "d"], [0, 1, 0], lowest_fraction=1.0)
    assert abs(frames.angle_deg(up, rot_x(8) @ [0, 1, 0])) < 0.01 and rms < 1e-9 and n == 200


def test_floor_fit_ignores_a_raised_foot():
    rng = np.random.default_rng(4)
    T = 60
    names = ["RHEE", "RTOE", "LHEE", "LTOE"]
    pts = np.zeros((T, 4, 3))
    pts[:, 0] = [-0.10, 0.0, 0.10]
    pts[:, 1] = [0.15, 0.0, 0.12]
    pts[:, 2] = [-0.10, 0.25 + 0.05 * np.sin(np.arange(T) / 5)[0], -0.10]  # left foot never touches down
    pts[:, 3] = [0.15, 0.30, -0.12]
    pts[:, 2, 1] = 0.25 + 0.05 * np.sin(np.arange(T) / 5)
    pts += rng.normal(0, 0.002, pts.shape)
    pts[:, :2, 0] += np.linspace(0, 0.02, T)[:, None]  # small stance-foot sway, still ~collinear
    with pytest.raises(ValueError):  # one stance foot cannot define a plane...
        frames.estimate_floor_up(pts, names, names, [0, 1, 0])
    both = pts.copy()
    both[: T // 2, 2:, 1] = [0.0, 0.0]  # ...but once the left foot lands, the plane is found
    up, rms, n = frames.estimate_floor_up(both @ rot_x(10).T, names, names, [0, 1, 0])
    assert frames.angle_deg(up, rot_x(10) @ [0, 1, 0]) < 1.5 and rms < 0.01


def test_floor_fit_rejects_collinear_feet():
    pts = np.zeros((10, 3, 3))
    pts[:, :, 0] = np.linspace(0, 0.3, 3)
    with pytest.raises(ValueError):
        frames.estimate_floor_up(pts, ["a", "b", "c"], ["a", "b", "c"], [0, 1, 0])


def test_to_opensim_ground_heading():
    # y up and right hip at -x means the subject faces world +z (right-handed frame);
    # OpenSim wants x forward, y up, z right
    names = ["RHIP", "LHIP", "HEEL"]
    pts = np.array([[[-0.1, 1.0, 0.0], [0.1, 1.0, 0.0], [0.0, 0.05, 0.1]]] * 3)
    R, t = frames.to_opensim_ground(pts, names, [0, 1, 0], [("RHIP", "LHIP")], floor_names=["HEEL"])
    g = frames.apply(R, pts, t)
    assert np.allclose(R @ [0, 0, 1], [1, 0, 0], atol=1e-9)   # facing direction -> +x
    assert np.allclose(R @ [-1, 0, 0], [0, 0, 1], atol=1e-9)  # subject's right -> +z
    assert g[0, 0, 2] > g[0, 1, 2]                             # right hip has larger z
    assert abs(g[:, 2, 1].min()) < 1e-9                         # heel on the floor


# -------------------------------------------------------------- filtering

def test_plan_segments_bridges_short_gaps_and_splits_long():
    valid = np.ones(300, bool)
    valid[100:103] = False   # 0.1 s at 30 fps -> bridged
    valid[200:230] = False   # 1 s -> split
    segs, imputed = filtering.plan_segments(valid, 30, max_gap_s=0.2, min_segment_s=1.0)
    assert segs == [(0, 200), (230, 300)] and imputed == [100, 101, 102]


def test_lowpass_cutoff_is_minus_3db():
    fps, fc = 100.0, 6.0
    t = np.arange(2000) / fps
    for f, expect in ((1.0, 1.0), (fc, 0.707), (20.0, 0.0)):
        y = filtering.lowpass(np.sin(2 * np.pi * f * t), fps, fc)
        gain = np.std(y[300:-300]) / np.std(np.sin(2 * np.pi * f * t[300:-300]))
        assert abs(gain - expect) < 0.03, (f, gain)


def test_interpolate_gaps():
    x = np.array([0.0, np.nan, 2.0, np.nan, np.nan, 5.0])
    assert np.allclose(filtering.interpolate_gaps(x), [0, 1, 2, 3, 4, 5])


# ------------------------------------------------------------- kinematics

@pytest.mark.parametrize("coord,expect", [
    ("hip_flexion_r", ("hip_r", "sagittal")), ("hip_adduction_l", ("hip_l", "frontal")),
    ("knee_angle_r", ("knee_r", "sagittal")), ("L5_S1_Lat_Bending", ("lumbar", "frontal")),
    ("L1_T12_axial_rotation", ("lumbar", "transverse")), ("pelvis_tx", ("pelvis", "translation")),
    ("pro_sup_l", ("forearm_l", "transverse")), ("knee_angle_r_beta", ("patella_r", "coupled")),
])
def test_classify(coord, expect):
    assert classify(coord) == expect


def test_fppa_valgus_positive_both_legs():
    fwd, up, right = np.array([1.0, 0, 0]), np.array([0, 1.0, 0]), np.array([0, 0, 1.0])
    # right leg at z = +0.1; knee pushed medially (toward z = 0)
    r = _fppa(np.array([0, 1.0, 0.1]), np.array([0.1, 0.5, 0.05]), np.array([0, 0.05, 0.1]), fwd, up, right, "r")
    l = _fppa(np.array([0, 1.0, -0.1]), np.array([0.1, 0.5, -0.05]), np.array([0, 0.05, -0.1]), fwd, up, right, "l")
    assert r > 5 and l > 5 and abs(r - l) < 1e-9
    straight = _fppa(np.array([0, 1.0, 0.1]), np.array([0, 0.5, 0.1]), np.array([0, 0.0, 0.1]), fwd, up, right, "r")
    assert abs(straight) < 1e-9


# ---------------------------------------------------------------- metrics

def test_segment_reps_counts_peaks():
    fps = 30
    t = np.arange(0, 12, 1 / fps)
    sig = 45 * (1 - np.cos(2 * np.pi * 0.25 * t))  # 3 full reps in 12 s
    reps = segment_reps(sig, fps, min_prominence_deg=20, min_rep_s=1.0)
    assert len(reps) == 3
    for a, p, b in reps:
        assert a < p < b and sig[p] > 85


# ------------------------------------------------------------- validation

def test_validation_bias_gates_and_synthetic_never_approves():
    t = np.arange(0, 5, 0.01)
    ref = Table(["knee_angle_r", "hip_adduction_r", "pelvis_tx"],
                np.stack([60 * np.sin(t), 10 * np.sin(t), t], axis=1), t)
    est = Table(ref.columns, ref.data + [2.0, 6.0, 0.5], t)
    cmp = validation.compare(est, ref)
    assert set(cmp["coordinates"]) == {"knee_angle_r", "hip_adduction_r"}  # translations excluded
    k = cmp["coordinates"]["knee_angle_r"]
    assert abs(k["bias_deg"] - 2) < 1e-9 and k["rmse_offset_removed_deg"] < 1e-9
    rep = validation.report(cmp, "P", "test", ["squat"], synthetic=False)
    assert rep["gates"]["knee_r.sagittal_rmse_le_3deg"] == "pass"
    assert rep["gates"]["hip_r.frontal_rmse_le_5deg"] == "fail"
    assert rep["feedback_allowed_joint_planes"] == ["knee_r.sagittal"] and rep["approved_for"] == ["screening"]
    assert validation.report(cmp, "P", "test", ["squat"], synthetic=True)["approved_for"] == []
    bad = validation.compare(Table(ref.columns, ref.data + [9.0, 9.0, 0.0], t), ref)
    assert validation.report(bad, "P", "test", ["squat"])["approved_for"] == []  # nothing passed


def test_validation_finds_time_lag():
    t = np.arange(0, 6, 0.01)
    ref = Table(["knee_angle_r"], (50 * np.sin(2 * t))[:, None], t)
    est = Table(["knee_angle_r"], (50 * np.sin(2 * (t - 0.12)))[:, None], t)
    cmp = validation.compare(est, ref, max_lag_s=0.3)
    assert abs(cmp["lag_s"] - 0.12) < 0.011 and cmp["coordinates"]["knee_angle_r"]["rmse_deg"] < 0.5


# ------------------------------------------------------------------- HSMR

def test_hsmr_input_size_replicates_upstream_resize():
    assert hsmr.hsmr_input_size(1920, 1080) == (1920, 1080)
    assert hsmr.hsmr_input_size(3840, 2160) == (1080, 608)   # HSMR's (w, h) argument quirk
    assert hsmr.hsmr_input_size(1080, 1920) == (1080, 1920)


def test_full_image_cam_t_matches_upstream_formula():
    pc = np.array([[0.1, -0.2, 40.0]])
    bb = np.array([[700.0, 400.0, 512.0]])
    t = hsmr.full_image_cam_t(pc, bb, 1920, 1080)
    z = 40.0 * 256 / 512
    assert np.allclose(t, [[0.1 + (700 - 960) / 5000 * z, -0.2 + (400 - 540) / 5000 * z, z]])


def test_select_track_follows_person_and_rejects_jumps():
    frames_ = [
        {"bbx_cs": [[500, 500, 400], [1500, 500, 150]]},  # subject (large) + bystander
        {"bbx_cs": [[1510, 505, 150], [510, 502, 405]]},  # order swapped
        {"bbx_cs": [[1500, 500, 150]]},                   # subject missed, only bystander
        {"bbx_cs": np.zeros((0, 3))},
        {"bbx_cs": [[520, 505, 410]]},
    ]
    assert hsmr.select_track(frames_).tolist() == [0, 1, -1, -1, 0]


def test_validation_aliases_lumbar_total_to_single_joint_models():
    t = np.arange(0, 3, 0.01)
    ref = Table(["lumbar_extension", "knee_angle_r"], np.stack([-20 * np.sin(t), 40 * np.sin(t)], axis=1), t)
    est = Table(["lumbar_total.sagittal", "knee_angle_r"], ref.data + [1.0, 0.0], t)
    per = validation.compare(est, ref)["coordinates"]
    assert per["lumbar_total.sagittal"]["reference_column"] == "lumbar_extension"
    assert abs(per["lumbar_total.sagittal"]["bias_deg"] - 1.0) < 1e-9


def test_device_gravity_overrides_image_estimates():
    # a subject standing upright, seen by a camera pitched 20 deg down (OpenCV frame)
    names = ["RHIP", "LHIP", "RHEE", "LHEE", "RTOE", "LTOE"]
    body = np.array([[0.1, 0.9, 0], [-0.1, 0.9, 0], [0.1, 0, -0.05], [-0.1, 0, -0.05], [0.1, 0, 0.15], [-0.1, 0, 0.15]])
    cam_from_world = rot_x(-20) @ np.diag([1.0, -1.0, -1.0])   # y-up world -> pitched OpenCV camera
    pts = np.repeat((body @ cam_from_world.T + [0, 0.5, 3.0])[None], 40, axis=0)
    up_cv = cam_from_world @ [0, 1.0, 0]
    seq = MarkerSequence(fps=30, marker_names=names, markers=pts, frame="opencv_camera",
                         meta={"gravity_up_cv": up_cv.tolist(), "gravity_source": "test IMU"})
    cfg = {"frames": {"up": "auto", "foot_markers": [], "right_left_pairs": [["RHIP", "LHIP"]]}}
    _, g, qc = opensim_stage.to_ground(seq, cfg)
    assert qc["up_source"] == "device gravity (test IMU)" and abs(qc["device_tilt_vs_camera_level_deg"] - 20) < 1e-6
    # the feet -> hips direction keeps exactly its true inclination to gravity
    hips = g[0, :2].mean(axis=0) - g[0, 2:].mean(axis=0)
    true = body[:2].mean(axis=0) - body[2:].mean(axis=0)
    assert abs(frames.angle_deg(hips, [0, 1, 0]) - frames.angle_deg(true, [0, 1, 0])) < 1e-6


def test_correction_target_modes():
    t = np.arange(5) * 0.1
    tab = Table(["a_r", "a_l"], np.array([[0, 1], [2, 1], [4, 1], [6, 1], [8, 1.0]]), t)
    spec = {"targets": [{"coordinate": "a_r", "mode": "clamp", "max": 5.0}]}
    assert correction.apply_targets(tab, spec)["a_r"].tolist() == [0, 2, 4, 5, 5]
    spec = {"targets": [{"coordinate": "a_r", "mode": "scale", "factor": 0.5, "about": 2.0}]}
    assert correction.apply_targets(tab, spec)["a_r"].tolist() == [1, 2, 3, 4, 5]
    spec = {"targets": [{"coordinate": "a_r", "mode": "mirror", "from": "a_l"}]}
    assert correction.apply_targets(tab, spec)["a_r"].tolist() == [1] * 5
    spec = {"targets": [{"coordinate": "a_r", "mode": "set", "value": 3}, {"coordinate": "a_l", "mode": "offset", "delta": -1}]}
    out = correction.apply_targets(tab, spec)
    assert out["a_r"].tolist() == [3] * 5 and out["a_l"].tolist() == [0] * 5
    with pytest.raises(ValueError):
        correction.apply_targets(tab, {"targets": [{"coordinate": "missing", "mode": "set", "value": 0}]})


def test_correction_specs_load():
    for name in ("squat_knee_valgus_right", "squat_trunk_upright"):
        spec = correction.load_spec(name)
        assert spec["targets"] and spec["anchors"] and "TEMPLATE" in spec["author"]


def _rule_spec(**sched):
    return {"name": "t", "rules": [{"id": "v", "signal": "s", "joint_plane": "knee_r.frontal", "op": ">", "threshold": 10.0,
                                     "min_duration_s": 0.2, "cue": {"actuator": "a"}}],
            "schedule": {"bandwidth_deg": 2.0, "refractory_s": 0.0, "start_fraction": 1.0, "end_fraction": 1.0,
                         "fade_events": 1, **sched}}


def test_cue_engine_hysteresis_min_duration_and_gate():
    t = np.arange(0, 6, 0.01)
    s = np.zeros_like(t)
    s[(t > 1) & (t < 1.1)] = 15        # too short: no cue
    s[(t > 2) & (t < 3)] = 12          # one violation...
    s[(t >= 2.5) & (t < 2.6)] = 9      # ...dipping below threshold but inside the 2 deg band: still one
    s[(t > 4) & (t < 5)] = 20          # second violation
    log, sent = feedback.replay(_rule_spec(), t, {"s": s}, tier="A", allowed_joint_planes=["knee_r.frontal"])
    decisions = [e for e in log if "decision" in e]
    assert [d["decision"] for d in decisions] == ["cue", "cue"] and len(sent) == 2
    assert 2.2 <= decisions[0]["t"] <= 2.23         # after min_duration (violation starts at the first frame > 2 s)
    log_c, sent_c = feedback.replay(_rule_spec(), t, {"s": s}, tier="C")
    assert not sent_c and all(e["decision"] == "would_cue" for e in log_c if "decision" in e)
    log_u, sent_u = feedback.replay(_rule_spec(), t, {"s": s}, tier="A", allowed_joint_planes=[])
    assert not sent_u and "not validated" in [e for e in log_u if "decision" in e][0]["reason"]


def test_cue_engine_faded_schedule_and_refractory():
    t = np.arange(0, 20, 0.01)
    s = np.where((t % 2) < 0.5, 15.0, 0.0)          # 10 violations, one every 2 s
    spec = _rule_spec(start_fraction=1.0, end_fraction=0.25, fade_events=4)
    log, sent = feedback.replay(spec, t, {"s": s}, tier="A", allowed_joint_planes=["knee_r.frontal"])
    d = [e["decision"] for e in log if "decision" in e]
    assert len(d) == 10 and d[0] == "cue" and 3 <= d.count("cue") <= 5    # fades towards 1 in 4
    spec = _rule_spec(refractory_s=5.0)
    log, sent = feedback.replay(spec, t, {"s": s}, tier="A", allowed_joint_planes=["knee_r.frontal"])
    times = [c["timestamp"] for c in sent]
    assert all(b - a >= 5.0 for a, b in zip(times, times[1:]))


def test_feedback_rules_template_loads():
    spec = feedback.load_rules("squat_posture")
    assert "TEMPLATE" in spec["author"] and all("joint_plane" in r for r in spec["rules"])


def test_lsl_live_loop_matches_offline_replay():
    pylsl = pytest.importorskip("pylsl")  # noqa: F841
    import threading
    from rehabtwin import lsl_bridge
    t = np.arange(0, 8, 0.02)
    s = np.where((t % 2) < 0.6, 15.0, 0.0)          # 4 violations
    spec = _rule_spec(start_fraction=1.0, end_fraction=0.5, fade_events=2)
    _, offline = feedback.replay(spec, t, {"s": s}, tier="A", allowed_joint_planes=["knee_r.frontal"])
    res = {}
    live = threading.Thread(target=lambda: res.update(eng=lsl_bridge.run_live(
        spec, "A", ["knee_r.frontal"], duration_s=20, source="rt_test_posture", resolve_timeout=10)))
    live.start()
    lsl_bridge.stream_posture(t, {"s": s}, speed=4.0, name="rt_test_posture")
    live.join()
    online = [e for e in res["eng"].log if e.get("decision") == "cue"]
    assert len(online) == len(offline) >= 2


def _rot_quat(axis, deg):
    a = np.radians(deg) / 2
    axis = np.asarray(axis, float) / np.linalg.norm(axis)
    return np.array([*(axis * np.sin(a)), np.cos(a)])


def _vmc_frame(knee_deg=60.0, valgus_deg=8.0, trunk_deg=30.0):
    """Synthetic SlimeVR-like VMC bundle (Unity left-handed args) for a subject facing +x, right = +z."""
    from rehabtwin.vmc import rh_to_unity
    fwd_axis, right_axis = [1, 0, 0], [0, 0, 1]
    ident = np.array([0.0, 0.0, 0.0, 1.0])
    rh = {
        "Hips": ([0, 0.9, 0], ident),
        "Spine": ([0, 0.1, 0], _rot_quat(right_axis, -trunk_deg)),   # bend forward at the spine (towards +x)
        "Chest": ([0, 0.2, 0], ident),
        "Neck": ([0, 0.25, 0], ident),
        # right thigh: knee pushed medially (towards -z) by valgus/2, shank back out by valgus
        "RightUpperLeg": ([0, -0.05, 0.1], _rot_quat(fwd_axis, valgus_deg / 2)),
        "RightLowerLeg": ([0, -0.42, 0], _rot_quat(fwd_axis, -valgus_deg)),
        "RightFoot": ([0, -0.42, 0], ident),
        "LeftUpperLeg": ([0, -0.05, -0.1], _rot_quat(right_axis, knee_deg / 2)),
        "LeftLowerLeg": ([0, -0.42, 0], _rot_quat(right_axis, -knee_deg)),
        "LeftFoot": ([0, -0.42, 0], ident),
    }
    return {name: rh_to_unity(np.array(p, float), q) for name, (p, q) in rh.items()}


def test_vmc_forward_kinematics_and_posture_signals():
    from rehabtwin.vmc import VMCPose
    pose = VMCPose()
    for name, (p, q) in _vmc_frame().items():
        pose.on_bone("/VMC/Ext/Bone/Pos", name, *p, *q)
    pose.on_root("/VMC/Ext/Root/Pos", "root", 0, 0, 0, 0, 0, 0, 1)
    s = pose.signals()
    assert abs(s["knee_angle_l"] - 60.0) < 1e-6 and abs(s["knee_angle_r"] - 8.0) < 1e-6
    assert abs(s["knee_fppa_r"] - 8.0) < 1e-6          # medial knee = valgus, positive
    # the fixture bends at the Spine joint: pelvis upright, chest + neck (0.45 m) tilted 30 deg
    expected_trunk = np.degrees(np.arctan2(0.45 * np.sin(np.radians(30)), 0.1 + 0.45 * np.cos(np.radians(30))))
    assert abs(s["torso.sagittal"] - expected_trunk) < 1e-6 and abs(s["torso.frontal"]) < 1e-6
    assert abs(s["lumbar_total.sagittal"] + 30.0) < 1e-6   # spine flexion, negative like OpenSim


def test_vmc_over_udp():
    pytest.importorskip("pythonosc")
    import threading
    from pythonosc import osc_bundle_builder, osc_message_builder, udp_client
    from rehabtwin import vmc
    got = []
    port = 39911
    th = threading.Thread(target=lambda: vmc.serve(port, rate_hz=50, duration_s=1.5, publish_lsl=False,
                                                    on_signals=lambda t, s: got.append(s), host="127.0.0.1"))
    th.start()
    client = udp_client.SimpleUDPClient("127.0.0.1", port)
    time.sleep(0.3)
    for _ in range(20):
        b = osc_bundle_builder.OscBundleBuilder(osc_bundle_builder.IMMEDIATELY)
        msgs = [("/VMC/Ext/Root/Pos", ["root", 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0])]
        msgs += [("/VMC/Ext/Bone/Pos", [n, *map(float, p), *map(float, q)]) for n, (p, q) in _vmc_frame(knee_deg=45).items()]
        for addr, args in msgs:
            m = osc_message_builder.OscMessageBuilder(address=addr)
            for a in args:
                m.add_arg(a)
            b.add_content(m.build())
        client.send(b.build())
        time.sleep(0.05)
    th.join()
    assert got and abs(got[-1]["knee_angle_l"] - 45.0) < 1e-3


FAKE_BH = """
#define BH_LAYOUT_TACTSUITX40 {                                              \\
""" + "".join(f"    {{ Target::{'ChestFront' if i < 10 or i >= 30 else 'ChestBack'}, BH_LAYOUT_TACTSUITX40_MAKE_POINT({(i % 2) + (2 if i >= 20 else 0)}, {(i % 10) // 2}) }}, \\\n" for i in range(40)) + """  }
#define BH_LAYOUT_TACTOSY2 {                                              \\
""" + "".join(f"    BH_LAYOUT_TACTOSY2_MAKE_POINT({i % 3}, {i // 3}), \\\n" for i in range(6)) + """  }
"""


def test_suit_payload_encoding_and_patterns(tmp_path):
    from rehabtwin import suit
    levels = np.zeros(40)
    levels[[0, 3, 39]] = [1.0, 0.5, 1.0]
    p = suit.encode_vest(levels)
    assert len(p) == 20 and p[0] == 0xF0 and p[1] == 0x08 and p[19] == 0x0F
    assert suit.encode_plain([0.6, 0, 1.2]) == bytes([60, 0, 100])
    assert [suit.envelope("double", t, 1.0) for t in (0.1, 0.5, 0.7, 1.1)] == [1.0, 0.0, 1.0, 0.0]
    hdr = tmp_path / "devices.hpp"
    hdr.write_text(FAKE_BH)
    assert len(suit.parse_layout("TACTSUITX40", hdr)) == 40 and len(suit.parse_layout("TACTOSY2", hdr)) == 6
    d = suit.SuitDriver("suit_bhaptics", header=hdr)
    assert d.add({"actuator": "thigh_r_lateral", "intensity": 0.6, "duration_ms": 200}, 0.0)
    assert not d.add({"actuator": "nonexistent"}, 0.0) and d.unknown == {"nonexistent"}
    assert d.frame(0.1)["thigh_r"] == bytes([60] * 6) and d.frame(0.3)["thigh_r"] == bytes(6)
    d.add({"actuator": "upper_back_center", "intensity": 1.0, "duration_ms": 300}, 1.0)
    vest = d.frame(1.1)["vest"]
    assert sum(bin(b).count("1") for b in vest) == 4 * 4      # 4 motors at full (4 bits each)


def test_live_chain_posture_to_suit_payloads(tmp_path):
    """IMU-like posture stream -> CueEngine -> cue markers -> suit payloads, all over LSL."""
    pytest.importorskip("pylsl")
    import threading
    from rehabtwin import lsl_bridge, suit
    hdr = tmp_path / "devices.hpp"
    hdr.write_text(FAKE_BH)
    spec = feedback.load_rules("squat_posture")
    t = np.arange(0, 4, 0.02)
    sig = {"knee_fppa_r": np.where((t > 1) & (t < 2), 18.0, 2.0), "torso.sagittal": np.full_like(t, 10.0)}
    res = {}
    transport = suit.DryRunTransport()
    threads = [
        threading.Thread(target=lambda: res.update(eng=lsl_bridge.run_live(
            spec, "A", ["knee_r.frontal"], duration_s=15, source="rt_chain_posture"))),
        threading.Thread(target=lambda: suit.run_bridge(suit.SuitDriver("suit_bhaptics", header=hdr), transport,
                                                        duration_s=4.0, rate_hz=50)),
    ]
    for th in threads:
        th.start()
    time.sleep(0.5)
    lsl_bridge.stream_posture(t, sig, speed=2.0, name="rt_chain_posture")
    for th in threads:
        th.join()
    sent = [e for e in res["eng"].log if e.get("decision") == "cue"]
    assert len(sent) == 1 and sent[0]["actuator"] == "thigh_r_lateral"
    on = [e for e in transport.log if e["device"] == "thigh_r" and e["payload_hex"] != "00" * 6]
    assert on and on[0]["payload_hex"] == f"{60:02x}" * 6     # 0.6 intensity on all 6 sleeve motors


def test_parse_assist():
    from rehabtwin.muscles import parse_assist
    assert parse_assist("knee_angle_r=40") == ("knee_angle_r", 40.0, -1.0, 1.0)
    assert parse_assist("hip_flexion_l=25.5:neg") == ("hip_flexion_l", 25.5, -1.0, 0.0)
    assert parse_assist("L5_S1_Flex_Ext=30:pos")[2:] == (0.0, 1.0)
