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
    assert val["processing_id"] == sess["pipeline"]["processing_id"]        # the feedback gate checks this
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
    from rehabtwin.correction import CorrectionRefused
    out, res, _ = selftest_run
    rep = res["metrics"]["reps"][0]
    with pytest.raises(CorrectionRefused):          # Tier C: no device profile without --illustrative
        cli.muscle_study(out, start=rep["peak_s"] - 0.1, stop=rep["peak_s"] + 0.1, assist=["knee_angle_r=40:neg"])
    study, mdir = cli.muscle_study(out, start=rep["peak_s"] - 0.3, stop=rep["peak_s"] + 0.3,
                                   weaken=["gluteus_maximus_r=0.5"], assist=["knee_angle_r=40:neg"],
                                   passive=["knee_angle_r=60@20:pos"], illustrative=True)
    base = study["runs"]["measured"]
    assert base["grf"]["feet_planted"] and 0.8 < base["grf"]["min_vertical_bw"] <= base["grf"]["peak_vertical_bw"] < 1.4
    prior = study["kinematics_prior"]["measured"]                    # double stance: feet held where they stood
    assert prior["feet_max_excursion_m"]["planted"] < 0.01 and prior["coordinate_rms_change_deg"]["mean"] < 1.0
    assert base["dynamic_consistency"]["consistent"]                  # slow synthetic squat: forces fit the motion
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


def test_augmenter_adds_plausible_anatomical_markers(tmp_path):
    """OpenCap's LSTM (via Pose2Sim ONNX) on MediaPipe-named keypoints taken from the model itself."""
    pytest.importorskip("onnxruntime")
    from rehabtwin.augmenter import RESPONSES, augment
    from rehabtwin.sequence import MarkerSequence
    cfg = load_config("mediapipe33_pose2sim")
    model = opensim.Model(str(resolve(cfg["model"])))
    ms = opensim.MarkerSet(str(resolve(cfg["marker_set"])))
    for i in range(ms.getSize()):
        model.addMarker(ms.get(i).clone())
    model.finalizeConnections()
    state = model.initSystem()
    names = [ms.get(i).getName() for i in range(ms.getSize())]
    frames = []
    for k in range(90):                      # a slow, shallow squat
        q = np.radians(25.0 * (1 - np.cos(2 * np.pi * k / 90)))
        for c, v in (("hip_flexion_r", q), ("hip_flexion_l", q), ("knee_angle_r", 2 * q), ("knee_angle_l", 2 * q),
                     ("ankle_angle_r", q), ("ankle_angle_l", q)):
            model.getCoordinateSet().get(c).setValue(state, v, False)
        model.getCoordinateSet().get("pelvis_ty").setValue(state, 0.93 - 0.25 * (1 - np.cos(2 * np.pi * k / 90)) / 2, False)
        model.realizePosition(state)
        frames.append([[model.getMarkerSet().get(n).getLocationInGround(state).get(j) for j in range(3)] for n in names])
    seq = MarkerSequence(fps=30.0, marker_names=names, markers=np.array(frames), frame="yup_world")
    out = augment(seq, height_m=1.75, mass_kg=70.0)
    pts = {n: out.markers[:, out.marker_names.index(n)] for n in out.marker_names}
    assert out.meta["default_config"] == "mediapipe_lstm_pose2sim" and len(out.marker_names) == len(names) + 43
    assert all(np.isfinite(pts[n]).all() for p in RESPONSES.values() for n in p)
    # model faces +x: ASIS in front of PSIS, hip joint centres near the hip keypoints, heels near the calcaneus markers
    assert (pts["r.ASIS_study"][:, 0] - pts["r.PSIS_study"][:, 0] > 0.05).all()
    assert np.linalg.norm(pts["RHJC_study"] - pts["RHip"], axis=1).max() < 0.10
    assert np.linalg.norm(pts["r_calc_study"] - pts["RHeel"], axis=1).max() < 0.08


