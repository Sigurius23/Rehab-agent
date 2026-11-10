---
type: "step"
title: "Dynamic force-plate check: our sole against OpenCap's spheres"
status: "dropped"
area: "sole"
parent: "[[goal-sole-simulation]]"
depends_on:
  - "[[sole-forceplate-quasistatic]]"
priority: "1"
stop_rule: "arm A fails the pilot gate under settings v3"
stop_by: "2026-11-11"
stop_owner: "owner"
record: "hardware/sensor-sole/VALIDATION_PLAN.md"
source: "hardware/sensor-sole/VALIDATION_PLAN.md stage A item 2, Amendments 4-7 and the v3 pilot's result"
updated: "2026-11-10"
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

**Closed by the stop rule, 2026-11-10: not evaluated, not failed.** The v3 pilot (2026-11-09) failed the gate in both
arms. Arm A did not converge and was never feasible (worst rotation RMS 95.5°, pelvis 576 mm). Arm B converged, with
residuals far inside the limits, but missed the gate on pelvis tilt (10.8° RMS against 5°). No force data was opened.
The owner chose option 2 ([[d-dynamic-check-arm-a]]): arm A is reported as not solvable with the assumed contact,
and the LabValidation dynamic comparison is closed. [[t-dyn-h1]] and [[t-dyn-h2]] are not evaluated. The figures
and the decision's wording are in VALIDATION_PLAN.md, after amendment 7.
