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

Experimental. This is simulated foot-to-ground contact through a virtual sole, not the foot pressing on a sole
inside a shoe, and nothing here has been validated against measurements. Agreement between simulations is not
physical validation.

Supported feet (anything else is refused with UnsupportedModel, before the model is changed):
  - bodies calcn_<s> and toes_<s>, joined by a chain of joints from calcn to the toes;
  - every joint in that chain a weld or a single rotational coordinate about one axis through the joint centre
    (each axis is measured, not assumed);
  - generic foot contact made only of ContactSpheres on chain bodies, each used by exactly one
    SmoothSphereHalfSpaceForce, all against one ContactHalfSpace on ground and with identical parameters; no
    other contact geometry on the foot (the chain's parent body and below).
Tested on: the pipeline's two-segment self-test model; D'Hondt et al. 2024's nominal 3- and 4-segment models.

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


class UnsupportedModel(SystemExit):
    """The model's foot is arranged in a way this adapter does not handle. Nothing was written."""


STATUS = ("experimental: simulated foot-to-ground contact through a virtual sole, not foot-insole contact inside "
          "a shoe; registration is approximate (see registration_residuals); not validated against measurements")


def _vec(p):
    return np.array([p.get(0), p.get(1), p.get(2)])


def _rot(R):
    return np.array([[R.get(i, j) for j in range(3)] for i in range(3)])


def foot_chain(model, side):
    """The foot's bodies from calcn_<s> to toes_<s>, following the joints, and the joints between them.

    Two-segment feet (calcn -> toes) and multi-segment ones (calcn -> midfoot -> forefoot -> toes, as in D'Hondt
    et al. 2024) both work. Anything else stops here rather than being simulated with the sole in the wrong place."""
    s = side.lower()
    bodies = model.getBodySet()
    if not (bodies.contains(f"calcn_{s}") and bodies.contains(f"toes_{s}")):
        raise UnsupportedModel(f"the model has no calcn_{s} and toes_{s}: this foot is not supported")
    into = {}
    for j in model.getJointSet():
        into[j.getChildFrame().findBaseFrame().getName()] = j
    chain, joints, b = [f"toes_{s}"], [], f"toes_{s}"
    while b != f"calcn_{s}":
        j = into.get(b)
        if j is None or len(chain) > 8:
            raise UnsupportedModel(f"toes_{s} is not reached from calcn_{s} through the model's joints: "
                                   f"this foot is not supported (chain so far: {chain[::-1]})")
        joints.append(j.getName())
        b = j.getParentFrame().findBaseFrame().getName()
        chain.append(b)
    return chain[::-1], joints[::-1]


def joint_motion(model, state, joint, calcn, step=1e-4):
    """How one joint of the foot chain moves, measured rather than assumed: its child frame is moved through a
    small step of the joint's coordinate at the default pose. Returns (kind, centre, axis) in the calcn frame:
    ("weld", centre, None) or ("rotation", centre, unit axis). Joints with more than one coordinate, with a
    translational coordinate, or whose rotation axis does not pass through the joint centre are refused."""
    import opensim as osim
    name = joint.getName()
    centre = _vec(joint.getChildFrame().findStationLocationInAnotherFrame(state, osim.Vec3(0, 0, 0), calcn))
    n = joint.numCoordinates()
    if n == 0:
        return "weld", centre, None
    if n != 1:
        raise UnsupportedModel(f"joint {name} in the foot chain has {n} coordinates: only single-axis joints "
                               f"(or welds) are supported")
    c = joint.get_coordinates(0)
    if c.getMotionType() != osim.Coordinate.Rotational:
        raise UnsupportedModel(f"joint {name}'s coordinate {c.getName()} is not rotational: not supported")
    q0 = c.getValue(state)

    def pose():
        model.realizePosition(state)
        X = joint.getChildFrame().findTransformBetween(state, calcn)
        return _rot(X.R()), _vec(X.p())
    R0, p0 = pose()
    c.setValue(state, q0 + step, False)
    R1, p1 = pose()
    c.setValue(state, q0, False)
    model.realizePosition(state)
    dR = R0.T @ R1                                            # the step's rotation, in the child frame
    angle = math.acos(max(-1.0, min(1.0, (np.trace(dR) - 1) / 2)))
    if abs(angle - step) > 0.02 * step:
        raise UnsupportedModel(f"joint {name}: a step of {step} rad in {c.getName()} rotates its child by {angle:.2e} "
                               f"rad; the joint is not a plain rotation about one axis")
    w = np.array([dR[2, 1] - dR[1, 2], dR[0, 2] - dR[2, 0], dR[1, 0] - dR[0, 1]]) / (2 * math.sin(angle))
    axis = R0 @ w
    if np.linalg.norm(p1 - p0) > 1e-7:
        raise UnsupportedModel(f"joint {name}: its centre moves by {np.linalg.norm(p1 - p0):.2e} m when "
                               f"{c.getName()} moves, so the rotation axis does not pass through the joint centre "
                               f"(or the joint translates): not supported")
    return "rotation", centre, axis / np.linalg.norm(axis)


def _boundary(kind, centre, axis):
    """Signed distance (m) of a point (X, Z) on the sole plane from a joint's boundary line, positive on the
    distal side. A rotation joint's line is its axis projected onto the plane, through the joint centre (a
    vertical plane containing the axis); a weld's is the line across the foot (along z) through its centre."""
    if kind == "weld":
        return lambda X, Z: X - centre[0]
    d = np.array([axis[0], axis[2]])
    if np.linalg.norm(d) < 0.3:
        raise UnsupportedModel("a foot joint axis is within 17 deg of vertical: no boundary line on the sole plane")
    d = d / np.linalg.norm(d)
    nrm = np.array([d[1], -d[0]])
    if nrm[0] < 0:
        nrm = -nrm
    if nrm[0] < 0.5:
        raise UnsupportedModel("a foot joint axis runs within 30 deg of the foot's long axis: its boundary line would "
                               "not separate proximal from distal")
    return lambda X, Z: nrm[0] * (X - centre[0]) + nrm[1] * (Z - centre[2])


def model_foot(model, side, state):
    """One foot's landmarks in the calcn frame, at the model's default pose: heel x, plantar height, the toe
    joint's centre and its measured rotation axis, and each segment boundary between calcn and the toes."""
    import opensim as osim
    s = side.lower()
    chain, joints = foot_chain(model, side)
    calcn = model.getBodySet().get(f"calcn_{s}")
    model.realizePosition(state)
    spheres = []
    for i in range(model.getContactGeometrySet().getSize()):
        g = model.getContactGeometrySet().get(i)
        base = g.getFrame().findBaseFrame().getName()
        if g.getConcreteClassName() == "ContactSphere" and base in chain:
            sp = osim.ContactSphere.safeDownCast(g)
            at = _vec(g.getFrame().findStationLocationInAnotherFrame(state, sp.get_location(), calcn))
            spheres.append((base, at, sp.getRadius()))
    on_calcn = [q for q in spheres if q[0] == f"calcn_{s}"]
    if not on_calcn:
        raise UnsupportedModel(f"no contact spheres on calcn_{s}: cannot find the heel and the plantar plane")
    heel = min(on_calcn, key=lambda q: q[1][0])
    heel_x = heel[1][0] - heel[2]
    plantar_y = float(np.mean([q[1][1] - q[2] for q in on_calcn]))
    motions = [joint_motion(model, state, model.getJointSet().get(jn), calcn) for jn in joints]
    kind, centre, axis = motions[-1]
    if kind != "rotation":
        raise UnsupportedModel(f"the joint into toes_{s} ({joints[-1]}) is a weld: there is no toe joint to register on")
    toe_line = _boundary(kind, centre, axis)                  # also checks the axis can be projected
    segments = [(body, k, c, a) for body, (k, c, a) in zip(chain[1:-1], motions[:-1])]
    pose = {}
    for jn in joints:
        j = model.getJointSet().get(jn)
        for k in range(j.numCoordinates()):
            c = j.get_coordinates(k)
            pose[c.getName()] = round(c.getValue(state), 6)
    return dict(heel_x=float(heel_x), plantar_y=plantar_y, mtp_point=centre, mtp_axis=axis, toe_line=toe_line,
                generic_spheres=spheres, chain=chain, joints=joints, segments=segments, pose=pose,
                motions={jn: dict(kind=k, centre_m=np.round(c, 5).tolist(),
                                  axis=None if a is None else np.round(a, 4).tolist())
                         for jn, (k, c, a) in zip(joints, motions)})


def _foot_subtree(model, chain):
    """The foot chain's parent body (usually the talus) and every body below it."""
    kids = {}
    for j in model.getJointSet():
        kids.setdefault(j.getParentFrame().findBaseFrame().getName(), []).append(j.getChildFrame().findBaseFrame().getName())
    parent = next(j.getParentFrame().findBaseFrame().getName() for j in model.getJointSet()
                  if j.getChildFrame().findBaseFrame().getName() == chain[0])
    start = chain[0] if parent == model.getGround().getName() else parent    # never the whole model
    out, todo = set(), [start]
    while todo:
        b = todo.pop()
        if b not in out:
            out.add(b)
            todo += kids.get(b, [])
    return out


def contact_inventory(model, model_path, chain, keep_generic):
    """What the sole will replace, checked so that nothing else is removed or left in a changed state.

    Every contact geometry on the foot (the chain's parent body and everything below it) must be a ContactSphere
    on a chain body used by exactly one force, a SmoothSphereHalfSpaceForce against one ContactHalfSpace on
    ground, and all those forces must share their contact parameters. Anything else stops here (UnsupportedModel)
    before the model is changed. Returns (forces, spheres, half-space name, parameters)."""
    import re
    import xml.etree.ElementTree as ET
    import opensim as osim
    subtree = _foot_subtree(model, chain)
    geo = {}
    for g in model.getContactGeometrySet():
        geo[g.getName()] = (g.getConcreteClassName(), g.getFrame().findBaseFrame().getName())
    foot_geo = {n: v for n, v in geo.items() if v[1] in subtree}
    # which force uses which geometry, read from the model file (covers every force type: contact geometry is
    # referenced by name or by path in the force's properties)
    refs = {}
    # OpenSim writes some nested set types with C++ scope in the tag (e.g. <HuntCrossleyForce::ContactParametersSet>),
    # which is not valid XML; only the text inside the elements matters here
    text = re.sub(r"(</?[A-Za-z_][\w.\-]*)::", r"\1__", Path(model_path).read_text(encoding="utf-8"))
    root = ET.fromstring(text)
    fset = root.find(".//ForceSet/objects")
    for f in (list(fset) if fset is not None else []):
        tokens = set()
        for e in f.iter():
            if e.text and e.text.strip():
                tokens |= set(re.split(r"[\s/]+", e.text.strip()))
        for n in geo:
            if n in tokens:
                refs.setdefault(n, []).append((f.tag, f.get("name")))
    problems = []
    for n, (cls, body) in (sorted(foot_geo.items()) if not keep_generic else []):
        users = refs.get(n, [])
        if cls != "ContactSphere":
            problems.append(f"{cls} '{n}' on {body}")
        elif body not in chain:
            problems.append(f"contact sphere '{n}' on {body}, outside the calcn-to-toes chain")
        elif not users:
            problems.append(f"contact sphere '{n}' on {body} is used by no force (it would be removed silently)")
        elif len(users) > 1 or any(t != "SmoothSphereHalfSpaceForce" for t, _ in users):
            problems.append(f"contact sphere '{n}' on {body} is used by {users} (only one SmoothSphereHalfSpaceForce "
                            f"is supported)")
    forces, spheres, halves, params = [], [], set(), {}
    for i in range(model.getForceSet().getSize()):
        fo = model.getForceSet().get(i)
        if fo.getConcreteClassName() != "SmoothSphereHalfSpaceForce":
            continue
        ss = osim.SmoothSphereHalfSpaceForce.safeDownCast(fo)
        sp = ss.getConnectee("sphere")
        if sp.getFrame().findBaseFrame().getName() not in chain:
            continue
        hs = ss.getConnectee("half_space")
        halves.add((hs.getName(), hs.getFrame().findBaseFrame().getName()))
        forces.append(fo.getName()); spheres.append(sp.getName())
        params[fo.getName()] = dict(
            stiffness=ss.get_stiffness(), dissipation=ss.get_dissipation(), static_friction=ss.get_static_friction(),
            dynamic_friction=ss.get_dynamic_friction(), viscous_friction=ss.get_viscous_friction(),
            transition_velocity=ss.get_transition_velocity(), constant_contact_force=ss.get_constant_contact_force(),
            hertz_smoothing=ss.get_hertz_smoothing(), hunt_crossley_smoothing=ss.get_hunt_crossley_smoothing())
    if not forces:
        problems.append("no SmoothSphereHalfSpaceForce on the foot: nothing to copy contact parameters from")
    if len(halves) > 1:
        problems.append(f"the foot's contact forces use more than one half-space: {sorted(halves)}")
    for hs, body in halves:
        if body != model.getGround().getName():
            problems.append(f"half-space '{hs}' is on {body}, not on ground")
    distinct = {json.dumps(p, sort_keys=True) for p in params.values()}
    if len(distinct) > 1:
        problems.append(f"the foot's contact forces have {len(distinct)} different parameter sets "
                        f"({sorted(params)}): one set cannot stand for all of them")
    if problems:
        raise UnsupportedModel("unsupported foot contact, nothing written:\n  - " + "\n  - ".join(problems))
    return forces, spheres, next(iter(halves))[0], next(iter(params.values()))


# --------------------------------------------------------------------------------------------- OpenSim
PERTURB_KEYS = ("scale", "lateral_mm", "pitch_deg", "boundary_mm", "stiffness")

# One assumed sole-contact model, used identically on every foot model in controlled comparisons. ASSUMED, NOT
# MEASURED: it stands in for the sole stack plus the plantar soft tissue until the coupon test gives a measured
# curve. Pressure on each sphere's grid cell follows p = pressure_kpa * (indentation / indentation_mm) ** 1.5 (the
# Hertz exponent). The per-sphere stiffness is calibrated numerically in OpenSim for that (calibrate_stiffness),
# so the assumed law is the same at any contact spacing. The smoothing is tightened from OpenSim's defaults
# (constant_contact_force 1e-5, hertz_smoothing 300), which act like a ~3 mm minimum indentation and let a sphere
# 2 mm above the floor carry a fifth of its 3 mm force; with these values the law is within ~1 % of Hertz from
# 1 mm indentation, and a sphere above the floor carries almost nothing. Dissipation and friction are the values
# the two-segment and D'Hondt models share.
ASSUMED_CONTACT_V1 = dict(
    name="assumed sole contact v1", status="assumed, not measured",
    pressure_kpa=100.0, indentation_mm=3.0,
    dissipation=2.0, static_friction=0.8, dynamic_friction=0.8, viscous_friction=0.5, transition_velocity=0.2,
    constant_contact_force=1e-8, hertz_smoothing=2000.0, hunt_crossley_smoothing=50.0)
_CONTACT_PARAMS = ("dissipation", "static_friction", "dynamic_friction", "viscous_friction", "transition_velocity",
                   "constant_contact_force", "hertz_smoothing", "hunt_crossley_smoothing")


def calibrate_stiffness(radius_m, force_n, indentation_m, params):
    """The SmoothSphereHalfSpaceForce stiffness at which one sphere of this radius, with these smoothing and
    friction parameters, pushes back with force_n at indentation_m at rest. Measured in OpenSim (the force is
    linear in stiffness, checked here) rather than taken from a formula."""
    import opensim as osim

    def unit(E):
        m = osim.Model(); g = m.getGround()
        b = osim.Body("b", 1.0, osim.Vec3(0), osim.Inertia(1e-3)); m.addBody(b)
        m.addJoint(osim.SliderJoint("j", g, osim.Vec3(0), osim.Vec3(0, 0, math.pi / 2), b, osim.Vec3(0),
                                    osim.Vec3(0, 0, math.pi / 2)))
        hs = osim.ContactHalfSpace(osim.Vec3(0), osim.Vec3(0, 0, -math.pi / 2), g, "floor"); m.addContactGeometry(hs)
        sp = osim.ContactSphere(radius_m, osim.Vec3(0), b, "s"); m.addContactGeometry(sp)
        f = osim.SmoothSphereHalfSpaceForce("c", sp, hs); f.set_stiffness(E)
        for k in _CONTACT_PARAMS:
            getattr(f, f"set_{k}")(params[k])
        m.addForce(f)
        st = m.initSystem(); c = m.getCoordinateSet().get(0)
        c.setValue(st, radius_m - indentation_m); m.realizeDynamics(st)
        lab, val = f.getRecordLabels(), f.getRecordValues(st)
        return [val.get(i) for i in range(lab.size()) if lab.get(i).endswith(".Sphere.force.Y")][0]
    f1, f2 = unit(1e6), unit(2e6)
    if abs(f2 / f1 - 2.0) > 1e-3:
        raise RuntimeError(f"contact force is not linear in stiffness here ({f1}, {f2}): cannot calibrate")
    return 1e6 * force_n / f1


def add_to_osim(model_path, sole_json, out_path, radius_mm=None, keep_generic=False, perturb=None, contact=None):
    """Write a copy of the model whose foot meets the ground through the sole's contact points. Experimental.

    perturb (sensitivity checks only): scale (factor on the registered scale), lateral_mm (shift of the sole along
    the calcn z axis), pitch_deg (tilt of the sole plane about the heel point, toe up for positive), boundary_mm
    (shift of every segment boundary and the toe line, for assigning points only), stiffness (factor)."""
    import opensim as osim
    if contact is not None:
        missing = {"pressure_kpa", "indentation_mm", *_CONTACT_PARAMS} - set(contact)
        if missing:
            raise ValueError(f"contact model lacks {sorted(missing)}")
    perturb = dict(perturb or {})
    bad = set(perturb) - set(PERTURB_KEYS)
    if bad:
        raise ValueError(f"unknown perturbation {sorted(bad)}; known: {PERTURB_KEYS}")
    sole = json.loads(Path(sole_json).read_text())
    side = sole["side"]; s = side.lower()
    model = osim.Model(str(model_path))
    state = model.initSystem()
    foot = model_foot(model, side, state)
    chain = foot["chain"]
    forces_old, spheres_old, hs_name, params = contact_inventory(model, model_path, chain, keep_generic)
    to_calcn, scale, mtp_x = register(sole, foot["heel_x"], foot["plantar_y"], foot["mtp_point"], foot["mtp_axis"])
    scale_used = scale * perturb.get("scale", 1.0)
    dz = perturb.get("lateral_mm", 0.0) / 1000.0
    tilt = math.tan(math.radians(perturb.get("pitch_deg", 0.0)))
    shift = perturb.get("boundary_mm", 0.0) / 1000.0
    r = (radius_mm if radius_mm else sole["point_spacing_mm"] / 2) / 1000.0
    calcn = model.getBodySet().get(f"calcn_{s}")
    bounds = [(b, _boundary(k, c, a)) for b, k, c, a in foot["segments"]]
    toe_line = foot["toe_line"]
    plan, conflicts_toe, conflicts_other, near = [], [], [], []
    for n, pts in sole["contact_points"].items():
        for k, (x, z) in enumerate(pts):
            X = foot["heel_x"] + scale_used * x / 1000.0
            Z = scale_used * z / 1000.0 + dz
            Y = foot["plantar_y"] + tilt * (X - foot["heel_x"])
            dt = toe_line(X, Z)
            if n.startswith("toe"):
                body = f"toes_{s}"
                if dt < 0:
                    conflicts_toe.append((n, k, round(-dt * 1000, 1)))
            else:
                body = f"calcn_{s}"
                for seg, fb in bounds:
                    if fb(X, Z) - shift > 0:
                        body = seg
                if dt > 0:
                    conflicts_other.append((n, k, round(dt * 1000, 1)))
            dmin = min([abs(dt)] + [abs(fb(X, Z)) for _, fb in bounds])
            if dmin < 0.005:
                near.append((n, k, round(dmin * 1000, 1)))
            at = calcn.findStationLocationInAnotherFrame(state, osim.Vec3(X, Y + r, Z), model.getBodySet().get(body))
            plan.append((n, k, body, _vec(at)))
    # residuals: how far the adapter's simplifications sit from the model's own foot (reported, not corrected)
    gen = foot["generic_spheres"]
    plane_mm = {}
    for b, at, rad in gen:
        plane_mm.setdefault(b, []).append(round(1000 * (at[1] - rad - foot["plantar_y"]), 2))
    ax = foot["mtp_axis"]
    toe_deg = math.degrees(math.atan2(ax[0], ax[2])) if ax[2] >= 0 else math.degrees(math.atan2(-ax[0], -ax[2]))
    bd = np.asarray(sole["bend"]["dir"], float)
    bend_deg = math.degrees(math.atan2(bd[0], bd[1])) if bd[1] >= 0 else math.degrees(math.atan2(-bd[0], -bd[1]))
    residuals = dict(
        note="reported, not corrected; small values here do not establish anatomical registration",
        generic_sphere_bottoms_vs_plane_mm=plane_mm,
        generic_calcn_sphere_z_mm=[round(1000 * at[2], 1) for b, at, rad in gen if b == f"calcn_{s}"],
        toe_axis_from_z_deg=round(toe_deg, 1), sole_bend_line_from_z_deg=round(bend_deg, 1),
        toe_points_proximal_of_toe_axis=conflicts_toe, other_points_distal_of_toe_axis=conflicts_other,
        points_within_5mm_of_a_boundary=near,
        joints=foot["motions"])
    if not keep_generic:                                      # replace exactly the inventoried contact, nothing else
        fs = model.getForceSet()
        for name in forces_old:
            fs.remove(fs.getIndex(name))
        cg = model.getContactGeometrySet()
        for name in spheres_old:
            cg.remove(cg.getIndex(name))
    # Keep the foot's overall contact stiffness: Hertz contact scales with sqrt(radius) per sphere, so n sole
    # spheres of radius r get stiffness k * (n_generic * sqrt(R_generic)) / (n * sqrt(r)). Otherwise 55 spheres with
    # the generic stiffness make the foot several times stiffer than the model it came from.
    n_sole = len(plan)
    if contact is None:                                 # native: the model's own contact, overall stiffness kept
        k_scale = (sum(math.sqrt(q[2]) for q in gen) / (n_sole * math.sqrt(r))) if gen else 1.0
        params = dict(params)
        params["stiffness"] = params["stiffness"] * k_scale * perturb.get("stiffness", 1.0)
        contact_model = dict(name="native", status="the model's own generic contact parameters (incl. its smoothing), "
                             "stiffness scaled so the sole keeps the generic foot's overall contact stiffness")
    else:                                               # one assumed law for every model
        k_scale = None
        cell_m2 = (sole["point_spacing_mm"] * scale_used / 1000.0) ** 2
        force = contact["pressure_kpa"] * 1000.0 * cell_m2
        params = {k: contact[k] for k in _CONTACT_PARAMS}
        params["stiffness"] = calibrate_stiffness(r, force, contact["indentation_mm"] / 1000.0, params) * perturb.get("stiffness", 1.0)
        contact_model = dict(contact, cell_area_mm2=round(cell_m2 * 1e6, 3), force_per_sphere_at_reference_N=round(force, 4))
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
    meta = dict(status=STATUS, model=str(out_path), source_model=str(model_path), sole=sole["board_id"], side=side,
                scale=round(scale, 4), scale_used=round(scale_used, 4), perturbation=perturb, warning=warn,
                spheres=len(placed), radius_m=r, replaced_generic=not keep_generic,
                replaced_forces=forces_old if not keep_generic else [],
                replaced_spheres=spheres_old if not keep_generic else [],
                contact_model=contact_model,
                stiffness_scale=None if k_scale is None else round(k_scale, 4), stiffness_per_sphere=params["stiffness"],
                registration=dict(heel_x=foot["heel_x"], plantar_y=foot["plantar_y"],
                                  mtp_point=foot["mtp_point"].tolist(), mtp_axis=np.round(foot["mtp_axis"], 4).tolist()),
                registration_residuals=residuals,
                regions={n: sum(1 for p in placed if p["region"] == n) for n in sole["contact_points"]},
                on_toes=sorted({p["region"] for p in placed if p["body"].startswith("toes")}),
                foot_chain=chain, toe_joint=foot["joints"][-1], pose=foot["pose"],
                spheres_per_body={b: sum(1 for p in placed if p["body"] == b) for b in chain},
                replaced_generic_on=sorted({q[0] for q in gen}) if not keep_generic else [])
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


def sphere_centre_of_pressure(head, data, sole):
    """Centre of pressure in the sole frame (mm) from each sphere's vertical force at its own contact point: finer
    than the region centroids of centre_of_pressure()."""
    s = sole["side"].lower()
    num, tot = np.zeros((len(data), 2)), np.zeros(len(data))
    for n, pts in sole["contact_points"].items():
        for k, (x, z) in enumerate(pts):
            pre = f"force_sole_{s}_{n}_{k:02d}."
            col = [i for i, h in enumerate(head) if h.startswith(pre) and h.lower().endswith(".sphere.force.y")]
            if len(col) != 1:
                raise ValueError(f"expected one force column {pre}Sphere.force.Y, found {len(col)}")
            f = np.clip(data[:, col[0]], 0, None)
            num += f[:, None] * np.array([x, z]); tot += f
    with np.errstate(invalid="ignore", divide="ignore"):
        return num / tot[:, None], tot


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("export"); e.add_argument("board_json"); e.add_argument("--map"); e.add_argument("-o", required=True)
    e.add_argument("--spacing", type=float, default=15.0)
    o = sub.add_parser("osim"); o.add_argument("model"); o.add_argument("sole_json"); o.add_argument("-o", required=True)
    o.add_argument("--radius-mm", type=float); o.add_argument("--keep-generic", action="store_true")
    o.add_argument("--contact", choices=["native", "assumed-v1"], default="native",
                   help="native: the model's own contact (default); assumed-v1: ASSUMED_CONTACT_V1, assumed, not measured")
    o.add_argument("--perturb", action="append", default=[], metavar="KEY=VALUE",
                   help=f"sensitivity checks only; keys {', '.join(PERTURB_KEYS)}")
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
        pert = {k: float(v) for k, v in (kv.split("=", 1) for kv in a.perturb)}
        try:
            meta = add_to_osim(a.model, a.sole_json, a.o, a.radius_mm, a.keep_generic, pert,
                               ASSUMED_CONTACT_V1 if a.contact == "assumed-v1" else None)
        except UnsupportedModel as e:
            raise SystemExit(f"refused: {e}")
        print(json.dumps(meta, indent=1, default=float))
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
