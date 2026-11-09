---
type: "idea"
title: "Muscle and fat change with what and when the person eats"
status: "new"
area: "nutrition"
serves:
  - "[[pillar-adapt]]"
source: "owner's idea, 2026-11-09"
updated: "2026-11-09"
---
# Muscle and fat change with what and when the person eats

Predict how the twin's muscle and fat layers change with food intake: how much, what (protein especially), and when (meal timing, protein spread over the day, timing around training). The twin then shows the expected change in muscle capacity and fat distribution, and the next measurement (DXA, body shape, strength) checks it.

**Building blocks:**
- energy balance and body-composition dynamics, such as Hall et al.'s model behind the NIDDK Body Weight Planner, which splits a weight change into fat and fat-free mass;
- the twin's existing layers: fat (`fat-distribution/`), mass distribution from DXA, muscle capacity, strength calibration and training load from the sessions.

**Caveats to carry into the model:** the evidence for total intake and protein amount is much stronger than for meal timing, so timing effects need wide uncertainty bands. Food logs are health data: local-only by default ([[D-07]]).

## Resources

- [Hall et al. 2011, Quantification of the effect of energy imbalance on bodyweight (Lancet)](https://pubmed.ncbi.nlm.nih.gov/21872751/)
- [NIDDK Body Weight Planner, built on that model](https://niddk.nih.gov/research-funding/at-niddk/labs-branches/laboratory-biological-modeling/integrative-physiology-section/research/body-weight-planner)
- [The fat-distribution models in this repository](../../fat-distribution/README.md)
