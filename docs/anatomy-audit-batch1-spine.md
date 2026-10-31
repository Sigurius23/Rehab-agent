# Anatomy audit — Batch 1: spine & trunk (SP-02 … SP-19)

> Filed 2026-10-28. First systematic batch from
> [`anatomy-issues-checklist.md`](anatomy-issues-checklist.md).
> SP-01 (scoliosis) and SP-20 (spine-bending mechanics) were researched
> earlier; this batch covers the remaining common spine/trunk issues.
> Verdict key: **ADOPT** (usable in our OpenSim stage), **ADAPT**
> (exists, needs personalisation work), **RESEARCH ONLY** (papers/FE,
> no turnkey use), **PARAMETER** (not a separate model — a configuration
> of the spine model we already plan to use), **VISUALISE ONLY**.

## Headline finding

**The spine is the best-modelled region on the entire checklist — almost
nothing here is unmodelled.** But the coverage splits into two very
different kinds:

1. **Posture/alignment "issues" (SP-06…SP-13) are mostly not diseases with
   their own models — they are parameter values of one model class**: the
   *spinopelvic sagittal-alignment framework* (pelvic incidence PI —
   fixed per person; sacral slope SS; pelvic tilt PT; lumbar lordosis LL;
   thoracic kyphosis; sagittal vertical axis; Roussouly morphotypes;
   SRS-Schwab modifiers). PI = PT + SS, healthy PI ≈ 33–85°, and the
   clinical target LL ≈ PI ± 9°. Any posture claim we make should be
   expressed in these parameters, measured from the twin, not invented
   per condition.
2. **Structural conditions (SP-02…05, SP-14…SP-19) are modelled as
   patient-specific finite-element (FE) spines** built from that person's
   CT/EOS — extensively published, validated against cadaver/in-vivo data,
   and almost never released as reusable code. Our route is the geometry
   pipeline (EOS/CT → personalised model), not downloading "a
   spondylolisthesis model".

Two reusable platforms stand out:
- **Bruno articulated thoracolumbar OpenSim model** (SP-20 note) — the
  musculoskeletal carrier for nearly every verdict below.
- **SpineView (UPF)** — a public repository of **16,807 thoracolumbar FE
  spine models** generated from EOS images via a statistical shape model
  (SSM) + mesh morphing, personalisable from sagittal-balance
  measurements. The closest thing to a spine-morphology dataset that
  exists; directly relevant to Tier-A personalisation.

## Per-issue verdicts

