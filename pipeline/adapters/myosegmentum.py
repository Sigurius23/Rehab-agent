"""MyoSegmenTUM thigh (Schlaeger et al. 2018, PLOS ONE, doi 10.1371/journal.pone.0198200) as a test of the muscle layer.

The database has water-fat MRI of both thighs of 15 healthy volunteers and 4 patients with neuromuscular disease.
It gives, per thigh and muscle group (quadriceps, sartorius, gracilis, hamstrings), the volume and the mean
proton-density fat fraction. HV001-HV003 were scanned three times. It also gives sex, age, height, weight and
maximum isometric knee-extension torque (Isomed 2000; seated, hip at 90°, knee at 60° and 90° flexion). That
makes it a test of ``rehabtwin/capacity.py`` against real people:

1. **Size:** each person's measured muscle volumes against the height-and-mass regression's.
2. **Strength:** measured torque against the model's isometric knee-extension moment at the same posture,
   with leg capacity from (a) the generic subject, (b) the regression, (c) the measured quadriceps volume and
   fat fraction. The model is the generic one scaled uniformly to the person's height (no motion capture here),
   so the moment arms are generic.

The published volumes (Table2) are wrong. They count mask voxels as 1 x 1 mm pixels (the real spacing is
0.78-1.02 mm, per stack), as 1 mm slices for the patients (the real spacing is 4 mm), and they count the
healthy volunteers' overlapping stack slices twice. ``volumes`` recomputes them from the masks with each stack's
DICOM geometry; the fat fractions in the table are right.

Data: the project's OSF page (the view-only key is in the paper's data availability statement). No licence is
stated on the project, so the data stays outside the repository:

    python adapters/myosegmentum.py volumes DATA_DIR --view-only KEY --out volumes.json   # 2.9 GB, zips deleted
    python adapters/myosegmentum.py analyse DATA_DIR --volumes volumes.json --out results.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

GROUPS = {"QF": "quadriceps", "HS": "hamstrings", "SA": "sartorius", "GR": "gracilis"}
MODEL_GROUPS = {"QF": ("recfem", "vaslat", "vasmed", "vasint"), "HS": ("bflh", "bfsh", "semimem", "semiten"),
                "SA": ("sart",), "GR": ("grac",)}
POSTURES = {"60": {"hip_flexion_r": 90, "knee_angle_r": 60}, "90": {"hip_flexion_r": 90, "knee_angle_r": 90}}


# ---- the scans: Table2's volumes are mask voxels x 4 mm³, as if every pixel were 1 x 1 mm (the masks' and
# NIfTI files' spacing), and the healthy volunteers' two stacks overlap by a few slices that both segment. The
# DICOM files carry the real pixel spacing (0.78-1.02 mm), so ``volumes`` recomputes them from the masks.

def read_mha(data):
    """(array (z, y, x), spacing (x, y, z) mm, header) of a MetaImage file's bytes."""
    import zlib
    head, pos = {}, 0
    while True:
        end = data.index(b"\n", pos)
        k, _, v = data[pos:end].decode("latin-1").partition("=")
        pos = end + 1
        head[k.strip()] = v.strip()
        if k.strip() == "ElementDataFile":
            break
    body = data[pos:]
    if head.get("CompressedData", "False") == "True":
        body = zlib.decompress(body)
    types = {"MET_UCHAR": np.uint8, "MET_CHAR": np.int8, "MET_USHORT": np.uint16, "MET_SHORT": np.int16,
             "MET_FLOAT": np.float32}
    dims = [int(x) for x in head["DimSize"].split()]
    return (np.frombuffer(body, types[head["ElementType"]]).reshape(dims[::-1]),
            [float(x) for x in head["ElementSpacing"].split()], head)


def _ds_values(data, tag):
    import re
    import struct
    out = []
    for m in re.finditer(re.escape(tag) + rb"DS", data):
        n = struct.unpack("<H", data[m.end():m.end() + 2])[0]
        out.append(data[m.end() + 2:m.end() + 2 + n].decode("latin-1").strip())
    return out