def test_lstm_path_splits_at_a_lost_knee_instead_of_freezing_it(tmp_path):
    """A keypoint lost > 0.2 s masks the augmenter's lower-body markers; the stage must not solve (or freeze) there."""
    pytest.importorskip("onnxruntime")
    from rehabtwin.augmenter import augment
    from rehabtwin.io_formats import read_trc
    from rehabtwin.sequence import MarkerSequence
    cfg = load_config("mediapipe33_pose2sim")
    model = opensim.Model(str(resolve(cfg["model"])))
    ms = opensim.MarkerSet(str(resolve(cfg["marker_set"])))
    for i in range(ms.getSize()):
        model.addMarker(ms.get(i).clone())
    model.finalizeConnections()
    state = model.initSystem()
    names = [ms.get(i).getName() for i in range(ms.getSize())]
    k = np.arange(420)                       # 1 s still, six 2 s squats, 1 s still at 30 fps
    depth = np.where((k >= 30) & (k < 390), 0.5 * (1 - np.cos(2 * np.pi * (k - 30) / 60)), 0.0)
    frames = []
    for d in depth:
        q = np.radians(50.0 * d)
        for c, v in (("hip_flexion_r", q), ("hip_flexion_l", q), ("knee_angle_r", 2 * q), ("knee_angle_l", 2 * q),
                     ("ankle_angle_r", q), ("ankle_angle_l", q), ("pelvis_ty", 0.93 - 0.25 * d)):
            model.getCoordinateSet().get(c).setValue(state, v, False)
        model.realizePosition(state)
        frames.append([[model.getMarkerSet().get(n).getLocationInGround(state).get(j) for j in range(3)] for n in names])
    X = np.array(frames)
    X[120:135, names.index("LKnee")] = np.nan    # 0.5 s: no lower-body augmented markers there
    X[340:360, names.index("LElbow")] = np.nan   # 0.67 s: arm markers missing; LElbow is the TRC's last column
    augment(MarkerSequence(fps=30.0, marker_names=names, markers=X, frame="yup_world"), 1.75, 70.0).save(tmp_path / "a.npz")
    res = cli.process(tmp_path / "a.npz", tmp_path / "s", exercise="squat", mass_kg=70.0, height_m=1.75)
    qc = res["qc"]
    assert [(s["start_frame"], s["stop_frame"]) for s in qc["segments"]] == [(0, 120), (135, 420)]
    assert [(s["start_frame"], s["stop_frame"]) for s in qc["unsolved"]["spans"]] == [(120, 135)]
    assert qc["missing_target_frames"] == list(range(340, 360)) and qc["ik"]["pass"]
    trc_names, trc, _, _ = read_trc(tmp_path / "s" / "opensim" / "markers_dynamic.trc")
    assert trc_names[-1] == "LElbow" and np.isnan(trc[340:360, -1]).all() and np.isnan(trc[120:135]).all()
    assert read_table(res["motion"]).time[0] == pytest.approx(135 / 30.0)
    reps = res["metrics"]["reps"]
    hit = [r["start_s"] <= 359 / 30.0 and r["stop_s"] >= 340 / 30.0 for r in reps]
    assert any(hit) and [r["contains_missing_markers"] for r in reps] == hit
    assert "frames not solved" in (tmp_path / "s" / "report.html").read_text()


def test_person_model_keeps_the_bones_across_sessions(selftest_run, tmp_path):
    """Build a person from the selftest session, re-process another recording of that body with it: the bones
    are the person's (same scale factors and segment lengths), not re-fitted to the new frames."""
    from rehabtwin import person
    out, res, _ = selftest_run
    d = tmp_path / "person"
    person.init(d, "SYNTHETIC-NOT-A-PATIENT")
    with pytest.raises(person.PersonRefused, match="synthetic session"):
        person.build_from_session(d, out)
    rec = person.build_from_session(d, out, allow_synthetic=True)
    assert rec["synthetic"] and rec["model"]["scale_set"] == res["qc"]["scale_factors"]
    assert rec["layers"]["bone_geometry"]["tier"] == "C"
    assert 0.3 < rec["segments"]["thigh_r"]["length_m"] < 0.6 and set(rec["keypoint_segments"]) == set(person.KEYPOINT_SEGMENTS)

    seq2, truth2, truth_model2 = cli._synth(tmp_path / "s2", seed=1)
    alone = cli.process(seq2, tmp_path / "alone", reference=truth2, reference_model=truth_model2,
                        reference_system="synthetic truth")
    used = cli.process(seq2, tmp_path / "with", reference=truth2, reference_model=truth_model2,
                       reference_system="synthetic truth", person=d)
    sc = used["qc"]["scaling"]
    assert sc["person_model"]["version"] == rec["version"] and sc["max_scale_factor_difference"] < 1e-4
    assert used["session"]["person_model"]["kind"] == "scaled-generic" and records.validate(used["session"], "session")
    segs, _ = person.model_lengths(tmp_path / "with" / used["session"]["pipeline"]["outputs"]["model"])
    for k, v in rec["segments"].items():
        assert abs(segs[k] - v["length_m"]) < 1e-3, k
    # each session's own scaling moves the bones a little; the person's stay put and still track as well
    drift = max(abs(a - b) for body, f in rec["model"]["scale_set"].items()
                for a, b in zip(f, alone["qc"]["scale_factors"][body]))
    assert drift > sc["max_scale_factor_difference"]
    per, per_alone = used["validation"]["per_coordinate"], alone["validation"]["per_coordinate"]
    worse = {c: (per[c]["rmse_deg"], per_alone[c]["rmse_deg"]) for c in cli.SELFTEST_LIMITS
             if per[c]["rmse_deg"] > per_alone[c]["rmse_deg"] + 0.1}
    assert worse == {}
    assert abs(sc["recording_scale"]["recording_vs_person"] - 1.0) < 0.02 and "rescaled_by" not in sc["recording_scale"]
    with pytest.raises(person.PersonRefused, match="itself processed with a person model"):
        person.build_from_session(d, tmp_path / "with", allow_synthetic=True)

    # a recording 15% small: one camera's size is a guess, so it is brought to the person's; a calibrated one
    # that far off is another body or a fault
    from rehabtwin.sequence import MarkerSequence
    small = MarkerSequence.load(seq2)
    for k in ("markers", "joints", "static_markers", "static_joints"):     # every point the front end gave
        if getattr(small, k, None) is not None:
            setattr(small, k, getattr(small, k) * 0.85)
    small.meta["metric_scale"] = False
    small.save(tmp_path / "small.npz")
    mono = cli.process(tmp_path / "small.npz", tmp_path / "small", reference=truth2, reference_model=truth_model2,
                       reference_system="synthetic truth", person=d)
    rs = mono["qc"]["scaling"]["recording_scale"]
    assert rs["rescaled_by"] == pytest.approx(1 / 0.85, abs=0.02) and not rs["scale_measured"]
    per_small = mono["validation"]["per_coordinate"]
    assert {c: per_small[c]["rmse_deg"] for c in cli.SELFTEST_LIMITS
            if per_small[c]["rmse_deg"] > per_alone[c]["rmse_deg"] + 0.3} == {}
    assert mono["qc"]["ik"]["marker_rms_m"]["mean"] < used["qc"]["ik"]["marker_rms_m"]["mean"] + 0.002
    small.meta["metric_scale"] = True
    small.save(tmp_path / "small_metric.npz")
    with pytest.raises(ValueError, match="0.85 times the person model's size"):
        cli.process(tmp_path / "small_metric.npz", tmp_path / "small_metric", person=d)
    assert not (tmp_path / "small_metric" / "opensim" / "markers_dynamic.trc").exists()   # refused before writing


