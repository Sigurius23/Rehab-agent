# Anatomy issues checklist — systematic model coverage audit

> Created 2026-10-28. Purpose: list the human **anatomy issues that change
> body geometry, posture, movement, or internal structure** — the things the
> Rehab Agent digital twin may need to represent — so we can go through
> them systematically and record, for each one: *does a model exist, what
> kind, and can we use it?*
>
> **Scope:** musculoskeletal / structural / movement-relevant issues.
> Excluded: organ diseases, cancers, infections, metabolic diseases etc.
> *unless* they change geometry or movement (those cases are included via
> their structural effect, e.g. osteoporotic wedge vertebra).
>
> **Status legend**
> - `RESearched — models exist` = we have already checked (link to note)
> - `TO CHECK` = not yet researched
> - Later statuses as the audit proceeds: `MODEL EXISTS — adoptable`,
>   `MODEL EXISTS — research only`, `NO MODEL FOUND`, `OUT OF SCOPE`
>
> **Priority** = relevance to posture correction / twin accuracy
> (H = core, M = common or geometry-changing, L = rarer/specialist).

## A. Spine & trunk (SP)

| ID | Issue | What changes anatomically | Priority | Status |
|---|---|---|---|---|
| SP-01 | Scoliosis — adolescent idiopathic | Lateral spinal curvature + vertebral rotation, rib hump | H | RESearched — subject-specific OpenSim models exist (`research-detailed-anatomy-models.md` §2) |
| SP-02 | Scoliosis — congenital | Malformed vertebrae driving curvature | M | MODEL EXISTS — patient-specific EOS/CT 3D + FE (audit batch 1) |
| SP-03 | Scoliosis — neuromuscular | Curvature from muscle imbalance/paralysis | M | MODEL EXISTS (geometry) — muscle drivers unmodelled (audit batch 1) |
| SP-04 | Scoliosis — adult degenerative | Asymmetric disc/facet degeneration curvature | M | MODEL EXISTS — patient-specific FE, validated (audit batch 1) |
| SP-05 | Hyperkyphosis / Scheuermann's kyphosis | Wedged thoracic vertebrae, rigid round back | H | MODEL EXISTS — coupled OpenSim+FE subject-specific (audit batch 1) |
| SP-06 | Postural kyphosis (flexible) | Habitual thoracic over-flexion, no bone change | H | PARAMETER of spinopelvic model — no separate model (audit batch 1) |
| SP-07 | Lumbar hyperlordosis | Excess lumbar extension curve, anterior pelvic tilt coupling | H | PARAMETER of spinopelvic model (audit batch 1) |
| SP-08 | Flat back (lumbar hypolordosis) | Loss of lumbar curve | M | PARAMETER of spinopelvic model (audit batch 1) |
| SP-09 | Swayback posture | Pelvis shifted forward, thoracic back-sway | M | PARAMETER — posture pattern (audit batch 1) |
| SP-10 | Anterior pelvic tilt | Pelvis rotated forward; hip flexor/erector dominance | H | PARAMETER — pelvic tilt metric (audit batch 1) |
| SP-11 | Posterior pelvic tilt | Pelvis rotated backward; flat lumbar | M | PARAMETER — pelvic tilt metric (audit batch 1) |
| SP-12 | Pelvic obliquity (lateral tilt) | One side of pelvis higher; apparent leg-length difference | H | MODEL EXISTS — 3D pelvic geometry EOS/CT (audit batch 1) |
| SP-13 | Pelvic rotation asymmetry | Pelvis rotated in transverse plane | M | MEASUREMENT ONLY — dedicated model gap (audit batch 1) |
| SP-14 | Spondylolisthesis | Vertebra slipped forward on the one below | M | MODEL EXISTS — patient-specific FE, research only (audit batch 1) |
| SP-15 | Spondylolysis | Pars defect (stress fracture) in vertebra | L | MODEL EXISTS — FE pars-defect models (audit batch 1) |
| SP-16 | Spinal stenosis | Narrowed spinal canal/foramina | L | MODEL EXISTS — surgical FE; visualise-only for twin (audit batch 1) |
| SP-17 | Ankylosing spondylitis | Progressively fused/rigid spine | M | MODEL EXISTS — FE ankylosed spine; lock joints in OpenSim (audit batch 1) |
| SP-18 | Disc degeneration / herniation | Disc height loss, segment geometry change | M | MODEL EXISTS — poroelastic FE discs, research only (audit batch 1) |
| SP-19 | Osteoporotic vertebral wedge fracture | Wedged vertebral body → focal kyphosis | M | MODEL EXISTS — validated CT FE wedge models (audit batch 1) |
| SP-20 | Spine bending mechanics (general) | How curvature distributes across vertebrae | H | RESearched — articulated OpenSim spine models exist (§2 of anatomy note) |

## B. Head, neck & jaw (HN)

