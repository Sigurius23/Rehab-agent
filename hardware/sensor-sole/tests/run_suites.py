#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors
# SPDX-License-Identifier: CERN-OHL-S-2.0
"""Run test modules under the current interpreter and print, as JSON, what actually ran: each test's outcome
(ok, skipped with its reason, expected failure, failure, error). Used to write TEST_RUNS.md.

  python tests/run_suites.py test_sim_osim test_dhondt_port
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


class Recorder(unittest.TextTestResult):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.rows = []

    def addSuccess(self, t):
        super().addSuccess(t); self.rows.append((t.id(), "ok", ""))

    def addSkip(self, t, reason):
        super().addSkip(t, reason); self.rows.append((t.id(), "skipped", reason))

    def addExpectedFailure(self, t, err):
        super().addExpectedFailure(t, err); self.rows.append((t.id(), "expected failure", ""))

    def addUnexpectedSuccess(self, t):
        super().addUnexpectedSuccess(t); self.rows.append((t.id(), "UNEXPECTED SUCCESS", ""))

    def addFailure(self, t, err):
        super().addFailure(t, err); self.rows.append((t.id(), "FAIL", str(err[1])[:200]))

    def addError(self, t, err):
        super().addError(t, err); self.rows.append((t.id(), "ERROR", str(err[1])[:200]))


def main():
    out = {}
    for name in sys.argv[1:]:
        suite = unittest.defaultTestLoader.loadTestsFromName(name)
        runner = unittest.TextTestRunner(stream=open("/dev/null", "w"), resultclass=Recorder)
        res = runner.run(suite)
        # a module with no unittest cases (a script-style check) must not read as a clean pass
        out[name] = res.rows or [(name, "ERROR", "no unittest tests found: run it as a script and use its exit code")]
    print(json.dumps(out))


if __name__ == "__main__":
    main()