def dicom_geometry(data):
    """((row, column) pixel spacing mm, slice spacing mm) of an explicit-VR multi-frame DICOM file: PixelSpacing
    (0028,0030) and SpacingBetweenSlices (0018,0088), else SliceThickness (0018,0050). The patients' scans have
    8 mm slices every 4 mm. The masks' own headers claim 1 mm pixels (and, for the patients, 1 mm slices),
    which the published volumes inherited."""
    ps = _ds_values(data, b"\x28\x00\x30\x00")
    dz = _ds_values(data, b"\x18\x00\x88\x00") or _ds_values(data, b"\x18\x00\x50\x00")
    if not ps or not dz:
        raise ValueError("no PixelSpacing or slice spacing in the DICOM header")
    r, c = (float(v) for v in ps[0].split("\\"))
    return (r, c), float(dz[0])


def read_nifti(data):
    """NIfTI-1 image as a float array (z, y, x), scaled by scl_slope/scl_inter."""
    import struct
    e = "<" if struct.unpack("<i", data[:4])[0] == 348 else ">"
    dim = struct.unpack(e + "8h", data[40:56])
    dtype = {2: "u1", 4: "i2", 8: "i4", 16: "f4", 64: "f8", 512: "u2"}[struct.unpack(e + "h", data[70:72])[0]]
    off = int(struct.unpack(e + "f", data[108:112])[0])
    slope, inter = struct.unpack(e + "2f", data[112:120])
    n = dim[1] * dim[2] * dim[3]
    a = np.frombuffer(data[off:], np.dtype(dtype).newbyteorder(e), count=n).astype(float)
    a = a.reshape(dim[3], dim[2], dim[1])
    return a * slope + inter if slope not in (0.0,) else a


def scan_volumes(zip_path):
    """{side: {group: {"volume_cm3", "pdff", "stacks", "slices"}}} of one scan zip, from its masks: real pixel
    spacing from each stack's DICOM, each world slice counted once where stacks overlap, PDFF (FATFRACTION image)
    averaged over the counted voxels."""
    import re
    import zipfile
    z = zipfile.ZipFile(zip_path)
    names = [n for n in z.namelist() if "__MACOSX" not in n]
    stacks = sorted({int(m.group(1)) for n in names for m in [re.search(r"_stack(\d+)_[RL]_[A-Z]{2}\.mha$", n)] if m})
    spacing, ff = {}, {}
    for k in stacks:
        dcm = next(n for n in names if re.search(rf"FATFRACTION_stack{k}\.dcm$", n))
        with z.open(dcm) as fh:
            spacing[k] = dicom_geometry(fh.read())
        nii = next((n for n in names if re.search(rf"FATFRACTION_stack{k}\.nii$", n)), None)
        ff[k] = read_nifti(z.read(nii)) if nii else None
    out = {}
    for side in ("R", "L"):
        for g in GROUPS:
            claimed, vol, ffsum, nvox, used = set(), 0.0, 0.0, 0, 0
            for k in stacks:                       # stack 1 is the upper thigh; later stacks give only new slices
                f = next((n for n in names if n.endswith(f"_stack{k}_{side}_{g}.mha")), None)
                if f is None:
                    continue
                a, _, head = read_mha(z.read(f))      # its spacing claims 1 mm: the DICOM's is used
                (pr, pc), dz = spacing[k]
                z0 = float(head["Offset"].split()[2])
                dz *= float(head.get("TransformMatrix", "1 0 0 0 1 0 0 0 1").split()[8])
                for i in np.nonzero((a > 0).reshape(a.shape[0], -1).any(axis=1))[0]:
                    key = round((z0 + dz * i) / abs(dz))          # a slice position, in slice steps
                    if key in claimed:
                        continue
                    claimed.add(key)
                    m = a[i] > 0
                    vol += m.sum() * pr * pc * abs(dz)
                    if ff[k] is not None and ff[k].shape == a.shape:
                        ffsum += ff[k][i][m].sum()
                        nvox += int(m.sum())
                used += 1
            if claimed:
                out.setdefault(side, {})[g] = {"volume_cm3": vol / 1000, "pdff": ffsum / nvox / 100 if nvox else None,
                                               "stacks": used, "slices": len(claimed)}
    return out


def _rehabtwin():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _num(s):
    s = s.strip().replace(",", ".")
    return float(s) if s else None


