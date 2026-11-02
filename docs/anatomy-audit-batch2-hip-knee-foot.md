# Anatomy audit — Batch 2: hip → knee → foot alignment chain

> Filed 2026-10-28. Second systematic batch from
> [`anatomy-issues-checklist.md`](anatomy-issues-checklist.md):
> HP-01…HP-16, KN-01…KN-18, FT-02…FT-15, FT-17…FT-25 (57 issues;
> FT-01/FT-16 were done in the detailed-anatomy note).
> Verdict key as in Batch 1 (ADOPT / ADAPT / RESEARCH ONLY / PARAMETER /
> VISUALISE ONLY / NO MODEL FOUND).

## Headline findings

1. **The single most adoptable find of the audit so far: the Torsion Tool**
   (SimTK, open source). It generates OpenSim models with personalised
   **femoral neck-shaft angle, femoral anteversion, and tibial torsion**
   from imaging measurements. Validated against manually segmented
   femurs (max error −19%, RMS −18% vs generic scaling; bigger gains the
   more abnormal the anatomy), and already used clinically: personalised
   models for femoral-derotation-osteotomy decisions in 254 limbs of
   children with cerebral palsy. This one tool covers HP-04, HP-05,
   HP-06 and KN-06 properly, and it plugs straight into our OpenSim
   stage. Its inputs are CT/MRI measurements — i.e. Tier A, as they
   should be: torsion cannot be seen from the surface.
2. **Alignment issues are again parameters, not models** (KN-01/02
   varus/valgus, KN-03, pelvic-drop HP-10, pronation/supination
   FT-04/05, equinus FT-15): mechanical-axis angles (HKA etc. from EOS),
   joint-range limits, and muscle force/stiffness scalings on models we
   already plan to run.
3. **Joint-shape diseases (hip socket/femur shape, patella, meniscus,
   most foot deformities) are patient-specific FE + statistical shape
   models (SSM)** — a mature research literature (systematic reviews
   exist for cam-FAI FE alone), essentially no reusable code. Geometry
   from the patient's imaging or it doesn't exist.
4. **Implants are well modelled**: total knee replacement has
   OpenSim→FE pipelines *validated against instrumented-implant ground
   truth* (Grand Challenge data) — the best-validated modelling chain in
   this batch.
5. **The genuine gaps cluster in rare paediatric foot/limb variants**
   (FT-17, FT-20, FT-22…25, KN-10, KN-15…17): geometry can be captured
   and shown, but nobody has published biomechanical models. We record
   them as VISUALISE ONLY / NO MODEL rather than pretending.

## Family A — Lower-limb alignment & torsion

| ID | Verdict | Model / evidence | Twin decision |
|---|---|---|---|
| HP-04 Coxa vara/valga | **ADOPT** | Torsion Tool personalises neck-shaft angle in OpenSim | Parameter from imaging |
| HP-05 Femoral anteversion | **ADOPT** | Torsion Tool; CP osteotomy cohort (254 limbs) showed personalised models change hip-rotation kinematics vs generic | Parameter from imaging; core for in-toeing |
| HP-06 Femoral retroversion | **ADOPT** | Same tool (negative version) + patellofemoral loading simulations with personalised torsion (40 PF-instability patients) | Parameter from imaging |
| KN-06 Tibial torsion | **ADOPT** | Torsion Tool (tibial torsion angle) | Parameter from imaging |
| KN-01 Genu valgum | PARAMETER | Mechanical-axis (HKA) framework; multi-compartment knee OpenSim models (Lerner-type) compute compartment loads under varus/valgus | Alignment angles from EOS/scan; load split estimated, labelled |
| KN-02 Genu varum | PARAMETER | As KN-01 (varus raises medial load/KAM — the knee-OA driver) | As KN-01 |
| KN-03 Genu recurvatum | PARAMETER | Joint ROM/hyperextension limit; posterior-structure stiffness in knee models | ROM limit in model; measure in session |
| KN-13 Blount disease | RESEARCH ONLY (sparse) | Growth/mechanobiology modelling concepts; mostly geometry + surgical literature | Geometry parameter; growth claims excluded |
| HP-16 Proximal femoral focal deficiency | VISUALISE ONLY | No biomechanical model found; leg-length/prosthetic planning geometry | Geometry + leg-length parameter |
| KN-17 Fibular hemimelia | VISUALISE ONLY | As HP-16 | Geometry + leg-length parameter |

