---
type: "step"
title: "CI runs every test suite that needs no external files"
status: "doing"
area: "project"
parent: "[[goal-working-method]]"
priority: "2"
source: "hardware/sensor-sole/TEST_RUNS.md"
updated: "2026-11-09"
---
# CI runs every test suite that needs no external files

CI (`.github/workflows/validate.yml`) runs only `test_channel_map.py` (`hardware/sensor-sole/TEST_RUNS.md`).
Several suites need nothing external and could run on every push, with this map's check.

**2026-11-09:** a CI job `plan-and-sole` (`.github/workflows/validate.yml`): the plan's check, its tests and an
up-to-date map, and five sensor-sole suites (`test_channel_map`, `test_case_store`, `test_compare_results`,
`test_forceplate_metrics`, `test_static_ik`; 47 cases, none skipped on this machine). Python 3.13 with numpy 2.5.4.
`plan/test_build.py` did not run on Python 3.11 (an f-string with a backslash); fixed.
