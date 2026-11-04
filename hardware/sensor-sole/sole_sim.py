#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors
# SPDX-License-Identifier: CERN-OHL-S-2.0
"""The sensor sole in simulation: a virtual sole that reads what a simulated foot presses on it.

Simulation comes before any physical test. This file puts a sole design into the musculoskeletal model as a
sensorised contact layer, and turns what the simulation computes into the readings the real pod would
produce. Nothing here is a measurement: the sensor response is an assumption until the coupon test
(DESIGN.md, section 8) replaces it.

Three steps:
  export   board file -> <id>.sole_sim.json. Regions in the sole frame, a grid of contact points inside each
           region, and the contact-to-region map (from the verified deployed map when given).
           Needs shapely (the generator's Python).
  osim     OpenSim model + sole_sim.json -> a model whose foot touches the ground through the sole: one contact
           sphere per contact point, each named after its region. Toe regions ride on the toes. Every other
           point rides on the foot segment it lies under: calcn on a two-segment foot (the metatarsal heads are
           proximal of the toe joint), or calcn, midfoot or forefoot on a multi-segment one, found by following
           the joints from calcn to the toes. A foot without that chain is refused. By default the spheres
           replace the generic contact spheres on every segment of that foot.
           Needs the opensim package (the pipeline's Python).
  readout  forces from a simulation (an OpenSim ForceReporter .sto) -> per-region normal force, centre of
           pressure and pod readings in contact order, through the assumed sensor model. numpy only.

Frames. The sole frame is the generator's: x from the heel point along the heel -> 2nd-toe axis, z to the
right (a left sole is the mirror, so its lateral side is -z), millimetres. OpenSim's calcn frames use the same
axes (x forward, y up, z right for both feet), in metres. The sole is registered on the model by two
landmarks: its heel point on the back of the model's heel sphere, and its toe-joint bend line on the model's
toe joint (mtp) axis; the scale between them is applied to x and z. The plantar plane is the bottom of the
model's calcn contact spheres. Landmarks are read at the model's default pose, through OpenSim's own frame
transforms, so a toe joint that hangs from a midfoot or forefoot segment is located correctly.

  python sole_sim.py export out/sole_EU42_R.board.json --map maps/EU42_R_<hash>.json -o sim/
  python sole_sim.py osim model_scaled.osim sim/EU42_R_<hash>.sole_sim.json -o model_with_sole.osim
  python sole_sim.py readout forces.sto sim/EU42_R_<hash>.sole_sim.json -o readings.csv
"""
import argparse
import json
import math
from pathlib import Path

import numpy as np

FORMAT = "sensor-sole-sim/1"
# Assumed sensor response, until the coupon test measures the film (DESIGN.md, section 8). Stated, not measured.
SENSOR_MODEL = dict(
    kind="assumed: power law with saturation, 12-bit readout",
    full_scale_kpa=600.0,      # pressure on a region's sensing area that reaches full scale
    exponent=1.0,              # reading ~ (F / F_full) ** exponent below saturation
    adc_bits=12,
    noise_fraction=0.005,      # standard deviation as a fraction of full scale
    rate_hz=100.0,
    note="Not measured. Replace with the coupon test's curve per material; hysteresis, creep and temperature "
         "drift are not modelled.")


