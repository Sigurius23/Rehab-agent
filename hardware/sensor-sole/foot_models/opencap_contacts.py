#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors
# SPDX-License-Identifier: CERN-OHL-S-2.0
"""Foot contact spheres added to an OpenCap scaled model by OpenCap's own rule (VALIDATION_PLAN.md, stage A,
amendment 1 to the "Model" rule).

The rule is `generate_model_with_contacts` in opencap-processing's `utilsProcessing.py`, at commit
72b5416bf6172fe3d9b42b01e1a02252362b20fc (Apache-2.0; Falisse and Uhlrich). This file re-implements it, rather than
calling it, because the function expects OpenCap's folder layout and an "_adjusted" model:
  - the same six reference spheres per foot (radius 0.032 m) on calcn and toes;
  - each location divided by (reference scale factor / the body's first attached geometry's scale factors), with the
    y factor set to 1, so the height is not scaled;
  - one ground half-space named "floor" (orientation 0, 0, -pi/2), with the function's contact parameters;
  - the same object names, so the result can be compared with the function's own output file.
Unlike the function, the patella masses are left as they are, and a model that already has contact geometry is
refused (the spheres would be added twice).

In this project the spheres only locate the sole (sole_sim.add_to_osim: heel point and plantar plane); the sole
then replaces them, with its own contact law, so the contact parameters here do not enter the results.

  python foot_models/opencap_contacts.py MODEL_scaled.osim OUT.osim
  python foot_models/opencap_contacts.py MODEL_scaled.osim OUT.osim --check-against utilsProcessing.py
      also runs OpenCap's function itself on a copy of the model, in the folder layout it expects, and checks that
      the two models' spheres, half-space and contact forces agree (locations to 1e-9 m)
"""
import argparse
import ast
import json
import math
import shutil
import sys
import tempfile
from pathlib import Path

SOURCE = dict(repository="https://github.com/stanfordnmbl/opencap-processing", file="utilsProcessing.py",
              function="generate_model_with_contacts", commit="72b5416bf6172fe3d9b42b01e1a02252362b20fc",
              licence="Apache-2.0")
# Copied from the function at that commit (values as written there).
REFERENCE_SPHERES = {
    "s1_r": (0.032, (0.0019011578840796601, -0.01, -0.00382630379623308), "calcn_r"),
    "s2_r": (0.032, (0.14838639994206301, -0.01, -0.028713422052654002), "calcn_r"),
    "s3_r": (0.032, (0.13300117060705099, -0.01, 0.051636247344956601), "calcn_r"),
    "s4_r": (0.032, (0.066234666199163503, -0.01, 0.026364160674169801), "calcn_r"),
    "s5_r": (0.032, (0.059999999999999998, -0.01, -0.018760308461917698), "toes_r"),
    "s6_r": (0.032, (0.044999999999999998, -0.01, 0.061856956754965199), "toes_r"),
    "s1_l": (0.032, (0.0019011578840796601, -0.01, 0.00382630379623308), "calcn_l"),
    "s2_l": (0.032, (0.14838639994206301, -0.01, 0.028713422052654002), "calcn_l"),
    "s3_l": (0.032, (0.13300117060705099, -0.01, -0.051636247344956601), "calcn_l"),
    "s4_l": (0.032, (0.066234666199163503, -0.01, -0.026364160674169801), "calcn_l"),
    "s5_l": (0.032, (0.059999999999999998, -0.01, 0.018760308461917698), "toes_l"),
    "s6_l": (0.032, (0.044999999999999998, -0.01, -0.061856956754965199), "toes_l"),
}
REFERENCE_SCALE = 0.91392399999999996          # the same for calcn and toes, both sides, all three axes
HALF_SPACE = dict(name="floor", location=(0.0, 0.0, 0.0), orientation=(0.0, 0.0, -math.pi / 2))
CONTACT = dict(stiffness=1000000, dissipation=2.0, static_friction=0.8, dynamic_friction=0.8, viscous_friction=0.5,
               transition_velocity=0.2)


def sphere_locations(geometry_scale):
    """{sphere: (body, radius, location)} for the given {body: (sx, sy, sz)} of each foot body's first attached
    geometry, by the function's arithmetic: location / (reference / geometry), y factor 1."""
    out = {}
    for name, (radius, loc, body) in REFERENCE_SPHERES.items():
        f = [REFERENCE_SCALE / g for g in geometry_scale[body]]
        f[1] = 1.0
        out[name] = (body, radius, tuple(v / k for v, k in zip(loc, f)))
    return out


def add_contacts(model_in, model_out):
    """Write model_out: model_in with the spheres, the half-space and their forces. Returns a record."""
    import opensim as osim
    model = osim.Model(str(model_in))
    if model.getContactGeometrySet().getSize():
        raise ValueError(f"{model_in}: already has contact geometry; refusing to add OpenCap's spheres twice")
    bodies = model.getBodySet()
    scale = {}
    for b in sorted({body for _, _, body in REFERENCE_SPHERES.values()}):
        if not bodies.contains(b):
            raise ValueError(f"{model_in}: no body {b}")
        if bodies.get(b).getPropertyByName("attached_geometry").size() < 1:
            raise ValueError(f"{model_in}: body {b} has no attached geometry, whose scale factors the rule uses")
        v = bodies.get(b).get_attached_geometry(0).get_scale_factors()
        scale[b] = (v.get(0), v.get(1), v.get(2))
    ground = model.get_ground()
    hs = osim.ContactHalfSpace(osim.Vec3(*HALF_SPACE["location"]), osim.Vec3(*HALF_SPACE["orientation"]), ground,
                               HALF_SPACE["name"])
    hs.connectSocket_frame(ground)
    model.addContactGeometry(hs)
    spheres = sphere_locations(scale)
    for name, (body, radius, loc) in spheres.items():
        b = bodies.get(body)
        sp = osim.ContactSphere(radius, osim.Vec3(*loc), b, name)
        sp.connectSocket_frame(b)
        model.addContactGeometry(sp)
        fo = osim.SmoothSphereHalfSpaceForce("SmoothSphereHalfSpaceForce_" + name, sp, hs)
        for k, v in CONTACT.items():
            getattr(fo, f"set_{k}")(v)
        fo.connectSocket_half_space(hs)
        fo.connectSocket_sphere(sp)
        model.addForce(fo)
    model.finalizeConnections()
    model.initSystem()
    model.printToXML(str(model_out))
    return dict(source=SOURCE, model_in=str(model_in), model_out=str(model_out), geometry_scale_factors=scale,
                spheres={n: dict(body=b, radius_m=r, location_m=list(l)) for n, (b, r, l) in spheres.items()})


