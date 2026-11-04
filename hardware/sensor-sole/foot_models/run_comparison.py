#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors
# SPDX-License-Identifier: CERN-OHL-S-2.0
"""Run the experimental foot-model comparison and the sensitivity checks; write one summary JSON.

Inputs are named on the command line; none of the models or kinematics are in this repository:
  --selftest   the pipeline's scaled self-test model (two-segment foot, calcn + toes)
  --dhondt     folder with DHondt_2024_3-segment_foot_fixed_knee.osim and DHondt_2024_4-segment_foot_fixed_knee.osim
               (github.com/Lars-DHondt-KUL/3dpredictsim, branch four-segment_foot_model, commit e963f4a)
  --mot        squat kinematics in degrees (OpenCap's squats1_videoAndMocap.mot)
  --sole-r/-l  the simulation soles (sim/*.sole_sim.json); --sole-r10/-l10 the same at 10 mm spacing
Each case writes its own folder under --out with the model it solved and result.json.

  python foot_models/run_comparison.py --selftest ... --dhondt ... --mot ... --sole-r ... --sole-l ... --out runs/
"""
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import compare_feet as CF  # noqa: E402
import dhondt_port as DP  # noqa: E402

POSTURES = {"standing": 0.00, "squat_knee30": 0.51, "squat_knee60": 2.20, "squat_knee80": 2.46}
COP_TARGETS = (0.30, 0.45, 0.60, 0.75)       # fractions of the sole's heel-to-bend-line length


