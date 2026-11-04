#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors
# SPDX-License-Identifier: CERN-OHL-S-2.0
#
# Set up a workstation (such as the lab laptop) for the sensor-sole simulations. Linux or WSL2 (Ubuntu).
# Installs nothing system-wide and needs no account or token. Everything goes under DATA, outside the
# repository (default ~/rehab-agent-data/sensor-sole):
#   envs/sim        Python 3.13 with OpenSim 4.6, numpy, scipy, jsonschema (the comparison, the pipeline self-test)
#   envs/casadi     Python 3.13 with CasADi 3.8.2, numpy, scipy (the bspline check). Separate on purpose: OpenSim
#                   4.6's wheel carries its own CasADi 3.7 for Moco, and CasADi 3.8.2 cannot be loaded in the same
#                   process, whichever is imported first.
#   envs/generator  Python 3.13 with the generator's packages (requirements.txt), pinned
#   inputs/         the external models and kinematics at their pinned commits, checked against
#                   foot_models/PROVENANCE.json (fetch_inputs.py), plus the two-segment self-test model
#   machine.json    the machine (CPU, cores, memory, GPU, OS) and every package version
#   test_runs/      what each test suite did on this machine
#   boards/, soles/ regenerated EU 42 boards and their exports at other spacings (the `soles` step)
#
#   workstation/setup.sh                  envs, inputs, machine and tests
#   workstation/setup.sh envs|inputs|machine|tests
#   workstation/setup.sh tests --slow     also the slow generator cases (minutes each)
#   workstation/setup.sh soles 3.75 2.5   contact-point spacings (mm) beyond the committed 15/10/7.5/5
#   DATA=/elsewhere workstation/setup.sh
#   SIM_PY=... CASADI_PY=... GEN_PY=... KPY=...   use existing Pythons instead of making the environments
#
# Needs: bash, git, python3 (any 3.8+, for the standard-library helpers) and uv (https://docs.astral.sh/uv/;
# it downloads Python 3.13 itself if the system has none). Optional: KiCad 7 with its Python (pcbnew) for the
# board-check suites.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOLE="$(dirname "$HERE")"
REPO="$(cd "$SOLE/../.." && pwd)"
DATA="${DATA:-$HOME/rehab-agent-data/sensor-sole}"
PY_VERSION=3.13
SIM_PKGS=(opensim==4.6 numpy==2.5.4 scipy==1.18.1 jsonschema==4.26.0)
CASADI_PKGS=(casadi==3.8.2 numpy==2.5.4 scipy==1.18.1)
GEN_PKGS=(numpy==2.5.4 scipy==1.18.1 shapely==2.2.0 matplotlib==3.11.2 ezdxf==1.4.5 manifold3d==3.5.4)
OWN_SIM=${SIM_PY:+1}; OWN_CASADI=${CASADI_PY:+1}; OWN_GEN=${GEN_PY:+1}
KPY="${KPY:-python3}"

die() { echo "setup: $*" >&2; exit 1; }
say() { echo "== $*"; }

checks() {
  [ "$(uname -s)" = Linux ] || die "run this under Linux or WSL2 (Ubuntu); this is $(uname -s)"
  command -v git >/dev/null || die "git not found"
  command -v python3 >/dev/null || die "python3 not found"
  mkdir -p "$DATA"
  DATA="$(cd "$DATA" && pwd -P)"
  case "$DATA/" in "$(cd "$REPO" && pwd -P)/"*) die "DATA ($DATA) must be outside the repository";; esac
  SIM_PY="${SIM_PY:-$DATA/envs/sim/bin/python}"
  CASADI_PY="${CASADI_PY:-$DATA/envs/casadi/bin/python}"
  GEN_PY="${GEN_PY:-$DATA/envs/generator/bin/python}"
}

make_env() {   # name, python path, variable that overrides it, packages...
  local name=$1 py=$2 var=$3; shift 3
  command -v uv >/dev/null || die "uv not found: install it (https://docs.astral.sh/uv/getting-started/installation/) or set $var"
  [ -x "$py" ] || uv venv -q -p "$PY_VERSION" "$DATA/envs/$name"
  uv pip install -q --python "$py" "$@"
  echo "$name: $("$py" -c 'import sys; print(sys.version.split()[0])'), $*"
}

step_envs() {
  say "environments in $DATA/envs"
  [ -n "$OWN_SIM" ] && echo "sim: using $SIM_PY" || make_env sim "$SIM_PY" SIM_PY "${SIM_PKGS[@]}"
  [ -n "$OWN_CASADI" ] && echo "casadi: using $CASADI_PY" || make_env casadi "$CASADI_PY" CASADI_PY "${CASADI_PKGS[@]}"
  [ -n "$OWN_GEN" ] && echo "generator: using $GEN_PY" || make_env generator "$GEN_PY" GEN_PY "${GEN_PKGS[@]}"
  "$SIM_PY" -c "import opensim; print('opensim', opensim.__version__)"
  "$CASADI_PY" -c "import casadi; print('casadi', casadi.__version__)"
  "$GEN_PY" -c "import shapely; print('shapely', shapely.__version__)"
}

