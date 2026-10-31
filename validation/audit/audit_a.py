"""Audit part A: re-derive the claims from raw files with code written for the audit (no rehabtwin imports).

Checks: Pose2Sim/OpenCap marker facts, shank lengths, OpenCap agreement RMSE, SKEL synthetic results,
SKEL on OpenCap subject 2, the squat DXA demo. Prints one line per check and writes audit_a.json.
"""
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import opensim as osim

SP = Path(sys.argv[1])
UP = Path(sys.argv[2])            # upstream clones (Pose2Sim)
OC = Path(sys.argv[3])            # opencap-core clone
P2S_MODEL = UP / "perfanalytics/pose2sim/Pose2Sim/OpenSim_Setup/Model_Pose2Sim_muscles_flex.osim"
P2S_MARKERS = UP / "perfanalytics/pose2sim/Pose2Sim/OpenSim_Setup/Markers_LSTM.xml"
LAI_MODEL = OC / "opensimPipeline/Models/LaiUhlrich2022.osim"
LAI_MARKERS = OC / "opensimPipeline/Models/LaiUhlrich2022_markers_augmenter.xml"
results = []


def check(section, claim, stated, measured, ok, note=""):
    results.append({"section": section, "claim": claim, "stated": stated, "measured": measured, "ok": bool(ok),
                    "note": note})
    print(f"[{'OK  ' if ok else 'DIFF'}] {section}: {claim} | stated {stated} | measured {measured} {note}")


# ---- 1. marker facts, straight from the XML files and OpenSim ------------------------------------------------
def markers_xml(path):
    out = {}
    for m in ET.parse(path).getroot().iter("Marker"):
        loc = [float(x) for x in m.find("location").text.split()]
        out[m.get("name")] = (m.find("socket_parent_frame").text.split("/")[-1], np.array(loc))
    return out


mp, ml = markers_xml(P2S_MARKERS), markers_xml(LAI_MARKERS)
common = sorted(set(mp) & set(ml))
same = [n for n in common if mp[n][0] == ml[n][0] and np.allclose(mp[n][1], ml[n][1], atol=1e-9)]
check("markers", "Markers_LSTM.xml reuses LaiUhlrich2022's augmenter marker locations", "all 43 identical",
      f"{len(same)} of {len(common)} common markers identical", len(same) == len(common) == 43)


def origins(model_path, extra_markers=None):
    m = osim.Model(str(model_path))
    if extra_markers:
        ms = osim.MarkerSet(str(extra_markers))
        for i in range(ms.getSize()):
            m.addMarker(ms.get(i).clone())
    s = m.initSystem()
    b = m.getBodySet()
    g = lambda p: np.array([p.get(0), p.get(1), p.get(2)])
    bodies = {b.get(i).getName(): g(b.get(i).getPositionInGround(s)) for i in range(b.getSize())}
    mk = {}
    if extra_markers:
        M = m.getMarkerSet()
        mk = {M.get(i).getName(): g(M.get(i).getLocationInGround(s)) for i in range(M.getSize())}
    return bodies, mk


d = lambda P, a, b: float(np.linalg.norm(P[a] - P[b]))
Bp, Mp = origins(P2S_MODEL, P2S_MARKERS)
Bl, Ml = origins(LAI_MODEL, LAI_MARKERS)
check("markers", "generic tibia (knee to ankle joint centre), Pose2Sim vs LaiUhlrich2022", "0.430 vs 0.400 m",
      f"{d(Bp, 'tibia_r', 'talus_r'):.4f} vs {d(Bl, 'tibia_r', 'talus_r'):.4f} m",
      abs(d(Bp, "tibia_r", "talus_r") - 0.430) < 5e-4 and abs(d(Bl, "tibia_r", "talus_r") - 0.400) < 5e-4)
check("markers", "generic femur (hip to knee), Pose2Sim vs LaiUhlrich2022", "0.397 vs 0.406 m",
      f"{d(Bp, 'femur_r', 'tibia_r'):.4f} vs {d(Bl, 'femur_r', 'tibia_r'):.4f} m",
      abs(d(Bp, "femur_r", "tibia_r") - 0.397) < 5e-4 and abs(d(Bl, "femur_r", "tibia_r") - 0.406) < 5e-4)
hp, hl = 100 * (Mp["r_ankle_study"][1] - Bp["talus_r"][1]), 100 * (Ml["r_ankle_study"][1] - Bl["talus_r"][1])
check("markers", "lateral malleolus marker height above the ankle joint centre (default pose)", "4.5 cm vs 1.5 cm",
      f"{hp:.1f} cm vs {hl:.1f} cm", abs(hp - 4.5) < 0.1 and abs(hl - 1.5) < 0.1)
hip_off = 100 * np.linalg.norm(Mp["RHJC_study"] - Bp["femur_r"])
check("markers", "RHJC_study marker distance from the Pose2Sim model's right hip joint", "about 2 cm",
      f"{hip_off:.1f} cm", 1.5 < hip_off < 2.5)

