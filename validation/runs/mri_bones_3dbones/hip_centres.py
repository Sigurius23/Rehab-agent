"""Hip joint centres from the skin against MRI bones on the 3DBones test subjects (README.md in this folder).

The hip centre is the centre of a sphere fitted to the femoral head, extracted the same way everywhere: from the MRI
femur, from each skin-only prediction (SKEL, SKEL-J, OSSO; HIT has no bone labels) and from the floor (SKEL-J fitted to
the MRI bones). The predicted femurs are first cut at the MRI's own slice planes (20 mm apart) and their outlines
sampled on the MRI's 2.1 mm grid, so every centre comes from the same kind of points. Each mesh is also fitted
unsliced, which shows how far the slicing alone moves a centre. Errors are split into anterior, medial and superior
components and set against the femur's length (the floor femur's, which is not quantised by the slices).

    python -I hip_centres.py run --release mri_bones_release_v2.zip --skel-dir models_npz --osso-dir models_npz \
        --out $WORK/mri_bones_3dbones/hip_subjects.json
    python -I hip_centres.py summarize $WORK/mri_bones_3dbones/hip_subjects.json \
        ../../results/mri_bones_3dbones_hip.json

Paths default to $BONES3D_ZIP, $MODELS_NPZ and $WORK as in run_bench.py. Per-subject output stays in $WORK."""
import argparse
import json
import os
import sys
import zipfile
from pathlib import Path

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree
from scipy.stats import wilcoxon

sys.path.insert(0, str(Path(__file__).parent))
from run_bench import inputs, osso_layout, read_ply, split_sides  # noqa: E402

SLICE = 0.02                 # the release's slice spacing, m; slices sit at whole multiples of it
PIXEL = 0.0021               # in-plane spacing of the MRI point clouds, m
HEAD_R = (0.017, 0.032)      # plausible femoral head radius, m
TOL = 0.002                  # a point belongs to the sphere within this distance, m
CAP_MM = 25                  # an MRI femur whose top slice is wider than this has lost the top of its head
METHODS = ("skel", "skel_j", "osso", "skel_mri")
TARGET_MM = 5.0              # docs/accuracy.md: joint-centre location vs imaging (Tier A)


def slice_outline(v, f, z0):
    """Where the mesh crosses the plane z = z0: segment points every <= one pixel, snapped to the pixel grid as the
    MRI outlines are."""
    s = v[f, 2] - z0                                            # (F, 3) signed heights
    cross = (s.min(1) < 0) & (s.max(1) > 0)
    pts = []
    for tri, h in zip(f[cross], s[cross]):
        ends = []
        for i, j in ((0, 1), (1, 2), (2, 0)):
            if (h[i] < 0) != (h[j] < 0):
                t = h[i] / (h[i] - h[j])
                ends.append(v[tri[i]] + t * (v[tri[j]] - v[tri[i]]))
        if len(ends) == 2:
            n = max(1, int(np.ceil(np.linalg.norm(ends[1] - ends[0]) / PIXEL)))
            pts.append(ends[0] + np.linspace(0, 1, n + 1)[:, None] * (ends[1] - ends[0]))
    if not pts:
        return np.zeros((0, 3))
    p = np.vstack(pts)
    p[:, :2] = np.round(p[:, :2] / PIXEL) * PIXEL
    p[:, 2] = z0
    return np.unique(np.round(p, 6), axis=0)


def sliced(v, f):
    """The mesh as the MRI sees it: outlines on every slice plane it spans."""
    ks = np.arange(np.ceil(v[:, 2].min() / SLICE), np.floor(v[:, 2].max() / SLICE) + 1)
    out = [slice_outline(v, f, k * SLICE) for k in ks]
    return np.vstack([o for o in out if len(o)])


def dense(v, f, spacing=0.0015, seed=0):
    """The mesh surface itself: vertices plus area-weighted samples."""
    a, b, c = v[f[:, 0]], v[f[:, 1]], v[f[:, 2]]
    n = np.maximum(1, np.ceil(0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1) / spacing ** 2)).astype(int)
    fid = np.repeat(np.arange(len(f)), n)
    rng = np.random.default_rng(seed)
    r1, r2 = rng.random(len(fid)), rng.random(len(fid))
    s = np.sqrt(r1)
    pts = (1 - s)[:, None] * a[fid] + (s * (1 - r2))[:, None] * b[fid] + (s * r2)[:, None] * c[fid]
    return np.vstack([v[np.unique(f)], pts])


