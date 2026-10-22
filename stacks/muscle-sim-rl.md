# Stack: Muscle simulation & RL

```
opensim-core model ──► myoconverter ──► myo_sim / myosuite (MuJoCo Gym)
   predictive: scone-core + scone-studio (+ sconegym / depRL for RL)
   humanoid:   SMPLSim + PHC · locomotion benchmark: loco-mujoco · full-body: musclemimic(_models)
```
Clone it: `python scripts/clone.py --category musculoskeletal-sim`

**Implemented first step (OpenSim, no RL):** `rehabtwin muscles SESSION` estimates ground forces
for double-stance exercises, then runs inverse dynamics and static optimisation on the session's
318-muscle Pose2Sim model. It reports muscle-group demand for the measured motion, a corrected
motion, and what-if weakness (`--weaken gluteus_medius_r=0.5`). With hand-held dynamometry,
`rehabtwin strength` replaces the generic capacities of the tested muscle groups with measured
ones (`muscles --strength`), and `--grf-sensitivity` shows which conclusions survive the
uncertain left/right load split. See `pipeline/README.md`.
MyoSuite/SCONE remain the path for predictive and assistive (exoskeleton) simulation.
