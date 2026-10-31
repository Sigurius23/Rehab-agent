# Anatomy audit — Batch 7: neuromotor conditions (NM)

> Filed 2026-10-28. Seventh systematic batch from
> [`anatomy-issues-checklist.md`](anatomy-issues-checklist.md):
> NM-01…NM-15. 15 issues.

## Headline findings

1. **Neuromotor conditions are a *driver layer*, not new geometry.**
   Every NM item decomposes into parameter families already adopted in
   earlier batches — per-muscle weakness (max-force scaling),
   contracture (passive stiffness / fibre length), bone deformity
   (Torsion Tool, Batch 2), foot deformity (Batch 2) — plus exactly one
   genuinely new ingredient: **spasticity as velocity-dependent reflex
   feedback** (personalised feedback gains fitted from instrumented
   stretch assessments; demonstrated in OpenSim CP models and, at the
   research frontier, a closed-loop NEURON+OpenSim spinal model that
   reproduces clinical Tardieu/pendulum tests in silico).
2. **Predictive simulation is the CP state of the art**: MRI-based
   neuro-musculoskeletal models + predictive gait simulation showed,
   in a crouch-gait case study, that altered muscle–tendon properties
   (not motor-control simplification alone) caused the crouch pattern;
   personalised models also improved femoral-derotation surgical
   decisions in the 254-limb cohort (Batch 2). Duchenne simulations
   (2025) likewise reproduce the three clinical gait patterns only when
   weakness *and* contractures are combined.
3. **This batch feeds the exoskeleton directly**: foot-drop and
   Charcot-Marie-Tooth predictive simulations already optimise ankle
   assistive-torque profiles per patient (simulated metabolic cost
   −9.9% in CMT). That is precisely our exo design loop — with
   clinician gating, because all NM causes are clinical diagnoses the
   twin must never make.

| ID | Verdict | Model / evidence | Twin decision |
|---|---|---|---|
| NM-01 CP crouch gait | MODEL EXISTS | MRI-based CP neuro-MSK models + predictive simulation (crouch attributed to muscle–tendon properties); muscle-function analyses vs unimpaired gait | Impairment-parameter set (weakness/contracture/bone) on personalised model; predictive sim research-only |
| NM-02 CP spastic equinus/patterns | MODEL EXISTS | CP spasticity+contracture instrumented-assessment models (below) + foot deformity family (Batch 2) | Same parameter set; equinus = ankle parameter subset |
| NM-03 Stroke hemiparesis | ADAPT | Predictive sims of unilateral weakness reproduce post-stroke gait asymmetry/metabolic effects (SimTK post-stroke project; Moco) | Per-side weakness scaling from strength/EMG assessment; asymmetry = model output |
| NM-04 Parkinsonian stoop/camptocormia | RESEARCH ONLY | Forward-dynamics model with muscle-tone vectors + neural controller (OpenSim/SCONE, 2023) explores PD posture hypotheses | Trunk-flexion posture metrics recorded; tone/rigidity claims excluded |
| NM-05 Foot drop | MODEL EXISTS | OpenSim dorsiflexor-weakness simulations quantify compensations and design AFO/powered-AFO torque (incl. patient-specific SMA-AFO torque design) | Tibialis-anterior strength parameter; AFO/exo ankle torque derived by simulation, clinician-approved |
| NM-06 Muscular dystrophy | ADAPT | DMD predictive sims: weakness+contractures reproduce the 3 longitudinal gait patterns (137 measures, 30 boys, 2025) | Progressive weakness/contracture parameter trajectory; serial re-fitting |
| NM-07 Spinal muscular atrophy | PARAMETER (sparse) | No dedicated SMA model found; proximal-weakness distribution fits the same weakness-parameter framework | Weakness distribution parameters; specialist pathway |
| NM-08 Multiple sclerosis | RESEARCH ONLY (sparse) | No dedicated MS model found; presentation = weakness + spasticity + fatigue/ataxia combination | Parameter combination recorded; ataxia unmodelled; no disease claims |
| NM-09 Dystonia | RESEARCH ONLY | Tone-vector/posture models exist for parkinsonian axial deformity; cervical dystonia links HN-04 | Involuntary-posture metrics recorded; cause clinical |
| NM-10 Charcot neuropathic foot | MODEL EXISTS (research) | Patient FE Charcot foot predicts internal strain/ulcer location (simulated peak pressure at cuboid matched the real ulcer) | Foot geometry + plantar-pressure screening; ulcer-risk claims = clinician only |
| NM-11 Spasticity/hypertonia (general) | MODEL EXISTS (research) | Velocity-dependent reflex-feedback models fitted per subject from instrumented slow/fast stretch + EMG (OpenSim CP hamstring model); NEURON+OpenSim closed-loop spinal model (2025) | Reflex-gain parameters only from instrumented clinical assessment; twin never "detects spasticity" from video |
| NM-12 Hypotonia (general) | PARAMETER | Reduced tone/force + activation parameters (links MS-07 hypermobility stiffness findings) | Low-force parameter set; cause clinical |
| NM-13 Charcot-Marie-Tooth | ADAPT | Patient-specific OpenSim CMT models (2025) + predictive exo-assistance optimisation (−9.9% simulated metabolic cost) | Distal-weakness + cavovarus parameter set; exo torque via simulation |
| NM-14 Friedreich/hereditary ataxias | RESEARCH ONLY (sparse) | Component deformities modelled (scoliosis SP, cavus FT); gait ataxia itself unmodelled | Record components; ataxia metrics descriptive only |
| NM-15 Post-polio residual deformity | PARAMETER | Asymmetric atrophy/weakness + limb-length/joint parameters (MS-02/WB-01/13 families) | Parameter set from measurement; no disease model needed |

