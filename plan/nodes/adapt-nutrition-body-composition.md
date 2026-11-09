---
type: "step"
title: "Predict muscle and fat change from what and when the person eats"
status: "open"
area: "nutrition"
parent: "[[pillar-adapt]]"
depends_on:
  - "[[layer-muscles]]"
  - "[[layer-shape-and-mass]]"
priority: "2"
source: "promoted from idea-nutrition-body-composition, owner 2026-11-09"
updated: "2026-11-09"
---
# Predict muscle and fat change from what and when the person eats

Forward-predict the twin's lean and fat mass from logged food intake (amount, protein, timing) and training. The evidence and its strength are in [[idea-nutrition-body-composition]].

**The model:**
- **The core:** energy balance and body-composition dynamics (Hall et al. 2011), plus a protein-and-training term for lean mass with a plateau of uncertain height that shrinks with age.
- **Timing terms:** protein spread, protein before sleep, the eating window, late eating, as small modifiers with priors near zero and wide uncertainty.
- **Calibration per person:** each prediction is checked against the next DXA, body-shape or strength measurement.

**What it needs:** food and training logs, and repeated body-composition measurements. DXA is the reference when available ([[d-dxa-optional]]); body shape and strength are cheaper checks. Food logs are health data: local-only by default ([[D-07]]).
