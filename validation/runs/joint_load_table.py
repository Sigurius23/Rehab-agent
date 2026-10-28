"""Aggregate numbers of a joint-load study (study.json -> results JSON): knee loads, scenario changes with their
ground-force bands, effort changes, labels. No motion or force time series."""
import json
import sys

s = json.load(open(sys.argv[1]))
jl = s["joint_load"]
out = {"twin_tier": s["twin_tier"], "body_mass": s["body_mass"], "muscle_model": s["muscle_model"]["source"],
       "labels": jl["labels"], "baseline": jl["baseline"], "baseline_band_over_grf_split": jl.get("baseline_band_over_grf_split"),
       "fat_model": {k: jl["fat_model"][k] for k in ("fat_change_kg", "method", "dxa", "model_mass_kg")} if jl.get("fat_model") else None,
       "scenarios": {lab: {k: v for k, v in sc.items()} for lab, sc in jl["scenarios"].items()},
       "dynamic_consistency": {lab: r["dynamic_consistency"] for lab, r in s["runs"].items()},
       "reserve_torque_peaks_Nm": {lab: r["reserve_torque_peaks_Nm"] for lab, r in s["runs"].items()}}
print(json.dumps(out, indent=1, ensure_ascii=False))
