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
from .io_formats import Table, read_table, to_degrees, write_table
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
# Residuals the estimated ground forces leave on the pelvis. A moment residual is expressed as the
# centre-of-pressure shift that would explain it; beyond ~10 cm (or 10 % BW of force) the forces and
# the motion do not belong together (e.g. fast squats with arm swing: segment angular momentum).
CONSISTENCY_COP_SHIFT_M = 0.10
CONSISTENCY_FORCE_BW = 0.10


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
    """Pose ``model`` at frame ``f`` of a degree table (``to_degrees`` first)."""
    import opensim as osim
    for c in cols:
        co = cs.get(c)
        v = table.data[f, table.columns.index(c)]
        co.setValue(state, np.radians(v) if co.getMotionType() == osim.Coordinate.Rotational else v, False)
    model.realizePosition(state)


def estimate_grf(model_path, table: Table, cutoff_hz=6.0, max_foot_speed=0.15, share_bias=0.0):
    """Quasi-static double-stance GRF estimate. Returns (columns, data (T, 18), qc dict).

    ``share_bias`` shifts the right foot's share of the load (e.g. +0.15) for sensitivity runs.
    """
    osim = _osim()
    model = osim.Model(str(model_path))
    state = model.initSystem()
    table = to_degrees(table, model)
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
    share_r = np.clip(np.sum(c * d, axis=1) / np.maximum(np.sum(d * d, axis=1), 1e-9) + share_bias, 0.0, 1.0)
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
        "right_share_bias": share_bias,
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


def parse_passive(spec):
    """'knee_angle_r=40@10:pos' -> (coordinate, K in N·m/rad, slack angle in deg, 'pos' | 'neg').

    A one-sided elastic element across the joint (band, spring): no torque until the coordinate
    passes the slack angle q0 in the given direction, then torque = -K (q - q0). 'pos' resists the
    coordinate increasing past q0 (e.g. knee flexion), 'neg' resists it decreasing.
    """
    coord, rest = spec.split("=", 1)
    rest, _, direction = rest.partition(":")
    k, _, q0 = rest.partition("@")
    direction = direction or "pos"
    if direction not in ("pos", "neg"):
        raise ValueError(f"passive: direction must be pos or neg, got {direction!r}")
    return coord, float(k), float(q0 or 0.0), direction


def passive_torque(k, q0_deg, direction, q_deg):
    """Torque (N·m) of a ``parse_passive`` element at coordinate values ``q_deg``."""
    d = np.radians(np.asarray(q_deg, float) - q0_deg)
    return -k * (np.maximum(d, 0.0) if direction == "pos" else np.minimum(d, 0.0))


def dynamics_model(model_path, out_path, weaken=None, passive=()):
    """Copy of the subject model for ID/SO: foot contact forces removed, optional weakened groups.

    ``weaken``: {"gluteus_medius_r": 0.5, ...} scales max isometric force.
    ``passive``: ``parse_passive`` tuples, added as ExpressionBasedCoordinateForce (static
    optimisation and inverse dynamics then treat them as known applied forces).
    Returns {"weakened": {group: [muscles]}, "passive": [...]}.
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
    resolved = []
    for coord, k, q0, direction in passive:
        real, gain = device_coordinate(model, coord)
        if not model.getCoordinateSet().contains(real):
            raise ValueError(f"passive: no coordinate {coord!r} in the model")
        # physical torque -K (gain q - q0) between the segments = generalized force -K gain^2 (q - q0/gain)
        fn = "max" if direction == "pos" else "min"
        force = osim.ExpressionBasedCoordinateForce(real, f"-{k * gain * gain}*{fn}(0,q-({np.radians(q0) / gain}))")
        force.setName(f"passive_{coord}")
        model.addForce(force)
        resolved.append((coord, k, q0, direction, real, gain))
    model.finalizeConnections()
    model.initSystem()
    model.printToXML(str(out_path))
    return {"weakened": {g: {"factor": weaken[g], "muscles": len(m)} for g, m in applied.items()},
            "passive": [{"coordinate": c, "stiffness_Nm_per_rad": k, "slack_deg": q0, "direction": d,
                         "model_coordinate": real, "coupling_gain": round(gain, 4)}
                        for c, k, q0, d, real, gain in resolved]}


# Trunk devices act between pelvis and thorax. In the Pose2Sim/Christophy spine the six lumbar levels
# are coupled to L5_S1, so a generalized force on L5_S1_* is not a physical trunk torque (the trunk
# turns ~7x the L5_S1 angle). These device coordinates take physical units and are converted.
TRUNK_COORDS = {"lumbar_total_extension": ("L5_S1_Flex_Ext", "lumbar_extension"),
                "lumbar_total_bending": ("L5_S1_Lat_Bending", "lumbar_bending"),
                "lumbar_total_rotation": ("L5_S1_axial_rotation", "lumbar_rotation")}


def _rotation(model, state, body):
    R = model.getBodySet().get(body).getTransformInGround(state).R()
    return np.array([[R.get(i, j) for j in range(3)] for i in range(3)])


def coupling_gain(model, coord, base="pelvis", body="torso", delta=0.05):
    """d(angle of ``body`` relative to ``base``)/d(``coord``) with the model's coupler constraints enforced."""
    state = model.initSystem()
    model.realizePosition(state)
    r0 = _rotation(model, state, base).T @ _rotation(model, state, body)
    model.getCoordinateSet().get(coord).setValue(state, delta, True)
    model.realizePosition(state)
    r1 = _rotation(model, state, base).T @ _rotation(model, state, body)
    d = r0.T @ r1
    return float(np.arccos(np.clip((np.trace(d) - 1.0) / 2.0, -1.0, 1.0)) / delta)


