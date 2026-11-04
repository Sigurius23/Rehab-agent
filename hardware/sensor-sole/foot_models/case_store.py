#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors
# SPDX-License-Identifier: CERN-OHL-S-2.0
"""Resumable case folders for long batches (foot_models/run_comparison.py). Standard library only.

Each case runs in its own folder, named from a fingerprint of everything that can change its result: the
inputs' sha256, the parameters, the code's sha256 and the tool versions. A case counts as done only when its
completion record (`case.json`) exists, holds the same full fingerprint, and its result file reads back. The record
is written last and atomically, so a run stopped at any point (laptop closed, process killed) leaves that case
not done, and the next run repeats it. Anything else in the folder is cleared before a case is repeated.

A result is reused only for the exact fingerprint. Changing an input, a parameter, the code or the OpenSim version
gives a new folder; nothing is reused across such a change.
"""
import hashlib
import json
import os
import shutil
import time
from pathlib import Path

RECORD = "case.json"


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def fingerprint(key):
    """sha256 of the key as canonical JSON (sorted keys; floats as JSON writes them)."""
    return hashlib.sha256(json.dumps(key, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _write_atomic(path, text):
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(text)
    os.replace(tmp, path)


class CaseStore:
    def __init__(self, root, resume=True):
        self.root = Path(root)
        self.resume = resume

    def folder(self, group, key):
        return self.root / group / fingerprint(key)[:16]

    def done(self, group, key, result_name="result.json"):
        """The stored result and its completion record if this exact case finished before, else None."""
        d = self.folder(group, key)
        try:
            rec = json.loads((d / RECORD).read_text())
            if rec.get("fingerprint") != fingerprint(key):
                return None
            return json.loads((d / result_name).read_text()), rec
        except (OSError, ValueError):
            return None

    def run(self, group, key, fn, result_name="result.json"):
        """fn(folder) must write folder/result_name. Returns (result, record, reused)."""
        if self.resume:
            hit = self.done(group, key, result_name)
            if hit:
                return hit[0], hit[1], True
        d = self.folder(group, key)
        if d.exists():
            shutil.rmtree(d)                     # an interrupted or superseded attempt
        d.mkdir(parents=True)
        t0 = time.time()
        fn(d)
        result = json.loads((d / result_name).read_text())
        rec = dict(fingerprint=fingerprint(key), key=key, seconds=round(time.time() - t0, 1),
                   finished=time.strftime("%Y-%m-%dT%H:%M:%S%z"))
        _write_atomic(d / RECORD, json.dumps(rec, indent=1, sort_keys=True) + "\n")
        return result, rec, False
