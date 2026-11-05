<!-- SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors -->
<!-- SPDX-License-Identifier: CERN-OHL-S-2.0 -->

# Foot models on the virtual sole: a controlled comparison

**2026-11-04. Experimental. No foot model is selected by this comparison.**

**What this is:** the same sensor-sole design (EU 42, `EU42 R 636645a928` / `EU42 L 40fe8e1d0c`), loaded onto
different OpenSim foot models through the same adapter (`sole_sim.py`), under the same quasi-static, passive
loading.
- **Contact:** one sole-contact model on every foot model (`ASSUMED_CONTACT_V1`), **assumed, not measured**.
  The models' own native contact is a separate sensitivity analysis.
- **What the main experiment is:** a passive foot with a prescribed centre of pressure. It is a **control**, not
  a predicted movement. No muscle-driven squat or gait was simulated, and none of these results is one.

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

## 4. Contact, and the tasks

**The assumed sole contact** (`sole_sim.ASSUMED_CONTACT_V1`), the same on every foot model. It is **assumed,
not measured**: it stands in for the sole stack plus the plantar soft tissue until the coupon test gives a
measured curve.
- **Law:** each sphere carries p = 100 kPa × (indentation / 3 mm)^1.5 over its grid cell (the Hertz exponent).
  Its stiffness is calibrated numerically in OpenSim, so the law is the same at any spacing.
- **Smoothing:** constant-contact term 1e-8 and Hertz smoothing 2000 /m, instead of OpenSim's defaults (1e-5 and
  300).
- **Dissipation and friction:** the values the two-segment and D'Hondt models already share.

**Why the smoothing changed.** All three models use OpenSim's default smoothing, which is not Hertz-like at
millimetre scale:
- it acts like a minimum indentation of about 3 mm;
- a sphere 2 mm **above** the floor still carries 22 % of its force at 3 mm indentation.
With the assumed values, the law is within about 1 % of Hertz from 1 mm indentation, and a sphere above the floor
carries almost nothing (`tests/test_sim_osim.py`, `AssumedContact`).

**Native contact** (the sensitivity analysis): each model's own contact parameters, including that smoothing,
with the stiffness scaled so the sole keeps the generic foot's overall contact stiffness. Per sphere, at 15 mm
spacing:

| | Two-segment | D'Hondt |
|---|---|---|
| Native | 2.3 × 10⁵ | 1.6 × 10⁶ |
| Assumed (cells larger on the two-segment foot, scale 1.16) | 4.5 × 10⁶ | 3.3 × 10⁶ |

**The tasks.** Every task is passive below the ankle: muscles are removed. The posture comes from OpenCap's squat
(the standing frame, and knee flexion 30°, 60° and 80°), the same on left and right.
- **Controlled loading: the main experiment, and a control.** Each foot's centre of pressure is prescribed at
  0.30, 0.45, 0.60 or 0.75 of the sole's heel-to-bend length. The body is held at the pelvis, so every foot model
  is loaded at the same centre of pressure. **It does not predict where a person's centre of pressure would
  be.**
- **Posture-based balance.** The ankle torque is solved so that each foot's centre of pressure lies under the
  body's centre of mass. It depends on each body's centre of mass, so it compares bodies and postures as much as
  feet. It is a passive quasi-static posture, not a squat movement.

**Why solved, not simulated.** On soft contact, letting a passive rigid body settle tips it over. With a
whole-body tilt as the only rotation, the centre of pressure moves almost as fast as the centre of mass (about
880 against 920 mm/rad), so that equilibrium is ill-conditioned. The equilibria are therefore solved with damped
Newton (`foot_models/compare_feet.py`).
- **All 244 runs solved:** support within 0.034 % of body weight, centre of pressure on target within 0.05 mm.
- No midtarsal angle left the paper's ±30° range.
- Whether an equilibrium is stable is not claimed.

## 5. Results

Shares of one foot's load (right; left is the mirror): **heel / arch and midfoot / metatarsals / toes, %.**

**5.1 Internal controls (assumed contact).**
- D'Hondt 3- and 4-segment with the foot locked are the same rigid foot. They give identical results in every
  `.osim`-only and ported combination.
