# Full benchmark, aggregation (t-kin-labvalidation). Readings fixed here before any figure was printed (2026-11-10):
#  - Evaluated trial (per route): the route produced its validation report (it passed the pipeline's refusals) and
#    the report's coverage is not short (validation.MIN_COVERAGE). Otherwise run but not evaluated; a trial with no
#    synced video is not run.
#  - Cell = joint x plane; a trial's cell RMSE is the max over the cell's coordinates (validation.by_joint_plane).
#    A subject's cell RMSE is the mean over that subject's evaluated trials. Subject 2's squats1 is left out (pilot
#    trial) and reported separately.
#  - Pass (expected result): a cell passes on a route if its RMSE is within docs/accuracy.md's target (sagittal <= 3,
#    frontal <= 5 deg) in every evaluated subject. Transverse cells are reported only.
#  - Bias and spread (SD of the difference) per coordinate: means over subjects of the subject means.
#  - Lag-search best case: validation.compare on the route's IK result against the same (shifted) reference, +-4 s.
#  - Stop rule: per subject, a squat trial (squats1, squatsAsym1; subject2 squats1 included, since the rule is about
#    getting through) whose five-camera route gave a report and at least one repetition with no imputed frames and
#    no missing markers. Counted for both five-camera routes (multi, multi_aug).
# 2026-11-13: the HSMR route added (reports under <trial>/hsmr_route/session); the readings above are unchanged.
# Args: runs_dir out_json
import json, sys, collections
import numpy as np
from pathlib import Path
from rehabtwin import validation as V
from rehabtwin.io_formats import read_table, to_degrees
R, OUT = Path(sys.argv[1]), Path(sys.argv[2])
MOC = Path.home() / "rehab-agent-data/datasets/opencap-labvalidation/mocap-ik/LabValidation_withoutVideos"
ROUTES = ("multi", "multi_aug", "mono", "mono_aug", "hsmr")
RDIR = lambda d, r: d / "hsmr_route" / "session" if r == "hsmr" else d / r; TARGET = {"sagittal": 3.0, "frontal": 5.0}
EXCL = ("subject2", "squats1")
mean = lambda x: float(np.mean(x)) if len(x) else None
def movement(t): return "walking" if t.startswith("walking") else "squat" if t.startswith("squats") else "sit-to-stand" if t.startswith("STS") else "drop jump"

rows = []
for st_path in sorted(R.glob("*/*/status.json")):
    s = json.loads(st_path.read_text()); subj, trial = st_path.parts[-3], st_path.parts[-2]; d = st_path.parent
    for r in ROUTES:
        rec = dict(subject=subj, trial=trial, movement=movement(trial), route=r)
        if not s.get("inputs", {}).get("ok"):
            rows.append(dict(rec, status="not run", why=s.get("inputs", {}).get("error"))); continue
        rep_p = RDIR(d, r) / "validation-report.json"
        if not rep_p.exists():
            hs = json.loads((d / "hsmr_route" / "status_hsmr.json").read_text()) if r == "hsmr" and (d / "hsmr_route" / "status_hsmr.json").exists() else s
            failed = [k for k, v in hs.items() if isinstance(v, dict) and v.get("ok") is False and (r == "hsmr" or k.startswith(r.split("_")[0]))]
            rows.append(dict(rec, status="run, not evaluated", why="refused: " + ", ".join(failed))); continue
        v = json.loads(rep_p.read_text()); cov = v["coverage"]
        short = cov["fraction"] < cov["min_fraction"]
        cells = collections.defaultdict(float)
        for c, x in v["per_coordinate"].items():
            cells[f"{x['joint']}.{x['plane']}"] = max(cells[f"{x['joint']}.{x['plane']}"], x["rmse_deg"])
        m = json.loads((RDIR(d, r) / "metrics.json").read_text())
        complete = sum(1 for rp in m.get("reps", []) if not rp.get("contains_imputed_frames") and not rp.get("contains_missing_markers"))
        # lag-search best case
        best = None
        try:
            mots = [p for p in (RDIR(d, r) / "opensim").glob("ik*.mot")]
            est = read_table(max(mots, key=lambda p: len(read_table(p).time)))
            ref_p = d / "ref_multi.mot" if r.startswith("multi") else MOC / subj / "OpenSimData/Mocap/IK" / f"{trial}.mot"
            cmp = V.compare(est, read_table(ref_p), max_lag_s=4.0)
            bc = collections.defaultdict(float)
            for c, x in cmp["coordinates"].items(): bc[f"{x['joint']}.{x['plane']}"] = max(bc[f"{x['joint']}.{x['plane']}"], x["rmse_deg"])
            best = dict(lag_s=cmp["lag_s"], cells=dict(bc))
        except Exception as e:
            best = dict(error=str(e)[:200])
        rows.append(dict(rec, status="run, not evaluated" if short else "evaluated", why="coverage short" if short else None,
                         coverage=cov["fraction"], cells=dict(cells), complete_reps=complete,
                         per_coordinate={c: {k: x[k] for k in ("rmse_deg", "bias_deg", "rmse_offset_removed_deg")} for c, x in v["per_coordinate"].items()},
                         best_case=best))

