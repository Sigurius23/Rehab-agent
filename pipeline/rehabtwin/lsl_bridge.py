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

Streams carry the session they belong to (``session_id``, ``front_end`` in the stream
description and in ``source_id``). ``run_live`` refuses ambiguous resolves and downgrades to
Tier C (no cues, diagnostics only) when the posture stream is not the session's own front end:
an unvalidated IMU stream must not inherit a video session's approval. LSL streams are visible
to every host on the local network; run the live loop on a trusted network only.
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


def posture_info(pylsl, names, rate, session_id="", front_end="", name=POSTURE_STREAM):
    """StreamInfo for a posture stream, tagged with the session and front end it comes from."""
    info = pylsl.StreamInfo(name, "Posture", len(names), rate, "float32", f"{name}:{session_id}:{front_end}")
    info.desc().append_child_value("session_id", session_id)
    info.desc().append_child_value("front_end", front_end)
    ch = info.desc().append_child("channels")
    for n in names:
        c = ch.append_child("channel")
        c.append_child_value("label", n)
        c.append_child_value("unit", "deg")
    return info


def resolve_one(pylsl, name, timeout):
    """The single stream called ``name``; refuses none or several (no silent first-match)."""
    found = pylsl.resolve_byprop("name", name, timeout=timeout)
    if not found:
        raise RuntimeError(f"no LSL stream named {name!r}")
    if len({f.source_id() for f in found}) > 1:
        raise RuntimeError(f"{len(found)} LSL streams named {name!r} ({', '.join(f.source_id() for f in found)}): "
                           "refusing to guess which one drives feedback")
    return found[0]


def stream_posture(time_s, signals, speed=1.0, name=POSTURE_STREAM, wait_for_consumer_s=5.0, session_id="",
                   front_end=""):
    """Push recorded posture signals as an irregular-rate float stream with channel labels."""
    pylsl = _lsl()
    names = list(signals)
    info = posture_info(pylsl, names, pylsl.IRREGULAR_RATE, session_id, front_end, name)
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


def stream_tags(inlet):
    desc = inlet.info().desc()
    return desc.child_value("session_id"), desc.child_value("front_end")


def run_live(spec, tier, allowed_joint_planes, duration_s=None, source=POSTURE_STREAM, publish_would_cue=False,
             resolve_timeout=10.0, idle_timeout=2.0, expect_session=None, expect_front_end=None, baselines=None,
             holds=None, safety=None):
    """Real-time loop: posture stream in, cue markers out. Returns the engine (log in ``engine.log``).
    ``baselines``/``holds``/``safety``: the person's standing values, screening holds and clinician safety flags
    (rehabtwin/feedback.py).

    With ``expect_session``/``expect_front_end`` the posture stream must carry the same tags,
    otherwise the engine runs at Tier C (nothing is sent) and the mismatch is logged.
    """
    pylsl = _lsl()
    inlet = pylsl.StreamInlet(resolve_one(pylsl, source, resolve_timeout))
    labels = channel_labels(inlet)
    sid, fe = stream_tags(inlet)
    mismatch = []
    if expect_session is not None and sid != expect_session:
        mismatch.append(f"stream session {sid or 'untagged'!r} != {expect_session!r}")
    if expect_front_end is not None and fe != expect_front_end:
        mismatch.append(f"stream front end {fe or 'untagged'!r} != {expect_front_end!r}")
    if mismatch:
        tier, allowed_joint_planes = "C", ()
    out = pylsl.StreamOutlet(pylsl.StreamInfo(CUE_STREAM, "Markers", 1, pylsl.IRREGULAR_RATE, "string",
                                              f"{CUE_STREAM}:{expect_session or sid}"))
    eng = CueEngine(spec, tier=tier, allowed_joint_planes=tuple(allowed_joint_planes), baselines=dict(baselines or {}),
                    holds=dict(holds or {}), safety=dict(safety or {}))
    if mismatch:
        eng.log.append({"t": 0.0, "event": "source_mismatch", "reason": "; ".join(mismatch) + " -> Tier C, no cues"})
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
    try:
        inlet = pylsl.StreamInlet(resolve_one(pylsl, source, resolve_timeout))
    except RuntimeError as e:
        if "no LSL stream" in str(e):
            return []
        raise
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
