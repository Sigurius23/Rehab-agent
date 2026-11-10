#!/usr/bin/env bash
cd $HOME/rehab-agent-data/kinematics/bench && exec systemd-inhibit --what=sleep:idle:handle-lid-switch --who=rehab-agent --why="video benchmark" --mode=block $HOME/rehab-agent-data/kinematics/envs/pipeline/bin/python -I scripts/bench_run.py --workers 8 >> $HOME/rehab-agent-data/kinematics/bench/bench.log 2>&1
