# Research note — Dance movement → 3D mapping, and motion data beyond the squat

> Filed 2026-10-28. Question asked: *"Is there more than OpenCap for mapping
> movement to 3D — and more usable movement data than the squat-heavy rehab
> sets?"* Short answer: **yes, a lot more — but it answers a different need.**
> OpenCap-class tools give *validated biomechanics on a few clinical
> movements*. The dance/motion literature gives *huge, diverse 3D movement
> corpora with no biomechanical ground truth*. This note separates the two
> so we use each for what it is actually good for.
> Nothing here is added to the main catalog yet — this is a research note.

## 1. The landscape in one paragraph

Three data families exist: **(A) true motion-capture dance datasets**
(marker-based, accurate poses, small catalogues of genres), **(B) 3D dance
reconstructed from video at internet scale** (SMPL pseudo-labels, tens of
hours, noisy), and **(C) general human-motion corpora** (AMASS, Motion-X…)
that are not dance-specific but dwarf exercise datasets in movement
diversity. On top of the data sit two method families: **video → 3D
reconstruction** (WHAM / TRAM / GVHMR, already partly catalogued) and
**music/text → 3D dance generation** (Bailando, EDGE, Lodge…), which is
generation, not measurement — relevant to our "corrected movement" drafts,
never to tracking claims.

## 2. Dance datasets with real 3D

### A. Motion-capture ground truth (accurate, small)

| Dataset | Scale | Capture | Representation | Notes |
|---|---|---|---|---|
| **FineDance** (ICCV 2023) | 14.6 h, 22 genres, 27 pro dancers | Optical mocap (Vicon-class) | SMPL-X, 52 joints incl. fingers | Largest *mocap* music–dance set; genre labels by dance artists |
| **SoulDance** (ICCV 2025) | 12.5 h | Professional mocap | SMPL-X body + hands + **face** | First holistic (face-included) music–dance set; quality over scale |
| **Motorica Dance** | 6 h, 8 styles | OptiTrack, 17 cameras, 120 fps | BVH, retargeted skeleton | Includes finger capture in some sessions; audio paired; KTH |
| **ChoreoMaster** (ACM TOG 2021) | 9.91 h total, **1.48 h public** | Mocap, NetEase | FBX motion units + music + labels | Copyright-free subset only; non-commercial research licence |

### B. Reconstructed from video (huge, pseudo-labelled)

| Dataset | Scale | Source | Representation | Notes |
|---|---|---|---|---|
| **AIST++** (ICCV 2021) | 5.2 h, 1,408 seqs, 10 genres, 30 dancers | AIST multi-view dance videos (9 views) | SMPL (24 pose params), COCO 2D/3D joints, camera params, music | The standard benchmark; multi-view reconstruction makes labels better than monocular pseudo-labels, still not mocap |
| **ChoreoSpectrum3D** (EnchantDance, 2023) | **70.32 h**, 4 coarse genres | In-the-wild video reconstruction | SMPL | 14× AIST++ in hours; genre granularity is coarse |
| **OpenDance5D / OpenDanceNet** (2025) | **101.68 h**, 14 genres | Internet video, semi-automatic pipeline | RGB + audio + 2D keypoints + 3D SMPL + fine-grained text | Largest dance corpus found; 10 fps 3D; explicitly multimodal/controllable |
| **ShapeDancer** (ShapeRhythm) | 13,574 s (~3.8 h) | Dance videos via PyMAF-X | SMPL **θ + β (body shape)** + shape text descriptions | Rare: pairs motion with *body-shape variation* — interesting for a shape-aware twin |
| **BRACE** (ECCV-W 2022) | 3.5 h | Red Bull BC One competition video | Densely annotated 2D poses (hybrid manual/auto) | Breakdance stress test: acrobatic, tangled poses where estimators fail; poses, not full SMPL motion |
| **HardMo** (CVPR 2024) | 7M images, 15 dance + 14 martial-arts categories | Internet video, mined "hard cases" | 2D keypoints + SMPL per image | A *pose-estimation benchmark*, not motion sequences; useful to harden a tracker, not to train motion priors |

