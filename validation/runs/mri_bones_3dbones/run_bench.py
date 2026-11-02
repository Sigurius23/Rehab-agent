"""Skin-only skeletons against MRI bones on the 3DBones test subjects (README.md in this folder).

How far the MRI-segmented bone points lie from each method's skeleton predicted from the skin alone (SKEL, SKEL-J,
OSSO, HIT, as released), per bone; plus femur and tibia lengths. The release's SKEL-J fit to the MRI bones themselves
(skel_mri) is scored the same way: the floor no skin-only prediction in that model can beat on this ground truth.

    python -I run_bench.py --release mri_bones_release_v2.zip --skel-dir models_npz --osso-dir models_npz \
        --out $WORK/mri_bones_3dbones/subjects.json [--workers 4]
    python -I run_bench.py --selftest          # the reader and the distance code, no data needed

--release defaults to $BONES3D_ZIP, the model folders to $MODELS_NPZ, --out to $WORK/mri_bones_3dbones/subjects.json.
The output holds per-subject rows with the release's subject ids: it stays in $WORK, never in this repository.

Ground truth = the release's per-part MRI point clouds: 2.1 mm in-plane, slices 20 mm apart, so bone lengths along the
slices carry up to ~20 mm of quantisation. Distances are exact point-to-triangle distances (the nearest triangle is
found among candidates from a dense surface sample, then measured exactly; checked against brute force on three
subjects every run). Nothing in the release is executed: meshes are parsed from bytes, the one pickle per subject is
not read. The scans are lying down with the arms overhead, so the body's extent is not stature; body size is the MRI
SMPL fit's volume and how deep the bones lie below the skin."""
import argparse
import json
import multiprocessing
import os
import sys
import zipfile
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

PREFIX = "mri_bones_release_v2/test/"
PARTS = {"Femur": ("femur",), "Tibia-Fibula": ("tibia",), "Pelvis": ("pelvis",), "Humerus": ("humerus",),
         "Radius-Ulna": ("ulna", "radius")}
OSSO_PARTS = {"Femur": ("LeftLeg1", "RightLeg1"), "Tibia-Fibula": ("LeftLeg2", "RightLeg2"), "Pelvis": ("Pelvis",),
              "Humerus": ("LeftArm1", "RightArm1"), "Radius-Ulna": ("LeftArm2", "RightArm2")}
METHODS = ("skel", "skel_j", "osso", "hit", "skel_mri")     # skel_mri: SKEL-J fitted to the MRI bones (the floor)
GET_DATA = ("The 3DBones release is not in this repository. Register on the 3DBones project site "
            "(3dbones.is.tue.mpg.de; non-commercial research terms, read them there), download "
            "mri_bones_release_v2.zip and pass it with --release or $BONES3D_ZIP. See README.md in this folder.")
GET_MODELS = ("SKEL (skel_female.npz, skel_male.npz) and OSSO (skeleton_model.npz) come from your own accounts on "
              "the MPI sites; convert the downloads once with "
              "python -I pipeline/adapters/body_model_files.py convert DOWNLOADS/ models_npz/")

_T = {"char": "i1", "uchar": "u1", "int8": "i1", "uint8": "u1", "short": "i2", "ushort": "u2", "int16": "i2",
      "uint16": "u2", "int": "i4", "uint": "u4", "int32": "i4", "uint32": "u4", "float": "f4", "float32": "f4",
      "double": "f8", "float64": "f8"}


def read_ply(raw):
    """Binary little-endian PLY: vertices x, y, z and triangle faces, numpy only. Reads bytes, never executes."""
    end = raw.index(b"end_header") + len(b"end_header")
    end += 2 if raw[end:end + 2] == b"\r\n" else 1    # exactly one line ending: the binary data may start with 0x0a
    lines = raw[:end].decode("ascii").splitlines()
    fmt = next(ln.split()[1] for ln in lines if ln.startswith("format"))
    if fmt != "binary_little_endian":
        raise ValueError(f"PLY format {fmt} not handled")
    elements, cur = [], None
    for ln in lines:
        p = ln.split()
        if not p:
            continue
        if p[0] == "element":
            cur = {"name": p[1], "count": int(p[2]), "props": []}
            elements.append(cur)
        elif p[0] == "property":
            cur["props"].append(p[1:])
    off, out = end, {}
    for el in elements:
        if el["name"] == "face":
            lst = el["props"][0]
            if lst[0] != "list" or len(el["props"]) != 1:
                raise ValueError("face element with extra properties not handled")
            rec = np.dtype([("n", "<" + _T[lst[1]]), ("i", "<" + _T[lst[2]], 3)])
            arr = np.frombuffer(raw, rec, el["count"], off)
            if not np.all(arr["n"] == 3):
                raise ValueError("non-triangle faces")
            out["faces"] = arr["i"].astype(np.int64)
            off += rec.itemsize * el["count"]
        else:
            if any(pp[0] == "list" for pp in el["props"]):
                raise ValueError(f"list property in {el['name']} not handled")
            rec = np.dtype([(pp[1], "<" + _T[pp[0]]) for pp in el["props"]])
            arr = np.frombuffer(raw, rec, el["count"], off)
            off += rec.itemsize * el["count"]
            if el["name"] == "vertex":
                out["v"] = np.column_stack([arr["x"], arr["y"], arr["z"]]).astype(np.float64)
    return out


