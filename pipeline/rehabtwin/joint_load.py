"""Knee joint load on the muscle stage, and what-if scenarios compared within one person.

docs/design-joint-load-stress-model.md, knee-first slice. After static optimisation (rehabtwin/muscles.py),
OpenSim's Joint Reaction analysis gives the force the femur exerts on the tibia, with every muscle force,
the estimated ground forces, gravity and the segments' inertia: the total tibiofemoral force. The quadriceps
reach the tibia through the last segment of their paths (patella to tibial tuberosity), so the patellar tendon's
pull is in it. Its axial component (along the tibia) is the compression reported here.

What it is not: no ligaments, no cartilage contact model, no medial/lateral split (that needs contact points
from imaging, Lerner et al. 2015). Ground forces are estimated, so every number travels with the band from the
ground-force split. Absolute values are not validated for anyone here; **changes within the same person**, on
the same replayed motion, are the output.

Scenarios (each a variant of the muscle study, compared with the measured baseline):

- **Fat change** (``fat_change_model``): the person's DXA regional fat with ``fat_kg`` added or removed, each
  region in proportion to its fat (an assumption: where a person loses fat first varies). Each region's bodies
  lose that many kg; inertia scales with mass. Replaying the same motion with less mass gives a
  roughly proportional change. Published cohort evidence of a larger change in walking (Messier et al. 2005,
  ``MESSIER``) is quoted beside it, never as model output.
- **Strength** (the muscle study's group factors): reported as effort (fraction of capacity), with the load
  change shown as it comes out: stronger muscles can raise compression while easing effort.
- **Combined**: both.
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np

from .io_formats import read_table

MESSIER = ("Published evidence, not model output: in 142 overweight and obese older adults with knee osteoarthritis, "
           "each 9.8 N (1 kg) of weight lost went with 40.6 N less knee compressive force per step in walking, about "
           "4:1 (Messier et al. 2005, Arthritis & Rheumatism 52:2026-2032). Their gait adapted as they lost weight; "
           "this model replays the same motion, so it cannot show that adaptation (that needs predictive simulation).")
STRENGTH_READING = ("Stronger muscles change effort (fraction of capacity used) more than load: compression can "
                    "stay the same or rise while effort falls. Load distribution (medial/lateral) and stability are "
                    "not modelled in this slice.")
LABELS = {
    "output": "Within-person changes on the same replayed motion. Model estimates for clinician discussion, never a "
              "weight-loss or exercise prescription, and no claim about disease progression.",
    "absolute_values": "Absolute knee forces are not validated for this person (no instrumented implant or contact "
                       "model): read them as the baseline the changes are taken from.",
    "contact": "Total tibiofemoral force from OpenSim's Joint Reaction analysis: no ligaments, no cartilage contact "
               "model, no medial/lateral split.",
    "patellofemoral": "Patellofemoral force: the force holding the patella to the femur in a model whose patella "
                      "moves with the knee angle; unvalidated.",
    "patellar_mechanism": "The quadriceps path runs over the patella to the tibia, so the patellar tendon carries the "
                          "full quadriceps tension; in cadaver knees it carries about 0.7 of it at 90 deg of flexion "
                          "(Huberti et al. 1984). Deep-flexion compression from the quadriceps is likely overestimated.",
    "quadriceps_moment_arm": "The model's quadriceps moment arm falls from about 4.5 cm near extension to about 2.1 cm "
                             "at 90 deg (gastrocnemius keeps 3.3 cm): the generic model's geometry, not the person's. "
                             "The quadriceps force for a knee moment scales with 1 / moment arm.",
    "reportable": "A knee's numbers are reportable only when, at its peak, the estimated ground forces fit the motion "
                  "(the muscle stage's pelvis-residual rule), no knee-crossing muscle is at its capacity, and reserve "
                  "torque carries at most 10% of the knee moment: otherwise the muscle forces are inflated or rest "
                  "on forces that don't fit, and a change is not stated even within the person. The impulse (the "
                  "whole rep) needs the same over every frame of the rep, not only at the peak.",
}
MIN_ROBUST_PCT = 2.0         # a load change smaller than this (% of baseline peak) is not reported as an effect
FAT_LIMIT = 0.5              # a scenario may change total fat by at most half of it
SERIES_FPS = 30.0
# Plausibility, not validation: Bergmann et al. 2014 (PLoS One 9:e86035), 8 subjects with instrumented knee
# implants, standardised 'High 100' loads (the highest average loads expected in a 100 kg patient): peak resultant
# 3,372-4,218 N in daily activities other than jogging, knee bends included.
IN_VIVO_HIGH_BW = 4218.0 / (100.0 * 9.81)
IN_VIVO_BAND = ("Instrumented knee implants (Bergmann et al. 2014, 8 subjects, 'High 100' standard loads): peak "
                "resultant 3.4-4.3 BW in daily activities other than jogging, knee bends included. They are implant "
                "patients, so this is a plausibility band, not a limit for other knees.")
SATURATED = 0.98             # activation at which a muscle is at its capacity
RESERVE_SHARE_LIMIT = 0.10   # reserve torque beyond this share of the knee moment: the muscles could not carry it
DISTAL = ("tibia", "talus", "calcn", "toes")       # bodies below the knee


def knee_joints(model):
    """{side: {"tibiofemoral": joint name, "patellofemoral": joint name or None}}: joints whose child is
    tibia_<side> / patella_<side>."""
    js = model.getJointSet()
    child = {js.get(i).getChildFrame().findBaseFrame().getName(): js.get(i).getName() for i in range(js.getSize())}
    out = {}
    for s in ("r", "l"):
        if f"tibia_{s}" in child:
            out[s] = {"tibiofemoral": child[f"tibia_{s}"], "patellofemoral": child.get(f"patella_{s}")}
    if not out:
        raise ValueError("the model has no joint with a tibia_r/tibia_l child body")
    return out


def reaction_setup_xml(t0, t1, joint_names, forces_file="so_StaticOptimization_force.sto"):
    """AnalyzeTool setup for Joint Reaction in a muscle run's folder (muscles.run's files): reactions on the child
    body, expressed in the child's frame."""
    return f"""<?xml version="1.0" encoding="UTF-8" ?>
<OpenSimDocument Version="40500"><AnalyzeTool name="jr">
<model_file>model_dynamics.osim</model_file><replace_force_set>false</replace_force_set>
<force_set_files>reserves.xml</force_set_files><results_directory>.</results_directory>
<output_precision>8</output_precision><initial_time>{t0}</initial_time><final_time>{t1}</final_time>
<solve_for_equilibrium_for_auxiliary_states>false</solve_for_equilibrium_for_auxiliary_states>
<AnalysisSet name="Analyses"><objects><JointReaction name="JointReaction"><on>true</on>
<start_time>{t0}</start_time><end_time>{t1}</end_time><step_interval>1</step_interval><in_degrees>true</in_degrees>
<forces_file>{forces_file}</forces_file><joint_names> {' '.join(joint_names)}</joint_names>
<apply_on_bodies> child</apply_on_bodies><express_in_frame> child</express_in_frame>
</JointReaction></objects><groups/></AnalysisSet>
<ControllerSet name="Controllers"><objects/><groups/></ControllerSet>
<external_loads_file>external_loads.xml</external_loads_file><coordinates_file>motion.mot</coordinates_file>
<lowpass_cutoff_frequency_for_coordinates>6</lowpass_cutoff_frequency_for_coordinates>
</AnalyzeTool></OpenSimDocument>
"""


