set -uo pipefail
D=$WORK/oc_verify/data; M=$WORK/oc_merged; R=$WORK/skel_work/oc_person_fix; PY=${BIO_PY:-python}
cd $REPO/pipeline
export REHAB_UPSTREAM=$REPO/upstream
REF=(--reference "$D/OpenSimData/Kinematics/squats1.mot" --reference-model "$D/OpenSimData/Model/LaiUhlrich2022_scaled.osim"
     --reference-grade markerless --max-lag-s 4 --reference-system "OpenCap 5-camera pipeline (OpenPose, LSTM augmenter, LaiUhlrich2022)")
SUBJ=(--exercise squat --mass-kg 78.2 --height-m 1.96 --person-ref opencap-subject2)
$PY -m rehabtwin process $WORK/oc_final/multi_aug_seq.npz $R/multi_aug "${SUBJ[@]}" "${REF[@]}" > $R/multi_aug.log 2>&1
rm -rf $R/person
$PY -m rehabtwin person init $R/person --person-ref opencap-subject2 --height-m 1.96 --mass-kg 78.2 > $R/person.log 2>&1
$PY -m rehabtwin person build $R/person $R/multi_aug >> $R/person.log 2>&1
for s in mono cams04 cams123; do
  ( $PY -m rehabtwin process "$M/${s}_aug_seq.npz" "$R/${s}_alone" "${SUBJ[@]}" "${REF[@]}" > "$R/${s}_alone.log" 2>&1
    $PY -m rehabtwin process "$M/${s}_aug_seq.npz" "$R/${s}_person" "${SUBJ[@]}" "${REF[@]}" --person "$R/person" > "$R/${s}_person.log" 2>&1
    echo "$s exit $?" >> $R/done.txt ) &
done
wait
echo ALL >> $R/done.txt
