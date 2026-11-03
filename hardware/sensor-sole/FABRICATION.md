<!-- SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors -->
<!-- SPDX-License-Identifier: CERN-OHL-S-2.0 -->

# Sensor sole: fabrication assumptions and open questions

**Status: not released for fabrication.** No manufacturer has confirmed any of this yet. The table below
compares our assumptions with two flex fabricators' *published* capability pages. The questions at the end
need a written answer from the chosen fabricator before the first order.

A clean KiCad design-rule check only shows that the copper meets *our own* rules (in the `.kicad_pro`). It
says nothing about any of the following:
- the fabricator's real process limits;
- bend durability at the toe joint;
- fit in the shoe;
- pressure-sensing accuracy.

Those come from the coupon board, the fit test and the force-plate comparison (DESIGN.md, section 8).

## What we assume

| Item | Our design | JLCPCB, published¹ | PCBWay, published² | Status |
|---|---|---|---|---|
| Layers, base | 2-layer polyimide flex, 25 µm PI core | 2-layer, 25 µm or 50 µm PI | 1–12 layers; adhesive and adhesiveless PI | OK |
| Copper | 18 µm (½ oz), rolled-annealed (RA) wanted for dynamic flexing | 12 / 18 / 35 µm; RA or ED not stated | Not stated | **Ask** (RA vs ED) |
| Finished thickness | ≈ 0.11–0.12 mm | 2-layer: 0.11 / 0.12 / 0.2 mm | 4–40 mil | OK |
| Board size, one sole | EU 37: 237 × 155 mm; EU 42: 270 × 167 mm; EU 46: 297 × 177 mm (outline bounding box, tail included) | Regular max 234 × 490 mm; 250 × 600 mm with edge rails on request | Max 8.668″ × 27.5″ (≈ 220 × 698 mm) | One sole per panel fits both. L and R in one panel exceed JLCPCB's 234 × 490 mm unless nested. **Ask** |
| Track / clearance | Sense lines 0.12 mm, COM 0.20 mm, clearance 0.15 mm | 18 µm copper: 3.5 / 3.5 mil (0.089 mm); width tolerance ±20 % | 2 / 2 mil | OK |
| Comb fingers / gaps | 0.20 / 0.20 mm | Within the track rules; ±20 % width tolerance | Within the track rules | OK. The ±20 % tolerance (±0.04 mm) changes each region's sensitivity, so per-region calibration is needed anyway |
| Vias | 0.45 mm pad, 0.20 mm drill (ring 0.125 mm), 18–24 per sole | Regular 0.30 / 0.55 mm; 2-layer "extreme" 0.10 / 0.30 mm at extra cost; pad ≥ hole + 0.2 mm (≥ 0.25 better); PTH annular ring ≥ 0.25 mm recommended, 0.18 mm absolute | Min drill 4 mil | Our vias fall in JLCPCB's extra-cost class. **Ask** whether the 0.18 mm ring limit applies to vias. Fallback: regenerate with 0.55 / 0.30 mm vias |
| Copper to outline | 0.30 mm (DRC rule) | ≥ 0.3 mm; outline ±0.1 mm (±0.05 on request) | Not stated | OK |
| Coverlay over the combs | One opening per region exposing both combs, notched where F.Cu tracks land or run within 0.16 mm (covers ≤ 1.5 % of a region's sensing area at EU 42); coverlay everywhere else on F, full coverlay on B | Opening-to-trace ≥ 0.15 mm; "coverlay expansion (one-sided) 0.1 mm"; coverlay over vias recommended | Min coverlay bridge 8 mil (0.2 mm) | DRC checks other copper ≥ 0.15 mm from an opening. Openings are ≥ 1.2 mm apart. **Ask** whether the 0.1 mm expansion is added to our openings |
| Surface finish | ENIG on the contacts and the combs | ENIG only, 1 or 2 µ″ gold | HASL, ENIG, ENEPIG, electrolytic Ni/Au, soft gold, hard gold, immersion silver, OSP, immersion tin | **Ask.** See "Dynamic flexing" below |
| ZIF tail contacts | 18 × 0.30 mm at 0.50 mm pitch, 4.0 mm long, 0.5 mm from the tail end, on B.Cu | Gold-finger pad ≥ 0.2 mm from the edge (else cut back); thickness ±0.03 mm in the gold-finger area | Not stated | OK. Check against the chosen connector's FFC drawing |
| Stiffener at the tail | PI on the F side (behind the contacts), total 0.30 mm at the contacts | PI 0.1 / 0.15 / 0.20 / 0.225 / 0.25 mm; "0.3 mm connector on a 0.11 mm FPC: 0.225 mm stiffener" | Thickness with PI stiffener ±10 % | OK at JLCPCB (±0.03 mm at the gold fingers). PCBWay's ±10 % is ±0.03 mm only if it applies to the 0.3 mm total. **Ask** |
| Bend at the toe joint | Dynamic, once per step: about 2–4 million cycles a year of daily walking. Radius set by the foot, estimated ≥ 10 mm (≈ 80 × thickness) | Not stated | Min bend radius, double-layer: 7–10 × thickness (static or dynamic not stated) | **Ask** for their dynamic-flex rules. Measure on the coupon board |

¹ <https://jlcpcb.com/capabilities/flex-pcb-capabilities>, read 2026-11-03.
² <https://www.pcbway.com/fpc-rigid-flex-pcb/flex-pcb.html>, read 2026-11-03.

Published pages change, and they describe standard orders. The fabricator's written answer to the questions
below is what counts.

## Dynamic flexing: design points to review with the fabricator

- **Plating on flexing copper.** ENIG puts a nickel layer under the gold. Nickel is brittle, and 35–61 % of
  each of the mt1–mt5 combs lies in the toe-joint bend zone (EU 42 R; the generator reports this per board as
  `regions_in_bend_pct`). Options:
  - ENIG only on the tail contacts, and a ductile finish or carbon ink on the combs;
  - ENIG everywhere, and measure the crack rate on the coupon board.
- **Copper on both sides in the bend zone.** Under the regions, B.Cu is kept free, so the combs have no
  copper behind them. Where the trunk crosses the bend zone, F.Cu common lines could lie over B.Cu sense lines
  and stiffen the flex locally (the "I-beam" effect). The generator measures this per board as
  `stacked_copper_in_bend_mm2`. It is 0 mm² on both EU 42 boards; all 14 mm² of stacked copper lies outside
  the bend zone.
- **Vias** are kept out of a ±12 mm band around the toe-joint line (a rule area on the board).
- **Fingers** run parallel to the bend line, so a bend strains them along their length the least.

## Questions for the fabricator (draft enquiry, not sent)

> We are prototyping a two-layer polyimide flex circuit: a pressure-sensing insole, about 270 × 167 mm
> (EU 42; other sizes 237 × 155 mm to 297 × 177 mm). It has an 18-contact, 0.5 mm-pitch ZIF tail. Quantity:
> 2–5 pairs (left and right are mirror images). Gerbers and drill files are available. Please confirm or
> correct:
>
> 1. Rolled-annealed copper, 18 µm, on adhesiveless 25 µm polyimide: available, and at what cost?
> 2. Vias 0.20 mm drill / 0.45 mm pad (0.125 mm annular ring): acceptable, and in which price class?
> 3. Large coverlay openings (one per sensing region, 300–2800 mm² each) expose interleaved 0.20 / 0.20 mm
>    comb electrodes. Do you add an expansion to our openings, and what is your registration tolerance?
> 4. Surface finish: can ENIG be limited to the tail contacts, with a different finish on the combs (OSP,
>    immersion silver or bare copper)? Or would you recommend ENIG throughout for a part that flexes at
>    every step?
> 5. Tail: PI stiffener on the side opposite the contacts, for a total of 0.30 ± 0.03 mm at the contacts.
>    Which stiffener thickness do you use with this stack-up?
> 6. Dynamic flexing: what is your minimum bend radius for a two-layer part flexed millions of times, and do
>    you have rules for copper on both layers inside the flex zone?
> 7. Can the left and right soles share one panel, or must they be ordered as separate panels?

The enquiry has not been sent. Sending it, choosing a fabricator and ordering need the project owner's
approval.
