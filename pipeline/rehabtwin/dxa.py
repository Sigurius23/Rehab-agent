"""A whole-body DXA scan of the person: per-leg muscle, segment mass distribution, regional fat, bone density.

DXA (dual-energy X-ray absorptiometry) splits the body into arms, legs, trunk and head and gives each region's
lean soft tissue, fat and bone mineral content (BMC). The twin uses a regional table from a whole-body scan for:

- **Leg muscle, per leg** (``rehabtwin/capacity.py``): skeletal muscle of both legs = 0.78 × leg lean − 1.07 kg
  (McCarthy et al. 2023, Sci Rep 13:2580: Deming regression against whole-body MRI in 475 adults, Hologic QDR
  4500A; validation RMSE 0.95 kg, R² 0.91), applied per leg with half the intercept each. In NHANES 1999-2002
  (``adapters/nhanes_strength.py``), DXA leg muscle predicted measured knee-extension torque at r = 0.78 against
  0.64 for the height-and-mass regression.
- **Segment masses**: each region's share of the scanned mass (lean + fat + BMC) becomes the share of the model's
  bodies in that region, so a person with heavy legs and a light trunk gets that in inverse dynamics and the
  ground-force estimate. The model's total mass stays the measured body mass; within a region the bodies keep
  their relative masses, and inertia scales with mass (segment shape and centre of mass stay the model's).
- **Regional fat**: recorded as the soft-tissue layer.
- **Bone density** (optional ``bone_density`` part of the record): classified as ``rehabtwin person bone`` does.

What DXA does not give: bone geometry or joint centres (a 2-D projection), individual muscles (lean soft tissue
of a region, ~70 % of it muscle in the legs), muscle quality (fat inside the muscle), or strength. With DXA, the
person-to-person spread of measured torque around the prediction was still 22 % in NHANES (28 % without).

Record (``rehabtwin person dxa FOLDER record.json``), masses in kg as on the scanner's regional table:

    {"method": "DXA Hologic Horizon A whole body", "date": "2026-10-01", "approved_by": "...",
     "regions": {"left_arm": {"lean_kg": 2.9, "fat_kg": 1.1, "bmc_kg": 0.18}, "right_arm": {...},
                 "left_leg": {...}, "right_leg": {...}, "trunk": {...}, "head": {...}},
     "bone_density": {"sites": {"femoral_neck": {"t_score": -1.1}}, "postmenopausal": true}}

``lean_kg`` is lean soft tissue without bone mineral (Hologic tables also list "Lean + BMC": subtract BMC).
"""
from __future__ import annotations

REGIONS = ("left_arm", "right_arm", "left_leg", "right_leg", "trunk", "head")
# DXA regions -> bodies of the Rajagopal / Pose2Sim models
BODIES = {"left_leg": ("femur_l", "patella_l", "tibia_l", "talus_l", "calcn_l", "toes_l"),
          "right_leg": ("femur_r", "patella_r", "tibia_r", "talus_r", "calcn_r", "toes_r"),
          "left_arm": ("humerus_l", "ulna_l", "radius_l", "hand_l"),
          "right_arm": ("humerus_r", "ulna_r", "radius_r", "hand_r"),
          "head": ("head",),
          "trunk": ("pelvis", "sacrum", "lumbar1", "lumbar2", "lumbar3", "lumbar4", "lumbar5", "torso", "Abdomen")}
LEG_LEAN_RANGE_KG = (2.0, 25.0)     # one leg; outside this the table is not kg of one leg's lean soft tissue
MASS_TOL = 0.15                     # scanned mass vs the person's measured mass
FACTOR_RANGE = (0.5, 2.0)           # a region's mass change beyond this is a data error, not a body
METHOD = ("DXA regional lean, fat and BMC. Leg muscle per leg: 0.78 × leg lean − 0.535 kg (McCarthy et al. 2023, "
          "against whole-body MRI). Segment masses: each region's share of the scanned mass, model total kept")


