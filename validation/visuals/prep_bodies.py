"""3D page data, part 1: bodies and bones (SKEL), and synthetic depth frames.

Writes OUT/bodies.json (+ arrays in OUT/bodies.bin) for the page, and OUT/skel_check.npz (bone meshes computed
here for a few bodies, to test the page's JavaScript port against).

    python -I prep_bodies.py $WORK $REPO OUT
"""
import csv
import json
import os
import sys
from pathlib import Path

import numpy as np

SP, REPO, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
sys.path.insert(0, str(REPO / "pipeline"))
sys.path.insert(0, str(REPO / "pipeline/adapters"))
from rehabtwin import shape, skel_bones   # noqa: E402
import bedlam2                             # noqa: E402

SEXES = ("female", "male")
SMPL_FILES = {"female": "basicmodel_f_lbs_10_207_0_v1.1.0.npz", "male": "basicmodel_m_lbs_10_207_0_v1.1.0.npz"}
FIXED = [0, 5, 10, 13, 18, 23]               # SKEL joint_idx_fixed_beta
# SKEL kin_skel.scaling_keypoints: (bone, axis in bone space, axis in SMPL space): (skin vertex, skin vertex)
KEYPOINTS = [(13, 0, 2, 410, 384), (13, 1, 1, 414, 384), (13, 2, 0, 196, 3708),
             (18, 0, 1, 6179, 6137), (18, 1, 0, 5670, 5906), (23, 0, 1, 6179, 6137), (23, 1, 0, 5670, 5906)]
THORAX = (3027, 3495, 3506)                  # back, front, sternum
NB = 16                                      # shape parameters: the depth fits use 16 (SKEL's own forward uses 10)


class Pack:
    """Arrays into one little-endian binary file, described by name -> [dtype, shape, offset] (+ scale)."""
    def __init__(self):
        self.parts, self.index, self.size = [], {}, 0

    def add(self, name, a, dtype, scale=None):
        a = np.asarray(a)
        q = np.round(a / scale).astype(dtype) if scale else a.astype(dtype)
        if scale:
            assert np.abs(q.astype(float) * scale - a).max() <= scale, name
        b = q.tobytes()
        pad = (-self.size) % 4
        self.parts.append(b"\0" * pad)
        self.size += pad
        self.index[name] = {"dtype": np.dtype(dtype).name, "shape": list(q.shape), "offset": self.size,
                            **({"scale": scale} if scale else {})}
        self.parts.append(b)
        self.size += len(b)

    def write(self, path):
        Path(path).write_bytes(b"".join(self.parts))
        return self.index


def kintree(skel):
    kt = skel["osim_kintree_table"].astype(np.int64)
    col = {int(kt[1, i]): i for i in range(kt.shape[1])}
    parent = np.array([-1] + [col[int(kt[0, i])] for i in range(1, kt.shape[1])])
    child = []
    for i in range(kt.shape[1]):                 # as SKEL: the first child in the table, 0 for a leaf
        js = np.where(kt[0] == i)[0]
        child.append(int(kt[1, js[0]]) if len(js) else 0)
    return parent, np.array(child)


def rot_from_vectors(a, b):
    a = a / np.linalg.norm(a, axis=-1, keepdims=True)
    b = b / np.linalg.norm(b, axis=-1, keepdims=True)
    v = np.cross(a, b)
    c = (a * b).sum(-1)
    s = np.linalg.norm(v, axis=-1) + np.finfo(float).eps
    K = np.zeros(v.shape[:-1] + (3, 3))
    K[..., 0, 1], K[..., 0, 2], K[..., 1, 0] = -v[..., 2], v[..., 1], v[..., 2]
    K[..., 1, 2], K[..., 2, 0], K[..., 2, 1] = -v[..., 0], -v[..., 1], v[..., 0]
    return np.eye(3) + K + K @ K * ((1 - c) / s ** 2)[..., None, None]


