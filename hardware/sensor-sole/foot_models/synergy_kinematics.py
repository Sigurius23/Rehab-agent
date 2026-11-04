#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors
# SPDX-License-Identifier: CERN-OHL-S-2.0
"""The sole on the Synergy-Based Foot Model (Conconi, Modenese et al., submitted): a kinematic comparison. Experimental.

The model (github.com/modenaxe/synergy-based-foot-model-opensim, Apache-2.0) has 19 bones, the five toes among
them, moved by five coupled synergy gains, and no muscles, ligaments or contact. So there is no load here: this
asks how the sole's regions would move with the bones under them.

Registration, from bone landmarks (the model has no contact spheres to register on, unlike the other models):
  - heel point: the most posterior point of the calcaneus (CA) on the plantar plane;
  - plantar plane: through the lowest points of the calcaneus and of the first and fifth metatarsal heads;
  - long axis: heel towards the second metatarsal head, in that plane;
  - toe-joint line: a line fitted through the five metatarsophalangeal joint centres; the sole's bend line goes
    on it at the long axis, and that sets the scale (as in sole_sim.register).
Each sole point goes on the lowest bone within 5 mm of it, seen from below; otherwise it is "no bone" (soft
tissue only, e.g. under the medial arch). Then each synergy gain is swept across its coordinate range, and across a
small band (neutral +/- 10 % of that range), with the others at their neutral values, and for every region the motion relative to the calcaneus, the stretch of the
sole between neighbouring points on different bones, and each toe's rotation relative to its metatarsal are
measured.

What this is not: a contact or load simulation; a measured motion (the synergies are the model's, from its
authors' data, swept over coordinate ranges, not over a recorded movement); or a fit to any person's foot.

  python foot_models/synergy_kinematics.py synergy_foot_r.osim sim/EU42_R_636645a928.sole_sim.json -o out.json
"""
import argparse
import json
import struct
from pathlib import Path

import numpy as np

TOES = [f"T{i}_r" for i in range(1, 6)]
METATARSALS = [f"M{i}_r" for i in range(1, 6)]


