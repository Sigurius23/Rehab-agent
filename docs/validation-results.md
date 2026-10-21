# Validation results — what has actually been measured

Results from `pipeline/` (rehabtwin 0.1.0, OpenSim 4.6, Pose2Sim model
`Model_Pose2Sim_muscles_flex.osim`). Each block says what was compared with what.
**None of these is a clinical validation**: no marker-mocap reference has been run yet
(see "Next" below). Targets are the engineering targets in `docs/accuracy.md`.

## 1. Software round trip (synthetic truth) — the back-end is correct

`python -m rehabtwin selftest` generates a 12 s bodyweight squat (3 reps, right-knee valgus,
41° trunk lean) on a body scaled 3–7 % away from the generic model. It perturbs every skin
marker by ~1 cm, adds 4 mm jitter, 6 mm drift and two dropouts, and views it from a camera
pitched 7.5° down. That sequence goes through the full stage: camera → gravity → scale →
static IK → marker placement → IK → metrics → validation.

| Signal | RMSE (°) | Bias (°) | True range (°) |
|---|---:|---:|---:|
| knee flexion R / L | 0.88 / 0.96 | +0.6 / +0.6 | 95 |
| hip flexion R / L | 1.15 / 1.26 | +0.4 / +0.4 | 90 / 88 |
| hip adduction R · rotation R | 0.62 · 0.69 | 0.0 | 6 · 5 |
| ankle dorsiflexion R / L | 1.36 / 1.04 | 0.0 | 28 / 27 |
| pelvis tilt | 0.88 | −0.2 | 20 |
| total lumbar flexion | 1.02 | +0.1 | 21 |
| **trunk inclination vs gravity, sagittal / frontal** | **0.35 / 1.56** | +0.1 / −1.5 | 42 / 9 |
| knee frontal-plane projection angle R / L | 1.15 / 1.48 | ±0.4 | 19 / 3 |
| shoulder flexion R · elbow flexion R | 1.56 · 2.63 | −1.4 · +2.5 | 70 · 10 |
| forearm pro/supination R | 10.9 | +9.3 | 0 (poorly observable) |

Other checks: segment scale factors are recovered within 0.5 % (femur 1.0705 against a true
1.07). The floor-plane fit recovers the camera pitch. All three reps are found, and the
right-knee valgus shows as +20.7° against −4.2° on the left. The IK marker residual is
8.4 mm.

What this proves: frames, gaps, filtering, scaling, marker placement, IK, metrics and the
validation code do what they claim. What it does **not** prove: anything about real people,
real video, or SKEL/HSMR accuracy.

Bugs this test caught on the way, all fixed:
- OpenSim MarkerPlacer static-pose bias (4.4° pelvis tilt baked into every frame).
- Pose2Sim head-marker frame error.
- Pelvis scaling from skin markers off by 4 %.
- Floor fit fooled by foot-marker height differences (RANSAC locked onto a rolled plane).
- Trunk frontal-lean formula undefined past 90°.

## 2. Real video — one camera vs four (Pose2Sim demo trial)

`examples/pose2sim_demo.sh`: Pose2Sim's `Demo_SinglePerson` (one person balancing on one leg,
4 calibrated synchronised cameras, 1.67 s at 60 fps).

- **Reference:** MediaPipe Pose on all 4 views, DLT-triangulated (median reprojection
  11.6 px ≈ 2 cm), OpenSim IK (marker RMS 3.0 cm). This is a *markerless* reference using the
  same keypoint model: it measures what one camera loses against four, not truth.
- **Estimate:** MediaPipe on camera 1 alone (calibrated focal length), with world landmarks
  and the camera translation solved per frame.

| Signal | RMSE (°) | Bias (°) | SD after bias removal (°) | Reference range (°) |
|---|---:|---:|---:|---:|
| knee flexion R / L | 18.6 / 15.4 | +12.9 / −5.7 | 13.3 / 14.3 | 52 / 44 |
| hip flexion R / L | 16.6 / 20.9 | −13.0 / −19.4 | 10.2 / 7.8 | 53 / 31 |
| hip adduction R / L | 5.8 / 6.5 | +3.2 / −4.7 | 4.9 / 4.5 | 34 / 40 |
| ankle dorsiflexion R / L | 41 / 50 | −10 / −48 | 40 / 15 | 42 |
| pelvis tilt | 12.6 | −7.8 | 9.8 | 20 |
| trunk inclination sagittal (camera-level gravity) | 47.6 | +45.7 | 13.0 | 30 |
| trunk inclination sagittal (device gravity) | 25.8 | +21.8 | 13.9 | 30 |
| knee FPPA R / L | 11.5 / 23.8 | −5.4 / +18.6 | 10.2 / 14.9 | 25 / 15 |