def reaction_force(table, joint, body):
    """(T, 3) force on ``body`` at ``joint``, in ``body``'s frame, from a ReactionLoads table."""
    return np.column_stack([table.col(f"{joint}_on_{body}_in_{body}_f{a}") for a in "xyz"])


def knee_loads(run_dir, joints, body_mass_kg, motion):
    """Knee loads of one muscle run from its Joint Reaction output: per side the tibiofemoral compression (along
    the tibia: -y in the tibia frame), resultant and shear, and the patellofemoral resultant. N and x body weight
    of this run's model."""
    jr = read_table(Path(run_dir) / "jr_JointReaction_ReactionLoads.sto")
    weight = body_mass_kg * 9.81
    t = jr.time
    step = max(1, round((1.0 / float(np.median(np.diff(t)))) / SERIES_FPS)) if len(t) > 1 else 1
    out = {"body_weight_N": round(weight, 1), "series": {"t": [round(float(x), 3) for x in t[::step]]}}
    for s, j in joints.items():
        F = reaction_force(jr, j["tibiofemoral"], f"tibia_{s}")
        comp = -F[:, 1]
        i = int(np.argmax(comp))
        knee = np.interp(t, motion.time, motion.col(f"knee_angle_{s}")) if motion.has(f"knee_angle_{s}") else None
        side = {"peak_compression_N": round(float(comp[i]), 1), "peak_compression_bw": round(float(comp[i] / weight), 3),
                "time_of_peak_s": round(float(t[i]), 3),
                "knee_flexion_at_peak_deg": round(float(knee[i]), 1) if knee is not None else None,
                "mean_compression_N": round(float(comp.mean()), 1),
                "impulse_Ns": round(float(np.sum((comp[1:] + comp[:-1]) / 2 * np.diff(t))), 1),
                "peak_resultant_N": round(float(np.linalg.norm(F, axis=1).max()), 1),
                "peak_shear_ap_N": round(float(np.abs(F[:, 0]).max()), 1),
                "peak_shear_ml_N": round(float(np.abs(F[:, 2]).max()), 1)}
        if j.get("patellofemoral"):
            P = reaction_force(jr, j["patellofemoral"], f"patella_{s}")
            side["patellofemoral_peak_N"] = round(float(np.linalg.norm(P, axis=1).max()), 1)
        out[s] = side
        out["series"][s] = [round(float(x), 1) for x in comp[::step]]          # N, so scenarios compare directly
    return out


