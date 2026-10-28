"""Haptic posture cues (stacks/haptic-exo-suit.md, Track 1): rules → actuator events.

One streaming engine (``CueEngine.update`` per frame) serves both an offline
replay of a recorded session and, later, a live IMU-driven suit.

Design choices from motor-learning practice, all configurable per rule set:
* hysteresis ("bandwidth"): a violation starts beyond the threshold and ends
  only once the signal is back inside it by ``bandwidth_deg``;
* minimum duration: brief excursions do not cue;
* refractory period per actuator: no buzzing storms;
* faded feedback: the fraction of violations that get a cue falls from
  ``start_fraction`` to ``end_fraction`` over ``fade_events`` violations,
  because constant guidance builds dependence on the cue (guidance hypothesis).

Safety gate (docs/accuracy.md): a cue is only *sent* when the twin tier is A
and the rule's joint/plane passed validation. Otherwise the event is logged as
``would_cue`` with the blocking reason, which is still useful for reviewing a
rule set on recorded sessions.

The person's own skeleton (rehabtwin/alignment.py): a rule with ``"relative_to":
"standing"`` compares the signal's change from the person's standing value
(``baselines``) with its threshold, so a knee that stands in valgus is not cued
for standing as it does. Without that baseline the rule is not evaluated. At a
joint/plane in ``flags`` (a structural alignment on record, or a standing angle
beyond the screening threshold) no cue is sent unless the rule says its target was
set by the treating clinician (``"clinician_target": true``).
"""
from __future__ import annotations

import json
import operator
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from .config import CONFIG_DIR

OPS = {">": operator.gt, "<": operator.lt, ">=": operator.ge, "<=": operator.le}


def load_rules(name_or_path):
    p = Path(name_or_path)
    if not p.suffix:
        p = CONFIG_DIR / "feedback" / f"{name_or_path}.json"
    spec = json.loads(p.read_text())
    spec["_path"] = str(p)
    for r in spec["rules"]:
        if r["op"] not in OPS:
            raise ValueError(f"{p}: rule {r['id']}: op must be one of {list(OPS)}")
    return spec


@dataclass
class _RuleState:
    active: bool = False
    since: float = 0.0
    peak: float = 0.0
    cued: bool = False
    events: int = 0
    credit: float = 0.0


def gate_reason(rule, tier, allowed_joint_planes, flags=None):
    """None if the rule's cues may be sent, else the reason they are blocked."""
    if (flags or {}).get(rule["joint_plane"]) and not rule.get("clinician_target"):
        return f"{flags[rule['joint_plane']]}: the target must be set by the treating clinician"
    if tier != "A":
        return f"tier {tier}: feedback requires a Tier-A twin"
    if rule["joint_plane"] not in allowed_joint_planes:
        return f"{rule['joint_plane']} not validated for feedback"
    return None


def needs_baseline(rule, baselines):
    return rule.get("relative_to") == "standing" and (baselines or {}).get(rule["signal"]) is None