# ---- 2. shank and hip width of the scaled models -------------------------------------------------------------
OF = SP / "skel_work/oc_fix"
for label, sess, stated_sh, stated_hw in (("before", "multi_aug_base", (0.542, 0.546), 0.203),
                                          ("after", "multi_aug_fix", (0.493, 0.497), 0.188)):
    B, _ = origins(OF / sess / "opensim/model_scaled.osim")
    sh = (d(B, "tibia_r", "talus_r"), d(B, "tibia_l", "talus_l"))
    hw = d(B, "femur_r", "femur_l")
    check("shank", f"5-phone scaled shank R/L and hip width, {label} the marker fix",
          f"{stated_sh[0]}/{stated_sh[1]} m, hip {stated_hw}", f"{sh[0]:.3f}/{sh[1]:.3f} m, hip {hw:.3f}",
          abs(sh[0] - stated_sh[0]) < 6e-4 and abs(sh[1] - stated_sh[1]) < 6e-4 and abs(hw - stated_hw) < 6e-4)
B, _ = origins(SP / "oc_verify/data/OpenSimData/Model/LaiUhlrich2022_scaled.osim")
check("shank", "OpenCap's own scaled model, shank R/L", "0.485/0.495 m",
      f"{d(B, 'tibia_r', 'talus_r'):.3f}/{d(B, 'tibia_l', 'talus_l'):.3f} m",
      abs(d(B, "tibia_r", "talus_r") - 0.485) < 6e-4 and abs(d(B, "tibia_l", "talus_l") - 0.495) < 6e-4)


# ---- 3. OpenCap agreement, RMSE recomputed from the motion files ----------------------------------------------
def read_mot(path):
    lines = Path(path).read_text().splitlines()
    k = next(i for i, l in enumerate(lines) if l.strip().lower() == "endheader")
    header = {l.split("=")[0].strip(): l.split("=")[-1].strip() for l in lines[:k] if "=" in l}
    cols = lines[k + 1].split()
    data = np.array([[float(x) for x in l.split()] for l in lines[k + 2:] if l.strip()])
    deg = header.get("inDegrees", "yes").lower() == "yes"
    return cols, data, deg


def rmse(est_path, ref_path, lag, coords):
    ce, de, dege = read_mot(est_path)
    cr, dr, degr = read_mot(ref_path)
    te, tr = de[:, 0], dr[:, 0] + lag
    inside = (te >= tr[0]) & (te <= tr[-1])
    out = {}
    for c in coords:
        e = de[inside, ce.index(c)] * (1 if dege else 180 / np.pi)
        r = np.interp(te[inside], tr, dr[:, cr.index(c)]) * (1 if degr else 180 / np.pi)
        out[c] = float(np.sqrt(np.mean((e - r) ** 2)))
    return out, int(inside.sum())


REF = SP / "oc_verify/data/OpenSimData/Kinematics/squats1.mot"
COORDS = ["pelvis_tilt", "hip_flexion_r", "hip_flexion_l", "knee_angle_r", "knee_angle_l", "ankle_angle_r", "ankle_angle_l"]
STATED = {("multi_aug", "base"): [6.0, 13.9, 13.9, 9.3, 9.2, 4.9, 4.6], ("multi_aug", "fix"): [2.8, 8.2, 7.9, 7.4, 7.1, 5.4, 5.3],
          ("cams123_aug", "base"): [6.7, 14.6, 13.3, 12.0, 8.1, 6.5, 4.6], ("cams123_aug", "fix"): [3.3, 9.4, 8.0, 10.5, 6.5, 7.3, 4.4]}
agreement = {}
for (sess, c), stated in STATED.items():
    rep = json.loads((OF / f"{sess}_{c}" / "validation-report.json").read_text())
    got, n = rmse(OF / f"{sess}_{c}" / "opensim/ik.mot", REF, rep["time_lag_applied_s"], COORDS)
    agreement[f"{sess}_{c}"] = got
    worst = max(abs(got[k] - s) for k, s in zip(COORDS, stated))
    check("opencap", f"RMSE vs OpenCap, {sess.replace('_aug', '')} {('before' if c == 'base' else 'after')} the fix "
          "(pelvis tilt, hip R/L, knee R/L, ankle R/L)", " / ".join(f"{s:.1f}" for s in stated),
          " / ".join(f"{got[k]:.1f}" for k in COORDS) + f" (n={n} frames)", worst < 0.06,
          "independent reader; reference shifted by the report's lag")

# ---- 4. SKEL synthetic validation: summary recomputed from the per-body rows ---------------------------------
rows = json.loads((SP / "skel_work/skel_bones.json").read_text())["rows"]
ok_rows = [r for r in rows if "error" not in r]
bmis = [r["bmi"] for r in ok_rows]
check("skel-synthetic", "bodies, sexes and BMI range", "45 bodies, 23 female / 22 male, BMI 17-43",
      f"{len(ok_rows)} bodies, {sum(r['sex'] == 'female' for r in ok_rows)} female / "
      f"{sum(r['sex'] == 'male' for r in ok_rows)} male, BMI {min(bmis):.1f}-{max(bmis):.1f}",
      len(ok_rows) == 45 and 16.5 < min(bmis) < 18 and 42 < max(bmis) < 44)
