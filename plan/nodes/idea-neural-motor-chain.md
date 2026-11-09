---
type: "idea"
title: "A neural motor-control chain: brain-inspired controller, spinal cord and motor units, then muscles"
status: "new"
area: "neuro"
serves:
  - "[[pillar-simulate]]"
source: "owner's research note on fascia, nerve and motor-control models, 2026-11-04"
updated: "2026-11-09"
---
# A neural motor-control chain: brain-inspired controller, spinal cord and motor units, then muscles

The owner's research note proposes: **μSim-like controller → MyoGen-like spinal and motor-unit model → the musculoskeletal model.** A proposed architecture, not an existing, verified integration: joining their signals, time steps, muscles and coordinate systems is substantial engineering, and needs its own validation.
- **μSim:** motor-cortex-inspired controller producing muscle commands (macaque upper-limb cycling so far). Code MIT.
- **MyoGen:** descending drive, spinal circuitry, proprioception, motor units, force and synthetic EMG; selected motor-unit statistics compared with human recordings. Its cortical drive is an input, not the person's measured brain activity. AGPL-3.0-or-later, which has deployment obligations.

It would also drive [[idea-brain-activity]] for the mover's own motor activity.

## Resources

- [μSim (bioRxiv)](https://www.biorxiv.org/content/10.1101/2024.02.02.578628v3)
- [MyoGen (bioRxiv)](https://www.biorxiv.org/content/10.64898/2026.01.01.697284v1)

The owner's research note on fascia, nerve and motor-control models, 2026-11-04 also lists NeuroMotion beside μSim-like controllers and MyoGen, as modular hypothetical generators, each compared with held-out neural, EMG, movement and force data at its own level. TRIBE v2's BOLD signals are not to be converted into motor spikes.