- The two-segment and D'Hondt rigid feet agree within 0.2 points at every spacing and centre of pressure. Under
  native contact they differed by 3–8 points, which was entirely the contact each model brought with it.

**5.2 Controlled loading, assumed contact, 15 mm spacing.** These are discretisation-sensitive (5.3).

| Model | COP at 0.30 | 0.45 | 0.60 | 0.75 |
|---|---|---|---|---|
| Two-segment, rigid | 66.6 / 32.1 / 1.2 / 0.1 | 45.1 / 40.2 / 12.7 / 2.0 | 31.9 / 36.3 / 21.4 / 10.3 | 20.6 / 30.5 / 27.4 / 21.4 |
| D'Hondt, rigid (3- or 4-segment; `.osim` only or ported) | 66.4 / 32.4 / 1.1 / 0.0 | 45.1 / 40.1 / 12.7 / 2.0 | 31.9 / 36.3 / 21.4 / 10.4 | 20.6 / 30.5 / 27.4 / 21.4 |
| D'Hondt 3-segment ported, MTP free | 66.4 / 32.5 / 1.1 / 0.0 | 44.6 / 40.5 / 13.7 / 1.1 | 28.6 / 38.0 / 29.5 / 3.9 | 13.9 / 33.0 / 46.3 / 6.8 |
| D'Hondt 4-segment ported, midtarsal and MTP free | 66.6 / 32.0 / 1.3 / 0.0 | 42.1 / 45.9 / 10.2 / 1.8 | 23.2 / 50.7 / 19.2 / 6.9 | 6.8 / 50.8 / 29.5 / 12.9 |
| D'Hondt 4-segment `.osim` only, midtarsal and MTP free | 66.8 / 32.0 / 0.6 / 0.6 | 42.3 / 47.2 / 6.6 / 3.9 | 23.5 / 51.6 / 16.1 / 8.8 | 7.4 / 50.6 / 27.7 / 14.3 |

Foot angles (ported): midtarsal up to 2.4°, MTP up to 1.8°. The `.osim`-only foot has no MTP passive torque, and
its MTP extends to −2.3° at a centre of pressure of 0.30.

**5.3 Discretisation sensitivity** (contact spacing 15, 10, 7.5 and 5 mm). This is the sensitivity to one
modelling choice. **It is not a confidence interval and not the total uncertainty.** With the assumed contact,
absolute shares changed:
- by up to 7.9 points from 15 to 10 mm;
- by up to 2.5 points from 10 to 7.5 mm;
- by up to 3.4 points from 7.5 to 5 mm.

They are not converged. Paired differences (two models, same spacing and centre of pressure), heel / arch /
metatarsals / toes in percentage points, at 15 / 10 / 7.5 / 5 mm:

| Difference | Contact | COP | 15 mm | 10 mm | 7.5 mm | 5 mm |
|---|---|---|---|---|---|---|
| 4-segment, midtarsal and MTP free, minus rigid | assumed | 0.45 | −3.0/+5.8/−2.6/−0.2 | −3.1/+6.2/−2.8/−0.3 | −3.2/+6.2/−2.5/−0.5 | −3.2/+6.3/−2.9/−0.2 |
| | assumed | 0.75 | −13.9/+20.3/+2.1/−8.5 | −14.1/+22.3/−2.0/−6.2 | −14.1/+22.1/−1.1/−6.8 | −13.4/+21.9/−3.5/−5.0 |
| | native | 0.45 | −1.5/+2.7/−0.6/−0.6 | −1.0/+2.1/−0.8/−0.3 | −1.1/+2.3/−0.8/−0.3 | −1.1/+2.2/−1.0/−0.2 |
| | native | 0.75 | −5.2/+6.2/+4.6/−5.5 | −4.0/+5.8/+1.3/−3.0 | −4.1/+5.9/+1.2/−3.0 | −3.7/+5.8/−0.1/−2.0 |
| 3-segment, MTP free, minus rigid | assumed | 0.75 | −6.7/+2.5/+18.9/−14.6 | −6.1/+3.9/+14.6/−12.3 | −6.3/+3.7/+15.6/−13.0 | −5.4/+3.2/+13.2/−11.0 |
| | native | 0.75 | −3.6/+1.3/+10.5/−8.1 | −2.8/+1.2/+8.4/−6.8 | −2.8/+1.2/+8.3/−6.6 | −2.4/+0.8/+7.4/−5.8 |
| Two-segment minus D'Hondt, both rigid | assumed | 0.45 | −0.0/+0.1/−0.0/−0.0 | −0.2/+0.2/−0.0/−0.1 | −0.1/+0.2/−0.0/−0.1 | −0.1/+0.2/+0.0/−0.1 |
| | native | 0.45 | −4.4/+7.8/−1.2/−2.3 | −3.0/+5.5/−1.0/−1.5 | −3.5/+6.4/−1.2/−1.8 | −3.1/+5.8/−1.3/−1.4 |

