<!-- SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors -->
<!-- SPDX-License-Identifier: CERN-OHL-S-2.0 -->

# Sensor sole: verification and risk summary

**2026-11-03. Status: not released for fabrication.**

This summary covers the eight boards in `kicad/`, generated from commit 99c7468 and checked with
`verify_board.py`.

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
  in a map set, so a collision would be caught, not silently accepted.
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

**Remaining identity risks:**
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

  These two were regenerated as a spot check. The other six were not, but use the same code path.
  The file also records the git revision, so reproducing the exact file needs that revision. The design hash,
  and so the ID and map, depends only on the design.

## 4. Checker confidence

**Negative controls** (`tests/test_verify_negative.py`). Take the passing EU 42 R board, break it in one known
way, and require `verify_board.py` to fail for that reason. An unbroken copy must pass.

Run on the committed EU 42 R board (`EU42 R 4ea1726398`). Each check runs in its own process, as in real use.

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
Both injections were fixed and the cases rerun. A control that passes only shows the fault was not really
injected; each one is now confirmed to fail.

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
