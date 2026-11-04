<!-- SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors -->
<!-- SPDX-License-Identifier: CERN-OHL-S-2.0 -->

# Foot models on the virtual sole: a controlled comparison

**2026-11-04. Experimental. No foot model is selected by this comparison.**

**What this is:** the same sensor-sole design (EU 42, `EU42 R 636645a928` / `EU42 L 40fe8e1d0c`), loaded onto
different OpenSim foot models through the same adapter (`sole_sim.py`), under the same quasi-static loading.

**What it is not:**
- **Not foot–insole contact.** It is simulated foot-to-ground contact through a virtual sole: the foot pressing
  on a sole inside a shoe is not modelled, and there are no footbed or shoe layers.
- **Not physical validation.** Agreement between simulations is not validation, and a plausible load map is not
  proof of accuracy.
- **Not a measurement.** Nothing here was measured. Measured pressure or force-plate data is the next step for
  any result below to mean something.

## 1. What was compared

| Model | Source (pinned) | Licence | Foot structure | How it was used |
|---|---|---|---|---|
| Two-segment foot | The pipeline's scaled self-test model | (ours) | calcn + toes; MTP pin joint, 35° oblique | Foot rigid |
| D'Hondt et al. (2024), 3-segment | `3dpredictsim` (branch `four-segment_foot_model`, commit e963f4a), `OpenSimModel/Nominal models/DHondt_2024_3-segment_foot_fixed_knee.osim`, sha256 `f78df978…` | MIT | calcn, midfoot, forefoot welded; toes on an MTP joint | `.osim` only, and ported (section 3); MTP locked or free |
| D'Hondt et al. (2024), 4-segment | The same, `DHondt_2024_4-segment_foot_fixed_knee.osim`, sha256 `241eb5dd…` | MIT | calcn, midfoot on a midtarsal joint, forefoot welded to it, toes on an MTP joint; plantar fascia and 12 midtarsal ligaments as OpenSim `Ligament`s | `.osim` only, and ported; midtarsal and MTP locked or free |
| Synergy-Based Foot Model | `modenaxe/synergy-based-foot-model-opensim` (0015fc7), `synergy_foot_r.osim` | Apache-2.0 | 19 bones, five toes among them, driven by five coupled synergy gains; no muscles, ligaments or contact | Kinematic only (section 6) |
| Sikidar–Kalyanasundaram | SimTK `ankle-foot`, `Model.zip` | MIT-style terms on the download page | The project description reports 24 DOFs, 46 ligaments, 1 capsule, 19 fasciae, 30 tendons and 65 muscles; **package contents not verified** | Not yet: the download needs a SimTK account |

