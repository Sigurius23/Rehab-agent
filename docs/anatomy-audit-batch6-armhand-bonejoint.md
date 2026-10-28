# Anatomy audit — Batch 6: arm & hand (UL) + bone & joint, general (BJ)

> Filed 2026-10-28. Sixth systematic batch from
> [`anatomy-issues-checklist.md`](anatomy-issues-checklist.md):
> UL-01…UL-11 and BJ-01…BJ-11. 22 issues.

## Headline findings

1. **The arm/hand carrier models exist in OpenSim**: MoBL-ARMS
   (Saul et al. 2015; 15 DOF across shoulder, elbow, forearm, wrist,
   thumb and index finger; 50 muscle compartments) for the arm, and
   the TU Delft OpenSim hand–wrist model (Mirakhorlo et al.; 23 DOF,
   43 muscles, tendon forces validated against experimental data) for
   the hand. Nearly every UL item is then a joint-limit, joint-axis or
   muscle-parameter edit on those carriers.
2. **One hard twin limitation found**: SMPL-X/MANO hand topology has a
   fixed digit count and layout. Syndactyly/polydactyly (UL-09) and
   radial club hand (UL-07) **cannot be represented** by the parametric
   hand — these need scan-based custom hand geometry, or honest
   "not representable" labelling. Surface-only hand claims must say so.
