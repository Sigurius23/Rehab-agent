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

**Experimental.** This is simulated foot-to-ground contact through a virtual sole, not the foot pressing on a sole
inside a shoe. The registration is approximate (section 3), and nothing has been validated against measurements.
Agreement between simulations is not physical validation.

**Supported models**, as listed in `sole_sim.py`:
- feet with `calcn_<s>` and `toes_<s>` joined by welds or single-axis joints (each axis measured, not assumed);
- generic contact made only of contact spheres used by one smooth sphere-half-space force each, all with the same
  parameters, against one half-space on ground.
Anything else is refused before the model is changed (`tests/test_sim_osim.py` has the negative controls).
Tested on the pipeline's two-segment self-test model and D'Hondt et al.'s nominal 3- and 4-segment models.

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
     - The boundary between segments is a line through the joint centre along the joint's measured axis,
       projected onto the sole plane. It is a simplification: a point near a boundary may belong to the
       neighbouring segment.
     - A model whose toes are not reached from `calcn` through its joints is refused.
       (`tests/test_sim_osim.py` covers both cases.)
   - **Registration.** The sole's heel point goes on the back of the model's heel sphere. Its toe-joint bend line
     goes on the model's toe joint axis, at the foot's long axis. The scale between those two landmarks applies
     to x and z. Both landmarks are read in the `calcn` frame at the model's default pose, through OpenSim's frame
     transforms. A toe joint that hangs from a forefoot segment is therefore located correctly.
   - **Plantar plane:** the bottom of the model's `calcn` contact spheres.
   - **They replace the generic contact spheres on every segment of that foot** (`--keep-generic` keeps them).
   - **Contact parameters**, one of two choices (`--contact`):
     - `native` (the default): copied from the model's own foot contact. The stiffness is scaled so the foot as
       a whole keeps the same contact stiffness: Hertz contact grows with the square root of the radius per
       sphere, so 55 small spheres with the generic stiffness would make the foot several times stiffer.
     - `assumed-v1` (`sole_sim.ASSUMED_CONTACT_V1`): the same law on every model, whatever contact it brings.
       Each sphere carries p = 100 kPa × (indentation / 3 mm)^1.5 over its grid cell; its stiffness is
       calibrated numerically. **Assumed, not measured:** it stands in for the sole stack and plantar soft
       tissue until the coupon test gives a measured curve. It also uses smaller smoothing terms (constant
       contact force 1e-8, Hertz smoothing 2000 /m). OpenSim's defaults, which the models' native contact
       uses, act like about 3 mm of minimum indentation and let a sphere 2 mm above the floor carry 22 % of
       its force at 3 mm.
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

### Other foot models (2026-11-04): see FOOT_MODELS.md

The adapter now also supports multi-segment feet: D'Hondt et al.'s nominal 3- and 4-segment models. They were
compared with the two-segment foot under the same sole and the same quasi-static loading, in `FOOT_MODELS.md`.
That comparison is experimental and selects no model.

An earlier version of this section, from the first multi-segment run (commit acf6ce7), is superseded:
- **Model file.** It used a subject file from the same repository, not the published nominal models.
- **Toe-joint axis.** It took the axis from the joint's frame. On D'Hondt's CustomJoint the real axis is 16.6°
  away; the registered scale is now 0.998, not 0.996.
- **"All 110 sphere bottoms on the plantar plane."** That holds by construction: the adapter places every
  sphere there. It is not evidence of registration.
- **The drop test.** It carried the body weight (608.4 N against 608.2 N) with every joint locked. Like the
  first check, it says nothing about the load pattern.

## 3. Limits to keep in mind

- **A coarse grid.** 15 mm spacing gives about 55 spheres per EU 42 sole, and some small regions have 2. A finer
  grid (`--spacing`) costs simulation time.
- **The stiffness rule** keeps the foot's overall stiffness, not the sole's real compliance. That comes from the
  coupon and printed-prototype tests.
- **Registration is approximate, and its residuals are reported, not corrected** (`registration_residuals` in the
  metadata):
  - three landmarks only, with no lateral registration and one scale for length and width;
  - one plantar plane, although the model's own contact spheres sit up to 3.8 mm off it;
  - toe regions put on the toes by name, with metatarsal points that lie past the toe-joint axis reported.
  A scale near 1, and sphere bottoms on the plane (true by construction), do not establish anatomical
  registration.
- **Segment boundaries** on a multi-segment foot are lines through each joint centre along its measured axis. A
  sphere near a boundary may ride on the neighbouring segment.
- **Contact.** With `native`, the contact is inherited from each model's generic contact, so the same sole is
  stiffer on some models than on others, and that alone changed regional shares by 3–8 points. With
  `assumed-v1` the law is the same on every model, but it is an assumption. Switching between the two changes
  D'Hondt's regional shares by up to 14 points (`FOOT_MODELS.md`, sections 5.1 and 5.4). Neither is measured.
- **Length is registered on two landmarks** (heel and toe joint). The self-test model's toe-joint axis is more
  oblique (about 35°) than the sole's bend line (about 13°), so the toe-joint line is matched at the foot's long
  axis only.

## 4. Next steps in simulation (planned, not done)

1. **Tracking simulation** (OpenSim Moco) of a squat and of walking, with the sensorised soles as the foot
   contact. Region loads and centre of pressure over time. The pipeline's estimated ground forces are not a
   reference: the comparison is against measured force plates (`VALIDATION_PLAN.md`, stage A), and it is
   reported separately from the passive, prescribed-centre-of-pressure control in `FOOT_MODELS.md`.
2. **MuJoCo / MyoSuite.** Export the same contact layer as an MJCF fragment for models converted with
   `myoconverter`.
3. **Sensor variants.** Run the same motion through the baseline, T1 and a printed-prototype region set to see
   what each could resolve. These would still be simulated, not measured.
4. **Validation path** (`VALIDATION_PLAN.md`): three separate stages, each with candidate public datasets.
   First the current foot-to-ground model against force plates; then regional barefoot plantar pressure; then
   foot–insole contact, which needs the footbed and shoe layers and the sole's measured response first. Once the
   printed prototype exists, the same motion can be recorded on the bench or a force plate against the
   simulated readings. Thresholds are set before the data is seen.

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