def test_limb_alignment_contract_and_safety_flags(selftest_run, tmp_path):
    """Genu valgum on a radiograph personalises the knee of every session; the camera's standing estimate is
    screening only; structural alignment holds valgus cues for a clinician-set target; a clinician safety flag
    holds cues and assistance what-ifs at its region; the person model exports a valid twin manifest."""
    from rehabtwin import alignment, person
    from rehabtwin.correction import CorrectionRefused
    out, res, _ = selftest_run
    est = res["qc"]["static_alignment"]
    assert est["status"] == "estimated" and est["uncertainty"].startswith("not yet measured")
    assert res["qc"]["alignment"]["limb_alignment"] is None              # the camera never changes the model
    d = tmp_path / "person"
    person.init(d, "SYNTHETIC-NOT-A-PATIENT", age_years=70, sex="female")
    person.build_from_session(d, out, allow_synthetic=True)
    rec = person.set_alignment_screening(d, out)
    assert "limb_alignment" not in rec and rec["alignment_screening"]["status"] == "estimated"
    lay = rec["layers"]["joint_alignment"]
    assert "screening only" in lay["status"] and lay["tier"] is None    # the estimate doesn't fill the layer
    assert person.manifest(d)["accuracy_layers"]["joint_alignment"]["status"] == "generic"
    xray = tmp_path / "xray.json"
    xray.write_text(json.dumps({"measured_at": "2026-09-01", "structural": True, "diagnosis": "genu valgum",
                                "right": {"mechanical_axis_hka_deg": 9.0, "source": "radiograph"},
                                "left": {"mechanical_axis_hka_deg": 7.0, "source": "radiograph"}}))
    rec = person.set_limb_alignment(d, xray)
    assert rec["limb_alignment"]["tier"] == "B" and set(rec["limb_alignment"]["holds"]) == {"knee_r.frontal", "knee_l.frontal"}
    assert rec["layers"]["joint_alignment"]["tier"] == "B" and "genu valgum" in person.summary(rec)
    exam = tmp_path / "exam.json"
    exam.write_text(json.dumps({"measured_at": "2026-10-01", "right": {"mechanical_axis_hka_deg": 2.0,
                                                                       "source": "clinical-measurement"}}))
    with pytest.raises(person.PersonRefused, match="Tier B limb alignment"):
        person.set_limb_alignment(d, exam)
    camera = tmp_path / "camera.json"
    camera.write_text(json.dumps({"measured_at": "2026-10-01", "right": {"mechanical_axis_hka_deg": 9.0,
                                                                         "source": "standing frame markers"}}))
    with pytest.raises(person.PersonRefused, match="screening only"):
        person.set_limb_alignment(d, camera)

    seq2, truth2, truth_model2 = cli._synth(tmp_path / "s2", seed=1)
    used = cli.process(seq2, tmp_path / "with", reference=truth2, reference_model=truth_model2,
                       reference_system="synthetic truth", person=d)
    knee = used["qc"]["alignment"]["limb_alignment"]["knee"]
    assert knee["r"]["after_deg"] == pytest.approx(9.0, abs=0.05) and knee["l"]["after_deg"] == pytest.approx(7.0, abs=0.05)
    m = opensim.Model(str(tmp_path / "with" / used["session"]["pipeline"]["outputs"]["model"]))
    assert alignment.model_knee_frontal(m, m.initSystem(), "r") == pytest.approx(9.0, abs=0.1)
    result, _ = cli.cue_replay(tmp_path / "with", "squat_posture")
    pr = result["summary"]["per_rule"]
    assert "genu valgum" in pr["knee_valgus_r"]["gate"] and pr["knee_valgus_r"]["standing_value"] == pytest.approx(9.0, abs=1.0)
    assert "genu valgum" not in (pr["trunk_forward"]["gate"] or "")          # the knee holds only knee cues

    flags = tmp_path / "flags.json"
    flags.write_text(json.dumps([{"flag": "joint-instability", "body_region": "right knee", "status": "suspected",
                                  "set_by": "clinician", "set_at": "2026-10-20", "restrictions": ["no valgus loading"]}]))
    person.set_safety_flags(d, flags)
    result, _ = cli.cue_replay(tmp_path / "with", "squat_posture")          # read from the person folder, now
    pr = result["summary"]["per_rule"]
    assert "clinician safety flag" in pr["knee_valgus_r"]["gate"] and "clinician safety flag" not in pr["knee_valgus_l"]["gate"]
    assert set(result["summary"]["safety_holds"]) == {"knee_r"}
    with pytest.raises(CorrectionRefused, match="no assistance what-if at this joint"):
        cli.muscle_study(tmp_path / "with", assist=["knee_angle_r=40"], illustrative=True, view_3d=False)
    flags.write_text(json.dumps([{"flag": "joint-instability", "body_region": "right knee", "status": "suspected",
                                  "set_by": "physio", "set_at": "2026-10-20"}]))
    with pytest.raises(person.PersonRefused, match="never sets or clears"):
        person.set_safety_flags(d, flags)

    man = person.manifest(d)                       # checked against schemas/twin-manifest.schema.json inside
    assert man["limb_alignment"]["right"] == {"mechanical_axis_hka_deg": 9.0, "source": "radiograph"}
    assert man["accuracy_layers"]["joint_alignment"]["status"] == "personalised" and man["twin_tier"] == "C"
    assert man["safety_flags"][0]["body_region"] == "right knee" and man["body_state"]["age_parameter_set"] == "older-adult"
    assert man["muscle_parameters"]["source"] == "generic-scaled" and man["provenance"]["limb_alignment"]["tier"] == "B"