### C. General motion corpora — the "beyond the squat" data

| Dataset | Scale | Representation | Why it matters here |
|---|---|---|---|
| **AMASS** | >40 h, >300 subjects, >11,000 motions | SMPL(+H) unified from many marker-mocap sets | The canonical motion prior corpus; everyday + expressive movement, mocap-accurate |
| **Motion-X** (NeurIPS 2023) | 81.1K clips, 15.6M poses, ~144 h | SMPL-X whole body (hands/face) + text labels | Built from online video + 8 existing sets; whole-body and text-annotated; quality traded for diversity |
| **HumanML3D** | 14,616 motions, 28.6 h, 44,970 text descriptions | Standardised joint representation (from AMASS/HumanAct12) | The text-to-motion training standard |
| **BABEL** | ~43 h of AMASS, 250+ action categories, frame-level labels | AMASS motions + dense action labels | Lets us *select movement types* (reach, bend, turn…) instead of whole clips |

### D. Exercise/fitness data beyond squats (rehab-adjacent)

| Dataset | Content | Notes |
|---|---|---|
| **Fit3D / AIFit** (CVPR 2021) | **37 repeated exercises**, all major muscle groups, >3M images + mocap ground truth + subject 3D scans | Instructors *and* trainees performing correctly and incorrectly — closest published analogue to our wrong-vs-corrected idea |
| **MM-Fit** | >800 min, ~11 full-body exercises | Synchronised wearables (phone/watch/earbuds) + multi-view RGB-D + 2D/3D pose — matches our multi-sensor session idea |
| **InfiniteForm** (2021) | Synthetic 60K images, 15 fitness pose categories | Synthetic, minimal-bias pose data for hardening estimators |
| UI-PRMD / KIMORE | Rehab exercise quality sets | Already in the main catalog (rehab-assessment) — squat/lunge-heavy, which is the gap this note addresses |

## 3. Mapping methods (video → 3D), dance-relevant

- **AIST++ pipeline itself** is the template for multi-view → SMPL dance
  recovery: recover camera calibration from uncalibrated multi-view video,
  triangulate, fit SMPL. Directly analogous to our clinic multi-camera rig.
- **World-grounded monocular recovery — WHAM, TRAM, GVHMR** (GVHMR already
  catalogued): recover global trajectory, not just in-camera pose. Dance is
  the stress case: spins, floor work, occlusion, moving broadcast cameras.
  A 2025/26 diagnostic study on K-pop broadcast dance found leading methods
  keep plausible per-frame meshes but **world-space trajectories drift badly
  under fast camera motion** (camera/human scale mismatch) — a concrete
  warning for any moving-iPhone-camera design (open decision D-01).
- **DanceHMR** (2026 preprint): hand-aware whole-body (SMPL-X) recovery
  specifically from monocular dance video; beats GVHMR+HaMeR combos on
  temporal/hand metrics in its tests. Recent — treat as promising, verify.
- Generation-side (not measurement): **FACT/AI-Choreographer** (first
  AIST++ model), **Bailando** (VQ-VAE choreographic memory + GPT),
  **EDGE** (editable diffusion), **Lodge** (CVPR 2024, long sequences),
  **EnchantDance**, **GCDance/SoulNet**. Relevance: the same machinery we
  would adapt to *generate clinician-constrained corrected-movement drafts*
  — under the existing red line that generated motion must be constrained
  by SKEL/OpenSim joint limits and never presented as measured.

## 4. What this data can and cannot do for Rehab Agent

**Good uses**
1. **Motion priors / pretraining:** train or fine-tune pose/motion models on
   AMASS + Motion-X + dance corpora so the tracker has seen turns, bends,
   reaches, floor transitions — not just squats — before it ever sees a
   patient.