None of these models, nor the squat kinematics (OpenCap's `squats1_videoAndMocap.mot`), is in this repository.

## 2. How the sole goes on, and what the adapter supports

**Supported feet** (`sole_sim.py osim`). Anything else is refused with `UnsupportedModel` before the model is
changed:
- Bodies `calcn_<s>` and `toes_<s>`, joined by a chain of joints.
- Every joint in that chain a weld, or a single rotational coordinate about one axis through the joint centre.
  Each axis is measured by moving the joint, not assumed from its frame.
- The generic foot contact made only of `ContactSphere`s on chain bodies, each used by exactly one
  `SmoothSphereHalfSpaceForce`. All of them must act against one `ContactHalfSpace` on ground and share the same
  parameters.
- No other contact geometry on the foot: the chain's parent body and below.

**Tested on:** the two-segment self-test model, and D'Hondt's nominal 3- and 4-segment models. **Not
supported:** the Synergy model, which has no `calcn`/`toes` bodies and no contact.

**Negative controls** (`tests/test_sim_osim.py`). These are what the earlier adapter (acf6ce7) did with each
arrangement, checked on synthetic feet:

| Arrangement | Earlier adapter | Now |
|---|---|---|
| Foot geometry used by another force type (`HuntCrossleyForce`) | Removed it; OpenSim then failed with an unclear error | Refused, naming the geometry and the force |
| Contact sphere used by no force | Removed it silently | Refused |
| Non-sphere geometry on the foot (ellipsoid) | Removed it silently | Refused |
| Half-space attached to the foot | Removed it and the force using it, silently | Refused |
| Generic spheres with different stiffness | Copied the first one's parameters silently | Refused |
| Contact sphere on the talus | Kept: the foot would touch twice | Refused |
| Two-coordinate joint in the foot chain | Accepted | Refused |
| Toe joint whose axis is not its frame's z axis | Frame z used: wrong toe line and scale | Measured axis used |
| Oblique midtarsal axis | Boundary as a straight line across the foot | Boundary along the measured axis |

On the self-test model the output is unchanged: the same spheres, bodies and forces.

**Registration, and its residuals (reported, not corrected).** The adapter uses three landmarks: the heel point
on the back of the heel sphere, the toe-joint line at the foot's long axis, and one plantar plane. A scale near 1
and sphere bottoms on that plane **do not prove anatomical registration**: the spheres lie on the plane by
construction. What the residual report (`registration_residuals` in each run's metadata) shows:

| | Two-segment | D'Hondt 3- and 4-segment |
|---|---|---|
| Scale (sole heel-to-bend → model heel-to-toe-joint) | 1.162 | 0.998 |
| Toe-joint axis from the lateral axis, against the sole's bend line (−13.2°) | −35.5° | −16.5° (measured; the frame's z axis would give 0°) |
| Model's own sphere bottoms against the single plantar plane | toes −2.1 mm | calcn ±2.5 mm, forefoot +1.8/+3.8 mm, toes +2.0 mm |
| Metatarsal-region points distal of the toe-joint axis, kept on the forefoot or calcaneus | 9, up to 36 mm | 7, up to 18 mm |
| Lateral offset | Not registered: the sole's long axis is put on the calcaneus x axis | The same |

Toe regions are put on the toes by name. The boundaries between other segments are lines through each joint
centre along its measured axis.

## 3. D'Hondt: the `.osim` alone against the paper's laws, and the port

The paper's simulations evaluate the model through CasADi and add the passive foot laws in MATLAB. A plain
OpenSim run of the nominal `.osim` is therefore a different model. Measured on the nominal 4-segment file:

| Element | Nominal `.osim` in OpenSim | Paper (`CreateCasadiFunctions.m`, `f_PredSim_Gait92_FootModel.m`) |
|---|---|---|
| Plantar fascia | `Ligament`, slack 0.146 m, a 17-point spline × 70 N. It matches the Natali (2010) law within 0.1 % over 1–10 % strain; the largest difference is near slack, where forces are small | Natali (2010) law on the same path (fitted as polynomials) |
| Midtarsal ligaments | 12 OpenSim `Ligament`s. Within 2–7 % of the paper's moment inside ±15°; beyond ±20° they differ (+30°: −106 against −74 N·m) | A fitted bspline (`f_getMtjLigamentMoment_exp5`, −30° to +30°), with exponential range-of-motion torques and 0.1 N·m·s/rad damping |
| MTP passive torque | **None** | −1·q − 0.1·q̇ plus exponential range-of-motion torques (3-segment: −25·q − 2·q̇ plus the same) |

*Correction to the inspection note of 2026-11-04:* both D'Hondt files define a fascia force-length curve. The
earlier XML query missed it. The subject file's curve is a generic, much weaker one (about 48 N at 5 % strain).

**The port** (`foot_models/dhondt_port.py`) applies the paper's laws to the nominal models:
- It switches the 12 midtarsal `Ligament`s off.
- It gives the fascia the Natali law exactly.
- It adds the midtarsal and MTP passive torques as `ExpressionBasedCoordinateForce`s.
- It refuses any input other than the two pinned files.
- It does not port the other joints' passive torques, the muscle settings or the paper's optimal-control
  simulations.

**Verified against the original equations before use** (`tests/test_dhondt_port.py`):
- **The midtarsal ligament moment:**
  - the committed knot table equals the paper's own saved bspline, evaluated with CasADi, at 1,201 angles;
  - in OpenSim, the ported generalized force matches that bspline within 0.15 N·m over ±30°, with and without
    speed;
  - outside ±30° the paper's function is undefined (the saved spline returns 0), and runs flag it
    (`mtj_outside_paper_range`; no run here left the range).
- **The fascia tension** matches a separately transcribed Natali law within 0.05 N + 0.2 %. One known
  difference remains: OpenSim's `Ligament` never pushes, while the paper's smoothed law dips to −0.69 N within
  0.9 mm below slack.
- **MTP:** exact.

## 4. The tasks

Passive below the ankle: muscles are removed. The posture comes from OpenCap's squat (the standing frame, and
knee flexion 30°, 60° and 80°), the same on left and right.
- **Posture-based balance.** The ankle torque is solved so that each foot's centre of pressure lies under the
  body's centre of mass, as in quasi-static standing. The result depends on each body's centre of mass, so it
  compares bodies and postures as much as feet.
- **Controlled loading (the main comparison).** Each foot's centre of pressure is prescribed at 0.30, 0.45, 0.60
  or 0.75 of the sole's heel-to-bend length. The body is held at the pelvis. Every foot model is then loaded at
  the same centre of pressure.