def test_marker_rescale_and_marker_to_joint(tmp_path):
    """Markers placed for another model's bones move to the same place on this model's: rescaled along their
    body, or put on the joint centre they name."""
    from rehabtwin import opensim_stage
    cfg = load_config("mediapipe_lstm_pose2sim")
    cfg["marker_rescale"] = [{"markers": ["r_ankle_study"], "factors": [1.0, 1.075, 1.0], "why": "test"}]
    cfg["marker_to_joint"] = {"markers": {"RHJC_study": "femur_r"}, "why": "test"}
    path, names, notes = opensim_stage.prepare_model(cfg, tmp_path, {"r_ankle_study", "RHJC_study", "LHJC_study"})
    m = opensim.Model(str(path))
    s = m.initSystem()
    loc = lambda n: [m.getMarkerSet().get(n).get_location().get(i) for i in range(3)]
    assert loc("r_ankle_study") == pytest.approx([-0.02, -0.385 * 1.075, 0.053], abs=1e-6)
    hip = m.getBodySet().get("femur_r").findStationLocationInAnotherFrame(s, opensim.Vec3(0, 0, 0), m.getBodySet().get("pelvis"))
    assert loc("RHJC_study") == pytest.approx([hip.get(i) for i in range(3)], abs=1e-9)
    assert loc("LHJC_study") == pytest.approx([-0.056276, -0.07849, -0.07726], abs=1e-6)     # not listed: unchanged
    assert any("rescaled 1 markers" in n for n in notes) and any("RHJC_study" in n for n in notes)


def test_person_bones_from_skel_joint_centres(selftest_run, tmp_path):
    """``person bones``: SKEL joint centres 1.1x the generic model's give 1.1 on every body, a model whose
    thigh is 1.1x the generic one at the measured mass; a session-built model is kept and compared."""
    from rehabtwin import person, skel_bones, tiers
    generic = resolve(CFG["model"])
    gen = skel_bones.generic_origins(generic)
    bones = ("pelvis", "femur_r", "tibia_r", "talus_r", "calcn_r", "toes_r", "femur_l", "tibia_l", "talus_l", "calcn_l",
             "toes_l", "humerus_r", "ulna_r", "radius_r", "hand_r", "humerus_l", "ulna_l", "radius_l", "hand_l")
    v = np.array([1.1 * np.array([-gen[b][2], gen[b][1], gen[b][0]]) for b in bones])     # OpenSim -> SMPL axes
    np.savez(tmp_path / "basicmodel_m_lbs_10_207_0_v1.1.0.npz", v_template=v, shapedirs=np.zeros((len(v), 3, 1)),
             f=np.array([[0, 1, 2]]))
    np.savez(tmp_path / "skel_male.npz", J_regressor_osim=np.eye(len(v)), bone_names=np.array(bones), skin_template_v=v,
             skin_template_f=np.array([[0, 1, 2]]), shapedirs=np.zeros((len(v), 3, 1)))
    d = tmp_path / "P"
    person.init(d, "P", height_m=1.8, mass_kg=77.0, sex="male")
    rec = person.load(d)
    rec["surface_shape"] = {"betas": [], "height_m": 1.8, "mass_kg_from_volume": 77.0, "bmi_from_volume": 23.8,
                            "checks": {}, "source": {"recording": "toy", "body_model": {
        "kind": "SMPL", "file": "toy", "sha256": tiers.sha256(tmp_path / "basicmodel_m_lbs_10_207_0_v1.1.0.npz")}}}
    person.save(d, rec, "toy SMPL surface")
    rec = person.set_bones(d, tmp_path, tmp_path, config="skel105_pose2sim")
    assert rec["skel_bones"]["source"] == "shape" and rec["model"]["built_from"]["method"] == "skel"
    assert {tuple(f) for f in rec["model"]["scale_set"].values()} == {(1.1, 1.1, 1.1)}
    m = opensim.Model(str(d / "model.osim"))
    assert m.getTotalMass(m.initSystem()) == pytest.approx(77.0, abs=1e-6)
    segs, _ = person.model_lengths(generic)
    assert rec["segments"]["thigh_r"]["length_m"] == pytest.approx(1.1 * segs["thigh_r"], abs=1e-3)
    assert rec["layers"]["bone_geometry"]["tier"] == "C" and "SKEL" in person.summary(rec)
    out, _, _ = selftest_run
    s = tmp_path / "S"
    ref = json.loads((out / "session.json").read_text())["person_ref"]
    person.init(s, ref, sex="male")
    built = person.build_from_session(s, out, allow_synthetic=True)
    rec2 = person.load(s)
    rec2["surface_shape"] = rec["surface_shape"]
    person.save(s, rec2, "toy SMPL surface")
    kept = person.set_bones(s, tmp_path, tmp_path)
    assert kept["model"]["sha256"] == built["model"]["sha256"] and kept["person_ref"] == ref
    assert set(kept["skel_bones"]["vs_model_cm"]) >= {"thigh_r", "hip_width"}
    replaced = person.set_bones(s, tmp_path, tmp_path, replace=True)
    assert replaced["model"]["built_from"]["method"] == "skel"