@dataclass
class CueEngine:
    spec: dict
    tier: str = "C"
    allowed_joint_planes: tuple = ()
    baselines: dict = field(default_factory=dict)    # {signal: the person's standing value}
    flags: dict = field(default_factory=dict)        # {joint_plane: why cues there wait for a clinician}
    log: list = field(default_factory=list)

    def __post_init__(self):
        for r in self.spec["rules"]:
            if r.get("relative_to") not in (None, "standing"):
                raise ValueError(f"rule {r['id']}: relative_to must be 'standing'")
        self.state = {r["id"]: _RuleState() for r in self.spec["rules"]}
        self.evaluated = {r["id"]: 0 for r in self.spec["rules"]}   # samples where the rule's signal was usable
        self.last_cue = {}
        sch = self.spec.get("schedule", {})
        self.bandwidth = sch.get("bandwidth_deg", 2.0)
        self.refractory = sch.get("refractory_s", 1.0)
        self.f0, self.f1 = sch.get("start_fraction", 1.0), sch.get("end_fraction", 0.33)
        self.fade_n = max(1, sch.get("fade_events", 6))

    def gate(self, rule):
        """None if the cue may be sent, else the reason it is blocked."""
        return gate_reason(rule, self.tier, self.allowed_joint_planes, self.flags)

    def _fraction(self, k):
        """Share of violations that get a cue at violation number k (0-based), linear fade."""
        a = min(k / self.fade_n, 1.0)
        return self.f0 + (self.f1 - self.f0) * a

    def update(self, t, signals):
        """Feed one frame ({signal: value}); returns the actuator commands to send now."""
        out = []
        for r in self.spec["rules"]:
            if r["signal"] not in signals or not np.isfinite(signals[r["signal"]]) or needs_baseline(r, self.baselines):
                continue
            self.evaluated[r["id"]] += 1
            base = self.baselines[r["signal"]] if r.get("relative_to") == "standing" else None
            v = float(signals[r["signal"]]) - (base or 0.0)
            st = self.state[r["id"]]
            op = OPS[r["op"]]
            beyond = op(v, r["threshold"])
            back_inside = not op(v, r["threshold"] - self.bandwidth if r["op"] in (">", ">=") else r["threshold"] + self.bandwidth)
            if not st.active and beyond:
                st.active, st.since, st.peak, st.cued = True, t, v, False
            elif st.active:
                st.peak = max(st.peak, v) if r["op"] in (">", ">=") else min(st.peak, v)
                if back_inside:
                    self._close(r, st, t)
                    continue
            if st.active and not st.cued and t - st.since >= r.get("min_duration_s", 0.2):
                st.cued = True  # decide once per violation
                k = st.events
                st.events += 1
                st.credit += self._fraction(k)
                deliver = st.credit >= 1.0 - 1e-9
                if deliver:
                    st.credit -= 1.0
                cue = r["cue"]
                reason = None
                if not deliver:
                    reason = "faded schedule: withheld to reduce dependence on the cue"
                elif t - self.last_cue.get(cue["actuator"], -np.inf) < self.refractory:
                    reason = "actuator refractory period"
                gate = self.gate(r)
                entry = {"t": round(t, 3), "rule": r["id"], "signal": r["signal"], "value": round(v, 2),
                         "threshold": r["threshold"], "actuator": cue["actuator"], "violation": st.events}
                if base is not None:
                    entry["standing_value"] = round(base, 2)
                if reason:
                    entry["decision"], entry["reason"] = "withheld", reason
                elif gate:
                    entry["decision"], entry["reason"] = "would_cue", gate
                else:
                    entry["decision"] = "cue"
                    self.last_cue[cue["actuator"]] = t
                    out.append({"timestamp": t, "actuator": cue["actuator"], "pattern": cue.get("pattern", "pulse"),
                                "intensity": cue.get("intensity", 0.5), "duration_ms": cue.get("duration_ms", 250),
                                "rule": r["id"], "message": r.get("message", "")})
                self.log.append(entry)
        return out

    def _close(self, r, st, t):
        st.active = False
        self.log.append({"t": round(t, 3), "rule": r["id"], "event": "violation_end", "peak": round(st.peak, 2),
                         "duration_s": round(t - st.since, 3)})


def replay(spec, time, signals, tier="C", allowed_joint_planes=(), baselines=None, flags=None):
    """Run the engine over a recorded session. Returns (engine log, sent commands)."""
    eng = CueEngine(spec, tier=tier, allowed_joint_planes=tuple(allowed_joint_planes), baselines=dict(baselines or {}),
                    flags=dict(flags or {}))
    sent = []
    for k, t in enumerate(time):
        sent += eng.update(float(t), {n: v[k] for n, v in signals.items()})
    for rid, n in eng.evaluated.items():
        eng.log.append({"rule": rid, "event": "evaluated_samples", "n": n, "of": len(time)})
    return eng.log, sent


def summarise(spec, log, sent, tier, allowed, baselines=None, flags=None):
    per_rule = {}
    for r in spec["rules"]:
        ev = [e for e in log if e.get("rule") == r["id"] and "decision" in e]
        ends = [e for e in log if e.get("rule") == r["id"] and e.get("event") == "violation_end"]
        ev_n = next((e["n"] for e in log if e.get("rule") == r["id"] and e.get("event") == "evaluated_samples"), None)
        per_rule[r["id"]] = {
            "evaluated_samples": ev_n,
            # a rule whose signal never arrived reports no violations because it never looked
            "unevaluated": ev_n == 0,
            "violations": len(ev),
            "cues_sent": sum(e["decision"] == "cue" for e in ev),
            "would_cue": sum(e["decision"] == "would_cue" for e in ev),
            "withheld_by_schedule": sum(e.get("reason", "").startswith("faded") for e in ev),
            "peaks": [e["peak"] for e in ends],
            "gate": gate_reason(r, tier, allowed, flags),
        }
        if r.get("relative_to") == "standing":
            per_rule[r["id"]]["standing_value"] = (baselines or {}).get(r["signal"])
            if needs_baseline(r, baselines):
                per_rule[r["id"]]["not_evaluated_because"] = f"no standing value of {r['signal']} for this person"
    return {"rules": spec["name"], "author": spec.get("author", "unspecified"), "twin_tier": tier,
            "allowed_joint_planes": list(allowed), "alignment_flags": dict(flags or {}), "per_rule": per_rule,
            "commands_sent": len(sent)}