**Why solved, not simulated.** On this soft contact, letting a passive rigid body settle tips it over. With a
whole-body tilt as the only rotation, the centre of pressure moves almost as fast as the centre of mass (about
880 against 920 mm/rad), so that equilibrium is ill-conditioned. The equilibria are therefore solved with damped
Newton (`foot_models/compare_feet.py`), and every one is checked:
- support within 0.034 % of body weight;
- centre of pressure on its target within 0.05 mm.
Whether an equilibrium is stable is not claimed.

## 5. Results

Shares of one foot's load (right; left is the mirror): **heel / arch and midfoot / metatarsals / toes, %.**

**5.1 Internal controls.**
- D'Hondt 3- and 4-segment with the foot locked are the same rigid foot, and give identical results in every
  `.osim`-only and ported combination.
- The two-segment and D'Hondt rigid feet differ at the same centre of pressure, by 3–8 points at 0.45. That
  difference is **entirely the contact stiffness** the sole inherits from each model's own generic contact:
  1.6 × 10⁶ against 2.3 × 10⁵ per sphere. With the stiffness matched, the two-segment foot gives
  50.3 / 32.0 / 13.0 / 4.7, against D'Hondt's 50.2 / 32.0 / 13.2 / 4.6.

**5.2 Controlled loading, 15 mm contact spacing.**

| Model | COP at 0.30 | 0.45 | 0.60 | 0.75 |
|---|---|---|---|---|
| Two-segment, rigid | 67.2 / 31.7 / 1.1 / 0.0 | 45.8 / 39.9 / 12.0 / 2.4 | 32.0 / 36.3 / 21.6 / 10.1 | 20.6 / 30.5 / 27.8 / 21.1 |
| D'Hondt, rigid (3- or 4-segment; `.osim` only or ported) | 70.1 / 25.2 / 4.2 / 0.5 | 50.2 / 32.0 / 13.2 / 4.6 | 34.1 / 33.2 / 20.7 / 12.0 | 20.7 / 30.4 / 27.7 / 21.2 |
| D'Hondt 3-segment ported, MTP free | 70.0 / 25.2 / 4.3 / 0.5 | 49.5 / 32.8 / 14.1 / 3.7 | 31.8 / 35.3 / 24.6 / 8.3 | 17.1 / 31.7 / 38.2 / 13.1 |
| D'Hondt 4-segment ported, midtarsal and MTP free | 69.9 / 25.6 / 4.1 / 0.4 | 48.7 / 34.7 / 12.6 / 4.0 | 30.2 / 39.2 / 21.0 / 9.6 | 15.4 / 36.6 / 32.3 / 15.7 |
| D'Hondt 4-segment `.osim` only, midtarsal and MTP free | 70.5 / 25.3 / 2.5 / 1.7 | 49.2 / 34.8 / 10.4 / 5.6 | 30.5 / 39.1 / 20.1 / 10.2 | 15.6 / 36.2 / 32.5 / 15.6 |

Foot angles: midtarsal 0.3–2.4° (ported) and MTP up to 4.2° (3-segment), within the paper's range. In the
`.osim`-only foot, the MTP joint has no passive torque, and it extends to −6.1° when the forefoot is lightly
loaded (COP at 0.30).

**5.3 Convergence in contact spacing.** **Absolute shares are not converged.** From 15 to 10 mm they change by
up to 6 points; between 7.5 and 5 mm, by up to 3. No single regional share here is better than about ±3 points.

**Paired differences** (two models at the same spacing and centre of pressure) are steadier: heel / arch /
metatarsals / toes, percentage points, at 15 / 10 / 7.5 / 5 mm:

| Difference | COP | 15 mm | 10 mm | 7.5 mm | 5 mm |
|---|---|---|---|---|---|
| 4-segment, midtarsal and MTP free, minus rigid | 0.45 | −1.5/+2.7/−0.6/−0.6 | −1.0/+2.1/−0.8/−0.3 | −1.1/+2.3/−0.8/−0.3 | −1.1/+2.2/−1.0/−0.2 |
| | 0.75 | −5.2/+6.2/+4.6/−5.5 | −4.0/+5.8/+1.3/−3.0 | −4.1/+5.9/+1.2/−3.0 | −3.7/+5.8/−0.1/−2.0 |
| 3-segment, MTP free, minus rigid | 0.45 | −0.7/+0.8/+0.9/−1.0 | −0.4/+0.5/+0.6/−0.7 | −0.5/+0.6/+0.6/−0.7 | −0.4/+0.4/+0.5/−0.5 |
| | 0.75 | −3.6/+1.3/+10.5/−8.1 | −2.8/+1.2/+8.4/−6.8 | −2.8/+1.2/+8.3/−6.6 | −2.4/+0.8/+7.4/−5.8 |

