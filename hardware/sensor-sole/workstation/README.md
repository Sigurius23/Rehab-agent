<!-- SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors -->
<!-- SPDX-License-Identifier: CERN-OHL-S-2.0 -->

# Running the sole simulations on a workstation

For a machine with more cores, memory and disk than a cloud session, such as the lab laptop, which is free only
some of the time. These scripts set it up, check every external input, and run the comparison so that a run cut
short carries on where it stopped. Everything here is experimental simulation, as in `FOOT_MODELS.md`.

## What it needs

- **Linux, or WSL2 with Ubuntu on Windows.** On Windows: `wsl --install -d Ubuntu-24.04`, then work inside
  Ubuntu. Keep the data in the Linux file system (the default `~/rehab-agent-data`), not under `/mnt/c`, which is
  much slower.
- `git`, `python3` (any 3.8 or later), and [uv](https://docs.astral.sh/uv/). uv fetches Python 3.13 itself.
- **Optional:** KiCad 7 with its Python (`sudo apt install kicad` on Ubuntu 24.04) for the board-check suites.
- **No GPU work yet.** OpenSim, Moco and CasADi run on the CPU. The GPU is recorded in `machine.json` for later
  work (MuJoCo/MyoSuite, the video pipeline).
- **No accounts or tokens.** Everything fetched is public. Don't store GitHub credentials on a shared lab machine.
  Push from your own machine or the cloud session.

## First time (about 5–10 minutes, most of it downloads)

```
git clone -b feat/sensor-sole https://github.com/Sigurius23/Rehab-agent rehab-agent   # full history: the
cd rehab-agent/hardware/sensor-sole                                                    # self-test needs it
workstation/setup.sh
```

**What `setup.sh` does, in order.** Each step can also be run on its own: `setup.sh envs|inputs|machine|tests`.
1. **Environments**, under `~/rehab-agent-data/sensor-sole/envs`:
   - `sim`: OpenSim 4.6;
   - `casadi`: CasADi 3.8.2;
   - `generator`: the sole generator's packages.
   All versions are pinned. OpenSim and CasADi need separate environments: OpenSim's wheel carries its own
   CasADi 3.7 for Moco, and CasADi 3.8.2 then fails to load in the same process, whichever is imported first.
2. **Inputs** (`fetch_inputs.py`). D'Hondt's models and saved function, the Synergy model, OpenCap's squat and
   Pose2Sim's model files are fetched at their pinned commits. Every file is checked against
   `foot_models/PROVENANCE.json`, and **any mismatch stops the setup.** The two-segment foot is then rebuilt with
   the pipeline as it was at commit 33aeb49. That reproduces the recorded model byte for byte; today's pipeline
   would make the body about 3 % heavier.
3. **Machine record** (`machine.json`): CPU, cores, memory, GPU, OS and every package version. Results from this
   machine are tied to it.
4. **Tests** (`test_runs/`): every suite in its environment, with what ran and what was skipped.
   `setup.sh tests --slow` adds the slow generator cases and the KiCad negative controls, which take minutes per
   case.

Running `setup.sh` again is safe: it keeps what is already there and checks it again.

## Running the comparison

```
workstation/run_comparison.sh                          # all groups; cores - 2 cases at a time
workstation/run_comparison.sh --only controlled_cop    # one group
JOBS=8 workstation/run_comparison.sh
```

- **Output:** `~/rehab-agent-data/sensor-sole/runs/comparison/summary.json`, plus one folder per case.
- **Interruptions:** if the run is cut short (laptop closed, shut down, terminal closed), run the same command
  again. Finished cases are reused; only unfinished ones run again.
- **When results are reused:** only for exactly the same inputs, parameters, code and OpenSim version. Changing
  any of them runs the case again (`foot_models/case_store.py`). `--no-resume` recomputes everything.
- **Sleep:** start long runs inside `tmux`, or with `nohup`, so closing the terminal doesn't stop them. On
  Windows, a laptop that sleeps pauses WSL. Set the lid to do nothing while plugged in, if the lab allows it.

**Finer contact spacing** (the discretisation sensitivity, `FOOT_MODELS.md` section 5.3). The soles at 15, 10,
7.5 and 5 mm are committed in `sim/`. For finer ones:

```
workstation/setup.sh soles 3.75 2.5        # regenerates the EU 42 boards once (a few minutes each)
SPACING_SOLES="$HOME/rehab-agent-data/sensor-sole/soles/3.75mm $HOME/rehab-agent-data/sensor-sole/soles/2.5mm" \
    workstation/run_comparison.sh --only discretisation
```

The regenerated boards must reproduce the committed 15 mm soles byte for byte, or `setup.sh soles` stops.

## Bringing results back

`summary.json`, `machine.json` and `test_runs/*.json` are small and hold no personal data. Copy them to the
repository (or hand them to the cloud session) to be checked and written up. The per-case folders are for
re-checking and can stay on the laptop. Downloaded models and datasets stay out of the repository. Measured
recordings of people are health data and never go into it.