def device_coordinate(model, coord):
    """(model coordinate, gain) for a device coordinate; physical angle = gain x model coordinate."""
    if coord not in TRUNK_COORDS:
        return coord, 1.0
    coupled, single = TRUNK_COORDS[coord]
    if model.getCoordinateSet().contains(coupled):
        return coupled, coupling_gain(model, coupled)
    if model.getCoordinateSet().contains(single):     # one-joint lumbar (Rajagopal): no coupling
        return single, 1.0
    raise ValueError(f"{coord}: the model has neither {coupled} nor {single}")


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
        real, gain = device_coordinate(model, coord)
        if not cs.contains(real):
            raise ValueError(f"assist: no coordinate {coord!r} in the model")
        cap = torque * gain            # physical torque cap -> generalized force on the model coordinate
        opt = exo_optimal_force(cap)
        items.append(f'<CoordinateActuator name="exo_{coord}"><coordinate>{real}</coordinate>'
                     f"<optimal_force>{opt}</optimal_force><min_control>{lo * cap / opt}</min_control>"
                     f"<max_control>{hi * cap / opt}</max_control></CoordinateActuator>")
    Path(path).write_text('<?xml version="1.0" encoding="UTF-8" ?>\n<OpenSimDocument Version="40500">'
                          f'<ForceSet name="reserves"><objects>{"".join(items)}</objects><groups/></ForceSet></OpenSimDocument>\n')