2. **Stress-testing the tracker:** dance (fast spins, self-occlusion,
   tangled poses — BRACE, HardMo, K-pop-style footage) is the adversarial
   benchmark for the camera/LiDAR pipeline. If it survives breaking, slow
   rehab movement is easy.
3. **Movement vocabulary for visualisation:** diverse, natural movement
   clips for the wrong-vs-corrected and avatar demos, retargeted onto the
   twin.
4. **Shape-aware motion research:** ShapeDancer's β-annotated dance is a
   rare starting point for "how does movement differ by body shape" —
   adjacent to the fat-distribution folder's concerns.

**Hard limits (do not cross)**
- **No kinetics:** none of these sets has ground-reaction forces, joint
  moments, EMG, or clinical labels. SMPL pose ≠ biomechanics. OpenCap's
  value is precisely the validated OpenSim layer dance data lacks.
- **Pseudo-label error:** video-reconstructed sets (B-family, Motion-X)
  carry estimator error in every frame; fine for priors, forbidden as
  accuracy ground truth.
- **Population mismatch:** professional dancers are an extreme,
  hypermobile population. Priors trained mostly on dancers can bias
  amplitude/speed expectations for patients — mix with AMASS/Fit3D and
  clinical data, and keep dancer data out of any normative comparison.
- **Licences:** AIST++, ChoreoMaster, Motion-X and AMASS derivatives are
  research/non-commercial with per-source terms. Audit before any
  product use; SMPL/SMPL-X model licences apply separately as always.

## 5. Recommendation

1. **Keep OpenCap as the biomechanics reference**; it is not replaced by
   any of this — it is complemented by it.
2. **Adopt as data (pending licence audit):** AMASS (+BABEL labels) and
   Motion-X for motion priors; FineDance or Motorica where mocap-accurate
   expressive motion is needed; Fit3D as the exercise-form reference.
3. **Adopt as benchmarks:** AIST++ (multi-view recovery), BRACE/HardMo
   (tracker stress tests).
4. **Watch, don't depend on:** OpenDance5D and DanceHMR (2025–26, verify
   release quality/licence before planning around them).
5. Next step if approved: add the datasets above to the main catalog as a
   `motion-data` group (they are *data*, not tools — the catalog currently
   has only 2 dataset entries), with the limits in §4 recorded per entry.

## Sources (accessed 2026-10-28)

- AIST++ / AI Choreographer — https://arxiv.org/abs/2101.08779 ·
  https://google.github.io/aistplusplus_dataset/
- FineDance — https://arxiv.org/abs/2212.03741
- SoulDance/SoulNet (ICCV 2025) — CVF open access (SoulDance dataset)
- Motorica — https://github.com/simonalexanderson/MotoricaDanceDataset
- ChoreoMaster — https://github.com/NetEase-GameAI/ChoreoMaster
- ChoreoSpectrum3D / EnchantDance — https://arxiv.org/abs/2312.15946
- OpenDance5D — https://arxiv.org/abs/2506.07565
- ShapeDancer/ShapeRhythm — Springer IJCV (ShapeRhythm)
- BRACE — https://arxiv.org/abs/2207.10120
- HardMo — CVPR 2024 (CVF open access)
- AMASS / BABEL / HumanML3D — https://amass.is.tue.mpg.de/ ·
  https://babel.is.tue.mpg.de/
- Motion-X — https://github.com/IDEA-Research/Motion-X
- Fit3D/AIFit — https://arxiv.org/abs/2107.10471 (CVPR 2021)
- MM-Fit — https://mmfit.github.io/
- InfiniteForm — https://arxiv.org/abs/2110.01330
- WHAM/TRAM/GVHMR world-grounded recovery + K-pop camera-dynamics
  diagnostic — arXiv (world-space HMR diagnostic study, 2025/26)
- DanceHMR — arXiv (hand-aware whole-body recovery from dance video, 2026)
- Generation models — Bailando (CVPR 2022), EDGE
  (https://edge-dance.github.io/), Lodge (https://github.com/li-ronghui/LODGE)
