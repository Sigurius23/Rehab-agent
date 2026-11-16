# t-kin-camera-plus-imu-sim: fuse_trial.py over the trials evaluated in round 0, for the one-camera MediaPipe route
# without and with the augmenter. Resumable. Usage: python3 -I run_imu_sim.py [workers]
import json, subprocess, sys, time
from multiprocessing import Pool
from pathlib import Path
HOME = Path.home(); K = HOME / "rehab-agent-data/kinematics"; D = HOME / "rehab-agent-data/datasets/opencap-labvalidation"
OUT = K / "imu_sim/runs"; PY = K / "envs/pipeline/bin/python"
ENV = {"REHAB_UPSTREAM": str(K / "upstream"), "PATH": "/usr/bin:/bin", "HOME": str(HOME), "OMP_NUM_THREADS": "1"}
def one(job):
    s, t, r = job; o = OUT / s / t / r
    if (o / "record.json").exists(): return job, True
    o.mkdir(parents=True, exist_ok=True)
    p = subprocess.run([str(PY), "-I", str(K / "imu_sim/scripts/fuse_trial.py"), str(K / "bench/runs" / s / t / r / "opensim"),
                        str(D / "kinematics/LabValidation_withoutVideos" / s / "OpenSimData/Mocap/Model/LaiArnoldModified2017_poly_withArms_weldHand_scaled.osim"),
                        str(D / "mocap-ik/LabValidation_withoutVideos" / s / "OpenSimData/Mocap/IK" / f"{t}.mot"), str(o), f"{s}/{t}/{r}"],
                       capture_output=True, text=True, env=ENV, cwd=o)
    (o / "run.log").write_text(p.stdout[-3000:] + p.stderr[-3000:]); return job, p.returncode == 0
if __name__ == "__main__":
    rows = json.loads((K / "bench/results_v2.json").read_text())["rows"]
    jobs = [(x["subject"], x["trial"], x["route"]) for x in rows if x["route"] in ("mono", "mono_aug") and x["status"] == "evaluated"]
    print(time.strftime("%F %T"), len(jobs), "route-trials", flush=True)
    with Pool(int(sys.argv[1]) if len(sys.argv) > 1 else 12) as pool:
        for k, (j, ok) in enumerate(pool.imap_unordered(one, jobs), 1): print(time.strftime("%T"), f"[{k}/{len(jobs)}]", *j, "ok" if ok else "FAILED", flush=True)
    print(time.strftime("%F %T"), "done", flush=True)
