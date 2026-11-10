#!/usr/bin/env bash
# Video-benchmark pilot, stage B (only after the alignment check passed): each route processed against the trial's
# marker motion capture (the pilot's reference) and against OpenCap's own markerless result (the comparison).
set -euo pipefail
K=$HOME/rehab-agent-data/kinematics; OUT=$K/pilot; D=$OUT/data
PY=$K/envs/pipeline/bin/python; export REHAB_UPSTREAM=$K/upstream
L=$HOME/rehab-agent-data/datasets/opencap-labvalidation/kinematics/LabValidation_withoutVideos/subject2/OpenSimData/Mocap
cd "$OUT"
SUBJ=(--exercise squat --mass-kg 78.2 --height-m 1.96 --person-ref opencap-subject2)
REF_mocap=(--reference "$L/IK/squats1.mot" --reference-model "$L/Model/LaiArnoldModified2017_poly_withArms_weldHand_scaled.osim"
           --reference-grade marker-mocap --max-lag-s 4
           --reference-system "OpenCap LabValidation marker motion capture, inverse kinematics (LaiArnoldModified2017), subject2 squats1")
REF_opencap=(--reference "$D/OpenSimData/Kinematics/squats1.mot" --reference-model "$D/OpenSimData/Model/LaiUhlrich2022_scaled.osim"
             --reference-grade markerless --max-lag-s 4 --reference-system "OpenCap 5-camera pipeline (OpenPose, LSTM augmenter, LaiUhlrich2022)")
for ref in mocap opencap; do
  declare -n R="REF_$ref"
  echo "$(date '+%F %T') reference $ref"
  "$PY" -I -m rehabtwin process "$OUT/multi_seq.npz" "$OUT/$ref/multi" --config mediapipe33_pose2sim "${SUBJ[@]}" "${R[@]}"
  "$PY" -I -m rehabtwin process "$OUT/multi_aug_seq.npz" "$OUT/$ref/multi_aug" "${SUBJ[@]}" "${R[@]}"
  "$PY" -I -m rehabtwin process "$OUT/mono_seq.npz" "$OUT/$ref/mono" --config mediapipe33_pose2sim "${SUBJ[@]}" "${R[@]}"
  "$PY" -I -m rehabtwin process "$OUT/mono_aug_seq.npz" "$OUT/$ref/mono_aug" "${SUBJ[@]}" "${R[@]}"
done
echo "$(date '+%F %T') stage B done"
