# Kinect v1 (Xbox 360) as a depth viewpoint

**Status:** the capture tool and the front end are built and tested on synthetic recordings and a fake
sensor (`pipeline/tests/test_kinect.py`). They have not run on a real sensor yet, so the result is Tier C
until it is measured against another system (see "Validating it").

A Kinect v1 measures how far each pixel is from the sensor (640 × 480 at 30 fps, about 0.8–4 m). A single
phone cannot (`docs/validation-results.md` §4: one camera cannot resolve pelvis tilt, hip flexion or lumbar
flexion). The front end puts each MediaPipe keypoint at the depth the sensor measured there. It adds:

- **Metric scale and distance** from one viewpoint. The depth error grows with the square of the distance:
  a few mm at 1 m, around 4 cm at the far end of the range (Khoshelham & Elberink 2012). Expect 1–3 cm at
  the 2.5–3 m a full standing body needs.
- **Gravity** from a floor plane fitted to the depth, cross-checked against the SDK's own floor plane.
- **Left/right check:** the SDK's skeleton labels sides anatomically, so a mirrored colour stream is
  detected instead of silently swapping every joint.

It does not:

- **See behind the body.** A hip hidden behind an arm has no depth; that keypoint is left empty, not guessed.
- **Measure joint centres.** It measures skin, so each keypoint is moved along the line of sight by the
  distance from skin to joint centre. That distance comes from height and BMI (`--height-m`, `--mass-kg`),
  fitted on 1,526 BEDLAM2 body models (`docs/bedlam2.md`). The hip's distance grows from about 10 cm at
  BMI < 22 to 14 cm above BMI 30, so height alone is not enough. The fit uses unclothed bodies standing
  upright; clothing and deep flexion change the distance, and the validation measures how much.
- **See a hip behind the thigh.** In a deep squat facing the sensor, the thigh lies in front of the hip. The
  front end checks every hip against the person's thigh length: measured in frames where the thigh is seen
  side-on, or given with `--segment-lengths` (e.g. `{"LHip-LKnee": 0.43, "RHip-RKnee": 0.43}` from the
  person's model). A hip that is not at that distance from its knee is placed on its own line of sight at
  thigh length behind the knee (`docs/bedlam2.md`, result 3).
- **Measure the heels, toes or hand points.** From the front the heel is behind the foot, and hand points
  are too small for the depth. These are placed from the depth-measured ankle or wrist, using MediaPipe's
  own 3D offset between them.
- **Use its own skeleton as the measurement.** Studies comparing Kinect skeletons with marker mocap find
  knee-angle errors above 5° in squats. The skeleton is recorded for comparison and for the left/right check.

## Setup (Windows)

1. Install the **Kinect for Windows SDK 1.8** (`KinectSDK-v1.8-Setup.exe` from Microsoft's download
   centre) before plugging the sensor in. It supports the Xbox 360 sensor for development.
2. An Xbox 360 sensor needs the **Kinect USB + power adapter**: it draws 12 V from the mains, and USB alone
   is not enough. Use a USB 2.0 port that no other camera shares.
3. Build the recorder: open a command prompt in `pipeline\capture\kinect_v1` and run `build.cmd`. It uses
   the C# compiler that ships with Windows; no Visual Studio is needed. A compile error naming a Kinect
   member means the SDK differs from what the tool assumes (`api_stub\MicrosoftKinectStub.cs`): report it.

## Placement

- 2.5–3 m from the person, sensor 0.8–1.2 m high and roughly level (the tilt is recorded). The whole body,
  both feet and some floor must be in the image. The recorder's framing check prints `feet ok` and
  `floor ok` once a second.
- Indoors, out of direct sunlight, which drowns the infrared pattern.
- Avoid black or glossy clothing.
- No second Kinect v1 facing the same scene, since the patterns interfere. Phones are fine.
- Face the sensor for part of the recording, so the left/right check has frames to compare.

## Record

```
KinectCapture.exe C:\rec\squat01 --seconds 40
```

There is a 5 s framing check first, then recording. Jump once at the start: the jump syncs the recording
with phones. Each recording gets its own folder; the recorder refuses a folder that is not empty. It
writes about 40 MB/s:

| File | Content |
|---|---|
| `colour/000000.jpg …` | 640 × 480 colour frames |
| `depth_registered.u16` | per frame 640 × 480 uint16 depth in mm on the colour pixel grid. It uses the SDK's factory registration (`CoordinateMapper.MapDepthFrameToColorFrame`); 0 = no depth |
| `depth_raw.u16` | the same depth on the depth camera's own grid |
| `frames.csv` | sensor frame numbers and timestamps, host time, accelerometer, SDK floor plane |
| `skeleton.csv` | the SDK's 20-joint skeleton of the nearest tracked person, in metres and colour pixels |
| `meta.json` | format `rehabtwin-kinect-v1/1`, sensor id, nominal intrinsics, tilt, frame counts |

Frames the sensor drops show up as gaps in the frame numbers (`sensor_frames_missed`). They become gaps in
time, never shifted frames.

## Process (any OS)

```
python pipeline/adapters/mediapipe_pose.py C:\rec\squat01\colour\%06d.jpg --model pose_landmarker_heavy.task --out C:\rec\squat01\mediapipe.npz
python -m rehabtwin kinect C:\rec\squat01 C:\rec\squat01\mediapipe.npz squat01_seq.npz --height-m 1.80 --mass-kg 75 --person-ref P01
python -m rehabtwin augment squat01_seq.npz squat01_aug.npz --height-m 1.80 --mass-kg 75 --mass-source measured
python -m rehabtwin process squat01_aug.npz out\squat01 --exercise squat --height-m 1.80
```

(Inside a `.cmd` file, write `%%06d`.)

`rehabtwin kinect` refuses three cases:
- a MediaPipe dump with another frame count than the recording;
- a recording it cannot read (truncated, or another format);
- a recording where it cannot tell whether the colour stream is mirrored. Pass `--mirrored` or
  `--not-mirrored` once you have checked: the person's right hand must appear on the left of the image.

Its output records:
- the share of frames each keypoint was lifted in;
- which keypoints were left empty because their depth disagreed with the pose by more than 0.2 m;
- the floor fit, and its angle to the SDK's floor plane;
- the left/right decision.

## Validating it

Record the same squats with the Kinect and three phones (−40°, 0°, +40°, `docs/hardware.md`) at once, and
jump at the start. Process the phones as in `docs/validation-results.md` §4 (`mp-multiview --sync`,
`augment`, `process`). Then use their motion as the reference for the Kinect session:

```
python -m rehabtwin process squat01_aug.npz out\squat01 --exercise squat --height-m 1.80 \
    --reference out\phones\opensim\ik.mot --reference-model out\phones\opensim\model_scaled.osim \
    --reference-grade markerless --max-lag-s 4
```

That is agreement with another markerless system, not accuracy, and it approves nothing. It answers the
open question of whether one Kinect beats one phone on the trunk–pelvis–hip chain, and it measures the
bias of the skin-to-joint-centre offsets.

## Toward tracking with a phone alone

The Kinect (plus phones) session is meant as a calibration step for one person. It gives:
- metric scale and segment lengths;
- a check of what a single phone gets wrong for this person.

Later sessions could then use one phone with that personal model. The scaling would come from the
calibration session instead of each session's own frames; this is not built yet. What a phone-only
session may claim follows from that per-person check. An iPhone with LiDAR is a colour-plus-depth source
too, so the same lifting applies to its depth (`record3d` in the catalog). Once the Kinect path is
validated, a LiDAR phone can follow it.