**Convergence criterion for finer spacings** (written on 2026-11-05, before the 3.75 and 2.5 mm runs, and not to
be changed after them): “Converged: the largest change between the two finest spacings is at most 1.0
percentage point, for every absolute share and every paired difference in the section 5.3 table, and the
changes shrink from one step to the next.” If it is not met, the result is reported as not converged. Nothing is
tuned to make it pass. How it is evaluated, also fixed before the runs:
- **Quantities:** the four absolute shares of every discretisation case (4 models × centre of pressure 0.45 and
  0.75 × assumed and native contact: 64 values), and the 32 paired differences of the table above (8 rows × 4
  shares).
- **Change:** the absolute difference between successive spacings, taken from the results' values (two
  decimals), not from the rounded table. "At most 1.0" means at most 1.00 at the step from 3.75 to 2.5 mm, for
  every quantity.
- **Shrinking:** the largest change over all 96 quantities is strictly smaller at each step than at the step
  before, over the steps 7.5 → 5, 5 → 3.75 and 3.75 → 2.5 mm. Counted from 15 mm, it already fails before any new
  run: 8.06, 2.63, then 3.45 points.

**5.4 Sensitivity** (largest change in any group, percentage points, against each case's assumed-contact
baseline at 15 mm):

| Change | Two-segment, COP under COM | Two-segment, COP at 0.45 | D'Hondt 4-segment free, COP under COM | D'Hondt 4-segment free, COP at 0.45 |
|---|---|---|---|---|
| Scale −5 % / +5 % | 3.1 / 2.8 | 0.2 / 0.2 | 4.1 / 3.6 | 0.8 / 0.9 |
| Lateral −5 / +5 mm | 0.0 / 0.0 | 0.1 / 0.1 | 0.3 / 0.4 | 0.1 / 0.1 |
| Sole-plane pitch −2° / +2° | 1.0 / 0.9 | 0.8 / 0.5 | 1.3 / 1.4 | 0.5 / 0.5 |
| Segment boundaries −5 / +5 mm | 0.0 / 0.0 | 0.0 / 0.0 | 0.2 / 0.1 | 0.0 / 0.0 |
| Assumed contact stiffness ×0.5 / ×2 | 0.1 / 0.3 | 0.6 / 1.7 | 5.3 / 4.0 | 1.2 / 0.8 |
| **Native contact instead of the assumed** | 0.5 | 0.7 | **14.3** | **11.2** |
| Contact spacing 10 mm (from 15) | 3.1 | 7.9 | 2.7 | 7.7 |

**5.5 Native contact (sensitivity analysis): controlled loading, 15 mm.**

| Model | COP at 0.30 | 0.45 | 0.60 | 0.75 |
|---|---|---|---|---|
| Two-segment, rigid | 67.2 / 31.7 / 1.1 / 0.0 | 45.8 / 39.9 / 12.0 / 2.4 | 32.0 / 36.3 / 21.6 / 10.1 | 20.6 / 30.5 / 27.8 / 21.1 |
| D'Hondt, rigid | 70.1 / 25.2 / 4.2 / 0.5 | 50.2 / 32.0 / 13.2 / 4.6 | 34.1 / 33.2 / 20.7 / 12.0 | 20.7 / 30.4 / 27.7 / 21.2 |
| D'Hondt 3-segment ported, MTP free | 70.0 / 25.2 / 4.3 / 0.5 | 49.5 / 32.8 / 14.1 / 3.7 | 31.8 / 35.3 / 24.6 / 8.3 | 17.1 / 31.7 / 38.2 / 13.1 |
| D'Hondt 4-segment ported, midtarsal and MTP free | 69.9 / 25.6 / 4.1 / 0.4 | 48.7 / 34.7 / 12.6 / 4.0 | 30.2 / 39.2 / 21.0 / 9.6 | 15.4 / 36.6 / 32.3 / 15.7 |
| D'Hondt 4-segment `.osim` only, midtarsal and MTP free | 70.5 / 25.3 / 2.5 / 1.7 | 49.2 / 34.8 / 10.4 / 5.6 | 30.5 / 39.1 / 20.1 / 10.2 | 15.6 / 36.2 / 32.5 / 15.6 |

