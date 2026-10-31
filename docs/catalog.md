# Full catalog — all 117 repositories

Generated from `catalog/repos.json` by `scripts/generate_catalog.py`. Do not hand-edit this file; edit the JSON and regenerate.

## Documentation standard

Every repo entry MUST document: slug, url, description (>=40 chars, factual), category, tier, pipeline_stages (>=1), tags (>=2), language (or an explicit no-primary-language note), license + license_source, stars/forks/updated snapshots (private repo exempt), notes (>=30 chars: role in this project + caveats), upstream_path. Enforced by scripts/validate_catalog.py and tests/test_catalog.py.

Stars/forks/updated are dated snapshots, **not live data** (see the `snapshot_note` in `catalog/repos.json`). Licenses were verified against the GitHub API or the repo-root license file on the date in each entry's `license_source`; a repo with **no license file is all-rights-reserved by default** and must not be copied/redistributed until cleared. Model weights and datasets frequently carry separate terms from code — the entry's notes flag known cases.

## body-models — Parametric body & skeleton models (SMPL/SMPL-X, SKEL, OSSO, tissues) (10)

| # | Repository | Tier | Stages | Lang | License | ★ snapshot | Description |
|---:|---|---|---|---|---|---:|---|
| 2 | [vchoutas/smplx](https://github.com/vchoutas/smplx) | core | body-model | Python | NOASSERTION | 2746 | SMPL-X: expressive parametric human body model (body, hands, face) |
| 4 | [MarilynKeller/OSSO](https://github.com/MarilynKeller/OSSO) | core | body-model, skeleton | Python | NOASSERTION | 239 | From a body shape, infer the anatomic skeleton |
| 5 | [MarilynKeller/SKEL](https://github.com/MarilynKeller/SKEL) | core | body-model, skeleton, biomechanics | Python | NOASSERTION | 372 | SKEL — From Skin to Skeleton: biomechanically accurate 3D digital humans (SIGGRAPH Asia 2023) |
| 6 | [ahmedosman/SUPR](https://github.com/ahmedosman/SUPR) | extended | body-model | Python | NOASSERTION | 184 | SUPR: A Sparse Unified Part-Based Human Representation (ECCV 2022) |
| 10 | [open-mmlab/mmhuman3d](https://github.com/open-mmlab/mmhuman3d) | extended | body-model, pose, tooling | Python | Apache-2.0 | 1431 | OpenMMLab 3D Human Parametric Model Toolbox and Benchmark |
| 21 | [MarilynKeller/HIT](https://github.com/MarilynKeller/HIT) | extended | body-model, skeleton | Python | NOASSERTION | 105 | HIT: Estimating Internal Human Implicit Tissues from the Body Surface (2024) |
| 24 | [ahmedosman/STAR](https://github.com/ahmedosman/STAR) | extended | body-model | Python | NOASSERTION | 727 | STAR — A Sparse Trained Articulated Human Body Regressor (ECCV 2020) |
| 60 | [hailsong/RC-SMPL](https://github.com/hailsong/RC-SMPL) | specialized | body-model, visualization | C# | none found in repo root | 10 | RC-SMPL — Real-time Cumulative SMPL-based Avatar Body Generation (IEEE ISMAR 2023); cumulatively updates avatar texture and normal maps from images/video in real time |
| 71 | [muelea/shapy](https://github.com/muelea/shapy) | core | body-model | Python | none found in repo root | 389 | SHAPY — accurate 3D body shape regression using metric and semantic attributes; predicts SMPL-X shape plus height/weight/chest/waist/hip measurements from an image |
| 73 | [yfeng95/PIXIE](https://github.com/yfeng95/PIXIE) | extended | body-model | Python | NOASSERTION | 517 | PIXIE — collaborative regression of expressive bodies: whole-body SMPL-X with detailed face and hand articulation from a single image |

## anatomy-models — Anatomy & personalised model generation (9)

| # | Repository | Tier | Stages | Lang | License | ★ snapshot | Description |
|---:|---|---|---|---|---|---:|---|
| 1 | [Kevin-Mattheus-Moerman/BodyParts3D](https://github.com/Kevin-Mattheus-Moerman/BodyParts3D) | extended | body-model, visualization | HTML | MIT | 180 | Clone of the BodyParts3D / Anatomography 3D model files |
| 3 | [Z-Anatomy/Models-of-human-anatomy](https://github.com/Z-Anatomy/Models-of-human-anatomy) | extended | body-model, visualization | Python | NOASSERTION | 281 | Open-source 3D human male anatomy model for Blender - layered bones, muscles, organs and body systems from the Z-Anatomy project |
| 11 | [makehumancommunity/mpfb2](https://github.com/makehumancommunity/mpfb2) | specialized | body-model, visualization | Python | NOASSERTION | 670 | MPFB2 — free and open source human generator for Blender |
| 39 | [modenaxe/msk-STAPLE](https://github.com/modenaxe/msk-STAPLE) | specialized | skeleton, body-model | MATLAB | NOASSERTION | 65 | STAPLE — Shared Tools for Automatic Personalised Lower Extremity modelling: generating skeletal models from 3D bone geometries |
| 47 | [LNSGroup/MS-Human-700](https://github.com/LNSGroup/MS-Human-700) | specialized | muscle-sim, body-model | — | Apache-2.0 | 244 | MS-Human-700: Whole-body Human MusculoSkeletal Model |
| 103 | [PatrikMrnka/msk-PIPE](https://github.com/PatrikMrnka/msk-PIPE) | extended | skeleton, biomechanics, muscle-sim | Python | none found in repo root | 2 | Automated pipeline generating personalised musculoskeletal models from medical images: CT/MRI -> segmentation -> OpenSim model with muscle attachments and wrapping |
| 104 | [katya-stanzy/thin-plate-spline_personalised_muscoloskeletal_model](https://github.com/katya-stanzy/thin-plate-spline_personalised_muscoloskeletal_model) | extended | skeleton, biomechanics | Jupyter Notebook | none found in repo root | 10 | MRI-based workflow for personalised musculoskeletal models: subject-specific joint centres and muscle paths via thin-plate-spline mapping (3D Slicer + OpenSim) |
| 114 | [MicheleConconi/Synergy-Based-Foot-Model](https://github.com/MicheleConconi/Synergy-Based-Foot-Model) | specialized | skeleton, biomechanics | MATLAB | none found in repo root | 0 | Multi-body foot model tracking the spatial kinematics of all foot bones with only 5 DOF, exploiting experimentally derived bone-motion coupling (synergies) measured from weight-bearing CT |
| 115 | [OllieBoyne/Foot3D](https://github.com/OllieBoyne/Foot3D) | specialized | body-model, dataset | — | MIT | 47 | Foot3D - dataset of scanned 3D feet behind the FIND articulated foot model; external foot-shape/scan data for fitting the digital twin's foot surface |

## pose-mocap — Pose estimation & motion capture (video, markerless, IMU) (23)

| # | Repository | Tier | Stages | Lang | License | ★ snapshot | Description |
|---:|---|---|---|---|---|---:|---|
| 8 | [opencap-org/opencap-core](https://github.com/opencap-org/opencap-core) | core | capture, pose, biomechanics | Python | Apache-2.0 | 381 | Main OpenCap processing pipeline — markerless motion capture from smartphones |
| 13 | [Sigurius23/Dynamic-AI-Driven-Anatomical-Pose-Transfer-DAAPT-](https://github.com/Sigurius23/Dynamic-AI-Driven-Anatomical-Pose-Transfer-DAAPT-) 🔒 | private | pose, body-model | — | not recorded | 1 | Dynamic AI-Driven Anatomical Pose Transfer (DAAPT) |
| 14 | [cuevhv/mamma](https://github.com/cuevhv/mamma) | extended | capture, pose | Python | NOASSERTION | 864 | MAMMA: Markerless Accurate Multi-person Motion Acquisition |
| 19 | [NTUYWANG103/ViDiHand](https://github.com/NTUYWANG103/ViDiHand) | specialized | pose | — | none found in repo root | 194 | Official PyTorch implementation: The Surprising Effectiveness of Video Diffusion Models for Hand Motion Reconstruction |
| 28 | [IsshikiHugh/HSMR](https://github.com/IsshikiHugh/HSMR) | core | pose, skeleton | Python | MIT | 636 | Reconstructing Humans with a Biomechanically Accurate Skeleton (CVPR 2025 Oral) |
| 29 | [Intellindust-AI-Lab/SKEL-CF](https://github.com/Intellindust-AI-Lab/SKEL-CF) | experimental | pose, skeleton, body-model | Jupyter Notebook | none found in repo root | 83 | SKEL-CF: Coarse-to-Fine Biomechanical Skeleton and Surface Mesh Recovery |
| 35 | [perfanalytics/pose2sim](https://github.com/perfanalytics/pose2sim) | core | capture, pose, biomechanics | Python | BSD-3-Clause | 861 | Markerless kinematics with any cameras — from 2D pose estimation to 3D OpenSim motion |
| 36 | [vchoutas/smplify-x](https://github.com/vchoutas/smplify-x) | core | pose, body-model | Python | NOASSERTION | 2185 | Expressive Body Capture: 3D Hands, Face, and Body from a Single Image (SMPLify-X) |
| 59 | [mohamedhassanmus/prox](https://github.com/mohamedhassanmus/prox) | specialized | pose, body-model | Python | NOASSERTION | 232 | PROX: Resolving 3D Human Pose Ambiguities with 3D Scene Constraints |
| 63 | [Xinyu-Yi/TransPose](https://github.com/Xinyu-Yi/TransPose) | core | capture, pose | Python | GPL-3.0 | 456 | TransPose — real-time motion capture that estimates poses and global translations using only 6 IMUs |
| 64 | [Xinyu-Yi/PIP](https://github.com/Xinyu-Yi/PIP) | core | capture, pose, biomechanics | Python | GPL-3.0 | 369 | PIP — real-time system that captures physically correct human motion, joint torques, and ground reaction forces with only 6 IMUs |
| 65 | [Xinyu-Yi/PNP](https://github.com/Xinyu-Yi/PNP) | extended | capture, pose, biomechanics | Python | GPL-3.0 | 137 | PNP — real-time human motion capture based on 6 IMUs, upgrading PIP through non-inertial forces |
| 68 | [freemocap/freemocap](https://github.com/freemocap/freemocap) | core | capture, pose | TypeScript | AGPL-3.0 | 10474 | FreeMoCap — Free Motion Capture for Everyone |
| 74 | [google-ai-edge/mediapipe](https://github.com/google-ai-edge/mediapipe) | core | capture, pose | C++ | Apache-2.0 | 37345 | MediaPipe — cross-platform ML perception pipelines; Pose infers 33 3D body landmarks in real time on phone, desktop and web |
| 75 | [open-mmlab/mmpose](https://github.com/open-mmlab/mmpose) | core | pose | Python | Apache-2.0 | 7967 | MMPose — OpenMMLab pose estimation toolbox and benchmark, including the RTMPose real-time model family |
| 76 | [zju3dv/GVHMR](https://github.com/zju3dv/GVHMR) | core | pose, body-model | Jupyter Notebook | NOASSERTION | 2161 | GVHMR — world-grounded human motion recovery via gravity-view coordinates; SMPL motion in camera and world frames from monocular video |
| 77 | [zju3dv/EasyMocap](https://github.com/zju3dv/EasyMocap) | extended | capture, pose, body-model | Python | MIT-like | 4929 | EasyMocap — multi-view and monocular SMPL/SMPL-X/MANO motion capture toolkit |
| 78 | [facebookresearch/sapiens](https://github.com/facebookresearch/sapiens) | extended | capture, pose | Python | CC | 5432 | Sapiens — high-resolution foundation models for human-centric vision: 2D pose, body-part segmentation, depth and normals |
| 79 | [facebookresearch/sapiens2](https://github.com/facebookresearch/sapiens2) | experimental | capture, pose | Python | NOASSERTION | 998 | Sapiens2 — 1K-resolution human vision transformers pretrained on 1B human images; pose, segmentation, normals, pointmaps, matting |
| 83 | [DeepLabCut/DeepLabCut](https://github.com/DeepLabCut/DeepLabCut) | specialized | pose, tooling | Python | LGPL | 5795 | DeepLabCut — markerless pose estimation of user-defined features with deep learning (animals incl. humans) |
| 84 | [DeepLabCut/DeepLabCut-live](https://github.com/DeepLabCut/DeepLabCut-live) | specialized | capture, pose | Python | AGPL-3.0 | 239 | DeepLabCut-Live — SDK for running DeepLabCut models on a live video stream |
| 116 | [utahmobl/opencap-monocular](https://github.com/utahmobl/opencap-monocular) | experimental | capture, pose, biomechanics | Python | PolyForm-Noncommercial-1.0.0 | 243 | OpenCap Monocular: 3D kinematics and dynamics from a single smartphone video (WHAM 3D pose, then OpenSim inverse kinematics), validated against marker mocap |
| 117 | [davidpagnon/Sports2D](https://github.com/davidpagnon/Sports2D) | extended | pose, biomechanics | Python | BSD-3-Clause | 336 | Sports2D: 2D keypoint trajectories and joint and segment angles from a single video or webcam, by the author of Pose2Sim; can export OpenSim kinematics |

## biomechanics — Biomechanics engines & OpenSim pipeline (13)

| # | Repository | Tier | Stages | Lang | License | ★ snapshot | Description |
|---:|---|---|---|---|---|---:|---|
| 9 | [opencap-org/opencap-processing](https://github.com/opencap-org/opencap-processing) | core | biomechanics, tooling | Python | Apache-2.0 | 160 | Utility library for processing OpenCap recordings - data handling and downstream OpenSim-oriented analysis of smartphone motion-capture sessions |
| 22 | [MarilynKeller/SMPL2AddBiomechanics](https://github.com/MarilynKeller/SMPL2AddBiomechanics) | core | skeleton, biomechanics, tooling | Python | NOASSERTION | 157 | Enable inputting a SMPL sequence into AddBiomechanics to fit an OpenSim skeleton model to the sequence |
| 26 | [MyoHub/myoconverter](https://github.com/MyoHub/myoconverter) | core | biomechanics, muscle-sim, tooling | Python | Apache-2.0 | 130 | Convert OpenSim 4.0+ MSK models into MuJoCo format with optimized muscle kinematics and kinetics |
| 32 | [opensim-org/opensim-core](https://github.com/opensim-org/opensim-core) | core | biomechanics, muscle-sim | C++ | Apache-2.0 | 1139 | SimTK OpenSim C++ libraries and command-line applications, with Java/Python wrapping |
| 33 | [keenon/nimblephysics](https://github.com/keenon/nimblephysics) | extended | biomechanics, muscle-sim | C++ | NOASSERTION | 496 | Nimble: Physics Engine for Biomechanics and Deep Learning |
| 34 | [keenon/AddBiomechanics](https://github.com/keenon/AddBiomechanics) | core | biomechanics, tooling | TypeScript | NOASSERTION | 67 | A tool to automatically process and share biomechanics data |
| 38 | [pyomeca/biobuddy](https://github.com/pyomeca/biobuddy) | specialized | body-model, biomechanics, tooling | Python | MIT | 16 | A generic interface to generate a virtual buddy (biomechanical models) |
| 50 | [stanfordnmbl/GaitDynamics](https://github.com/stanfordnmbl/GaitDynamics) | extended | biomechanics | Python | MIT | 135 | Gait dynamics tools from Stanford NMBL - utilities for gait-dynamics analysis alongside OpenSim workflows |
| 62 | [dfki-av/simspine](https://github.com/dfki-av/simspine) | experimental | skeleton, biomechanics | Python | NOASSERTION | 13 | SIMSPINE: A Biomechanics-Aware Simulation Framework for 3D Spine Motion Annotation and Benchmarking |
| 67 | [jerela/OpenSimLive](https://github.com/jerela/OpenSimLive) | specialized | capture, biomechanics | C++ | Apache-2.0 | 30 | Live inverse kinematics based on IMU orientations using OpenSim 4.1 API |
| 89 | [opensim-org/opensim-moco](https://github.com/opensim-org/opensim-moco) | extended | biomechanics, muscle-sim | C++ | Apache-2.0 | 73 | OpenSim Moco — solve optimal control problems for musculoskeletal models with direct collocation (muscle activity for observed/corrected motion, motion prediction) |
| 90 | [mitkof6/OpenSimRT](https://github.com/mitkof6/OpenSimRT) | extended | capture, biomechanics | C++ | GPL-3.0 | 82 | OpenSimRT — real-time musculoskeletal kinematics and dynamics analysis using marker- and IMU-based solutions |
| 91 | [CEINMS/CEINMS](https://github.com/CEINMS/CEINMS) | core | biomechanics, muscle-sim | C++ | Apache-2.0 | 33 | CEINMS — Calibrated EMG-Informed Neuromusculoskeletal Modelling Toolbox; estimates muscle forces and joint moments calibrated to the individual, OpenSim-compatible |

## musculoskeletal-sim — Musculoskeletal simulation, humanoid control & RL (13)

| # | Repository | Tier | Stages | Lang | License | ★ snapshot | Description |
|---:|---|---|---|---|---|---:|---|
| 20 | [MyoHub/myosuite](https://github.com/MyoHub/myosuite) | core | muscle-sim, control-rl | Python | Apache-2.0 | 1267 | MyoSuite — musculoskeletal environments/tasks in MuJoCo, wrapped in the Gym API |
| 25 | [MyoHub/myo_sim](https://github.com/MyoHub/myo_sim) | core | muscle-sim | Python | Apache-2.0 | 214 | MyoSuite's MuJoCo musculoskeletal model library - muscle-actuated limb and full-body models loaded by the MyoSuite environments |
| 30 | [ZhengyiLuo/SMPLSim](https://github.com/ZhengyiLuo/SMPLSim) | extended | muscle-sim, control-rl | Python | BSD-3-Clause | 354 | Simulating SMPL humanoid, supporting PHC / PHC-MJX / PULSE / SimXR code bases |
| 31 | [ZhengyiLuo/PHC](https://github.com/ZhengyiLuo/PHC) | extended | control-rl, muscle-sim | Python | NOASSERTION | 1307 | Perpetual Humanoid Control for Real-time Simulated Avatars (ICCV 2023) |
| 40 | [tgeijten/scone-core](https://github.com/tgeijten/scone-core) | extended | biomechanics, muscle-sim | C++ | Apache-2.0 | 62 | SCONE core — software for performing predictive simulations of biological motion |
| 42 | [tgeijten/sconegym](https://github.com/tgeijten/sconegym) | extended | control-rl, muscle-sim | Python | Apache-2.0 | 50 | Gym environments for SCONE - reinforcement-learning environments wrapping SCONE predictive musculoskeletal simulations |
| 43 | [tgeijten/depRL](https://github.com/tgeijten/depRL) | specialized | control-rl, muscle-sim | Python | MIT | 3 | DEP-RL: Embodied Exploration for Reinforcement Learning in Overactuated and Musculoskeletal Systems (ICLR 2023) |
| 44 | [amathislab/musclemimic](https://github.com/amathislab/musclemimic) | extended | muscle-sim, control-rl | Python | Apache-2.0 | 359 | Towards Embodied AI with MuscleMimic: Unlocking full-body musculoskeletal motor learning at scale |
| 45 | [amathislab/musclemimic_models](https://github.com/amathislab/musclemimic_models) | extended | muscle-sim, body-model | Python | Apache-2.0 | 63 | Musculoskeletal models released from MuscleMimic research: full-body musculoskeletal model |
| 46 | [robfiras/loco-mujoco](https://github.com/robfiras/loco-mujoco) | extended | control-rl, muscle-sim | Python | MIT | 1471 | Imitation learning benchmark focusing on complex locomotion tasks using MuJoCo |
| 54 | [lsw9021/MASS](https://github.com/lsw9021/MASS) | specialized | muscle-sim, control-rl | Mathematica | Apache-2.0 | 638 | MASS (Muscle-Actuated Skeletal System) — simulation and control of a full-body musculoskeletal system driven by muscle activations, with Python/PyTorch deep-RL interfacing (SIGGRAPH 2019) |
| 92 | [sofa-framework/sofa](https://github.com/sofa-framework/sofa) | specialized | muscle-sim, visualization | C++ | none found in repo root | 1279 | SOFA — real-time multi-physics simulation with emphasis on medical simulation; FEM soft-tissue modelling |
| 113 | [Lars-DHondt-KUL/3dpredictsim](https://github.com/Lars-DHondt-KUL/3dpredictsim) | extended | biomechanics, muscle-sim | C++ | MIT | 4 | Framework generating 3D muscle-driven predictive simulations of human movement via direct collocation and algorithmic differentiation (KU Leuven); hosts the four-segment foot model with longitudinal arch used for predictive gait simulations |

## visualization-tools — Visualization, viewers & editing tools (8)

| # | Repository | Tier | Stages | Lang | License | ★ snapshot | Description |
|---:|---|---|---|---|---|---:|---|
| 7 | [PashavanBijlert/MuSkeMo](https://github.com/PashavanBijlert/MuSkeMo) | specialized | visualization, biomechanics | TeX | none found in repo root | 73 | Build and visualize musculoskeletal models in Blender |
| 12 | [ZhUyU1997/open-pose-editor](https://github.com/ZhUyU1997/open-pose-editor) | specialized | visualization, tooling | TypeScript | MIT | 960 | Online 3D OpenPose editor for Stable Diffusion and ControlNet |
| 23 | [MarilynKeller/aitviewer-skel](https://github.com/MarilynKeller/aitviewer-skel) | core | visualization | Python | MIT | 80 | aitviewer fork supporting visualization of OpenSim models and SKEL |
| 27 | [opencap-org/opencap-viewer](https://github.com/opencap-org/opencap-viewer) | extended | visualization | JavaScript | Apache-2.0 | 11 | OpenCap viewer - browser-based web viewer for inspecting OpenCap motion-capture sessions, trials and results |
| 37 | [eth-ait/aitviewer](https://github.com/eth-ait/aitviewer) | core | visualization | Python | MIT | 756 | A set of tools to visualize and interact with sequences of 3D data |
| 41 | [tgeijten/scone-studio](https://github.com/tgeijten/scone-studio) | extended | visualization, biomechanics | C++ | GPL-3.0 | 46 | SCONE Studio — graphical user interface for SCONE |
| 58 | [strayrobots/3d-annotation-tool](https://github.com/strayrobots/3d-annotation-tool) | specialized | visualization, tooling | C++ | MIT | 94 | A graphical user interface to annotate point clouds and 3D data |
| 85 | [sangho0n/Realtime_SMPLX_Unity](https://github.com/sangho0n/Realtime_SMPLX_Unity) | specialized | visualization, body-model | C# | MIT | 50 | Real-time SMPL-X in Unity — shape reconstruction via a Python server plus MediaPipe pose in Unity, animating SMPL-X live |

## data-capture — RGB-D / sensor capture (8)

| # | Repository | Tier | Stages | Lang | License | ★ snapshot | Description |
|---:|---|---|---|---|---|---:|---|
| 51 | [marek-simonik/record3d](https://github.com/marek-simonik/record3d) | specialized | capture | C | LGPL-2.1 | 493 | Record3D iOS app library — receive RGBD stream from iOS devices with TrueDepth cameras |
| 57 | [strayrobots/scanner](https://github.com/strayrobots/scanner) | specialized | capture | C++ | MIT | 155 | An app for collecting raw RGB-D scans on iOS devices |
| 80 | [SlimeVR/SlimeVR-Server](https://github.com/SlimeVR/SlimeVR-Server) | core | capture, pose | Fluent | MIT | 1047 | SlimeVR Server — server for the SlimeVR open full-body tracking ecosystem; fuses IMU trackers into a full-body pose |
| 81 | [SlimeVR/SlimeVR-Tracker-ESP](https://github.com/SlimeVR/SlimeVR-Tracker-ESP) | core | capture | C++ | MIT | 1088 | SlimeVR Tracker firmware for ESP32/ESP8266 and various IMUs — DIY open-hardware body trackers |
| 82 | [sccn/labstreaminglayer](https://github.com/sccn/labstreaminglayer) | core | capture, tooling | HTML | MIT | 788 | Lab Streaming Layer (LSL) — multimodal time-synchronised data transmission and recording (liblsl, pylsl, LabRecorder/XDF ecosystem) |
| 105 | [realsenseai/librealsense](https://github.com/realsenseai/librealsense) | core | capture, tooling | C++ | Apache-2.0 | 9060 | RealSense SDK 2.0 (librealsense) — official cross-platform driver/library for RealSense depth cameras including the D455; includes pyrealsense2 and ROS wrappers |
| 106 | [ethz-asl/kalibr](https://github.com/ethz-asl/kalibr) | specialized | capture, tooling | C++ | BSD-3-Clause | 5770 | Kalibr — visual-inertial calibration toolbox for cameras and IMUs |
| 107 | [AprilRobotics/apriltag](https://github.com/AprilRobotics/apriltag) | specialized | capture, tooling | C | BSD-2-Clause | 2578 | AprilTag — visual fiducial marker system for robotics (pose of tagged objects from camera images) |

## datasets-interaction — Datasets & human-object/scene interaction (5)

| # | Repository | Tier | Stages | Lang | License | ★ snapshot | Description |
|---:|---|---|---|---|---|---:|---|
| 61 | [xiexh20/behave-dataset](https://github.com/xiexh20/behave-dataset) | specialized | dataset, pose | Python | NOASSERTION | 193 | Code to access the BEHAVE dataset (CVPR 2022) — human-object interaction |
| 66 | [ptrvilya/echo](https://github.com/ptrvilya/echo) | experimental | pose, dataset | Python | MIT | 17 | ECHO: method for reconstructing human-object interaction from sparse ego-centric tracking |
| 109 | [IDEA-Research/Motion-X](https://github.com/IDEA-Research/Motion-X) | specialized | dataset, pose | Python | NOASSERTION - non-commercial scientific research purposes only | 905 | Motion-X (NeurIPS 2023) - large-scale 3D expressive whole-body human motion dataset: 81.1K clips / ~144 h of SMPL-X whole-body poses (body, hands, face) with text annotations, built from online video plus eight existing datasets |
| 111 | [NetEase-GameAI/ChoreoMaster](https://github.com/NetEase-GameAI/ChoreoMaster) | specialized | dataset, pose | — | none found in repo root | 120 | ChoreoMaster (ACM TOG 2021) - choreography-oriented, music-driven dance synthesis dataset and code (FBX motion units + music + labels); only ~1.48 h of the 9.91 h corpus is public |
| 112 | [simonalexanderson/MotoricaDanceDataset](https://github.com/simonalexanderson/MotoricaDanceDataset) | specialized | dataset, pose | Python | NOASSERTION - custom Motorica AB copyright terms | 113 | Motorica Dance Dataset - 6 h of OptiTrack motion capture (17 cameras, 120 fps) across 8 dance styles; BVH plus retargeted skeletons, finger capture in some sessions, paired audio |

## rehab-assistive — Rehab, gait & assistive-device specific projects (5)

| # | Repository | Tier | Stages | Lang | License | ★ snapshot | Description |
|---:|---|---|---|---|---|---:|---|
| 48 | [DaebangStn/exo-plore](https://github.com/DaebangStn/exo-plore) | specialized | control-rl, muscle-sim | C++ | NOASSERTION | 23 | EXO-PLORE: Exploring Exoskeleton Control Space through Human-Aligned Simulation (ICLR 2026) |
| 49 | [stanfordnmbl/sit2stand](https://github.com/stanfordnmbl/sit2stand) | specialized | biomechanics | HTML | none found in repo root | 4 | Stanford NMBL sit-to-stand project (details in upstream repo) |
| 53 | [rohwalia/MyoBack](https://github.com/rohwalia/MyoBack) | specialized | muscle-sim, biomechanics | Python | none found in repo root | 7 | MyoBack — simulation of a neuromusculoskeletal model of the back with an exoskeleton; a MyoSuite back model derived from a physiologically accurate OpenSim model, validated with a passive back exoskeleton |
| 55 | [neumovelab/myoassist](https://github.com/neumovelab/myoassist) | specialized | muscle-sim, control-rl | Jupyter Notebook | Apache-2.0 | 62 | MyoAssist (assistive musculoskeletal simulation; details in upstream repo) |
| 56 | [hzm2016/mass-dart-exo](https://github.com/hzm2016/mass-dart-exo) | specialized | muscle-sim, control-rl | Mathematica | Apache-2.0 | 2 | MASS/DART exoskeleton variant — upstream README presents the MASS muscle-actuated full-body skeletal simulation system; exoskeleton-specific changes are not documented in the README |

## 3d-reconstruction — 3D reconstruction, mesh generation & world models (9)

| # | Repository | Tier | Stages | Lang | License | ★ snapshot | Description |
|---:|---|---|---|---|---|---:|---|
| 15 | [MaureenZOU/worldstring](https://github.com/MaureenZOU/worldstring) | experimental | pose, dataset | Python | none found in repo root | 82 | Official implementation for Actionable World Representation (worldstring) |
| 16 | [haoz19/world-tracing](https://github.com/haoz19/world-tracing) | experimental | pose, visualization | Python | NOASSERTION | 373 | Official inference code for World Tracing |
| 17 | [Andy-Cheng/Flex4DHuman](https://github.com/Andy-Cheng/Flex4DHuman) | experimental | capture, pose | — | none found in repo root | 106 | Flex4DHuman turns monocular or sparse multi-view videos of dynamic subjects into synchronized dense multi-view videos |
| 18 | [facebookresearch/meshflow](https://github.com/facebookresearch/meshflow) | experimental | body-model, visualization | Python | NOASSERTION | 528 | MeshFlow: Efficient Artistic Mesh Generation via MeshVAE and Flow-based Diffusion Transformer (CVPR 2026) |
| 52 | [isl-org/Open3D](https://github.com/isl-org/Open3D) | core | capture, visualization, tooling | C++ | NOASSERTION | 14136 | Open3D: A Modern Library for 3D Data Processing |
| 69 | [xibushu/UniForge3D](https://github.com/xibushu/UniForge3D) | experimental | body-model | Python | MIT | 373 | UniForge3D: Joint 3D Reconstruction and Generation in a Shared Anchor-Guided Space |
| 70 | [Net-Maker/GaussiAnimate](https://github.com/Net-Maker/GaussiAnimate) | experimental | body-model, visualization | Python | MIT | 157 | GaussiAnimate: Reconstruct and Rig Animatable Categories with Level of Dynamics |
| 72 | [YuliangXiu/ECON](https://github.com/YuliangXiu/ECON) | extended | capture, body-model | Python | NOASSERTION | 1213 | ECON — explicit clothed humans optimised via normal integration; high-fidelity 3D clothed human from a single image, SMPL-X animatable |
| 108 | [alicevision/Meshroom](https://github.com/alicevision/Meshroom) | extended | capture, body-model | Python | none found in repo root | 13028 | Meshroom — node-based photogrammetry toolbox (AliceVision) for 3D reconstruction from photos |

## rehab-assessment — Rehab exercise assessment, clinical scores & movement correction (4)

| # | Repository | Tier | Stages | Lang | License | ★ snapshot | Description |
|---:|---|---|---|---|---|---:|---|
| 86 | [avakanski/A-Deep-Learning-Framework-for-Assessing-Physical-Rehabilitation-Exercises](https://github.com/avakanski/A-Deep-Learning-Framework-for-Assessing-Physical-Rehabilitation-Exercises) | extended | dataset, pose | Jupyter Notebook | none found in repo root | 75 | Framework for quality assessment of physical rehabilitation exercises on the UI-PRMD dataset (skeletal joint data, correct vs incorrect movements) |
| 87 | [fokhruli/STGCN-rehab](https://github.com/fokhruli/STGCN-rehab) | core | dataset, pose | Python | MIT | 44 | Graph convolutional networks for assessment of physical rehabilitation exercises (KIMORE and UI-PRMD) |
| 88 | [GuyTevet/motion-diffusion-model](https://github.com/GuyTevet/motion-diffusion-model) | experimental | pose, body-model | Python | MIT | 4120 | MDM — Human Motion Diffusion Model; text/action-to-motion generation plus motion editing and in-betweening |
| 110 | [li-ronghui/LODGE](https://github.com/li-ronghui/LODGE) | experimental | pose, body-model | Python | none found in repo root | 178 | LODGE (CVPR 2024) - coarse-to-fine diffusion network for long music-driven dance generation guided by characteristic dance primitives |

## haptics-exoskeleton — Haptic feedback suits, exoskeleton hardware & actuators (6)

| # | Repository | Tier | Stages | Lang | License | ★ snapshot | Description |
|---:|---|---|---|---|---|---:|---|
| 93 | [naubiomech/OpenExo](https://github.com/naubiomech/OpenExo) | core | control-rl, feedback-haptics, muscle-sim | HTML | LGPL | 384 | OpenExo — open-source modular exoskeleton platform for mobility and rehabilitation research: mechanical designs, electronics, firmware, control and biofeedback schemes |
| 94 | [neurobionics/opensourceleg](https://github.com/neurobionics/opensourceleg) | extended | control-rl | Python | LGPL | 120 | Open-Source Leg — open-source SDK for developing and testing algorithms on robotic prosthesis/exoskeleton leg hardware (actuators and sensors) |
| 95 | [senseshift/senseshift-firmware](https://github.com/senseshift/senseshift-firmware) | core | feedback-haptics | C++ | GPL-3.0 | 149 | SenseShift firmware — open-source firmware for DIY haptic-feedback devices (vest, gloves, sleeves), compatible with bHaptics and OpenGloves protocols |
| 96 | [LucidVR/lucidgloves](https://github.com/LucidVR/lucidgloves) | specialized | feedback-haptics | C++ | MIT | 2396 | LucidGloves — Arduino/ESP32 DIY VR haptic gloves with force feedback, via OpenGloves |
| 97 | [mjbots/moteus](https://github.com/mjbots/moteus) | extended | control-rl, feedback-haptics | C++ | Apache-2.0 | 1345 | moteus — open-source brushless DC servo motor controller (firmware and PCB designs) |
| 98 | [simplefoc/Arduino-FOC](https://github.com/simplefoc/Arduino-FOC) | specialized | control-rl | C++ | MIT | 3074 | Arduino SimpleFOC — field-oriented control library for BLDC and stepper motors across Arduino/STM32/ESP32-class hardware |

## medical-imaging — Medical imaging, segmentation & patient-specific anatomy (DICOM/MRI/CT) (4)

| # | Repository | Tier | Stages | Lang | License | ★ snapshot | Description |
|---:|---|---|---|---|---|---:|---|
| 99 | [wasserth/TotalSegmentator](https://github.com/wasserth/TotalSegmentator) | core | body-model, skeleton | Python | Apache-2.0 | 3074 | Tool for robust segmentation of >100 important anatomical structures in CT and MR images |
| 100 | [MIC-DKFZ/nnUNet](https://github.com/MIC-DKFZ/nnUNet) | extended | body-model, tooling | Python | Apache-2.0 | 8978 | nnU-Net — self-configuring biomedical image segmentation framework (the segmentation engine behind TotalSegmentator) |
| 101 | [Slicer/Slicer](https://github.com/Slicer/Slicer) | core | body-model, visualization, tooling | C++ | GPL | 2674 | 3D Slicer — free open-source platform for medical image visualisation, DICOM handling, segmentation, registration and quantification |
| 102 | [unibas-gravis/scalismo](https://github.com/unibas-gravis/scalismo) | specialized | body-model, skeleton | Scala | Apache-2.0 | 269 | Scalismo — library for statistical shape modelling and model-based image analysis |

## Repository details — every repo, fully documented

### 1. [Kevin-Mattheus-Moerman/BodyParts3D](https://github.com/Kevin-Mattheus-Moerman/BodyParts3D)

- **What it is:** Clone of the BodyParts3D / Anatomography 3D model files
- **Why it's in this catalog:** Reference anatomy geometry; check source-data terms before redistribution.
- **Category / tier:** anatomy-models / extended
- **Pipeline stages:** body-model, visualization
- **Tags:** anatomy, 3d-models, anatomography
- **Primary language (GitHub):** HTML
- **License:** MIT _(source: GitHub API (live 2026-10-28))_
- **Snapshot:** ★ 180 · forks 33 · upstream updated 2026-10-26 (live API 2026-10-28)
- **Clone target when vendored:** `upstream/Kevin-Mattheus-Moerman/BodyParts3D` (never commit upstream code to this repo)

### 2. [vchoutas/smplx](https://github.com/vchoutas/smplx)

- **What it is:** SMPL-X: expressive parametric human body model (body, hands, face)
- **Why it's in this catalog:** Model weights are license-gated via the SMPL-X website; code license != model license.
- **Category / tier:** body-models / core
- **Pipeline stages:** body-model
- **Tags:** smpl-x, parametric, body, hands, face
- **Primary language (GitHub):** Python
- **License:** NOASSERTION (custom/mixed license file in repo - read before use) _(source: repo-root LICENSE file, non-standard text (checked 2026-10-28))_
- **Snapshot:** ★ 2746 · forks 400 · upstream updated 2026-10-28 (live API 2026-10-28)
- **Clone target when vendored:** `upstream/vchoutas/smplx` (never commit upstream code to this repo)

### 3. [Z-Anatomy/Models-of-human-anatomy](https://github.com/Z-Anatomy/Models-of-human-anatomy)

- **What it is:** Open-source 3D human male anatomy model for Blender - layered bones, muscles, organs and body systems from the Z-Anatomy project
- **Why it's in this catalog:** Blender-oriented anatomy reference.
- **Category / tier:** anatomy-models / extended
- **Pipeline stages:** body-model, visualization
- **Tags:** anatomy, blender, male-model
- **Primary language (GitHub):** Python
- **License:** NOASSERTION (custom/mixed license file in repo - read before use) _(source: GitHub API (live 2026-10-28); license file present but non-standard)_
- **Snapshot:** ★ 281 · forks 59 · upstream updated 2026-10-28 (live API 2026-10-28)
- **Clone target when vendored:** `upstream/Z-Anatomy/Models-of-human-anatomy` (never commit upstream code to this repo)

### 4. [MarilynKeller/OSSO](https://github.com/MarilynKeller/OSSO)

- **What it is:** From a body shape, infer the anatomic skeleton
- **Why it's in this catalog:** Key bridge: surface body -> skeleton for rehab biomechanics.
- **Category / tier:** body-models / core
- **Pipeline stages:** body-model, skeleton
- **Tags:** skeleton-inference, smpl, osso
- **Primary language (GitHub):** Python
- **License:** NOASSERTION (custom/mixed license file in repo - read before use) _(source: repo-root LICENSE.txt file, non-standard text (checked 2026-10-28))_
- **Snapshot:** ★ 239 · forks 33 · upstream updated 2026-10-25 (live API 2026-10-28)
- **Clone target when vendored:** `upstream/MarilynKeller/OSSO` (never commit upstream code to this repo)

### 5. [MarilynKeller/SKEL](https://github.com/MarilynKeller/SKEL)

- **What it is:** SKEL — From Skin to Skeleton: biomechanically accurate 3D digital humans (SIGGRAPH Asia 2023)
- **Why it's in this catalog:** Core skeleton model for the SMPL->OpenSim path. rehabtwin reads SKEL's 24 anatomical joints + 105 BSM skin markers; SKEL q = 0 is used as the neutral static trial for OpenSim scaling.
- **Category / tier:** body-models / core
- **Pipeline stages:** body-model, skeleton, biomechanics
- **Tags:** skel, skeleton, smpl, biomechanics
- **Primary language (GitHub):** Python
- **License:** NOASSERTION (custom/mixed license file in repo - read before use) _(source: repo-root LICENSE.txt file, non-standard text (checked 2026-10-28))_
- **Snapshot:** ★ 372 · forks 49 · upstream updated 2026-10-26 (live API 2026-10-28)
- **Clone target when vendored:** `upstream/MarilynKeller/SKEL` (never commit upstream code to this repo)

### 6. [ahmedosman/SUPR](https://github.com/ahmedosman/SUPR)

- **What it is:** SUPR: A Sparse Unified Part-Based Human Representation (ECCV 2022)
- **Why it's in this catalog:** Alternative parametric body representation.
- **Category / tier:** body-models / extended
- **Pipeline stages:** body-model
- **Tags:** supr, parametric, part-based
- **Primary language (GitHub):** Python
- **License:** NOASSERTION (custom/mixed license file in repo - read before use) _(source: repo-root LICENSE file, non-standard text (checked 2026-10-28))_
- **Snapshot:** ★ 184 · forks 11 · upstream updated 2026-08-29 (live API 2026-10-28)
- **Clone target when vendored:** `upstream/ahmedosman/SUPR` (never commit upstream code to this repo)

### 7. [PashavanBijlert/MuSkeMo](https://github.com/PashavanBijlert/MuSkeMo)

- **What it is:** Build and visualize musculoskeletal models in Blender
- **Why it's in this catalog:** Blender MSK authoring/visualization.
- **Category / tier:** visualization-tools / specialized
- **Pipeline stages:** visualization, biomechanics
- **Tags:** blender, musculoskeletal, visualization
- **Primary language (GitHub):** TeX
- **License:** none found in repo root (checked 2026-10-28; treat as all-rights-reserved) _(source: checked repo root 2026-10-28)_
- **Snapshot:** ★ 73 · forks 4 · upstream updated 2026-10-27 (live API 2026-10-28)
- **Clone target when vendored:** `upstream/PashavanBijlert/MuSkeMo` (never commit upstream code to this repo)

### 8. [opencap-org/opencap-core](https://github.com/opencap-org/opencap-core)

- **What it is:** Main OpenCap processing pipeline — markerless motion capture from smartphones
- **Why it's in this catalog:** Clinically oriented markerless mocap; check cloud/API dependencies.
- **Category / tier:** pose-mocap / core
- **Pipeline stages:** capture, pose, biomechanics
- **Tags:** opencap, markerless, smartphone, gait
- **Primary language (GitHub):** Python
- **License:** Apache-2.0 _(source: GitHub API (live 2026-10-28))_
- **Snapshot:** ★ 381 · forks 257 · upstream updated 2026-10-28 (live API 2026-10-28)
- **Clone target when vendored:** `upstream/opencap-org/opencap-core` (never commit upstream code to this repo)

### 9. [opencap-org/opencap-processing](https://github.com/opencap-org/opencap-processing)

- **What it is:** Utility library for processing OpenCap recordings - data handling and downstream OpenSim-oriented analysis of smartphone motion-capture sessions
- **Why it's in this catalog:** Companion to opencap-core for downstream OpenSim analysis.
- **Category / tier:** biomechanics / core
- **Pipeline stages:** biomechanics, tooling
- **Tags:** opencap, opensim, utilities
- **Primary language (GitHub):** Python
- **License:** Apache-2.0 _(source: GitHub API (live 2026-10-28))_
- **Snapshot:** ★ 160 · forks 104 · upstream updated 2026-10-28 (live API 2026-10-28)
- **Clone target when vendored:** `upstream/opencap-org/opencap-processing` (never commit upstream code to this repo)

### 10. [open-mmlab/mmhuman3d](https://github.com/open-mmlab/mmhuman3d)

- **What it is:** OpenMMLab 3D Human Parametric Model Toolbox and Benchmark
- **Why it's in this catalog:** Broad toolbox; heavier dependency stack.
- **Category / tier:** body-models / extended
- **Pipeline stages:** body-model, pose, tooling
- **Tags:** mmhuman3d, smpl, toolbox, benchmark
- **Primary language (GitHub):** Python
- **License:** Apache-2.0 _(source: GitHub API (live 2026-10-28))_
- **Snapshot:** ★ 1431 · forks 155 · upstream updated 2026-10-25 (live API 2026-10-28)
- **Clone target when vendored:** `upstream/open-mmlab/mmhuman3d` (never commit upstream code to this repo)

### 11. [makehumancommunity/mpfb2](https://github.com/makehumancommunity/mpfb2)

- **What it is:** MPFB2 — free and open source human generator for Blender
- **Why it's in this catalog:** Patient/avatar generation in Blender.
- **Category / tier:** anatomy-models / specialized
- **Pipeline stages:** body-model, visualization
- **Tags:** makehuman, blender, human-generator
- **Primary language (GitHub):** Python
- **License:** NOASSERTION (custom/mixed license file in repo - read before use) _(source: GitHub API (live 2026-10-28); license file present but non-standard)_
- **Snapshot:** ★ 670 · forks 96 · upstream updated 2026-10-28 (live API 2026-10-28)
- **Clone target when vendored:** `upstream/makehumancommunity/mpfb2` (never commit upstream code to this repo)

### 12. [ZhUyU1997/open-pose-editor](https://github.com/ZhUyU1997/open-pose-editor)

- **What it is:** Online 3D OpenPose editor for Stable Diffusion and ControlNet
- **Why it's in this catalog:** Peripheral to rehab; useful for pose authoring/annotation UX ideas.
- **Category / tier:** visualization-tools / specialized
- **Pipeline stages:** visualization, tooling
- **Tags:** openpose, editor, controlnet
- **Primary language (GitHub):** TypeScript
- **License:** MIT _(source: GitHub API (live 2026-10-28))_
- **Snapshot:** ★ 960 · forks 224 · upstream updated 2026-10-28 (live API 2026-10-28)
- **Clone target when vendored:** `upstream/ZhUyU1997/open-pose-editor` (never commit upstream code to this repo)

### 13. [Sigurius23/Dynamic-AI-Driven-Anatomical-Pose-Transfer-DAAPT-](https://github.com/Sigurius23/Dynamic-AI-Driven-Anatomical-Pose-Transfer-DAAPT-) 🔒 private

- **What it is:** Dynamic AI-Driven Anatomical Pose Transfer (DAAPT)
- **Why it's in this catalog:** PRIVATE in source list — not publicly cloneable. Listed for completeness only.
- **Category / tier:** pose-mocap / private
- **Pipeline stages:** pose, body-model
- **Tags:** pose-transfer, anatomical, private
- **Primary language (GitHub):** none reported
- **License:** not recorded (private repository) _(source: private - not publicly verifiable)_
- **Snapshot:** ★ 1 · forks not recorded · upstream updated May 22 (snapshot)
- **Clone target when vendored:** `upstream/Sigurius23/Dynamic-AI-Driven-Anatomical-Pose-Transfer-DAAPT-` (never commit upstream code to this repo)

### 14. [cuevhv/mamma](https://github.com/cuevhv/mamma)

- **What it is:** MAMMA: Markerless Accurate Multi-person Motion Acquisition
- **Why it's in this catalog:** Multi-person markerless mocap.
- **Category / tier:** pose-mocap / extended
- **Pipeline stages:** capture, pose
- **Tags:** markerless, multi-person, mocap
- **Primary language (GitHub):** Python
- **License:** NOASSERTION (custom/mixed license file in repo - read before use) _(source: repo-root LICENSE file, non-standard text (checked 2026-10-28))_
- **Snapshot:** ★ 864 · forks 85 · upstream updated 2026-10-28 (live API 2026-10-28)
- **Clone target when vendored:** `upstream/cuevhv/mamma` (never commit upstream code to this repo)

### 15. [MaureenZOU/worldstring](https://github.com/MaureenZOU/worldstring)

- **What it is:** Official implementation for Actionable World Representation (worldstring)
- **Why it's in this catalog:** Research code; rehab relevance is indirect (world/action representation).
- **Category / tier:** 3d-reconstruction / experimental
- **Pipeline stages:** pose, dataset
- **Tags:** world-representation, actionable
- **Primary language (GitHub):** Python
- **License:** none found in repo root (checked 2026-10-28; treat as all-rights-reserved) _(source: checked repo root 2026-10-28)_
- **Snapshot:** ★ 82 · forks 1 · upstream updated 2026-08-10 (live API 2026-10-28)
- **Clone target when vendored:** `upstream/MaureenZOU/worldstring` (never commit upstream code to this repo)

### 16. [haoz19/world-tracing](https://github.com/haoz19/world-tracing)

- **What it is:** Official inference code for World Tracing
- **Why it's in this catalog:** Research code; evaluate before depending on it.
- **Category / tier:** 3d-reconstruction / experimental
- **Pipeline stages:** pose, visualization
- **Tags:** world-tracing, 3d-tracing
- **Primary language (GitHub):** Python
- **License:** NOASSERTION (custom/mixed license file in repo - read before use) _(source: GitHub API (live 2026-10-28); license file present but non-standard)_
- **Snapshot:** ★ 373 · forks 29 · upstream updated 2026-10-26 (live API 2026-10-28)
- **Clone target when vendored:** `upstream/haoz19/world-tracing` (never commit upstream code to this repo)

### 17. [Andy-Cheng/Flex4DHuman](https://github.com/Andy-Cheng/Flex4DHuman)

- **What it is:** Flex4DHuman turns monocular or sparse multi-view videos of dynamic subjects into synchronized dense multi-view videos
- **Why it's in this catalog:** Useful if multi-view synthesis helps assessment review. GitHub reports no primary language (checked 2026-10-28).
- **Category / tier:** 3d-reconstruction / experimental
- **Pipeline stages:** capture, pose
- **Tags:** multi-view, video, 4d-human
- **Primary language (GitHub):** none reported
- **License:** none found in repo root (checked 2026-10-28; treat as all-rights-reserved) _(source: checked repo root 2026-10-28)_
- **Snapshot:** ★ 106 · forks 7 · upstream updated 2026-10-27 (live API 2026-10-28)
- **Clone target when vendored:** `upstream/Andy-Cheng/Flex4DHuman` (never commit upstream code to this repo)

### 18. [facebookresearch/meshflow](https://github.com/facebookresearch/meshflow)

- **What it is:** MeshFlow: Efficient Artistic Mesh Generation via MeshVAE and Flow-based Diffusion Transformer (CVPR 2026)
- **Why it's in this catalog:** General mesh generation, not human-specific by default.
- **Category / tier:** 3d-reconstruction / experimental
- **Pipeline stages:** body-model, visualization
- **Tags:** mesh-generation, diffusion, vae
- **Primary language (GitHub):** Python
- **License:** NOASSERTION (custom/mixed license file in repo - read before use) _(source: repo-root LICENSE file, non-standard text (checked 2026-10-28))_
- **Snapshot:** ★ 528 · forks 28 · upstream updated 2026-10-26 (live API 2026-10-28)
- **Clone target when vendored:** `upstream/facebookresearch/meshflow` (never commit upstream code to this repo)

### 19. [NTUYWANG103/ViDiHand](https://github.com/NTUYWANG103/ViDiHand)

- **What it is:** Official PyTorch implementation: The Surprising Effectiveness of Video Diffusion Models for Hand Motion Reconstruction
- **Why it's in this catalog:** Hand rehab (fine motor) is the plausible niche. GitHub reports no primary language (checked 2026-10-28).
- **Category / tier:** pose-mocap / specialized
- **Pipeline stages:** pose
- **Tags:** hand, video-diffusion, reconstruction
- **Primary language (GitHub):** none reported
- **License:** none found in repo root (checked 2026-10-28; treat as all-rights-reserved) _(source: checked repo root 2026-10-28)_
- **Snapshot:** ★ 194 · forks 7 · upstream updated 2026-10-25 (live API 2026-10-28)
- **Clone target when vendored:** `upstream/NTUYWANG103/ViDiHand` (never commit upstream code to this repo)

### 20. [MyoHub/myosuite](https://github.com/MyoHub/myosuite)

- **What it is:** MyoSuite — musculoskeletal environments/tasks in MuJoCo, wrapped in the Gym API
- **Why it's in this catalog:** Core RL/control sandbox for muscle-actuated rehab tasks.
- **Category / tier:** musculoskeletal-sim / core
- **Pipeline stages:** muscle-sim, control-rl
- **Tags:** myosuite, mujoco, gym, musculoskeletal
- **Primary language (GitHub):** Python
- **License:** Apache-2.0 _(source: GitHub API (live 2026-10-28))_
- **Snapshot:** ★ 1267 · forks 181 · upstream updated 2026-10-28 (live API 2026-10-28)
- **Clone target when vendored:** `upstream/MyoHub/myosuite` (never commit upstream code to this repo)

### 21. [MarilynKeller/HIT](https://github.com/MarilynKeller/HIT)

- **What it is:** HIT: Estimating Internal Human Implicit Tissues from the Body Surface (2024)
- **Why it's in this catalog:** Internal tissue estimation; research-stage.
- **Category / tier:** body-models / extended
- **Pipeline stages:** body-model, skeleton
- **Tags:** internal-tissues, implicit, body-surface
- **Primary language (GitHub):** Python
- **License:** NOASSERTION (custom/mixed license file in repo - read before use) _(source: GitHub API (live 2026-10-28); license file present but non-standard)_
- **Snapshot:** ★ 105 · forks 13 · upstream updated 2026-10-27 (live API 2026-10-28)
- **Clone target when vendored:** `upstream/MarilynKeller/HIT` (never commit upstream code to this repo)

### 22. [MarilynKeller/SMPL2AddBiomechanics](https://github.com/MarilynKeller/SMPL2AddBiomechanics)

- **What it is:** Enable inputting a SMPL sequence into AddBiomechanics to fit an OpenSim skeleton model to the sequence
- **Why it's in this catalog:** Critical glue repo: SMPL motion -> OpenSim skeleton fitting.
- **Category / tier:** biomechanics / core
- **Pipeline stages:** skeleton, biomechanics, tooling
- **Tags:** smpl, addbiomechanics, opensim, bridge
- **Primary language (GitHub):** Python
- **License:** NOASSERTION (custom/mixed license file in repo - read before use) _(source: repo-root LICENSE.txt file, non-standard text (checked 2026-10-28))_
- **Snapshot:** ★ 157 · forks 18 · upstream updated 2026-10-14 (live API 2026-10-28)
- **Clone target when vendored:** `upstream/MarilynKeller/SMPL2AddBiomechanics` (never commit upstream code to this repo)

### 23. [MarilynKeller/aitviewer-skel](https://github.com/MarilynKeller/aitviewer-skel)

- **What it is:** aitviewer fork supporting visualization of OpenSim models and SKEL
- **Why it's in this catalog:** Preferred viewer for SKEL/OpenSim rehab sequences.
- **Category / tier:** visualization-tools / core
- **Pipeline stages:** visualization
- **Tags:** aitviewer, opensim, skel, visualization
- **Primary language (GitHub):** Python
- **License:** MIT _(source: GitHub API (live 2026-10-28))_
- **Snapshot:** ★ 80 · forks 16 · upstream updated 2026-10-14 (live API 2026-10-28)
- **Clone target when vendored:** `upstream/MarilynKeller/aitviewer-skel` (never commit upstream code to this repo)

### 24. [ahmedosman/STAR](https://github.com/ahmedosman/STAR)

- **What it is:** STAR — A Sparse Trained Articulated Human Body Regressor (ECCV 2020)
- **Why it's in this catalog:** Older parametric model; prefer SMPL-X/SKEL for new work unless STAR is required.
- **Category / tier:** body-models / extended
- **Pipeline stages:** body-model
- **Tags:** star, parametric, body
- **Primary language (GitHub):** Python
- **License:** NOASSERTION (custom/mixed license file in repo - read before use) _(source: repo-root LICENSE file, non-standard text (checked 2026-10-28))_
- **Snapshot:** ★ 727 · forks 107 · upstream updated 2026-10-14 (live API 2026-10-28)
- **Clone target when vendored:** `upstream/ahmedosman/STAR` (never commit upstream code to this repo)

### 25. [MyoHub/myo_sim](https://github.com/MyoHub/myo_sim)

- **What it is:** MyoSuite's MuJoCo musculoskeletal model library - muscle-actuated limb and full-body models loaded by the MyoSuite environments
- **Why it's in this catalog:** Model library companion to MyoSuite.
- **Category / tier:** musculoskeletal-sim / core
- **Pipeline stages:** muscle-sim
- **Tags:** mujoco, musculoskeletal, models
- **Primary language (GitHub):** Python
- **License:** Apache-2.0 _(source: GitHub API (live 2026-10-28))_
- **Snapshot:** ★ 214 · forks 51 · upstream updated 2026-10-27 (live API 2026-10-28)
- **Clone target when vendored:** `upstream/MyoHub/myo_sim` (never commit upstream code to this repo)

### 26. [MyoHub/myoconverter](https://github.com/MyoHub/myoconverter)

- **What it is:** Convert OpenSim 4.0+ MSK models into MuJoCo format with optimized muscle kinematics and kinetics
- **Why it's in this catalog:** Bridge between clinical biomechanics (OpenSim) and RL sim (MuJoCo).
- **Category / tier:** biomechanics / core
- **Pipeline stages:** biomechanics, muscle-sim, tooling
- **Tags:** opensim, mujoco, converter
- **Primary language (GitHub):** Python
- **License:** Apache-2.0 _(source: GitHub API (live 2026-10-28))_
- **Snapshot:** ★ 130 · forks 16 · upstream updated 2026-10-21 (live API 2026-10-28)
- **Clone target when vendored:** `upstream/MyoHub/myoconverter` (never commit upstream code to this repo)

### 27. [opencap-org/opencap-viewer](https://github.com/opencap-org/opencap-viewer)

- **What it is:** OpenCap viewer - browser-based web viewer for inspecting OpenCap motion-capture sessions, trials and results
- **Why it's in this catalog:** Web viewer for OpenCap sessions.
- **Category / tier:** visualization-tools / extended
- **Pipeline stages:** visualization
- **Tags:** opencap, viewer, web
- **Primary language (GitHub):** JavaScript
- **License:** Apache-2.0 _(source: GitHub API (live 2026-10-28))_
- **Snapshot:** ★ 11 · forks 13 · upstream updated 2026-10-14 (live API 2026-10-28)
- **Clone target when vendored:** `upstream/opencap-org/opencap-viewer` (never commit upstream code to this repo)

### 28. [IsshikiHugh/HSMR](https://github.com/IsshikiHugh/HSMR)

- **What it is:** Reconstructing Humans with a Biomechanically Accurate Skeleton (CVPR 2025 Oral)
- **Why it's in this catalog:** Direct image/video -> biomechanical skeleton path; high rehab relevance. Front-end of pipeline/ (adapters/hsmr_to_skelseq.py). Needs the gated SKEL model (skel.is.tue.mpg.de) and its checkpoint from HuggingFace. Quirk: demo resizes inputs with (H, W) passed as (W, H) - a 3840x2160 video runs at 1080x608; the adapter replicates this.
- **Category / tier:** pose-mocap / core
- **Pipeline stages:** pose, skeleton
- **Tags:** hsmr, skeleton, reconstruction
- **Primary language (GitHub):** Python
- **License:** MIT _(source: GitHub API (live 2026-10-28))_
- **Snapshot:** ★ 636 · forks 55 · upstream updated 2026-10-27 (live API 2026-10-28)
- **Clone target when vendored:** `upstream/IsshikiHugh/HSMR` (never commit upstream code to this repo)

### 29. [Intellindust-AI-Lab/SKEL-CF](https://github.com/Intellindust-AI-Lab/SKEL-CF)

- **What it is:** SKEL-CF: Coarse-to-Fine Biomechanical Skeleton and Surface Mesh Recovery
- **Why it's in this catalog:** Newer SKEL-based recovery; evaluate reproducibility.
- **Category / tier:** pose-mocap / experimental
- **Pipeline stages:** pose, skeleton, body-model
- **Tags:** skel, skeleton-recovery, coarse-to-fine
- **Primary language (GitHub):** Jupyter Notebook
- **License:** none found in repo root (checked 2026-10-28; treat as all-rights-reserved) _(source: checked repo root 2026-10-28)_
- **Snapshot:** ★ 83 · forks 5 · upstream updated 2026-10-27 (live API 2026-10-28)
- **Clone target when vendored:** `upstream/Intellindust-AI-Lab/SKEL-CF` (never commit upstream code to this repo)

### 30. [ZhengyiLuo/SMPLSim](https://github.com/ZhengyiLuo/SMPLSim)

- **What it is:** Simulating SMPL humanoid, supporting PHC / PHC-MJX / PULSE / SimXR code bases
- **Why it's in this catalog:** Simulation harness around SMPL humanoids.
- **Category / tier:** musculoskeletal-sim / extended
- **Pipeline stages:** muscle-sim, control-rl
- **Tags:** smpl, humanoid, simulation
- **Primary language (GitHub):** Python
- **License:** BSD-3-Clause _(source: GitHub API (live 2026-10-28))_
- **Snapshot:** ★ 354 · forks 28 · upstream updated 2026-10-22 (live API 2026-10-28)
- **Clone target when vendored:** `upstream/ZhengyiLuo/SMPLSim` (never commit upstream code to this repo)

### 31. [ZhengyiLuo/PHC](https://github.com/ZhengyiLuo/PHC)

- **What it is:** Perpetual Humanoid Control for Real-time Simulated Avatars (ICCV 2023)
- **Why it's in this catalog:** Humanoid control policy; useful for simulated patient/exercise avatars.
- **Category / tier:** musculoskeletal-sim / extended
- **Pipeline stages:** control-rl, muscle-sim
- **Tags:** phc, humanoid-control, avatar
- **Primary language (GitHub):** Python
- **License:** NOASSERTION (custom/mixed license file in repo - read before use) _(source: GitHub API (live 2026-10-28); license file present but non-standard)_
- **Snapshot:** ★ 1307 · forks 128 · upstream updated 2026-10-27 (live API 2026-10-28)
- **Clone target when vendored:** `upstream/ZhengyiLuo/PHC` (never commit upstream code to this repo)

### 32. [opensim-org/opensim-core](https://github.com/opensim-org/opensim-core)

- **What it is:** SimTK OpenSim C++ libraries and command-line applications, with Java/Python wrapping
- **Why it's in this catalog:** The clinical biomechanics engine. Heavy native build; prefer Python conda packages where possible.
- **Category / tier:** biomechanics / core
- **Pipeline stages:** biomechanics, muscle-sim
- **Tags:** opensim, simtk, inverse-kinematics, dynamics
- **Primary language (GitHub):** C++
- **License:** Apache-2.0 _(source: GitHub API (live 2026-10-28))_
- **Snapshot:** ★ 1139 · forks 405 · upstream updated 2026-10-28 (live API 2026-10-28)
- **Clone target when vendored:** `upstream/opensim-org/opensim-core` (never commit upstream code to this repo)

### 33. [keenon/nimblephysics](https://github.com/keenon/nimblephysics)

- **What it is:** Nimble: Physics Engine for Biomechanics and Deep Learning
- **Why it's in this catalog:** Differentiable biomechanics physics; research-grade.
- **Category / tier:** biomechanics / extended
- **Pipeline stages:** biomechanics, muscle-sim
- **Tags:** nimble, physics, differentiable
- **Primary language (GitHub):** C++
- **License:** NOASSERTION (custom/mixed license file in repo - read before use) _(source: GitHub API (live 2026-10-28); license file present but non-standard)_
- **Snapshot:** ★ 496 · forks 55 · upstream updated 2026-10-27 (live API 2026-10-28)
- **Clone target when vendored:** `upstream/keenon/nimblephysics` (never commit upstream code to this repo)

### 34. [keenon/AddBiomechanics](https://github.com/keenon/AddBiomechanics)

- **What it is:** A tool to automatically process and share biomechanics data
- **Why it's in this catalog:** Automated marker/mocap -> OpenSim processing and sharing.
- **Category / tier:** biomechanics / core
- **Pipeline stages:** biomechanics, tooling
- **Tags:** addbiomechanics, opensim, data-processing
- **Primary language (GitHub):** TypeScript
- **License:** NOASSERTION (custom/mixed license file in repo - read before use) _(source: GitHub API (live 2026-10-28); license file present but non-standard)_
- **Snapshot:** ★ 67 · forks 15 · upstream updated 2026-10-14 (live API 2026-10-28)
- **Clone target when vendored:** `upstream/keenon/AddBiomechanics` (never commit upstream code to this repo)

### 35. [perfanalytics/pose2sim](https://github.com/perfanalytics/pose2sim)

- **What it is:** Markerless kinematics with any cameras — from 2D pose estimation to 3D OpenSim motion
- **Why it's in this catalog:** Best-documented open path: cameras -> OpenSim kinematics. Strong rehab candidate. Used by pipeline/ (rehabtwin): Model_Pose2Sim_muscles_flex.osim + Markers_SKEL.xml/Markers_Mediapipe.xml. Known issue (2026-10-21): the 7 head markers in Markers_SKEL.xml carry torso-frame coordinates (top of head ~0.5 m too high); rehabtwin re-expresses them (configs/skel105_pose2sim.json).
- **Category / tier:** pose-mocap / core
- **Pipeline stages:** capture, pose, biomechanics
- **Tags:** pose2sim, opensim, markerless, triangulation
- **Primary language (GitHub):** Python
- **License:** BSD-3-Clause _(source: GitHub API (live 2026-10-28))_
- **Snapshot:** ★ 861 · forks 119 · upstream updated 2026-10-28 (live API 2026-10-28)
- **Clone target when vendored:** `upstream/perfanalytics/pose2sim` (never commit upstream code to this repo)

### 36. [vchoutas/smplify-x](https://github.com/vchoutas/smplify-x)

- **What it is:** Expressive Body Capture: 3D Hands, Face, and Body from a Single Image (SMPLify-X)
- **Why it's in this catalog:** Single-image fitting baseline; slower optimization-based path.
- **Category / tier:** pose-mocap / core
- **Pipeline stages:** pose, body-model
- **Tags:** smplify-x, smpl-x, fitting, single-image
- **Primary language (GitHub):** Python
- **License:** NOASSERTION (custom/mixed license file in repo - read before use) _(source: repo-root LICENSE file, non-standard text (checked 2026-10-28))_
- **Snapshot:** ★ 2185 · forks 375 · upstream updated 2026-10-28 (live API 2026-10-28)
- **Clone target when vendored:** `upstream/vchoutas/smplify-x` (never commit upstream code to this repo)

### 37. [eth-ait/aitviewer](https://github.com/eth-ait/aitviewer)

- **What it is:** A set of tools to visualize and interact with sequences of 3D data
- **Why it's in this catalog:** Upstream viewer; see aitviewer-skel fork for OpenSim/SKEL.
- **Category / tier:** visualization-tools / core
- **Pipeline stages:** visualization
- **Tags:** aitviewer, smpl, visualization
- **Primary language (GitHub):** Python
- **License:** MIT _(source: GitHub API (live 2026-10-28))_
- **Snapshot:** ★ 756 · forks 76 · upstream updated 2026-10-14 (live API 2026-10-28)
- **Clone target when vendored:** `upstream/eth-ait/aitviewer` (never commit upstream code to this repo)

### 38. [pyomeca/biobuddy](https://github.com/pyomeca/biobuddy)

- **What it is:** A generic interface to generate a virtual buddy (biomechanical models)
- **Why it's in this catalog:** Small/emerging; evaluate API maturity.
- **Category / tier:** biomechanics / specialized
- **Pipeline stages:** body-model, biomechanics, tooling
- **Tags:** biobuddy, biomechanical-model, generation
- **Primary language (GitHub):** Python
- **License:** MIT _(source: GitHub API (live 2026-10-28))_
- **Snapshot:** ★ 16 · forks 18 · upstream updated 2026-10-24 (live API 2026-10-28)
- **Clone target when vendored:** `upstream/pyomeca/biobuddy` (never commit upstream code to this repo)

### 39. [modenaxe/msk-STAPLE](https://github.com/modenaxe/msk-STAPLE)

- **What it is:** STAPLE — Shared Tools for Automatic Personalised Lower Extremity modelling: generating skeletal models from 3D bone geometries
- **Why it's in this catalog:** Lower-limb personalization; MATLAB dependency.
- **Category / tier:** anatomy-models / specialized
- **Pipeline stages:** skeleton, body-model
- **Tags:** staple, lower-limb, personalised, matlab
- **Primary language (GitHub):** MATLAB
- **License:** NOASSERTION (custom/mixed license file in repo - read before use) _(source: GitHub API (live 2026-10-28); license file present but non-standard)_
- **Snapshot:** ★ 65 · forks 18 · upstream updated 2026-10-14 (live API 2026-10-28)
- **Clone target when vendored:** `upstream/modenaxe/msk-STAPLE` (never commit upstream code to this repo)

### 40. [tgeijten/scone-core](https://github.com/tgeijten/scone-core)

- **What it is:** SCONE core — software for performing predictive simulations of biological motion
- **Why it's in this catalog:** Predictive gait/movement simulation.
- **Category / tier:** musculoskeletal-sim / extended
- **Pipeline stages:** biomechanics, muscle-sim
- **Tags:** scone, predictive-simulation, gait
- **Primary language (GitHub):** C++
- **License:** Apache-2.0 _(source: GitHub API (live 2026-10-28))_
- **Snapshot:** ★ 62 · forks 10 · upstream updated 2026-10-21 (live API 2026-10-28)
- **Clone target when vendored:** `upstream/tgeijten/scone-core` (never commit upstream code to this repo)

### 41. [tgeijten/scone-studio](https://github.com/tgeijten/scone-studio)

- **What it is:** SCONE Studio — graphical user interface for SCONE
- **Why it's in this catalog:** GUI companion to scone-core for building, running and inspecting predictive simulations without writing code.
- **Category / tier:** visualization-tools / extended
- **Pipeline stages:** visualization, biomechanics
- **Tags:** scone, gui
- **Primary language (GitHub):** C++
- **License:** GPL-3.0 _(source: GitHub API (live 2026-10-28))_
- **Snapshot:** ★ 46 · forks 7 · upstream updated 2026-10-14 (live API 2026-10-28)
- **Clone target when vendored:** `upstream/tgeijten/scone-studio` (never commit upstream code to this repo)

### 42. [tgeijten/sconegym](https://github.com/tgeijten/sconegym)

- **What it is:** Gym environments for SCONE - reinforcement-learning environments wrapping SCONE predictive musculoskeletal simulations
- **Why it's in this catalog:** RL interface to SCONE models; pairs with scone-core and depRL for learning muscle-control policies.
- **Category / tier:** musculoskeletal-sim / extended
- **Pipeline stages:** control-rl, muscle-sim
- **Tags:** scone, gym, rl
- **Primary language (GitHub):** Python
- **License:** Apache-2.0 _(source: GitHub API (live 2026-10-28))_
- **Snapshot:** ★ 50 · forks 10 · upstream updated 2026-10-14 (live API 2026-10-28)
- **Clone target when vendored:** `upstream/tgeijten/sconegym` (never commit upstream code to this repo)

### 43. [tgeijten/depRL](https://github.com/tgeijten/depRL)

- **What it is:** DEP-RL: Embodied Exploration for Reinforcement Learning in Overactuated and Musculoskeletal Systems (ICLR 2023)
- **Why it's in this catalog:** RL method for overactuated muscle systems. Star count in snapshot is ambiguous.
- **Category / tier:** musculoskeletal-sim / specialized
- **Pipeline stages:** control-rl, muscle-sim
- **Tags:** dep-rl, musculoskeletal, rl
- **Primary language (GitHub):** Python
- **License:** MIT _(source: GitHub API (live 2026-10-28))_
- **Snapshot:** ★ 3 · forks 0 · upstream updated 2026-10-14 (live API 2026-10-28)
- **Clone target when vendored:** `upstream/tgeijten/depRL` (never commit upstream code to this repo)

### 44. [amathislab/musclemimic](https://github.com/amathislab/musclemimic)

- **What it is:** Towards Embodied AI with MuscleMimic: Unlocking full-body musculoskeletal motor learning at scale
- **Why it's in this catalog:** Recent full-body muscle motor learning; watch maturity.
- **Category / tier:** musculoskeletal-sim / extended
- **Pipeline stages:** muscle-sim, control-rl
- **Tags:** musclemimic, full-body, motor-learning
- **Primary language (GitHub):** Python
- **License:** Apache-2.0 _(source: GitHub API (live 2026-10-28))_
- **Snapshot:** ★ 359 · forks 50 · upstream updated 2026-10-27 (live API 2026-10-28)
- **Clone target when vendored:** `upstream/amathislab/musclemimic` (never commit upstream code to this repo)

### 45. [amathislab/musclemimic_models](https://github.com/amathislab/musclemimic_models)

- **What it is:** Musculoskeletal models released from MuscleMimic research: full-body musculoskeletal model
- **Why it's in this catalog:** Companion model assets for musclemimic.
- **Category / tier:** musculoskeletal-sim / extended
- **Pipeline stages:** muscle-sim, body-model
- **Tags:** musclemimic, models, full-body
- **Primary language (GitHub):** Python
- **License:** Apache-2.0 _(source: GitHub API (live 2026-10-28))_
- **Snapshot:** ★ 63 · forks 7 · upstream updated 2026-10-27 (live API 2026-10-28)
- **Clone target when vendored:** `upstream/amathislab/musclemimic_models` (never commit upstream code to this repo)

### 46. [robfiras/loco-mujoco](https://github.com/robfiras/loco-mujoco)

- **What it is:** Imitation learning benchmark focusing on complex locomotion tasks using MuJoCo
- **Why it's in this catalog:** Locomotion benchmark; rehab relevance via gait retraining sims.
- **Category / tier:** musculoskeletal-sim / extended
- **Pipeline stages:** control-rl, muscle-sim
- **Tags:** loco-mujoco, imitation-learning, locomotion, benchmark
- **Primary language (GitHub):** Python
- **License:** MIT _(source: GitHub API (live 2026-10-28))_
- **Snapshot:** ★ 1471 · forks 153 · upstream updated 2026-10-28 (live API 2026-10-28)
- **Clone target when vendored:** `upstream/robfiras/loco-mujoco` (never commit upstream code to this repo)

### 47. [LNSGroup/MS-Human-700](https://github.com/LNSGroup/MS-Human-700)

- **What it is:** MS-Human-700: Whole-body Human MusculoSkeletal Model
- **Why it's in this catalog:** Model asset repo; verify format/license before use. GitHub reports no primary language (checked 2026-10-28).
- **Category / tier:** anatomy-models / specialized
- **Pipeline stages:** muscle-sim, body-model
- **Tags:** whole-body, musculoskeletal-model, 700
- **Primary language (GitHub):** none reported
- **License:** Apache-2.0 _(source: GitHub API (live 2026-10-28))_
- **Snapshot:** ★ 244 · forks 25 · upstream updated 2026-10-28 (live API 2026-10-28)
- **Clone target when vendored:** `upstream/LNSGroup/MS-Human-700` (never commit upstream code to this repo)

### 48. [DaebangStn/exo-plore](https://github.com/DaebangStn/exo-plore)

- **What it is:** EXO-PLORE: Exploring Exoskeleton Control Space through Human-Aligned Simulation (ICLR 2026)
- **Why it's in this catalog:** Exoskeleton control exploration.
- **Category / tier:** rehab-assistive / specialized
- **Pipeline stages:** control-rl, muscle-sim
- **Tags:** exoskeleton, control, simulation
- **Primary language (GitHub):** C++
- **License:** NOASSERTION (custom/mixed license file in repo - read before use) _(source: GitHub API (live 2026-10-28); license file present but non-standard)_
- **Snapshot:** ★ 23 · forks 4 · upstream updated 2026-10-25 (live API 2026-10-28)
- **Clone target when vendored:** `upstream/DaebangStn/exo-plore` (never commit upstream code to this repo)

### 49. [stanfordnmbl/sit2stand](https://github.com/stanfordnmbl/sit2stand)

- **What it is:** Stanford NMBL sit-to-stand project (details in upstream repo)
- **Why it's in this catalog:** Sit-to-stand is a core rehab functional task; inspect upstream for scope/data.
- **Category / tier:** rehab-assistive / specialized
- **Pipeline stages:** biomechanics
- **Tags:** sit-to-stand, stanford-nmbl, functional-movement
- **Primary language (GitHub):** HTML
- **License:** none found in repo root (checked 2026-10-28; treat as all-rights-reserved) _(source: checked repo root 2026-10-28)_
- **Snapshot:** ★ 4 · forks 2 · upstream updated 2026-10-14 (live API 2026-10-28)
- **Clone target when vendored:** `upstream/stanfordnmbl/sit2stand` (never commit upstream code to this repo)

### 50. [stanfordnmbl/GaitDynamics](https://github.com/stanfordnmbl/GaitDynamics)

- **What it is:** Gait dynamics tools from Stanford NMBL - utilities for gait-dynamics analysis alongside OpenSim workflows
- **Why it's in this catalog:** Gait analysis; pairs with OpenSim workflows.
- **Category / tier:** biomechanics / extended
- **Pipeline stages:** biomechanics
- **Tags:** gait, dynamics, stanford-nmbl
- **Primary language (GitHub):** Python
- **License:** MIT _(source: GitHub API (live 2026-10-28))_
- **Snapshot:** ★ 135 · forks 17 · upstream updated 2026-10-27 (live API 2026-10-28)
- **Clone target when vendored:** `upstream/stanfordnmbl/GaitDynamics` (never commit upstream code to this repo)

### 51. [marek-simonik/record3d](https://github.com/marek-simonik/record3d)

- **What it is:** Record3D iOS app library — receive RGBD stream from iOS devices with TrueDepth cameras
- **Why it's in this catalog:** Low-cost depth capture from iPhone/iPad.
- **Category / tier:** data-capture / specialized
- **Pipeline stages:** capture
- **Tags:** rgbd, ios, truedepth, streaming
- **Primary language (GitHub):** C
- **License:** LGPL-2.1 _(source: GitHub API (live 2026-10-28))_
- **Snapshot:** ★ 493 · forks 78 · upstream updated 2026-10-14 (live API 2026-10-28)
- **Clone target when vendored:** `upstream/marek-simonik/record3d` (never commit upstream code to this repo)

### 52. [isl-org/Open3D](https://github.com/isl-org/Open3D)

- **What it is:** Open3D: A Modern Library for 3D Data Processing
- **Why it's in this catalog:** General 3D backbone for scans/point clouds; not rehab-specific.
- **Category / tier:** 3d-reconstruction / core
- **Pipeline stages:** capture, visualization, tooling
- **Tags:** open3d, point-cloud, 3d-processing
- **Primary language (GitHub):** C++
- **License:** NOASSERTION (custom/mixed license file in repo - read before use) _(source: GitHub API (live 2026-10-28); license file present but non-standard)_
- **Snapshot:** ★ 14136 · forks 2646 · upstream updated 2026-10-28 (live API 2026-10-28)
- **Clone target when vendored:** `upstream/isl-org/Open3D` (never commit upstream code to this repo)

### 53. [rohwalia/MyoBack](https://github.com/rohwalia/MyoBack)

- **What it is:** MyoBack — simulation of a neuromusculoskeletal model of the back with an exoskeleton; a MyoSuite back model derived from a physiologically accurate OpenSim model, validated with a passive back exoskeleton
- **Why it's in this catalog:** Resolved 2026-10-21 from upstream README. Back/spine rehab + exo evaluation niche; pairs with dfki-av/simspine. License: not declared in GitHub API metadata (2026-10-21) — check upstream repo.
- **Category / tier:** rehab-assistive / specialized
- **Pipeline stages:** muscle-sim, biomechanics
- **Tags:** myoback, back, myosuite, exoskeleton, opensim
- **Primary language (GitHub):** Python
- **License:** none found in repo root (checked 2026-10-28; treat as all-rights-reserved) _(source: checked repo root 2026-10-28)_
- **Snapshot:** ★ 7 · forks 1 · upstream updated 2026-10-14 (live API 2026-10-21)
- **Clone target when vendored:** `upstream/rohwalia/MyoBack` (never commit upstream code to this repo)

### 54. [lsw9021/MASS](https://github.com/lsw9021/MASS)

- **What it is:** MASS (Muscle-Actuated Skeletal System) — simulation and control of a full-body musculoskeletal system driven by muscle activations, with Python/PyTorch deep-RL interfacing (SIGGRAPH 2019)
- **Why it's in this catalog:** Resolved 2026-10-21 from upstream README (Apache-2.0). Research simulator; compare against MyoSuite/SCONE before adopting. License (GitHub API, 2026-10-21): Apache-2.0.
- **Category / tier:** musculoskeletal-sim / specialized
- **Pipeline stages:** muscle-sim, control-rl
- **Tags:** mass, muscle-actuated, full-body, rl
- **Primary language (GitHub):** Mathematica
- **License:** Apache-2.0 _(source: repo-root LICENSE file (checked 2026-10-28))_
- **Snapshot:** ★ 638 · forks 122 · upstream updated 2026-10-20 (live API 2026-10-21)
- **Clone target when vendored:** `upstream/lsw9021/MASS` (never commit upstream code to this repo)

### 55. [neumovelab/myoassist](https://github.com/neumovelab/myoassist)

- **What it is:** MyoAssist (assistive musculoskeletal simulation; details in upstream repo)
- **Why it's in this catalog:** Assistive-device simulation niche.
- **Category / tier:** rehab-assistive / specialized
- **Pipeline stages:** muscle-sim, control-rl
- **Tags:** assistive, musculoskeletal, exoskeleton
- **Primary language (GitHub):** Jupyter Notebook
- **License:** Apache-2.0 _(source: repo-root LICENSE file (checked 2026-10-28))_
- **Snapshot:** ★ 62 · forks 21 · upstream updated 21 minutes ago (snapshot)
- **Clone target when vendored:** `upstream/neumovelab/myoassist` (never commit upstream code to this repo)

### 56. [hzm2016/mass-dart-exo](https://github.com/hzm2016/mass-dart-exo)

- **What it is:** MASS/DART exoskeleton variant — upstream README presents the MASS muscle-actuated full-body skeletal simulation system; exoskeleton-specific changes are not documented in the README
- **Why it's in this catalog:** Partially resolved 2026-10-21: base system identified as MASS, but exo specifics are undocumented upstream — audit the code diff before any use. License (GitHub API, 2026-10-21): Apache-2.0.
- **Category / tier:** rehab-assistive / specialized
- **Pipeline stages:** muscle-sim, control-rl
- **Tags:** mass, dart, exoskeleton
- **Primary language (GitHub):** Mathematica
- **License:** Apache-2.0 _(source: repo-root LICENSE file (checked 2026-10-28))_
- **Snapshot:** ★ 2 · forks 0 · upstream updated 2026-10-14 (live API 2026-10-21)
- **Clone target when vendored:** `upstream/hzm2016/mass-dart-exo` (never commit upstream code to this repo)

### 57. [strayrobots/scanner](https://github.com/strayrobots/scanner)

- **What it is:** An app for collecting raw RGB-D scans on iOS devices
- **Why it's in this catalog:** iOS RGB-D scan-collection app; candidate capture front-end for Tier-B surface scanning.
- **Category / tier:** data-capture / specialized
- **Pipeline stages:** capture
- **Tags:** rgbd, ios, scanner
- **Primary language (GitHub):** C++
- **License:** MIT _(source: repo-root LICENSE.md file (checked 2026-10-28))_
- **Snapshot:** ★ 155 · forks 30 · upstream updated Apr 4 (snapshot)
- **Clone target when vendored:** `upstream/strayrobots/scanner` (never commit upstream code to this repo)

### 58. [strayrobots/3d-annotation-tool](https://github.com/strayrobots/3d-annotation-tool)

- **What it is:** A graphical user interface to annotate point clouds and 3D data
- **Why it's in this catalog:** Annotation tooling for 3D clinical datasets.
- **Category / tier:** visualization-tools / specialized
- **Pipeline stages:** visualization, tooling
- **Tags:** annotation, point-cloud, gui
- **Primary language (GitHub):** C++
- **License:** MIT _(source: repo-root LICENSE.txt file (checked 2026-10-28))_
- **Snapshot:** ★ 94 · forks 13 · upstream updated Jun 27, 2022
- **Clone target when vendored:** `upstream/strayrobots/3d-annotation-tool` (never commit upstream code to this repo)

### 59. [mohamedhassanmus/prox](https://github.com/mohamedhassanmus/prox)

- **What it is:** PROX: Resolving 3D Human Pose Ambiguities with 3D Scene Constraints
- **Why it's in this catalog:** Older (2021); scene-aware pose in home/clinic environments is conceptually relevant.
- **Category / tier:** pose-mocap / specialized
- **Pipeline stages:** pose, body-model
- **Tags:** prox, scene-constraints, smpl-x
- **Primary language (GitHub):** Python
- **License:** NOASSERTION (custom/mixed license file in repo - read before use) _(source: repo-root LICENSE file, non-standard text (checked 2026-10-28))_
- **Snapshot:** ★ 232 · forks 18 · upstream updated Jul 13, 2021
- **Clone target when vendored:** `upstream/mohamedhassanmus/prox` (never commit upstream code to this repo)

### 60. [hailsong/RC-SMPL](https://github.com/hailsong/RC-SMPL)

- **What it is:** RC-SMPL — Real-time Cumulative SMPL-based Avatar Body Generation (IEEE ISMAR 2023); cumulatively updates avatar texture and normal maps from images/video in real time
- **Why it's in this catalog:** Resolved 2026-10-21 from upstream README. Twin *appearance* layer (texture/normals), not anatomical accuracy. License: not declared in GitHub API metadata (2026-10-21) — check upstream repo.
- **Category / tier:** body-models / specialized
- **Pipeline stages:** body-model, visualization
- **Tags:** rc-smpl, smpl, avatar, real-time, texture
- **Primary language (GitHub):** C#
- **License:** none found in repo root (checked 2026-10-28; treat as all-rights-reserved) _(source: checked repo root 2026-10-28)_
- **Snapshot:** ★ 10 · forks 0 · upstream updated 2026-10-14 (live API 2026-10-21)
- **Clone target when vendored:** `upstream/hailsong/RC-SMPL` (never commit upstream code to this repo)

### 61. [xiexh20/behave-dataset](https://github.com/xiexh20/behave-dataset)

- **What it is:** Code to access the BEHAVE dataset (CVPR 2022) — human-object interaction
- **Why it's in this catalog:** HOI dataset; useful for ADL (activities of daily living) rehab contexts.
- **Category / tier:** datasets-interaction / specialized
- **Pipeline stages:** dataset, pose
- **Tags:** behave, human-object-interaction, dataset
- **Primary language (GitHub):** Python
- **License:** NOASSERTION (custom/mixed license file in repo - read before use) _(source: repo-root LICENSE file, non-standard text (checked 2026-10-28))_
- **Snapshot:** ★ 193 · forks 8 · upstream updated Feb 16, 2025
- **Clone target when vendored:** `upstream/xiexh20/behave-dataset` (never commit upstream code to this repo)

### 62. [dfki-av/simspine](https://github.com/dfki-av/simspine)

- **What it is:** SIMSPINE: A Biomechanics-Aware Simulation Framework for 3D Spine Motion Annotation and Benchmarking
- **Why it's in this catalog:** Spine-specific; relevant to back rehab / MyoBack thread.
- **Category / tier:** biomechanics / experimental
- **Pipeline stages:** skeleton, biomechanics
- **Tags:** spine, simulation, annotation, benchmark
- **Primary language (GitHub):** Python
- **License:** NOASSERTION (custom/mixed license file in repo - read before use) _(source: repo-root LICENSE file, non-standard text (checked 2026-10-28))_
- **Snapshot:** ★ 13 · forks 0 · upstream updated 2026-10-14 (live API 2026-10-28)
- **Clone target when vendored:** `upstream/dfki-av/simspine` (never commit upstream code to this repo)

### 63. [Xinyu-Yi/TransPose](https://github.com/Xinyu-Yi/TransPose)

- **What it is:** TransPose — real-time motion capture that estimates poses and global translations using only 6 IMUs
- **Why it's in this catalog:** Wearable IMU path for home rehab without cameras.
- **Category / tier:** pose-mocap / core
- **Pipeline stages:** capture, pose
- **Tags:** imu, real-time, mocap, 6-imu
- **Primary language (GitHub):** Python
- **License:** GPL-3.0 _(source: repo-root LICENSE file (checked 2026-10-28))_
- **Snapshot:** ★ 456 · forks 84 · upstream updated May 8, 2025
- **Clone target when vendored:** `upstream/Xinyu-Yi/TransPose` (never commit upstream code to this repo)

### 64. [Xinyu-Yi/PIP](https://github.com/Xinyu-Yi/PIP)

- **What it is:** PIP — real-time system that captures physically correct human motion, joint torques, and ground reaction forces with only 6 IMUs
- **Why it's in this catalog:** IMU + physics outputs (torques/GRF) are unusually rehab-relevant.
- **Category / tier:** pose-mocap / core
- **Pipeline stages:** capture, pose, biomechanics
- **Tags:** imu, joint-torque, ground-reaction-force, physics
- **Primary language (GitHub):** Python
- **License:** GPL-3.0 _(source: repo-root LICENSE file (checked 2026-10-28))_
- **Snapshot:** ★ 369 · forks 41 · upstream updated May 8, 2025
- **Clone target when vendored:** `upstream/Xinyu-Yi/PIP` (never commit upstream code to this repo)

### 65. [Xinyu-Yi/PNP](https://github.com/Xinyu-Yi/PNP)

- **What it is:** PNP — real-time human motion capture based on 6 IMUs, upgrading PIP through non-inertial forces
- **Why it's in this catalog:** Successor direction to PIP; compare before choosing.
- **Category / tier:** pose-mocap / extended
- **Pipeline stages:** capture, pose, biomechanics
- **Tags:** imu, pip-successor, physics
- **Primary language (GitHub):** Python
- **License:** GPL-3.0 _(source: repo-root LICENSE file (checked 2026-10-28))_
- **Snapshot:** ★ 137 · forks 16 · upstream updated Aug 10, 2025
- **Clone target when vendored:** `upstream/Xinyu-Yi/PNP` (never commit upstream code to this repo)

### 66. [ptrvilya/echo](https://github.com/ptrvilya/echo)

- **What it is:** ECHO: method for reconstructing human-object interaction from sparse ego-centric tracking
- **Why it's in this catalog:** Egocentric human-object interaction reconstruction; early-stage research code with niche relevance to hand/object rehab review.
- **Category / tier:** datasets-interaction / experimental
- **Pipeline stages:** pose, dataset
- **Tags:** egocentric, human-object-interaction, reconstruction
- **Primary language (GitHub):** Python
- **License:** MIT _(source: GitHub API (live 2026-10-28))_
- **Snapshot:** ★ 17 · forks 0 · upstream updated 2026-10-23 (live API 2026-10-28)
- **Clone target when vendored:** `upstream/ptrvilya/echo` (never commit upstream code to this repo)

### 67. [jerela/OpenSimLive](https://github.com/jerela/OpenSimLive)

- **What it is:** Live inverse kinematics based on IMU orientations using OpenSim 4.1 API
- **Why it's in this catalog:** Real-time OpenSim IK from IMUs; pinned to OpenSim 4.1 — check maintenance.
- **Category / tier:** biomechanics / specialized
- **Pipeline stages:** capture, biomechanics
- **Tags:** opensim, imu, real-time, inverse-kinematics
- **Primary language (GitHub):** C++
- **License:** Apache-2.0 _(source: repo-root LICENSE file (checked 2026-10-28))_
- **Snapshot:** ★ 30 · forks 8 · upstream updated Apr 5, 2023
- **Clone target when vendored:** `upstream/jerela/OpenSimLive` (never commit upstream code to this repo)

### 68. [freemocap/freemocap](https://github.com/freemocap/freemocap)

- **What it is:** FreeMoCap — Free Motion Capture for Everyone
- **Why it's in this catalog:** Most accessible entry point: webcams -> 3D motion. Strong Phase-1 candidate.
- **Category / tier:** pose-mocap / core
- **Pipeline stages:** capture, pose
- **Tags:** freemocap, markerless, webcam, mocap
- **Primary language (GitHub):** TypeScript
- **License:** AGPL-3.0 _(source: repo-root LICENSE file (checked 2026-10-28))_
- **Snapshot:** ★ 10474 · forks 982 · upstream updated 2 days ago (snapshot)
- **Clone target when vendored:** `upstream/freemocap/freemocap` (never commit upstream code to this repo)

### 69. [xibushu/UniForge3D](https://github.com/xibushu/UniForge3D)

- **What it is:** UniForge3D: Joint 3D Reconstruction and Generation in a Shared Anchor-Guided Space
- **Why it's in this catalog:** General 3D; human application needs validation.
- **Category / tier:** 3d-reconstruction / experimental
- **Pipeline stages:** body-model
- **Tags:** 3d-reconstruction, generation
- **Primary language (GitHub):** Python
- **License:** MIT _(source: repo-root LICENSE file (checked 2026-10-28))_
- **Snapshot:** ★ 373 · forks 33 · upstream updated 4 days ago (snapshot)
- **Clone target when vendored:** `upstream/xibushu/UniForge3D` (never commit upstream code to this repo)

### 70. [Net-Maker/GaussiAnimate](https://github.com/Net-Maker/GaussiAnimate)

- **What it is:** GaussiAnimate: Reconstruct and Rig Animatable Categories with Level of Dynamics
- **Why it's in this catalog:** Rigging/animation research; peripheral until human-specific results are shown.
- **Category / tier:** 3d-reconstruction / experimental
- **Pipeline stages:** body-model, visualization
- **Tags:** gaussian, rigging, animation
- **Primary language (GitHub):** Python
- **License:** MIT _(source: repo-root LICENSE file (checked 2026-10-28))_
- **Snapshot:** ★ 157 · forks 15 · upstream updated 4 days ago (snapshot)
- **Clone target when vendored:** `upstream/Net-Maker/GaussiAnimate` (never commit upstream code to this repo)

### 71. [muelea/shapy](https://github.com/muelea/shapy)

- **What it is:** SHAPY — accurate 3D body shape regression using metric and semantic attributes; predicts SMPL-X shape plus height/weight/chest/waist/hip measurements from an image
- **Why it's in this catalog:** Digital-twin onboarding: turns a photo + optional measurements into a personalised body shape. License: not declared in GitHub API metadata (2026-10-21) — check upstream repo.
- **Category / tier:** body-models / core
- **Pipeline stages:** body-model
- **Tags:** shapy, anthropometry, body-measurements, smpl-x
- **Primary language (GitHub):** Python
- **License:** none found in repo root (checked 2026-10-28; treat as all-rights-reserved) _(source: checked repo root 2026-10-28)_
- **Snapshot:** ★ 389 · forks 62 · upstream updated 2026-10-05 (live API 2026-10-21)
- **Clone target when vendored:** `upstream/muelea/shapy` (never commit upstream code to this repo)

### 72. [YuliangXiu/ECON](https://github.com/YuliangXiu/ECON)

- **What it is:** ECON — explicit clothed humans optimised via normal integration; high-fidelity 3D clothed human from a single image, SMPL-X animatable
- **Why it's in this catalog:** Captures the patient's actual outer/clothed shape for the twin. License (GitHub API, 2026-10-21): NOASSERTION.
- **Category / tier:** 3d-reconstruction / extended
- **Pipeline stages:** capture, body-model
- **Tags:** econ, clothed-avatar, single-image
- **Primary language (GitHub):** Python
- **License:** NOASSERTION (custom/mixed license file in repo - read before use) _(source: repo-root LICENSE file, non-standard text (checked 2026-10-28))_
- **Snapshot:** ★ 1213 · forks 115 · upstream updated 2026-10-14 (live API 2026-10-21)
- **Clone target when vendored:** `upstream/YuliangXiu/ECON` (never commit upstream code to this repo)

### 73. [yfeng95/PIXIE](https://github.com/yfeng95/PIXIE)

- **What it is:** PIXIE — collaborative regression of expressive bodies: whole-body SMPL-X with detailed face and hand articulation from a single image
- **Why it's in this catalog:** Avatar personalisation including face/hands. License (GitHub API, 2026-10-21): NOASSERTION.
- **Category / tier:** body-models / extended
- **Pipeline stages:** body-model
- **Tags:** pixie, expressive, avatar, face, hands
- **Primary language (GitHub):** Python
- **License:** NOASSERTION (custom/mixed license file in repo - read before use) _(source: repo-root LICENSE file, non-standard text (checked 2026-10-28))_
- **Snapshot:** ★ 517 · forks 70 · upstream updated 2026-09-29 (live API 2026-10-21)
- **Clone target when vendored:** `upstream/yfeng95/PIXIE` (never commit upstream code to this repo)

### 74. [google-ai-edge/mediapipe](https://github.com/google-ai-edge/mediapipe)

- **What it is:** MediaPipe — cross-platform ML perception pipelines; Pose infers 33 3D body landmarks in real time on phone, desktop and web
- **Why it's in this catalog:** Zero-friction patient-side tracker for the live twin. License (GitHub API, 2026-10-21): Apache-2.0.
- **Category / tier:** pose-mocap / core
- **Pipeline stages:** capture, pose
- **Tags:** mediapipe, blazepose, real-time, mobile, web
- **Primary language (GitHub):** C++
- **License:** Apache-2.0 _(source: repo-root LICENSE file (checked 2026-10-28))_
- **Snapshot:** ★ 37345 · forks 6189 · upstream updated 2026-10-20 (live API 2026-10-21)
- **Clone target when vendored:** `upstream/google-ai-edge/mediapipe` (never commit upstream code to this repo)

### 75. [open-mmlab/mmpose](https://github.com/open-mmlab/mmpose)

- **What it is:** MMPose — OpenMMLab pose estimation toolbox and benchmark, including the RTMPose real-time model family
- **Why it's in this catalog:** Production/swappable 2D-pose layer under Pose2Sim-style pipelines. License (GitHub API, 2026-10-21): Apache-2.0.
- **Category / tier:** pose-mocap / core
- **Pipeline stages:** pose
- **Tags:** mmpose, rtmpose, real-time, toolbox
- **Primary language (GitHub):** Python
- **License:** Apache-2.0 _(source: repo-root LICENSE file (checked 2026-10-28))_
- **Snapshot:** ★ 7967 · forks 1540 · upstream updated 2026-10-20 (live API 2026-10-21)
- **Clone target when vendored:** `upstream/open-mmlab/mmpose` (never commit upstream code to this repo)

### 76. [zju3dv/GVHMR](https://github.com/zju3dv/GVHMR)

- **What it is:** GVHMR — world-grounded human motion recovery via gravity-view coordinates; SMPL motion in camera and world frames from monocular video
- **Why it's in this catalog:** Gravity/world frame is essential for posture (vs camera-frame pose). License (GitHub API, 2026-10-21): NOASSERTION.
- **Category / tier:** pose-mocap / core
- **Pipeline stages:** pose, body-model
- **Tags:** gvhmr, world-grounded, gravity, smpl, monocular
- **Primary language (GitHub):** Jupyter Notebook
- **License:** NOASSERTION (custom/mixed license file in repo - read before use) _(source: repo-root LICENSE file, non-standard text (checked 2026-10-28))_
- **Snapshot:** ★ 2161 · forks 256 · upstream updated 2026-10-20 (live API 2026-10-21)
- **Clone target when vendored:** `upstream/zju3dv/GVHMR` (never commit upstream code to this repo)

### 77. [zju3dv/EasyMocap](https://github.com/zju3dv/EasyMocap)

- **What it is:** EasyMocap — multi-view and monocular SMPL/SMPL-X/MANO motion capture toolkit
- **Why it's in this catalog:** Clinic-grade multi-camera tier for higher-accuracy twin sessions. License (GitHub API, 2026-10-21): NOASSERTION.
- **Category / tier:** pose-mocap / extended
- **Pipeline stages:** capture, pose, body-model
- **Tags:** easymocap, multi-view, smpl-x, calibration
- **Primary language (GitHub):** Python
- **License:** MIT-like (see file) _(source: repo-root LICENSE file (checked 2026-10-28))_
- **Snapshot:** ★ 4929 · forks 571 · upstream updated 2026-10-20 (live API 2026-10-21)
- **Clone target when vendored:** `upstream/zju3dv/EasyMocap` (never commit upstream code to this repo)

### 78. [facebookresearch/sapiens](https://github.com/facebookresearch/sapiens)

- **What it is:** Sapiens — high-resolution foundation models for human-centric vision: 2D pose, body-part segmentation, depth and normals
- **Why it's in this catalog:** Dense human perception front-end (keypoints + parts) for twin fitting. License (GitHub API, 2026-10-21): NOASSERTION.
- **Category / tier:** pose-mocap / extended
- **Pipeline stages:** capture, pose
- **Tags:** sapiens, foundation-model, whole-body, segmentation
- **Primary language (GitHub):** Python
- **License:** CC (see file) _(source: repo-root LICENSE file (checked 2026-10-28))_
- **Snapshot:** ★ 5432 · forks 323 · upstream updated 2026-10-16 (live API 2026-10-21)
- **Clone target when vendored:** `upstream/facebookresearch/sapiens` (never commit upstream code to this repo)

### 79. [facebookresearch/sapiens2](https://github.com/facebookresearch/sapiens2)

- **What it is:** Sapiens2 — 1K-resolution human vision transformers pretrained on 1B human images; pose, segmentation, normals, pointmaps, matting
- **Why it's in this catalog:** Successor to Sapiens; evaluate against Sapiens v1 before adopting. License (GitHub API, 2026-10-21): NOASSERTION.
- **Category / tier:** pose-mocap / experimental
- **Pipeline stages:** capture, pose
- **Tags:** sapiens2, foundation-model, whole-body
- **Primary language (GitHub):** Python
- **License:** NOASSERTION (custom/mixed license file in repo - read before use) _(source: repo-root LICENSE.md file, non-standard text (checked 2026-10-28))_
- **Snapshot:** ★ 998 · forks 68 · upstream updated 2026-10-20 (live API 2026-10-21)
- **Clone target when vendored:** `upstream/facebookresearch/sapiens2` (never commit upstream code to this repo)

### 80. [SlimeVR/SlimeVR-Server](https://github.com/SlimeVR/SlimeVR-Server)

- **What it is:** SlimeVR Server — server for the SlimeVR open full-body tracking ecosystem; fuses IMU trackers into a full-body pose
- **Why it's in this catalog:** Sensor-suit hub: the wearable side of the 1:1 twin without cameras. License (GitHub API, 2026-10-21): Apache-2.0. pipeline/ reads its VMC output (`rehabtwin vmc-posture`) for live posture cues.
- **Category / tier:** data-capture / core
- **Pipeline stages:** capture, pose
- **Tags:** slimevr, imu, full-body-tracking, suit
- **Primary language (GitHub):** Fluent
- **License:** MIT _(source: repo-root LICENSE-MIT file (checked 2026-10-28))_
- **Snapshot:** ★ 1047 · forks 257 · upstream updated 2026-10-18 (live API 2026-10-21)
- **Clone target when vendored:** `upstream/SlimeVR/SlimeVR-Server` (never commit upstream code to this repo)

### 81. [SlimeVR/SlimeVR-Tracker-ESP](https://github.com/SlimeVR/SlimeVR-Tracker-ESP)

- **What it is:** SlimeVR Tracker firmware for ESP32/ESP8266 and various IMUs — DIY open-hardware body trackers
- **Why it's in this catalog:** Buildable/buyable IMU trackers; pairs with SlimeVR-Server. License (GitHub API, 2026-10-21): Apache-2.0.
- **Category / tier:** data-capture / core
- **Pipeline stages:** capture
- **Tags:** slimevr, esp32, imu, firmware, open-hardware
- **Primary language (GitHub):** C++
- **License:** MIT _(source: repo-root LICENSE-MIT file (checked 2026-10-28))_
- **Snapshot:** ★ 1088 · forks 396 · upstream updated 2026-10-20 (live API 2026-10-21)
- **Clone target when vendored:** `upstream/SlimeVR/SlimeVR-Tracker-ESP` (never commit upstream code to this repo)

### 82. [sccn/labstreaminglayer](https://github.com/sccn/labstreaminglayer)

- **What it is:** Lab Streaming Layer (LSL) — multimodal time-synchronised data transmission and recording (liblsl, pylsl, LabRecorder/XDF ecosystem)
- **Why it's in this catalog:** Sync layer that keeps video + IMU + EMG + haptic streams aligned for a true 1:1 twin. License (GitHub API, 2026-10-21): NOASSERTION.
- **Category / tier:** data-capture / core
- **Pipeline stages:** capture, tooling
- **Tags:** lsl, synchronization, xdf, multimodal, emg
- **Primary language (GitHub):** HTML
- **License:** MIT _(source: repo-root LICENSE file (checked 2026-10-28))_
- **Snapshot:** ★ 788 · forks 197 · upstream updated 2026-10-17 (live API 2026-10-21)
- **Clone target when vendored:** `upstream/sccn/labstreaminglayer` (never commit upstream code to this repo)

### 83. [DeepLabCut/DeepLabCut](https://github.com/DeepLabCut/DeepLabCut)

- **What it is:** DeepLabCut — markerless pose estimation of user-defined features with deep learning (animals incl. humans)
- **Why it's in this catalog:** Use when rehab needs custom landmarks (e.g. scapula/pelvis) trained on your own labelled video. License (GitHub API, 2026-10-21): LGPL-3.0.
- **Category / tier:** pose-mocap / specialized
- **Pipeline stages:** pose, tooling
- **Tags:** deeplabcut, custom-landmarks, markerless, training
- **Primary language (GitHub):** Python
- **License:** LGPL (see file) _(source: repo-root LICENSE file (checked 2026-10-28))_
- **Snapshot:** ★ 5795 · forks 1795 · upstream updated 2026-10-20 (live API 2026-10-21)
- **Clone target when vendored:** `upstream/DeepLabCut/DeepLabCut` (never commit upstream code to this repo)

### 84. [DeepLabCut/DeepLabCut-live](https://github.com/DeepLabCut/DeepLabCut-live)

- **What it is:** DeepLabCut-Live — SDK for running DeepLabCut models on a live video stream
- **Why it's in this catalog:** Real-time companion to DeepLabCut for live custom-landmark tracking. License (GitHub API, 2026-10-21): NOASSERTION.
- **Category / tier:** pose-mocap / specialized
- **Pipeline stages:** capture, pose
- **Tags:** deeplabcut-live, real-time, live
- **Primary language (GitHub):** Python
- **License:** AGPL-3.0 _(source: repo-root LICENSE file (checked 2026-10-28))_
- **Snapshot:** ★ 239 · forks 57 · upstream updated 2026-10-02 (live API 2026-10-21)
- **Clone target when vendored:** `upstream/DeepLabCut/DeepLabCut-live` (never commit upstream code to this repo)

### 85. [sangho0n/Realtime_SMPLX_Unity](https://github.com/sangho0n/Realtime_SMPLX_Unity)

- **What it is:** Real-time SMPL-X in Unity — shape reconstruction via a Python server plus MediaPipe pose in Unity, animating SMPL-X live
- **Why it's in this catalog:** Reference implementation for the missing live-twin Unity front-end (example code, not a product). License (GitHub API, 2026-10-21): MIT.
- **Category / tier:** visualization-tools / specialized
- **Pipeline stages:** visualization, body-model
- **Tags:** unity, smpl-x, real-time, digital-twin-runtime
- **Primary language (GitHub):** C#
- **License:** MIT _(source: repo-root LICENSE file (checked 2026-10-28))_
- **Snapshot:** ★ 50 · forks 6 · upstream updated 2026-07-25 (live API 2026-10-21)
- **Clone target when vendored:** `upstream/sangho0n/Realtime_SMPLX_Unity` (never commit upstream code to this repo)

### 86. [avakanski/A-Deep-Learning-Framework-for-Assessing-Physical-Rehabilitation-Exercises](https://github.com/avakanski/A-Deep-Learning-Framework-for-Assessing-Physical-Rehabilitation-Exercises)

- **What it is:** Framework for quality assessment of physical rehabilitation exercises on the UI-PRMD dataset (skeletal joint data, correct vs incorrect movements)
- **Why it's in this catalog:** Teaches the agent what 'wrong' looks like for standard rehab exercises. License: not declared in GitHub API metadata (2026-10-21) — check upstream repo.
- **Category / tier:** rehab-assessment / extended
- **Pipeline stages:** dataset, pose
- **Tags:** ui-prmd, exercise-assessment, quality-score, dataset
- **Primary language (GitHub):** Jupyter Notebook
- **License:** none found in repo root (checked 2026-10-28; treat as all-rights-reserved) _(source: checked repo root 2026-10-28)_
- **Snapshot:** ★ 75 · forks 22 · upstream updated 2026-10-18 (live API 2026-10-21)
- **Clone target when vendored:** `upstream/avakanski/A-Deep-Learning-Framework-for-Assessing-Physical-Rehabilitation-Exercises` (never commit upstream code to this repo)

### 87. [fokhruli/STGCN-rehab](https://github.com/fokhruli/STGCN-rehab)

- **What it is:** Graph convolutional networks for assessment of physical rehabilitation exercises (KIMORE and UI-PRMD)
- **Why it's in this catalog:** Clinician-scored exercise quality (KIMORE includes patients) — core for the correction layer. License (GitHub API, 2026-10-21): MIT.
- **Category / tier:** rehab-assessment / core
- **Pipeline stages:** dataset, pose
- **Tags:** stgcn, kimore, ui-prmd, quality-score, clinical-scores
- **Primary language (GitHub):** Python
- **License:** MIT _(source: repo-root LICENSE file (checked 2026-10-28))_
- **Snapshot:** ★ 44 · forks 16 · upstream updated 2026-08-31 (live API 2026-10-21)
- **Clone target when vendored:** `upstream/fokhruli/STGCN-rehab` (never commit upstream code to this repo)

### 88. [GuyTevet/motion-diffusion-model](https://github.com/GuyTevet/motion-diffusion-model)

- **What it is:** MDM — Human Motion Diffusion Model; text/action-to-motion generation plus motion editing and in-betweening
- **Why it's in this catalog:** Generates a 'corrected' movement to show the patient. MUST be constrained by SKEL/OpenSim joint limits; diffusion alone can produce anatomically impossible motion. License (GitHub API, 2026-10-21): MIT.
- **Category / tier:** rehab-assessment / experimental
- **Pipeline stages:** pose, body-model
- **Tags:** mdm, diffusion, motion-editing, correction-visualization
- **Primary language (GitHub):** Python
- **License:** MIT _(source: repo-root LICENSE file (checked 2026-10-28))_
- **Snapshot:** ★ 4120 · forks 464 · upstream updated 2026-10-20 (live API 2026-10-21)
- **Clone target when vendored:** `upstream/GuyTevet/motion-diffusion-model` (never commit upstream code to this repo)

### 89. [opensim-org/opensim-moco](https://github.com/opensim-org/opensim-moco)

- **What it is:** OpenSim Moco — solve optimal control problems for musculoskeletal models with direct collocation (muscle activity for observed/corrected motion, motion prediction)
- **Why it's in this catalog:** Standalone repo is ARCHIVED; development moved into opensim-core (already catalogued). Listed so the capability is discoverable. License (GitHub API, 2026-10-21): Apache-2.0. ARCHIVED upstream (read-only).
- **Category / tier:** biomechanics / extended
- **Pipeline stages:** biomechanics, muscle-sim
- **Tags:** moco, optimal-control, opensim, muscle-activity
- **Primary language (GitHub):** C++
- **License:** Apache-2.0 _(source: repo-root LICENSE.txt file (checked 2026-10-28))_
- **Snapshot:** ★ 73 · forks 18 · upstream updated 2026-07-26 (live API 2026-10-21)
- **Clone target when vendored:** `upstream/opensim-org/opensim-moco` (never commit upstream code to this repo)

### 90. [mitkof6/OpenSimRT](https://github.com/mitkof6/OpenSimRT)

- **What it is:** OpenSimRT — real-time musculoskeletal kinematics and dynamics analysis using marker- and IMU-based solutions
- **Why it's in this catalog:** Real-time biofeedback path (e.g. gait retraining) on top of OpenSim. License (GitHub API, 2026-10-21): GPL-3.0.
- **Category / tier:** biomechanics / extended
- **Pipeline stages:** capture, biomechanics
- **Tags:** opensimrt, real-time, biofeedback, imu
- **Primary language (GitHub):** C++
- **License:** GPL-3.0 _(source: repo-root LICENSE file (checked 2026-10-28))_
- **Snapshot:** ★ 82 · forks 26 · upstream updated 2026-08-07 (live API 2026-10-21)
- **Clone target when vendored:** `upstream/mitkof6/OpenSimRT` (never commit upstream code to this repo)

### 91. [CEINMS/CEINMS](https://github.com/CEINMS/CEINMS)

- **What it is:** CEINMS — Calibrated EMG-Informed Neuromusculoskeletal Modelling Toolbox; estimates muscle forces and joint moments calibrated to the individual, OpenSim-compatible
- **Why it's in this catalog:** The muscle-personalisation layer: without EMG-informed calibration, 'underdeveloped muscle' claims are generic-model guesses. A real-time variant (CEINMS-RT) targets wearable-robot control. License (GitHub API, 2026-10-21): Apache-2.0.
- **Category / tier:** biomechanics / core
- **Pipeline stages:** biomechanics, muscle-sim
- **Tags:** ceinms, emg, personalized, muscle-force, opensim
- **Primary language (GitHub):** C++
- **License:** Apache-2.0 _(source: repo-root LICENSE.txt file (checked 2026-10-28))_
- **Snapshot:** ★ 33 · forks 12 · upstream updated 2026-08-26 (live API 2026-10-21)
- **Clone target when vendored:** `upstream/CEINMS/CEINMS` (never commit upstream code to this repo)

### 92. [sofa-framework/sofa](https://github.com/sofa-framework/sofa)

- **What it is:** SOFA — real-time multi-physics simulation with emphasis on medical simulation; FEM soft-tissue modelling
- **Why it's in this catalog:** Muscle/soft-tissue deformation layer — MuJoCo/MyoSuite muscles are line actuators and cannot show bulge/atrophy visually. License (GitHub API, 2026-10-21): LGPL-2.1.
- **Category / tier:** musculoskeletal-sim / specialized
- **Pipeline stages:** muscle-sim, visualization
- **Tags:** sofa, fem, soft-tissue, medical-simulation
- **Primary language (GitHub):** C++
- **License:** none found in repo root (checked 2026-10-28; treat as all-rights-reserved) _(source: checked repo root 2026-10-28)_
- **Snapshot:** ★ 1279 · forks 368 · upstream updated 2026-10-20 (live API 2026-10-21)
- **Clone target when vendored:** `upstream/sofa-framework/sofa` (never commit upstream code to this repo)

### 93. [naubiomech/OpenExo](https://github.com/naubiomech/OpenExo)

- **What it is:** OpenExo — open-source modular exoskeleton platform for mobility and rehabilitation research: mechanical designs, electronics, firmware, control and biofeedback schemes
- **Why it's in this catalog:** KEY hardware repo: the buildable exoskeleton base (hip/ankle/elbow configurations). License (GitHub API, 2026-10-21): NOASSERTION.
- **Category / tier:** haptics-exoskeleton / core
- **Pipeline stages:** control-rl, feedback-haptics, muscle-sim
- **Tags:** openexo, exoskeleton, hardware, modular, rehabilitation
- **Primary language (GitHub):** HTML
- **License:** LGPL (see file) _(source: repo-root LICENSE.md file (checked 2026-10-28))_
- **Snapshot:** ★ 384 · forks 97 · upstream updated 2026-10-19 (live API 2026-10-21)
- **Clone target when vendored:** `upstream/naubiomech/OpenExo` (never commit upstream code to this repo)

### 94. [neurobionics/opensourceleg](https://github.com/neurobionics/opensourceleg)

- **What it is:** Open-Source Leg — open-source SDK for developing and testing algorithms on robotic prosthesis/exoskeleton leg hardware (actuators and sensors)
- **Why it's in this catalog:** Lower-limb actuator/sensor control stack; prosthesis-first but transferable to exo legs. License (GitHub API, 2026-10-21): LGPL-2.1.
- **Category / tier:** haptics-exoskeleton / extended
- **Pipeline stages:** control-rl
- **Tags:** open-source-leg, prosthesis, actuators, sdk
- **Primary language (GitHub):** Python
- **License:** LGPL (see file) _(source: repo-root LICENSE file (checked 2026-10-28))_
- **Snapshot:** ★ 120 · forks 76 · upstream updated 2026-10-10 (live API 2026-10-21)
- **Clone target when vendored:** `upstream/neurobionics/opensourceleg` (never commit upstream code to this repo)

### 95. [senseshift/senseshift-firmware](https://github.com/senseshift/senseshift-firmware)

- **What it is:** SenseShift firmware — open-source firmware for DIY haptic-feedback devices (vest, gloves, sleeves), compatible with bHaptics and OpenGloves protocols
- **Why it's in this catalog:** The posture-cueing suit: vibrate where posture breaks. Haptic cueing is buildable today, unlike powered spinal support. License (GitHub API, 2026-10-21): GPL-3.0. pipeline/ drives it via `rehabtwin suit-bridge` (bHaptics BLE payloads; layouts parsed from devices.hpp at run time).
- **Category / tier:** haptics-exoskeleton / core
- **Pipeline stages:** feedback-haptics
- **Tags:** haptic-vest, diy, bhaptics-protocol, vibrotactile
- **Primary language (GitHub):** C++
- **License:** GPL-3.0 _(source: repo-root LICENSE file (checked 2026-10-28))_
- **Snapshot:** ★ 149 · forks 22 · upstream updated 2026-10-05 (live API 2026-10-21)
- **Clone target when vendored:** `upstream/senseshift/senseshift-firmware` (never commit upstream code to this repo)

### 96. [LucidVR/lucidgloves](https://github.com/LucidVR/lucidgloves)

- **What it is:** LucidGloves — Arduino/ESP32 DIY VR haptic gloves with force feedback, via OpenGloves
- **Why it's in this catalog:** Hand-rehab niche only; not a body/posture solution. License (GitHub API, 2026-10-21): MIT.
- **Category / tier:** haptics-exoskeleton / specialized
- **Pipeline stages:** feedback-haptics
- **Tags:** haptic-gloves, force-feedback, hands, diy
- **Primary language (GitHub):** C++
- **License:** MIT _(source: repo-root LICENSE file (checked 2026-10-28))_
- **Snapshot:** ★ 2396 · forks 288 · upstream updated 2026-10-20 (live API 2026-10-21)
- **Clone target when vendored:** `upstream/LucidVR/lucidgloves` (never commit upstream code to this repo)

### 97. [mjbots/moteus](https://github.com/mjbots/moteus)

- **What it is:** moteus — open-source brushless DC servo motor controller (firmware and PCB designs)
- **Why it's in this catalog:** Actuator controller for actual joint-support torque in an exo build. License (GitHub API, 2026-10-21): Apache-2.0.
- **Category / tier:** haptics-exoskeleton / extended
- **Pipeline stages:** control-rl, feedback-haptics
- **Tags:** moteus, bldc, servo-controller, open-hardware
- **Primary language (GitHub):** C++
- **License:** Apache-2.0 _(source: repo-root LICENSE file (checked 2026-10-28))_
- **Snapshot:** ★ 1345 · forks 405 · upstream updated 2026-10-20 (live API 2026-10-21)
- **Clone target when vendored:** `upstream/mjbots/moteus` (never commit upstream code to this repo)

### 98. [simplefoc/Arduino-FOC](https://github.com/simplefoc/Arduino-FOC)

- **What it is:** Arduino SimpleFOC — field-oriented control library for BLDC and stepper motors across Arduino/STM32/ESP32-class hardware
- **Why it's in this catalog:** Cheapest path to custom actuator control for exo prototyping. License (GitHub API, 2026-10-21): MIT.
- **Category / tier:** haptics-exoskeleton / specialized
- **Pipeline stages:** control-rl
- **Tags:** simplefoc, foc, bldc, actuator, prototyping
- **Primary language (GitHub):** C++
- **License:** MIT _(source: repo-root LICENSE file (checked 2026-10-28))_
- **Snapshot:** ★ 3074 · forks 762 · upstream updated 2026-10-20 (live API 2026-10-21)
- **Clone target when vendored:** `upstream/simplefoc/Arduino-FOC` (never commit upstream code to this repo)

### 99. [wasserth/TotalSegmentator](https://github.com/wasserth/TotalSegmentator)

- **What it is:** Tool for robust segmentation of >100 important anatomical structures in CT and MR images
- **Why it's in this catalog:** Accuracy-first onboarding: patient bone/muscle/organ geometry from their own MRI/CT, replacing statistical guessing. License (GitHub API, 2026-10-21): Apache-2.0.
- **Category / tier:** medical-imaging / core
- **Pipeline stages:** body-model, skeleton
- **Tags:** totalsegmentator, ct, mri, segmentation, anatomy
- **Primary language (GitHub):** Python
- **License:** Apache-2.0 _(source: repo-root LICENSE file (checked 2026-10-28))_
- **Snapshot:** ★ 3074 · forks 490 · upstream updated 2026-10-20 (live API 2026-10-21)
- **Clone target when vendored:** `upstream/wasserth/TotalSegmentator` (never commit upstream code to this repo)

### 100. [MIC-DKFZ/nnUNet](https://github.com/MIC-DKFZ/nnUNet)

- **What it is:** nnU-Net — self-configuring biomedical image segmentation framework (the segmentation engine behind TotalSegmentator)
- **Why it's in this catalog:** Train custom bone/muscle segmentation when TotalSegmentator classes are not specific enough. License (GitHub API, 2026-10-21): Apache-2.0.
- **Category / tier:** medical-imaging / extended
- **Pipeline stages:** body-model, tooling
- **Tags:** nnunet, segmentation, medical-imaging, training
- **Primary language (GitHub):** Python
- **License:** Apache-2.0 _(source: repo-root LICENSE file (checked 2026-10-28))_
- **Snapshot:** ★ 8978 · forks 2503 · upstream updated 2026-10-20 (live API 2026-10-21)
- **Clone target when vendored:** `upstream/MIC-DKFZ/nnUNet` (never commit upstream code to this repo)

### 101. [Slicer/Slicer](https://github.com/Slicer/Slicer)

- **What it is:** 3D Slicer — free open-source platform for medical image visualisation, DICOM handling, segmentation, registration and quantification
- **Why it's in this catalog:** Clinician workstation to inspect/correct segmentations and landmarks before they enter the twin. Accuracy gate, not optional tooling. License (GitHub API, 2026-10-21): NOASSERTION.
- **Category / tier:** medical-imaging / core
- **Pipeline stages:** body-model, visualization, tooling
- **Tags:** 3d-slicer, dicom, segmentation, medical-imaging
- **Primary language (GitHub):** C++
- **License:** GPL (see file) _(source: repo-root License.txt file (checked 2026-10-28))_
- **Snapshot:** ★ 2674 · forks 799 · upstream updated 2026-10-20 (live API 2026-10-21)
- **Clone target when vendored:** `upstream/Slicer/Slicer` (never commit upstream code to this repo)

### 102. [unibas-gravis/scalismo](https://github.com/unibas-gravis/scalismo)

- **What it is:** Scalismo — library for statistical shape modelling and model-based image analysis
- **Why it's in this catalog:** Reconstruct full bone shapes from sparse landmarks/imaging when a full MRI/CT is unavailable. License (GitHub API, 2026-10-21): Apache-2.0.
- **Category / tier:** medical-imaging / specialized
- **Pipeline stages:** body-model, skeleton
- **Tags:** scalismo, statistical-shape-model, bone, scala
- **Primary language (GitHub):** Scala
- **License:** Apache-2.0 _(source: repo-root LICENSE file (checked 2026-10-28))_
- **Snapshot:** ★ 269 · forks 66 · upstream updated 2026-10-17 (live API 2026-10-21)
- **Clone target when vendored:** `upstream/unibas-gravis/scalismo` (never commit upstream code to this repo)

### 103. [PatrikMrnka/msk-PIPE](https://github.com/PatrikMrnka/msk-PIPE)

- **What it is:** Automated pipeline generating personalised musculoskeletal models from medical images: CT/MRI -> segmentation -> OpenSim model with muscle attachments and wrapping
- **Why it's in this catalog:** End-to-end patient-specific OpenSim generation (uses MSK-STAPLE, already catalogued). New/small project — audit before depending on it. License: not declared in GitHub API metadata (2026-10-21) — check upstream repo.
- **Category / tier:** anatomy-models / extended
- **Pipeline stages:** skeleton, biomechanics, muscle-sim
- **Tags:** msk-pipe, personalised, opensim, ct, mri, muscle-attachments
- **Primary language (GitHub):** Python
- **License:** none found in repo root (checked 2026-10-28; treat as all-rights-reserved) _(source: checked repo root 2026-10-28)_
- **Snapshot:** ★ 2 · forks 0 · upstream updated 2026-10-11 (live API 2026-10-21)
- **Clone target when vendored:** `upstream/PatrikMrnka/msk-PIPE` (never commit upstream code to this repo)

### 104. [katya-stanzy/thin-plate-spline_personalised_muscoloskeletal_model](https://github.com/katya-stanzy/thin-plate-spline_personalised_muscoloskeletal_model)

- **What it is:** MRI-based workflow for personalised musculoskeletal models: subject-specific joint centres and muscle paths via thin-plate-spline mapping (3D Slicer + OpenSim)
- **Why it's in this catalog:** Evidence-driven alternative to generic scaling; published comparison shows generic scaling can misplace e.g. the knee centre by centimetres. License: not declared in GitHub API metadata (2026-10-21) — check upstream repo.
- **Category / tier:** anatomy-models / extended
- **Pipeline stages:** skeleton, biomechanics
- **Tags:** mri, personalised, joint-centres, thin-plate-spline, opensim
- **Primary language (GitHub):** Jupyter Notebook
- **License:** none found in repo root (checked 2026-10-28; treat as all-rights-reserved) _(source: checked repo root 2026-10-28)_
- **Snapshot:** ★ 10 · forks 0 · upstream updated 2026-09-04 (live API 2026-10-21)
- **Clone target when vendored:** `upstream/katya-stanzy/thin-plate-spline_personalised_muscoloskeletal_model` (never commit upstream code to this repo)

### 105. [realsenseai/librealsense](https://github.com/realsenseai/librealsense)

- **What it is:** RealSense SDK 2.0 (librealsense) — official cross-platform driver/library for RealSense depth cameras including the D455; includes pyrealsense2 and ROS wrappers
- **Why it's in this catalog:** Selected-hardware driver (optional RealSense D455 — see docs/hardware.md). Depth is stereo with on-device calibration; use rs-align for RGB-depth alignment and record hardware timestamps for LSL sync. License (GitHub API, 2026-10-21): Apache-2.0.
- **Category / tier:** data-capture / core
- **Pipeline stages:** capture, tooling
- **Tags:** realsense, d455, depth-camera, sdk, rgbd
- **Primary language (GitHub):** C++
- **License:** Apache-2.0 _(source: repo-root LICENSE file (checked 2026-10-28))_
- **Snapshot:** ★ 9060 · forks 5044 · upstream updated 2026-10-20 (live API 2026-10-21)
- **Clone target when vendored:** `upstream/realsenseai/librealsense` (never commit upstream code to this repo)

### 106. [ethz-asl/kalibr](https://github.com/ethz-asl/kalibr)

- **What it is:** Kalibr — visual-inertial calibration toolbox for cameras and IMUs
- **Why it's in this catalog:** Extrinsic/intrinsic calibration for the selected hardware (cameras + D455 IMU). Accuracy of everything downstream is bounded by this step. License (GitHub API, 2026-10-21): NOASSERTION.
- **Category / tier:** data-capture / specialized
- **Pipeline stages:** capture, tooling
- **Tags:** kalibr, calibration, camera-imu, visual-inertial
- **Primary language (GitHub):** C++
- **License:** BSD-3-Clause _(source: repo-root LICENSE file (checked 2026-10-28))_
- **Snapshot:** ★ 5770 · forks 1617 · upstream updated 2026-10-20 (live API 2026-10-21)
- **Clone target when vendored:** `upstream/ethz-asl/kalibr` (never commit upstream code to this repo)

### 107. [AprilRobotics/apriltag](https://github.com/AprilRobotics/apriltag)

- **What it is:** AprilTag — visual fiducial marker system for robotics (pose of tagged objects from camera images)
- **Why it's in this catalog:** Known-geometry fiducials for extrinsic calibration checks and validation-rig ground truth (docs/validation-protocol.md). License (GitHub API, 2026-10-21): NOASSERTION.
- **Category / tier:** data-capture / specialized
- **Pipeline stages:** capture, tooling
- **Tags:** apriltag, fiducial, calibration, ground-truth
- **Primary language (GitHub):** C
- **License:** BSD-2-Clause _(source: repo-root LICENSE.md file (checked 2026-10-28))_
- **Snapshot:** ★ 2578 · forks 684 · upstream updated 2026-10-20 (live API 2026-10-21)
- **Clone target when vendored:** `upstream/AprilRobotics/apriltag` (never commit upstream code to this repo)

### 108. [alicevision/Meshroom](https://github.com/alicevision/Meshroom)

- **What it is:** Meshroom — node-based photogrammetry toolbox (AliceVision) for 3D reconstruction from photos
- **Why it's in this catalog:** Higher-resolution static surface reconstruction from the RGB cameras than iPhone LiDAR; subject must hold still — breathing/movement is the accuracy limit. License (GitHub API, 2026-10-21): NOASSERTION.
- **Category / tier:** 3d-reconstruction / extended
- **Pipeline stages:** capture, body-model
- **Tags:** meshroom, photogrammetry, alicevision, surface-reconstruction
- **Primary language (GitHub):** Python
- **License:** none found in repo root (checked 2026-10-28; treat as all-rights-reserved) _(source: checked repo root 2026-10-28)_
- **Snapshot:** ★ 13028 · forks 1235 · upstream updated 2026-10-20 (live API 2026-10-21)
- **Clone target when vendored:** `upstream/alicevision/Meshroom` (never commit upstream code to this repo)

### 109. [IDEA-Research/Motion-X](https://github.com/IDEA-Research/Motion-X)

- **What it is:** Motion-X (NeurIPS 2023) - large-scale 3D expressive whole-body human motion dataset: 81.1K clips / ~144 h of SMPL-X whole-body poses (body, hands, face) with text annotations, built from online video plus eight existing datasets
- **Why it's in this catalog:** Video-derived SMPL-X motion corpus for motion priors and tracker stress-testing. Pseudo-labelled, so never accuracy ground truth; non-commercial research licence with per-source terms - audit before any product use.
- **Category / tier:** datasets-interaction / specialized
- **Pipeline stages:** dataset, pose
- **Tags:** motion-x, smpl-x, dataset, text-to-motion
- **Primary language (GitHub):** Python
- **License:** NOASSERTION - non-commercial scientific research purposes only (repo LICENSE) _(source: repo-root LICENSE file + GitHub API NOASSERTION (checked 2026-10-28))_
- **Snapshot:** ★ 905 · forks 25 · upstream updated 2026-10-28 (live API 2026-10-28)
- **Clone target when vendored:** `upstream/IDEA-Research/Motion-X` (never commit upstream code to this repo)

### 110. [li-ronghui/LODGE](https://github.com/li-ronghui/LODGE)

- **What it is:** LODGE (CVPR 2024) - coarse-to-fine diffusion network for long music-driven dance generation guided by characteristic dance primitives
- **Why it's in this catalog:** Dance-generation reference for clinician-constrained 'corrected movement' drafts only - generation, not measurement; output must pass SKEL/OpenSim joint limits before display. No root licence file found: treat code as all-rights-reserved until cleared.
- **Category / tier:** rehab-assessment / experimental
- **Pipeline stages:** pose, body-model
- **Tags:** lodge, dance-generation, diffusion, music-to-dance
- **Primary language (GitHub):** Python
- **License:** none found in repo root (checked 2026-10-28; treat as all-rights-reserved) _(source: checked repo root 2026-10-28)_
- **Snapshot:** ★ 178 · forks 21 · upstream updated 2026-09-09 (live API 2026-10-28)
- **Clone target when vendored:** `upstream/li-ronghui/LODGE` (never commit upstream code to this repo)

### 111. [NetEase-GameAI/ChoreoMaster](https://github.com/NetEase-GameAI/ChoreoMaster)

- **What it is:** ChoreoMaster (ACM TOG 2021) - choreography-oriented, music-driven dance synthesis dataset and code (FBX motion units + music + labels); only ~1.48 h of the 9.91 h corpus is public
- **Why it's in this catalog:** True-mocap dance material for movement-library/prior work; the public subset is copyright-free, the wider corpus is non-commercial. GitHub reports no primary language (checked 2026-10-28).
- **Category / tier:** datasets-interaction / specialized
- **Pipeline stages:** dataset, pose
- **Tags:** choreomaster, dance, mocap, music-driven
- **Primary language (GitHub):** none reported
- **License:** none found in repo root (checked 2026-10-28; treat as all-rights-reserved) _(source: checked repo root 2026-10-28)_
- **Snapshot:** ★ 120 · forks 10 · upstream updated 2026-05-17 (live API 2026-10-28)
- **Clone target when vendored:** `upstream/NetEase-GameAI/ChoreoMaster` (never commit upstream code to this repo)

### 112. [simonalexanderson/MotoricaDanceDataset](https://github.com/simonalexanderson/MotoricaDanceDataset)

- **What it is:** Motorica Dance Dataset - 6 h of OptiTrack motion capture (17 cameras, 120 fps) across 8 dance styles; BVH plus retargeted skeletons, finger capture in some sessions, paired audio
- **Why it's in this catalog:** One of the few true-mocap (not video-reconstructed) dance corpora - candidate prior/stress-test data close to ground truth. Commercial copyright terms; licence audit mandatory before any product use.
- **Category / tier:** datasets-interaction / specialized
- **Pipeline stages:** dataset, pose
- **Tags:** motorica, dance, mocap, optitrack
- **Primary language (GitHub):** Python
- **License:** NOASSERTION - custom Motorica AB copyright terms (LICENSE.txt; not an open-source licence) _(source: repo-root LICENSE.txt file (checked 2026-10-28))_
- **Snapshot:** ★ 113 · forks 8 · upstream updated 2026-09-23 (live API 2026-10-28)
- **Clone target when vendored:** `upstream/simonalexanderson/MotoricaDanceDataset` (never commit upstream code to this repo)

### 113. [Lars-DHondt-KUL/3dpredictsim](https://github.com/Lars-DHondt-KUL/3dpredictsim)

- **What it is:** Framework generating 3D muscle-driven predictive simulations of human movement via direct collocation and algorithmic differentiation (KU Leuven); hosts the four-segment foot model with longitudinal arch used for predictive gait simulations
- **Why it's in this catalog:** Predictive-simulation framework behind the 4-segment arch foot adopted in docs/research-detailed-anatomy-models.md. Research code with a very small community - pin commits and validate before use.
- **Category / tier:** musculoskeletal-sim / extended
- **Pipeline stages:** biomechanics, muscle-sim
- **Tags:** predictive-simulation, opensim, foot-model, direct-collocation, gait
- **Primary language (GitHub):** C++
- **License:** MIT _(source: GitHub API (live 2026-10-28))_
- **Snapshot:** ★ 4 · forks 3 · upstream updated 2025-07-17 (live API 2026-10-28)
- **Clone target when vendored:** `upstream/Lars-DHondt-KUL/3dpredictsim` (never commit upstream code to this repo)

### 114. [MicheleConconi/Synergy-Based-Foot-Model](https://github.com/MicheleConconi/Synergy-Based-Foot-Model)

- **What it is:** Multi-body foot model tracking the spatial kinematics of all foot bones with only 5 DOF, exploiting experimentally derived bone-motion coupling (synergies) measured from weight-bearing CT
- **Why it's in this catalog:** Source model for the synergy-based arch foot recommended in docs/research-detailed-anatomy-models.md (arch as an explicit DOF). The referenced OpenSim port did not resolve on GitHub at check time - verify before planning on it. No root licence file: all-rights-reserved until cleared.
- **Category / tier:** anatomy-models / specialized
- **Pipeline stages:** skeleton, biomechanics
- **Tags:** foot, synergy, arch, weight-bearing-ct, multi-body
- **Primary language (GitHub):** MATLAB
- **License:** none found in repo root (checked 2026-10-28; treat as all-rights-reserved) _(source: checked repo root 2026-10-28)_
- **Snapshot:** ★ 0 · forks 0 · upstream updated 2026-04-09 (live API 2026-10-28)
- **Clone target when vendored:** `upstream/MicheleConconi/Synergy-Based-Foot-Model` (never commit upstream code to this repo)

### 115. [OllieBoyne/Foot3D](https://github.com/OllieBoyne/Foot3D)

- **What it is:** Foot3D - dataset of scanned 3D feet behind the FIND articulated foot model; external foot-shape/scan data for fitting the digital twin's foot surface
- **Why it's in this catalog:** Surface-shape foot data only - silent about arch mechanics and fascia strain; pair with the synergy-based or four-segment models for dynamics. GitHub reports no primary language (checked 2026-10-28).
- **Category / tier:** anatomy-models / specialized
- **Pipeline stages:** body-model, dataset
- **Tags:** foot3d, foot-scans, statistical-shape, find
- **Primary language (GitHub):** none reported
- **License:** MIT _(source: GitHub API (live 2026-10-28))_
- **Snapshot:** ★ 47 · forks 2 · upstream updated 2026-09-20 (live API 2026-10-28)
- **Clone target when vendored:** `upstream/OllieBoyne/Foot3D` (never commit upstream code to this repo)

### 116. [utahmobl/opencap-monocular](https://github.com/utahmobl/opencap-monocular)

- **What it is:** OpenCap Monocular: 3D kinematics and dynamics from a single smartphone video (WHAM 3D pose, then OpenSim inverse kinematics), validated against marker mocap
- **Why it's in this catalog:** Everyday-mode front-end candidate (one phone); its walking, squat and sit-to-stand validation is the comparison in docs/validation-results.md. Non-commercial only, and it needs SMPL model files (MPI licence, non-commercial). Not wired into pipeline/ yet: needs an evaluation slot.
- **Category / tier:** pose-mocap / experimental
- **Pipeline stages:** capture, pose, biomechanics
- **Tags:** opencap, monocular, smartphone, wham, smpl
- **Primary language (GitHub):** Python
- **License:** PolyForm-Noncommercial-1.0.0 _(source: repo-root LICENSE file at e2d0b14 (checked 2026-10-28); the GitHub API says NOASSERTION, and the paper's Apache-2.0 does not match the file)_
- **Snapshot:** ★ 243 · forks 33 · upstream updated 2026-10-28 (GitHub API, fetched by the HarmannBitte session 2026-10-28)
- **Clone target when vendored:** `upstream/utahmobl/opencap-monocular` (never commit upstream code to this repo)

### 117. [davidpagnon/Sports2D](https://github.com/davidpagnon/Sports2D)

- **What it is:** Sports2D: 2D keypoint trajectories and joint and segment angles from a single video or webcam, by the author of Pose2Sim; can export OpenSim kinematics
- **Why it's in this catalog:** Monocular companion to Pose2Sim, cloned under upstream/ for reference; not called by pipeline/. Angles in the camera plane from one view, so Tier C screening at best.
- **Category / tier:** pose-mocap / extended
- **Pipeline stages:** pose, biomechanics
- **Tags:** sports2d, pose2sim, monocular, 2d-angles
- **Primary language (GitHub):** Python
- **License:** BSD-3-Clause _(source: GitHub API, fetched by the HarmannBitte session 2026-10-28; matches the repo-root LICENSE file)_
- **Snapshot:** ★ 336 · forks 46 · upstream updated 2026-10-28 (GitHub API, fetched by the HarmannBitte session 2026-10-28)
- **Clone target when vendored:** `upstream/davidpagnon/Sports2D` (never commit upstream code to this repo)
