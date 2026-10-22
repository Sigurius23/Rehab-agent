# Stack: Accuracy-first personalised digital twin

**Design priority #1 is anatomical accuracy — see `docs/accuracy.md` for tiers,
targets and red lines. This stack implements Tier A; lower tiers must be
labelled and may not drive corrections or exoskeleton assistance.**

```
TIER-A ONBOARDING (once per person — this is what makes it a twin, not an avatar)
  MRI/CT (DICOM)
    ──► Slicer/Slicer (clinician review) 
    ──► wasserth/TotalSegmentator (+ MIC-DKFZ/nnUNet for custom structures)
    ──► patient bone/muscle meshes (unibas-gravis/scalismo if imaging is sparse)
    ──► PatrikMrnka/msk-PIPE / TPS-MRI workflow / msk-STAPLE
        ──► personalised OpenSim .osim (patient joint centres/axes, muscle attachments)
    ──► functional calibration movements + CEINMS calibration (if EMG collected)
    ──► validation report stored WITH the twin (error per accuracy layer)

LIVE TWIN (every session — solved against the Tier-A model, not a generic body)
  hardware: RGB camera(s) + iPhone LiDAR + optional RealSense D455 (docs/hardware.md)
  clinic:  multi-cam EasyMocap / Pose2Sim (+ D455 depth view) + IMU fusion
  home:    iPhone (Record3D RGB-D) and/or SlimeVR trackers ──► SlimeVR-Server
  always:  labstreaminglayer (LSL) syncs video + IMU + EMG (+ haptics) into one XDF
  front-end pose (mediapipe / mmpose / GVHMR) is an input signal only —
      final joint angles come from IK on the patient's own OpenSim model

LOWER TIERS (screening only, labelled, no corrections/exo from these)
  Tier B: photos/scan ──► shapy / ECON / PIXIE ──► SMPL-X ──► SKEL/OSSO ──► scaled OpenSim
  Tier C: video/IMU only on a generic model (adherence, rep counting)

CORRECTION VIEW (Tier A only; implemented as `rehabtwin correct` + `rehabtwin muscles`, see pipeline/README.md —
                 on Tier B/C it only produces labelled illustrations)
  measured motion ──► STGCN-rehab / UI-PRMD (quality score)
                  ──► corrected target computed on the patient's joint geometry/limits
                      (motion-diffusion-model may propose; OpenSim validates)
                  ──► OpenSim Moco (muscle activity the corrected motion requires)
                  ──► side-by-side: patient twin vs corrected twin, errors displayed
```

Clone Tier-A onboarding:
`python scripts/clone.py --only Slicer/Slicer,wasserth/TotalSegmentator,MIC-DKFZ/nnUNet,PatrikMrnka/msk-PIPE,CEINMS/CEINMS,opensim-org/opensim-core`
Clone live layer:
`python scripts/clone.py --only zju3dv/EasyMocap,perfanalytics/pose2sim,SlimeVR/SlimeVR-Server,SlimeVR/SlimeVR-Tracker-ESP,sccn/labstreaminglayer`
