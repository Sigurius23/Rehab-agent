<!-- SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors -->
<!-- SPDX-License-Identifier: CERN-OHL-S-2.0 -->

# Sensor sole: verification and risk summary

**2026-11-03, section 7 added 2026-11-04. Status: not released for fabrication.**

Sections 1–6 cover the eight boards generated from commit 99c7468 and checked with `verify_board.py`. Those
boards are kept unchanged in `archive/baseline-99c7468/`, and the IDs, hashes and map paths in sections 2–5
are theirs. Section 7 covers the boards now in `kicad/`, regenerated on 2026-11-04 after the generator fixes,
and compares them with the archived ones item by item. The geometry figures in section 5 still hold for the
regenerated baseline boards, because their copper is the same (section 7.2).

**What the checks establish:** the copper meets *our own* design rules, connects as intended, and carries a
traceable identity.

**What they do not establish:**
- that a fabricator can make it;
- how long it survives flexing;
- whether it fits the shoe;
- how accurately it senses pressure.

Those need the fabricator's written answers (FABRICATION.md) and physical tests (DESIGN.md, section 8).
Nothing has been ordered, made or sent to a fabricator.

## 1. Scope: what was checked, and what was not

| Configuration | Checked here | Notes |
|---|---|---|
| EU 37, EU 42, EU 46, default proportions, right and left | Yes, all pass | Default arch tail exit, region mode |
| Personal example, right and left (`person_example.json`) | Yes, both pass | **Synthetic**: illustrative landmarks, not a real person's foot. It tests that a 14-region, non-default foot routes and checks, **not** that the sole fits or works on any real foot |
| EU 36, 38–41, 43–45, 47 | **No** | Run the checks before using any of them |
| Measured length and width (`--length`, `--width`) | **No** | |
| Real scanned feet | **No** | |
| Heel tail exit, point mode | **No** | |
| Higher-resolution candidate T1 (`candidates/T1/`) | Separately, in `CANDIDATES.md` | A different design; not covered by this summary, its identity tests or its negative controls |

The router fixes of this session made all four checked configurations pass. Nothing in that says the untested
ones will.

## 2. Identity and channel maps

**The old ID was ambiguous.** It printed size or foot file, side and git revision. Shown with the old rule:

| Different inputs | Old printed ID |
|---|---|
| EU 42 defaults · EU 42 with a measured 265 × 101 mm foot · EU 42 with the tail exit at the heel | all `EU42 R g49ad079` |
| Two different uncommitted generator edits | both `EU42 R g49ad079+` |

On top of that, every export of the same design was a different file, because KiCad assigns random UUIDs.

**Now:**
- **Design hash.** It covers everything that defines the copper and the map: outline, regions, combs,
  routing, pin order, configuration, side and rules. It covers nothing about how or when the board was made.
  The printed ID is `<label> <side> <first 10 hex>`, e.g. `EU42 R 4ea1726398`. The label (`EU42`, `L265W101`,
  `F54cfa0`) is for people. The hash is what identifies the board.
