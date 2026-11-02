"""Leg priors side by side on the 3DBones test subjects (README.md in this folder): how far apart SKEL, SKEL-J and OSSO
put the hip, knee and ankle centres of the same leg, and what that does to thigh length, shank length and hip width.

No ground truth decides between them here (hip_centres.py: this MRI cannot test 5 mm, and knee and ankle centres are
not defined on its 20 mm slices). Their disagreement is still informative: where two priors differ by d, at least one
is off by d/2 or more. The skeleton fitted to the MRI bones (the floor) is compared the same way, as the skeleton that
saw the bones, not as truth: where the MRI stops short (femoral heads, tibia ends) it is the model filling in.

Every centre comes from the same geometry on every mesh, from the dense bone surface:
  hip    centre of a sphere fitted to the femoral head (hip_centres.head_centre)
  knee   midpoint of the femoral epicondyles: the most medial and lateral femur points within 40 mm of its distal end
  ankle  midpoint of the malleoli: the most medial and lateral tibia-fibula points within 30 mm of its distal end
The femur is its label's largest piece (OSSO's thigh part also holds the patella). These are not the joint centres
SKEL itself regresses, which person bones uses.

    python -I leg_priors.py run --release mri_bones_release_v2.zip --skel-dir models_npz --osso-dir models_npz \
        --out $WORK/mri_bones_3dbones/leg_subjects.json [--workers 4]
    python -I leg_priors.py summarize $WORK/mri_bones_3dbones/leg_subjects.json \
        ../../results/mri_bones_3dbones_legs.json

Paths default to $BONES3D_ZIP, $MODELS_NPZ and $WORK as in run_bench.py. Per-subject output stays in $WORK."""
import argparse
import json
import multiprocessing
import os
import sys
import zipfile
from itertools import combinations
from pathlib import Path

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.stats import wilcoxon

sys.path.insert(0, str(Path(__file__).parent))
from hip_centres import _components, _swap, dense, floor_pieces, head_centre  # noqa: E402
from run_bench import inputs, osso_layout, read_ply, split_sides  # noqa: E402

METHODS = ("skel", "skel_j", "osso", "skel_mri")
PRIORS = ("skel", "skel_j", "osso")
JOINTS = ("hip", "knee", "ankle")
KNEE_BAND, ANKLE_BAND = 0.040, 0.030


def largest_piece(v, f):
    """The biggest connected piece of a submesh."""
    n = len(v)
    A = coo_matrix((np.ones(3 * len(f)), (np.r_[f[:, 0], f[:, 1], f[:, 2]], np.r_[f[:, 1], f[:, 2], f[:, 0]])),
                   shape=(n, n))
    lab = connected_components(A, directed=False)[1]
    keep = np.bincount(lab[f[:, 0]]).argmax()
    ff = f[lab[f[:, 0]] == keep]
    used, inv = np.unique(ff, return_inverse=True)
    return v[used], inv.reshape(-1, 3)


def side_mesh(v, faces, mask_side):
    ff = faces[mask_side[faces].all(1)]
    used, inv = np.unique(ff, return_inverse=True)
    return v[used], inv.reshape(-1, 3)


def epicondyle_midpoint(p, band):
    """Midpoint of the most medial and most lateral points (lateral axis = y) within `band` of the distal end."""
    end = p[p[:, 2] < p[:, 2].min() + band]
    return (end[end[:, 1].argmin()] + end[end[:, 1].argmax()]) / 2


def leg_centres(fem_v, fem_f, shank_v, shank_f, axis, medial):
    fv, ff = largest_piece(fem_v, fem_f)
    fem = _swap(dense(fv, ff), axis)
    shank = _swap(dense(shank_v, shank_f), axis)
    hip = head_centre(fem, medial)
    return {"hip": hip["centre"], "knee": epicondyle_midpoint(fem, KNEE_BAND),
            "ankle": epicondyle_midpoint(shank, ANKLE_BAND), "head_fit_rms_mm": hip["fit_rms_mm"]}


