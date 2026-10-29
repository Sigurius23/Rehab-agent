"""Aggregate summary of run_bench.py's per-subject output (README.md in this folder): per method and bone, mean
point-to-mesh distance (mm) over subjects and by sex; paired tests between methods, overall and per bone; how the
error follows body size and soft tissue; femur and tibia length differences. Aggregates only: no subject ids leave
the per-subject file.

    python -I summarize.py $WORK/mri_bones_3dbones/subjects.json ../../results/mri_bones_3dbones.json"""
import json
import sys

import numpy as np
from scipy.stats import spearmanr, wilcoxon

METHODS = ["skel", "skel_j", "osso", "hit", "skel_mri"]
PARTS = ["Femur", "Tibia-Fibula", "Pelvis", "Humerus", "Radius-Ulna"]
PAIRS = (("skel_j", "skel"), ("skel_j", "osso"), ("skel", "osso"), ("skel_j", "hit"), ("osso", "skel"),
         ("osso", "skel_j"))
NOTES = [
    "Scored: the skin-only predictions shipped with the 3DBones release (MICCAI 2024); the methods were not re-run.",
    "Metric: mean distance from each MRI bone point to the predicted skeleton (point-to-triangle), one way. same_part "
    "measures to the predicted bone of that name; any_part to the nearest predicted bone (HIT and skel_mri carry no "
    "bone labels).",
    "skel_mri is the release's SKEL-J fitted to the MRI bones themselves: the floor for this model on this ground "
    "truth.",
    "One cohort (HIT MRI data), scanned lying down with the arms overhead; SKEL-J was trained on this cohort's "
    "training split, SKEL and OSSO were not.",
    "Ground truth slices are 20 mm apart: length differences are dominated by that quantisation and where the "
    "segmentation stops; they cannot validate segment lengths.",
    "Point-to-mesh distance is not joint-centre error.",
    "The SKEL column is the best case for person bones (a perfect body surface).",
]


def sig(p):
    """A p-value to two significant digits (a small one stays visible, not 0.0)."""
    return float(f"{float(p):.2g}")


def main():
    b = json.load(open(sys.argv[1]))
    rows = b["subjects"]
    out = {"n_subjects": len(rows), "n_female": sum(r["sex"] == "female" for r in rows),
           "n_male": sum(r["sex"] == "male" for r in rows), "n_failed": len(b["failed"]),
           "exactness_max_abs_diff_vs_brute_force_mm": max(c["max_abs_diff_vs_brute_force_mm"]
                                                           for c in b["exactness_checks"]),
           "notes": NOTES, "methods": {}}
    per_subject = {}
    for m in METHODS:
        have = [r for r in rows if m in r["methods"]]
        res = {"n": len(have)}
        for kind in ("any_part_mm", "same_part_mm"):
            if not have[0]["methods"][m][kind]:
                continue
            per = {p: np.array([r["methods"][m][kind][p] for r in have]) for p in PARTS}
            subj = np.mean([per[p] for p in PARTS], axis=0)
            female = np.array([r["sex"] == "female" for r in have])
            res[kind] = {"mean_over_bones": round(float(subj.mean()), 2),
                         "female": round(float(subj[female].mean()), 2), "male": round(float(subj[~female].mean()), 2),
                         "worst_subject": round(float(subj.max()), 2),
                         "per_bone": {p: round(float(v.mean()), 2) for p, v in per.items()},
                         "worst_single_bone": max(({"bone": p, "mm": round(float(v.max()), 2)} for p, v in per.items()),
                                                  key=lambda x: x["mm"])}
            per_subject[(m, kind)] = {"all": subj, **per, "ids": [r["subject"] for r in have]}
            if kind == "any_part_mm":
                for cov in ("body_volume_l", "bone_depth_mm", "thigh_depth_mm"):
                    rho, p = spearmanr([r[cov] for r in have], subj)
                    res[kind][f"vs_{cov}_spearman"] = [round(float(rho), 2), sig(p)]
                rho, p = spearmanr([r["thigh_depth_mm"] for r in have], per["Femur"])
                res[kind]["femur_vs_thigh_depth_spearman"] = [round(float(rho), 2), sig(p)]
                res[kind]["worst_three"] = [{"sex": have[i]["sex"], "body_volume_l": have[i]["body_volume_l"],
                                             "bone_depth_mm": have[i]["bone_depth_mm"], "mm": round(float(subj[i]), 2)}
                                            for i in np.argsort(subj)[::-1][:3]]
        if have[0]["methods"][m]["length_err_mm"]:
            res["length_minus_mri_mm"] = {}
            for p in ("Femur", "Tibia-Fibula"):
                e = np.array([x for r in have for x in r["methods"][m]["length_err_mm"][p]])
                res["length_minus_mri_mm"][p] = {"mean": round(float(e.mean()), 1),
                                                 "mean_abs": round(float(np.abs(e).mean()), 1),
                                                 "sd": round(float(e.std()), 1), "n_sides": len(e)}
        out["methods"][m] = res

    def paired(a, c, kind, part):
        A, C = per_subject[(a, kind)], per_subject[(c, kind)]
        assert A["ids"] == C["ids"]
        d = A[part] - C[part]
        return {"mean_mm": round(float(d.mean()), 2), "first_better_in": f"{int((d < 0).sum())}/{len(d)}",
                "wilcoxon_p": sig(wilcoxon(d).pvalue)}
    out["paired_any_part"] = {f"{a} - {c}": paired(a, c, "any_part_mm", "all") for a, c in PAIRS[:4]}
    out["paired_per_bone_same_part"] = {f"{a} - {c}": {p: paired(a, c, "same_part_mm", p) for p in PARTS}
                                        for a, c in (("osso", "skel"), ("osso", "skel_j"), ("skel_j", "skel"))}
    out["population"] = {k: [min(r[k] for r in rows), max(r[k] for r in rows)]
                         for k in ("body_volume_l", "bone_depth_mm", "thigh_depth_mm")}
    with open(sys.argv[2], "w") as f:
        json.dump(out, f, indent=1)
        f.write("\n")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
