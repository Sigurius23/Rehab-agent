# Anatomy audit — Batch 5: head & neck (HN) + chest/abdominal remainder (RA)

> Filed 2026-10-28. Fifth systematic batch from
> [`anatomy-issues-checklist.md`](anatomy-issues-checklist.md):
> HN-01…HN-12 and RA-04…RA-09, RA-11, RA-12 (RA-01/02/03/10 were
> researched earlier via the breathing programme). 20 issues.

## Headline findings

1. **The neck is modelled; the cervical curve is not surface-visible.**
   A proper OpenSim head–neck model exists (Mortensen 2018: 20 DOF,
   84 muscle subvolumes in 15 groups; an impact variant adds 80
   ligament sections). Head *pose* is measurable by our camera twin,
   but the internal cervical curve (lordosis/kyphosis, HN-02/03) needs
   lateral imaging — surface posture only weakly proxies it.
2. **Forward head posture has an honest error budget**: the
   craniovertebral angle (CVA) from photogrammetry is valid/reliable
   with a minimum detectable change of ≈ 5° — so the twin may report
   CVA trends only above ~5°, exactly matching the accuracy doc's
   sagittal-plane philosophy.
3. **Chest-wall deformity is FE territory with real validation**:
   patient-specific FE simulation of the Nuss procedure predicts
   postoperative chest contour to ~3% / sternal elevation within
   ~5 mm of postoperative CT; carinatum brace FE models even simulate
   the rib-flare side effect. Surface geometry (pectus depth, rib
   flare, rib hump) *is* surface-measurable — one of the few places
   our scan twin measures the actual deformity, though severity
   indices like Haller still need CT.
4. **The jaw is a separate specialty**: a validated dynamic jaw +
   FE TMJ model exists (muscle-driven rigid-body mandible, FE disc,
   MRI-validated), but nothing about it belongs in the posture
   pipeline; jaw items are record/visualise-only for us.

## Head & neck (HN)

| ID | Verdict | Model / evidence | Twin decision |
|---|---|---|---|
| HN-01 Forward head posture | PARAMETER | CVA photogrammetry valid vs radiography; MDC ≈ 5° (ICC 0.83–0.89) | CVA as headline surface metric; report changes ≥5° only |
| HN-02 Loss of cervical lordosis | PARAMETER (imaging) | Radiographic ARA C2–C7 / C2–C7 SVA, ICC > 0.7, SEM 1–2° | Imaging-sourced curve parameter at Tier-A onboarding; never surface-inferred |
| HN-03 Cervical kyphosis | PARAMETER (imaging) | As HN-02 | As HN-02 |
| HN-04 Torticollis | ADAPT (neck model) | OpenSim Mortensen neck model can carry shortened/raised-stiffness SCM parameters; congenital form = SCM fibrosis/shortening clinically | Head tilt/rotation envelope + SCM parameter; cause (muscular vs dystonic vs ocular) is clinical |
| HN-05 TMJ disorder/jaw misalignment | RESEARCH ONLY | Dynamic jaw model with FE TMJ disc, validated against MRI protrusion/opening | Record only; dental/maxillofacial specialty |
| HN-06 Cranial asymmetry (plagiocephaly) | PARAMETER (surface geometry) | Head shape is directly scannable (cranial vault asymmetry indices are surface metrics) | Serial head-shape record (infant pathway = clinician-led) |
| HN-07 Cervical rib | VISUALISE ONLY | Imaging finding; links SH-09 (no TOS model, Batch 3) | Record if imaged |
| HN-08 Hemifacial microsomia | VISUALISE ONLY | Craniofacial geometry; surgical-planning literature | Geometry record |
| HN-09 Jaw size/position discrepancies | PARAMETER (geometry) | Cephalometric geometry (imaging) | Geometry parameters if imaged |
| HN-10 Ocular torticollis | **NO MODEL FOUND** (cause is ophthalmic) | Head-tilt posture is recordable; cause is eye-muscle imbalance | Record tilt; twin must never attribute cause |
| HN-11 Webbed neck | VISUALISE ONLY | Surface/neck contour geometry | Geometry record |
| HN-12 TMJ ankylosis | PARAMETER (sparse) | Jaw-opening restriction (mm) as ROM parameter; FE implant literature | Opening ROM record only |

