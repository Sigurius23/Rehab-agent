# Full benchmark, the pipeline's own routes (plan/nodes/t-kin-labvalidation.md; design approved 2026-11-10, commit
# 7736081, before any video was extracted). Per trial, from the dataset's *_syncdWithMocap videos:
#   MediaPipe per camera (Cam0-Cam4) -> four routes, as examples/opencap_agreement.sh runs them:
#     multi      mp-multiview --sync (5 cameras), process --config mediapipe33_pose2sim
#     multi_aug  augment, process
#     mono       mp-mono on Cam2 (focal and gravity from that session's calibration), process --config mediapipe33_pose2sim
#     mono_aug   augment, process
# Each route is compared with the trial's motion-capture IK at lag 0 (the synced video's frame k is mocap time k/60).
# The only shift is the route's own: the multi-view sync's trimmed start (reference_start_frame / fps), applied to a
# copy of the reference's time column, with --max-lag-s 0. The lag-search best case is computed afterwards.
# Resumable: each step leaves its output; a failed step is recorded in status.json and not retried unless --retry.
# Usage: python -I bench_run.py [--workers N] [--only subjectN/trial ...] [--retry]
import argparse, json, re, subprocess, sys, time, traceback
from multiprocessing import Pool
from pathlib import Path

HOME = Path.home()
K = HOME / "rehab-agent-data/kinematics"
VID = HOME / "rehab-agent-data/datasets/opencap-labvalidation/videos-synced/LabValidation_withVideos"
MOC = HOME / "rehab-agent-data/datasets/opencap-labvalidation/mocap-ik/LabValidation_withoutVideos"
MODELS = HOME / "rehab-agent-data/datasets/opencap-labvalidation/kinematics/LabValidation_withoutVideos"
OUT = K / "bench/runs"
REPO = HOME / "rehab-agent"
PY, MP = K / "envs/pipeline/bin/python", K / "envs/mediapipe/bin/python"
TASK = K / "models/mediapipe/pose_landmarker_heavy.task"
ENV = {"REHAB_UPSTREAM": str(K / "upstream"), "PATH": "/usr/bin:/bin", "HOME": str(HOME), "OMP_NUM_THREADS": "2"}
CAMS = [f"Cam{c}" for c in range(5)]
MONO_CAM = "Cam2"


def meta(subject):
    txt = (VID / subject / "sessionMetadata.yaml").read_text()
    g = lambda k: float(re.search(rf"^{k}:\s*([0-9.]+)", txt, re.M).group(1))
    return g("mass_kg"), g("height_m")


def trials():
    out = []
    for s in sorted(MOC.glob("subject*"), key=lambda p: int(p.name[7:])):
        for mot in sorted((s / "OpenSimData/Mocap/IK").glob("*.mot")):
            out.append((s.name, mot.stem))
    return out


def run(cmd, log, cwd):
    with open(log, "a") as f:
        f.write(f"\n$ {' '.join(map(str, cmd))}\n"); f.flush()
        r = subprocess.run([str(c) for c in cmd], stdout=f, stderr=subprocess.STDOUT, cwd=cwd, env=ENV)
    if r.returncode != 0:
        raise RuntimeError(f"exit {r.returncode}: {' '.join(map(str, cmd[:4]))}")


def shifted_ref(src, dst, lag):
    lines = Path(src).read_text().splitlines()
    i = next(k for k, l in enumerate(lines) if l.strip() == "endheader")
    out = lines[:i + 2]
    for l in lines[i + 2:]:
        if l.strip():
            f = l.split("\t"); f[0] = f"{float(f[0]) + lag:.8f}"; l = "\t".join(f)
        out.append(l)
    Path(dst).write_text("\n".join(out) + "\n")


