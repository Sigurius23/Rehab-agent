#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors
# SPDX-License-Identifier: CERN-OHL-S-2.0
#
# Sole -> KiCad board -> fabrication files (Gerbers, drill, zip), for one foot.
#   ./make_fab.sh 42 R                       # EU size and side
#   FOOT=person.json NAME=sole_anna_R ./make_fab.sh 42 R   # a person's landmarks instead of the size defaults
# Fabrication files are written only if verify_board.py passes (DRC with the project rules, the
# region-to-contact map traced through the copper, contact numbering, provenance). Passing that is not a
# release: see FABRICATION.md for what the fabricator still has to confirm.
# Needs: the generator's Python packages (requirements.txt) for PY, and KiCad 7+ (pcbnew, kicad-cli).
set -euo pipefail
SIZE=${1:-42}; SIDE=${2:-R}
PY=${PY:-python3}                 # Python with numpy, scipy, shapely, matplotlib, ezdxf
KPY=${KPY:-python3}               # Python that imports pcbnew (KiCad's)
cd "$(dirname "$0")"
STEM="${NAME:-sole_EU${SIZE}_${SIDE}}"
ARGS=(--size "$SIZE" --side "$SIDE" --out out --name "$STEM")
[ -n "${FOOT:-}" ] && ARGS+=(--foot "$FOOT")
"$PY" sole_gen.py "${ARGS[@]}"
mkdir -p kicad fab
"$KPY" kicad_export.py "out/${STEM}.board.json" "kicad/${STEM}.kicad_pcb"
if ! "$KPY" verify_board.py "kicad/${STEM}.kicad_pcb"; then
  echo "verification failed (kicad/${STEM}.check.json): no fabrication files written" >&2
  exit 1
fi
rm -rf "fab/${STEM}"; mkdir -p "fab/${STEM}"
kicad-cli pcb export gerbers -o "fab/${STEM}/" -l F.Cu,B.Cu,F.Mask,B.Mask,Edge.Cuts,F.Fab "kicad/${STEM}.kicad_pcb"
kicad-cli pcb export drill -o "fab/${STEM}/" "kicad/${STEM}.kicad_pcb"
(cd fab && rm -f "${STEM}.zip" && zip -qr "${STEM}.zip" "${STEM}")
echo "fabrication files: fab/${STEM}.zip  (2-layer polyimide flex, see kicad/${STEM}.kicad_pcb F.Fab notes)"
