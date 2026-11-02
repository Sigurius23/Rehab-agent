<!-- SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors -->
<!-- SPDX-License-Identifier: CERN-OHL-S-2.0 -->
# Sensor sole

This is an open pressure-sensing sole for five-toe barefoot shoes, made in any size and fitted to a person's own
foot. A thin passive flex circuit with 16 sensing regions lies in the shoe; a small pod outside the shoe reads it.

**Status: design only.** The layout and its generator exist; nothing has been fabricated or measured. See
[`DESIGN.md`](DESIGN.md) for the design, its targets against Moticon OpenGo, and the validation plan.

| File | What it is |
|---|---|
| `DESIGN.md` | Design specification: fit, layer stack, sensing, routing, scaling, pod, calibration, decisions |
| `sole_gen.py` | Generator: foot spec → outline with toe tabs, sensing regions, electrode combs, routing plan, tail, checks; exports SVG, DXF, JSON and previews |
| `person_example.json` | Personalisation format (illustrative values, not a real person) |
| `requirements.txt` | Python packages the generator needs |

```
pip install -r requirements.txt
python sole_gen.py --size 42 --out out/                  # EU 42, right foot
python sole_gen.py --size 42 --side L --out out/         # left foot
python sole_gen.py --foot person_example.json --out out/ # a person's foot
```

## Licence

Everything in this folder is licensed under the **CERN Open Hardware Licence Version 2 – Strongly Reciprocal
(CERN-OHL-S-2.0)**; the full text is in [`LICENSE`](LICENSE). The rest of this repository remains under its own
licence (MIT; see the repository root).

Source Location: <https://github.com/Sigurius23/rehab-agent/tree/main/hardware/sensor-sole>

If you make or convey a sole or pod built from this design, CERN-OHL-S-2.0 section 4 applies: give each
recipient the Complete Source or tell them this Source Location. This notice asks that the Source Location
be shown on the product's packaging or documentation.

This design is provided as is, without warranty (CERN-OHL-S-2.0 section 6). It is a research device. It is not a
medical device and is not validated for clinical use.
