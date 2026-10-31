# Research note — Detailed anatomy: foot arch/flat feet, spine bending, ribcage breathing

> Filed 2026-10-28. Question asked: *"Has anyone modelled arch height /
> flat feet, bending of the spine, and ribcage expansion through breathing
> with the diaphragm?"*
> **Short answer: yes — all four have been modelled, mostly in biomechanics
> and radiotherapy, almost never inside avatar/SMPL-style body models.**
> The twin can adopt the biomechanics models; it cannot get these from
> SMPL/SMPL-X, which treat the foot as one rigid piece, the trunk as three
> lumped spine joints, and do not breathe at all.

## Verdict table

| Detail | Modelled? | Best existing models | Open code? | Twin readiness |
|---|---|---|---|---|
| Foot arch height (dynamic) | Yes | Multi-segment foot models (Oxford/Milwaukee/Ghent); synergy-based foot model (arch as an explicit DOF); 4-segment OpenSim foot with longitudinal arch | Partly (see §1) | Adoptable at the OpenSim stage |
| Flat feet (pes planus) | Yes | Subject-specific muscle-driven FE flatfoot models (CT/MRI-built); orthosis-design variants | Rarely; research-built per subject | Reference/method only |
| Spine bending (per-vertebra) | Yes, extensively | Bruno et al. fully articulated thoracolumbar spine + rib cage (OpenSim); lumbar-spine models; scoliosis personalisation pipelines | Yes (SimTK/OpenSim) | **Adopt — posture correction is our core claim** |
| Ribcage expansion + diaphragm (breathing) | Yes, in radiotherapy | Patient-specific FE diaphragm + rib-kinematics models from 4D CT (≤~2 mm error); PCA respiratory-motion models linking body surface → internal motion | Mostly no; method papers | Port the method, not the code |

## 1. Foot arch height and flat feet

**Kinematic/dynamic arch (how the arch rises and collapses during gait):**
- **Multi-segment foot models** — Oxford Foot Model (4 segments, clinical
  standard, Vicon-integrated), Milwaukee, and Ghent (6 segments, separate
  midfoot/medial-lateral forefoot). They track rearfoot/forefoot/hallux
  motion and derive medial-longitudinal-arch behaviour during stance.
  Known catch, demonstrated in 2024 comparisons: segment definitions change
  the joint moments/powers you compute, and models without a midfoot
  segment (Oxford) can miss dynamic midfoot/arch motion. Model choice is a
  documented decision, not a default.
- **Synergy-based foot model** (2026 preprint, Univ. Bologna group):
  bone-coupling "synergies" extracted by PCA from **weight-bearing CT**,
  reduced to 5 DOF — ankle flexion; foot adduction, pronation, **arching**;
  toe flexion — while still predicting bone-level kinematics.
  Code: `MicheleConconi/Synergy-Based-Foot-Model` (verified on GitHub
  2026-10-28). An OpenSim port is referenced in the preprint
  (`modenaxe/SynergyFootModel-OpenSim`) but did **not** resolve on GitHub
  at check time — verify before planning on it.
- **OpenSim ankle-foot models:** a four-segment foot with a longitudinal
  arch, plantar fascia and intrinsic foot muscle, built for predictive
  gait simulations (KU Leuven; code in `Lars-DHondt-KUL/3dpredictsim`,
  `four-segment_foot_model` branch, MIT — verified 2026-10-28); and an
  open-source 24-DOF ankle-foot model with 66 ligaments/fasciae elements
  for connective-tissue strain (SimTK).
- **Arch measurement (clinical metrics, for our session schema):** Arch
  Height Index, navicular drop/height, arch index (footprint), Foot
  Posture Index. These are the quantities to *store*, whichever model
  computes them.

