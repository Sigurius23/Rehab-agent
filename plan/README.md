<!-- SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors -->
<!-- SPDX-License-Identifier: MIT -->

# Plan: goals, steps, tests, ideas and decisions

The project's open work, as one note per item in `plan/nodes/`. The notes are the source. The map is drawn from
them by `build.py`, so it never goes stale:
- **`MAP.md`:** first the engine: the end goal and its pillars (sense, personalise, simulate, adapt, act, and how
  we work), each with a tally of its work. Then one diagram per pillar, in the pillars' `order`: its goals, steps
  (with a tally of their tests), open ideas and the decisions that block them; notes from other pillars that link
  in are drawn faded. Then lists of what needs your input, what is ready to work on, and every test, open decision
  and idea.
- **`map.canvas`:** every note on an Obsidian Canvas, laid out as a tree, with ideas and decisions in rows below.

Never edit `MAP.md` or `map.canvas` by hand: edit the notes and run the script. The documents elsewhere in the
repository keep the reasoning; the notes keep the status and point to them (`record`, `source`).

## In Obsidian

Open the `plan/` folder as a vault. Wikilinks, backlinks and the graph view work on the notes as they are.
`map.canvas` opens as a canvas, and `MAP.md` renders its diagram. Sketch freely in Excalidraw, but keep the
structure in the notes, so the map stays true.

## Adding to the plan

Three ways, from quickest to most structured:
1. **The inbox.** Write one line per idea in `plan/inbox.md`, under "Inbox", in plain words, with a link if you have
   one. Any editor works: Obsidian, GitHub's web editor, a phone. The next AI session turns each line into a note
   and removes it. `MAP.md` lists the lines until then.
2. **Obsidian templates.** In Obsidian's settings, turn on the core Templates plugin and set its folder to
   `templates`. Then "Insert template" in a new note under `nodes/` gives an idea, step, test or decision with the
   header filled in. Set its links (`serves`, `parent`, `blocks`) and run the check.
3. **The command line,** for sessions and terminals: `python3 plan/add.py idea "Title" --serves pillar-simulate
   --area neuro --link "Paper=https://..." --text "Why it would help."` It names the note, refuses links to notes
   that don't exist, then checks the plan and redraws the map. `python3 plan/add.py --help` lists every option.

You can also just tell an AI session what to add, in your own words.

## Node types

| Type | What it is | Key fields |
|---|---|---|
| `goal` | An outcome. One root goal, the project's end goal; the others have a goal as parent | `parent` |
| `step` | Work that moves a goal forward | `parent`, `depends_on`, `priority`, a stop rule for priority 1 |
| `test` | How a step is known to have worked | `expected` (written first), `result`, `fresh`, `record` |
| `idea` | Not yet tied to a test or a plan | `serves`; becomes a step by `status: promoted` and `promoted_to` |
| `decision` | A question only the owner can answer | `question`, `options`, `blocks`, then `decided` and `recorded_in` |

Every note has `type`, `title`, `status`, `area` and, where it came from a document, `source`. The full field list
and the allowed statuses are at the top of `build.py`.

## Testing rules (Valve-style: test early, test with fresh eyes)

- **Every open step has a test.** The check warns otherwise: how will you know it worked?
- **Write `expected` before the test runs.** A finished test without one is an error.
- **Say whether the test was fresh:** `fresh: yes` when the data or people were unseen while the thing was built,
  like a playtester who has never seen the game; `no` when they were seen; `n/a` for pure checks.
- **Iterate freely on what is not fresh.** Claims about how well something works come from fresh tests.
- **Priority-1 steps get a stop rule:** a condition with a number, a date (`stop_by`) and an owner who is not the
  person pushing the step.

## Commands

```bash
python3 plan/build.py           # check the notes, then write MAP.md and map.canvas; exit 1 on errors
python3 plan/build.py --check   # check only
python3 plan/test_build.py      # tests of the checker, and that this plan has no errors
```

Standard library only.

## For AI sessions

- Read `plan/MAP.md` first: what is ready, what needs the owner's input.
- When work changes the status of a step or test, update its note, then run `python3 plan/build.py` and fix every
  error before committing. Commit the notes with the regenerated `MAP.md` and `map.canvas`.
- New ideas go in as `idea` notes (`plan/add.py`). They become steps only when they have a test.
- Empty `plan/inbox.md`: turn each line under "Inbox" into a note, link it to its pillar, and remove the line.
- Decisions are the owner's: add a `decision` note and ask, never decide.
- Nothing private in the notes while the repository is public: no prices, supplier contacts, enquiry drafts or
  unpublished assessments.
