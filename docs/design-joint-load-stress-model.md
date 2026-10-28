# Design — joint load & stress model ("bridge simulation" for the body)

> Filed 2026-10-28. Design spec for a scenario/what-if load model:
> body composition and muscle parameters in → per-joint forces,
> load distribution and (Tier-A) tissue stress out. Status: **design,
> not built, not validated**. An illustrative demo with deliberately
> simplified arithmetic lives in `examples/joint-load-demo/`.

## The bridge analogy, made precise

A bridge simulation takes dead load (structure weight) + live load
(traffic) + material properties, and outputs force paths and stress
per member. The body version:

| Bridge | Body (this model) |
|---|---|
| Dead load | Segment masses/inertias — **including fat mass and its distribution** (`fat-distribution/` Tier-A measured or Tier-B estimated, labelled) |
| Live load | Ground reaction forces + movement task (gait, squat, stairs) |
| Beams/cables | Bones (compression members) and muscles (active cables whose tension **adds** joint compression) |
| Member forces | Per-joint reaction forces: hip, knee (medial/lateral, patellofemoral), ankle, spine levels |
| Stress check | Optional Tier-A FE: cartilage contact pressure, bone stress from imaging geometry |
| Retrofit scenario | "Lose X kg fat", "strengthen muscle group Y by Z%", "add AFO/exo torque" → rerun and compare |

## Pipeline (all catalogued already)

```
twin manifest (mass distribution, limb_alignment, muscle_parameters,
               bone_quality, devices_and_prostheses, safety_flags)
  + session motion (IK kinematics) + GRF (force plates / instrumented
    insoles / estimated, labelled)
  → OpenSim inverse dynamics (joint moments)
  → muscle forces (static optimisation; CEINMS if EMG-calibrated)
  → Joint Reaction Analysis (per-joint forces; medial/lateral knee
    via subject-specific contact-point models, Lerner-style)
  → outputs per joint: peak/impulse in N and ×BW, medial:lateral
    ratio, cumulative load per 1,000 steps / per km
  → OPTIONAL Tier-A: FE cartilage/bone stress (imaging geometry only)
```

## What the evidence says the scenarios will show

1. **Fat loss reduces joint load superlinearly per step.** In the
   Messier weight-loss cohort, each 1 lb of weight lost produced a
   **4 lb reduction in knee compressive load per step** (≈48,000 lb
   less cumulative load per mile for a 10 lb loss, per knee). Mass
   enters the model through segment inertias *and* gait kinetics —
   which is why the effect exceeds simple proportionality.
2. **Muscle strengthening does NOT reliably reduce total joint
   compression — and the model must not pretend it does.**
   Quadriceps-strengthening trials show pain/function improve while
   measured knee compressive force stays flat or *increases*
   (stronger muscles pull harder across the joint). Muscle's real
   contributions, which the model should report separately:
   - **effort** (% of max capacity for the same task — falls as
     strength rises; this is the fatigue/endurance benefit),
   - **distribution** (medial:lateral load share, contact-point
     excursion — hip-abductor/quadriceps strength relates to these),
   - **stability margin** (resistance to perturbation, frontal-plane
     control).
   Reporting "total load ↓" from a strengthening scenario would be a
   false claim; reporting effort/distribution/stability is honest.
3. **Obesity changes load paths, not just magnitudes**: coupled
   MSK→FE knee simulations with obese gait show ligament loads more
   than doubling at some stance instants and cartilage-loading
   changes — which is why fat *distribution* (segment-level), not
   just total mass, is an input. A single "BMI slider" is not an
   acceptable model input.
4. **Validation anchor exists but is narrow**: model knee contact
   forces have been checked against instrumented knee implants
   (Grand-Challenge-type data; subject-specific alignment/contact
   points matter, Lerner 2015). Hip/ankle/spine in-vivo validation
   is far thinner. Consequence: **within-person scenario deltas are
   the trustworthy output; absolute values carry wide uncertainty**
   and must be displayed with their validation status per joint.

## Outputs (per scenario, always side-by-side with baseline)

- Per-joint peak force and impulse (N, ×BW), medial:lateral knee ratio
- Cumulative load per distance (the "48,000 lb per mile" view)
- Muscle effort (%MVC-equivalent) for key groups; stability margin
- Bridge-style visualisation: skeleton heat-map by joint load +
  ranked bar list — generated from the same numbers, never decorative
- Every figure labelled: model tier, input provenance (measured vs
  estimated fat), joint-specific validation status

## Scenario definitions (v1)

| Scenario | Parameter change | Expected honest output |
|---|---|---|
| Fat change | Segment fat masses ± (from fat-distribution pipeline; re-run gait or scaled kinetics) | Joint loads ↓/↑ (Messier-anchored at knee), effort ↓/↑ |
| Muscle training | `force_scale` per muscle group in `muscle_parameters` | Effort ↓, stability ↑, total compression ≈/↑ (shown, not hidden) |
| Combined | Both | Load ↓ *and* effort ↓ — the actual rehabilitation story |
| Assistive torque | AFO/exo torque profile (Batches 2/7 design loops) | Joint moment offloaded; muscle effort ↓; device torque shown as its own load path |

## Red lines

- Scenario outputs are **model estimates for clinician discussion**,
  never weight-loss or exercise prescriptions, never disease-
  progression claims (weight loss has *not* been shown to slow OA
  progression; pain/function claims belong to clinicians, D-03).
- No scenario from Tier-B-estimated fat presented with Tier-A
  confidence; provenance labels are part of the output, not a footnote.
- `safety_flags` and `bone_quality` derating gate every scenario
  involving assistance torque (accuracy.md red lines apply).
- Absolute joint-force numbers for hip/spine displayed as
  *unvalidated estimates* until a validation path exists.

## Build order

1. Knee-first vertical slice (best validation): manifest-driven
   OpenSim gait → Joint Reaction → baseline vs fat-change scenario.
2. Add muscle-effort/distribution outputs + combined scenario.
3. Hip/ankle, then spine (with unvalidated labelling); FE cartilage
   stress only as Tier-A offline study.
4. Exo/AFO torque scenario joins the Batch-7 design loop.

## Sources (accessed 2026-10-28)

- Messier et al., Arthritis Rheum (2005): 1 lb lost → 4 lb/step knee
  load reduction; WFU summary (48,000 lb/mile per 10 lb)
- Lerner et al. (2015): subject-specific alignment/contact points vs
  instrumented-knee medial/lateral forces (OpenSim Joint Reaction)
- Quadriceps strengthening vs knee compressive force — ECU thesis
  line and RCT literature (pain/function ↑, compressive load ≈/↑);
  knee-OA contact-mechanics/strength associations, PMC4817272
- Obesity MSK→FE knee framework (weight factors, ligament loads,
  cartilage loading); obese-children tibiofemoral simulations,
  PMC3833069
- Joint-loading regression in overweight/obese gait (PMC12634799) —
  screening-grade surrogates only