def one(job):
    subject, trial, retry = job
    d = OUT / subject / trial; d.mkdir(parents=True, exist_ok=True)
    st_path = d / "status.json"
    st = json.loads(st_path.read_text()) if st_path.exists() else {}
    log = d / "run.log"
    def step(name, fn):
        if st.get(name, {}).get("ok") or (st.get(name) and not retry):
            return st[name].get("ok", False)
        t0 = time.time()
        try:
            fn(); st[name] = dict(ok=True, s=round(time.time() - t0, 1))
        except Exception as e:
            st[name] = dict(ok=False, error=f"{type(e).__name__}: {e}"[:500], s=round(time.time() - t0, 1))
        st_path.write_text(json.dumps(st, indent=1))
        return st[name]["ok"]
    try:
        vids = {c: next(VID.glob(f"{subject}/VideoData/Session*/{c}/{trial}/{trial}_syncdWithMocap.avi"), None) for c in CAMS}
        if any(v is None for v in vids.values()):
            st["inputs"] = dict(ok=False, error=f"missing synced video for {[c for c, v in vids.items() if v is None]}")
            st_path.write_text(json.dumps(st, indent=1)); return subject, trial, st
        session = vids["Cam0"].parts[-4]
        cal = {c: VID / subject / "VideoData" / session / c / "cameraIntrinsicsExtrinsics.pickle" for c in CAMS}
        mass, height = meta(subject)
        ref = MOC / subject / "OpenSimData/Mocap/IK" / f"{trial}.mot"
        ref_model = MODELS / subject / "OpenSimData/Mocap/Model/LaiArnoldModified2017_poly_withArms_weldHand_scaled.osim"
        st["inputs"] = dict(ok=True, session=session, mass_kg=mass, height_m=height)
        subj = ["--exercise", "squat", "--mass-kg", mass, "--height-m", height, "--person-ref", f"opencap-{subject}"]
        refargs = lambda r: ["--reference", r, "--reference-model", ref_model, "--reference-grade", "marker-mocap", "--max-lag-s", "0",
                             "--reference-system", f"OpenCap LabValidation marker motion capture IK, {subject} {trial}, lag 0 (synced video)"]
        for c in CAMS:
            step(f"mediapipe_{c}", lambda c=c: (d / f"{c}.npz").exists() or run(
                [MP, "-I", REPO / "pipeline/adapters/mediapipe_pose.py", vids[c], "--model", TASK, "--out", d / f"{c}.npz"], log, d))
        dumps = [d / f"{c}.npz" for c in CAMS]
        if all(st.get(f"mediapipe_{c}", {}).get("ok") for c in CAMS):
            if step("multi_seq", lambda: run([PY, "-I", "-m", "rehabtwin", "mp-multiview", *dumps, "--sync", "--out", d / "multi_seq.npz",
                                              "--person-ref", f"opencap-{subject}", "--opencap-calib", *[cal[c] for c in CAMS]], log, d)):
                def multi_ref():
                    out = subprocess.run([str(PY), "-I", "-c", "import json,sys;from rehabtwin.sequence import MarkerSequence as M;"
                                          "s=M.load(sys.argv[1]);print(json.dumps(dict(start=s.meta['sync']['reference_start_frame'],fps=s.fps,lags=s.meta['sync']['lags_frames'])))",
                                          str(d / "multi_seq.npz")], capture_output=True, text=True, env=ENV, cwd=d, check=True)
                    sy = json.loads(out.stdout); st["multi_sync"] = sy
                    shifted_ref(ref, d / "ref_multi.mot", -sy["start"] / sy["fps"])
                if step("multi_ref", multi_ref):
                    step("multi", lambda: run([PY, "-I", "-m", "rehabtwin", "process", d / "multi_seq.npz", d / "multi", "--config", "mediapipe33_pose2sim",
                                               *subj, *refargs(d / "ref_multi.mot")], log, d))
                    if step("multi_aug_seq", lambda: run([PY, "-I", "-m", "rehabtwin", "augment", d / "multi_seq.npz", d / "multi_aug_seq.npz",
                                                          "--height-m", height, "--mass-kg", mass, "--mass-source", "measured"], log, d)):
                        step("multi_aug", lambda: run([PY, "-I", "-m", "rehabtwin", "process", d / "multi_aug_seq.npz", d / "multi_aug",
                                                       *subj, *refargs(d / "ref_multi.mot")], log, d))
        if st.get(f"mediapipe_{MONO_CAM}", {}).get("ok"):
            def mono_seq():
                out = subprocess.run([str(PY), "-I", "-c", "import sys,numpy as np;from rehabtwin.mediapipe_front import read_opencap_calibration as r;"
                                      "c=r([sys.argv[1]])[0];print((c.K[0,0]+c.K[1,1])/2);print(','.join(f'{v:.5f}' for v in c.R@np.array([0.0,-1.0,0.0])))",
                                      str(cal[MONO_CAM])], capture_output=True, text=True, env=ENV, cwd=d, check=True)
                focal, up = out.stdout.split()
                st["mono_calibration"] = dict(camera=MONO_CAM, focal_px=float(focal), gravity_up_cv=up)
                run([PY, "-I", "-m", "rehabtwin", "mp-mono", d / f"{MONO_CAM}.npz", d / "mono_seq.npz", "--focal-px", f"{float(focal):.1f}",
                     f"--gravity-up-cv={up}", "--gravity-source", "checkerboard calibration", "--person-ref", f"opencap-{subject}"], log, d)
            if step("mono_seq", mono_seq):
                step("mono", lambda: run([PY, "-I", "-m", "rehabtwin", "process", d / "mono_seq.npz", d / "mono", "--config", "mediapipe33_pose2sim",
                                          *subj, *refargs(ref)], log, d))
                if step("mono_aug_seq", lambda: run([PY, "-I", "-m", "rehabtwin", "augment", d / "mono_seq.npz", d / "mono_aug_seq.npz",
                                                     "--height-m", height, "--mass-kg", mass, "--mass-source", "measured"], log, d)):
                    step("mono_aug", lambda: run([PY, "-I", "-m", "rehabtwin", "process", d / "mono_aug_seq.npz", d / "mono_aug",
                                                  *subj, *refargs(ref)], log, d))
    except Exception:
        st["crash"] = traceback.format_exc()[-1500:]
    st_path.write_text(json.dumps(st, indent=1))
    return subject, trial, st


if __name__ == "__main__":
    a = argparse.ArgumentParser(); a.add_argument("--workers", type=int, default=8); a.add_argument("--only", nargs="*"); a.add_argument("--retry", action="store_true")
    a = a.parse_args()
    jobs = [(s, t, a.retry) for s, t in trials() if not a.only or f"{s}/{t}" in a.only]
    print(time.strftime("%F %T"), f"{len(jobs)} trials, {a.workers} workers", flush=True)
    with Pool(a.workers) as pool:
        for k, (s, t, st) in enumerate(pool.imap_unordered(one, jobs), 1):
            routes = {r: st.get(r, {}).get("ok") for r in ("multi", "multi_aug", "mono", "mono_aug")}
            print(time.strftime("%F %T"), f"[{k}/{len(jobs)}] {s} {t}", routes, "crash" if "crash" in st else "", flush=True)
    print(time.strftime("%F %T"), "done", flush=True)