def _crosses_knee(path_bodies, side):
    distal = {f"{b}_{side}" for b in DISTAL}
    return bool(path_bodies & distal) and bool(path_bodies - distal - {f"patella_{side}"})


def _knee_group(name):
    from .muscles import GROUPS
    stem = name.rsplit("_", 1)[0]
    if re.match(r"^gas(lat|med)$", stem):
        return "gastrocnemius"
    return next((g for g, pat in GROUPS.items() if re.match(pat, stem)), "other knee-crossing muscles")


def diagnostics(run_dir, joints, loads, motion):
    """How far each knee's peak can be trusted (muscles.run's folder after Joint Reaction): knee-crossing muscles at
    their capacity and the knee reserve torque's share of the knee moment (beyond ``RESERVE_SHARE_LIMIT`` the
    muscles could not carry it, and static optimisation inflates their forces), what makes up the compression at
    the peak (each muscle group's pull on the shank and foot along the tibia, the ground force less the shank and
    foot weight, and the rest: inertia, reserves), and the peak against the in-vivo band. ``motion``: the run's
    motion in degrees."""
    from .muscles import CONSISTENCY_COP_SHIFT_M, CONSISTENCY_FORCE_BW, _set_state
    from .opensim_stage import _osim
    osim = _osim()
    run_dir = Path(run_dir)
    model = osim.Model(str(run_dir / "model_dynamics.osim"))
    state = model.initSystem()
    force, act = read_table(run_dir / "so_StaticOptimization_force.sto"), read_table(run_dir / "so_StaticOptimization_activation.sto")
    idt, grf = read_table(run_dir / "inverse_dynamics.sto"), read_table(run_dir / "grf.mot")
    cs, bodies = model.getCoordinateSet(), model.getBodySet()
    cols = [c for c in motion.columns if cs.contains(c)]
    muscles = model.getMuscles()
    paths = {}
    for i in range(muscles.getSize()):
        mu = muscles.get(i)
        p = osim.GeometryPath.safeDownCast(mu.getPath())
        if p is not None:
            pts = p.getPathPointSet()
            paths[mu.getName()] = (p, {pts.get(k).getParentFrame().findBaseFrame().getName() for k in range(pts.getSize())})
    weight = loads["body_weight_N"]
    out = {}
    for s in joints:
        t_pk = loads[s]["time_of_peak_s"]
        k = int(np.argmin(np.abs(force.time - t_pk)))
        knee = [n for n, (_, b) in paths.items() if n.endswith(f"_{s}") and _crosses_knee(b, s)]
        saturated = sorted(n for n in knee if act.has(n) and act.col(n)[k] >= SATURATED)
        window = np.column_stack([act.col(n) for n in knee if act.has(n)] or [np.zeros_like(act.time)])
        moment = np.interp(force.time, idt.time, idt.col(f"knee_angle_{s}_moment"))
        reserve = force.col(f"reserve_knee_angle_{s}") if force.has(f"reserve_knee_angle_{s}") else np.zeros_like(moment)
        big = np.abs(moment) >= 0.1 * np.abs(moment).max()
        share = np.abs(reserve) / np.maximum(np.abs(moment), 1e-9)
        _set_state(model, state, motion, int(np.argmin(np.abs(motion.time - t_pk))), cs, cols)
        model.realizeVelocity(state)
        R = bodies.get(f"tibia_{s}").getTransformInGround(state).R()
        y = np.array([R.get(i, 1) for i in range(3)])          # the tibia's long axis in ground
        distal = {f"{b}_{s}" for b in DISTAL}
        by_group = {}
        for n in knee:
            pfds = osim.ArrayPointForceDirection()
            paths[n][0].getPointForceDirections(state, pfds)
            pull = np.zeros(3)
            for j in range(pfds.getSize()):
                d = pfds.get(j)
                if d.frame().findBaseFrame().getName() in distal:
                    pull += d.scale() * np.array([d.direction().get(a) for a in range(3)])
            g = _knee_group(n)
            by_group[g] = by_group.get(g, 0.0) + float(force.col(n)[k] * pull @ y)
        quads = [n for n in knee if _knee_group(n) == "quadriceps" and force.col(n)[k] > 1.0]
        arm = (sum(force.col(n)[k] * abs(muscles.get(n).computeMomentArm(state, cs.get(f"knee_angle_{s}"))) for n in quads)
               / sum(force.col(n)[k] for n in quads)) if quads else None
        ground = np.array([np.interp(force.time[k], grf.time, grf.col(f"ground_force_{s}_v{a}")) for a in "xyz"])
        distal_weight = 9.81 * sum(bodies.get(b).getMass() for b in distal if bodies.contains(b))
        external = float((ground - [0.0, distal_weight, 0.0]) @ y)
        total = loads[s]["peak_compression_N"]
        muscle_total = sum(by_group.values())
        ki = int(np.argmin(np.abs(idt.time - t_pk)))
        cop_shift = max((abs(idt.col(c)[ki]) for c in idt.columns if c.startswith("pelvis_") and c.endswith("_moment")),
                        default=0.0) / weight
        residual_force = max((abs(idt.col(c)[ki]) for c in idt.columns if c.startswith("pelvis_") and c.endswith("_force")),
                             default=0.0) / weight
        why = []
        if cop_shift > CONSISTENCY_COP_SHIFT_M or residual_force > CONSISTENCY_FORCE_BW:
            why.append(f"the estimated ground forces don't fit the motion at the peak (pelvis residual as a "
                       f"{cop_shift * 100:.0f} cm centre-of-pressure shift, {residual_force:.2f} BW)")
        if saturated:
            why.append(f"{len(saturated)} knee-crossing muscle(s) at capacity at the peak ({', '.join(saturated)})")
        if share[k] > RESERVE_SHARE_LIMIT and big[k]:
            why.append(f"reserve torque carries {share[k]:.0%} of the knee moment at the peak")
        resultant_bw = loads[s]["peak_resultant_N"] / weight
        out[s] = {"saturated_knee_muscles_at_peak": saturated,
                  "frames_with_a_saturated_knee_muscle": round(float(np.mean(window.max(axis=1) >= SATURATED)), 3),
                  "knee_reserve_share_at_peak": round(float(share[k]), 3),
                  "knee_reserve_share_max": round(float(share[big].max()) if big.any() else 0.0, 3),
                  "compression_at_peak_N": {**{g: round(v, 1) for g, v in sorted(by_group.items(), key=lambda x: -x[1])},
                                            "ground force less shank and foot weight": round(external, 1),
                                            "rest (inertia, reserves, constraints)": round(total - muscle_total - external, 1)},
                  "gastrocnemius_share_of_muscle_compression": round(by_group.get("gastrocnemius", 0.0) / muscle_total, 3)
                  if muscle_total > 0 else None,
                  "quadriceps_moment_arm_cm_at_peak": round(100 * arm, 2) if arm is not None else None,
                  "knee_moment_Nm_at_peak": round(float(moment[k]), 1),
                  "ground_forces_fit_at_peak": {"pelvis_residual_as_cop_shift_m": round(cop_shift, 3),
                                                "pelvis_force_residual_bw": round(residual_force, 3)},
                  "peak_resultant_bw": round(resultant_bw, 2),
                  "above_in_vivo_band": bool(resultant_bw > IN_VIVO_HIGH_BW),
                  "reportable": not why, "why_not_reportable": why}
        # the impulse integrates the whole rep, so it needs the whole rep to hold, not just the peak frame
        pelvis = [c for c in idt.columns if c.startswith("pelvis_")]
        rep_cop = np.max([np.abs(idt.col(c)) for c in pelvis if c.endswith("_moment")], axis=0) / weight
        rep_force = max((float(np.abs(idt.col(c)).max()) for c in pelvis if c.endswith("_force")), default=0.0) / weight
        why_impulse = []
        if rep_cop.max() > CONSISTENCY_COP_SHIFT_M or rep_force > CONSISTENCY_FORCE_BW:
            why_impulse.append(f"the estimated ground forces don't fit the motion everywhere in the rep (worst pelvis "
                               f"residual as a {rep_cop.max() * 100:.0f} cm centre-of-pressure shift at "
                               f"{idt.time[int(rep_cop.argmax())]:.2f} s)")
        if out[s]["frames_with_a_saturated_knee_muscle"] > 0:
            why_impulse.append(f"a knee-crossing muscle is at capacity in "
                               f"{out[s]['frames_with_a_saturated_knee_muscle']:.0%} of the frames")
        if out[s]["knee_reserve_share_max"] > RESERVE_SHARE_LIMIT:
            why_impulse.append(f"reserve torque carries up to {out[s]['knee_reserve_share_max']:.0%} of the knee moment")
        out[s].update({"impulse_reportable": not why_impulse, "why_impulse_not_reportable": why_impulse})
    return out


