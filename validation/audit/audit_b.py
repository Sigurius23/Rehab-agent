"""Audit part B: NHANES (DXA / age-sex / height-mass against knee strength) and MyoSegmenTUM, recomputed from the
raw survey files and the per-person rows with code written for the audit. Writes audit_b.json."""
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

SP, REPO, OUT = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
results = []


def check(section, claim, stated, measured, ok, note=""):
    results.append({"section": section, "claim": claim, "stated": stated, "measured": measured, "ok": bool(ok),
                    "note": note})
    print(f"[{'OK  ' if ok else 'DIFF'}] {section}: {claim} | stated {stated} | measured {measured} {note}")


# the shipped coefficients, read as text from capacity.py (not imported)
src = (REPO / "pipeline/rehabtwin/capacity.py").read_text()
COEF = np.array([float(x) for x in re.search(r"LEG_LEAN_MODEL = \(([^)]*)\)", src).group(1).split(",")])


def terms(age, male, h, m):
    a, s = np.asarray(age, float), np.asarray(male, float)
    return np.column_stack([np.ones(len(a)), a, (a - 50) ** 2 / 100, s, h, m, s * a, s * h, s * m])


D = SP / "nhanes_data"
read = lambda name: pd.read_sas(D / f"{name}.xpt", format="xport")


def dxa(suffix):
    x = read(f"DXX{suffix}")
    x = x[(x.DXAEXSTS == 1) & (x.DXITOT.abs() < 1e-50)]          # measured scan, no region imputed
    spread = x.groupby("SEQN")[["DXDRLLE", "DXDLLLE"]].agg(lambda v: v.max() - v.min()).max(axis=1)
    return x[(x._MULT_ == 1) & x.SEQN.isin(spread[spread < 1e-6].index)]   # legs identical in all implicates


# ---- fit-default: refit the leg-lean model on all adults ----------------------------------------------------
frames = []
for s in ("", "_B"):
    x = dxa(s)[["SEQN", "DXDRLLE", "DXDLLLE"]]
    x = x.merge(read(f"DEMO{s}")[["SEQN", "RIDAGEYR", "RIAGENDR", "RIDEXPRG"]], on="SEQN")
    x = x.merge(read(f"BMX{s}")[["SEQN", "BMXWT", "BMXHT"]], on="SEQN").dropna(subset=["BMXWT", "BMXHT", "DXDRLLE", "DXDLLLE"])
    frames.append(x[(x.RIDAGEYR >= 18) & (x.RIDEXPRG != 1)])
ad = pd.concat(frames)
X = terms(ad.RIDAGEYR, ad.RIAGENDR == 1, ad.BMXHT / 100, ad.BMXWT)
beta, *_ = np.linalg.lstsq(X, (ad.DXDRLLE + ad.DXDLLLE).to_numpy() / 2000, rcond=None)
check("nhanes", "leg-lean model refitted on all NHANES 1999-2002 adults with DXA", "n 7528, coefficients as shipped",
      f"n {len(ad)}, max coefficient difference {np.abs(beta - COEF).max():.1e}", len(ad) == 7528 and np.allclose(beta, COEF, atol=1e-5))

# ---- knee strength cohort --------------------------------------------------------------------------------------
rows = []
for s in ("", "_B"):
    q = read(f"MSX{s}")
    q = q[q.MSDPF.notna() & q.MSXARML.between(20, 60) & q.MSDPFVEL.between(50, 70)].copy()
    q["torque"] = q.MSDPF * q.MSXARML / 100
    x = q[["SEQN", "torque"]].merge(dxa(s)[["SEQN", "DXDRLLE", "DXDLLLE"]], on="SEQN")
    x = x.merge(read(f"DEMO{s}")[["SEQN", "RIDAGEYR", "RIAGENDR"]], on="SEQN")
    x = x.merge(read(f"BMX{s}")[["SEQN", "BMXWT", "BMXHT"]], on="SEQN").dropna(subset=["BMXWT", "BMXHT", "DXDRLLE", "DXDLLLE"])
    rows.append(x[x.RIDAGEYR >= 50])
c = pd.concat(rows)
male, h, m = (c.RIAGENDR == 1).to_numpy(), (c.BMXHT / 100).to_numpy(), c.BMXWT.to_numpy()
pred = {"height and mass": 47 * m * h + 1285,                                   # Handsfield (only proportions matter)
        "age, sex, height, mass": 0.78 * (terms(c.RIDAGEYR, male, h, m) @ COEF) - 0.535,
        "DXA (right leg)": 0.78 * c.DXDRLLE.to_numpy() / 1000 - 0.535}
t = c.torque.to_numpy()
check("nhanes", "adults 50+ with knee strength and DXA", "2104", str(len(c)), len(c) == 2104)
STATED = {"all": [(0.65, 28.0), (0.75, 23.7), (0.79, 22.3)], "women": [(0.51, 24.4), (0.56, 23.5), (0.62, 22.4)],
          "men": [(0.51, 24.3), (0.58, 23.0), (0.65, 21.5)]}
