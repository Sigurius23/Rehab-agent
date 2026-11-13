#!/usr/bin/env bash
cd $HOME/rehab-agent-data/kinematics/bench && exec systemd-inhibit --what=sleep:idle:handle-lid-switch --who=rehab-agent --why="HSMR benchmark" --mode=block /usr/bin/python3 -I scripts/bench_hsmr.py >> $HOME/rehab-agent-data/kinematics/bench/hsmr.log 2>&1