| ID | Issue | What changes anatomically | Priority | Status |
|---|---|---|---|---|
| HN-01 | Forward head posture | Head translated forward of trunk line | H | PARAMETER — CVA surface metric, 5° floor (batch 5) |
| HN-02 | Loss of cervical lordosis ("military neck") | Straightened cervical curve | M | PARAMETER (imaging) — radiographic curve (batch 5) |
| HN-03 | Cervical kyphosis | Reversed cervical curve | M | PARAMETER (imaging) — radiographic curve (batch 5) |
| HN-04 | Torticollis (congenital muscular / spasmodic) | Sternocleidomastoid shortening/spasm, head tilt+rotation | M | MODEL EXISTS — OpenSim neck model, SCM params (batch 5) |
| HN-05 | TMJ disorder / jaw misalignment | Jaw joint mechanics, bite asymmetry | L | MODEL EXISTS (research) — jaw+FE TMJ, specialty (batch 5) |
| HN-06 | Cranial asymmetry (plagiocephaly) | Skull shape asymmetry | L | PARAMETER — scannable head-shape geometry (batch 5) |

## C. Shoulder girdle (SH)

| ID | Issue | What changes anatomically | Priority | Status |
|---|---|---|---|---|
| SH-01 | Rounded shoulders | Protracted/ internally rotated shoulder girdle posture | H | PARAMETER — scapular posture metrics (batch 3) |
| SH-02 | Scapular winging | Medial scapular border lifts off rib cage (serratus/long thoracic) | M | MODEL EXISTS — muscle-deficiency params in shoulder MS models (batch 3) |
| SH-03 | Scapular dyskinesis | Abnormal scapular motion pattern in arm movement | M | PARAMETER — Kibler pattern from model kinematics (batch 3) |
| SH-04 | Shoulder impingement anatomy | Acromion shape / subacromial space narrowing | M | MODEL EXISTS — FE + scapula SSM, research only (batch 3) |
| SH-05 | Rotator cuff tear + fatty infiltration | Tendon tear, muscle atrophy/fatty degeneration | M | MODEL EXISTS — shoulder sim + MRI fat-fraction params (batch 3) |
| SH-06 | Adhesive capsulitis (frozen shoulder) | Capsular contracture, severe range loss | M | PARAMETER — ROM envelope (batch 3) |
| SH-07 | Shoulder instability | Laxity / labral anatomy, dislocation history | L | MODEL EXISTS — FE stability, research only (batch 3) |
| SH-08 | Clavicle malunion / deformity | Shortened/angulated clavicle after fracture | L | PARAMETER — clavicle geometry in shoulder models (batch 3) |
| SH-09 | Thoracic outlet compression anatomy | Narrowed scalene/costoclavicular space | L | NO MODEL FOUND (twin-relevant) (batch 3) |

## D. Arm, elbow, wrist & hand (UL)

| ID | Issue | What changes anatomically | Priority | Status |
|---|---|---|---|---|
| UL-01 | Cubitus valgus / varus | Elbow carrying-angle deformity | L | PARAMETER — carrying angle per side (batch 6) |
| UL-02 | Elbow flexion contracture | Fixed loss of extension | M | PARAMETER — ROM envelope + stiffness (batch 6) |
| UL-03 | Madelung deformity (wrist) | Distal radius growth deformity | L | VISUALISE ONLY — wrist geometry (batch 6) |
| UL-04 | Dupuytren's contracture | Palmar fascia cords, finger flexion deformity | L | PARAMETER (sparse) — per-finger flexion limits (batch 6) |
| UL-05 | Rheumatoid hand deformities | Swan-neck / boutonnière / ulnar drift | L | MODEL EXISTS (research) — finger FE mechanisms (batch 6) |

## E. Hip & pelvis (HP)

| ID | Issue | What changes anatomically | Priority | Status |
|---|---|---|---|---|
| HP-01 | Developmental hip dysplasia | Shallow acetabulum, femoral head coverage loss | M | MODEL EXISTS — parametric/patient FE + hip SSM (batch 2) |
| HP-02 | Femoroacetabular impingement — cam | Aspherical femoral head-neck junction | M | MODEL EXISTS — FE systematic-review level, research only (batch 2) |
| HP-03 | Femoroacetabular impingement — pincer | Acetabular over-coverage | M | MODEL EXISTS — parametric FE, research only (batch 2) |
| HP-04 | Coxa vara / coxa valga | Femoral neck-shaft angle decreased / increased | M | ADOPT — Torsion Tool neck-shaft personalisation (batch 2) |
| HP-05 | Femoral anteversion | Femoral neck twisted forward → in-toeing | H | ADOPT — Torsion Tool anteversion, clinically used (batch 2) |
| HP-06 | Femoral retroversion | Femoral neck twisted backward → out-toeing | M | ADOPT — Torsion Tool version parameter (batch 2) |
| HP-07 | Hip osteoarthritis | Joint space loss, osteophytes, deformity | H | MODEL EXISTS — hip FE + shape SSM (batch 2) |
| HP-08 | Avascular necrosis of femoral head | Femoral head collapse | L | MODEL EXISTS — FE collapse studies, research only (batch 2) |
| HP-09 | Total hip replacement | Prosthetic joint geometry, leg-length change | M | MODEL EXISTS — implant MSK/FE models (batch 2) |
| HP-10 | Gluteal insufficiency / Trendelenburg | Hip abductor weakness → pelvic drop in gait | H | PARAMETER — abductor strength scaling (batch 2) |

## F. Knee & leg alignment (KN)

