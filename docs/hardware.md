# Hardware specification — selected sensor set

> **Selected hardware: RGB camera(s) + iPhone LiDAR + optional Intel RealSense D455.**
> This document fixes what each device is *for*, what accuracy it can deliver
> (see `docs/accuracy.md`), and the calibration/synchronisation protocol that
> makes the three streams one twin. Accuracy remains design priority #1:
> this sensor set does **not** replace MRI/CT for the Tier-A bone/muscle layers.

## Bill of materials

| Role | Device | Minimum spec / notes |
|---|---|---|
| Primary motion cameras | 1–4× RGB cameras (webcam/machine-vision/phone) | 1080p @ 60 fps preferred, manual exposure + focus lock, global shutter preferred for fast movement; tripod-mounted at known positions |
| Body surface scan + mobile RGB-D | iPhone Pro with LiDAR (iPhone 12 Pro or later Pro/Pro Max) | Rear LiDAR for whole-body surface; front TrueDepth for head/face close range |
| Optional fixed depth viewpoint | Intel RealSense D455 | The D455 is a long-range stereo depth camera with a 95 mm baseline, global-shutter depth sensors, an RGB sensor, and a built-in IMU [1](https://github.com/realsenseai/librealsense) |
| Host | Workstation/laptop with GPU | Runs pose, fusion, twin solving, recording (LSL) |
| Calibration kit | ChArUco board (printed rigid, measured square size), tape measure, floor markers | Used every setup change — see protocol below |
| Anthropometry kit | Height measure, scale, segment-length tape measurements | Cheap ground truth that constrains SHAPY/SMPL shape fitting |
| Lighting | Diffuse, flicker-free, no backlight | Depth and pose both degrade under glare/dark clothing/hair |

## What each sensor actually delivers (verified specs)

| Stream | Resolution / rate | Range | Accuracy character |
|---|---|---|---|
| iPhone rear LiDAR (via ARKit) | Depth map 256 × 192 [8](https://www.tandfonline.com/doi/full/10.1080/2150704X.2026.2720055), up to 60 Hz app-dependent | ~0.3–5 m | **Centimetre-level.** An iPhone-model comparison study found point-cloud RMSE of ≈2.05–2.06 cm against known validation shapes [8](https://www.tandfonline.com/doi/full/10.1080/2150704X.2026.2720055) |
| iPhone front TrueDepth | 640 × 480 depth [13](https://ar5iv.labs.arxiv.org/html/2201.10865) | Close range (face/head, ~0.15–0.5 m useful) | Sub-mm–mm on small close targets in lab tests, but only at close range — not a whole-body sensor |
| RealSense D455 depth | Up to 1280 × 720, up to 90 fps; ideal range 0.6 m to 6 m; depth accuracy <2 % at 4 m [2](https://realsenseai.com/products/real-sense-depth-camera-d455f/) | 0.6–6 m ideal | <2 % of distance means ~4 cm at 2 m, ~8 cm at 4 m worst case — excellent occupancy/occlusion/scale evidence, **not** a surface-metrology sensor |
| RealSense D455 RGB + IMU | RGB up to 1280 × 800 (global shutter); built-in Bosch BMI055 IMU [5](https://www.intel.com/content/www/us/en/products/sku/205847/intel-realsense-depth-camera-d455/specifications.html) | — | RGB is a usable extra camera viewpoint; IMU helps when the camera itself moves (keep it tripod-fixed for rehab) |
| RGB cameras | 1080p60+ | Capture volume 2–5 m | The **primary kinematics signal** (via MediaPipe/MMPose → Pose2Sim/EasyMocap → patient OpenSim model) |

**Streaming path for the iPhone:** the Record3D library receives an RGBD stream
from iOS devices with TrueDepth cameras to a computer via USB, with C++ and
Python libraries [1](https://github.com/marek-simonik/record3d) — and current
versions also stream LiDAR confidence maps and camera poses. Apple's own
RoomPlan/Object Capture (RealityKit `PhotogrammetrySession`) exist as platform
APIs for room/object reconstruction; they are **not GitHub repos**, are designed
for rooms/objects rather than moving people, and may only be used here for a
*static, held-pose* surface capture after validation — never as the live twin.

## Role assignment in the twin (do not swap these)

| Twin layer (docs/accuracy.md) | Sensor(s) in charge | Tier achievable |
|---|---|---|
| Bone geometry, joint centres | **MRI/CT only** — no device in this hardware set sees bone | A (imaging) |
| Muscle geometry/activation | MRI/CT + EMG (CEINMS); hardware set contributes nothing directly | A (imaging+EMG) |
| Surface shape | iPhone LiDAR full-body scan (A-pose, slow rotation) fused with RGB photogrammetry/SHAPY; D455 as a second depth view | **B** (cm-level) — register to Tier-A imaging when available |
| Live kinematics | RGB cameras (multi-view where possible) + D455 depth for occlusion/scale robustness; iPhone as an additional viewpoint | B, A-kinematics only after per-joint/per-plane validation |
| Session context | D455/iPhone depth for feet-floor contact, chair/props position | supporting evidence |

## Clinic rig (recommended geometry)

```
                 [Cam 2]
                    \
   [Cam 1] ——  subject (2–4 m)  —— [D455, fixed, 2–3 m, ~1.2 m height]
                    /
        [iPhone on tripod: live view or scan station]
   Floor: marked capture volume, calibration board position logged
```
- Subject distance to D455: keep inside 0.6–6 m ideal range, practically 2–3 m.
- Three cameras about 40° apart (−40°, 0°, +40°), all seeing the front of the body; avoid collinear views.
  Measured on a public 5-phone squat (`docs/validation-results.md` §4): three phones kept every MediaPipe
  keypoint and matched five. Two phones 80° apart lost a knee for up to 1.4 s at the bottom of the squat,
  which the pipeline refuses to bridge, so use two only if both keep the knees in view at full depth.
  Two near-side views 130° apart lost trunk and lumbar (8.7°/14° vs 2.8°/7.6° against OpenCap). One phone
  cannot resolve pelvis tilt, hip flexion or lumbar flexion (10–26°) — use it for knee FPPA and frontal signals only.
- iPhone body scan is a separate, static station step (person rotates slowly
  in A-pose, tight clothing) — it is not recorded during dynamic exercise.

## Calibration & sync protocol (every setup change; log everything)

1. **Intrinsics:** cameras — verify factory intrinsics or calibrate with the
   ChArUco board; iPhone — take intrinsics streamed per frame (Record3D);
   D455 — factory intrinsics + on-chip calibration check via librealsense.
2. **RGB↔depth alignment:** D455 via SDK `align` (pyrealsense2); iPhone depth
   is registered to its RGB by the platform — verify with a board corner test.
3. **Extrinsics:** one shared ChArUco capture sequence per device → all devices
   into the room frame (Open3D/Pose2Sim calibration utilities). Reprojection
   error is written to the session record.
4. **Temporal sync:** all streams published/recorded through
   `labstreaminglayer` (LSL). D455 hardware timestamps and Record3D per-frame
   pose/intrinsics metadata are preserved, never replaced by receive time.
5. **Sync proof per session:** LED-flash / hand-clap event visible in every
   stream at session start; measured inter-stream offset must be logged and
   < 5 ms after correction for kinematics use.
6. **Body-scan QC:** LiDAR scan checked for holes (armpits, hair, dark/black
   clothing, feet) and re-scanned before the person leaves; segment lengths
   from the scan cross-checked against tape measurements — disagreement
   > 2 cm on a long segment triggers investigation, not silent acceptance.
7. **Session record** (one folder per session): raw streams, calibration files,
   sync offsets, QC results, twin tier (A/B/C), software + upstream commit pins.
8. **Gravity per camera:** phones record the device gravity vector (ARKit/CoreMotion)
   with every capture; fixed cameras get it from the calibration board or a spirit
   level. Without it, every trunk/pelvis inclination from that camera is off by the
   camera's tilt (measured: 26° on a real setup, `docs/validation-results.md`).
9. **Mirroring check per camera:** front ("selfie") cameras often record the mirrored
   preview, and MediaPipe then swaps every left/right landmark without any error
   (a right-knee valgus cue would go to the left knee). Before recording, have the
   subject face the camera and raise their right hand: it must appear on the
   **left** of the image. If it appears on the right, use the rear camera, turn off
   mirroring, or pass `--mirrored` (`adapters/mediapipe_pose.py`, or `rehabtwin mp-mono`
   for a dump already made); the setting is recorded in the dump/sequence meta. For
   several cameras, un-mirror at the adapter: `mp-multiview` cannot do it afterwards.

## Software map (all already in the catalog)

| Need | Repo |
|---|---|
| D455 driver (USB, depth/RGB/IMU, alignment) | `realsenseai/librealsense` (#105 in catalog) |
| iPhone RGB-D streaming | `marek-simonik/record3d` · `strayrobots/scanner` |
| Point-cloud / RGB-D processing, TSDF fusion | `isl-org/Open3D` |
| Multi-stream sync + recording | `sccn/labstreaminglayer` |
| Pose from RGB | `google-ai-edge/mediapipe` · `open-mmlab/mmpose` · `perfanalytics/pose2sim` · `zju3dv/EasyMocap` |

## Privacy note

Depth/LiDAR feels anonymous but combined RGB-D of a patient's body in a home
is health data. Process locally, keep RGB and depth under the same consent and
retention policy, and store scans with the twin — not in this git repository.

## What this hardware cannot do (stated deliberately)

- It cannot measure bone position, joint centres, or muscle size. Claims at
  those layers without imaging violate `docs/accuracy.md`.
- LiDAR/D455 surfaces are centimetre-class: good for shape registration,
  segment volumes (approximate) and contact context; not for the ≤2 mm
  Tier-A surface target, and never for surgical-style claims.
- A single phone (RGB+LiDAR) alone is a Tier-C/B screening rig. The full
  system above is the smallest configuration this project may call a twin.