def test_personalised_person_model_is_used_as_it_is(selftest_run, tmp_path):
    """An imaging-personalised model (here: the synthetic generator's truth model with a Tier B record) is not
    re-scaled: unit scale factors, only the segment masses follow the person's measured mass."""
    from rehabtwin import person, tiers
    from rehabtwin.sequence import MarkerSequence
    out, _, _ = selftest_run
    seq = MarkerSequence.load(out / "skel_seq.npz")
    seq.meta.update(synthetic=False, person_ref="P-TEST")      # stands in for a real recording of this person
    seq.meta.pop("mass_kg", None)
    seq.save(tmp_path / "seq.npz")
    model = out / "truth" / "truth_model.osim"
    prov = tmp_path / "prov.json"
    prov.write_text(json.dumps({"tier": "B", "person_ref": "P-TEST", "model": model.name,
                                "model_sha256": tiers.sha256(model), "evidence": "test stand-in for an MRI model",
                                "approved_by": "test"}))
    d = tmp_path / "person"
    person.init(d, "P-TEST", height_m=1.75, mass_kg=80)
    rec = person.attach_personalised_model(d, model, prov)
    assert rec["layers"]["bone_geometry"]["tier"] == "B" and rec["model"]["kind"] == "personalised"
    res = cli.process(tmp_path / "seq.npz", tmp_path / "s", person=d, tier="B")
    sess = res["session"]
    assert sess["twin_tier"] == "B" and sess["person_model"]["kind"] == "personalised"
    assert res["qc"]["scaling"]["max_scale_factor_difference"] < 1e-4
    assert abs(res["qc"]["scaling"]["recording_scale"]["recording_vs_person"] - 1.0) < 0.03   # the size is checked too
    assert res["qc"]["subject"] == {"mass_kg": 80.0, "mass_source": "measured", "height_m": 1.75,
                                    "mass_from": f"person model v{rec['version']}"}
    assert "used as it is" in sess["accuracy_layers"]["bone_geometry"]["error"]
    m = opensim.Model(str(tmp_path / "s" / sess["pipeline"]["outputs"]["model"]))
    assert abs(m.getTotalMass(m.initSystem()) - 80.0) < 0.01
    segs, _ = person.model_lengths(tmp_path / "s" / sess["pipeline"]["outputs"]["model"])
    assert all(abs(segs[k] - v["length_m"]) < 1e-3 for k, v in rec["segments"].items())
    with pytest.raises(tiers.TierRefused):
        cli.process(tmp_path / "seq.npz", tmp_path / "s2", tier="B")          # the generic model has no record


def test_leg_capacity_scales_with_body_size(selftest_run, tmp_path):
    """Fmax ∝ limb muscle volume / fibre length: heavier and taller -> stronger legs, trunk unchanged."""
    from rehabtwin import capacity
    out, res, _ = selftest_run
    model = out / res["session"]["pipeline"]["outputs"]["model"]
    generic = resolve(CFG["model"])
    small = capacity.scale_model(model, generic, 55.0, 1.60, tmp_path / "small.osim")
    big = capacity.scale_model(model, generic, 110.0, 1.90, tmp_path / "big.osim")
    assert small["muscles_scaled"] == big["muscles_scaled"] == 80
    assert small["leg_fmax_N"]["right"]["scaled"] < small["leg_fmax_N"]["right"]["generic"] < big["leg_fmax_N"]["right"]["scaled"]
    assert big["caveats"][0].startswith("BMI 30.5")
    g, m, b = (opensim.Model(str(p)) for p in (generic, model, tmp_path / "big.osim"))
    v = capacity.limb_muscle_volume_cm3(110.0, 1.90) / capacity.limb_muscle_volume_cm3(**{k: capacity.REFERENCE[k] for k in ("mass_kg", "height_m")})
    for n in ("vaslat_r", "soleus_l"):
        expect = v * g.getMuscles().get(n).getOptimalFiberLength() / m.getMuscles().get(n).getOptimalFiberLength()
        assert b.getMuscles().get(n).getMaxIsometricForce() == pytest.approx(g.getMuscles().get(n).getMaxIsometricForce() * expect, rel=1e-6)
    assert b.getMuscles().get("rect_abd_r").getMaxIsometricForce() == g.getMuscles().get("rect_abd_r").getMaxIsometricForce()
    with pytest.raises(ValueError, match="already changed"):
        capacity.scale_model(tmp_path / "big.osim", generic, 80.0, 1.80, tmp_path / "twice.osim")