def read_contacts(path):
    """Spheres, half-spaces and sphere forces of a model file, for comparison."""
    import opensim as osim
    m = osim.Model(str(path))
    geo, forces = {}, {}
    for i in range(m.getContactGeometrySet().getSize()):
        g = m.getContactGeometrySet().get(i)
        loc, ori = g.get_location(), g.get_orientation()
        rec = dict(kind=g.getConcreteClassName(), frame=g.getFrame().getName(),
                   location=[loc.get(k) for k in range(3)], orientation=[ori.get(k) for k in range(3)])
        if rec["kind"] == "ContactSphere":
            rec["radius"] = osim.ContactSphere.safeDownCast(g).getRadius()
        geo[g.getName()] = rec
    for i in range(m.getForceSet().getSize()):
        f = m.getForceSet().get(i)
        if f.getConcreteClassName() == "SmoothSphereHalfSpaceForce":
            s = osim.SmoothSphereHalfSpaceForce.safeDownCast(f)
            forces[f.getName()] = dict(sphere=f.getSocket("sphere").getConnecteePath(),
                                       half_space=f.getSocket("half_space").getConnecteePath(),
                                       **{k: getattr(s, f"get_{k}")() for k in CONTACT})
    masses = {m.getBodySet().get(i).getName(): m.getBodySet().get(i).getMass() for i in range(m.getBodySet().getSize())}
    return geo, forces, masses


def run_opencap_function(utils_py, model_in, work):
    """OpenCap's own function, taken from its source file without importing the module (which pulls in plotting
    and API helpers), run on a copy of the model in the layout it expects. Patella masses left as they are."""
    import numpy as np
    import opensim
    import os
    tree = ast.parse(Path(utils_py).read_text())
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == SOURCE["function"])
    ns = dict(os=os, np=np, opensim=opensim)
    exec(compile(ast.Module(body=[fn], type_ignores=[]), str(utils_py), "exec"), ns)
    stem = Path(model_in).name[:-len("_scaled.osim")]
    folder = Path(work) / "subject" / "OpenSimData" / "Model"
    folder.mkdir(parents=True)
    shutil.copyfile(model_in, folder / f"{stem}_scaled_adjusted.osim")
    ns[SOURCE["function"]](str(work), "subject", OpenSimModel=stem, setPatellaMasstoZero=False, contact_side="all",
                           overwrite=True)
    return folder / f"{stem}_scaled_adjusted_contacts.osim"


def compare(ours, theirs, tol=1e-9):
    """Differences between two models' contacts and body masses (empty if they agree)."""
    (ga, fa, ma), (gb, fb, mb) = read_contacts(ours), read_contacts(theirs)
    diff = []
    if set(ga) != set(gb) or set(fa) != set(fb) or set(ma) != set(mb):
        diff.append(("names differ", sorted(set(ga) ^ set(gb)), sorted(set(fa) ^ set(fb)), sorted(set(ma) ^ set(mb))))
    for n in set(ga) & set(gb):
        a, b = ga[n], gb[n]
        for k in a:
            if isinstance(a[k], list):
                d = max(abs(x - y) for x, y in zip(a[k], b[k]))
                if d > tol:
                    diff.append((n, k, d))
            elif isinstance(a[k], float):
                if abs(a[k] - b[k]) > tol:
                    diff.append((n, k, a[k], b[k]))
            elif a[k] != b[k]:
                diff.append((n, k, a[k], b[k]))
    for n in set(fa) & set(fb):
        if fa[n] != fb[n]:
            diff.append((n, fa[n], fb[n]))
    for n in set(ma) & set(mb):
        if ma[n] != mb[n]:
            diff.append((n, "mass", ma[n], mb[n]))
    return diff


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("model"); ap.add_argument("out")
    ap.add_argument("--check-against", metavar="utilsProcessing.py",
                    help="OpenCap's source file at the commit above; runs its function and compares")
    a = ap.parse_args()
    rec = add_contacts(a.model, a.out)
    if a.check_against:
        with tempfile.TemporaryDirectory() as d:
            theirs = run_opencap_function(a.check_against, a.model, d)
            diff = compare(a.out, theirs)
            spheres = sum(1 for g in read_contacts(theirs)[0].values() if g["kind"] == "ContactSphere")
        rec["check_against_opencap"] = dict(spheres_compared=spheres, tolerance_m=1e-9, agree=not diff,
                                            differences=[list(map(str, x)) for x in diff])
    print(json.dumps(rec, indent=1))
    if a.check_against and diff:
        sys.exit("our model and OpenCap's function's model differ")


if __name__ == "__main__":
    main()
