import json, sys
D = sys.argv[1]
for v in ("reg", "age", "dxa"):
    try:
        s = json.load(open(f"{D}/s_{v}/muscles/study.json"))
    except FileNotFoundError:
        continue
    cap = s["muscle_model"]["capacity"]
    x = s["runs"]["measured"]
    ga = x["group_activation"]
    jm = x["joint_moments"]
    knee = {k: v2 for k, v2 in jm.items() if "knee" in k or "hip_flexion" in k or "ankle" in k}
    print(f"== {v}: {cap.get('leg_source')} legs {cap.get('leg_muscle_cm3')} Fmax {cap['leg_fmax_N']['right']['scaled']}/{cap['leg_fmax_N']['left']['scaled']}")
    print("   quads peak R/L", ga["quadriceps_r"]["peak"], ga["quadriceps_l"]["peak"], "mean", ga["quadriceps_r"]["mean"], ga["quadriceps_l"]["mean"])
    print("   glmax peak R/L", ga["gluteus_maximus_r"]["peak"], ga["gluteus_maximus_l"]["peak"], " triceps surae", ga["triceps_surae_r"]["peak"], ga["triceps_surae_l"]["peak"])
    print("   saturated", len(x["muscles_saturated"]), "pelvis residual", x["pelvis_residual_force_N"].get("pelvis_ty_force"), x["pelvis_residual_force_N"].get("pelvis_tilt_moment"))
    print("   moments", json.dumps(knee)[:600])
    if cap.get("mass_distribution"):
        print("   masses", {r: (d["model_share_before"], d["dxa_share"], d["factor"]) for r, d in cap["mass_distribution"]["regions"].items()})
