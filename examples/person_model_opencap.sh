#!/usr/bin/env bash
# Person model on real video (docs/person-model.md): bones from the 5-phone session of the OpenCap trial, then
# the 3-, 2- and 1-phone recordings of the same trial with those bones, each against OpenCap's own result.
# Run examples/opencap_agreement.sh OUT_DIR first, then this with the same OUT_DIR. The subsets need
# mp-multiview on cameras 1 2 3 and 0 4 (below). ~10 min on 4 CPU cores.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${1:-$ROOT/sessions/opencap_subject2_squats1}"
PY="${BIO_PY:-python}"
D="$OUT/data"
cd "$ROOT/pipeline"
REF=(--reference "$D/OpenSimData/Kinematics/squats1.mot" --reference-model "$D/OpenSimData/Model/LaiUhlrich2022_scaled.osim"
     --reference-grade markerless --max-lag-s 4 --reference-system "OpenCap 5-camera pipeline (OpenPose, LSTM augmenter, LaiUhlrich2022)")
SUBJ=(--exercise squat --mass-kg 78.2 --height-m 1.96 --person-ref opencap-subject2)
subset() {   # name cams...
  local name=$1; shift; local CAL=() DUMPS=()
  for c in "$@"; do CAL+=("$D/Videos/Cam$c/cameraIntrinsicsExtrinsics.pickle"); DUMPS+=("$OUT/cam$c.npz"); done
  [ -f "$OUT/${name}_aug_seq.npz" ] && return
  "$PY" -m rehabtwin mp-multiview "${DUMPS[@]}" --sync --out "$OUT/${name}_seq.npz" --person-ref opencap-subject2 --opencap-calib "${CAL[@]}"
  "$PY" -m rehabtwin augment "$OUT/${name}_seq.npz" "$OUT/${name}_aug_seq.npz" --height-m 1.96 --mass-kg 78.2 --mass-source measured
}
subset cams123 1 2 3
subset cams04 0 4
rm -rf "$OUT/person"
"$PY" -m rehabtwin person init "$OUT/person" --person-ref opencap-subject2 --height-m 1.96 --mass-kg 78.2
"$PY" -m rehabtwin person build "$OUT/person" "$OUT/multi_aug"       # the 5-phone session from opencap_agreement.sh
for s in cams123 cams04 mono; do
  "$PY" -m rehabtwin process "$OUT/${s}_aug_seq.npz" "$OUT/${s}_aug" "${SUBJ[@]}" "${REF[@]}"
  "$PY" -m rehabtwin process "$OUT/${s}_aug_seq.npz" "$OUT/${s}_person" "${SUBJ[@]}" "${REF[@]}" --person "$OUT/person"
done
echo "compare $OUT/{cams123,cams04,mono}_{aug,person}/validation-report.json; qc.json scaling.recording_scale"
