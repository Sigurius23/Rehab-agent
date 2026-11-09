#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors
# SPDX-License-Identifier: MIT
"""Check the plan's notes and draw the map. Standard library only.

The plan is one Markdown note per node in plan/nodes/ (an Obsidian vault when plan/ is opened as one). Each note
starts with front matter between two `---` lines:

    type: goal | step | test | idea | decision
    title: one line
    status: (by type, see STATUS below)
    area: project | pipeline | person-model | cues | suit | sole | forces | assistance | catalog | neuro |
          nutrition
    parent: "[[note]]"                  goals (except the root), steps and tests
    depends_on:                         steps: steps that must be done first
      - "[[note]]"
    priority: 1 | 2 | 3                 steps; default 2. Priority 1 needs a stop rule
    stop_rule: a condition with a number   stop_by: YYYY-MM-DD   stop_owner: who decides
    expected: what should happen        tests: written before the test runs
    result: what happened               tests: when passed, failed or mixed
    fresh: yes | no | n/a               tests: were the data or people unseen while the thing was built?
    record: repo path                   tests and steps: where the evidence is
    serves: ["[[note]]"]                ideas: what they would help
    question / options / blocks / decided / recorded_in      decisions
    source: where the item came from (file and section)
    order: 1, 2, ...                    the root goal's children: their order in the map

Only a small YAML subset is read: `key: value`, `key: [a, b]` and block lists (`  - item`).

Writes plan/MAP.md (Mermaid diagram and lists) and plan/map.canvas (JSON Canvas, for Obsidian). Never edit those
two by hand. Exit code 1 when the plan has errors, so it can gate a commit.

  python3 plan/build.py            check and write
  python3 plan/build.py --check    check only
"""
import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
TYPES = ("goal", "step", "test", "idea", "decision")
STATUS = {
    "goal": ("open", "done"),
    "step": ("open", "doing", "done", "blocked", "dropped"),
    "test": ("planned", "running", "passed", "failed", "mixed", "dropped"),
    "idea": ("new", "promoted", "dropped"),
    "decision": ("open", "decided"),
}
AREAS = ("project", "pipeline", "person-model", "cues", "suit", "sole", "forces", "assistance", "catalog", "neuro",
         "nutrition")