| ID | Verdict | Best existing model(s) | Evidence / notes | Twin decision |
|---|---|---|---|---|
| SP-02 Congenital scoliosis | ADAPT | Biplanar (EOS) 3D reconstruction incl. hemivertebra modelling; patient-specific FE/3D-printed models for surgery | EOS reconstruction vs CT mean shape accuracy **1.8 mm**; hemivertebra shape/pose auto-quantified | Same personalisation pipeline as SP-01, with malformed-vertebra geometry from imaging (Tier A) |
| SP-03 Neuromuscular scoliosis | RESEARCH ONLY (partial) | CT-based 3D pelvic-asymmetry analysis + surgical simulation (53 neuromuscular pelvises: asymmetry in 88.6%); generic scoliosis FE adapted per patient | Geometry side is solved like SP-01/02; the *muscle-imbalance driver* (which muscles, how weak) has no validated model — that belongs to the NM batch | Geometry ADAPT; do not claim cause. Muscle drivers deferred to NM audit |
| SP-04 Adult degenerative scoliosis | ADAPT | Patient-specific FE degenerative lumbar scoliosis (CT→Mimics/ANSYS), validated | Cobb/LL error < 1°, centroid deviation < 1.76 mm (2025); earlier T12–S1 patient FE models exist | Personalisation pipeline + degenerated-disc parameters (SP-18) |
| SP-05 Scheuermann's hyperkyphosis | ADAPT | Coupled OpenSim musculoskeletal + CT-based FE, subject-specific (20 Scheuermann thoracolumbar-kyphosis patients vs 20 controls, 2025) | In-vivo mocap+EMG → OpenSim forces → FE tissue stress; peri-spinal stress elevation quantified | Bruno posed with wedged-vertebra geometry from imaging; FE as offline Tier-A study |
| SP-06 Postural kyphosis | PARAMETER | Spinopelvic framework; flexible curve = pose, not bone | No bone change by definition; measure thoracic kyphosis angle + flexibility | Pose parameters on the articulated spine; store TK angle per session |
| SP-07 Lumbar hyperlordosis | PARAMETER | Spinopelvic framework (LL, PI−LL mismatch) | LL target ≈ PI ± 9°; PI−LL mismatch tracks disability in chronic LBP cohorts | Parameters, not a model. Flag PI−LL mismatch, clinician thresholds (D-03) |
| SP-08 Flat back / hypolordosis | PARAMETER | Same framework; surgical flatback literature models sagittal imbalance + compensation (pelvic retroversion, knee flexion) | Compensation chain is modelled in adult-deformity work | Parameters + compensation-chain outputs |
| SP-09 Swayback posture | PARAMETER | Whole-body sagittal posture classification (SVA, PT, trunk shift) | Posture pattern, no structural lesion | Posture-pattern classifier on twin parameters |
| SP-10 Anterior pelvic tilt | PARAMETER | Spinopelvic PT/SS (PT is the dynamic rotation term of PI = PT + SS) | Directly measurable from twin pelvis orientation | Session metric; linked muscle pattern = MS-06 (lower crossed), audit later |
| SP-11 Posterior pelvic tilt | PARAMETER | Same as SP-10 | — | Session metric |
| SP-12 Pelvic obliquity | ADAPT | 3D pelvic geometry from EOS/CT; neuromuscular CT series quantify hemipelvis asymmetry in 3 planes | Weight-bearing hemipelvis remodels (opening/closing, pivoting, shortening) | Geometry from onboarding imaging/scan; session metric from twin pelvis |
| SP-13 Pelvic rotation asymmetry | PARAMETER (weak coverage) | EOS 3D reconstruction parameters; no dedicated model found beyond measurement | Least-modelled of the alignment set — flagged as a genuine small gap | Measure and store; no model claims |
| SP-14 Spondylolisthesis | RESEARCH ONLY → ADAPT geometry | Extensive patient-specific FE (L5–S1, personalised geometry from radiographs/CT): slip-% parameterised, growth-plate/disc stresses; progression correlates with PI, sacral slope, slip % | Multiple validated segment models (pars stress concentration matches clinical observation) | Geometry/slip grade from imaging; FE offline Tier-A only. Never infer slip from surface |
| SP-15 Spondylolysis | RESEARCH ONLY | FE pars-defect motion-segment models (same literature family as SP-14), validated against cadaver segment data | Segment stiffness falls with defect/slip; lateral bending + torsion most affected | As SP-14 |
| SP-16 Spinal stenosis | VISUALISE ONLY | Patient FE lumbar models with stenosis geometry — built to test *decompression surgery* (resection ↑ ROM/instability), reviewed quantitatively 2025 | Models answer surgical questions, not posture questions; canal geometry is invisible to movement | Segment and show canal geometry from imaging if present; no movement claims |
| SP-17 Ankylosing spondylitis | ADAPT | FE ankylosed-spine models: ossified discs/ligaments, fused facet joints, whole-spine patient-CT FE for AS kyphosis | AS thoracolumbar FE ROM collapses to ~2° flexion over T9–L5 under test loads — fusion is the model's essence | Bruno with affected intervertebral joints locked + kyphotic rest pose from imaging |
| SP-18 Disc degeneration / herniation | RESEARCH ONLY (strong) | Poroelastic FE discs (grade-parameterised: height, water content, permeability, depressurisation) + coupled musculoskeletal-FE spine | Coupled MS-FE validated: intradiscal-pressure RMSE 0.12 MPa, R² 0.72; muscle activity trends matched in 19 subjects | Coarse twin: per-level disc height (imaging) + joint stiffness scaling. FE offline. Diurnal disc-height change (~1.3 mm/day modelled) is a measurement confound worth noting |
| SP-19 Osteoporotic wedge fracture | ADAPT | CT-based FE wedge-fracture models, experimentally validated on cadaver vertebrae (stiffness/strength/fracture pattern); wedge-angle parameterised (10°/20°) whole-spine stress studies | Wedge at T12 raises adjacent-vertebra stress (bimodal peaks) — the "next fracture" mechanism, quantified | Wedge angle per vertebra as geometry parameter from imaging; FE offline for stress claims |

