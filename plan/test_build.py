#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors
# SPDX-License-Identifier: MIT
"""Checks of plan/build.py on small synthetic plans, and that the real plan has no errors. Standard library only.

  python3 plan/test_build.py
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build as B  # noqa: E402

BASE = {
    "root": 'type: "goal"\ntitle: "Root"\nstatus: "open"\narea: "project"',
    "s1": 'type: "step"\ntitle: "Step one"\nstatus: "done"\narea: "sole"\nparent: "[[root]]"\nrecord: "plan/build.py"',
    "s2": ('type: "step"\ntitle: "Step two"\nstatus: "open"\narea: "sole"\nparent: "[[root]]"\n'
           'depends_on:\n  - "[[s1]]"'),
    "t2": ('type: "test"\ntitle: "Test of two"\nstatus: "planned"\narea: "sole"\nparent: "[[s2]]"\n'
           'expected: "at most 5 points"'),
    "d1": ('type: "decision"\ntitle: "Buy it"\nstatus: "open"\narea: "sole"\nquestion: "Buy it?"\n'
           'blocks: ["[[s2]]"]'),
    "i1": 'type: "idea"\ntitle: "An idea"\nstatus: "new"\narea: "sole"\nserves: ["[[s2]]"]',
}


class Plans(unittest.TestCase):
    def build(self, **changes):
        notes = {k: v for k, v in {**BASE, **changes}.items() if v is not None}
        self.tmp = tempfile.TemporaryDirectory()
        d = Path(self.tmp.name) / "plan"
        (d / "nodes").mkdir(parents=True)
        for k, v in notes.items():
            (d / "nodes" / f"{k}.md").write_text(f"---\n{v}\n---\n# {k}\n", encoding="utf-8")
        nodes, errs = B.load(d / "nodes")
        e2, warns, needs, children, roots = B.check(nodes, HERE.parent)
        B.write_map(nodes, children, roots, errs + e2, warns, needs, d)
        return errs + e2, warns, needs, d, nodes

    def tearDown(self):
        if hasattr(self, "tmp"):
            self.tmp.cleanup()

    def test_valid_plan_has_no_errors_and_draws_every_note(self):
        errs, warns, needs, d, nodes = self.build()
        self.assertEqual(errs, [])
        canvas = json.loads((d / "map.canvas").read_text())
        self.assertEqual({n["id"] for n in canvas["nodes"]}, set(nodes))
        self.assertIn("```mermaid", (d / "MAP.md").read_text())
        self.assertTrue(any("d1" in n for n in needs))          # the open decision is listed for the owner
        self.assertEqual(B.ready(nodes), [])                    # s2 is blocked by the open decision

    def test_ready_once_the_decision_is_taken(self):
        _, _, _, _, nodes = self.build(d1=BASE["d1"].replace('status: "open"', 'status: "decided"')
                                       + '\ndecided: "yes"')
        self.assertEqual(B.ready(nodes), ["s2"])

    def test_broken_link(self):
        errs = self.build(s2=BASE["s2"].replace("[[s1]]", "[[nope]]"))[0]
        self.assertTrue(any("unknown note 'nope'" in e for e in errs))

    def test_dependency_cycle(self):
        errs = self.build(s1=BASE["s1"] + '\ndepends_on:\n  - "[[s2]]"')[0]
        self.assertTrue(any("cycle" in e for e in errs))

    def test_two_roots(self):
        errs = self.build(other='type: "goal"\ntitle: "Other"\nstatus: "open"\narea: "project"')[0]
        self.assertTrue(any("exactly one root goal" in e for e in errs))

    def test_finished_test_needs_expected_result_and_fresh(self):
        errs = self.build(t2=BASE["t2"].replace('"planned"', '"passed"'))[0]
        self.assertTrue(any("no result" in e for e in errs))
        self.assertTrue(any("fresh" in e for e in errs))
        errs = self.build(t2=BASE["t2"].replace('"planned"', '"failed"').replace('expected: "at most 5 points"', '')
                          + '\nresult: "7 points"\nfresh: "yes"')[0]
        self.assertTrue(any("no expected result" in e for e in errs))

    def test_priority_one_stop_rule(self):
        errs, _, needs, _, _ = self.build(s2=BASE["s2"] + '\npriority: "1"')
        self.assertEqual(errs, [])
        self.assertTrue(any("needs a stop rule" in n for n in needs))
        errs = self.build(s2=BASE["s2"] + '\npriority: "1"\nstop_rule: "fails again"\nstop_by: "soon"')[0]
        self.assertTrue(any("no number" in e for e in errs))
        self.assertTrue(any("stop_by must be a date" in e for e in errs))
        self.assertTrue(any("stop_owner" in e for e in errs))
        errs = self.build(s2=BASE["s2"] + '\npriority: "1"\nstop_rule: "fails after 3 versions"\n'
                          'stop_by: "2026-12-01"\nstop_owner: "owner"')[0]
        self.assertEqual(errs, [])

    def test_wrong_parent_type_and_bad_status(self):
        errs = self.build(t2=BASE["t2"].replace("[[s2]]", "[[i1]]"), i1=BASE["i1"].replace('"new"', '"maybe"'))[0]
        self.assertTrue(any("cannot have a idea as parent" in e for e in errs))
        self.assertTrue(any("status 'maybe'" in e for e in errs))

    def test_pillars_follow_their_order(self):
        _, _, _, _, nodes = self.build(
            pa='type: "goal"\ntitle: "Zeta pillar"\nstatus: "open"\narea: "project"\nparent: "[[root]]"\norder: "1"',
            pb='type: "goal"\ntitle: "Alpha pillar"\nstatus: "open"\narea: "project"\nparent: "[[root]]"\norder: "2"',
            s1=BASE["s1"].replace("[[root]]", "[[pb]]"), s2=BASE["s2"].replace("[[root]]", "[[pa]]"))
        roots = [n for n in nodes if not B.links(nodes[n]["meta"].get("parent"))
                 and nodes[n]["meta"].get("type") == "goal"]
        root, top, groups = B.pillars(nodes, roots)
        self.assertEqual(top, ["pa", "pb"])
        engine = B.mermaid_engine(nodes, {}, roots)
        self.assertLess(engine.index("Zeta pillar"), engine.index("Alpha pillar"))
        self.assertIn("1 idea", engine)                          # singular
        self.assertIn("s2", groups["pa"])
        self.assertIn("i1", groups["pa"])                        # an idea sits with what it serves

    def test_open_step_without_test_is_a_warning(self):
        errs, warns, *_ = self.build(t2=None)
        self.assertEqual(errs, [])
        self.assertTrue(any("s2: open step with no test" in w for w in warns))


class Adding(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.plan = Path(self.tmp.name) / "plan"
        (self.plan / "nodes").mkdir(parents=True)
        for k in ("root", "s2"):
            (self.plan / "nodes" / f"{k}.md").write_text(f"---\n{BASE[k] if k == 'root' else BASE['s2'].replace(chr(10) + 'depends_on:' + chr(10) + '  - \"[[s1]]\"', '')}\n---\n")
        import add as A
        self.A = A

    def tearDown(self):
        self.tmp.cleanup()

    def run_add(self, *args):
        import contextlib, io
        with contextlib.redirect_stdout(io.StringIO()):
            return self.A.main([*args, "--dir", str(self.plan)])

    def test_added_notes_pass_the_check(self):
        self.assertEqual(self.run_add("idea", "Brain: regions light up", "--serves", "s2", "--area", "neuro",
                                      "--link", "paper=https://example.org/x"), 0)
        self.assertEqual(self.run_add("test", "It responds", "--parent", "s2", "--expected", "at most 5 points"), 0)
        self.assertEqual(self.run_add("decision", "Buy the film", "--blocks", "s2"), 0)
        notes = {p.stem for p in (self.plan / "nodes").glob("*.md")}
        self.assertIn("idea-brain-regions-light-up", notes)
        text = (self.plan / "nodes" / "idea-brain-regions-light-up.md").read_text()
        self.assertIn("[paper](https://example.org/x)", text)
        nodes, errs = B.load(self.plan / "nodes")
        self.assertEqual(errs + B.check(nodes, self.plan.parent)[0], [])

    def test_unknown_reference_and_missing_parent_are_refused(self):
        import contextlib, io
        for args in (("idea", "X", "--serves", "nope"), ("step", "Y")):
            with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
                self.run_add(*args)

    def test_inbox_lines_are_listed(self):
        (self.plan / "inbox.md").write_text("# Inbox\n\nIntro.\n\n## Inbox\n\n- a TRIBE-style brain view\n- \n"
                                           "- food timing and muscle\n\n## Other\n\n- not this\n")
        self.assertEqual(B.inbox(self.plan), ["a TRIBE-style brain view", "food timing and muscle"])


class RealPlan(unittest.TestCase):
    def test_the_plan_in_this_repository_has_no_errors(self):
        nodes, errs = B.load(HERE / "nodes")
        errs += B.check(nodes, HERE.parent)[0]
        self.assertEqual(errs, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