**5.6 Posture-based balance, assumed contact** (centre of pressure under each body's centre of mass).

| Model | Standing | Squat, knee 30° | knee 60° | knee 80° |
|---|---|---|---|---|
| Two-segment, rigid | 20.2 / 30.3 / 27.6 / 21.9 | 19.0 / 29.1 / 30.4 / 21.4 | 26.7 / 29.4 / 31.5 / 12.4 | 39.4 / 30.5 / 24.7 / 5.3 |
| D'Hondt, rigid | 20.6 / 30.4 / 27.5 / 21.5 | 4.7 / 17.0 / 35.4 / 42.9 | *out of range* | *out of range* |
| D'Hondt 4-segment ported, free | 6.2 / 50.4 / 30.1 / 13.2 | 0.0 / 11.9 / 60.8 / 27.3 | *out of range* | *out of range* |

- **Out of range:** the 60° and 80° frames exceed the D'Hondt model's own coordinate ranges (hip flexion 80–100°
  against 50°, lumbar −34° to −45° against ±30°). They were run, flagged (`posture_outside_model_range` in the
  results) and are **not interpreted**: nothing here describes valid deep-squat behaviour.
- **Confounds:** the bodies' centres of mass sit differently over their feet, and the self-test model's
  multi-level lumbar spine was left at 0. These are passive postures; a person keeps the centre of pressure
  nearer mid-foot in a real squat.

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

Within these simulations only, and for a passive foot with a prescribed centre of pressure:
- **Directions consistent across both contact models and all four spacings:**
  - freeing D'Hondt's midtarsal joint moves load from the heel onto the arch;
  - freeing the MTP joint moves load from the toes onto the metatarsals.
- **Sizes depend strongly on the contact model.** At a centre of pressure of 0.75, the arch share rises by +20 to
  +22 points with the assumed contact, against +6 with native contact. At 0.45 the figures are +6 against +2. The
  native smoothing lets spheres that are not touching carry load, which hides the arch's deformation. Which
  size is closer to a real foot is not known: **neither contact model is measured.**
- **With one contact law, the rigid two-segment and D'Hondt feet are equivalent.** Their earlier differences were
  the contact each model brought with it.
- **The `.osim`-only and ported 4-segment feet differ by up to 3.6 points** with the assumed contact (0.7 at a
  centre of pressure of 0.30, 3.6 at 0.45, 3.0 at 0.60, 1.8 at 0.75), most of it metatarsal load moved onto the
  toes: the `.osim` has no MTP torque. With native contact the difference is up to 2.2 points.
- **Not shown:**
  - that any model is more accurate for a real foot;
  - where a person's centre of pressure would be, which the controlled experiment prescribes;
  - anything about a muscle-driven squat, walking, deep squats, or contact inside a shoe.

## 8. Limits

- **Contact:**
  - the assumed law is a stated assumption, not a measurement;
  - Hertz spheres on a rigid floor;
  - not converged in spacing (5.3);
  - no sole, footbed or shoe compliance;
  - native contact differs from it by up to 14 points (5.4).
- **Passive below the ankle:** no muscle supports the arch or holds the toes. The ankle torque is a single
  solved number, and the body is rigid in each posture.
- **Registration:**
  - three landmarks, with no lateral registration and one scale for length and width;
  - segment boundaries are lines through joint centres;
  - toe regions are assigned by name.
- **Models:**
  - D'Hondt's other joints' passive torques are not ported, and its 60° and 80° squat frames exceed its
    coordinate ranges;
  - the Synergy foot is kinematic only, with landmark registration on one generic skeleton;
  - Sikidar is not inspected.
- **Data:** one example subject's squat kinematics (OpenCap's example data, which has no force plates), mapped
  onto other bodies.

