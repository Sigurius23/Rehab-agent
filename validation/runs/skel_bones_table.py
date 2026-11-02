import json, sys
r = json.load(open(sys.argv[1]))
s = r["summary"]
print("bodies", s["bodies"], "failed", s["failed"], "fit failed", s["fit_failed"])
print("height error (cm):", json.dumps(s["height_cm"]))
segs = ("thigh_r", "shank_r", "upper_arm_r", "forearm_r", "hip_width")
for g in ("all", "female", "male", "BMI < 20", "20-25", "25-30", "30-35", "> 35"):
    if g not in s["segments"]:
        continue
    print(f"== {g} (n={s['segments'][g]['depth fit']['thigh_r']['n']})")
    for src in ("depth fit", "depth fit + measured height", "height and mass", "height only"):
        v = s["segments"][g][src]
        print(f"  {src:28s}", "  ".join(f"{k}: {v[k]['bias_cm']:+.1f}/{v[k]['mae_cm']:.1f}/{v[k]['max_cm']:.1f}" for k in segs))
print("measures (all), MAE cm:")
for src in ("depth fit", "depth fit + measured height", "height and mass", "height only"):
    v = s["measures"]["all"][src]
    print(f"  {src:28s}", "  ".join(f"{k}: {v[k]['mae_cm']:.1f}" for k in v))
warn = sum(1 for row in r["rows"] if "fits" in row and row["fits"].get("depth fit", {}).get("warnings"))
print("fits with warnings (no height):", warn)
