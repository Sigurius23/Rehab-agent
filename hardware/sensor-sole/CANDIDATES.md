<!-- SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors -->
<!-- SPDX-License-Identifier: CERN-OHL-S-2.0 -->

# Sensor sole: higher-resolution candidates

**2026-11-03. Design and analysis only.**
- **Not released for fabrication.**
- **Untested:** sensing, fit in the shoe and durability, until physical evidence exists.
- **Nothing has been** fabricated, fitted, measured, bought or sent to a fabricator.
- **The shoe is unchanged:** the outsole and the leather footbed stay in place, and the sole lies on the
  footbed.

## 1. What is compared

| | Baseline | Candidate T1 (targeted) | Matrix |
|---|---|---|---|
| What it is | 16 regions, one sense line each | The same method with more regions where they add information: 20 at EU 42 | Rows and columns crossing at cells, one line per row and per column |
| Status | Generated, routed, checked: 8 boards pass `verify_board.py` | Generated, routed and checked with the same rules and checker: 6 of 8 boards pass; EU 37 fails on both sides | **Geometry study only**: not routed, not checked. One assumed architecture (section 3), not the only possible matrix |
| Files | `out/`, `kicad/`, `maps/` | `candidates/T1/` | `candidates/study.py`, results in `candidates/study.json` |

**Both designs are kept for a fair comparison.**
- **One generator for both.** `sole_candidate.py` makes the candidate from `candidates/T1/layout.json` with the
  shared `sole_gen.py`, `sole_route.py`, `kicad_export.py` and `verify_board.py`. It has no generator code of its
  own.
- **The shared generator was fixed on 2026-11-04** (commit 0257862; VERIFICATION.md, section 7):
  - `fracture()` fails closed;
  - exported outlines stay valid on the board file's grid;
  - lines whose vias break the plan's planarity are re-routed.
  Both designs were regenerated with it and checked again. The baseline's copper, outlines, rules and maps are
  unchanged, but its IDs are new, because rebuilt outlines change the design hash.
- **The earlier sets are kept unchanged**, for comparison: the baseline in `archive/baseline-99c7468/` and T1
  in `archive/T1-5dd52ff/`.
- **Candidate soles cannot be mistaken for baseline ones.**
  - Their IDs carry the layout name, for example `T1-EU42 R 54183ab293`.
  - Their deployed maps live in `candidates/T1/maps/`.
  - Their title blocks also record the candidate script and layout file hashes. `verify_board.py` checks
    only the three shared generator files (see section 7).

## 2. Candidate T1: a targeted layout

| Zone | Baseline | T1 | What the extra regions are for |
|---|---|---|---|
| Heel | 3: posterior, medial, lateral | 4: 2 × 2 | Front–back and inner–outer loading at heel strike |
| Midfoot | 3: medial arch, lateral proximal, lateral distal | 3, unchanged | Kept for coverage; no regions forced where they would compromise fit |
| Forefoot | 5 metatarsal heads | 5 heads, plus 2 regions behind them (under metatarsals 1–2 and 3–4) | Front–back detail around the heads |
| Big toe | 1 | 2: base and tip | Where the big toe takes load at push-off |
| Lesser toes | 4 | 4, unchanged | One region each; their tabs have no room for more |

- **Why not more.**
  - A third region behind the heads, under metatarsals 4–5, would sit almost on the lateral midfoot
    region's anchor (7.6 mm apart at EU 42), so it was left out.
  - A row under the toe bases would sit in the toe-joint bend band, where no via may go.
- **A person's choices carry over.** Each T1 region names the baseline regions it comes from. The synthetic
  foot switches off the medial arch and the fifth toe, so its T1 sole has 18 regions.

### Results, with the same rules and the same checker as the baseline

Generated from commit 0257862, the fixed shared generator. Left and right are mirrors and give the same
results. The 5dd52ff boards are in `archive/T1-5dd52ff/`.

