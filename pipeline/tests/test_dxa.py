"""The DXA tier and the age-and-sex default (rehabtwin/dxa.py, capacity.py, person.py) without OpenSim.

Per-leg sizing and the segment mass distribution through OpenSim are in test_pipeline.py.
"""
import json

import pytest

from rehabtwin import capacity, dxa, person


def _scan(**over):
    rec = {"method": "DXA (test scanner) whole body", "date": "2026-10-01",
           "regions": {"left_arm": {"lean_kg": 3.0, "fat_kg": 1.2, "bmc_kg": 0.2},
                       "right_arm": {"lean_kg": 3.2, "fat_kg": 1.2, "bmc_kg": 0.2},
                       "left_leg": {"lean_kg": 8.6, "fat_kg": 3.5, "bmc_kg": 0.5},
                       "right_leg": {"lean_kg": 9.4, "fat_kg": 3.4, "bmc_kg": 0.5},
                       "trunk": {"lean_kg": 27.0, "fat_kg": 10.0, "bmc_kg": 0.8},
                       "head": {"lean_kg": 3.3, "fat_kg": 1.0, "bmc_kg": 0.5}}}
    rec.update(over)
    return rec


def test_dxa_record_checks():
    c = dxa.check(_scan(), mass_kg=80.0)
    assert c["distribution"] and c["mass_kg"] == 77.5 and c["mass_check"]["difference"] == pytest.approx(-0.031, abs=1e-3)
    assert dxa.leg_lean_kg(_scan()) == {"_r": 9.4, "_l": 8.6}
    legs_only = _scan(regions={k: {"lean_kg": v["lean_kg"]} for k, v in _scan()["regions"].items() if "leg" in k})
    assert dxa.check(legs_only, 80.0) == {"distribution": False, "mass_kg": None, "mass_check": None}
    grams = _scan()
    grams["regions"]["trunk"]["lean_kg"] = 27000
    for bad, match in ((_scan(method="BIA scale"), "start with 'DXA'"), (_scan(date=""), "date"), (grams, "grams"),
                       (_scan(regions={"right_leg": {"lean_kg": 9}}), "left_leg.lean_kg"),
                       (_scan(regions={**_scan()["regions"], "pelvis": {"lean_kg": 1}}), "pelvis"),
                       (_scan(regions={**_scan()["regions"], "left_leg": {"lean_kg": 0.9}}), "2-25 kg"),
                       (_scan(regions={**_scan()["regions"], "trunk": {"lean": 27}}), "lean_kg, fat_kg and bmc_kg")):
        with pytest.raises(ValueError, match=match):
            dxa.check(bad)
    with pytest.raises(ValueError, match="another person's scan"):
        dxa.check(_scan(), mass_kg=100.0)                    # 77.5 kg scanned, -22 %
    f = dxa.fat_summary(_scan())
    assert f["total"]["fat_kg"] == pytest.approx(20.3) and f["right_leg"]["fat_pct"] == pytest.approx(25.6, abs=0.1)


def test_leg_muscle_ladder_without_opensim():
    """Reference subject of the generic model (25-year-old man, 1.70 m, 75.3 kg): ~8.9 kg lean per leg, of which
    0.78 × lean - 0.535 kg is muscle (McCarthy 2023) -> ~6,040 cm³ at 1.06 g/cm³."""
    ref = capacity.predicted_leg_lean_kg(25, True, 1.70, 75.337)
    assert ref == pytest.approx(8.89, abs=0.01)
    assert capacity.leg_muscle_cm3(ref) == pytest.approx(6039, abs=3)
    woman = capacity.predicted_leg_lean_kg(70, False, 1.62, 68)
    assert woman == pytest.approx(6.08, abs=0.01)
    assert capacity.predicted_leg_lean_kg(70, True, 1.70, 75.337) < ref          # older, same size: less muscle
    assert capacity.predicted_leg_lean_kg(25, False, 1.70, 75.337) < ref         # woman, same size: less
    assert "DXA" in capacity.caveats(80, 1.8, leg_source="dxa")[0]
    assert "age, sex" in capacity.caveats(80, 1.8, leg_source="anthropometry")[0]
    assert capacity.caveats(110, 1.75)[0].startswith("BMI 35.9")                  # the regression's BMI warning


