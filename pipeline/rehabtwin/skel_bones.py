"""Bones from body shape: SKEL's anatomical joint centres for a person's body (layer 1, bone geometry; Tier C).

SKEL (Keller et al., SIGGRAPH Asia 2023, skel.is.tue.mpg.de) is a body model whose skin is SMPL and whose
skeleton is the BSM OpenSim model (a Rajagopal-based full-body model). It regresses the BSM joint centres
linearly from the SMPL body surface in its rest pose:

    J = J_regressor_osim · v_shaped        (24 body origins: pelvis, femur_r, tibia_r, ..., hand_l)

So any body surface in SMPL topology gives a skeleton. This module turns that into what the person model
stores (``rehabtwin person bones``):

- **Surface:** an SMPL body of the person's sex fitted to their Kinect depth (``person shape --smpl-model``).
  Without one, ``betas_for_height_mass`` gives the SMPL body closest to the mean shape with the measured height
  and mass. An SMPL-X fit is not converted: carrying SMPL-X bodies over to SMPL through a surface
  correspondence made them 4-8 cm taller in tests, so the surface is fitted with SMPL itself.
- **Segment lengths** between SKEL joint centres, and from them per-body scale factors for the generic OpenSim
  model (``scale_set``). The groups mirror the video measurement set (configs ``scaling.measurements``): femur
  and tibia per side, foot, pelvis depth/height and width, trunk height and shoulder width, upper arm, forearm.
  The generic model's lengths are the same joint-centre distances in its default pose.

What it is and is not:
- **A population prior from the surface, not imaging.** SKEL's regressor was learned from other people's
  data; nothing here sees this person's bone. A person with a long femur and a short shank for their surface
  gets the average split. The layer stays Tier C.
- **SKEL is male or female** (no neutral model); the person's recorded sex picks it.
- **Only lengths are transferred.** Bone shapes, joint axes and muscle paths stay the generic model's, scaled.

The model files are licensed separately (non-commercial research; skel.is.tue.mpg.de, smpl.is.tue.mpg.de) and
stay outside the repository. They come as Python pickles: convert them once with
``adapters/body_model_files.py`` and load only the resulting .npz (no pickle).
"""
from __future__ import annotations

import numpy as np
from scipy.optimize import least_squares

SKEL_KEYS = ("J_regressor_osim", "bone_names", "skin_template_v", "skin_template_f", "shapedirs")
SMPL_KEYS = ("v_template", "shapedirs", "f")
SIDES = ("r", "l")
LATERAL = {"smpl": 0, "opensim": 2}          # SMPL/SKEL: x to the body's left, y up, z forward; OpenSim: z right
DENSITY = 1000.0                             # kg/m^3, as rehabtwin.shape: mass from volume is an estimate
TRUNK = ("torso", "lumbar1", "lumbar2", "lumbar3", "lumbar4", "lumbar5", "Abdomen", "head", "sacrum")
# measurement -> {body: axes}, as configs' scaling.measurements (video) assign them
GROUPS = {"femur_r": {"femur_r": "XYZ", "patella_r": "XYZ"}, "femur_l": {"femur_l": "XYZ", "patella_l": "XYZ"},
          "tibia_r": {"tibia_r": "XYZ"}, "tibia_l": {"tibia_l": "XYZ"},
          "foot": {f"{b}_{s}": "XYZ" for b in ("talus", "calcn", "toes") for s in SIDES},
          "pelvisXY": {"pelvis": "XY"}, "pelvisZ": {"pelvis": "Z"},
          "torsoXY": dict.fromkeys(TRUNK, "XY"), "torsoZ": dict.fromkeys(TRUNK, "Z"),
          "humerus": {"humerus_r": "XYZ", "humerus_l": "XYZ"},
          "radius": {f"{b}_{s}": "XYZ" for b in ("ulna", "radius", "hand") for s in SIDES}}
# the person model's joint-centre segments (rehabtwin/person.py JOINT_SEGMENTS) as SKEL bone pairs
SEGMENTS = {"thigh_r": ("femur_r", "tibia_r"), "thigh_l": ("femur_l", "tibia_l"),
            "shank_r": ("tibia_r", "talus_r"), "shank_l": ("tibia_l", "talus_l"),
            "upper_arm_r": ("humerus_r", "ulna_r"), "upper_arm_l": ("humerus_l", "ulna_l"),
            "forearm_r": ("ulna_r", "hand_r"), "forearm_l": ("ulna_l", "hand_l"),
            "hip_width": ("femur_r", "femur_l")}


def _load(path, keys, what):
    m = np.load(path, allow_pickle=False)
    missing = [k for k in keys if k not in m.files]
    if missing:
        raise ValueError(f"{path}: not a converted {what} model (missing {missing}); convert the downloaded "
                         "pickle with adapters/body_model_files.py")
    return {k: m[k] for k in m.files}


def load_skel(path):
    """A SKEL model converted to .npz (skel_male.npz / skel_female.npz)."""
    return _load(path, SKEL_KEYS, "SKEL")


def load_smpl(path):
    """An SMPL model converted to .npz (basicmodel_{f,m}_lbs_10_207_0_v1.1.0.npz)."""
    return _load(path, SMPL_KEYS, "SMPL")


def rest_surface(smpl, betas):
    """SMPL rest-pose vertices (6890, 3) for shape parameters ``betas``."""
    b = np.asarray(betas, float)
    return smpl["v_template"] + smpl["shapedirs"][:, :, :len(b)] @ b


