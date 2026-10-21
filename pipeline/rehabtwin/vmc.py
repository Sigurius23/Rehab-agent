"""IMU suit (SlimeVR) → live posture signals, via the VMC protocol (OSC over UDP).

SlimeVR-Server can send the solved skeleton as VMC (Settings → OSC → VMC,
default port 39539): every frame a bundle with ``/VMC/Ext/Root/Pos`` and one
``/VMC/Ext/Bone/Pos name px py pz qx qy qz qw`` per Unity humanoid bone, as
*local* transforms in Unity's left-handed frame. This module rebuilds global
joint positions by forward kinematics and computes the same posture signals the
video pipeline produces (``torso.sagittal``, ``torso.frontal``, ``knee_fppa_r/l``,
``knee_angle_r/l``, approximate ``lumbar_total.sagittal``), so one rule set
(``configs/feedback``) and one ``CueEngine`` serve video replay and the live suit.

    SlimeVR trackers ─► SlimeVR-Server ─VMC/OSC─► VMCPose ─LSL "rehabtwin_posture"─► rehabtwin lsl-live ─► cues

Accuracy: consumer IMU trackers on a generic skeleton are Tier C until validated
(docs/accuracy.md); IMU yaw drifts, so transverse-plane signals are not offered.
"""
from __future__ import annotations

import threading
import time

import numpy as np

from .kinematics import _fppa

# Unity humanoid hierarchy (child -> parent candidates, first present wins)
PARENTS = {
    "Hips": (), "Spine": ("Hips",), "Chest": ("Spine", "Hips"), "UpperChest": ("Chest", "Spine", "Hips"),
    "Neck": ("UpperChest", "Chest", "Spine", "Hips"), "Head": ("Neck", "UpperChest", "Chest"),
    "LeftUpperLeg": ("Hips",), "LeftLowerLeg": ("LeftUpperLeg",), "LeftFoot": ("LeftLowerLeg",), "LeftToes": ("LeftFoot",),
    "RightUpperLeg": ("Hips",), "RightLowerLeg": ("RightUpperLeg",), "RightFoot": ("RightLowerLeg",), "RightToes": ("RightFoot",),
    "LeftShoulder": ("UpperChest", "Chest"), "LeftUpperArm": ("LeftShoulder", "UpperChest", "Chest"),
    "LeftLowerArm": ("LeftUpperArm",), "LeftHand": ("LeftLowerArm",),
    "RightShoulder": ("UpperChest", "Chest"), "RightUpperArm": ("RightShoulder", "UpperChest", "Chest"),
    "RightLowerArm": ("RightUpperArm",), "RightHand": ("RightLowerArm",),
}
SIGNALS = ["torso.sagittal", "torso.frontal", "knee_angle_r", "knee_angle_l", "knee_fppa_r", "knee_fppa_l",
           "lumbar_total.sagittal"]


def quat_to_matrix(q):
    x, y, z, w = q
    n = np.sqrt(x * x + y * y + z * z + w * w) or 1.0
    x, y, z, w = x / n, y / n, z / n, w / n
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def unity_to_rh(p, q):
    """Unity left-handed (x, y, z | qx, qy, qz, qw) -> right-handed y-up (inverse of SlimeVR's mirror)."""
    return np.array([p[0], p[1], -p[2]], float), np.array([-q[0], -q[1], q[2], q[3]], float)


def rh_to_unity(p, q):
    """Right-handed -> Unity, exactly as SlimeVR's VMCHandler.addTransformToArgs writes it."""
    return [p[0], p[1], -p[2]], [q[0], q[1], -q[2], -q[3]]


class VMCPose:
    """Latest VMC skeleton (thread-safe) with forward kinematics and posture signals."""

    def __init__(self):
        self.local = {}
        self.root = (np.zeros(3), np.array([0.0, 0.0, 0.0, 1.0]))
        self.lock = threading.Lock()
        self.frames = 0

    # OSC handlers (python-osc dispatcher signature: address, *args)
    def on_bone(self, address, name, px, py, pz, qx, qy, qz, qw):
        with self.lock:
            self.local[str(name)] = unity_to_rh((px, py, pz), (qx, qy, qz, qw))

    def on_root(self, address, name, px, py, pz, qx, qy, qz, qw, *rest):
        with self.lock:
            self.root = unity_to_rh((px, py, pz), (qx, qy, qz, qw))
            self.frames += 1

    def global_positions(self):
        with self.lock:
            local = dict(self.local)
            rp, rq = self.root
        pos, rot = {}, {}
        R0 = quat_to_matrix(rq)

        def solve(b):
            if b in pos:
                return True
            if b not in local:
                return False
            t, q = local[b]
            parent = next((p for p in PARENTS.get(b, ()) if p in local), None)
            if parent is None:
                pos[b], rot[b] = rp + R0 @ t, R0 @ quat_to_matrix(q)
            else:
                solve(parent)
                pos[b] = pos[parent] + rot[parent] @ t
                rot[b] = rot[parent] @ quat_to_matrix(q)
            return True

        for b in local:
            solve(b)
        return pos

    def signals(self):
        return posture_signals(self.global_positions())


