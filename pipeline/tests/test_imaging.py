"""Muscle size and quality from imaging, and bone density (rehabtwin/capacity.py, bone.py, person.py) without OpenSim.

The capacity arithmetic through OpenSim is in test_pipeline.py.
"""
import json

import pytest

from rehabtwin import bone, capacity, person
from rehabtwin.correction import CorrectionRefused


def _dxa(**over):
    rec = {"method": "DXA (test scanner)", "date": "2026-09-01", "age_years": 62, "sex": "male",
           "sites": {"femoral_neck": {"bmd_g_cm2": 0.62, "t_score": -2.7, "z_score": -1.2},
                     "lumbar_spine_L1_L4": {"bmd_g_cm2": 0.95, "t_score": -1.4, "z_score": 0.1}}}
    rec.update(over)
    return rec


def test_bone_density_categories_follow_the_score_the_person_needs():
    c = bone.classify(_dxa())                                      # man >= 50: T-score
    assert (c["category"], c["site"], c["value"]) == ("osteoporosis", "femoral_neck", "T-score -2.7")
    assert c["per_site"]["lumbar_spine_L1_L4"]["category"] == "low bone mass"
    young = bone.classify(_dxa(age_years=35))                      # man < 50: Z-score, same scan
    assert young["category"] == "within the expected range for age" and young["value"] == "Z-score -1.2"
    with pytest.raises(ValueError, match="postmenopausal"):
        bone.classify(_dxa(sex="female"))
    assert bone.classify(_dxa(sex="female", postmenopausal=True))["category"] == "osteoporosis"
    low_z = _dxa(age_years=40, sex="female", postmenopausal=False)
    low_z["sites"]["femoral_neck"]["z_score"] = -2.3
    assert bone.classify(low_z)["category"] == "below the expected range for age"
    qct = {"method": "QCT", "date": "2026-09-01", "sites": {"lumbar_spine_L1_L2": {"vbmd_mg_cm3": 95}}}
    assert bone.classify(qct)["category"] == "low bone mass"
    qct["sites"]["lumbar_spine_L1_L2"]["vbmd_mg_cm3"] = 72
    assert bone.classify(qct)["category"] == "osteoporosis"


def test_bone_density_refuses_what_is_not_a_calibrated_density():
    with pytest.raises(ValueError, match="Hounsfield"):
        bone.classify({"method": "CT abdomen", "date": "2026-01-01", "sites": {"lumbar_spine_L1_L4": {"mean_hu": 110}}})
    with pytest.raises(ValueError, match="Hounsfield"):
        bone.classify({"method": "DXA", "date": "2026-01-01", "sites": {"total_hip": {"mean_hu": 110, "t_score": -1}},
                       "age_years": 60, "sex": "male"})
    with pytest.raises(ValueError, match="date"):
        bone.classify({**_dxa(), "date": ""})
    with pytest.raises(ValueError, match="site"):
        bone.classify(_dxa(sites={"skull": {"t_score": -3}}))
    assert bone.caveat(None).startswith("Bone density not measured")
    assert bone.caveat(bone.classify(_dxa(age_years=35))) is None
    assert "clinician's sign-off" in bone.caveat(bone.classify(_dxa()))


def test_imaging_labels_map_to_model_muscles_without_overlap():
    owner = capacity.check_imaging({"muscles": {"quadriceps_r": {"volume_cm3": 2000},
                                                "vastus_lateralis_l": {"fat_fraction": 0.1},
                                                "soleus_l": {"volume_cm3": 500, "fat_fraction": 0.05}}})
    assert sorted(owner) == ["recfem_r", "soleus_l", "vasint_r", "vaslat_l", "vaslat_r", "vasmed_r"]
    with pytest.raises(ValueError, match="both cover vaslat_r"):
        capacity.check_imaging({"muscles": {"quadriceps_r": {"volume_cm3": 2000}, "vaslat_r": {"volume_cm3": 900}}})
    with pytest.raises(ValueError, match="_r or _l"):
        capacity.check_imaging({"muscles": {"quadriceps": {"volume_cm3": 2000}}})
    with pytest.raises(ValueError, match="fraction in"):
        capacity.check_imaging({"muscles": {"hamstrings_r": {"fat_fraction": 8}}})       # percent, not fraction
    with pytest.raises(ValueError, match="unknown muscle"):
        capacity.check_imaging({"muscles": {"biceps_brachii_r": {"volume_cm3": 300}}})
    with pytest.raises(ValueError, match="needs volume_cm3"):
        capacity.check_imaging({"muscles": {"hamstrings_r": {}}})
    assert any("BMI 35.9" in c for c in capacity.caveats(110, 1.75))
    assert not any(c.startswith("BMI") for c in capacity.caveats(110, 1.75, imaged=80))   # all measured