def closest_on_triangles(p, a, b, c):
    """Closest point to p on triangle abc, row by row (Ericson, Real-Time Collision Detection 5.1.5)."""
    ab, ac, ap = b - a, c - a, p - a
    d1, d2 = (ab * ap).sum(1), (ac * ap).sum(1)
    bp, cp = p - b, p - c
    d3, d4 = (ab * bp).sum(1), (ac * bp).sum(1)
    d5, d6 = (ab * cp).sum(1), (ac * cp).sum(1)
    vc, vb, va = d1 * d4 - d3 * d2, d5 * d2 - d1 * d6, d3 * d6 - d5 * d4

    def safe(x):
        return np.where(x == 0, 1.0, x)
    res = np.empty_like(p)
    done = np.zeros(len(p), bool)

    def put(mask, val):
        nonlocal done
        m = mask & ~done
        res[m] = val[m]
        done |= m
    put((d1 <= 0) & (d2 <= 0), a)
    put((d3 >= 0) & (d4 <= d3), b)
    put((vc <= 0) & (d1 >= 0) & (d3 <= 0), a + (d1 / safe(d1 - d3))[:, None] * ab)
    put((d6 >= 0) & (d5 <= d6), c)
    put((vb <= 0) & (d2 >= 0) & (d6 <= 0), a + (d2 / safe(d2 - d6))[:, None] * ac)
    put((va <= 0) & (d4 - d3 >= 0) & (d5 - d6 >= 0),
        b + ((d4 - d3) / safe((d4 - d3) + (d5 - d6)))[:, None] * (c - b))
    den = safe(va + vb + vc)
    put(np.ones(len(p), bool), a + ab * (vb / den)[:, None] + ac * (vc / den)[:, None])
    return res


class MeshDistance:
    """Exact distance from points to a triangle mesh: candidates from a dense area-weighted surface sample."""

    def __init__(self, v, f, spacing=0.0015, k=16, seed=0):
        self.v, self.f, self.k = v, f, k
        a, b, c = v[f[:, 0]], v[f[:, 1]], v[f[:, 2]]
        area = 0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1)
        n = np.maximum(1, np.ceil(area / spacing ** 2)).astype(int)
        fid = np.repeat(np.arange(len(f)), n)
        rng = np.random.default_rng(seed)
        r1, r2 = rng.random(len(fid)), rng.random(len(fid))
        s = np.sqrt(r1)
        pts = (1 - s)[:, None] * a[fid] + (s * (1 - r2))[:, None] * b[fid] + (s * r2)[:, None] * c[fid]
        self.fid = np.concatenate([fid, np.arange(len(f))])
        self.tree = cKDTree(np.vstack([pts, (a + b + c) / 3]))

    def __call__(self, p):
        _, idx = self.tree.query(p, self.k)
        cand = self.fid[idx]                                   # (N, k) candidate faces
        P = np.repeat(p, self.k, axis=0)
        F = self.f[cand.ravel()]
        q = closest_on_triangles(P, self.v[F[:, 0]], self.v[F[:, 1]], self.v[F[:, 2]])
        return np.linalg.norm(P - q, axis=1).reshape(len(p), self.k).min(axis=1)


def check_exact(md, pts, n=300, seed=1):
    """Brute force over every triangle for a sample of points: the candidate search must find the true minimum."""
    rng = np.random.default_rng(seed)
    sel = pts[rng.choice(len(pts), min(n, len(pts)), replace=False)]
    a, b, c = (md.v[md.f[:, i]] for i in range(3))
    brute = np.array([np.linalg.norm(q - closest_on_triangles(np.repeat(q[None], len(a), 0), a, b, c), axis=1).min()
                      for q in sel])
    return float(np.max(np.abs(brute - md(sel))))


def bone_length(points):
    """Extent of a bone's points along its own long axis (first principal axis), m."""
    x = points - points.mean(0)
    axis = np.linalg.svd(x, full_matrices=False)[2][0]
    t = x @ axis
    return float(t.max() - t.min())


