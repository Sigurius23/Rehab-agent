<!-- SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors -->
<!-- SPDX-License-Identifier: CERN-OHL-S-2.0 -->

# Printed prototype

**Status, 2026-11-17: design only.** Nothing has been printed, cut, bought or measured, and no material is
chosen. Sensing, fit and durability are untested. Not released: nothing is made without the owner's approval.

**Decisions by the project owner:**
- 2026-11-04: the first physical prototype is 3D-printed; the flex circuit (`DESIGN.md`, `kicad/`) comes later.
- 2026-11-17: the printed prototype must match the final product
  (`plan/nodes/d-printed-prototype-matches-final.md`). The earlier through-mode stack (film between two
  electrodes) is dropped. This prototype has the flex sole's stack and sensing.

`sole_print.py` builds it from the same generator output as the flex board: the outline with toe tabs and
tail, the sensing regions and the routing plan.

```
python sole_print.py out/sole_EU42_R.board.json -o print/   # generator's Python, manifold3d and ezdxf
```

## 1. The stack, and how it matches the flex sole

Bottom to top:

| Layer | Made how | File | The flex sole's counterpart |
|---|---|---|---|
| **Carrier,** 1.0 mm: wire channels on the underside (0.5 mm) and a closed floor with one hole per wire (0.5 mm). Flat top | Printed, TPU (95A class, proposed) | `.carrier.stl` | The polyimide and the sense lines on its back; a hole is a via |
| **Electrode sheet:** per region two interleaved combs. Each sense comb is an island, wired through its hole. All common combs are one piece with a web that runs under the spacer's walls to the tail root | Cut from copper foil on an adhesive carrier (proposed) | `.electrodes.dxf` (layers `SENSE`, `COMMON`, `HOLES`, `OUTLINE`) | The combs and the common net on the front copper |
| **Spacer:** a frame with one window per region (the region inset by 0.6 mm) | Cut from double-sided adhesive film (proposed) | `.spacer.dxf` | The adhesive spacer frame |
| **Film:** one pressure-sensitive patch per window, fixed under the cover | Cut; material not chosen | `.film.dxf` | The film patch per region |
| **Cover,** 0.4 mm | Printed, TPU | `.cover.stl` | The top cover |

- **Same:** shunt-mode sensing (the film bridges two combs), the 16 regions, one sense line per region, one
  common net, a film patch per region, and the readout (`DESIGN.md`, section 6).
- **Different:**
  - the combs' fingers and gaps are 0.6 mm, which a desktop cutter can make; the flex board's are 0.2 mm. The
    sensitivity will differ, so the coupon test (section 5) should include both pitches;
  - insulated wires in printed channels replace the copper routing and the 0.5 mm-pitch tail;
  - the printed parts are 1.4 mm together, plus about 0.25 mm of foil, spacer and film (to be measured). The
    flex sole's target is 0.35–0.40 mm. Whether this fits in the KSO Trek's toe pockets is a first question
    for the fit test.
- **Fingers** run parallel to the toe-joint bend line, as on the flex board. The sense comb's spine is on the
  side nearest the region's via, and a 0.8 mm land surrounds each hole for the solder joint.

## 2. Added in this prototype

- **A reference cell** (`ref`) on the tail, outside the loaded sole: the same combs and film, never pressed,
  read on its own wire. It is for following the film's drift with temperature and humidity; re-zeroing in the
  swing phase corrects the offset but not the gain. It sits on the tail, so it follows the shoe's temperature
  only roughly. That makes 16 sense wires, one reference wire and one common wire: **18 conductors**, the
  same count as the flex tail's 18 contacts. The 16-channel readout needs one more input for it.
- **Venting.** No cell is sealed. Each window opens through its wire hole (1.2 mm, for a 0.35 mm wire) into
  the underside channels, which run to the tail's end. The holes must not be potted or filled with solder.
  `sole_print.py` checks the path for every cell. Sweat can enter the same way; that is part of the tests.
- **Connector (not chosen):** an 18-way wire-to-board connector at 1.27 mm pitch or wider at the tail's end,
  with strain relief on the tail, instead of a 0.5 mm-pitch flat-flex connector.
