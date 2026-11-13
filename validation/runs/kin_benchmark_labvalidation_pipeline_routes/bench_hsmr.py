# Full benchmark, HSMR route (t-kin-labvalidation; HSMR's rules recorded in 4119c00 before it ran). Per trial: HSMR's
# demo on Cam2's *_syncdWithMocap video, the repository's adapter (hsmr_to_skelseq.py) to skel_seq.npz, then
# rehabtwin process against the motion-capture IK at lag 0 (--max-lag-s 0). One trial at a time (GPU).
# Resumable; each step is recorded in runs/<subject>/<trial>/status_hsmr.json.
import json, re, subprocess, sys, time
from pathlib import Path

HOME = Path.home(); K = HOME / "rehab-agent-data/kinematics"
VID = HOME / "rehab-agent-data/datasets/opencap-labvalidation/videos-synced/LabValidation_withVideos"
MOC = HOME / "rehab-agent-data/datasets/opencap-labvalidation/mocap-ik/LabValidation_withoutVideos"
MODELS = HOME / "rehab-agent-data/datasets/opencap-labvalidation/kinematics/LabValidation_withoutVideos"
OUT = K / "bench/runs"; HSMR = K / "upstream/IsshikiHugh/HSMR"; REPO = HOME / "rehab-agent"
ENV = {"PATH": "/usr/bin:/bin", "HOME": str(HOME), "FVCORE_CACHE": str(K / "cache"), "REHAB_UPSTREAM": str(K / "upstream")}

def run(cmd, log, cwd):
    with open(log, "a") as f:
        f.write(f"\n$ {' '.join(map(str, cmd))}\n"); f.flush()
        r = subprocess.run([str(c) for c in cmd], stdout=f, stderr=subprocess.STDOUT, cwd=cwd, env=ENV)
    if r.returncode: raise RuntimeError(f"exit {r.returncode}: {Path(str(cmd[1])).name if len(cmd) > 1 else cmd[0]}")

def meta(subject):
    t = (VID / subject / "sessionMetadata.yaml").read_text()
    return [float(re.search(rf"^{k}:\s*([0-9.]+)", t, re.M).group(1)) for k in ("mass_kg", "height_m")]

def one(subject, trial):
    d = OUT / subject / trial / "hsmr_route"; d.mkdir(parents=True, exist_ok=True)
    sp = d / "status_hsmr.json"; st = json.loads(sp.read_text()) if sp.exists() else {}; log = d / "run.log"
    def step(name, fn):
        if name in st: return st[name]["ok"]
        t0 = time.time()
        try: fn(); st[name] = dict(ok=True, s=round(time.time() - t0, 1))
        except Exception as e: st[name] = dict(ok=False, error=str(e)[:400], s=round(time.time() - t0, 1))
        sp.write_text(json.dumps(st, indent=1)); return st[name]["ok"]
    v = next(VID.glob(f"{subject}/VideoData/Session*/Cam2/{trial}/{trial}_syncdWithMocap.avi"), None)
    if v is None:
        st["inputs"] = dict(ok=False, error="no synced Cam2 video"); sp.write_text(json.dumps(st, indent=1)); return st
    mass, height = meta(subject); npy = d / "hsmr_out" / f"HSMR-{v.stem}.npy"
    ref = MOC / subject / "OpenSimData/Mocap/IK" / f"{trial}.mot"
    ref_model = MODELS / subject / "OpenSimData/Mocap/Model/LaiArnoldModified2017_poly_withArms_weldHand_scaled.osim"
    if step("hsmr_demo", lambda: run([K / "envs/hsmr/bin/python", "exp/run_demo.py", "--input_path", v, "--output_path", d / "hsmr_out",
                                      "--ignore_skel", "--rec_bs", "32", "--max_instances", "1"], log, HSMR)):
        (d / "hsmr_out" / f"HSMR-{v.stem}.mp4").unlink(missing_ok=True)   # the rendered video is not needed
        if step("adapter", lambda: run([K / "envs/hsmr/bin/python", REPO / "pipeline/adapters/hsmr_to_skelseq.py", "--hsmr-npy", npy, "--video", v,
                                        "--skel-model-dir", HSMR / "data_inputs/body_models/skel", "--out", d / "skel_seq.npz",
                                        "--person-ref", f"opencap-{subject}", "--height-m", height, "--hsmr-root", HSMR,
                                        "--marker-yaml", K / "upstream/MarilynKeller/SMPL2AddBiomechanics/smpl2ab/data/bsm_markers.yaml"], log, d)):
            step("process", lambda: run([K / "envs/pipeline/bin/python", "-I", "-m", "rehabtwin", "process", d / "skel_seq.npz", d / "session",
                                         "--exercise", "squat", "--mass-kg", mass, "--height-m", height, "--person-ref", f"opencap-{subject}",
                                         "--reference", ref, "--reference-model", ref_model, "--reference-grade", "marker-mocap", "--max-lag-s", "0",
                                         "--reference-system", f"OpenCap LabValidation marker motion capture IK, {subject} {trial}, lag 0 (synced video)"], log, d))
    return st

if __name__ == "__main__":
    only = sys.argv[1:]
    jobs = [(s.name, m.stem) for s in sorted(MOC.glob("subject*"), key=lambda p: int(p.name[7:])) for m in sorted((s / "OpenSimData/Mocap/IK").glob("*.mot"))]
    jobs = [j for j in jobs if not only or f"{j[0]}/{j[1]}" in only]
    print(time.strftime("%F %T"), len(jobs), "trials", flush=True)
    for k, (s, t) in enumerate(jobs, 1):
        st = one(s, t)
        print(time.strftime("%F %T"), f"[{k}/{len(jobs)}] {s} {t}", {n: v.get("ok") for n, v in st.items()}, flush=True)
    print(time.strftime("%F %T"), "done", flush=True)
