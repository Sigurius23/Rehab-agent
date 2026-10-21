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


def test_correction_view_on_synthetic_valgus(selftest_run):
    out, _, _ = selftest_run
    from rehabtwin.correction import CorrectionRefused
    with pytest.raises(CorrectionRefused):           # Tier C: no targets without --illustrative
        cli.run_correction(out, "squat_knee_valgus_right")
    s, cdir = cli.run_correction(out, "squat_knee_valgus_right", illustrative=True)
    assert s["status"].startswith("ILLUSTRATION ONLY")
    fppa = s["derived_signals"]["knee_fppa_r"]
    assert fppa["measured_range"][1] - fppa["corrected_range"][1] > 15      # valgus removed
    drift = s["feet_anchor_drift_m"]["max"]
    assert drift < 0.025                                                       # feet (nearly) planted
    assert s["admissible"] == (drift < 0.02 and not s["range_of_motion_violations"])
    assert (cdir / "correction.html").read_text().count("ILLUSTRATION ONLY") >= 1
    rc = s["rule_check"]                                   # the spec asks for a posture-rule check
    assert "knee_valgus_r" in rc["removed"] and rc["per_rule"]["knee_valgus_r"]["corrected"]["violations"] == 0
    t, _ = cli.run_correction(out, "squat_trunk_upright", illustrative=True)
    trunk = t["derived_signals"]["torso.sagittal"]
    assert trunk["measured_range"][1] - trunk["corrected_range"][1] > 8       # less trunk lean


def test_muscle_effects_and_weakness_what_if(selftest_run):
    out, res, _ = selftest_run
    rep = res["metrics"]["reps"][0]
    study, mdir = cli.muscle_study(out, start=rep["peak_s"] - 0.3, stop=rep["peak_s"] + 0.3,
                                   weaken=["gluteus_maximus_r=0.5"], assist=["knee_angle_r=40:neg"],
                                   passive=["knee_angle_r=60@20:pos"])
    base = study["runs"]["measured"]
    assert base["grf"]["feet_planted"] and 0.8 < base["grf"]["min_vertical_bw"] <= base["grf"]["peak_vertical_bw"] < 1.4
    ga = base["group_activation"]
    # a deep squat is carried by the knee and hip extensors
    top = sorted(ga, key=lambda g: -ga[g]["peak"])[:4]
    assert any(g.startswith("quadriceps") for g in top) and any(g.startswith("gluteus_maximus") for g in top)
    knee = base["joint_moments"]["knee_angle_r"]
    assert 0.5 < -knee["min_Nm_per_kg"] < 2.0          # knee extension moment, N·m/kg
    weak = study["comparisons"]["gluteus_maximus_r at 50%"]["gluteus_maximus_r"]
    assert weak["other"] > weak["base"] * 1.3          # the weakened muscle must work closer to its limit
    exo = study["runs"]["ideal exo knee_angle_r <= 40 N·m (neg)"]
    dev = exo["assistive_devices"]["knee_angle_r"]
    assert 5 < dev["peak_abs_Nm"] <= 40.0 + 1e-6                     # used, never above its cap
    q = study["comparisons"]["ideal exo knee_angle_r <= 40 N·m (neg)"]["quadriceps_r"]
    assert q["other"] < 0.8 * q["base"]                               # knee-extension assist offloads the quadriceps
    pas = study["runs"]["passive spring knee_angle_r 60 N·m/rad from 20° (pos)"]["passive_devices"]["knee_angle_r"]
    assert pas["peak_abs_Nm"] > 20 and pas["engaged_fraction"] > 0.9               # deep in the squat: stretched
    q = study["comparisons"]["passive spring knee_angle_r 60 N·m/rad from 20° (pos)"]["quadriceps_r"]
    assert q["other"] < 0.9 * q["base"]                               # a knee-extension elastic offloads them too
    assert (mdir / "muscles.html").exists() and (mdir / "study.json").exists()
    # 3D muscle view: one path per muscle per frame, activations per variant, weakened capacity visible
    page = (mdir / "muscles.html").read_text()
    view = json.loads(page.split("id='mus-data'>", 1)[1].split("</script>", 1)[0])
    assert set(view["runs"]) == set(study["runs"]) and len(view["motions"]) == 1    # no corrected variant here
    n, frames = len(view["muscles"]), len(view["t"])
    paths = view["motions"]["m0"]["paths"]
    assert n > 50 and len(paths) == frames and all(len(f) == n for f in paths)
    assert all(len(p) >= 6 and len(p) % 3 == 0 for p in paths[0])                  # >= 2 points, xyz in mm
    pelvis = np.array(view["motions"]["m0"]["bodies"]["pelvis"][0])
    assert np.abs(np.array(paths[0][0]).reshape(-1, 3) - pelvis).max() < 1500
    m = view["muscles"].index("glmax1_r")
    weak_run, base_run = view["runs"]["gluteus_maximus_r at 50%"], view["runs"]["measured"]
    assert weak_run["fmax"][m] == pytest.approx(0.5 * base_run["fmax"][m], abs=1)
    assert len(weak_run["act"]) == frames and all(0 <= a <= 100 for row in weak_run["act"] for a in row)


