"""Fast unit tests (numpy/scipy only). Run: python -m pytest pipeline/tests -q"""
import numpy as np
import pytest

from rehabtwin import filtering, frames, hsmr, validation
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