| Configuration | Regions | Contacts; tail | Fine routing pass | `verify_board.py` | Weakest region (sensing area as a share of its tile) | Copper on both layers in the bend band | Most comb copper under coverlay, any region |
|---|---|---|---|---|---|---|---|
| EU 37, R and L | 20 | 22; 14 mm | 2 lines left in conflict (mt3, mt4); no jumper; the plan is now planar | **Fail**. 3 clearance errors at one spot, S_mt3 to S_mt4, 0.135 mm against the 0.15 mm rule. The common net does not reach heel_pl (1 unconnected). No map written | mt1, 47 % | 0.74 mm² | 0.18 mm² |
| EU 42, R and L | 20 | 22; 14 mm | Clean | Pass | toe1_base, 58 % | 0 | 0.19 mm² |
| EU 46, R and L | 20 | 22; 14 mm | Clean | Pass | mt4, 54 % | 0 | 0.20 mm² |
| Synthetic foot, R and L | 18 | 20; 13 mm | Clean | Pass | ffp_med, 46 % | 0.83 mm² | 0.20 mm² |
| *Baseline, same configurations* | *16 (14)* | *18; 12 mm (16; 11 mm)* | *Clean* | *8 of 8 pass* | *mt4 69 % (EU 37, 42), mt4 58 % (EU 46), mt1 73 % (synthetic)* | *0, except EU 46: 0.43 mm²* | *0.20 mm² worst* |

- **Unchanged by the regeneration:** the copper of the EU 42 and EU 46 boards. The synthetic foot's boards
  differ only in one comb, mt2's COM, by under 0.0003 mm² (VERIFICATION.md, section 7.3).
- **The last column now gives the checker's figure.** It is the largest `covered_mm2` over the regions in
  `.check.json`. The earlier table gave 0.13–0.18 mm², and its source could not be traced. The checker
  reports 0.19–0.20 mm² on the archived 5dd52ff boards too.

- **The cost of more regions.** Smaller regions lose a larger share to the bundles that pass them. On the
  passing T1 boards the weakest region keeps 46–58 % of its tile; on the baseline, 58–73 %.
  - The big-toe base loses most at EU 42, because the tip's line runs along it.
  - The share that senses is a geometric estimate; how a part-covered region responds is for the coupon test.
- **Copper on both layers in the bend band.** T1 removes EU 46's 0.43 mm² but adds 0.83 mm² on the synthetic
  foot. Either way it is a durability question for the bend test.
- **Why EU 37 failed at 5dd52ff.**
  - Six pairs of sense lines crossed an odd number of times in the plan, so one needed a jumper.
  - ffp_med's via sat at the far corner of its region, and its line ran back beside the big-toe bundle.
  - The fine pass could not separate it from toe1_tip's line: 0.007 mm apart.
- **What the router fix changed** (commit 0257862). When the plan is not planar, the router now re-routes the
  regions involved. On EU 37 one round did it:
  - deeper vias for ffp_cen and mt4;
  - toe3–toe5 leave from the other side of their tab base.
  The plan became planar, with no jumper, and the ffp_med / toe1_tip conflict is gone.
- **Why EU 37 still fails.**
  - **mt3 and mt4.** Their lines are now squeezed together at the forefoot, 0.135 mm apart against 0.15 mm.
    The fine pass leaves them there with 8 negotiation rounds, and also with 16 or 32.
  - **heel_pl.** The new via layout cuts its common comb off from contact 1.
  - **Copper in the bend band** rose from 0.31 to 0.74 mm².
  - **Not tuned away.** T1's anchors were not moved at EU 37 alone, and no rule was relaxed. Both would be
    design decisions.
  - **The regression test** for the clean fine pass stays an expected failure until the board passes
    (`tests/test_generator_regressions.py`, slow cases).
- **The splitting bug is fixed in the shared generator.** `fracture()`, which splits a comb into hole-free
  KiCad pads, recursed forever on the mirrored synthetic foot with T1's regions.
  - It now fails closed: a split that makes no progress tries the next cut, and stops with an error if none
    works.
  - `sole_candidate.py` no longer carries its own guard.
  - A regression test uses the captured comb (`tests/fixtures/t1_mirrored_comb.wkt`).
