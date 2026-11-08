---
type: "step"
title: "CI runs every test suite that needs no external files"
status: "open"
area: "project"
parent: "[[rehab-agent]]"
priority: "2"
source: "hardware/sensor-sole/TEST_RUNS.md"
updated: "2026-11-08"
---
# CI runs every test suite that needs no external files

CI (`.github/workflows/validate.yml`) runs only `test_channel_map.py` (`hardware/sensor-sole/TEST_RUNS.md`).
Several suites need nothing external and could run on every push, with this map's check.
