"""Muscle effects of an exercise: estimated ground forces → inverse dynamics → static optimisation.

What it answers (on the session's OpenSim model):
* which muscle groups carry the movement, as a fraction of their capacity;
* how that changes for a corrected version of the movement (correction view);
* "what if" a group is weaker (max isometric force scaled), e.g. how hard the
  remaining gluteal muscles have to work, or whether the movement becomes
  infeasible (reserve actuators take over).

Ground reaction forces are *estimated*, not measured: whole-body Newton
(F = m (a_com + g)) split between two planted feet by where the centre of
mass sits between them, applied under each foot. That is only meaningful for
slow double-stance exercises (squat, heel raise, trunk flexion) — not gait,
jumps, or sit-to-stand with a chair. Every output carries this caveat, the
twin tier, and the residual/reserve evidence of how consistent it was.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np

from .filtering import lowpass
from .io_formats import Table, read_table, write_table
from .opensim_stage import _cwd, _osim

# Muscle groups of the Pose2Sim / Lai-Uhlrich / Rajagopal muscle set (names without _r/_l)
GROUPS = {
    "gluteus_maximus": r"^glmax\d$",
    "gluteus_medius": r"^glmed\d$",
    "gluteus_minimus": r"^glmin\d$",
    "tensor_fasciae_latae": r"^tfl$",
    "iliopsoas": r"^(iliacus|psoas)$",
    "adductors": r"^(addbrev|addlong|addmag\w+|grac)$",
    "quadriceps": r"^(recfem|vasint|vaslat|vasmed)$",
    "hamstrings": r"^(bflh|bfsh|semimem|semiten)$",
    "triceps_surae": r"^(gaslat|gasmed|soleus)$",
    "tibialis_anterior": r"^tibant$",
    "erector_spinae": r"^(IL_|LTp)",
    "multifidus": r"^MF_",
    "quadratus_lumborum": r"^QL_",
    "abdominals": r"^(rect_abd|EO|IO)",
}

VALID_EXERCISES = {"squat", "trunk_flexion", "free_double_stance"}


def muscle_groups(names):
    """{"quadriceps_r": [muscle names], ...} for the muscles present."""
    out = {}
    for n in names:
        m = re.match(r"^(.*)_([rl])$", n)
        if not m:
            continue
        stem, side = m.groups()
        for g, pat in GROUPS.items():
            if re.match(pat, stem):
                out.setdefault(f"{g}_{side}", []).append(n)
    return out


def _set_state(model, state, table, f, cs, cols):
    import opensim as osim
    for c in cols:
        co = cs.get(c)
        v = table.data[f, table.columns.index(c)]
        co.setValue(state, np.radians(v) if co.getMotionType() == osim.Coordinate.Rotational else v, False)
    model.realizePosition(state)


def estimate_grf(model_path, table: Table, cutoff_hz=6.0, max_foot_speed=0.15):
    """Quasi-static double-stance GRF estimate. Returns (columns, data (T, 18), qc dict)."""
    osim = _osim()
    model = osim.Model(str(model_path))
    state = model.initSystem()
    cs = model.getCoordinateSet()
    cols = [c for c in table.columns if cs.contains(c)]
    T = len(table.time)
    com = np.zeros((T, 3))
    feet = {s: np.zeros((T, 3)) for s in "rl"}
    heel = {s: np.zeros((T, 3)) for s in "rl"}
    toe = {s: np.zeros((T, 3)) for s in "rl"}
    lowest = np.inf
    for f in range(T):
        _set_state(model, state, table, f, cs, cols)
        p = model.calcMassCenterPosition(state)
        com[f] = [p.get(0), p.get(1), p.get(2)]
        for s in "rl":
            pts = [model.getBodySet().get(b).getPositionInGround(state) for b in (f"calcn_{s}", f"toes_{s}")]
            pts = np.array([[q.get(0), q.get(1), q.get(2)] for q in pts])
            feet[s][f] = pts.mean(axis=0)
            heel[s][f], toe[s][f] = pts[0], pts[1]
            lowest = min(lowest, pts[:, 1].min())
    mass = model.getTotalMass(state)
    fps = 1.0 / float(np.median(np.diff(table.time)))
    com_f = lowpass(com, fps, cutoff_hz)
    acc = np.gradient(np.gradient(com_f, table.time, axis=0), table.time, axis=0)
    F = mass * (acc + np.array([0.0, 9.81, 0.0]))
    R, L = feet["r"], feet["l"]
    d = R - L
    d[:, 1] = 0.0
    c = com_f - L
    c[:, 1] = 0.0
    share_r = np.clip(np.sum(c * d, axis=1) / np.maximum(np.sum(d * d, axis=1), 1e-9), 0.0, 1.0)
    # Whole-body centre of pressure from moment balance about the COM (segment angular
    # momentum neglected): CoP = COM_h - height * F_h / F_v. Its component across the
    # foot-to-foot line sets the split above; its component along the feet (front/back)
    # shifts each foot's CoP, limited to that foot's heel-toe extent.
    height = com_f[:, 1] - lowest
    cop_total = com_f.copy()
    cop_total[:, [0, 2]] -= height[:, None] * F[:, [0, 2]] / np.maximum(F[:, 1:2], 1.0)
    cop_total[:, 1] = lowest
    data, names = [], []
    for s, share in (("r", share_r), ("l", 1.0 - share_r)):
        centre = (R if s == "r" else L).copy()
        axis = toe[s] - heel[s]
        axis[:, 1] = 0.0
        length = np.linalg.norm(axis, axis=1, keepdims=True)
        axis = axis / np.maximum(length, 1e-9)
        along = np.sum((cop_total - centre) * axis, axis=1, keepdims=True)
        along = np.clip(along, -0.5 * length, 0.5 * length)   # stay under the foot
        cop = centre + along * axis
        cop[:, 1] = lowest
        data += [F * share[:, None], cop, np.zeros((T, 3))]
        names += [f"ground_force_{s}_v{a}" for a in "xyz"] + [f"ground_force_{s}_p{a}" for a in "xyz"] \
            + [f"ground_torque_{s}_{a}" for a in "xyz"]
    foot_speed = max(float(np.max(np.linalg.norm(np.gradient(feet[s], table.time, axis=0), axis=1))) for s in "rl")
    qc = {
        "method": "quasi-static double stance: F = m (a_com + g), split by centre-of-mass position between the feet",
        "body_mass_kg": round(mass, 2),
        "peak_vertical_bw": round(float(F[:, 1].max() / (mass * 9.81)), 3),
        "min_vertical_bw": round(float(F[:, 1].min() / (mass * 9.81)), 3),
        "right_share_range": [round(float(share_r.min()), 3), round(float(share_r.max()), 3)],
        "max_foot_speed_m_s": round(foot_speed, 3),
        "feet_planted": foot_speed <= max_foot_speed,
    }
    return names, np.column_stack(data), qc


def _external_loads_xml(datafile):
    forces = "".join(f"""<ExternalForce name="grf_{s}"><applied_to_body>calcn_{s}</applied_to_body>