for g, sel in (("all", np.ones(len(c), bool)), ("women", ~male), ("men", male)):
    got = []
    for k in pred:
        ratio = t[sel] / pred[k][sel]
        got.append((np.corrcoef(t[sel], pred[k][sel])[0, 1], 100 * ratio.std(ddof=1) / ratio.mean()))
    ok = all(abs(a - sa) < 0.006 and abs(b - sb) < 0.06 for (a, b), (sa, sb) in zip(got, STATED[g]))
    check("nhanes", f"{g}: r / person-to-person spread, height-mass -> age-sex -> DXA",
          " -> ".join(f"{a:.2f} / {b:.1f} %" for a, b in STATED[g]), " -> ".join(f"{a:.3f} / {b:.1f} %" for a, b in got), ok)

# ---- MyoSegmenTUM ---------------------------------------------------------------------------------------------
r = json.loads((SP / "myoseg_work/results_v2.json").read_text())
early = [x for x in r["rows"] if x["healthy"] and int(x["id"][2:]) <= 11]
meas = np.array([x["strength_Nm"]["R60"] for x in early])
got = {}
for k in ("generic", "regression", "imaging"):
    p = np.array([x["model_Nm"][k]["60"] for x in early])
    ratio = meas / p
    got[k] = (np.corrcoef(meas, p)[0, 1], 100 * ratio.std(ddof=1) / ratio.mean())
check("myosegmentum", "knee extension at 60 deg, HV001-HV011: r and spread, regression vs MRI volume + fat",
      "r 0.44 -> 0.86, spread 16 % -> 10 %", f"r {got['regression'][0]:.2f} -> {got['imaging'][0]:.2f}, spread "
      f"{got['regression'][1]:.1f} % -> {got['imaging'][1]:.1f} % (n={len(early)}; generic r {got['generic'][0]:.2f})",
      abs(got["regression"][0] - 0.44) < 0.006 and abs(got["imaging"][0] - 0.86) < 0.006
      and abs(got["regression"][1] - 16.3) < 0.1 and abs(got["imaging"][1] - 9.9) < 0.1)
healthy = [x for x in r["rows"] if x["healthy"]]
legs = [(x["measured"][s]["QF"]["volume_cm3"], x["predicted_cm3"]["QF"]) for x in healthy for s in ("R", "L")
        if s in x["measured"] and "QF" in x["measured"][s]]
ratio = np.array([a / b for a, b in legs])
check("myosegmentum", "quadriceps measured / height-mass regression, healthy legs", "0.75, spread 15 %",
      f"{ratio.mean():.3f}, spread {100 * ratio.std(ddof=1) / ratio.mean():.1f} % (n={len(legs)} legs)",
      abs(ratio.mean() - 0.75) < 0.006 and abs(100 * ratio.std(ddof=1) / ratio.mean() - 15.4) < 0.15)
pat = [(x["measured"][s]["QF"]["volume_cm3"], x["predicted_cm3"]["QF"]) for x in r["rows"] if not x["healthy"]
       for s in ("R", "L") if s in x["measured"] and "QF" in x["measured"][s]]
pr = np.array([a / b for a, b in pat])
check("myosegmentum", "patients' quadriceps measured / regression", "0.49 (the regression gives twice theirs)",
      f"{pr.mean():.3f} (n={len(pat)} legs)", abs(pr.mean() - 0.49) < 0.006)
# age-and-sex default on the same healthy people: quadriceps share of the model's leg (1854.5 / 7089 cm3)
share = r["reference_volumes_cm3"]["QF"] / 7089.0
qf = np.array([np.mean([x["measured"][s]["QF"]["volume_cm3"] for s in ("R", "L")]) for x in healthy])
lean = terms([x["age"] for x in healthy], [x["sex"] == "m" for x in healthy], [x["height_m"] for x in healthy],
             [x["mass_kg"] for x in healthy]) @ COEF
pq = share * (0.78 * lean - 0.535) * 1000 / 1.06
reg = np.array([x["predicted_cm3"]["QF"] for x in healthy])
check("myosegmentum", "quadriceps measured / predicted: height-mass regression vs age-and-sex default (15 healthy)",
      "0.75 -> 0.93, r 0.54 -> 0.60", f"{(qf / reg).mean():.3f} -> {(qf / pq).mean():.3f}, r {np.corrcoef(qf, reg)[0, 1]:.3f} -> "
      f"{np.corrcoef(qf, pq)[0, 1]:.3f}", abs((qf / pq).mean() - 0.93) < 0.01 and abs(np.corrcoef(qf, pq)[0, 1] - 0.60) < 0.01)

json.dump({"checks": results}, open(OUT, "w"), indent=1)
print(f"{sum(x['ok'] for x in results)} of {len(results)} checks match")
