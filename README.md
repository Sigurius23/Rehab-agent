# Rehab Agent — Meta-Repository

> A curated meta-repo that organises **115 upstream GitHub repositories** into one
> rehabilitation-technology pipeline: capture → pose → body/skeleton model →
> biomechanics → muscle simulation → feedback & visualisation.
>
> **This repo contains no upstream code.** It contains a machine-readable catalog,
> clone/status tooling, architecture docs, recommended stacks, and the first
> working pipeline slice (`pipeline/`: video → SKEL → OpenSim). Each upstream
> project stays in its own repo, under its own license.

[![Catalog](https://img.shields.io/badge/catalog-115_repos-blue)](#catalog)
![Status](https://img.shields.io/badge/status-research__prototype-orange)

## ⚠️ Not a medical device

Research and engineering use only. Nothing here diagnoses, treats, or replaces a
clinician. Any patient-facing use needs clinical validation, ethics approval, and
privacy review for video / IMU / health data. See
[`docs/safety-and-licensing.md`](docs/safety-and-licensing.md).

## 🎯 Design priority #1: anatomical accuracy

**Full accuracy of the human body in the twin is the key requirement.**
A webcam + SMPL-X gives a statistically average body that moves plausibly —
that is Tier C screening, not a twin. The target is **Tier A**: the patient's
own bones, joint centres/axes and muscle attachments from their MRI/CT,
tracked live against that personalised model, with a measured error budget
attached to every output. Tiers, targets, onboarding pipeline and red lines:
[`docs/accuracy.md`](docs/accuracy.md) · [`stacks/digital-twin.md`](stacks/digital-twin.md).

## 📷 Selected hardware

**RGB camera(s) + iPhone LiDAR (Pro, 12 Pro+) + optional RealSense D455.**
Roles, verified sensor specs, clinic-rig geometry, and the calibration/sync
protocol are fixed in [`docs/hardware.md`](docs/hardware.md). Honest summary:
LiDAR/D455 surfaces are centimetre-class (Tier B) — they register shape and
support live tracking, but bone/joint/muscle accuracy still comes from MRI/CT
(Tier A, `docs/accuracy.md`).

## 🧪 Working slice: video → SKEL → OpenSim

`pipeline/` (Python package `rehabtwin`) takes a front-end's 3D output (HSMR/SKEL, or
non-gated MediaPipe) and produces a scaled OpenSim model, joint angles, trunk/pelvis posture
against gravity, rep metrics, QC, a validation report and an HTML report. Every output is
labelled with its accuracy tier.

```bash
pip install -e "pipeline[test]" && python3 scripts/clone.py --only perfanalytics/pose2sim
cd pipeline && python -m rehabtwin selftest /tmp/rt     # synthetic squat with known truth: ~1° joint-angle RMSE
```

Measured so far ([`docs/validation-results.md`](docs/validation-results.md)): the back-end
recovers known kinematics to about 1° (trunk lean vs gravity 0.35°). On real video,
single-camera MediaPipe fails every gate against a 4-camera reference, so it is not the
answer. The next step is HSMR/SKEL on the public OpenCap LabValidation dataset against
marker mocap. A person model keeps one person's bones and measurements across sessions and setups
([`docs/person-model.md`](docs/person-model.md)). Details: [`pipeline/README.md`](pipeline/README.md) ·
[`stacks/video-skel-opensim.md`](stacks/video-skel-opensim.md).

## 🧈 Fat distribution (separate folder)

Models of the patient's **fat/adipose distribution** — a layer the surface
scan alone cannot see (fat + muscle + bone are summed in SMPL/LiDAR shape).
Kept separate from the main catalog as requested: measured models from
MRI/CT (TotalSegmentator tissue subtasks, vatsatseg, whole-body compartment
quantification → Tier A) vs shape/silhouette-predicted depots (Pseudo-DXA,
UK-Biobank silhouette model → Tier B, **estimate only**), plus paper-only and
closed reference models: [`fat-distribution/README.md`](fat-distribution/README.md).

## Quick start

```bash
git clone <this-repo> rehab-agent && cd rehab-agent

python3 scripts/validate_catalog.py     # check the catalog (115 repos)
python3 scripts/list.py --tier core     # see the recommended first wave
python3 scripts/clone.py --tier core --dry-run
python3 scripts/clone.py --tier core    # shallow-clone core repos into upstream/
python3 scripts/status.py               # what is cloned, at what commit
python3 scripts/list.py --search imu    # e.g. the IMU / wearable path
```

Clones land in `upstream/<owner>/<repo>/` and are **git-ignored** — this meta-repo
stays small and never redistributes upstream code or model weights.

## The pipeline

```mermaid
flowchart LR
  A[Capture\nFreeMoCap · OpenCap · IMU · RGB-D] --> B[Pose / mocap\nPose2Sim · TransPose/PIP · MAMMA]
  B --> C[Body model\nSMPL-X · SMPLify-X · MMHuman3D]
  C --> D[Skeleton\nSKEL · OSSO · HSMR · SKEL-CF]
  D --> E[Biomechanics\nOpenSim · AddBiomechanics · Pose2Sim]
  E --> F[Muscle sim / control\nMyoSuite · MyoSim · SCONE · PHC]
  F --> G[Assessment & feedback\njoint angles · ROM · gait · torques]
  G --> H[Visualisation\naitviewer-skel · OpenCap Viewer · Blender/MuSkeMo]
```

Full data-flow, formats and contracts: [`docs/architecture.md`](docs/architecture.md).

## Catalog

Source of truth: [`catalog/repos.json`](catalog/repos.json) ·
Human views: [`docs/catalog.md`](docs/catalog.md) · [`catalog/repos.csv`](catalog/repos.csv) · [`catalog/repos.yaml`](catalog/repos.yaml)

### By category

| Category | What it covers | Repos |
|---|---|---:|
| `body-models` | Parametric body & skeleton models (SMPL/SMPL-X, SKEL, OSSO, tissues) | 10 |
| `anatomy-models` | Anatomy & personalised model generation | 7 |
| `pose-mocap` | Pose estimation & motion capture (video, markerless, IMU) | 23 |
| `biomechanics` | Biomechanics engines & OpenSim pipeline | 13 |
| `musculoskeletal-sim` | Musculoskeletal simulation, humanoid control & RL | 12 |
| `visualization-tools` | Visualization, viewers & editing tools | 8 |
| `data-capture` | RGB-D / sensor capture | 8 |
| `datasets-interaction` | Datasets & human-object/scene interaction | 2 |
| `rehab-assessment` | Rehab exercise assessment, clinical scores & movement correction | 3 |
| `haptics-exoskeleton` | Haptic feedback suits, exoskeleton hardware & actuators | 6 |
| `medical-imaging` | Medical imaging, segmentation & patient-specific anatomy (DICOM/MRI/CT) | 4 |
| `rehab-assistive` | Rehab, gait & assistive-device specific projects | 5 |
| `3d-reconstruction` | 3D reconstruction, mesh generation & world models | 9 |

### By tier

| Tier | Meaning | Repos |
|---|---|---:|
| `core` | Core — evaluate first for Rehab Agent v1 | 35 |
| `extended` | Extended — useful second wave / alternatives | 33 |
| `specialized` | Specialized — niche modality, task, or platform | 30 |
| `experimental` | Experimental — recent/paper code; validate before depending on it | 11 |
| `needs-review` | Needs review — source list gave no usable description | 0 (all resolved 2026-10-21) |
| `private` | Private — listed but not publicly cloneable | 1 |

### Core stack — evaluate first (35 repos)

| Repository | Category | Why it is core |
|---|---|---|
| [vchoutas/smplx](https://github.com/vchoutas/smplx) | body-models | SMPL-X: expressive parametric human body model (body, hands, face) |
| [MarilynKeller/OSSO](https://github.com/MarilynKeller/OSSO) | body-models | From a body shape, infer the anatomic skeleton |
| [MarilynKeller/SKEL](https://github.com/MarilynKeller/SKEL) | body-models | SKEL — From Skin to Skeleton: biomechanically accurate 3D digital humans (SIGGRAPH Asia 2023) |
| [opencap-org/opencap-core](https://github.com/opencap-org/opencap-core) | pose-mocap | Main OpenCap processing pipeline — markerless motion capture from smartphones |
| [opencap-org/opencap-processing](https://github.com/opencap-org/opencap-processing) | biomechanics | Utilities for processing OpenCap data |
| [MyoHub/myosuite](https://github.com/MyoHub/myosuite) | musculoskeletal-sim | MyoSuite — musculoskeletal environments/tasks in MuJoCo, wrapped in the Gym API |
| [MarilynKeller/SMPL2AddBiomechanics](https://github.com/MarilynKeller/SMPL2AddBiomechanics) | biomechanics | Enable inputting a SMPL sequence into AddBiomechanics to fit an OpenSim skeleton model to the sequence |
| [MarilynKeller/aitviewer-skel](https://github.com/MarilynKeller/aitviewer-skel) | visualization-tools | aitviewer fork supporting visualization of OpenSim models and SKEL |
| [MyoHub/myo_sim](https://github.com/MyoHub/myo_sim) | musculoskeletal-sim | Musculoskeletal models in MuJoCo |
| [MyoHub/myoconverter](https://github.com/MyoHub/myoconverter) | biomechanics | Convert OpenSim 4.0+ MSK models into MuJoCo format with optimized muscle kinematics and kinetics |
| [IsshikiHugh/HSMR](https://github.com/IsshikiHugh/HSMR) | pose-mocap | Reconstructing Humans with a Biomechanically Accurate Skeleton (CVPR 2025 Oral) |
| [opensim-org/opensim-core](https://github.com/opensim-org/opensim-core) | biomechanics | SimTK OpenSim C++ libraries and command-line applications, with Java/Python wrapping |
| [keenon/AddBiomechanics](https://github.com/keenon/AddBiomechanics) | biomechanics | A tool to automatically process and share biomechanics data |
| [perfanalytics/pose2sim](https://github.com/perfanalytics/pose2sim) | pose-mocap | Markerless kinematics with any cameras — from 2D pose estimation to 3D OpenSim motion |
| [vchoutas/smplify-x](https://github.com/vchoutas/smplify-x) | pose-mocap | Expressive Body Capture: 3D Hands, Face, and Body from a Single Image (SMPLify-X) |
| [eth-ait/aitviewer](https://github.com/eth-ait/aitviewer) | visualization-tools | A set of tools to visualize and interact with sequences of 3D data |
| [isl-org/Open3D](https://github.com/isl-org/Open3D) | 3d-reconstruction | Open3D: A Modern Library for 3D Data Processing |
| [Xinyu-Yi/TransPose](https://github.com/Xinyu-Yi/TransPose) | pose-mocap | TransPose — real-time motion capture that estimates poses and global translations using only 6 IMUs |
| [Xinyu-Yi/PIP](https://github.com/Xinyu-Yi/PIP) | pose-mocap | PIP — real-time system that captures physically correct human motion, joint torques, and ground reaction forces with only 6 IMUs |
| [freemocap/freemocap](https://github.com/freemocap/freemocap) | pose-mocap | FreeMoCap — Free Motion Capture for Everyone |
| [muelea/shapy](https://github.com/muelea/shapy) | body-models | Metric body-shape regression from an image (twin onboarding measurements) |
| [google-ai-edge/mediapipe](https://github.com/google-ai-edge/mediapipe) | pose-mocap | Real-time 33-landmark pose on phone/web/laptop |
| [open-mmlab/mmpose](https://github.com/open-mmlab/mmpose) | pose-mocap | RTMPose real-time pose toolbox (swappable 2D-pose layer) |
| [zju3dv/GVHMR](https://github.com/zju3dv/GVHMR) | pose-mocap | World/gravity-grounded SMPL motion from monocular video |
| [SlimeVR/SlimeVR-Server](https://github.com/SlimeVR/SlimeVR-Server) | data-capture | IMU full-body tracking server (wearable twin sensing) |
| [SlimeVR/SlimeVR-Tracker-ESP](https://github.com/SlimeVR/SlimeVR-Tracker-ESP) | data-capture | ESP32 IMU tracker firmware (open-hardware suit sensors) |
| [sccn/labstreaminglayer](https://github.com/sccn/labstreaminglayer) | data-capture | LSL: time-sync for video + IMU + EMG + haptics |
| [fokhruli/STGCN-rehab](https://github.com/fokhruli/STGCN-rehab) | rehab-assessment | Clinician-scored exercise quality (KIMORE / UI-PRMD) |
| [CEINMS/CEINMS](https://github.com/CEINMS/CEINMS) | biomechanics | EMG-informed, per-person calibrated muscle forces |
| [naubiomech/OpenExo](https://github.com/naubiomech/OpenExo) | haptics-exoskeleton | Modular open-source exoskeleton platform (hardware + control) |
| [senseshift/senseshift-firmware](https://github.com/senseshift/senseshift-firmware) | haptics-exoskeleton | DIY haptic vest/sleeve firmware (posture cueing suit) |
| [wasserth/TotalSegmentator](https://github.com/wasserth/TotalSegmentator) | medical-imaging | >100 anatomical structures segmented from the patient's own CT/MRI |
| [Slicer/Slicer](https://github.com/Slicer/Slicer) | medical-imaging | 3D Slicer: clinician DICOM/segmentation review — the accuracy gate |
| [realsenseai/librealsense](https://github.com/realsenseai/librealsense) | data-capture | RealSense SDK for the optional D455 depth camera (selected hardware) |
| [utahmobl/opencap-monocular](https://github.com/utahmobl/opencap-monocular) | pose-mocap | Single-phone video → OpenSim; 4.8° MAE vs marker mocap (preprint) — the monocular bar to beat |

## Recommended stacks

| Stack | Use when | Doc |
|---|---|---|
| Markerless video rehab | Patient exercises filmed on webcams/phones | [`stacks/markerless-video.md`](stacks/markerless-video.md) |
| IMU real-time home rehab | No cameras; 6-IMU wearables, live feedback | [`stacks/imu-realtime.md`](stacks/imu-realtime.md) |
| SMPL → biomechanics | You have SMPL/SMPL-X motion and need joint loads | [`stacks/smpl-to-biomechanics.md`](stacks/smpl-to-biomechanics.md) |
| Muscle simulation & RL | Simulate muscle effort, assistance, exoskeletons | [`stacks/muscle-sim-rl.md`](stacks/muscle-sim-rl.md) |
| Blender anatomy visualisation | Clinician/patient-facing 3D anatomy | [`stacks/blender-anatomy.md`](stacks/blender-anatomy.md) |
| Accuracy-first digital twin | Tier-A: patient MRI/CT → own bones/joints/muscles → live 1:1 tracking → wrong-vs-corrected view | [`stacks/digital-twin.md`](stacks/digital-twin.md) |
| Haptic suit + exoskeleton | Vibrotactile posture cueing now; powered joint support as research track | [`stacks/haptic-exo-suit.md`](stacks/haptic-exo-suit.md) |
| **Video → SKEL → OpenSim (implemented)** | One video (or several) → scaled OpenSim model, joint angles, posture vs gravity, validation | [`stacks/video-skel-opensim.md`](stacks/video-skel-opensim.md) |

## Repo map

```
rehab-agent/
├── README.md                  ← you are here
├── catalog/
│   ├── repos.json             ← SOURCE OF TRUTH (edit this)
│   ├── repos.csv / repos.yaml ← generated
├── docs/
│   ├── catalog.md             ← generated full tables (all 115)
│   ├── architecture.md        ← pipeline, data formats, contracts
│   ├── roadmap.md             ← phased build plan
│   ├── evaluation.md          ← scoring rubric for picking repos
│   ├── validation-results.md  ← what has actually been measured
│   └── safety-and-licensing.md
├── stacks/                    ← 8 opinionated recipes (video-skel-opensim is implemented)
├── pipeline/                  ← rehabtwin: video → SKEL → OpenSim slice (code, configs, tests)
│   ├── rehabtwin/             ← frames, filtering, OpenSim stage, metrics, validation, records, report
│   ├── adapters/              ← HSMR → SKEL sequence, MediaPipe extraction
│   ├── configs/               ← model/marker-set configs, exercise profiles
│   └── tests/                 ← unit + end-to-end (synthetic truth) tests
├── scripts/
│   ├── clone.py  list.py  status.py
│   ├── validate_catalog.py  generate_catalog.py
└── upstream/                  ← your clones go here (git-ignored)
```

## Working rules

1. **Edit `catalog/repos.json`, then regenerate:** `python3 scripts/generate_catalog.py`
2. **Never commit upstream clones, model weights, or patient data** (see `.gitignore`).
3. **Check the upstream license before any use** — especially SMPL/SMPL-X/STAR/SUPR
   model weights, which are typically gated and non-commercial.
4. Pin upstream commits in your own experiment notes (`scripts/status.py` prints HEADs).

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md). Adding a repo = one JSON entry + regenerate + validate.

## License

This meta-repo's own docs and scripts: MIT (see `LICENSE`).
**Upstream repositories and model weights keep their own licenses** — this repo
grants you no rights to them.
