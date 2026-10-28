# Knee joint load on the OpenCap subject 2 squat (docs/joint-load.md): the dxa_squat.sh session with the
# illustrative DXA record (not this person's scan), rep 2, fat -5 kg, quadriceps at 120 %, both, GRF band +/-0.10.
cd $REPO/pipeline
export REHAB_UPSTREAM=$REPO/upstream
rm -rf $WORK/joint_load && mkdir -p $WORK/joint_load
cp -r $WORK/dxa_demo/s_dxa $WORK/joint_load/session && rm -rf $WORK/joint_load/session/muscles
${BIO_PY:-python} -m rehabtwin joint-load $WORK/joint_load/session --rep 2 --person $WORK/dxa_demo/P_dxa \
  --fat-change-kg -5 --strengthen quadriceps_r=1.2 --strengthen quadriceps_l=1.2 --grf-sensitivity 0.10 \
  > $WORK/joint_load/run.log 2>&1
echo "exit $?" >> $WORK/joint_load/run.log
${BIO_PY:-python} -I $REPO/validation/runs/joint_load_table.py $WORK/joint_load/session/muscles/study.json \
  > $REPO/validation/results/joint_load_squat.json
