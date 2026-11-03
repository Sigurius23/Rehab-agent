#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors
# SPDX-License-Identifier: CERN-OHL-S-2.0
"""verify_board.run_drc must fail closed: every broken or unexpected DRC report is a failure.

Run with the Python that ships KiCad's pcbnew:  python3 tests/test_verify_drc.py
(KiCad's report writer is replaced by a stub that writes each test report.)
"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pcbnew  # noqa: E402
import verify_board as V  # noqa: E402

LIB = ("[lib_footprint_issues]: The current configuration does not include the library 'sensor_sole'.\n"
       "    Local override; Severity: warning\n    @(1.0 mm, 1.0 mm): Footprint {ref}\n")


def report(n_found, entries, unconnected=0, fp_errors=0, sections=("v", "u", "f", "e")):
    parts = ["** Drc report for x.kicad_pcb **", "** Created on 2026-11-03 **", ""]
    if "v" in sections:
        parts += [f"** Found {n_found} DRC violations **", "".join(entries)]
    if "u" in sections:
        parts += [f"** Found {unconnected} unconnected pads **", ""]
    if "f" in sections:
        parts += [f"** Found {fp_errors} Footprint errors **", ""]
    if "e" in sections:
        parts += ["** End of Report **"]
    return "\n".join(parts) + "\n"


GOOD = report(2, [LIB.format(ref="S01"), LIB.format(ref="J1")])
CASES = {
    "clean": (True, GOOD, True),
    "writer reports failure": (False, GOOD, False),
    "empty report": (True, "", False),
    "missing section": (True, report(2, [LIB.format(ref="S01"), LIB.format(ref="J1")], sections=("v", "u", "e")), False),
    "header count differs": (True, report(3, [LIB.format(ref="S01"), LIB.format(ref="J1")]), False),
    "warning for an unknown footprint": (True, report(2, [LIB.format(ref="S01"), LIB.format(ref="X9")]), False),
    "warning missing for a footprint": (True, report(1, [LIB.format(ref="S01")]), False),
    "any other entry": (True, report(3, [LIB.format(ref="S01"), LIB.format(ref="J1"),
                                         "[clearance]: Clearance violation\n    Rule: x; Severity: error\n"
                                         "    @(1 mm, 1 mm): Track\n"]), False),
}


def main():
    failures = 0
    with tempfile.TemporaryDirectory() as d:
        pcb = Path(d) / "x.kicad_pcb"
        for name, (ret, text, should_pass) in CASES.items():
            def fake(board, path, units, all_errors, _t=text, _r=ret):
                if _t:
                    Path(path).write_text(_t)
                return _r
            pcbnew.WriteDRCReport = fake
            _, problems = V.run_drc(None, pcb, ["S01", "J1"])
            ok = (not problems) == should_pass
            failures += not ok
            print(f"{'ok  ' if ok else 'FAIL'} {name}: {'passes' if not problems else problems[0]}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