def test_person_records_imaging_and_bone_density(tmp_path):
    d = tmp_path / "P1"
    person.init(d, "P1", height_m=1.75, mass_kg=70)
    (tmp_path / "mri.json").write_text(json.dumps({
        "method": "MRI 3T Dixon (test)", "date": "2026-09-14",
        "muscles": {"quadriceps_r": {"volume_cm3": 1900, "fat_fraction": 0.06}, "quadriceps_l": {"volume_cm3": 1650}}}))
    rec = person.set_muscle_imaging(d, tmp_path / "mri.json")
    assert rec["layers"]["muscle"]["tier"] == "C" and "covering 8 of 80" in rec["layers"]["muscle"]["status"]
    assert rec["muscle_imaging"]["sha256"] and rec["version"] == 2
    (tmp_path / "dxa.json").write_text(json.dumps({**_dxa(), "approved_by": "radiologist (test)"}))
    rec = person.set_bone_density(d, tmp_path / "dxa.json")
    assert rec["layers"]["bone_density"]["tier"] == "A" and "osteoporosis" in rec["layers"]["bone_density"]["status"]
    text = person.summary(rec)
    assert "quadriceps_r 1900 cm³" in text and "quadriceps_r 6.0 %" in text and "osteoporosis at femoral_neck" in text
    (tmp_path / "bad.json").write_text(json.dumps({"method": "MRI", "date": "x", "muscles": {"quadriceps": {"volume_cm3": 1}}}))
    with pytest.raises(person.PersonRefused, match="_r or _l"):
        person.set_muscle_imaging(d, tmp_path / "bad.json")
    (tmp_path / "nodate.json").write_text(json.dumps({"method": "DXA", "sites": {}}))
    with pytest.raises(person.PersonRefused, match="lacks"):
        person.set_bone_density(d, tmp_path / "nodate.json")
    assert person.load(d)["version"] == 3                                     # refusals changed nothing


def test_manifest_emits_only_recorded_blocks(tmp_path):
    """Safety flags hold every status but 'cleared', so a placeholder 'not-assessed' entry would hold everyone's
    cues: the manifest carries flags and anatomy blocks only when a record put them there."""
    d = tmp_path / "P1"
    person.init(d, "P1", height_m=1.75, mass_kg=70)
    man = person.manifest(d)
    for block in ("safety_flags", "limb_alignment", "bone_quality", "spinopelvic_parameters", "devices_and_prostheses"):
        assert block not in man and block not in person.load(d)
    assert man["muscle_parameters"] == {"source": "generic-scaled", "muscles": []}    # what the model uses, said plainly
    flags = [{"flag": "bone-fragility", "body_region": "whole body", "status": "cleared", "set_by": "clinician",
              "set_at": "2026-10-20"}]
    (tmp_path / "flags.json").write_text(json.dumps(flags))
    person.set_safety_flags(d, tmp_path / "flags.json")
    assert person.manifest(d)["safety_flags"] == flags                         # as the clinician gave them


