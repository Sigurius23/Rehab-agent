#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors
# SPDX-License-Identifier: CERN-OHL-S-2.0
"""Checks of foot_models/case_store.py, the resumable case folders. Standard library only.

  - a finished case is reused, and only for the exact same fingerprint;
  - a case stopped before its completion record (laptop closed, process killed, an error) is repeated, and what
    the stopped attempt left in the folder is cleared first;
  - a damaged or mismatched record or result is not trusted;
  - --no-resume (resume=False) repeats finished cases;
  - cases run in separate processes at once land in their own folders.
"""
import json
import sys
import tempfile
import unittest
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import get_context
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "foot_models"))
import case_store as CS  # noqa: E402

KEY = dict(label="a", cop_target=0.45, model_sha256="0" * 64, contact=None)


def writer(value, calls=None, extra=None):
    def fn(d):
        if calls is not None:
            calls.append(d)
        (d / "result.json").write_text(json.dumps(dict(value=value)))
        if extra:
            (d / extra).write_text("x")
    return fn


def _in_worker(args):
    root, n = args
    r, rec, reused = CS.CaseStore(root).run("g", dict(KEY, label=f"case {n}"), writer(n))
    return r["value"], reused


class Store(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.store = CS.CaseStore(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_finished_case_is_reused(self):
        calls = []
        r1, rec1, reused1 = self.store.run("g", KEY, writer(1, calls))
        r2, rec2, reused2 = self.store.run("g", dict(KEY), writer(2, calls))
        self.assertEqual((r1, reused1, reused2, len(calls)), (dict(value=1), False, True, 1))
        self.assertEqual(r2, r1)
        self.assertEqual(rec2["fingerprint"], CS.fingerprint(KEY))
        self.assertEqual(rec2["key"], KEY)

    def test_any_change_in_the_key_runs_again_in_a_new_folder(self):
        self.store.run("g", KEY, writer(1))
        for change in (dict(cop_target=0.6), dict(model_sha256="1" * 64), dict(contact=dict(name="assumed")),
                       dict(code_sha256={"x.py": "f"})):
            with self.subTest(change=change):
                k = dict(KEY, **change)
                r, _, reused = self.store.run("g", k, writer(2))
                self.assertFalse(reused)
                self.assertNotEqual(self.store.folder("g", k), self.store.folder("g", KEY))
        self.assertEqual(self.store.run("g", KEY, writer(3))[0], dict(value=1))   # the original is untouched

    def test_same_key_in_another_group_is_another_case(self):
        self.store.run("g", KEY, writer(1))
        self.assertFalse(self.store.run("h", KEY, writer(2))[2])

    def test_interrupted_case_is_repeated_and_its_folder_cleared(self):
        def stopped(d):
            (d / "result.json").write_text(json.dumps(dict(value="partial")))
            (d / "half_written.osim").write_text("x")
            raise KeyboardInterrupt
        with self.assertRaises(KeyboardInterrupt):
            self.store.run("g", KEY, stopped)
        d = self.store.folder("g", KEY)
        self.assertFalse((d / CS.RECORD).exists())
        self.assertIsNone(self.store.done("g", KEY))
        r, _, reused = self.store.run("g", KEY, writer(1))
        self.assertEqual((r, reused), (dict(value=1), False))
        self.assertFalse((d / "half_written.osim").exists())

    def test_failing_case_leaves_no_record(self):
        def fails(d):
            raise RuntimeError("solver failed")
        with self.assertRaises(RuntimeError):
            self.store.run("g", KEY, fails)
        self.assertIsNone(self.store.done("g", KEY))

    def test_case_without_a_result_file_is_not_recorded(self):
        with self.assertRaises(FileNotFoundError):
            self.store.run("g", KEY, lambda d: None)
        self.assertIsNone(self.store.done("g", KEY))

    def test_damaged_record_or_result_is_not_trusted(self):
        for damage in ("record", "result", "fingerprint", "no result"):
            with self.subTest(damage=damage):
                self.store.run("g", KEY, writer(1))
                d = self.store.folder("g", KEY)
                if damage == "record":
                    (d / CS.RECORD).write_text("{trunc")
                elif damage == "result":
                    (d / "result.json").write_text("{trunc")
                elif damage == "fingerprint":
                    rec = json.loads((d / CS.RECORD).read_text()); rec["fingerprint"] = "0" * 64
                    (d / CS.RECORD).write_text(json.dumps(rec))
                else:
                    (d / "result.json").unlink()
                r, _, reused = self.store.run("g", KEY, writer(2))
                self.assertEqual((r, reused), (dict(value=2), False))
                CS.CaseStore(self.root, resume=False).run("g", KEY, writer(1))   # reset for the next subtest

    def test_no_resume_repeats_finished_cases(self):
        self.store.run("g", KEY, writer(1))
        r, _, reused = CS.CaseStore(self.root, resume=False).run("g", KEY, writer(2))
        self.assertEqual((r, reused), (dict(value=2), False))

    def test_record_is_written_last(self):
        seen = {}
        def fn(d):
            seen["record_before_result"] = (d / CS.RECORD).exists()
            (d / "result.json").write_text("{}")
        self.store.run("g", KEY, fn)
        self.assertFalse(seen["record_before_result"])
        self.assertEqual([p.name for p in self.store.folder("g", KEY).iterdir() if p.name.endswith(".tmp")], [])

    def test_fingerprint_is_canonical(self):
        self.assertEqual(CS.fingerprint(dict(a=1, b=[1, 2])), CS.fingerprint(dict(b=[1, 2], a=1)))
        self.assertNotEqual(CS.fingerprint(dict(a=1.0)), CS.fingerprint(dict(a=1.0000001)))

    def test_parallel_workers_use_their_own_folders(self):
        with ProcessPoolExecutor(max_workers=3, mp_context=get_context("spawn")) as pool:
            first = list(pool.map(_in_worker, [(str(self.root), n) for n in range(6)]))
            again = list(pool.map(_in_worker, [(str(self.root), n) for n in range(6)]))
        self.assertEqual(first, [(n, False) for n in range(6)])
        self.assertEqual(again, [(n, True) for n in range(6)])
        self.assertEqual(len(list((self.root / "g").iterdir())), 6)


if __name__ == "__main__":
    unittest.main(verbosity=2)
