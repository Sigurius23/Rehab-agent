---
type: "idea"
title: "Brain regions lighting up with the person's movement (a TRIBE v2-style model)"
status: "new"
area: "neuro"
serves:
  - "[[pillar-simulate]]"
source: "owner's idea, 2026-11-09"
updated: "2026-11-09"
---
# Brain regions lighting up with the person's movement (a TRIBE v2-style model)

Show which brain regions are active as the twin moves: motor cortex, cerebellum, basal ganglia, by body part and phase of the movement. Useful for explaining a movement and, later, for rehabilitation after stroke or with Parkinson's.

**What TRIBE v2 is, and what it is not.** Meta FAIR's TRIBE v2 (March 2026) is an encoding model: it predicts the fMRI response of a person **watching or hearing** a stimulus (video, audio, text), trained on over 1,000 hours of fMRI from 720 people. Fed a video of the squat, it would predict a viewer's brain response, which includes action-observation areas, not the activity that **produces** the mover's movement. Its weights are released under a non-commercial licence (CC BY-NC).

**So two routes, to check before building anything:**
- an observer's view: TRIBE v2 on the session video, labelled as what watching the movement evokes;
- the mover's own activity: a model from movement (joint angles, muscle activations from the twin) to motor-system activity, from fMRI or EEG data recorded during movement. Which datasets and models exist for that is the first question.

Anything shown is a model's prediction, not a measurement of this person's brain.

## Resources

- [TRIBE v2 paper (Meta FAIR, arXiv 2605.04326)](https://arxiv.org/abs/2605.04326)
- [Neuromotor anatomy audit in this repository](../../docs/anatomy-audit-batch7-neuromotor.md)
