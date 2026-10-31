"""NHANES 1999-2002: does a DXA scan predict a person's leg strength better than height and mass? And the twin's
leg-lean model from age, sex, height and mass.

NHANES measured isokinetic knee-extension strength (Kin-Com dynamometer, 60 °/s, examinees aged 50 and over:
peak force and the lever-arm length, so torque = force × lever arm) in the same people who had whole-body DXA
(lean, fat and bone mass per arm, leg and trunk). That tests the two ways the twin can size a person's leg
muscles (``rehabtwin/capacity.py``):

- **height and mass:** the Handsfield 2014 regression, the twin's default when it knows nothing else;
- **age, sex, height and mass:** leg lean predicted by ``capacity.LEG_LEAN_MODEL`` (``fit-default`` fits it on all
  NHANES adults with DXA), then the McCarthy equation below;
- **with DXA:** leg skeletal muscle from DXA leg lean mass, SM = 0.78 × leg lean − 1.07 kg for both legs (McCarthy
  et al. 2023, Sci Rep 13:2580, Deming regression against whole-body MRI in 475 adults; validation RMSE 0.95 kg),
  applied per leg with half the intercept each.

With the model scaled uniformly to a person's height, fibre lengths and moment arms grow together, so the model's
isometric knee torque is proportional to the muscle volume it is given. Each estimate is therefore compared with
the measured torque directly: the correlation, and the spread of measured / predicted between people (CV) after
the common bias (specific tension, voluntary activation, generic moment arms) is divided out. A model fitted to
age, sex, height and weight, with and without DXA leg lean, is trained on 1999-2000 and tested on 2001-2002 as the
fairer baseline.

Data (public domain, CDC): DEMO, BMX, DXX and MSX for 1999-2000 and DEMO_B, BMX_B, DXX_B, MSX_B for 2001-2002, as
.xpt files in one folder (``download``). Needs pandas (``pip install pandas``); the data stays outside the
repository.

    python adapters/nhanes_strength.py download DATA_DIR
    python adapters/nhanes_strength.py analyse DATA_DIR --out results.json
    python adapters/nhanes_strength.py fit-default DATA_DIR --out leg_lean_model.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

CYCLES = {"1999-2000": ("1999", ""), "2001-2002": ("2001", "_B")}
TABLES = ("DEMO", "BMX", "DXX", "MSX")
URL = "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/{year}/DataFiles/{name}.xpt"
MCCARTHY_SLOPE, MCCARTHY_INTERCEPT_KG = 0.78, -1.07       # both legs; per leg: half the intercept
MUSCLE_DENSITY = 1.06                                      # g/cm³
QUADRICEPS_REF_CM3 = 1854.0                                # the generic model's quadriceps (one leg)


def download(data_dir):
    import urllib.request
    d = Path(data_dir)
    d.mkdir(parents=True, exist_ok=True)
    for year, suffix in CYCLES.values():
        for t in TABLES:
            name = t + suffix
            if not (d / f"{name}.xpt").exists():
                urllib.request.urlretrieve(URL.format(year=year, name=name), d / f"{name}.xpt")
                print(name, "downloaded", file=sys.stderr)


def _rehabtwin():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def leg_muscle_kg(leg_lean_kg):
    """Skeletal muscle of one leg from its DXA lean soft tissue (McCarthy 2023, intercept split between legs)."""
    return MCCARTHY_SLOPE * np.asarray(leg_lean_kg, float) + MCCARTHY_INTERCEPT_KG / 2


def regression_quadriceps_cm3(mass_kg, height_m):
    """The twin's default without imaging: the generic quadriceps scaled by Handsfield's limb volume ratio."""
    _rehabtwin()
    from rehabtwin import capacity
    ref = capacity.limb_muscle_volume_cm3(capacity.REFERENCE["mass_kg"], capacity.REFERENCE["height_m"])
    return np.array([QUADRICEPS_REF_CM3 * capacity.limb_muscle_volume_cm3(m, h) / ref for m, h in zip(mass_kg, height_m)])


def cohort(data_dir, cycle):
    """One row per eligible examinee: strength measured, DXA measured with no region imputed (first implicate,
    identical leg values across the five implicates), height and weight present."""
    import pandas as pd
    _, s = CYCLES[cycle]
    d = Path(data_dir)
    t = {k: pd.read_sas(d / f"{k}{s}.xpt", format="xport") for k in TABLES}
    msx = t["MSX"]
    msx = msx[msx.MSDPF.notna() & msx.MSXARML.between(20, 60) & msx.MSDPFVEL.between(50, 70)].copy()
    msx["torque_Nm"] = msx.MSDPF * msx.MSXARML / 100
    dxx = t["DXX"]
    dxx = dxx[(dxx.DXAEXSTS == 1) & (dxx.DXITOT.abs() < 1e-50)]
    spread = dxx.groupby("SEQN")[["DXDRLLE", "DXDLLLE"]].agg(lambda v: v.max() - v.min()).max(axis=1)
    consistent = spread[spread < 1e-6].index
    dxx = dxx[(dxx._MULT_ == 1) & dxx.SEQN.isin(consistent)]
    demo = t["DEMO"][["SEQN", "RIDAGEYR", "RIAGENDR"]]
    bmx = t["BMX"][["SEQN", "BMXWT", "BMXHT"]]
    df = msx.merge(dxx[["SEQN", "DXDRLLE", "DXDLLLE", "DXXRLFAT", "DXXLLFAT"]], on="SEQN").merge(demo, on="SEQN")
    df = df.merge(bmx, on="SEQN").dropna(subset=["BMXWT", "BMXHT", "DXDRLLE", "DXDLLLE"])
    df = df[df.RIDAGEYR >= 50]
    out = pd.DataFrame({"seqn": df.SEQN.astype(int), "cycle": cycle, "age": df.RIDAGEYR, "male": (df.RIAGENDR == 1).astype(int),
                        "mass_kg": df.BMXWT, "height_m": df.BMXHT / 100, "torque_Nm": df.torque_Nm,
                        "lean_r_kg": df.DXDRLLE / 1000, "lean_l_kg": df.DXDLLLE / 1000,
                        "fat_r_kg": df.DXXRLFAT / 1000, "fat_l_kg": df.DXXLLFAT / 1000})
    out["bmi"] = out.mass_kg / out.height_m ** 2
    return out.reset_index(drop=True)


LEAN_TERMS = ("1", "age", "(age - 50)^2/100", "male", "height_m", "mass_kg", "male*age", "male*height_m", "male*mass_kg")


def _lean_terms(age, male, height_m, mass_kg):
    a, m, h, w = (np.asarray(v, float) for v in (age, male, height_m, mass_kg))
    return np.column_stack([np.ones(len(a)), a, (a - 50) ** 2 / 100, m, h, w, m * a, m * h, m * w])


def adults(data_dir, cycle):
    """Every adult (18+, not pregnant) with a measured whole-body DXA, no region imputed: mean leg lean (kg)."""
    import pandas as pd
    _, s = CYCLES[cycle]
    d = Path(data_dir)
    dxx = pd.read_sas(d / f"DXX{s}.xpt", format="xport")
    dxx = dxx[(dxx.DXAEXSTS == 1) & (dxx.DXITOT.abs() < 1e-50)]
    spread = dxx.groupby("SEQN")[["DXDRLLE", "DXDLLLE"]].agg(lambda v: v.max() - v.min()).max(axis=1)
    dxx = dxx[(dxx._MULT_ == 1) & dxx.SEQN.isin(spread[spread < 1e-6].index)]
    demo = pd.read_sas(d / f"DEMO{s}.xpt", format="xport")[["SEQN", "RIDAGEYR", "RIAGENDR", "RIDEXPRG"]]
    bmx = pd.read_sas(d / f"BMX{s}.xpt", format="xport")[["SEQN", "BMXWT", "BMXHT"]]
    df = dxx[["SEQN", "DXDRLLE", "DXDLLLE"]].merge(demo, on="SEQN").merge(bmx, on="SEQN")
    df = df.dropna(subset=["BMXWT", "BMXHT", "DXDRLLE", "DXDLLLE"])
    df = df[(df.RIDAGEYR >= 18) & (df.RIDEXPRG != 1)]
    return pd.DataFrame({"cycle": cycle, "age": df.RIDAGEYR, "male": (df.RIAGENDR == 1).astype(float),
                         "height_m": df.BMXHT / 100, "mass_kg": df.BMXWT,
                         "lean_kg": (df.DXDRLLE + df.DXDLLLE) / 2000}).reset_index(drop=True)


def fit_default(data_dir):
    """Least squares of mean leg lean on LEAN_TERMS: trained on 1999-2000 and tested on 2001-2002, then refitted on
    both (the coefficients ``capacity.LEG_LEAN_MODEL`` holds)."""
    import pandas as pd
    df = pd.concat([adults(data_dir, c) for c in CYCLES], ignore_index=True)
    X = lambda f: _lean_terms(f.age, f.male, f.height_m, f.mass_kg)
    tr, te = df[df.cycle == "1999-2000"], df[df.cycle == "2001-2002"]
    beta, *_ = np.linalg.lstsq(X(tr), tr.lean_kg.to_numpy(), rcond=None)
    err = X(te) @ beta - te.lean_kg.to_numpy()
    rel = np.abs(err) / te.lean_kg.to_numpy()
    groups = {"18-49": te.age < 50, "50+": te.age >= 50, "BMI >= 30": te.mass_kg / te.height_m ** 2 >= 30,
              "women": te.male == 0, "men": te.male == 1}
    final, *_ = np.linalg.lstsq(X(df), df.lean_kg.to_numpy(), rcond=None)
    _rehabtwin()
    from rehabtwin import capacity
    return {"terms": list(LEAN_TERMS), "coef": [round(float(b), 6) for b in final], "n": len(df),
            "ages": [int(df.age.min()), int(df.age.max())],
            "test_2001_2002": {"n": len(te), "mae_kg": round(float(np.abs(err).mean()), 3),
                               "mae_pct": round(float(rel.mean() * 100), 2), "bias_kg": round(float(err.mean()), 3),
                               "by_group_mae_pct": {k: round(float(rel[v.to_numpy()].mean() * 100), 1)
                                                    for k, v in groups.items()}},
            "matches_capacity_LEG_LEAN_MODEL": bool(np.allclose(final, capacity.LEG_LEAN_MODEL, atol=1e-5))}


def _proportional(measured, predicted):
    m, p = np.asarray(measured, float), np.asarray(predicted, float)
    ratio = m / p
    return {"n": len(m), "r": round(float(np.corrcoef(m, p)[0, 1]), 3),
            "ratio_mean": round(float(ratio.mean()), 4), "spread_cv_pct": round(float(ratio.std(ddof=1) / ratio.mean() * 100), 1)}


def _fit(train, test, cols):
    X = np.column_stack([np.ones(len(train))] + [train[c] for c in cols])
    beta, *_ = np.linalg.lstsq(X, train.torque_Nm.to_numpy(), rcond=None)
    pred = np.column_stack([np.ones(len(test))] + [test[c] for c in cols]) @ beta
    err = test.torque_Nm.to_numpy() - pred
    ss = ((test.torque_Nm - test.torque_Nm.mean()) ** 2).sum()
    return {"features": cols, "test_r2": round(float(1 - (err ** 2).sum() / ss), 3),
            "test_mae_Nm": round(float(np.abs(err).mean()), 1),
            "test_mae_pct": round(float(np.mean(np.abs(err) / test.torque_Nm) * 100), 1)}


def analyse(data_dir):
    import pandas as pd
    df = pd.concat([cohort(data_dir, c) for c in CYCLES], ignore_index=True)
    df["v_regression"] = regression_quadriceps_cm3(df.mass_kg, df.height_m)
    for side in ("r", "l"):
        df[f"v_dxa_{side}"] = leg_muscle_kg(df[f"lean_{side}_kg"]) * 1000 / MUSCLE_DENSITY
    df["v_dxa_mean"] = (df.v_dxa_r + df.v_dxa_l) / 2
    _rehabtwin()
    from rehabtwin import capacity
    lean = _lean_terms(df.age, df.male, df.height_m, df.mass_kg) @ np.asarray(capacity.LEG_LEAN_MODEL)
    df["v_anthropometry"] = leg_muscle_kg(lean) * 1000 / MUSCLE_DENSITY
    groups = {"all": df, "women": df[df.male == 0], "men": df[df.male == 1], "age 50-64": df[df.age < 65],
              "age 65+": df[df.age >= 65], "BMI >= 30": df[df.bmi >= 30]}
    out = {"cohort": {c: int((df.cycle == c).sum()) for c in CYCLES}, "proportional": {}, "fitted": {}}
    for g, sub in groups.items():
        out["proportional"][g] = {k: _proportional(sub.torque_Nm, sub[k]) for k in
                                  ("v_regression", "v_anthropometry", "v_dxa_r", "v_dxa_l", "v_dxa_mean")}
    train, test = df[df.cycle == "1999-2000"].copy(), df[df.cycle == "2001-2002"].copy()
    for frame in (train, test):
        frame["male_age"] = frame.male * frame.age
        frame["male_height"] = frame.male * frame.height_m
    base = ["age", "male", "height_m", "mass_kg", "male_age", "male_height"]
    out["fitted"] = {"anthropometry": _fit(train, test, base),
                     "anthropometry + right leg lean": _fit(train, test, [*base, "lean_r_kg"]),
                     "anthropometry + left leg lean": _fit(train, test, [*base, "lean_l_kg"]),
                     "anthropometry + both leg lean": _fit(train, test, [*base, "lean_r_kg", "lean_l_kg"]),
                     "anthropometry + both leg lean and fat": _fit(train, test, [*base, "lean_r_kg", "lean_l_kg",
                                                                                 "fat_r_kg", "fat_l_kg"])}
    return out, df


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    dl = sub.add_parser("download", help="the eight NHANES .xpt files (public domain, ~75 MB)")
    dl.add_argument("data_dir")
    an = sub.add_parser("analyse", help="DXA leg lean vs the height-and-mass regression against measured torque")
    an.add_argument("data_dir")
    an.add_argument("--out", required=True)
    fd = sub.add_parser("fit-default", help="refit capacity.LEG_LEAN_MODEL (leg lean from age, sex, height, mass)")
    fd.add_argument("data_dir")
    fd.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "download":
        download(a.data_dir)
        return
    if a.cmd == "fit-default":
        res = fit_default(a.data_dir)
        Path(a.out).write_text(json.dumps(res, indent=1))
        print(json.dumps(res, indent=1))
        return
    res, _ = analyse(a.data_dir)
    Path(a.out).write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