def sphere_lsq(p):
    """Least-squares sphere: |x|^2 = 2 c.x + k."""
    A = np.column_stack([2 * p, np.ones(len(p))])
    sol, *_ = np.linalg.lstsq(A, (p ** 2).sum(1), rcond=None)
    c = sol[:3]
    return c, float(np.sqrt(max(sol[3] + c @ c, 0.0)))


def head_centre(p, medial, seed=0, iters=3000):
    """Femoral head centre from one femur's points (any sampling): the proximal points medial of the shaft, a RANSAC
    sphere within the head radius range, refined by least squares on its inliers. The same code for every source."""
    top = p[:, 2].max()
    shaft = p[(p[:, 2] < top - 0.10) & (p[:, 2] > top - 0.20)]
    if len(shaft) < 10:
        raise ValueError("no shaft below the head")
    sy = shaft[:, 1].mean()
    cand = p[(p[:, 2] > top - 0.07) & ((p[:, 1] - sy) * medial > 0.010)]
    if len(cand) < 12:
        raise ValueError("too few head points")
    rng = np.random.default_rng(seed)
    best = (0, None)
    for _ in range(iters):
        q = cand[rng.choice(len(cand), 4, replace=False)]
        A = np.column_stack([2 * (q[1:] - q[0])])
        b = (q[1:] ** 2).sum(1) - (q[0] ** 2).sum()
        if abs(np.linalg.det(A)) < 1e-12:
            continue
        c = np.linalg.solve(A, b)
        r = np.linalg.norm(q[0] - c)
        if not HEAD_R[0] <= r <= HEAD_R[1]:
            continue
        n = int((np.abs(np.linalg.norm(cand - c, axis=1) - r) < TOL).sum())
        if n > best[0]:
            best = (n, c, r)
    if best[1] is None:
        raise ValueError("no sphere in the head radius range")
    c, r = best[1], best[2]
    for _ in range(3):
        inl = cand[np.abs(np.linalg.norm(cand - c, axis=1) - r) < TOL]
        c, r = sphere_lsq(inl)
    res = np.linalg.norm(inl - c, axis=1) - r
    rms = 1000 * float(np.sqrt((res ** 2).mean()))
    return {"centre": c, "radius_mm": round(1000 * r, 1), "fit_rms_mm": round(rms, 2),
            "inliers": int(len(inl)), "slices": int(len(np.unique(np.round(inl[:, 2], 4))))}


def femur_sides(v, faces, midline, axis):
    """One femur submesh per side (faces given), split at the midline along the lateral axis: {'lo': (v, f), ...}."""
    out = {}
    cen = v[faces].mean(1)[:, axis]
    for side, m in (("lo", cen < midline), ("hi", cen >= midline)):
        ff = faces[m]
        used, inv = np.unique(ff, return_inverse=True)
        out[side] = (v[used], inv.reshape(-1, 3))
    return out


def floor_pieces(v, f, gt_points, k):
    """The floor mesh carries no bone labels; its bones are separate pieces. The k pieces lying on an MRI bone (femur:
    2; tibia-fibula: 4) are that bone. Returns a vertex mask."""
    n = len(v)
    A = coo_matrix((np.ones(3 * len(f)), (np.r_[f[:, 0], f[:, 1], f[:, 2]], np.r_[f[:, 1], f[:, 2], f[:, 0]])),
                   shape=(n, n))
    _, lab = connected_components(A, directed=False)
    d = cKDTree(gt_points).query(v)[0]
    comps = sorted(set(lab), key=lambda c: np.median(d[lab == c]))[:k]
    return np.isin(lab, comps), lab, comps


def floor_femur_faces(v, f, gt_fem):
    """The floor's two femurs (checked: each 0.3-0.6 m tall)."""
    _, lab, comps = floor_pieces(v, f, gt_fem, 2)
    for c in comps:
        ext = np.ptp(v[lab == c][:, 2])
        if not 0.3 < ext < 0.6:
            raise ValueError(f"floor femur piece {ext:.2f} m tall")
    return f[np.isin(lab[f[:, 0]], comps)]