def skel_rest(skel, betas):
    """SKEL in its rest (T) pose for ``betas``: skin vertices, joint centres, and per bone the rotation, the
    scale and the translation that place the template bone mesh (SKEL forward with zero pose, skelmesh=True)."""
    parent, child = kintree(skel)
    v0 = skel["skin_template_v"]
    b = np.asarray(betas, float)
    vs = v0 + skel["shapedirs"][:, :, :len(b)] @ b
    J = skel["J_regressor_osim"] @ vs
    Jl = J.copy()
    Jl[1:] = J[1:] - J[parent[1:]]
    osim = skel["apose_rel_transfo"][:, :3, 3]
    # bone orientation (compute_bone_orientation, 'learn_adjust')
    bv = Jl[child].copy()
    bv[16] += bv[17]
    bv[21] += bv[22]
    bv[12] = bv[11]
    ov = osim[child].copy()
    ov[16] += ov[17]
    ov[21] += ov[22]
    Gl = skel["per_joint_rot"]
    Gk = rot_from_vectors(np.einsum("jab,jb->ja", Gl, ov), bv)
    Gk[np.isnan(Gk)] = 0
    Gk[FIXED] = np.eye(3)
    Gk = Gk @ Gl
    # bone scale (compute_bone_scale)
    bsp = np.linalg.norm(Jl, axis=1) / np.linalg.norm(osim, axis=1)
    bs = np.ones(24)
    nl = child != 0
    bs[nl] = bsp[child][nl]
    bs[16], bs[21] = bs[17], bs[22]
    bs[12] = bs[11]
    bs[11] = abs(Jl[11, 1]) / abs(osim[11, 1])
    S = np.repeat(bs[:, None], 3, 1)
    for j, d, ds, a, b in KEYPOINTS:
        S[j, d] = ((vs[a] - vs[b]) / (v0[a] - v0[b]))[ds]
    back, front, sternum = THORAX
    S[12, 0] = min(((vs[back] - vs[front]) / (v0[back] - v0[front]))[2],
                   ((vs[back] - vs[sternum]) / (v0[back] - v0[sternum]))[2])
    S[11, 0] = S[12, 0]
    return vs, J, Gk, S


def bone_vertices(local, bone, J, Gk, S):
    return np.einsum("vab,vb->va", Gk[bone], S[bone] * local) + J[bone]


CELL_M = {**dict.fromkeys(range(24), 0.006), **dict.fromkeys((0, 11, 12, 13), 0.008),
          **dict.fromkeys((3, 4, 5, 8, 9, 10, 18, 23), 0.004)}     # coarse trunk and skull, fine hands and feet


def decimate(skel, cells=CELL_M):
    """Vertex clustering of the template bone mesh, per bone in its own frame (the transform is per bone, so
    the reduced mesh transforms exactly as the full one)."""
    v, f = skel["skel_template_v"], skel["skel_template_f"].astype(np.int64)
    bone = skel["skel_weights_rigid"].argmax(1)
    cell = np.array([cells[b] for b in range(24)])[bone][:, None]
    key = np.column_stack([bone, np.floor(v / cell).astype(np.int64)])
    _, cluster, counts = np.unique(key, axis=0, return_inverse=True, return_counts=True)
    cluster = cluster.ravel()
    nv = counts.size
    nvert = np.zeros((nv, 3))
    np.add.at(nvert, cluster, v)
    nvert /= counts[:, None]
    nbone = np.zeros(nv, np.int64)
    nbone[cluster] = bone
    nf = cluster[f]
    keep = (nf[:, 0] != nf[:, 1]) & (nf[:, 1] != nf[:, 2]) & (nf[:, 0] != nf[:, 2])
    nf = nf[keep]
    nf = nf[np.sort(np.unique(np.sort(nf, 1), axis=0, return_index=True)[1])]
    return nvert, nbone, nf, (len(v), len(f))


