"""Leg muscle capacity scaled to the person's body size (Handsfield et al. 2014, as used by Rajagopal et al. 2016).

OpenSim's ScaleTool lengthens fibres and tendons with the bones but leaves every muscle's maximum isometric
force (Fmax) at the generic subject's value, so a 50 kg and a 110 kg person get the same leg strength. Fmax is
specific tension × physiological cross-section, and the cross-section is volume / optimal fibre length:

    Fmax_person = Fmax_generic × (V_person / V_generic) × (lopt_generic / lopt_person)

Handsfield 2014 measured 35 lower-limb muscles by MRI in 24 young healthy adults. Total limb muscle volume
followed height × mass, V ≈ 47 · m · h + 1285 (cm³; kg, m), and each muscle kept a near-constant share of it.
Rajagopal 2016 built the generic leg muscles from this regression for a 75.337 kg, 1.70 m subject. The
Pose2Sim model's 80 leg muscles are Rajagopal's, so the same reference applies to them; its 238 trunk
muscles come from other sources and stay generic.

This is a population estimate: it gives the leg the muscle an average young, healthy adult of this height
and mass has. It is not this person's strength. Fat mass raises body mass without muscle (BMI > 30), and
age, training and injury change muscle volume; dynamometry (``rehabtwin strength``) measures the tested
groups, and the regression only replaces generic values for the rest.
"""
from __future__ import annotations

# Rajagopal 2016 lower-limb muscles (each with _r and _l), the ones Handsfield's regression covers
LEG_MUSCLES = ("addbrev", "addlong", "addmagDist", "addmagIsch", "addmagMid", "addmagProx", "bflh", "bfsh", "edl",
               "ehl", "fdl", "fhl", "gaslat", "gasmed", "glmax1", "glmax2", "glmax3", "glmed1", "glmed2", "glmed3",
               "glmin1", "glmin2", "glmin3", "grac", "iliacus", "perbrev", "perlong", "piri", "psoas", "recfem",
               "sart", "semimem", "semiten", "soleus", "tfl", "tibant", "tibpost", "vasint", "vaslat", "vasmed")
REFERENCE = {"mass_kg": 75.337, "height_m": 1.70,
             "source": "Rajagopal et al. 2016 generic subject (model mass; height as reported for the model)"}
METHOD = ("Handsfield et al. 2014 limb muscle volume 47·m·h + 1285 cm³, per-muscle share kept; "
          "Fmax ∝ volume / optimal fibre length (Rajagopal et al. 2016)")
BMI_CAVEAT = 30.0


def limb_muscle_volume_cm3(mass_kg, height_m):
    """Total lower-limb muscle volume of one leg (Handsfield 2014 regression)."""
    return 47.0 * float(mass_kg) * float(height_m) + 1285.0


def caveats(mass_kg, height_m):
    bmi = mass_kg / height_m ** 2
    out = ["Population regression (young healthy adults): the leg muscle an average person of this height and mass "
           "has, not this person's measured strength. Age, training and injury are not in it.",
           "Trunk and arm muscles keep generic capacities."]
    if bmi > BMI_CAVEAT:
        out.insert(0, f"BMI {bmi:.1f} > {BMI_CAVEAT:g}: extra body mass is mostly fat, so the regression likely "
                      "overestimates muscle volume and strength.")
    return out


def scale_model(model_path, generic_model_path, mass_kg, height_m, out_path):
    """Write a copy of a scaled session model with leg Fmax scaled to the body; returns the record.

    Refuses a model whose leg Fmax already differs from the generic model's (scaled before, or another
    model), so capacity is never scaled twice.
    """
    from .opensim_stage import _osim
    if not (mass_kg and mass_kg > 0 and height_m and height_m > 0):
        raise ValueError(f"capacity scaling needs a body mass and height, got {mass_kg} kg, {height_m} m")
    osim = _osim()
    generic = osim.Model(str(generic_model_path))
    model = osim.Model(str(model_path))
    gm, ms = generic.getMuscles(), model.updMuscles()
    v_ratio = limb_muscle_volume_cm3(mass_kg, height_m) / limb_muscle_volume_cm3(REFERENCE["mass_kg"], REFERENCE["height_m"])
    factors, missing = {}, []
    for base in LEG_MUSCLES:
        for side in ("_r", "_l"):
            n = base + side
            if not (ms.contains(n) and gm.contains(n)):
                missing.append(n)
                continue
            g, m = gm.get(n), ms.get(n)
            if abs(m.getMaxIsometricForce() - g.getMaxIsometricForce()) > 1e-6 * g.getMaxIsometricForce():
                raise ValueError(f"{n}: Fmax {m.getMaxIsometricForce():.1f} N differs from the generic "
                                 f"{g.getMaxIsometricForce():.1f} N; capacity was already changed in {model_path}")
            k = v_ratio * g.getOptimalFiberLength() / m.getOptimalFiberLength()
            m.setMaxIsometricForce(g.getMaxIsometricForce() * k)
            factors[n] = k
    if missing:
        raise ValueError(f"{model_path}: not the Rajagopal leg muscles this regression covers (missing {missing[:4]}...)")
    model.finalizeConnections()
    model.printToXML(str(out_path))
    ks = sorted(factors.values())
    total = lambda mdl, side: sum(mdl.getMuscles().get(b + side).getMaxIsometricForce() for b in LEG_MUSCLES)  # noqa: E731
    return {"method": METHOD, "reference": REFERENCE,
            "subject": {"mass_kg": round(mass_kg, 2), "height_m": round(height_m, 3), "bmi": round(mass_kg / height_m ** 2, 1)},
            "volume_ratio": round(v_ratio, 4), "muscles_scaled": len(factors),
            "factor_min": round(ks[0], 3), "factor_median": round(ks[len(ks) // 2], 3), "factor_max": round(ks[-1], 3),
            "leg_fmax_N": {side: {"generic": round(total(generic, s)), "scaled": round(total(model, s))}
                           for side, s in (("right", "_r"), ("left", "_l"))},
            "factors": {n: round(k, 4) for n, k in sorted(factors.items())},
            "caveats": caveats(mass_kg, height_m)}
