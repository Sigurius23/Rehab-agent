"""Leg muscle capacity for this person: measured muscle size and quality where imaging gives them, otherwise
scaled to body size (Handsfield et al. 2014, as used by Rajagopal et al. 2016).

OpenSim's ScaleTool lengthens fibres and tendons with the bones but leaves every muscle's maximum isometric
force (Fmax) at the generic subject's value, so a 50 kg and a 110 kg person get the same leg strength. Fmax is
specific tension × physiological cross-section, and the cross-section is volume / optimal fibre length:

    Fmax = σ · V · q / lopt        q = (1 − fat fraction) / (1 − healthy fat fraction)

The generic leg muscles were built this way with σ = 60 N/cm² (Rajagopal 2016), so the model itself gives each
muscle's reference volume V_ref = Fmax · lopt / σ. Summed over the 40 muscles of one leg that is 7,089 cm³,
97 % of what Handsfield's regression gives for the generic subject (the rest: small muscles the model leaves
out), which checks the regression's units.

Where V comes from, per muscle:
- **Measured** (``imaging``): a muscle or group volume from MRI/CT segmentation, split among the group's model
  muscles by their reference shares.
- **Regression**: Handsfield 2014 measured 35 lower-limb muscles by MRI in 24 young healthy adults. Total limb
  muscle volume followed height × mass, V ≈ 47 · m · h + 1285 (cm³; kg, m), and each muscle kept a near-constant
  share of it. Rajagopal 2016 built the generic leg muscles from this regression for a 75.337 kg, 1.70 m subject.

Muscle quality ``q``: σ applies to the whole volume of healthy young muscle, which holds a few percent fat. A
measured fat fraction (MRI proton-density fat fraction) scales the contractile part against that healthy
level (``HEALTHY_FAT_FRACTION``). CT attenuation (HU) is recorded but not converted: it depends on the scanner
and protocol.

The Pose2Sim model's 80 leg muscles are Rajagopal's; its 238 trunk muscles come from other sources and stay
generic. The regression is a population estimate: on MyoSegmenTUM thigh MRI (15 healthy adults) it gave a third
more quadriceps than measured, +-15 % between people, while measured volume predicted knee-extension strength at
r = 0.86 against its 0.44 (adapters/myosegmentum.py). It gives the leg muscle an average young, healthy adult of this
height and mass has, not this person's strength. Fat mass raises body mass without muscle (BMI > 30), and age,
training and injury change muscle volume and quality; that is what the imaging inputs are for.
"""
from __future__ import annotations

# Rajagopal 2016 lower-limb muscles (each with _r and _l), the ones Handsfield's regression covers
LEG_MUSCLES = ("addbrev", "addlong", "addmagDist", "addmagIsch", "addmagMid", "addmagProx", "bflh", "bfsh", "edl",
               "ehl", "fdl", "fhl", "gaslat", "gasmed", "glmax1", "glmax2", "glmax3", "glmed1", "glmed2", "glmed3",
               "glmin1", "glmin2", "glmin3", "grac", "iliacus", "perbrev", "perlong", "piri", "psoas", "recfem",
               "sart", "semimem", "semiten", "soleus", "tfl", "tibant", "tibpost", "vasint", "vaslat", "vasmed")
# Imaging labels -> model muscles. Map a segmentation tool's labels onto these by its own label definitions.
GROUPS = {"quadriceps": ("recfem", "vaslat", "vasmed", "vasint"),
          "hamstrings": ("bflh", "bfsh", "semimem", "semiten"),
          "adductors": ("addbrev", "addlong", "addmagDist", "addmagIsch", "addmagMid", "addmagProx"),
          "adductor_magnus": ("addmagDist", "addmagIsch", "addmagMid", "addmagProx"),
          "gluteus_maximus": ("glmax1", "glmax2", "glmax3"),
          "gluteus_medius": ("glmed1", "glmed2", "glmed3"),
          "gluteus_minimus": ("glmin1", "glmin2", "glmin3"),
          "iliopsoas": ("iliacus", "psoas"),
          "triceps_surae": ("gaslat", "gasmed", "soleus"),
          "gastrocnemius": ("gaslat", "gasmed"),
          "anterior_leg": ("tibant", "edl", "ehl"),
          "lateral_leg": ("perbrev", "perlong"),
          "deep_posterior_leg": ("tibpost", "fdl", "fhl")}
