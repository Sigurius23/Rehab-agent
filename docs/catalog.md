# Full catalog — all 110 repositories

Generated from `catalog/repos.json` by `scripts/generate_catalog.py`. Do not hand-edit this file; edit the JSON and regenerate.

Stars/forks/updated are the maintainer's pasted snapshot, **not live data**.

## body-models — Parametric body & skeleton models (SMPL/SMPL-X, SKEL, OSSO, tissues) (10)

| # | Repository | Tier | Stages | Lang | ★ snapshot | Description |
|---:|---|---|---|---|---:|---|
| 2 | [vchoutas/smplx](https://github.com/vchoutas/smplx) | core | body-model | Python | 2738 | SMPL-X: expressive parametric human body model (body, hands, face) |
| 4 | [MarilynKeller/OSSO](https://github.com/MarilynKeller/OSSO) | core | body-model, skeleton | Python | 238 | From a body shape, infer the anatomic skeleton |
| 5 | [MarilynKeller/SKEL](https://github.com/MarilynKeller/SKEL) | core | body-model, skeleton, biomechanics | Python | 370 | SKEL — From Skin to Skeleton: biomechanically accurate 3D digital humans (SIGGRAPH Asia 2023) |
| 6 | [ahmedosman/SUPR](https://github.com/ahmedosman/SUPR) | extended | body-model | Python | 184 | SUPR: A Sparse Unified Part-Based Human Representation (ECCV 2022) |
| 10 | [open-mmlab/mmhuman3d](https://github.com/open-mmlab/mmhuman3d) | extended | body-model, pose, tooling | Python | 1430 | OpenMMLab 3D Human Parametric Model Toolbox and Benchmark |
| 21 | [MarilynKeller/HIT](https://github.com/MarilynKeller/HIT) | extended | body-model, skeleton | Python | 102 | HIT: Estimating Internal Human Implicit Tissues from the Body Surface (2024) |
| 24 | [ahmedosman/STAR](https://github.com/ahmedosman/STAR) | extended | body-model | Python | 727 | STAR — A Sparse Trained Articulated Human Body Regressor (ECCV 2020) |
| 60 | [hailsong/RC-SMPL](https://github.com/hailsong/RC-SMPL) | specialized | body-model, visualization | C# | 10 | RC-SMPL — Real-time Cumulative SMPL-based Avatar Body Generation (IEEE ISMAR 2023); cumulatively updates avatar texture and normal maps from images/video in real time |
| 71 | [muelea/shapy](https://github.com/muelea/shapy) | core | body-model | Python | 389 | SHAPY — accurate 3D body shape regression using metric and semantic attributes; predicts SMPL-X shape plus height/weight/chest/waist/hip measurements from an image |
| 73 | [yfeng95/PIXIE](https://github.com/yfeng95/PIXIE) | extended | body-model | Python | 517 | PIXIE — collaborative regression of expressive bodies: whole-body SMPL-X with detailed face and hand articulation from a single image |

## anatomy-models — Anatomy & personalised model generation (7)

| # | Repository | Tier | Stages | Lang | ★ snapshot | Description |
|---:|---|---|---|---|---:|---|
| 1 | [Kevin-Mattheus-Moerman/BodyParts3D](https://github.com/Kevin-Mattheus-Moerman/BodyParts3D) | extended | body-model, visualization | HTML | 176 | Clone of the BodyParts3D / Anatomography 3D model files |
| 3 | [Z-Anatomy/Models-of-human-anatomy](https://github.com/Z-Anatomy/Models-of-human-anatomy) | extended | body-model, visualization | Python | 255 | Human male anatomy model |
| 11 | [makehumancommunity/mpfb2](https://github.com/makehumancommunity/mpfb2) | specialized | body-model, visualization | Python | 648 | MPFB2 — free and open source human generator for Blender |
| 39 | [modenaxe/msk-STAPLE](https://github.com/modenaxe/msk-STAPLE) | specialized | skeleton, body-model | MATLAB | 65 | STAPLE — Shared Tools for Automatic Personalised Lower Extremity modelling: generating skeletal models from 3D bone geometries |
| 47 | [LNSGroup/MS-Human-700](https://github.com/LNSGroup/MS-Human-700) | specialized | muscle-sim, body-model | — | 51 | MS-Human-700: Whole-body Human MusculoSkeletal Model |
| 103 | [PatrikMrnka/msk-PIPE](https://github.com/PatrikMrnka/msk-PIPE) | extended | skeleton, biomechanics, muscle-sim | Python | 2 | Automated pipeline generating personalised musculoskeletal models from medical images: CT/MRI -> segmentation -> OpenSim model with muscle attachments and wrapping |
| 104 | [katya-stanzy/thin-plate-spline_personalised_muscoloskeletal_model](https://github.com/katya-stanzy/thin-plate-spline_personalised_muscoloskeletal_model) | extended | skeleton, biomechanics | Jupyter Notebook | 10 | MRI-based workflow for personalised musculoskeletal models: subject-specific joint centres and muscle paths via thin-plate-spline mapping (3D Slicer + OpenSim) |

## pose-mocap — Pose estimation & motion capture (video, markerless, IMU) (23)

| # | Repository | Tier | Stages | Lang | ★ snapshot | Description |
|---:|---|---|---|---|---:|---|
| 8 | [opencap-org/opencap-core](https://github.com/opencap-org/opencap-core) | core | capture, pose, biomechanics | Python | 374 | Main OpenCap processing pipeline — markerless motion capture from smartphones |
| 13 | [Sigurius23/Dynamic-AI-Driven-Anatomical-Pose-Transfer-DAAPT-](https://github.com/Sigurius23/Dynamic-AI-Driven-Anatomical-Pose-Transfer-DAAPT-) 🔒 | private | pose, body-model | — | 1 | Dynamic AI-Driven Anatomical Pose Transfer (DAAPT) |
| 14 | [cuevhv/mamma](https://github.com/cuevhv/mamma) | extended | capture, pose | Python | 839 | MAMMA: Markerless Accurate Multi-person Motion Acquisition |
| 19 | [NTUYWANG103/ViDiHand](https://github.com/NTUYWANG103/ViDiHand) | specialized | pose | — | 193 | Official PyTorch implementation: The Surprising Effectiveness of Video Diffusion Models for Hand Motion Reconstruction |
| 28 | [IsshikiHugh/HSMR](https://github.com/IsshikiHugh/HSMR) | core | pose, skeleton | Python | 634 | Reconstructing Humans with a Biomechanically Accurate Skeleton (CVPR 2025 Oral) |
| 29 | [Intellindust-AI-Lab/SKEL-CF](https://github.com/Intellindust-AI-Lab/SKEL-CF) | experimental | pose, skeleton, body-model | Jupyter Notebook | 82 | SKEL-CF: Coarse-to-Fine Biomechanical Skeleton and Surface Mesh Recovery |
| 35 | [perfanalytics/pose2sim](https://github.com/perfanalytics/pose2sim) | core | capture, pose, biomechanics | Python | 852 | Markerless kinematics with any cameras — from 2D pose estimation to 3D OpenSim motion |
| 36 | [vchoutas/smplify-x](https://github.com/vchoutas/smplify-x) | core | pose, body-model | Python | 2182 | Expressive Body Capture: 3D Hands, Face, and Body from a Single Image (SMPLify-X) |
| 59 | [mohamedhassanmus/prox](https://github.com/mohamedhassanmus/prox) | specialized | pose, body-model | Python | 232 | PROX: Resolving 3D Human Pose Ambiguities with 3D Scene Constraints |
| 63 | [Xinyu-Yi/TransPose](https://github.com/Xinyu-Yi/TransPose) | core | capture, pose | Python | 456 | TransPose — real-time motion capture that estimates poses and global translations using only 6 IMUs |
| 64 | [Xinyu-Yi/PIP](https://github.com/Xinyu-Yi/PIP) | core | capture, pose, biomechanics | Python | 369 | PIP — real-time system that captures physically correct human motion, joint torques, and ground reaction forces with only 6 IMUs |
| 65 | [Xinyu-Yi/PNP](https://github.com/Xinyu-Yi/PNP) | extended | capture, pose, biomechanics | Python | 137 | PNP — real-time human motion capture based on 6 IMUs, upgrading PIP through non-inertial forces |
| 68 | [freemocap/freemocap](https://github.com/freemocap/freemocap) | core | capture, pose | TypeScript | 10474 | FreeMoCap — Free Motion Capture for Everyone |
| 74 | [google-ai-edge/mediapipe](https://github.com/google-ai-edge/mediapipe) | core | capture, pose | C++ | 37345 | MediaPipe — cross-platform ML perception pipelines; Pose infers 33 3D body landmarks in real time on phone, desktop and web |
| 75 | [open-mmlab/mmpose](https://github.com/open-mmlab/mmpose) | core | pose | Python | 7967 | MMPose — OpenMMLab pose estimation toolbox and benchmark, including the RTMPose real-time model family |
| 76 | [zju3dv/GVHMR](https://github.com/zju3dv/GVHMR) | core | pose, body-model | Jupyter Notebook | 2161 | GVHMR — world-grounded human motion recovery via gravity-view coordinates; SMPL motion in camera and world frames from monocular video |
| 77 | [zju3dv/EasyMocap](https://github.com/zju3dv/EasyMocap) | extended | capture, pose, body-model | Python | 4929 | EasyMocap — multi-view and monocular SMPL/SMPL-X/MANO motion capture toolkit |
| 78 | [facebookresearch/sapiens](https://github.com/facebookresearch/sapiens) | extended | capture, pose | Python | 5432 | Sapiens — high-resolution foundation models for human-centric vision: 2D pose, body-part segmentation, depth and normals |
| 79 | [facebookresearch/sapiens2](https://github.com/facebookresearch/sapiens2) | experimental | capture, pose | Python | 998 | Sapiens2 — 1K-resolution human vision transformers pretrained on 1B human images; pose, segmentation, normals, pointmaps, matting |
| 83 | [DeepLabCut/DeepLabCut](https://github.com/DeepLabCut/DeepLabCut) | specialized | pose, tooling | Python | 5795 | DeepLabCut — markerless pose estimation of user-defined features with deep learning (animals incl. humans) |
| 84 | [DeepLabCut/DeepLabCut-live](https://github.com/DeepLabCut/DeepLabCut-live) | specialized | capture, pose | Python | 239 | DeepLabCut-Live — SDK for running DeepLabCut models on a live video stream |
| 109 | [utahmobl/opencap-monocular](https://github.com/utahmobl/opencap-monocular) | core | pose, body-model, biomechanics | Python | — | OpenCap Monocular — 3D human kinematics and musculoskeletal dynamics from a single smartphone video (WHAM pose, camera/pose optimisation, OpenSim IK and export) |
| 110 | [davidpagnon/Sports2D](https://github.com/davidpagnon/Sports2D) | extended | pose, biomechanics | Python | — | Sports2D — joint and segment angles from a single video (RTMPose), with optional OpenSim inverse kinematics |

## biomechanics — Biomechanics engines & OpenSim pipeline (13)

| # | Repository | Tier | Stages | Lang | ★ snapshot | Description |
|---:|---|---|---|---|---:|---|
| 9 | [opencap-org/opencap-processing](https://github.com/opencap-org/opencap-processing) | core | biomechanics, tooling | Python | 158 | Utilities for processing OpenCap data |
| 22 | [MarilynKeller/SMPL2AddBiomechanics](https://github.com/MarilynKeller/SMPL2AddBiomechanics) | core | skeleton, biomechanics, tooling | Python | 157 | Enable inputting a SMPL sequence into AddBiomechanics to fit an OpenSim skeleton model to the sequence |
| 26 | [MyoHub/myoconverter](https://github.com/MyoHub/myoconverter) | core | biomechanics, muscle-sim, tooling | Python | 129 | Convert OpenSim 4.0+ MSK models into MuJoCo format with optimized muscle kinematics and kinetics |
| 32 | [opensim-org/opensim-core](https://github.com/opensim-org/opensim-core) | core | biomechanics, muscle-sim | C++ | 1132 | SimTK OpenSim C++ libraries and command-line applications, with Java/Python wrapping |
| 33 | [keenon/nimblephysics](https://github.com/keenon/nimblephysics) | extended | biomechanics, muscle-sim | C++ | 496 | Nimble: Physics Engine for Biomechanics and Deep Learning |
| 34 | [keenon/AddBiomechanics](https://github.com/keenon/AddBiomechanics) | core | biomechanics, tooling | TypeScript | 67 | A tool to automatically process and share biomechanics data |
| 38 | [pyomeca/biobuddy](https://github.com/pyomeca/biobuddy) | specialized | body-model, biomechanics, tooling | Python | 15 | A generic interface to generate a virtual buddy (biomechanical models) |
| 50 | [stanfordnmbl/GaitDynamics](https://github.com/stanfordnmbl/GaitDynamics) | extended | biomechanics | Python | 132 | Gait dynamics tools (Stanford NMBL) |
| 62 | [dfki-av/simspine](https://github.com/dfki-av/simspine) | experimental | skeleton, biomechanics | Python | 13 | SIMSPINE: A Biomechanics-Aware Simulation Framework for 3D Spine Motion Annotation and Benchmarking |
| 67 | [jerela/OpenSimLive](https://github.com/jerela/OpenSimLive) | specialized | capture, biomechanics | C++ | 30 | Live inverse kinematics based on IMU orientations using OpenSim 4.1 API |
| 89 | [opensim-org/opensim-moco](https://github.com/opensim-org/opensim-moco) | extended | biomechanics, muscle-sim | C++ | 73 | OpenSim Moco — solve optimal control problems for musculoskeletal models with direct collocation (muscle activity for observed/corrected motion, motion prediction) |
| 90 | [mitkof6/OpenSimRT](https://github.com/mitkof6/OpenSimRT) | extended | capture, biomechanics | C++ | 82 | OpenSimRT — real-time musculoskeletal kinematics and dynamics analysis using marker- and IMU-based solutions |
| 91 | [CEINMS/CEINMS](https://github.com/CEINMS/CEINMS) | core | biomechanics, muscle-sim | C++ | 33 | CEINMS — Calibrated EMG-Informed Neuromusculoskeletal Modelling Toolbox; estimates muscle forces and joint moments calibrated to the individual, OpenSim-compatible |

## musculoskeletal-sim — Musculoskeletal simulation, humanoid control & RL (12)

| # | Repository | Tier | Stages | Lang | ★ snapshot | Description |
|---:|---|---|---|---|---:|---|
| 20 | [MyoHub/myosuite](https://github.com/MyoHub/myosuite) | core | muscle-sim, control-rl | Python | 1260 | MyoSuite — musculoskeletal environments/tasks in MuJoCo, wrapped in the Gym API |
| 25 | [MyoHub/myo_sim](https://github.com/MyoHub/myo_sim) | core | muscle-sim | Python | 211 | Musculoskeletal models in MuJoCo |
| 30 | [ZhengyiLuo/SMPLSim](https://github.com/ZhengyiLuo/SMPLSim) | extended | muscle-sim, control-rl | — | — | Simulating SMPL humanoid, supporting PHC / PHC-MJX / PULSE / SimXR code bases |
| 31 | [ZhengyiLuo/PHC](https://github.com/ZhengyiLuo/PHC) | extended | control-rl, muscle-sim | Python | 1305 | Perpetual Humanoid Control for Real-time Simulated Avatars (ICCV 2023) |
| 40 | [tgeijten/scone-core](https://github.com/tgeijten/scone-core) | extended | biomechanics, muscle-sim | C++ | 62 | SCONE core — software for performing predictive simulations of biological motion |
| 42 | [tgeijten/sconegym](https://github.com/tgeijten/sconegym) | extended | control-rl, muscle-sim | Python | 50 | Gym environments for SCONE |
| 43 | [tgeijten/depRL](https://github.com/tgeijten/depRL) | specialized | control-rl, muscle-sim | Python | 3 | DEP-RL: Embodied Exploration for Reinforcement Learning in Overactuated and Musculoskeletal Systems (ICLR 2023) |
| 44 | [amathislab/musclemimic](https://github.com/amathislab/musclemimic) | extended | muscle-sim, control-rl | Python | 353 | Towards Embodied AI with MuscleMimic: Unlocking full-body musculoskeletal motor learning at scale |
| 45 | [amathislab/musclemimic_models](https://github.com/amathislab/musclemimic_models) | extended | muscle-sim, body-model | Python | 61 | Musculoskeletal models released from MuscleMimic research: full-body musculoskeletal model |
| 46 | [robfiras/loco-mujoco](https://github.com/robfiras/loco-mujoco) | extended | control-rl, muscle-sim | Python | 1474 | Imitation learning benchmark focusing on complex locomotion tasks using MuJoCo |
| 54 | [lsw9021/MASS](https://github.com/lsw9021/MASS) | specialized | muscle-sim, control-rl | Mathematica | 638 | MASS (Muscle-Actuated Skeletal System) — simulation and control of a full-body musculoskeletal system driven by muscle activations, with Python/PyTorch deep-RL interfacing (SIGGRAPH 2019) |
| 92 | [sofa-framework/sofa](https://github.com/sofa-framework/sofa) | specialized | muscle-sim, visualization | C++ | 1279 | SOFA — real-time multi-physics simulation with emphasis on medical simulation; FEM soft-tissue modelling |

## visualization-tools — Visualization, viewers & editing tools (8)

| # | Repository | Tier | Stages | Lang | ★ snapshot | Description |
|---:|---|---|---|---|---:|---|
| 7 | [PashavanBijlert/MuSkeMo](https://github.com/PashavanBijlert/MuSkeMo) | specialized | visualization, biomechanics | TeX | 71 | Build and visualize musculoskeletal models in Blender |
| 12 | [ZhUyU1997/open-pose-editor](https://github.com/ZhUyU1997/open-pose-editor) | specialized | visualization, tooling | TypeScript | 959 | Online 3D OpenPose editor for Stable Diffusion and ControlNet |
| 23 | [MarilynKeller/aitviewer-skel](https://github.com/MarilynKeller/aitviewer-skel) | core | visualization | Python | 80 | aitviewer fork supporting visualization of OpenSim models and SKEL |
| 27 | [opencap-org/opencap-viewer](https://github.com/opencap-org/opencap-viewer) | extended | visualization | JavaScript | 11 | OpenCap viewer |
| 37 | [eth-ait/aitviewer](https://github.com/eth-ait/aitviewer) | core | visualization | Python | 756 | A set of tools to visualize and interact with sequences of 3D data |
| 41 | [tgeijten/scone-studio](https://github.com/tgeijten/scone-studio) | extended | visualization, biomechanics | C++ | 46 | SCONE Studio — graphical user interface for SCONE |
| 58 | [strayrobots/3d-annotation-tool](https://github.com/strayrobots/3d-annotation-tool) | specialized | visualization, tooling | C++ | 94 | A graphical user interface to annotate point clouds and 3D data |
| 85 | [sangho0n/Realtime_SMPLX_Unity](https://github.com/sangho0n/Realtime_SMPLX_Unity) | specialized | visualization, body-model | C# | 50 | Real-time SMPL-X in Unity — shape reconstruction via a Python server plus MediaPipe pose in Unity, animating SMPL-X live |

## data-capture — RGB-D / sensor capture (8)

| # | Repository | Tier | Stages | Lang | ★ snapshot | Description |
|---:|---|---|---|---|---:|---|
| 51 | [marek-simonik/record3d](https://github.com/marek-simonik/record3d) | specialized | capture | C | 493 | Record3D iOS app library — receive RGBD stream from iOS devices with TrueDepth cameras |
| 57 | [strayrobots/scanner](https://github.com/strayrobots/scanner) | specialized | capture | C++ | 155 | An app for collecting raw RGB-D scans on iOS devices |
| 80 | [SlimeVR/SlimeVR-Server](https://github.com/SlimeVR/SlimeVR-Server) | core | capture, pose | Fluent | 1047 | SlimeVR Server — server for the SlimeVR open full-body tracking ecosystem; fuses IMU trackers into a full-body pose |
| 81 | [SlimeVR/SlimeVR-Tracker-ESP](https://github.com/SlimeVR/SlimeVR-Tracker-ESP) | core | capture | C++ | 1088 | SlimeVR Tracker firmware for ESP32/ESP8266 and various IMUs — DIY open-hardware body trackers |
| 82 | [sccn/labstreaminglayer](https://github.com/sccn/labstreaminglayer) | core | capture, tooling | HTML | 788 | Lab Streaming Layer (LSL) — multimodal time-synchronised data transmission and recording (liblsl, pylsl, LabRecorder/XDF ecosystem) |
| 105 | [realsenseai/librealsense](https://github.com/realsenseai/librealsense) | core | capture, tooling | C++ | 9060 | RealSense SDK 2.0 (librealsense) — official cross-platform driver/library for RealSense depth cameras including the D455; includes pyrealsense2 and ROS wrappers |
| 106 | [ethz-asl/kalibr](https://github.com/ethz-asl/kalibr) | specialized | capture, tooling | C++ | 5770 | Kalibr — visual-inertial calibration toolbox for cameras and IMUs |
| 107 | [AprilRobotics/apriltag](https://github.com/AprilRobotics/apriltag) | specialized | capture, tooling | C | 2578 | AprilTag — visual fiducial marker system for robotics (pose of tagged objects from camera images) |

## datasets-interaction — Datasets & human-object/scene interaction (2)

| # | Repository | Tier | Stages | Lang | ★ snapshot | Description |
|---:|---|---|---|---|---:|---|
| 61 | [xiexh20/behave-dataset](https://github.com/xiexh20/behave-dataset) | specialized | dataset, pose | Python | 193 | Code to access the BEHAVE dataset (CVPR 2022) — human-object interaction |
| 66 | [ptrvilya/echo](https://github.com/ptrvilya/echo) | experimental | pose, dataset | Python | 16 | ECHO: method for reconstructing human-object interaction from sparse ego-centric tracking |

## rehab-assistive — Rehab, gait & assistive-device specific projects (5)

| # | Repository | Tier | Stages | Lang | ★ snapshot | Description |
|---:|---|---|---|---|---:|---|
| 48 | [DaebangStn/exo-plore](https://github.com/DaebangStn/exo-plore) | specialized | control-rl, muscle-sim | C++ | 22 | EXO-PLORE: Exploring Exoskeleton Control Space through Human-Aligned Simulation (ICLR 2026) |
| 49 | [stanfordnmbl/sit2stand](https://github.com/stanfordnmbl/sit2stand) | specialized | biomechanics | HTML | 4 | Stanford NMBL sit-to-stand project (details in upstream repo) |
| 53 | [rohwalia/MyoBack](https://github.com/rohwalia/MyoBack) | specialized | muscle-sim, biomechanics | Python | 7 | MyoBack — simulation of a neuromusculoskeletal model of the back with an exoskeleton; a MyoSuite back model derived from a physiologically accurate OpenSim model, validated with a passive back exoskeleton |
| 55 | [neumovelab/myoassist](https://github.com/neumovelab/myoassist) | specialized | muscle-sim, control-rl | Jupyter Notebook | 62 | MyoAssist (assistive musculoskeletal simulation; details in upstream repo) |
| 56 | [hzm2016/mass-dart-exo](https://github.com/hzm2016/mass-dart-exo) | specialized | muscle-sim, control-rl | Mathematica | 2 | MASS/DART exoskeleton variant — upstream README presents the MASS muscle-actuated full-body skeletal simulation system; exoskeleton-specific changes are not documented in the README |

## 3d-reconstruction — 3D reconstruction, mesh generation & world models (9)

| # | Repository | Tier | Stages | Lang | ★ snapshot | Description |
|---:|---|---|---|---|---:|---|
| 15 | [MaureenZOU/worldstring](https://github.com/MaureenZOU/worldstring) | experimental | pose, dataset | [Highlight] Python | 82 | Official implementation for Actionable World Representation (worldstring) |
| 16 | [haoz19/world-tracing](https://github.com/haoz19/world-tracing) | experimental | pose, visualization | Python | 371 | Official inference code for World Tracing |
| 17 | [Andy-Cheng/Flex4DHuman](https://github.com/Andy-Cheng/Flex4DHuman) | experimental | capture, pose | — | 105 | Flex4DHuman turns monocular or sparse multi-view videos of dynamic subjects into synchronized dense multi-view videos |
| 18 | [facebookresearch/meshflow](https://github.com/facebookresearch/meshflow) | experimental | body-model, visualization | Python | 528 | MeshFlow: Efficient Artistic Mesh Generation via MeshVAE and Flow-based Diffusion Transformer (CVPR 2026) |
| 52 | [isl-org/Open3D](https://github.com/isl-org/Open3D) | core | capture, visualization, tooling | C++ | 14109 | Open3D: A Modern Library for 3D Data Processing |
| 69 | [xibushu/UniForge3D](https://github.com/xibushu/UniForge3D) | experimental | body-model | Python | 373 | UniForge3D: Joint 3D Reconstruction and Generation in a Shared Anchor-Guided Space |
| 70 | [Net-Maker/GaussiAnimate](https://github.com/Net-Maker/GaussiAnimate) | experimental | body-model, visualization | Python | 157 | GaussiAnimate: Reconstruct and Rig Animatable Categories with Level of Dynamics |
| 72 | [YuliangXiu/ECON](https://github.com/YuliangXiu/ECON) | extended | capture, body-model | Python | 1213 | ECON — explicit clothed humans optimised via normal integration; high-fidelity 3D clothed human from a single image, SMPL-X animatable |
| 108 | [alicevision/Meshroom](https://github.com/alicevision/Meshroom) | extended | capture, body-model | Python | 13028 | Meshroom — node-based photogrammetry toolbox (AliceVision) for 3D reconstruction from photos |

## rehab-assessment — Rehab exercise assessment, clinical scores & movement correction (3)

| # | Repository | Tier | Stages | Lang | ★ snapshot | Description |
|---:|---|---|---|---|---:|---|
| 86 | [avakanski/A-Deep-Learning-Framework-for-Assessing-Physical-Rehabilitation-Exercises](https://github.com/avakanski/A-Deep-Learning-Framework-for-Assessing-Physical-Rehabilitation-Exercises) | extended | dataset, pose | Jupyter Notebook | 75 | Framework for quality assessment of physical rehabilitation exercises on the UI-PRMD dataset (skeletal joint data, correct vs incorrect movements) |
| 87 | [fokhruli/STGCN-rehab](https://github.com/fokhruli/STGCN-rehab) | core | dataset, pose | Python | 44 | Graph convolutional networks for assessment of physical rehabilitation exercises (KIMORE and UI-PRMD) |
| 88 | [GuyTevet/motion-diffusion-model](https://github.com/GuyTevet/motion-diffusion-model) | experimental | pose, body-model | Python | 4120 | MDM — Human Motion Diffusion Model; text/action-to-motion generation plus motion editing and in-betweening |

## haptics-exoskeleton — Haptic feedback suits, exoskeleton hardware & actuators (6)

| # | Repository | Tier | Stages | Lang | ★ snapshot | Description |
|---:|---|---|---|---|---:|---|
| 93 | [naubiomech/OpenExo](https://github.com/naubiomech/OpenExo) | core | control-rl, feedback-haptics, muscle-sim | HTML | 384 | OpenExo — open-source modular exoskeleton platform for mobility and rehabilitation research: mechanical designs, electronics, firmware, control and biofeedback schemes |
| 94 | [neurobionics/opensourceleg](https://github.com/neurobionics/opensourceleg) | extended | control-rl | Python | 120 | Open-Source Leg — open-source SDK for developing and testing algorithms on robotic prosthesis/exoskeleton leg hardware (actuators and sensors) |
| 95 | [senseshift/senseshift-firmware](https://github.com/senseshift/senseshift-firmware) | core | feedback-haptics | C++ | 149 | SenseShift firmware — open-source firmware for DIY haptic-feedback devices (vest, gloves, sleeves), compatible with bHaptics and OpenGloves protocols |
| 96 | [LucidVR/lucidgloves](https://github.com/LucidVR/lucidgloves) | specialized | feedback-haptics | C++ | 2396 | LucidGloves — Arduino/ESP32 DIY VR haptic gloves with force feedback, via OpenGloves |
| 97 | [mjbots/moteus](https://github.com/mjbots/moteus) | extended | control-rl, feedback-haptics | C++ | 1345 | moteus — open-source brushless DC servo motor controller (firmware and PCB designs) |
| 98 | [simplefoc/Arduino-FOC](https://github.com/simplefoc/Arduino-FOC) | specialized | control-rl | C++ | 3074 | Arduino SimpleFOC — field-oriented control library for BLDC and stepper motors across Arduino/STM32/ESP32-class hardware |

## medical-imaging — Medical imaging, segmentation & patient-specific anatomy (DICOM/MRI/CT) (4)

| # | Repository | Tier | Stages | Lang | ★ snapshot | Description |
|---:|---|---|---|---|---:|---|
| 99 | [wasserth/TotalSegmentator](https://github.com/wasserth/TotalSegmentator) | core | body-model, skeleton | Python | 3074 | Tool for robust segmentation of >100 important anatomical structures in CT and MR images |
| 100 | [MIC-DKFZ/nnUNet](https://github.com/MIC-DKFZ/nnUNet) | extended | body-model, tooling | Python | 8978 | nnU-Net — self-configuring biomedical image segmentation framework (the segmentation engine behind TotalSegmentator) |
| 101 | [Slicer/Slicer](https://github.com/Slicer/Slicer) | core | body-model, visualization, tooling | C++ | 2674 | 3D Slicer — free open-source platform for medical image visualisation, DICOM handling, segmentation, registration and quantification |
| 102 | [unibas-gravis/scalismo](https://github.com/unibas-gravis/scalismo) | specialized | body-model, skeleton | Scala | 269 | Scalismo — library for statistical shape modelling and model-based image analysis |