- **Different designs get different IDs.** Same design gets the same ID, and the same map. A collision would
  need two designs whose 40-bit prefix matches. `manifest.py` and `channel_map.py check` reject duplicate IDs
  within one map set. That catches a collision only among the maps in that set (section "Remaining identity
  risks").
- **Seeded export.** KiCad's UUIDs are seeded from the design hash, so exports are byte-reproducible (section 3).
- **The checker binds the ID.** `verify_board.py` requires the printed ID to equal the design ID written on
  the board, which must match the hash in the title block.
- **Deployed maps.** For a passing board only, the checker writes a small package to `maps/`, separate from
  the development `.check.json`. It holds:
  - the ID, design hash and side;
  - the contact → region map;
  - the board's and project file's sha256 and the check result's sha256;
  - provenance (inputs, generator hashes, tool versions, rules, checker version);
  - a hash over its own content.
- **Resolving a sole** (`channel_map.py resolve "<printed ID>" --side L|R --maps maps/`) returns exactly one
  map, or refuses. It refuses:
  - an ID not of the required form;
  - no map, or more than one;
  - the wrong foot;
  - a package edited after verification;
  - a map that does not name each region exactly once with COM on the end contacts;
  - any unreadable file in the map set.
  Ten unit tests cover these and run in CI (`tests/test_channel_map.py`).

The boards checked in 99c7468 (now in `archive/baseline-99c7468/`, map packages in its `maps/`; the regenerated
boards and their IDs are in section 7):

| Board | Printed ID | Board file sha256 (first 12) | Map package |
|---|---|---|---|
| EU 37 R | `EU37 R 1ae8010c95` | `51a018de2116` | `maps/EU37_R_1ae8010c95.json` |
| EU 37 L | `EU37 L be318d6216` | `5c742d597730` | `maps/EU37_L_be318d6216.json` |
| EU 42 R | `EU42 R 4ea1726398` | `50ca340ed60e` | `maps/EU42_R_4ea1726398.json` |
| EU 42 L | `EU42 L 7d4eecd3c9` | `5f3730524062` | `maps/EU42_L_7d4eecd3c9.json` |
| EU 46 R | `EU46 R 4fb67c089d` | `1ebcc6b1bca2` | `maps/EU46_R_4fb67c089d.json` |
| EU 46 L | `EU46 L 55351e5576` | `8def0f28296f` | `maps/EU46_L_55351e5576.json` |
| Personal (synthetic) R | `F54cfa0 R 8a07f794d2` | `1d8c972f8aaa` | `maps/F54cfa0_R_8a07f794d2.json` |
| Personal (synthetic) L | `F54cfa0 L 1ad600b888` | `4ba35f496c3b` | `maps/F54cfa0_L_1ad600b888.json` |

**Remaining identity risks (open):**
- **Collisions outside a map set.** Rejecting duplicate IDs inside one map set does not rule out a collision
  with a design outside it: another branch, an older revision, or someone else's build of the generator. If
  such a sole were resolved against a set holding a different design with the same 10-hex prefix, it would get
  the wrong map. The risk is small (40 bits) but not excluded.
  - Mitigations, none built yet: resolve only against the set the sole was verified with; compare the full
    design hash when it can be read; use a longer printed ID; or give the sole an electrical ID the pod can
    read.
- **The physical label and the matching process are not validated.** Nothing has shown that a person reads
  the printed ID reliably, enters it correctly, or picks the right foot. Nor that the pod refuses in practice
  when they do not.
- **Legibility.** The ID is silkscreen text 1.0 mm high with 0.15 mm lines. That is exactly JLCPCB's published
  minimum for silkscreen, and it sits on a part that flexes. It may print or wear illegibly. Ask the
  fabricator, and test it.
- **Reading it.** Nothing yet reads the ID automatically. The pod or host must be told the ID and the side by a
  person, and refuses to label channels if they do not resolve.

## 3. Reproducibility and provenance

- **All eight boards are committed** (`kicad/*.kicad_pcb`, `*.kicad_pro`), each with its DRC report and check
  result. Previously six were only reproducible from the generator.
- **Each check result records** (`provenance`):
  - the input configuration (options, foot file and its sha256, sensors requested and built);
  - the generator-file hashes taken at the run's start, and the git revision;
  - the tool versions: Python 3.13.16, numpy 2.5.4, scipy 1.18.1, shapely 2.2.0, matplotlib 3.11.2,
    ezdxf 1.4.5, and KiCad 7.0.11 for export and check;
  - the project rules read from the `.kicad_pro`;
  - the sha256 of the board and project files;
  - the checker's own hash.
  `kicad/MANIFEST.json` (`manifest.py`) collects all eight. It confirms that every committed board file matches
  the sha256 its check result recorded, that IDs are unique, and that every passing board has a map.
- **Exact reproduction, tested.** In a clean worktree at 99c7468, with the tool versions above, the generator
  and exporter were run again:
  - **EU 37 R: byte-identical** board and project file;
  - **personal example L: byte-identical** board and project file.

  **Two of the eight boards** were regenerated as a spot check. **The other six have not been tested for exact
  reproduction.** They use the same code path, but that is an expectation, not a result.
  The file also records the git revision, so reproducing the exact file needs that revision. The design hash,
  and so the ID and map, depends only on the design.

## 4. Checker confidence

**Negative controls** (`tests/test_verify_negative.py`). Take the passing EU 42 R board, break it in one known
way, and require `verify_board.py` to fail for that reason. An unbroken copy must pass.

**One fresh run of all twelve cases** (2026-11-03), on:
- the test file as committed in 1d87666 (sha256 `05f35d8c3532d491…`);
- the checker `verify_board.py` (sha256 `3815d9024f5d10ce…`);
- the committed EU 42 R board `EU42 R 4ea1726398` (sha256 `50ca340ed60e9562…`).

Each check runs in its own process, as in real use. This run replaces the earlier partial results below.

| Fault injected | Result | The expected reason is among the reported problems (first one shown) |
|---|---|---|
| None (control) | passes | — |
| A track shorting contacts 2 and 3 | fails | yes; DRC: solder-mask bridge and clearance errors; copper trace: contacts joined |
| One region's via-to-comb stub removed | fails | yes; DRC: dangling via; copper trace: comb reached from no contact |
| One comb piece moved off its comb | fails | yes; DRC: 1 unconnected; copper trace: comb pieces not all connected |
| Configuration names a region that is not on the board | fails | yes; regions on the board differ from the configuration |
| Contact numbers 2 and 3 swapped | fails | yes; pad numbers do not follow the physical order |
| Net labels of contacts 2 and 3 swapped (the map would be wrong) | fails | yes; DRC: bridge and clearance errors; copper trace: contact's net reaches another region |
| One coverlay opening shrunk to 80 % | fails | yes; opening off its region; 39 % of the comb copper under coverlay |
| A track inside the copper-free margin | fails | yes; DRC: items not allowed (margin keep-out) |
| The printed ID altered by one digit | fails | yes; printed ID differs from the design ID |
| A generator hash in the title block altered | fails | yes; generator files changed since the board was made |
| The project rules file removed | fails | yes; design rules would be KiCad defaults |

Two of the controls first went wrong because of the test, not the checker:
- **The floating comb piece** was copied without KiCad 7's local-coordinate call, so it reloaded inside its own
  comb, and the board rightly passed.
- **KiCad's save** writes a project file of its own, so "rules file removed" still had its rules.
Both injections were fixed. Each was investigated, the injection and then the checker, before the result
was accepted, and the fresh run above repeats every case on the fixed test. An unexpected pass means either
the fault was not really injected or the checker missed it, so it stays open until one of the two is shown.
Here both were the injection.

**Other tests:**
- **Fail-closed DRC parsing** (`tests/test_verify_drc.py`, 8 cases): a failed report write, an empty report, a
  missing section, a count that differs from its header, a library warning for an unknown footprint, a missing
  one, or any other entry all fail.
- **Resolver** (`tests/test_channel_map.py`, 10 cases, in CI).

**Limits of the checker:**
- **The 2 % coverlay limit** is a design-check threshold. It is not a validated sensing or manufacturing
  tolerance. On the eight boards, at most 0.20 mm² (0.15 %) of any region's comb copper lies under coverlay.
- **It checks our rules, not the fabricator's process.** No annular-ring or drill rules from a real stack-up, no
  coverlay registration, no panelisation, no silkscreen legibility.
- **Single-fault controls.** The negative controls inject one fault at a time, into one board.

## 5. Geometry risks, quantified

Measured from each board's copper (shapely, edge to edge):

| Risk | EU 37 R/L | EU 42 R/L | EU 46 R/L | Personal R/L | Rule or target |
|---|---|---|---|---|---|
| Tightest via clearance to other-net copper | 0.189 mm (toe2 via to COM, F.Cu) | 0.200 mm (heel_med via to heel_post, B.Cu) | 0.190 mm (mid_lat_prox via to COM, F.Cu) | 0.212 mm (toe4 via to COM, F.Cu) | ≥ 0.15 mm (DRC) |
| Vias with no clear cell (planner fallback) | arch_med 0.212, heel_med 0.231 mm | heel_med 0.200, arch_med 0.265 mm | heel_med 0.213, arch_med 0.235 mm | none | Planner aims for about 0.65 mm |
| Longest via-to-comb stub (F.Cu) | 2.2 mm, clearance 0.26 mm | 2.8 mm, clearance 0.52 mm | 2.0 mm, clearance 0.75 mm | **8.7 mm** (mt3), clearance 0.19 mm | none in the bend zone on any board |
| Copper on both layers in the bend zone | 0 | 0 | **0.43 mm²**: the COM line crosses the B.Cu lines of mt1, mt2, mt3, toe1 and toe2 obliquely, each crossing about 1.4 mm long, 5.8–11.9 mm from the bend line | 0 | 0 wanted |
| Copper in the 2 mm edge margin | 0 | 0 | 0 | 0 | 0; now also a DRC keep-out |

**What these mean:**
- **Tight vias.** All are above the 0.15 mm rule, by 0.04–0.12 mm. The fallback vias are well below the
  planner's own 0.65 mm aim. Trace width tolerance (±20 % published, ±0.012 mm per edge on 0.12 mm lines) does
  not reach the rule. Coverlay and drill registration are for the fabricator.
- **The 8.7 mm stub.** It is a 0.12 mm F.Cu line under coverlay, 0.19 mm from the nearest other copper, outside
  the bend zone. Its resistance (about 0.07 Ω) is negligible against the sensor's. The risk is mechanical: a
  long thin line between regions, on a synthetic foot.
- **EU 46 crossings.** Five short crossings of F.Cu over B.Cu inside the toe-joint zone stiffen the flex locally.
  The planner does not yet avoid them. The bend test on the coupon should include such a crossing.

**Tail-root fillets** (5 mm radius, added this session against tearing and to give the trunk room to turn):

| Distance past the sole edge | 1 mm | 2 mm | 3 mm | 4 mm | 5 mm |
|---|---|---|---|---|---|
| Outline width across the tail (EU sizes; tail 12 mm) | 16.1 mm | 14.0 mm | 12.9 mm | 12.2 mm | 12.0 mm |
| Personal example (tail 11 mm) | 15.1 mm | 13.0 mm | 11.9 mm | 11.2 mm | 11.0 mm |

- The fillets add about 11 mm² of outline, the margin follows them, and no copper is in the margin on any board.
- **Fit risk.** The fillets sit where the tail leaves the sole at the medial arch and turns up the shoe's
  inside wall. A tail up to 4 mm wider for the first 2–3 mm bends stiffer and may wrinkle there. Only a fit test
  in the KSO Trek shows whether it matters; a paper or polyimide mock-up is enough.
- **Unchanged:** the outsole and the leather footbed. The sensor sole lies on top of the footbed.

## 6. What needs the fabricator, and what needs physical testing

**Fabricator** (draft questions in FABRICATION.md; not sent):
- Vias 0.45 / 0.20 mm: their extra-cost class; whether the 0.18 mm annular-ring limit applies to vias.
- Coverlay: registration tolerance and the 0.1 mm expansion against our 0.16 mm margin. Possibly blocking: with
  the expansion added, only 0.06 mm would remain.
- Rolled-annealed copper; finish on flexing combs (ENIG nickel is brittle).
- Stiffener and total thickness at the ZIF contacts (0.30 ± 0.03 mm); panelising left and right.
- Silkscreen on coverlay at 1.0 mm text (the ID).

**Physical tests** (DESIGN.md, section 8):
- **Coupon:** sensing linearity, hysteresis, creep and temperature drift per material. This also tests whether
  the geometric sensing-area estimate predicts real sensitivity.
- **Bend fatigue at the toe joint:** combs, an F.Cu-over-B.Cu crossing, a fallback-clearance via and a long
  stub.
- **Fit in the KSO Trek, EU 42:** toe tabs, the tail root with fillets, the collar crossing, and the tail
  length.
- **Force plates:** total force and centre of pressure. Left/right sync. Durability over cycles. Delamination
  at the stiffener. Legibility of the printed ID after wear.

## 7. Regenerated boards (2026-11-04)

### 7.1 What changed, and what did not

**The generator changed in commit 0257862** (`sole_gen.py`; `sole_route.py` unchanged):
- **`fracture()` fails closed.** It splits a comb with holes into hole-free KiCad pads. When no cut made
  progress, it used to recurse without end; on T1's mirrored synthetic foot it never returned. It now stops
  with `FractureError`.
- **Exported outlines stay valid at the board file's 0.1 µm precision.** Rounding a valid outline to that
  grid can make it invalid: a spike, two vertices on one point, or a keyhole slit whose two sides cross.
  - Only a piece that rounding makes invalid is rebuilt on the grid. Valid pieces are written as before.
  - Every exported set is compared with the unrounded copper. Any difference thicker than rounding and larger
    than 1e-4 mm² stops the export, as does a comb that falls into separate parts. A join at a single point
    does not count as connected.
  - Region outlines and coverlay openings must also be valid on the grid, or the export stops.
  - The board file records what was rebuilt (`source.export_rebuilt_outlines`) and any sliver dropped
    (`source.export_slivers_mm2`). No board dropped one.
  - There is no `buffer(0)` repair anywhere in the export.
- **Planarity-triggered re-route.** If the plan leaves sense lines that cross an odd number of times, the
  router re-routes only those regions, up to three rounds. Non-toe regions get deeper vias; toes switch to the
  other side of the tab base. A round is kept only if it reduces the odd crossings.

**Unchanged:**
- the checker `verify_board.py` (sha256 `3815d9024f5d…`), the exporter `kicad_export.py` and the resolver
  `channel_map.py`;
- the design rules (`.kicad_pro`), KiCad 7.0.11 and the Python tool versions of section 3.

**Regression tests** (`tests/test_generator_regressions.py`). Eight fast cases:
- the captured mirrored-foot comb splits;
- a cut that makes no progress falls back to the next one;
- no progress at all raises `FractureError`;
- a sub-grid slit is rebuilt;
- a larger difference fails closed;
- a sub-grid neck fails closed;
- a valid outline is written unchanged;
- the mirrored comb exports valid pads.

Three slow cases run with `SOLE_SLOW_TESTS=1`: the T1 EU 37 R plan is planar; T1 on the mirrored synthetic foot
exports; and the T1 EU 37 R fine pass is clean. The last one is marked as an expected failure until that
board passes (7.4).

### 7.2 All sixteen boards, checked again

Each board was generated, exported and checked with `verify_board.py` in its own run. The checks are:
- DRC with the project rules;
- the physical copper trace from every contact;
- contact numbering;
- coverlay openings;
- copper-free margin keep-outs;
- provenance (generator hashes at the run's start, git revision 0257862, tool versions, rules).

The source files matched on every board. Comparisons use `compare_boards.py` (old board against new). It
checks, item by item:
- the Edge.Cuts outline (area of the XOR);
- tracks and vias as multisets;
- comb copper per footprint and net (XOR area and pad count);
- coverlay openings;
- rule areas, including the margin keep-outs;
- J1's contacts;
- the configuration text and title block;
- the `.kicad_pro` rules;
- the deployed map's contact → region map, regions and side.

"Same geometry" means every XOR is below 1e-4 mm².

| Board | Archived ID → regenerated ID | Check | Compared with the archived board |
|---|---|---|---|
| EU 37 R | `EU37 R 1ae8010c95` → `EU37 R 990884049b` | passes | same geometry; 2 pad pieces and the margin rebuilt |
| EU 37 L | `EU37 L be318d6216` → `EU37 L 188e8665af` | passes | same geometry; 2 pad pieces and the margin rebuilt |
| EU 42 R | `EU42 R 4ea1726398` → `EU42 R 636645a928` | passes | same geometry; the margin rebuilt |
| EU 42 L | `EU42 L 7d4eecd3c9` → `EU42 L 40fe8e1d0c` | passes | same geometry; the margin rebuilt |
| EU 46 R | `EU46 R 4fb67c089d` → `EU46 R 0ce24d7591` | passes | same geometry; 3 pad pieces and the margin rebuilt |
| EU 46 L | `EU46 L 55351e5576` → `EU46 L 8c0b4df473` | passes | same geometry; 3 pad pieces and the margin rebuilt |
| Personal (synthetic) R | `F54cfa0 R 8a07f794d2` → `F54cfa0 R 6b6695e4db` | passes | same geometry; 1 pad piece and the margin rebuilt |
| Personal (synthetic) L | `F54cfa0 L 1ad600b888` → `F54cfa0 L 8ad4cd74ee` | passes | same geometry; 1 pad piece and the margin rebuilt |
| T1 EU 37 R | `T1-EU37 R 393cca5a99` → `T1-EU37 R e2034da2e5` | **fails** | routing changed (7.4) |
| T1 EU 37 L | `T1-EU37 L 21e1be9450` → `T1-EU37 L 7b5c8400b6` | **fails** | routing changed (7.4) |
| T1 EU 42 R | `T1-EU42 R 8bf33cb25b` → `T1-EU42 R 54183ab293` | passes | same geometry; 1 pad piece and the margin rebuilt |
| T1 EU 42 L | `T1-EU42 L 4372223cc1` → `T1-EU42 L 1139ebcea9` | passes | same geometry; 1 pad piece and the margin rebuilt |
| T1 EU 46 R | `T1-EU46 R 4d6f6e20bd` → `T1-EU46 R 0874227edb` | passes | same geometry; 4 pad pieces and the margin rebuilt |
| T1 EU 46 L | `T1-EU46 L f5bfbc77d2` → `T1-EU46 L a01d3f4fa7` | passes | same geometry; 4 pad pieces and the margin rebuilt |
| T1 synthetic R | `T1-F54cfa0 R e9634e6328` → `T1-F54cfa0 R d049ca37a1` | passes | mt2 COM comb: 0.00029 mm² less, 0.00008 mm² more; 8 → 12 pads (7.3) |
| T1 synthetic L | `T1-F54cfa0 L 0bb63af7f4` → `T1-F54cfa0 L a628dcb9a3` | passes | the same as R, mirrored |

**What is the same on all 14 passing boards:**
- the outline (XOR 0);
- every track and via (identical multisets);
- every rule area, including the margin keep-out;
- the coverlay openings;
- J1's contacts;
- the project rules;
- the map: contact → region, regions and side.

The configuration text differs only in `board_id` and `design_hash`, and the title block only in the two
comments that carry them. The most comb copper under coverlay in any one region is 0.18–0.20 mm². On the eight
baseline boards it is 0.19–0.20 mm², against at most 0.20 mm² before (section 4).

**Why every ID changed, though on 12 of the 14 passing boards the copper did not.** The design hash covers the
exported coordinate lists.
- **Margin keep-out.** On every board, the copper-free margin outline became invalid once rounded. It touches
  itself at a point on 6 boards, for example at (119.4588, −39.5504) on EU 42 R, and crosses itself on 10. It
  is now written as a valid ring, for example 3196 → 3191 vertices on EU 42 R. KiCad's reading of the keep-out
  area is the same as before on every board (XOR 0).
- **Pad pieces.** A few pieces with self-touching or crossing rings (7.3) were rebuilt.

New vertex lists give a new hash, and so a new ID. On 12 of the 14 passing boards the copper differs by less
than 1e-4 mm². The two T1 synthetic-foot boards (R and L) exceed that threshold in mt2's COM comb (7.3). This
is why the comparison above is item by item, not by bytes or IDs.

**Maps and the manifest.**
- Maps were written for the 14 passing boards: 8 in `maps/` and 6 in `candidates/T1/maps/`.
- `kicad/MANIFEST.json` was rewritten: all 8 baseline boards pass, IDs are unique, every board file matches
  its check result, and every passing board has a map.
- `channel_map.py` refuses the archived IDs against the current `maps/`. For example, `EU42 R 4ea1726398`
  gets "no verified map". Those IDs resolve only from the archive folders.

### 7.3 Self-touching and crossing pad outlines

**What the archived boards had.** Their board files held pad pieces whose rounded outline was not a valid
polygon:

| | EU 37 | EU 42 | EU 46 | Personal | T1 EU 37 | T1 EU 42 | T1 EU 46 | T1 synthetic |
|---|---|---|---|---|---|---|---|---|
| Pieces per board (R and L alike) | 2 | 0 | 3 | 1 | 7 | 1 | 4 | 1 |
| Kind | touch at a point | — | touch at a point | touch at a point | 4 touch, 3 cross | touch at a point | touch at a point | **crosses itself** |

Each one was checked before deciding what to change; none was repaired with `buffer(0)`:
- **No piece splits into separate lobes.** Read as `make_valid`, none falls apart, so no copper hung on a
  zero-width point.
- **KiCad built the copper intended.** It matches `make_valid` within 0.00033 mm² per piece, except T1 EU 46,
  at 0.005 mm². That difference lies under other pieces of the same comb, so the comb's copper is unchanged.
- **The crossing piece.** On the T1 synthetic foot, mt2's COM comb piece (230.69 mm²) has keyhole slits whose
  sides cross once rounded. `make_valid` reads it as one polygon with four holes. KiCad's copper has the same
  area, 230.6919 mm², and leaves the same places bare.
- **What the archived checks rested on.** Their DRC and copper trace passed on these boards. The trace counts
  a single-point touch as a connection (below), so it does not tell a self-touch from a real join.

**What the regenerated boards have.** No invalid pad outline remains on any of the 16 boards; each was
rebuilt as described in 7.1. On 12 of the 14 passing boards, the comb copper is unchanged within 1e-4 mm².

**The T1 synthetic foot, on both sides, is the exception.** Its crossing piece became 5 valid pieces, so the comb has 12 pads
instead of 8. Against the `make_valid` reading of the old piece:
- 0.00029 mm² went;
- 0.00008 mm² came;
- the comb is still one connected shape;
- the board passes with the same contacts and map.

**Checker limit, still open.** The copper trace joins two shapes when KiCad's `Collide(…, 0)` reports a
touch, and that includes a touch at a single point. A comb whose pieces met only at a point would be
reported as connected, though it would not be one piece of copper. The exporter now refuses such joins, so
the regenerated boards cannot contain one, but the checker would not catch one on its own. A negative
control for it, and a minimum-overlap rule in the trace, are not built yet.

### 7.4 T1 EU 37: changed, still failing

| | Archived (5dd52ff) | Regenerated (0257862) |
|---|---|---|
| Lines crossing an odd number of times in the plan | 6 pairs; one jumper (toe4 / mt3) | **0**; no jumper. One re-route round: deeper vias for ffp_cen and mt4; toe3–toe5 on the other side of the tab base |
| Fine pass did not finish | ffp_med, mt3, toe1_tip, toe4 | mt3, mt4 |
| Vias | 24 | 22 |
| DRC clearance errors (rule 0.15 mm) | 3: S_ffp_med to S_toe1_tip on B.Cu, 0.0073 mm apart | 3: S_mt3 to S_mt4 on B.Cu at the forefoot, 0.1346 mm apart |
| Common net | reaches every region | **does not reach heel_pl**: KiCad reports 1 unconnected item between the COM pads of S02 and S04; the copper trace finds heel_pl's COM comb reached from no contact |
| Map | none | none |

**Assessment.**
- The fix removed the conflict it was aimed at: the odd crossings and the near-short between ffp_med and
  toe1_tip.
- It did not make the board pass. The mt3 and mt4 lines are squeezed 0.015 mm under the rule at one spot.
  The new via layout leaves heel_pl's common comb cut off.
- Running the fine pass with 16 or 32 negotiation rounds did not clear the squeeze.
- Moving T1's anchors at EU 37 would be a design decision, and it was not taken. Nor were the rules relaxed.

Both sides fail the same way, mirrored. They stay without a map, and the slow regression test stays an
expected failure.

### 7.5 Not done in this round

- **Exact reproduction** of the regenerated boards in a clean worktree. Section 3's spot check was for 99c7468.
- **Negative controls on a regenerated board.** The checker is unchanged, and the controls were run on the
  archived EU 42 R (section 4).
- **Fabrication.** Nothing was sent to a fabricator, ordered or made. None of these boards is released for
  fabrication.
