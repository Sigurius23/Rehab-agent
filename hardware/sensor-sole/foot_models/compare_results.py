#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors
# SPDX-License-Identifier: CERN-OHL-S-2.0
"""Check a foot-model comparison run against a reference results file, case by case and field by field.
Standard library only (Python 3.8 or later). Experimental simulation, as in FOOT_MODELS.md.

A case is one result row of a summary.json written by foot_models/run_comparison.py: a dict holding 'solved',
under one of the result groups (controlled_cop, posture_based, native_contact, sensitivity, discretisation),
named by its path in the file. Every field of every case is compared exactly, except 'seconds' and
'reused_from_earlier_run', which describe the run rather than its result.

Exit 1 on any changed value, missing case or extra case; each is named. Input hashes, tool versions and code
hashes that differ are reported as information, not as a failure: the rebuilt two-segment model's sha256, for
one, depends on the machine (PROVENANCE.json, two_segment). Exit 2 if a file cannot be read.

  python3 foot_models/compare_results.py ~/rehab-agent-data/sensor-sole/runs/comparison/summary.json
  python3 foot_models/compare_results.py RUN/summary.json --reference other_results.json
"""
import argparse
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_REFERENCE = HERE / "results_2026-11-04.json"
GROUPS = ("controlled_cop", "posture_based", "native_contact", "sensitivity", "discretisation")
IGNORED = ("seconds", "reused_from_earlier_run")
ABSENT = object()                                 # a field present on one side only


def cases(summary):
    """{path (tuple of keys): row} for every result row under the result groups."""
    out = {}

    def walk(node, path):
        if isinstance(node, dict) and "solved" in node:
            out[path] = node
        elif isinstance(node, dict):
            for k, v in node.items():
                walk(v, path + (k,))

    for g in GROUPS:
        walk(summary.get(g, {}), (g,))
    return out


def same(a, b):
    """Equal as JSON values: a bool is not a number, an int equals the float of the same value, NaN equals NaN."""
    if isinstance(a, bool) or isinstance(b, bool):
        return type(a) is type(b) and a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return a == b or (math.isnan(a) and math.isnan(b))
    return type(a) is type(b) and a == b


def differences(ref, run, where=""):
    """(field, reference value, run value) for each difference; nested fields as a.b and a[0]."""
    if isinstance(ref, dict) and isinstance(run, dict):
        for k in list(ref) + [k for k in run if k not in ref]:
            field = f"{where}.{k}" if where else str(k)
            if k not in run:
                yield field, ref[k], ABSENT
            elif k not in ref:
                yield field, ABSENT, run[k]
            else:
                yield from differences(ref[k], run[k], field)
    elif isinstance(ref, list) and isinstance(run, list) and len(ref) == len(run):
        for i, (a, b) in enumerate(zip(ref, run)):
            yield from differences(a, b, f"{where}[{i}]")
    elif not same(ref, run):
        yield where, ref, run


def information(reference, run):
    """Lines on inputs, tool versions and code that differ between the two files. Not failures."""
    lines = []
    ri, ui = reference.get("inputs") or {}, run.get("inputs") or {}
    for k in sorted(set(ri) | set(ui)):
        a, b = (ri.get(k) or {}).get("sha256"), (ui.get(k) or {}).get("sha256")
        if a != b:
            lines.append(f"input {k}: sha256 {a or '(not recorded)'} in the reference, {b or '(not recorded)'} "
                         "in the run")
    for name in ("environment", "code_sha256"):
        r, u = reference.get(name), run.get(name)
        if not (isinstance(r, dict) and isinstance(u, dict)):
            continue                              # the 2026-11-04 file records no code hashes
        for k in sorted(set(r) & set(u)):         # only what both record
            if r[k] != u[k]:
                lines.append(f"{name} {k}: {r[k]} in the reference, {u[k]} in the run")
    return lines


def compare(reference, run):
    """Compare two parsed summaries. Returns a dict: compared, matched, changed {case: [(field, ref, run)]},
    missing [case], extra [case], information [line]."""
    R, S = cases(reference), cases(run)
    changed = {}
    for path in (p for p in R if p in S):
        strip = lambda row: {k: v for k, v in row.items() if k not in IGNORED}
        d = list(differences(strip(R[path]), strip(S[path])))
        if d:
            changed[path] = d
    compared = sum(p in S for p in R)
    return dict(reference_cases=len(R), run_cases=len(S), compared=compared, matched=compared - len(changed),
                changed=changed, missing=[p for p in R if p not in S], extra=[p for p in S if p not in R],
                information=information(reference, run))


def show(v):
    if v is ABSENT:
        return "(absent)"
    s = json.dumps(v)
    return s if len(s) <= 120 else s[:117] + "..."


def name(path):
    return " / ".join(path)


def report(res, reference_path, run_path, out=None):
    p = lambda *a: print(*a, file=out or sys.stdout)   # sys.stdout looked up now, so redirection works
    p(f"reference: {reference_path} ({res['reference_cases']} cases)")
    p(f"run:       {run_path} ({res['run_cases']} cases)")
    if res["information"]:
        p("information, not a failure:")
        for line in res["information"]:
            p(f"  {line}")
    for path, diffs in res["changed"].items():
        p(f"CHANGED: {name(path)}")
        for field, a, b in diffs:
            p(f"    {field}: {show(a)} in the reference, {show(b)} in the run")
    for path in res["missing"]:
        p(f"MISSING from the run: {name(path)}")
    for path in res["extra"]:
        p(f"EXTRA in the run: {name(path)}")
    n_changed, n_missing, n_extra = len(res["changed"]), len(res["missing"]), len(res["extra"])
    p(f"compared {res['compared']} cases: {res['matched']} match, {n_changed} changed; "
      f"{n_missing} missing, {n_extra} extra (ignoring {', '.join(IGNORED)})")
    ok = not (n_changed or n_missing or n_extra)
    p("OK: every case matches the reference" if ok else
      f"FAIL: {n_changed} changed, {n_missing} missing, {n_extra} extra")
    return ok


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("summary", help="the run's summary.json")
    ap.add_argument("--reference", default=str(DEFAULT_REFERENCE),
                    help="results file to compare with (default: foot_models/results_2026-11-04.json)")
    a = ap.parse_args(argv)
    try:
        reference = json.loads(Path(a.reference).read_text())
        run = json.loads(Path(a.summary).read_text())
    except (OSError, ValueError) as e:
        print(f"compare_results: cannot read the files: {e}", file=sys.stderr)
        return 2
    return 0 if report(compare(reference, run), a.reference, a.summary) else 1


if __name__ == "__main__":
    sys.exit(main())
