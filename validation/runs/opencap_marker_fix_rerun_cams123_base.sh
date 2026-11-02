cd $REPO/pipeline
export REHAB_UPSTREAM=$REPO/upstream
until [ "$(wc -l < $WORK/skel_work/oc_fix/done.txt)" -ge 10 ]; do sleep 20; done
grep -q '"marker_rescale"' configs/mediapipe_lstm_pose2sim.json && { echo "config has the fix: not a baseline"; exit 3; }
rm -rf $WORK/skel_work/oc_fix/cams123_aug_base
D=$WORK/oc_verify/data
${BIO_PY:-python} -m rehabtwin process $WORK/oc_verify/cams123_aug_seq.npz $WORK/skel_work/oc_fix/cams123_aug_base --config mediapipe_lstm_pose2sim --exercise squat --mass-kg 78.2 --height-m 1.96 --person-ref opencap-subject2 \
  --reference $D/OpenSimData/Kinematics/squats1.mot --reference-model $D/OpenSimData/Model/LaiUhlrich2022_scaled.osim \
  --reference-grade markerless --max-lag-s 4 --reference-system "OpenCap 5-camera pipeline" > $WORK/skel_work/oc_fix/cams123_aug_base.log 2>&1
echo "cams123_aug base-rerun exit $?" >> $WORK/skel_work/oc_fix/done.txt
