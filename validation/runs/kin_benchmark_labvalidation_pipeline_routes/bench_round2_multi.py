# Fix round 2 of 2 (t-kin-labvalidation, recorded in 1963484 before this ran): the multi-view routes back to round 0's
# --sync offsets, from round 0's MediaPipe dumps; the reference is shifted by the sync's trimmed start (as in round 0),
# compared at lag 0. Writes runs_round2/<subject>/<trial>/{multi,multi_aug}; rounds 0 and 1 are left as they are. Usage: python3 -I bench_round1.py [--workers N] [subjectN/trial ...]
import json, re, subprocess, sys, time
from multiprocessing import Pool
from pathlib import Path
HOME = Path.home(); K = HOME / "rehab-agent-data/kinematics"
R0, R1 = K / "bench/runs", K / "bench/runs_round2"
VID = HOME / "rehab-agent-data/datasets/opencap-labvalidation/videos-synced/LabValidation_withVideos"
MOC = HOME / "rehab-agent-data/datasets/opencap-labvalidation/mocap-ik/LabValidation_withoutVideos"
MODELS = HOME / "rehab-agent-data/datasets/opencap-labvalidation/kinematics/LabValidation_withoutVideos"
PY = K / "envs/pipeline/bin/python"; CAMS = [f"Cam{c}" for c in range(5)]
ENV = {"REHAB_UPSTREAM": str(K / "upstream"), "PATH": "/usr/bin:/bin", "HOME": str(HOME), "OMP_NUM_THREADS": "2"}

def run(cmd, log, cwd):
    with open(log, "a") as f:
        f.write(f"\n$ {' '.join(map(str, cmd))}\n"); f.flush()
        r = subprocess.run([str(c) for c in cmd], stdout=f, stderr=subprocess.STDOUT, cwd=cwd, env=ENV)
    if r.returncode: raise RuntimeError(f"exit {r.returncode}: {cmd[3] if len(cmd) > 3 else cmd}")

def one(job):
    subject, trial = job; d0, d = R0 / subject / trial, R1 / subject / trial; d.mkdir(parents=True, exist_ok=True)
    sp = d / "status.json"; st = json.loads(sp.read_text()) if sp.exists() else {}; log = d / "run.log"
    def step(name, fn):
        if name in st: return st[name]["ok"]
        t0 = time.time()
        try: fn(); st[name] = dict(ok=True, s=round(time.time() - t0, 1))
        except Exception as e: st[name] = dict(ok=False, error=str(e)[:400])
        sp.write_text(json.dumps(st, indent=1)); return st[name]["ok"]
    s0 = json.loads((d0 / "status.json").read_text())
    if not s0.get("inputs", {}).get("ok") or not all(s0.get(f"mediapipe_{c}", {}).get("ok") for c in CAMS):
        st["inputs"] = dict(ok=False, error="no synced videos or no MediaPipe dumps in round 0"); sp.write_text(json.dumps(st, indent=1)); return job, st
    t = (VID / subject / "sessionMetadata.yaml").read_text(); mass, height = [re.search(rf"^{k}:\s*([0-9.]+)", t, re.M).group(1) for k in ("mass_kg", "height_m")]
    session = s0["inputs"]["session"]; cal = [VID / subject / "VideoData" / session / c / "cameraIntrinsicsExtrinsics.pickle" for c in CAMS]
    ref = MOC / subject / "OpenSimData/Mocap/IK" / f"{trial}.mot"
    ref_model = MODELS / subject / "OpenSimData/Mocap/Model/LaiArnoldModified2017_poly_withArms_weldHand_scaled.osim"
    subj = ["--exercise", "squat", "--mass-kg", mass, "--height-m", height, "--person-ref", f"opencap-{subject}"]
    refa = ["--reference", ref, "--reference-model", ref_model, "--reference-grade", "marker-mocap", "--max-lag-s", "0",
            "--reference-system", f"OpenCap LabValidation marker motion capture IK, {subject} {trial}, lag 0 (synced video, round 0 sync shift)"]
    if step("multi_seq", lambda: run([PY, "-I", "-m", "rehabtwin", "mp-multiview", *[d0 / f"{c}.npz" for c in CAMS], "--sync", "--out", d / "multi_seq.npz",
                                      "--person-ref", f"opencap-{subject}", "--opencap-calib", *cal], log, d)):
        def shift():
            out = subprocess.run([str(PY), "-I", "-c", "import json,sys;from rehabtwin.sequence import MarkerSequence as M;s=M.load(sys.argv[1]);"
                                  "print(json.dumps(dict(start=s.meta['sync']['reference_start_frame'],fps=s.fps,lags=s.meta['sync']['lags_frames'])))",
                                  str(d / "multi_seq.npz")], capture_output=True, text=True, env=ENV, check=True)
            sy = json.loads(out.stdout); st["multi_sync"] = sy
            lines = ref.read_text().splitlines(); i = next(k for k, l in enumerate(lines) if l.strip() == "endheader"); o = lines[:i + 2]
            for l in lines[i + 2:]:
                if l.strip(): f = l.split("\t"); f[0] = f"{float(f[0]) - sy['start'] / sy['fps']:.8f}"; l = "\t".join(f)
                o.append(l)
            (d / "ref_multi.mot").write_text("\n".join(o) + "\n")
        step("multi_ref", shift)
        refa[1] = d / "ref_multi.mot"
        step("multi", lambda: run([PY, "-I", "-m", "rehabtwin", "process", d / "multi_seq.npz", d / "multi", "--config", "mediapipe33_pose2sim", *subj, *refa], log, d))
        if step("multi_aug_seq", lambda: run([PY, "-I", "-m", "rehabtwin", "augment", d / "multi_seq.npz", d / "multi_aug_seq.npz",
                                              "--height-m", height, "--mass-kg", mass, "--mass-source", "measured"], log, d)):
            step("multi_aug", lambda: run([PY, "-I", "-m", "rehabtwin", "process", d / "multi_aug_seq.npz", d / "multi_aug", *subj, *refa], log, d))
    return job, st

if __name__ == "__main__":
    a = sys.argv[1:]; w = 8
    if a[:1] == ["--workers"]: w, a = int(a[1]), a[2:]
    jobs = [(p.parts[-3], p.parts[-2]) for p in sorted(R0.glob("*/*/status.json"))]
    jobs = [j for j in jobs if not a or f"{j[0]}/{j[1]}" in a]
    print(time.strftime("%F %T"), len(jobs), "trials", flush=True)
    with Pool(w) as pool:
        for k, ((s, t), st) in enumerate(pool.imap_unordered(one, jobs), 1):
            print(time.strftime("%F %T"), f"[{k}/{len(jobs)}] {s} {t}", {n: v.get("ok") for n, v in st.items()}, flush=True)
    print(time.strftime("%F %T"), "done", flush=True)