def score_subject(z, s, osso, skel_models):
    sex, sid = s.split("/")[2], s.split("/")[3]

    def read(name):
        return read_ply(z.read(f"{s}/{name}"))
    gt_fem, gt_tib = read("per_part_pc/Femur_pc.ply")["v"], read("per_part_pc/Tibia-Fibula_pc.ply")["v"]
    axis, g_lo, g_hi = split_sides(gt_fem)
    midline = (g_lo[:, axis].max() + g_hi[:, axis].min()) / 2
    sm = skel_models[sex]
    bone_names = [str(x) for x in sm["bone_names"]]
    vlab = np.argmax(sm["skel_weights_rigid"], axis=1)
    skel = read("skel.ply")
    toes = np.isin(vlab, [i for i, b in enumerate(bone_names) if b.startswith("toes")])
    heel = np.isin(vlab, [i for i, b in enumerate(bone_names) if b.startswith("calcn")])
    anterior = float(np.sign(skel["v"][toes, 1 - axis].mean() - skel["v"][heel, 1 - axis].mean()))
    osso_faces, osso_face_part = osso_layout(osso)
    osso_names = [str(x) for x in osso["names"]]
    medial = {"lo": 1.0, "hi": -1.0}
    row = {"subject": sid, "sex": sex, "anterior_sign": anterior, "methods": {}}
    for method in METHODS:
        m = skel if method == "skel" else read(f"{method}.ply")
        v, f = m["v"], m["faces"]
        if method in ("skel", "skel_j"):
            if len(v) != len(vlab):
                raise ValueError(f"{sid} {method}: not SKEL's template topology")
            fem = np.isin(vlab, [i for i, b in enumerate(bone_names) if b.startswith("femur")])
            shk = np.isin(vlab, [i for i, b in enumerate(bone_names) if b.startswith("tibia")])
        elif method == "osso":
            if not np.array_equal(f, osso_faces):
                raise ValueError(f"{sid} osso: not OSSO's parts laid end to end")
            fem, shk = np.zeros(len(v), bool), np.zeros(len(v), bool)
            for names, mask in ((("LeftLeg1", "RightLeg1"), fem), (("LeftLeg2", "RightLeg2"), shk)):
                ff = f[np.isin(osso_face_part, [osso_names.index(n) for n in names])]
                mask[np.unique(ff)] = True
        else:
            fem = floor_pieces(v, f, gt_fem, 2)[0]
            shk = floor_pieces(v, f, gt_tib, 4)[0]
        res = {}
        for side in ("lo", "hi"):
            on_side = (v[:, axis] < midline) if side == "lo" else (v[:, axis] >= midline)
            c = leg_centres(*side_mesh(v, f, fem & on_side), *side_mesh(v, f, shk & on_side), axis, medial[side])
            res[side] = {j: c[j] for j in JOINTS} | {"head_fit_rms_mm": c["head_fit_rms_mm"]}
        row["methods"][method] = res
    for side in ("lo", "hi"):
        for method in METHODS:
            c = row["methods"][method][side]
            c["thigh_mm"] = round(1000 * float(np.linalg.norm(c["hip"] - c["knee"])), 1)
            c["shank_mm"] = round(1000 * float(np.linalg.norm(c["knee"] - c["ankle"])), 1)
    for method in METHODS:
        r = row["methods"][method]
        r["hip_width_mm"] = round(1000 * float(np.linalg.norm(r["lo"]["hip"] - r["hi"]["hip"])), 1)
    row["pairs"] = {}
    for a, b in combinations(METHODS, 2):
        row["pairs"][f"{a} - {b}"] = {side: {j: _components(row["methods"][a][side][j] - row["methods"][b][side][j],
                                                            medial[side], anterior) for j in JOINTS}
                                      for side in ("lo", "hi")}
    for method in METHODS:
        for side in ("lo", "hi"):
            for j in JOINTS:
                row["methods"][method][side][j] = np.round(1000 * row["methods"][method][side][j], 2).tolist()
    print(sid, "thigh", "  ".join(f"{m} {row['methods'][m]['lo']['thigh_mm']:.0f}" for m in METHODS), flush=True)
    return row


def score_job(job):
    release, skel_dir, osso_dir, s = job
    osso = np.load(osso_dir / "skeleton_model.npz", allow_pickle=False)
    skel_models = {sex: np.load(skel_dir / f"skel_{sex}.npz", allow_pickle=False) for sex in ("female", "male")}
    with zipfile.ZipFile(release) as z:
        try:
            return {"row": score_subject(z, s, osso, skel_models)}
        except ValueError as e:                      # recorded, not hidden: the subject is left out and listed
            print("FAILED", e, flush=True)
            return {"failed": {"subject": s.split("/")[3], "error": str(e)}}