## Chest, rib cage & abdominal wall (RA remainder)

| ID | Verdict | Model / evidence | Twin decision |
|---|---|---|---|
| RA-04 Pectus excavatum | MODEL EXISTS (research) | Patient-specific CT→FE Nuss simulations validated vs postoperative CT (≈3% contour, ≈5 mm sternal elevation) | Surface depression geometry from scan (honest surface metric); Haller index + any surgical claim = CT only; FE offline |
| RA-05 Pectus carinatum | MODEL EXISTS (sparse) | Patient FE thorax models simulate brace compression and the rib-flaring side effect | Surface protrusion geometry; brace work clinician-led |
| RA-06 Barrel chest (COPD) | PARAMETER | AP/ML chest geometry + compartment kinematics measurable (OEP; multi-volume CT deformation metrics) | Geometry + breathing-compartment parameters; respiratory claims screening-only (D-03) |
| RA-07 Rib flare | PARAMETER (surface) | Lower-rib protrusion is surface geometry, coupled to diaphragm position/lordosis | Surface metric; interpretation with breathing layer |
| RA-08 Rib hump | PARAMETER (surface) | Rotational rib deformity is what scoliosis surface topography measures (links SP-01) | Surface topography metric; curve magnitude itself = imaging (Batch 1 rule) |
| RA-09 Abdominal wall hernia | MODEL EXISTS (research) | Patient-specific abdominal-wall FE (breathing/lifting loads, mesh/suture simulation, recurrence studies) | Defect geometry record; FE offline, surgical specialty |
| RA-11 Diaphragmatic eventration/elevation | VISUALISE ONLY | Diaphragm-position finding (ultrasound/fluoroscopy, links RA-03) | Record via breathing-layer ultrasound pathway |
| RA-12 Post-surgical chest-wall deformity | PARAMETER | Chest asymmetry geometry + compartment breathing asymmetry (OEP-lite, breathing note) | Serial geometry + breathing-asymmetry screening metrics |

## Build implications

1. **Adopt CVA with its 5° floor** (HN-01) and treat all other
   head/neck posture numbers as model/imaging parameters — the neck
   model (Mortensen) is the simulation carrier if neck loading ever
   enters scope.
2. **Surface twin earns three honest chest metrics**: pectus
   depression/protrusion depth, rib flare, rib hump (RA-04/05/07/08)
   — geometry yes, severity indices no.
3. Nothing in HN/RA changes the sensor set; TMJ and craniofacial items
   stay record-only so the twin never drifts into dental/ophthalmic
   claims (HN-10 is the standing example).

## Sources (accessed 2026-10-28)

- OpenSim Human Neck Model (Mortensen 2018 lineage; confluence docs);
  head-impact variant with ligament sections, J R Soc Interface (2019)
- CVA photogrammetry validity/MDC — J Clin Med (2024) radiography
  comparison; FHP-app validation, PMC7559098 (MDC 4.96–5.52°)
- Nuss FE simulation — in silico Nuss study, PMC10703950 (2023);
  simulation-vs-postoperative-CT feasibility (2018, ~3% contour error)
- Pectus carinatum elastic-thorax FE + rib-flare simulation (Springer
  2024 workflow; bracing literature)
- Dynamic jaw + FE TMJ — PMC6757193 (MRI-validated)
- COPD chest-wall kinematics — OEP pursed-lip study (2007);
  multi-volume CT diaphragm/chest-wall deformation metrics (AJRCCM
  2025 abstract)
- Hernia FE — patient-specific ventral hernia repair FE (PMC, 2026);
  abdominal-wall breathing/contraction FE (2023)
