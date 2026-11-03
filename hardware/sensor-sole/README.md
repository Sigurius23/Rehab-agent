<!-- SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors -->
<!-- SPDX-License-Identifier: CERN-OHL-S-2.0 -->
# Sensor sole

This is an open pressure-sensing sole for five-toe barefoot shoes, made in any size and fitted to a person's own
foot. A thin passive flex circuit with 16 sensing regions lies in the shoe; a small pod outside the shoe reads it.

**Status: design only, not released for fabrication.** The layout, its generator and KiCad boards exist;
nothing has been fabricated or measured. No fabricator has confirmed the assumptions in
[`FABRICATION.md`](FABRICATION.md). Check results per size and side are in DESIGN.md, sections 5 and 10.
See [`DESIGN.md`](DESIGN.md) for the
design, its targets against Moticon OpenGo, and the validation plan.

| File | What it is |
|---|---|
| `DESIGN.md` | Design specification: fit, layer stack, sensing, routing, scaling, pod, calibration, decisions |
| `sole_gen.py` | Generator: foot spec → outline with toe tabs, sensing regions, electrode combs, routed copper, tail, checks; exports SVG, DXF, JSON, a board file and previews |
| `sole_route.py` | Copper routing used by the generator: sense lines (B.Cu) as a planar tree, guided fine-grid pass, common net (F.Cu), vias, stubs |
| `kicad_export.py` | Board file → KiCad 7 board (`.kicad_pcb` + `.kicad_pro`, which holds the design rules); run with the Python that ships KiCad's `pcbnew` |
| `verify_board.py` | Checks a board before fabrication: DRC with the project rules, the region-to-contact map traced through the copper, contact numbering, coverlay openings, provenance; writes `.drc.rpt` and `.check.json` |
| `make_fab.sh` | Generator → KiCad → check → Gerbers and drill; writes no fabrication files if the check fails |
| `kicad/` | The EU 42 boards (right and left) with their DRC reports, check results (including each side's contact map, tied to the board's sha256 and printed ID) and previews |
| `kicad/checks/` | DRC reports and check results of the EU 37, EU 46 and personal-example boards (the boards regenerate exactly) |
| `tests/test_verify_drc.py` | Shows that the checker fails closed on broken DRC reports (KiCad's Python) |
| `FABRICATION.md` | Fabrication assumptions against published flex-PCB capabilities, open questions, draft enquiry (not sent) |
| `person_example.json` | Personalisation format (illustrative values, not a real person) |
| `requirements.txt` | Python packages the generator needs |

```
pip install -r requirements.txt
python sole_gen.py --size 42 --out out/                  # EU 42, right foot (a few minutes: routing)
python sole_gen.py --size 42 --side L --out out/         # left foot
python sole_gen.py --foot person_example.json --out out/ # a person's foot
python3 kicad_export.py out/sole_EU42_R.board.json kicad/sole_EU42_R.kicad_pcb   # KiCad's Python
python3 verify_board.py kicad/sole_EU42_R.kicad_pcb                              # KiCad's Python
./make_fab.sh 42 R                                       # all of the above, then Gerbers if the check passes
```

## Licence

Everything in this folder is licensed under the **CERN Open Hardware Licence Version 2 – Strongly Reciprocal
(CERN-OHL-S-2.0)**; the full text is in [`LICENSE`](LICENSE). The rest of this repository remains under its own
licence (MIT; see the repository root).

Source Location: <https://github.com/Sigurius23/Rehab-agent/tree/main/hardware/sensor-sole>

If you make or convey a sole or pod built from this design, CERN-OHL-S-2.0 section 4 applies: give each
recipient the Complete Source or tell them this Source Location. This notice asks that the Source Location
be shown on the product's packaging or documentation.

This design is provided as is, without warranty (CERN-OHL-S-2.0 section 6). It is a research device. It is not a
medical device and is not validated for clinical use.
