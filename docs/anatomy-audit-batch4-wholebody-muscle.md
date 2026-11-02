# Anatomy audit — Batch 4: whole-body & muscle (WB, MS)

> Filed 2026-10-28. Fourth systematic batch from
> [`anatomy-issues-checklist.md`](anatomy-issues-checklist.md):
> WB-01…WB-19 (except WB-03, done in `fat-distribution/`) and
> MS-01…MS-15 (MS-03 partially done via fat-measurement notes).
> 32 issues. Verdict key as before.

## Headline findings

1. **Muscle issues are one parameterisation problem, and it is solved
   conceptually**: an OpenSim-class muscle is defined by maximum
   isometric force (from physiological cross-sectional area / muscle
   volume), optimal fibre length, tendon stiffness, and activation
   dynamics. *Every* muscle item in this batch — sarcopenia, atrophy,
   asymmetry, fatty infiltration, contracture, ageing — is "measure the
   person's muscle volumes/strength, set the parameters". The
   measurement side is mature: MRI muscle segmentation (TotalSegmentator
   muscle classes; UK-Biobank-scale Dixon pipelines segment 27 pelvic–
   thigh structures at Dice ≈ 0.90, thigh volume vs DXA lean mass
   r = 0.936), DXA appendicular lean mass with guideline cut-offs
   (EWGSOP2: ALM/height² < 7.0 kg/m² men, < 5.5 women), and strength
   testing (grip, dynamometry). **One Tier-A muscle-measurement pipeline
   serves MS-01, MS-02, MS-03, WB-06, WB-18 and SH-05.**
2. **Amputation is genuinely modelled in OpenSim** — full-body
   transtibial-amputee models validated against instrumented-prosthesis
   loads (ankle torque mean absolute error 7.7%), and the SimTK
   gait1415+2 transfemoral bone-anchored-prosthesis model. Adopt/adapt.
3. **Pregnancy and ageing have published musculoskeletal adaptations**:
   a pregnant-woman model with trimester-varying segment mass/inertia
   (its main finding: lumbar moment changes dominate), and age-adjusted
   muscle-parameter models (reduced force, slowed activation/deactivation
   — the Thelen-style ageing adjustments) used in elderly gait pipelines.
4. **Honesty flags**: Janda crossed syndromes (MS-05/06) are a clinical
   *pattern language*, not a validated anatomical model — treatment
   studies report benefits, but the pattern's reliability as a pain/
   dysfunction marker is criticised in the literature. We record them as
   pattern labels computed from measured muscle parameters, never as
   diagnoses the twin "detects". Lipedema/lipodystrophy (WB-04/05) have
   **no biomechanical models** — body-composition geometry only.

## Whole-body (WB)

