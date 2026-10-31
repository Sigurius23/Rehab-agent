"""Knee joint load scenarios (rehabtwin/joint_load.py) without OpenSim. Through OpenSim: test_pipeline.py."""
import pytest

from rehabtwin import joint_load as jl


def _dxa(**fat):
    regions = {"left_arm": (3.0, 1.0, 0.17), "right_arm": (3.1, 1.0, 0.18), "left_leg": (9.5, 3.2, 0.5),
               "right_leg": (9.6, 3.2, 0.5), "trunk": (25.0, 7.0, 0.8), "head": (3.3, 0.9, 0.55)}
    return {"method": "DXA (test)", "date": "2026-10-28",
            "regions": {r: {"lean_kg": a, "fat_kg": fat.get(r, b), "bmc_kg": c} for r, (a, b, c) in regions.items()}}


def test_fat_change_follows_each_regions_fat_and_refuses_a_bmi_slider():
    change = jl.fat_change_regions(_dxa(), -5.0)
    assert sum(change.values()) == pytest.approx(-5.0)
    assert change["trunk"] / change["left_arm"] == pytest.approx(7.0)        # in proportion to the region's fat
    assert change["right_leg"] == pytest.approx(-5.0 * 3.2 / 16.3)
    no_fat = _dxa()
    del no_fat["regions"]["trunk"]["fat_kg"]
    with pytest.raises(ValueError, match="regional fat"):
        jl.fat_change_regions(no_fat, -5.0)                                  # no table, no scenario
    with pytest.raises(ValueError, match="up to 50%"):
        jl.fat_change_regions(_dxa(), -9.0)
    with pytest.raises(ValueError, match="up to"):
        jl.fat_change_regions(_dxa(), 0.0)


def _load(peak_r, peak_l, imp=100.0):
    return {"r": {"peak_compression_N": peak_r, "impulse_Ns": imp}, "l": {"peak_compression_N": peak_l, "impulse_Ns": imp}}


def test_changes_are_robust_only_when_every_ground_force_split_agrees():
    cmp = jl.compare(_load(2000.0, 1800.0), _load(1900.0, 1800.0, 95.0))
    assert cmp["r"]["peak"]["change_N"] == -100.0 and cmp["r"]["peak"]["change_pct"] == -5.0
    assert cmp["l"]["peak"]["change_pct"] == 0.0 and cmp["r"]["impulse_pct"] == -5.0
    assert jl.robust([-5.0, -4.1, -6.3]) and not jl.robust([-5.0, 0.5, -6.0]) and not jl.robust([-1.0, -1.5])
    assert not jl.robust([None, None])


def test_readings_keep_published_evidence_and_effort_apart_from_model_output():
    base = {"measured": {"knee_load": {**_load(2000.0, 1900.0), "body_weight_N": 700.0, "series": {"t": [0.0], "r": [1.0]}}}}
    runs = {**base,
            "fat -5 kg": {"knee_load": {**_load(1860.0, 1770.0, 93.0), "body_weight_N": 651.0, "series": {"t": [0.0]}}},
            "quadriceps_r at 120%": {"knee_load": {**_load(2040.0, 1900.0), "body_weight_N": 700.0, "series": {"t": [0.0]}}}}
    comparisons = {"quadriceps_r at 120%": {"quadriceps_r": {"base": 0.6, "other": 0.5, "change": -0.1},
                                            "adductors_r": {"base": 0.2, "other": 0.1, "change": -0.1}}}
    out = jl.summarise(runs, {"fat -5 kg": "fat", "quadriceps_r at 120%": "strength"}, comparisons,
                       mass={"measured": 71.4, "fat -5 kg": 66.4, "quadriceps_r at 120%": 71.4},
                       fat={"dxa": {"method": "DXA (test)", "date": "2026-10-28"}})
    fat = out["scenarios"]["fat -5 kg"]
    assert fat["mass_change"] == {"kg": -5.0, "pct": -7.0}
    assert fat["reading"].startswith("Model-computed on the replayed motion") and "4:1" not in fat["reading"]
    assert "not model output" in fat["published_evidence"] and "40.6 N" in fat["published_evidence"]
    strong = out["scenarios"]["quadriceps_r at 120%"]
    assert set(strong["effort"]) == {"quadriceps_r"}                         # effort groups only
    assert "+2.0%" in strong["reading"] and "can stay the same or rise" in strong["reading"]
    assert "load" not in strong.get("published_evidence", "")
    assert "ground_forces" in out["labels"] and "assumption" in out["labels"]["fat_provenance"]
    assert "baseline_band_over_grf_split" not in out                        # no split runs, no band claimed
    illus = jl.summarise(runs, {"fat -5 kg": "fat"}, comparisons, mass={"measured": 71.4, "fat -5 kg": 66.4,
                                                                        "quadriceps_r at 120%": 71.4},
                         fat={"dxa": {"method": "DXA (illustrative values)"}})
    assert illus["labels"]["fat_provenance"].startswith("ILLUSTRATIVE regional fat, not measured")


