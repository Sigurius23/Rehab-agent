#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors
# SPDX-License-Identifier: CERN-OHL-S-2.0
"""Checks of foot_models/compare_results.py, the results checker. Standard library only.

Negative controls on copies of the committed results file (foot_models/results_2026-11-04.json), run through
the command line as run_comparison.sh runs it:
  - the file against itself passes, with every case compared;
  - one changed value fails, and names the case and the field;
  - a missing case fails and names it; an extra case fails and names it;
  - only 'seconds' (and 'reused_from_earlier_run') differing passes;
  - a different input hash (as the rebuilt two-segment model's) is reported as information and passes;
  - true is not 1, and a field present on one side only is a change.
"""
import contextlib
import copy
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "foot_models"))
import compare_results as CR  # noqa: E402

REFERENCE = json.loads(CR.DEFAULT_REFERENCE.read_text())


def at(tree, path):
    for k in path:
        tree = tree[k]
    return tree


class Checker(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.run_tree = copy.deepcopy(REFERENCE)
        self.first = next(iter(CR.cases(self.run_tree)))     # path of one case

    def check(self, run_tree):
        """Run the checker's command line on run_tree against the committed file: (exit code, output)."""
        p = Path(self.tmp.name) / "summary.json"
        p.write_text(json.dumps(run_tree))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = CR.main([str(p)])
        return code, out.getvalue()

    def test_reference_against_itself_passes(self):
        code, out = self.check(self.run_tree)
        self.assertEqual(code, 0, out)
        self.assertEqual(len(CR.cases(REFERENCE)), 244)
        self.assertIn("compared 244 cases: 244 match, 0 changed; 0 missing, 0 extra", out)

    def test_one_changed_value_fails_and_is_named(self):
        row = at(self.run_tree, self.first)
        row["heel_pct"] = row["heel_pct"] + 0.01
        code, out = self.check(self.run_tree)
        self.assertEqual(code, 1, out)
        self.assertIn(f"CHANGED: {CR.name(self.first)}", out)
        self.assertIn("    heel_pct: ", out)
        self.assertIn("243 match, 1 changed; 0 missing, 0 extra", out)

    def test_a_changed_nested_value_is_named_by_its_field(self):
        at(self.run_tree, self.first)["cop_sole_mm"][1] += 0.1
        code, out = self.check(self.run_tree)
        self.assertEqual(code, 1, out)
        self.assertIn("    cop_sole_mm[1]: ", out)

    def test_a_missing_case_fails_and_is_named(self):
        del at(self.run_tree, self.first[:-1])[self.first[-1]]
        code, out = self.check(self.run_tree)
        self.assertEqual(code, 1, out)
        self.assertIn(f"MISSING from the run: {CR.name(self.first)}", out)
        self.assertIn("compared 243 cases: 243 match, 0 changed; 1 missing, 0 extra", out)

    def test_an_extra_case_fails_and_is_named(self):
        parent = at(self.run_tree, self.first[:-1])
        parent["0.90"] = copy.deepcopy(parent[self.first[-1]])
        code, out = self.check(self.run_tree)
        self.assertEqual(code, 1, out)
        self.assertIn(f"EXTRA in the run: {CR.name(self.first[:-1] + ('0.90',))}", out)
        self.assertIn("244 match, 0 changed; 0 missing, 1 extra", out)

    def test_only_seconds_and_reuse_differing_passes(self):
        for row in CR.cases(self.run_tree).values():
            row["seconds"] = row["seconds"] + 100.0
            row["reused_from_earlier_run"] = True
        code, out = self.check(self.run_tree)
        self.assertEqual(code, 0, out)
        self.assertIn("compared 244 cases: 244 match", out)

    def test_a_different_input_hash_is_information_not_a_failure(self):
        self.run_tree["inputs"]["selftest"]["sha256"] = "e" * 64
        code, out = self.check(self.run_tree)
        self.assertEqual(code, 0, out)
        self.assertIn("information, not a failure:", out)
        self.assertIn(f"input selftest: sha256 {REFERENCE['inputs']['selftest']['sha256']} in the reference, "
                      f"{'e' * 64} in the run", out)

    def test_true_is_not_one_and_one_sided_fields_are_changes(self):
        row = at(self.run_tree, self.first)
        row["solved"] = 1
        row["new_field"] = 0
        del row["foot_N"]
        res = CR.compare(REFERENCE, self.run_tree)
        fields = {f for f, _, _ in res["changed"][self.first]}
        self.assertEqual(fields, {"solved", "new_field", "foot_N"})

    def test_an_unreadable_file_is_exit_2(self):
        out = io.StringIO()
        with contextlib.redirect_stderr(out):
            self.assertEqual(CR.main([str(Path(self.tmp.name) / "absent.json")]), 2)


if __name__ == "__main__":
    unittest.main()
