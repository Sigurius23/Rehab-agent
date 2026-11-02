# Research note — Tracking breathing: diaphragm → rib cage + abdominal wall

> Filed 2026-10-28. Question asked: *"Anything on tracking breathing,
> because of diaphragm expansion? It changes the rib cage — expanding,
> tightening. The diaphragm is pushing the muscles."*
> **Short answer: yes — this is a mature measurement field (respiratory
> physiology), with a gold-standard optical method we can imitate with our
> own cameras, and validated depth-camera results on hardware very close
> to our RealSense D455.** It also matters beyond breathing: the diaphragm
> is a spinal stabiliser, so breathing quality is posture data.
> Companion note: `research-detailed-anatomy-models.md` §3 (models).

## 1. The mechanics chain we would be tracking

On inhalation, in sequence:

1. **Diaphragm contracts and descends** (dome flattens, moving down
   roughly 1–2 cm in quiet breathing, 5–7 cm in deep breathing).
2. **Rib cage expands:** through the zone of apposition the diaphragm
   lifts and flares the lower ribs; intercostals rotate the ribs
   ("pump-handle" at the sternum, "bucket-handle" at the sides). Upper
   and lower rib cage do not expand identically — hence the 3-compartment
   model below.
3. **The diaphragm pushes the abdominal contents down and out:** the
   abdominal wall (rectus, obliques, transversus abdominis) yields
   eccentrically — the belly expands — and the pelvic floor descends.
   Intra-abdominal pressure (IAP) rises.
4. **On exhalation** the diaphragm recoils up; in forced exhalation,
   coughing or bracing, the abdominal muscles actively **tighten** and
   push the diaphragm back up. "Expanding, tightening" is exactly this
   inhale-yield / exhale-tighten cycle of the abdominal wall.

**Why a posture project must care (Hodges & Gandevia line of work):**
the diaphragm is dual-purpose. It contracts *before* rapid limb movements
to raise IAP, and IAP measurably increases lumbar-spine stiffness. When
respiratory demand rises, its postural contribution is reduced — i.e.
**a patient who breathes badly stabilises badly, especially during
exercise.** Breathing pattern is therefore a first-class input to posture
correction, not a side metric. Dysfunctional patterns to detect:
thoracic/apical-dominant breathing, paradoxical abdominal motion
(belly draws *in* on inhalation), and thoracoabdominal asynchrony.

## 2. What to measure (metrics for the session schema)

- Respiratory rate, inspiratory/expiratory timing, breath-to-breath
  variability.
- **Compartment contributions** to tidal volume: pulmonary rib cage,
  abdominal rib cage, abdomen (% each) — the objective version of
  "chest breather vs belly breather".
- **Phase angle / thoracoabdominal asynchrony** between rib cage and
  abdomen (0° = synchronous, 180° = fully paradoxical), from Konno-Mead
  (Lissajous) loops or cross-correlation.
- End-expiratory level drift (breath-stacking / hyperinflation proxy).
- Diaphragm-specific (spot-check only): excursion and thickening
  fraction by ultrasound (§3).
- Synchronisation with movement: breath phase vs exercise phase
  (e.g. exhale-on-effort cueing), breath-holds during reps.

## 3. Tracking methods, ranked for our purposes

| Method | What it actually measures | Accuracy / validation | Fit for Rehab Agent |
|---|---|---|---|
| **Spirometry / pneumotach** | True airflow and volume at the mouth | The reference standard | Calibration ground truth at onboarding only — a mouthpiece changes natural breathing and can't be worn through exercise |
| **Respiratory inductance plethysmography (RIP), dual belts** | Rib-cage + abdomen circumference (Konno-Mead 2-compartment model) | Calibrated tidal volume within ~10% while posture is fixed; phase angle works even uncalibrated | **Best worn reference**: cheap, continuous during exercise, gives the RC/AB phase angle directly. Use as the breathing channel + camera calibration source |
| **Optoelectronic plethysmography (OEP)** | 3D chest-wall surface from ~89 reflective markers; volumes of pulmonary rib cage, abdominal rib cage, abdomen; left/right hemithorax | Validated against spirometry; breath-by-breath; distinguishes breathing-pattern disorders from healthy patterns by compartment contribution + phase angles | **The gold standard to imitate.** Marker-based mocap method (commercial: BTS Bioengineering). Our clinic cameras + pose pipeline can approximate it markerlessly (§4) |
| **Depth camera (Kinect/ToF/RealSense) — OUR HARDWARE** | Thoracoabdominal surface depth/volume change | Kinect vs spirometer tidal volume r ≈ 0.97–0.99; chest-volume FVC/vital-capacity estimates within ~±1% after per-subject scaling, forced-flow metrics poor. RealSense D415 RGB-D rehab system: thorax signal vs spirometric volume r = 0.90 ± 0.05, abdomen r = 0.73 ± 0.22, with real-time visual feedback increasing expansion | **Directly applicable** (D455 ≥ D415 depth). Per-subject calibration scaling is required — depth gives *shape change*, absolute litres need a spirometer/belt calibration factor |
| **RGB video (markerless chest ROI, motion magnification)** | Surface chest motion from ordinary video | Works for respiratory rate; volume/compartment claims weak, lighting/clothing sensitive | Fallback channel only, on the existing RGB cameras |
| **Diaphragm ultrasound** | The diaphragm itself: dome excursion (quiet ≈1–2 cm, deep ≈5–7 cm) and thickening fraction at the zone of apposition (quiet ≈50%, deep >100%; <20% = dysfunction flag) | Reproducible, clinically used; correlates with transdiaphragmatic pressure/effort | **Clinician spot-check** at onboarding/milestones — the only direct diaphragm measure. Not continuous, not during exercise, needs a trained operator |
| **4D MRI / dynamic imaging** | True internal diaphragm + lung motion | Research-grade truth | Only if imaging exists clinically; never acquire solely for this |
| **Respiratory-muscle EMG / abdominal-wall ultrasound** | The "tightening" side: abdominal muscle activation, transversus thickening | Research/clinical adjuncts | Optional clinician adjunct; surface EMG of diaphragm itself is unreliable (crosstalk) |

