cd $WORK/skel_work
OMP_NUM_THREADS=1 ${BIO_PY:-python} $REPO/pipeline/adapters/bedlam2_skel.py run --smplx $WORK/bedlam2_x/models_lockedhead/smplx/SMPLX_NEUTRAL.npz --smpl-dir $WORK/body_models/npz --skel-dir $WORK/body_models_skel/npz --motions $WORK/bedlam2_x/motions_npz_training --mapping "$WORK/bedlam2_dl/Rehab agent/b2_bedlam2amass_motion_training.csv" --jobs 4 --out $WORK/skel_work/skel_bones.json > $WORK/skel_work/full.log 2>&1
echo "exit $?" >> $WORK/skel_work/full.log
