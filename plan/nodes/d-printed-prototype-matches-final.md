---
type: "decision"
title: "The printed prototype matches the final sole"
status: "decided"
area: "sole"
question: "Must the 3D-printed prototype use the same sensing as the final flex sole?"
decided: "Yes: the printed prototype must match the final product (same sensing principle, regions and readout); the aim is the best possible design"
recorded_in: "owner, 2026-11-17"
source: "design look at hardware/sensor-sole, 2026-11-17"
updated: "2026-11-17"
---
# The printed prototype matches the final sole

The owner decided on 2026-11-17 that the 3D-printed prototype must match the final product, and that the aim is the best possible design.

What this changes: `hardware/sensor-sole/PRINTED.md` describes a through-mode stack (film between two electrodes), while the flex sole in `DESIGN.md` is shunt-mode (film over interleaved combs). The two respond differently, so the printed stack as written is superseded. How the printed prototype gets matching electrodes is not decided yet.

Suggestions from the same design look, none decided: a vent per region, an unloaded reference cell, a defined pressure range with per-channel gain, a capacitive coupon beside the resistive ones, a sturdier tail connector, metatarsal combs kept out of the bend zone, and a big-toe-only first build.

**Done in the design (2026-11-17):** `sole_print.py` now writes a prototype with the flex sole's stack and sensing:
a printed carrier and cover, cut copper comb electrodes (shunt mode), a cut spacer and film patches, with a
reference cell on the tail and a checked vent path. The EU 42 right and left files are in
`hardware/sensor-sole/print/`, and all of the generator's checks pass. It is described in
`hardware/sensor-sole/PRINTED.md`, and the other makers' insoles were revisited in `COMPARISON.md`.

The owner asked for one final print-ready design and left the choices to this session. Chosen, and open to change:
- comb electrodes cut from copper foil, at 0.6 mm fingers and gaps;
- resistive film now, with a capacitive coupon proposed beside it;
- all five toes kept;
- the metatarsal combs left in the bend zone.

Nothing has been printed, cut, bought or measured. Buying materials is [[d-prototype-materials]].