**5.4 Sensitivity** (largest change in any group, percentage points, against each case's baseline):

| Change | Two-segment, COP under COM | Two-segment, COP at 0.45 | D'Hondt 4-segment free, COP under COM | D'Hondt 4-segment free, COP at 0.45 |
|---|---|---|---|---|
| Scale −5 % / +5 % | 3.4 / 2.9 | 0.0 / 0.0 | 4.3 / 2.9 | 0.5 / 0.5 |
| Lateral −5 / +5 mm | 0.0 / 0.0 | 0.0 / 0.0 | 0.4 / 0.4 | 0.1 / 0.0 |
| Sole-plane pitch −2° / +2° | 1.0 / 0.9 | 0.0 / 0.0 | 1.4 / 1.4 | 0.2 / 0.1 |
| Segment boundaries −5 / +5 mm | 0.0 / 0.0 | 0.0 / 0.0 | 0.1 / 0.0 | 0.0 / 0.0 |
| Contact stiffness ×0.5 / ×2 | 0.1 / 0.1 | 0.8 / 1.6 | 1.2 / 0.1 | 2.1 / 2.7 |
| Contact spacing 10 mm (from 15) | 2.9 | 5.9 | 2.7 | 5.0 |

**5.5 Posture-based balance** (centre of pressure under each body's centre of mass):

| Model | Standing | Squat, knee 30° | knee 60° | knee 80° |
|---|---|---|---|---|
| Two-segment, rigid | 20.3 / 30.4 / 27.9 / 21.4 | 18.9 / 29.5 / 28.9 / 22.7 | 25.6 / 33.1 / 25.7 / 15.6 | 36.7 / 37.6 / 19.1 / 6.6 |
| D'Hondt, rigid | 20.6 / 30.4 / 27.7 / 21.2 | 5.5 / 16.3 / 30.8 / 47.3 | 5.7 / 16.2 / 31.5 / 46.6 * | 11.7 / 23.0 / 32.1 / 33.1 * |
| D'Hondt 4-segment ported, free | 14.8 / 36.1 / 33.1 / 16.1 | 0.1 / 7.1 / 63.1 / 29.7 | 0.2 / 8.1 / 62.0 / 29.8 * | 5.3 / 24.5 / 47.4 / 22.8 * |

\* The posture lies outside the D'Hondt model's own ranges: hip flexion 80–100° against 50°, lumbar −34° to −45°
against ±30°.
- The two bodies' centres of mass sit differently over their feet, and the self-test model's multi-level lumbar
  spine was left at 0, since the data's lumbar angle has no single counterpart there. These columns compare
  bodies and postures as much as feet.
- In a real squat a person keeps the centre of pressure near mid-foot. These passive postures don't, which is
  another reason the controlled loading is the main comparison.

## 6. Synergy foot: a five-toe kinematic comparison

The model has no contact, so the sole is registered on bone landmarks. The heel point is on the calcaneus; the
plantar plane runs through the lowest points of the calcaneus and the first and fifth metatarsal heads; the
toe-joint line is fitted through the five MTP joint centres. This differs from the other models' sphere-based
registration (`foot_models/synergy_kinematics.py`).

**Registration:**
- Scale 0.936.
- Toe-joint line at −21.4°, against the sole's bend line at −13.2°.
- 5 of 55 contact points have no bone within 5 mm above them.

**Which bone lies under each region:**
- **Matches:** heel regions → calcaneus; mt1 → M1; mt2 → M2; toe1–toe3 → T1–T3.
- **Mismatches:** mt3 → M3/M4/T3; mt4 → M5/T4/T5; mt5 → T5 or no bone; toe4 → T4 or no bone; toe5 → no bone.
  The sole's lateral regions do not line up with this generic skeleton. Whether that is registration or
  anatomy (a different foot shape) needs a person's measured foot to tell.

**Motion.** Each gain is swept over neutral ±10 % of its coordinate range; the full ranges give far larger
values.

| Gain | Largest region motion relative to the calcaneus | Neighbouring points on different bones, relative change | Toe rotation |
|---|---|---|---|
| 1, ankle flexion | 0 mm | 0 % | 0° |
| 2, abduction | 9.4 mm (toe4) | 51 % | 0° |
| 3, pronation | 16.8 mm (toe1) | 18 % | 0° |
| 4, arching | 9.0 mm (toe4) | 15 % | 0° |
| 5, big-toe rotation | 10.5 mm (toe1) | 21 % | **10.0° on all five toes** |

**What this shows:**
- Under the sole, the Synergy model moves the metatarsals and toes relative to each other and to the
  calcaneus, unlike the two- and four-segment feet, where whole regions move rigidly.
- **All five toes turn together** (one coordinate, the same angle). It is a five-toe topology without
  independent toes.
- The relative motion between neighbouring points on different bones is what the skin and soft tissue between
  bone and sole would have to absorb. It is not a strain the sole itself would see.

## 7. What the results show, and what they do not

Within these simulations only:
- **Freeing the D'Hondt midtarsal joint moves load onto the arch:** about +2 points at a centre of pressure of
  0.45 and about +6 at 0.75, at every contact spacing tried.
- **Freeing the MTP joint moves load from the toes onto the metatarsals:** about −6 to −8 points of toe load at
  0.75.
- **The `.osim`-only and ported 4-segment feet agree within 1 point** at centres of pressure of 0.60 and
  above. Inside ±15° the nominal file's ligaments and fascia are close to the paper's laws. With less load on the
  forefoot they differ by up to 2.2 points (metatarsals and toes at 0.45), because the `.osim` has no MTP torque.
- **These effects are no larger than the modelling uncertainties around them:** contact spacing (up to 6
  points), the contact stiffness the sole inherits (3–8 points between models), and registration scale (3–4
  points when the centre of pressure follows the centre of mass).
- **Not shown:**
  - that any model is more accurate for a real foot;
  - that the sole would read these loads inside a shoe;
  - anything about walking or dynamic loading.

## 8. Limits

- **Contact:** Hertz spheres on a rigid floor, a coarse grid not yet converged, and stiffness inherited from
  each model's own contact. There is no sole, footbed or shoe compliance.
- **Passive below the ankle:** no muscle supports the arch or holds the toes. The ankle torque is a single
  solved number, and the body is rigid in each posture.
- **Registration:**
  - three landmarks, with no lateral registration and one scale for length and width;
  - segment boundaries are lines through joint centres;
  - toe regions are assigned by name.
- **Models:**
  - D'Hondt's other joints' passive torques are not ported, and its squat postures exceed its coordinate ranges;
  - the Synergy foot is kinematic only, with landmark registration on one generic skeleton;
  - Sikidar is not inspected.
- **Data:** one example subject's squat kinematics (OpenCap's example data), mapped onto other bodies.

## 9. Proposed next steps (not started)

1. **One sole contact model for every foot model**, set from the sole's own compliance (the coupon test, or a
   stated assumption), instead of inheriting each model's contact stiffness.
