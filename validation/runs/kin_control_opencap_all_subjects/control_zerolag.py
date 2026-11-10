# POST HOC (owner, 2026-11-10, after the result of 326f260): the same comparison at zero lag, no lag search. A trial is evaluated when coverage is not short and all 18 angles exist; the clear-peak rule does not apply.
# Every OpenCap video IK result against its motion-capture IK, with the pipeline's comparison steps
# (validation.compare: degrees, aliases, sagittal lag over +-4 s, resampling, coverage). Clear-peak rule and
# evaluated rule as in the note. Args: video_ik_root mocap_ik_root out_json
import json, sys, re, numpy as np
from pathlib import Path
from multiprocessing import Pool
from rehabtwin import validation as V
from rehabtwin.io_formats import read_table, to_degrees
VID, MOC, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
SET = ["pelvis_tilt", "pelvis_list", "pelvis_rotation"] + [f"{c}_{s}" for s in "rl" for c in ("hip_flexion", "hip_adduction", "hip_rotation", "knee_angle", "ankle_angle", "subtalar_angle")] + ["lumbar_extension", "lumbar_bending", "lumbar_rotation"]
def movement(t):
    return "walking" if t.startswith("walking") else "squat" if t.startswith("squats") else "sit-to-stand" if t.startswith("STS") else "drop jump" if t.startswith("DJ") else "other"
def one(p):
    parts = p.parts; i = parts.index("Video"); subj = [x for x in parts if re.fullmatch(r"subject\d+", x)][0]
    est_name, cams, trial = parts[i + 1], parts[i + 2], p.stem
    rec = dict(subject=subj, estimator=est_name, cameras=cams, trial=trial, movement=movement(trial))
    refp = next(MOC.glob(f"*/{subj}/OpenSimData/Mocap/IK/{trial}.mot"), None)
    if refp is None: return dict(rec, status="not run: no motion capture")
    try:
        e0, r0 = read_table(p), read_table(refp)
        est, ref = to_degrees(e0), to_degrees(r0)
        ref, _ = V._apply_aliases(est, ref, V.DEFAULT_ALIASES)
        ang = [c for c in est.columns if c in ref.columns and V.classify(c)[1] in ("sagittal", "frontal", "transverse")]
        sag = [c for c in ang if V.classify(c)[1] == "sagittal"] or ang
        dt = float(np.median(np.diff(est.time))); lags = np.array([0.0]); obj = []
        for lag in lags:
            r = V._resample(V.Table(ref.columns, ref.data, ref.time + lag), est.time); errs = []
            for c in sag:
                d = est.col(c) - r[:, ref.columns.index(c)]; d = d[np.isfinite(d)]
                if len(d) > 10: errs.append(np.mean(d ** 2))
            obj.append(np.mean(errs) if errs else np.inf)
        obj = np.array(obj); i0 = int(np.argmin(obj)); best = float(lags[i0])
        mins = [k for k in range(len(obj)) if np.isfinite(obj[k]) and (k == 0 or obj[k] < obj[k-1]) and (k == len(obj)-1 or obj[k] <= obj[k+1])]
        oth = [k for k in mins if abs(lags[k] - best) > 0.3]; ratio = float(min(obj[k] for k in oth) / obj[i0]) if oth else float("inf")
        clear = bool(np.isfinite(obj[i0]) and 4 - abs(best) >= 0.2 and ratio >= 2.0)
        cov = V.coverage(est.time, ref.time, best); short = cov["fraction"] < V.MIN_COVERAGE
        r = V._resample(V.Table(ref.columns, ref.data, ref.time + best), est.time); per = {}
        for c in SET:
            if c in est.columns and c in ref.columns:
                d = est.col(c) - r[:, ref.columns.index(c)]; d = d[np.isfinite(d)]
                if len(d) >= 2: per[c] = dict(mae=float(np.mean(np.abs(d))), bias=float(np.mean(d)), spread=float(np.std(d)), rmse=float(np.sqrt(np.mean(d ** 2))))
        missing = [c for c in SET if c not in per]
        ok = not short and not missing
        why = [] if ok else (["coverage short"] if short else []) + ([f"missing {missing}"] if missing else [])
        return dict(rec, status="evaluated" if ok else "run, not evaluated", why=why, lag_s=round(best, 4), ratio=round(ratio, 2) if np.isfinite(ratio) else None,
                    coverage=cov["fraction"], mae18=float(np.mean([per[c]["mae"] for c in SET])) if not missing else None, per=per)
    except Exception as ex:
        return dict(rec, status="run, not evaluated", why=[f"error: {type(ex).__name__}: {ex}"])
if __name__ == "__main__":
    files = sorted(VID.glob("**/OpenSimData/Video/*/*/IK/*.mot"))
    with Pool(16) as pool: rows = pool.map(one, files, chunksize=4)
    json.dump(dict(set=SET, rows=rows), open(OUT, "w"))
    import collections
    print(len(rows), collections.Counter(r["status"] for r in rows))
    print(collections.Counter(w.split(":")[0] for r in rows for w in r.get("why", [])))