step_inputs() {
  say "external inputs in $DATA/inputs"
  python3 -I "$HERE/fetch_inputs.py" --data "$DATA"
  # shellcheck disable=SC1091
  source "$DATA/inputs/inputs.env"
  # The two-segment foot is the pipeline's self-test model, made by the pipeline as it was at the recorded commit.
  # Today's pipeline scales body masses differently, so it would give another model.
  local commit st model want got prov="$SOLE/foot_models/PROVENANCE.json"
  commit=$(python3 -I -c "import json,sys; print(json.load(open(sys.argv[1]))['two_segment']['pipeline_commit'])" "$prov")
  want=$(python3 -I -c "import json,sys; print(json.load(open(sys.argv[1]))['two_segment']['sha256'])" "$prov")
  st="$DATA/inputs/selftest_${commit:0:7}"; model="$st/out/opensim/model_scaled.osim"
  if [ ! -f "$model" ]; then
    say "two-segment model: the pipeline's self-test at ${commit:0:7} (synthetic squat; a minute or two)"
    git -C "$REPO" cat-file -e "$commit^{commit}" 2>/dev/null \
      || die "commit $commit is not in this clone: fetch the full history (git fetch --unshallow) and run again"
    rm -rf "$st"; mkdir -p "$st"
    git -C "$REPO" archive "$commit" pipeline schemas | tar -x -C "$st"
    (cd "$st" && REHAB_UPSTREAM="$REHAB_UPSTREAM" PYTHONPATH="$st/pipeline" "$SIM_PY" -m rehabtwin selftest "$st/out") \
      > "$st/selftest.log" 2>&1 || echo "setup: the self-test reported a problem (see $st/selftest.log)" >&2
  fi
  [ -f "$model" ] || die "no self-test model at $model (see $st/selftest.log)"
  got=$(sha256sum "$model" | cut -d' ' -f1)
  if [ "$got" = "$want" ]; then
    echo "two-segment model: matches the recorded sha256"
  else
    echo "two-segment model: sha256 $got differs from the recorded $want."
    echo "  Runs record the hash they used, and their two-segment results are not the recorded comparison's."
  fi
  printf 'export SELFTEST_MODEL=%q\n' "$model" >> "$DATA/inputs/inputs.env"
}

step_machine() {
  say "machine record: $DATA/machine.json"
  local freeze=()
  for name in sim casadi generator; do
    local var="${name^^}_PY"; [ "$name" = generator ] && var=GEN_PY
    freeze+=("$name" "$(uv pip freeze --python "${!var}" 2>/dev/null | tr '\n' ' ' || echo unavailable)")
  done
  python3 -I - "$DATA/machine.json" "$REPO" "${freeze[@]}" <<'PY'
import json, os, platform, shutil, subprocess, sys, time
out, repo, *pairs = sys.argv[1:]
def sh(*cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=30).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""
cpu = next((l.split(":", 1)[1].strip() for l in open("/proc/cpuinfo") if l.startswith("model name")), platform.processor())
mem = next((int(l.split()[1]) for l in open("/proc/meminfo") if l.startswith("MemTotal")), 0)
osr = dict(l.strip().split("=", 1) for l in open("/etc/os-release") if "=" in l) if os.path.exists("/etc/os-release") else {}
rec = dict(recorded=time.strftime("%Y-%m-%dT%H:%M:%S%z"),
           os=osr.get("PRETTY_NAME", "").strip('"'), kernel=platform.release(),
           wsl="microsoft" in platform.release().lower(),
           cpu=cpu, logical_cores=os.cpu_count(), memory_gib=round(mem / 2**20, 1),
           gpu=sh("nvidia-smi", "--query-gpu=name,driver_version,memory.total", "--format=csv,noheader")
               if shutil.which("nvidia-smi") else "none found (nvidia-smi absent)",
           repository=dict(commit=sh("git", "-C", repo, "rev-parse", "HEAD"),
                           uncommitted_changes=bool(sh("git", "-C", repo, "status", "--porcelain"))),
           environments={pairs[i]: pairs[i + 1].split() for i in range(0, len(pairs), 2)})
open(out, "w").write(json.dumps(rec, indent=1) + "\n")
print(f"{rec['cpu']}, {rec['logical_cores']} logical cores, {rec['memory_gib']} GiB; GPU: {rec['gpu']}")
PY
}