# ------------------------------------------------------------------------------------------------- export
def export(board_json, map_json=None, spacing=15.0, min_points=2):
    """A sole design for simulation, from the generator's board file (and its deployed map if given)."""
    from shapely.geometry import Point, Polygon
    d = json.loads(Path(board_json).read_text())
    regions, points = {}, {}
    for n, r in d["regions"].items():
        poly = Polygon(r["outline"])
        regions[n] = dict(outline=[[round(x, 2), round(z, 2)] for x, z in poly.simplify(0.1).exterior.coords[:-1]],
                          area_mm2=round(poly.area, 1),
                          centroid=[round(poly.centroid.x, 2), round(poly.centroid.y, 2)])
        # contact points: a square grid inside the region, finer for small regions so each has at least a few.
        # The grid is anchored at the region's centroid, so a left sole's points mirror the right sole's exactly.
        step = min(spacing, max(3.0, math.sqrt(poly.area / max(min_points, 1))))
        x0, z0, x1, z1 = poly.bounds
        cx, cz = poly.centroid.x, poly.centroid.y
        inner = poly.buffer(-min(step / 2, 2.0))
        xs = cx + step * np.arange(math.floor((x0 - cx) / step), math.ceil((x1 - cx) / step) + 1)
        zs = cz + step * np.arange(math.floor((z0 - cz) / step), math.ceil((z1 - cz) / step) + 1)
        pts = [(x, z) for x in xs for z in zs if inner.contains(Point(x, z))]
        if not pts:
            pts = [tuple(poly.representative_point().coords[0])]
        points[n] = [[round(x, 2), round(z, 2)] for x, z in pts]
    if map_json:
        m = json.loads(Path(map_json).read_text())
        if m.get("board_id") != d["board_id"]:
            raise SystemExit(f"map is for {m.get('board_id')!r}, the board is {d['board_id']!r}")
        contacts = {str(k): v for k, v in m["map"].items()}
        source = f"deployed map {Path(map_json).name} (verified through the copper)"
    else:
        order = d["copper_routing"]["pin_order"]
        contacts = {str(i + 1): n for i, n in enumerate(order)}
        source = "the board file's planned pin order (not verified; pass --map for the deployed map)"
    return dict(format=FORMAT, board_id=d["board_id"], design_hash=d["design_hash"], side=d["side"],
                foot_length_mm=d["foot_length"], ball_width_mm=d["ball_width"],
                frame="sole frame: x from the heel point along the heel -> 2nd-toe axis, z to the right "
                      "(a left sole is mirrored), mm",
                bend=dict(point=d["bend"]["point"], dir=d["bend"]["dir"]),
                regions=regions, contact_points=points, point_spacing_mm=spacing,
                contacts=contacts, contacts_source=source, sensor_model=SENSOR_MODEL,
                status="simulation model only: sensing, fit and durability untested; not released for fabrication")


# ----------------------------------------------------------------------------------------- registration
def register(sole, heel_x, plantar_y, mtp_point, mtp_axis):
    """Sole frame (mm) -> calcn frame (m). Returns (to_calcn(x, z) -> (X, Y, Z), scale, mtp line x(z))."""
    bp, bd = np.asarray(sole["bend"]["point"], float), np.asarray(sole["bend"]["dir"], float)
    bend_x0 = bp[0] - bp[1] * bd[0] / bd[1] if abs(bd[1]) > 1e-9 else bp[0]      # bend line at z = 0, mm
    ax = np.asarray(mtp_axis, float)
    mtp_x = lambda Z: mtp_point[0] + (Z - mtp_point[2]) * ax[0] / ax[2] if abs(ax[2]) > 1e-9 else mtp_point[0]
    scale = (mtp_x(0.0) - heel_x) / (bend_x0 / 1000.0)                            # m per (mm / 1000)
    to_calcn = lambda x, z: (heel_x + scale * x / 1000.0, plantar_y, scale * z / 1000.0)
    return to_calcn, scale, mtp_x


def foot_chain(model, side):
    """The foot's bodies from calcn_<s> to toes_<s>, following the joints, and the joints between them.

    Two-segment feet (calcn -> toes) and multi-segment ones (calcn -> midfoot -> forefoot -> toes, as in D'Hondt
    et al. 2024) both work. Anything else stops here rather than being simulated with the sole in the wrong place."""
    s = side.lower()
    bodies = model.getBodySet()
    if not (bodies.contains(f"calcn_{s}") and bodies.contains(f"toes_{s}")):
        raise SystemExit(f"the model has no calcn_{s} and toes_{s}: this foot is not supported")
    into = {}
    for j in model.getJointSet():
        into[j.getChildFrame().findBaseFrame().getName()] = j
    chain, joints, b = [f"toes_{s}"], [], f"toes_{s}"
    while b != f"calcn_{s}":
        j = into.get(b)
        if j is None or len(chain) > 8:
            raise SystemExit(f"toes_{s} is not reached from calcn_{s} through the model's joints: "
                             f"this foot is not supported (chain so far: {chain[::-1]})")
        joints.append(j.getName())
        b = j.getParentFrame().findBaseFrame().getName()
        chain.append(b)
    return chain[::-1], joints[::-1]


