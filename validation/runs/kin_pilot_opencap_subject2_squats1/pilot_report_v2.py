# The pilot's results, after the owner's option A (2026-11-10). Version 2 of pilot_report.py: the same cell rule,
# plus what the owner recorded with the decision: per-coordinate differences beside each cell, coordinates over
# 2.0 deg inside a passing cell named, run and evaluated counts, and the one-camera shared-lag sensitivity.
# Cell RMSE = max over the cell's coordinates (validation.by_joint_plane). Spread = SD of the difference.
# Args: pilot_dir out_json
import json, sys
from pathlib import Path
P, out = Path(sys.argv[1]), Path(sys.argv[2])
ROUTES = ("multi", "multi_aug", "mono", "mono_aug")
load = lambda d: json.loads((d / "validation-report.json").read_text()) if (d / "validation-report.json").exists() else None
rep = {ref: {r: load(P / ref / r) for r in ROUTES} for ref in ("mocap", "opencap")}
shared = {r: load(P / "mocap_sharedlag" / r) for r in ("mono", "mono_aug")}
def cells(v):
    acc = {}
    for c, s in v["per_coordinate"].items():
        acc.setdefault((s["joint"], s["plane"]), []).append(dict(s, coordinate=c))
    return acc
def evaluated(v):
    cov = v.get("coverage") or {}
    return not (cov and cov.get("fraction", 1.0) < cov.get("min_fraction", 0.0))
res = dict(counts={}, routes={}, sensitivity_one_camera_shared_lag={}, expected=None)
for ref in ("mocap", "opencap"):
    res["counts"][ref] = dict(run=sum(rep[ref][r] is not None for r in ROUTES),
                              evaluated=sum(rep[ref][r] is not None and evaluated(rep[ref][r]) for r in ROUTES))
for r in ROUTES:
    m, o = rep["mocap"][r], rep["opencap"][r]
    cm, co = cells(m), cells(o)
    rows = []
    for key in sorted(cm):
        j, pl = key
        cs = cm[key]; worst = max(cs, key=lambda s: s["rmse_deg"])
        oc = {s["coordinate"]: s for s in co.get(key, [])}
        o_cell = max((s["rmse_deg"] for s in co.get(key, [])), default=None)
        per = [dict(coordinate=s["coordinate"], rmse_deg=s["rmse_deg"], bias_deg=s["bias_deg"], spread_deg=s["rmse_offset_removed_deg"],
                    rom_deg=s["reference_rom_deg"], rmse_vs_opencap_deg=oc.get(s["coordinate"], {}).get("rmse_deg"),
                    difference_deg=None if s["coordinate"] not in oc else round(s["rmse_deg"] - oc[s["coordinate"]]["rmse_deg"], 3))
               for s in sorted(cs, key=lambda s: s["coordinate"])]
        rows.append(dict(joint=j, plane=pl, rmse_deg=worst["rmse_deg"], worst_coordinate=worst["coordinate"],
                         gate=m["gates"].get(f"{j}.{pl}_rmse_le_{m['targets_deg'][pl]:g}deg"),
                         rmse_vs_opencap_deg=o_cell, difference_deg=None if o_cell is None else round(worst["rmse_deg"] - o_cell, 3),
                         coordinates=per))
    res["routes"][r] = dict(lag_vs_mocap_s=m["time_lag_applied_s"], lag_vs_opencap_s=o["time_lag_applied_s"],
                            coverage_vs_mocap=m["coverage"], evaluated_vs_mocap=evaluated(m), evaluated_vs_opencap=evaluated(o),
                            approved_for=m["approved_for"], rows=rows)
for r, v in shared.items():
    cm = cells(v)
    res["sensitivity_one_camera_shared_lag"][r] = dict(
        lag_s=json.loads((P / "sharedlag_ref/lag.json").read_text())["shared_lag_s"], coverage=v["coverage"], evaluated=evaluated(v),
        rows=[dict(joint=j, plane=pl, rmse_deg=max(s["rmse_deg"] for s in cs),
                   primary_rmse_deg=next(x["rmse_deg"] for x in res["routes"][r]["rows"] if (x["joint"], x["plane"]) == (j, pl)),
                   gate=v["gates"].get(f"{j}.{pl}_rmse_le_{v['targets_deg'][pl]:g}deg")) for (j, pl), cs in sorted(cm.items())])
ma = res["routes"]["multi_aug"]
both = [x for x in ma["rows"] if x["difference_deg"] is not None]
outside = [f"{x['joint']}.{x['plane']}" for x in both if abs(x["difference_deg"]) > 2.0]
named = [f"{c['coordinate']} ({c['difference_deg']:+.2f}) in {x['joint']}.{x['plane']}" for x in both if abs(x["difference_deg"]) <= 2.0
         for c in x["coordinates"] if c["difference_deg"] is not None and abs(c["difference_deg"]) > 2.0]
end_to_end = all(rep[ref][r] is not None for ref in rep for r in ROUTES)
res["expected"] = dict(rule="per joint x plane cell present in both reports, |RMSE vs motion capture - RMSE vs OpenCap| <= 2.0 deg (five cameras + augmenter); all four routes produce their reports",
                       end_to_end=end_to_end, cells_compared=len(both), cells_outside=outside,
                       coordinates_over_2deg_inside_passing_cells=named, met=bool(end_to_end and both and not outside))
out.write_text(json.dumps(res, indent=1))
print("counts", json.dumps(res["counts"]))
for r in ROUTES:
    t = res["routes"][r]
    print(f"\n== {r}: lag vs mocap {t['lag_vs_mocap_s']:.3f} s, vs OpenCap {t['lag_vs_opencap_s']:.3f} s; coverage {t['coverage_vs_mocap']['fraction']}; "
          f"evaluated {t['evaluated_vs_mocap']}/{t['evaluated_vs_opencap']}; approved {t['approved_for']}")
    print(f"   {'cell':24s} {'RMSE':>6} {'worst coordinate':22s} {'bias':>6} {'spread':>6} {'ROM':>6} {'vsOC':>6} {'diff':>6}  gate")
    for x in t["rows"]:
        w = next(c for c in x["coordinates"] if c["coordinate"] == x["worst_coordinate"])
        f = lambda v, s="6.2f": "" if v is None else format(v, s)
        print(f"   {x['joint'] + '.' + x['plane']:24s} {x['rmse_deg']:6.2f} {x['worst_coordinate']:22s} {w['bias_deg']:6.2f} {w['spread_deg']:6.2f} {w['rom_deg']:6.1f} "
              f"{f(x['rmse_vs_opencap_deg']):>6} {f(x['difference_deg'], '+6.2f'):>6}  {x['gate']}")
for r, t in res["sensitivity_one_camera_shared_lag"].items():
    print(f"\n== sensitivity {r} at shared lag {t['lag_s']:.3f} s: coverage {t['coverage']['fraction']}, evaluated {t['evaluated']}")
    for x in t["rows"]:
        print(f"   {x['joint'] + '.' + x['plane']:24s} {x['rmse_deg']:6.2f}  (primary {x['primary_rmse_deg']:6.2f})  {x['gate']}")
print("\nexpected:", json.dumps(res["expected"]))
