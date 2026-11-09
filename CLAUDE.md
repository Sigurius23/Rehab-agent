<!-- SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors -->
<!-- SPDX-License-Identifier: MIT -->

# Standing rules for agent sessions

The project is a full-body digital twin that personalises to each person and adapts as they change. It works in
five stages: sense, personalise, simulate, adapt and act (feedback, a haptic suit, an exoskeleton). The plan is
in `plan/`. Read `plan/MAP.md` first: what is ready, and what needs the owner's input.

These rules hold in every session, on every machine, whether or not a prompt repeats them.

## Decisions and outside actions

- **Decisions are the owner's.** Add a `decision` note (`plan/add.py decision ...`) and ask. Never decide.
- **Ask first** before buying, ordering, printing or fabricating anything, and before sending or contacting anyone.
  That includes manufacturers, suppliers and vendors. No board is released for fabrication.
- Don't merge `feat/sensor-sole`. Push only to `origin` (github.com/Sigurius23/Rehab-agent), and only when the
  owner asks for it. On the lab laptop, ask before every push.

## Tests come before the data

- **Write the rule before the data it judges is opened.** Hypotheses, thresholds, validity rules and stop rules
  go in as dated amendments, for example in `hardware/sensor-sole/VALIDATION_PLAN.md`. A rule written later is
  reported as such, beside the original result.
- **No dynamic force data before the owner's "go".** The force-plate files are opened only when the plan's phase
  says so.
- **Plan tests:** `expected` is written before the test runs. `fresh` says whether the data was seen while the
  thing was built. Priority-1 steps have a stop rule with a number, a date and an owner.
- **A skip is not a pass.** Record what ran and what was skipped (`hardware/sensor-sole/TEST_RUNS.md`).
- **Report results as they are:**
  - an invalid or non-converged solve is reported as not evaluated, never as passing;
  - a spacing study is reported as discretisation sensitivity, not total uncertainty;
  - out-of-range cases stay flagged;
  - an assumed value, such as the assumed sole contact, is never described as measured.

## Reproducibility

- Don't change the files that feed the comparison's case fingerprints, all in `hardware/sensor-sole/foot_models/`:
  - `compare_feet.py`;
  - `sole_sim.py`;
  - `dhondt_port.py`;
  - `dhondt2024_mtj_ligament_moment.json`.
- Record every input's sha256 and every package version (`foot_models/PROVENANCE.json`, `machine.json`).

## Data and licences

- **Nothing downloaded goes in the repository:** no datasets, model weights, upstream code or recordings.
  Recordings of people are health data. Downloaded data lives under `~/rehab-agent-data`.
- **Downloaded files are untrusted.**
  - Put each download in its own directory.
  - Never execute it. Read it with `python -I`.
  - Load `.npz` files with `allow_pickle=False`.
- **BEDLAM2, SMPL, SMPL-X and SKEL are licence-gated and non-commercial.** Never commit their files or use them
  in tests.

## The repository is public

- Nothing private goes in:
  - no quotes or prices from enquiries;
  - no supplier contacts or enquiry drafts;
  - no unpublished assessments or verbatim research notes;
  - nothing about where the owner lives or works.
- Never ask for or accept passwords. Never print a token.
- Don't store GitHub credentials on the lab laptop.

## End of a session

- Update the plan note of every step or test whose status changed.
- Then run `python3 plan/build.py`; it must show 0 errors. Run `python3 plan/test_build.py` as well.
- Commit the notes together with the regenerated `MAP.md` and `map.canvas`.
- Run long jobs in `tmux` or with `nohup`. Use the resumable runners (`hardware/sensor-sole/workstation/`).
