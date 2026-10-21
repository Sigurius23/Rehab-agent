"""Self-contained HTML session report a clinician can open and disagree with.

No plotting dependency: charts are inline SVG. The tier/claims banner is
always at the top so no number is read without its accuracy context.
"""
from __future__ import annotations

import html
from pathlib import Path

import numpy as np

PALETTE = ["#2563eb", "#dc2626", "#059669", "#d97706", "#7c3aed", "#0891b2"]


def _svg_chart(t, series, reps, title, unit="deg", w=760, h=220, ref=None):
    """Line chart; ``ref`` = (ref_time, {name: values}) is drawn dashed in the same colours."""
    pad_l, pad_r, pad_t, pad_b = 48, 12, 30, 28
    ref_t, ref_series = ref if ref else (None, {})
    vals = np.concatenate([np.asarray(v, float) for v in list(series.values()) + list(ref_series.values())])
    vals = vals[np.isfinite(vals)]
    lo, hi = (float(vals.min()), float(vals.max())) if len(vals) else (0.0, 1.0)
    if hi - lo < 1e-6:
        hi = lo + 1.0
    span = hi - lo
    lo, hi = lo - 0.05 * span, hi + 0.05 * span
    t0, t1 = float(t[0]), float(t[-1]) if t[-1] > t[0] else float(t[0]) + 1

    def x(v):
        return pad_l + (v - t0) / (t1 - t0) * (w - pad_l - pad_r)

    def y(v):
        return pad_t + (hi - v) / (hi - lo) * (h - pad_t - pad_b)

    parts = [f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="{html.escape(title)}" class="chart">',
             f'<text x="{pad_l}" y="15" class="ct">{html.escape(title)} ({unit})</text>']
    lx = w - pad_r
    legend = [(n, PALETTE[i % len(PALETTE)], False) for i, n in enumerate(series)]
    if ref_series:
        legend.append(("dashed = reference", None, True))
    for name, col, is_note in reversed(legend):
        parts.append(f'<text x="{lx}" y="15" class="lg" text-anchor="end"'
                     f'{"" if is_note else f" fill={chr(34)}{col}{chr(34)}"}>{html.escape(name)}</text>')
        lx -= 7 * len(name) + 14
    for r in reps:
        parts.append(f'<rect x="{x(r["start_s"]):.1f}" y="{pad_t}" width="{x(r["stop_s"]) - x(r["start_s"]):.1f}" '
                     f'height="{h - pad_t - pad_b}" class="rep"/>')
        parts.append(f'<text x="{x(r["peak_s"]):.1f}" y="{pad_t + 12}" class="rl">{r["rep"]}</text>')
    for k in range(5):
        v = lo + k * (hi - lo) / 4
        parts.append(f'<line x1="{pad_l}" x2="{w - pad_r}" y1="{y(v):.1f}" y2="{y(v):.1f}" class="grid"/>')
        parts.append(f'<text x="{pad_l - 6}" y="{y(v) + 4:.1f}" class="ax" text-anchor="end">{v:.0f}</text>')
    for k in range(6):
        tv = t0 + k * (t1 - t0) / 5
        parts.append(f'<text x="{x(tv):.1f}" y="{h - 8}" class="ax" text-anchor="middle">{tv:.1f}s</text>')
    for i, name in enumerate(series):
        col = PALETTE[i % len(PALETTE)]
        for tt, v, dash in ((t, series[name], ""), (ref_t, ref_series.get(name), ' stroke-dasharray="5 4"')):
            if v is None:
                continue
            v = np.asarray(v, float)
            step = max(1, len(v) // 600)
            keep = [(a, b) for a, b in zip(tt[::step], v[::step]) if np.isfinite(b) and t0 <= a <= t1]
            pts = " ".join(f"{x(a):.1f},{y(b):.1f}" for a, b in keep)
            parts.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="1.6"{dash}/>')
    parts.append("</svg>")
    return "".join(parts)


CHARTS = [
    ("Knee flexion", ["knee_angle_r", "knee_angle_l"]),
    ("Hip flexion", ["hip_flexion_r", "hip_flexion_l"]),
    ("Trunk & pelvis vs gravity (sagittal, + forward)", ["torso.sagittal", "pelvis.sagittal"]),
    ("Trunk & pelvis vs gravity (frontal, + right)", ["torso.frontal", "pelvis.frontal"]),
    ("Knee frontal-plane projection angle (+ valgus)", ["knee_fppa_r", "knee_fppa_l"]),
    ("Ankle dorsiflexion", ["ankle_angle_r", "ankle_angle_l"]),
    ("Shoulder flexion", ["arm_flex_r", "arm_flex_l"]),
]


def write(path, session, qc, metrics, signals, time, validation=None, reference=None):
    """``reference``: optional (time, {signal: values}) drawn dashed on the charts."""
    tier = metrics["tier"]
    e = html.escape
    synthetic = session.get("synthetic")
    rows = []
    for k, s in metrics["summary"].items():
        badge = "validated" if s["validated"] else "unvalidated"
        rows.append(f"<tr><td>{e(k)}</td><td>{e(s['plane'] or '')}</td><td>{s['session_min']}</td><td>{s['session_max']}</td>"
                    f"<td>{'' if s['rep_peak_mean'] is None else s['rep_peak_mean']}</td>"
                    f"<td>{'' if s['rep_peak_sd'] is None else s['rep_peak_sd']}</td>"
                    f"<td><span class='b {badge}'>{badge}</span></td></tr>")
    rep_rows = []
    for r in metrics["reps"]:
        cells = "".join(f"<td>{r['values'][k]['at_peak']}</td>" for k in list(metrics["summary"])[:6])
        flag = " ⚠ imputed frames" if r["contains_imputed_frames"] else ""
        rep_rows.append(f"<tr><td>{r['rep']}</td><td>{r['start_s']}–{r['stop_s']}</td><td>{r['duration_s']}</td>{cells}<td>{flag}</td></tr>")
    rep_head = "".join(f"<th>{e(k)} @peak</th>" for k in list(metrics["summary"])[:6])
    charts = []
    for title, keys in CHARTS:
        ser = {k: signals[k] for k in keys if k in signals}
        if ser:
            ref = None
            if reference is not None:
                ref = (reference[0], {k: reference[1][k] for k in ser if k in reference[1]})
            charts.append(_svg_chart(time, ser, metrics["reps"], title, ref=ref))
    ik = qc.get("ik", {})
    fr = qc.get("frames", {})
    val_html = ""
    if validation:
        gate_rows = "".join(f"<tr><td>{e(g)}</td><td><span class='b {v}'>{v}</span></td></tr>"
                            for g, v in validation["gates"].items() if v != "not-tested")
        val_html = (f"<h2>Validation against reference</h2><p>Reference: {e(validation['reference_system'])}. "
                    f"Approved for: <b>{e(', '.join(validation['approved_for']) or 'nothing')}</b>. {e(validation.get('notes', ''))}</p>"
                    f"<table><tr><th>gate</th><th>result</th></tr>{gate_rows}</table>")
    doc = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Session {e(session['session_id'])}</title>
<style>
:root {{ --bg:#ffffff; --fg:#111827; --muted:#6b7280; --line:#e5e7eb; --rep:#dbeafe55; --warn:#fef3c7; --warnfg:#92400e; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#0b1020; --fg:#e5e7eb; --muted:#9ca3af; --line:#1f2937; --rep:#1e3a8a55; --warn:#451a03; --warnfg:#fde68a; }} }}
body {{ font: 14px/1.5 system-ui, sans-serif; background: var(--bg); color: var(--fg); margin: 0 auto; max-width: 980px; padding: 16px; }}
h1 {{ font-size: 20px; margin: 8px 0; }} h2 {{ font-size: 16px; margin-top: 28px; }}
.banner {{ background: var(--warn); color: var(--warnfg); padding: 10px 14px; border-radius: 8px; }}
table {{ border-collapse: collapse; width: 100%; font-size: 13px; display: block; overflow-x: auto; }}
td, th {{ border-bottom: 1px solid var(--line); padding: 4px 8px; text-align: left; white-space: nowrap; }}
.b {{ padding: 1px 6px; border-radius: 10px; font-size: 12px; }}
.validated, .pass {{ background: #d1fae5; color: #065f46; }} .unvalidated, .not-tested {{ background: #e5e7eb; color: #374151; }}
.fail {{ background: #fee2e2; color: #991b1b; }}
.chart {{ width: 100%; height: auto; margin: 8px 0; }} .ct {{ font-size: 13px; fill: var(--fg); font-weight: 600; }}
.ax {{ font-size: 10px; fill: var(--muted); }} .lg {{ font-size: 11px; font-weight: 600; }}
.grid {{ stroke: var(--line); }} .rep {{ fill: var(--rep); }} .rl {{ font-size: 10px; fill: var(--muted); }}
.kv span {{ display: inline-block; margin-right: 18px; }} .muted {{ color: var(--muted); }}
</style></head><body>
<h1>Session {e(session['session_id'])} — {e(metrics['exercise'])}{' (SYNTHETIC)' if synthetic else ''}</h1>
<p class="banner"><b>Tier {tier}.</b> {e(metrics['claims'])} Research prototype, not a medical device.</p>
<div class="kv muted"><span>reps: <b>{metrics['n_reps']}</b></span><span>detection rate: {qc.get('detection_rate')}</span>
<span>imputed frames: {len(qc.get('imputed_frames', []))}</span><span>gravity: {e(str(fr.get('up_source')))}</span>
<span>IK marker RMS: {ik.get('marker_rms_m', {}).get('mean')} m (p95 {ik.get('marker_rms_m', {}).get('p95')})</span></div>
{''.join(charts)}
<h2>Per-rep values</h2>
{f"<table><tr><th>rep</th><th>time (s)</th><th>dur (s)</th>{rep_head}<th></th></tr>{''.join(rep_rows)}</table>" if rep_rows
 else f"<p class='muted'>No reps segmented (exercise profile '{e(metrics['exercise'])}'{' has no rep driver' if not metrics['rep_driver'] else ''}).</p>"}
<h2>Session summary</h2>
<table><tr><th>signal</th><th>plane</th><th>min</th><th>max</th><th>rep-peak mean</th><th>rep-peak SD</th><th>status</th></tr>{''.join(rows)}</table>
{val_html}
<h2>Provenance</h2>
<p class="muted">Front-end: {e(session['pipeline']['front_end'])} · back-end: {e(session['pipeline']['back_end'])} ·
config: {e(session['pipeline']['config'])} · software: {e(', '.join(f'{k} {v}' for k, v in session['pipeline']['software'].items()))}</p>
<p class="muted">Every number above comes from files in this session folder (opensim/*.mot, metrics.json, qc.json).</p>
</body></html>"""
    Path(path).write_text(doc)
    return path
