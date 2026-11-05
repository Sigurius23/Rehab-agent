#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors
# SPDX-License-Identifier: CERN-OHL-S-2.0
#
# Start, or resume, the experimental foot-model comparison on a workstation set up with workstation/setup.sh.
# Finished cases are reused (foot_models/case_store.py), so after an interruption run the same command again.
# Output: DATA/runs/comparison/summary.json, one folder per case, and OpenSim's log in opensim_logs/ there.
# After a full run, the results are checked against foot_models/results_2026-11-04.json
# (foot_models/compare_results.py). The check is printed; it does not change this script's exit code.
#
#   workstation/run_comparison.sh                         every group, cores - 2 cases at a time
#   workstation/run_comparison.sh --only controlled_cop   one group (any run_comparison.py option passes through)
#   JOBS=4 workstation/run_comparison.sh
#   SPACING_SOLES="DATA/soles/3.75mm DATA/soles/2.5mm" workstation/run_comparison.sh --only discretisation
# For a long run, start it inside tmux or with nohup, so closing the terminal does not stop it. A laptop that
# sleeps pauses the run; one that shuts down loses only the cases in progress.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOLE="$(dirname "$HERE")"
DATA="${DATA:-$HOME/rehab-agent-data/sensor-sole}"
[ -d "$DATA" ] && DATA="$(cd "$DATA" && pwd -P)"
SIM_PY="${SIM_PY:-$DATA/envs/sim/bin/python}"
[ -f "$DATA/inputs/inputs.env" ] || { echo "run workstation/setup.sh first (no $DATA/inputs/inputs.env)" >&2; exit 1; }
# shellcheck disable=SC1091
source "$DATA/inputs/inputs.env"
[ -n "${SELFTEST_MODEL:-}" ] || { echo "no self-test model recorded: run workstation/setup.sh inputs" >&2; exit 1; }
JOBS="${JOBS:-$(( $(nproc) > 3 ? $(nproc) - 2 : 1 ))}"
one() { [ $# = 1 ] && [ -f "$1" ] || { echo "expected exactly one file, found: $*" >&2; return 1; }; echo "$1"; }
SR=$(one "$SOLE"/sim/EU42_R_*.sole_sim.json); SL=$(one "$SOLE"/sim/EU42_L_*.sole_sim.json)
SR10=$(one "$SOLE"/sim/spacing/10mm/EU42_R_*.sole_sim.json); SL10=$(one "$SOLE"/sim/spacing/10mm/EU42_L_*.sole_sim.json)
OUT="$DATA/runs/comparison"
# shellcheck disable=SC2086
"$SIM_PY" "$SOLE/foot_models/run_comparison.py" \
  --selftest "$SELFTEST_MODEL" --dhondt "$DHONDT_NOMINAL_DIR" --mot "$SQUAT_MOT" \
  --sole-r "$SR" --sole-l "$SL" --sole-r10 "$SR10" --sole-l10 "$SL10" \
  --spacing-soles "$SOLE/sim/spacing/10mm" "$SOLE/sim/spacing/7.5mm" "$SOLE/sim/spacing/5mm" ${SPACING_SOLES:-} \
  --out "$OUT" --jobs "$JOBS" "$@"

# A full run is checked against the recorded results. --only (one group) or extra soles give a different set of
# cases, so those are not checked here. A later --out (also abbreviated) replaces the folder, as in argparse.
full=1; prev=""
for arg in "$@"; do
  case "$prev" in --ou|--out) OUT=$arg ;; esac
  case "$arg" in --ou=*|--out=*) OUT=${arg#*=} ;; esac
  case "$arg" in --on*|--sp*) full=0 ;; esac                # --only, --spacing-soles (or abbreviated)
  prev=$arg
done
[ -z "${SPACING_SOLES:-}" ] || full=0
check=(python3 -I "$SOLE/foot_models/compare_results.py" "$OUT/summary.json")
if [ "$full" = 1 ]; then
  echo "== results check against foot_models/results_2026-11-04.json"
  if "${check[@]}"; then
    echo "results check: passed"
  else
    echo "results check: FAILED, see above (the run itself finished; its results are in $OUT/summary.json)"
  fi
else
  echo "results check: not run (not a full run); to check by hand: $(printf '%q ' "${check[@]}")"
fi