# ---------------------------------------------------------------- fat-change scenario

def fat_change_regions(record, fat_kg):
    """{region: kg of fat added (+) or removed (-)}: ``fat_kg`` spread over the DXA regions in proportion to each
    region's fat. Refuses a record without every region's fat, and a change beyond ``FAT_LIMIT`` of the total."""
    from . import dxa
    if not dxa.check(record)["distribution"]:
        raise ValueError("a fat-change scenario needs the person's regional fat: a whole-body DXA table with lean, fat "
                         "and BMC of arms, legs, trunk and head (rehabtwin person dxa)")
    fat = {r: float(record["regions"][r]["fat_kg"]) for r in dxa.REGIONS}
    total = sum(fat.values())
    if not fat_kg or abs(fat_kg) > FAT_LIMIT * total:
        raise ValueError(f"fat change {fat_kg:+g} kg: give a change up to {FAT_LIMIT:.0%} of the scanned fat "
                         f"({FAT_LIMIT * total:.1f} kg)")
    return {r: fat_kg * f / total for r, f in fat.items()}


def fat_change_model(model_path, record, fat_kg, out_path):
    """Copy of ``model_path`` with ``fat_kg`` of fat added or removed (``fat_change_regions``): each DXA region's
    bodies scaled so the region gains or loses that many kg (inertia scales with mass; segment shape and centre of
    mass stay), so the model's mass changes by ``fat_kg``. Returns the record of what changed."""
    from . import dxa
    from .opensim_stage import _osim
    change = fat_change_regions(record, fat_kg)
    osim = _osim()
    model = osim.Model(str(model_path))
    bodies = model.updBodySet()
    names = {bodies.get(i).getName() for i in range(bodies.getSize())}
    regions = {r: [b for b in bs if b in names] for r, bs in dxa.BODIES.items()}
    if not regions["head"]:                       # Rajagopal 2016: the torso body carries the head
        regions.pop("head")
        change["trunk"] += change.pop("head")
    before = sum(bodies.get(i).getMass() for i in range(bodies.getSize()))
    applied = {}
    for r, bs in regions.items():
        mass = sum(bodies.get(b).getMass() for b in bs)
        if mass + change[r] <= 0.5 * mass:
            raise ValueError(f"fat change {fat_kg:+g} kg would take {r} below half its model mass")
        factor = (mass + change[r]) / mass
        for b in bs:
            if bodies.get(b).getMass() > 0:
                bodies.get(b).scaleMass(factor)
        applied[r] = {"fat_change_kg": round(change[r], 3), "mass_factor": round(factor, 4), "bodies": bs}
    model.finalizeConnections()
    model.initSystem()
    after = sum(bodies.get(i).getMass() for i in range(bodies.getSize()))
    model.printToXML(str(out_path))
    return {"fat_change_kg": fat_kg, "method": "DXA regional fat changed in proportion to each region's fat "
                                               "(assumption); each region's bodies lose or gain that many kg",
            "dxa": {k: record[k] for k in ("method", "date", "approved_by") if record.get(k)},
            "model_mass_kg": {"before": round(before, 2), "after": round(after, 2)}, "regions": applied}