def test_a_saturated_knee_states_no_change_even_within_the_person():
    diag = {"r": {"why_not_reportable": ["1 knee-crossing muscle(s) at capacity at the peak (vaslat_r)"],
                  "above_in_vivo_band": True},
            "l": {"why_not_reportable": [], "above_in_vivo_band": True,
                  "why_impulse_not_reportable": ["the estimated ground forces don't fit the motion everywhere in the rep"]}}
    runs = {"measured": {"knee_load": {**_load(7500.0, 4200.0), "body_weight_N": 700.0, "series": {"t": [0.0]},
                                       "diagnostics": diag}},
            "fat -5 kg": {"knee_load": {**_load(7000.0, 3900.0), "body_weight_N": 651.0, "series": {"t": [0.0]},
                                        "diagnostics": {"r": {"why_not_reportable": []}, "l": {"why_not_reportable": []}}}}}
    out = jl.summarise(runs, {"fat -5 kg": "fat"}, {}, mass={"measured": 71.4, "fat -5 kg": 66.4})
    sc = out["scenarios"]["fat -5 kg"]
    assert not sc["knee"]["r"]["reportable"] and sc["knee"]["l"]["reportable"]
    assert "right knee not reportable (baseline: 1 knee-crossing muscle" in sc["reading"]
    assert "right knee peak compression" not in sc["reading"]
    assert "left knee peak compression -7.1% (baseline above the in-vivo band: model-limited)" in sc["reading"]
    assert out["baseline_diagnostics"] == diag and "Bergmann" in out["labels"]["in_vivo_band"]
    assert sc["knee"]["l"]["impulse_pct"] is None and sc["knee"]["l"]["why_impulse_not_reportable"][0].startswith("baseline")
    assert sc["knee"]["r"]["impulse_pct"] is not None     # the peak's verdict and the impulse's are separate
    held = jl.summarise({**runs, "quadriceps_r at 120%": runs["fat -5 kg"]}, {"quadriceps_r at 120%": "strength"},
                        {"quadriceps_r at 120%": {"quadriceps_r": {"base": 0.8, "other": 0.7, "change": -0.1},
                                                  "quadriceps_l": {"base": 0.5, "other": 0.45, "change": -0.05}}},
                        mass={"measured": 71.4, "quadriceps_r at 120%": 71.4})["scenarios"]["quadriceps_r at 120%"]
    assert set(held["effort"]) == {"quadriceps_l"} and "right-side effort not reportable either" in held["reading"]
    both = {s: {"why_not_reportable": ["the estimated ground forces don't fit the motion at the peak"]} for s in "rl"}
    none = jl.summarise({"measured": {"knee_load": {**runs["measured"]["knee_load"], "diagnostics": both}},
                         "fat -5 kg": runs["fat -5 kg"]}, {"fat -5 kg": "fat"}, {},
                        mass={"measured": 71.4, "fat -5 kg": 66.4})["scenarios"]["fat -5 kg"]
    assert "About proportional" in sc["reading"] and "About proportional" not in none["reading"]   # nothing stated
