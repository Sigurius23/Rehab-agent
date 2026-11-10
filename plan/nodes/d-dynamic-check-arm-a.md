---
type: "decision"
title: "Arm A after the stop rule"
status: "decided"
area: "sole"
question: "Arm A failed the pilot gate under settings v3: amend the contact, report arm A as not solvable with the assumed contact, or pause until the coupon test?"
options:
  - "an amendment to the contact itself"
  - "report arm A as not solvable with the assumed contact (v1)"
  - "pause the dynamic stage until the coupon test"
decided: "Option 2: arm A is reported as not solvable with the assumed contact; the LabValidation dynamic comparison is closed, and H1 and H2 are not evaluated"
recorded_in: "owner, 2026-11-10"
record: "hardware/sensor-sole/VALIDATION_PLAN.md"
source: "VALIDATION_PLAN.md amendment 7; the v3 pilot of [[sole-forceplate-dynamic]], 2026-11-09"
updated: "2026-11-10"
---
# Arm A after the stop rule

The v3 pilot failed the gate, and arm A's failure triggered the stop rule (amendment 7). The owner chose option 2 on
2026-11-10, in this wording:

> Arm A did not converge in three pilots (settings v1–v3) with the assumed contact (v1). Under v3, arm B, identical
> except for the contact, converged. In this setup the assumed contact is therefore the likely cause; this does not
> show that no solution exists. The LabValidation dynamic comparison is closed. H1 and H2 are not evaluated.

Option 3 was not chosen because it could not change arm A's result in this dataset:
- the coupon test measures only the sensor stack (about 0.4 mm), while the assumed contact stands for everything
  between the bones and the floor: the plantar soft tissue, the shoe and the sensor stack;
- a law for our sole and shoe would describe a person wearing them, not LabValidation's participants
  (`FOOT_MODELS.md` section 9, item 2).

It closes [[sole-forceplate-dynamic]], [[t-dyn-h1]] and [[t-dyn-h2]].
