# t-twin-bet-scaled-model: the stand-in twin. For one subject, per-body scale factors that make the pipeline's generic
# model (Pose2Sim full-body) match the segment lengths of the subject's motion-capture-scaled model, written into a
# person folder that `rehabtwin process --person` uses in place of scaling a new body.
# Segment lengths are distances between body origins (joint centres) in each model's default pose:
#   thigh (femur -> tibia), shank (tibia -> talus), foot (calcn -> toes), upper arm (humerus -> ulna),
#   forearm (ulna -> hand), hip width (femur_r -> femur_l), trunk (midpoint of the femurs -> midpoint of the humeri).
# Each generic body gets one uniform factor = mocap length / generic length of its segment:
#   femur, patella: thigh;  tibia: shank;  talus, calcn, toes: foot;  humerus: upper arm;  ulna, radius, hand: forearm;
#   pelvis, sacrum: hip width;  lumbar1-5, torso, head, Abdomen: trunk.
# The person folder is made by the pipeline's own commands (person init, person build from the subject's round-0
# one-camera session, which gives a valid record for the same generic model); then only model.scale_set in person.json is
# replaced by these factors. No pipeline code is changed.
# Args: subject mocap_model round0_session person_dir mass height
import json, subprocess, sys, shutil
from pathlib import Path
import numpy as np
import opensim as osim
from rehabtwin.config import load_config, resolve
subject, mocap_model, session, pdir, mass, height = sys.argv[1], sys.argv[2], sys.argv[3], Path(sys.argv[4]), sys.argv[5], sys.argv[6]
def origins(path):
    m = osim.Model(str(path)); s = m.initSystem(); b = m.getBodySet()
    return {b.get(i).getName(): np.array([b.get(i).getPositionInGround(s).get(k) for k in range(3)]) for i in range(b.getSize())}
d = lambda o, a, c: float(np.linalg.norm(o[a] - o[c]))
def lengths(o):
    L = {}
    for s in "rl":
        L[f"thigh_{s}"] = d(o, f"femur_{s}", f"tibia_{s}"); L[f"shank_{s}"] = d(o, f"tibia_{s}", f"talus_{s}"); L[f"foot_{s}"] = d(o, f"calcn_{s}", f"toes_{s}")
        L[f"upper_arm_{s}"] = d(o, f"humerus_{s}", f"ulna_{s}"); L[f"forearm_{s}"] = d(o, f"ulna_{s}", f"hand_{s}")
    L["hip_width"] = d(o, "femur_r", "femur_l")
    L["trunk"] = float(np.linalg.norm((o["humerus_r"] + o["humerus_l"]) / 2 - (o["femur_r"] + o["femur_l"]) / 2))
    return L
generic = resolve(load_config("mediapipe33_pose2sim")["model"])
G, Mo = lengths(origins(generic)), lengths(origins(mocap_model))
ratio = {k: Mo[k] / G[k] for k in G}
SEG = {"pelvis": "hip_width", "sacrum": "hip_width", "lumbar5": "trunk", "lumbar4": "trunk", "lumbar3": "trunk", "lumbar2": "trunk", "lumbar1": "trunk",
       "torso": "trunk", "head": "trunk", "Abdomen": "trunk"}
for s in "rl":
    SEG.update({f"femur_{s}": f"thigh_{s}", f"patella_{s}": f"thigh_{s}", f"tibia_{s}": f"shank_{s}", f"talus_{s}": f"foot_{s}", f"calcn_{s}": f"foot_{s}",
                f"toes_{s}": f"foot_{s}", f"humerus_{s}": f"upper_arm_{s}", f"ulna_{s}": f"forearm_{s}", f"radius_{s}": f"forearm_{s}", f"hand_{s}": f"forearm_{s}"})
if pdir.exists(): shutil.rmtree(pdir)
py = [sys.executable, "-I", "-m", "rehabtwin", "person"]
subprocess.run(py + ["init", str(pdir), "--person-ref", f"opencap-{subject}", "--height-m", height, "--mass-kg", mass], check=True, capture_output=True)
subprocess.run(py + ["build", str(pdir), session], check=True, capture_output=True)
rec = json.loads((pdir / "person.json").read_text())
old = rec["model"]["scale_set"]; assert set(old) == set(SEG), sorted(set(old) ^ set(SEG))
rec["model"]["scale_set"] = {b: [round(ratio[SEG[b]], 6)] * 3 for b in old}
(pdir / "person.json").write_text(json.dumps(rec, indent=1))
out = dict(subject=subject, generic_lengths_m={k: round(v, 4) for k, v in G.items()}, mocap_lengths_m={k: round(v, 4) for k, v in Mo.items()},
           scale_factor_by_segment={k: round(v, 4) for k, v in ratio.items()}, body_to_segment=SEG,
           height_scaled_round0_factors={b: round(v[0], 4) for b, v in old.items()})
(pdir / "twin_scale_factors.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out["scale_factor_by_segment"]))