## Family B — Hip joint shape & disease

| ID | Verdict | Model / evidence | Twin decision |
|---|---|---|---|
| HP-01 Hip dysplasia | ADAPT | Parametric FE (centre-edge angle parameterises dysplasia→FAI spectrum) + patient FE/SSM hip shape | Geometry from imaging; FE offline |
| HP-02 Cam FAI | RESEARCH ONLY | Systematic-review-level FE literature (patient CT/MRI models, cartilage stress); SSM quantifies cam morphology (~1 mm neck thickening vs controls) | Geometry/alpha angle from imaging; stress claims FE-only |
| HP-03 Pincer FAI | RESEARCH ONLY | Same parametric FE family (high CE angle) | As HP-02 |
| HP-14 Acetabular retroversion | RESEARCH ONLY | Geometry within the same SSM/FE hip literature | Geometry parameter |
| HP-13 Protrusio acetabuli | VISUALISE ONLY | Geometry described clinically; no dedicated biomech model found | Geometry from imaging |
| HP-07 Hip osteoarthritis | ADAPT | Hip FE cartilage models + hip-shape SSM (shape modes predict OA); musculoskeletal hip contact-force modelling | Geometry + contact-force estimate labelled; cartilage FE offline |
| HP-08 Avascular necrosis | RESEARCH ONLY | FE femoral-head collapse prediction literature | Geometry only; no collapse prediction claims |
| HP-11 Perthes disease | RESEARCH ONLY | Patient geometry/FE case literature | Geometry only |
| HP-12 SCFE | RESEARCH ONLY | FE growth-plate slip models | Geometry only |
| HP-09 Total hip replacement | ADAPT | Musculoskeletal + FE implant modelling (mature surgical literature); implant geometry/ROM envelopes known per device | Implant geometry parameter + ROM limits; record device in twin manifest |
| HP-10 Gluteal insufficiency / Trendelenburg | PARAMETER | Not an anatomy model: hip-abductor strength scaling in OpenSim; measured as pelvic drop in gait | Muscle-strength parameter (needs strength/EMG input — see MS batch) |
| HP-15 SI joint asymmetry | RESEARCH ONLY | Pelvic FE models with SI joints exist for load-transfer studies; "SI dysfunction" clinical construct itself is contested | Geometry if imaged; no dysfunction claims |

## Family C — Knee joint

| ID | Verdict | Model / evidence | Twin decision |
|---|---|---|---|
| KN-07 Knee osteoarthritis | ADAPT | Musculoskeletal-FE knee models with fibril-reinforced poroelastic cartilage/meniscus; mechanobiological progression simulation (collagen damage/proteoglycan loss rules); KAM as load proxy (video-estimated KAM R² 0.86 in one study) | Compartment load estimates labelled; progression simulation research only |
| KN-12 Total knee replacement | **ADAPT (strong)** | OpenSim→FEBio subject-specific pipelines validated against *instrumented implant* forces (Grand Challenge); generic-model choice changes answers — documented | Implant parameterisation; best-validated chain in batch |
| KN-05 Patellar maltracking/instability | ADAPT | Patient-specific patellofemoral FE validated vs experiment (kinematics RMSE ~4.0°/3.1 mm); OpenSim studies with personalised torsion (Family A) | Geometry + torsion parameters; FE offline for stress |
| KN-04 Patella alta/baja | RESEARCH ONLY | Validated FE knee modified by patellar height (Caton-Deschamps 0.8–1.4): alta ↓contact area, ↑peak pressure, ↓lateral restraint | Height ratio parameter from imaging |
| KN-18 Bipartite patella | VISUALISE ONLY | Incidental variant; no model needed | Note in manifest |
| KN-08 Ligament laxity / ACL deficiency | ADAPT | FE healthy vs cruciate-deficient knee validated (predicts PF mechanics after resection); OpenSim ligament-constrained knee models | Ligament stiffness/deficiency parameters; instability claims need clinical testing |
| KN-09 Meniscal deficiency | RESEARCH ONLY | Meniscus inside the KN-07 FE family (FRPE material) | Geometry if imaged; FE offline |
| KN-14 Discoid meniscus | RESEARCH ONLY (sparse) | Case-level FE/geometry | Geometry only |
| KN-11 Knee flexion contracture | PARAMETER | Fixed ROM limit in any MSK model | ROM parameter; cause deferred (MS/NM batches) |
| KN-10 Osgood-Schlatter | **NO MODEL FOUND** | Biomechanical modelling essentially absent (clinical/imaging literature only) | Record finding; visualise only |
| KN-15 Nail-patella syndrome | **NO MODEL FOUND** | No biomechanical models; patellar geometry is the twin-relevant part | Geometry only |
| KN-16 Congenital knee dislocation | **NO MODEL FOUND** | Surgical/case literature only | Geometry only |

