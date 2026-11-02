cd $REPO/pipeline
export REHAB_UPSTREAM=$REPO/upstream
D=$WORK/oc_verify/data
O=$WORK/skel_work/oc_fix
mkdir -p $O
for s in multi_aug cams04_aug cams123_aug cams13_aug mono_aug; do
  for c in base fix; do
    if [ $c = fix ]; then CFG=(--config $WORK/skel_work/cfg/lstm_markerfix.json); else CFG=(--config mediapipe_lstm_pose2sim); fi
    ${BIO_PY:-python} -m rehabtwin process $WORK/oc_verify/${s}_seq.npz $O/${s}_$c "${CFG[@]}" --exercise squat --mass-kg 78.2 --height-m 1.96 --person-ref opencap-subject2 \
      --reference $D/OpenSimData/Kinematics/squats1.mot --reference-model $D/OpenSimData/Model/LaiUhlrich2022_scaled.osim \
      --reference-grade markerless --max-lag-s 4 --reference-system "OpenCap 5-camera pipeline" > $O/${s}_$c.log 2>&1
    echo "$s $c exit $?" >> $O/done.txt
  done
done
