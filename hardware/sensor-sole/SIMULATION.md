<!-- SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors -->
<!-- SPDX-License-Identifier: CERN-OHL-S-2.0 -->

# Sensor sole in simulation

**2026-11-04. Simulation comes first.** The sole is tested in the musculoskeletal simulation before any physical
test.

**What a simulated reading is not:**
- **Not a measurement.** It comes from the simulation's contact model and an assumed sensor response.
- **Not evidence of sensing, fit or durability.** Those stay untested until physical tests exist.
- **Not a release.** Nothing here releases anything for fabrication or printing.

`sole_sim.py` puts a sole design into the simulation as a sensorised contact layer. Every reading the
simulation produces comes out in the same layout as the real pod's: one value per region, in contact order.
Any sole the generator makes can be loaded: the baseline, candidate T1, any size or a person's foot. The 3D-printed
prototype (`PRINTED.md`) uses the same regions.

## 1. How the sole gets into the model

```
python sole_sim.py export out/sole_EU42_R.board.json --map maps/EU42_R_<hash>.json -o sim/   # generator's Python
python sole_sim.py osim model_scaled.osim sim/EU42_R_<hash>.sole_sim.json -o model_with_sole.osim   # pipeline's Python (opensim)
python sole_sim.py readout forces.sto sim/EU42_R_<hash>.sole_sim.json -o readings.csv
```

1. **Export** (`<id>.sole_sim.json`, format `sensor-sole-sim/1`). It holds:
   - the regions in the sole frame;
   - a grid of contact points inside each region, 15 mm apart and anchored at the region's centroid, so a left
     sole mirrors the right exactly;
   - the contact-to-region map, taken from the verified deployed map when one is given;
   - the assumed sensor model;
   - the board ID and design hash, so a simulated reading names the exact sole it came from.
2. **OpenSim.** A copy of the model is written in which the foot meets the floor through the sole:
   - **One contact sphere per contact point.** Each is named `sole_<side>_<region>_<k>` and has its own
     `SmoothSphereHalfSpaceForce` against the model's floor.
   - **Which body.** `sole_sim.py` follows the model's joints from `calcn_<side>` to `toes_<side>`.
     - Spheres for toe regions ride on the toes.
     - Every other sphere rides on the segment it lies under: the last segment whose proximal joint is behind
       it. On a two-segment foot that is `calcn`, since the metatarsal heads are proximal of the toe joint. On a
       multi-segment foot it is `calcn`, `midfoot` or `forefoot`.
     - The boundary between segments is a line across the foot through the joint centre. It approximates an
       oblique joint axis.
     - A model whose toes are not reached from `calcn` through its joints is refused.
       (`tests/test_sim_osim.py` covers both cases.)
   - **Registration.** The sole's heel point goes on the back of the model's heel sphere. Its toe-joint bend line
     goes on the model's toe joint axis, at the foot's long axis. The scale between those two landmarks applies
     to x and z. Both landmarks are read in the `calcn` frame at the model's default pose, through OpenSim's frame
     transforms. A toe joint that hangs from a forefoot segment is therefore located correctly.
   - **Plantar plane:** the bottom of the model's `calcn` contact spheres.
   - **They replace the generic contact spheres on every segment of that foot** (`--keep-generic` keeps them).
   - **Contact parameters** are copied from the model's own foot contact. The stiffness is scaled so the foot as a
     whole keeps the same contact stiffness: Hertz contact grows with the square root of the radius per sphere,
     so 55 small spheres with the generic stiffness would make the foot several times stiffer.
3. **Readout.** It takes the simulation's force report (OpenSim `ForceReporter`) and gives:
   - each region's normal force;
   - the total force and the centre of pressure, from the region centroids;
   - the pod's readings in contact order, through the assumed sensor model: full scale at 600 kPa on the
     region, linear, 12-bit, 0.5 % noise.

   The sensor model is a placeholder until the coupon test measures the film. Hysteresis, creep and temperature
   are not modelled.

**Frames.** The generator's sole frame and OpenSim's `calcn` frames share their axes: x forward, y up, z to the
right for both feet. A left sole's lateral side is therefore −z.

## 2. First check: dropping the model onto both soles

The pipeline's scaled self-test model was used, with EU 42 soles on both feet (55 contact spheres each).

**Set-up:**
- every coordinate is locked except the pelvis height;
- muscles are removed (with the joints locked they only slow the run);
- the run starts 2 mm above the floor and lasts 1 s.

| | Result |
|---|---|
| Start | Lowest sole point 2.0 mm above the floor; 27 N, the smooth contact model's onset before touch |
| Impact peak, right foot | 683 N |
| Settled, at 1 s | 344.3 N per foot, 688.6 N together; the model weighs 686.7 N (0.3 % over, still settling) |
| Left and right | Mirror images, as they should be |
| Readout | 16 readings per foot in contact order, from the verified map |

