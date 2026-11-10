#!/usr/bin/env bash
# Video-benchmark pilot, stage A: the four routes of examples/opencap_agreement.sh (a copy, outside the repo),
# processed WITHOUT a reference, so that no error is computed before the alignment check.
set -euo pipefail
K=$HOME/rehab-agent-data/kinematics; OUT=$K/pilot; D=$OUT/data; REPO=$HOME/rehab-agent
PY=$K/envs/pipeline/bin/python; MP=$K/envs/mediapipe/bin/python; TASK=$K/models/mediapipe/pose_landmarker_heavy.task
export REHAB_UPSTREAM=$K/upstream
cd "$OUT"
CAL=(); DUMPS=()
for c in 0 1 2 3 4; do
  [ -f "cam$c.npz" ] || "$MP" -I "$REPO/pipeline/adapters/mediapipe_pose.py" "$D/Videos/Cam$c/InputMedia/squats1/squats1.mov" --model "$TASK" --out "$OUT/cam$c.npz"
  CAL+=("$D/Videos/Cam$c/cameraIntrinsicsExtrinsics.pickle"); DUMPS+=("$OUT/cam$c.npz")
done
SUBJ=(--exercise squat --mass-kg 78.2 --height-m 1.96 --person-ref opencap-subject2)
echo "$(date '+%F %T') five cameras"
"$PY" -I -m rehabtwin mp-multiview "${DUMPS[@]}" --sync --out "$OUT/multi_seq.npz" --person-ref opencap-subject2 --opencap-calib "${CAL[@]}"
"$PY" -I -m rehabtwin process "$OUT/multi_seq.npz" "$OUT/noref/multi" --config mediapipe33_pose2sim "${SUBJ[@]}"
"$PY" -I -m rehabtwin augment "$OUT/multi_seq.npz" "$OUT/multi_aug_seq.npz" --height-m 1.96 --mass-kg 78.2 --mass-source measured
"$PY" -I -m rehabtwin process "$OUT/multi_aug_seq.npz" "$OUT/noref/multi_aug" "${SUBJ[@]}"
echo "$(date '+%F %T') one camera"
UP=$("$PY" -I -c "
from rehabtwin.mediapipe_front import read_opencap_calibration
import numpy as np
c = read_opencap_calibration(['$D/Videos/Cam2/cameraIntrinsicsExtrinsics.pickle'])[0]
print(','.join(f'{v:.5f}' for v in c.R @ np.array([0.0, -1.0, 0.0])))")
"$PY" -I -m rehabtwin mp-mono "$OUT/cam2.npz" "$OUT/mono_seq.npz" --focal-px 913.3 --gravity-up-cv="$UP" \
    --gravity-source "checkerboard calibration" --person-ref opencap-subject2
"$PY" -I -m rehabtwin process "$OUT/mono_seq.npz" "$OUT/noref/mono" --config mediapipe33_pose2sim "${SUBJ[@]}"
"$PY" -I -m rehabtwin augment "$OUT/mono_seq.npz" "$OUT/mono_aug_seq.npz" --height-m 1.96 --mass-kg 78.2 --mass-source measured
"$PY" -I -m rehabtwin process "$OUT/mono_aug_seq.npz" "$OUT/noref/mono_aug" "${SUBJ[@]}"
echo "$(date '+%F %T') stage A done"