def test_cue_replay_blocked_on_tier_c(selftest_run):
    out, _, _ = selftest_run
    result, cdir = cli.cue_replay(out, "squat_posture")
    pr = result["summary"]["per_rule"]["knee_valgus_r"]
    assert pr["violations"] == 3 and pr["cues_sent"] == 0 and pr["would_cue"] >= 1
    assert result["summary"]["commands_sent"] == 0
    assert (cdir / "commands.csv").read_text().count("\n") == 1     # header only


def test_strength_calibration_reproduces_measured_torques(selftest_run, tmp_path):
    from rehabtwin import muscles, strength
    out, res, _ = selftest_run
    sess = json.loads((out / "session.json").read_text())
    model_path = out / sess["pipeline"]["outputs"]["model"]
    acts = strength.load_actions()
    model = opensim.Model(str(model_path))
    names = ["hip_abduction_r", "hip_abduction_l", "hip_extension_r", "hip_extension_l", "knee_extension_r",
             "knee_extension_l", "ankle_plantarflexion_r", "trunk_extension"]
    generic = {n: sum(strength.isometric_moments(model, strength.parse_test({"action": n, "torque_Nm": 1}, acts)).values())
               for n in names}
    assert 100 < generic["trunk_extension"] < 600          # about L5/S1 alone, not summed over coupled levels
    # right hip abductors weak: the fitted model reproduces every measured torque, and LSI flags it
    tests = [{"action": n, "torque_Nm": generic[n] * (0.6 if n == "hip_abduction_r" else 1.0)} for n in names]
    tests[0] = {"action": "hip_abduction_r", "force_N": tests[0]["torque_Nm"] / 0.8, "lever_arm_m": 0.8}
    rec = strength.calibrate(model_path, tests, tmp_path / "weak_abductors")
    for t in rec["tests"]:
        assert t["calibrated_model_Nm"] == pytest.approx(t["measured_Nm"], rel=0.01) and not t["at_bound"]
    ha = next(t for t in rec["tests"] if t["action"] == "hip_abduction_r")
    assert ha["factor"] < 0.6          # synergists calibrated elsewhere stay strong, so the prime movers drop further
    assert rec["muscle_factors"]["vaslat_r"] == pytest.approx(1.0, abs=0.01)
    sym = rec["symmetry"]["hip_abduction"]
    assert sym["lsi_pct"] == pytest.approx(60.0, abs=0.1) and sym["weaker_side"] == "r" and sym["flag"]
    assert not rec["symmetry"]["knee_extension"]["flag"]
    # everyone at half the generic strength (via the CLI) -> one common factor, and the squat costs twice as much
    spec = tmp_path / "hhd.json"
    spec.write_text(json.dumps({"device": "test", "tests": [{"action": n, "torque_Nm": 0.5 * generic[n]} for n in names]}))
    half, sdir = cli.strength_calibration(out, spec)
    assert all(t["factor"] == pytest.approx(0.5, abs=0.005) for t in half["tests"])
    assert (sdir / "strength.html").exists() and "Strength calibration" in (out / "index.html").read_text()
    rep = res["metrics"]["reps"][0]
    w = (rep["peak_s"] - 0.3, rep["peak_s"] + 0.3)
    generic_run = muscles.run(model_path, out / sess["pipeline"]["outputs"]["motion"], tmp_path / "generic",
                              start=w[0], stop=w[1])
    study, _ = cli.muscle_study(out, start=w[0], stop=w[1], view_3d=False, use_strength=True)
    assert study["muscle_model"]["source"].startswith("strength")
    for g in ("quadriceps_r", "gluteus_maximus_r"):
        ratio = study["runs"]["measured"]["group_activation"][g]["peak"] / generic_run["group_activation"][g]["peak"]
        assert 1.6 < ratio < 2.4, (g, ratio)


