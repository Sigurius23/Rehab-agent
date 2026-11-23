---
type: "decision"
title: "Buy the materials for the printed prototype and the coupon test"
status: "open"
area: "sole"
question: "Buy the materials for the printed prototype and the coupon test?"
options:
  - "yes"
  - "not yet"
blocks:
  - "[[sole-physical-prototype]]"
  - "[[sole-coupon-test]]"
source: "planning discussion 2026-11-08"
updated: "2026-11-23"
---
# Buy the materials for the printed prototype and the coupon test

A small purchase; nothing is bought without approval.

**What to buy (2026-11-22):** the parts list and tools are in `hardware/sensor-sole/BUILD.md`, section 2: TPU, copper foil, transfer tape, spacer film, enamelled wire, solder, two or three candidate films, and the bench readout (XIAO nRF52840, CD74HC4067 breakout, MCP6002, resistors and capacitors). The cost estimate is below.

## Cost estimate (2026-11-23)

A rough guide for the first prototype: the coupon and the bench readout. Prices including VAT, in euros. Three items
were checked against current shop listings (the XIAO board, Velostat film, the Cricut cutter); the rest are
estimates of typical retail prices. They are public list prices, not quotes; check them when ordering. Nothing has
been bought.

**Materials, if the tools are to hand: about €120-220.**

| Item | Estimate |
|---|---|
| XIAO nRF52840 Sense (the base board is about €10 before VAT) | €15-20 |
| Multiplexer breakout, op-amp, resistor and capacitor assortment | €15-25 |
| Breadboard and jumper wires | €8-12 |
| Velostat film, one 28 × 28 cm sheet (about \$5 at Adafruit) | €5-10 |
| A second film candidate, e.g. piezoresistive fabric (not price-checked) | €15-30 |
| Copper foil, transfer tape, double-sided spacer film | €25-45 |
| Enamelled wire, solder, flux | €15-25 |
| TPU filament, 0.5-1 kg (enough for the coupon and both soles) | €20-35 |
| Indenter (printed) and weights (bottles of water work) | €0-20 |

**The full pair of soles afterwards** adds about €50-100: more foil, film and spacer, about 20 m of wire, the 18-way
connectors, and a second readout for both feet at once.

**Tools, only if they are not to hand: about €650-1,250.**

| Tool | Estimate |
|---|---|
| Cutting plotter (Cricut Maker 3 bundles listed at about \$349-439) | €300-450 |
| 3D printer that prints TPU (direct-drive extruder) | €250-600 |
| Temperature-controlled soldering iron | €40-100 |
| Multimeter, calipers, tweezers, scalpel, loupe | €50-100 |

**Ways to cut the tool cost:**
- a makerspace, or someone else's printer and cutter, which leaves the materials only;
- a version with ready-made force sensors (FSRs), which needs no cutter but senses spots, not whole regions. It
  would not match the final sole, so it is a separate decision ([[d-printed-prototype-matches-final]]).

The first real session also needs the IMU trackers ([[d-imu-trackers]]) and two phones.

### Sources

- [Seeed XIAO nRF52840, RS Online](https://ie.rs-online.com/web/p/arduino-compatible-boards-kits/2500967)
- [Seeed XIAO nRF52840 Sense, RS Online](https://ie.rs-online.com/web/p/arduino-compatible-boards-kits/2500968)
- [Seeed datasheet listing](https://atta.szlcsc.com/upload/public/pdf/source/20260724/EF9B64229EB34B531643B5029927D518.pdf)
- [Velostat/Linqstat sheet, Adafruit](https://www.adafruit.com/products/1361)
- [Velostat 1 m roll, Cool Components](https://coolcomponents.co.uk/collections/all/products/pressure-sensitive-conductive-sheet-velostat-linqstat-1m)
- [Cricut Maker 3, Walmart](https://www.walmart.com/ip/Cricut-Maker-3-Smart-Die-Cutting-Machine-Card-Starter-Bundle-Mist/6113610751)
- [Cricut machines, Cricut](https://cricut.com/en_us/machines.html?cat=408)