def model_foot(model, side, state):
    """One foot's landmarks in the calcn frame, at the model's default pose: heel x, plantar height, toe-joint
    point and axis, and where each segment between calcn and the toes begins (its proximal joint)."""
    import opensim as osim
    s = side.lower()
    chain, joints = foot_chain(model, side)
    calcn = model.getBodySet().get(f"calcn_{s}")
    model.realizePosition(state)
    v = lambda p: np.array([p.get(0), p.get(1), p.get(2)])
    spheres = []
    for i in range(model.getContactGeometrySet().getSize()):
        g = model.getContactGeometrySet().get(i)
        base = g.getFrame().findBaseFrame().getName()
        if g.getConcreteClassName() == "ContactSphere" and base in chain:
            sp = osim.ContactSphere.safeDownCast(g)
            at = v(g.getFrame().findStationLocationInAnotherFrame(state, sp.get_location(), calcn))
            spheres.append((base, at, sp.getRadius()))
    on_calcn = [q for q in spheres if q[0] == f"calcn_{s}"]
    if not on_calcn:
        raise SystemExit(f"no contact spheres on calcn_{s}: cannot find the heel and the plantar plane")
    heel = min(on_calcn, key=lambda q: q[1][0])
    heel_x = heel[1][0] - heel[2]
    plantar_y = float(np.mean([q[1][1] - q[2] for q in on_calcn]))
    toe_joint = model.getJointSet().get(joints[-1])           # the joint into the toes (mtp)
    P = toe_joint.getParentFrame()
    mtp_point = v(P.findStationLocationInAnotherFrame(state, osim.Vec3(0, 0, 0), calcn))
    mtp_axis = v(P.expressVectorInAnotherFrame(state, osim.Vec3(0, 0, 1), calcn))
    segments = []                                             # (body, x of its proximal joint in calcn)
    for body, jn in zip(chain[1:-1], joints[:-1]):
        C = model.getJointSet().get(jn).getChildFrame()
        segments.append((body, float(v(C.findStationLocationInAnotherFrame(state, osim.Vec3(0, 0, 0), calcn))[0])))
    pose = {}
    for jn in joints:
        j = model.getJointSet().get(jn)
        for k in range(j.numCoordinates()):
            c = j.get_coordinates(k)
            pose[c.getName()] = round(c.getValue(state), 6)
    return dict(heel_x=float(heel_x), plantar_y=plantar_y, mtp_point=mtp_point, mtp_axis=mtp_axis,
                generic_spheres=spheres, chain=chain, joints=joints, segments=segments, pose=pose)