**Flat feet specifically:**
- The serious models are **subject-specific finite-element feet** built
  from one person's CT/MRI: bones, bulk soft tissue, and a 3D plantar
  fascia, driven by muscle forces from a multibody model. Used to test
  orthosis design — e.g. how arch-support height changes plantar-fascia
  strain and plantar pressure in flexible flatfoot during walking (higher
  support generally unloads the fascia proximally but can raise midfoot
  pressure — a real, quantified trade-off). These are per-subject research
  builds (Abaqus-class), not downloadable products.
- External-shape foot data/models exist for the *surface* side (e.g.
  `OllieBoyne/Foot3D` scan dataset behind the FIND articulated-foot model)
  — useful for fitting the twin's foot surface, silent about fascia strain.

**For the twin:** an iPhone LiDAR foot scan can give a *static external*
arch index only (and only barefoot, weight-bearing state noted). Bone-level
arch behaviour needs the kinematic models above driven by gait data; FE
flatfoot analysis is a Tier-A, per-subject, imaging-based offline study —
exactly analogous to the fat layer's Tier A/B split.

## 2. Bending of the spine

This is the best-covered of the four — and the most important, because
posture correction is our core claim while SMPL gives the spine three
lumped joints (spine/spine1/spine2) and SKEL deliberately smooths it into
a constant-curvature chain. Neither supports claims about *where* the
spine bends.

- **Bruno et al. fully articulated thoracolumbar spine and rib cage**
  (OpenSim, J Biomech Eng 2015; male/female full-body versions on SimTK):
  individual vertebrae T1–L5, each intervertebral joint 3 rotational DOF,
  ribs on costovertebral pin joints, sternum, and trunk musculature whose
  cross-sections/positions were adjusted from community-cohort CT. This is
  the reference model for per-vertebra flexion/lateral-bending/rotation
  and spinal loading.
- **Lumbar-focused models:** Christophy-style lumbar spine (5 vertebrae,
  238 muscle fascicles, motion distributed across levels); Beaucage-Gauvreau
  full-body model with detailed lumbar spine, *validated* for spinal loads
  in symmetric/asymmetric lifting.
- **Personalisation / pathology:** a 2025 PLOS ONE pipeline morphs the
  Bruno generic model into **subject-specific severe-scoliosis models**
  (per-vertebra scaling + re-posed intervertebral joints from CT landmarks,
  muscle wrapping preserved); parametric CAD spine models vary stature and
  Cobb angle for scoliosis simulation; low-dose EOS + 3D Slicer workflows
  reconstruct patient scoliotic spines clinically.
- Narrative reviews catalogue ~17 specific spine + 6 full-body OpenSim
  spine models, so model selection should follow the Bruno/lumbar line
  above rather than starting fresh.

**For the twin:** replace the lumped trunk at the biomechanics stage with
an articulated-spine OpenSim model (Bruno full-body), export per-vertebra
angles as first-class session outputs, and treat any SMPL/SKEL spine curve
as visualisation only. Scoliosis-class curvature = Tier A (imaging-based
personalisation), same rule as bones elsewhere.

## 3. Ribcage expansion and breathing (diaphragm)

Modelled seriously — but by the **radiotherapy** community (they must
predict lung-tumour motion during breathing), not by avatar research.

- **Patient-specific FE respiratory models:** finite-element diaphragm
  (muscle-contraction driven) + rib kinematics extracted from the patient's
  own **4D CT**, lungs expanded by pleural pressure coupling. Reported
  accuracy: average diaphragm/lung surface error ≈ **< 2.2 mm**
  (diaphragm-contact region) and < 2 mm across lung lobes over a full
  breathing cycle. The consistent finding the twin should inherit:
  breathing is driven by **two semi-independent actuators — diaphragm
  descent and rib-cage expansion** ("pump-handle/bucket-handle" rib
  motion) — and their patient-specific split must be calibrated, not
  assumed. (Physiology teaching models put the diaphragm's share of tidal
  volume at roughly 60–75%.)
