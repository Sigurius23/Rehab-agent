---
type: "idea"
title: "Thoracolumbar full-body model, for a later spine-load study"
status: "new"
area: "person-model"
serves:
  - "[[rehab-agent]]"
source: "discussion 2026-11-09, settings v2 pilot diagnosis of [[sole-forceplate-dynamic]]"
updated: "2026-11-09"
---
# Thoracolumbar full-body model, for a later spine-load study

The full-body thoracolumbar spine model (Burkhart, Allaire, Banks and Anderson; OpenSim 4 version 2.0, male and
female) models the trunk with muscles: 446 trunk muscles and every spine level from the sacrum to the head. It suits
a study of spinal loads and trunk muscle forces. The owner has a download, not in the repository.

It stays out of the dynamic force-plate check (owner, 2026-11-09). There the combined vertical force and centre of
pressure follow from the motion and the mass distribution, not from how the joint torques are produced. It would
also cost weeks per solve.

Compared with the check's model, from the model files and one timed dynamics evaluation on the lab laptop
(2026-11-09):

| | Current model (OpenCap, scaled to subject 2) | Thoracolumbar model (male) |
|---|---|---|
| Muscles | 80, all in the legs | 620: 446 trunk, 106 arms and shoulders, 68 legs |
| Trunk and arms driven by | 13 torque actuators | muscles, plus 8 torque actuators |
| Free joint angles | 35 | 108 (18 spine levels, ribs, shoulder girdle) |
| Covered by the dataset's kinematics | 35 of 35 | 16 of 108 (pelvis, hips, knees, ankles) |
| Scaled to the subject | yes | no (generic 78 kg male) |
| Foot contact, subtalar and toe joints | yes | none; subtalar and toe joints locked |
| Variables per time point in the solve | 263 | about 1600-1700 (~6x) |
| One dynamics evaluation | 0.45 ms | 2.79 ms (6x) |

Estimates, not measured: about 40 times the work per solver iteration, and a constraint matrix of a few hundred
million nonzeros where the check's has about 9 million.

To use it, it would need, per subject: scaling, inverse kinematics from the markers for its 92 joint angles that
the dataset does not give, and foot contact.
