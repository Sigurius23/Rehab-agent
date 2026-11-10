# Positive control, step 1 (before any error): the lag of OpenCap's squats1.mot against the motion capture, as
# `rehabtwin validate` aligns them (validation.compare: degrees, aliases, sagittal coordinates), and whether its
# peak is clear (criterion as in the pilot: best lag >= 0.2 s inside +-4 s; every other local minimum > 0.3 s away
# >= 2x the best's objective). Prints the lag and ratio only. Args: estimate_mot reference_mot
import json, sys, numpy as np
from rehabtwin import validation as V
from rehabtwin.io_formats import read_table, to_degrees
est, ref = to_degrees(read_table(sys.argv[1])), to_degrees(read_table(sys.argv[2]))
ref, _ = V._apply_aliases(est, ref, V.DEFAULT_ALIASES)
ang = [c for c in est.columns if c in ref.columns and V.classify(c)[1] in ("sagittal", "frontal", "transverse")]
coords = [c for c in ang if V.classify(c)[1] == "sagittal"] or ang
dt = float(np.median(np.diff(est.time))); lags = np.arange(-4, 4 + dt / 2, dt); obj = []
for lag in lags:
    r = V._resample(V.Table(ref.columns, ref.data, ref.time + lag), est.time); e = []
    for c in coords:
        d = est.col(c) - r[:, ref.columns.index(c)]; d = d[np.isfinite(d)]
        if len(d) > 10: e.append(np.mean(d ** 2))
    obj.append(np.mean(e) if e else np.inf)
obj = np.array(obj); i0 = int(np.argmin(obj)); best = float(lags[i0])
assert abs(best - V.best_lag(est, ref, coords, 4.0)) < 1e-9
mins = [i for i in range(len(obj)) if (i == 0 or obj[i] < obj[i-1]) and (i == len(obj)-1 or obj[i] <= obj[i+1])]
oth = [i for i in mins if abs(lags[i] - best) > 0.3]; ratio = float(min(obj[i] for i in oth) / obj[i0]) if oth else float("inf")
print(json.dumps(dict(sagittal_coords=coords, best_lag_s=round(best, 4), inside=bool(4 - abs(best) >= 0.2),
                      next_minimum_s=None if not oth else round(float(lags[min(oth, key=lambda i: obj[i])]), 3),
                      ratio=round(ratio, 2), clear_peak=bool(4 - abs(best) >= 0.2 and ratio >= 2))))