def test_measured_muscle_size_and_fat_fraction_set_capacity(selftest_run, tmp_path):
    """Imaging replaces the regression where it measures: Fmax = σ·V·q/lopt per muscle, group volumes split by
    the model's reference shares, fat fraction against healthy young muscle."""
    from rehabtwin import capacity
    out, res, _ = selftest_run
    model = out / res["session"]["pipeline"]["outputs"]["model"]
    generic = resolve(CFG["model"])
    g, m = (opensim.Model(str(p)) for p in (generic, model))
    vref = {n: g.getMuscles().get(n).getMaxIsometricForce() * g.getMuscles().get(n).getOptimalFiberLength() * 100 / 60.0
            for n in ("recfem_r", "vaslat_r", "vasmed_r", "vasint_r")}
    assert sum(vref.values()) == pytest.approx(853 + 443 + 281 + 277, abs=2)     # the model's own quadriceps volume
    imaging = {"method": "MRI test", "date": "2026-09-14",
               "muscles": {"quadriceps_r": {"volume_cm3": 1.5 * sum(vref.values())},   # 50 % more than the reference
                           "hamstrings_l": {"fat_fraction": 0.20},                       # fatty, size from the regression
                           "soleus_r": {"volume_cm3": 454.0 * 0.8, "fat_fraction": 0.026}}}
    rec = capacity.scale_model(model, generic, 80.0, 1.80, tmp_path / "imaged.osim", imaging=imaging)
    b = opensim.Model(str(tmp_path / "imaged.osim"))
    lratio = lambda n: g.getMuscles().get(n).getOptimalFiberLength() / m.getMuscles().get(n).getOptimalFiberLength()
    f = lambda mdl, n: mdl.getMuscles().get(n).getMaxIsometricForce()
    v = capacity.limb_muscle_volume_cm3(80, 1.8) / capacity.limb_muscle_volume_cm3(75.337, 1.70)
    assert f(b, "vaslat_r") == pytest.approx(f(g, "vaslat_r") * 1.5 * lratio("vaslat_r"), rel=1e-6)
    assert f(b, "semimem_l") == pytest.approx(f(g, "semimem_l") * v * 0.80 / (1 - 0.026) * lratio("semimem_l"), rel=1e-6)
    assert f(b, "soleus_r") == pytest.approx(f(g, "soleus_r") * 454.0 * 0.8 / (f(g, "soleus_r") * g.getMuscles().get(
        "soleus_r").getOptimalFiberLength() * 100 / 60) * lratio("soleus_r"), rel=1e-4)
    assert f(b, "vaslat_l") == pytest.approx(f(g, "vaslat_l") * v * lratio("vaslat_l"), rel=1e-6)    # not imaged
    assert rec["sources"] == {"measured": 4, "measured + fat fraction": 1, "regression": 71, "regression + fat fraction": 4}
    # imaging alone (no measured mass): the rest stays generic in size
    rec = capacity.scale_model(model, generic, None, None, tmp_path / "only.osim", imaging=imaging)
    o = opensim.Model(str(tmp_path / "only.osim"))
    assert f(o, "vaslat_l") == pytest.approx(f(g, "vaslat_l") * lratio("vaslat_l"), rel=1e-6)
    assert rec["sources"]["generic"] == 71 and "subject" not in rec


def test_dxa_sizes_each_leg_and_age_sex_sizes_the_default(selftest_run, tmp_path):
    """Leg volume, best first: DXA per leg (McCarthy 2023), then age, sex, height and mass (NHANES), then height
    and mass (Handsfield); the generic share per muscle within a leg either way, imaging still per muscle."""
    from rehabtwin import capacity
    out, res, _ = selftest_run
    model = out / res["session"]["pipeline"]["outputs"]["model"]
    generic = resolve(CFG["model"])
    g, m = (opensim.Model(str(p)) for p in (generic, model))
    f = lambda mdl, n: mdl.getMuscles().get(n).getMaxIsometricForce()
    lratio = lambda n: g.getMuscles().get(n).getOptimalFiberLength() / m.getMuscles().get(n).getOptimalFiberLength()
    ref_leg = sum(f(g, b + "_r") * g.getMuscles().get(b + "_r").getOptimalFiberLength() * 100 / 60
                  for b in capacity.LEG_MUSCLES)
    assert ref_leg == pytest.approx(7089, abs=5)
    rec = capacity.scale_model(model, generic, 80.0, 1.80, tmp_path / "dxa.osim", dxa_leg_lean_kg={"_r": 9.5, "_l": 8.0})
    d = opensim.Model(str(tmp_path / "dxa.osim"))
    for n, lean in (("vaslat_r", 9.5), ("soleus_l", 8.0)):
        k = capacity.leg_muscle_cm3(lean) / ref_leg * lratio(n)
        assert f(d, n) == pytest.approx(f(g, n) * k, rel=1e-3)
    assert rec["leg_source"] == "dxa" and rec["sources"] == {"dxa": 80}
    assert rec["leg_muscle_cm3"] == {"right": round(capacity.leg_muscle_cm3(9.5)), "left": round(capacity.leg_muscle_cm3(8.0))}
    assert rec["leg_fmax_N"]["right"]["scaled"] > rec["leg_fmax_N"]["left"]["scaled"]
    imaged = capacity.scale_model(model, generic, 80.0, 1.80, tmp_path / "both.osim", dxa_leg_lean_kg={"_r": 9.5, "_l": 8.0},
                                  imaging={"muscles": {"quadriceps_r": {"volume_cm3": 2000}}})
    assert imaged["sources"] == {"dxa": 76, "measured": 4}
    old = capacity.scale_model(model, generic, 68.0, 1.62, tmp_path / "old.osim", age_years=70, male=False)
    assert old["leg_source"] == "anthropometry" and old["subject"]["sex"] == "female"
    assert old["leg_muscle_cm3"]["right"] == round(capacity.leg_muscle_cm3(capacity.predicted_leg_lean_kg(70, False, 1.62, 68)))
    young = capacity.scale_model(model, generic, 68.0, 1.62, tmp_path / "young.osim")
    assert old["leg_fmax_N"]["right"]["scaled"] < 0.8 * young["leg_fmax_N"]["right"]["scaled"]
    beyond = capacity.scale_model(model, generic, 68.0, 1.62, tmp_path / "beyond.osim", age_years=91, male=False)
    assert beyond["leg_source"] == "regression" and beyond["caveats"][0].startswith("Age 91 is outside")


