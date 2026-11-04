#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors
# SPDX-License-Identifier: CERN-OHL-S-2.0
"""Run the experimental foot-model comparison and its sensitivity analyses; write one summary JSON. Experimental.

Contact. The main comparison uses ONE assumed sole-contact model on every foot model (sole_sim.ASSUMED_CONTACT_V1:
assumed, not measured). The same runs with each model's own native contact are kept as a separate sensitivity
analysis, not as the result.

Groups (each case has its own folder under --out, with result.json):
  controlled_cop   the main comparison: passive foot, centre of pressure prescribed, assumed contact. A control,
                   not a predicted movement.
  posture_based    centre of pressure under each body's centre of mass, assumed contact. Confounded by body and
                   posture; postures outside a model's coordinate ranges are flagged and not to be interpreted.
  native_contact   both of the above with each model's native contact (sensitivity analysis).
  sensitivity      registration, assumed-contact parameters, native contact and spacing, for two cases.
  discretisation   contact spacing (15, 10, 7.5, 5 mm): discretisation sensitivity, not a confidence interval and
                   not the total uncertainty.
None of these is a muscle-driven squat or gait result.

Resumable. Each case's folder is named from a fingerprint of its inputs (sha256), parameters, code (sha256) and
tool versions, and is marked done only when it finished (foot_models/case_store.py). Run the same command again
after an interruption and finished cases are reused; nothing is reused once an input, the code or the OpenSim
version changes. --no-resume recomputes everything. --jobs N runs N cases at once, in separate processes.

Inputs are named on the command line; none of the models or kinematics are in this repository:
  --selftest   the pipeline's scaled self-test model (two-segment foot, calcn + toes)
  --dhondt     folder with DHondt_2024_3-segment_foot_fixed_knee.osim and DHondt_2024_4-segment_foot_fixed_knee.osim
               (github.com/Lars-DHondt-KUL/3dpredictsim, branch four-segment_foot_model, commit e963f4a)
  --mot        squat kinematics in degrees (OpenCap's squats1_videoAndMocap.mot)
  --sole-r/-l  the simulation soles (sim/*.sole_sim.json); --sole-r10/-l10 the same at 10 mm spacing
  --spacing-soles  folders with soles at further spacings (discretisation group; sim/spacing/*)
workstation/fetch_inputs.py fetches the external files at their pinned commits and checks them.

  python foot_models/run_comparison.py --selftest ... --dhondt ... --mot ... --sole-r ... --sole-l ... --out runs/ \
      [--jobs 8]
"""
import argparse
import hashlib
import json
import platform
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import get_context
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import case_store as CS  # noqa: E402
import compare_feet as CF  # noqa: E402
import dhondt_port as DP  # noqa: E402
import sole_sim as SS  # noqa: E402

POSTURES = {"standing": 0.00, "squat_knee30": 0.51, "squat_knee60": 2.20, "squat_knee80": 2.46}
COP_TARGETS = (0.30, 0.45, 0.60, 0.75)       # fractions of the sole's heel-to-bend-line length
ASSUMED = SS.ASSUMED_CONTACT_V1
# Files whose content decides a case's result.json. A change to any of them invalidates every stored case.
CODE_FILES = (HERE / "compare_feet.py", HERE.parent / "sole_sim.py", HERE / "dhondt_port.py",
              HERE / "dhondt2024_mtj_ligament_moment.json")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


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
                posture_notes=r["posture_applied"]["notes"], contact=r["contact_model"]["name"],
                stiffness_per_sphere=r["stiffness_per_sphere"])


def execute(spec):
    """One case, in this process or a worker. Returns (spec id, summary row)."""
    store = CS.CaseStore(spec["root"], resume=spec["resume"])
    run = spec["run"]
    fn = lambda d: CF.run(run["model"], run["sole_r"], run["sole_l"], d, run["posture"], run["free"], run["pert"],
                          label=run["label"], cop_target=run["cop"], contact=run["contact"])
    result, rec, reused = store.run(spec["group"], spec["key"], fn)
    s = summarise(result)
    s["seconds"] = rec["seconds"]
    s["reused_from_earlier_run"] = reused
    return spec["id"], s


