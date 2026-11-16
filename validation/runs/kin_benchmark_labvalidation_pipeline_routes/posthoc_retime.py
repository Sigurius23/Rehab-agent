# POST HOC (owner, 2026-11-16), changing no recorded figure. Round 2's outputs, every route, walking and subject 2's
# squats1 left out, evaluated trials only. Each estimate frame is re-timed by its own stored video frame's timestamp
# (OpenCV CAP_PROP_POS_MSEC) instead of index/60, and compared with the motion-capture IK at lag 0; the lag search
# (+-4 s) gives the new best lag. The baseline is the same comparison on the index timing (the recorded alignment).
# Both use validation.compare on the IK result (the pipeline's comparison, without derived signals).
# Multi-view routes: estimate frame m is Cam0's stored frame m + reference_start_frame (the --sync trim).
# One-camera routes and HSMR (on the stored frames since round 2): estimate frame k is Cam2's stored frame k.
# Args: bench_dir out_json
import json, sys, collections
import numpy as np
from pathlib import Path
from rehabtwin import validation as V
from rehabtwin.io_formats import read_table
B, OUT = Path(sys.argv[1]), Path(sys.argv[2])
MOC = Path.home() / "rehab-agent-data/datasets/opencap-labvalidation/mocap-ik/LabValidation_withoutVideos"
TS = json.loads((B / "posthoc_frame_timestamps.json").read_text())
CELLS = ["hip_r.sagittal", "hip_l.sagittal", "knee_r.sagittal", "knee_l.sagittal", "ankle_r.sagittal", "ankle_l.sagittal"]
ROUTES = dict(multi=("runs_round2", "multi"), multi_aug=("runs_round2", "multi_aug"), mono=("runs", "mono"), mono_aug=("runs", "mono_aug"),
              hsmr=("runs_round2", "hsmr_route/session"))
r2, r0 = (json.loads((B / f).read_text()) for f in ("results_round2.json", "results_v2.json"))
evald = {r: {(x["subject"], x["trial"]) for x in (r0 if r.startswith("mono") else r2)["rows"] if x["route"] == r and x["status"] == "evaluated"} for r in ROUTES}
def cells(cmp):
    c = collections.defaultdict(float)
    for x in cmp["coordinates"].values(): c[f"{x['joint']}.{x['plane']}"] = max(c[f"{x['joint']}.{x['plane']}"], x["rmse_deg"])
    return c
def shifted(t, s): return V.Table(t.columns, t.data, t.time + s, t.in_degrees, t.header)
rows = []
for r, (runs, sub) in ROUTES.items():
    for s, t in sorted(evald[r]):
        if t.startswith("walking") or (s, t) == ("subject2", "squats1"): continue
        d = B / runs / s / t / sub / "opensim"
        mots = list(d.glob("ik*.mot"))
        if not mots: continue
        est = read_table(max(mots, key=lambda p: len(read_table(p).time)))
        ref = read_table(MOC / s / "OpenSimData/Mocap/IK" / f"{t}.mot")
        if r.startswith("multi"):
            start = json.loads((B / runs / s / t / "status.json").read_text())["multi_sync"]["start"]; ts = np.array(TS[f"{s}/{t}/Cam0"])
        else:
            start = 0; ts = np.array(TS[f"{s}/{t}/Cam2"])
        idx = np.rint(est.time * 60).astype(int) + start
        if idx.max() >= len(ts): continue
        base_ref = shifted(ref, -start / 60.0)          # the recorded alignment: index timing, reference shifted by the trim
        retimed = V.Table(est.columns, est.data, ts[idx] - ts[start], est.in_degrees, est.header)   # own timestamps, from the same origin
        b0, b4 = V.compare(est, base_ref, max_lag_s=0), V.compare(est, base_ref, max_lag_s=4)
        n0, n4 = V.compare(retimed, shifted(ref, -ts[start]), max_lag_s=0), V.compare(retimed, shifted(ref, -ts[start]), max_lag_s=4)
        rows.append(dict(route=r, subject=s, trial=t, gap_frames=int(round((ts[-1] - ts[0]) * 60)) + 1 - len(ts),
                         base=dict(cells={c: cells(b0)[c] for c in CELLS}, best_lag_frames=b4["lag_s"] * 60),
                         retimed=dict(cells={c: cells(n0)[c] for c in CELLS}, best_lag_frames=n4["lag_s"] * 60)))
summary = {}
for r in ROUTES:
    rr = [x for x in rows if x["route"] == r]; subs = sorted({x["subject"] for x in rr})
    m = lambda k, c: float(np.mean([np.mean([x[k]["cells"][c] for x in rr if x["subject"] == s]) for s in subs]))
    lag = lambda k, lim: float(np.median([x[k]["best_lag_frames"] for x in rr if abs(x[k]["best_lag_frames"]) <= lim]))
    summary[r] = dict(trials=len(rr), subjects=len(subs),
                      cells={c: dict(index_timing_deg=round(m("base", c), 2), timestamp_timing_deg=round(m("retimed", c), 2), change_deg=round(m("retimed", c) - m("base", c), 2)) for c in CELLS},
                      best_lag_median_frames=dict(index_timing=lag("base", 18), timestamp_timing=lag("retimed", 18),
                                                  index_timing_abs_median=float(np.median([abs(x["base"]["best_lag_frames"]) for x in rr if abs(x["base"]["best_lag_frames"]) <= 18])),
                                                  timestamp_timing_abs_median=float(np.median([abs(x["retimed"]["best_lag_frames"]) for x in rr if abs(x["retimed"]["best_lag_frames"]) <= 18])),
                                                  note="medians over trials with |best lag| <= 18 frames (0.3 s); aliases left out"),
                      trials_with_gap=sum(x["gap_frames"] > 0 for x in rr))
OUT.write_text(json.dumps(dict(what=open(__file__).read().split("import json")[0], summary=summary, rows=rows), indent=1))
for r, v in summary.items():
    print(f"== {r}: {v['trials']} trials, {v['subjects']} subjects, {v['trials_with_gap']} with a gap | best lag median {v['best_lag_median_frames']['index_timing']:+.1f} -> {v['best_lag_median_frames']['timestamp_timing']:+.1f} frames; |lag| median {v['best_lag_median_frames']['index_timing_abs_median']:.1f} -> {v['best_lag_median_frames']['timestamp_timing_abs_median']:.1f}")
    for c, x in v["cells"].items(): print(f"     {c:18s} {x['index_timing_deg']:6.2f} -> {x['timestamp_timing_deg']:6.2f}  ({x['change_deg']:+.2f})")