PARENT_TYPES = {"goal": ("goal",), "step": ("goal", "step"), "test": ("step", "goal")}
FINISHED_TESTS = ("passed", "failed", "mixed")
LINK = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")
NUMBER = re.compile(r"\d")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def parse_note(path):
    """(front matter dict, body). Raises ValueError on malformed front matter."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError("no front matter")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise ValueError("front matter not closed")
    meta, key = {}, None
    for n, line in enumerate(text[4:end].splitlines(), 2):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith((" ", "\t")) and line.strip().startswith("- "):
            if key is None or not isinstance(meta.get(key), list):
                raise ValueError(f"line {n}: list item without a list key")
            meta[key].append(_scalar(line.strip()[2:]))
            continue
        m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if not m:
            raise ValueError(f"line {n}: not `key: value`")
        key, value = m.group(1), m.group(2).strip()
        if value == "":
            meta[key] = []
        elif value.startswith("[") and value.endswith("]") and not value.startswith("[["):
            inner = value[1:-1].strip()
            meta[key] = [_scalar(v) for v in _split_inline(inner)] if inner else []
        else:
            meta[key] = _scalar(value)
    return meta, text[end + 5:]


def _split_inline(s):
    out, depth, cur = [], 0, ""
    for ch in s:
        depth += ch == "[" or -(ch == "]")
        if ch == "," and depth == 0:
            out.append(cur); cur = ""
        else:
            cur += ch
    out.append(cur)
    return [v.strip() for v in out]


def _scalar(v):
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        v = v[1:-1]
    return v


def links(value):
    vals = value if isinstance(value, list) else ([value] if value else [])
    out = []
    for v in vals:
        found = LINK.findall(str(v))
        out.extend(f.strip() for f in found) if found else out.append(str(v).strip())
    return [o for o in out if o]


def load(nodes_dir):
    nodes, errors = {}, []
    for p in sorted(Path(nodes_dir).glob("*.md")):
        try:
            meta, body = parse_note(p)
        except ValueError as e:
            errors.append(f"{p.name}: {e}")
            continue
        nodes[p.stem] = dict(meta=meta, body=body, path=p)
    return nodes, errors


def check(nodes, repo_root):
    errs, warns = [], []
    children = defaultdict(list)
    for nid, n in nodes.items():
        m = n["meta"]
        t = m.get("type")
        if t not in TYPES:
            errs.append(f"{nid}: type {t!r} is not one of {', '.join(TYPES)}"); continue
        if not m.get("title"):
            errs.append(f"{nid}: no title")
        if m.get("status") not in STATUS[t]:
            errs.append(f"{nid}: status {m.get('status')!r} for a {t} must be one of {', '.join(STATUS[t])}")
        if m.get("area") not in AREAS:
            errs.append(f"{nid}: area {m.get('area')!r} is not one of {', '.join(AREAS)}")
        for field in ("parent", "depends_on", "serves", "blocks", "promoted_to"):
            for target in links(m.get(field)):
                if target not in nodes:
                    errs.append(f"{nid}: {field} points at unknown note {target!r}")
        for target in LINK.findall(n["body"]):
            if target.strip() not in nodes:
                warns.append(f"{nid}: body links to unknown note {target.strip()!r}")
        par = links(m.get("parent"))
        if len(par) > 1:
            errs.append(f"{nid}: more than one parent")
        if par and par[0] in nodes:
            ptype = nodes[par[0]]["meta"].get("type")
            if t in PARENT_TYPES and ptype not in PARENT_TYPES[t]:
                errs.append(f"{nid}: a {t} cannot have a {ptype} as parent")
            children[par[0]].append(nid)
        if t in ("step", "test") and not par:
            errs.append(f"{nid}: a {t} needs a parent")
        for d in links(m.get("depends_on")):
            if d in nodes and nodes[d]["meta"].get("type") != "step":
                errs.append(f"{nid}: depends_on {d!r} is a {nodes[d]['meta'].get('type')}; dependencies are steps")
        rec = m.get("record")
        if rec and not (repo_root / rec).exists():
            warns.append(f"{nid}: record {rec!r} does not exist in the repository")
    roots = [i for i, n in nodes.items() if n["meta"].get("type") == "goal" and not links(n["meta"].get("parent"))]
    if len(roots) != 1:
        errs.append(f"exactly one root goal (a goal without parent) is needed; found {len(roots)}: {roots}")
    # cycles: parent chains and dependencies
    for nid in nodes:
        seen, cur = set(), nid
        while True:
            par = links(nodes[cur]["meta"].get("parent"))
            if not par or par[0] not in nodes:
                break
            if par[0] in seen or par[0] == nid:
                errs.append(f"{nid}: parent chain loops"); break
            seen.add(par[0]); cur = par[0]
    state = {}
    def visit(nid, stack):
        if state.get(nid) == 1:
            errs.append(f"dependency cycle: {' -> '.join(stack + [nid])}"); return
        if state.get(nid) == 2:
            return
        state[nid] = 1
        for d in links(nodes[nid]["meta"].get("depends_on")):
            if d in nodes:
                visit(d, stack + [nid])
        state[nid] = 2
    for nid in nodes:
        visit(nid, [])
    needs = []
    for nid, n in nodes.items():
        m, t, s = n["meta"], n["meta"].get("type"), n["meta"].get("status")
        if t == "step":
            tests = [c for c in children[nid] if nodes[c]["meta"].get("type") == "test"]
            if s in ("open", "doing") and not tests:
                warns.append(f"{nid}: open step with no test: how will you know it worked?")
            if s == "done" and not any(nodes[c]["meta"].get("status") in FINISHED_TESTS for c in tests) \
                    and not m.get("record"):
                warns.append(f"{nid}: done, but no finished test and no record")
            if str(m.get("priority", "2")) not in ("1", "2", "3"):
                errs.append(f"{nid}: priority must be 1, 2 or 3")
            if str(m.get("priority", "2")) == "1" and s in ("open", "doing", "blocked"):
                rule = str(m.get("stop_rule") or "")
                if not rule:
                    needs.append(f"{nid}: priority-1 step needs a stop rule (a number, a date, an owner)")
                elif rule.startswith("none:"):
                    if len(rule) < 35:
                        errs.append(f"{nid}: a waived stop rule needs a reason of at least 30 characters")
                else:
                    if not NUMBER.search(rule):
                        errs.append(f"{nid}: stop_rule has no number in it")
                    if not DATE.match(str(m.get("stop_by") or "")):
                        errs.append(f"{nid}: stop_by must be a date, YYYY-MM-DD")
                    if not m.get("stop_owner"):
                        errs.append(f"{nid}: stop_owner is missing")
        if t == "test":
            if not m.get("expected"):
                (errs if s in FINISHED_TESTS else needs).append(
                    f"{nid}: no expected result" + (" (required once the test has run)" if s in FINISHED_TESTS
                                                    else ": write it before the test runs"))
            if s in FINISHED_TESTS:
                if not m.get("result"):
                    errs.append(f"{nid}: {s}, but no result")
                if m.get("fresh") not in ("yes", "no", "n/a"):
                    errs.append(f"{nid}: {s}, but fresh is not yes, no or n/a")
        if t == "idea" and s == "promoted" and not links(m.get("promoted_to")):
            errs.append(f"{nid}: promoted, but promoted_to is empty")
        if t == "decision":
            if not m.get("question"):
                errs.append(f"{nid}: a decision needs a question")
            if s == "decided" and not m.get("decided"):
                errs.append(f"{nid}: decided, but `decided` is empty")
            if s == "open":
                needs.append(f"{nid}: open decision: {m.get('question', '')}")
    return errs, warns, needs, children, roots


def inbox(plan_dir):
    """Unsorted ideas: the `- ` lines under the inbox's `## Inbox` heading."""
    p = Path(plan_dir) / "inbox.md"
    if not p.exists():
        return []
    items, on = [], False
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            on = line.strip().lower() == "## inbox"
        elif on and line.startswith("- ") and line[2:].strip():
            items.append(line[2:].strip())
    return items