def put(tree, path, value):
    for k in path[:-1]:
        tree = tree.setdefault(k, {})
    tree[path[-1]] = value


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for k in ("selftest", "dhondt", "mot", "sole-r", "sole-l", "sole-r10", "sole-l10", "out"):
        ap.add_argument(f"--{k}", required=k not in ("sole-r10", "sole-l10"))
    ap.add_argument("--only", nargs="*", default=None,
                    choices=["controlled_cop", "posture_based", "native_contact", "sensitivity", "discretisation"])
    ap.add_argument("--spacing-soles", nargs="*", default=[], metavar="DIR")
    ap.add_argument("--jobs", type=int, default=1, help="cases run at once, each in its own process (default 1)")
    ap.add_argument("--no-resume", action="store_true", help="recompute every case, even finished ones")
    a = ap.parse_args()
    want = lambda g: a.only is None or g in a.only
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
    import numpy
    import opensim
    import scipy
    versions = dict(python=platform.python_version(), opensim=opensim.__version__, numpy=numpy.__version__,
                    scipy=scipy.__version__)
    code = {str(Path(f).relative_to(HERE.parent)): sha(f) for f in CODE_FILES}
    inputs = {k: dict(path=v, sha256=sha(v)) for k, v in (("selftest", a.selftest), ("mot", a.mot),
                                                          ("sole_r", a.sole_r), ("sole_l", a.sole_l))}
    for kind in ("3", "4"):
        inputs[f"dhondt_{kind}seg"] = dict(path=str(ported[kind][0]), sha256=sha(ported[kind][0]))
        inputs[f"dhondt_{kind}seg_ported"] = dict(sha256=sha(ported[kind][1]))
    summary = dict(status=CF.STATUS, assumed_contact=ASSUMED, inputs=inputs, postures_from_mot_s=POSTURES,
                   cop_targets=COP_TARGETS, environment=dict(versions, machine=platform.machine(),
                                                             system=platform.system()),
                   code_sha256=code, controlled_cop={}, posture_based={},
                   native_contact=dict(controlled_cop={}, posture_based={}), sensitivity={}, discretisation={})

    file_sha = {}
    def fsha(p):
        p = str(p)
        if p not in file_sha:
            file_sha[p] = sha(p)
        return file_sha[p]

    mot_sha = fsha(a.mot)
    plan = []                                     # (spec, [(summary path, display tag, display condition)])
    index = {}

    def case(group, label, model, free, pname, slot, tag, cond, cop=None, pert=None, soles=None, contact=ASSUMED):
        posture = CF.symmetric(CF.posture_from_mot(a.mot, POSTURES[pname], CF.SAGITTAL))
        sr, sl = soles or (a.sole_r, a.sole_l)
        key = dict(label=label, model_sha256=fsha(model), free_foot=free, posture_name=pname,
                   posture_time_s=POSTURES[pname], mot_sha256=mot_sha, posture_deg=posture, cop_target=cop,
                   perturbation=pert or {}, sole_r_sha256=fsha(sr), sole_l_sha256=fsha(sl), contact=contact,
                   code_sha256=code, versions=versions)
        ident = (group, CS.fingerprint(key))
        if ident not in index:                    # the same case asked for twice runs once
            index[ident] = len(plan)
            plan.append((dict(id=len(plan), root=str(out), resume=not a.no_resume, group=group, key=key,
                              run=dict(model=str(model), sole_r=str(sr), sole_l=str(sl), posture=posture, free=free,
                                       pert=pert, label=label, cop=cop, contact=contact)), []))
        plan[index[ident]][1].append((slot, tag, label, cond))

    for label, (model, free) in models.items():
        for contact, store in ((ASSUMED, ()), (None, ("native_contact",))):
            if (contact is ASSUMED and want("controlled_cop")) or (contact is None and want("native_contact")):
                for cop in COP_TARGETS:
                    case("controlled_cop" if contact else "native_controlled", label, model, free, "standing",
                         store + ("controlled_cop", label, f"{cop:.2f}"), "COP" if contact else "COP native",
                         f"{cop:.2f}", cop=cop, contact=contact)
            if (contact is ASSUMED and want("posture_based")) or (contact is None and want("native_contact")):
                for pname in POSTURES:
                    case("posture_based" if contact else "native_posture", label, model, free, pname,
                         store + ("posture_based", label, pname), "POSTURE" if contact else "POSTURE native", pname,
                         contact=contact)
    if want("sensitivity"):
        perturbations = {"baseline": {}, "scale -5%": dict(scale=0.95), "scale +5%": dict(scale=1.05),
                         "lateral -5 mm": dict(lateral_mm=-5), "lateral +5 mm": dict(lateral_mm=5),
                         "sole plane pitch -2 deg": dict(pitch_deg=-2), "sole plane pitch +2 deg": dict(pitch_deg=2),
                         "boundaries -5 mm": dict(boundary_mm=-5), "boundaries +5 mm": dict(boundary_mm=5),
                         "assumed contact stiffness x0.5": dict(stiffness=0.5),
                         "assumed contact stiffness x2": dict(stiffness=2.0)}
        cases = {"two-segment (self-test), foot rigid": (a.selftest, False),
                 "D'Hondt 4-segment ported, midtarsal and MTP free": (ported["4"][1], True)}
        for label, (model, free) in cases.items():
            for cond, cop in (("standing, COP under COM", None), ("controlled, COP at 0.45", 0.45)):
                runs = dict(perturbations)
                runs["native contact (model's own)"] = "native"
                if a.sole_r10:
                    runs["sphere spacing 10 mm"] = "spacing10"
                for name, pert in runs.items():
                    slot = ("sensitivity", label, cond, name)
                    shown = f"{cond[:12]} {name}"[:24]
                    if pert == "spacing10":
                        case("sensitivity", label, model, free, "standing", slot, "SENS", shown, cop=cop,
                             soles=(a.sole_r10, a.sole_l10))
                    elif pert == "native":
                        case("sensitivity", label, model, free, "standing", slot, "SENS", shown, cop=cop, contact=None)
                    else:
                        case("sensitivity", label, model, free, "standing", slot, "SENS", shown, cop=cop, pert=pert)
    if want("discretisation") and a.spacing_soles:
        conv = {"two-segment (self-test), foot rigid": (a.selftest, False),
                "D'Hondt 4-segment ported, foot rigid": (ported["4"][1], False),
                "D'Hondt 3-segment ported, MTP free": (ported["3"][1], True),
                "D'Hondt 4-segment ported, midtarsal and MTP free": (ported["4"][1], True)}
        sets = [(a.sole_r, a.sole_l)]
        for d in a.spacing_soles:
            fs = sorted(Path(d).glob("*.sole_sim.json"), key=lambda f: json.loads(f.read_text())["side"] != "R")
            sets.append(tuple(str(f) for f in fs))
        for sr, sl in sets:
            sp = json.loads(Path(sr).read_text())["point_spacing_mm"]
            for label, (model, free) in conv.items():
                for cop in (0.45, 0.75):
                    for contact in (ASSUMED, None):
                        case("discretisation", label, model, free, "standing",
                             ("discretisation", "assumed" if contact else "native", label, f"{cop:.2f}", f"{sp:g} mm"),
                             "SPACING" if contact else "SPACING native", f"{sp:g} mm, COP {cop:.2f}", cop=cop,
                             soles=(sr, sl), contact=contact)

    def show(tag, label, cond, s):
        print(f"{tag:14s} {label:52s} {cond:24s} solved {s['solved']!s:5s} heel {s['heel_pct']:5.1f} arch {s['arch_midfoot_pct']:5.1f} "
              f"mt {s['metatarsal_pct']:5.1f} toes {s['toes_pct']:5.1f} angles {s['foot_angles_deg']}"
              f"{' OUTSIDE MODEL RANGE' if s['posture_outside_model_range'] else ''}"
              f"{' (reused)' if s['reused_from_earlier_run'] else ''}", flush=True)

    rows = {}
    t0 = time.time()
    print(f"{len(plan)} cases, {a.jobs} at a time, {'recomputing all' if a.no_resume else 'reusing finished ones'}",
          flush=True)

    def collect(i, s):
        rows[i] = s
        for slot, tag, label, cond in plan[i][1]:
            show(tag, label, cond, s)

    if a.jobs <= 1:
        for spec, _ in plan:
            collect(*execute(spec))
    else:
        # spawn: each worker starts its own interpreter and OpenSim; fork after OpenSim has loaded is not safe
        with ProcessPoolExecutor(max_workers=a.jobs, mp_context=get_context("spawn")) as pool:
            for fut in as_completed([pool.submit(execute, spec) for spec, _ in plan]):
                collect(*fut.result())
    for i, (spec, slots) in enumerate(plan):
        for slot, *_ in slots:
            put(summary, slot, rows[i])
    reused = sum(s["reused_from_earlier_run"] for s in rows.values())
    summary["run"] = dict(cases=len(plan), reused_from_earlier_run=reused, computed=len(plan) - reused, jobs=a.jobs,
                          wall_seconds=round(time.time() - t0, 1),
                          case_folders="named by a fingerprint of inputs, parameters, code and versions "
                                       "(foot_models/case_store.py)")
    (out / "summary.json").write_text(json.dumps(summary, indent=1) + "\n")
    print(f"done: {len(plan) - reused} computed, {reused} reused, {summary['run']['wall_seconds']} s", flush=True)


if __name__ == "__main__":
    main()
