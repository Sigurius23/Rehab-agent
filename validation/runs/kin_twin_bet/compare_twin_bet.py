# t-twin-bet-scaled-model, comparison, by the rules committed in 3a1c5da. Baseline: the route's earlier run with the
# pipeline's usual body (round 0 for MediaPipe, round 2 for HSMR); twin: the same sequences with the mocap-scaled body.
# Judged figure: over trials evaluated in both runs, without walking and without subject 2's squats1, the sagittal hip and
# knee RMSE at lag 0 (right and left averaged), mean over subjects of the subject's mean. Walking separately.
# Args: baseline_mono.json baseline_hsmr.json twin_results.json out_json
import json, sys, collections, numpy as np
b0, b2, tw = (json.load(open(p)) for p in sys.argv[1:4])
base = {"mono": b0, "mono_aug": b0, "hsmr": b2}
SIG = dict(hip=("hip_r.sagittal", "hip_l.sagittal"), knee=("knee_r.sagittal", "knee_l.sagittal"), ankle=("ankle_r.sagittal", "ankle_l.sagittal"),
           pelvis_tilt=("pelvis.sagittal",), lumbar_flexion=("lumbar.sagittal",), trunk_inclination=("torso_segment.sagittal",), hip_frontal=("hip_r.frontal", "hip_l.frontal"))
m = lambda v: float(np.mean(v)) if len(v) else None
out = {}
for r in ("mono", "mono_aug", "hsmr"):
    B = {(x["subject"], x["trial"]): x for x in base[r]["rows"] if x["route"] == r}; T = {(x["subject"], x["trial"]): x for x in tw["rows"] if x["route"] == r}
    ev = lambda d: {k for k, x in d.items() if x["status"] == "evaluated"}
    res = dict(evaluated=dict(baseline=len(ev(B)), twin=len(ev(T)), both=len(ev(B) & ev(T))),
               twin_not_evaluated=dict(collections.Counter(str(x.get("why")) for k, x in T.items() if x["status"] == "run, not evaluated")))
    for label, sel in (("without_walking", lambda k: not k[1].startswith("walking")), ("walking", lambda k: k[1].startswith("walking"))):
        keys = sorted(k for k in ev(B) & ev(T) if sel(k) and k != ("subject2", "squats1")); subs = sorted({k[0] for k in keys}, key=lambda s: int(s[7:]))
        sec = dict(trials=len(keys), subjects=len(subs), signals={})
        for name, cells in SIG.items():
            def val(d, lag0=True):
                per = []
                for s in subs:
                    v = [np.mean([(d[k]["cells"] if lag0 else d[k]["best_case"]["cells"])[c] for c in cells]) for k in keys if k[0] == s and all(c in (d[k]["cells"] if lag0 else (d[k].get("best_case") or {}).get("cells", {})) for c in cells)]
                    if v: per.append(np.mean(v))
                return m(per)
            a, b = val(B), val(T)
            sec["signals"][name] = dict(baseline_deg=a, twin_deg=b, change_deg=None if a is None or b is None else b - a, change_pct=None if not a or b is None else 100 * (b - a) / a,
                                        baseline_best_case_deg=val(B, False), twin_best_case_deg=val(T, False))
        res[label] = sec
    out[r] = res
j = out["mono"]["without_walking"]["signals"]
out["expected"] = dict(rule="one-camera MediaPipe route (no augmenter): sagittal hip error at lag 0 falls by at least half and knee by at least a third against the height-scaled body",
                       hip_change_pct=j["hip"]["change_pct"], knee_change_pct=j["knee"]["change_pct"], met=bool(j["hip"]["change_pct"] <= -50 and j["knee"]["change_pct"] <= -100 / 3))
out["prediction"] = dict(text="it does not: the errors fall by less than 3 deg", hip_change_deg=j["hip"]["change_deg"], knee_change_deg=j["knee"]["change_deg"],
                         holds=bool(not out["expected"]["met"] and j["hip"]["change_deg"] > -3 and j["knee"]["change_deg"] > -3))
json.dump(out, open(sys.argv[4], "w"), indent=1)
for r in ("mono", "mono_aug", "hsmr"):
    print(f"== {r}: evaluated {out[r]['evaluated']}; twin not evaluated {out[r]['twin_not_evaluated']}")
    for label in ("without_walking", "walking"):
        sec = out[r][label]; print(f"   {label}: {sec['trials']} trials, {sec['subjects']} subjects")
        for n, v in sec["signals"].items():
            if v["baseline_deg"] is not None: print(f"      {n:18s} {v['baseline_deg']:6.2f} -> {v['twin_deg']:6.2f}  ({v['change_deg']:+.2f}, {v['change_pct']:+.0f}%)   best case {v['baseline_best_case_deg'] or 0:.1f} -> {v['twin_best_case_deg'] or 0:.1f}")
print("expected", out["expected"]); print("prediction", out["prediction"])