def bone_ends(floor, gt_fem, gt_tib, midline, axis):
    """How far the floor (fitted to the MRI bones) reaches beyond the MRI femur and tibia-fibula at each end, per side,
    mm. Slicing alone leaves up to one slice (20 mm) between a bone's end and its last MRI slice, about 10 mm on
    average; more than that means the segmentation stops short."""
    out = {"lo": {}, "hi": {}}
    for name, g, k in (("femur", gt_fem, 2), ("tibia_fibula", gt_tib, 4)):
        mask, _, _ = floor_pieces(floor["v"], floor["faces"], g, k)
        fv = floor["v"][mask]
        for side, gs, fs in (("lo", g[g[:, axis] < midline], fv[fv[:, axis] < midline]),
                             ("hi", g[g[:, axis] >= midline], fv[fv[:, axis] >= midline])):
            out[side][f"{name}_top"] = round(1000 * float(fs[:, 2].max() - gs[:, 2].max()), 1)
            out[side][f"{name}_bottom"] = round(1000 * float(gs[:, 2].min() - fs[:, 2].min()), 1)
    return out


def score_subject(z, names, s, osso, skel_models):
    sex, sid = s.split("/")[2], s.split("/")[3]

    def read(name):
        return read_ply(z.read(f"{s}/{name}"))
    gt = read("per_part_pc/Femur_pc.ply")["v"]
    axis, g_lo, g_hi = split_sides(gt)
    midline = (g_lo[:, axis].max() + g_hi[:, axis].min()) / 2
    sm = skel_models[sex]
    bone_names = [str(x) for x in sm["bone_names"]]
    vlab = np.argmax(sm["skel_weights_rigid"], axis=1)
    skel = read("skel.ply")
    toes = np.isin(vlab, [i for i, b in enumerate(bone_names) if b.startswith("toes")])
    heel = np.isin(vlab, [i for i, b in enumerate(bone_names) if b.startswith("calcn")])
    other = 1 - axis if axis in (0, 1) else 0
    anterior = float(np.sign(skel["v"][toes, other].mean() - skel["v"][heel, other].mean()))  # the toes point forward
    row = {"subject": sid, "sex": sex, "sides": {}}
    gt_side = {"lo": g_lo, "hi": g_hi}
    medial = {"lo": 1.0, "hi": -1.0}             # toward the midline along the lateral axis
    osso_faces, osso_face_part = osso_layout(osso)
    osso_names = [str(x) for x in osso["names"]]
    floor = read("skel_mri.ply")
    meshes = {}
    for method in METHODS:
        m = {"skel": skel, "skel_mri": floor}.get(method) or read(f"{method}.ply")
        v, f = m["v"], m["faces"]
        if method in ("skel", "skel_j"):
            if len(v) != len(vlab):
                raise ValueError(f"{sid} {method}: not SKEL's template topology")
            fem = np.isin(vlab, [i for i, b in enumerate(bone_names) if b.startswith("femur")])
            faces = f[fem[f].all(1)]
        elif method == "osso":
            if not np.array_equal(f, osso_faces):
                raise ValueError(f"{sid} osso: not OSSO's parts laid end to end")
            faces = f[np.isin(osso_face_part, [osso_names.index(n) for n in ("LeftLeg1", "RightLeg1")])]
        else:
            faces = floor_femur_faces(v, f, gt)
        meshes[method] = femur_sides(v, faces, midline, axis)
    ends = bone_ends(floor, gt, read("per_part_pc/Tibia-Fibula_pc.ply")["v"], midline, axis)
    for side in ("lo", "hi"):
        g = head_centre(_swap(gt_side[side], axis), medial[side])
        top = gt_side[side][:, 2].max()
        cap = gt_side[side][np.abs(gt_side[side][:, 2] - top) < 1e-4]
        cap_mm = 1000 * max(np.ptp(cap[:, 0]), np.ptp(cap[:, 1]))
        reach_mm = 1000 * (g["centre"][2] + g["radius_mm"] / 1000 - top)
        rec = {"mri": _clean(g), "top_slice_mm": round(cap_mm, 1), "sphere_top_above_top_slice_mm": round(reach_mm, 1),
               "head_complete": bool(cap_mm <= CAP_MM and -5 <= reach_mm <= 10), "floor_overshoot_mm": ends[side],
               "methods": {}}
        floor_v, floor_f = meshes["skel_mri"][side]
        span = float(np.ptp(floor_v @ np.linalg.svd(floor_v - floor_v.mean(0), full_matrices=False)[2][0]))
        rec["floor_femur_length_mm"] = round(1000 * span, 1)
        for method, sides in meshes.items():
            mv, mf = sides[side]
            c_sl = head_centre(_swap(sliced(mv, mf), axis), medial[side])
            c_de = head_centre(_swap(dense(mv, mf), axis), medial[side])
            err = c_sl["centre"] - g["centre"]
            rec["methods"][method] = {
                "sliced": _clean(c_sl), "unsliced": _clean(c_de),
                "error_mm": _components(err, medial[side], anterior),
                "slicing_shift_mm": _components(c_sl["centre"] - c_de["centre"], medial[side], anterior)}
        row["sides"][side] = rec
    print(sid, "complete heads:", sum(r["head_complete"] for r in row["sides"].values()), flush=True)
    return row


