# Aggregates of rows.json per the note's rules. Args: rows_json out_json
import json, sys, numpy as np, collections
d = json.load(open(sys.argv[1])); SET, rows = d["set"], d["rows"]
PRIMARY = ("HRNet", "2-cameras"); EXCL = ("subject2", "squats1")
key = lambda r: (r["estimator"], r["cameras"])
m = lambda xs: float(np.mean(xs)) if xs else None
def summary(rs, exclude=True):
    ev = [r for r in rs if r["status"] == "evaluated" and not (exclude and (r["subject"], r["trial"]) == EXCL)]
    subj = collections.defaultdict(list)
    for r in ev: subj[r["subject"]].append(r["mae18"])
    per_subject = {s: m(v) for s, v in sorted(subj.items(), key=lambda kv: int(kv[0][7:]))}
    mov = collections.defaultdict(lambda: collections.defaultdict(list))
    for r in ev: mov[r["movement"]][r["subject"]].append(r["mae18"])
    per_movement = {k: dict(mae_deg=m([m(x) for x in v.values()]), subjects=len(v), trials=sum(len(x) for x in v.values())) for k, v in sorted(mov.items())}
    angles = {c: dict(mae_deg=m([m([r["per"][c]["mae"] for r in ev if r["subject"] == s]) for s in subj]),
                      bias_deg=m([m([r["per"][c]["bias"] for r in ev if r["subject"] == s]) for s in subj]),
                      spread_deg=m([m([r["per"][c]["spread"] for r in ev if r["subject"] == s]) for s in subj])) for c in SET}
    return dict(run=len(rs), evaluated=len(ev), subjects_evaluated=len(subj), mae_deg=m(list(per_subject.values())),
                per_subject=per_subject, per_movement=per_movement, per_angle=angles,
                not_evaluated_by_movement=dict(collections.Counter(r["movement"] for r in rs if r["status"] != "evaluated")))
out = dict(primary="HRNet, 2 cameras", configurations={f"{e} {c}": summary([r for r in rows if key(r) == (e, c)]) for e, c in sorted({key(r) for r in rows})})
p = out["configurations"]["HRNet 2-cameras"]
out["expected"] = dict(rule="primary MAE (per trial -> subject mean over evaluated trials -> mean over the 10 subjects, subject2 squats1 excluded) within 2 deg of 4.5",
                       mae_deg=p["mae_deg"], subjects_evaluated=p["subjects_evaluated"], met=bool(p["mae_deg"] is not None and abs(p["mae_deg"] - 4.5) <= 2.0 and p["subjects_evaluated"] == 10))
# prediction
pm = p["per_movement"]; avg = m([v["mae_deg"] for v in pm.values()])
prim_ev = [r for r in rows if key(r) == PRIMARY and r["status"] == "evaluated" and (r["subject"], r["trial"]) != EXCL]
opp = {}
for s in sorted({r["subject"] for r in prim_ev}, key=lambda s: int(s[7:])):
    rs = [r for r in prim_ev if r["subject"] == s]
    pt = m([r["per"]["pelvis_tilt"]["bias"] for r in rs]); hf = m([(r["per"]["hip_flexion_r"]["bias"] + r["per"]["hip_flexion_l"]["bias"]) / 2 for r in rs])
    opp[s] = dict(pelvis_tilt_bias=round(pt, 2), hip_flexion_bias=round(hf, 2), opposite=bool(pt * hf < 0))
out["prediction"] = dict(text="squats worse than the average over movements; pelvis tilt and hip flexion opposite biases in >= 6 of 10 subjects",
    squat_mae_deg=pm.get("squat", {}).get("mae_deg"), average_over_movements_deg=avg, squats_worse=bool(pm.get("squat") and pm["squat"]["mae_deg"] > avg),
    opposite_bias_subjects=sum(v["opposite"] for v in opp.values()), per_subject=opp,
    met=bool(pm.get("squat") and pm["squat"]["mae_deg"] > avg and sum(v["opposite"] for v in opp.values()) >= 6))
s2 = [r for r in rows if (r["subject"], r["trial"]) == EXCL]
out["subject2_squats1"] = {f"{r['estimator']} {r['cameras']}": dict(status=r["status"], lag_s=r.get("lag_s"), ratio=r.get("ratio"), mae18_deg=r.get("mae18")) for r in s2}
lags = [r["lag_s"] for r in rows if "lag_s" in r]
out["lags"] = dict(median_s=float(np.median(lags)), abs_le_0p05_s=sum(abs(x) <= 0.05 for x in lags), n=len(lags),
                   ratio_median_not_evaluated=float(np.median([r["ratio"] for r in rows if r["status"] != "evaluated" and r.get("ratio")])))
json.dump(out, open(sys.argv[2], "w"), indent=1)
print("config                     run  eval subj  MAE")
for k, v in out["configurations"].items(): print(f"{k:26s} {v['run']:4d} {v['evaluated']:4d} {v['subjects_evaluated']:3d}  {v['mae_deg'] and round(v['mae_deg'],2)}   not-eval by movement {v['not_evaluated_by_movement']}")
print("primary per movement:", {k: (round(v["mae_deg"], 2), v["subjects"], v["trials"]) for k, v in pm.items()}, "avg", round(avg, 2))
print("primary per subject:", {k: round(v, 2) for k, v in p["per_subject"].items()})
print("primary per angle (MAE, bias, spread):"); [print(f"   {c:18s} {a['mae_deg']:6.2f} {a['bias_deg']:+6.2f} {a['spread_deg']:6.2f}") for c, a in p["per_angle"].items()]
print("expected:", out["expected"]); print("prediction:", {k: v for k, v in out["prediction"].items() if k != "per_subject"}); print(opp)
print("subject2 squats1:", out["subject2_squats1"]); print("lags:", out["lags"])