- **Pressure range and gain (design targets, to be set by the coupon test):** the one published range among
  the insoles we compared is XSENSOR's, 7–883 kPa (`COMPARISON.md`). The regions' areas differ eightfold (toe5 249 mm², arch
  1,992 mm²), so one amplifier gain cannot suit all of them. The readout should have a selectable gain per
  channel, chosen from the coupon's curve so that no region saturates below its expected peak pressure.
- **Not changed: the metatarsal combs stay in the bend zone.** Keeping copper out of it would remove the
  sensing right under the metatarsal heads. The fingers run parallel to the bend line, which strains them
  least. Whether that is enough is for the bend test.

## 3. The generated design (EU 42)

Generated on the lab laptop from its boards, whose design IDs differ from the committed KiCad boards'
(`EU42 R 636645a928`): the laptop's regeneration gives `82647223b9`, with every region's area within 0.05 mm²
(`plan/nodes/t-rebuild-laptop.md` is the open test of that difference). The files carry the laptop's IDs.

| | EU42 R 82647223b9 | EU42 L 553b446206 |
|---|---|---|
| Carrier: thickness, volume, holes through the floor | 1.0 mm, 20.7 cm³, 18 | 1.0 mm, 20.7 cm³, 18 |
| Cover | 0.4 mm, 8.6 cm³ | 0.4 mm, 8.6 cm³ |
| Both printed parts watertight | yes | yes |
| Bed fit (256 × 256 mm) | 217 × 216 mm, turned 138° | 217 × 216 mm, turned 42° |
| Sense combs | 17 pieces (16 regions and `ref`) | 17 |
| Common net | one piece, 7,800 mm² | one piece, 7,806 mm² |
| Smallest gap between a sense comb and the common net | 0.597 mm (rule 0.6 mm less rounding) | 0.597 mm |
| Share of each window where both combs interleave | 80 % (toe5) to 94 % (arch_med); `ref` 66 % | 81 % to 93 %; `ref` 63 % |
| Narrowest spacer wall between windows | 2.4 mm | 2.4 mm |
| Every hole on its sense comb; every cell vented to the tail's end | yes | yes |
| Walls under 0.8 mm removed from the printed layers | 7.6 mm² (channels), 0.1 mm² (floor) | 7.7 mm², 0.1 mm² |

"Interleave" is a geometric estimate: the part of a window within one finger pitch of both combs. It is not a
measured sensitivity. All of `sole_print.py`'s checks pass on both feet (`checks` in each `.print.json`).

## 4. Files

`print/EU42_R_<hash>.*`: `carrier.stl`, `cover.stl`, `electrodes.dxf`, `spacer.dxf`, `film.dxf`, `print.json`
(parameters, cells, wires, checks, bed fit) and `print.png` (the electrode sheet and the carrier's underside).
All drawings are in millimetres, in the board's coordinates, so they register on the outline layer.

**Assembly order (a plan; the full instructions, with a check after each step, are in [`BUILD.md`](BUILD.md)):**
1. Print the carrier (underside up or down, to be tried) and the cover.
2. Cut the electrode sheet, weed it, and lay it on the carrier's flat top, registered on the outline.
3. Solder each sense wire to its land through the hole, and the common wire at the tail root. Lay the wires
   in the channels to the tail's end. Leave the holes open.
4. Lay the spacer frame; fix the film patches under the cover; close the cover onto the spacer.

## 5. First tests once it is made (a plan; nothing made yet)

1. **Coupon:** a few cells with this stack, loaded with dead weights and an indenter: linearity, hysteresis,
   creep, partial loading, crosstalk between neighbours, and the same with 0.2 mm combs on a small flex board
   when one exists. A capacitive coupon beside it would show whether the resistive film is the right choice.
2. **Reference cell:** its reading against temperature and humidity, beside a loaded cell's drift.
3. **Fit:** the toe tabs in the KSO Trek's pockets, the tail at the collar, comfort over an hour.
4. **Against simulation:** the same task simulated with this sole's regions (`SIMULATION.md`) and recorded on
   the bench, with thresholds set before the data is seen.
5. **Durability:** bending at the toe joint, foil cracks, delamination, and wire breaks in the channels.
