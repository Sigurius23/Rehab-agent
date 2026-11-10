#!/usr/bin/env bash
# Sensitivity analysis (owner, 2026-11-10): both one-camera routes against the motion capture at ONE shared lag,
# the five-camera-with-augmenter route's lag against the motion capture plus Cam2's offset from the multi-view
# sync (46 frames of sync lag + 5 frames trimmed at the common window's start = 51 frames at 60 fps). The pipeline
# is unchanged: a copy of the reference with its time column shifted by that lag, and --max-lag-s 0.
set -euo pipefail
K=$HOME/rehab-agent-data/kinematics; OUT=$K/pilot
PY=$K/envs/pipeline/bin/python; export REHAB_UPSTREAM=$K/upstream
L=$HOME/rehab-agent-data/datasets/opencap-labvalidation/kinematics/LabValidation_withoutVideos/subject2/OpenSimData/Mocap
mkdir -p "$OUT/sharedlag_ref"; cd "$OUT"
LAG=$("$PY" -I - "$OUT" <<'PYEOF'
import json, sys
from pathlib import Path
from rehabtwin.sequence import MarkerSequence
P = Path(sys.argv[1])
five = json.loads((P / "mocap/multi_aug/validation-report.json").read_text())["time_lag_applied_s"]
sy = MarkerSequence.load(P / "multi_seq.npz").meta["sync"]
fps = MarkerSequence.load(P / "mono_seq.npz").fps
cam2 = (sy["lags_frames"][2] + sy["reference_start_frame"]) / fps
print(repr(five + cam2))
(P / "sharedlag_ref/lag.json").write_text(json.dumps(dict(five_camera_augmenter_lag_s=five, cam2_sync_lag_frames=sy["lags_frames"][2],
    reference_start_frame=sy["reference_start_frame"], fps=fps, cam2_offset_s=cam2, shared_lag_s=five + cam2), indent=1))
PYEOF
)
"$PY" -I - "$L/IK/squats1.mot" "$OUT/sharedlag_ref/squats1_shifted.mot" "$LAG" <<'PYEOF'
import sys
src, dst, lag = sys.argv[1], sys.argv[2], float(sys.argv[3])
lines = open(src).read().splitlines()
i = next(k for k, l in enumerate(lines) if l.strip() == "endheader")
out = lines[:i + 2]          # header and the column labels
for l in lines[i + 2:]:
    if not l.strip():
        out.append(l); continue
    f = l.split("\t")
    f[0] = f"{float(f[0]) + lag:.8f}"
    out.append("\t".join(f))
open(dst, "w").write("\n".join(out) + "\n")
PYEOF
SUBJ=(--exercise squat --mass-kg 78.2 --height-m 1.96 --person-ref opencap-subject2)
REF=(--reference "$OUT/sharedlag_ref/squats1_shifted.mot" --reference-model "$L/Model/LaiArnoldModified2017_poly_withArms_weldHand_scaled.osim"
     --reference-grade marker-mocap --max-lag-s 0
     --reference-system "OpenCap LabValidation marker motion capture, inverse kinematics (LaiArnoldModified2017), subject2 squats1, time shifted by the shared lag $LAG s")
"$PY" -I -m rehabtwin process "$OUT/mono_seq.npz" "$OUT/mocap_sharedlag/mono" --config mediapipe33_pose2sim "${SUBJ[@]}" "${REF[@]}"
"$PY" -I -m rehabtwin process "$OUT/mono_aug_seq.npz" "$OUT/mocap_sharedlag/mono_aug" "${SUBJ[@]}" "${REF[@]}"
echo "shared lag $LAG s: done"