## 9. Next steps (not started)

1. **Validation against measurement**, in three separate stages (`VALIDATION_PLAN.md`):
   - a force-plate comparison of the current foot-to-ground model first (OpenCap LabValidation as first choice);
   - regional plantar pressure, barefoot;
   - foot–insole contact.
2. **Replace the assumed contact law** with the sole's measured response once the coupon test exists. Keep the
   assumed law as the comparison's reference.
3. **Converge the contact spacing** (5 mm or finer) before quoting absolute shares.
4. **A muscle-driven tracking simulation** (OpenSim Moco) of the squat on the D'Hondt port, reported separately
   from this passive control.
5. **Synergy foot:** per-toe placement in the adapter, a contact model, and a measured foot to register on.
6. **Sikidar:** inspect the package once it is downloaded.

## 10. Reproducing

- **Hashes:** every external input (models, the paper's saved function, the transcribed source files,
  kinematics, soles), the port's deterministic output, and the tool versions are in
  `foot_models/PROVENANCE.json`. `tests/test_dhondt_port.py` checks the port against them.
- **Test record:** `TEST_RUNS.md` lists which tests ran and which skipped in each environment, and why. Several
  need the external models, or CasADi, and skip without them.
- **Results:** `foot_models/results_2026-11-04.json` holds the summary of all 244 runs that the tables here
  come from.
- **On another machine:** `workstation/setup.sh` fetches every external input at its pinned commit and checks it
  against `PROVENANCE.json`. It rebuilds the two-segment model from the pipeline at the recorded commit, and
  `workstation/run_comparison.sh` then runs the comparison (`workstation/README.md`). The rebuilt model's bytes
  depend on the machine, so its hash can differ from the recorded one. The differences are in the fitted marker
  positions and the last digit of muscle lengths, which the comparison does not use. On a laptop without
  AVX-512 the hash differed, and all 244 runs still matched the results file in every field.
- **Resumable runs:** each case's folder is named from a fingerprint of its inputs, parameters, code and OpenSim
  version (`foot_models/case_store.py`). A rerun after an interruption reuses finished cases, never across a
  change to any of these. `--jobs N` runs cases in parallel. A run killed partway and resumed, with three
  workers, reproduced the 32 controlled-loading cases of the results file in every field.
- **Soles at other spacings** are committed in `sim/spacing/`. Regenerating the EU 42 R board and exporting it at
  15 and 5 mm reproduced the committed files byte for byte.

```
# the pipeline's Python (opensim, numpy, scipy)
python foot_models/dhondt_port.py DHondt_2024_4-segment_foot_fixed_knee.osim ported_4seg.osim
python foot_models/run_comparison.py --selftest model_scaled.osim --dhondt <nominal models folder> \
    --mot squats1_videoAndMocap.mot --sole-r sim/EU42_R_636645a928.sole_sim.json \
    --sole-l sim/EU42_L_40fe8e1d0c.sole_sim.json --sole-r10 sim/spacing/10mm/EU42_R_636645a928.sole_sim.json \
    --sole-l10 sim/spacing/10mm/EU42_L_40fe8e1d0c.sole_sim.json \
    --spacing-soles sim/spacing/10mm sim/spacing/7.5mm sim/spacing/5mm --out runs/ [--jobs N]
# or, on a machine set up with workstation/setup.sh:
workstation/run_comparison.sh
python foot_models/synergy_kinematics.py synergy_foot_r.osim sim/EU42_R_636645a928.sole_sim.json -o synergy.json
# tests (several skip without the external models; see TEST_RUNS.md)
DHONDT_NOMINAL_DIR=... python tests/test_dhondt_port.py
DHONDT_EXP5=... <CasADi's Python> tests/test_dhondt_port.py   # a separate environment: OpenSim 4.6 carries CasADi 3.7
DHONDT_NOMINAL_DIR=... SYNERGY_MODEL=... python tests/test_foot_comparison.py
python tests/test_sim_osim.py
```

Soles at other spacings come from `sole_sim.py export ... --spacing <mm>` (the generator's Python), or
`workstation/setup.sh soles <mm>`.
