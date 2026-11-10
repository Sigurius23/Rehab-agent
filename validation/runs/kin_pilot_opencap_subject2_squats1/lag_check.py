# Alignment check before any error is computed: the pipeline's own lag objective (validation.best_lag: mean over
# the shared sagittal angular coordinates of the squared difference, estimate minus lag-shifted reference) over the
# whole search window, built as `rehabtwin process` builds its comparison. Prints only the lag and ratios, no error.
# Criterion, fixed 2026-11-10 before the first check: one clear peak = the best lag lies at least 0.2 s inside the
# +-max_lag window, and every other local minimum more than 0.3 s away has an objective at least 2x the best's.
# Args: estimate_mot scaled_model reference_mot reference_model label [max_lag_s]
import json, sys
from pathlib import Path
import numpy as np
from rehabtwin import metrics as M, validation as V
from rehabtwin.io_formats import read_table, to_degrees
est_mot, est_model, ref_mot, ref_model, label = sys.argv[1:6]
max_lag = float(sys.argv[6]) if len(sys.argv) > 6 else 4.0
est = read_table(est_mot)
est = M.with_signals(est, M.derived_signals(est, Path(est_model)))
ref = to_degrees(read_table(ref_mot), Path(ref_model))
ref = M.with_signals(ref, M.derived_signals(ref, Path(ref_model)))
est, ref = to_degrees(est), to_degrees(ref)
ref, _ = V._apply_aliases(est, ref, V.DEFAULT_ALIASES)
shared = [c for c in est.columns if c in ref.columns]
angular = [c for c in shared if V.classify(c)[1] in ("sagittal", "frontal", "transverse")]
coords = [c for c in angular if V.classify(c)[1] == "sagittal"] or angular
dt = float(np.median(np.diff(est.time)))
lags = np.arange(-max_lag, max_lag + dt / 2, dt)
obj = []
for lag in lags:
    r = V._resample(V.Table(ref.columns, ref.data, ref.time + lag), est.time)
    errs = []
    for c in coords:
        d = est.col(c) - r[:, ref.columns.index(c)]
        d = d[np.isfinite(d)]
        if len(d) > 10:
            errs.append(np.mean(d ** 2))
    obj.append(np.mean(errs) if errs else np.inf)
obj = np.array(obj)
i0 = int(np.argmin(obj)); best = float(lags[i0])
assert abs(best - V.best_lag(est, ref, coords, max_lag)) < 1e-9, "differs from the pipeline's best_lag"
mins = [i for i in range(len(obj)) if np.isfinite(obj[i]) and (i == 0 or obj[i] < obj[i - 1]) and (i == len(obj) - 1 or obj[i] <= obj[i + 1])]
others = [i for i in mins if abs(lags[i] - best) > 0.3]
ratio = float(min(obj[i] for i in others) / obj[i0]) if others else float("inf")
inside = (max_lag - abs(best)) >= 0.2
res = dict(label=label, coords=len(coords), step_s=round(dt, 4), best_lag_s=round(best, 4),
           best_lag_inside_window=inside, local_minima=len(mins),
           next_minimum=None if not others else dict(lag_s=round(float(lags[min(others, key=lambda i: obj[i])]), 3), ratio_to_best=round(ratio, 2)),
           clear_peak=bool(inside and ratio >= 2.0))
print(json.dumps(res))