ALIASES = {"rectus_femoris": "recfem", "vastus_lateralis": "vaslat", "vastus_medialis": "vasmed",
           "vastus_intermedius": "vasint", "biceps_femoris_long_head": "bflh", "biceps_femoris_short_head": "bfsh",
           "semimembranosus": "semimem", "semitendinosus": "semiten", "sartorius": "sart", "gracilis": "grac",
           "tensor_fasciae_latae": "tfl", "adductor_longus": "addlong", "adductor_brevis": "addbrev",
           "iliacus": "iliacus", "psoas": "psoas", "piriformis": "piri", "soleus": "soleus",
           "gastrocnemius_medialis": "gasmed", "gastrocnemius_lateralis": "gaslat", "tibialis_anterior": "tibant",
           "tibialis_posterior": "tibpost", "extensor_digitorum_longus": "edl", "extensor_hallucis_longus": "ehl",
           "flexor_digitorum_longus": "fdl", "flexor_hallucis_longus": "fhl", "peroneus_longus": "perlong",
           "peroneus_brevis": "perbrev"}
SIGMA_N_PER_CM2 = 60.0              # Rajagopal 2016 specific tension
# Healthy young-adult proton-density fat fraction, 3 T six-echo water-fat MRI, n = 30, ~30 years: quadriceps
# 2.5-2.7 %, gluteal 5.3-5.5 % (Eur Radiol Exp 2020, doi 10.1186/s41747-020-00162-5). No reference was found
# for the other groups; they use the quadriceps value.
HEALTHY_FAT_FRACTION = {**{m: 0.054 for m in GROUPS["gluteus_maximus"] + GROUPS["gluteus_medius"]
                           + GROUPS["gluteus_minimus"]}}
HEALTHY_FAT_FRACTION_DEFAULT = 0.026
REFERENCE = {"mass_kg": 75.337, "height_m": 1.70,
             "source": "Rajagopal et al. 2016 generic subject (model mass; height as reported for the model)"}
METHOD = ("Fmax = σ·V·q/lopt (Rajagopal et al. 2016, σ = 60 N/cm²). V: measured where imaging gives it, else "
          "Handsfield et al. 2014 limb muscle volume 47·m·h + 1285 cm³ with each muscle's share kept. q: measured "
          "fat fraction against healthy young muscle, else 1")
BMI_CAVEAT = 30.0


def limb_muscle_volume_cm3(mass_kg, height_m):
    """Total lower-limb muscle volume of one leg (Handsfield 2014 regression)."""
    return 47.0 * float(mass_kg) * float(height_m) + 1285.0


def caveats(mass_kg, height_m, imaged=0):
    out = []
    if mass_kg and height_m:
        out.append("Muscles without imaging: population regression (young healthy adults), the leg muscle an average "
                   "person of this height and mass has. Age, training and injury are not in it.")
        bmi = mass_kg / height_m ** 2
        if bmi > BMI_CAVEAT and imaged < 2 * len(LEG_MUSCLES):
            out.insert(0, f"BMI {bmi:.1f} > {BMI_CAVEAT:g}: extra body mass is mostly fat, so the regression likely "
                          "overestimates muscle volume and strength.")
    if imaged:
        out.append(f"{imaged} muscles from measured volume and/or fat fraction; muscle geometry (paths, fibre lengths) "
                   "stays the scaled generic model's, so measured size changes force, not shape.")
    out.append("Trunk and arm muscles keep generic capacities.")
    return out


def resolve_name(label):
    """'quadriceps_r' / 'vastus_lateralis_l' / 'vaslat_r' -> (side suffix, model base names)."""
    if len(label) < 3 or label[-2:] not in ("_r", "_l"):
        raise ValueError(f"imaging label {label!r} must end in _r or _l (side)")
    name, side = label[:-2], label[-2:]
    base = GROUPS.get(name) or ((ALIASES.get(name, name),) if ALIASES.get(name, name) in LEG_MUSCLES else None)
    if not base:
        raise ValueError(f"imaging label {label!r}: unknown muscle or group; known groups {sorted(GROUPS)}, muscles "
                         f"{sorted(ALIASES)} or model names {list(LEG_MUSCLES[:3])}...")
    return side, base


def check_imaging(imaging):
    """{model muscle: (label, entry)} for an imaging record's 'muscles'; refuses overlaps and bad values."""
    owner = {}
    for label, e in (imaging or {}).get("muscles", {}).items():
        side, base = resolve_name(label)
        v, ff = e.get("volume_cm3"), e.get("fat_fraction")
        if v is None and ff is None:
            raise ValueError(f"imaging {label}: needs volume_cm3 and/or fat_fraction")
        if v is not None and not v > 0:
            raise ValueError(f"imaging {label}: volume_cm3 must be positive, got {v}")
        if ff is not None and not 0 <= ff < 1:
            raise ValueError(f"imaging {label}: fat_fraction is a fraction in [0, 1) (e.g. 0.08 for 8 %), got {ff}")
        for b in base:
            if b + side in owner:
                raise ValueError(f"imaging {label} and {owner[b + side][0]} both cover {b + side}")
            owner[b + side] = (label, e)
    return owner