def test_dxa_scan_sets_segment_masses_in_the_muscle_model(selftest_run, tmp_path):
    """cli._capacity_model with a person's DXA scan: legs sized per side, each region's mass share from the scan,
    total body mass unchanged."""
    import shutil

    from rehabtwin import dxa
    out, _, _ = selftest_run
    s = tmp_path / "s"
    shutil.copytree(out, s, ignore=shutil.ignore_patterns("muscles", "correction", "strength", "capacity"))
    sess = json.loads((s / "session.json").read_text())
    scan = {"method": "DXA (test)", "date": "2026-10-01", "sha256": "x",
            "regions": {"left_arm": {"lean_kg": 3.0, "fat_kg": 1.2, "bmc_kg": 0.2},
                        "right_arm": {"lean_kg": 3.2, "fat_kg": 1.2, "bmc_kg": 0.2},
                        "left_leg": {"lean_kg": 8.6, "fat_kg": 3.5, "bmc_kg": 0.5},
                        "right_leg": {"lean_kg": 9.4, "fat_kg": 3.4, "bmc_kg": 0.5},
                        "trunk": {"lean_kg": 27.0, "fat_kg": 10.0, "bmc_kg": 0.8},
                        "head": {"lean_kg": 3.3, "fat_kg": 1.0, "bmc_kg": 0.5}}}
    scan["checks"] = dxa.check(scan)
    person_rec = {"person_ref": sess["person_ref"], "version": 3, "dxa": scan, "sex": "male",
                  "anthropometrics": {"age_years": {"value": 60, "measured_at": "2026-10-01T00:00:00+00:00"}}}
    body_mass = cli._session_mass(s, allow_assumed_mass=True)
    path, rec = cli._capacity_model(s, sess, body_mass, True, person_rec)
    assert rec["leg_source"] == "dxa" and rec["dxa"]["date"] == "2026-10-01"
    before = opensim.Model(str(s / sess["pipeline"]["outputs"]["model"]))
    after = opensim.Model(str(path))
    mass = lambda mdl, names: sum(mdl.getBodySet().get(b).getMass() for b in names)
    total = lambda mdl: sum(mdl.getBodySet().get(i).getMass() for i in range(mdl.getBodySet().getSize()))
    assert total(after) == pytest.approx(total(before), rel=1e-9)
    scanned = dxa.region_masses(scan)
    for region, bodies in dxa.BODIES.items():
        assert mass(after, bodies) / total(after) == pytest.approx(scanned[region] / sum(scanned.values()), rel=1e-6)
        assert rec["mass_distribution"]["regions"][region]["dxa_share"] == pytest.approx(
            scanned[region] / sum(scanned.values()), abs=1e-4)
    fem = lambda mdl: mdl.getBodySet().get("femur_r")
    k = rec["mass_distribution"]["regions"]["right_leg"]["factor"]
    assert fem(after).getMass() == pytest.approx(fem(before).getMass() * k, rel=1e-3)
    assert fem(after).getInertia().getMoments().get(0) == pytest.approx(
        fem(before).getInertia().getMoments().get(0) * k, rel=1e-3)
    assert "mass_distribution" in cli._capacity_summary(rec)
    bad = {**scan, "regions": {**scan["regions"], "head": {"lean_kg": 30.0, "fat_kg": 5.0, "bmc_kg": 0.5}}}
    with pytest.raises(ValueError, match="more than"):
        dxa.apply_mass_distribution(opensim.Model(str(s / sess["pipeline"]["outputs"]["model"])), bad)