# --------------------------------------------------------------------------------------------- OpenSim
def add_to_osim(model_path, sole_json, out_path, radius_mm=None, keep_generic=False):
    """Write a copy of the model whose foot meets the ground through the sole's contact points."""
    import opensim as osim
    sole = json.loads(Path(sole_json).read_text())
    side = sole["side"]; s = side.lower()
    model = osim.Model(str(model_path))
    state = model.initSystem()
    foot = model_foot(model, side, state)
    chain = foot["chain"]
    to_calcn, scale, mtp_x = register(sole, foot["heel_x"], foot["plantar_y"], foot["mtp_point"], foot["mtp_axis"])
    # where each sole point goes, worked out before the model is changed (its state is still valid now):
    # toe regions ride on the toes; every other point on the foot segment it lies under, i.e. the last segment
    # whose proximal joint is behind it (calcn if the foot has no segment between calcn and the toes). The
    # boundary is a line across the foot through the joint centre, an approximation of an oblique joint axis.
    r = (radius_mm if radius_mm else sole["point_spacing_mm"] / 2) / 1000.0
    calcn = model.getBodySet().get(f"calcn_{s}")
    plan = []
    for n, pts in sole["contact_points"].items():
        for k, (x, z) in enumerate(pts):
            X, Y, Z = to_calcn(x, z)
            if n.startswith("toe"):
                body = f"toes_{s}"
            else:
                body = f"calcn_{s}"
                for seg, bx in foot["segments"]:
                    if X >= bx:
                        body = seg
            at = calcn.findStationLocationInAnotherFrame(state, osim.Vec3(X, Y + r, Z), model.getBodySet().get(body))
            plan.append((n, k, body, np.array([at.get(0), at.get(1), at.get(2)])))
    forces = model.getForceSet()
    template, half_space = None, None
    for i in range(forces.getSize()):
        fo = forces.get(i)
        if fo.getConcreteClassName() == "SmoothSphereHalfSpaceForce":
            ss = osim.SmoothSphereHalfSpaceForce.safeDownCast(fo)
            if ss.getConnectee("sphere").getFrame().findBaseFrame().getName() in chain:
                template = template or ss
                half_space = half_space or ss.getConnectee("half_space")
    if template is None:
        raise SystemExit(f"no SmoothSphereHalfSpaceForce on foot {side}: nothing to copy contact parameters from")
    params = dict(stiffness=template.get_stiffness(), dissipation=template.get_dissipation(),
                  static_friction=template.get_static_friction(), dynamic_friction=template.get_dynamic_friction(),
                  viscous_friction=template.get_viscous_friction(), transition_velocity=template.get_transition_velocity(),
                  constant_contact_force=template.get_constant_contact_force(),
                  hertz_smoothing=template.get_hertz_smoothing(), hunt_crossley_smoothing=template.get_hunt_crossley_smoothing())
    hs_name, template_name = half_space.getName(), template.getName()
    if not keep_generic:                                  # the sole replaces the generic contact of every segment
        for i in reversed(range(forces.getSize())):
            fo = forces.get(i)
            if fo.getConcreteClassName() == "SmoothSphereHalfSpaceForce":
                ss = osim.SmoothSphereHalfSpaceForce.safeDownCast(fo)
                if ss.getConnectee("sphere").getFrame().findBaseFrame().getName() in chain:
                    forces.remove(i)
        cg = model.getContactGeometrySet()
        for i in reversed(range(cg.getSize())):
            if cg.get(i).getFrame().findBaseFrame().getName() in chain:
                cg.remove(i)
    # Keep the foot's overall contact stiffness: Hertz contact scales with sqrt(radius) per sphere, so n sole
    # spheres of radius r get stiffness k * (n_generic * sqrt(R_generic)) / (n * sqrt(r)). Otherwise 55 spheres with
    # the generic stiffness make the foot several times stiffer than the model it came from.
    generic = [q for q in foot["generic_spheres"]]
    n_sole = sum(len(v) for v in sole["contact_points"].values())
    k_scale = (sum(math.sqrt(q[2]) for q in generic) / (n_sole * math.sqrt(r))) if generic else 1.0
    params["stiffness"] = params["stiffness"] * k_scale
    placed = []
    for n, k, body, loc in plan:
        name = f"sole_{s}_{n}_{k:02d}"
        sp = osim.ContactSphere(r, osim.Vec3(*loc), model.getBodySet().get(body), name)
        model.addContactGeometry(sp)
        hs = osim.ContactHalfSpace.safeDownCast(model.getContactGeometrySet().get(hs_name))
        fo = osim.SmoothSphereHalfSpaceForce(f"force_{name}", sp, hs)
        for key, v in params.items():
            getattr(fo, f"set_{key}")(v)
        model.addForce(fo)
        placed.append(dict(region=n, sphere=name, body=body))
    model.finalizeConnections()
    model.initSystem()
    model.printToXML(str(out_path))
    warn = None
    if abs(scale - 1) > 0.05:
        warn = (f"the sole is scaled by {scale:.3f} to fit this model's foot (heel to toe joint): the sole was not "
                f"made for this foot. Generate it for the model's foot length for a faithful simulation.")
    meta = dict(model=str(out_path), sole=sole["board_id"], side=side, scale=round(scale, 4), warning=warn,
                spheres=len(placed), radius_m=r, replaced_generic=not keep_generic,
                contact_parameters_from=template_name, stiffness_scale=round(k_scale, 4),
                stiffness_per_sphere=params["stiffness"], registration=dict(
                    heel_x=foot["heel_x"], plantar_y=foot["plantar_y"], mtp_point=foot["mtp_point"].tolist()),
                regions={n: sum(1 for p in placed if p["region"] == n) for n in sole["contact_points"]},
                on_toes=sorted({p["region"] for p in placed if p["body"].startswith("toes")}),
                foot_chain=chain, toe_joint=foot["joints"][-1], pose=foot["pose"],
                segment_starts_x={b: round(x, 5) for b, x in foot["segments"]},
                spheres_per_body={b: sum(1 for p in placed if p["body"] == b) for b in chain},
                replaced_generic_on=sorted({q[0] for q in generic}) if not keep_generic else [])
    Path(out_path).with_suffix(".sole_sim_meta.json").write_text(json.dumps(meta, indent=1, default=float) + "\n")
    return meta


# --------------------------------------------------------------------------------------------- readout
def read_sto(path):
    """Columns of an OpenSim storage/table file (.sto/.mot)."""
    lines = Path(path).read_text().splitlines()
    i = next(k for k, ln in enumerate(lines) if ln.strip().lower() == "endheader")
    head = lines[i + 1].split("\t")
    data = np.array([[float(v) for v in ln.split("\t")] for ln in lines[i + 2:] if ln.strip()])
    return head, data


