#!/usr/bin/env bash
# Real-video validation demo on Pose2Sim's 4-camera "Demo_SinglePerson" trial
# (a person balancing on one leg; calibrated, synchronised cameras).
#
#   reference : MediaPipe on all 4 views, triangulated, OpenSim IK
#   estimate  : MediaPipe on camera 1 only (monocular), OpenSim IK
#
# The reference is markerless (same keypoint model), not gold standard: it
# measures what one camera loses against four, nothing more.
#
# Needs: the twin-live env (mediapipe, opencv) and the biomech env (opensim),
# see pipeline/README.md; `python3 scripts/clone.py --only perfanalytics/pose2sim`.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LIVE_PY="${LIVE_PY:-python}"        # interpreter with mediapipe
BIO_PY="${BIO_PY:-python}"          # interpreter with opensim + rehabtwin
MODEL="${MP_MODEL:?set MP_MODEL to pose_landmarker_heavy.task}"
OUT="${1:-$ROOT/sessions/pose2sim_demo}"
DEMO="$ROOT/upstream/perfanalytics/pose2sim/Pose2Sim/Demo_SinglePerson"
mkdir -p "$OUT"
cd "$ROOT/pipeline"

for c in 01 02 03 04; do
  "$LIVE_PY" adapters/mediapipe_pose.py "$DEMO/videos/cam$c.mp4" --model "$MODEL" --out "$OUT/cam${c}_mp.npz"
done
"$BIO_PY" -m rehabtwin mp-multiview "$OUT"/cam0{1,2,3,4}_mp.npz --qca "$DEMO/calibration/Calib.qca.txt" \
  --out "$OUT/multiview_seq.npz" --person-ref POSE2SIM-DEMO
# Camera 1's intrinsics and gravity direction come from the calibration here; on a phone they
# would come from the device (ARKit/CoreMotion gravity vector, lens metadata).
read -r FOCAL UP <<<"$("$BIO_PY" -c "
from rehabtwin.mediapipe_front import read_qca
c = read_qca('$DEMO/calibration/Calib.qca.txt')[0]
up = c.R @ [0, 0, 1]   # lab z-up expressed in camera 1 (OpenCV) coordinates
print(c.K[0, 0], ','.join(f'{v:.6f}' for v in up))")"
"$BIO_PY" -m rehabtwin mp-mono "$OUT/cam01_mp.npz" "$OUT/cam01_mono_seq.npz" --focal-px "$FOCAL" --person-ref POSE2SIM-DEMO
"$BIO_PY" -m rehabtwin mp-mono "$OUT/cam01_mp.npz" "$OUT/cam01_mono_gravity_seq.npz" --focal-px "$FOCAL" \
  --person-ref POSE2SIM-DEMO --gravity-up-cv "$UP" --gravity-source "lab calibration (stands in for phone IMU)"

"$BIO_PY" -m rehabtwin process "$OUT/multiview_seq.npz" "$OUT/multiview" --exercise free \
  --config mediapipe33_pose2sim --person-ref POSE2SIM-DEMO
"$BIO_PY" -m rehabtwin process "$OUT/cam01_mono_seq.npz" "$OUT/monocular" --exercise free \
  --config mediapipe33_pose2sim --person-ref POSE2SIM-DEMO \
  --reference "$OUT/multiview/opensim/ik.mot" --reference-grade markerless \
  --reference-system "4-camera MediaPipe triangulation + OpenSim IK (markerless, same keypoint model)"
"$BIO_PY" -m rehabtwin process "$OUT/cam01_mono_gravity_seq.npz" "$OUT/monocular_gravity" --exercise free \
  --config mediapipe33_pose2sim --person-ref POSE2SIM-DEMO \
  --reference "$OUT/multiview/opensim/ik.mot" --reference-grade markerless \
  --reference-system "4-camera MediaPipe triangulation + OpenSim IK (markerless, same keypoint model)"
echo "open $OUT/monocular*/report.html and $OUT/monocular*/validation-report.json"