| ID | Verdict | Model / evidence | Twin decision |
|---|---|---|---|
| WB-01 LLD structural | PARAMETER | Per-side femur/tibia lengths in any MSK model; EOS is the measurement standard. Even 5–10 mm simulated LLD measurably changes gait kinematics in all three planes | Segment lengths per side in manifest; compensation is model *output* |
| WB-02 LLD functional | PARAMETER | Apparent LLD from pelvic obliquity (SP-12)/foot posture — same parameter set, different cause | Cause attribution is clinical; twin reports components |
| WB-04 Lipedema | VISUALISE ONLY | No biomechanical model found; fat-depot geometry (links WB-03 methods, but lipedema fat is not predicted by shape models) | Volume/shape record; no model claims. Clinical diagnosis only |
| WB-05 Lipodystrophy | VISUALISE ONLY | As WB-04 | Shape record only |
| WB-06 L–R muscle asymmetry | PARAMETER | Bilateral muscle volumes (MRI pipeline above) → per-side force parameters | Core progress metric; needs Tier-A or strength inputs |
| WB-07 Amputation | **ADAPT** | OpenSim transtibial full-body model (validated vs prosthesis load cell, 7.7% torque MAE); SimTK gait1415+2 transfemoral + bone-anchored prosthesis; BK-amputee socket-interface model variants | Prosthesis as body segments with device parameters in manifest; socket interface = research-grade |
| WB-08 Congenital limb deficiency | ADAPT | Same amputee-model machinery, geometry-driven | Geometry + prosthesis parameters |
| WB-09 Skeletal dysplasia/achondroplasia | PARAMETER | Segment-proportion scaling; no disease-specific model | Proportion parameters; specialist population flag |
| WB-10 Marfan habitus | PARAMETER | Proportion scaling + chest/spine links (SP/RA) | Proportion parameters |
| WB-11 Pregnancy | ADAPT | Published pregnant-woman MSK model: trimester segment mass/CoM/inertia (thorax, pelvis, thighs, legs), reproduces lumbar-curvature change; lumbar moment is the big mover | Time-varying body parameters; posture advice needs obstetric sign-off (D-03) |
| WB-12 Ageing posture change | ADAPT | Age-adjusted muscle parameters + kyphosis trend (SP) in elderly gait pipelines | Age-parameter set, not a disease label |
| WB-13 Hemihypertrophy/hypotrophy | PARAMETER | Side-wise segment size/mass scaling | Geometry/mass parameters from scan+imaging |
| WB-14 Segmental overgrowth | VISUALISE ONLY | Progressive asymmetric geometry; no models | Serial geometry record |
| WB-15 Acromegaly/gigantism | PARAMETER | Proportion/jaw/hand-foot geometry scaling | Geometry parameters |
| WB-16 Multiple hereditary exostoses | VISUALISE ONLY | Bony outgrowth geometry; muscle-path interference case-level | Geometry if imaged |
| WB-17 NF1 skeletal signs | VISUALISE ONLY | Tibial bowing/pseudoarthrosis + scoliosis link geometry | Geometry; links SP/FT items |
| WB-18 Cachexia | PARAMETER | Extreme end of WB-03/MS-01 measurement pipelines | Body-composition parameters; clinical context mandatory |
| WB-19 Burn/scar contractures | PARAMETER (sparse models) | Joint ROM restriction parameter; scar biomechanics FE is wound-care literature | ROM limits per joint; region specialist |

## Muscle & soft tissue (MS)

