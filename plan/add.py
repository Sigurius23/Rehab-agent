#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors
# SPDX-License-Identifier: MIT
"""Add a note to the plan from the command line, then check the plan and redraw the map. Standard library only.

  python3 plan/add.py idea "Brain regions lighting up with movement" --serves pillar-simulate --area neuro \\
      --link "TRIBE v2 paper=https://arxiv.org/abs/2605.04326" --text "Why it would help."
  python3 plan/add.py step "Record a squat with the sole" --parent goal-sensor-sole --area sole
  python3 plan/add.py test "Every region responds to a press" --parent sole-physical-prototype --area sole \\
      --expected "All 16 regions respond to a 1 kg press"
  python3 plan/add.py decision "Buy the coupon-test film" --blocks sole-coupon-test --area sole

The note's name comes from the title. `--parent`, `--serves`, `--blocks` and `--depends-on` take note names
(the file names in plan/nodes/ without .md). Edit the note afterwards for anything this does not cover.
"""
import argparse
import datetime
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build as B  # noqa: E402

FIRST_STATUS = {"goal": "open", "step": "open", "test": "planned", "idea": "new", "decision": "open"}


def slug(title, kind):
    s = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    s = "-".join(s.split("-")[:7]) or "note"
    return f"idea-{s}" if kind == "idea" and not s.startswith("idea-") else s


def quote(v):
    v = str(v).replace('"', "'")
    return f'"{v}"'


def make(kind, title, area, parent=None, serves=(), blocks=(), depends_on=(), expected=None, question=None,
         text="", links=(), source=None, today=None):
    today = today or datetime.date.today().isoformat()
    fm = [f"type: {quote(kind)}", f"title: {quote(title)}", f"status: {quote(FIRST_STATUS[kind])}",
          f"area: {quote(area)}"]
    if parent:
        fm.append(f'parent: "[[{parent}]]"')
    for key, vals in (("depends_on", depends_on), ("serves", serves), ("blocks", blocks)):
        if vals:
            fm.append(f"{key}:")
            fm += [f'  - "[[{v}]]"' for v in vals]
    if kind == "step":
        fm.append('priority: "2"')
    if expected:
        fm.append(f"expected: {quote(expected)}")
    if kind == "decision":
        fm.append(f"question: {quote(question or title.rstrip('?') + '?')}")
    fm += [f"source: {quote(source or 'owner ' + today)}", f"updated: {quote(today)}"]
    body = [f"# {title}", ""]
    if text:
        body += [text.strip(), ""]
    if links:
        body += ["## Resources", ""]
        for link in links:
            name, _, url = link.partition("=")
            body.append(f"- [{name}]({url})" if url else f"- {name}")
        body.append("")
    return "---\n" + "\n".join(fm) + "\n---\n" + "\n".join(body)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("kind", choices=sorted(FIRST_STATUS))
    ap.add_argument("title")
    ap.add_argument("--area", default="project", choices=B.AREAS)
    ap.add_argument("--parent")
    ap.add_argument("--serves", nargs="*", default=[])
    ap.add_argument("--blocks", nargs="*", default=[])
    ap.add_argument("--depends-on", nargs="*", default=[])
    ap.add_argument("--expected", help="tests: the expected result, written before the test runs")
    ap.add_argument("--question", help="decisions: the question (default: the title)")
    ap.add_argument("--text", default="", help="the note's body")
    ap.add_argument("--link", action="append", default=[], metavar="NAME=URL", help="a resource link (repeatable)")
    ap.add_argument("--source")
    ap.add_argument("--name", help="the note's file name (default: from the title)")
    ap.add_argument("--dir", default=str(HERE), help="the plan folder (default: this script's folder)")
    a = ap.parse_args(argv)
    if a.kind in ("step", "test") and not a.parent:
        ap.error(f"a {a.kind} needs --parent")
    if a.kind == "idea" and not (a.serves or a.parent):
        a.serves = ["rehab-agent"]
    plan = Path(a.dir)
    nid = a.name or slug(a.title, a.kind)
    path = plan / "nodes" / f"{nid}.md"
    if path.exists():
        ap.error(f"{path.name} already exists; choose another --name")
    known = {p.stem for p in (plan / "nodes").glob("*.md")}
    for ref in [a.parent] * bool(a.parent) + a.serves + a.blocks + a.depends_on:
        if ref not in known:
            ap.error(f"no note named {ref!r} in {plan / 'nodes'}")
    path.write_text(make(a.kind, a.title, a.area, a.parent if a.kind != "idea" else None, a.serves, a.blocks,
                         a.depends_on, a.expected, a.question, a.text, a.link, a.source), encoding="utf-8")
    print(f"wrote {path.relative_to(plan.parent)}")
    return B.main(["--dir", str(plan)])


if __name__ == "__main__":
    sys.exit(main())