def run(args):
    release, skel_dir, osso_dir, subjects = inputs(args)
    with multiprocessing.get_context("spawn").Pool(args.workers) as pool:
        done = pool.map(score_job, [(release, skel_dir, osso_dir, s) for s in subjects], chunksize=1)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"subjects": [d["row"] for d in done if "row" in d],
                               "failed": [d["failed"] for d in done if "failed" in d]}, indent=1))
    print(f"{sum('row' in d for d in done)} subjects, {sum('failed' in d for d in done)} failed -> {out}")


def _stats(x):
    x = np.asarray(x, float)
    return {"mean": round(float(x.mean()), 2), "sd": round(float(x.std(ddof=1)), 2),
            "median": round(float(np.median(x)), 2), "p90": round(float(np.percentile(x, 90)), 2)}


def summarize(path, out_path):
    b = json.load(open(path))
    rows = b["subjects"]
    legs = [(r, side) for r in rows for side in ("lo", "hi")]
    out = {"n_subjects": len(rows), "n_legs": len(legs), "n_failed": len(b["failed"]), "notes": [
        "Leg priors side by side: the same geometry on every mesh (hip: femoral head sphere; knee: femoral epicondyle "
        "midpoint; ankle: malleolus midpoint), from each released skin-only prediction and from the floor.",
        "No ground truth decides between the priors here; where two differ by d, at least one is off by d/2 or more.",
        "skel_mri (the floor) saw the MRI bones but fills in where the segmentation stops short (femoral heads, tibia "
        "ends); it is a reference, not truth.",
        "Differences are first minus second, mm: anterior, medial (toward the midline), superior, distance.",
        "These centres are geometric, not the joint centres SKEL regresses (which person bones uses).",
        "One cohort, lying down, arms overhead; SKEL-J was trained on this cohort, SKEL and OSSO were not."],
        "segments_mm": {}, "pairs": {}}
    for m in METHODS:
        out["segments_mm"][m] = {
            "thigh": _stats([r["methods"][m][s]["thigh_mm"] for r, s in legs]),
            "shank": _stats([r["methods"][m][s]["shank_mm"] for r, s in legs]),
            "hip_width": _stats([r["methods"][m]["hip_width_mm"] for r in rows]),
            "head_fit_rms_mm": _stats([r["methods"][m][s]["head_fit_rms_mm"] for r, s in legs])}
    for key in rows[0]["pairs"]:
        a, c = key.split(" - ")
        rec = {}
        for j in JOINTS:
            e = [r["pairs"][key][s][j] for r, s in legs]
            rec[j] = {k: _stats([x[k] for x in e]) for k in ("distance", "anterior", "medial", "superior")}
        for seg in ("thigh", "shank"):
            d = np.array([r["methods"][a][s][f"{seg}_mm"] - r["methods"][c][s][f"{seg}_mm"] for r, s in legs])
            base = np.array([r["methods"][c][s][f"{seg}_mm"] for r, s in legs])
            rec[f"{seg}_length"] = {"difference_mm": _stats(d), "abs_difference_mm": _stats(np.abs(d)),
                                    "abs_difference_pct": _stats(100 * np.abs(d) / base),
                                    "wilcoxon_p": float(f"{wilcoxon(d).pvalue:.2g}")}
        d = np.array([r["methods"][a]["hip_width_mm"] - r["methods"][c]["hip_width_mm"] for r in rows])
        rec["hip_width"] = {"difference_mm": _stats(d), "wilcoxon_p": float(f"{wilcoxon(d).pvalue:.2g}")}
        out["pairs"][key] = rec
    spread = {j: [max(np.linalg.norm(np.subtract(r["methods"][a][s][j], r["methods"][c][s][j]))
                      for a, c in combinations(PRIORS, 2)) for r, s in legs] for j in JOINTS}
    out["largest_disagreement_among_priors_mm"] = {j: _stats(v) for j, v in spread.items()}
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
                                                                   / "leg_subjects.json"))
    r.add_argument("--workers", type=int, default=4)
    s = sub.add_parser("summarize")
    s.add_argument("subjects")
    s.add_argument("out")
    args = ap.parse_args()
    if args.cmd == "run":
        run(args)
    else:
        summarize(args.subjects, args.out)


if __name__ == "__main__":       # the worker processes import this file again
    main()