## Family D — Foot & ankle (beyond FT-01/16)

| ID | Verdict | Model / evidence | Twin decision |
|---|---|---|---|
| FT-02 Adult-acquired flat foot (PTTD) | ADAPT | OpenSim arched-vs-flatfoot forward simulations (posterior-tibialis disabled reproduces deformity GRF shift); multi-segment biomechanical model quantifies joint load redistribution; MRI-based FE feet (30 bones + fascia/ligaments) | Muscle-function parameter + arch model from Batch FT-01 |
| FT-03 Pes cavus | RESEARCH ONLY | FE/MS cavus modelling exists but thinner than flatfoot | Geometry + arch parameters |
| FT-18 Cavovarus | RESEARCH ONLY | Modelled within Charcot-Marie-Tooth foot literature (NM-13 link) | Geometry + arch/varus parameters |
| FT-04 Dynamic overpronation | PARAMETER | Output of multi-segment foot models (Oxford/Ghent class, FT-16), not a separate model | Session metric (arch deformation, eversion) |
| FT-05 Oversupination | PARAMETER | As FT-04 | Session metric |
| FT-09 Plantar fasciitis | RESEARCH ONLY | Plantar-fascia strain is a standard output of the FT-01 FE foot family (validated vs pressure data) | FE offline; fascia strain never from surface |
| FT-06 Hallux valgus | RESEARCH ONLY | Systematic-review-level foot FE (first-ray load transfer, hypermobility simulation, pre/post-op models) | Geometry (hallux valgus angle) from scan/imaging; FE offline |
| FT-07 Hallux rigidus | RESEARCH ONLY (sparse) | 1st-MTP FE within foot FE family | Geometry + ROM parameter |
| FT-08 Hammer/claw toes | PARAMETER (sparse) | Toe segments exist in multi-segment models (hallux) but lesser-toe deformity modelling is sparse | Toe geometry from scan; no load claims |
| FT-10 Achilles tendinopathy | PARAMETER | Achilles tendon stiffness/force is a standard OpenSim muscle-tendon parameter; tendon models validated in gait simulations | Tendon stiffness parameter (needs ultrasound/strength input for individual values) |
| FT-15 Equinus | PARAMETER | Gastrocnemius/soleus length-stiffness (contracture) parameter; the 4-segment arch OpenSim model was built partly to study this | Muscle-tendon parameter; ROM measured per session |
| FT-11 Clubfoot | ADAPT (emerging) | Iterative FE Ponseti-correction simulation from a *surface scan* (no imaging): reproduces correction stages, mean angular deviation ±3.2° (2025 feasibility); optical-scan+FE assessment matches Ponseti stages | Promising scan-based path; infant population — specialist use only |
| FT-14 Chronic ankle instability | RESEARCH ONLY | Ankle ligament-laxity MS/FE modelling exists; giving-way is also neuromuscular (NM link) | Ligament parameter + clinical tests |
| FT-12 Tarsal coalition | VISUALISE ONLY | Case/surgical literature; coalition = fused segment geometry | Geometry: fuse segments in foot model if imaged |
| FT-13 Metatarsus adductus | VISUALISE ONLY | Paediatric geometry; no biomech model found | Geometry parameter |
| FT-17 Vertical talus | VISUALISE ONLY | Rocker-bottom geometry; surgical literature | Geometry only |
| FT-19 Skewfoot | VISUALISE ONLY | Combined deformity geometry; no model found | Geometry only |
| FT-20 Brachymetatarsia | VISUALISE ONLY | Short-metatarsal geometry; FE only as case reports | Geometry only |
| FT-21 Accessory navicular | RESEARCH ONLY (sparse) | Posterior-tibial insertion mechanics case modelling | Geometry only |
| FT-22 Freiberg infraction | VISUALISE ONLY | Metatarsal-head geometry; no model found | Geometry only |
| FT-23 Toe polydactyly/syndactyly/macrodactyly | VISUALISE ONLY | Shape variants | Geometry from scan |
| FT-24 Calcaneovalgus | VISUALISE ONLY | Flexible newborn posture-deformity | Geometry only |
| FT-25 Köhler/Sever osteochondroses | **NO MODEL FOUND** | Growth-plate conditions; imaging/clinical only | Record; exclude |