def test_person_age_sex_and_dxa(tmp_path):
    d = tmp_path / "P1"
    rec = person.init(d, "P1", height_m=1.75, mass_kg=80, age_years=61.5, sex="male")
    assert person.age_years(rec) == pytest.approx(61.5, abs=0.01) and rec["sex"] == "male"
    a = rec["anthropometrics"]["age_years"]
    later = a["measured_at"].replace(a["measured_at"][:4], str(int(a["measured_at"][:4]) + 2), 1)
    assert person.age_years(rec, later) == pytest.approx(63.5, abs=0.01)           # the age counts on
    assert "by age, sex, height and mass" in person._muscle_layer(rec)["status"]
    with pytest.raises(person.PersonRefused, match="sex"):
        person.set_measurement(d, sex="other")
    with pytest.raises(person.PersonRefused, match="age"):
        person.set_measurement(d, age_years=640)
    (tmp_path / "dxa.json").write_text(json.dumps(_scan(bone_density={
        "sites": {"femoral_neck": {"bmd_g_cm2": 0.62, "t_score": -2.7, "z_score": -1.2}}})))
    rec = person.set_dxa(d, tmp_path / "dxa.json")
    assert rec["dxa"]["sha256"] and rec["dxa"]["checks"]["mass_check"]["difference"] == pytest.approx(-0.031, abs=1e-3)
    assert "bone_density" not in rec["dxa"]
    assert rec["layers"]["soft_tissue"]["tier"] == "B" and "body fat 26" in rec["layers"]["soft_tissue"]["status"]
    assert "leg lean right 9.4 kg, left 8.6 kg" in rec["layers"]["muscle"]["status"]
    assert rec["layers"]["muscle"]["tier"] == "C"                                 # per leg, not per muscle
    b = rec["bone_density"]                                                       # age and sex from the person
    assert b["classification"]["category"] == "osteoporosis" and b["from"] == "dxa record"
    assert rec["layers"]["bone_density"]["tier"] == "B"
    text = person.summary(rec)
    assert "male, 62 years" in text and "leg lean R 9.4 kg, L 8.6 kg; body fat 26" in text
    (tmp_path / "far.json").write_text(json.dumps(_scan(regions={**_scan()["regions"],
                                                                 "trunk": {"lean_kg": 47.0, "fat_kg": 20, "bmc_kg": 0.8}})))
    with pytest.raises(person.PersonRefused, match=r"\+34%"):
        person.set_dxa(d, tmp_path / "far.json")
    assert person.load(d)["version"] == rec["version"]                           # refusals changed nothing


def test_cli_person_dxa(tmp_path, capsys):
    from rehabtwin import cli
    d = tmp_path / "P1"
    assert cli.main(["person", "init", str(d), "--person-ref", "P1", "--height-m", "1.75", "--mass-kg", "80",
                     "--age-years", "62", "--sex", "female"]) == 0
    (tmp_path / "dxa.json").write_text(json.dumps(_scan()))
    assert cli.main(["person", "dxa", str(d), str(tmp_path / "dxa.json")]) == 0
    out = capsys.readouterr().out
    assert "female, 62 years" in out and "DXA       DXA (test scanner)" in out and "soft_tissue    Tier B" in out
    (tmp_path / "bad.json").write_text(json.dumps(_scan(method="InBody 970")))
    assert cli.main(["person", "dxa", str(d), str(tmp_path / "bad.json")]) == 2
    assert "start with 'DXA'" in capsys.readouterr().err