3. **Bone strength is FE-solved and it matters for exo safety**:
   QCT-based FE femoral strength predicts failure load better than BMD
   (R² ≈ 0.80–0.85, validated in vitro; load-to-strength ratio predicts
   hip fracture prospectively). For a haptic/actuated exo, bone-quality
   flags (osteoporosis, OI, Paget's) are *load-limit inputs*, not
   trivia — they belong in the twin manifest beside joint ROM limits.
4. **Implants generalise**: reverse-shoulder arthroplasty now has
   OpenSim virtual-surgery pipelines (statistical scapula models →
   implant placement → predictive ADL simulation) — the same
   "prosthesis block in the manifest" pattern as HP-09/KN-12/Batch 2.

## Arm & hand (UL)

| ID | Verdict | Model / evidence | Twin decision |
|---|---|---|---|
| UL-01 Cubitus valgus/varus | PARAMETER | Carrying angle is a defined measurement (normal ≈5–15°; >15° valgus, <5° varus; goniometer/imaging) | Elbow joint-axis/alignment parameter per side |
| UL-02 Elbow flexion contracture | PARAMETER | ROM envelope + passive-stiffness parameters (MS-04 family) on MoBL-class models | ROM limit per joint; cause clinical |
| UL-03 Madelung deformity | VISUALISE ONLY | Distal-radius growth geometry (imaging-defined); no dynamic model | Wrist geometry if imaged |
| UL-04 Dupuytren's contracture | PARAMETER (sparse) | Per-finger fixed flexion angles are directly measurable; FE finger models simulate tendon/fascia imbalance mechanisms | Joint-limit set per finger on the hand model; progression = serial angles |
| UL-05 Rheumatoid hand deformities | RESEARCH ONLY | FE finger models reproduce swan-neck/boutonnière mechanisms (central-slip / FDS removal conditions); cadaveric SND models likewise | Record deformity angles per joint; mechanism claims excluded |
| UL-06 Congenital radioulnar synostosis | PARAMETER | Forearm rotation is an explicit DOF in MoBL-class models — fused = locked at measured angle | Locked-rotation parameter |
| UL-07 Radial longitudinal deficiency | VISUALISE ONLY | Hand/forearm geometry adaptation; parametric hand topology cannot represent it faithfully | Scan geometry; label parametric-hand mismatch |
| UL-08 Camptodactyly/clinodactyly | PARAMETER | Fixed finger flexion/lateral curvature as per-joint angle limits in the hand model | Joint-limit parameters |
| UL-09 Syndactyly/polydactyly | VISUALISE ONLY | Digit count/layout differs from MANO/SMPL-X fixed topology | Custom scan geometry or explicit "not representable" state |
| UL-10 Volkmann ischaemic contracture | PARAMETER | Forearm fibrosis → claw posture = contracture parameter family (MS-04) on arm+hand models | Muscle passive-stiffness + joint-limit set |
| UL-11 Trigger finger | **NO MODEL FOUND** (dynamic catching) | Stenosing tenosynovitis is a tendon-gliding event; MSK models don't simulate catching | Record grip function/ROM clinically; no model claims |

## Bone & joint — general (BJ)

| ID | Verdict | Model / evidence | Twin decision |
|---|---|---|---|
| BJ-01 Osteoporosis/low BMD | MODEL EXISTS (research) | QCT hvFE femoral strength validated in vitro (strength R² 0.80–0.85, beats BMD) and prospectively (load-to-strength HR ≈ 4.0) | DXA/QCT bone-quality flag in manifest; exo load limits derated; FE offline Tier-A |
| BJ-02 OA, other joints | RESEARCH ONLY | Same joint-FE/SSM family as Batch 2 (shoulder/ankle/facet/hand OA imaging models) | Joint-space/alignment parameters from imaging |
| BJ-03 RA deformity pattern | VISUALISE ONLY | Pattern record; hand mechanisms at UL-05 | Deformity-geometry record; activity/diagnosis clinical |
| BJ-04 Fracture malunion | MODEL EXISTS | 3D CT planning with mirrored contralateral template + simulated osteotomy is clinical routine (systematic-review level for distal radius) | Deformity angles from imaging; twin visualises current vs mirrored-contralateral geometry |
| BJ-05 Other joint replacements (shoulder/ankle) | ADAPT | RTSA OpenSim virtual-surgery + predictive-sim pipelines; muscle-wrapping validated intact vs implanted | Prosthesis block in manifest (type/side/ROM envelope), as HP-09/KN-12 |
| BJ-06 Rickets/osteomalacia | PARAMETER | Bowing geometry parameters once imaged (geometry family of BJ-07) | Long-bone curvature parameters; metabolic cause clinical |
| BJ-07 Osteogenesis imperfecta | MODEL EXISTS (research) | Patient-specific FE of bowed OI tibia/femur quantifies fracture risk vs bowing angle | Geometry + bone-quality flag; strict exo load derating; FE offline |
| BJ-08 Paget disease | VISUALISE ONLY | Enlarged/deformed bone geometry (imaging) | Geometry + bone-quality flag |
| BJ-09 Fibrous dysplasia | VISUALISE ONLY | Deformity geometry (e.g. shepherd's-crook femur) | Geometry if imaged |
| BJ-10 Osteopetrosis | VISUALISE ONLY | Density disorder; geometry often near-normal until fracture/deformity | Imaging record; bone-quality flag |
| BJ-11 Limb-salvage/tumour reconstruction | PARAMETER | Non-standard anatomy + endoprosthesis = geometry + implant-block family (WB-07/BJ-05) | Custom geometry + prosthesis block; specialist pathway |

## Build implications

1. **Adopt MoBL-ARMS + TU Delft hand as the UL carriers** (model
   references, SimTK/OpenSim ecosystem — verify distribution terms
   before vendoring anything; this repo clones nothing by default).
2. **Add a `bone_quality` block to the twin manifest** (DXA T-score /
   QCT class / diagnosed bone disease) feeding exo torque derating —
   BJ-01/07/08/10 become safety inputs, not annotations.
3. **Hand-topology honesty rule** (UL-07/09): when a hand can't be
   represented by the parametric model, the twin must say so and fall
   back to scan geometry — never silently draw a five-normal-finger
   hand.
4. Malunion (BJ-04) gives a clean visualisation pattern: current bone
   vs mirrored healthy side — reusable for WB-13/FT asymmetries.

## Sources (accessed 2026-10-28)

- MoBL-ARMS upper-limb model — Saul et al. (2015), 15 DOF / 50 muscle
  compartments (OpenSim)
- TU Delft hand–wrist OpenSim model — Mirakhorlo et al. (2016), 23 DOF /
  43 muscles, tendon-force validation
- QCT FE femoral strength — hvFE validation (2012, R² 0.80–0.85);
  DXA+FE fracture-risk cohort (load-to-strength HR ≈ 4.0)
- RTSA predictive simulation with statistical + MSK shoulder models —
  Silvestros et al., J Orthop Res (2024); muscle-wrapping model intact
  vs rTSA, PMC6857842
- Malunion 3D planning — distal-radius corrective-osteotomy systematic
  review, PMC12343530 (2025); upper-extremity 3D planning review,
  PMC7887308
- Finger-deformity FE (swan-neck/boutonnière mechanisms) — 3D finger
  FE tendon-rupture simulations (JSME); in-vitro SND model (2022)
- Carrying-angle norms/measurement — elbow arthro-kinematics and
  clinical goniometry literature (5–15° normal range)
- OI bowed-bone FE fracture risk — Caouette et al. patient-specific
  OI tibia/femur FE line