# ---------------------------------------------------------------- the comparison

def _change(base, other):
    if base is None or other is None:
        return None
    return {"base_N": base, "scenario_N": other, "change_N": round(other - base, 1),
            "change_pct": round(100 * (other - base) / base, 2) if base else None}


def compare(base, other):
    """Per side: change in peak and impulse of tibiofemoral compression, and in patellofemoral peak (N, %)."""
    out = {}
    for s in ("r", "l"):
        b, o = base.get(s), other.get(s)
        if not (b and o):
            continue
        out[s] = {"peak": _change(b["peak_compression_N"], o["peak_compression_N"]),
                  "impulse_pct": round(100 * (o["impulse_Ns"] / b["impulse_Ns"] - 1), 2) if b["impulse_Ns"] else None,
                  "patellofemoral_peak": _change(b.get("patellofemoral_peak_N"), o.get("patellofemoral_peak_N"))}
    return out


def robust(changes_pct, min_pct=MIN_ROBUST_PCT):
    """A change keeps its sign and is at least ``min_pct`` under every ground-force split it was recomputed with."""
    c = [x for x in changes_pct if x is not None]
    return bool(c) and (all(x >= min_pct for x in c) or all(x <= -min_pct for x in c))


EFFORT_GROUPS = ("quadriceps", "hamstrings", "triceps_surae", "gluteus_maximus")