def scale_model(model_path, generic_model_path, mass_kg, height_m, out_path, imaging=None):
    """Write a copy of a scaled session model with leg Fmax for this person; returns the record.

    ``imaging``: a person model's muscle imaging record ({"muscles": {label: {"volume_cm3", "fat_fraction"}}}).
    Muscles it does not cover use the regression, which needs ``mass_kg`` and ``height_m``; without them they keep
    generic volumes. Refuses a model whose leg Fmax already differs from the generic model's (scaled before, or
    another model), so capacity is never scaled twice.
    """
    from .opensim_stage import _osim
    owner = check_imaging(imaging)
    regression = bool(mass_kg and mass_kg > 0 and height_m and height_m > 0)
    if not regression and not owner:
        raise ValueError(f"capacity scaling needs a body mass and height, got {mass_kg} kg, {height_m} m")
    osim = _osim()
    generic = osim.Model(str(generic_model_path))
    model = osim.Model(str(model_path))
    gm, ms = generic.getMuscles(), model.updMuscles()
    v_ratio = (limb_muscle_volume_cm3(mass_kg, height_m) / limb_muscle_volume_cm3(REFERENCE["mass_kg"], REFERENCE["height_m"])
               if regression else 1.0)
    missing = [b + s for b in LEG_MUSCLES for s in ("_r", "_l") if not (ms.contains(b + s) and gm.contains(b + s))]
    if missing:
        raise ValueError(f"{model_path}: not the Rajagopal leg muscles this regression covers (missing {missing[:4]}...)")
    vref = {b + s: gm.get(b + s).getMaxIsometricForce() * gm.get(b + s).getOptimalFiberLength() * 100 / SIGMA_N_PER_CM2
            for b in LEG_MUSCLES for s in ("_r", "_l")}
    factors, sources, used = {}, {}, {}
    for n, v_ref in vref.items():
        g, m = gm.get(n), ms.get(n)
        if abs(m.getMaxIsometricForce() - g.getMaxIsometricForce()) > 1e-6 * g.getMaxIsometricForce():
            raise ValueError(f"{n}: Fmax {m.getMaxIsometricForce():.1f} N differs from the generic "
                             f"{g.getMaxIsometricForce():.1f} N; capacity was already changed in {model_path}")
        label, e = owner.get(n, (None, {}))
        if e.get("volume_cm3") is not None:
            members = [k for k, (lab, _) in owner.items() if lab == label]
            v, src = e["volume_cm3"] * v_ref / sum(vref[k] for k in members), "measured"
        else:
            v, src = v_ref * v_ratio, "regression" if regression else "generic"
        q = 1.0
        if e.get("fat_fraction") is not None:
            base = n[:-2]
            q = (1 - e["fat_fraction"]) / (1 - HEALTHY_FAT_FRACTION.get(base, HEALTHY_FAT_FRACTION_DEFAULT))
            src += " + fat fraction"
        k = v / v_ref * q * g.getOptimalFiberLength() / m.getOptimalFiberLength()
        m.setMaxIsometricForce(g.getMaxIsometricForce() * k)
        factors[n], sources[n] = k, src
        if label:
            used[label] = used.get(label, 0) + 1
    model.finalizeConnections()
    model.printToXML(str(out_path))
    ks = sorted(factors.values())
    total = lambda mdl, side: sum(mdl.getMuscles().get(b + side).getMaxIsometricForce() for b in LEG_MUSCLES)
    imaged = sum(1 for s in sources.values() if s != ("regression" if regression else "generic"))
    rec = {"method": METHOD, "reference": REFERENCE, "volume_ratio": round(v_ratio, 4), "muscles_scaled": len(factors),
           "factor_min": round(ks[0], 3), "factor_median": round(ks[len(ks) // 2], 3), "factor_max": round(ks[-1], 3),
           "leg_fmax_N": {side: {"generic": round(total(generic, s)), "scaled": round(total(model, s))}
                          for side, s in (("right", "_r"), ("left", "_l"))},
           "sources": {k: sum(1 for s in sources.values() if s == k) for k in sorted(set(sources.values()))},
           "imaging_labels_used": used, "factors": {n: round(k, 4) for n, k in sorted(factors.items())},
           "caveats": caveats(mass_kg if regression else None, height_m if regression else None, imaged)}
    if regression:
        rec["subject"] = {"mass_kg": round(mass_kg, 2), "height_m": round(height_m, 3),
                          "bmi": round(mass_kg / height_m ** 2, 1)}
    if imaging:
        rec["imaging"] = {k: imaging[k] for k in ("method", "date", "approved_by", "sha256") if imaging.get(k)}
    return rec