Result: **no joint/plane meets its target; the report approves nothing.** That is the
system working as designed (`docs/accuracy.md`: the system degrades its claims, not its
standards).

Diagnosis (in `pipeline/` QC and ad-hoc checks):
- **Depth.** MediaPipe's single-view 3D skeleton differs from the triangulated one by 8.6 cm
  RMS even after the best rigid alignment, and is rotated ~14° relative to the true camera
  frame. A full 6-DoF reprojection fit of that skeleton to its own 2D landmarks only reduced
  the rotation to 12°. The 3D shape itself is wrong for this pose, which no post-processing
  can fix.
- **Gravity.** Camera 1 is tilted 26° (from the calibration). The camera-level assumption
  therefore puts every inclination off by up to 26°. The single-view floor fit found a 25.5°
  tilt, but in the wrong direction (24.6° from the true up vector), because it sits on the
  same broken depth. It was correctly rejected. Supplying the true gravity (as a phone IMU
  would) halved the trunk-inclination error. Recording device gravity is now in the pipeline
  and the hardware protocol.

Consequences for the project:
1. MediaPipe monocular is not usable for joint angles, even at Tier-C screening level, beyond
   rep counting. Keep it as a non-gated test front-end only.
2. The monocular front-end must be a model that reasons in 3D with a body prior: HSMR/SKEL
   (this slice's adapter), or WHAM as used by OpenCap Monocular. OpenCap Monocular reports
   4.8° MAE against marker mocap for walking, squats and sit-to-stand (arXiv 2603.24733).
   That figure is the bar to match.
3. Every phone capture must store the device gravity vector.

## 3. HSMR / SKEL front-end — software tested, not yet measured

The adapter (`pipeline/adapters/hsmr_to_skelseq.py`) is tested end to end with an emulated
HSMR dump (fake detections including a bystander, fake SKEL forward). The real HSMR network
and the SKEL model are licence-gated (MPI-IS registration) and could not be run in the
build environment. **Its accuracy is unknown until step 4 below has been run.**

## 4. Real video against an independent markerless reference — OpenCap, 5 phones, one squat trial

**Data.** The only public video trial reachable from the build environment: OpenCap's LabValidation
fixture `subject2/squats1` in `stanfordnmbl/opencap-test-data` (5 iPhones at ±65°, ±40°, 0°; 60 fps,
720×1280; checkerboard calibration; 1.96 m, 78.2 kg; 5 squats). Its marker-mocap files live only on
SimTK, which the build network blocks. The reference is therefore **OpenCap's own result** for the same
videos (OpenPose → triangulation → LSTM marker augmenter → LaiUhlrich2022 IK). OpenCap reports about
4.5° mean absolute joint-angle error against marker mocap (Uhlrich et al. 2023), so this measures
*agreement with a validated markerless system*, not accuracy. The validation reports carry
`reference_grade: markerless` and approve nothing. Reproduce with `examples/opencap_agreement.sh`.

**Pipeline.**
- MediaPipe Pose (heavy) per camera.
- Camera sync: the phones started up to 46 frames (0.77 s) apart. Hip-motion cross-correlation recovered the offsets (peak r 0.79–0.85), and the remaining lag to OpenCap's timeline was 0.07 s.
- Weighted DLT triangulation with OpenCap's calibration, median reprojection 7.4 px.
- `rehabtwin process`, optionally after `rehabtwin augment` (OpenCap's LSTM via Pose2Sim's ONNX).

Values are RMSE in degrees; brackets give (bias / SD after removing the bias).

| Signal | 5 cams, keypoints only | **5 cams + augmenter** | 1 cam (frontal) | 1 cam + augmenter |
|---|---|---|---|---|
| Trunk inclination, sagittal | 47.4 (−23.4 / 41.3) | **2.7 (−0.8 / 2.6)** | 9.7 (+7.4 / 6.3) | 9.4 (+6.0 / 7.3) |
| Trunk inclination, frontal | 8.7 (+2.0 / 8.4) | **2.6 (+1.2 / 2.3)** | 10.3 (+8.9 / 5.2) | 7.2 (+6.8 / 2.5) |
| Pelvis tilt | 37.3 (−29.1 / 23.4) | **6.0 (−5.5 / 2.4)** | 18.9 (+15.5 / 10.9) | 20.1 (+18.8 / 7.2) |
| Pelvis list | 2.6 | **2.6** | 7.8 | 4.3 |
| Lumbar flexion (total) | 50.9 (+37.5 / 34.4) | **7.1 (+6.3 / 3.2)** | 25.3 (−23.7 / 8.8) | 25.8 (−25.0 / 6.3) |
| Hip flexion R | 36.0 (+25.7 / 25.3) | **13.9 (+13.1 / 4.6)** | 17.6 (−14.7 / 9.6) | 10.4 (−8.3 / 6.3) |
| Hip adduction R | 2.4 | **3.2** | 3.3 | 4.6 |
| Knee flexion R / L | 8.1 / 5.9 | **9.3 / 9.2 (+8.7 / 3.2)** | 9.7 / 13.6 | 14.9 / 21.5 |
| Ankle dorsiflexion R / L | 8.5 / 6.5 | **4.9 / 4.6** | 14.5 / 13.8 | 13.3 / 18.4 |
| Knee FPPA R / L | 20.7 / 21.4 | **4.7 / 9.5** | 6.6 / 10.2 | 5.9 / 7.1 |

What this shows:

1. **Sparse keypoints leave the pelvis unobservable.** Two hip points fix the pelvis's left-right axis
   but not its tilt, so IK trades pelvis tilt, hip flexion and lumbar flexion freely. It settled on
   up to 95° of pelvis tilt with 56° of lumbar *extension*. The synthetic round trip (§1) could not
   show this, because it uses 105 dense SKEL markers.
2. **OpenCap's LSTM augmenter fixes it.** It predicts ASIS/PSIS, epicondyles and malleoli from the
   keypoints, height and mass. With 5 cameras, the trunk then agrees within 2.7°, pelvis tilt within
   6° (2.4° after removing the bias), knee FPPA R within 4.7°, and ankle within 5°.
3. **Pose2Sim's weak L5/S1 prior hurt here.** OpenCap's IK has none. With the prior, pelvis tilt was
   13.0° and hip flexion 20.3°; without it, 6.0° and 13.9°. `mediapipe_lstm_pose2sim` now leaves the
   prior out.
4. **Remaining constant offsets are mostly definitional.** Knee is +8.7° and hip flexion +13°. The
   Pose2Sim model and LaiUhlrich2022 define the pelvis and knee frames differently, and MediaPipe's hip
   landmarks are not OpenPose's. The bias-removed agreement is 2.4–4.6° for these joints.
5. **One camera is not enough for the trunk–pelvis–hip chain**, even with the augmenter: 9–26° on
   those signals, and the knee and ankle get worse (13–22°). Knee FPPA, hip adduction and frontal pelvis
   stay within 4–8°.

One trial and one subject, against a markerless reference: nothing here approves a use. It does say
which front end to measure against marker mocap first: 5 cameras plus augmenter. It also says which
signals monocular capture should not drive (pelvis, hip flexion, lumbar).

## Next: the first real accuracy measurement (closes gap D-04 for kinematics)

Use the public **OpenCap LabValidation** dataset (SimTK project "opencap"): 10 subjects;
squats, sit-to-stand, drop jumps and walking; synchronised phone videos, marker motion
capture and its OpenSim IK (`<subject>/OpenSimData/Mocap/IK/<movement>.mot`). OpenCap
Monocular's own validation code (`upstream/utahmobl/opencap-monocular/validation/`) reads
the same layout.

```bash
# per subject × movement × camera (hsmr env, then biomech env)
# video files live under <subject>/VideoData/<session>/<cam>/<movement>/ (check the exact names in your download)
python exp/run_demo.py --input_path <video> --output_path hsmr_out
python pipeline/adapters/hsmr_to_skelseq.py --hsmr-npy hsmr_out/HSMR-<video>.npy --video <video> --skel-model-dir ... --out S/skel_seq.npz
python -m rehabtwin process S/skel_seq.npz S --exercise squat \
    --reference <subject>/OpenSimData/Mocap/IK/squats1.mot --reference-system "OpenCap LabValidation marker mocap IK" \
    --max-lag-s 0.5
```

Report per joint × plane across subjects. Compare with OpenCap Monocular's 4.8° on the same
trials. Only joint/planes that pass may ever reach a feedback rule.
