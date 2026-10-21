"""Lab Streaming Layer bridge for live haptic cues (needs ``pip install pylsl``).

    posture source ──LSL "rehabtwin_posture" (float channels = signal names)──►
        CueEngine (rehabtwin.feedback) ──LSL "rehabtwin_cues" (JSON markers)──► suit firmware bridge

LSL is already the project's sync layer (docs/hardware.md), so cues land in
the same XDF recording as video/IMU/EMG and can be audited afterwards.

* ``stream_posture``: replays a recorded session's posture signals as a live
  stream (testing without hardware, or demoing a rule set);
* ``run_live``: the real-time loop — gating is the same as offline: cues are
  only sent for a Tier-A twin on validated joint/planes, everything else is
  published on the cue stream as a ``would_cue`` diagnostic only if asked;
* ``listen``: prints received cues (stand-in for the firmware bridge).
"""
from __future__ import annotations

import json
import time

import numpy as np

from .feedback import CueEngine

POSTURE_STREAM = "rehabtwin_posture"
CUE_STREAM = "rehabtwin_cues"


def _lsl():
    try:
        import pylsl
    except ImportError as e:  # pragma: no cover
        raise ImportError("live cues need pylsl: pip install pylsl") from e
    return pylsl


def stream_posture(time_s, signals, speed=1.0, name=POSTURE_STREAM, wait_for_consumer_s=5.0):
    """Push recorded posture signals as an irregular-rate float stream with channel labels."""
    pylsl = _lsl()
    names = list(signals)
    info = pylsl.StreamInfo(name, "Posture", len(names), pylsl.IRREGULAR_RATE, "float32", f"{name}_uid")
    ch = info.desc().append_child("channels")
    for n in names:
        c = ch.append_child("channel")
        c.append_child_value("label", n)
        c.append_child_value("unit", "deg")
    out = pylsl.StreamOutlet(info)
    out.wait_for_consumers(wait_for_consumer_s)
    t0, stamp0 = time.monotonic(), pylsl.local_clock()
    for k, t in enumerate(time_s):
        delay = (t - time_s[0]) / speed - (time.monotonic() - t0)
        if delay > 0:
            time.sleep(delay)
        # stamped on the recording's own timeline, so rule durations mean the same at any replay speed
        out.push_sample([float(signals[n][k]) for n in names], stamp0 + (t - time_s[0]))
    return len(time_s)


def channel_labels(inlet):
    info = inlet.info()
    ch = info.desc().child("channels").child("channel")
    labels = []
    for _ in range(info.channel_count()):
        labels.append(ch.child_value("label"))
        ch = ch.next_sibling()
    return labels


def run_live(spec, tier, allowed_joint_planes, duration_s=None, source=POSTURE_STREAM, publish_would_cue=False,
             resolve_timeout=10.0, idle_timeout=2.0):
    """Real-time loop: posture stream in, cue markers out. Returns the engine (log in ``engine.log``)."""
    pylsl = _lsl()
    found = pylsl.resolve_byprop("name", source, timeout=resolve_timeout)
    if not found:
        raise RuntimeError(f"no LSL stream named {source!r}")
    inlet = pylsl.StreamInlet(found[0])
    labels = channel_labels(inlet)
    out = pylsl.StreamOutlet(pylsl.StreamInfo(CUE_STREAM, "Markers", 1, pylsl.IRREGULAR_RATE, "string", f"{CUE_STREAM}_uid"))
    eng = CueEngine(spec, tier=tier, allowed_joint_planes=tuple(allowed_joint_planes))
    t_start, t_first = time.monotonic(), None
    while duration_s is None or time.monotonic() - t_start < duration_s:
        sample, ts = inlet.pull_sample(timeout=idle_timeout)
        if sample is None:
            if t_first is not None:
                break           # source went quiet: end of a replay
            continue
        t_first = ts if t_first is None else t_first
        n_log = len(eng.log)
        for cmd in eng.update(ts - t_first, dict(zip(labels, sample))):
            out.push_sample([json.dumps(cmd)])
        if publish_would_cue:
            for e in eng.log[n_log:]:
                if e.get("decision") == "would_cue":
                    out.push_sample([json.dumps({"diagnostic": "would_cue", **e})])
    return eng


def listen(duration_s=10.0, source=CUE_STREAM, resolve_timeout=10.0):
    """Collect cue markers for ``duration_s`` (what a suit bridge would receive)."""
    pylsl = _lsl()
    found = pylsl.resolve_byprop("name", source, timeout=resolve_timeout)
    if not found:
        return []
    inlet = pylsl.StreamInlet(found[0])
    got, t0 = [], time.monotonic()
    while time.monotonic() - t0 < duration_s:
        sample, ts = inlet.pull_sample(timeout=0.5)
        if sample:
            got.append(json.loads(sample[0]))
    return got


def session_signals(tab, derived, names):
    """Posture signals of a processed session restricted to the names a rule set uses."""
    all_sig = {c: tab.col(c) for c in tab.columns}
    all_sig.update(derived)
    return {n: np.asarray(all_sig[n], float) for n in names if n in all_sig}
