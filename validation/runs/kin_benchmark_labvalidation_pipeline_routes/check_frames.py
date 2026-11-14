# Check (in the HSMR environment) that imageio's FFmpeg reader returns exactly the OpenCV frames of the source video.
import sys, cv2, imageio, numpy as np
src, dst = sys.argv[1], sys.argv[2]
A = [f for f in imageio.get_reader(dst, format="FFMPEG")]
c = cv2.VideoCapture(src); B = []
while True:
    ok, f = c.read()
    if not ok: break
    B.append(f[:, :, ::-1])
same = len(A) == len(B) and all(np.array_equal(a, b) for a, b in zip(A, B))
print(f'{{"imageio_frames": {len(A)}, "opencv_frames": {len(B)}, "pixel_identical": {str(same).lower()}}}')
sys.exit(0 if same else 1)