- **Self-touching and crossing pad outlines: resolved.** After rounding, some comb pieces touched themselves
  at a point, or crossed themselves: 0–3 per baseline board and 1–7 per T1 board.
  - On the archived boards, KiCad's copper matched what was intended, and no copper hung on a single point.
  - The export now rebuilds such pieces on the grid, and checks that the copper and its connectivity are
    unchanged.
  - No invalid outline remains on any regenerated board. Details are in VERIFICATION.md, section 7.3.
- **IDs and maps.** All 8 T1 IDs differ from each other and from the baseline's.
  - `channel_map.py` resolves the 6 passing ones from `candidates/T1/maps/`.
  - It refuses every T1 ID against the baseline's `maps/`.
  - The two failing EU 37 boards have no map anywhere.

## 3. Targeted layout against a dense matrix

EU 42, right foot, unless stated. The baseline and T1 figures come from routed boards that the checker
passed. The matrix figures are first-order geometry: a grid laid over the same outline, not routed (the
assumptions are in `candidates/study.py`). Ranges across EU 37, 42, 46 and the synthetic foot are in
`candidates/study.json`. The figure `candidates/compare_EU42.png` shows the three side by side.

| | Baseline | T1 (targeted) | Matrix, 7.5 mm pitch | Matrix, 10 mm pitch |
|---|---|---|---|---|
| Sensing elements | 16 regions | 20 regions | 341 cells | 188 cells |
| … heel / midfoot / forefoot / toes | 3 / 3 / 5 / 5 | 4 / 3 / 7 / 6 | 79 / 97 / 107 / 58 | 42 / 53 / 64 / 29 |
| Share of the sole that senses (outlines; geometric) | 74 % | 73 % | 64 %, before the edge channels below take their share | 68 %, the same caveat |
| **Spatial information** (geometric estimate, not measured): RMS localisation error from knowing only which element is loaded (median; heel / midfoot / forefoot / toes) | 16.5 / 17.1 / 16.8 / 11.0 mm | 12.8 / 16.7 / 13.0 / 9.5 mm | 2.5 mm everywhere | 3.6 mm everywhere |
| Elements across the forefoot | 5 | 5, plus 2 behind them | about 13 | about 10 |
| **Toe-pocket fit:** the outline, the tabs and the 2 mm slits with 1.0 mm round ends | Same | Same | Same | Same |
| … copper lines inside the toe tabs | 138 mm | 205 mm (the big-toe tip's line runs along its tab) | about 1,560 mm | about 1,110 mm |
| … vias inside the toe tabs | 5 | 6 | about 87 | about 50 |
| … layers crossing inside the tabs | No: one comb pair per toe, lines leave at the base | The same; one more line runs along the big-toe tab | Yes, at every toe cell: stiffer tabs | The same |
| **Tail:** contacts at 0.5 mm, and width | 18; 12 mm | 22; 14 mm | 72 (48 if the toe pieces are linked behind the slits); 39 mm (27 mm) | 56 (37); 31 mm (21.5 mm) |
| **Routing** | Routed; 8 of 8 boards pass | Routed; 6 of 8 boards pass. EU 37 fails: 3 clearance errors at one spot, and the common net misses one region | Not routed. A line crossing the foot is cut by every toe slit, so each toe's piece needs its own line out of the tab, on the other layer, with one extra via: 29 pieces | 21 pieces |
| … vias in the toe-joint bend band, where the baseline rules allow none | 0 | 0 | 43: one per cell there, unless those cells are dropped | 24 |
| … edge channels beside the tail, distal / proximal side | Carved per bundle; checked | The same | about 17 / 12 mm wide, eating into the cells there | about 12.5 / 9 mm |
| **Readout:** conversions per second per foot at 100 Hz | 1,600 | 2,000 | 34,100 | 18,800 |
| … hardware | One 16:1 multiplexer, one transimpedance amplifier; 10 of the XIAO's 11 pins | Two 16:1 multiplexers and two amplifiers, or one 32:1 multiplexer; all 11 pins | Drivers for 35–59 lines and sense for 13. Suppressing sneak paths means holding every unselected line at the sense potential: a driver or switch per line, not one multiplexer chain. Beyond the XIAO's pins without expanders | The same, smaller |
| … sneak paths through other sensors | None by construction | None by construction | Yes: suppressed or compensated (smartinsole's 2026 paper) | Yes |
| **Calibration:** curves per sole | 16 | 20 | 341, or a shared model with a gain per cell | 188 |

**What each could give the twin.** None of this has been measured. Each column says what the geometry allows,
not what the sole would deliver. The localisation figures above are geometric estimates (where an element's
centre is), not measured localisation accuracy.
- **Baseline:** one load signal per anatomical segment (heel, midfoot, each metatarsal head, each toe), with
  total force and centre of pressure estimated from 16 regions.
- **T1 adds** the following, still with one aggregate signal per region, so a peak cannot be located inside a
  region:
  - front–back and inner–outer loading at the heel;
  - load under the metatarsal shafts against the heads;
  - the big toe's tip against its base.
- **A matrix** samples a pressure map every 7.5–10 mm. That gives where a peak is, how large the contact area
  is, and pressure gradients, so the twin could use a distribution rather than segment totals. The cost is
  hundreds of cells to calibrate, sneak paths to suppress, and coverage lost to the channels.

**Decided 2026-11-04: T1 is carried forward as a candidate, not a final selection, and the matrix stays open.**
T1 adds information where the comparison suggested it (DESIGN.md, section 9.1) without changing what the sole
asks of the shoe:

- the same outline and tabs;
- 2 mm more tail;
- no vias in the bend band;
- the same one-channel-per-region readout.

The matrix figures come from **one assumed architecture**: a two-layer flex, one via per cell, crossing lines cut
by the toe slits. They are not evidence that matrix approaches are impractical in general. With that
architecture, against the current design rules, a matrix would need:

- vias in the bend band;
- copper crossing inside the toe tabs;
- a tail about three times as wide at the collar;
- a different readout.

Each of those is a fit, durability or electronics question the baseline avoided. Other matrix architectures
could answer some of them: a sub-array per toe, more layers, through-mode cells between two printed or flex
layers (no via per cell), or a printed matrix. They are not studied here and stay open.

## 4. A broken sense line: can it be detected?

With the readout proposed in DESIGN.md (section 6), the common comb is driven and each sense line goes, through
the multiplexer, to a transimpedance amplifier. At zero load the film barely conducts. An unloaded region and a
region whose line is broken may then both read about zero. They do not have to stay indistinguishable,
though: diagnostics can be added. The options, with estimates from the routed copper (`candidates/open_line.py`;
nothing measured):

| Option | What changes | What it would detect | Cost and open questions |
|---|---|---|---|
| **Capacitive self-test** | Readout only: step the common net's drive and integrate the charge that flows into the selected line (an analog switch on the drive, a feedback capacitor and a reset switch on the amplifier) | A break in the sense line, its via or stub, or the connector; a comb that came off; partly a cut spine (part of the fingers lost) | Promising on estimates below the table; not measured. Needs zero load (before the shoe goes on, or in swing), and a reference record per channel and per sole, because the multiplexer, connector and cable add capacitance of their own. The film's permittivity, humidity and temperature shift the reading. Not tested |
| **Loop-back lines** | Sole and pod: each sense comb joined to the tail by two lines, through its spine; continuity between the two contacts | Any break along the loop, including the spine; not a broken finger | Doubles the sense lines: 34 contacts for the baseline (tail about 20 mm), 42 for T1 at EU 42 (about 24 mm). More bundle width to carve out of the regions |
| **Reference conductance** | Sole: a printed resistor across each comb, or a film with a stable conductance at zero load | An intact channel reads a known small value; an open line reads zero | Needs a printed-resistor process or a suitable film (coupon test). Adds an offset and its drift to every reading |
| **Common-net continuity** | Pod only: the first and last contacts both carry the common net | That the connector is seated at both ends | Does not test the sense lines (DESIGN.md, section 9.3) |
| **Test structures on the panel** | Fabrication: comb and via-chain coupons beside the soles, measured on receipt | Process defects in that batch | Not breaks that happen in use |
| **Plausibility in the data** | Firmware: a channel flat at zero while its neighbours load | Suspicion only | Cannot confirm a break; an unloaded region looks the same |

**Capacitive self-test: estimates from the routed copper, not measured performance** (`candidates/open_line.py`). Over
the four baseline configurations and T1:

- **The comb** has 8–260 pF to the common net, depending on the region and the permittivity assumed.
- **The line itself** has mostly under 3 pF. Where the common net runs above a sense line for a long
  stretch, it reaches 14 pF.
- **A break right at the comb**, the worst case, would remove 47–100 % of what the channel measures. A
  break nearer the tail removes more.
- **The weakest cases** are toe5 at EU 46 (47–67 %, baseline and T1 alike), toe4 at EU 42 (52–72 %, baseline)
  and toe5 at EU 42 (57–76 %, T1). Keeping the common net off long stretches of sense lines would raise them;
  not done.

**Proposed next step (a plan, not done):** prototype the capacitive self-test first, because it needs no change
to the sole. Prove it on the coupon board the way the checker was proved: cut lines deliberately at known
places (near the tail, mid-way, at the comb) and require the test to flag each one, while intact channels pass.

## 5. Crosstalk: to be measured

One line per region, with the unselected lines left floating, has none of a matrix's sneak paths. That does
not guarantee low crosstalk. The remaining paths are listed in DESIGN.md, section 6. One of them, from the
routed copper: neighbouring sense lines run side by side for up to about 300 mm at EU 42 (and more at EU 46),
which gives about 7–12 pF (up to 14 pF at EU 46) of coupling between them. The readout has to settle through
it after every switch. Crosstalk is measured in the channel-isolation test (DESIGN.md, 9.2): load one region
and read its neighbours, at the chosen settling time, dry and humid. The same test applies to T1. A matrix
needs it more: it has sneak paths of its own, and those need suppressing (by holding unselected lines at the
sense potential) or compensating (smartinsole's 2026 paper).

## 6. What would decide between them

None of the comparison above is evidence of sensing performance. What would decide:
- **Coupon test** (DESIGN.md, section 8): the film's response, hysteresis and partial loading of one large
  region against several small ones.
- **Spatial reference.** An indenter at known points on the bench, and a pressure plate with the sole lying on
  it outside the shoe. A force plate cannot check a pressure map.
- **The same tasks and references for each candidate,** with acceptance criteria set before the data is seen:
  walking first, then the McNeese jump protocol if jumps become an intended use (COMPARISON.md).
- **Fit and durability** in the KSO Trek: toe tabs in the pockets, the tail at the collar, bend cycles at the
  toe joint.

## 7. Reproducing

```
# generator Python (numpy 2.5.4, scipy 1.18.1, shapely 2.2.0, matplotlib 3.11.2, ezdxf 1.4.5; Python 3.13.16)
python sole_candidate.py candidates/T1/layout.json --size 42 --side R
python sole_candidate.py candidates/T1/layout.json --foot person_example.json --side L
# KiCad 7 Python
python3 kicad_export.py candidates/T1/out/cand_T1_EU42_R.board.json candidates/T1/kicad/cand_T1_EU42_R.kicad_pcb
python3 verify_board.py --maps candidates/T1/maps candidates/T1/kicad/cand_T1_EU42_R.kicad_pcb
# comparisons
python candidates/study.py
python candidates/open_line.py out/sole_EU42_R.board.json candidates/T1/out/cand_T1_EU42_R.board.json
```
- **Generator outputs:** `out/` and `candidates/T1/out/` are not committed, the same as for the baseline.
  The study and open-line scripts read the board files there, so generate them first. Their results are
  committed as `candidates/study.json` and `candidates/open_line.json`.
- **No fabrication files:** `make_fab.sh` is not used for candidates, and none are made for them.
- **Provenance:** the boards were generated from commit 0257862, with no generator file modified. Their title
  blocks record the hashes of `sole_gen`, `sole_route`, `sole_candidate`, `layout` and `kicad_export`. The
  boards from 5dd52ff are kept in `archive/T1-5dd52ff/`.
- **What `verify_board.py` checks:** the three shared files. The candidate script and layout hashes are
  recorded for tracing, but not checked by it.