| ID | Issue | What changes anatomically | Priority | Status |
|---|---|---|---|---|
| KN-01 | Genu valgum (knock knees) | Valgus knee alignment | H | PARAMETER — mechanical-axis alignment (batch 2) |
| KN-02 | Genu varum (bow legs) | Varus knee alignment | H | PARAMETER — mechanical-axis alignment (batch 2) |
| KN-03 | Genu recurvatum | Knee hyperextension | M | PARAMETER — ROM limit (batch 2) |
| KN-04 | Patella alta / baja | Patella abnormally high / low | L | MODEL EXISTS — validated FE patellar height (batch 2) |
| KN-05 | Patellar maltracking / instability | Patella tracks laterally, dislocation risk | M | MODEL EXISTS — patient PF FE validated (batch 2) |
| KN-06 | Tibial torsion (internal/external) | Shin bone twisted along its axis | M | ADOPT — Torsion Tool tibial torsion (batch 2) |
| KN-07 | Knee osteoarthritis | Compartment joint-space loss → progressive varus/valgus | H | MODEL EXISTS — MS-FE OA models (batch 2) |
| KN-08 | Ligament laxity / ACL deficiency | Joint instability | M | MODEL EXISTS — FE/MSK ligament models (batch 2) |
| KN-09 | Meniscal injury/deficiency | Load-distribution anatomy changed | L | MODEL EXISTS — meniscus in knee FE (batch 2) |
| KN-10 | Osgood-Schlatter (adolescent) | Tibial tubercle apophysitis/bump | L | NO MODEL FOUND (batch 2) |
| KN-11 | Knee flexion contracture | Fixed loss of extension (common post-stroke/arthritic) | M | PARAMETER — ROM limit (batch 2) |
| KN-12 | Total knee replacement | Prosthetic joint geometry/alignment | M | MODEL EXISTS — OpenSim-FE validated vs instrumented implant (batch 2) |

## G. Foot & ankle (FT)

| ID | Issue | What changes anatomically | Priority | Status |
|---|---|---|---|---|
| FT-01 | Pes planus — flexible flat foot | Arch collapses under load, recovers unloaded | H | RESearched — FE + kinematic models exist (§1 of anatomy note) |
| FT-02 | Adult-acquired flat foot (posterior tibial tendon dysfunction) | Progressive arch collapse + hindfoot valgus | M | MODEL EXISTS — OpenSim flatfoot sim + FE (batch 2) |
| FT-03 | Pes cavus (high arch) | Abnormally high, rigid arch | M | MODEL EXISTS — FE/MS cavus, thinner lit (batch 2) |
| FT-04 | Dynamic overpronation | Excess arch collapse/eversion in gait | H | PARAMETER — multi-segment foot output (batch 2) |
| FT-05 | Oversupination | Lateral loading, rigid high-arch gait | L | PARAMETER — multi-segment foot output (batch 2) |
| FT-06 | Hallux valgus (bunion) | Big-toe lateral deviation + 1st metatarsal shift | M | MODEL EXISTS — foot FE systematic-review level (batch 2) |
| FT-07 | Hallux rigidus | 1st MTP joint arthritis/stiffness | L | MODEL EXISTS (sparse) — 1st-MTP FE (batch 2) |
| FT-08 | Hammer / claw / mallet toes | Toe joint deformities | L | PARAMETER (sparse) — toe segment geometry (batch 2) |
| FT-09 | Plantar fasciitis / fascia thickening | Plantar fascia degeneration/thickening | M | MODEL EXISTS — fascia strain in foot FE (batch 2) |
| FT-10 | Achilles tendinopathy / Haglund deformity | Tendon thickening / heel bone prominence | L | PARAMETER — tendon stiffness in OpenSim (batch 2) |
| FT-11 | Clubfoot (talipes equinovarus) | Congenital inward/downward foot deformity | M | MODEL EXISTS — iterative FE Ponseti from surface scan (batch 2) |
| FT-12 | Tarsal coalition | Abnormal bone/cartilage bridge between tarsals | L | VISUALISE ONLY — fused-segment geometry (batch 2) |
| FT-13 | Metatarsus adductus | Forefoot deviated inward (paediatric) | L | VISUALISE ONLY — geometry (batch 2) |
| FT-14 | Chronic ankle instability | Ligament laxity, recurrent giving way | M | MODEL EXISTS — ankle laxity MS/FE (batch 2) |
| FT-15 | Equinus (gastrocnemius/soleus tightness) | Limited ankle dorsiflexion | M | PARAMETER — muscle-tendon contracture (batch 2) |
| FT-16 | Arch height (general mechanics) | Dynamic arch rise/collapse in gait | H | RESearched — multi-segment + synergy foot models exist (§1 of anatomy note) |

## H. Whole-body alignment, proportions & composition (WB)