def scenario_reading(kind, cmp, effort, mass_change=None):
    """One plain sentence per scenario, built from the numbers (never a recommendation)."""
    side = {"r": "right", "l": "left"}
    load = "; ".join([f"{side[s]} knee peak compression {v['peak']['change_pct']:+.1f}%"
                      + (" (baseline above the in-vivo band: model-limited)" if v.get("above_in_vivo_band") else "")
                      for s, v in cmp.items() if v["peak"] and v["peak"]["change_pct"] is not None
                      and v.get("reportable", True)]
                     + [f"{side[s]} knee not reportable ({v['why_not_reportable'][0]})"
                        for s, v in cmp.items() if not v.get("reportable", True)])
    eff = ", ".join(f"{g} {v['base'] * 100:.0f}% → {v['other'] * 100:.0f}% of capacity" for g, v in effort.items())
    held = [side[s] for s, v in cmp.items() if not v.get("reportable", True)]
    if held:
        eff = (eff + "; " if eff else "") + f"{' and '.join(held)}-side effort not reportable either"
    stated = any(v.get("reportable", True) for v in cmp.values())
    if kind == "fat":
        return (f"Model-computed on the replayed motion: body mass {mass_change['pct']:+.1f}% "
                f"({mass_change['kg']:+.1f} kg), {load}."
                + (" About proportional: the same motion with less mass." if stated else ""))
    if kind == "strength":
        return f"Effort: {eff or 'no group changed'}. Load as computed: {load}. {STRENGTH_READING}"
    if kind == "combined":
        return (f"Body mass {mass_change['pct']:+.1f}% and stronger muscles: {load}; effort: {eff or 'unchanged'}. "
                f"{STRENGTH_READING}")
    return f"{load}; effort: {eff or 'unchanged'}."