step_tests() {
  local slow=${1:-}
  say "test suites (record in $DATA/test_runs)"
  [ -f "$DATA/inputs/inputs.env" ] || die "run the inputs step first"
  # shellcheck disable=SC1091
  source "$DATA/inputs/inputs.env"
  local rec="$DATA/test_runs"; mkdir -p "$rec"; rm -f "$rec"/*.json "$rec"/*.log   # this run only
  run() {   # config name, python, modules...
    local name=$1 py=$2; shift 2
    echo "  $name: $*"
    (cd "$SOLE/tests" && "$py" run_suites.py "$@" 2> "$rec/$name.log" | tail -1 > "$rec/$name.json") \
      || echo "setup: $name did not finish (see $rec/$name.log)" >&2
  }
  run sim "$SIM_PY" test_sim_osim test_dhondt_port test_foot_comparison test_case_store
  run casadi "$CASADI_PY" test_dhondt_port
  if [ "$slow" = --slow ]; then
    SOLE_SLOW_TESTS=1 run generator "$GEN_PY" test_sim_print test_generator_regressions
  else
    run generator "$GEN_PY" test_sim_print test_generator_regressions
  fi
  run system python3 test_channel_map test_case_store
  script() {   # config name, python, script: a script-style check, recorded by its exit code
    local name=$1 py=$2 file=$3 code=0
    echo "  $name: $file (script)"
    (cd "$SOLE/tests" && "$py" "$file" > "$rec/$name.log" 2>&1) || code=$?
    printf '{"%s": [["%s", "%s", "exit %s"]]}\n' "$file" "$file" "$([ $code = 0 ] && echo ok || echo FAIL)" "$code" \
      > "$rec/$name.json"
  }
  if "$KPY" -c "import pcbnew" 2>/dev/null; then
    script kicad_drc "$KPY" test_verify_drc.py
    if [ "$slow" = --slow ]; then
      script kicad_negative "$KPY" test_verify_negative.py
    else
      echo "  kicad_negative: not run (2-3 minutes per case; use tests --slow)"
    fi
  else
    echo "  kicad: skipped (no pcbnew in $KPY; install KiCad 7 or set KPY)"
  fi
  python3 -I - "$rec" <<'PY'
import collections, json, pathlib, sys
bad = 0
for f in sorted(pathlib.Path(sys.argv[1]).glob("*.json")):
    try:
        d = json.loads(f.read_text())
    except ValueError:
        print(f"{f.stem}: no result (see {f.with_suffix('.log')})"); bad += 1; continue
    for mod, rows in d.items():
        c = collections.Counter(r[1] for r in rows)
        why = sorted({r[2] for r in rows if r[1] == "skipped"})
        print(f"{f.stem:10s} {mod:28s} " + ", ".join(f"{k} {v}" for k, v in sorted(c.items()))
              + (f"  [skipped: {'; '.join(why)}]" if why else ""))
        bad += sum(v for k, v in c.items() if k in ("FAIL", "ERROR", "UNEXPECTED SUCCESS"))
print("all suites passed (skips listed above)" if not bad else f"{bad} failure(s): see the logs in {sys.argv[1]}")
sys.exit(1 if bad else 0)
PY
}

step_soles() {
  [ $# -gt 0 ] || die "give one or more spacings in mm, e.g. soles 3.75 2.5"
  say "EU 42 boards in $DATA/boards and soles in $DATA/soles"
  mkdir -p "$DATA/boards"
  local side board map sp
  for side in R L; do
    board="$DATA/boards/sole_EU42_$side.board.json"
    map=$(ls "$SOLE"/maps/EU42_"$side"_*.json)
    [ "$(echo "$map" | wc -l)" = 1 ] || die "expected one deployed EU 42 $side map, found: $map"
    if [ ! -f "$board" ]; then
      echo "  generating EU 42 $side (a few minutes)"
      (cd "$SOLE" && "$GEN_PY" sole_gen.py --size 42 --side "$side" --out "$DATA/boards" --name "sole_EU42_$side") \
        > "$DATA/boards/sole_EU42_$side.log" 2>&1 || die "generator failed (see $DATA/boards/sole_EU42_$side.log)"
    fi
    # the regenerated board must give the committed 15 mm sole byte for byte, or the spacings are not comparable
    (cd "$SOLE" && "$GEN_PY" sole_sim.py export "$board" --map "$map" -o "$DATA/soles/check15") > /dev/null
    cmp -s "$DATA/soles/check15/$(basename "${map%.json}").sole_sim.json" "$SOLE/sim/$(basename "${map%.json}").sole_sim.json" \
      || die "the regenerated EU 42 $side board does not reproduce sim/$(basename "${map%.json}").sole_sim.json"
    for sp in "$@"; do
      (cd "$SOLE" && "$GEN_PY" sole_sim.py export "$board" --map "$map" --spacing "$sp" -o "$DATA/soles/${sp}mm")
    done
  done
  rm -rf "$DATA/soles/check15"
  echo "run them with: SPACING_SOLES=\"$(for sp in "$@"; do printf '%s ' "$DATA/soles/${sp}mm"; done)\" workstation/run_comparison.sh"
}

checks
case "${1:-all}" in
  all) step_envs; step_inputs; step_machine; step_tests ;;
  envs) step_envs ;;
  inputs) step_inputs ;;
  machine) step_machine ;;
  tests) shift; step_tests "${1:-}" ;;
  soles) shift; step_soles "$@" ;;
  *) die "unknown step '$1' (all, envs, inputs, machine, tests [--slow], soles SPACING...)" ;;
esac
