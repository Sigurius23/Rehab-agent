"""Gap handling and low-pass filtering for marker trajectories.

Policy (recorded in QC, never silent):
* gaps up to ``max_gap_s`` are linearly bridged and listed as imputed frames;
* longer whole-frame gaps split the trial into separate segments, each solved on its own;
* a longer gap of a single marker stays NaN (no IK target there), never frozen or bridged;
* the low-pass runs over each finite stretch separately, so it never smears across a gap.
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


def interpolate_gaps(x, max_gap=None):
    """Linearly interpolate NaN runs along axis 0 of (T, ...) data; runs at the edges are held.

    ``max_gap`` (samples) limits what is filled: a longer run, inside or at an edge, stays NaN
    as a whole, so a marker lost for a second is not frozen or drawn as a straight line.
    ``None`` fills every run; only for consumers that need dense input and mask the result
    themselves (the augmenter's LSTM).
    """
    x = np.array(x, dtype=float, copy=True)
    flat = x.reshape(x.shape[0], -1)
    t = np.arange(x.shape[0])
    for j in range(flat.shape[1]):
        col = flat[:, j]
        ok = np.isfinite(col)
        if ok.all() or not ok.any():
            continue
        fill = ~ok
        if max_gap is not None:
            fill = np.zeros_like(ok)
            for a, b in runs(~ok):
                fill[a:b] = b - a <= max_gap
        col[fill] = np.interp(t[fill], t[ok], col[ok])
    return flat.reshape(x.shape)


def lowpass(x, fps, cutoff_hz=6.0, order=4):
    """Zero-lag Butterworth low-pass along axis 0 (Winter-style, 6 Hz default).

    Each finite stretch of a column is filtered on its own: NaN stays NaN and a gap never
    pulls its neighbours. Stretches too short for filtfilt's padding are returned as-is.
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
    flat = x.reshape(x.shape[0], -1)
    out = flat.copy()
    for j in range(flat.shape[1]):
        for s, e in runs(np.isfinite(flat[:, j])):
            if e - s > padlen:
                out[s:e, j] = filtfilt(b, a, flat[s:e, j])
    return out.reshape(x.shape)