- **PCA respiratory-motion models (McClelland 2006; Fayad 2012):**
  learn, from 4D CT, a low-dimensional model linking an **external
  surrogate** (a breathing-belt signal, or the patient's own 3D body
  *surface*) to the full internal deformation field; surface-driven
  versions reach ~1.35 mm model error. This is the exact pattern a twin
  needs: measured surface/belt signal in → plausible internal motion out,
  with published error bars.
- **Ribcage kinematics inside musculoskeletal models:** the Bruno model
  (§2) already lets ribs rotate on costovertebral joints relative to their
  thoracic vertebrae — i.e. ribcage *expansion is representable* in our
  OpenSim stage, but nothing in standard avatar pipelines *actuates* it
  with breathing. SMPL-family models have no respiratory DOF; animation
  "breathing" is hand-faked chest scaling.

**For the twin:** add breathing as a separate physiological layer, not a
pose detail — (a) *measure* it (respiratory belt / chest-surface motion
from the clinic cameras / spirometer at onboarding), (b) drive ribcage +
diaphragm motion on the personalised model with a PCA-style
surface→internal mapping calibrated per patient (4D imaging only if
clinically available — do not CT people just for this), (c) label
diaphragm motion as *inferred* everywhere: it cannot be observed from the
surface, only estimated, same honesty rule as the fat layer.

**Tracking methods in depth** (measurement ranking, our-hardware
implementation, session metrics, red lines):
[`research-breathing-tracking.md`](research-breathing-tracking.md).

## 4. Recommended adoptions (pending your approval, as with the dance note)

1. **Spine:** Bruno thoracolumbar full-body OpenSim model as the posture
   stage default; per-vertebra angles in the session schema.
2. **Foot:** synergy-based or 4-segment arch OpenSim foot for gait work;
   store Arch Height Index / navicular drop per session; FE flatfoot only
   as an imaging-based Tier-A study path.
3. **Breathing:** new twin layer per §3 — measured breathing signal in,
   calibrated rib/diaphragm motion out, labelled inferred.
4. Add the OpenSim spine/foot models to the main catalog (they are *models
   for our existing OpenSim stage*, not new repos to clone blindly) and
   record the SMPL/SKEL limitations in `docs/accuracy.md`.

## Sources (accessed 2026-10-28)

- Multi-segment foot model comparisons (Oxford/Milwaukee/Ghent) —
  PMC11118526, PMC11470432; Oxford Foot Model —
  https://www.ouh.nhs.uk/gait-lab/research/oxford-foot-model/
- Synergy-based foot model — bioRxiv 2026.05.17.725725;
  https://github.com/MicheleConconi/Synergy-Based-Foot-Model
- Four-segment arch foot (predictive sims) — PLOS Comput Biol 1012219;
  https://github.com/Lars-DHondt-KUL/3dpredictsim
- Open-source 24-DOF OpenSim ankle-foot model — Sikidar &
  Kalyanasundaram, Comput Methods Programs Biomed (SimTK)
- Muscle-driven FE flatfoot / arch-support height — Peng et al., Comput
  Biol Med 132:104355 (2021); Frontiers Bioeng Biotechnol 10:853085 (2022)
- FIND articulated foot / scan data — https://github.com/OllieBoyne/Foot3D
- Bruno thoracolumbar spine + rib cage (OpenSim) — PMC5101035;
  downloads: https://simtk.org/frs/?group_id=959
- Spine OpenSim model review — J Musculoskelet Trauma (narrative review);
  Beaucage-Gauvreau lifting validation (2019)
- Subject-specific scoliotic models — PLOS ONE 10.1371/journal.pone.0336211
  (2025); SKEL constant-curvature spine — SKEL paper (SIGGRAPH Asia 2023)
- FE diaphragm + rib kinematics from 4D CT — patient-specific respiratory
  biomechanics series (diaphragm surface error 2.2 ± 2.1 mm; whole-cycle
  dynamic model < 2.0 mm lobar error)
- PCA respiratory motion models — McClelland et al., Med Phys 33:3348
  (2006); Fayad et al., Med Phys (2012), surface-based model error
  1.35 ± 0.21 mm
