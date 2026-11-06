#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors
# SPDX-License-Identifier: CERN-OHL-S-2.0
# Amendment 4, phase 1 (no force data): the pilot (subject2 squats1, both arms), then, only if both converged, every
# solve with the same settings. Resumable: run it again and finished solves are reused (foot_models/case_store.py).
# Meant to run unattended inside tmux:
#   tmux new-session -d -s dynamic 'hardware/sensor-sole/workstation/run_dynamic.sh'
#   JOBS=6 THREADS=4 ...  (defaults: 6 solves at once, 4 threads each)
set -u
HERE="$(cd "$(dirname "$0")/.." && pwd -P)"
DATA="${DATA:-$HOME/rehab-agent-data/sensor-sole}"
PY="${SIM_PY:-$DATA/envs/sim/bin/python}"
KIN="${KIN:-$HOME/rehab-agent-data/datasets/opencap-labvalidation/kinematics/LabValidation_withoutVideos}"
MODELS="${MODELS:-$DATA/forceplate/models}"
OUT="${OUT:-$DATA/forceplate/dynamic}"
JOBS="${JOBS:-6}"; THREADS="${THREADS:-4}"
mkdir -p "$OUT/logs"
cd "$OUT"            # OpenSim and CasADi write files to the working directory; keep them out of the repository
stamp() { date '+%Y-%m-%d %H:%M:%S'; }
echo "$(stamp) pilot: subject2 squats1, arms A and B" | tee -a "$OUT/logs/run.log"
"$PY" -I "$HERE/foot_models/dynamic_track.py" batch --subjects-dir "$MODELS" --kinematics "$KIN" -o "$OUT" \
    --only subject2:squats1 --jobs 2 --threads $(( JOBS * THREADS / 2 )) > "$OUT/logs/pilot.log" 2>&1
grep -E 'arm [AB]:|ERROR' "$OUT/logs/pilot.log" | tee -a "$OUT/logs/run.log"
if ! "$PY" -I -c '
import json, sys
from pathlib import Path
out = Path(sys.argv[1])
res = {}
for arm in "AB":
    for f in (out / "cases" / f"subject2_squats1_{arm}").glob("*/result.json"):
        res[arm] = json.loads(f.read_text())["converged"]
sys.exit(0 if res.get("A") and res.get("B") else 1)' "$OUT"; then
  echo "$(stamp) STOP: the pilot did not converge in both arms; the settings need a logged change (both arms) before the batch." | tee -a "$OUT/logs/run.log"
  exit 1
fi
echo "$(stamp) pilot converged in both arms; all solves, $JOBS at a time, $THREADS threads each" | tee -a "$OUT/logs/run.log"
"$PY" -I "$HERE/foot_models/dynamic_track.py" batch --subjects-dir "$MODELS" --kinematics "$KIN" -o "$OUT" \
    --jobs "$JOBS" --threads "$THREADS" > "$OUT/logs/batch.log" 2>&1
grep -E 'arm [AB]:|ERROR|^done' "$OUT/logs/batch.log" | tee -a "$OUT/logs/run.log"
echo "$(stamp) finished" | tee -a "$OUT/logs/run.log"
