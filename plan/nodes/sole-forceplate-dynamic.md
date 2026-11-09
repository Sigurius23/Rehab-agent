---
type: "step"
title: "Dynamic force-plate check: our sole against OpenCap's spheres"
status: "doing"
area: "sole"
parent: "[[goal-sole-simulation]]"
depends_on:
  - "[[sole-forceplate-quasistatic]]"
priority: "1"
stop_rule: "arm A fails the pilot gate under settings v3"
stop_by: "2026-11-11"
stop_owner: "owner"
record: "hardware/sensor-sole/VALIDATION_PLAN.md"
source: "hardware/sensor-sole/VALIDATION_PLAN.md stage A item 2, Amendments 4-7"
updated: "2026-11-09"
---
# Dynamic force-plate check: our sole against OpenCap's spheres

Muscle-driven Moco tracking of the squats, twice: our sole (arm A) and OpenCap's six spheres per foot (arm B).
Amendments 4-6 fix the design, validity (convergence, tracking, residuals on body weight) and hypotheses. The
pilot runs on the lab laptop.

The v1 and v2 pilots stopped: arm A never converged. The v2 diagnosis (2026-11-09, models and kinematics only):
arm A's contact is 3-4 times as stiff as arm B's and less damped, and arm B dropped its trunk because its torque
actuators made tracking the trunk costly. Settings v3 changes the solver settings only, for both arms.

Stop rule (Amendment 7, owner, 2026-11-09): if arm A fails the pilot gate under settings v3, stop and report. The
owner then chooses: an amendment to the contact, reporting arm A as not solvable with the assumed contact, or
pausing the dynamic stage until the coupon test ([[sole-coupon-test]]).