## What this means for the build

1. **Adopt a spinopelvic parameter layer now**: PI (from onboarding
   imaging), PT, SS, LL, TK, SVA, PI−LL mismatch computed and stored for
   every twin/session. This single layer "covers" SP-06…SP-13 more
   honestly than eight fake condition models.
2. **Bruno spine stays the carrier**; conditions enter as: rest-pose
   geometry (imaging), locked joints (SP-17), wedged vertebrae (SP-05/19),
   slip offsets (SP-14), disc stiffness scaling (SP-18).
3. **FE is a Tier-A offline service**, per patient, from their imaging —
   budget it like the fat layer's MRI path, not as a library download.
   SpineView's EOS+SSM approach is the template for making that cheap.
4. **Genuine gaps found in this batch:** SP-13 (transverse-plane pelvic
   rotation — measured, barely modelled) and the *drivers* of SP-03
   (muscle imbalance as cause, deferred to the neuromotor batch).
5. Nothing in this batch may be inferred from surface/camera data:
   wedges, slips, fusions, canal geometry are **imaging findings**.
   Surface twin reports alignment *parameters* only.

## Sources (accessed 2026-10-28)

- Scheuermann coupled OpenSim–FE — Nature Sci Rep 15:27408 (2025)
- Spinopelvic parameters — Duval-Beaupère/Legaye (pelvic incidence);
  Roussouly classification; SRS-Schwab modifiers; PI−LL mismatch &
  disability (PMC12574469, 2025); sagittal balance review (JKOA 2016)
- Spondylolisthesis/spondylolysis FE — El-Rich et al. (2009, personalised
  L5–S1); Sairyo-lineage validated segment models; adolescent progression
  FE (J Child Orthop / Scoliosis 2012)
- Ankylosing spondylitis FE — PMC6125933 (cervicothoracic AS fracture FE);
  PLOS ONE e0250009 (AS thoracolumbar FE, ROM data); AS kyphosis patient
  FE (2017/2023 case series)
- Disc degeneration poroelastic FE — Woo et al. (2007); Galbusera et al.
  (2011); coupled MS-FE spine (intradiscal pressure RMSE 0.12 MPa)
- Wedge-fracture FE — validated cadaver T9–T12 FE (Spine Deformity 2026);
  THUMS-based 10°/20° T12 wedge stress study (2014)
- Congenital scoliosis EOS 3D — PMC3555618 (1.8 mm vs CT)
- Degenerative scoliosis FE — Frontiers Bioeng Biotechnol (2025),
  Cobb/LL < 1° validation
- Neuromuscular pelvic asymmetry 3D CT — Spine Deformity (2025),
  53 scans, 88.6% asymmetric
- Stenosis/decompression FE — quantitative review, Biomech Model
  Mechanobiol (2025)
- SpineView SSM FE cohort (16,807 models) — https://thc.spineview.upf.edu/
- Bruno thoracolumbar OpenSim model — see
  `research-detailed-anatomy-models.md` §2
