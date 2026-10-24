"""Bone density of the person (DXA or QCT), as a screening flag the twin's load what-ifs must show.

Bone density is not part of the OpenSim model: segment masses and joint motion do not depend on it. It matters
for what the twin may suggest: device torques, corrections that shift load, and exercise progression on a
person with osteoporosis need a clinician's sign-off. This module classifies a measured scan with the standard
categories and never diagnoses:

- DXA, T-score (postmenopausal women, men aged 50 and over; WHO categories, ISCD official positions):
  T <= -2.5 osteoporosis, -2.5 < T < -1.0 low bone mass, T >= -1.0 normal.
- DXA, Z-score (premenopausal women, men under 50; ISCD): Z <= -2.0 "below the expected range for age",
  otherwise "within the expected range for age".
- QCT, lumbar spine volumetric BMD (ACR practice parameter): < 80 mg/cm³ osteoporosis, 80-120 low bone mass,
  > 120 normal.

The DXA sites the categories apply to are the lumbar spine (L1-L4), total hip and femoral neck; the lowest
classified site counts. Raw Hounsfield units from an ordinary CT are not a bone density and are refused.
"""
from __future__ import annotations

DXA_SITES = ("lumbar_spine_L1_L4", "total_hip", "femoral_neck", "distal_radius_33")
QCT_SITES = ("lumbar_spine_L1_L2", "lumbar_spine_L1_L3")
ORDER = {"osteoporosis": 0, "below the expected range for age": 0, "low bone mass": 1, "normal": 2,
         "within the expected range for age": 2}


def check(record):
    """Refuse a bone-density record the categories cannot be applied to."""
    method = str(record.get("method", ""))
    sites = record.get("sites") or {}
    if not sites:
        raise ValueError("bone density record needs 'sites' (e.g. {'femoral_neck': {'t_score': -1.8, 'bmd_g_cm2': 0.71}})")
    if not record.get("date"):
        raise ValueError("bone density record needs the scan 'date'")
    kind = "QCT" if method.upper().startswith("QCT") else "DXA" if method.upper().startswith("DXA") else None
    if kind is None:
        raise ValueError(f"bone density method {method!r}: must start with 'DXA' or 'QCT' (ordinary CT Hounsfield "
                         "units are not a calibrated bone density)")
    allowed = QCT_SITES if kind == "QCT" else DXA_SITES
    for site, v in sites.items():
        if site not in allowed:
            raise ValueError(f"{kind} site {site!r}: one of {allowed}")
        if "hu" in {k.lower() for k in v} or "mean_hu" in v:
            raise ValueError(f"{site}: Hounsfield units are not a bone density; give the calibrated value")
        if kind == "QCT" and not v.get("vbmd_mg_cm3"):
            raise ValueError(f"QCT {site}: needs vbmd_mg_cm3")
        if kind == "DXA" and v.get("t_score") is None and v.get("z_score") is None:
            raise ValueError(f"DXA {site}: needs t_score and/or z_score as the scanner reports them")
    return kind


def score_for(record):
    """'T' or 'Z': which DXA score the categories use for this person (ISCD)."""
    age, sex = record.get("age_years"), str(record.get("sex", "")).lower()
    if age is None or sex not in ("female", "male"):
        raise ValueError("DXA classification needs age_years and sex ('female' or 'male') at the scan")
    if sex == "male":
        return "T" if age >= 50 else "Z"
    post = record.get("postmenopausal")
    if post is None:
        raise ValueError("DXA classification of a woman needs 'postmenopausal' (true/false): it decides T- or Z-score")
    return "T" if post else "Z"


def classify(record):
    """{'category', 'site', 'value', 'basis', 'per_site'}: the lowest classified site of a checked record."""
    kind = check(record)
    per = {}
    if kind == "QCT":
        for site, v in record["sites"].items():
            x = float(v["vbmd_mg_cm3"])
            per[site] = ("osteoporosis" if x < 80 else "low bone mass" if x <= 120 else "normal", f"vBMD {x:g} mg/cm³")
        basis = "QCT lumbar spine vBMD (ACR: < 80 osteoporosis, 80-120 low bone mass)"
    else:
        score = score_for(record)
        for site, v in record["sites"].items():
            x = v.get("t_score" if score == "T" else "z_score")
            if x is None:
                continue
            x = float(x)
            if score == "T":
                cat = "osteoporosis" if x <= -2.5 else "low bone mass" if x < -1.0 else "normal"
            else:
                cat = "below the expected range for age" if x <= -2.0 else "within the expected range for age"
            per[site] = (cat, f"{score}-score {x:+.1f}")
        if not per:
            raise ValueError(f"DXA: no site has the {score}-score this person's categories use")
        basis = ("DXA T-score (WHO categories)" if score == "T" else "DXA Z-score (ISCD: <= -2.0 below expected range)")
    site = min(per, key=lambda s: ORDER[per[s][0]])
    return {"category": per[site][0], "site": site, "value": per[site][1], "basis": basis, "date": record["date"],
            "method": record["method"], "per_site": {s: {"category": c, "value": v} for s, (c, v) in per.items()}}


def caveat(status):
    """One line for load what-ifs (devices, corrections), or None when bone density gives no reason for one."""
    if not status:
        return ("Bone density not measured: device loads and exercise progression assume healthy bone; a DXA scan "
                "fills this in (rehabtwin person bone).")
    if ORDER[status["category"]] >= 2:
        return None
    return (f"Bone density: {status['category']} at {status['site'].replace('_', ' ')} ({status['value']}, "
            f"{status['method']} {status['date']}). Device torques, corrections that shift load and exercise "
            "progression need a clinician's sign-off.")
