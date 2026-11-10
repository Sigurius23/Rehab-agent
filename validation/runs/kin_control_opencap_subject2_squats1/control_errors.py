# Positive control, step 2: `rehabtwin validate`'s report (RMSE, bias, spread = SD of the difference) plus the mean
# absolute error per coordinate at the same lag and resampling (validation.compare's own steps), and the MAE over the
# 18 lower-limb and trunk angles (16 without subtalar). Args: estimate_mot reference_mot report_json out_json
import json, sys, numpy as np
from rehabtwin import validation as V
from rehabtwin.io_formats import read_table, to_degrees
est, ref = to_degrees(read_table(sys.argv[1])), to_degrees(read_table(sys.argv[2]))
rep = json.load(open(sys.argv[3])); lag = rep["time_lag_applied_s"]
ref, _ = V._apply_aliases(est, ref, V.DEFAULT_ALIASES)
r = V._resample(V.Table(ref.columns, ref.data, ref.time + lag), est.time)
SET = ["pelvis_tilt", "pelvis_list", "pelvis_rotation"] + [f"{c}_{s}" for s in "rl" for c in ("hip_flexion", "hip_adduction", "hip_rotation", "knee_angle", "ankle_angle", "subtalar_angle")] + ["lumbar_extension", "lumbar_bending", "lumbar_rotation"]
rows = {}
for c, s in rep["per_coordinate"].items():
    d = est.col(c) - r[:, ref.columns.index(c)]; d = d[np.isfinite(d)]
    rows[c] = dict(rmse_deg=s["rmse_deg"], mae_deg=round(float(np.mean(np.abs(d))), 3), bias_deg=s["bias_deg"], spread_deg=s["rmse_offset_removed_deg"], n=s["n"], in_set=c in SET)
missing = [c for c in SET if c not in rows]
mae18 = float(np.mean([rows[c]["mae_deg"] for c in SET if c in rows])); mae16 = float(np.mean([rows[c]["mae_deg"] for c in SET if c in rows and "subtalar" not in c]))
out = dict(lag_s=lag, coverage=rep["coverage"], coordinates=rows, angle_set=SET, missing_from_set=missing,
           mae_set18_deg=round(mae18, 3), mae_set16_no_subtalar_deg=round(mae16, 3),
           expected=dict(rule="MAE over the 18 angles within 2 deg of the paper's 4.5 deg, with one clear lag (0.417 s, ratio 3.02)",
                         met=bool(abs(mae18 - 4.5) <= 2.0 and not missing)))
json.dump(out, open(sys.argv[4], "w"), indent=1)
for c, x in sorted(rows.items(), key=lambda kv: (not kv[1]["in_set"], kv[0])):
    print(f"{'*' if x['in_set'] else ' '} {c:20s} RMSE {x['rmse_deg']:6.2f}  MAE {x['mae_deg']:6.2f}  bias {x['bias_deg']:6.2f}  spread {x['spread_deg']:6.2f}")
print("missing:", missing, "| MAE 18:", round(mae18, 2), "| MAE 16:", round(mae16, 2), "| lag", lag, "| coverage", rep["coverage"]["fraction"], "| met:", out["expected"]["met"])
