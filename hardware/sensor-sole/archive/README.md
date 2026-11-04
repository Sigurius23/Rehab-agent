<!-- SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors -->
<!-- SPDX-License-Identifier: CERN-OHL-S-2.0 -->

# Archived board sets, kept for comparison

These are earlier verified sets, moved here unchanged with `git mv`. Every file is byte-identical to the file
as committed, and its history follows the move. **None of them is released for fabrication.**

| Folder | What | Made from | Checked |
|---|---|---|---|
| `baseline-99c7468/` | The 16-region baseline: EU 37, 42, 46 and the synthetic foot, right and left (8 boards), with project rules, DRC reports, check results, deployed maps and `MANIFEST.json` | Generator at commit 99c7468 | All 8 passed `verify_board.py` at the time |
| `T1-5dd52ff/` | Candidate T1: the same 8 configurations | Generator at commit 5dd52ff, with the candidate's own guard on `fracture()` | 6 passed; EU 37 failed on both sides (3 clearance errors each) and has no map |

**Why they were replaced.** The shared generator was changed:
- `fracture()` now fails closed;
- exported outlines must stay valid at the board file's 0.1 µm precision;
- the router re-routes the few lines whose vias break the plan's planarity.

The current boards in `kicad/`, `maps/`, `candidates/T1/kicad/` and `candidates/T1/maps/` were regenerated
with it. `VERIFICATION.md`, section 7, compares them with these sets item by item, using
`compare_boards.py`.

**Checking these files again.** `verify_board.py` now reports "generator files changed since this board was
made" for them. That is expected: they record the generator that made them, and that generator has since
changed. Their `.check.json` files are the record of the checks run when they were current. Their deployed
maps resolve only from these folders; the current `maps/` refuses their IDs unless a regenerated board has
the same design hash.
