---
type: "step"
title: "The sensor film's measured response (coupon test)"
status: "open"
area: "sole"
parent: "[[goal-sensor-sole]]"
priority: "2"
source: "hardware/sensor-sole/DESIGN.md sections 8 and 9.3; hardware/sensor-sole/FOOT_MODELS.md sections 4 and 9"
updated: "2026-11-09"
---
# The sensor film's measured response (coupon test)

Small coupons of each candidate material, measured as `DESIGN.md` section 8 and 9.3 set out, with dead weights and
an indenter:
- linearity, hysteresis, creep and repeatability;
- temperature and moisture drift;
- baseline shift when bent to a 10 mm radius;
- partial loading.

It chooses the material, and gives the sensor model in `sole_sim.py` a measured curve in place of its placeholder.
Needs the materials ([[d-prototype-materials]]).

**What it does not give (2026-11-09).** The assumed contact law stands for everything between the bones and the
floor: the plantar soft tissue, the shoe and the sensor stack. The stack is the thinnest of the three, so the
coupon test gives only a small part of the law (`FOOT_MODELS.md` section 9). If the rig can measure compression,
the stack's compression on the footbed is worth recording too.

A law built for our sole and shoe describes a person wearing them. It would not make arm A of the LabValidation
comparison ([[sole-forceplate-dynamic]]) valid, because those participants were recorded in other footwear.