def _swap(p, axis):
    """Points with the lateral axis as y (the code above reads medial along y)."""
    if axis == 1:
        return p
    q = p.copy()
    q[:, [0, 1]] = q[:, [1, 0]]
    return q


def _clean(c):
    return {k: (np.round(1000 * v, 2).tolist() if k == "centre" else v) for k, v in c.items()}


def _components(d, medial, anterior):
    """A centre difference (m, lateral axis as y) as anterior, medial, superior and distance, mm."""
    return {"anterior": round(1000 * float(d[0] * anterior), 2), "medial": round(1000 * float(d[1] * medial), 2),
            "superior": round(1000 * float(d[2]), 2), "distance": round(1000 * float(np.linalg.norm(d)), 2)}


def run(args):
    release, skel_dir, osso_dir, subjects = inputs(args)
    osso = np.load(osso_dir / "skeleton_model.npz", allow_pickle=False)
    skel_models = {sex: np.load(skel_dir / f"skel_{sex}.npz", allow_pickle=False) for sex in ("female", "male")}
    rows, failed = [], []
    with zipfile.ZipFile(release) as z:
        names = set(z.namelist())
        for s in subjects:
            try:
                rows.append(score_subject(z, names, s, osso, skel_models))
            except ValueError as e:                  # recorded, not hidden: the subject is left out and listed
                failed.append({"subject": s.split("/")[3], "error": str(e)})
                print("FAILED", e, flush=True)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"subjects": rows, "failed": failed}, indent=1))
    print(f"{len(rows)} subjects, {len(failed)} failed -> {out}")


def _stats(x):
    x = np.asarray(x)
    return {"mean": round(float(x.mean()), 2), "sd": round(float(x.std(ddof=1)), 2),
            "median": round(float(np.median(x)), 2), "p90": round(float(np.percentile(x, 90)), 2)}


