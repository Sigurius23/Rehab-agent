"""Convert MPI body-model downloads (SMPL, SKEL, OSSO; Python pickles) to plain .npz arrays, without running them.

The model files from smpl.is.tue.mpg.de, skel.is.tue.mpg.de and osso.is.tue.mpg.de are pickles, and unpickling
a file can run any code it names. This reads them with an unpickler that only builds what these files are
made of: numpy arrays, scipy sparse matrices, chumpy arrays (SMPL 1.x; their numeric value is kept, chumpy is
not imported), sets, ranges, plain objects and the string encoder Python 3 uses for raw bytes. Any other name a file asks for is refused before it is used.
The result is one .npz per pickle that loads with ``allow_pickle=False``:

- chumpy arrays become their values, sparse matrices dense arrays, ranges integer arrays;
- nested dicts and lists are flattened to "a/b/0" keys; keys that held None are listed in "__none__";
- a manifest (manifest.json) records each source's sha256 and its arrays.

The downloads are licensed separately (non-commercial research) and stay outside the repository, as does
the converted output.

    python -I adapters/body_model_files.py convert DOWNLOAD_DIR OUT_DIR     # every .pkl below DOWNLOAD_DIR
"""
from __future__ import annotations

import argparse
import codecs
import copyreg
import hashlib
import io
import json
import pickle
import pickletools
import sys
from pathlib import Path

import numpy as np


class Ch:
    """Stands in for chumpy.ch.Ch: keeps the pickled state, runs nothing."""

    def __setstate__(self, state):
        self.state = state


def _reconstruct(*a):
    try:
        from numpy._core.multiarray import _reconstruct as r
    except ImportError:                                   # numpy < 2
        from numpy.core.multiarray import _reconstruct as r
    return r(*a)


def _allowed():
    import scipy.sparse
    return {("copy_reg", "_reconstructor"): copyreg._reconstructor, ("copyreg", "_reconstructor"): copyreg._reconstructor,
            ("__builtin__", "object"): object, ("builtins", "object"): object,
            ("__builtin__", "set"): set, ("builtins", "set"): set, ("builtins", "range"): range, ("__builtin__", "xrange"): range,
            ("numpy.core.multiarray", "_reconstruct"): _reconstruct, ("numpy._core.multiarray", "_reconstruct"): _reconstruct,
            ("numpy", "ndarray"): np.ndarray, ("numpy", "dtype"): np.dtype,
            ("scipy.sparse.csc", "csc_matrix"): scipy.sparse.csc_matrix,
            ("scipy.sparse._csc", "csc_matrix"): scipy.sparse.csc_matrix,
            ("scipy.sparse._coo", "coo_matrix"): scipy.sparse.coo_matrix,
            ("scipy.sparse.coo", "coo_matrix"): scipy.sparse.coo_matrix,
            ("chumpy.ch", "Ch"): Ch, ("_codecs", "encode"): codecs.encode}   # bytes in protocol-2 pickles from Python 3


class Restricted(pickle.Unpickler):
    def __init__(self, fh):
        super().__init__(fh, encoding="latin1")
        self.allowed = _allowed()

    def find_class(self, module, name):
        if (module, name) not in self.allowed:
            raise pickle.UnpicklingError(f"refused {module}.{name}: not part of a body-model file")
        return self.allowed[(module, name)]


def load(data):
    """The object in pickle bytes ``data``, built only from the allowed names."""
    if any(op.name.startswith("EXT") for op, _, _ in pickletools.genops(data)):
        raise pickle.UnpicklingError("uses the copyreg extension registry")
    return Restricted(io.BytesIO(data)).load()


def _value(x):
    import scipy.sparse
    if isinstance(x, Ch):
        s = x.state
        return _value(s.get("x", s.get("a")) if isinstance(s, dict) else s)
    if scipy.sparse.issparse(x):
        return x.toarray()
    if isinstance(x, range):
        return np.arange(x.start, x.stop, x.step)
    return x


def flatten(obj, prefix="", none=None):
    """{"a/b": array} of a pickled body-model object; ``none`` collects the keys that held None."""
    none = [] if none is None else none
    obj = _value(obj)
    key = prefix.rstrip("/") or "value"
    if obj is None:
        none.append(key)
        return {}
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            out.update(flatten(v, f"{prefix}{k}/", none))
        return out
    if isinstance(obj, (list, tuple)) and obj:
        try:
            a = None if any(_value(v) is None for v in obj) else np.asarray([_value(v) for v in obj])
        except ValueError:                                # ragged
            a = None
        if a is None or a.dtype == object:
            out = {}
            for i, v in enumerate(obj):
                out.update(flatten(v, f"{prefix}{i}/", none))
            return out
        return {key: a}
    a = np.asarray(obj)
    if a.dtype == object:
        raise ValueError(f"{key}: {type(obj).__name__} is not a plain array")
    return {key: a}


def convert(src_dir, out_dir):
    """Every .pkl below ``src_dir`` -> OUT_DIR/<name>.npz and OUT_DIR/manifest.json; returns the manifest."""
    src, dst = Path(src_dir), Path(out_dir)
    dst.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for f in sorted(src.rglob("*.pkl")):
        data = f.read_bytes()
        none = []
        arrays = flatten(load(data), none=none)
        if none:
            arrays["__none__"] = np.array(none)
        out = dst / (f.stem + ".npz")
        if out.name in {m["npz"] for m in manifest.values()}:
            raise ValueError(f"two files named {f.stem}.pkl below {src}: convert them separately")
        np.savez(out, **arrays)
        with np.load(out, allow_pickle=False) as check:          # the result needs no pickle
            assert sorted(check.files) == sorted(arrays)
        manifest[str(f.relative_to(src))] = {"source_sha256": hashlib.sha256(data).hexdigest(), "npz": out.name,
                                             "arrays": {k: [list(v.shape), str(v.dtype)] for k, v in arrays.items()}}
        print(f"{f.relative_to(src)} -> {out.name} ({len(arrays)} arrays)", file=sys.stderr)
    (dst / "manifest.json").write_text(json.dumps(manifest, indent=1))
    return manifest


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("convert", help="every .pkl below a folder to .npz (refusing anything but arrays)")
    c.add_argument("src_dir")
    c.add_argument("out_dir")
    a = ap.parse_args(argv)
    convert(a.src_dir, a.out_dir)


if __name__ == "__main__":
    main()
