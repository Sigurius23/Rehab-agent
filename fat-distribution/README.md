# Fat-distribution models

> Separate research folder for **models of human fat (adipose) distribution**,
> as requested. Machine-readable list: [`models.json`](models.json) ·
> Clone list: [`repos.txt`](repos.txt)
>
> These are **not** in the main 108-repo catalog (`catalog/repos.json`) — this
> folder is a self-contained shortlist (12 models: 8 code repos, 2 paper-only
> models, 2 closed reference models). Metadata was fetched live from GitHub
> on 2026-10-21.
>
> **Reference standards:** which fat measurements are actually best, which
> metrics to store in the twin, and why LiDAR/shape estimates are not
> conclusive — see [`measurement-notes.md`](measurement-notes.md).

## Why the twin needs a fat layer at all

Every surface the twin can see — SMPL-X shape, iPhone LiDAR scan, D455 depth —
is **fat + muscle + bone summed together**. That creates three concrete problems:

1. **Honesty:** a large limb can be fat, muscle, or both. Without a fat layer,
   the twin cannot say anything truthful about muscle development (this is a
   red line in `../docs/accuracy.md`).
2. **Correct targets:** a posture/exercise correction that is realistic for one
   body composition is unrealistic for another; the fat layer changes segment
   masses and inertials in the OpenSim model.
3. **Progress:** fat distribution *changes* with training and diet. A twin that
   cannot re-measure it goes stale exactly where the user cares.

## The landscape — two fundamentally different kinds of model

### 1. Measured: segmentation of the person's own imaging (→ Tier A)

These produce **measurements**, and are the only fat data allowed to drive
clinical-style claims in this project.

| Model | Input | Fat outputs | Notes |
|---|---|---|---|
| [TotalSegmentator](https://github.com/wasserth/TotalSegmentator) tissue-types subtasks | CT / MRI | subcutaneous fat, torso fat, intermuscular fat | Already main-catalog #99. Start here |
| [NIH_CADLab_Body_Composition](https://github.com/rsummers11/NIH_CADLab_Body_Composition) | Whole-torso CT | torso adipose + muscle (MIST + 3D nnU-Net) | NIH research release; weights downloadable |
| [vatsatseg](https://github.com/maxdiefenbach/vatsatseg) | Water–fat (Dixon) MRI | **VAT vs SAT** | The metabolically critical split; classical, auditable |
| [AT_Seg_3DCNN](https://github.com/HoldenWuLab/AT_Seg_3DCNN) | Multi-contrast abdominal MRI | SAT/VAT volumes, longitudinal | Academic license (UCLA) — check terms |
| [WholeBodyATQuantification](https://github.com/tobihaui/WholeBodyATQuantification) | Whole-body Dixon MRI | **19 compartments** incl. thoracic/abdominal/gluteofemoral + ectopic fat | Richest taxonomy; model weights on request (2026 preprint) |
| [Adipose_Tissue_Segmentation](https://github.com/bogdanneamtu76/Adipose_Tissue_Segmentation) | Abdominal MRI | TAT / VAT / SAT | Classical-method baseline (Otsu, k-means, fuzzy c-means) |

### 2. Estimated: predicted from surface shape / silhouettes (→ Tier B, estimate only)

These infer *probable* interior distribution from exterior shape. Useful for
onboarding and visualisation — **never measurements**.

| Model | Input | Outputs | Evidence / catch |
|---|---|---|---|
| [Pseudo-DXA](https://github.com/LambertLeong/Pseudo-DXA) | 3D surface scan (SMPL-standardised) | Synthetic DXA → regional fat/lean/bone mass | Weights on request; needs Meshcapade fitting |
| Silhouette model in [broadinstitute/ml4h](https://github.com/broadinstitute/ml4h/tree/master/model_zoo/silhouette_mri) | Front+side silhouettes | VAT (R² .88), ASAT (R² .93), GFAT (R² .93), VAT/ASAT ratio (R² .50–.55) | 40k UK Biobank vs MRI truth; ratio limit shows where shape stops informing |
| GNN on surface meshes ([paper](https://arxiv.org/abs/2308.02493)) | Body surface mesh | VAT (R² .893), ASAT (R² .935) | No verified public code — reimplementation candidate |
| SMPL-shape → composition ([paper](https://www.researchgate.net/publication/380068058_Prediction_of_Total_and_Regional_Body_Composition_from_3D_Body_Shape)) | SMPL betas + waist/hip/height | Total + regional DXA masses | No verified public code |

### 3. Closed reference models (know they exist; do not build on them)

- **GHBMC** consortium FE human models and Toyota's **THUMS** family model
  flesh/fat, muscle and organs for injury biomechanics under licence. Useful
  as a material-modelling reference for SOFA work; not open source.

### Explicitly excluded
- Single **body-fat-percentage** regressors (dozens of small ML repos): one
  scalar from tabular measures — no spatial distribution, useless to a twin.
- **GWAS/genetics** fat-distribution repos: population science, not a
  per-person body model.

## How this plugs into the twin (accuracy-first)

```
Tier A onboarding (docs/accuracy.md):
  MRI/CT ──► TotalSegmentator tissue_4_types ──► subcutaneous + torso + intermuscular fat volumes
         └─► (abdominal Dixon) vatsatseg / WholeBodyATQuantification ──► VAT/SAT + compartments
         ──► fat layer registered onto the patient's bones/muscles (msk-PIPE/OpenSim model):
             segment masses & inertials updated; muscle volumes corrected for intermuscular fat

Tier B onboarding (camera + iPhone LiDAR, docs/hardware.md):
  surface scan ──► Pseudo-DXA / silhouette model ──► ESTIMATED depot volumes
  (stored flagged `estimated`, with model name + cohort caveat; replaced by
   Tier-A measurement whenever imaging becomes available)

Progress loop:
  repeat scan (Tier B) each block; repeat imaging (Tier A) at clinical milestones;
  fat-layer deltas are reported with their tier and error — never blended silently.
```

## Red lines for this folder
- A predicted depot volume must be labelled **estimated** everywhere it
  appears, including UI. (Silhouette VAT/ASAT ratio at R²≈0.5 is a risk
  indicator, not a body measurement.)
- Models trained on UK Biobank / DXA cohorts carry population bias — validate
  on the deployment population before quoting numbers.
- Several of these are 0–6-star research releases with academic or
  on-request weights. Availability is recorded per model in `models.json`;
  re-check before planning around any of them.
