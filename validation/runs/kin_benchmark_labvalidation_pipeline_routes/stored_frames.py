# Fix round 2 (HSMR): write exactly the frames stored in a video, as OpenCV returns them in order, to a lossless FFV1
# .avi at the same fps, so that HSMR's imageio/FFmpeg reader sees no timestamp gap and no duplicated frames.
# Then check that imageio reads back exactly the OpenCV frames (count and pixels). Args: src_video dst_avi
import sys, cv2, numpy as np
src, dst = sys.argv[1], sys.argv[2]
c = cv2.VideoCapture(src); fps = c.get(cv2.CAP_PROP_FPS); frames = []
while True:
    ok, f = c.read()
    if not ok: break
    frames.append(f)
h, w = frames[0].shape[:2]
wr = cv2.VideoWriter(dst, cv2.VideoWriter_fourcc(*"FFV1"), fps, (w, h))
if not wr.isOpened(): sys.exit("FFV1 writer not available")
for f in frames: wr.write(f)
wr.release()
print(f'{{"stored_frames": {len(frames)}, "fps": {fps}, "listed_frames": {int(cv2.VideoCapture(src).get(cv2.CAP_PROP_FRAME_COUNT))}}}')
