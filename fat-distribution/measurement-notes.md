# Fat measurement notes — reference standard hierarchy

> Filed 2026-10-28 so the team can refer back to these decisions.
> Companion to [`README.md`](README.md) and [`models.json`](models.json).
> Status labels used below: **measured** = the method observes the tissue;
> **estimated** = the method infers it statistically. Only *measured* values
> may support Tier-A claims (see `../docs/accuracy.md`).

## 1. Method hierarchy — total fat vs fat distribution have different gold standards

| Tier | Method | Best for | Reality check |
|---|---|---|---|
| Criterion | **4-compartment (4C) model** | Total fat mass / body-fat % | Combines DXA (bone mineral) + body volume (BodPod / underwater weighing) + total body water (deuterium dilution). The reference standard other methods are validated against. Gives **no spatial distribution**, and is a multi-device research procedure, not a single scan. |
| Gold (distribution) | **Whole-body Dixon MRI** | VAT, SAT, intermuscular fat, regional compartment volumes | Directly images and separates fat depots volumetrically; no ionising radiation; repeatable. This is what the best models in this folder run on (TotalSegmentator tissue types, WholeBodyATQuantification). Downside: cost, access, scan time. |
| Gold (ectopic fat) | **MRI-PDFF / MR spectroscopy (MRS)** | Liver fat, muscle fat infiltration | Reference for fat *inside* organs and muscle — a key health signal no surface method can observe. |
| Excellent, dose-limited | **CT (volumetric, or single L4/L5 slice)** | VAT/SAT cross-sectional area and volume | Historical VAT reference standard; superb fat contrast. Ionising radiation, so it cannot be repeated freely for progress tracking. |
| Best practical | **DXA** | Total + regional fat/lean/bone, android/gynoid split | Fast, relatively cheap, tiny dose, excellent repeatability on the same scanner. Caveat: its "visceral fat" output is an algorithm applied to the android region, **not** a direct tomographic image of VAT — validated against CT/MRI, but one step removed. |
| Field grade | Ultrasound, skinfolds, BodPod (2-compartment), BIA | Local subcutaneous thickness, rough totals | Operator- and hydration-dependent. Acceptable for low-stakes trends only. |
| Estimate only | 3D optical / LiDAR shape models (Pseudo-DXA, silhouette models, etc.) | Screening, engagement, frequent trend interpolation | Statistical inference from the body surface. **Not a measurement** — see §4. |

Ultimate historical reference, for completeness: chemical analysis of cadavers
is the only direct assay of body fat; every in-vivo method above is validated
indirectly against multi-compartment models derived from it.

## 2. Measurements worth storing in the twin (priority order)

1. **VAT volume** (L or cm³) — the metabolically dangerous depot; from MRI/CT.
2. **SAT volume, split abdominal vs gluteofemoral** — the same total fat has
   very different risk and shape meaning depending on the split.
3. **Total fat mass (kg) and body-fat %** — from DXA or the 4C model.
4. **Regional fat mass** (trunk / arms / legs, android / gynoid) — from DXA;
   this is what visibly changes with training.
5. **Intermuscular fat + muscle fat fraction (PDFF)** — directly relevant to
   muscle quality and to any "underdeveloped muscle" claim.
6. **Liver PDFF** — if metabolic health is in scope.

Each stored value must carry provenance: method, device/scanner, date,
protocol version, and whether it is `measured`, `derived` (e.g. DXA-VAT), or
`estimated` (shape model). See also the session/twin schemas in `../schemas/`.

## 3. Rehab Agent recommendation (matches the Tier A/B/C rules)

- **Onboarding + clinical milestones → whole-body Dixon MRI** (Tier A truth;
  feeds the segmentation models already catalogued in this folder).
- **Periodic progress (e.g. quarterly) → DXA**, same scanner, same protocol.
  For tracking *change*, repeatability (precision) matters more than
  absolute accuracy.
- **Frequent check-ins → iPhone LiDAR shape estimate**, labelled `estimated`
  everywhere, used only to interpolate trends between real measurements.
- **Never compare numbers across methods.** A DXA body-fat % and an
  MRI-derived body-fat % are different quantities with different biases.
  Pick one reference method per metric and stick to it longitudinally.

## 4. Is LiDAR/shape-based fat estimation conclusive? — No (settled reasoning)

- **Physics, not search coverage:** a surface scan is one observation with
  several unknowns underneath it. The same waist silhouette can be mostly
  visceral fat, mostly subcutaneous fat, or large muscles plus posture,
  breath and clothing. Shape models resolve that ambiguity *statistically,
  from their training population* — correlation with a depot, not
  observation of it.
- Even with research-grade 3D-optical scanners, visceral-fat prediction is
  only moderate (reported R² ≈ 0.75 vs DXA; VAT/ASAT ratio ≈ 0.5 in the
  large UK-Biobank silhouette study). iPhone LiDAR (~2 cm surface error,
  clothing on top) sits strictly below those scanners in fidelity and
  inherits all of that uncertainty plus its own. (Model details:
  [`README.md`](README.md) §2.)
- Commercial phone apps marketing LiDAR/photo body-fat numbers are
  proprietary and their accuracy claims are not published validation;
  none are catalogued here.
- **What would make a LiDAR pipeline conclusive enough to quote numbers:**
  (a) a paired validation set — same person, same day, LiDAR scan +
  DXA/MRI ground truth; (b) per-depot error reported as Bland–Altman
  limits, not just R²; (c) test–retest repeatability under the fixed scan
  protocol; (d) performance broken down by sex / age / BMI / ancestry
  subgroups. Until that exists for our pipeline, LiDAR fat output stays
  **Tier B: trend-only, always labelled estimated**.

## 5. Provenance of this note

- Method hierarchy and metric list: project reference note, compiled
  2026-10-28 from the fat-distribution research in this folder.
- Shape-model accuracy figures and LiDAR discussion: see
  [`README.md`](README.md) and [`models.json`](models.json) for the
  per-model sources (Pseudo-DXA, UK-Biobank silhouette model, GNN mesh
  model, WholeBodyATQuantification, TotalSegmentator).