## Build implications

1. **Adopt the Torsion Tool into the OpenSim stage** (with CT/MRI
   torsion inputs) — highest value-per-effort item in Batches 1–2.
   Add `femoral_anteversion_deg`, `neck_shaft_angle_deg`,
   `tibial_torsion_deg` (per side) to the twin manifest schema.
2. **EOS-style alignment parameters** (HKA, joint orientation angles)
   join the spinopelvic layer from Batch 1 as the standing-alignment
   record. Surface scans can *screen* alignment; angles that drive
   claims come from EOS/imaging.
3. **Implant awareness**: twin manifest must record prosthesis
   type/side (HP-09, KN-12) — geometry and ROM envelopes change.
4. **Foot**: the arch/synergy models (FT-01/16) + posterior-tibialis
   function parameter cover the clinically central foot issues;
   the long niche tail is geometry-only, and three items
   (KN-10, KN-15, KN-16, FT-25) are honest NO MODEL FOUND records.
5. Nothing in Family B/C joint-shape territory may be inferred from
   camera or LiDAR. Alpha angles, CE angles, patellar height, torsion —
   all imaging findings.

## Sources (accessed 2026-10-28)

- Torsion Tool — https://simtk.org/projects/torsiontool; Veerkamp et al.,
  J Biomech (2021), validation vs segmented femurs; CP derotation-
  osteotomy personalised-model cohort, J Orthop Surg Res (2025)
- Cam/pincer/dysplasia FE + hip SSM — systematic review, PLOS ONE
  10.1371/journal.pone.0147813; Harris et al. cam SSM, J Orthop Res (2013)
- Patellofemoral FE validation — PMC4761469 (RMSE 4.0°/3.1 mm);
  patella alta FE, PubMed 28852343
- Knee OA MS-FE + mechanobiological progression — Mononen-lineage FRPE
  models; AI-FE knee OA review (2026); TKR OpenSim→FEBio Grand
  Challenge validation, PMC8085535
- PTTD/flatfoot — OpenSim arched/flatfoot forward simulation, PLOS ONE
  e0270638; Arangio multi-segment PTTD model, Clin Biomech (2009);
  cadaver dynamic simulator, Gait Posture (2013)
- Hallux valgus FE — systematic review of FE in hallux valgus (2025);
  first-ray pre/post-op FE, Clin Biomech (2018)
- Clubfoot iterative FE (surface-scan Ponseti) — Children (2025),
  ±3.2° feasibility; optical-scan+FE clubfoot assessment (2026)
- Foot arch/synergy/OpenSim foot models — see
  `research-detailed-anatomy-models.md` §1
