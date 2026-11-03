#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors
# SPDX-License-Identifier: CERN-OHL-S-2.0
"""One manifest for the committed boards: identity, file hashes, inputs, run-start generator hashes, tool
versions, project rules and the checker that passed each board, from the check results and deployed maps.
Plain Python. Usage: python3 manifest.py   (writes kicad/MANIFEST.json and prints a summary)
"""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    boards = []
    maps = {json.loads(p.read_text())["board_id"]: p for p in sorted((HERE / "maps").glob("*.json"))}
    for chk in sorted((HERE / "kicad").glob("*.check.json")):
        r = json.loads(chk.read_text())
        pcb = chk.with_name(r["board"])
        pv = r.get("provenance", {})
        mp = maps.get(pv.get("board_id"))
        entry = dict(
            board=r["board"], board_id=pv.get("board_id"), design_hash=pv.get("design_hash"),
            passed=r["ok"], problems=r["problems"],
            files=dict(kicad_pcb=sha(pcb) if pcb.exists() else None, kicad_pro=r.get("project_sha256"),
                       check_json=sha(chk), map=mp.name if mp else None, map_sha256=sha(mp) if mp else None),
            board_sha256_matches_check=(sha(pcb) == r["sha256"]) if pcb.exists() else False,
            inputs=pv.get("inputs"), generator_files_at_run_start=pv.get("generator_files_at_run_start"),
            tools=pv.get("tools"), project_rules=pv.get("project_rules"), checker=pv.get("checker"),
            synthetic_foot=("person_example" in r["board"]))
        boards.append(entry)
    ids = [b["board_id"] for b in boards]
    out = dict(note="Boards that pass verify_board.py. Not released for fabrication (FABRICATION.md).",
               all_passed=all(b["passed"] for b in boards), ids_unique=len(set(ids)) == len(ids),
               board_files_match_their_checks=all(b["board_sha256_matches_check"] for b in boards),
               every_passing_board_has_a_map=all(b["files"]["map"] for b in boards if b["passed"]),
               boards=boards)
    (HERE / "kicad" / "MANIFEST.json").write_text(json.dumps(out, indent=1) + "\n")
    for b in boards:
        print(f"{b['board_id']:22s} {b['files']['kicad_pcb'][:12]}  passed={b['passed']}  map={b['files']['map']}"
              f"{'  (synthetic foot)' if b['synthetic_foot'] else ''}")
    print({k: v for k, v in out.items() if k != "boards" and k != "note"})


if __name__ == "__main__":
    main()