segs = ("thigh_r", "shank_r", "upper_arm_r", "forearm_r", "hip_width")
for src, stated_mae, stated_max in (("depth fit", 0.2, 1.1), ("height and mass", 0.5, 1.5), ("height only", 1.8, 4.8)):
    err = np.array([[100 * (r["segments"][src][k] - r["segments"]["true"][k]) for k in segs] for r in ok_rows])
    mae, mx = np.abs(err).mean(0), np.abs(err).max()
    check("skel-synthetic", f"SKEL segment error, {src} (mean abs per segment; worst)",
          f"mean <= {stated_mae} cm, worst {stated_max} cm", f"{' / '.join(f'{x:.2f}' for x in mae)} cm; worst {mx:.2f} cm",
          mae.max() <= stated_mae + 0.05 and abs(mx - stated_max) < 0.06, "order: thigh, shank, upper arm, forearm, hip width")
# the stored "true" bones re-derived from the stored shape parameters with the SKEL file, by plain numpy
skel = {s: np.load(SP / f"body_models_skel/npz/skel_{s}.npz", allow_pickle=False) for s in ("female", "male")}
smpl = {s: np.load(SP / f"body_models/npz/basicmodel_{s[0]}_lbs_10_207_0_v1.1.0.npz", allow_pickle=False)
        for s in ("female", "male")}
worst = 0.0
for r in ok_rows[:10]:
    k, s = skel[r["sex"]], smpl[r["sex"]]
    b = np.array(r["betas_true"])
    v = s["v_template"] + s["shapedirs"][:, :, :len(b)] @ b
    J = dict(zip([str(n) for n in k["bone_names"]], k["J_regressor_osim"] @ v))
    worst = max(worst, abs(np.linalg.norm(J["femur_r"] - J["tibia_r"]) - r["segments"]["true"]["thigh_r"]))
check("skel-synthetic", "stored true thigh lengths re-derived from shape parameters (10 bodies)", "identical",
      f"max difference {worst * 1000:.4f} mm", worst < 1e-6)

# ---- 5. SKEL on OpenCap subject 2 (height and mass) ----------------------------------------------------------
pj = json.loads((SP / "skel_work/oc_P/person.json").read_text())["skel_bones"]
b = np.array(pj["betas"])
k, s = skel["male"], smpl["male"]
v = s["v_template"] + s["shapedirs"][:, :, :len(b)] @ b
J = dict(zip([str(n) for n in k["bone_names"]], k["J_regressor_osim"] @ v))
a, f = s["f"][:, 0], s["f"]
vol = abs(np.einsum("ij,ij->i", v[f[:, 0]], np.cross(v[f[:, 1]], v[f[:, 2]])).sum()) / 6
h = v[:, 1].max() - v[:, 1].min()
check("skel-subject2", "SKEL body for 1.96 m / 78.2 kg", "1.960 m, 78.2 kg", f"{h:.3f} m, {vol * 1000:.1f} kg (1000 kg/m3)",
      abs(h - 1.96) < 0.01 and abs(vol * 1000 - 78.2) < 1.6)
th, sh, ua = d(J, "femur_r", "tibia_r"), d(J, "tibia_r", "talus_r"), d(J, "humerus_r", "ulna_r")
check("skel-subject2", "SKEL thigh / shank / upper arm", "0.471 / 0.491 / 0.313 m", f"{th:.3f} / {sh:.3f} / {ua:.3f} m",
      abs(th - 0.471) < 6e-4 and abs(sh - 0.491) < 6e-4 and abs(ua - 0.313) < 6e-4)

# ---- 6. squat with the illustrative DXA record ----------------------------------------------------------------
st = {c: json.loads((SP / f"dxa_demo/s_{c}/muscles/study.json").read_text()) for c in ("reg", "age", "dxa")}
km = {c: st[c]["runs"]["measured"]["joint_moments"]["knee_angle_r"]["min_Nm_per_kg"] for c in st}
check("dxa-squat", "right knee peak extension moment, height-and-mass vs DXA run", "-12 %",
      f"{km['reg']:.3f} -> {km['dxa']:.3f} N.m/kg ({100 * (km['dxa'] / km['reg'] - 1):+.1f} %)",
      abs(100 * (km["dxa"] / km["reg"] - 1) + 12) < 0.6)
fm = {c: st[c]["muscle_model"]["capacity"]["leg_fmax_N"]["right"]["scaled"] for c in st}
check("dxa-squat", "right leg Fmax: height and mass / age and sex / DXA", "48.5 / 42.5 / 47.2 kN",
      " / ".join(f"{fm[c] / 1000:.1f}" for c in ("reg", "age", "dxa")) + " kN",
      abs(fm["reg"] - 48469) < 50 and abs(fm["age"] - 42542) < 50 and abs(fm["dxa"] - 47248) < 50)

json.dump({"checks": results, "agreement": agreement}, open(sys.argv[4], "w"), indent=1)
print(f"{sum(r['ok'] for r in results)} of {len(results)} checks match")