def summarise(runs, kinds, comparisons, shifted=None, mass=None, safety_holds=None, fat=None, grf_bias=None):
    """The study's joint-load block. ``runs``: {label: muscles.run summary with knee_load}; ``kinds``: {label:
    "fat" | "strength" | "combined" | other}; ``comparisons``: the muscle study's per-group activation changes;
    ``shifted``: {bias: {label: summary}} from the ground-force split runs; ``mass``: {label: body mass kg}."""
    base = runs["measured"]["knee_load"]
    diag = {lab: r["knee_load"].get("diagnostics") or {} for lab, r in runs.items()}
    out = {"baseline": {s: base[s] for s in ("r", "l") if s in base}, "body_weight_N": base["body_weight_N"],
           "baseline_diagnostics": diag["measured"],
           "series": {lab: r["knee_load"]["series"] for lab, r in runs.items()},
           "labels": {**LABELS, "in_vivo_band": IN_VIVO_BAND}, "scenarios": {}}
    if shifted:
        out["labels"]["ground_forces"] = (f"Estimated, not measured; bands re-run every scenario with the right foot's "
                                          f"share of the load shifted by ±{grf_bias:.2f}.")
        out["baseline_band_over_grf_split"] = {
            s: [min(r["measured"]["knee_load"][s]["peak_compression_N"] for r in [runs, *shifted.values()]),
                max(r["measured"]["knee_load"][s]["peak_compression_N"] for r in [runs, *shifted.values()])]
            for s in out["baseline"]}
    else:
        out["labels"]["ground_forces"] = "Estimated, not measured; no ground-force split band computed for this run."
    if fat:
        method = fat["dxa"].get("method", "DXA")
        source = (f"ILLUSTRATIVE regional fat, not measured on this person ({method} {fat['dxa'].get('date', '')})"
                  if "illustrative" in method.lower() else f"Regional fat measured by {method} {fat['dxa'].get('date', '')}")
        out["labels"]["fat_provenance"] = f"{source}; the change is spread in proportion to each region's fat (an assumption)."
        out["fat_model"] = fat
    if safety_holds:
        out["labels"]["safety"] = "; ".join(f"{j}: {r}" for j, r in safety_holds.items())
    for lab, r in runs.items():
        if lab == "measured":
            continue
        kind = kinds.get(lab, "other")
        cmp = compare(base, r["knee_load"])
        for s, v in cmp.items():
            why = ([f"baseline: {w}" for w in diag["measured"].get(s, {}).get("why_not_reportable", [])]
                   + [f"scenario: {w}" for w in diag[lab].get(s, {}).get("why_not_reportable", [])])
            v["reportable"] = not why
            if why:
                v["why_not_reportable"] = why
            v["above_in_vivo_band"] = bool(diag["measured"].get(s, {}).get("above_in_vivo_band"))
            why_i = ([f"baseline: {w}" for w in diag["measured"].get(s, {}).get("why_impulse_not_reportable", [])]
                     + [f"scenario: {w}" for w in diag[lab].get(s, {}).get("why_impulse_not_reportable", [])])
            if why_i:                     # the change in impulse is not stated: the rep doesn't hold throughout
                v["impulse_pct"] = None
                v["why_impulse_not_reportable"] = why_i
            if shifted and v["peak"]:
                alt = [compare(sh["measured"]["knee_load"], sh[lab]["knee_load"]).get(s, {}).get("peak")
                       for sh in shifted.values() if lab in sh]
                pcts = [v["peak"]["change_pct"]] + [a["change_pct"] for a in alt if a]
                v["peak"]["change_pct_range_over_grf_split"] = [min(pcts), max(pcts)]
                v["peak"]["robust_to_grf_split"] = robust(pcts)
        # effort comes from the same muscle solution: not stated on a side whose knee is not reportable
        effort = {g: c for g, c in (comparisons.get(lab) or {}).items()
                  if g.rsplit("_", 1)[0] in EFFORT_GROUPS and abs(c["change"]) >= 0.01
                  and cmp.get(g.rsplit("_", 1)[1], {}).get("reportable", True)}
        item = {"kind": kind, "knee": cmp, "effort": effort}
        if mass and lab in mass:
            dm = mass[lab] - mass["measured"]
            item["mass_change"] = {"kg": round(dm, 2), "pct": round(100 * dm / mass["measured"], 2)}
        item["reading"] = scenario_reading(kind, cmp, effort, item.get("mass_change"))
        if kind in ("fat", "combined"):
            item["published_evidence"] = MESSIER
        out["scenarios"][lab] = item
    return out