2. **Converge the contact spacing**, at 5 mm or finer, before quoting any absolute share.
3. **Compare with measurement:** a pressure insole or a force plate, standing and squatting, against the
   controlled-loading and posture-based results, with agreement thresholds set before looking at the data.
4. **A muscle-driven tracking simulation** (OpenSim Moco) of the squat on the D'Hondt port, so the arch has
   muscle support and the centre of pressure follows a real movement.
5. **Synergy foot:** per-toe placement in the adapter, a contact model, and a measured foot to register on.
6. **Sikidar:** inspect the package once it is downloaded.

## 10. Reproducing

```
# the pipeline's Python (opensim, numpy, scipy)
python foot_models/dhondt_port.py DHondt_2024_4-segment_foot_fixed_knee.osim ported_4seg.osim
python foot_models/run_comparison.py --selftest model_scaled.osim --dhondt <nominal models folder> \
    --mot squats1_videoAndMocap.mot --sole-r sim/EU42_R_636645a928.sole_sim.json \
    --sole-l sim/EU42_L_40fe8e1d0c.sole_sim.json --sole-r10 <10 mm R> --sole-l10 <10 mm L> --out runs/
python foot_models/run_comparison.py ... --only convergence --spacing-soles <10 mm dir> <7.5 mm dir> <5 mm dir>
python foot_models/synergy_kinematics.py synergy_foot_r.osim sim/EU42_R_636645a928.sole_sim.json -o synergy.json
# tests (they skip without the external models)
DHONDT_NOMINAL_DIR=... python tests/test_dhondt_port.py      # and DHONDT_EXP5=... with casadi for the bspline check
DHONDT_NOMINAL_DIR=... SYNERGY_MODEL=... python tests/test_foot_comparison.py
python tests/test_sim_osim.py
```

Soles at other spacings come from `sole_sim.py export ... --spacing 10` (the generator's Python).
