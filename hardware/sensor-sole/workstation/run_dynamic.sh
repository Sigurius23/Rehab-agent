#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors
# SPDX-License-Identifier: CERN-OHL-S-2.0
# Amendment 4, phase 1 (no force data): the pilot (subject2 squats1, both arms), then, only if the pilot gate passes
# (both arms converged and tracking within the gate, foot_models/dynamic_summary.py), every solve with the same
# settings. Resumable: run it again and finished solves are reused (foot_models/case_store.py).
# Meant to run unattended inside tmux; it blocks sleep, idle and the lid switch for as long as it runs:
#   tmux new-session -d -s dynamic 'hardware/sensor-sole/workstation/run_dynamic.sh'
#   JOBS=6 THREADS=4 ...  (defaults: 6 solves at once, 4 threads each)
set -u
if [ -z "${DYNAMIC_SLEEP_BLOCKED:-}" ] && command -v systemd-inhibit >/dev/null 2>&1; then
  export DYNAMIC_SLEEP_BLOCKED=1
  exec systemd-inhibit --what=sleep:idle:handle-lid-switch --who="rehab-agent dynamic run" \
      --why="Moco solves (run_dynamic.sh)" --mode=block "$0" "$@"
fi
HERE="$(cd "$(dirname "$0")/.." && pwd -P)"
DATA="${DATA:-$HOME/rehab-agent-data/sensor-sole}"
PY="${SIM_PY:-$DATA/envs/sim/bin/python}"
KIN="${KIN:-$HOME/rehab-agent-data/datasets/opencap-labvalidation/kinematics/LabValidation_withoutVideos}"
MODELS="${MODELS:-$DATA/forceplate/models}"
OUT="${OUT:-$DATA/forceplate/dynamic}"
JOBS="${JOBS:-6}"; THREADS="${THREADS:-4}"
PILOT=subject2_squats1
mkdir -p "$OUT/logs"
cd "$OUT"            # OpenSim and CasADi write files to the working directory; keep them out of the repository
stamp() { date '+%Y-%m-%d %H:%M:%S'; }
log() { echo "$(stamp) $*" | tee -a "$OUT/logs/run.log"; }
summary() {
  if "$PY" -I "$HERE/foot_models/dynamic_summary.py" "$OUT" -o "$OUT/dynamic_solutions_summary.json" >> "$OUT/logs/run.log" 2>&1; then
    log "summary written: $OUT/dynamic_solutions_summary.json"
  else
    log "summary FAILED (see above)"
  fi
}
log "pilot: subject2 squats1, arms A and B"
"$PY" -I "$HERE/foot_models/dynamic_track.py" batch --subjects-dir "$MODELS" --kinematics "$KIN" -o "$OUT" \
    --only subject2:squats1 --jobs 2 --threads $(( JOBS * THREADS / 2 )) >> "$OUT/logs/pilot.log" 2>&1
grep -E 'arm [AB]:|ERROR' "$OUT/logs/pilot.log" | tail -2 | tee -a "$OUT/logs/run.log"
gate_out="$("$PY" -I "$HERE/foot_models/dynamic_summary.py" "$OUT" --gate "$PILOT" 2>&1)"; gate_rc=$?
echo "$gate_out" | tee -a "$OUT/logs/run.log"
if [ "$gate_rc" -ne 0 ]; then
  log "STOP: the pilot gate did not pass; the settings need a logged change (both arms) before the batch."
  summary
  exit 1
fi
log "pilot gate passed; all solves, $JOBS at a time, $THREADS threads each"
"$PY" -I "$HERE/foot_models/dynamic_track.py" batch --subjects-dir "$MODELS" --kinematics "$KIN" -o "$OUT" \
    --jobs "$JOBS" --threads "$THREADS" >> "$OUT/logs/batch.log" 2>&1
grep -E 'arm [AB]:|ERROR|^done' "$OUT/logs/batch.log" | tee -a "$OUT/logs/run.log"
log "finished"
summary