out = dict(readings=open(__file__).read().split("import json")[0], routes={})
for r in ROUTES:
    rr = [x for x in rows if x["route"] == r]
    ev = [x for x in rr if x["status"] == "evaluated" and (x["subject"], x["trial"]) != EXCL]
    subs = sorted({x["subject"] for x in ev}, key=lambda s: int(s[7:]))
    cellnames = sorted({c for x in ev for c in x["cells"]})
    cells = {}
    for c in cellnames:
        per_s = {s: mean([x["cells"][c] for x in ev if x["subject"] == s and c in x["cells"]]) for s in subs}
        per_s = {s: v for s, v in per_s.items() if v is not None}
        plane = c.split(".")[-1]
        bestv = {s: mean([x["best_case"]["cells"][c] for x in ev if x["subject"] == s and x.get("best_case", {}).get("cells", {}).get(c) is not None]) for s in subs}
        cells[c] = dict(mean_over_subjects_deg=mean(list(per_s.values())), worst_subject_deg=max(per_s.values()) if per_s else None,
                        subjects=len(per_s), per_subject=per_s,
                        target_deg=TARGET.get(plane), passes=(all(v <= TARGET[plane] for v in per_s.values()) if plane in TARGET and per_s else None),
                        best_case_mean_deg=mean([v for v in bestv.values() if v is not None]))
    coords = sorted({c for x in ev for c in x["per_coordinate"]})
    per_coord = {c: {k: mean([mean([x["per_coordinate"][c][k] for x in ev if x["subject"] == s and c in x["per_coordinate"]]) for s in subs
                               if any(c in x["per_coordinate"] for x in ev if x["subject"] == s)]) for k in ("rmse_deg", "bias_deg", "rmse_offset_removed_deg")} for c in coords}
    by_mov = {mv: dict(run=sum(x["movement"] == mv and x["status"] != "not run" for x in rr), evaluated=sum(x["movement"] == mv for x in ev)) for mv in ("walking", "squat", "sit-to-stand", "drop jump")}
    out["routes"][r] = dict(trials=len(rr), not_run=sum(x["status"] == "not run" for x in rr), run=sum(x["status"] != "not run" for x in rr),
                            evaluated=len(ev), subjects_evaluated=len(subs), by_movement=by_mov,
                            not_evaluated_why=dict(collections.Counter(x["why"] for x in rr if x["status"] == "run, not evaluated")),
                            cells=cells, per_coordinate=per_coord,
                            passing_cells=[c for c, v in cells.items() if v["passes"]], failing_cells=[c for c, v in cells.items() if v["passes"] is False])
stop = {}
for r in ("multi", "multi_aug"):
    ok = sorted({x["subject"] for x in rows if x["route"] == r and x["movement"] == "squat" and x["status"] != "not run" and x.get("complete_reps", 0) > 0}, key=lambda s: int(s[7:]))
    stop[r] = dict(subjects=ok, count=len(ok), threshold=8, triggered=len(ok) < 8)
out["stop_rule"] = dict(rule="fewer than 8 of the 10 subjects with a complete squat repetition through the gates (five-camera route)", **stop,
                        note="subject6 shared no videos, so at most 9 subjects can count")
out["subject2_squats1"] = {x["route"]: dict(status=x["status"], cells=x.get("cells")) for x in rows if (x["subject"], x["trial"]) == EXCL}
out["rows"] = rows
OUT.write_text(json.dumps(out, indent=1))
for r, v in out["routes"].items():
    print(f"== {r}: run {v['run']}, evaluated {v['evaluated']} ({v['subjects_evaluated']} subjects); by movement {v['by_movement']}")
    print("   not evaluated:", v["not_evaluated_why"])
    print(f"   passing: {v['passing_cells']}")
    for c, x in v["cells"].items():
        if x["target_deg"] or c.split('.')[-1] == "transverse":
            print(f"     {c:26s} mean {x['mean_over_subjects_deg']:6.2f} worst {x['worst_subject_deg']:6.2f} best-case {x['best_case_mean_deg'] if x['best_case_mean_deg'] is None else round(x['best_case_mean_deg'],2)}  target {x['target_deg']}  pass {x['passes']}")
print("stop rule:", {k: (v["count"], v["triggered"]) for k, v in stop.items()})