<force_expressed_in_body>ground</force_expressed_in_body><point_expressed_in_body>ground</point_expressed_in_body>
<force_identifier>ground_force_{s}_v</force_identifier><point_identifier>ground_force_{s}_p</point_identifier>
<torque_identifier>ground_torque_{s}_</torque_identifier><data_source_name>{datafile}</data_source_name></ExternalForce>"""
                     for s in "rl")
    return f"""<?xml version="1.0" encoding="UTF-8" ?>
<OpenSimDocument Version="40500"><ExternalLoads name="estimated_grf"><objects>{forces}</objects><groups/>
<datafile>{datafile}</datafile></ExternalLoads></OpenSimDocument>
"""


def dynamics_model(model_path, out_path, weaken=None):
    """Copy of the subject model for ID/SO: foot contact forces removed, optional weakened groups.

    ``weaken``: {"gluteus_medius_r": 0.5, ...} scales max isometric force.
    Returns {"weakened": {group: [muscles]}}.
    """
    osim = _osim()
    model = osim.Model(str(model_path))
    fs = model.updForceSet()
    for i in reversed(range(fs.getSize())):
        if "SmoothSphereHalfSpaceForce" in fs.get(i).getConcreteClassName() or "ContactForce" in fs.get(i).getConcreteClassName():
            fs.remove(i)
    applied = {}
    if weaken:
        names = [model.getMuscles().get(i).getName() for i in range(model.getMuscles().getSize())]
        groups = muscle_groups(names)
        for g, factor in weaken.items():
            if g not in groups:
                raise ValueError(f"unknown muscle group {g!r}; known: {sorted(groups)}")
            for n in groups[g]:
                mu = model.updMuscles().get(n)
                mu.setMaxIsometricForce(mu.getMaxIsometricForce() * factor)
            applied[g] = groups[g]
    model.finalizeConnections()
    model.initSystem()
    model.printToXML(str(out_path))
    return {"weakened": {g: {"factor": weaken[g], "muscles": len(m)} for g, m in applied.items()}}


def exo_optimal_force(cap_nm):
    """Optimal force for a 'free' ideal device: big enough that (torque/opt)^2 is negligible."""
    return max(1000.0, 100.0 * cap_nm)


def parse_assist(spec):
    """'knee_angle_r=40' (both directions) or 'knee_angle_r=40:neg' / ':pos' -> (coord, max N·m, lo, hi)."""
    coord, rest = spec.split("=", 1)
    torque, _, direction = rest.partition(":")
    lo, hi = {"": (-1.0, 1.0), "pos": (0.0, 1.0), "neg": (-1.0, 0.0)}[direction]
    return coord, float(torque), lo, hi


def reserves_xml(model_path, path, residual_force=10.0, reserve_force=1.0, ideal_force=200.0, assist=()):
    """Pelvis residuals, weak reserves where muscles act, ideal torque actuators elsewhere (arms, neck).

    ``assist``: ideal assistive devices (Dembia et al. 2017 style) as ``parse_assist`` tuples:
    a torque actuator capped at its max torque that is (practically) free to use up to that cap.
    Static optimisation charges every actuator its squared control, so the device is given a
    very large optimal force with its control bounded to cap / optimal force: its cost becomes
    negligible and the result is the most a device of that size could offload.
    """
    osim = _osim()
    model = osim.Model(str(model_path))
    state = model.initSystem()
    cs = model.getCoordinateSet()
    items = []
    for i in range(cs.getSize()):
        co = cs.get(i)
        if co.isConstrained(state) or co.getLocked(state):
            continue
        n = co.getName()
        if n.startswith("pelvis_"):
            opt = residual_force
        elif n.startswith(("arm_", "elbow_", "pro_sup", "wrist_", "neck_")):
            opt = ideal_force   # no muscles in the model here
        else:
            opt = reserve_force
        items.append(f'<CoordinateActuator name="reserve_{n}"><coordinate>{n}</coordinate>'
                     f"<optimal_force>{opt}</optimal_force><min_control>-Inf</min_control><max_control>Inf</max_control>"
                     "</CoordinateActuator>")
    for coord, torque, lo, hi in assist:
        if not cs.contains(coord):
            raise ValueError(f"assist: no coordinate {coord!r} in the model")
        opt = exo_optimal_force(torque)
        items.append(f'<CoordinateActuator name="exo_{coord}"><coordinate>{coord}</coordinate>'
                     f"<optimal_force>{opt}</optimal_force><min_control>{lo * torque / opt}</min_control>"
                     f"<max_control>{hi * torque / opt}</max_control></CoordinateActuator>")
    Path(path).write_text('<?xml version="1.0" encoding="UTF-8" ?>\n<OpenSimDocument Version="40500">'
                          f'<ForceSet name="reserves"><objects>{"".join(items)}</objects><groups/></ForceSet></OpenSimDocument>\n')


def run(model_path, motion_path, out_dir, weaken=None, label="measured", exercise="squat", start=None, stop=None,
        assist=()):
    """GRF estimate → ID → SO for one motion. Returns a summary dict (also written to muscles.json)."""
    osim = _osim()
    out = Path(out_dir) / label
    out.mkdir(parents=True, exist_ok=True)
    tab = read_table(motion_path)
    t0 = tab.time[0] if start is None else start
    t1 = tab.time[-1] if stop is None else stop
    write_table(out / "motion.mot", tab.columns, tab.data, tab.time, tab.in_degrees, name="motion")
    names, grf, grf_qc = estimate_grf(model_path, tab)
    write_table(out / "grf.mot", names, grf, tab.time, in_degrees=False, name="estimated_grf")
    (out / "external_loads.xml").write_text(_external_loads_xml("grf.mot"))
    model_info = dynamics_model(model_path, out / "model_dynamics.osim", weaken)
    assist = [parse_assist(a) if isinstance(a, str) else a for a in assist]
    reserves_xml(out / "model_dynamics.osim", out / "reserves.xml", assist=assist)

    (out / "id_setup.xml").write_text(f"""<?xml version="1.0" encoding="UTF-8" ?>