def ready(nodes):
    """Open steps whose dependencies are all done and that no open decision blocks."""
    blocked = {b for n in nodes.values() if n["meta"].get("type") == "decision" and n["meta"].get("status") == "open"
               for b in links(n["meta"].get("blocks"))}
    out = []
    for nid, n in sorted(nodes.items()):
        m = n["meta"]
        if m.get("type") == "step" and m.get("status") == "open" and nid not in blocked and all(
                nodes[d]["meta"].get("status") == "done" for d in links(m.get("depends_on")) if d in nodes):
            out.append(nid)
    return out


def _label(s, width=34):
    """Mermaid-safe text, wrapped at word boundaries with <br/>."""
    words, lines, cur = str(s).replace('"', "#quot;").replace("[", "(").replace("]", ")").split(), [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > width:
            lines.append(cur); cur = w
        else:
            cur = f"{cur} {w}".strip()
    return "<br/>".join(lines + [cur] if cur else lines)


def _test_tally(nid, nodes, children):
    marks = {"passed": "✓", "failed": "✗", "mixed": "±", "planned": "○", "running": "▶"}
    count = defaultdict(int)
    for c in children.get(nid, []):
        if nodes[c]["meta"].get("type") == "test":
            count[nodes[c]["meta"].get("status")] += 1
    return " ".join(f"{marks[s]}{count[s]}" for s in marks if count[s])


def _pillar(nid, nodes, root):
    """The child of the root goal this note sits under (via parents, or what it serves or blocks), else None."""
    seen, cur = set(), nid
    while cur and cur not in seen:
        seen.add(cur)
        m = nodes[cur]["meta"]
        par = links(m.get("parent"))
        if par and par[0] == root:
            return cur
        nxt = par or links(m.get("serves")) or links(m.get("blocks"))
        cur = nxt[0] if nxt and nxt[0] in nodes else None
    return None


def _classdefs():
    colours = {"done": "#c8e6c9", "passed": "#c8e6c9", "failed": "#ffcdd2", "mixed": "#fff3c4",
               "doing": "#fff3c4", "running": "#fff3c4", "blocked": "#ffe0b2", "dropped": "#eeeeee",
               "promoted": "#eeeeee"}
    lines = []
    for t in TYPES:
        for s in STATUS[t]:
            fill = colours.get(s, {"goal": "#e1d5f5", "idea": "#d7f0f7", "decision": "#ffe0b2"}.get(t, "#ffffff"))
            dash = ",stroke-dasharray: 4 3" if t == "idea" else ""
            lines.append(f"  classDef {t}_{s} fill:{fill},stroke:#555,color:#111{dash}")
    lines.append("  classDef external fill:#f5f5f5,stroke:#aaa,color:#777,stroke-dasharray: 2 2")
    return lines


def pillars(nodes, roots):
    """The root's child goals in their `order`, and every shown note grouped under its pillar."""
    root = roots[0] if len(roots) == 1 else None
    def rank(p):
        o = str(nodes[p]["meta"].get("order", ""))
        return (int(o) if o.isdigit() else 999, p)
    top = sorted((c for c, n in nodes.items() if links(n["meta"].get("parent")) == [root]
                  and n["meta"].get("type") == "goal"), key=rank) if root else []
    shown = {nid for nid, n in nodes.items() if n["meta"].get("type") in ("goal", "step")
             or (n["meta"].get("type") == "idea" and n["meta"].get("status") == "new")}
    shown |= {nid for nid, n in nodes.items() if n["meta"].get("type") == "decision"
              and any(b in shown for b in links(n["meta"].get("blocks")))}
    groups = defaultdict(list)
    for nid in sorted(shown - {root}):
        groups[_pillar(nid, nodes, root)].append(nid)
    return root, top, groups


def mermaid_engine(nodes, children, roots):
    """The end goal and its pillars, each with a tally of the work under it."""
    root, top, groups = pillars(nodes, roots)
    if not root:
        return "flowchart TB\n  none[No single root goal]"
    lines = ["flowchart TB", f'  r(["{_label(nodes[root]["meta"].get("title", root), 40)}"]):::goal_open']
    for k, p in enumerate(top):
        count = defaultdict(int)
        for nid in groups.get(p, []):
            m = nodes[nid]["meta"]
            t, st = m.get("type"), m.get("status")
            if t == "step":
                count[st] += 1
            elif t in ("idea", "decision"):
                count[t + "s"] += 1
        word = lambda x, n: x[:-1] if x.endswith("s") and n == 1 else x
        tally = " · ".join(f"{count[x]} {word(x, count[x])}" for x in
                           ("done", "doing", "open", "blocked", "ideas", "decisions") if count[x])
        lines.append(f'  p{k}(["{_label(nodes[p]["meta"].get("title", p), 30)}<br/><i>{tally}</i>"]):::goal_open')
        lines.append(f"  r --> p{k}")
    return "\n".join(lines + _classdefs())


def mermaid_pillar(nodes, children, roots, pillar):
    """One pillar: its goals, steps (with a tally of their tests), open ideas and blocking decisions. Notes from other
    pillars that link to it are drawn faded, so no connection is lost."""
    root, top, groups = pillars(nodes, roots)
    members = groups.get(pillar, [])
    member_set = set(members)
    edges, external = [], []
    for nid in members:
        m = nodes[nid]["meta"]
        for p in links(m.get("parent")):
            if p in member_set:
                edges.append((p, nid, "-->", ""))
        for d in links(m.get("depends_on")):
            edges.append((d, nid, "-.->", "needed by"))
        for b in links(m.get("blocks")):
            edges.append((nid, b, "-.->", "blocks"))
        for s_ in links(m.get("serves")):
            edges.append((nid, s_, "-.-o", ""))
    for nid, n in nodes.items():                      # links from other pillars into this one
        if nid in member_set:
            continue
        m = n["meta"]
        for d in links(m.get("depends_on")):
            if d in member_set:
                edges.append((d, nid, "-.->", "needed by"))
        for b in links(m.get("blocks")):
            if b in member_set and m.get("type") == "decision":
                edges.append((nid, b, "-.->", "blocks"))
    for a, b_, _, _ in edges:
        for x in (a, b_):
            if x in nodes and x not in member_set and x not in external and x != root:
                external.append(x)
    shown = members + external
    ids = {nid: f"n{i}" for i, nid in enumerate(shown)}
    lines = ["flowchart LR"]
    for nid in shown:
        m = nodes[nid]["meta"]
        t, st = m.get("type"), m.get("status")
        text = _label(m.get("title", nid)) if t != "decision" else _label(f"{nid}: {m.get('question', '')}", 30)
        tally = _test_tally(nid, nodes, children) if t == "step" else ""
        if tally:
            text += f"<br/>tests {tally}"
        if nid in external:
            owner = _pillar(nid, nodes, root)
            text += "<br/><i>(" + _label(str(nodes[owner]["meta"].get("title", "")).split(":")[0] if owner else "elsewhere") + ")</i>"
        shape = {"goal": ('(["', '"])'), "decision": ('{{"', '"}}'), "idea": ('>"', '"]')}.get(t, ('["', '"]'))
        cls = "external" if nid in external else f"{t}_{st}"
        lines.append(f'  {ids[nid]}{shape[0]}{text}{shape[1]}:::{cls}')
    seen = set()
    for a, b_, arrow, label in edges:
        if a in ids and b_ in ids and (a, b_, arrow) not in seen:
            seen.add((a, b_, arrow))
            link = f"-. {label} .->" if label else arrow
            lines.append(f"  {ids[a]} {link} {ids[b_]}")
    return "\n".join(lines + _classdefs())


def canvas(nodes, children, roots):
    """JSON Canvas (jsoncanvas.org): the tree from the root, then rows for loose ideas and decisions."""
    W, H, DX, DY = 280, 120, 320, 220
    pos, slot = {}, [0]
    def place(nid, depth):
        kids = sorted(children.get(nid, []), key=lambda c: (nodes[c]["meta"].get("type") == "test", c))
        if not kids:
            pos[nid] = (slot[0] * DX, depth * DY); slot[0] += 1; return
        for k in kids:
            place(k, depth + 1)
        xs = [pos[k][0] for k in kids]
        pos[nid] = ((min(xs) + max(xs)) / 2, depth * DY)
    for r in roots:
        place(r, 0)
    maxdepth = max((y for _, y in pos.values()), default=0) // DY
    for row, kind in enumerate(("idea", "decision"), 2):
        loose = [i for i in sorted(nodes) if i not in pos and nodes[i]["meta"].get("type") == kind]
        for k, nid in enumerate(loose):
            pos[nid] = (k * DX, (maxdepth + row) * DY)
    leftover = [i for i in sorted(nodes) if i not in pos]
    for k, nid in enumerate(leftover):
        pos[nid] = (k * DX, (maxdepth + 4) * DY)
    colour = {"done": "4", "passed": "4", "failed": "1", "mixed": "3", "doing": "3", "running": "3",
              "blocked": "2", "open_decision": "2", "idea": "5", "goal": "6"}
    cnodes = []
    for nid in sorted(nodes):
        m = nodes[nid]["meta"]
        t, s = m.get("type"), m.get("status")
        c = colour.get(s) or (colour["open_decision"] if t == "decision" and s == "open" else colour.get(t))
        node = dict(id=nid, type="file", file=f"nodes/{nodes[nid]['path'].name}", x=int(pos[nid][0]),
                    y=int(pos[nid][1]), width=W, height=H)
        if c:
            node["color"] = c
        cnodes.append(node)
    edges = []
    for nid in sorted(nodes):
        m = nodes[nid]["meta"]
        for kind, field, col in (("parent", "parent", None), ("needed by", "depends_on", "3"),
                                 ("blocks", "blocks", "2"), ("serves", "serves", "5")):
            for other in links(m.get(field)):
                if other not in nodes:
                    continue
                a, b = (other, nid) if field in ("parent", "depends_on") else (nid, other)
                e = dict(id=f"{a}--{kind}--{b}", fromNode=a, toNode=b, fromSide="bottom", toSide="top")
                if col:
                    e.update(color=col, label=kind)
                edges.append(e)
    return dict(nodes=cnodes, edges=edges)


def write_map(nodes, children, roots, errs, warns, needs, out_dir):
    by_type = defaultdict(list)
    for nid in sorted(nodes):
        by_type[nodes[nid]["meta"].get("type")].append(nid)
    def row(nid, *fields):
        m = nodes[nid]["meta"]
        return "| [[" + nid + "]] | " + " | ".join(str(m.get(f, "") or "").replace("|", "/") for f in fields) + " |"
    md = ["<!-- Generated by plan/build.py from plan/nodes/. Do not edit; edit the notes and run the script. -->",
          "", "# Plan map", "",
          f"{len(nodes)} notes: " + ", ".join(f"{len(by_type[t])} {t}s" for t in TYPES) + ".", "",
          "## The engine", "",
          "```mermaid", mermaid_engine(nodes, children, roots), "```", ""]
    root, top, groups = pillars(nodes, roots)
    for p in top:
        md += [f"## {nodes[p]['meta'].get('title', p)}", "", "```mermaid", mermaid_pillar(nodes, children, roots, p),
               "```", ""]
    unsorted = inbox(out_dir)
    md += ["## Inbox", "", f"{len(unsorted)} unsorted {'idea' if len(unsorted) == 1 else 'ideas'} in `plan/inbox.md`; "
           "the next session turns each into a note.",
           ""] + [f"- {x}" for x in unsorted] + ([""] if unsorted else [])
    md += ["## Needs your input", ""]
    md += [f"- {x}" for x in needs] or ["- nothing"]
    md += ["", "## Ready to work on now", "", "Open steps whose dependencies are done and that no open decision "
           "blocks.", ""]
    md += [f"- [[{r}]]: {nodes[r]['meta'].get('title', '')}" for r in ready(nodes)] or ["- none"]
    md += ["", "## Tests", "", "| Test | Status | Fresh | Expected | Result |", "|---|---|---|---|---|"]
    md += [row(n, "status", "fresh", "expected", "result") for n in by_type["test"]]
    md += ["", "## Open decisions", "", "| Decision | Question | Blocks |", "|---|---|---|"]
    md += [row(n, "question", "blocks") for n in by_type["decision"] if nodes[n]["meta"].get("status") == "open"]
    md += ["", "## Decisions taken", "", "| Decision | Question | Answer | Where |", "|---|---|---|---|"]
    md += [row(n, "question", "decided", "recorded_in") for n in by_type["decision"]
           if nodes[n]["meta"].get("status") == "decided"]
    md += ["", "## Ideas", "", "| Idea | Status | Title |", "|---|---|---|"]
    md += [row(n, "status", "title") for n in by_type["idea"]]
    md += ["", "## Check", "", f"{len(errs)} errors, {len(warns)} warnings."]
    md += [f"- ERROR {e}" for e in errs] + [f"- warning: {w}" for w in warns]
    (out_dir / "MAP.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    (out_dir / "map.canvas").write_text(json.dumps(canvas(nodes, children, roots), indent=1) + "\n", encoding="utf-8")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="check only; write nothing")
    ap.add_argument("--dir", default=str(HERE), help="the plan folder (default: this script's folder)")
    a = ap.parse_args(argv)
    plan_dir = Path(a.dir)
    nodes, errs = load(plan_dir / "nodes")
    e2, warns, needs, children, roots = check(nodes, plan_dir.parent)
    errs += e2
    if not a.check:
        write_map(nodes, children, roots, errs, warns, needs, plan_dir)
    for e in errs:
        print("ERROR", e)
    for w in warns:
        print("warning:", w)
    print(f"{len(nodes)} notes, {len(errs)} errors, {len(warns)} warnings, {len(needs)} items need your input")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
