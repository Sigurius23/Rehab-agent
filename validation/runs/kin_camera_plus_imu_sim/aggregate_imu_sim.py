# t-kin-camera-plus-imu-sim, aggregation, by the details committed in bf56aea: validation.compare at lag 0 against the
# motion-capture IK; RMSE, bias and spread per coordinate as means over subjects of the subject's mean; hip and knee
# average right and left; subject 2's squats1 left out; judged without walking. Args: runs_dir out_json
import json, sys, collections, numpy as np
from pathlib import Path
from rehabtwin import validation as V
from rehabtwin.io_formats import read_table
R, OUT = Path(sys.argv[1]), Path(sys.argv[2])
MOC = Path.home() / "rehab-agent-data/datasets/opencap-labvalidation/mocap-ik/LabValidation_withoutVideos"
CONDS = ["none", "pelvis_clean", "pelvis_noisy", "pelvis_thighs_clean", "pelvis_thighs_noisy"]
SIG = dict(pelvis_tilt=["pelvis_tilt"], hip_sagittal=["hip_flexion_r", "hip_flexion_l"], knee_sagittal=["knee_angle_r", "knee_angle_l"],
           pelvis_frontal=["pelvis_list"], hip_frontal=["hip_adduction_r", "hip_adduction_l"], ankle_sagittal=["ankle_angle_r", "ankle_angle_l"])
rows = []
for rec in sorted(R.glob("*/*/*/record.json")):
    s, t, r = rec.parts[-4], rec.parts[-3], rec.parts[-2]
    if (s, t) == ("subject2", "squats1"): continue
    ref = read_table(MOC / s / "OpenSimData/Mocap/IK" / f"{t}.mot"); row = dict(subject=s, trial=t, route=r, walking=t.startswith("walking"), cond={})
    for c in CONDS:
        cmp = V.compare(read_table(rec.parent / f"{c}.mot"), ref, max_lag_s=0)["coordinates"]
        row["cond"][c] = {k: {st: float(np.mean([cmp[x][key] for x in cols])) for st, key in (("rmse", "rmse_deg"), ("bias", "bias_deg"), ("spread", "rmse_offset_removed_deg"))} for k, cols in SIG.items()}
    rows.append(row)
m = lambda v: float(np.mean(v)) if len(v) else None
def table(sel):
    out = {}
    for r in ("mono", "mono_aug"):
        rr = [x for x in rows if x["route"] == r and sel(x)]; subs = sorted({x["subject"] for x in rr}, key=lambda s: int(s[7:]))
        out[r] = dict(trials=len(rr), subjects=len(subs), conditions={c: {k: {st: m([m([x["cond"][c][k][st] for x in rr if x["subject"] == s]) for s in subs]) for st in ("rmse", "bias", "spread")} for k in SIG} for c in CONDS})
    return out
res = dict(without_walking=table(lambda x: not x["walking"]), walking=table(lambda x: x["walking"]), all_movements=table(lambda x: True))
j = res["without_walking"]["mono"]["conditions"]["pelvis_thighs_noisy"]
res["expected"] = dict(rule="one-camera MediaPipe route, pelvis + thigh sensors, assumed noise, without walking: sagittal hip RMSE <= 10 deg and pelvis tilt RMSE <= 5 deg (means over subjects)",
                       hip_deg=j["hip_sagittal"]["rmse"], pelvis_tilt_deg=j["pelvis_tilt"]["rmse"], met=bool(j["hip_sagittal"]["rmse"] <= 10 and j["pelvis_tilt"]["rmse"] <= 5))
OUT.write_text(json.dumps(dict(signals=SIG, conditions=CONDS, **res, rows=rows), indent=1))
for sec in ("without_walking", "walking"):
    for r in ("mono", "mono_aug"):
        t = res[sec][r]; print(f"== {sec} / {r}: {t['trials']} trials, {t['subjects']} subjects   (RMSE / bias / spread)")
        for c in CONDS: print(f"   {c:20s}", "  ".join(f"{k.split('_')[0][:6]}_{k.split('_')[1][:3]} {v['rmse']:5.1f}/{v['bias']:+5.1f}/{v['spread']:4.1f}" for k, v in t["conditions"][c].items()))
print("expected", res["expected"])