<OpenSimDocument Version="40500"><InverseDynamicsTool name="id">
<results_directory>.</results_directory><model_file>model_dynamics.osim</model_file>
<time_range> {t0} {t1}</time_range><forces_to_exclude> Muscles</forces_to_exclude>
<external_loads_file>external_loads.xml</external_loads_file><coordinates_file>motion.mot</coordinates_file>
<lowpass_cutoff_frequency_for_coordinates>6</lowpass_cutoff_frequency_for_coordinates>
<output_gen_force_file>inverse_dynamics.sto</output_gen_force_file>
</InverseDynamicsTool></OpenSimDocument>
""")
    (out / "so_setup.xml").write_text(f"""<?xml version="1.0" encoding="UTF-8" ?>
<OpenSimDocument Version="40500"><AnalyzeTool name="so">
<model_file>model_dynamics.osim</model_file><replace_force_set>false</replace_force_set>
<force_set_files>reserves.xml</force_set_files><results_directory>.</results_directory>
<output_precision>8</output_precision><initial_time>{t0}</initial_time><final_time>{t1}</final_time>
<solve_for_equilibrium_for_auxiliary_states>false</solve_for_equilibrium_for_auxiliary_states>
<AnalysisSet name="Analyses"><objects><StaticOptimization name="StaticOptimization"><on>true</on>
<start_time>{t0}</start_time><end_time>{t1}</end_time><step_interval>1</step_interval><in_degrees>true</in_degrees>
<use_model_force_set>true</use_model_force_set><activation_exponent>2</activation_exponent>
<use_muscle_physiology>true</use_muscle_physiology><optimizer_convergence_criterion>0.0001</optimizer_convergence_criterion>
<optimizer_max_iterations>200</optimizer_max_iterations></StaticOptimization></objects><groups/></AnalysisSet>
<ControllerSet name="Controllers"><objects/><groups/></ControllerSet>
<external_loads_file>external_loads.xml</external_loads_file><coordinates_file>motion.mot</coordinates_file>
<lowpass_cutoff_frequency_for_coordinates>6</lowpass_cutoff_frequency_for_coordinates>
</AnalyzeTool></OpenSimDocument>
""")
    with _cwd(out):
        if not osim.InverseDynamicsTool(str(out / "id_setup.xml")).run():
            raise RuntimeError(f"inverse dynamics failed ({out})")
        if not osim.AnalyzeTool(str(out / "so_setup.xml")).run():
            raise RuntimeError(f"static optimisation failed ({out})")
    summary = summarise(out, model_path, grf_qc, exercise, assist)
    summary.update({"label": label, "model_changes": model_info, "time_range_s": [round(t0, 3), round(t1, 3)]})
    (out / "muscles.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


def summarise(out, model_path, grf_qc, exercise, assist=()):
    osim = _osim()
    act = read_table(out / "so_StaticOptimization_activation.sto")
    model = osim.Model(str(out / "model_dynamics.osim"))
    model.initSystem()
    ms = model.getMuscles()
    fmax = {ms.get(i).getName(): ms.get(i).getMaxIsometricForce() for i in range(ms.getSize())}
    groups = muscle_groups([c for c in act.columns if c in fmax])
    group_act = {}
    for g, mus in sorted(groups.items()):
        w = np.array([fmax[m] for m in mus])
        a = np.column_stack([act.col(m) for m in mus])
        series = a @ w / w.sum()    # capacity-weighted mean activation = fraction of group capacity used
        group_act[g] = {"peak": round(float(series.max()), 3), "mean": round(float(series.mean()), 3),
                        "peak_single_muscle": round(float(a.max()), 3)}
    reserves = [c for c in act.columns if c.startswith("reserve_") and not c.startswith(("reserve_pelvis",
                "reserve_arm", "reserve_elbow", "reserve_pro_sup", "reserve_wrist", "reserve_neck"))]
    idt = read_table(out / "inverse_dynamics.sto")
    mass = grf_qc["body_mass_kg"]
    moments = {}
    for c in ("knee_angle_r_moment", "knee_angle_l_moment", "hip_flexion_r_moment", "hip_flexion_l_moment",
              "hip_adduction_r_moment", "hip_adduction_l_moment", "ankle_angle_r_moment", "ankle_angle_l_moment",
              "L5_S1_Flex_Ext_moment"):
        if idt.has(c):
            v = idt.col(c) / mass
            moments[c.replace("_moment", "")] = {"max_Nm_per_kg": round(float(v.max()), 3), "min_Nm_per_kg": round(float(v.min()), 3)}
    residual = {c: round(float(np.max(np.abs(idt.col(c)))), 1) for c in idt.columns if c.startswith("pelvis_t")}
    # Reserve torques that SO had to use (N·m) — large values mean muscles could not do it alone.
    reserve_peak = {}
    for r in reserves:
        # activation file holds controls for actuators; torque = control * optimal force (1 N·m here)
        peak = float(np.max(np.abs(act.col(r))))
        if peak > 1.0:
            reserve_peak[r[len("reserve_"):]] = round(peak, 2)
    exo = {}
    for coord, torque, lo, hi in assist:
        tq = act.col(f"exo_{coord}") * exo_optimal_force(torque)     # control x optimal force
        exo[coord] = {"max_torque_Nm": torque, "direction": {(-1.0, 1.0): "both", (0.0, 1.0): "pos", (-1.0, 0.0): "neg"}[(lo, hi)],
                      "peak_abs_Nm": round(float(np.max(np.abs(tq))), 2), "mean_abs_Nm": round(float(np.mean(np.abs(tq))), 2),
                      "time_at_cap_fraction": round(float(np.mean(np.abs(tq) > 0.98 * torque)), 3)}
    return {
        "exercise": exercise,
        "valid_exercise": exercise in VALID_EXERCISES,
        "assistive_devices": exo,
        "grf": grf_qc,
        "group_activation": group_act,
        "joint_moments": moments,
        "pelvis_residual_force_N": residual,
        "reserve_torque_peaks_Nm": reserve_peak,
        "muscles_saturated": sorted(c for c in act.columns if c in fmax and act.col(c).max() > 0.98),
        "caveats": [
            "Ground reaction forces are estimated (quasi-static double stance), not measured.",
            "Generic (scaled) muscle parameters: no personalised strength, no EMG calibration.",
            "Static optimisation minimises summed squared activation; real recruitment differs (co-contraction).",
        ] + (["Assistive devices are ideal (massless, instantaneous, optimally controlled): an upper bound on "
              "the benefit. Offloading a muscle in training also removes training stimulus - consider "
              "assist-as-needed rather than constant support."] if assist else []),
    }


def compare(base, other):
    """Per-group change in peak activation between two summaries (other - base)."""
    out = {}
    for g, v in base["group_activation"].items():
        if g in other["group_activation"]:
            b, o = v["peak"], other["group_activation"][g]["peak"]
            out[g] = {"base": b, "other": o, "change": round(o - b, 3),
                      "relative": round((o - b) / b, 3) if b > 1e-3 else None}
    return out