| ID | Verdict | Model / evidence | Twin decision |
|---|---|---|---|
| MS-01 Sarcopenia | ADAPT | Diagnostic framework (strength + DXA ALM cut-offs) maps directly onto muscle force/volume parameters; MRI volumetric phenotyping at population scale | Parameter set + guideline flags (clinician-confirmed) |
| MS-02 Muscle atrophy | ADAPT | Per-muscle volume from MRI segmentation (TotalSegmentator classes) → PCSA/force scaling | Per-muscle parameters at Tier-A onboarding |
| MS-03 Muscle fatty infiltration | ADAPT (done) | MRI fat fraction (Dixon PDFF) per muscle — see `fat-distribution/measurement-notes.md` | Already specified; feeds MS-01/02, SH-05 |
| MS-04 Contracture (general) | PARAMETER | Shortened optimal fibre length + raised passive stiffness in muscle-tendon parameters; cerebral-palsy contracture modelling literature is the deep end (NM batch) | Per-muscle parameters + ROM envelope |
| MS-05 Upper crossed syndrome | PATTERN LABEL ONLY | Janda framework: tight pectorals/upper-trapezius vs weak deep-neck/scapular muscles. Clinical popularity high; pattern validity as pain marker criticised; intervention studies positive but small | Compute the underlying muscle/posture metrics; label as pattern, never diagnose |
| MS-06 Lower crossed syndrome | PATTERN LABEL ONLY | As MS-05 (hip-flexor/erector tightness vs abdominal/gluteal weakness ↔ SP-10) | As MS-05 |
| MS-07 Hypermobility / EDS | RESEARCH ONLY (sparse) | Gait studies quantify reduced hip/ankle stiffness in hypermobile EDS (ligament laxity + hypotonia), but no validated patient MS model; ligament-stiffness parameterisation is the obvious route | Extended ROM envelopes measured; stiffness claims excluded until modelled |
| MS-08 Diastasis recti | ADAPT | FE abdominal-wall models (muscles + linea alba; breathing/contraction simulated; standard models use 2 cm linea-alba width — diastasis is literally widening that parameter); ultrasound is the adequate measurement per meta-analysis | Linea-alba width parameter from ultrasound; FE offline; links RA breathing layer (IAP) |
| MS-09 Lymphedema | PARAMETER (volume) | Limb volume is directly measurable from surface scan/perometry — one case where our surface twin *is* the measurement for volume (not for cause) | Serial limb-volume metric, labelled volume-only |
| MS-10 Tendinopathy (general) | PARAMETER | Tendon stiffness parameter (as FT-10 Achilles) | Per-tendon parameter; individual values need ultrasound/strength input |
| MS-11 Muscle rupture retraction | VISUALISE ONLY | Displaced muscle-belly geometry; surgical literature | Geometry + actuator path change if imaged |
| MS-12 Muscle hernia | VISUALISE ONLY | Fascial-defect bulge geometry | Geometry record |
| MS-13 Heterotopic ossification | VISUALISE ONLY | Bone-in-muscle = motion block geometry + ROM limit | ROM parameter if imaged |
| MS-14 Myotonic disorders | **NO MODEL FOUND** | Delayed relaxation could in principle be an activation-dynamics parameter (deactivation time constant), but no published twin-relevant model | Record; exclude |
| MS-15 Chronic exertional compartment syndrome | **OUT OF SCOPE (recorded)** | Pressure phenomenon without geometry signature; no model | Exclude per checklist scope rule |

## Build implications

1. **Build the muscle-parameter pipeline once** (Tier-A MRI volumes +
   fat fraction + strength tests → per-muscle OpenSim parameters).
   It discharges MS-01/02/03, WB-06, WB-18, SH-05, HP-10 and part of
   NM later. This is the muscle analogue of the spine finding.
2. **Manifest additions**: per-side segment lengths (WB-01), prosthesis
   blocks (WB-07/08), pregnancy time-varying body set (WB-11),
   age-parameter flag (WB-12).
3. **Pattern labels ≠ diagnoses** (MS-05/06): the twin may display
   "metrics consistent with the described pattern" only with clinician
   sign-off (D-03).
4. Surface twin earns one honest measurement here: **limb volume**
   (MS-09, WB-14 serial geometry) — volume change is surface-true even
   when cause is not.

## Sources (accessed 2026-10-28)

- Simulated-LLD gait effects from 5 mm — Khamis & Carmeli, Gait Posture
  (2018); IMU LLI compensation study, J Orthop Surg Res (2021)
- Amputee OpenSim models — full-body transtibial model (load-cell
  validation 7.7% MAE); gait1415+2 SimTK
  (https://simtk.org/projects/oi-tfp-reduced); BK amputee model SimTK
- Muscle measurement — UK Biobank Dixon 27-structure segmentation
  (Dice 0.896; thigh volume vs DXA r = 0.936, npj Digit Med 2026);
  EWGSOP2 DXA ALM cut-offs; muscle-imaging sarcopenia statement (PMC)
- Abdominal wall FE (breathing/contraction, linea alba) — abdominal-wall
  FE literature; diastasis ultrasound meta-analysis (ECR 2025)
- Pregnant-woman MSK model — Gait Posture (2020), segment mass/inertia
  by trimester
- Ageing muscle parameters — Thelen-style age adjustments; elderly
  OpenSim gait pipelines (2021–2026)
- Janda crossed syndromes — intervention systematic reviews (2025) vs
  pattern-validity criticism (clinical commentary literature)
- Hypermobile EDS gait stiffness — Rigoldi/Cimolin line, Res Dev
  Disabil (2011–2012)