def split_sides(points):
    """Left/right halves of a two-sided part by 2-means along the lateral axis: of the two horizontal axes (z is
    vertical in the release's frame), the one whose halves lie furthest apart."""
    best = None
    for ax in range(2):
        c = np.median(points[:, ax])
        lo, hi = points[points[:, ax] < c], points[points[:, ax] >= c]
        gap = abs(lo[:, ax].mean() - hi[:, ax].mean()) if len(lo) and len(hi) else 0
        if best is None or gap > best[0]:
            best = (gap, ax)
    ax = best[1]
    c = np.median(points[:, ax])
    for _ in range(20):
        lo, hi = points[points[:, ax] < c], points[points[:, ax] >= c]
        c = (lo[:, ax].mean() + hi[:, ax].mean()) / 2
    return ax, points[points[:, ax] < c], points[points[:, ax] >= c]


def osso_layout(osso):
    """osso.ply as released is OSSO's 21 parts laid end to end: part i's vertices in part2bodyPoints order, its faces
    partFaces/i offset by the vertices before it. Returns those faces and each face's part index."""
    n = len(osso["names"])
    counts = [len(osso[f"part2bodyPoints/{i}"]) for i in range(n)]
    off = np.concatenate([[0], np.cumsum(counts)[:-1]])
    pf = [osso[f"partFaces/{i}"].astype(np.int64) for i in range(n)]
    return np.vstack([f + o for f, o in zip(pf, off)]), np.repeat(np.arange(n), [len(f) for f in pf])


def score_subject(z, names, s, si, osso, skel_models, checks):
    sex, sid = s.split("/")[2], s.split("/")[3]

    def read(f):
        return read_ply(z.read(f"{s}/{f}"))
    gt = {p: read(f"per_part_pc/{p}_pc.ply")["v"] for p in PARTS}
    skin = read("skin_pc.ply")["v"]
    smpl = read("mri_smpl.ply")
    sv, sf = smpl["v"], smpl["faces"]
    vol = abs(np.einsum("ij,ij->i", sv[sf[:, 0]], np.cross(sv[sf[:, 1]], sv[sf[:, 2]])).sum()) / 6
    skin_tree = cKDTree(skin)
    depth = {p: float(skin_tree.query(pts)[0].mean()) for p, pts in gt.items()}   # how deep each bone lies below skin
    row = {"subject": sid, "sex": sex, "body_volume_l": round(1000 * float(vol), 1),
           "bone_depth_mm": round(1000 * float(np.mean(list(depth.values()))), 1),
           "thigh_depth_mm": round(1000 * depth["Femur"], 1), "methods": {}}
    sm = skel_models[sex]
    bone_names = [str(x) for x in sm["bone_names"]]
    vlab = np.argmax(sm["skel_weights_rigid"], axis=1)
    osso_faces, osso_face_part = osso_layout(osso)
    osso_names = [str(x) for x in osso["names"]]
    for method in METHODS:
        fname = f"{method}.ply"
        if f"{s}/{fname}" not in names:
            continue
        m = read(fname)
        v, f = m["v"], m["faces"]
        whole = MeshDistance(v, f)
        res = {"any_part_mm": {}, "same_part_mm": {}, "length_err_mm": {}}
        if si < 3:
            checks.append({"subject": sid, "method": method,
                           "max_abs_diff_vs_brute_force_mm": round(1000 * check_exact(whole, gt["Femur"]), 4)})
        face_part = None
        if method in ("skel", "skel_j"):
            if len(v) != len(vlab) or not np.array_equal(f, sm["skel_template_f"].astype(np.int64)):
                raise ValueError(f"{sid} {method}: not SKEL's template topology")
            face_part = {p: np.isin(vlab[f[:, 0]], [i for i, b in enumerate(bone_names) if b.startswith(PARTS[p])])
                         for p in PARTS}
        elif method == "osso":
            if not np.array_equal(f, osso_faces):
                raise ValueError(f"{sid} osso: not OSSO's parts laid end to end")
            face_part = {p: np.isin(osso_face_part, [osso_names.index(n) for n in OSSO_PARTS[p]]) for p in PARTS}
        for p, pts in gt.items():
            res["any_part_mm"][p] = round(1000 * float(whole(pts).mean()), 2)
            if face_part is not None:
                pf = f[face_part[p]]
                res["same_part_mm"][p] = round(1000 * float(MeshDistance(v, pf)(pts).mean()), 2)
                if p in ("Femur", "Tibia-Fibula"):
                    used = np.unique(pf)
                    _, g_lo, g_hi = split_sides(pts)
                    _, m_lo, m_hi = split_sides(v[used])
                    res["length_err_mm"][p] = [round(1000 * (bone_length(mm) - bone_length(gg)), 1)
                                               for gg, mm in ((g_lo, m_lo), (g_hi, m_hi))]
        row["methods"][method] = res
    print(f"{si + 1:2d} {sex:6s} " + "  ".join(
        f"{k} {np.mean(list(v['any_part_mm'].values())):.1f}" for k, v in row["methods"].items()), flush=True)
    return row


