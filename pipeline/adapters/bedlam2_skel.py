"""Bones from one depth frame: SKEL joint centres from an SMPL body fitted to synthetic Kinect v1 depth.

``rehabtwin person bones`` takes the person's bones from SKEL's anatomical joint centres for their SMPL body
surface (``rehabtwin/skel_bones.py``). This measures how well one standing depth frame determines those bones:

1. **Truth bodies:** for each BEDLAM2 test body that ``bedlam2.py shapefit`` uses (5 per size label, XS to 5XL,
   development bodies left out), an SMPL body of the same height and BMI (``skel_bones.betas_for_height_mass``)
   with its own proportions added (shape parameters 3-10 drawn from N(0, 0.7²)), female and male in turn.
   They are SMPL bodies from the start: carrying the BEDLAM2 (SMPL-X) bodies over to SMPL distorted them.
2. **Depth frame:** the body in that BEDLAM2 body's near-standing motion frame (body pose; hands at rest), on
   the floor, seen by a front-facing Kinect v1 2.7 m away with its noise (``bedlam2.synth_frame``).
3. **Fit:** ``rehabtwin.shape.fit_shape`` with the SMPL model of that sex, as ``person shape --smpl-model`` runs
   it; once without and once with the measured height (true height + N(0, 5 mm)).
4. **Bones:** SKEL joint centres for the fitted and the true shape; segment lengths and the per-body
   scale-factor measurements (``skel_bones.measures``) compared.

Baselines from the true height and mass alone: the SKEL template scaled to the height, and the SMPL body nearest
the mean shape with that height and mass.

This is the error of the measurement chain (sensor, fit) against SKEL's own prediction, not against bone:
whether SKEL's joint centres are where a person's are needs imaging.

    python adapters/bedlam2_skel.py run --smplx SMPLX_NEUTRAL.npz --smpl-dir SMPL_NPZ_DIR --skel-dir SKEL_NPZ_DIR \\
        --motions motions_npz_training/ --mapping b2_bedlam2amass_motion_training.csv --jobs 4 --out skel_bones.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bedlam2

SEXES = ("female", "male")
SMPL_FILES = {"female": "basicmodel_f_lbs_10_207_0_v1.1.0.npz", "male": "basicmodel_m_lbs_10_207_0_v1.1.0.npz"}
_W = {}


def _init(smpl_dir, skel_dir):
    bedlam2._rehabtwin()
    from rehabtwin import skel_bones
    _W["smpl"] = {s: skel_bones.load_smpl(os.path.join(smpl_dir, SMPL_FILES[s])) for s in SEXES}
    _W["skel"] = {s: skel_bones.load_skel(os.path.join(skel_dir, f"skel_{s}.npz")) for s in SEXES}


def smpl_pose(smplx_pose):
    """SMPL pose (72) from an SMPL-X pose (165): the root and 21 body joints, hands at rest."""
    return np.concatenate([np.asarray(smplx_pose, float)[:66], np.zeros(6)])


def bones(skel, smpl, betas):
    from rehabtwin import skel_bones
    P = skel_bones.joints(skel, skel_bones.rest_surface(smpl, betas))
    return skel_bones.segment_lengths(P), skel_bones.measures(P)


SOURCES = ("depth fit", "depth fit + measured height", "height and mass", "height only")


def truth_body(smpl, height_m, bmi, rng):
    """SMPL shape parameters of a body near ``height_m`` and ``bmi`` with its own proportions."""
    from rehabtwin import skel_bones
    b, _ = skel_bones.betas_for_height_mass(smpl, height_m, bmi * height_m ** 2)
    b[2:] += rng.normal(0, 0.7, len(b) - 2)
    return b


def body(job):
    """All results of one body: ``job`` = (index, ``bedlam2.pick_bodies`` entry, its SMPL-X height and BMI)."""
    from rehabtwin import shape, skel_bones
    t0 = time.time()
    k, item, hx, bmix = job
    sex = SEXES[k % 2]
    smpl, skel = _W["smpl"][sex], _W["skel"][sex]
    rng = np.random.default_rng(bedlam2._seed(item["body"], "skel truth"))
    out = {"body": item["body"], "size": item["size"], "sex": sex, "bedlam2_height_m": hx, "bedlam2_bmi": bmix}
    try:
        betas = truth_body(smpl, hx, bmix, rng)
    except ValueError as e:
        out["error"] = f"truth body: {e}"
        return out
    h, mass = skel_bones.body_measures(skel_bones.rest_surface(smpl, betas), smpl["f"])
    seg_t, mea_t = bones(skel, smpl, betas)
    path, fi, _, motion = item["frames"][0]
    d = np.load(path, allow_pickle=False)
    pose, trans = smpl_pose(d["poses"][fi]), np.asarray(d["trans"][fi], float).copy()
    v, _ = bedlam2.pose_body(smpl, betas, pose, trans)
    trans[1] -= v[:, 1].min()                                    # standing on the floor (y = 0)
    obs = bedlam2.synth_frame(smpl, betas, pose, trans, np.random.default_rng(bedlam2._seed(item["body"], "A", "skel")))
    out.update({"motion": motion, "frame": int(fi), "height_m": h, "mass_kg": mass, "bmi": mass / h ** 2,
                "betas_true": betas.tolist(), "segments": {"true": seg_t}, "measures": {"true": mea_t}, "fits": {}})
    frame = [{"points": obs["points"], "floor": obs["floor"], "keypoints_uv": obs["keypoints_uv"]}]
    given = h + np.random.default_rng(bedlam2._seed(item["body"], "height")).normal(0, 0.005)
    for src, height in (("depth fit", None), ("depth fit + measured height", given)):
        try:
            res = shape.fit_shape(shape.BodyModel(smpl), frame, bedlam2.KINECT_K, height_m=height)
        except (ValueError, IndexError, np.linalg.LinAlgError) as e:
            out["fits"][src] = {"error": f"{type(e).__name__}: {e}"}
            continue
        out["fits"][src] = {"height_m": res["height_m"], "mass_kg": res["mass_kg"], "warnings": res["fit"]["warnings"],
                            "betas": res["betas"]}
        out["segments"][src], out["measures"][src] = bones(skel, smpl, np.asarray(res["betas"]))
    b0 = np.zeros(10)
    seg0, mea0 = bones(skel, smpl, b0)
    h0, _ = skel_bones.body_measures(skel_bones.rest_surface(smpl, b0), smpl["f"])
    out["segments"]["height only"] = {k: v * h / h0 for k, v in seg0.items()}
    out["measures"]["height only"] = {k: v * h / h0 for k, v in mea0.items()}
    bhm, _ = skel_bones.betas_for_height_mass(smpl, h, mass)
    out["segments"]["height and mass"], out["measures"]["height and mass"] = bones(skel, smpl, bhm)
    out["runtime_s"] = round(time.time() - t0, 1)
    return out


def summarise(rows):
    """Per source and segment/measurement: bias, SD and mean absolute error (cm) against the true body's, all
    bodies, per sex and per BMI group."""
    ok = [r for r in rows if "error" not in r]
    groups = {"all": ok, "female": [r for r in ok if r["sex"] == "female"], "male": [r for r in ok if r["sex"] == "male"],
              **{lab: [r for r in ok if lo <= r["bmi"] < hi] for lab, lo, hi in bedlam2.FIT_BMI_BINS}}
    out = {"bodies": len(rows), "failed": [r["body"] for r in rows if "error" in r],
           "fit_failed": {s: [r["body"] for r in ok if "error" in r["fits"].get(s, {})] for s in SOURCES[:2]},
           "height_cm": {s: _stats([100 * (r["fits"][s]["height_m"] - r["height_m"]) for r in ok
                                    if "height_m" in r["fits"].get(s, {})]) for s in SOURCES[:2]}}
    for kind in ("segments", "measures"):
        out[kind] = {}
        for g, rs in groups.items():
            if not rs:
                continue
            out[kind][g] = {src: {k: _stats([100 * (r[kind][src][k] - r[kind]["true"][k]) for r in rs if src in r[kind]])
                                  for k in rs[0][kind]["true"]} for src in SOURCES}
    return out


def _stats(x):
    x = np.asarray(x, float)
    if not len(x):
        return {"n": 0}
    return {"n": len(x), "bias_cm": round(float(x.mean()), 2), "sd_cm": round(float(x.std(ddof=1)), 2) if len(x) > 1 else None,
            "mae_cm": round(float(np.abs(x).mean()), 2), "max_cm": round(float(np.abs(x).max()), 2)}


def run(smplx_path, smpl_dir, skel_dir, motion_dir, mapping_csv, jobs=1, per_size=5, seed=0):
    bedlam2._rehabtwin()
    from rehabtwin import shape
    smplx = bedlam2.load_smplx(smplx_path)
    bmx = shape.BodyModel(smplx)
    items = bedlam2.pick_bodies(bmx, smplx, motion_dir, mapping_csv, per_size, "test", seed)
    jobs_in = []
    for k, it in enumerate(items):
        h, _, _, bmi = shape.body_measures(bmx.rest(it["betas"])[0], bmx.faces)
        jobs_in.append((k, it, h, bmi))
    print(f"{len(items)} bodies", flush=True)
    rows = []
    if jobs > 1:
        import multiprocessing as mp
        for var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
            os.environ.setdefault(var, "1")
        with mp.get_context("spawn").Pool(jobs, _init, (smpl_dir, skel_dir)) as pool:
            for k, r in enumerate(pool.imap_unordered(body, jobs_in)):
                rows.append(r)
                print(f"  {k + 1}/{len(items)} {r['body']} {r.get('error', '')}", flush=True)
    else:
        _init(smpl_dir, skel_dir)
        for k, j in enumerate(jobs_in):
            rows.append(body(j))
            print(f"  {k + 1}/{len(items)} {j[1]['body']}", flush=True)
    return {"rows": rows, "summary": summarise(rows),
            "settings": {"split": "test", "per_size": per_size, "seed": seed, "sensor": "2.7 m in front, level at 1.0 m",
                         "truth": "SMPL body of the BEDLAM2 body's height and BMI, shape parameters 3-10 + N(0, 0.7^2)",
                         "measured height": "true + N(0, 5 mm)"}}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="SKEL bones from one synthetic depth frame vs the true body's")
    for a in ("--smplx", "--smpl-dir", "--skel-dir", "--motions", "--mapping", "--out"):
        r.add_argument(a, required=True)
    r.add_argument("--jobs", type=int, default=1)
    r.add_argument("--per-size", type=int, default=5)
    a = ap.parse_args(argv)
    res = run(a.smplx, a.smpl_dir, a.skel_dir, a.motions, a.mapping, a.jobs, a.per_size)
    with open(a.out, "w") as fh:
        json.dump(res, fh, indent=1)
    print(json.dumps({k: res["summary"][k] for k in ("bodies", "failed", "fit_failed", "height_cm")}, indent=1))


if __name__ == "__main__":
    main()
