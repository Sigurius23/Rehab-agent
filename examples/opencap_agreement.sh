#!/usr/bin/env bash
# Real-video agreement check against OpenCap on one public trial (docs/validation-results.md §4):
# OpenCap LabValidation fixture subject2 / squats1 — 5 synchronised-ish iPhones, checkerboard calibration,
# and OpenCap's own IK result (OpenPose + LSTM marker augmenter + LaiUhlrich2022) as a *markerless* reference.
# Needs: biomech env with onnxruntime (pip install -e "pipeline[test,augment]"), the twin-live env with
# mediapipe, pose_landmarker_heavy.task, and `python3 scripts/clone.py --only perfanalytics/pose2sim`.
# ~10 min on 4 CPU cores. Usage: examples/opencap_agreement.sh OUT_DIR [MODEL.task]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${1:-$ROOT/sessions/opencap_subject2_squats1}"
TASK="${2:-pose_landmarker_heavy.task}"
PY="${BIO_PY:-python}"            # biomech env
MP="${MP_PY:-python}"             # env with mediapipe
B=https://raw.githubusercontent.com/stanfordnmbl/opencap-test-data/main/Data/labvalidation-fixtures/subject2_session0_5-cameras
D="$OUT/data"; mkdir -p "$D"
for f in OpenSimData/Kinematics/squats1.mot OpenSimData/Model/LaiUhlrich2022_scaled.osim sessionMetadata.yaml \
         $(for c in 0 1 2 3 4; do echo Videos/Cam$c/InputMedia/squats1/squats1.mov Videos/Cam$c/cameraIntrinsicsExtrinsics.pickle; done); do
  [ -f "$D/$f" ] || { mkdir -p "$D/$(dirname "$f")"; curl -sSf --retry 3 -o "$D/$f" "$B/$f"; }
done
cd "$ROOT/pipeline"
CAL=(); DUMPS=()
for c in 0 1 2 3 4; do
  [ -f "$OUT/cam$c.npz" ] || "$MP" adapters/mediapipe_pose.py "$D/Videos/Cam$c/InputMedia/squats1/squats1.mov" --model "$TASK" --out "$OUT/cam$c.npz"
  CAL+=("$D/Videos/Cam$c/cameraIntrinsicsExtrinsics.pickle"); DUMPS+=("$OUT/cam$c.npz")
done
REF=(--reference "$D/OpenSimData/Kinematics/squats1.mot" --reference-model "$D/OpenSimData/Model/LaiUhlrich2022_scaled.osim"
     --reference-grade markerless --max-lag-s 4 --reference-system "OpenCap 5-camera pipeline (OpenPose, LSTM augmenter, LaiUhlrich2022)")
SUBJ=(--exercise squat --mass-kg 78.2 --height-m 1.96 --person-ref opencap-subject2)
# 5 cameras: triangulated keypoints, then + LSTM anatomical markers (the recommended path)
"$PY" -m rehabtwin mp-multiview "${DUMPS[@]}" --sync --out "$OUT/multi_seq.npz" --person-ref opencap-subject2 --opencap-calib "${CAL[@]}"
"$PY" -m rehabtwin process "$OUT/multi_seq.npz" "$OUT/multi" --config mediapipe33_pose2sim "${SUBJ[@]}" "${REF[@]}"
"$PY" -m rehabtwin augment "$OUT/multi_seq.npz" "$OUT/multi_aug_seq.npz" --height-m 1.96 --mass-kg 78.2 --mass-source measured
"$PY" -m rehabtwin process "$OUT/multi_aug_seq.npz" "$OUT/multi_aug" "${SUBJ[@]}" "${REF[@]}"
# 1 camera (Cam2, facing the subject): calibrated focal length and the board's gravity direction
UP=$("$PY" -c "
from rehabtwin.mediapipe_front import read_opencap_calibration
import numpy as np
c = read_opencap_calibration(['$D/Videos/Cam2/cameraIntrinsicsExtrinsics.pickle'])[0]
print(','.join(f'{v:.5f}' for v in c.R @ np.array([0.0, -1.0, 0.0])))")
"$PY" -m rehabtwin mp-mono "$OUT/cam2.npz" "$OUT/mono_seq.npz" --focal-px 913.3 --gravity-up-cv="$UP" \
    --gravity-source "checkerboard calibration" --person-ref opencap-subject2
"$PY" -m rehabtwin process "$OUT/mono_seq.npz" "$OUT/mono" --config mediapipe33_pose2sim "${SUBJ[@]}" "${REF[@]}"
"$PY" -m rehabtwin augment "$OUT/mono_seq.npz" "$OUT/mono_aug_seq.npz" --height-m 1.96 --mass-kg 78.2 --mass-source measured
"$PY" -m rehabtwin process "$OUT/mono_aug_seq.npz" "$OUT/mono_aug" "${SUBJ[@]}" "${REF[@]}"
echo "validation reports: $OUT/{multi,multi_aug,mono,mono_aug}/validation-report.json"
