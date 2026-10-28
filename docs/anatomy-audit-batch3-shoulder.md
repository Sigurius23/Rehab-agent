# Anatomy audit — Batch 3: shoulder girdle (SH-01 … SH-15)

> Filed 2026-10-28. Third systematic batch from
> [`anatomy-issues-checklist.md`](anatomy-issues-checklist.md).
> Verdict key as in Batches 1–2.

## Headline findings

1. **The shoulder has real, open, adoptable models — the problem is
   measurement, not modelling.** The scapula slides on the rib cage
   *under skin and muscle*, so no camera or surface scan observes it
   directly. Every credible model therefore treats the scapula as
   **constrained inference**: the reference implementation (Seth et al.
   scapulothoracic joint, OpenSim, free on SimTK) constrains the scapula
   to an ellipsoid fitted to the thorax and drives it from humerus/
   clavicle motion — validated against **bone-pin** ground truth to
   within **2 mm RMSE**, and shown to cut marker-noise variability by
   ~65% vs unconstrained angles. SKEL (already catalogued) uses the same
   sliding-scapula idea. TU Delft's thoracoscapular/Delft shoulder-elbow
   models (TSM/TDSEM) add closed-loop shoulder-girdle musculature and
   subject-specific scaling tools.
   **Twin rule: scapula pose is always labelled *model-inferred*, never
   measured. Bone pins and biplanar videoradiography are the only
   ground truths, and neither is in our clinic.**
2. **Most shoulder "issues" are force/geometry parameters of those
   models**: a winging scapula is serratus-anterior/trapezius force
   deficiency; Poland syndrome is a deleted pectoralis; frozen shoulder
   is ROM limits; rotator-cuff fatty infiltration is a muscle-quality
   parameter whose *measurement* already lives in our fat-distribution
   methods (MRI fat fraction / Goutallier grading).
3. **Impingement is a shape-and-space question** answered by statistical
   shape models + FE (scapular shape modes are statistically linked to
   cuff tears and subacromial narrowing using in-vivo biplanar
   kinematics) — imaging territory, not camera territory.

## Per-issue verdicts

| ID | Verdict | Best existing model / evidence | Twin decision |
|---|---|---|---|
| SH-01 Rounded shoulders | PARAMETER | Resting scapular protraction/anterior-tilt/downward-rotation + thoracic kyphosis (SP-06) outputs of shoulder models | Posture metrics per session; no condition model |
| SH-02 Scapular winging | ADAPT | Shoulder MS models (Seth/Delp thoracoscapular; Delft) accept per-muscle force scaling — winging = serratus anterior (medial winging, long thoracic) or trapezius (lateral winging, spinal accessory) deficiency; clinical medial/lateral classification is well defined | Muscle-deficiency parameters; cause (nerve vs muscle) is a clinical finding, not inferred |
| SH-03 Scapular dyskinesis | PARAMETER (measurement) | Kibler type I–IV pattern classification on model kinematics; visual rating inter-rater reliability only ~0.48–0.61, 3D wing-CT 0.97 — quantify from model angles, don't eyeball | Compute pattern metrics from inferred scapula kinematics, with inferred-label |
| SH-04 Impingement anatomy | RESEARCH ONLY | FE supraspinatus impingement simulations (stress concentration at critical zone); scapula SSM coupled to congruence biomechanics: glenoid cranial orientation + subacromial narrowing associated with cuff tears; acromion morphology parameters (Bigliani type, critical shoulder angle, acromial index) | Shape parameters from imaging if present; no impingement claim from motion alone |
| SH-05 Rotator cuff tear + fatty infiltration | ADAPT | Validated human computational shoulder model used to simulate cuff-tear repair mechanics/tension; muscle side parameterised by volume + fat fraction — measurable by MRI Dixon fat fraction (fat-distribution note) and graded clinically (Goutallier) | Muscle-quality parameters per cuff muscle at Tier-A onboarding; tear geometry from imaging only |
| SH-06 Frozen shoulder | PARAMETER | Capsular contracture = joint ROM envelope; no special model | ROM limits measured per session |
| SH-07 Shoulder instability | RESEARCH ONLY | Glenohumeral FE stability/labral modelling literature; joint-centre constraint assumptions are exactly what MS models simplify | Geometry/clinical history; no stability simulation claims |
| SH-08 Clavicle malunion | PARAMETER | Clavicle length/orientation is explicit in closed-loop shoulder models (Delft family); shortening effects simulated in shoulder-kinematics studies | Clavicle geometry parameter from imaging/scan |
| SH-09 Thoracic outlet anatomy | **NO MODEL FOUND** (twin-relevant) | Surgical/anatomical literature; no biomechanical twin model of neurovascular compression found | Record anatomy if imaged; exclude from simulation |
| SH-10 Sprengel deformity | VISUALISE ONLY | Elevated scapula = scapula rest-position geometry | Rest-position parameter |
| SH-11 Poland syndrome | PARAMETER | Absent pectoralis major = remove/zero that actuator in the MS model; chest asymmetry geometry | Muscle-set parameter from imaging/exam |
| SH-12 Snapping scapula | RESEARCH ONLY (sparse) | Scapulothoracic contact modelling is rare; mostly clinical/CT classification | Record; no model claims |
| SH-13 Erb's palsy posture | RESEARCH ONLY (sparse) | Paediatric shoulder MS modelling scarce; posture is a muscle-imbalance parameter set | Muscle parameters; specialist population |
| SH-14 Glenoid dysplasia/retroversion | RESEARCH ONLY | Glenoid version is a quantified SSM shape mode (extremes differ ~8.7° version in cuff-tear shape analysis) | Version angle parameter from imaging |
| SH-15 Os acromiale | VISUALISE ONLY | Anatomical variant; acromial geometry | Note in manifest; geometry if imaged |

## Build implications

1. **Adopt a scapulothoracic-constrained shoulder model** (Seth OpenSim
   model family / Delft TDSEM scaling) for the upper-body stage; do not
   regress scapula pose freely from markers or depth.
2. **Scapula = inferred, with error budget.** The 2 mm figure is against
   bone pins in a lab model fit; our markerless input will be worse.
   Shoulder correction claims must carry the scapula caveat (add to the
   accuracy error-budget table when implemented).
3. **Cuff muscle quality joins the fat-layer outputs**: per-muscle fat
   fraction from onboarding MRI is the honest input for SH-05/MS-03 —
   one measurement pipeline, several checklist items served.
4. Gaps recorded: SH-09 (no model), SH-12/SH-13 (sparse).

## Sources (accessed 2026-10-28)

- Seth et al., biomechanical scapulothoracic joint model (OpenSim,
  bone-pin validation 2 mm RMSE) — SimTK thoracoscapular project;
  Seth/Delp shoulder model muscle-contribution studies (SimTK, free)
- TU Delft TDSEM/TSM scaling & validation tools (2021)
- Scapula SSM + cuff-tear association with in-vivo biplanar kinematics
  (Henry Ford Health scholarly commons); acromion morphology /
  critical shoulder angle literature
- Scapular dyskinesis classification & reliability (Kibler types;
  3D wing-CT IRR 0.972 vs visual 0.780) — J Shoulder Elbow Surg line
- Rotator-cuff tear/fatty-infiltration modelling & Goutallier grading —
  Mannava et al. review (2013) and human shoulder simulation lineage
- Winging classification (medial=serratus/long thoracic,
  lateral=trapezius/spinal accessory) — WikiMSK / Fiddian classification
