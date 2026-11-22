<!-- SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors -->
<!-- SPDX-License-Identifier: CERN-OHL-S-2.0 -->

# Building the printed prototype

How to make the printed sensor sole (`PRINTED.md`) and read it on a bench. Start with the **coupon**: a small piece
with four cells and the reference cell, the sole's exact stack in miniature. It proves the cutting, the soldering
and the film on a fraction of the material, and it is what the coupon test measures (`plan/nodes/t-coupon.md`).
Build the whole sole only after the coupon works.

**Status, 2026-11-22: instructions only.** Nothing here has been bought, printed, cut, soldered or run. The steps
are a plan; the first build will correct them. Buying the materials is the owner's decision
(`plan/nodes/d-prototype-materials.md`). Recordings of a person wearing the sole are health data and stay outside
the repository.

## 1. What you build, and the files

| Part | Coupon (`print/coupon/`) | Sole, EU 42 (`print/`) | Made how |
|---|---|---|---|
| Carrier, 1.0 mm, wire channels underneath | `COUPON_C_8fa2e7f7b4.carrier.stl` | `EU42_R_82647223b9.carrier.stl`, `EU42_L_553b446206.carrier.stl` | Printed, TPU |
| Electrode sheet: two combs per cell | `.electrodes.dxf` | `.electrodes.dxf` | Cut from copper foil |
| Spacer: a frame with one window per cell | `.spacer.dxf` | `.spacer.dxf` | Cut from double-sided adhesive film |
| Film: one patch per window | `.film.dxf` | `.film.dxf` | Cut from the pressure-sensitive film |
| Cover, 0.4 mm | `.cover.stl` | `.cover.stl` | Printed, TPU |
| Readout | `readout/` (part 3) | the same, 16 lines | Breadboard |

**The coupon's cells** (`coupon_print.py`, which uses `sole_print.py`'s builder unchanged, so every check is the
sole's):

| Cell | Size | Window | Why |
|---|---|---|---|
| `cell_s16` | 16 × 16 mm | 219 mm² | about the smallest sole region (toe5, 249 mm²) |
| `cell_m30` | 30 × 30 mm | 829 mm² | a mid-sized region |
| `cell_l45` | 45 × 45 mm | 1,918 mm² | about the largest region (the arch, 1,992 mm²) |
| `bend_60x12` | 60 × 12 mm | 635 mm² | the bend test: its baseline at a 10 mm radius |
| `ref` | on the tail | 192 mm² | never pressed: drift with temperature and humidity |

The coupon is 115 × 80 mm with a 60 mm tail, 1.4 mm printed. All of its checks pass (`print.json`): watertight
parts, one hole per wire, every comb in one piece, 0.6 mm between combs, every cell vented to the tail's end.

**If the cutter can't hold 0.6 mm,** generate a coarser coupon and use it throughout:
`python coupon_print.py -o print/coupon_0.8 --finger 0.8 --gap 0.8`. The sole's files take the same options
(`sole_print.py --finger 0.8 --gap 0.8`). Coarser combs sense less of each window; the coupon shows how much.

## 2. Parts and tools

The parts are classes, with examples. Choosing and buying them is the owner's decision. No prices or suppliers
here: check them when ordering.

**Sole stack:**

| Item | What to look for | For the coupon | For two soles |
|---|---|---|---|
| TPU filament, 1.75 mm | shore 95A class | about 6 m (14 cm³) | about 30 m (carrier and cover, about 30 cm³ a foot, plus trials) |
| Copper foil | about 35 µm (1 oz), solderable, on an adhesive back; non-conductive adhesive is safest | 120 × 100 mm (the copper is 112 × 92 mm) | two sheets of about 280 × 170 mm (the copper is 267 × 164 mm) |
| Transfer tape | low-tack, for weeding and placing cut foil | a sheet | a few sheets |
| Spacer film | double-sided adhesive with a carrier, about 0.05–0.1 mm | 120 × 100 mm | two sheets of about 280 × 170 mm |
| Pressure-sensitive film | **not chosen: see below** | 120 × 100 mm of each candidate | two sheets of about 280 × 170 mm |
| Wire | solderable enamelled copper (polyurethane), 30–32 AWG, outer diameter at most 0.35 mm | 2 m | 20 m |
| Solder | 0.5 mm, with flux; plus a flux pen | | |
| Adhesive | flexible, for the wires at the tail's end only | | |

**The film, the one open choice.** The coupon is how it gets chosen (`DESIGN.md`, "Material"). Get small pieces of
two or three:
- **carbon-loaded polyolefin film** (Velostat or Linqstat class, about 0.1 mm): cheap, the usual choice in DIY
  pressure sensors, and known for hysteresis, creep and temperature drift;
