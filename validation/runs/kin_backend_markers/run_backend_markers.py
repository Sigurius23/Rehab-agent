# t-kin-backend-markers (method committed in ff572ba before this ran): OpenCap's *_study markers through the pipeline's
# back end, compared at lag 0 with the motion-capture IK. Resumable. Usage: python3 -I run_backend_markers.py [workers]
import json, re, subprocess, sys, time
from multiprocessing import Pool
from pathlib import Path
HOME = Path.home(); K = HOME / "rehab-agent-data/kinematics"; D = HOME / "rehab-agent-data/datasets/opencap-labvalidation"
TRC = D / "video-markers/LabValidation_withoutVideos"; MOC = D / "mocap-ik/LabValidation_withoutVideos"
MODELS = D / "kinematics/LabValidation_withoutVideos"; VID = D / "videos-synced/LabValidation_withVideos"
OUT = K / "backend_markers/runs"; PY = K / "envs/pipeline/bin/python"; ADAPTER = K / "backend_markers/scripts/trc_to_seq.py"
ENV = {"REHAB_UPSTREAM": str(K / "upstream"), "PATH": "/usr/bin:/bin", "HOME": str(HOME), "OMP_NUM_THREADS": "2"}
def run(cmd, log, cwd):
    with open(log, "a") as f:
        f.write(f"\n$ {' '.join(map(str, cmd))}\n"); f.flush()
        r = subprocess.run([str(c) for c in cmd], stdout=f, stderr=subprocess.STDOUT, cwd=cwd, env=ENV)
    if r.returncode: raise RuntimeError(f"exit {r.returncode}")
def one(job):
    s, t = job; d = OUT / s / t; d.mkdir(parents=True, exist_ok=True); sp = d / "status.json"
    st = json.loads(sp.read_text()) if sp.exists() else {}; log = d / "run.log"
    def step(name, fn):
        if name in st: return st[name]["ok"]
        try: fn(); st[name] = dict(ok=True)
        except Exception as e: st[name] = dict(ok=False, error=str(e)[:300])
        sp.write_text(json.dumps(st, indent=1)); return st[name]["ok"]
    trc = TRC / s / "MarkerData/Video/HRNet/2-cameras" / f"{t}_videoAndMocap.trc"
    if not trc.exists():
        st["inputs"] = dict(ok=False, error="no marker file"); sp.write_text(json.dumps(st, indent=1)); return job, st
    meta = (MODELS / s / "sessionMetadata.yaml").read_text()
    mass, height = [re.search(rf"^{k}:\s*([0-9.]+)", meta, re.M).group(1) for k in ("mass_kg", "height_m")]
    ref = MOC / s / "OpenSimData/Mocap/IK" / f"{t}.mot"
    ref_model = MODELS / s / "OpenSimData/Mocap/Model/LaiArnoldModified2017_poly_withArms_weldHand_scaled.osim"
    if step("adapter", lambda: run([PY, "-I", ADAPTER, trc, d / "seq.npz", f"opencap-{s}"], log, d)):
        step("process", lambda: run([PY, "-I", "-m", "rehabtwin", "process", d / "seq.npz", d / "session", "--config", "mediapipe_lstm_pose2sim",
                                     "--exercise", "squat", "--mass-kg", mass, "--height-m", height, "--person-ref", f"opencap-{s}",
                                     "--reference", ref, "--reference-model", ref_model, "--reference-grade", "marker-mocap", "--max-lag-s", "0",
                                     "--reference-system", f"OpenCap LabValidation marker motion capture IK, {s} {t}, lag 0"], log, d))
    return job, st
if __name__ == "__main__":
    jobs = [(p.parts[-5], p.stem) for p in sorted(MOC.glob("subject*/OpenSimData/Mocap/IK/*.mot"))]
    print(time.strftime("%F %T"), len(jobs), "trials", flush=True)
    with Pool(int(sys.argv[1]) if len(sys.argv) > 1 else 8) as pool:
        for k, ((s, t), st) in enumerate(pool.imap_unordered(one, jobs), 1):
            print(time.strftime("%T"), f"[{k}/{len(jobs)}] {s} {t}", {n: v.get("ok") for n, v in st.items()}, flush=True)
    print(time.strftime("%F %T"), "done", flush=True)
