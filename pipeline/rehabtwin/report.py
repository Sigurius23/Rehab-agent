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


PLAYER_JS = r"""
(function () {
  const D = JSON.parse(document.getElementById('skel-data').textContent);
  const cv = document.getElementById('skel'), ctx = cv.getContext('2d');
  const slider = document.getElementById('skel-t'), btn = document.getElementById('skel-play'), lab = document.getElementById('skel-time');
  let yaw = -0.7, pitch = 0.45, k = 0, playing = true, drag = null, last = 0;
  const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
  slider.max = D.t.length - 1;
  // fit: centre on the mean pelvis position, scale to the body height
  const P = D.est.pelvis; let cx = 0, cz = 0;
  for (const p of P) { cx += p[0]; cz += p[2]; } cx /= P.length; cz /= P.length;
  function proj(p) {
    const x = p[0] - cx, y = p[1] - 0.9, z = p[2] - cz;
    const cy = Math.cos(yaw), sy = Math.sin(yaw), cp = Math.cos(pitch), sp = Math.sin(pitch);
    const x1 = cy * x + sy * z, z1 = -sy * x + cy * z;
    const y2 = cp * y - sp * z1, z2 = sp * y + cp * z1;
    const s = cv.height / 2.6 * 3.5 / (3.5 + z2);
    return [cv.width / 2 + s * x1, cv.height * 0.52 - s * y2];
  }
  function line(a, b, col, w, dash) {
    const p = proj(a), q = proj(b);
    ctx.beginPath(); ctx.setLineDash(dash || []); ctx.strokeStyle = col; ctx.lineWidth = w;
    ctx.moveTo(p[0], p[1]); ctx.lineTo(q[0], q[1]); ctx.stroke();
  }
  function side(a, b) { return /_r$/.test(b) || /_r$/.test(a) ? '#2563eb' : /_l$/.test(b) || /_l$/.test(a) ? '#dc2626' : css('--fg'); }
  function draw() {
    const dpr = window.devicePixelRatio || 1, w = cv.clientWidth;
    if (cv.width !== Math.round(w * dpr)) { cv.width = Math.round(w * dpr); cv.height = Math.round(w * 0.6 * dpr); }
    ctx.clearRect(0, 0, cv.width, cv.height);
    for (let i = -5; i <= 5; i++) {  // floor grid (y = 0), 20 cm
      line([cx + i * 0.2, 0, cz - 1], [cx + i * 0.2, 0, cz + 1], css('--muted'), 0.6);
      line([cx - 1, 0, cz + i * 0.2], [cx + 1, 0, cz + i * 0.2], css('--muted'), 0.6);
    }
    if (D.ref) {
      const kr = Math.min(k, D.ref.pelvis.length - 1);
      for (const [a, b] of D.bones) if (D.ref[a] && D.ref[b]) line(D.ref[a][kr], D.ref[b][kr], css('--muted'), 2 * (window.devicePixelRatio || 1), [6, 5]);
    }
    for (const [a, b] of D.bones) if (D.est[a] && D.est[b]) line(D.est[a][k], D.est[b][k], side(a, b), 3 * (window.devicePixelRatio || 1));
    slider.value = k; lab.textContent = D.t[k].toFixed(2) + ' s';
  }
  function tick(ts) {
    if (playing && ts - last > 1000 / D.fps) { k = (k + 1) % D.t.length; last = ts; draw(); }
    requestAnimationFrame(tick);
  }
  cv.addEventListener('pointerdown', e => { drag = [e.clientX, e.clientY, yaw, pitch]; cv.setPointerCapture(e.pointerId); });
  cv.addEventListener('pointermove', e => { if (!drag) return; yaw = drag[2] + (e.clientX - drag[0]) / 150;
    pitch = Math.max(-1.2, Math.min(1.2, drag[3] + (e.clientY - drag[1]) / 150)); draw(); });
  cv.addEventListener('pointerup', () => { drag = null; });
  slider.addEventListener('input', () => { k = +slider.value; playing = false; btn.textContent = 'Play'; draw(); });
  btn.addEventListener('click', () => { playing = !playing; btn.textContent = playing ? 'Pause' : 'Play'; });
  window.addEventListener('resize', draw);
  draw(); requestAnimationFrame(tick);
})();
"""


def _player(skeleton, ref_skeleton=None):
    import json
    from .kinematics import SKELETON_BONES
    t, pos = skeleton
    fps = 1.0 / float(np.median(np.diff(t))) if len(t) > 1 else 30.0
    data = {"t": [round(float(v), 3) for v in t], "fps": fps, "bones": SKELETON_BONES,
            "est": {b: np.round(p, 3).tolist() for b, p in pos.items()}}
    if ref_skeleton is not None:
        # Resample the reference to the replay times and overlay it on the estimate's
        # pelvis (horizontal shift only: heights above the floor stay as measured).
        rt, rpos = ref_skeleton
        shift = None
        if "pelvis" in rpos and "pelvis" in pos:
            rp = np.stack([np.interp(t, rt, rpos["pelvis"][:, j]) for j in range(3)], axis=1)
            shift = pos["pelvis"] - rp
            shift[:, 1] = 0.0
        ref = {}
        for b, p in rpos.items():
            q = np.stack([np.interp(t, rt, p[:, j]) for j in range(3)], axis=1)
            ref[b] = np.round(q + (shift if shift is not None else 0.0), 3).tolist()
        data["ref"] = ref
    legend = ("<span style='color:#2563eb'>right</span> · <span style='color:#dc2626'>left</span>"
              + (" · <span class='muted'>dashed = reference, overlaid on the estimate's pelvis</span>" if ref_skeleton is not None else ""))
    return (f"<h2>3D replay</h2><p class='muted'>OpenSim model joint centres from the IK solution; drag to orbit. {legend}</p>"
            "<canvas id='skel' style='width:100%;touch-action:none;cursor:grab'></canvas>"
            "<div class='kv'><button id='skel-play' type='button'>Pause</button> "
            "<input id='skel-t' type='range' min='0' value='0' style='width:60%;vertical-align:middle'> "
            "<span id='skel-time' class='muted'></span></div>"
            f"<script type='application/json' id='skel-data'>{json.dumps(data, separators=(',', ':'))}</script>"
            f"<script>{PLAYER_JS}</script>")


def write(path, session, qc, metrics, signals, time, validation=None, reference=None, skeleton=None,
          ref_skeleton=None):
    """``reference``: optional (time, {signal: values}) drawn dashed on the charts.
    ``skeleton``/``ref_skeleton``: optional (time, {body: (K,3)}) for the 3D replay."""
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
button {{ font: inherit; padding: 2px 12px; border-radius: 6px; border: 1px solid var(--line); background: var(--bg); color: var(--fg); }}
</style></head><body>
<h1>Session {e(session['session_id'])} — {e(metrics['exercise'])}{' (SYNTHETIC)' if synthetic else ''}</h1>
<p class="banner"><b>Tier {tier}.</b> {e(metrics['claims'])} Research prototype, not a medical device.</p>
<div class="kv muted"><span>reps: <b>{metrics['n_reps']}</b></span><span>detection rate: {qc.get('detection_rate')}</span>
<span>imputed frames: {len(qc.get('imputed_frames', []))}</span><span>gravity: {e(str(fr.get('up_source')))}</span>
<span>IK marker RMS: {ik.get('marker_rms_m', {}).get('mean')} m (p95 {ik.get('marker_rms_m', {}).get('p95')})</span></div>
{_player(skeleton, ref_skeleton) if skeleton is not None else ''}
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