| ID | Issue | What changes anatomically | Priority | Status |
|---|---|---|---|---|
| WB-01 | Leg-length discrepancy — structural | True bone length difference | H | PARAMETER — per-side segment lengths (batch 4) |
| WB-02 | Leg-length discrepancy — functional | Apparent difference from pelvis/foot posture | M | PARAMETER — apparent LLD components (batch 4) |
| WB-03 | Obesity / regional fat distribution | Fat mass amount + depot pattern | H | RESearched — see `fat-distribution/` folder |
| WB-04 | Lipedema | Symmetrical painful leg fat deposition, spares feet | M | VISUALISE ONLY — no biomechanical model (batch 4) |
| WB-05 | Lipodystrophy | Regional fat loss/redistribution | L | VISUALISE ONLY — shape record (batch 4) |
| WB-06 | Left–right muscle asymmetry | Side-to-side muscle size/strength difference | H | PARAMETER — bilateral muscle volumes (batch 4) |
| WB-07 | Limb amputation (upper/lower) | Missing limb segment; prosthesis interface | M | MODEL EXISTS — OpenSim amputee models, validated (batch 4) |
| WB-08 | Congenital limb deficiency | Partially formed limb | L | MODEL EXISTS — amputee-model machinery (batch 4) |
| WB-09 | Skeletal dysplasia / achondroplasia | Short-limb body proportions | L | PARAMETER — proportion scaling (batch 4) |
| WB-10 | Marfan habitus | Tall, long-limb proportions, chest deformity link | L | PARAMETER — proportion scaling (batch 4) |
| WB-11 | Pregnancy-related anatomical change | Centre-of-mass shift, lordosis, abdominal wall change | M | MODEL EXISTS — pregnant-woman MSK model (batch 4) |
| WB-12 | Ageing posture change | Kyphosis increase, height loss, sarcopenia coupling | M | MODEL EXISTS — age-adjusted muscle params (batch 4) |

## I. Muscle, tendon & soft tissue (MS)

| ID | Issue | What changes anatomically | Priority | Status |
|---|---|---|---|---|
| MS-01 | Sarcopenia | Age-related muscle mass/quality loss (incl. fatty infiltration) | H | MODEL EXISTS — DXA/MRI params + guideline cut-offs (batch 4) |
| MS-02 | Muscle atrophy (disuse/neurogenic) | Local muscle volume loss | H | MODEL EXISTS — MRI volume to force params (batch 4) |
| MS-03 | Muscle fatty infiltration | Fat within muscle (measurable as MRI fat fraction) | H | MODEL EXISTS — MRI fat fraction (Dixon PDFF) per muscle (fat notes + batch 4) |
| MS-04 | Muscle/tendon contracture (general) | Fixed shortening limiting joint range | H | PARAMETER — fibre-length/passive stiffness (batch 4) |
| MS-05 | Upper crossed syndrome (Janda) | Tight pectorals/upper traps vs weak deep neck flexors/scapular muscles | M | PATTERN LABEL ONLY — Janda, validity contested (batch 4) |
| MS-06 | Lower crossed syndrome (Janda) | Tight hip flexors/erectors vs weak abdominals/gluteals | M | PATTERN LABEL ONLY — Janda, validity contested (batch 4) |
| MS-07 | Joint hypermobility / Ehlers-Danlos | Ligament laxity, excessive joint range, instability | M | MODEL EXISTS (sparse) — stiffness studies, no patient model (batch 4) |
| MS-08 | Diastasis recti | Separated rectus abdominis along linea alba | M | MODEL EXISTS — abdominal-wall FE + ultrasound (batch 4) |
| MS-09 | Lymphedema / chronic edema | Regional limb volume increase (fluid) | L | PARAMETER — limb volume from surface (batch 4) |
| MS-10 | Tendinopathy (general mechanics) | Tendon thickening/stiffness change | L | PARAMETER — tendon stiffness (batch 4) |

## J. Bone & joint — general (BJ)

| ID | Issue | What changes anatomically | Priority | Status |
|---|---|---|---|---|
| BJ-01 | Osteoporosis / low bone mineral density | Bone mass/strength loss (DXA-measurable) | M | MODEL EXISTS — QCT FE bone strength (batch 6) |
| BJ-02 | Osteoarthritis (non hip/knee joints) | Joint space loss, deformity (shoulder, ankle, spine facets, hands) | M | MODEL EXISTS (research) — joint FE/SSM family (batch 6) |
| BJ-03 | Rheumatoid arthritis deformity pattern | Inflammatory joint destruction pattern | L | VISUALISE ONLY — deformity pattern record (batch 6) |
| BJ-04 | Fracture malunion | Bone healed in deformed position | M | MODEL EXISTS — 3D malunion planning (batch 6) |
| BJ-05 | Other joint replacements (shoulder, ankle) | Prosthetic joint geometry | L | MODEL EXISTS — RTSA OpenSim pipelines (batch 6) |
| BJ-06 | Rickets / osteomalacia | Softened bone → bowing deformities | L | PARAMETER — bowing geometry (batch 6) |

## K. Neuromotor conditions (movement presentation) (NM)

> Not "anatomy defects" themselves, but conditions whose *anatomical
> presentation* (posture, alignment, muscle bulk) the twin will encounter.