def test_muscle_study_takes_age_sex_and_dxa_from_the_person(tmp_path, monkeypatch):
    from rehabtwin import cli, muscles
    scaled = []

    def run(**kw):
        from pathlib import Path
        Path(kw["out_dir"], kw["label"]).mkdir(parents=True, exist_ok=True)
        return {"label": kw["label"], "exercise": kw["exercise"], "valid_exercise": True, "time_range_s": [0.0, 1.0],
                "grf": {"body_mass_kg": 80.0, "min_vertical_bw": 1.0, "peak_vertical_bw": 1.0,
                        "right_share_range": [0.5, 0.5], "feet_planted": True},
                "group_activation": {}, "joint_moments": {}, "pelvis_residual_force_N": {}, "reserve_torque_peaks_Nm": {},
                "muscles_saturated": [], "caveats": [muscles.muscle_caveat(kw.get("muscle_model"))]}

    def scale_model(*a, **k):
        scaled.append((a, k))
        src = "dxa" if k.get("dxa_leg_lean_kg") else "anthropometry" if k.get("age_years") else "regression"
        return {"method": "m", "factor_median": 0.9, "sources": {src: 80}, "leg_source": src,
                "leg_source_text": capacity.LEG_SOURCES[src], "leg_muscle_cm3": {"right": 6400, "left": 5850},
                "subject": {"mass_kg": 80.0, "height_m": 1.75, "bmi": 26.1, "age_years": 62.0, "sex": "male"},
                "caveats": capacity.caveats(80.0, 1.75, 0, src)}
    monkeypatch.setattr(muscles, "run", run)
    monkeypatch.setattr(capacity, "scale_model", scale_model)
    monkeypatch.setattr(cli, "resolve", lambda p: p)
    d = tmp_path / "s"
    d.mkdir()
    (d / "session.json").write_text(json.dumps({
        "session_id": "s", "person_ref": "P1", "twin_tier": "C", "started_at": "2027-10-01T09:00:00+00:00",
        "person_model": {"folder": str(tmp_path / "P1")},
        "pipeline": {"front_end": "x", "processing_id": "p0", "config": "skel105_pose2sim.json",
                     "outputs": {"model": "model.osim", "motion": "ik.mot"}}}))
    (d / "metrics.json").write_text(json.dumps({"exercise": "squat", "reps": [{"start_s": 0.0, "stop_s": 1.0}]}))
    (d / "qc.json").write_text(json.dumps({"subject": {"mass_kg": 80.0, "mass_source": "measured", "height_m": 1.75}}))
    p = tmp_path / "P1"
    rec = person.init(p, "P1", height_m=1.75, mass_kg=80, age_years=61, sex="male")
    study, mdir = cli.muscle_study(d, plant=False, view_3d=False, workers=1)
    k = scaled[-1][1]
    expect_age = person.age_years(rec, "2027-10-01T09:00:00+00:00")             # age at the session, not today
    assert k["male"] is True and k["age_years"] == pytest.approx(expect_age) and k["dxa_leg_lean_kg"] is None
    assert study["muscle_model"]["source"].startswith("body-size scaled by age, sex")
    assert "a 62-year-old male of 1.75 m" in (mdir / "muscles.html").read_text()
    legs = _scan(regions={k: {"lean_kg": v["lean_kg"]} for k, v in _scan()["regions"].items() if "leg" in k})
    (tmp_path / "dxa.json").write_text(json.dumps(legs))
    person.set_dxa(p, tmp_path / "dxa.json")
    study, mdir = cli.muscle_study(d, plant=False, view_3d=False, workers=1)
    assert scaled[-1][1]["dxa_leg_lean_kg"] == {"_r": 9.4, "_l": 8.6}
    cap = study["muscle_model"]["capacity"]
    assert study["muscle_model"]["source"].startswith("DXA-calibrated") and cap["dxa"]["date"] == "2026-10-01"
    assert "mass_distribution" not in cap and any("Segment masses: the generic" in c for c in cap["caveats"])
    page = (mdir / "muscles.html").read_text()
    assert "leg muscle sized from a DXA scan" in page and "6400 cm³ right" in page
    assert "Measured per leg, not per muscle" in muscles.muscle_caveat(study["muscle_model"])