def summarize(path, out_path):
    b = json.load(open(path))
    every = [s for r in b["subjects"] for s in r["sides"].values()]
    sides = [s for s in every if s["head_complete"]]
    n_subj = sum(any(s["head_complete"] for s in r["sides"].values()) for r in b["subjects"])
    ends = {k: np.array([s["floor_overshoot_mm"][k] for s in every]) for k in every[0]["floor_overshoot_mm"]}
    out = {"n_subjects": len(b["subjects"]), "n_sides": len(every), "n_failed": len(b["failed"]),
           "target_mm": TARGET_MM, "notes": [
               "Hip centre = sphere fitted to the femoral head, the same code on the MRI femur, each prediction and "
               "the floor; predictions are cut at the MRI's slice planes (20 mm apart) and sampled on its 2.1 mm grid "
               "first.",
               f"Only sides whose MRI femur keeps the top of its head are scored: the top slice at most {CAP_MM} mm "
               "across (a cap) and the fitted sphere's top within -5..+10 mm of it. Elsewhere the head's upper part is "
               "not in the segmentation and a centre fitted to what is left sits too low.",
               "Error = prediction minus MRI, mm: anterior, medial (toward the midline) and superior components.",
               "skel_mri (the floor) is SKEL-J fitted to the MRI bones: its error is what this ground truth can "
               "resolve.",
               "slicing_shift = sliced minus unsliced centre on the same mesh: what the 20 mm slicing alone moves.",
               "Relative error uses the floor femur's length (fitted to the person's bones, not quantised by slices).",
               "Hip only: knee and ankle centres are not defined well enough on 20 mm slices.",
               "One cohort, lying down, arms overhead; SKEL-J was trained on this cohort, SKEL and OSSO were not."],
           "segmentation": {
               "complete_heads": f"{len(sides)}/{len(every)} sides, {n_subj} subjects",
               "top_slice_mm_all_sides": _stats([s["top_slice_mm"] for s in every]),
               "floor_reaches_beyond_mri_mm": {k: {"median": round(float(np.median(v)), 1),
                                                   "over_10mm": f"{int((v > 10).sum())}/{len(v)}"}
                                               for k, v in ends.items()}},
           "mri_head": {"radius_mm": _stats([s["mri"]["radius_mm"] for s in sides]),
                        "fit_rms_mm": _stats([s["mri"]["fit_rms_mm"] for s in sides]),
                        "slices_used": _stats([s["mri"]["slices"] for s in sides])},
           "floor_femur_length_mm": _stats([s["floor_femur_length_mm"] for s in sides]), "methods": {}}
    for m in METHODS:
        e = [s["methods"][m]["error_mm"] for s in sides]
        comp = {k: np.array([x[k] for x in e]) for k in ("anterior", "medial", "superior", "distance")}
        bias = np.array([comp["anterior"].mean(), comp["medial"].mean(), comp["superior"].mean()])
        resid = np.column_stack([comp["anterior"], comp["medial"], comp["superior"]]) - bias
        rel = comp["distance"] / np.array([s["floor_femur_length_mm"] for s in sides]) * 100
        out["methods"][m] = {
            "distance_mm": _stats(comp["distance"]),
            "within_target": f"{int((comp['distance'] <= TARGET_MM).sum())}/{len(sides)}",
            "bias_mm": {k: _stats(comp[k]) for k in ("anterior", "medial", "superior")},
            "bias_vector_length_mm": round(float(np.linalg.norm(bias)), 2),
            "scatter_after_bias_rms_mm": round(float(np.sqrt((resid ** 2).sum(1).mean())), 2),
            "distance_pct_of_femur_length": _stats(rel),
            "slicing_shift_mm": _stats([s["methods"][m]["slicing_shift_mm"]["distance"] for s in sides]),
            "head_radius_mm": _stats([s["methods"][m]["sliced"]["radius_mm"] for s in sides]),
            "fit_rms_mm": _stats([s["methods"][m]["sliced"]["fit_rms_mm"] for s in sides])}
    out["paired_per_side"] = {}
    for a, c in (("skel_j", "skel"), ("osso", "skel"), ("osso", "skel_j")):
        d = np.array([s["methods"][a]["error_mm"]["distance"] - s["methods"][c]["error_mm"]["distance"] for s in sides])
        out["paired_per_side"][f"{a} - {c}"] = {"mean_mm": round(float(d.mean()), 2),
                                                "first_better_in": f"{int((d < 0).sum())}/{len(d)}",
                                                "wilcoxon_p": float(f"{wilcoxon(d).pvalue:.2g}")}
    fl = out["methods"]["skel_mri"]["distance_mm"]
    out["dataset_verdict"] = (
        f"On the {len(sides)} complete heads the floor (SKEL-J fitted to the MRI bones) lands {fl['mean']} mm from the "
        f"MRI hip centre on average (90th percentile {fl['p90']} mm). " + (
            f"That is above the {TARGET_MM:g} mm target, so this dataset cannot test it: predictors are ranked only at "
            "the precision the floor supports." if fl["p90"] > TARGET_MM else
            f"That is within the {TARGET_MM:g} mm target, so this ground truth can test it."))
    with open(out_path, "w") as fh:
        json.dump(out, fh, indent=1)
        fh.write("\n")
    print(json.dumps(out, indent=1))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--release", default=os.environ.get("BONES3D_ZIP"))
    r.add_argument("--skel-dir", default=os.environ.get("MODELS_NPZ"))
    r.add_argument("--osso-dir", default=os.environ.get("MODELS_NPZ"))
    r.add_argument("--out", default=os.environ.get("WORK") and str(Path(os.environ["WORK"]) / "mri_bones_3dbones"
                                                                   / "hip_subjects.json"))
    s = sub.add_parser("summarize")
    s.add_argument("subjects")
    s.add_argument("out")
    args = ap.parse_args()
    if args.cmd == "run":
        run(args)
    else:
        summarize(args.subjects, args.out)


if __name__ == "__main__":
    main()
