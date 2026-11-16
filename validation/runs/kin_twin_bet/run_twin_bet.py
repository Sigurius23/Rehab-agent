# t-twin-bet-scaled-model (method committed in 3a1c5da before this ran): the one-camera routes and HSMR reprocessed with
# each subject's stand-in twin (make_person.py) through `rehabtwin process --person`, at lag 0 against the motion capture.
# Sequences are reused: round 0's mono_seq/mono_aug_seq, round 2's HSMR skel_seq. Resumable. Usage: python3 -I run_twin_bet.py [workers]
import json, re, subprocess, sys, time
from multiprocessing import Pool
from pathlib import Path
HOME = Path.home(); K = HOME / "rehab-agent-data/kinematics"; D = HOME / "rehab-agent-data/datasets/opencap-labvalidation"
MOC = D / "mocap-ik/LabValidation_withoutVideos"; MODELS = D / "kinematics/LabValidation_withoutVideos"
R0, R2, OUT, PERS = K / "bench/runs", K / "bench/runs_round2", K / "twin_bet/runs", K / "twin_bet/persons"
PY = K / "envs/pipeline/bin/python"; SCR = K / "twin_bet/scripts"
ENV = {"REHAB_UPSTREAM": str(K / "upstream"), "PATH": "/usr/bin:/bin", "HOME": str(HOME), "OMP_NUM_THREADS": "2"}
MOCAP_MODEL = "OpenSimData/Mocap/Model/LaiArnoldModified2017_poly_withArms_weldHand_scaled.osim"
def run(cmd, log, cwd):
    with open(log, "a") as f:
        f.write(f"\n$ {' '.join(map(str, cmd))}\n"); f.flush()
        r = subprocess.run([str(c) for c in cmd], stdout=f, stderr=subprocess.STDOUT, cwd=cwd, env=ENV)
    if r.returncode: raise RuntimeError(f"exit {r.returncode}")
def meta(s):
    t = (MODELS / s / "sessionMetadata.yaml").read_text()
    return [re.search(rf"^{k}:\s*([0-9.]+)", t, re.M).group(1) for k in ("mass_kg", "height_m")]
def one(job):
    s, t = job; d = OUT / s / t; d.mkdir(parents=True, exist_ok=True); sp = d / "status.json"
    st = json.loads(sp.read_text()) if sp.exists() else {}; log = d / "run.log"
    def step(name, fn):
        if name in st: return st[name]["ok"]
        try: fn(); st[name] = dict(ok=True)
        except Exception as e: st[name] = dict(ok=False, error=str(e)[:300])
        sp.write_text(json.dumps(st, indent=1)); return st[name]["ok"]
    mass, height = meta(s); ref = MOC / s / "OpenSimData/Mocap/IK" / f"{t}.mot"; st["inputs"] = dict(ok=True)
    common = ["--exercise", "squat", "--mass-kg", mass, "--height-m", height, "--person-ref", f"opencap-{s}", "--person", PERS / s,
              "--reference", ref, "--reference-model", MODELS / s / MOCAP_MODEL, "--reference-grade", "marker-mocap", "--max-lag-s", "0",
              "--reference-system", f"OpenCap LabValidation marker motion capture IK, {s} {t}, lag 0 (synced video); person model = mocap-scaled segments"]
    for route, seq, cfg, out in (("mono", R0 / s / t / "mono_seq.npz", "mediapipe33_pose2sim", d / "mono"),
                                 ("mono_aug", R0 / s / t / "mono_aug_seq.npz", "mediapipe_lstm_pose2sim", d / "mono_aug"),
                                 ("hsmr", R2 / s / t / "hsmr_route/skel_seq.npz", "skel105_pose2sim", d / "hsmr_route/session")):
        if not seq.exists(): st[route] = dict(ok=False, error="no sequence from the earlier round"); continue
        out.parent.mkdir(parents=True, exist_ok=True)
        step(route, lambda: run([PY, "-I", "-m", "rehabtwin", "process", seq, out, "--config", cfg, *common], log, d))
    (d / "hsmr_route").mkdir(exist_ok=True); (d / "hsmr_route/status_hsmr.json").write_text(json.dumps({"process": st.get("hsmr", {"ok": False})}))
    sp.write_text(json.dumps(st, indent=1)); return job, st
if __name__ == "__main__":
    subjects = sorted({p.parts[-3] for p in R0.glob("*/*/mono_seq.npz")}, key=lambda x: int(x[7:]))
    print(time.strftime("%F %T"), "persons for", subjects, flush=True)
    for s in subjects:
        if (PERS / s / "twin_scale_factors.json").exists(): continue
        sess = sorted(p.parent for p in R0.glob(f"{s}/*/mono/session.json"))[0]; mass, height = meta(s)
        r = subprocess.run([str(PY), "-I", str(SCR / "make_person.py"), s, str(MODELS / s / MOCAP_MODEL), str(sess), str(PERS / s), mass, height], capture_output=True, text=True, env=ENV, cwd=OUT.parent)
        print(s, "from", sess.parent.name, r.stdout.strip().splitlines()[-1] if r.returncode == 0 else "FAILED " + r.stderr[-300:], flush=True)
        if r.returncode: sys.exit(1)
    jobs = [(p.parts[-3], p.parts[-2]) for p in sorted(R0.glob("*/*/mono_seq.npz"))]
    print(time.strftime("%F %T"), len(jobs), "trials", flush=True)
    with Pool(int(sys.argv[1]) if len(sys.argv) > 1 else 8) as pool:
        for k, ((s, t), st) in enumerate(pool.imap_unordered(one, jobs), 1):
            print(time.strftime("%T"), f"[{k}/{len(jobs)}] {s} {t}", {n: v.get("ok") for n, v in st.items()}, flush=True)
    print(time.strftime("%F %T"), "done", flush=True)
