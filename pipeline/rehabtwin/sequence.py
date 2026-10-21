"""The file contract between a video front-end and the OpenSim stage.

A front-end (HSMR+SKEL, MediaPipe, synthetic generator, ...) writes one
``MarkerSequence`` as ``.npz``. The OpenSim stage only ever reads this file,
so front-ends can be swapped without touching the back-end.

Frames
------
``frame`` names the coordinate frame of ``markers``/``joints``:

* ``opencv_camera`` — x right, y down, z forward from the camera (HSMR, MediaPipe world)
* ``yup_world``     — gravity-aligned, y up, arbitrary heading
* ``opensim``       — OpenSim ground: x forward (subject heading), y up, z right

``static_markers``/``static_joints`` (optional) describe the subject in the
model's neutral pose (SKEL q = 0, which is the BSM/OpenSim default pose) in
any rigid frame — they are only used for scaling and are rigidly registered
to the model before use.

Optional ``meta["gravity_up_cv"]`` (3,) is the up direction measured by the
recording device (phone IMU, calibration) in OpenCV camera coordinates; it
takes precedence over image-based gravity estimates.

Missing data is NaN and ``valid`` is False — nothing is silently filled in
here (docs/architecture.md, "no stage silently imputes").
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

FRAMES = ("opencv_camera", "yup_world", "opensim")
SCHEMA_VERSION = 1


@dataclass
class MarkerSequence:
    fps: float
    marker_names: list
    markers: np.ndarray            # (T, M, 3) metres
    frame: str
    valid: np.ndarray | None = None          # (T,) bool
    frame_index: np.ndarray | None = None    # (T,) source video frame numbers
    joint_names: list = field(default_factory=list)
    joints: np.ndarray | None = None         # (T, J, 3) metres
    static_markers: np.ndarray | None = None  # (M, 3)
    static_joints: np.ndarray | None = None   # (J, 3)
    skel_poses: np.ndarray | None = None     # (T, 46) radians, SKEL q
    skel_betas: np.ndarray | None = None     # (T, 10)
    meta: dict = field(default_factory=dict)

    def __post_init__(self):
        self.markers = np.asarray(self.markers, dtype=float)
        self.marker_names = [str(n) for n in self.marker_names]
        self.joint_names = [str(n) for n in self.joint_names]
        T = self.markers.shape[0]
        if self.valid is None:
            self.valid = np.isfinite(self.markers).any(axis=(1, 2))
        if self.frame_index is None:
            self.frame_index = np.arange(T)
        self.valid = np.asarray(self.valid, dtype=bool)
        self.frame_index = np.asarray(self.frame_index, dtype=int)
        self.check()

    # ------------------------------------------------------------------
    @property
    def n_frames(self):
        return self.markers.shape[0]

    @property
    def times(self):
        return self.frame_index / float(self.fps)

    def check(self):
        T, M = self.markers.shape[:2]
        problems = []
        if self.markers.ndim != 3 or self.markers.shape[2] != 3:
            problems.append(f"markers must be (T, M, 3), got {self.markers.shape}")
        if len(self.marker_names) != M:
            problems.append("marker_names length != markers.shape[1]")
        if len(set(self.marker_names)) != M:
            problems.append("duplicate marker names")
        if self.frame not in FRAMES:
            problems.append(f"frame must be one of {FRAMES}, got {self.frame!r}")
        if self.fps <= 0:
            problems.append("fps must be positive")
        if self.valid.shape != (T,) or self.frame_index.shape != (T,):
            problems.append("valid/frame_index must be (T,)")
        if np.any(np.diff(self.frame_index) <= 0):
            problems.append("frame_index must be strictly increasing")
        if self.joints is not None:
            self.joints = np.asarray(self.joints, dtype=float)
            if self.joints.shape[:1] != (T,) or self.joints.shape[1] != len(self.joint_names):
                problems.append("joints must be (T, len(joint_names), 3)")
        if self.static_markers is not None:
            self.static_markers = np.asarray(self.static_markers, dtype=float)
            if self.static_markers.shape != (M, 3):
                problems.append("static_markers must be (M, 3)")
        if self.static_joints is not None:
            self.static_joints = np.asarray(self.static_joints, dtype=float)
            if self.static_joints.shape != (len(self.joint_names), 3):
                problems.append("static_joints must be (J, 3)")
        if problems:
            raise ValueError("invalid MarkerSequence: " + "; ".join(problems))

    # ------------------------------------------------------------------
    def all_points(self, static=False):
        """Markers and joints stacked as one point set: (names, (T, N, 3)) or (N, 3) if static."""
        names = list(self.marker_names)
        if static:
            pts = [self.static_markers]
            if self.static_joints is not None:
                names += self.joint_names
                pts.append(self.static_joints)
            return names, np.concatenate(pts, axis=0)
        pts = [self.markers]
        if self.joints is not None:
            names += self.joint_names
            pts.append(self.joints)
        return names, np.concatenate(pts, axis=1)

    def save(self, path):
        path = Path(path)
        arrays = dict(
            schema_version=np.array(SCHEMA_VERSION),
            fps=np.array(self.fps, dtype=float),
            frame=np.array(self.frame),
            marker_names=np.array(self.marker_names),
            markers=self.markers.astype(np.float32),
            valid=self.valid,
            frame_index=self.frame_index,
            joint_names=np.array(self.joint_names),
            meta_json=np.array(json.dumps(self.meta, sort_keys=True)),
        )
        for key in ("joints", "static_markers", "static_joints", "skel_poses", "skel_betas"):
            val = getattr(self, key)
            if val is not None:
                arrays[key] = np.asarray(val, dtype=np.float32)
        np.savez_compressed(path, **arrays)
        return path

    @classmethod
    def load(cls, path) -> "MarkerSequence":
        z = np.load(Path(path), allow_pickle=False)
        version = int(z["schema_version"]) if "schema_version" in z else 0
        if version != SCHEMA_VERSION:
            raise ValueError(f"{path}: schema_version {version}, expected {SCHEMA_VERSION}")
        opt = {k: z[k] for k in ("joints", "static_markers", "static_joints", "skel_poses", "skel_betas") if k in z}
        return cls(
            fps=float(z["fps"]),
            frame=str(z["frame"]),
            marker_names=[str(n) for n in z["marker_names"]],
            markers=z["markers"],
            valid=z["valid"],
            frame_index=z["frame_index"],
            joint_names=[str(n) for n in z["joint_names"]],
            meta=json.loads(str(z["meta_json"])),
            **opt,
        )

    def subset(self, mask):
        """Frames where ``mask`` is True (used for trimming)."""
        mask = np.asarray(mask, dtype=bool)
        kw = dict(self.__dict__)
        for key in ("markers", "valid", "frame_index", "joints", "skel_poses", "skel_betas"):
            if kw.get(key) is not None:
                kw[key] = kw[key][mask]
        return MarkerSequence(**kw)