def test_muscle_study_uses_the_persons_imaging_and_shows_bone_density(tmp_path, monkeypatch):
    from rehabtwin import cli, muscles, strength
    calls, scaled = [], []

    def run(**kw):
        calls.append(kw)
        from pathlib import Path
        Path(kw["out_dir"], kw["label"]).mkdir(parents=True, exist_ok=True)
        return {"label": kw["label"], "exercise": kw["exercise"], "valid_exercise": True, "time_range_s": [0.0, 1.0],
                "grf": {"body_mass_kg": 70.0, "min_vertical_bw": 1.0, "peak_vertical_bw": 1.0,
                        "right_share_range": [0.5, 0.5], "feet_planted": True},
                "group_activation": {"quadriceps_r": {"peak": 0.4}}, "joint_moments": {}, "pelvis_residual_force_N": {},
                "reserve_torque_peaks_Nm": {}, "muscles_saturated": [], "caveats": [muscles.muscle_caveat(kw.get("muscle_model"))],
                "assistive_devices": {"knee_angle_r": {"max_torque_Nm": 40, "direction": "both", "peak_abs_Nm": 20,
                                                       "mean_abs_Nm": 10, "time_at_cap_fraction": 0.0}}}
    monkeypatch.setattr(muscles, "run", run)
    monkeypatch.setattr(muscles, "parse_assist", lambda spec: ("knee_angle_r", 40.0, -1.0, 1.0))
    monkeypatch.setattr(strength, "calibrate", lambda *a, **k: None)
    monkeypatch.setattr(capacity, "scale_model", lambda *a, **k: scaled.append((a, k)) or {
        "method": "m", "factor_median": 1.1, "sources": {"measured": 4, "regression": 76}, "imaging": {"method": "MRI t"},
        "caveats": []})
    monkeypatch.setattr(cli, "resolve", lambda p: p)
    d = tmp_path / "s"
    d.mkdir()
    (d / "session.json").write_text(json.dumps({
        "session_id": "s", "person_ref": "P1", "twin_tier": "C", "started_at": "2026-10-01T09:00:00+00:00",
        "person_model": {"folder": str(tmp_path / "P1")},
        "pipeline": {"front_end": "x", "processing_id": "p0", "config": "skel105_pose2sim.json",
                     "outputs": {"model": "model.osim", "motion": "ik.mot"}}}))
    (d / "metrics.json").write_text(json.dumps({"exercise": "squat", "reps": [{"start_s": 0.0, "stop_s": 1.0}]}))
    (d / "qc.json").write_text(json.dumps({"subject": {"mass_kg": 70.0, "mass_source": "measured", "height_m": 1.75}}))
    p = tmp_path / "P1"
    person.init(p, "P1", height_m=1.75, mass_kg=70)
    (tmp_path / "mri.json").write_text(json.dumps({"method": "MRI t", "date": "2026-09-14",
                                                   "muscles": {"quadriceps_r": {"volume_cm3": 1900}}}))
    person.set_muscle_imaging(p, tmp_path / "mri.json")
    (tmp_path / "dxa.json").write_text(json.dumps(_dxa()))
    person.set_bone_density(p, tmp_path / "dxa.json")
    with pytest.raises(CorrectionRefused, match="exo_torque_derating_factor"):     # low density, no clinician factor
        cli.muscle_study(d, plant=False, view_3d=False, assist=["knee_angle_r=40"], illustrative=True, workers=1)
    (tmp_path / "dxa.json").write_text(json.dumps(_dxa(exo_torque_derating_factor=0.5)))
    with pytest.raises(person.PersonRefused, match="approved_by"):
        person.set_bone_density(p, tmp_path / "dxa.json")
    (tmp_path / "dxa.json").write_text(json.dumps(_dxa(exo_torque_derating_factor=0.5, approved_by="Dr. T")))
    person.set_bone_density(p, tmp_path / "dxa.json")
    study, mdir = cli.muscle_study(d, plant=False, view_3d=False, assist=["knee_angle_r=40"], illustrative=True, workers=1)
    assert study["device_limits"]["applied"] == ["knee_angle_r=20"] and study["device_limits"]["set_by"] == "Dr. T"
    assert scaled[-1][1]["imaging"]["muscles"] == {"quadriceps_r": {"volume_cm3": 1900}}
    assert scaled[-1][0][2:4] == (70.0, 1.75)                                  # the rest by height and mass
    assert study["muscle_model"]["source"].startswith("measured muscle imaging")
    assert study["bone_density"]["category"] == "osteoporosis" and "sign-off" in study["bone_caveat"]
    page = (mdir / "muscles.html").read_text()
    assert "measured leg muscles" in page and "Bone density: osteoporosis" in page
    assert "Force follows contractile volume" in muscles.muscle_caveat(calls[-1]["muscle_model"])
    study, _ = cli.muscle_study(d, plant=False, view_3d=False)
    assert study["bone_caveat"] is None and study["bone_density"]["category"] == "osteoporosis"   # no load what-if
    other = tmp_path / "P2"
    person.init(other, "P2")
    with pytest.raises(person.PersonRefused, match="session of 'P1'"):
        cli.muscle_study(d, plant=False, view_3d=False, person=other)