def joints(skel, vertices):
    """{SKEL bone: joint centre (3,)}: the BSM body origins regressed from an SMPL-topology rest surface."""
    v = np.asarray(vertices, float)
    if v.shape != skel["skin_template_v"].shape:
        raise ValueError(f"surface has {v.shape[0]} vertices; SKEL needs SMPL topology ({len(skel['skin_template_v'])})")
    J = skel["J_regressor_osim"] @ v
    return {str(n): J[i] for i, n in enumerate(skel["bone_names"])}


def _without(vec, axis):
    out = np.array(vec, float)
    out[axis] = 0.0
    return out


def measures(P, frame="smpl"):
    """{measurement: m} of GROUPS from joint centres ``P`` ({body: (3,)}; SKEL bones or OpenSim body origins).

    Lengths between joint centres; pelvisXY and torsoXY leave out the lateral component (the video set
    measures them front to back and top to bottom)."""
    lat = LATERAL[frame]
    d = lambda a, b: float(np.linalg.norm(np.asarray(P[a]) - np.asarray(P[b])))
    mid = (np.asarray(P["humerus_r"]) + np.asarray(P["humerus_l"])) / 2
    return {"femur_r": d("femur_r", "tibia_r"), "femur_l": d("femur_l", "tibia_l"),
            "tibia_r": d("tibia_r", "talus_r"), "tibia_l": d("tibia_l", "talus_l"),
            "foot": float(np.mean([d(f"talus_{s}", f"toes_{s}") for s in SIDES])),
            "pelvisXY": float(np.mean([np.linalg.norm(_without(np.asarray(P[f"femur_{s}"]) - P["pelvis"], lat))
                                       for s in SIDES])),
            "pelvisZ": d("femur_r", "femur_l"),
            "torsoXY": float(np.linalg.norm(_without(mid - np.asarray(P["pelvis"]), lat))),
            "torsoZ": d("humerus_r", "humerus_l"),
            "humerus": float(np.mean([d(f"humerus_{s}", f"ulna_{s}") for s in SIDES])),
            "radius": float(np.mean([d(f"ulna_{s}", f"hand_{s}") for s in SIDES]))}


def segment_lengths(P):
    """{person-model joint segment: m} (thigh, shank, upper arm, forearm per side; hip width)."""
    return {k: float(np.linalg.norm(np.asarray(P[a]) - np.asarray(P[b]))) for k, (a, b) in SEGMENTS.items()}


def scale_set(person_measures, generic_measures):
    """{body: [sx, sy, sz]} for the generic OpenSim model: each GROUPS measurement's ratio on its bodies' axes."""
    out = {}
    for name, bodies in GROUPS.items():
        k = person_measures[name] / generic_measures[name]
        for body, axes in bodies.items():
            f = out.setdefault(body, [1.0, 1.0, 1.0])
            for ax in axes:
                f["XYZ".index(ax)] = round(float(k), 5)
    return out


def generic_origins(model_path):
    """{body: origin (3,)} of an OpenSim model in its default pose (ground frame)."""
    from .opensim_stage import _osim
    osim = _osim()
    model = osim.Model(str(model_path))
    state = model.initSystem()
    bodies = model.getBodySet()
    out = {}
    for i in range(bodies.getSize()):
        p = bodies.get(i).getPositionInGround(state)
        out[bodies.get(i).getName()] = np.array([p.get(0), p.get(1), p.get(2)])
    return out


def scale_model(generic_model_path, factors, mass_kg, out_path):
    """Write the generic model scaled by ``factors`` ({body: [sx, sy, sz]}), segment masses scaled to ``mass_kg``
    with the generic distribution kept (as OpenSim's ScaleTool with manual scale factors does)."""
    from .opensim_stage import _osim
    osim = _osim()
    model = osim.Model(str(generic_model_path))
    state = model.initSystem()
    ss = osim.ScaleSet()
    for body, f in factors.items():
        if not model.getBodySet().contains(body):
            continue
        s = osim.Scale()
        s.setSegmentName(body)
        s.setScaleFactors(osim.Vec3(*[float(x) for x in f]))
        s.setApply(True)
        ss.cloneAndAppend(s)
    if not model.scale(state, ss, True, float(mass_kg)):
        raise RuntimeError(f"OpenSim could not scale {generic_model_path}")
    model.printToXML(str(out_path))


# ---- a body of a given height and mass -------------------------------------------------------------------

def body_measures(v, faces, density=DENSITY):
    """(height m, mass kg from the mesh volume) of a rest-pose body standing along +y."""
    a, b, c = v[faces[:, 0]], v[faces[:, 1]], v[faces[:, 2]]
    vol = abs(float(np.einsum("ij,ij->i", a, np.cross(b, c)).sum())) / 6.0
    return float(v[:, 1].max() - v[:, 1].min()), vol * density


def betas_for_height_mass(smpl, height_m, mass_kg, n_betas=10, height_sd_m=0.002, mass_sd_kg=0.2):
    """The SMPL body nearest the mean shape (in the shape space's own units) with this height and mass from
    volume: a body-size prior when no surface was measured."""
    faces = np.asarray(smpl["f"])

    def res(b):
        h, m = body_measures(rest_surface(smpl, b), faces)
        return np.concatenate([[(h - height_m) / height_sd_m, (m - mass_kg) / mass_sd_kg], b])
    sol = least_squares(res, np.zeros(n_betas), x_scale=1.0)
    h, m = body_measures(rest_surface(smpl, sol.x), faces)
    if abs(h - height_m) > 0.01 or abs(m - mass_kg) > 0.02 * mass_kg:
        raise ValueError(f"no SMPL body near the mean shape has {height_m} m and {mass_kg} kg (best {h:.3f} m, {m:.1f} kg)")
    return sol.x, {"height_m": round(h, 4), "mass_kg": round(m, 2)}
