"""Arrays into one binary file for the 3D page."""
from pathlib import Path

import numpy as np


class Pack:
    """Arrays into one little-endian binary file, described by name -> [dtype, shape, offset] (+ scale)."""
    def __init__(self):
        self.parts, self.index, self.size = [], {}, 0

    def add(self, name, a, dtype, scale=None):
        a = np.asarray(a)
        q = np.round(a / scale).astype(dtype) if scale else a.astype(dtype)
        if scale:
            assert np.abs(q.astype(float) * scale - a).max() <= scale, name
        b = q.tobytes()
        pad = (-self.size) % 4
        self.parts.append(b"\0" * pad)
        self.size += pad
        self.index[name] = {"dtype": np.dtype(dtype).name, "shape": list(q.shape), "offset": self.size,
                            **({"scale": scale} if scale else {})}
        self.parts.append(b)
        self.size += len(b)

    def write(self, path):
        Path(path).write_bytes(b"".join(self.parts))
        return self.index
