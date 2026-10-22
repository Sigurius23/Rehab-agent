"""Readers/writers for OpenSim text formats (.trc markers, .mot/.sto tables).

Pure numpy so they can be used and tested without OpenSim installed.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np


# --------------------------------------------------------------------- TRC

def write_trc(path, marker_names, markers, times, units="m"):
    """Write markers (T, M, 3) to an OpenSim .trc file.

    Missing samples are written as ``NaN``, which OpenSim reads as "marker not
    observed in this frame" (IK skips it). Not empty fields: OpenSim's reader
    drops a trailing empty field and rejects the row when the last marker is missing.
    """
    path = Path(path)
    markers = np.asarray(markers, dtype=float)
    times = np.asarray(times, dtype=float)
    n_frames, n_markers, _ = markers.shape
    if len(marker_names) != n_markers or len(times) != n_frames:
        raise ValueError("marker_names/times do not match markers shape")
    rate = 1.0 / np.median(np.diff(times)) if n_frames > 1 else 1.0
    lines = [
        f"PathFileType\t4\t(X/Y/Z)\t{path.name}",
        "DataRate\tCameraRate\tNumFrames\tNumMarkers\tUnits\tOrigDataRate\tOrigDataStartFrame\tOrigNumFrames",
        f"{rate:.6f}\t{rate:.6f}\t{n_frames}\t{n_markers}\t{units}\t{rate:.6f}\t1\t{n_frames}",
        "Frame#\tTime\t" + "\t".join(f"{n}\t\t" for n in marker_names),
        "\t\t" + "\t".join(f"X{i + 1}\tY{i + 1}\tZ{i + 1}" for i in range(n_markers)),
        "",
    ]
    for f in range(n_frames):
        vals = []
        for v in markers[f].reshape(-1):
            vals.append(f"{v:.6f}" if np.isfinite(v) else "NaN")
        lines.append(f"{f + 1}\t{times[f]:.6f}\t" + "\t".join(vals))
    path.write_text("\n".join(lines) + "\n")
    return path


def read_trc(path):
    """Return (marker_names, markers (T, M, 3), times, units)."""
    rows = Path(path).read_text().splitlines()
    header_vals = rows[2].split("\t")
    header_keys = rows[1].split("\t")
    meta = dict(zip(header_keys, header_vals))
    units = meta.get("Units", "m")
    names = [n for n in rows[3].split("\t")[2:] if n.strip()]
    data = []
    for line in rows[5:]:
        if not line.strip():
            continue
        parts = line.split("\t")
        vals = [float(p) if p.strip() else np.nan for p in parts[1:]]
        vals += [np.nan] * (1 + 3 * len(names) - len(vals))
        data.append(vals[: 1 + 3 * len(names)])
    arr = np.asarray(data, dtype=float)
    times = arr[:, 0]
    markers = arr[:, 1:].reshape(len(arr), len(names), 3)
    return names, markers, times, units


# ----------------------------------------------------------------- MOT/STO

@dataclass
class Table:
    """A time-indexed table as stored in .mot/.sto files."""
    columns: list
    data: np.ndarray  # (T, C) — excludes the time column
    time: np.ndarray
    in_degrees: bool = True
    header: dict = field(default_factory=dict)

    def col(self, name):
        return self.data[:, self.columns.index(name)]

    def has(self, name):
        return name in self.columns


def read_table(path) -> Table:
    lines = Path(path).read_text().splitlines()
    header = {}
    i = 0
    while i < len(lines) and lines[i].strip().lower() != "endheader":
        if "=" in lines[i]:
            k, v = lines[i].split("=", 1)
            header[k.strip()] = v.strip()
        i += 1
    if i == len(lines):
        raise ValueError(f"{path}: no 'endheader' line")
    cols = lines[i + 1].split("\t")
    cols = [c.strip() for c in cols]
    body = [list(map(float, ln.split())) for ln in lines[i + 2:] if ln.strip()]
    arr = np.asarray(body, dtype=float).reshape(len(body), len(cols))
    t_idx = cols.index("time")
    data_cols = [c for j, c in enumerate(cols) if j != t_idx]
    data = np.delete(arr, t_idx, axis=1)
    in_deg = header.get("inDegrees", "yes").lower() == "yes"
    return Table(columns=data_cols, data=data, time=arr[:, t_idx], in_degrees=in_deg, header=header)


def write_table(path, columns, data, time, in_degrees=True, name=None):
    path = Path(path)
    data = np.asarray(data, dtype=float)
    lines = [
        name or path.stem,
        "version=1",
        f"nRows={data.shape[0]}",
        f"nColumns={data.shape[1] + 1}",
        f"inDegrees={'yes' if in_degrees else 'no'}",
        "endheader",
        "time\t" + "\t".join(columns),
    ]
    for t, row in zip(time, data):
        lines.append(f"{t:.6f}\t" + "\t".join(f"{v:.8f}" for v in row))
    path.write_text("\n".join(lines) + "\n")
    return path
