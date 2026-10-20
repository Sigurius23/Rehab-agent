"""End-to-end tests through OpenSim (skipped when OpenSim or the Pose2Sim clone is missing).

These are software round trips against synthetic truth: they prove the
plumbing (frames, gaps, scaling, IK, metrics, records), not measurement
accuracy on real people.
"""
import json

import numpy as np
import pytest

opensim = pytest.importorskip("opensim")

from rehabtwin import cli, records, synthetic  # noqa: E402
from rehabtwin.config import load_config, resolve  # noqa: E402
from rehabtwin.hsmr import build_sequence  # noqa: E402
from rehabtwin.io_formats import read_table  # noqa: E402
from rehabtwin.skel_names import SKEL_JOINT_NAMES  # noqa: E402

CFG = load_config("skel105_pose2sim")
try:
    resolve(CFG["model"])
except FileNotFoundError as e:  # pragma: no cover
    pytest.skip(str(e), allow_module_level=True)


@pytest.fixture(scope="module")
def selftest_run(tmp_path_factory):
    out = tmp_path_factory.mktemp("selftest")
    res, failures = cli.selftest(out)
    return out, res, failures


def test_selftest_round_trip_within_limits(selftest_run):
    _, res, failures = selftest_run
    assert failures == {}
    assert res["metrics"]["n_reps"] == 3


def test_selftest_scale_factors_recovered(selftest_run):
    _, res, _ = selftest_run
    sf = res["qc"]["scale_factors"]
    for body in ("femur_r", "tibia_l", "pelvis", "humerus_r"):
        assert abs(sf[body][0] - synthetic.DEFAULT_SUBJECT_SCALES[body]) < 0.02, (body, sf[body])


def test_selftest_records_are_schema_valid_and_honest(selftest_run):
    out, res, _ = selftest_run
    sess = json.loads((out / "session.json").read_text())
    val = json.loads((out / "validation-report.json").read_text())
    assert records.validate(sess, "session") and records.validate(val, "validation-report")
    assert sess["synthetic"] is True and sess["twin_tier"] == "C"
    assert val["approved_for"] == []  # synthetic validation licenses nothing
    met = json.loads((out / "metrics.json").read_text())
    assert not any(s["feedback_eligible"] for s in met["summary"].values())
    assert (out / "report.html").read_text().count("<svg") >= 4


def test_selftest_gravity_from_floor_fit(selftest_run):
    _, res, _ = selftest_run
    fr = res["qc"]["frames"]
    assert fr["up_source"] == "floor plane fit"
    # synthetic camera looks down ~7.5 deg; the floor fit must see it
    assert 6.0 < fr["floor_fit"]["tilt_vs_camera_level_deg"] < 9.0


def test_selftest_detects_right_knee_valgus(selftest_run):
    _, res, _ = selftest_run
    s = res["metrics"]["summary"]
    assert s["knee_fppa_r"]["rep_peak_mean"] > s["knee_fppa_l"]["rep_peak_mean"] + 10
    assert 30 < s["torso.sagittal"]["rep_peak_mean"] < 55


def test_hsmr_adapter_emulated_round_trip(tmp_path):
    """Feed synthetic markers through the HSMR adapter path (fake SKEL forward, fake detections)."""
    seq, truth = synthetic.generate(CFG, tmp_path / "truth", seed=3)
    markers, joints = seq.markers, seq.joints   # opencv camera frame
    jidx = {n: i for i, n in enumerate(seq.joint_names)}
    T = seq.n_frames
    W, H = 1920, 1080
    frames_, lut = [], {}
    for f in range(T):
        if not seq.valid[f]:
            frames_.append({"bbx_cs": np.zeros((0, 3)), "poses": np.zeros((0, 46)), "betas": np.zeros((0, 10)),
                            "patch_cam_t": np.zeros((0, 3))})
            continue
        cam_t = np.nanmean(markers[f], axis=0)
        s = 420.0
        cx, cy = W / 2 + 5000 * cam_t[0] / cam_t[2], H / 2 + 5000 * cam_t[1] / cam_t[2]
        patch = np.array([cam_t[0] - (cx - W / 2) / 5000 * cam_t[2], cam_t[1] - (cy - H / 2) / 5000 * cam_t[2],
                          cam_t[2] * s / 256])
        key = f + 1.0
        lut[key] = (markers[f] - cam_t, cam_t)
        pose = np.zeros(46)
        pose[0] = key
        people = [(pose, np.zeros(10), patch, [cx, cy, s])]
        if f % 7 == 0:  # a bystander in some frames, far away and smaller
            people.append((np.zeros(46), np.ones(10), np.array([0, 0, 50.0]), [cx + 700, cy, 150.0]))
        frames_.append({k: np.array([p[i] for p in people]) for i, k in enumerate(["poses", "betas", "patch_cam_t", "bbx_cs"])})

    full_j = np.full((T, 24, 3), np.nan)
    for j, name in enumerate(SKEL_JOINT_NAMES):
        if "JC_" + name in jidx:
            full_j[:, j] = joints[:, jidx["JC_" + name]]
    static_j = np.full((24, 3), np.nan)
    for j, name in enumerate(SKEL_JOINT_NAMES):
        if "JC_" + name in jidx:
            static_j[j] = seq.static_joints[jidx["JC_" + name]]

    def fake_forward(poses, betas):
        verts, jts = [], []
        for p in poses:
            if p[0] == 0:  # neutral q = 0 request -> the static pose
                verts.append(seq.static_markers)
                jts.append(static_j)
                continue
            v, t = lut[float(p[0])]
            f = int(p[0]) - 1
            verts.append(v)
            jts.append(full_j[f] - t)
        return np.array(verts), np.array(jts)

    ids = {n: i for i, n in enumerate(seq.marker_names)}
    hs = build_sequence(frames_, fake_forward, seq.fps, (W, H), ids, meta={"synthetic": True, "person_ref": "SYN"})
    assert hs.valid.sum() == seq.valid.sum()
    np.testing.assert_allclose(hs.markers[seq.valid], markers[seq.valid], atol=1e-6)
    hs.save(tmp_path / "skel_seq.npz")
    res = cli.process(tmp_path / "skel_seq.npz", tmp_path, exercise="squat", reference=truth["mot"],
                      reference_system="synthetic truth")
    per = res["validation"]["per_coordinate"]
    assert per["knee_angle_r"]["rmse_deg"] < 2.0 and per["hip_flexion_l"]["rmse_deg"] < 2.5
    assert res["metrics"]["n_reps"] == 3


def test_validate_cli(selftest_run, tmp_path):
    out, _, _ = selftest_run
    rc = cli.main(["validate", str(out / "opensim" / "ik.mot"), str(out / "truth" / "truth.mot"),
                   "--out", str(tmp_path / "v.json"), "--synthetic", "--movement", "squat"])
    assert rc == 0
    rep = json.loads((tmp_path / "v.json").read_text())
    assert rep["kinematics_rmse_deg"]["knee_r"]["sagittal"] < 2.0
    assert read_table(out / "opensim" / "ik.mot").has("knee_angle_r")