| ID | Issue | What changes anatomically | Priority | Status |
|---|---|---|---|---|
| NM-01 | Cerebral palsy — crouch gait | Persistent hip/knee flexion gait pattern | M | MODEL EXISTS — CP predictive simulation (batch 7) |
| NM-02 | Cerebral palsy — spastic equinus / patterns | Spasticity-driven foot/limb postures, contractures | M | MODEL EXISTS — spasticity+contracture models (batch 7) |
| NM-03 | Stroke hemiparesis posture | One-sided weakness/spasticity, asymmetric posture | H | MODEL EXISTS — unilateral weakness sims (batch 7) |
| NM-04 | Parkinsonian stooped posture / camptocormia | Trunk flexion posture, rigidity pattern | M | MODEL EXISTS (research) — tone-vector model (batch 7) |
| NM-05 | Foot drop (peroneal nerve / L5) | Dorsiflexor failure, steppage gait | M | MODEL EXISTS — weakness sims + AFO torque design (batch 7) |
| NM-06 | Muscular dystrophy posture | Progressive weakness → lordosis, pseudohypertrophy | L | MODEL EXISTS — DMD weakness+contracture sims (batch 7) |
| NM-07 | Spinal muscular atrophy | Proximal weakness postures | L | PARAMETER (sparse) — weakness distribution (batch 7) |
| NM-08 | Multiple sclerosis gait/posture | Spasticity + weakness + ataxia combination | L | MODEL EXISTS (sparse) — parameter combination only (batch 7) |
| NM-09 | Dystonia (incl. cervical) | Involuntary sustained muscle contractions → abnormal postures | L | MODEL EXISTS (research) — tone/posture models (batch 7) |
| NM-10 | Charcot (neuropathic) foot | Joint/bone collapse from neuropathy | L | MODEL EXISTS (research) — Charcot foot FE (batch 7) |
| NM-11 | Spasticity / hypertonia (general) | Velocity-dependent muscle overactivity | H | MODEL EXISTS (research) — reflex-feedback params (batch 7) |
| NM-12 | Hypotonia (general) | Low muscle tone, postural collapse tendency | M | PARAMETER — low-force parameter set (batch 7) |

## L. Chest, rib cage, breathing & abdominal wall (RA)

| ID | Issue | What changes anatomically | Priority | Status |
|---|---|---|---|---|
| RA-01 | Breathing pattern disorder (thoracic-dominant) | Upper-chest dominant ventilation, diaphragm under-recruited | H | RESearched — tracking + metrics in `research-breathing-tracking.md` |
| RA-02 | Paradoxical breathing / thoracoabdominal asynchrony | Abdomen moves inward on inhalation etc. | M | RESearched — phase-angle methods (§2–3 of breathing note) |
| RA-03 | Diaphragm paralysis / dysfunction | Elevated, weak or paradoxical hemidiaphragm | M | RESearched — ultrasound measures (excursion/thickening) in breathing note |
| RA-04 | Pectus excavatum | Sternum sunken inward | M | MODEL EXISTS — patient FE Nuss simulation (batch 5) |
| RA-05 | Pectus carinatum | Sternum protruding outward | L | MODEL EXISTS (sparse) — brace FE (batch 5) |
| RA-06 | Barrel chest (COPD hyperinflation) | Increased AP chest diameter, flattened diaphragm | M | PARAMETER — chest geometry + breathing (batch 5) |
| RA-07 | Rib flare | Lower ribs protrude outward (often with lordosis/diaphragm position) | M | PARAMETER — surface rib geometry (batch 5) |
| RA-08 | Rib hump (scoliosis-linked) | Rib cage rotational deformity | M | PARAMETER — surface topography, links SP-01 (batch 5) |
| RA-09 | Abdominal wall hernia | Wall defect with protrusion | L | MODEL EXISTS — abdominal-wall hernia FE (batch 5) |
| RA-10 | Rib cage expansion mechanics (general) | Pump/bucket-handle expansion, diaphragm coupling | H | RESearched — rib/diaphragm models in anatomy note §3 + breathing note |

## M. Niche & rare additions (added 2026-10-28)

