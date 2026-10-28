# Knee joint load: the first slice of the load model

The knee-first slice of `docs/design-joint-load-stress-model.md`, built on the muscle stage. Status: **built,
Tier C, not validated against measured joint forces**. What it gives is the change in one person's knee load
between scenarios on the same replayed motion, never an absolute clinical number.

```bash
python -m rehabtwin joint-load out/s02 --rep 2 --person people/P01 \
    --fat-change-kg -5 --strengthen quadriceps_r=1.2 --strengthen quadriceps_l=1.2   # GRF band ±0.10 by default
```

Results go into the muscle study (`out/s02/muscles/study.json` → `joint_load`, and the "Knee joint load" section
of `muscles.html`).

## What is computed

The muscle stage (`rehabtwin/muscles.py`) estimates the ground forces, then runs inverse dynamics and static
optimisation. On those muscle forces, OpenSim's Joint Reaction analysis gives the force the femur exerts on the
tibia, including every muscle force, the estimated ground forces, gravity and the segments' inertia
(`rehabtwin/joint_load.py`). Per knee:

| Value | Definition |
|---|---|
| peak compression (N, ×BW) | the largest axial component of that force, along the tibia (−y in the tibia frame) |
| knee flexion at the peak, time of the peak | from the motion |
| impulse (N·s) | compression integrated over the analysed rep |
| resultant, AP and ML shear | magnitude and the other two components |
| patellofemoral peak (N) | the force holding the patella to the femur |

The quadriceps reach the tibia through the last segment of their paths (patella to tibial tuberosity), so the
patellar tendon's pull is in the tibiofemoral force. A test pins the frames and signs. With ideal torque actuators
instead of muscles, the reaction must equal the leg's ground force less the shank and foot weight, and it does
within 2 % of the ground force at every checked frame. In the prototype it matched within about 1 N.

What it is not:

- no ligaments, no cartilage contact model, no medial/lateral split (that needs contact points from imaging,
  Lerner et al. 2015);
- the patella moves with the knee angle, so the patellofemoral force is the model's, not a contact force;
- ground forces are estimated (quasi-static double stance): valid for slow two-footed exercises such as squats,
  not for walking, so the walking evidence below can't be reproduced here.

## Can the peak be trusted?

The Joint Reaction arithmetic is checked (above); the weak link is the muscle forces static optimisation
estimates. Every knee's peak therefore carries its diagnostics (`baseline_diagnostics`, and per run under
`knee_load.diagnostics`):

| Diagnostic | Why |
|---|---|
| knee-crossing muscles at capacity at the peak (activation ≥ 0.98), and the share of frames with one | a muscle at its limit pushes the moment onto its synergists and reserves |
| knee reserve torque's share of the knee moment, at the peak and at most | the muscles could not carry the moment; static optimisation inflates their forces |
| compression at the peak by source | each knee-crossing group's pull on the shank and foot along the tibia, the ground force less the shank and foot weight, and the rest (inertia, reserves, constraints). In the prototype the rest was under 1 N, so the sources account for the whole joint reaction |
| quadriceps moment arm at the peak | a small moment arm in deep flexion means a large quadriceps force for the same knee moment |
| peak resultant against the in-vivo band | instrumented knee implants (Bergmann et al. 2014, 8 subjects, 'High 100' standard loads): peak resultant 3.4–4.3 BW in daily activities other than jogging, knee bends included. A plausibility band, not a limit: they are implant patients |

A knee is **reportable** only when no knee-crossing muscle is at capacity at the peak and reserve torque carries
at most 10 % of the knee moment there. Otherwise its change is not stated, not even within the person. A peak
above the in-vivo band is shown as model-limited.

A known bias of this model: the quadriceps path runs over the patella to the tibia, so the patellar tendon
carries the full quadriceps tension. In cadaver knees it carries about 0.7 of it at 90° of flexion (Huberti et
al. 1984). Deep-flexion compression from the quadriceps is therefore likely overestimated, and the model's
quadriceps moment arm falls from about 4.5 cm near extension to about 2.1 cm at 90° (gastrocnemius at 90°:
3.3 cm).

## Scenarios

Each scenario is a variant of the muscle study, compared with the measured baseline on the same motion:

| Scenario | What changes in the model | How it is reported |
|---|---|---|
| `--fat-change-kg` | The person's DXA regional fat with that much fat added or removed, each region in proportion to its fat (an assumption: where a person loses fat first varies). Each region's segments lose that share of their mass; inertia scales with mass, segment shape and centre of mass stay. | Model-computed change in knee load and body mass. The published walking evidence (Messier et al. 2005: about 4:1) is quoted beside it, never as output. |
| `--strengthen GROUP=F` | That group's maximum isometric forces × F (1 < F ≤ 2). | Effort (fraction of the group's capacity used), with the load change shown as it comes out: stronger muscles can raise compression while easing effort. |
| both | Fat model and stronger groups together. | Both readings. |

- A fat scenario needs a whole-body DXA table with every region's fat (`person dxa`). Without it the scenario is
  refused: there is no body-weight slider. The change is limited to half the scanned fat.
- Every scenario runs again with the right foot's share of the load shifted ±0.10 (`--grf-sensitivity`). A change
  is called robust when it keeps its sign and is at least 2 % under every split.
- Assistance what-ifs keep their own gates: clinician safety flags and bone-quality derating
  (`docs/accuracy.md`). A safety flag at a knee is printed with that knee's numbers.

## Results

RESULTS

## Red lines (from the design, applied)

- The outputs are model estimates for clinician discussion. They are never a weight-loss or exercise
  prescription, and they make no claim about disease progression.
- Strengthening is never reported as "load down"; effort is its output.
- The Messier figure is published evidence beside the model's number, never the model's number.
- Fat provenance (measured DXA, the allocation assumption) is part of every fat scenario's output.

## Next

- Medial/lateral split: contact points from the person's imaging (`limb_alignment` and knee geometry).
- Measured ground forces (force plates or insoles) for anything beyond slow two-footed exercises, walking first.
- Gait adaptation to weight change needs predictive simulation, not replay.
- Hip and ankle loads labelled unvalidated, then the spine.