## Build implications

1. **Add the reflex-gain parameter family** to the muscle-parameter
   pipeline (Batch 4): weakness, contracture and spasticity are three
   *separately fitted* parameter groups — conflating them is the
   classic modelling error this literature exists to avoid. Fitting
   requires instrumented assessment (controlled-velocity stretch +
   EMG/force), i.e. a clinic protocol, not our camera twin.
2. **Predictive simulation = clinician-gated research mode** (CP/DMD/
   CMT pattern): it may propose "what-if" visualisations (surgery,
   AFO torque, exo profile) but never patient-facing recommendations
   without D-03 sign-off.
3. **Standing red line reinforced**: the twin models *presentations
   and parameters*; every NM diagnosis, and any spasticity/tone
   grading, remains a clinician act. Camera-only spasticity or ataxia
   claims are prohibited.
4. NM-05/NM-13 give the exo programme its first literature-backed
   design loop: patient model → simulate weakness → derive assistive
   torque profile → verify against measured gait.

## Sources (accessed 2026-10-28)

- CP predictive simulation — Falisse/De Groote line: physics-based
  simulations of motor-control vs musculoskeletal deficits in crouch
  gait (Front Hum Neurosci 2020; bioRxiv 769042); OpenSim crouch
  muscle-function analyses (PMC4397580)
- Instrumented spasticity/contracture modelling — neuro-MSK simulation
  of hamstring assessment in CP (J NeuroEng Rehabil 2016); NEUROiD
  closed-loop spino-MSK spasticity model (Comput Biol Med 2025)
- Stroke — SimTK post-stroke predictive-simulation project (Moco,
  unilateral weakness); stroke strength-training MSK study (2025)
- Parkinson posture model — computational muscle-tone/neural-controller
  model (Front Comput Neurosci 2023)
- Foot drop — OpenSim dorsiflexor-weakness compensation simulations;
  patient-specific SMA-AFO torque design (2019–2021)
- DMD — weakness+contracture predictive simulations (J NeuroEng
  Rehabil 2025)
- CMT — patient-specific OpenSim CMT kinematics (Appl Sci 2025);
  exo-assistance optimisation by predictive simulation (2025)
- Charcot foot FE — biomechanical simulation of Charcot
  neuroarthropathic foot with plantar ulcer (2017)