> The main list (A–L) covers common and moderately common issues. This
> section adds the **niche layer**: rare, congenital, paediatric,
> post-surgical and syndrome-associated conditions that still change body
> geometry, posture, or movement. IDs continue each region's numbering so
> references stay stable. Deliberately still excluded: pain-only
> conditions with no structural/movement signature (e.g. fibromyalgia,
> Morton's neuroma), transient injuries with normal healing, and internal
> organ disease without a geometry/movement effect.

### Spine niche (SP, continued)

| ID | Issue | What changes anatomically | Priority | Status |
|---|---|---|---|---|
| SP-21 | Klippel-Feil syndrome | Congenitally fused cervical vertebrae, short neck, low motion | L | PARAMETER — locked cervical segments (batch 8) |
| SP-22 | Hemivertebra / congenital vertebral malformation | Half-formed vertebra → congenital scoliosis/kyphosis driver | L | PARAMETER — congenital curve geometry (batch 8) |
| SP-23 | Lumbosacral transitional vertebra (sacralisation/lumbarisation, Bertolotti) | Extra/fused lumbosacral segment alters load transfer | L | MODEL EXISTS (research) — LSTV FE models (batch 8) |
| SP-24 | Spina bifida (posterior arch defect) | Missing vertebral arch; neurological level-dependent posture | L | MODEL EXISTS — level-based MSK simulations (batch 8) |
| SP-25 | DISH (diffuse idiopathic skeletal hyperostosis) | Flowing spinal ossification → stiff spine | L | MODEL EXISTS (research) — DISH spine FE (batch 8) |
| SP-26 | Atlantoaxial instability (e.g. Down syndrome) | C1–C2 laxity, head/neck positioning risk | L | NO MODEL — SAFETY FLAG (batch 8) |
| SP-27 | Gibbus deformity | Sharp angular kyphosis (e.g. post-infectious Pott disease) | L | VISUALISE ONLY — angular kyphosis geometry (batch 8) |
| SP-28 | Thoracic insufficiency syndrome | Fused ribs/spine — chest cannot expand for lung growth | L | PARAMETER (sparse) — chest geometry record (batch 8) |
| SP-29 | Basilar invagination / cranial settling | Skull base settling onto cervical spine | L | VISUALISE ONLY — skull-base geometry + caution (batch 8) |
| SP-30 | OPLL (ossification of posterior longitudinal ligament) | Ossified ligament stiffens/narrows cervical canal | L | PARAMETER — stiffened segments (batch 8) |

### Head/neck niche (HN, continued)

| ID | Issue | What changes anatomically | Priority | Status |
|---|---|---|---|---|
| HN-07 | Cervical rib | Extra rib above 1st rib (thoracic-outlet link, SH-09) | L | VISUALISE ONLY — imaging finding (batch 5) |
| HN-08 | Hemifacial microsomia / craniofacial asymmetry | One side of face/jaw underdeveloped | L | VISUALISE ONLY — craniofacial geometry (batch 5) |
| HN-09 | Retrognathia / micrognathia / prognathism | Jaw size/position discrepancies | L | PARAMETER — cephalometric geometry (batch 5) |
| HN-10 | Ocular torticollis | Compensatory head tilt from eye-muscle imbalance | L | NO MODEL FOUND — ocular cause (batch 5) |
| HN-11 | Webbed neck (pterygium colli, e.g. Turner/Noonan) | Neck skin webbing, low hairline, posture appearance | L | VISUALISE ONLY — neck contour geometry (batch 5) |
| HN-12 | TMJ ankylosis | Fused jaw joint, severe opening restriction | L | PARAMETER (sparse) — jaw opening ROM (batch 5) |

### Shoulder niche (SH, continued)

| ID | Issue | What changes anatomically | Priority | Status |
|---|---|---|---|---|
| SH-10 | Sprengel deformity | Congenitally high, small scapula | L | VISUALISE ONLY — scapula rest position (batch 3) |
| SH-11 | Poland syndrome | Absent pectoralis major (+ hand differences), chest asymmetry | L | PARAMETER — absent-muscle actuator set (batch 3) |
| SH-12 | Snapping scapula syndrome | Scapulothoracic crepitus/abnormal tracking | L | MODEL EXISTS (sparse) — record only (batch 3) |
| SH-13 | Obstetric brachial plexus palsy (Erb's) posture | "Waiter's tip" arm posture, growth asymmetry | L | MODEL EXISTS (sparse) — paediatric MS scarce (batch 3) |
| SH-14 | Glenoid dysplasia / retroversion | Shallow/misoriented shoulder socket | L | MODEL EXISTS — glenoid version SSM/FE (batch 3) |
| SH-15 | Os acromiale / acromial variants | Unfused acromial ossification centre altering deltoid mechanics | L | VISUALISE ONLY — variant note (batch 3) |

### Arm/hand niche (UL, continued)

| ID | Issue | What changes anatomically | Priority | Status |
|---|---|---|---|---|
| UL-06 | Congenital radioulnar synostosis | Radius/ulna fused — forearm rotation fixed | L | PARAMETER — locked forearm rotation (batch 6) |
| UL-07 | Radial longitudinal deficiency (radial club hand) | Partial/absent radius, radial hand deviation | L | VISUALISE ONLY — geometry; parametric hand mismatch (batch 6) |
| UL-08 | Camptodactyly / clinodactyly | Fixed finger flexion / lateral finger curvature | L | PARAMETER — per-joint angle limits (batch 6) |
| UL-09 | Syndactyly / polydactyly (hand) | Fused or extra digits — hand shape/grip | L | VISUALISE ONLY — topology not representable (batch 6) |
| UL-10 | Volkmann ischaemic contracture | Forearm muscle fibrosis → claw-like contracture | L | PARAMETER — contracture parameter set (batch 6) |
| UL-11 | Trigger finger (stenosing tenosynovitis) | Tendon catching, functional grip loss | L | NO MODEL FOUND — dynamic catching (batch 6) |

### Hip niche (HP, continued)

| ID | Issue | What changes anatomically | Priority | Status |
|---|---|---|---|---|
| HP-11 | Legg-Calvé-Perthes disease | Childhood femoral-head necrosis → deformed head/hip | L | MODEL EXISTS — patient geometry/FE cases (batch 2) |
| HP-12 | Slipped capital femoral epiphysis (SCFE) | Growth-plate slip → hip deformity, leg rotation change | L | MODEL EXISTS — FE slip models (batch 2) |
| HP-13 | Protrusio acetabuli | Socket protrudes into pelvis, deep hip | L | VISUALISE ONLY — no dedicated model (batch 2) |
| HP-14 | Acetabular retroversion | Socket opening faces backward → impingement pattern | L | MODEL EXISTS — geometry in hip SSM/FE (batch 2) |
| HP-15 | Sacroiliac joint asymmetry/dysfunction | Pelvic ring asymmetry perception/mechanics | M | MODEL EXISTS — pelvic FE; clinical construct contested (batch 2) |
| HP-16 | Proximal femoral focal deficiency | Underdeveloped proximal femur → major leg-length difference | L | VISUALISE ONLY — geometry/leg-length (batch 2) |

### Knee/leg niche (KN, continued)

| ID | Issue | What changes anatomically | Priority | Status |
|---|---|---|---|---|
| KN-13 | Blount disease (tibia vara) | Growth disorder bowing the proximal tibia (infantile/adolescent) | L | MODEL EXISTS (sparse) — geometry/growth (batch 2) |
| KN-14 | Discoid meniscus | Disc-shaped (not C-shaped) meniscus, snapping knee | L | MODEL EXISTS (sparse) — case FE (batch 2) |
| KN-15 | Nail-patella syndrome | Small/absent patellae + elbow and iliac anomalies | L | NO MODEL FOUND (batch 2) |
| KN-16 | Congenital knee dislocation | Hyperextended/dislocated knee at birth | L | NO MODEL FOUND (batch 2) |
| KN-17 | Fibular hemimelia | Partial/absent fibula → leg-length and foot deformity | L | VISUALISE ONLY — geometry/leg-length (batch 2) |
| KN-18 | Bipartite patella (variant) | Patella in two unfused parts — usually incidental | L | VISUALISE ONLY — variant note (batch 2) |

### Foot niche (FT, continued)

| ID | Issue | What changes anatomically | Priority | Status |
|---|---|---|---|---|
| FT-17 | Congenital vertical talus | "Rocker-bottom" rigid flat foot | L | VISUALISE ONLY — geometry (batch 2) |
| FT-18 | Cavovarus foot | High arch + hindfoot varus (often Charcot-Marie-Tooth, NM-13) | M | MODEL EXISTS — CMT foot modelling (batch 2) |
| FT-19 | Skewfoot (serpentine foot) | Combined forefoot adduction + hindfoot valgus Z-deformity | L | VISUALISE ONLY — geometry (batch 2) |
| FT-20 | Brachymetatarsia | Abnormally short metatarsal (usually 4th toe) | L | VISUALISE ONLY — geometry (batch 2) |
| FT-21 | Accessory navicular syndrome | Extra navicular ossicle altering tibialis posterior mechanics | L | MODEL EXISTS (sparse) — insertion mechanics cases (batch 2) |
| FT-22 | Freiberg infraction | Flattened metatarsal head (osteochondrosis) | L | VISUALISE ONLY — geometry (batch 2) |
| FT-23 | Toe polydactyly / syndactyly / macrodactyly | Extra, fused, or enlarged toes | L | VISUALISE ONLY — shape from scan (batch 2) |
| FT-24 | Calcaneovalgus foot | Newborn foot bent up/outward (usually flexible) | L | VISUALISE ONLY — infant geometry (batch 2) |
| FT-25 | Köhler / Sever osteochondroses | Paediatric navicular/heel growth-plate conditions | L | NO MODEL FOUND (batch 2) |

### Whole-body niche (WB, continued)

| ID | Issue | What changes anatomically | Priority | Status |
|---|---|---|---|---|
| WB-13 | Hemihypertrophy / hemihypotrophy | One body side over- or under-grown | L | PARAMETER — side-wise size/mass (batch 4) |
| WB-14 | Segmental overgrowth (Proteus, Klippel-Trénaunay) | Progressive asymmetric limb overgrowth (+ vascular in KTS) | L | VISUALISE ONLY — serial geometry (batch 4) |
| WB-15 | Acromegaly / gigantism proportions | Enlarged jaw, hands, feet; altered proportions | L | PARAMETER — proportion geometry (batch 4) |
| WB-16 | Multiple hereditary exostoses | Multiple bone outgrowths deforming limbs/joints | L | VISUALISE ONLY — outgrowth geometry (batch 4) |
| WB-17 | Neurofibromatosis type 1 skeletal signs | Tibial bowing/pseudoarthrosis, scoliosis link | L | VISUALISE ONLY — skeletal geometry (batch 4) |
| WB-18 | Cachexia (severe wasting) | Extreme muscle/fat loss changing body shape | L | PARAMETER — body-composition extremes (batch 4) |
| WB-19 | Burn / scar contractures | Skin/fascia shortening restricting joint motion regionally | M | PARAMETER (sparse) — ROM restriction (batch 4) |

### Muscle/soft-tissue niche (MS, continued)

| ID | Issue | What changes anatomically | Priority | Status |
|---|---|---|---|---|
| MS-11 | Muscle rupture with retraction (e.g. "Popeye" biceps) | Muscle belly displaced/deformed after tendon rupture | L | VISUALISE ONLY — displaced muscle geometry (batch 4) |
| MS-12 | Muscle hernia | Muscle bulging through fascial defect | L | VISUALISE ONLY — bulge geometry (batch 4) |
| MS-13 | Heterotopic ossification / myositis ossificans | Bone forming inside muscle → motion block | L | VISUALISE ONLY — ROM block geometry (batch 4) |
| MS-14 | Myotonic disorders (stiffness) | Delayed muscle relaxation altering movement pattern | L | NO MODEL FOUND (batch 4) |
| MS-15 | Chronic exertional compartment syndrome | Exercise-induced compartment pressure (functional, low geometry signal) | L | OUT OF SCOPE — no geometry signature (batch 4) |

### Bone/joint niche (BJ, continued)

| ID | Issue | What changes anatomically | Priority | Status |
|---|---|---|---|---|
| BJ-07 | Osteogenesis imperfecta | Brittle bones → recurrent fractures, bowing, short stature | L | MODEL EXISTS (research) — OI bowed-bone FE (batch 6) |
| BJ-08 | Paget disease of bone | Enlarged, deformed, weak bone (e.g. bowed tibia, skull) | L | VISUALISE ONLY — deformed bone geometry (batch 6) |
| BJ-09 | Fibrous dysplasia | Fibrous bone replacement → deformity (e.g. shepherd's-crook femur) | L | VISUALISE ONLY — deformity geometry (batch 6) |
| BJ-10 | Osteopetrosis | Over-dense brittle bone, deformity/fracture pattern | L | VISUALISE ONLY — density imaging record (batch 6) |
| BJ-11 | Limb-salvage / tumour resection reconstruction | Resected bone with endoprosthesis — non-standard anatomy | L | PARAMETER — custom geometry + implant block (batch 6) |

### Neuromotor niche (NM, continued)

| ID | Issue | What changes anatomically | Priority | Status |
|---|---|---|---|---|
| NM-13 | Charcot-Marie-Tooth disease | Progressive distal wasting → cavovarus feet, hand wasting | M | MODEL EXISTS — CMT OpenSim + exo optimisation (batch 7) |
| NM-14 | Friedreich / hereditary ataxias | Progressive scoliosis + pes cavus + gait ataxia pattern | L | MODEL EXISTS (sparse) — components only, ataxia unmodelled (batch 7) |
| NM-15 | Post-polio residual deformity | Asymmetric atrophy, limb shortening, joint deformity | L | PARAMETER — asymmetric weakness/atrophy set (batch 7) |

### Chest/breathing niche (RA, continued)

| ID | Issue | What changes anatomically | Priority | Status |
|---|---|---|---|---|
| RA-11 | Diaphragmatic eventration / unilateral elevation | Abnormally high, thin diaphragm dome | L | VISUALISE ONLY — diaphragm position (batch 5) |
| RA-12 | Post-surgical chest-wall deformity | Thoracotomy/mastectomy asymmetry affecting posture/breathing | L | PARAMETER — geometry + breathing asymmetry (batch 5) |

### Systemic congenital (NC) — cross-cutting

| ID | Issue | What changes anatomically | Priority | Status |
|---|---|---|---|---|
| NC-01 | Arthrogryposis multiplex congenita | Multiple congenital joint contractures (links UL/MS regions) | L | MODEL EXISTS (research) — subject MSK orthosis models (batch 8) |
| NC-02 | Down syndrome musculoskeletal pattern | Hypotonia + ligament laxity + atlantoaxial risk (SP-26) + flat feet | M | PARAMETER — combination + SP-26 flag (batch 8) |
| NC-03 | Cerebral-palsy-associated skeletal deformity set | Hip displacement, torsional deformity, scoliosis cluster (links NM-01/02) | M | MODEL EXISTS — CP deformity cluster, cross-ref (batch 8) |

## Count & working order

**202 issues** after the 2026-10-28 niche expansion (SP 30, HN 12,
SH 15, UL 11, HP 16, KN 18, FT 25, WB 19, MS 15, BJ 11, NM 15, RA 12,
NC 3). Sections A–L hold the common layer; section M holds the niche
layer with IDs continuing each region's numbering.

**Completeness, honestly:** no finite list is provably complete —
thousands of rare conditions exist. This list is complete *for its stated
scope* (geometry/posture/movement-relevant, incl. niche) to the best of
current clinical taxonomy (orthopaedic, congenital and neuromuscular
categories cross-checked at creation). New finds get appended with fresh
IDs; IDs are never renumbered.

**AUDIT COMPLETE — 202/202 researched** (2026-10-28): the original 9
(SP-01, SP-20, FT-01, FT-16, WB-03, RA-01, RA-02, RA-03, RA-10;
MS-03 completed via the fat-measurement notes + Batch 4),
**Batch 1: SP-02…SP-19** (`anatomy-audit-batch1-spine.md`),
**Batch 2: HP/KN/FT chain** (`anatomy-audit-batch2-hip-knee-foot.md`),
**Batch 3: SH-01…SH-15** (`anatomy-audit-batch3-shoulder.md`),
**Batch 4: WB/MS** (`anatomy-audit-batch4-wholebody-muscle.md`),
**Batch 5: HN + RA remainder**
(`anatomy-audit-batch5-headneck-chest.md`), **Batch 6: UL + BJ**
(`anatomy-audit-batch6-armhand-bonejoint.md`), **Batch 7: NM**
(`anatomy-audit-batch7-neuromotor.md`), and **Batch 8: SP niche + NC**
(`anatomy-audit-batch8-niche-spine-crosscutting.md` — includes the
five-mechanism closing synthesis). Remaining TO CHECK: 0.

Suggested audit order (by twin impact):
1. **Spine/trunk remainder** (SP-05…SP-19) — posture is the core claim.
2. **Hip/knee/foot alignment chain** (HP, KN, FT remainder) — gait and
   squat-class movement claims depend on it.
3. **Shoulder girdle** (SH) — upper-body correction claims.
4. **Whole-body + muscle** (WB, MS) — asymmetry, atrophy, hypermobility.
5. **Chest/abdominal** (RA remainder) + **head/neck** (HN).
6. **Neuromotor + bone/joint + arm/hand** (NM, BJ, UL) — population
   coverage and edge cases.

For each issue, the audit records: model exists? (paper / dataset /
software / OpenSim-FE-avatar), open or closed, input it needs, accuracy
evidence, and a twin decision (adopt / adapt / visualise-only / exclude).
Findings go in follow-up research notes per region, linked from here.