def stl_vertices(path):
    b = Path(path).read_bytes()
    n = struct.unpack("<I", b[80:84])[0]
    a = np.frombuffer(b[84:84 + 50 * n], dtype=np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")]))
    return np.unique(a["v"].reshape(-1, 3), axis=0).astype(float)


def _vec(p):
    return np.array([p.get(0), p.get(1), p.get(2)])


def bone_vertices(model, state, geom_dir, step=7):
    """Ground coordinates of a subsample of each bone's mesh vertices, and the bone-frame coordinates."""
    import opensim as osim
    out = {}
    for b in model.getBodySet():
        for i in range(b.getPropertyByName("attached_geometry").size()):
            g = osim.Mesh.safeDownCast(b.get_attached_geometry(i))
            if g is None:
                continue
            sf = _vec(g.get_scale_factors())
            local = stl_vertices(Path(geom_dir) / g.get_mesh_file())[::step] * sf
            X = b.getTransformInGround(state)
            R = np.array([[X.R().get(r, c) for c in range(3)] for r in range(3)]); p = _vec(X.p())
            out[b.getName()] = dict(local=local, ground=local @ R.T + p)
    return out


def foot_frame(verts, mtp_centres):
    """Heel point, unit axes x (long), y (plantar normal, up), z (x cross y; right for a right foot), in ground."""
    ca = verts["CA_r"]["ground"]; m2 = verts["M2_r"]["ground"]; ti = verts["TI_r"]["ground"]
    c_ca = ca.mean(0)
    p_m2 = m2[np.argmax(np.linalg.norm(m2 - c_ca, axis=1))]
    long0 = (p_m2 - c_ca) / np.linalg.norm(p_m2 - c_ca)
    tib = ti[np.argmax(np.linalg.norm(ti - c_ca, axis=1))] - c_ca               # towards the knee
    up0 = tib - tib.dot(long0) * long0; up0 /= np.linalg.norm(up0)
    low = lambda v: v[np.argmin(v @ up0)]
    distal = lambda name: verts[name]["ground"][(verts[name]["ground"] - c_ca) @ long0 >
                                                np.percentile((verts[name]["ground"] - c_ca) @ long0, 60)]
    heel_low, m1, m5 = low(ca), low(distal("M1_r")), low(distal("M5_r"))
    y = np.cross(m1 - heel_low, m5 - heel_low); y /= np.linalg.norm(y)
    if y.dot(up0) < 0:
        y = -y
    x = (p_m2 - heel_low) - (p_m2 - heel_low).dot(y) * y; x /= np.linalg.norm(x)
    z = np.cross(x, y)
    heel = ca[np.argmin((ca - heel_low) @ x)]
    heel = heel - (heel - heel_low).dot(y) * y                                 # on the plantar plane
    plane = (heel_low, y)
    return dict(heel=heel, x=x, y=y, z=z, plane_point=heel_low, tripod=dict(heel=heel_low, mt1=m1, mt5=m5))


def register(sole, F, mtp_centres):
    """Scale from the MTP line (fitted through the joint centres, in the plantar plane) at the long axis."""
    pts = np.array([[(c - F["heel"]).dot(F["x"]), (c - F["heel"]).dot(F["z"])] for c in mtp_centres.values()])
    slope, x0 = np.polyfit(pts[:, 1], pts[:, 0], 1)                             # x = x0 + slope * z
    bp, bd = np.asarray(sole["bend"]["point"], float), np.asarray(sole["bend"]["dir"], float)
    bend_x0 = bp[0] - bp[1] * bd[0] / bd[1]
    scale = x0 / (bend_x0 / 1000.0)
    return scale, dict(mtp_line_x0_mm=round(1000 * x0, 1), mtp_line_angle_deg=round(float(np.degrees(np.arctan(slope))), 1),
                       mtp_centres_mm={k: np.round(1000 * v, 1).tolist() for k, v in zip(mtp_centres, pts)})


def analyse(model_path, sole_json, radius_mm=5.0, steps=9):
    import opensim as osim
    sole = json.loads(Path(sole_json).read_text())
    if sole["side"] != "R":
        raise SystemExit("this script handles the right foot (synergy_foot_r.osim)")
    m = osim.Model(str(model_path))
    st = m.initSystem(); m.realizePosition(st)
    geom = Path(model_path).parent / "Geometry"
    verts = bone_vertices(m, st, geom)
    mtp = {}
    for j in m.getJointSet():
        ch = j.getChildFrame().findBaseFrame().getName()
        if ch in TOES:
            mtp[ch] = _vec(j.getChildFrame().findStationLocationInGround(st, osim.Vec3(0, 0, 0)))
    F = foot_frame(verts, mtp)
    scale, reg = register(sole, F, mtp)
    to_ground = lambda x, z: F["heel"] + scale * (x * F["x"] + z * F["z"]) / 1000.0
    # which bone each sole point lies under
    under = {}
    for b, v in verts.items():
        if b.startswith(("virtual", "TI", "FI")):
            continue
        rel = v["ground"] - F["plane_point"]
        under[b] = (np.stack([(v["ground"] - F["heel"]) @ F["x"], (v["ground"] - F["heel"]) @ F["z"]], 1), rel @ F["y"])
    assign, clearance = {}, {}
    pts = []
    for n, P in sole["contact_points"].items():
        for k, (x, z) in enumerate(P):
            g = to_ground(x, z)
            q = np.array([(g - F["heel"]) @ F["x"], (g - F["heel"]) @ F["z"]])
            best = None
            for b, (xz, h) in under.items():
                near = np.linalg.norm(xz - q, axis=1) < radius_mm / 1000.0
                if near.any():
                    hb = h[near].min()
                    if best is None or hb < best[1]:
                        best = (b, hb)
            bone = best[0] if best else None
            assign[(n, k)] = bone
            clearance[(n, k)] = None if best is None else round(1000 * best[1], 1)
            pts.append((n, k, g, bone))
    region_bones = {}
    for (n, k), b in assign.items():
        region_bones.setdefault(n, {}).setdefault(b or "no bone", 0)
        region_bones[n][b or "no bone"] += 1
    # each point in its bone's frame at the neutral pose
    local = {}
    for n, k, g, b in pts:
        if b:
            X = m.getBodySet().get(b).getTransformInGround(st)
            R = np.array([[X.R().get(r, c) for c in range(3)] for r in range(3)]); p = _vec(X.p())
            local[(n, k)] = (b, R.T @ (g - p))
    nb = []                                                                   # neighbours on different bones
    keys = list(local)
    spacing = sole["point_spacing_mm"] * scale / 1000.0
    G0 = {kk: pts_g for kk, pts_g in ((p[0:2], p[2]) for p in pts)}
    for i, a in enumerate(keys):
        for bkey in keys[i + 1:]:
            if local[a][0] != local[bkey][0] and np.linalg.norm(G0[a] - G0[bkey]) < 1.5 * spacing:
                nb.append((a, bkey))
    cs = m.getCoordinateSet()
    neutral = {f"synergy_gain_{g}": cs.get(f"synergy_gain_{g}").getValue(st) for g in range(1, 6)}

    def pose_points():
        m.realizePosition(st)
        ca = m.getBodySet().get("CA_r").getTransformInGround(st)
        Rca = np.array([[ca.R().get(r, c) for c in range(3)] for r in range(3)]); pca = _vec(ca.p())
        out = {}
        for kk, (b, l) in local.items():
            X = m.getBodySet().get(b).getTransformInGround(st)
            R = np.array([[X.R().get(r, c) for c in range(3)] for r in range(3)]); p = _vec(X.p())
            out[kk] = Rca.T @ (R @ l + p - pca)                                # in the calcaneus frame
        rot = {}
        for t, mt in zip(TOES, METATARSALS):
            Xt, Xm = m.getBodySet().get(t).getTransformInGround(st), m.getBodySet().get(mt).getTransformInGround(st)
            Rt = np.array([[Xt.R().get(r, c) for c in range(3)] for r in range(3)])
            Rm = np.array([[Xm.R().get(r, c) for c in range(3)] for r in range(3)])
            rot[t] = Rm.T @ Rt
        return out, rot
    base, base_rot = pose_points()
    sweeps = {}
    for g, band in [(g, band) for g in range(1, 6) for band in ("full coordinate range", "neutral +/- 10% of range")]:
        c = cs.get(f"synergy_gain_{g}")
        lo, hi = c.getRangeMin(), c.getRangeMax()
        if band != "full coordinate range":
            w = 0.1 * (hi - lo); lo, hi = neutral[f"synergy_gain_{g}"] - w, neutral[f"synergy_gain_{g}"] + w
        vals = np.linspace(lo, hi, steps)
        disp, strain, toe = {}, 0.0, {t: 0.0 for t in TOES}
        for v in vals:
            c.setValue(st, float(v), True)
            P, rot = pose_points()
            for kk in local:
                d = 1000 * np.linalg.norm(P[kk] - base[kk])
                disp[kk[0]] = max(disp.get(kk[0], 0.0), d)
            for a, bkey in nb:
                d0 = np.linalg.norm(base[a] - base[bkey]); d1 = np.linalg.norm(P[a] - P[bkey])
                strain = max(strain, abs(d1 - d0) / d0)
            for t in TOES:
                dR = base_rot[t].T @ rot[t]
                toe[t] = max(toe[t], float(np.degrees(np.arccos(np.clip((np.trace(dR) - 1) / 2, -1, 1)))))
        c.setValue(st, neutral[f"synergy_gain_{g}"], True)
        sweeps.setdefault(f"synergy_gain_{g}", {})[band] = dict(range=[round(lo, 3), round(hi, 3)],
                                           max_region_motion_vs_calcaneus_mm={k: round(v, 1) for k, v in sorted(disp.items())},
                                           max_sole_stretch_between_bones_pct=round(100 * strain, 1),
                                           max_toe_rotation_vs_metatarsal_deg={k: round(v, 1) for k, v in toe.items()})
    return dict(status="experimental: kinematic only; no load, no contact; synergies swept over coordinate ranges",
                model=str(model_path), sole=sole["board_id"], scale=round(scale, 4), registration=reg,
                region_to_bones=region_bones,
                points_without_bone=sum(1 for b in assign.values() if b is None), points=len(assign),
                neighbour_pairs_across_bones=len(nb), sweeps=sweeps,
                toes_move_independently=False,
                note="all five toes follow synergy_gain_5 (one coordinate): their rotations differ in size, not in timing")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("model"); ap.add_argument("sole_json"); ap.add_argument("-o", required=True)
    a = ap.parse_args()
    r = analyse(a.model, a.sole_json)
    Path(a.o).write_text(json.dumps(r, indent=1) + "\n")
    print(json.dumps({k: r[k] for k in ("scale", "registration", "region_to_bones", "points_without_bone")}, indent=1))


if __name__ == "__main__":
    main()