def test_progress_between_two_synthetic_sessions(selftest_run, tmp_path):
    from rehabtwin import synthetic
    out, res, _ = selftest_run
    # a later session of the same synthetic person with less right-knee valgus (6° -> 1° hip adduction)
    later = tmp_path / "later"
    seq, truth, truth_model = cli._synth(later, seed=1, motion=synthetic.squat_motion(30.0, 12.0, valgus_r_deg=1.0))
    cli.process(seq, later, exercise="squat", reference=truth, reference_model=truth_model,
                reference_system="synthetic truth (rehabtwin.synthetic)")
    cli.main(["progress", str(later), str(out), "--out", str(tmp_path / "progress")])
    prog = json.loads((tmp_path / "progress" / "progress.json").read_text())
    assert [s["dir"] for s in prog["sessions"]] == [str(out), str(later)]          # chronological, not argument order
    fppa = prog["first_to_last"]["knee_fppa_r"]
    assert fppa["change"] < -5 and fppa["beyond_rep_scatter"]
    assert fppa["verdict"] == "consistent across reps; size not validated"         # synthetic validation sizes nothing
    assert abs(prog["first_to_last"]["knee_angle_r"]["change"]) < 2                 # depth unchanged
    assert (tmp_path / "progress" / "progress.html").read_text().count("<svg") >= 4


def test_trunk_devices_use_physical_units(selftest_run, tmp_path):
    from rehabtwin import muscles
    out, _, _ = selftest_run
    sess = json.loads((out / "session.json").read_text())
    model_path = out / sess["pipeline"]["outputs"]["model"]
    model = opensim.Model(str(model_path))
    real, gain = muscles.device_coordinate(model, "lumbar_total_extension")
    assert real == "L5_S1_Flex_Ext" and 5.0 < gain < 9.0        # six coupled levels turn the trunk ~7x L5/S1
    assert muscles.device_coordinate(model, "knee_angle_r") == ("knee_angle_r", 1.0)
    # a 30 N·m back exo is a 30*gain generalized-force cap on L5_S1
    muscles.reserves_xml(model_path, tmp_path / "r.xml", assist=[muscles.parse_assist("lumbar_total_extension=30:pos")])
    xml = (tmp_path / "r.xml").read_text()
    act = xml[xml.index('name="exo_lumbar_total_extension"'):]
    opt = float(act.split("<optimal_force>")[1].split("<")[0])
    assert float(act.split("<max_control>")[1].split("<")[0]) * opt == pytest.approx(30 * gain, rel=1e-6)
    # a back elastic: physical K -> K gain^2 on the model coordinate, slack angle / gain
    info = muscles.dynamics_model(model_path, tmp_path / "dyn.osim",
                                  passive=[muscles.parse_passive("lumbar_total_extension=60@-10:neg")])
    assert info["passive"][0]["model_coordinate"] == "L5_S1_Flex_Ext"
    dyn = opensim.Model(str(tmp_path / "dyn.osim"))
    expr = opensim.ExpressionBasedCoordinateForce.safeDownCast(
        dyn.getForceSet().get("passive_lumbar_total_extension")).get_expression()
    assert expr.startswith(f"-{60 * gain * gain}") and "min(0," in expr
