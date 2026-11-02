# Anatomy audit — Batch 8 (final): niche spine (SP-21…SP-30) + cross-cutting (NC)

> Filed 2026-10-28. Eighth and final systematic batch from
> [`anatomy-issues-checklist.md`](anatomy-issues-checklist.md):
> SP-21…SP-30 and NC-01…NC-03. 13 issues. **This completes the
> 202-issue audit (202/202 researched).**

## Headline findings

1. **The niche-spine items inherit Batch 1's machinery**: fused or
   stiffened segments = locked joints on the articulated-spine carrier
   (Klippel–Feil, DISH, OPLL — the ankylosing-spondylitis pattern),
   congenital curve drivers = rest-geometry from EOS/CT (hemivertebra,
   gibbus), and transitional anatomy = a segment-count/load parameter
   with real FE support (lumbosacral transitional vertebra models
   quantify the altered ROM and stress at the accessory articulation).
2. **One item is a safety flag, not a model**: atlantoaxial instability
   (SP-26, and with it the Down syndrome pattern NC-02). Excess C1–C2
   motion from transverse-ligament laxity/odontoid anomalies is a
   cord-injury risk. The twin's job is to *store the flag and restrict
   protocols* (no end-range neck loading, no exo neck actuation,
   assessment contraindications) — modelling the instability itself
   would be pointless and unsafe to act on.
3. **Cross-cutting syndromes decompose, as designed**: arthrogryposis
   already has subject-specific MSK orthosis-design modelling
   (muscles disabled/weak-substituted per subject; contractures as
   passive joint stiffness), Down syndrome is the NM-12 + MS-07 +
   FT + SP-26 parameter combination, and the CP skeletal set is the
   Batch-2/7 cluster (torsion, hip displacement, scoliosis) seen as
   one patient. The checklist's cross-references did their job — no
   new model families were needed to close the audit.

| ID | Verdict | Model / evidence | Twin decision |
|---|---|---|---|
| SP-21 Klippel–Feil | PARAMETER | Fused cervical segments = locked joints on the neck/spine carriers (Batch 5/1); adjacent-level hypermobility is the known compensation | Locked-segment set from imaging; neck ROM envelope per level |
| SP-22 Hemivertebra/congenital malformation | PARAMETER (geometry) | Congenital curve geometry handled by EOS/CT 3D reconstruction (Batch 1 congenital work) | Rest-geometry parameter; growth = serial imaging, clinician-led |
| SP-23 Lumbosacral transitional vertebra | MODEL EXISTS (research) | FE models of accessory L5–S1 articulation quantify changed ROM/stress vs normal (2019) | Segment-count + lumbosacral load parameter; level-counting noted for any spinal procedure |
| SP-24 Spina bifida | MODEL EXISTS | MSK gait simulations (tibial forces/joint loads vs typical development); level-dependent muscle-resource tables are standard | Weakness-by-neurological-level parameter set (NM framework); arch defect itself = imaging record |
| SP-25 DISH | MODEL EXISTS (research) | Spine FE with ossified anterior longitudinal ligament shows disc-stress redistribution and long-lever-arm fracture mechanics | Stiffened-segment set (AS family, Batch 1); bone/fragility caution flag |
| SP-26 Atlantoaxial instability | **NO MODEL — SAFETY FLAG** | Clinical/biomechanical literature: transverse-ligament laxity ± odontoid anomaly → excess C1–C2 translation, cord risk | Mandatory manifest safety flag; restricts neck ROM in assessments and prohibits neck actuation; status set by clinician imaging only |
| SP-27 Gibbus deformity | VISUALISE ONLY | Sharp angular kyphosis = rest geometry (imaging-defined) | Geometry record on spine carrier |
| SP-28 Thoracic insufficiency syndrome | PARAMETER (sparse) | Chest-volume/lung-growth condition managed with expandable rib devices (VEPTR); no twin-class model | Chest geometry + breathing-layer record; paediatric specialist pathway |
| SP-29 Basilar invagination/cranial settling | VISUALISE ONLY | Skull-base/cervical geometry (imaging); neurologically safety-relevant | Imaging record + shares SP-26-style caution flag |
| SP-30 OPLL | PARAMETER | Ossified ligament = stiffened segments + canal narrowing (DISH-associated FE family) | Stiffened-segment set; canal = visualise-only |
| NC-01 Arthrogryposis multiplex congenita | MODEL EXISTS (research) | Subject-specific MSK modelling for amyoplasia orthosis design (disabled/weak muscles substituted; contractures as passive stiffness) | Multi-joint contracture + weakness parameter set (UL/MS families, patient-specific) |
| NC-02 Down syndrome pattern | PARAMETER (combination) | Gait-initiation/biomechanics studies quantify hypotonia+laxity effects; components: NM-12 hypotonia, MS-07 laxity, FT flat feet | Parameter combination + **mandatory SP-26 safety flag check** |
| NC-03 CP skeletal deformity set | MODEL EXISTS | The Batch-2/7 cluster as one patient: Torsion-Tool personalisation, FDO cohort, hip-displacement and scoliosis pathways | Cross-referenced parameter set; closes the CP thread |

## Closing synthesis — what 202 issues taught the design

Across all eight batches the verdicts collapse into **five reusable
 mechanisms**, which is the real output of this audit:

1. **Parameter layers** (spinopelvic angles, torsion, carrying angle,
   segment lengths, ROM envelopes) — cheap, honest, adopted.
2. **One muscle-parameter pipeline** (volume/fat/strength → weakness,
   contracture, reflex-gain groups) — serves MS, WB, NM, SH, UL.
3. **Patient-specific FE/SSM from imaging** (spine, hip, knee, foot,
   chest, bone strength) — Tier-A, offline, research-grade only.
4. **Prosthesis/orthosis device blocks** in the manifest (implants,
   AFO/exo torque design loops).
5. **Safety flags and honesty labels** (atlantoaxial risk, bone
   quality, scapula=model-inferred, "not representable" hands,
   pattern-labels-not-diagnoses) — the twin says what it cannot do.

And the recurring negative result, now documented 202 times over:
**nothing internal — bone shape, joint space, muscle quality,
ligament state, neural drive — is inferable from camera/LiDAR.**
The surface twin measures surface geometry, limb volume, chest
motion and posture angles within stated error floors; everything
deeper enters through imaging and clinical assessment at Tier-A
onboarding, exactly as `docs/accuracy.md` requires.

## Sources (accessed 2026-10-28)

- LSTV FE — computational L5–S1 accessory-articulation ROM/stress
  pilot (2019); Bertolotti syndrome review (PMC4603258)
- DISH spine FE — ossified-ALL finite-element analysis (Appl Sci
  2021); DISH fracture pathomechanics reviews
- Atlantoaxial instability in Down syndrome — clinical literature on
  transverse-ligament laxity/odontoid anomalies (Medscape review;
  anaesthesia C-spine reviews)
- Spina bifida MSK simulation — ambulatory spina-bifida joint-force
  simulations (PMC9772073); level-based gait-pattern literature
- Thoracic insufficiency/VEPTR — Campbell lineage, CHOP centre and
  expansion-thoracoplasty literature
- Arthrogryposis modelling — subject-specific MSK passive-orthosis
  design for amyoplasia (PMC6453054)
- Down syndrome biomechanics — gait-initiation study (BMC Neurol
  2019) and DS motor-profile literature