def read_subjects(path):
    """Table1.csv: {id: sex, age, mass_kg, height_m, disease, strength_Nm {R60, R90, L90}} (the column labels)."""
    lines = Path(path).read_text(encoding="latin-1").splitlines()
    out = {}
    for line in lines[1:]:
        c = line.split(";")
        if not c[0].strip():
            continue
        out[c[0]] = {"sex": c[1], "age": _num(c[2]), "mass_kg": _num(c[3]), "height_m": _num(c[4]) / 100,
                     "disease": c[5] or None,
                     "strength_Nm": {k: _num(v) for k, v in zip(("R60", "R90", "L90"), c[6:9]) if _num(v) is not None}}
    return out


def read_scans(path):
    """Table2.csv: {scan id: {side: {group: {"volume_cm3", "pdff"}}}}, stacks summed (PDFF volume-weighted)."""
    lines = Path(path).read_text(encoding="latin-1").splitlines()
    head = lines[0].split(";")
    scans, cur = {}, None
    for line in lines[1:]:
        c = line.split(";")
        if not c[0].strip():
            continue
        if not c[0].startswith("stack"):
            cur = scans.setdefault(c[0], [])
            continue
        cur.append({h: _num(v) for h, v in zip(head[1:], c[1:])})
    out = {}
    for scan, stacks in scans.items():
        out[scan] = {}
        for side in ("R", "L"):
            for g in GROUPS:
                v = [s[f"{side}_{g}_V [mm3]"] for s in stacks if s.get(f"{side}_{g}_V [mm3]")]
                f = [s[f"{side}_{g}_PDFF_mean"] for s in stacks if s.get(f"{side}_{g}_V [mm3]")]
                if v:
                    out[scan].setdefault(side, {})[g] = {"volume_cm3": sum(v) / 1000,
                                                         "pdff": float(np.dot(v, f) / sum(v)) / 100, "stacks": len(v)}
    return out


def reference_volumes(generic_model):
    """{group: one leg's volume (cm³) in the generic model}, V = Fmax · lopt / σ (rehabtwin/capacity.py)."""
    _rehabtwin()
    from rehabtwin import capacity
    from rehabtwin.opensim_stage import _osim
    m = _osim().Model(str(generic_model))
    ms = m.getMuscles()
    v = lambda n: ms.get(n).getMaxIsometricForce() * ms.get(n).getOptimalFiberLength() * 100 / capacity.SIGMA_N_PER_CM2
    return {g: sum(v(b + "_r") for b in members) for g, members in MODEL_GROUPS.items()}


def scaled_model(generic_model, height_m, mass_kg, out_path):
    """The generic model scaled uniformly to a height (the reference subject's 1.70 m) and a mass."""
    _rehabtwin()
    from rehabtwin import capacity
    from rehabtwin.opensim_stage import _osim
    osim = _osim()
    model = osim.Model(str(generic_model))
    state = model.initSystem()
    s = height_m / capacity.REFERENCE["height_m"]
    ss = osim.ScaleSet()
    bodies = model.getBodySet()
    for i in range(bodies.getSize()):
        sc = osim.Scale()
        sc.setSegmentName(bodies.get(i).getName())
        sc.setScaleFactors(osim.Vec3(s, s, s))
        sc.setApply(True)
        ss.cloneAndAppend(sc)
    model.scale(state, ss, True, mass_kg)
    model.printToXML(str(out_path))
    return out_path


def knee_extension_Nm(model_path, posture):
    """Isometric knee-extension moment (N·m) of all muscles acting that way, at full activation."""
    _rehabtwin()
    from rehabtwin import strength
    from rehabtwin.opensim_stage import _osim
    test = strength.parse_test({"action": "knee_extension_r", "torque_Nm": 1.0, "posture_deg": posture},
                               strength.load_actions())
    return float(sum(strength.isometric_moments(_osim().Model(str(model_path)), test).values()))


def _stats(measured, predicted):
    m, p = np.asarray(measured, float), np.asarray(predicted, float)
    ratio = m / p
    r = float(np.corrcoef(m, p)[0, 1]) if len(m) > 2 else None
    # error once the common bias (specific tension, moment arms, voluntary activation) is divided out
    rel = ratio / ratio.mean() - 1
    return {"n": len(m), "ratio_mean": round(float(ratio.mean()), 3), "ratio_cv": round(float(ratio.std(ddof=1) / ratio.mean()), 3),
            "r": round(r, 3) if r is not None else None, "rms_after_bias_pct": round(float(np.sqrt(np.mean(rel ** 2)) * 100), 1)}


