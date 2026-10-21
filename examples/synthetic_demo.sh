#!/usr/bin/env bash
# Everything rehabtwin does, on a synthetic squat with known truth (no camera, no gated models):
# measurement -> validation -> correction view -> muscle effects (+ weakness, + ideal exo) -> haptic cue replay.
# Needs the biomech env (pip install -e "pipeline[test]") and `python3 scripts/clone.py --only perfanalytics/pose2sim`.
# Takes ~25 min on 4 CPU cores (static optimisation dominates). Open OUT/index.html afterwards.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="${BIO_PY:-python}"
OUT="${1:-$ROOT/sessions/synthetic_demo}"
cd "$ROOT/pipeline"
"$PY" -m rehabtwin selftest "$OUT"                                    # synth -> process -> validate vs truth
"$PY" -m rehabtwin correct "$OUT" --spec squat_knee_valgus_right --illustrative
"$PY" -m rehabtwin correct "$OUT" --spec squat_trunk_upright --illustrative
"$PY" -m rehabtwin muscles "$OUT" --rep 1 --correction squat_knee_valgus_right \
  --weaken gluteus_medius_r=0.5 --assist knee_angle_r=40:neg
"$PY" -m rehabtwin cues "$OUT" --rules squat_posture
"$PY" -m rehabtwin cues "$OUT" --rules squat_posture --motion "$OUT/correction/squat_knee_valgus_right/corrected.mot"
echo "open $OUT/index.html"