def region_forces(head, data, sole):
    """Per-region normal force (N) over time: the vertical force the ground exerts on each sole sphere, summed per
    region. OpenSim's ForceReporter labels it "<force>.Sphere.force.Y" (the half-space gets the opposite)."""
    s = sole["side"].lower()
    out = {}
    for n in sole["contact_points"]:
        pre = f"force_sole_{s}_{n}_"
        up = [k for k, h in enumerate(head) if h.startswith(pre) and h.lower().endswith(".sphere.force.y")]
        down = [k for k, h in enumerate(head) if h.startswith(pre) and h.lower().endswith(".halfspace.force.y")]
        if up:
            out[n] = np.sum(data[:, up], axis=1)
        elif down:
            out[n] = -np.sum(data[:, down], axis=1)
        else:
            raise ValueError(f"no force columns for region {n} (expected {pre}..Sphere.force.Y)")
    return out


def readings(forces, sole, seed=0):
    """Pod readings in contact order from region forces, through the assumed sensor model."""
    m = sole["sensor_model"]
    rng = np.random.default_rng(seed)
    full = (1 << m["adc_bits"]) - 1
    by_contact = {}
    for c, n in sorted(sole["contacts"].items(), key=lambda kv: int(kv[0])):
        if n == "COM" or n not in forces:
            continue
        f_full = m["full_scale_kpa"] * 1e3 * sole["regions"][n]["area_mm2"] * 1e-6
        x = np.clip(np.maximum(forces[n], 0) / f_full, 0, 1) ** m["exponent"]
        x = x + rng.normal(0, m["noise_fraction"], len(x))
        by_contact[int(c)] = np.clip(np.round(x * full), 0, full).astype(int)
    return by_contact


def centre_of_pressure(forces, sole):
    """Centre of pressure in the sole frame (mm) from region forces at region centroids."""
    names = list(forces)
    F = np.array([forces[n] for n in names]).clip(min=0)
    C = np.array([sole["regions"][n]["centroid"] for n in names])
    tot = F.sum(axis=0)
    with np.errstate(invalid="ignore", divide="ignore"):
        return (F.T @ C) / tot[:, None], tot


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("export"); e.add_argument("board_json"); e.add_argument("--map"); e.add_argument("-o", required=True)
    e.add_argument("--spacing", type=float, default=15.0)
    o = sub.add_parser("osim"); o.add_argument("model"); o.add_argument("sole_json"); o.add_argument("-o", required=True)
    o.add_argument("--radius-mm", type=float); o.add_argument("--keep-generic", action="store_true")
    r = sub.add_parser("readout"); r.add_argument("forces_sto"); r.add_argument("sole_json"); r.add_argument("-o", required=True)
    a = ap.parse_args()
    if a.cmd == "export":
        sole = export(a.board_json, a.map, a.spacing)
        out = Path(a.o); out.mkdir(parents=True, exist_ok=True)
        label, side, hx = sole["board_id"].split()
        path = out / f"{label}_{side}_{hx}.sole_sim.json"
        path.write_text(json.dumps(sole, indent=1) + "\n")
        print(f"{path}: {len(sole['regions'])} regions, {sum(len(v) for v in sole['contact_points'].values())} contact points")
    elif a.cmd == "osim":
        print(json.dumps(add_to_osim(a.model, a.sole_json, a.o, a.radius_mm, a.keep_generic), indent=1, default=float))
    else:
        sole = json.loads(Path(a.sole_json).read_text())
        head, data = read_sto(a.forces_sto)
        f = region_forces(head, data, sole)
        cop, tot = centre_of_pressure(f, sole)
        rd = readings(f, sole)
        t = data[:, 0]
        cols = ["time", "total_N", "cop_x_mm", "cop_z_mm"] + [f"F_{n}" for n in f] + [f"contact_{c}" for c in rd]
        rows = np.column_stack([t, tot, cop[:, 0], cop[:, 1]] + [f[n] for n in f] + [rd[c] for c in rd])
        np.savetxt(a.o, rows, delimiter=",", header=",".join(cols), comments="", fmt="%.6g")
        print(f"{a.o}: {len(t)} samples, {len(f)} regions, {len(rd)} channels (readings from the assumed sensor model)")


if __name__ == "__main__":
    main()