def _unit(v):
    n = np.linalg.norm(v)
    return v / n if n > 1e-9 else v


def posture_signals(pos):
    """Posture signals (deg) from global joint positions in a right-handed y-up frame."""
    need = ("Hips", "LeftUpperLeg", "RightUpperLeg")
    if not all(k in pos for k in need):
        return {}
    up = np.array([0.0, 1.0, 0.0])
    right = pos["RightUpperLeg"] - pos["LeftUpperLeg"]
    right[1] = 0.0
    right = _unit(right)
    fwd = np.cross(up, right)
    out = {}
    top = next((pos[k] for k in ("Neck", "UpperChest", "Chest") if k in pos), None)
    if top is not None:
        v = _unit(top - pos["Hips"])
        out["torso.sagittal"] = float(np.degrees(np.arctan2(v @ fwd, v @ up)))
        out["torso.frontal"] = float(np.degrees(np.arcsin(np.clip(v @ right, -1, 1))))
    for s, side in (("r", "Right"), ("l", "Left")):
        h, k, a = (pos.get(f"{side}{n}") for n in ("UpperLeg", "LowerLeg", "Foot"))
        if h is None or k is None or a is None:
            continue
        thigh, shank = _unit(k - h), _unit(a - k)
        out[f"knee_angle_{s}"] = float(np.degrees(np.arccos(np.clip(thigh @ shank, -1, 1))))
        out[f"knee_fppa_{s}"] = float(_fppa(h, k, a, fwd, up, right, s))
    if all(k in pos for k in ("Spine", "Chest")) and ("Neck" in pos or "UpperChest" in pos):
        pelvis = _unit(pos["Spine"] - pos["Hips"])
        chest = _unit((pos.get("Neck") if "Neck" in pos else pos["UpperChest"]) - pos["Chest"])
        # sagittal angle between pelvis and upper-trunk directions; flexion negative (OpenSim sign)
        a_p = np.arctan2(pelvis @ fwd, pelvis @ up)
        a_c = np.arctan2(chest @ fwd, chest @ up)
        out["lumbar_total.sagittal"] = float(-np.degrees(a_c - a_p))
    return out


def serve(port=39539, rate_hz=60.0, duration_s=None, publish_lsl=True, on_signals=None, host="0.0.0.0"):
    """Receive VMC, sample posture at ``rate_hz``; publish an LSL posture stream and/or call ``on_signals``."""
    from pythonosc import dispatcher, osc_server
    pose = VMCPose()
    d = dispatcher.Dispatcher()
    d.map("/VMC/Ext/Bone/Pos", pose.on_bone)
    d.map("/VMC/Ext/Root/Pos", pose.on_root)
    server = osc_server.ThreadingOSCUDPServer((host, port), d)
    th = threading.Thread(target=server.serve_forever, daemon=True)
    th.start()
    outlet = None
    if publish_lsl:
        import pylsl
        info = pylsl.StreamInfo("rehabtwin_posture", "Posture", len(SIGNALS), rate_hz, "float32", "rehabtwin_posture_vmc")
        ch = info.desc().append_child("channels")
        for n in SIGNALS:
            c = ch.append_child("channel")
            c.append_child_value("label", n)
            c.append_child_value("unit", "deg")
        outlet = pylsl.StreamOutlet(info)
    t0 = time.monotonic()
    try:
        while duration_s is None or time.monotonic() - t0 < duration_s:
            time.sleep(1.0 / rate_hz)
            if not pose.frames:
                continue
            sig = pose.signals()
            if not sig:
                continue
            if outlet is not None:
                outlet.push_sample([float(sig.get(n, np.nan)) for n in SIGNALS])
            if on_signals is not None:
                on_signals(time.monotonic() - t0, sig)
    finally:
        server.shutdown()
    return pose
