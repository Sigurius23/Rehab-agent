---
type: "idea"
title: "Brain regions lighting up with the person's movement (a TRIBE v2-style model)"
status: "new"
area: "neuro"
serves:
  - "[[pillar-simulate]]"
source: "owner's idea, 2026-11-09; owner's research note on fascia, nerve and motor-control models, 2026-11-04"
updated: "2026-11-09"
---
# Brain regions lighting up with the person's movement (a TRIBE v2-style model)

Show which brain regions are active as the twin moves: motor cortex, cerebellum, basal ganglia, by body part and
phase of the movement. Useful for explaining a movement and, later, for rehabilitation after stroke or with
Parkinson's.

**TRIBE v2 itself does something different.** Meta FAIR's TRIBE v2 (March 2026) predicts the fMRI response of a
person **watching or hearing** a stimulus. On a video of the squat, it would predict a viewer's brain response,
not the activity that **produces** the movement. Its weights are non-commercial (CC BY-NC).

**The motor counterpart, from the owner's research note (2026-11-04):**
- **μSim** is the closest: a motor-cortex-inspired recurrent controller that receives feedback and produces muscle
  commands, with its activity compared with recorded motor-cortex activity. Shown on macaque upper-limb cycling,
  not human walking or a whole brain. Code MIT; checkpoints and data to check separately.
- It does not replace TRIBE's video-to-fMRI function. The motor-control chain it belongs to is
  [[idea-neural-motor-chain]].

**So two routes:** TRIBE v2 on the session video, labelled as what watching the movement evokes; or the mover's
own motor activity, from a μSim-like controller driven by the twin's movement. Anything shown is a model's
prediction, not a measurement of this person's brain.

## Resources

- [TRIBE v2 paper (Meta FAIR, arXiv 2605.04326)](https://arxiv.org/abs/2605.04326)
- [μSim (bioRxiv)](https://www.biorxiv.org/content/10.1101/2024.02.02.578628v3)
- [Neuromotor anatomy audit in this repository](../../docs/anatomy-audit-batch7-neuromotor.md)
