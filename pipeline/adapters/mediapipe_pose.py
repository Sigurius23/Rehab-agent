#!/usr/bin/env python3
"""Run MediaPipe Pose Landmarker on a video and dump raw landmarks (.npz).

Non-gated front-end (Apache-2.0 code and model) used where the SKEL/HSMR
weights are not available. It is a *Tier C* signal: 33 landmarks on a
statistical body, no anatomical skeleton. Run in the ``twin-live`` env:

    python pipeline/adapters/mediapipe_pose.py video.mp4 --model pose_landmarker_heavy.task --out cam01_mp.npz

Model: https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_heavy/float16/latest/pose_landmarker_heavy.task

Output keys: image_xy (T,33,2) pixels, image_z (T,33) relative depth,
visibility/presence (T,33), world (T,33,3) metres (hip-centred, camera-aligned:
x right, y down, z away from the camera), detected (T,), fps, size (w, h).
Missing detections are NaN — nothing is filled in here.

Front ("selfie") cameras usually record a mirrored preview: MediaPipe then labels
every landmark with the wrong side and nothing looks wrong. Pass ``--mirrored``
for such clips; the dump is un-mirrored (``rehabtwin.mediapipe_front.unmirror_raw``)
and meta_json records ``camera_facing``/``mirrored``.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # pipeline/ -> import rehabtwin

from rehabtwin.mediapipe_front import unmirror_raw  # noqa: E402


def run(video, model, num_poses=1, min_conf=0.5):
    import cv2
    import mediapipe as mp
    from mediapipe.tasks.python import BaseOptions, vision

    cap = cv2.VideoCapture(str(video))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    opts = vision.PoseLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(model)),
        running_mode=vision.RunningMode.VIDEO, num_poses=num_poses,
        min_pose_detection_confidence=min_conf, min_pose_presence_confidence=min_conf, min_tracking_confidence=min_conf)
    xy, z, vis, pres, world, det = [], [], [], [], [], []
    with vision.PoseLandmarker.create_from_options(opts) as lm:
        f = 0
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            res = lm.detect_for_video(image, int(round(f * 1000.0 / fps)))
            if res.pose_landmarks:
                il, wl = res.pose_landmarks[0], res.pose_world_landmarks[0]
                xy.append([[p.x * w, p.y * h] for p in il])
                z.append([p.z for p in il])
                vis.append([p.visibility for p in il])
                pres.append([p.presence for p in il])
                world.append([[p.x, p.y, p.z] for p in wl])
                det.append(True)
            else:
                xy.append(np.full((33, 2), np.nan))
                z.append(np.full(33, np.nan))
                vis.append(np.zeros(33))
                pres.append(np.zeros(33))
                world.append(np.full((33, 3), np.nan))
                det.append(False)
            f += 1
    cap.release()
    return dict(image_xy=np.asarray(xy, float), image_z=np.asarray(z, float), visibility=np.asarray(vis, float),
                presence=np.asarray(pres, float), world=np.asarray(world, float), detected=np.asarray(det),
                fps=np.array(fps), size=np.array([w, h]))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--model", required=True, help="pose_landmarker_*.task")
    ap.add_argument("--out", required=True)
    ap.add_argument("--mirrored", action="store_true",
                    help="mirrored front-camera (selfie) clip: un-mirror landmarks so left/right are the subject's")
    a = ap.parse_args()
    out = run(a.video, a.model)
    if a.mirrored:
        out = unmirror_raw(out)
    out["meta_json"] = np.array(json.dumps({"video": str(a.video), "model": Path(a.model).name,
                                            "camera_facing": "front" if a.mirrored else "unspecified",
                                            "mirrored": a.mirrored}))
    np.savez_compressed(a.out, **out)
    print(json.dumps({"out": a.out, "frames": int(len(out["detected"])), "detected": int(out["detected"].sum()),
                      "fps": float(out["fps"]), "size": out["size"].tolist()}))


if __name__ == "__main__":
    main()
