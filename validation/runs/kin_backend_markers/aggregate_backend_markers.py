# t-kin-backend-markers, aggregation, by the rules committed in ff572ba: lag 0; evaluated = coverage not short and all 18
# angles; MAE over the 18 per trial -> subject -> subjects; subject 2's squats1 apart. Beside OpenCap's own IK on the same
# configuration (the zero-lag control's per-trial figures). Args: runs_dir control_rows_zerolag.json out_json
import json, sys, collections, numpy as np
from pathlib import Path
from rehabtwin import metrics as M, validation as V
from rehabtwin.io_formats import read_table, to_degrees
R, CTRL, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
MOC = Path.home() / "rehab-agent-data/datasets/opencap-labvalidation/mocap-ik/LabValidation_withoutVideos"
SET = ["pelvis_tilt", "pelvis_list", "pelvis_rotation"] + [f"{c}_{s}" for s in "rl" for c in ("hip_flexion", "hip_adduction", "hip_rotation", "knee_angle", "ankle_angle", "subtalar_angle")] + ["lumbar_extension", "lumbar_bending", "lumbar_rotation"]
EST = {"lumbar_extension": "lumbar_total.sagittal", "lumbar_bending": "lumbar_total.frontal", "lumbar_rotation": "lumbar_total.transverse"}
mv = lambda t: "walking" if t.startswith("walking") else "squat" if t.startswith("squats") else "sit-to-stand" if t.startswith("STS") else "drop jump"
rows = []
for sp in sorted(R.glob("*/*/status.json")):
    s, t = sp.parts[-3], sp.parts[-2]; d = sp.parent / "session"; rec = dict(subject=s, trial=t, movement=mv(t))
    mots = list((d / "opensim").glob("ik*.mot")) if d.exists() else []
    if not mots: rows.append(dict(rec, status="run, not evaluated", why="no IK result")); continue
    est = read_table(max(mots, key=lambda p: len(read_table(p).time)))
    est = to_degrees(M.with_signals(est, M.derived_signals(est, d / "opensim/model_scaled.osim")))
    ref = to_degrees(read_table(MOC / s / "OpenSimData/Mocap/IK" / f"{t}.mot"))
    q = json.loads((d / "qc.json").read_text()); seg = q["analysed_segment"]
    cov = V.coverage(est.time, ref.time, 0.0, (seg["start_s"], seg["start_s"] + seg["trial_s"]))
    r = V._resample(ref, est.time); per = {}
    for c in SET:
        e = EST.get(c, c)
        if e in est.columns and c in ref.columns:
            x = est.col(e) - r[:, ref.columns.index(c)]; x = x[np.isfinite(x)]
            if len(x) >= 2: per[c] = dict(mae=float(np.mean(np.abs(x))), bias=float(np.mean(x)), spread=float(np.std(x)), rmse=float(np.sqrt(np.mean(x ** 2))))
    missing = [c for c in SET if c not in per]; short = cov["fraction"] < V.MIN_COVERAGE
    rows.append(dict(rec, status="evaluated" if not missing and not short else "run, not evaluated", why=("coverage short" if short else f"missing {missing}" if missing else None),
                     coverage=cov["fraction"], segments=seg["of"], mae18=None if missing else float(np.mean([per[c]["mae"] for c in SET])), per=per))
ctrl = {(x["subject"], x["trial"]): x for x in json.loads(CTRL.read_text())["rows"] if x["estimator"] == "HRNet" and x["cameras"] == "2-cameras" and x["status"] == "evaluated"}
EXCL = ("subject2", "squats1"); m = lambda v: float(np.mean(v)) if len(v) else None
def summ(get, keys):
    subj = collections.defaultdict(list)
    for k in keys: subj[k[0]].append(k)
    S = sorted(subj, key=lambda s: int(s[7:]))
    return dict(trials=len(keys), subjects=len(S), mae_deg=m([m([get(k)["mae18"] for k in subj[s]]) for s in S]),
                per_subject={s: m([get(k)["mae18"] for k in subj[s]]) for s in S},
                per_movement={mo: dict(mae_deg=m([m([get(k)["mae18"] for k in subj[s] if mv(k[1]) == mo]) for s in S if any(mv(k[1]) == mo for k in subj[s])]), trials=sum(mv(k[1]) == mo for k in keys)) for mo in ("walking", "squat", "sit-to-stand", "drop jump")},
                per_angle={c: {st: m([m([get(k)["per"][c][st] for k in subj[s]]) for s in S]) for st in ("mae", "rmse", "bias", "spread")} for c in SET})
ours = {(x["subject"], x["trial"]): x for x in rows if x["status"] == "evaluated"}
common = sorted(k for k in ours if k in ctrl and k != EXCL)
res = dict(ours=summ(lambda k: ours[k], [k for k in sorted(ours) if k != EXCL]), ours_common=summ(lambda k: ours[k], common), opencap_common=summ(lambda k: ctrl[k], common),
           opencap_all=summ(lambda k: ctrl[k], [k for k in sorted(ctrl) if k != EXCL]),
           counts=dict(run=len(rows), evaluated=len(ours), not_evaluated=dict(collections.Counter(x["why"] for x in rows if x["status"] != "evaluated")), multi_segment=sum(x.get("segments", 1) > 1 for x in rows)),
           subject2_squats1=dict(ours=ours.get(EXCL, {}).get("mae18"), opencap=ctrl.get(EXCL, {}).get("mae18")))
d = res["ours_common"]["mae_deg"] - res["opencap_common"]["mae_deg"]
res["expected"] = dict(rule="our MAE over the 18 angles within 1.5 deg of OpenCap's own IK on the same markers (4.57 deg), zero-lag control's trials and rule",
                       ours_deg=res["ours"]["mae_deg"], opencap_deg=res["opencap_all"]["mae_deg"], difference_deg=res["ours"]["mae_deg"] - res["opencap_all"]["mae_deg"], difference_common_trials_deg=d,
                       met=bool(abs(res["ours"]["mae_deg"] - res["opencap_all"]["mae_deg"]) <= 1.5))
OUT.write_text(json.dumps(dict(set=SET, **res, rows=[{k: v for k, v in x.items() if k != "per"} for x in rows]), indent=1))
print("counts", res["counts"]); print("ours", round(res["ours"]["mae_deg"], 2), "| ours common", round(res["ours_common"]["mae_deg"], 2), "| OpenCap common", round(res["opencap_common"]["mae_deg"], 2), "| OpenCap all", round(res["opencap_all"]["mae_deg"], 2), "| trials", len(common))
print("per movement ours/opencap:", {k: (round(v["mae_deg"], 2), round(res["opencap_common"]["per_movement"][k]["mae_deg"], 2), v["trials"]) for k, v in res["ours_common"]["per_movement"].items() if v["mae_deg"]})
print("per subject ours:", {k[7:]: round(v, 1) for k, v in res["ours_common"]["per_subject"].items()})
print("angle               ours MAE  RMSE  bias spread | OpenCap MAE  bias spread")
for c in SET:
    a, b = res["ours_common"]["per_angle"][c], res["opencap_common"]["per_angle"][c]
    print(f"{c:18s} {a['mae']:8.2f} {a['rmse']:5.1f} {a['bias']:+6.1f} {a['spread']:5.1f} | {b['mae']:8.2f} {b['bias']:+6.1f} {b['spread']:5.1f}")
print("expected", res["expected"]); print("subject2 squats1", res["subject2_squats1"])