def score_job(job):
    release, skel_dir, osso_dir, s, si = job
    osso = np.load(osso_dir / "skeleton_model.npz", allow_pickle=False)
    skel_models = {sex: np.load(skel_dir / f"skel_{sex}.npz", allow_pickle=False) for sex in ("female", "male")}
    checks = []
    with zipfile.ZipFile(release) as z:
        try:
            return {"row": score_subject(z, set(z.namelist()), s, si, osso, skel_models, checks), "checks": checks}
        except ValueError as e:                      # recorded, not hidden: the subject is left out and listed
            print(f"{si + 1:2d} FAILED: {e}", flush=True)
            return {"failed": {"subject": s.split("/")[3], "error": str(e)}, "checks": checks}


def stop(msg):
    print(msg, file=sys.stderr)
    sys.exit(2)


def inputs(args):
    """The data and model files, or a message saying where they come from (no traceback)."""
    if not args.release:
        stop("No release given. " + GET_DATA)
    release = Path(args.release)
    if not release.is_file() or not zipfile.is_zipfile(release):
        stop(f"{release}: not found or not a zip. " + GET_DATA)
    with zipfile.ZipFile(release) as z:
        subjects = sorted({n.rsplit("/", 1)[0] for n in z.namelist()
                           if n.startswith(PREFIX) and n.endswith("/skel_j.ply")})
    if not subjects:
        stop(f"{release}: no {PREFIX}*/skel_j.ply inside; this script expects the 3DBones release v2 layout. "
             + GET_DATA)
    skel_dir, osso_dir = Path(args.skel_dir or "."), Path(args.osso_dir or ".")
    missing = [str(p) for p in (skel_dir / "skel_female.npz", skel_dir / "skel_male.npz",
                                osso_dir / "skeleton_model.npz") if not p.is_file()]
    if missing:
        stop("Missing model files: " + ", ".join(missing) + ". " + GET_MODELS)
    if not args.out:
        stop("No output path: pass --out or set $WORK.")
    return release, skel_dir, osso_dir, subjects


def selftest():
    """No data needed: the reader on a file whose binary data starts with a newline byte, and the candidate search
    against brute force on a random mesh."""
    v = np.array([[np.frombuffer(b"\x0a\x00\x00\x00", "<f4")[0], 0, 0], [1, 0, 0], [0, 1, 0]], "<f4")
    head = b"ply\nformat binary_little_endian 1.0\nelement vertex 3\nproperty float x\nproperty float y\n" \
           b"property float z\nelement face 1\nproperty list uchar int vertex_indices\nend_header\n"
    raw = head + v.tobytes() + np.array([3], "u1").tobytes() + np.array([0, 1, 2], "<i4").tobytes()
    m = read_ply(raw)
    assert np.array_equal(m["v"], v.astype(np.float64)) and m["faces"].tolist() == [[0, 1, 2]], "PLY reader"
    rng = np.random.default_rng(0)
    vv = rng.normal(size=(400, 3)) * 0.1
    ff = rng.integers(0, 400, size=(700, 3))
    ff = ff[(ff[:, 0] != ff[:, 1]) & (ff[:, 1] != ff[:, 2]) & (ff[:, 0] != ff[:, 2])]
    err = check_exact(MeshDistance(vv, ff, spacing=0.004, k=64), rng.normal(size=(200, 3)) * 0.12, n=200)
    assert err < 1e-4, f"candidate search off by {1000 * err:.3f} mm"
    print("selftest passed: PLY reader (data starting with 0x0a); point-to-mesh distance within "
          f"{1000 * err:.4f} mm of brute force")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--release", default=os.environ.get("BONES3D_ZIP"))
    ap.add_argument("--skel-dir", default=os.environ.get("MODELS_NPZ"))
    ap.add_argument("--osso-dir", default=os.environ.get("MODELS_NPZ"))
    ap.add_argument("--out", default=os.environ.get("WORK") and str(Path(os.environ["WORK"]) / "mri_bones_3dbones"
                                                                    / "subjects.json"))
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    release, skel_dir, osso_dir, subjects = inputs(args)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    jobs = [(release, skel_dir, osso_dir, s, si) for si, s in enumerate(subjects)]
    with multiprocessing.get_context("spawn").Pool(args.workers) as pool:
        done = pool.map(score_job, jobs, chunksize=1)
    rows = [d["row"] for d in done if "row" in d]
    failed = [d["failed"] for d in done if "failed" in d]
    checks = [c for d in done for c in d["checks"]]
    out.write_text(json.dumps({"subjects": rows, "failed": failed, "exactness_checks": checks}, indent=1))
    print(f"{len(rows)} subjects scored, {len(failed)} failed -> {out}")


if __name__ == "__main__":       # the worker processes import this file again
    main()
