cd $REPO/pipeline
export REHAB_UPSTREAM=$REPO/upstream
for v in reg age dxa; do
  ${BIO_PY:-python} -m rehabtwin muscles $WORK/dxa_demo/s_$v --rep 2 --no-3d --person $WORK/dxa_demo/P_$v > $WORK/dxa_demo/$v.log 2>&1
  echo "$v exit $?" >> $WORK/dxa_demo/done.txt
done
