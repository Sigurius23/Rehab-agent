<!-- SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors -->
<!-- SPDX-License-Identifier: MIT -->

# Shoe CAD capability map: from a foot scan to a last

The owner's research note of 2026-11-02, as an interactive page and a table. It compares 20 shoe and last design
tools on 26 features (520 rated cells; 20 are marked unverified rather than guessed). The tools are grouped along
six stages:
1. capture the foot;
2. clean the mesh;
3. create the last;
4. design the upper and pattern;
5. design the sole and footbed;
6. prepare for printing.

Open [`foot-to-last-capability-map.html`](foot-to-last-capability-map.html) in a browser. It is self-contained,
with no external scripts.

The ratings come from published vendor material, not hands-on testing. The `cost` column gives indicative
published list prices and is not scored. A `?` cell must be confirmed with the vendor before anything relies on
it. Nothing here has been bought, installed or tested.

## Files

| File | What it is |
|---|---|
| `data.py` | The source: features, weights, tools, and every rating with its note |
| `gen_part1.py`, `assets.py`, `build.py` | Generate the page and the table from `data.py` |
| `foot-to-last-capability-map.html` | The page |
| `index.html` | The same page, byte for byte. `build.py` writes both, as the preview root |
| `feature-map.csv` | The ratings as a table, with the two composite scores (core: a printable last; full: a printable shoe) |

## Regenerating

Edit `data.py`, then:

```bash
python3 shoe-cad-map/build.py
```

Standard library only. It writes the two HTML files and the CSV next to itself, and prints each tool's scores.
On 2026-11-09, the committed scripts regenerated all three outputs byte for byte.

## In the plan

[`plan/nodes/idea-personalised-footwear.md`](../plan/nodes/idea-personalised-footwear.md): personalised footwear
from the foot scan (last, sole and five-toe shoe). It connects to the personalised foot model and to the sensor
sole, which has to fit the shoe.