- **piezoresistive coated fabric** (EeonTex class): more compliant, thicker;
- a printed carbon layer only if a printing process is to hand.

**Bench readout** (part 3):

| Item | What to look for | Count |
|---|---|---|
| Microcontroller | Seeed XIAO nRF52840 (the Sense variant adds the pod's IMU; either works here) | 1 |
| Multiplexer | CD74HC4067 16:1 analog multiplexer on a breakout board | 1 |
| Op-amp | dual, rail-to-rail input and output, 3.3 V, low input bias: MCP6002 (DIP-8) for the breadboard. The pod's design uses a zero-drift part (OPA333 class); an OPA2333 on an adapter fits the same circuit | 1 |
| Resistors, 1 % metal film | 56 kΩ and 10 kΩ (the bias); for Rf, two each of 10 kΩ, 33 kΩ, 100 kΩ, 330 kΩ | |
| Capacitors | 100 pF ceramic (2), 1 µF ceramic (1) | |
| Breadboard, jumper wires, pin headers, USB-C cable | | |

**Tools:**
- an FDM printer that prints TPU (direct drive helps), with a bed of at least 217 × 216 mm for the sole (the coupon
  needs 115 × 140 mm);
- a cutting plotter that cuts foil (Cricut or Silhouette class). Whether it holds 0.6 mm fingers in copper is the
  first thing the coupon tests;
- a temperature-controlled soldering iron with a fine tip, able to reach about 380 °C to strip polyurethane enamel;
- a multimeter with continuity and a resistance range up to at least 20 MΩ;
- fine tweezers, a scalpel, calipers, isopropyl alcohol, a magnifier or loupe;
- for the coupon test: weights from 0.1 to 5 kg, and a flat round indenter of 10 mm diameter (printed in a hard
  plastic). 5 kg on 10 mm is about 620 kPa, 1 kg about 125 kPa, 0.1 kg about 12 kPa.

## 3. Build the coupon

Every step ends with a check. Don't go on until it passes: a fault found later costs the whole piece.

**3.1 Print.**
1. Print `carrier.stl` (try underside down first; `PRINTED.md` leaves the orientation open) and `cover.stl` in TPU.
2. **Check:** thickness 1.0 mm (carrier) and 0.4 mm (cover), ±0.1 mm, with calipers. Every hole is open: a wire
   passes through each of the 6. Every channel is clear from its hole to the tail's end.

**3.2 Cut the electrodes.**
1. Cut `electrodes.dxf` from the copper foil, all layers except `OUTLINE` and `HOLES`. Cut `OUTLINE` too if it
   helps registration. Weed the waste with tweezers under the magnifier.
2. **Check, before it goes on the carrier:**
   - under the loupe: no finger broken, no bridge across a gap;
   - each sense comb is one piece: continuity from its land to its farthest finger;
   - the common net is one piece: continuity between any two common combs;
   - **isolation: more than 20 MΩ between every sense comb and the common net.** Any lower reading is a bridge; fix
     it with the scalpel or recut.

**3.3 Lay the electrodes.**
1. Lift the cut sheet with transfer tape, line its outline up with the carrier's edge, and press it onto the flat
   top. Peel the transfer tape slowly.
2. **Check:** the land of each sense comb sits over its hole. Repeat the isolation check (more than 20 MΩ).

**3.4 Wires.**
1. For each cell: thread a wire up through its hole from underneath, strip the end with the iron (the enamel burns
   off at about 380 °C), and solder it to the land around the hole. The common wire goes to the common net's
   hole at the tail root. **Keep every hole open:** it is the cell's vent. No solder or glue in the hole.
2. Label each wire at the tail's end: `cell_s16`, `cell_m30`, `cell_l45`, `bend_60x12`, `ref`, `COM`.
3. Lay the wires in the underside channels to the tail's end. Fix them with flexible adhesive at the tail's end only.
4. **Check:**
   - continuity from each wire to its own comb;
   - isolation, more than 20 MΩ, between every pair of wires, and between every sense wire and `COM`;
   - the carrier still lies flat.

**3.5 Close the stack.**
1. Cut `spacer.dxf` from the adhesive film, and lay the frame on the electrodes, the windows over the cells.
2. Cut `film.dxf` from the chosen film. Place one patch in each window, then lay the cover on top. `PRINTED.md`
   fixes the patches under the cover; placing them in the windows first is easier to register.
3. **Check with the multimeter, each wire against `COM`:**
   - unloaded: write down the resistance (it depends on the film; often megaohms);
   - pressed with a finger: it falls clearly. A cell that doesn't respond has a film or contact fault;
   - `ref` unloaded, for the baseline.

**3.6 Choose the gain.** Press the hardest expected load on the largest cell (`cell_l45`) and note its lowest
resistance, R_min. Use the largest Rf at or below 5.4 × R_min, so the amplifier doesn't saturate (part 4). Record
the Rf for each line.

## 4. Build the bench readout

**How it reads.** The common comb is at ground. The selected sense line is held at Vbias (0.5 V) by an
amplifier's inverting input, so the film's conductance G draws a current, and the output is
Vout = Vbias × (1 + Rf × G). The logger reads Vbias as well, so G = (Vout / Vbias − 1) / Rf whatever the ADC's
reference is. The output tops out near 3.2 V, so the largest conductance that fits is about 5.4 / Rf:

| Rf | Largest G | Lowest film resistance |
|---|---|---|
| 10 kΩ | 540 µS | 1.9 kΩ |
| 33 kΩ | 164 µS | 6.1 kΩ |
| 100 kΩ | 54 µS | 18.5 kΩ |
| 330 kΩ | 16 µS | 61 kΩ |

**Wiring** (the XIAO's 3V3 and GND supply everything):

| From | To |
|---|---|
| 56 kΩ | 3V3 → **Vbias** node |
| 10 kΩ | **Vbias** node → GND (Vbias ≈ 0.5 V) |
| 1 µF | **Vbias** node → GND |
| **Vbias** node | op-amp pins 3 (IN A+) and 5 (IN B+), and XIAO **A2** (D2) |
| Op-amp pin 8 / pin 4 | 3V3 / GND |
| Multiplexer VCC / GND / EN | 3V3 / GND / GND |
| Multiplexer S0, S1, S2, S3 | XIAO D7, D8, D9, D10 |
| Multiplexer SIG | op-amp pin 2 (IN A−) |
| Rf (multiplexed) with 100 pF in parallel | op-amp pin 2 (IN A−) ↔ pin 1 (OUT A) |
| Op-amp pin 1 (OUT A) | XIAO **A0** (D0) |
| `ref` wire | op-amp pin 6 (IN B−) |
| Rf (reference) with 100 pF in parallel | op-amp pin 6 (IN B−) ↔ pin 7 (OUT B) |
| Op-amp pin 7 (OUT B) | XIAO **A1** (D1) |
| `COM` wire | GND |
| Coupon wires `cell_s16`, `cell_m30`, `cell_l45`, `bend_60x12` | multiplexer C0, C1, C2, C3 |
| Sync pulse (optional) | XIAO D6 (rising edge, 3.3 V logic) |

For the sole, the 16 region wires go to C0–C15 in the order of the sole's channel map (`maps/`), and `ref` stays
on its own amplifier.

**Firmware:** `readout/sole_bench/sole_bench.ino`, for the Arduino IDE with Seeed's nRF52 board package. It reads
each line at 100 Hz, with a 300 µs settling time after each switch and 4-fold oversampling. It accepts serial
commands to change the line count (`L16` for the sole), settling time, oversampling, frame period, and the Rf values
it records (`R100000`, `Q100000`).

**Checks before any film:**
1. With no sense wires connected, every line reads about Vbias (the counts on A0 equal A2's, within a few counts).
2. Put a 100 kΩ resistor from C0 to GND: the logger shows 10 µS at Rf 100 kΩ (G = 1 / 100 kΩ). Do the same on
   every line and on `ref`. This is the readout's own calibration.
3. Pulse D6 and see `sync_n` count up.

**Logging:** `python readout/log_bench.py <port> --names cell_s16 cell_m30 cell_l45 bend_60x12`. It writes a CSV
to `~/rehab-agent-data/sole-bench/` with raw counts, conductances in µS, and a flag for saturated lines. Then press
each cell in turn and check that the right column responds: that is the channel map, confirmed.

## 5. Then

1. **The coupon test** (`plan/nodes/t-coupon.md`): linearity, hysteresis, creep and repeatability under the weights
   and the indenter, the bend strip at a 10 mm radius, partial loading, crosstalk between neighbouring cells, and
   `ref` against temperature and humidity. Its expected result is still a proposal; confirm it, and set the full
   scale, before the first press.
2. **The sole,** once the coupon works: the same steps with the EU 42 files (`print/`), 16 cells and `ref`, and the
   18-way connector at the tail.
3. **Fit and the tests in `PRINTED.md`, section 5.**

**Status of the readout code:** the logger's parsing and conversion are tested
(`tests/test_coupon_readout.py`). The firmware has been checked only for syntax against a stub of the Arduino
API; it has not been compiled for the board or run on the hardware.
