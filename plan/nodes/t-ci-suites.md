---
type: "test"
title: "CI runs the standard-library suites and the plan check"
status: "passed"
area: "project"
parent: "[[project-ci-suites]]"
expected: "On every push, CI runs test_channel_map, test_case_store, test_compare_results, plan/test_build and plan/build.py --check, and all pass"
result: "GitHub Actions run 42722409612 on fa5c7b2, job plan-and-sole: plan check 0 errors, 14 plan tests OK, map up to date, the five sole suites 47 cases OK with none skipped"
fresh: "n/a"
record: ".github/workflows/validate.yml"
updated: "2026-11-09"
---
# CI runs the standard-library suites and the plan check