def analyse(data_dir, work_dir=None, volumes_path=None):
    _rehabtwin()
    import tempfile

    from rehabtwin import capacity
    from rehabtwin.config import load_config, resolve
    d = Path(data_dir)
    subjects = read_subjects(d / "Table1.csv")
    scans = json.loads(Path(volumes_path).read_text()) if volumes_path else read_scans(d / "Table2.csv")
    generic = resolve(load_config("skel105_pose2sim")["model"])
    ref = reference_volumes(generic)
    work = Path(work_dir or tempfile.mkdtemp(prefix="myoseg_"))
    work.mkdir(parents=True, exist_ok=True)
    rows = []
    for sid, s in subjects.items():
        scan = scans.get(f"{sid}_1")
        if not scan:
            continue
        ratio = capacity.limb_muscle_volume_cm3(s["mass_kg"], s["height_m"]) / capacity.limb_muscle_volume_cm3(
            capacity.REFERENCE["mass_kg"], capacity.REFERENCE["height_m"])
        row = {"id": sid, "healthy": s["disease"] is None, "sex": s["sex"], "age": s["age"], "mass_kg": s["mass_kg"],
               "height_m": s["height_m"], "strength_Nm": s["strength_Nm"],
               "repeats": [k for k in scans if k.startswith(sid + "_")],
               "measured": scan, "predicted_cm3": {g: ref[g] * ratio for g in GROUPS}}
        if s["disease"] is None:      # strength was measured in healthy volunteers only
            base = scaled_model(generic, s["height_m"], s["mass_kg"], work / f"{sid}_scaled.osim")
            qf = scan["R"]["QF"]
            models = {"generic": base,
                      "regression": work / f"{sid}_regression.osim",
                      "imaging": work / f"{sid}_imaging.osim"}
            capacity.scale_model(base, generic, s["mass_kg"], s["height_m"], models["regression"])
            capacity.scale_model(base, generic, s["mass_kg"], s["height_m"], models["imaging"], imaging={
                "method": "MyoSegmenTUM", "muscles": {"quadriceps_r": {"volume_cm3": qf["volume_cm3"],
                                                                       "fat_fraction": qf["pdff"]}}})
            row["model_Nm"] = {k: {a: round(knee_extension_Nm(p, POSTURES[a]), 1) for a in POSTURES}
                               for k, p in models.items()}
        rows.append(row)
        print(sid, "done", file=sys.stderr)
    return {"rows": rows, "reference_volumes_cm3": ref, "summary": summarise(rows, scans)}


