# Adapter for t-kin-backend-markers: OpenCap's video-derived markers (the 43 "*_study" markers of a LabValidation
# MarkerData/Video *_videoAndMocap.trc) -> a rehabtwin MarkerSequence (.npz). Only the *_study markers are taken: not
# the motion-capture markers in the same file, and not the *_offsetRemoved variants, which were shifted using the motion
# capture. mm -> m; frame "yup_world"; fps and frame times from the file (frame k at k/fps, the file's own clock).
# Args: in_trc out_npz person_ref
import sys, numpy as np
from rehabtwin.io_formats import read_trc
from rehabtwin.sequence import MarkerSequence
names, markers, times, units = read_trc(sys.argv[1])
keep = [i for i, n in enumerate(names) if n.endswith("_study")]
assert len(keep) == 43, len(keep)
x = np.asarray(markers, float)[:, keep, :] * (0.001 if units == "mm" else 1.0)
x[np.all(x == 0, axis=2)] = np.nan
fps = float(round(1.0 / np.median(np.diff(times)), 6))
# some files start after 0 s: keep the file's own clock by numbering frames from its first time (fixed 2026-11-16 after 12 files failed the t0 = 0 assert)
fidx = np.rint(np.asarray(times) * fps).astype(int); assert np.allclose(fidx / fps, times, atol=1e-6)
valid = np.isfinite(x).all(axis=(1, 2))
seq = MarkerSequence(fps=fps, frame="yup_world", marker_names=[names[i] for i in keep], markers=x, valid=valid, frame_index=fidx,
                     meta=dict(source="OpenCap LabValidation MarkerData/Video/HRNet/2-cameras (*_study markers)", person_ref=sys.argv[3], tier="C",
                               metric_scale=True, default_config="mediapipe_lstm_pose2sim"))
seq.save(sys.argv[2]); print(f'{{"frames": {seq.n_frames}, "valid": {int(valid.sum())}, "fps": {fps}, "units_in": "{units}"}}')