**What it shows:** the sole loads into the model, carries the body through its own contact spheres, and reads
out per region in the pod's layout. The forces add up to the body weight.

**What it does not show:**
- **The load pattern under the foot.** With every joint locked the feet cannot tilt, so each sphere carries the
  same share. The region forces then simply follow how many spheres each region has. Physiological heel and
  forefoot loading needs a balancing or tracking simulation (section 4).
- **Fit.** The registration scaled the sole by 1.16 to this synthetic subject's foot, and `sole_sim.py` warns
  about it: that sole was not made for that foot. For a person, generate the sole from their foot (`sole_gen.py
  --length/--width` or `--foot`), so the scale comes out near 1.
- **Rigid segments.** `calcn` and `toes` are rigid. There are no footbed or shoe layers yet: the sole meets the
  floor directly.

### A four-segment foot (2026-11-04)

The same EU 42 soles were loaded onto D'Hondt et al.'s four-segment foot model. It has `calcn`, then `midfoot`
through a midtarsal joint, a `forefoot` welded to the midfoot, and `toes`. The source is
`Fal_s1_mtjcf3_FK_sc_FDB2_MTc5_cspx10_cg9_o1x10.osim` from the `four-segment_foot_model` branch of
`Lars-DHondt-KUL/3dpredictsim` (MIT). The model is not committed here.

| | Before the fix | After |
|---|---|---|
| Toe joint located | in the forefoot's frame, read as if it were the calcaneus's | in the calcaneus frame |
| Sole scale | **0.454**, with only a warning | 0.996 |
| Midfoot and metatarsal regions | on `calcn`, though the forefoot moves separately | 18 spheres on `calcn`, 4 on `midfoot`, 20 on `forefoot`, 13 on `toes` |
| The model's own forefoot spheres | left in place, so the forefoot touched twice | replaced, with those on `calcn` and `toes` |
| Sphere bottoms at the default pose | — | all 110 on the plantar plane, on every segment |
| Drop test (same set-up as above) | — | settles at 304.2 N per foot, 608.4 N together; the model weighs 608.2 N |

**What this does not show:**
- The load pattern means as little as in the first check: the joints are locked and the foot is flat.
- The paper's foot mechanics are not reproduced by a plain OpenSim run of this model. The `.osim` carries a
  plantar-fascia path (`Ligament`, calcaneus to toes, resting length 0.149 m). The paper's fascia stiffness
  (Natali 2010, slack length 0.146 m) and its midtarsal ligament moment are applied in the repository's
  MATLAB/CasADi code (`VariousFunctions/getSettingsNominalModel.m`), not in the `.osim`.

## 3. Limits to keep in mind

- **A coarse grid.** 15 mm spacing gives about 55 spheres per EU 42 sole, and some small regions have 2. A finer
  grid (`--spacing`) costs simulation time.
- **The stiffness rule** keeps the foot's overall stiffness, not the sole's real compliance. That comes from the
  coupon and printed-prototype tests.
- **Segment boundaries** on a multi-segment foot are lines across the foot through each joint centre, not the
  joints' oblique axes. A sphere near a boundary may ride on the neighbouring segment.
- **The registration uses two landmarks** (heel and toe joint). The model's toe-joint axis is more oblique (about
  35°) than the sole's bend line (about 13°), so the toe-joint line is matched at the foot's long axis only.

## 4. Next steps in simulation (planned, not done)

1. **Tracking simulation** (OpenSim Moco) of a squat and of walking, with the sensorised soles as the foot
   contact. Region loads and centre of pressure over time, set against the pipeline's estimated ground forces.
2. **MuJoCo / MyoSuite.** Export the same contact layer as an MJCF fragment for models converted with
   `myoconverter`.
3. **Sensor variants.** Run the same motion through the baseline, T1 and a printed-prototype region set to see
   what each could resolve. These would still be simulated, not measured.
4. **Validation path.** Once the printed prototype exists: the same motion recorded on the bench or a force
   plate against the simulated readings. Thresholds are set before the data is seen.

## 5. High-performance computing: to plan, not started

An HPC allocation would suit embarrassingly parallel runs:
- **Routing sweeps:** every EU size and foot through the generator and checker. One configuration takes 5–7
  minutes and up to 7 GB of memory.
- **Tracking simulations with the sole contact:** Moco with about 110 contact spheres per model is slow.
- **Finite-element runs** of the printed carrier (TPU pockets under load).

Planning still needed:
- the software environment (containers with the generator's and the pipeline's pinned versions);
- data handling: recordings are health data and stay off shared systems unless approved;
- model licences (SMPL, SKEL and BEDLAM2 are non-commercial; check the HPC terms);
- how results are tied back to commits and design hashes.
