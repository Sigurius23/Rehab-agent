"""Cue markers → haptic suit (SenseShift / bHaptics-protocol BLE devices).

    LSL "rehabtwin_cues" ─► SuitDriver (actuator → motors, pattern envelopes, ~20 Hz frames)
                          ─► payload encoders ─► transport (dry-run log | BLE write)

SenseShift firmware (senseshift/senseshift-firmware, GPL-3.0) implements the
bHaptics BLE protocol on DIY ESP32 hardware:
* vest (TactSuit X40): 20-byte payload, two 4-bit intensities per byte
  (high nibble = motor 2i, low nibble = motor 2i+1), written to the NUS RX
  characteristic ``6e400002-…`` (write without response);
* sleeves/accessories (e.g. Tactosy2, 6 motors): one byte per motor, 0–100.

Motor layouts are parsed at run time from your SenseShift clone
(``lib/bhaptics/senseshift/bh/devices.hpp``) rather than copied here.
Which way a layout's x axis faces on the body must be checked on the
hardware once; the mapping file says which motors each cue uses.

Safety: SenseShift keeps a motor at its last level until told otherwise, so the bridge always
ends with an all-off frame (normal end, Ctrl-C or error). Each cue is capped in duration and
intensity, and each actuator in on-time share over a sliding window (mapping ``limits`` may
lower these caps, never raise them).
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .config import CONFIG_DIR, upstream_root

BH_SERVICE = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
BH_MOTOR_CHAR = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"
DEVICE_TYPES = {  # layout macro, payload encoding
    "tactsuit_x40": ("TACTSUITX40", "vest"),
    "tactosy2": ("TACTOSY2", "plain"),
    "tactosyf": ("TACTOSYF", "plain"),
    "tactosyh": ("TACTOSYH", "plain"),
}


def devices_header():
    return upstream_root() / "senseshift" / "senseshift-firmware" / "lib" / "bhaptics" / "senseshift" / "bh" / "devices.hpp"


def parse_layout(macro, header=None):
    """[(target, x, y)] in motor-index order for a SenseShift BH_LAYOUT_<macro> table."""
    text = Path(header or devices_header()).read_text()
    m = re.search(rf"#define BH_LAYOUT_{macro} \{{(.*?)\n\s*\}}", text, re.S)
    if not m:
        raise ValueError(f"BH_LAYOUT_{macro} not found in {header or devices_header()}")
    body = m.group(1)
    entries = re.findall(rf"(?:\{{\s*Target::(\w+),\s*)?BH_LAYOUT_{macro}_MAKE_POINT\((\d+),\s*(\d+)\)", body)
    return [(t or "Accessory", int(x), int(y)) for t, x, y in entries]


def encode_vest(levels):
    """40 levels in [0, 1] -> 20-byte bHaptics vest payload (4-bit per motor)."""
    q = np.clip(np.rint(np.asarray(levels, float) * 15), 0, 15).astype(int)
    if len(q) != 40:
        raise ValueError("vest payload needs 40 motor levels")
    return bytes(int((q[2 * i] << 4) | q[2 * i + 1]) for i in range(20))


def encode_plain(levels):
    """N levels in [0, 1] -> N bytes (0..100), the accessory encoding."""
    return bytes(int(v) for v in np.clip(np.rint(np.asarray(levels, float) * 100), 0, 100))


def envelope(pattern, t, duration_s):
    """On/off envelope (0/1) of a cue pattern at time t after its start."""
    if t < 0 or t >= duration_s:
        return 0.0
    u = t / duration_s
    if pattern == "double":
        return 1.0 if (u < 0.4 or u >= 0.6) else 0.0
    if pattern == "triple":
        return 1.0 if (u % (1 / 3)) < (0.7 / 3) else 0.0
    return 1.0  # "pulse", "long": continuous for the duration


def load_mapping(name_or_path, header=None):
    p = Path(name_or_path)
    if not p.suffix:
        p = CONFIG_DIR / "feedback" / f"{name_or_path}.json"
    spec = json.loads(p.read_text())
    layouts = {}
    for dev, d in spec["devices"].items():
        macro, enc = DEVICE_TYPES[d["type"]]
        layouts[dev] = (parse_layout(macro, header), enc)
    motors = {}
    for act, a in spec["actuators"].items():
        layout, _ = layouts[a["device"]]
        sel = a.get("select", {})
        idx = [i for i, (tgt, x, y) in enumerate(layout)
               if (not sel.get("target") or tgt == sel["target"])
               and (sel.get("x") is None or x in sel["x"]) and (sel.get("y") is None or y in sel["y"])]
        if not idx:
            raise ValueError(f"{p}: actuator {act!r} selects no motor")
        motors[act] = (a["device"], idx)
    return spec, layouts, motors


@dataclass
class _Active:
    device: str
    motors: list
    start: float
    duration: float
    pattern: str
    intensity: float


LIMITS = {"max_cue_ms": 1000.0, "max_intensity": 0.8, "max_on_share": 0.3, "window_s": 10.0}


class SuitDriver:
    """Turns cue commands into per-device payload frames, within hard safety caps."""

    def __init__(self, mapping, header=None):
        self.spec, self.layouts, self.motors = load_mapping(mapping, header)
        lim = self.spec.get("limits", {})
        self.limits = {k: min(float(lim.get(k, v)), v) if k != "window_s" else float(lim.get(k, v))
                       for k, v in LIMITS.items()}
        self.active = []
        self.unknown = set()
        self.rejected = []
        self.history = {}           # actuator -> [(start, duration)] inside the duty window

    def add(self, cmd, now):
        act = cmd["actuator"]
        if act not in self.motors:
            self.unknown.add(act)
            return False
        lim = self.limits
        dur = min(max(float(cmd.get("duration_ms", 250)), 0.0), lim["max_cue_ms"]) / 1000.0
        inten = min(max(float(cmd.get("intensity", 0.5)), 0.0), lim["max_intensity"])
        hist = [(t0, d) for t0, d in self.history.get(act, []) if t0 + d > now - lim["window_s"]]
        on = sum(min(t0 + d, now) - max(t0, now - lim["window_s"]) for t0, d in hist if t0 < now)
        if (on + dur) / lim["window_s"] > lim["max_on_share"]:
            self.rejected.append({"t": round(now, 3), "actuator": act, "reason": "on-time share cap"})
            self.history[act] = hist
            return False
        hist.append((now, dur))
        self.history[act] = hist
        dev, idx = self.motors[act]
        self.active.append(_Active(dev, idx, now, dur, cmd.get("pattern", "pulse"), inten))
        return True

    def all_off(self):
        """Zero payload for every device (stops every motor)."""
        self.active = []
        return {dev: (encode_vest(np.zeros(len(layout))) if enc == "vest" else encode_plain(np.zeros(len(layout))))
                for dev, (layout, enc) in self.layouts.items()}

    def frame(self, now):
        """{device: payload bytes} for every device (all-zero payload when idle, which stops the motors)."""
        levels = {dev: np.zeros(len(layout)) for dev, (layout, _) in self.layouts.items()}
        keep = []
        for a in self.active:
            e = envelope(a.pattern, now - a.start, a.duration)
            if now - a.start < a.duration:
                keep.append(a)
            if e > 0:
                lv = levels[a.device]
                lv[a.motors] = np.maximum(lv[a.motors], a.intensity * e)
        self.active = keep
        return {dev: (encode_vest(lv) if self.layouts[dev][1] == "vest" else encode_plain(lv))
                for dev, lv in levels.items()}


class DryRunTransport:
    """Logs payloads that changed (what would be written over BLE)."""

    def __init__(self):
        self.log, self.last = [], {}

    def send(self, device, payload, t, force=False):
        if force or self.last.get(device) != payload:
            self.last[device] = payload
            self.log.append({"t": round(t, 3), "device": device, "payload_hex": payload.hex()})

    def close(self):
        pass


class BleTransport:  # pragma: no cover - needs hardware
    """Writes payloads to SenseShift/bHaptics devices with bleak (pip install bleak)."""

    def __init__(self, addresses, devices=None):
        import asyncio
        from bleak import BleakClient
        unknown = sorted(set(addresses) - set(devices or addresses))
        if unknown:
            raise ValueError(f"--ble names {unknown} are not devices in the mapping ({sorted(devices)})")
        self.loop = asyncio.new_event_loop()
        self.clients = {dev: BleakClient(addr) for dev, addr in addresses.items()}
        for c in self.clients.values():
            self.loop.run_until_complete(c.connect())
        self.last = {}

    def send(self, device, payload, t, force=False):
        if device not in self.clients or (not force and self.last.get(device) == payload):
            return
        self.last[device] = payload
        # all-off frames go with response, so the stop is acknowledged
        self.loop.run_until_complete(self.clients[device].write_gatt_char(BH_MOTOR_CHAR, payload, response=force))

    def close(self):
        for c in self.clients.values():
            try:
                self.loop.run_until_complete(c.disconnect())
            except Exception:
                pass


def run_bridge(driver, transport, duration_s=None, rate_hz=20.0, source="rehabtwin_cues", resolve_timeout=10.0):
    """LSL cue markers -> payload frames at ``rate_hz`` until ``duration_s`` (or forever)."""
    import pylsl
    from .lsl_bridge import resolve_one
    inlet = pylsl.StreamInlet(resolve_one(pylsl, source, resolve_timeout))
    t0 = time.monotonic()
    now = 0.0
    try:
        while duration_s is None or time.monotonic() - t0 < duration_s:
            now = time.monotonic() - t0
            while True:
                sample, _ = inlet.pull_sample(timeout=0.0)
                if sample is None:
                    break
                cmd = json.loads(sample[0])
                if "diagnostic" not in cmd:     # would_cue diagnostics never drive motors
                    driver.add(cmd, now)
            for dev, payload in driver.frame(now).items():
                transport.send(dev, payload, now)
            time.sleep(1.0 / rate_hz)
    finally:
        # whatever ended the loop (duration, Ctrl-C, an exception), leave every motor off
        for dev, payload in driver.all_off().items():
            transport.send(dev, payload, now, force=True)
        transport.close()
    return transport
