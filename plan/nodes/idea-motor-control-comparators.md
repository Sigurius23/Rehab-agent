---
type: "idea"
title: "Compare the twin's muscle estimates with SCONE and MuscleMimic controllers"
status: "new"
area: "forces"
serves:
  - "[[goal-muscle-loads]]"
source: "owner's research note on fascia, nerve and motor-control models, 2026-11-04"
updated: "2026-11-09"
---
# Compare the twin's muscle estimates with SCONE and MuscleMimic controllers

- **SCONE:** optimises feedback and reflex controllers for predictive movement, including OpenSim gait studies. The most practical OpenSim gait-control comparator. A controller is a hypothesis about control, not a measurement of nerves or cortex.
- **MuscleMimic:** learned muscle-driven full-body control with released models and checkpoints (416 muscle actuators). MuJoCo, not OpenSim. Its muscle-EMG correlations varied a lot across the population, and matching motion does not guarantee correct muscle activation. Code Apache-2.0; some AMASS-derived data are non-commercial.

Both also matter for predictive assistance, [[exo-assist-simulation]].

## Resources

- [SCONE gait study on SimTK](https://simtk.org/projects/pfdeficitsgait)
- [MuscleMimic (arXiv 2603.25544)](https://arxiv.org/html/2603.25544v1)
