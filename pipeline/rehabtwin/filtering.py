"""Gap handling and low-pass filtering for marker trajectories.

Policy (recorded in QC, never silent):
* gaps up to ``max_gap_s`` are linearly bridged and listed as imputed frames;
* longer gaps split the trial into separate segments, each solved on its own.
"""
from __future__ import annotations

import numpy as np
from scipy.signal import butter, filtfilt


def runs(mask):
    """[(start, stop)) index ranges where mask is True."""
    mask = np.asarray(mask, bool)
    if not mask.any():
        return []
    d = np.diff(np.concatenate([[0], mask.astype(int), [0]]))
    return list(zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)))


def plan_segments(valid, fps, max_gap_s=0.2, min_segment_s=1.0):
    """Split frames into solvable segments.

    Returns (segments, imputed_frames) where segments are [(start, stop))
    ranges over frames (gaps short enough to bridge are inside a segment)
    and imputed_frames are the bridged frame indices.
    """
    valid = np.asarray(valid, bool)
    max_gap = int(round(max_gap_s * fps))
    min_len = int(round(min_segment_s * fps))
    segs = []
    imputed = []
    for start, stop in runs(valid):
        if segs and start - segs[-1][1] <= max_gap:
            imputed.extend(range(segs[-1][1], start))
            segs[-1] = (segs[-1][0], stop)
        else:
            segs.append((start, stop))
    keep = [(a, b) for a, b in segs if b - a >= max(min_len, 2)]
    kept_imputed = [f for f in imputed if any(a <= f < b for a, b in keep)]
    return keep, kept_imputed


def interpolate_gaps(x):
    """Linearly interpolate NaNs along axis 0 of (T, ...) data; edges are held."""
    x = np.array(x, dtype=float, copy=True)
    flat = x.reshape(x.shape[0], -1)
    t = np.arange(x.shape[0])
    for j in range(flat.shape[1]):
        col = flat[:, j]
        ok = np.isfinite(col)
        if ok.all() or not ok.any():
            continue
        col[~ok] = np.interp(t[~ok], t[ok], col[ok])
    return flat.reshape(x.shape)


def lowpass(x, fps, cutoff_hz=6.0, order=4):
    """Zero-lag Butterworth low-pass along axis 0 (Winter-style, 6 Hz default).

    Columns that are entirely NaN are left NaN; short series are returned as-is.
    """
    x = np.asarray(x, dtype=float)
    if cutoff_hz is None or cutoff_hz <= 0 or cutoff_hz >= fps / 2:
        return x.copy()
    # filtfilt runs a (order/2)-order filter twice; correct the cutoff so the
    # combined -3 dB point lands at cutoff_hz (Winter 2009, Eq. 3.11).
    single = max(order // 2, 1)
    correction = (2 ** 0.5 - 1) ** (1 / (2 * single))
    wn = min(cutoff_hz / correction / (fps / 2), 0.99)
    b, a = butter(single, wn)
    padlen = 3 * max(len(a), len(b))
    if x.shape[0] <= padlen:
        return x.copy()
    flat = x.reshape(x.shape[0], -1)
    out = np.full_like(flat, np.nan)
    for j in range(flat.shape[1]):
        col = flat[:, j]
        if np.isfinite(col).all():
            out[:, j] = filtfilt(b, a, col)
    return out.reshape(x.shape)