Radar/mmWave and chest-IMU wearables also exist for respiratory *rate*;
they add nothing over the above for compartment mechanics and are not
pursued.

## 4. Proposed implementation on the selected hardware

```
During every session (docs/hardware.md rig):
  front D455 + side cameras ─► torso surface stream (separate from pose)
  SMPL-X registration ─► subtract rigid torso motion (pose compensation —
                        exercise movement dwarfs the mm–cm breathing signal)
  surface displacement integrated over 3 torso compartments
      (pulmonary rib cage / abdominal rib cage / abdomen, defined on the
       twin's own torso mesh — "markerless OEP-lite")
  RIP dual-belt channel (LSL-synced) ─► per-session calibration scaling
      + reference phase angle
Outputs per breath: rate, timing, compartment %, RC–AB phase angle,
  end-expiratory drift, breath-vs-rep phase. Stored in session.json
  (schema extension needed: `breathing` block).
Onboarding/milestones (clinician): spirometer calibration set +
  diaphragm ultrasound spot-check (excursion + thickening fraction).
Twin visualisation: actuate the rib cage of the articulated-spine
  OpenSim model (Bruno ribs) with the measured rib-cage compartments;
  render a diaphragm surface driven by the abdomen compartment signal,
  labelled INFERRED (estimated — never measured); abdominal-wall
  expansion/tension shown on the mesh from the abdomen compartment +
  (optional) EMG.
```

**Confounds to engineer against:** loose clothing (tight top required,
same rule as LiDAR scans), arm occlusion of the lower ribs, torso rotation
during exercise, chair/bench occlusion in seated work, and drift of the
end-expiratory baseline. Breathing amplitudes on the surface are
millimetres-to-centimetres — inside D455 capability at 2–3 m, but only
with pose compensation and per-session calibration.

## 5. Red lines

- Camera/RIP breathing = **ventilation pattern estimate**. Absolute lung
  volumes require the spirometer calibration factor and still are not
  spirometry; never report FEV-style flow metrics from depth data
  (validated poorly).
- The diaphragm itself is **inferred**, never "tracked", in any
  camera-based output. Direct diaphragm claims require ultrasound.
- Asynchrony/paradox flags are **screening signals for clinician
  review** (decision D-03), not diagnoses of breathing-pattern disorder.
- Breathing data is health data: same privacy/jurisdiction handling as
  the rest of the session record (D-07).

## Sources (accessed 2026-10-28)

- Konno & Mead two-compartment chest-wall model; RIP technology and
  phase angle — https://en.wikipedia.org/wiki/Respiratory_inductance_plethysmography
- Optoelectronic plethysmography (3-compartment chest wall, 89-marker
  protocol) — https://en.wikipedia.org/wiki/Optoelectronic_plethysmography;
  local surface-kinematics extension, Frontiers Bioeng Biotechnol (2022);
  breathing-pattern disorders vs healthy via OEP, Smyth et al. (2022)
- Diaphragm dual respiratory/postural function, IAP and spinal stiffness —
  Hodges & Gandevia, J Appl Physiol 89:967 (2000); Hodges et al.,
  J Biomech 38:1873 (2005); Frontiers Physiol (2026) review
- Depth-camera respiratory assessment vs spirometry — Van Hove et al.,
  Clin Respir J (2023, Kinect r = 0.973–0.989); Frontiers Physiol (2017,
  Kinect v2 volume estimation); continuous RR with depth camera,
  J Clin Monit Comput (2019)
- RealSense D415 RGB-D pulmonary-rehabilitation feedback — PubMed
  38261861 (thorax r = 0.90, abdomen r = 0.73 vs spirometry)
- Diaphragm ultrasound (excursion + thickening fraction, reference
  values, <20% dysfunction) — Springer Lung (2023 reference values);
  ASRA POCUS diaphragm assessment (2025); Zambon et al., Intensive Care
  Med (2016) systematic review
- Thoracoabdominal asynchrony measurement (phase-angle techniques) —
  ResearchGate 11044582; abdominal vs thoracic breathing synchrony
  (Lissajous/CEEMD study, 2015)