def check(record, mass_kg=None):
    """Refuse a DXA record the twin cannot use; returns {"mass_kg", "mass_check", "distribution"} (what it supports)."""
    method = str(record.get("method", ""))
    if not method.upper().startswith("DXA"):
        raise ValueError(f"DXA record method {method!r}: must start with 'DXA' (a whole-body scan's regional table)")
    if not record.get("date"):
        raise ValueError("DXA record needs the scan 'date'")
    regions = record.get("regions") or {}
    unknown = sorted(set(regions) - set(REGIONS))
    if unknown:
        raise ValueError(f"DXA regions {unknown}: use {list(REGIONS)}")
    for side in ("left_leg", "right_leg"):
        if regions.get(side, {}).get("lean_kg") is None:
            raise ValueError(f"DXA record needs regions.{side}.lean_kg (lean soft tissue of the leg, kg)")
    for name, r in regions.items():
        for k, v in r.items():
            if k not in ("lean_kg", "fat_kg", "bmc_kg"):
                raise ValueError(f"DXA {name}.{k}: give lean_kg, fat_kg and bmc_kg (kg)")
            if not isinstance(v, (int, float)) or v < 0:
                raise ValueError(f"DXA {name}.{k} = {v!r}: a mass in kg, not negative")
            if v > 200:
                raise ValueError(f"DXA {name}.{k} = {v}: looks like grams; the record takes kg")
    lo, hi = LEG_LEAN_RANGE_KG
    for side in ("left_leg", "right_leg"):
        v = regions[side]["lean_kg"]
        if not lo <= v <= hi:
            raise ValueError(f"DXA {side}.lean_kg = {v}: one leg's lean soft tissue is {lo:g}-{hi:g} kg in adults")
    full = all(name in regions and all(regions[name].get(k) is not None for k in ("lean_kg", "fat_kg", "bmc_kg"))
               for name in REGIONS)
    out = {"distribution": full, "mass_kg": None, "mass_check": None}
    if full:
        out["mass_kg"] = round(sum(sum(r.values()) for r in regions.values()), 2)
        if mass_kg:
            d = out["mass_kg"] / mass_kg - 1
            out["mass_check"] = {"scanned_kg": out["mass_kg"], "measured_kg": mass_kg, "difference": round(d, 3)}
            if abs(d) > MASS_TOL:
                raise ValueError(f"the DXA regions add up to {out['mass_kg']:g} kg, {d:+.0%} from the person's measured "
                                 f"{mass_kg:g} kg: another person's scan, grams typed as kg, or a mass from long ago?")
    return out


def leg_lean_kg(record):
    """{"_r": kg, "_l": kg}: lean soft tissue of each leg (capacity.scale_model's ``dxa_leg_lean_kg``)."""
    r = record["regions"]
    return {"_r": float(r["right_leg"]["lean_kg"]), "_l": float(r["left_leg"]["lean_kg"])}


def region_masses(record):
    """{region: kg}: lean + fat + BMC of each region (needs all six)."""
    return {name: sum(record["regions"][name].values()) for name in REGIONS}


def fat_summary(record):
    """Regional and total fat (kg, and % of the region's mass) of a record with all six regions."""
    m = region_masses(record)
    reg = record["regions"]
    out = {name: {"fat_kg": round(reg[name]["fat_kg"], 2), "fat_pct": round(100 * reg[name]["fat_kg"] / m[name], 1)}
           for name in REGIONS}
    fat = sum(reg[n]["fat_kg"] for n in REGIONS)
    out["total"] = {"fat_kg": round(fat, 2), "fat_pct": round(100 * fat / sum(m.values()), 1)}
    return out


def apply_mass_distribution(model, record):
    """Scale the bodies of an OpenSim model so each DXA region's share of its mass is the scan's; returns the record.

    Keeps the model's total mass. Refuses a model without the region's bodies, and a region whose mass would change
    by more than a factor of two (a data error, not a body).
    """
    bodies = model.updBodySet()
    names = {bodies.get(i).getName() for i in range(bodies.getSize())}
    regions = dict(BODIES)
    scanned = region_masses(record)
    if "head" not in names:             # Rajagopal 2016: the torso body carries the head
        regions.pop("head")
        scanned["trunk"] += scanned.pop("head")
    missing = [b for bs in regions.values() for b in bs if b not in names and b not in ("sacrum", "Abdomen", "lumbar1",
                                                                                         "lumbar2", "lumbar3", "lumbar4",
                                                                                         "lumbar5")]
    if missing:
        raise ValueError(f"the model lacks the bodies DXA regions map to ({missing[:4]}...)")
    group = {r: [b for b in bs if b in names] for r, bs in regions.items()}
    mass = {r: sum(bodies.get(b).getMass() for b in bs) for r, bs in group.items()}
    others = [bodies.get(i).getName() for i in range(bodies.getSize())
              if not any(bodies.get(i).getName() in bs for bs in group.values())]
    other_mass = sum(bodies.get(b).getMass() for b in others)
    total = sum(mass.values()) + other_mass
    share = {r: v / sum(scanned.values()) for r, v in scanned.items()}
    available = total - other_mass       # bodies outside the regions (none in these models) keep their mass
    factors = {r: share[r] * available / mass[r] for r in group}
    bad = {r: round(f, 2) for r, f in factors.items() if not FACTOR_RANGE[0] <= f <= FACTOR_RANGE[1]}
    if bad:
        raise ValueError(f"DXA would change these regions' mass by {bad} (more than ×2 either way): check the record")
    for r, bs in group.items():
        for b in bs:
            if bodies.get(b).getMass() > 0:
                bodies.get(b).scaleMass(factors[r])
    after = sum(bodies.get(i).getMass() for i in range(bodies.getSize()))
    return {"method": "each DXA region's share of the scanned mass (lean + fat + BMC); model total kept",
            "total_mass_kg": round(after, 3),
            "regions": {r: {"bodies": group[r], "model_share_before": round(mass[r] / total, 4),
                            "dxa_share": round(share[r], 4), "factor": round(factors[r], 4),
                            "mass_kg": round(mass[r] * factors[r], 3)} for r in group},
            "unchanged_bodies": others}