def run(model_path, motion_path, out_dir, weaken=None, label="measured", exercise="squat", start=None, stop=None,
        assist=(), grf_share_bias=0.0, passive=(), max_fps=None, muscle_model=None):
    """GRF estimate → ID → SO for one motion. Returns a summary dict (also written to muscles.json).

    ``muscle_model``: the study's record of where muscle capacities came from (generic or dynamometry),
    so the caveats describe the model actually used."""
    osim = _osim()
    out = Path(out_dir) / label
    out.mkdir(parents=True, exist_ok=True)
    tab = to_degrees(read_table(motion_path), model_path)
    fps = 1.0 / float(np.median(np.diff(tab.time)))
    if max_fps and fps > 1.05 * max_fps:      # a slow exercise does not need 60 Hz static optimisation
        step = int(round(fps / max_fps))
        tab = Table(tab.columns, tab.data[::step], tab.time[::step], tab.in_degrees, tab.header)
        fps /= step
    t0 = tab.time[0] if start is None else start
    t1 = tab.time[-1] if stop is None else stop
    write_table(out / "motion.mot", tab.columns, tab.data, tab.time, tab.in_degrees, name="motion")
    names, grf, grf_qc = estimate_grf(model_path, tab, share_bias=grf_share_bias)
    write_table(out / "grf.mot", names, grf, tab.time, in_degrees=False, name="estimated_grf")
    (out / "external_loads.xml").write_text(_external_loads_xml("grf.mot"))
    passive = [parse_passive(p) if isinstance(p, str) else p for p in passive]
    model_info = dynamics_model(model_path, out / "model_dynamics.osim", weaken, passive)
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
    summary = summarise(out, model_path, grf_qc, exercise, assist, muscle_model)
    window = (tab.time >= t0 - 1e-9) & (tab.time <= t1 + 1e-9)
    summary["passive_devices"] = {}
    for dev in model_info["passive"]:
        coord, k, q0, direction = dev["coordinate"], dev["stiffness_Nm_per_rad"], dev["slack_deg"], dev["direction"]
        q = tab.col(dev["model_coordinate"])[window]
        q = dev["coupling_gain"] * q      # physical joint/trunk angle (deg)
        tq = passive_torque(k, q0, direction, q)
        summary["passive_devices"][coord] = {"stiffness_Nm_per_rad": k, "slack_deg": q0, "direction": direction,
                                             "peak_abs_Nm": round(float(np.max(np.abs(tq))), 2),
                                             "mean_abs_Nm": round(float(np.mean(np.abs(tq))), 2),
                                             "engaged_fraction": round(float(np.mean(np.abs(tq) > 1e-6)), 3)}
    if passive:
        summary["caveats"].append("Passive elements are ideal one-sided linear springs on the joint coordinate "
                                  "(no slip, no strap migration, no skin compression); real garments lose much of "
                                  "their nominal stiffness to soft tissue.")
    summary.update({"label": label, "model_changes": model_info, "time_range_s": [round(t0, 3), round(t1, 3)],
                    "analysis_fps": round(fps, 2)})
    (out / "muscles.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


def muscle_caveat(muscle_model=None):
    """Which capacities are measured and which generic: dynamometry fixes only the tested groups."""
    mm = muscle_model or {}
    cap = mm.get("capacity") or {}
    leg = {"dxa": "each leg's volume from its DXA lean mass (McCarthy 2023)",
           "anthropometry": "scaled to the person's age, sex, height and mass (NHANES DXA reference data)"}.get(
        cap.get("leg_source"), "scaled to the measured height and mass by a population regression (Handsfield 2014)")
    size = ("leg muscles from measured volume/fat fraction where imaged (" + (cap["imaging"].get("method") or "imaging")
            + f"), the others take their leg's volume from {cap.get('leg_source_text', 'height and mass')}, trunk and "
            "arms generic"
            if cap.get("imaging") else f"leg muscles {leg}, trunk and arms generic" if cap.get("scaled")
            else "generic (scaled) parameters")
    if cap.get("mass_distribution"):
        size += "; segment masses from the DXA regional masses"
    bmi = next((c for c in cap.get("caveats", []) if c.startswith(("BMI", "Age"))), "")
    if mm.get("source", "").startswith("strength"):
        return (f"Muscle capacities of the tested groups ({', '.join(mm.get('tests', [])) or 'none'}; "
                f"{mm.get('calibrated_muscles', '?')} muscles) come from dynamometry; all other muscles: {size}. "
                f"Muscle geometry is generic; no EMG calibration. {bmi}").strip()
    if cap.get("imaging"):
        return (f"Muscle capacities: {size}. Force follows contractile volume, not a strength test; muscle geometry "
                f"is generic; no EMG calibration. {bmi}").strip()
    if cap.get("scaled") and cap.get("leg_source") == "dxa":
        return (f"Muscle capacities: {size}. Measured per leg, not per muscle; force follows volume, not a strength "
                f"test; muscle geometry is generic; no EMG calibration. {bmi}").strip()
    if cap.get("scaled"):
        return (f"Muscle capacities: {size}. A population estimate, not this person's measured strength; "
                f"muscle geometry is generic; no EMG calibration. {bmi}").strip()
    return "Generic (scaled) muscle parameters: no personalised strength, no EMG calibration."


def summarise(out, model_path, grf_qc, exercise, assist=(), muscle_model=None):
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
    residual = {c: round(float(np.max(np.abs(idt.col(c)))), 1) for c in idt.columns if c.startswith("pelvis_")}
    weight = mass * 9.81
    rot = max((v for c, v in residual.items() if c.endswith("_moment")), default=0.0) / weight
    lin = max((v for c, v in residual.items() if c.endswith("_force")), default=0.0) / weight
    consistency = {"pelvis_moment_residual_as_cop_shift_m": round(rot, 3), "pelvis_force_residual_bw": round(lin, 3),
                   "consistent": bool(rot <= CONSISTENCY_COP_SHIFT_M and lin <= CONSISTENCY_FORCE_BW),
                   "rule": f"pelvis residual moment / body weight <= {CONSISTENCY_COP_SHIFT_M} m and residual force "
                           f"<= {CONSISTENCY_FORCE_BW} BW"}
    # Reserve torques that SO had to use (N·m) — large values mean muscles could not do it alone.
    reserve_peak = {}
    for r in reserves:
        # activation file holds controls for actuators; torque = control * optimal force (1 N·m here)
        peak = float(np.max(np.abs(act.col(r))))
        if peak > 1.0:
            reserve_peak[r[len("reserve_"):]] = round(peak, 2)
    exo = {}
    for coord, torque, lo, hi in assist:
        _, gain = device_coordinate(model, coord)
        tq = act.col(f"exo_{coord}") * exo_optimal_force(torque * gain) / gain   # physical torque
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
        "dynamic_consistency": consistency,
        "reserve_torque_peaks_Nm": reserve_peak,
        "muscles_saturated": sorted(c for c in act.columns if c in fmax and act.col(c).max() > 0.98),
        "caveats": [
            "Ground reaction forces are estimated (quasi-static double stance), not measured.",
            muscle_caveat(muscle_model),
            "Static optimisation minimises summed squared activation; real recruitment differs (co-contraction). "
            "It also shifts load from weak muscles to stronger synergists, so a weakness can show up as extra "
            "synergist demand rather than as higher activation of the weak muscle itself.",
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


def _xform(transform, v):
    R, p = transform.R(), transform.p()
    return [sum(R.get(i, j) * v.get(j) for j in range(3)) + p.get(i) for i in range(3)]


def simplify_polyline(P, tol):
    """Douglas-Peucker: drop points within ``tol`` of the chord (wrap surfaces are densely sampled)."""
    if len(P) < 3:
        return P
    a, b = P[0], P[-1]
    ab = b - a
    d = np.linalg.norm(np.cross(P - a, ab), axis=1) / (np.linalg.norm(ab) or 1.0)
    i = int(np.argmax(d))
    if d[i] <= tol:
        return P[[0, -1]]
    return np.vstack([simplify_polyline(P[:i + 1], tol)[:-1], simplify_polyline(P[i:], tol)])


def path_frames(model_path, motion_path, times, tol_mm=3.0):
    """Muscle lines of action in ground at ``times`` for the 3D muscle view.

    Returns (muscle names, max isometric forces, paths, bodies) where ``paths[k][m]`` is a flat
    [x, y, z, ...] polyline in integer mm, including the points on wrapping surfaces (drawn the
    way OpenSim's own visualiser draws a GeometryPath, simplified to ``tol_mm``), and
    ``bodies[name][k]`` the body origins (mm) for the bone lines.
    """
    osim = _osim()
    from .kinematics import SKELETON_BODIES
    model = osim.Model(str(model_path))
    state = model.initSystem()
    tab = to_degrees(read_table(motion_path), model)
    cs = model.getCoordinateSet()
    cols = [c for c in tab.columns if cs.contains(c)]
    interp = Table(tab.columns, np.column_stack([np.interp(times, tab.time, tab.data[:, j]) for j in range(len(tab.columns))]),
                   np.asarray(times, float), True)
    ms = model.getMuscles()
    names = [ms.get(i).getName() for i in range(ms.getSize())]
    fmax = [ms.get(i).getMaxIsometricForce() for i in range(ms.getSize())]
    geo = [osim.GeometryPath.safeDownCast(ms.get(i).getPath()) for i in range(ms.getSize())]
    bodies = {b: [] for b in SKELETON_BODIES if model.getBodySet().contains(b)}
    paths = []
    for k in range(len(times)):
        _set_state(model, state, interp, k, cs, cols)
        frame = []
        for g in geo:
            pts = []
            cur = g.getCurrentPath(state)
            for i in range(cur.getSize()):
                pp = cur.get(i)
                pwp = osim.PathWrapPoint.safeDownCast(pp)
                if pwp is not None:
                    X = pwp.getParentFrame().getTransformInGround(state)
                    surface = pwp.getWrapPath(state)
                    for j in range(surface.getSize()):
                        pts.extend(_xform(X, surface.get(j)))
                else:
                    loc = pp.getLocationInGround(state)
                    pts.extend(loc.get(j) for j in range(3))
            P = simplify_polyline(np.asarray(pts, float).reshape(-1, 3) * 1000.0, tol_mm)
            frame.append(np.rint(P).astype(int).ravel().tolist())
        paths.append(frame)
        for b in bodies:
            p = model.getBodySet().get(b).getPositionInGround(state)
            bodies[b].append([int(round(p.get(j) * 1000)) for j in range(3)])
    return names, fmax, paths, bodies


def activation_frames(run_dir, names, times):
    """SO activations of ``names`` resampled at ``times`` as integer percent ([k][m]); None if absent."""
    act = read_table(Path(run_dir) / "so_StaticOptimization_activation.sto")
    out = np.zeros((len(times), len(names)), int)
    for m, n in enumerate(names):
        if act.has(n):
            out[:, m] = np.rint(np.clip(np.interp(times, act.time, act.col(n)), 0, 1) * 100)
    return out.tolist()


def view_data(model_path, run_dirs, motions, start, stop, max_fps=20.0):
    """Data for the 3D muscle view.

    ``run_dirs``: {label: SO output folder}; ``motions``: {label: motion file the run used}.
    Paths are computed once per distinct motion; capacities come from each run's dynamics model,
    so a weakened group is visibly thinner.
    """
    osim = _osim()
    first = read_table(next(iter(motions.values())))
    fps = 1.0 / float(np.median(np.diff(first.time)))
    step = max(1, int(round(fps / max_fps)))
    sel = first.time[(first.time >= start - 1e-9) & (first.time <= stop + 1e-9)][::step]
    times = [round(float(t), 4) for t in sel]
    view = {"t": times, "fps": fps / step, "motions": {}, "runs": {}}
    by_file = {}
    for label, motion in motions.items():
        key = str(Path(motion).resolve())
        if key not in by_file:
            names, fmax, paths, bodies = path_frames(model_path, motion, times)
            by_file[key] = f"m{len(by_file)}"
            view["motions"][by_file[key]] = {"paths": paths, "bodies": bodies}
            view["muscles"] = names
            view["groups"] = {m: g for g, ms in muscle_groups(names).items() for m in ms}
        model = osim.Model(str(Path(run_dirs[label]) / "model_dynamics.osim"))
        cap = model.getMuscles()
        view["runs"][label] = {"motion": by_file[key],
                               "fmax": [round(cap.get(n).getMaxIsometricForce()) for n in view["muscles"]],
                               "act": activation_frames(run_dirs[label], view["muscles"], times)}
    from .kinematics import SKELETON_BONES
    view["bones"] = [b for b in SKELETON_BONES if "head_top" not in b]
    return view


def grf_bands(runs):
    """Per-group peak-activation band over GRF-split sensitivity runs ({label: summary})."""
    groups = set.intersection(*(set(r["group_activation"]) for r in runs.values()))
    return {g: {"lo": min(r["group_activation"][g]["peak"] for r in runs.values()),
                "hi": max(r["group_activation"][g]["peak"] for r in runs.values())} for g in sorted(groups)}


MIN_ROBUST_CHANGE = 0.02     # fraction of capacity: smaller changes are not reported as effects


def robust_to_grf(changes, min_change=MIN_ROBUST_CHANGE):
    """A paired change (variant - measured) is robust if it keeps its sign and stays >= ``min_change``
    under every GRF split it was recomputed with."""
    changes = list(changes)
    return bool(all(c >= min_change for c in changes) or all(c <= -min_change for c in changes))