def summarise(r):
    reg = r["R"]["regions_pct_of_foot"]
    grp = lambda *ps: round(sum(v for k, v in reg.items() if k.startswith(ps)), 2)
    return dict(solved=r["solved"], support_error_pct=r["support_error_pct"], ankle_angle_deg=r["angles_deg"]["ankle_angle_r"],
                ankle_torque_Nm=r["ankle_torque_Nm"]["r"], foot_angles_deg={k: v for k, v in r["angles_deg"].items()
                                                                              if "ankle" not in k and k.endswith("_r")},
                mtj_outside_paper_range=r["mtj_outside_paper_range"], cop_sole_mm=r["R"]["cop_sole_mm"],
                foot_N=r["R"]["total_N"], heel_pct=grp("heel"), arch_midfoot_pct=grp("arch", "mid", "ffp"),
                metatarsal_pct=grp("mt"), toes_pct=grp("toe"), regions_pct=reg,
                scale=r["registration"]["R"]["scale"], posture_outside_model_range=r["posture_applied"]["outside_model_range"],
                posture_notes=r["posture_applied"]["notes"])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for k in ("selftest", "dhondt", "mot", "sole-r", "sole-l", "sole-r10", "sole-l10", "out"):
        ap.add_argument(f"--{k}", required=k not in ("sole-r10", "sole-l10"))
    ap.add_argument("--only", choices=["comparison", "sensitivity", "convergence"], default=None)
    ap.add_argument("--spacing-soles", nargs="*", default=[], metavar="DIR",
                    help="folders each holding one right and one left *.sole_sim.json at another contact spacing "
                         "(convergence study)")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    nominal = Path(a.dhondt)
    ported = {}
    for kind in ("3", "4"):
        src = nominal / f"DHondt_2024_{kind}-segment_foot_fixed_knee.osim"
        dst = out / f"ported_{kind}seg.osim"
        DP.port(src, dst)
        ported[kind] = (src, dst)
    models = {
        "two-segment (self-test), foot rigid": (a.selftest, False),
        "D'Hondt 3-segment .osim only, foot rigid": (ported["3"][0], False),
        "D'Hondt 4-segment .osim only, foot rigid": (ported["4"][0], False),
        "D'Hondt 3-segment ported, foot rigid": (ported["3"][1], False),
        "D'Hondt 4-segment ported, foot rigid": (ported["4"][1], False),
        "D'Hondt 3-segment ported, MTP free": (ported["3"][1], True),
        "D'Hondt 4-segment ported, midtarsal and MTP free": (ported["4"][1], True),
        "D'Hondt 4-segment .osim only, midtarsal and MTP free": (ported["4"][0], True),
    }
    summary = dict(status=CF.STATUS, inputs=vars(a), postures_from_mot_s=POSTURES, cop_targets=COP_TARGETS,
                   posture_based={}, controlled_cop={}, sensitivity={})

    def case(group, label, model, free, pname, cop=None, pert=None, soles=None):
        posture = CF.symmetric(CF.posture_from_mot(a.mot, POSTURES[pname], CF.SAGITTAL))
        sr, sl = soles or (a.sole_r, a.sole_l)
        key = f"{label}|{pname}|{cop}|{json.dumps(pert, sort_keys=True)}|{sr}"
        d = out / group / hashlib.sha256(key.encode()).hexdigest()[:12]
        t0 = time.time()
        r = CF.run(model, sr, sl, d, posture, free, pert, label=label, cop_target=cop)
        s = summarise(r); s["seconds"] = round(time.time() - t0, 1)
        return s

    if a.only in (None, "comparison"):
        for label, (model, free) in models.items():
            for pname in POSTURES:
                s = case("posture_based", label, model, free, pname)
                summary["posture_based"].setdefault(label, {})[pname] = s
                print(f"POSTURE {label:52s} {pname:13s} solved {s['solved']!s:5s} heel {s['heel_pct']:5.1f} arch {s['arch_midfoot_pct']:5.1f} "
                      f"mt {s['metatarsal_pct']:5.1f} toes {s['toes_pct']:5.1f} angles {s['foot_angles_deg']} outside {bool(s['posture_outside_model_range'])}", flush=True)
            for cop in COP_TARGETS:
                s = case("controlled_cop", label, model, free, "standing", cop=cop)
                summary["controlled_cop"].setdefault(label, {})[f"{cop:.2f}"] = s
                print(f"COP {cop:.2f} {label:52s} solved {s['solved']!s:5s} heel {s['heel_pct']:5.1f} arch {s['arch_midfoot_pct']:5.1f} "
                      f"mt {s['metatarsal_pct']:5.1f} toes {s['toes_pct']:5.1f} angles {s['foot_angles_deg']}", flush=True)
    if a.only in (None, "sensitivity"):
        perturbations = {"baseline": {}, "scale -5%": dict(scale=0.95), "scale +5%": dict(scale=1.05),
                         "lateral -5 mm": dict(lateral_mm=-5), "lateral +5 mm": dict(lateral_mm=5),
                         "sole plane pitch -2 deg": dict(pitch_deg=-2), "sole plane pitch +2 deg": dict(pitch_deg=2),
                         "boundaries -5 mm": dict(boundary_mm=-5), "boundaries +5 mm": dict(boundary_mm=5),
                         "stiffness x0.5": dict(stiffness=0.5), "stiffness x2": dict(stiffness=2.0)}
        cases = {"two-segment (self-test), foot rigid": (a.selftest, False),
                 "D'Hondt 4-segment ported, midtarsal and MTP free": (ported["4"][1], True)}
        for label, (model, free) in cases.items():
            for cond, cop in (("standing, COP under COM", None), ("controlled, COP at 0.45", 0.45)):
                runs = dict(perturbations)
                if a.sole_r10:
                    runs["sphere spacing 10 mm"] = "spacing10"
                for name, pert in runs.items():
                    if pert == "spacing10":
                        s = case("sensitivity", label, model, free, "standing", cop=cop, soles=(a.sole_r10, a.sole_l10))
                    else:
                        s = case("sensitivity", label, model, free, "standing", cop=cop, pert=pert)
                    summary["sensitivity"].setdefault(label, {}).setdefault(cond, {})[name] = s
                    print(f"SENS {label:48s} {cond:24s} {name:24s} solved {s['solved']!s:5s} heel {s['heel_pct']:5.1f} "
                          f"arch {s['arch_midfoot_pct']:5.1f} mt {s['metatarsal_pct']:5.1f} toes {s['toes_pct']:5.1f} "
                          f"COP {s['cop_sole_mm']}", flush=True)
    if a.only == "convergence" or (a.only is None and a.spacing_soles):
        conv = {"two-segment (self-test), foot rigid": (a.selftest, False),
                "D'Hondt 4-segment ported, foot rigid": (ported["4"][1], False),
                "D'Hondt 3-segment ported, MTP free": (ported["3"][1], True),
                "D'Hondt 4-segment ported, midtarsal and MTP free": (ported["4"][1], True)}
        sets = [(a.sole_r, a.sole_l)]
        for d in a.spacing_soles:
            fs = sorted(Path(d).glob("*.sole_sim.json"))
            sets.append(tuple(str(f) for f in sorted(fs, key=lambda f: json.loads(f.read_text())["side"] != "R")))
        summary["convergence"] = {}
        for sr, sl in sets:
            sp = json.loads(Path(sr).read_text())["point_spacing_mm"]
            for label, (model, free) in conv.items():
                for cop in (0.45, 0.75):
                    s = case("convergence", label, model, free, "standing", cop=cop, soles=(sr, sl))
                    summary["convergence"].setdefault(label, {}).setdefault(f"{cop:.2f}", {})[f"{sp:g} mm"] = s
                    print(f"CONV {sp:4g} mm {label:52s} COP {cop:.2f} solved {s['solved']!s:5s} heel {s['heel_pct']:5.1f} "
                          f"arch {s['arch_midfoot_pct']:5.1f} mt {s['metatarsal_pct']:5.1f} toes {s['toes_pct']:5.1f} "
                          f"angles {s['foot_angles_deg']} ({s['seconds']} s)", flush=True)
    (out / "summary.json").write_text(json.dumps(summary, indent=1) + "\n")


if __name__ == "__main__":
    main()