def main():
    pack, meta = Pack(), {"sexes": {}, "presets": [], "depth": []}
    smpl = {s: skel_bones.load_smpl(SP / "body_models/npz" / SMPL_FILES[s]) for s in SEXES}
    skel = {s: skel_bones.load_skel(SP / f"body_models_skel/npz/skel_{s}.npz") for s in SEXES}
    check = {}
    for s in SEXES:
        k = skel[s]
        assert np.allclose(k["skin_template_v"], smpl[s]["v_template"]) and np.allclose(
            k["shapedirs"][:, :, :NB], smpl[s]["shapedirs"][:, :, :NB]), "SKEL skin is not this SMPL"
        parent, child = kintree(k)
        lv, lb, lf, full = decimate(k)
        sd = k["shapedirs"][:, :, :NB]
        pack.add(f"{s}.v0", k["skin_template_v"], np.int16, 5e-5)
        pack.add(f"{s}.sd", sd, np.int16, float(np.abs(sd).max()) / 32000)
        pack.add(f"{s}.J0", k["J_regressor_osim"] @ k["skin_template_v"], np.float32)
        pack.add(f"{s}.Jd", np.einsum("jv,vcb->jcb", k["J_regressor_osim"], sd), np.float32)
        pack.add(f"{s}.osim", k["apose_rel_transfo"][:, :3, 3], np.float32)
        pack.add(f"{s}.pjr", k["per_joint_rot"], np.float32)
        pack.add(f"{s}.bone_v", lv, np.int16, 2e-5)
        pack.add(f"{s}.bone_b", lb, np.uint8)
        w = k["skin_weights"]                    # skin follows each arm by its weights on that arm's bones
        pack.add(f"{s}.arm", np.column_stack([w[:, 15:19].sum(1), w[:, 20:24].sum(1)]).clip(0, 1), np.uint8, 1 / 250)
        pack.add(f"{s}.bone_f", lf, np.uint16 if len(lv) < 65536 else np.uint32)
        # betas for a height x BMI grid: the SMPL body nearest the mean shape (as person bones without a surface)
        H, B = np.round(np.arange(1.40, 2.101, 0.05), 3), np.arange(16.0, 46.1, 2.0)
        cache = OUT / f"cache_grid_{s}.npy"
        if cache.exists():
            grid = np.load(cache)
        else:
            grid, err = np.full((len(H), len(B), 10), np.nan), []
            for i, h in enumerate(H):
                for j, bmi in enumerate(B):
                    try:
                        grid[i, j], _ = skel_bones.betas_for_height_mass(smpl[s], h, bmi * h * h)
                    except ValueError as e:
                        err.append(str(e))
            if err:
                print(s, len(err), "grid points without a body:", err[:3])
            np.save(cache, grid)
        print(s, "grid points without a body:", int(np.isnan(grid[..., 0]).sum()), "of", grid[..., 0].size)
        pack.add(f"{s}.grid", np.nan_to_num(grid, nan=999.0), np.float32)
        meta["sexes"][s] = {"parent": parent.tolist(), "child": child.tolist(), "fixed": FIXED,
                            "keypoints": KEYPOINTS, "thorax": THORAX, "bone_names": k["bone_names"].tolist(),
                            "grid_height_m": H.tolist(), "grid_bmi": B.tolist(),
                            "bone_mesh": {"template_vertices": full[0], "template_faces": full[1],
                                          "vertices": len(lv), "faces": len(lf)}}
        print(s, "bone mesh", full, "->", len(lv), len(lf), flush=True)
        check[s] = (lv, lb)
    pack.add("faces", smpl["female"]["f"], np.uint16)

    # presets: test bodies across the BMI range, and OpenCap subject 2 from height and mass
    rows = {r["body"]: r for r in json.loads((SP / "skel_work/skel_bones.json").read_text())["rows"]}
    picks = ["us_2440_XS", "nl_6585_M", "us_2924_L", "us_2378_4XL", "nl_6562_5XL"]
    for b in picks:
        r = rows[b]
        meta["presets"].append({"name": f"test body {b.split('_')[-1]}", "id": b, "sex": r["sex"],
                                "height_m": round(r["height_m"], 3), "mass_kg": round(r["mass_kg"], 1),
                                "betas": [round(x, 5) for x in r["betas_true"]]})
    p = json.loads((SP / "skel_work/oc_P/person.json").read_text())["skel_bones"]
    meta["presets"].append({"name": "OpenCap subject 2", "id": "opencap-subject2", "sex": p["sex"], "height_m": 1.96,
                            "mass_kg": 78.2, "betas": p["betas"], "note": "from height and mass (no surface)"})

    # check values for the JavaScript port: two presets and one grid body
    for k, pr in enumerate(meta["presets"][:2] + meta["presets"][-1:]):
        s = pr["sex"]
        vs, J, Gk, S = skel_rest(skel[s], pr["betas"])
        lv, lb = check[s]
        np.savez(OUT / f"skel_check_{k}.npz", betas=np.array(pr["betas"]), sex=s, skin=vs, J=J, Gk=Gk, S=S,
                 bones=bone_vertices(lv, lb, J, Gk, S))

    # synthetic depth frames: two of the test bodies, regenerated exactly as adapters/bedlam2_skel.py did
    mapping = list(csv.DictReader(open(SP / "bedlam2_dl/Rehab agent/b2_bedlam2amass_motion_training.csv")))
    for b in ("nl_6585_M", "us_2378_4XL"):
        r = rows[b]
        s, betas = r["sex"], np.array(r["betas_true"])
        mid = [m["motion_id"] for m in mapping if m["body_id"] == b and m["motion_rel_fname"] == r["motion"]]
        assert len(mid) == 1, (b, mid)
        d = np.load(SP / f"bedlam2_x/motions_npz_training/{b}_{mid[0]}.npz", allow_pickle=False)
        fi = r["frame"]
        pose = np.concatenate([np.asarray(d["poses"][fi], float)[:66], np.zeros(6)])
        trans = np.asarray(d["trans"][fi], float).copy()
        v, _ = bedlam2.pose_body(smpl[s], betas, pose, trans)
        trans[1] -= v[:, 1].min()
        obs = bedlam2.synth_frame(smpl[s], betas, pose, trans, np.random.default_rng(bedlam2._seed(b, "A", "skel")))
        frame = [{"points": obs["points"], "floor": obs["floor"], "keypoints_uv": obs["keypoints_uv"]}]
        res = shape.fit_shape(shape.BodyModel(smpl[s]), frame, bedlam2.KINECT_K)
        assert np.allclose(res["betas"], r["fits"]["depth fit"]["betas"], atol=1e-4), "fit differs from the run"
        fr = res["frames"][0]
        fpose = np.concatenate([np.ravel(fr["global_orient"]), np.ravel(fr["body_pose"]), np.zeros(6)])
        vf, jf = bedlam2.pose_body(smpl[s], np.asarray(res["betas"]), fpose, np.asarray(fr["transl"], float))
        C, R = obs["camera"]
        vt = (bedlam2.pose_body(smpl[s], betas, pose, trans)[0] - C) @ R.T      # as synth_frame saw it
        jerr = np.abs(jf[:22] - np.asarray(fr["joints"])[:22]).max()
        print(b, "points", len(obs["points"]), "fit joints reproduced to", f"{jerr * 1000:.2f} mm", flush=True)
        assert jerr < 1e-3, "posed fit does not match the fit's own joints"
        k = len(meta["depth"])
        pack.add(f"depth{k}.points", obs["points"], np.int16, 1e-3)
        pack.add(f"depth{k}.fit", vf, np.int16, 2e-4)
        pack.add(f"depth{k}.truth", vt, np.int16, 2e-4)
        up, offset = obs["floor"]
        meta["depth"].append({"id": b, "sex": s, "size": r["size"], "height_m": round(r["height_m"], 3),
                              "mass_kg": round(r["mass_kg"], 1), "betas_true": r["betas_true"],
                              "betas_fit": [round(x, 5) for x in res["betas"]],
                              "fit_height_m": round(res["height_m"], 3), "fit_mass_kg": round(res["mass_kg"], 1),
                              "warnings": res["fit"]["warnings"], "floor_up": list(map(float, up)),
                              "segments_run": {src: {kk: r["segments"][src][kk] for kk in ("thigh_r", "shank_r", "upper_arm_r", "forearm_r", "hip_width")}
                                               for src in ("true", "depth fit")},
                              "floor_offset": float(offset), "sensor": "Kinect v1, 2.7 m in front, 1.0 m high",
                              "motion_frame": f"{r['motion']} frame {fi}"})
    meta["arrays"] = pack.write(OUT / "bodies.bin")
    (OUT / "bodies.json").write_text(json.dumps(meta))
    print("bodies.bin", os.path.getsize(OUT / "bodies.bin") // 1024, "KB")


if __name__ == "__main__":
    main()
