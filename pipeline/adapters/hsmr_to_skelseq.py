#!/usr/bin/env python3
"""Convert an HSMR demo dump into a rehabtwin SKEL sequence (skel_seq.npz).

Run this INSIDE the HSMR environment (it needs torch and the SKEL package),
after HSMR's own demo:

    cd upstream/IsshikiHugh/HSMR
    python exp/run_demo.py --input_path /path/to/exercise.mp4 --output_path /path/to/hsmr_out --ignore_skel
    python /path/to/rehab-agent/pipeline/adapters/hsmr_to_skelseq.py \
        --hsmr-npy /path/to/hsmr_out/HSMR-exercise.npy --video /path/to/exercise.mp4 \
        --skel-model-dir data_inputs/body_models/skel --out /path/to/session/skel_seq.npz \
        --person-ref P001 [--height-m 1.78]

Then, in the biomech environment:

    python -m rehabtwin process /path/to/session/skel_seq.npz /path/to/session --exercise squat

Licensing: SKEL/BSM model files and the SMPL2AddBiomechanics marker map are
non-commercial research assets of MPI-IS. They are read from your own
download/clone at run time and are never copied into this repository.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[1]))  # pipeline/ -> import rehabtwin

from rehabtwin.hsmr import build_sequence, hsmr_input_size  # noqa: E402

DEFAULT_MARKERS = HERE.parents[2] / "upstream" / "MarilynKeller" / "SMPL2AddBiomechanics" / "smpl2ab" / "data" / "bsm_markers.yaml"


def load_marker_ids(path):
    """Tiny parser for 'NAME: vertex_id  # comment' lines (avoids a PyYAML dependency)."""
    ids = {}
    for line in Path(path).read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        k, v = line.split(":", 1)
        if v.strip():
            ids[k.strip()] = int(v.strip())
    if len(ids) < 50:
        raise ValueError(f"{path}: expected ~105 markers, parsed {len(ids)}")
    return ids


def video_meta(path):
    """(fps, width, height, n_frames) via OpenCV if available, else ffprobe."""
    try:
        import cv2
        cap = cv2.VideoCapture(str(path))
        fps = cap.get(cv2.CAP_PROP_FPS)
        w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.release()
        if fps > 0 and w > 0:
            return fps, w, h, n
    except ImportError:
        pass
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height,r_frame_rate,nb_frames", "-of", "json", str(path)],
                         capture_output=True, text=True, check=True)
    st = json.loads(out.stdout)["streams"][0]
    num, den = st["r_frame_rate"].split("/")
    return float(num) / float(den), int(st["width"]), int(st["height"]), int(st.get("nb_frames", 0))


def make_skel_forward(model_dir, gender, device):
    import torch
    from skel.skel_model import SKEL
    model = SKEL(gender=gender, model_path=str(model_dir)).to(device).eval()

    def forward(poses, betas):
        with torch.no_grad():
            p = torch.as_tensor(np.asarray(poses), dtype=torch.float32, device=device)
            b = torch.as_tensor(np.asarray(betas), dtype=torch.float32, device=device)
            out = model(poses=p, betas=b, trans=torch.zeros(len(p), 3, device=device), skelmesh=False)
            return out.skin_verts.cpu().numpy(), out.joints.cpu().numpy()
    return forward


def git_head(path):
    r = subprocess.run(["git", "-C", str(path), "rev-parse", "HEAD"], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else "unknown"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--hsmr-npy", required=True, help="HSMR-<video>.npy written by exp/run_demo.py")
    ap.add_argument("--video", required=True, help="the original video (for fps and image size)")
    ap.add_argument("--skel-model-dir", required=True, help="folder with skel_male.pkl (SKEL v1.1.1)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--gender", default="male", help="must match the SKEL model HSMR used (male by default)")
    ap.add_argument("--marker-yaml", default=str(DEFAULT_MARKERS), help="SMPL2AddBiomechanics bsm_markers.yaml")
    ap.add_argument("--height-m", type=float, help="measured standing height; fixes monocular scale")
    ap.add_argument("--person-ref", default="UNSPECIFIED", help="pseudonymous subject reference (never a name)")
    ap.add_argument("--image-size", help="WxH HSMR ran on, if not derivable from the video (e.g. 1080x608)")
    ap.add_argument("--fps", type=float, help="override video fps")
    ap.add_argument("--per-frame-betas", action="store_true", help="let body shape vary per frame (default: median)")
    ap.add_argument("--max-jump", type=float, default=0.6, help="track continuity threshold (box sizes)")
    ap.add_argument("--device", default="cuda:0" if _cuda() else "cpu")
    ap.add_argument("--hsmr-root", default=str(HERE.parents[2] / "upstream" / "IsshikiHugh" / "HSMR"))
    a = ap.parse_args()

    # The HSMR dump is a pickled list of dicts produced by your own HSMR run.
    frames = list(np.load(a.hsmr_npy, allow_pickle=True))
    fps, w, h, n = video_meta(a.video)
    fps = a.fps or fps
    if a.image_size:
        iw, ih = map(int, a.image_size.lower().split("x"))
    else:
        iw, ih = hsmr_input_size(w, h)
    if n and abs(n - len(frames)) > 1:
        print(f"warning: video has {n} frames, HSMR dump has {len(frames)}", file=sys.stderr)
    seq = build_sequence(
        frames, make_skel_forward(a.skel_model_dir, a.gender, a.device), fps, (iw, ih),
        load_marker_ids(a.marker_yaml), gender=a.gender, height_m=a.height_m,
        per_frame_betas=a.per_frame_betas, max_jump=a.max_jump,
        meta={"person_ref": a.person_ref, "video": str(a.video), "video_size": [w, h],
              "upstream_pins": {"IsshikiHugh/HSMR": git_head(a.hsmr_root)},
              "marker_map": str(a.marker_yaml)})
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    seq.save(out)
    print(json.dumps({"out": str(out), "frames": seq.n_frames, "valid": int(seq.valid.sum()), "fps": fps,
                      "skel_height_m": seq.meta["skel_height_m"], "image_size": [iw, ih]}, indent=1))


def _cuda():
    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        return False


if __name__ == "__main__":
    main()