def test_knee_reaction_is_the_legs_ground_force_without_muscles(selftest_run, tmp_path, monkeypatch):
    """Frames and signs of the knee load (rehabtwin/joint_load.py): with ideal torque actuators instead of muscles,
    the femur pushes on the tibia with the leg's ground force less the shank and foot weight (slow squat:
    quasi-static), so tibiofemoral compression is -y in the tibia frame."""
    from rehabtwin import muscles
    from rehabtwin.io_formats import to_degrees
    out, res, _ = selftest_run
    rep = res["metrics"]["reps"][0]
    m = opensim.Model(str(out / res["session"]["pipeline"]["outputs"]["model"]))
    fs = m.updForceSet()
    for i in reversed(range(fs.getSize())):
        if fs.get(i).getConcreteClassName().endswith("Muscle"):
            fs.remove(i)
    m.finalizeConnections()
    m.initSystem()
    m.printToXML(str(tmp_path / "torques.osim"))
    reserves = muscles.reserves_xml          # ideal torque actuators carry the joints instead of the muscles
    monkeypatch.setattr(muscles, "reserves_xml", lambda *a, **k: reserves(*a, **{**k, "reserve_force": 500.0}))
    r = muscles.run(tmp_path / "torques.osim", out / res["session"]["pipeline"]["outputs"]["motion"], tmp_path,
                    start=rep["peak_s"] - 0.3, stop=rep["peak_s"] + 0.3, joint_load=True)
    run = tmp_path / "measured"
    jr, grf = read_table(run / "jr_JointReaction_ReactionLoads.sto"), read_table(run / "grf.mot")
    model = opensim.Model(str(run / "model_dynamics.osim"))
    state = model.initSystem()
    tab = to_degrees(read_table(run / "motion.mot"), model)
    cs = model.getCoordinateSet()
    bodies = model.getBodySet()
    for k in (0, len(jr.time) // 2, len(jr.time) - 1):
        muscles._set_state(model, state, tab, int(np.argmin(np.abs(tab.time - jr.time[k]))), cs,
                           [c for c in tab.columns if cs.contains(c)])
        for s in "rl":
            R = bodies.get(f"tibia_{s}").getTransformInGround(state).R()
            R = np.array([[R.get(i, j) for j in range(3)] for i in range(3)])
            ground = np.array([np.interp(jr.time[k], grf.time, grf.col(f"ground_force_{s}_v{a}")) for a in "xyz"])
            weight = 9.81 * sum(bodies.get(f"{b}_{s}").getMass() for b in ("tibia", "talus", "calcn", "toes"))
            expect = R.T @ -(ground - [0.0, weight, 0.0])
            got = np.array([jr.col(f"walker_knee_{s}_on_tibia_{s}_in_tibia_{s}_f{a}")[k] for a in "xyz"])
            assert np.abs(got - expect).max() < 0.02 * np.linalg.norm(ground), (s, k, got, expect)
    assert r["knee_load"]["r"]["peak_compression_N"] == pytest.approx(-min(jr.col("walker_knee_r_on_tibia_r_in_tibia_r_fy")),
                                                                      abs=0.1)


def test_joint_load_scenarios_within_one_person(selftest_run, tmp_path):
    """Knee load with the person's DXA: less fat lowers the load about in proportion on the replayed motion (the
    published 4:1 is quoted, never output); a stronger quadriceps eases effort, and its load change is shown as it
    comes out; every change carries its ground-force band; no DXA table, no fat scenario."""
    import shutil

    from rehabtwin import joint_load, person
    out, res, _ = selftest_run
    s = tmp_path / "s"
    shutil.copytree(out, s, ignore=shutil.ignore_patterns("muscles", "correction", "strength", "capacity", "feedback"))
    rep = res["metrics"]["reps"][0]
    d = tmp_path / "person"
    person.init(d, res["session"]["person_ref"], mass_kg=res["qc"]["subject"]["mass_kg"])
    window = {"start": rep["peak_s"] - 0.25, "stop": rep["peak_s"] + 0.25, "view_3d": False, "person": d}
    with pytest.raises(SystemExit, match="DXA regional table"):
        cli.muscle_study(s, joint_load=True, fat_change_kg=-5.0, **window)
    with pytest.raises(SystemExit, match="joint-load"):
        cli.muscle_study(s, strengthen=["quadriceps_r=1.2"], **window)
    with pytest.raises(SystemExit, match="above 1"):
        cli.muscle_study(s, joint_load=True, strengthen=["quadriceps_r=0.8"], **window)
    regions = {"left_arm": (3.0, 1.0, 0.17), "right_arm": (3.1, 1.0, 0.18), "left_leg": (9.5, 3.2, 0.5),
               "right_leg": (9.6, 3.2, 0.5), "trunk": (25.0, 7.0, 0.8), "head": (3.3, 0.9, 0.55)}
    (tmp_path / "dxa.json").write_text(json.dumps({"method": "DXA (test)", "date": "2026-10-28", "regions": {
        r: {"lean_kg": a, "fat_kg": b, "bmc_kg": c} for r, (a, b, c) in regions.items()}}))
    person.set_dxa(d, tmp_path / "dxa.json")
    study, mdir = cli.muscle_study(s, joint_load=True, fat_change_kg=-5.0, strengthen=["quadriceps_r=1.2"],
                                   grf_sensitivity=0.1, **window)
    jl = study["joint_load"]
    base = jl["baseline"]
    for side in "rl":
        assert 1.5 < base[side]["peak_compression_bw"] < 12 and base[side]["knee_flexion_at_peak_deg"] > 60
        lo, hi = jl["baseline_band_over_grf_split"][side]
        assert lo <= base[side]["peak_compression_N"] <= hi and hi > lo
    fat = jl["scenarios"]["fat -5 kg"]
    mass_pct = fat["mass_change"]["pct"]
    assert fat["mass_change"]["kg"] == pytest.approx(-5.0, abs=0.01)
    for side in "rl":
        p = fat["knee"][side]["peak"]
        assert p["change_N"] < 0 and 0.5 < p["change_pct"] / mass_pct < 2.0      # about proportional
        assert p["robust_to_grf_split"] and p["change_pct_range_over_grf_split"][1] < 0
    assert fat["published_evidence"] == joint_load.MESSIER and "4:1" not in fat["reading"]
    strong = jl["scenarios"]["quadriceps_r at 120%"]
    q = strong["effort"]["quadriceps_r"]
    assert q["other"] < q["base"] and joint_load.STRENGTH_READING in strong["reading"]
    assert "published_evidence" not in strong
    assert jl["scenarios"]["fat -5 kg + quadriceps_r at 120%"]["kind"] == "combined"
    assert "assumption" in jl["labels"]["fat_provenance"] and "safety" not in jl["labels"]
    page = (mdir / "muscles.html").read_text()
    assert "Knee joint load" in page and "not model output" in page and page.count("<svg") >= 3
