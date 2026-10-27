import json, sys
from pathlib import Path
sys.path.insert(0, "$REPO/pipeline")
from rehabtwin import person
O = Path(sys.argv[1])
SIG = [("trunk sag/front", ("torso_segment", "sagittal"), ("torso_segment", "frontal")),
       ("pelvis tilt/list", ("pelvis", "sagittal"), ("pelvis", "frontal")),
       ("lumbar flexion", ("lumbar", "sagittal"), None),
       ("hip flexion R/L", ("hip_r", "sagittal"), ("hip_l", "sagittal")),
       ("hip adduction R", ("hip_r", "frontal"), None),
       ("knee flexion R/L", ("knee_r", "sagittal"), ("knee_l", "sagittal")),
       ("ankle R/L", ("ankle_r", "sagittal"), ("ankle_l", "sagittal")),
       ("knee FPPA R/L", ("knee_r", "frontal"), ("knee_l", "frontal"))]
for s in sys.argv[2:]:
    res = {}
    for c in ("base", "fix"):
        d = O / f"{s}_{c}"
        if not (d / "validation-report.json").exists():
            res[c] = None
            continue
        v = json.loads((d / "validation-report.json").read_text())
        q = json.loads((d / "qc.json").read_text())
        j, _ = person.model_lengths(d / "opensim" / "model_scaled.osim")
        res[c] = (v, q, j)
    print(f"=== {s}")
    for c in ("base", "fix"):
        if not res[c]:
            print(f"  {c}: no report"); continue
        v, q, j = res[c]
        k = v["kinematics_rmse_deg"]
        g = lambda t: k.get(t[0], {}).get(t[1]) if t else None
        cells = []
        for name, a, b in SIG:
            x, y = g(a), g(b)
            cells.append(f"{name}: {x}" + (f"/{y}" if b else ""))
        print(f"  {c}: coverage {v['coverage']['fraction']}, marker RMS {q['ik']['marker_rms_m']['mean']*100:.2f} cm, shank {j['shank_r']:.3f}/{j['shank_l']:.3f}, thigh {j['thigh_r']:.3f}, hip w {j['hip_width']:.3f}")
        print("     " + " | ".join(cells))