def summarise(rows, scans):
    hv = [r for r in rows if r["healthy"]]
    out = {"size": {}, "strength": {}, "test_retest": {}, "fat_fraction": {}}
    sets = {"healthy": hv, "healthy HV001-HV011 (sequence A)": [r for r in hv if r["id"] <= "HV011"],
            "healthy HV012-HV015 (sequence B)": [r for r in hv if r["id"] > "HV011"],
            "patients": [r for r in rows if not r["healthy"]]}
    for g, name in GROUPS.items():
        for label, grp in sets.items():
            meas = [r["measured"][side][g]["volume_cm3"] for r in grp for side in ("R", "L") if g in r["measured"].get(side, {})]
            pred = [r["predicted_cm3"][g] for r in grp for side in ("R", "L") if g in r["measured"].get(side, {})]
            if len(meas) > 2:
                out["size"].setdefault(name, {})[label] = _stats(meas, pred)
        reps = {}
        for k, sc in scans.items():
            sid = k.rsplit("_", 1)[0]
            if g in sc.get("R", {}):
                reps.setdefault(sid, []).append(sc["R"][g]["volume_cm3"])
        cvs = [np.std(v, ddof=1) / np.mean(v) for v in reps.values() if len(v) > 1]
        if cvs:
            out["test_retest"][GROUPS[g]] = {"subjects": len(cvs), "volume_cv_pct": round(float(np.mean(cvs)) * 100, 1)}
        for label, grp in (("healthy", hv), ("patients", [r for r in rows if not r["healthy"]])):
            ff = [r["measured"][side][g]["pdff"] for r in grp for side in ("R", "L") if g in r["measured"].get(side, {})]
            if ff:
                out["fat_fraction"].setdefault(GROUPS[g], {})[label] = {
                    "mean_pct": round(float(np.mean(ff)) * 100, 1), "min_pct": round(float(np.min(ff)) * 100, 1),
                    "max_pct": round(float(np.max(ff)) * 100, 1)}
    # strength: HV001-HV011 have R60 and R90 under unambiguous labels; HV012-HV015 are reported separately
    # (the paper says 60° bilaterally, the tables label them 90°)
    for angle in ("60", "90"):
        sel = [r for r in hv if f"R{angle}" in r["strength_Nm"] and "model_Nm" in r and r["id"] <= "HV011"]
        meas = [r["strength_Nm"][f"R{angle}"] for r in sel]
        out["strength"][f"knee {angle}°, HV001-HV011"] = {
            k: _stats(meas, [r["model_Nm"][k][angle] for r in sel]) for k in ("generic", "regression", "imaging")}
    late = [r for r in hv if r["id"] > "HV011" and "model_Nm" in r and "R90" in r["strength_Nm"]]
    for angle in ("60", "90"):
        sel = [r for r in hv if r["id"] <= "HV011" and f"R{angle}" in r["strength_Nm"]] + late
        meas = [r["strength_Nm"][f"R{angle}"] if r["id"] <= "HV011" else r["strength_Nm"]["R90"] for r in sel]
        out["strength"][f"knee {angle}°, + HV012-HV015 read as {angle}°"] = {
            k: _stats(meas, [r["model_Nm"][k][angle] for r in sel]) for k in ("generic", "regression", "imaging")}
    return out


OSF_NODE = "svwa7"


def osf_files(view_only):
    """[(name, download url)] of the project's files (view-only key from the paper's data availability statement)."""
    import urllib.request
    url = f"https://api.osf.io/v2/nodes/{OSF_NODE}/files/osfstorage/?view_only={view_only}&page%5Bsize%5D=100"
    with urllib.request.urlopen(url, timeout=60) as r:
        d = json.load(r)
    return [(f["attributes"]["name"], f["links"]["download"]) for f in d["data"] if f["attributes"]["kind"] == "file"]


def volumes(data_dir, view_only, out, keep=False):
    """Download each scan zip into ``data_dir``, recompute its volumes and PDFF from the masks (``scan_volumes``),
    and delete the zip again unless ``keep``. Resumes: scans already in ``out`` are skipped."""
    import urllib.request
    d = Path(data_dir)
    d.mkdir(parents=True, exist_ok=True)
    res = json.loads(Path(out).read_text()) if Path(out).exists() else {}
    for name, url in osf_files(view_only):
        target = d / name
        if name.endswith(".csv") and not target.exists():
            urllib.request.urlretrieve(url, target)
        if not name.endswith(".zip") or name[:-4] in res:
            continue
        if not target.exists():
            urllib.request.urlretrieve(url, target)
        res[name[:-4]] = scan_volumes(target)
        Path(out).write_text(json.dumps(res, indent=1))
        if not keep:
            target.unlink()
        print(name, "done", file=sys.stderr)
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    an = sub.add_parser("analyse", help="size and strength against the muscle layer")
    an.add_argument("data_dir", help="folder with Table1.csv and Table2.csv")
    an.add_argument("--out", required=True)
    an.add_argument("--work", help="folder for the per-person models (default: a temporary one)")
    an.add_argument("--volumes", help="volumes.json from the 'volumes' command (default: Table2's, which are wrong)")
    vo = sub.add_parser("volumes", help="download the scans and recompute volumes and PDFF from the masks")
    vo.add_argument("data_dir")
    vo.add_argument("--view-only", required=True, help="the OSF view-only key in the paper's data availability statement")
    vo.add_argument("--out", required=True)
    vo.add_argument("--keep", action="store_true", help="keep the zips (2.9 GB)")
    a = ap.parse_args(argv)
    if a.cmd == "volumes":
        volumes(a.data_dir, a.view_only, a.out, a.keep)
        return
    res = analyse(a.data_dir, a.work, a.volumes)
    Path(a.out).write_text(json.dumps(res, indent=1))
    print(json.dumps(res["summary"], indent=1))


if __name__ == "__main__":
    main()
