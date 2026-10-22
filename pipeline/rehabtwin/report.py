"""Self-contained HTML session report a clinician can open and disagree with.

No plotting dependency: charts are inline SVG. The tier/claims banner is
always at the top so no number is read without its accuracy context.
"""
from __future__ import annotations

import html
from pathlib import Path

import numpy as np

_CSS = """
:root { --bg:#ffffff; --fg:#111827; --muted:#6b7280; --line:#e5e7eb; --rep:#dbeafe55; --warn:#fef3c7; --warnfg:#92400e; }
@media (prefers-color-scheme: dark) { :root { --bg:#0b1020; --fg:#e5e7eb; --muted:#9ca3af; --line:#1f2937; --rep:#1e3a8a55; --warn:#451a03; --warnfg:#fde68a; } }
body { font: 14px/1.5 system-ui, sans-serif; background: var(--bg); color: var(--fg); margin: 0 auto; max-width: 980px; padding: 16px; }
h1 { font-size: 20px; margin: 8px 0; } h2 { font-size: 16px; margin-top: 28px; }
.banner { background: var(--warn); color: var(--warnfg); padding: 10px 14px; border-radius: 8px; }
table { border-collapse: collapse; width: 100%; font-size: 13px; display: block; overflow-x: auto; }
td, th { border-bottom: 1px solid var(--line); padding: 4px 8px; text-align: left; white-space: nowrap; }
.b { padding: 1px 6px; border-radius: 10px; font-size: 12px; }
.validated, .pass { background: #d1fae5; color: #065f46; } .unvalidated, .not-tested { background: #e5e7eb; color: #374151; }
.fail { background: #fee2e2; color: #991b1b; }
.chart { width: 100%; height: auto; margin: 8px 0; } .ct { font-size: 13px; fill: var(--fg); font-weight: 600; }
.ax { font-size: 10px; fill: var(--muted); } .lg { font-size: 11px; font-weight: 600; } .note { fill: var(--muted); }
.grid { stroke: var(--line); } .rep { fill: var(--rep); } .rl { font-size: 10px; fill: var(--muted); }
.kv span { display: inline-block; margin-right: 18px; } .muted { color: var(--muted); }
button { font: inherit; padding: 2px 12px; border-radius: 6px; border: 1px solid var(--line); background: var(--bg); color: var(--fg); }
"""

PALETTE = ["#2563eb", "#dc2626", "#059669", "#d97706", "#7c3aed", "#0891b2"]


def _svg_chart(t, series, reps, title, unit="deg", w=760, h=220, ref=None, ref_label="reference", marks=()):
    """``marks``: [(time, colour, label)] drawn as vertical ticks (e.g. haptic cues)."""
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
        legend.append((f"dashed = {ref_label}", None, True))
    for name, col, is_note in reversed(legend):
        fill = 'class="lg note"' if is_note else f'class="lg" fill="{col}"'
        parts.append(f'<text x="{lx}" y="15" {fill} text-anchor="end">{html.escape(name)}</text>')
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
    for tm, colour, label in marks:
        if t0 <= tm <= t1:
            parts.append(f'<line x1="{x(tm):.1f}" x2="{x(tm):.1f}" y1="{pad_t}" y2="{h - pad_b}" stroke="{colour}" '
                         f'stroke-width="2"><title>{html.escape(label)}</title></line>')
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
    const y2 = cp * y + sp * z1, z2 = -sp * y + cp * z1;   // pitch > 0: camera above, looking down
    const s = cv.height / 2.6 * 4.5 / (4.5 + z2);
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
    for (let i = -4; i <= 4; i++) {  // floor grid (y = 0), 20 cm
      line([cx + i * 0.2, 0, cz - 0.8], [cx + i * 0.2, 0, cz + 0.8], css('--muted'), 0.6);
      line([cx - 0.8, 0, cz + i * 0.2], [cx + 0.8, 0, cz + i * 0.2], css('--muted'), 0.6);
    }
    if (D.ref) {
      const kr = Math.min(k, D.ref.pelvis.length - 1);
      for (const [a, b] of D.bones) if (D.ref[a] && D.ref[b]) line(D.ref[a][kr], D.ref[b][kr], D.ref_color || css('--muted'), 2 * (window.devicePixelRatio || 1), [6, 5]);
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


def _player(skeleton, ref_skeleton=None, ref_label="reference, overlaid on the estimate's pelvis",
            ref_color=None, align_pelvis=True):
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
        if align_pelvis and "pelvis" in rpos and "pelvis" in pos:
            rp = np.stack([np.interp(t, rt, rpos["pelvis"][:, j]) for j in range(3)], axis=1)
            shift = pos["pelvis"] - rp
            shift[:, 1] = 0.0
        ref = {}
        for b, p in rpos.items():
            q = np.stack([np.interp(t, rt, p[:, j]) for j in range(3)], axis=1)
            ref[b] = np.round(q + (shift if shift is not None else 0.0), 3).tolist()
        data["ref"] = ref
        if ref_color:
            data["ref_color"] = ref_color
    legend = ("<span style='color:#2563eb'>right</span> · <span style='color:#dc2626'>left</span>"
              + (f" · <span style='color:{ref_color or 'var(--muted)'}'>dashed = {html.escape(ref_label)}</span>" if ref_skeleton is not None else ""))
    return (f"<h2>3D replay</h2><p class='muted'>OpenSim model joint centres from the IK solution; drag to orbit. {legend}</p>"
            "<canvas id='skel' style='width:100%;touch-action:none;cursor:grab'></canvas>"
            "<div class='kv'><button id='skel-play' type='button'>Pause</button> "
            "<input id='skel-t' type='range' min='0' value='0' style='width:60%;vertical-align:middle'> "
            "<span id='skel-time' class='muted'></span></div>"
            f"<script type='application/json' id='skel-data'>{json.dumps(data, separators=(',', ':'))}</script>"
            f"<script>{PLAYER_JS}</script>")


# Muscle colour scales (OKLab-interpolated; each arm checked as a one-hue ordinal ramp with the
# dataviz validator against the report surfaces): activation = one red hue, light -> dark on a
# light page and dark -> light on a dark page; change vs measured = blue (less) - grey - red (more).
MUSCLE_RAMPS = {
    "light": {"seq": ("#dc9a90", "#9a1d1a"), "div": ("#1f5fae", "#bdbbb4", "#a8201d")},
    "dark": {"seq": ("#7a4741", "#ffb4a9"), "div": ("#8cc0fa", "#55544e", "#ff9890")},
}


def _oklab_ramp(stops, n):
    """n colours interpolated in OKLab through ``stops`` (hex)."""
    m1 = np.array([[0.4122214708, 0.5363325363, 0.0514459929], [0.2119034982, 0.6806995451, 0.1073969566],
                   [0.0883024619, 0.2817188376, 0.6299787005]])
    m2 = np.array([[0.2104542553, 0.7936177850, -0.0040720468], [1.9779984951, -2.4285922050, 0.4505937099],
                   [0.0259040371, 0.7827717662, -0.8086757660]])

    def to_lab(h):
        c = np.array([int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)])
        c = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
        return m2 @ np.cbrt(m1 @ c)

    def to_hex(lab):
        c = np.clip(np.linalg.solve(m1, np.linalg.solve(m2, lab) ** 3), 0, 1)
        c = np.where(c <= 0.0031308, 12.92 * c, 1.055 * c ** (1 / 2.4) - 0.055)
        return "#" + "".join(f"{int(round(v * 255)):02x}" for v in c)

    labs = [to_lab(h) for h in stops]
    out = []
    for k in range(n):
        u = k / (n - 1) * (len(stops) - 1)
        i = min(int(u), len(stops) - 2)
        out.append(to_hex(labs[i] * (1 - (u - i)) + labs[i + 1] * (u - i)))
    return out


MUSCLE_JS = r"""
(function () {
  const D = JSON.parse(document.getElementById('mus-data').textContent);
  const $ = id => document.getElementById(id);
  const cv = $('mus'), ctx = cv.getContext('2d'), slider = $('mus-t'), btn = $('mus-play'), lab = $('mus-time');
  const selRun = $('mus-run'), selMode = $('mus-mode'), tip = $('mus-tip'), topEl = $('mus-top'), leg = $('mus-legend');
  const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
  const dark = () => window.matchMedia && matchMedia('(prefers-color-scheme: dark)').matches;
  let yaw = -0.6, pitch = 0.3, k = 0, playing = true, drag = null, last = 0, hover = null, segs = [];
  slider.max = D.t.length - 1;
  for (const r of Object.keys(D.runs)) selRun.add(new Option(r, r));
  const P0 = D.motions[D.runs[D.base].motion].bodies.pelvis;
  let cx = 0, cz = 0; for (const p of P0) { cx += p[0]; cz += p[2]; } cx /= P0.length; cz /= P0.length;
  const fref = Math.max(...D.runs[D.base].fmax);
  const top = (D.motions[D.runs[D.base].motion].bodies.head || P0).reduce((h, p) => Math.max(h, p[1]), 0) / 1000 + 0.15;
  function proj(x, y, z) {   // fit: floor to top of the head over the window
    x = (x - cx) / 1000; y = y / 1000 - top / 2; z = (z - cz) / 1000;
    const cy = Math.cos(yaw), sy = Math.sin(yaw), cp = Math.cos(pitch), sp = Math.sin(pitch);
    const x1 = cy * x + sy * z, z1 = -sy * x + cy * z, y2 = cp * y + sp * z1, z2 = -sp * y + cp * z1;
    const s = cv.height / (top * 1.2) * 4.5 / (4.5 + z2);
    return [cv.width / 2 + s * x1, cv.height * 0.46 - s * y2];
  }
  const change = () => selMode.value === 'change' && selRun.value !== D.base;
  function value(run, m) { return change() ? run.act[k][m] - D.runs[D.base].act[k][m] : run.act[k][m]; }
  function colour(v) {
    const L = D.lut[dark() ? 'dark' : 'light'];
    if (change()) { const u = (Math.max(-D.span, Math.min(D.span, v)) + D.span) / (2 * D.span); return L.div[Math.round(u * (L.div.length - 1))]; }
    return L.seq[Math.round(Math.min(100, v) / 100 * (L.seq.length - 1))];
  }
  function legend() {
    const L = D.lut[dark() ? 'dark' : 'light'], c = change() ? L.div : L.seq;
    const ticks = change() ? ['-' + D.span + ' pts (less)', '0', '+' + D.span + ' pts (more)'] : ['0%', '50%', '100% of capacity'];
    leg.innerHTML = '<div style="height:10px;border-radius:5px;background:linear-gradient(90deg,' + c.join(',') + ')"></div>' +
      '<div style="display:flex;justify-content:space-between" class="muted">' + ticks.map(t => '<span>' + t + '</span>').join('') + '</div>';
  }
  function draw() {
    const dpr = window.devicePixelRatio || 1, w = cv.clientWidth;
    if (cv.width !== Math.round(w * dpr)) { cv.width = Math.round(w * dpr); cv.height = Math.round(Math.min(w * 0.75, 640) * dpr); }
    ctx.clearRect(0, 0, cv.width, cv.height);
    const run = D.runs[selRun.value], mot = D.motions[run.motion], paths = mot.paths[k];
    ctx.lineCap = 'round'; ctx.lineJoin = 'round';
    ctx.strokeStyle = css('--line'); ctx.lineWidth = dpr;
    for (let i = -4; i <= 4; i++) for (const [a, b] of [[[i * 200, -800], [i * 200, 800]], [[-800, i * 200], [800, i * 200]]]) {
      const p = proj(cx + a[0], 0, cz + a[1]), q = proj(cx + b[0], 0, cz + b[1]);
      ctx.beginPath(); ctx.moveTo(p[0], p[1]); ctx.lineTo(q[0], q[1]); ctx.stroke();
    }
    ctx.strokeStyle = css('--muted'); ctx.lineWidth = 1.5 * dpr;
    for (const [a, b] of D.bones) if (mot.bodies[a] && mot.bodies[b]) {
      const p = proj(...mot.bodies[a][k]), q = proj(...mot.bodies[b][k]);
      ctx.beginPath(); ctx.moveTo(p[0], p[1]); ctx.lineTo(q[0], q[1]); ctx.stroke();
    }
    const order = paths.map((_, m) => m).sort((a, b) => Math.abs(value(run, a)) - Math.abs(value(run, b)));
    segs = [];
    for (const m of order) {
      const pts = paths[m]; if (pts.length < 6) continue;
      ctx.beginPath(); ctx.strokeStyle = colour(value(run, m));
      ctx.lineWidth = dpr * (0.6 + 2.6 * Math.sqrt(run.fmax[m] / fref)) * (hover === m ? 2 : 1);
      let prev = null;
      for (let i = 0; i < pts.length; i += 3) {
        const p = proj(pts[i], pts[i + 1], pts[i + 2]);
        if (prev) { ctx.lineTo(p[0], p[1]); segs.push([m, prev[0], prev[1], p[0], p[1]]); } else ctx.moveTo(p[0], p[1]);
        prev = p;
      }
      ctx.stroke();
    }
    const ranked = paths.map((_, m) => m).sort((a, b) => Math.abs(value(run, b)) - Math.abs(value(run, a))).slice(0, 6);
    topEl.textContent = (change() ? 'Biggest changes now: ' : 'Most active now: ') +
      ranked.map(m => D.muscles[m] + ' ' + (change() ? (value(run, m) > 0 ? '+' : '') + value(run, m) + ' pts' : value(run, m) + '%')).join(' · ');
    slider.value = k; lab.textContent = D.t[k].toFixed(2) + ' s';
    if (hover !== null) showTip(run);
  }
  let tipXY = [0, 0];
  function showTip(run) {
    const m = hover, base = D.runs[D.base];
    tip.style.display = 'block'; tip.style.left = (tipXY[0] + 14) + 'px'; tip.style.top = (tipXY[1] + 10) + 'px';
    tip.innerHTML = '<b>' + D.muscles[m] + '</b> (' + (D.groups[D.muscles[m]] || 'other') + ')<br>activation ' + run.act[k][m] + '%' +
      (selRun.value !== D.base ? ' · measured ' + base.act[k][m] + '%' : '') + '<br>capacity ' + run.fmax[m] + ' N' +
      (run.fmax[m] !== base.fmax[m] ? ' (measured model ' + base.fmax[m] + ' N)' : '');
  }
  function nearest(x, y) {
    let best = null, bd = 8 * (window.devicePixelRatio || 1);
    for (const [m, x1, y1, x2, y2] of segs) {
      const dx = x2 - x1, dy = y2 - y1, L = dx * dx + dy * dy || 1, u = Math.max(0, Math.min(1, ((x - x1) * dx + (y - y1) * dy) / L));
      const d = Math.hypot(x - x1 - u * dx, y - y1 - u * dy);
      if (d <= bd) { bd = d; best = m; }   // later segments are drawn on top: prefer them on ties
    }
    return best;
  }
  function tick(ts) {
    if (playing && ts - last > 1000 / D.fps) { k = (k + 1) % D.t.length; last = ts; draw(); }
    requestAnimationFrame(tick);
  }
  cv.addEventListener('pointerdown', e => { drag = [e.clientX, e.clientY, yaw, pitch]; cv.setPointerCapture(e.pointerId); });
  cv.addEventListener('pointermove', e => {
    if (drag) { yaw = drag[2] + (e.clientX - drag[0]) / 150; pitch = Math.max(-1.2, Math.min(1.2, drag[3] + (e.clientY - drag[1]) / 150)); draw(); return; }
    const r = cv.getBoundingClientRect(), dpr = window.devicePixelRatio || 1;
    tipXY = [e.clientX - r.left, e.clientY - r.top];
    const h = nearest(tipXY[0] * dpr, tipXY[1] * dpr);
    if (h !== hover) { hover = h; if (h === null) tip.style.display = 'none'; draw(); } else if (h !== null) showTip(D.runs[selRun.value]);
  });
  cv.addEventListener('pointerup', () => { drag = null; });
  cv.addEventListener('pointerleave', () => { hover = null; tip.style.display = 'none'; draw(); });
  slider.addEventListener('input', () => { k = +slider.value; playing = false; btn.textContent = 'Play'; draw(); });
  btn.addEventListener('click', () => { playing = !playing; btn.textContent = playing ? 'Pause' : 'Play'; });
  const onSel = () => { selMode.disabled = selRun.value === D.base; legend(); draw(); };
  selRun.addEventListener('change', onSel); selMode.addEventListener('change', onSel);
  if (window.matchMedia) matchMedia('(prefers-color-scheme: dark)').addEventListener('change', onSel);
  window.addEventListener('resize', draw);
  onSel(); requestAnimationFrame(tick);
})();
"""


def _muscle_view(view, span_pts=30):
    """3D muscle view: lines of action coloured by SO activation, one scenario at a time."""
    import json
    data = dict(view, base="measured", span=span_pts,
                lut={mode: {"seq": _oklab_ramp(r["seq"], 21), "div": _oklab_ramp(r["div"], 21)}
                     for mode, r in MUSCLE_RAMPS.items()})
    return ("<h2>3D muscle view</h2><p class='muted'>Muscle lines of action on the session model (OpenSim paths, "
            "wrapping included), coloured by the static-optimisation activation of each muscle. Line width ∝ √(max "
            "isometric force), so a weakened group draws thinner. Drag to orbit; hover a muscle for its numbers. "
            "Weakened and exo variants reuse the measured motion; a corrected variant moves the body as corrected.</p>"
            "<div class='kv'><label>variant <select id='mus-run'></select></label> "
            "<label>colour <select id='mus-mode'><option value='act'>activation</option>"
            "<option value='change'>change vs measured</option></select></label></div>"
            "<div style='position:relative'><canvas id='mus' style='width:100%;touch-action:none;cursor:grab'></canvas>"
            "<div id='mus-tip' style='display:none;position:absolute;pointer-events:none;background:var(--bg);"
            "border:1px solid var(--line);border-radius:6px;padding:4px 8px;font-size:12px;white-space:nowrap'></div></div>"
            "<div id='mus-legend' style='max-width:360px;font-size:12px'></div>"
            "<div class='kv'><button id='mus-play' type='button'>Pause</button> "
            "<input id='mus-t' type='range' min='0' value='0' style='width:60%;vertical-align:middle'> "
            "<span id='mus-time' class='muted'></span></div><p id='mus-top' style='font-size:13px'></p>"
            f"<script type='application/json' id='mus-data'>{json.dumps(data, separators=(',', ':'))}</script>"
            f"<script>{MUSCLE_JS}</script>")


def _svg_bars(groups, variants, title, w=760, row=16):
    """Horizontal grouped bars: one row block per muscle group, one bar per variant (0..1 scale)."""
    names = list(variants)
    h = 40 + len(groups) * (row * len(names) + 8)
    left, right = 190, 50
    parts = [f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="{html.escape(title)}" class="chart">',
             f'<text x="8" y="15" class="ct">{html.escape(title)}</text>']
    # legend as wrapping HTML (variant names get long): swatch carries the colour, text stays in text colour
    legend = "".join(f"<span style='display:inline-flex;align-items:center;gap:6px;margin:2px 14px 2px 0'>"
                     f"<i style='width:12px;height:12px;border-radius:3px;background:{PALETTE[i % len(PALETTE)]}'></i>"
                     f"{html.escape(n)}</span>" for i, n in enumerate(names))
    scale = (w - left - right)
    for k in range(0, 11, 2):
        x = left + scale * k / 10
        parts.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="26" y2="{h - 6}" class="grid"/>')
        parts.append(f'<text x="{x:.1f}" y="{h}" class="ax" text-anchor="middle">{k * 10}%</text>')
    y = 30
    for g in groups:
        parts.append(f'<text x="{left - 8}" y="{y + row * len(names) / 2 + 4:.1f}" class="ax" text-anchor="end">{html.escape(g)}</text>')
        for i, n in enumerate(names):
            v = variants[n].get(g)
            if v is not None:
                parts.append(f'<rect x="{left}" y="{y:.1f}" width="{max(scale * min(v, 1.2), 1):.1f}" height="{row - 4}" '
                             f'fill="{PALETTE[i % len(PALETTE)]}" rx="2"/>')
                parts.append(f'<text x="{left + scale * min(v, 1.2) + 4:.1f}" y="{y + row - 6:.1f}" class="ax">{v * 100:.0f}%</text>')
            y += row
        y += 8
    parts.append("</svg>")
    return f"<div style='font-size:12px;margin-top:12px'>{legend}</div>" + "".join(parts)


def write_index(session_dir):
    """index.html for a session folder: every report it holds, with its status line.

    Derived reports carry the ``processing_id`` they were computed from; one that does not match
    session.json (re-processed since: other mass, tier or motion) stays listed but marked STALE.
    """
    import json
    from .records import stale_reason
    d = Path(session_dir)
    e = html.escape
    sess = json.loads((d / "session.json").read_text())
    items = [("Session report", "report.html", f"Tier {sess['twin_tier']} · {sess['pipeline']['front_end']}", None)]
    for c in sorted((d / "correction").glob("*/correction.json")):
        j = json.loads(c.read_text())
        items.append((f"Correction view: {j['spec']}", str(c.parent.relative_to(d) / "correction.html"),
                      f"{j['status']} · admissible: {'yes' if j['admissible'] else 'no'}", stale_reason(sess, j)))
    if (d / "strength" / "strength.json").exists():
        st = json.loads((d / "strength" / "strength.json").read_text())
        flags = [a for a, v in st["symmetry"].items() if v["flag"]]
        items.append(("Strength calibration", "strength/strength.html",
                      f"{len(st['tests'])} tests" + (f" · LSI < 90 %: {', '.join(flags)}" if flags else ""),
                      stale_reason(sess, st)))
    if (d / "muscles" / "study.json").exists():
        st = json.loads((d / "muscles" / "study.json").read_text())
        items.append(("Muscle effects", "muscles/muscles.html",
                      st.get("muscle_model", {}).get("source", "generic") + " · variants: " + ", ".join(st["runs"]),
                      stale_reason(sess, st)))
    for c in sorted((d / "feedback").glob("*/cues.json")):
        cues = json.loads(c.read_text())
        j = cues["summary"]
        items.append((f"Haptic cue replay: {c.parent.name}", str(c.parent.relative_to(d) / "cues.html"),
                      f"cues sent: {j['commands_sent']} · {sum(r['would_cue'] for r in j['per_rule'].values())} would-cue",
                      stale_reason(sess, cues)))
    rows = "".join(f"<tr><td><a href='{e(href)}'>{e(title)}</a></td><td class='muted'>"
                   + (f"<span class='b fail'>STALE</span> {e(why)} · " if why else "") + f"{e(note)}</td></tr>"
                   for title, href, note, why in items if (d / href).exists())
    doc = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Session {e(sess['session_id'])}</title>
<style>{_CSS} a {{ color: inherit; }}</style></head><body>
<h1>Session {e(sess['session_id'])}{' (SYNTHETIC)' if sess.get('synthetic') else ''}</h1>
<p class="muted">person {e(sess['person_ref'])} · started {e(sess['started_at'])} · tier {e(sess['twin_tier'])}</p>
<table><tr><th>report</th><th>status</th></tr>{rows}</table>
<p class="muted">Raw data: session.json, qc.json, metrics.json, opensim/, and the JSON next to each report.</p>
</body></html>"""
    (d / "index.html").write_text(doc)
    return d / "index.html"


CUE_COLOURS = {"cue": "#059669", "would_cue": "#d97706", "withheld": "#9ca3af"}


def write_cues(path, result, time, signals):
    """HTML for an offline haptic-cue replay (rehabtwin cues)."""
    e = html.escape
    summ, spec, log = result["summary"], result["spec"], result["log"]
    charts, rows = [], []
    for r in spec["rules"]:
        if r["signal"] not in signals:
            continue
        marks = [(ev["t"], CUE_COLOURS[ev["decision"]], f"{ev['decision']}: {ev.get('reason', r.get('message', ''))}")
                 for ev in log if ev.get("rule") == r["id"] and "decision" in ev]
        thr = np.full(len(time), r["threshold"], dtype=float)
        charts.append(_svg_chart(time, {r["signal"]: signals[r["signal"]]}, [], f"{r['id']}: {r['signal']} {r['op']} {r['threshold']}",
                                 ref=(time, {r["signal"]: thr}), ref_label="threshold", marks=marks))
        pr = summ["per_rule"][r["id"]]
        viol = "<b>not evaluated</b> (signal missing)" if pr.get("unevaluated") else pr["violations"]
        rows.append(f"<tr><td>{e(r['id'])}</td><td>{e(r['cue']['actuator'])}</td><td>{viol}</td>"
                    f"<td>{pr['cues_sent']}</td><td>{pr['would_cue']}</td><td>{pr['withheld_by_schedule']}</td>"
                    f"<td>{e(pr['gate'] or 'open')}</td></tr>")
    banner = ("<p class='banner'><b>Replay only — no cue may reach a person from this session.</b> "
              f"Tier {e(summ['twin_tier'])}; cues need a Tier-A twin and a validated joint/plane "
              f"(docs/accuracy.md). Validation gate: {e(summ.get('validation_gate', 'n/a'))}. "
              "Orange ticks show what <i>would</i> have been cued.</p>"
              if summ["commands_sent"] == 0 else
              "<p class='banner'><b>Cues were enabled</b> for validated joint/planes on a Tier-A twin.</p>")
    legend = " · ".join(f"<span style='color:{c}'>{k.replace('_', ' ')}</span>" for k, c in CUE_COLOURS.items())
    doc = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Haptic cue replay</title>
<style>{_CSS}</style></head><body>
<h1>Haptic cue replay — {e(spec['name'])}</h1>
<p class="muted">Motion replayed: {e(str(summ.get('motion', 'session motion')))}</p>
{banner}
<p class="muted">Rules by: {e(spec.get('author', 'unspecified'))}. Schedule: faded {spec.get('schedule', {}).get('start_fraction', 1)} →
{spec.get('schedule', {}).get('end_fraction', 0.33)} over {spec.get('schedule', {}).get('fade_events', 6)} violations,
bandwidth {spec.get('schedule', {}).get('bandwidth_deg', 2)}°, refractory {spec.get('schedule', {}).get('refractory_s', 1)} s. Ticks: {legend}.</p>
<table><tr><th>rule</th><th>actuator</th><th>violations</th><th>cues sent</th><th>would cue</th><th>withheld (fading)</th><th>gate</th></tr>{''.join(rows)}</table>
{''.join(charts)}
</body></html>"""
    Path(path).write_text(doc)
    return path


def _body_mass(bm, used_kg):
    """(header span, banner): ground forces are m (a_com + g), so every number below scales with this mass."""
    e = html.escape
    bm = bm or {"source": "unknown", "assumed": True}
    span = f"<span>body mass {used_kg} kg ({e(str(bm['source']))})</span>"
    kg = used_kg if bm.get("kg") is None else f"{bm['kg']:g}"
    banner = (f"<p class='banner'><b>body mass assumed ({kg} kg): every force, torque and activation scales with "
              "it.</b> Re-process the session with <code>--mass-kg</code> before reading any number here as this "
              "person's.</p>" if bm.get("assumed") else "")
    return span, banner


def _muscle_banner(study):
    e = html.escape
    mm = study.get("muscle_model", {})
    if mm.get("source", "").startswith("strength"):
        flags = ", ".join(f"{a} LSI {v['lsi_pct']:.0f}% (weaker {v['weaker_side']})" for a, v in mm["symmetry"].items() if v["flag"])
        return (f"<p class='banner'><b>What-if simulation with strength-calibrated capacities</b> ({len(mm['tests'])} "
                f"dynamometer tests, {mm['calibrated_muscles']} muscles; geometry generic, Tier {e(study['twin_tier'])}). "
                + (f"Measured deficits: {e(flags)}. " if flags else "No between-limb deficit below 90 %. ")
                + "Ground forces are estimated, not measured.</p>")
    return (f"<p class='banner'><b>What-if simulation on a generic (Tier {e(study['twin_tier'])}) muscle model.</b> "
            "Not a statement about this person's muscles (docs/accuracy.md: no 'underdeveloped muscle' claim without "
            "imaging/strength/EMG evidence; <code>rehabtwin strength</code> adds dynamometry). Ground forces are "
            "estimated, not measured.</p>")


def _consistency_span(base, study):
    e = html.escape
    out = []
    for folder, qc in study.get("kinematics_prior", {}).items():
        out.append(f"<span>planted-feet prior ({e(folder)}): feet {qc['feet_max_excursion_m']['measured'] * 100:.1f} → "
                   f"{qc['feet_max_excursion_m']['planted'] * 100:.1f} cm, joint angles changed "
                   f"{qc['coordinate_rms_change_deg']['mean']}° on average</span>")
    dc = base.get("dynamic_consistency")
    if dc:
        out.append(f"<span>dynamic consistency: <b>{'yes' if dc['consistent'] else 'NO'}</b> "
                   f"(residual ≙ {dc['pelvis_moment_residual_as_cop_shift_m'] * 100:.0f} cm CoP shift, "
                   f"{dc['pelvis_force_residual_bw'] * 100:.0f} % BW)</span>")
        if not dc["consistent"]:
            out.append("<p class='banner'><b>The estimated ground forces do not fit this motion.</b> The pelvis residuals "
                       "exceed the consistency rule, typically because the movement is too fast for a quasi-static "
                       "estimate (segment angular momentum, arm swing). Treat every muscle number on this page as "
                       "unreliable; measure ground forces (force plates or pressure insoles) for this exercise.</p>")
    return "".join(out)


def write_muscles(path, study, view=None):
    """HTML for a muscle-effects study (rehabtwin muscles); ``view`` from ``muscles.view_data``."""
    e = html.escape
    runs = study["runs"]
    groups = sorted({g for r in runs.values() for g in r["group_activation"]},
                    key=lambda g: -max(r["group_activation"].get(g, {}).get("peak", 0) for r in runs.values()))
    groups = [g for g in groups if max(r["group_activation"].get(g, {}).get("peak", 0) for r in runs.values()) >= 0.05]
    variants = {lab: {g: r["group_activation"][g]["peak"] for g in groups if g in r["group_activation"]} for lab, r in runs.items()}
    rows = []
    sens = study.get("grf_sensitivity")

    def robust(v):
        if "robust_to_grf_split" not in v:
            return ""
        lo, hi = v["change_range_over_grf_split"]
        rng = f"{lo * 100:+.0f} to {hi * 100:+.0f} pts"
        return f"<td>yes ({rng})</td>" if v["robust_to_grf_split"] else f"<td class='muted'>no ({rng})</td>"
    for lab, cmp in study.get("comparisons", {}).items():
        top = sorted(cmp.items(), key=lambda kv: -abs(kv[1]["change"]))[:8]
        cells = "".join(f"<tr><td>{e(lab)}</td><td>{e(g)}</td><td>{v['base'] * 100:.0f}%</td><td>{v['other'] * 100:.0f}%</td>"
                        f"<td>{v['change'] * 100:+.0f} pts</td>{robust(v)}</tr>" for g, v in top)
        rows.append(cells)
    sens_html = ""
    if sens:
        widest = sorted(sens["bands"].items(), key=lambda kv: -(kv[1]["hi"] - kv[1]["lo"]))[:6]
        sens_html = (f"<p class='muted'>GRF sensitivity: every variant re-run with the right foot's share of the load "
                     f"shifted by ±{sens['right_share_bias']:.2f}. A change is called robust only if it keeps its sign and "
                     f"stays ≥ {sens['min_change'] * 100:.0f} pts under every split. The absolute levels move much more "
                     f"than the changes; widest measured-run bands: "
                     + e(", ".join(f"{g} {b['lo'] * 100:.0f}–{b['hi'] * 100:.0f}%" for g, b in widest)) + "</p>")
    base = runs["measured"]
    mom = "".join(f"<tr><td>{e(k)}</td><td>{v['min_Nm_per_kg']}</td><td>{v['max_Nm_per_kg']}</td></tr>"
                  for k, v in base["joint_moments"].items())
    exo_rows = "".join(f"<tr><td>{e(lab)}</td><td>{e(c)}</td><td>{v['max_torque_Nm']}</td><td>{e(v['direction'])}</td>"
                       f"<td>{v['peak_abs_Nm']}</td><td>{v['mean_abs_Nm']}</td><td>{v['time_at_cap_fraction'] * 100:.0f}%</td></tr>"
                       for lab, r in runs.items() for c, v in r.get("assistive_devices", {}).items())
    dev_banner = (f"<p class='banner'><b>{e(study['devices_status'])}.</b></p>"
                  if study.get("devices_status", "target") not in (None, "target") else "")
    exo_html = (f"<h2>Ideal assistive devices</h2><table><tr><th>variant</th><th>joint</th><th>cap (N·m)</th><th>direction</th>"
                f"<th>peak (N·m)</th><th>mean (N·m)</th><th>time at cap</th></tr>{exo_rows}</table>" if exo_rows else "")
    pas_rows = "".join(f"<tr><td>{e(lab)}</td><td>{e(c)}</td><td>{v['stiffness_Nm_per_rad']:g}</td><td>{v['slack_deg']:g}°</td>"
                       f"<td>{e(v['direction'])}</td><td>{v['peak_abs_Nm']}</td><td>{v['mean_abs_Nm']}</td>"
                       f"<td>{v['engaged_fraction'] * 100:.0f}%</td></tr>"
                       for lab, r in runs.items() for c, v in r.get("passive_devices", {}).items())
    exo_html += (f"<h2>Passive elastic supports</h2><table><tr><th>variant</th><th>joint</th><th>stiffness (N·m/rad)</th>"
                 f"<th>slack until</th><th>resists</th><th>peak (N·m)</th><th>mean (N·m)</th><th>engaged</th></tr>"
                 f"{pas_rows}</table>" if pas_rows else "")
    exo_html = dev_banner + exo_html if exo_html else ""
    reserve_notes = "".join(f"<li>{e(lab)}: {e(', '.join(f'{k} {v} N·m' for k, v in r['reserve_torque_peaks_Nm'].items()) or 'none')}"
                            f"; saturated muscles: {e(', '.join(r['muscles_saturated']) or 'none')}</li>" for lab, r in runs.items())
    grf = base["grf"]
    mass_span, mass_banner = _body_mass(study.get("body_mass"), grf["body_mass_kg"])
    doc = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Muscle effects</title>
<style>{_CSS}</style></head><body>
<h1>Muscle effects — {e(base['exercise'])}</h1>
{_muscle_banner(study)}{mass_banner}
<div class="kv"><span>window: {base['time_range_s'][0]}–{base['time_range_s'][1]} s</span>{mass_span}
<span>vertical GRF: {grf['min_vertical_bw']}–{grf['peak_vertical_bw']} BW</span>
<span>right-foot share: {grf['right_share_range'][0]}–{grf['right_share_range'][1]}</span>
<span>feet planted: {'yes' if grf['feet_planted'] else 'NO — estimate invalid'}</span>
<span>valid exercise for this GRF model: {'yes' if base['valid_exercise'] else 'NO'}</span>
{_consistency_span(base, study)}</div>
{_svg_bars(groups, variants, "Peak muscle-group activation (fraction of group capacity)")}
{_muscle_view(view) if view else ""}
<h2>Biggest changes</h2>{sens_html}
<table><tr><th>variant</th><th>group</th><th>measured</th><th>variant</th><th>change</th>{"<th>robust to GRF split</th>" if sens else ""}</tr>{''.join(rows)}</table>
{exo_html}
<h2>Joint moments, measured (N·m/kg; OpenSim sign convention)</h2>
<table><tr><th>coordinate</th><th>min</th><th>max</th></tr>{mom}</table>
<h2>Consistency evidence</h2><ul>{reserve_notes}
<li>pelvis residuals (measured): {e(', '.join(f'{k} {v}' for k, v in base['pelvis_residual_force_N'].items()))}</li></ul>
<h2>Caveats</h2><ul>{''.join(f'<li>{e(c)}</li>' for c in dict.fromkeys(c for r in runs.values() for c in r['caveats']))}</ul>
</body></html>"""
    Path(path).write_text(doc)
    return path


def write_strength(path, rec, tier):
    """HTML for a strength calibration (rehabtwin strength)."""
    e = html.escape
    mass = rec["body_mass_kg"]
    mass_span, mass_banner = _body_mass(rec.get("body_mass"), mass)
    bound = " <span class='b fail'>at bound</span>"
    low = "<span class='b fail'>below 90%</span>"
    rows = "".join(
        f"<tr><td>{e(t['action'])}</td><td>{e(', '.join(f'{k} {v:g}°' for k, v in t['posture_deg'].items()) or 'neutral')}</td>"
        f"<td>{t['measured_Nm']:.1f}</td><td>{t['measured_Nm'] / mass:.2f}</td><td>{t['generic_model_Nm']:.1f}</td>"
        f"<td>{t['factor']:.2f}{bound if t['at_bound'] else ''}</td>"
        f"<td>{len(t['prime_movers'])} + {len(t['synergists_scaled_with_this_test'])} "
        f"({t['scaled_share_of_generic'] * 100:.0f}% of generic torque)</td></tr>"
        for t in rec["tests"])
    sym = "".join(
        f"<tr><td>{e(a)}</td><td>{v['right_Nm']:.1f}</td><td>{v['left_Nm']:.1f}</td><td>{v['lsi_pct']:.0f}%</td>"
        f"<td>{e(v['weaker_side'] or '-')}</td><td>{low if v['flag'] else 'ok'}</td></tr>"
        for a, v in rec["symmetry"].items())
    doc = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Strength calibration</title>
<style>{_CSS}</style></head><body>
<h1>Strength calibration</h1>
<p class="banner"><b>Measured joint strength, generic muscle geometry (Tier {e(tier)}).</b> Each factor is the
person's torque relative to the generic model's capacity for that test's prime movers; it rescales their
maximum isometric force and nothing else. "Weak" here means weak in the measured test — the factor says
nothing about muscle size or why.</p>{mass_banner}
<div class="kv">{mass_span}<span>muscles calibrated: {rec['calibrated_muscles']} of {rec['total_muscles']}</span>
{''.join(f"<span>{e(k)}: {e(str(rec[k]))}</span>" for k in ("device", "protocol", "tester", "date") if k in rec)}</div>
<h2>Tests</h2>
<table><tr><th>action</th><th>posture</th><th>measured (N·m)</th><th>N·m/kg</th><th>generic model (N·m)</th>
<th>factor</th><th>muscles scaled (prime + synergists)</th></tr>{rows}</table>
<h2>Limb symmetry</h2>
{f"<table><tr><th>action</th><th>right (N·m)</th><th>left (N·m)</th><th>LSI</th><th>weaker side</th><th></th></tr>{sym}</table>" if sym else "<p class='muted'>No action measured on both sides.</p>"}
<p class="muted">LSI = weaker / stronger side × 100; below 90 % is a common clinical threshold for a between-limb deficit.
Use <code>rehabtwin muscles SESSION --strength</code> to simulate with these capacities.</p>
<h2>Notes</h2><ul>{''.join(f'<li>{e(n)}</li>' for n in rec['notes'])}</ul>
</body></html>"""
    Path(path).write_text(doc)
    return path


def _svg_trend(points, title, unit, w=360, h=180):
    """One signal across sessions: mean of rep peaks with ±1 SD bars (native tooltips on points).

    A session without reps has no mean: it keeps its slot on the time axis, marked "no reps", and
    the line skips it."""
    e = html.escape
    pad_l, pad_r, pad_t, pad_b = 44, 14, 26, 34
    have = [p for p in points if p["mean"] is not None]
    if not have:
        return ""
    lo = min(p["mean"] - (p["sd"] or 0) for p in have)
    hi = max(p["mean"] + (p["sd"] or 0) for p in have)
    span = max(hi - lo, 2.0)
    lo, hi = lo - 0.15 * span, hi + 0.15 * span
    n = len(points)

    def x(i):
        return pad_l + (w - pad_l - pad_r) * (0.5 if n == 1 else i / (n - 1))

    def y(v):
        return pad_t + (h - pad_t - pad_b) * (hi - v) / (hi - lo)
    col = PALETTE[0]
    parts = [f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="{e(title)}" class="chart" style="max-width:{w}px">',
             f'<text x="{pad_l}" y="15" class="ct">{e(title)}</text>']
    for k in range(4):
        v = lo + k * (hi - lo) / 3
        parts.append(f'<line x1="{pad_l}" x2="{w - pad_r}" y1="{y(v):.1f}" y2="{y(v):.1f}" class="grid"/>'
                     f'<text x="{pad_l - 5}" y="{y(v) + 3:.1f}" class="ax" text-anchor="end">{v:.0f}</text>')
    line = " ".join(f"{x(i):.1f},{y(p['mean']):.1f}" for i, p in enumerate(points) if p["mean"] is not None)
    parts.append(f'<polyline points="{line}" fill="none" stroke="{col}" stroke-width="2"/>')
    for i, p in enumerate(points):
        if p["mean"] is None:
            parts.append(f'<text x="{x(i):.1f}" y="{(h + pad_t - pad_b) / 2:.1f}" class="ax" text-anchor="middle">'
                         f'no reps</text><text x="{x(i):.1f}" y="{h - 12}" class="ax" text-anchor="middle">'
                         f'{e(p["started_at"][:10])}</text>')
            continue
        if p["sd"]:
            parts.append(f'<line x1="{x(i):.1f}" x2="{x(i):.1f}" y1="{y(p["mean"] - p["sd"]):.1f}" '
                         f'y2="{y(p["mean"] + p["sd"]):.1f}" stroke="{col}" stroke-width="2"/>')
        tip = f'{p["session_id"]} ({p["started_at"][:10]}): {p["mean"]:.1f} {unit}' + (f' ± {p["sd"]:.1f}' if p["sd"] else "") \
            + f', {p["n_reps"]} reps'
        parts.append(f'<circle cx="{x(i):.1f}" cy="{y(p["mean"]):.1f}" r="5" fill="{col}" stroke="var(--bg)" stroke-width="2">'
                     f'<title>{e(tip)}</title></circle>'
                     f'<text x="{x(i):.1f}" y="{h - 12}" class="ax" text-anchor="middle">{e(p["started_at"][:10])}</text>')
    parts.append("</svg>")
    return "".join(parts)


def write_progress(path, prog):
    """HTML for rehabtwin progress: first → last verdicts and a trend per signal."""
    e = html.escape
    verdict_class = {"real change (beyond rep scatter and measurement error)": "pass",
                     "within measurement error": "not-tested", "within rep-to-rep scatter": "not-tested"}
    rows = []

    def num(v, f=".1f"):     # None: a session without reps
        return "–" if v is None else format(v, f)
    for sig, j in prog["first_to_last"].items():
        if not j:
            continue
        cls = verdict_class.get(j["verdict"], "unvalidated")
        rows.append(f"<tr><td>{e(sig)}</td><td>{num(j['from'])}</td><td>{num(j['to'])}</td>"
                    f"<td>{num(j['change'], '+.1f')} {e(j['unit'])}</td>"
                    f"<td>{j.get('rep_threshold', '–')}</td><td>{j.get('mdc95', '–')}</td>"
                    f"<td><span class='b {cls}'>{e(j['verdict'])}</span></td></tr>")
    pt = " <span class=muted>(processing time)</span>"
    sess = "".join(f"<tr><td>{e(s['session_id'])}</td><td>{e(s['started_at'])}"
                   f"{pt if s.get('started_at_source') == 'processing time' else ''}</td><td>{e(s['tier'])}</td>"
                   f"<td>{e(s['front_end'])}</td><td>{s['n_reps']}</td></tr>" for s in prog["sessions"])
    first = prog["first_to_last"]
    charts = "".join(_svg_trend(prog["series"][sig], f"{sig} (mean of rep peaks)", first[sig]["unit"])
                     for sig in prog["series"] if first.get(sig))
    warn = "".join(f"<p class='banner'>{e(w)}</p>" for w in prog["warnings"])
    doc = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Progress</title>
<style>{_CSS}</style></head><body>
<h1>Progress over {len(prog['sessions'])} sessions</h1>
<p class="banner"><b>A change is only called real when it beats both the rep-to-rep scatter and the validated
measurement error.</b> Without a marker-mocap validation of that joint × plane the size of a change is unknown, even
when it is consistent across reps.</p>{warn}
<h2>First → last session</h2>
<table><tr><th>signal</th><th>first</th><th>last</th><th>change</th><th>rep threshold</th><th>MDC95</th><th>verdict</th></tr>
{''.join(rows)}</table>
<h2>Trends</h2><div style="display:flex;flex-wrap:wrap;gap:8px">{charts}</div>
<h2>Sessions</h2><table><tr><th>session</th><th>started</th><th>tier</th><th>front end</th><th>reps</th></tr>{sess}</table>
<p class="muted">{e(prog['method'])}</p>
</body></html>"""
    Path(path).write_text(doc)
    return path


def write_correction(path, summary, measured_time, signals_measured, signals_corrected, skeleton, skeleton_corrected):
    """HTML for one correction: measured (solid) vs corrected (dashed) on the same model."""
    e = html.escape
    keys = list(summary["changes"]) + list(summary["compensations"])[:4]
    charts = []
    for k in keys:
        if k in signals_measured:
            charts.append(_svg_chart(measured_time, {k: signals_measured[k]}, [], f"{k}: measured vs corrected",
                                     ref=(measured_time, {k: signals_corrected[k]}), ref_label="corrected"))
    for title, ks in (("Knee frontal-plane projection angle (+ valgus)", ["knee_fppa_r", "knee_fppa_l"]),
                      ("Trunk vs gravity (sagittal, + forward)", ["torso.sagittal"])):
        ser = {k: signals_measured[k] for k in ks if k in signals_measured}
        if ser:
            charts.append(_svg_chart(measured_time, ser, [], title,
                                     ref=(measured_time, {k: signals_corrected[k] for k in ser}), ref_label="corrected"))
    rows = "".join(f"<tr><td>{e(c)}</td><td>requested</td><td>{v['max_abs_change_deg']}</td>"
                   f"<td>tracking RMSE {v['target_tracking_rmse_deg']}</td></tr>" for c, v in summary["changes"].items())
    rows += "".join(f"<tr><td>{e(c)}</td><td>compensation</td><td>{v['max_abs_change_deg']}</td>"
                    f"<td>mean {v['mean_change_deg']:+}</td></tr>" for c, v in summary["compensations"].items())
    viol = "".join(f"<li>{e(v['coordinate'])}: exceeds range {v['range']} by {v['exceeds_range_by']}°"
                   f" (measured motion: {v.get('measured_exceeds_by', 0)}°)</li>"
                   for v in summary["range_of_motion_violations"]) or "<li>none introduced by the correction</li>"
    viol += "".join(f"<li class='muted'>{e(v['coordinate'])}: already outside the model's range {v['range']} in the measured "
                    f"motion (by {v['measured_exceeds_by']}°) — a model limit, not a correction effect</li>"
                    for v in summary.get("range_exceeded_in_measured_motion", []))
    drift = summary["feet_anchor_drift_m"]
    rc = summary.get("rule_check")
    rule_html = ""
    if rc:
        def cell(v):
            return f"{v['violations']}" + (f" (worst {v['worst']:+.1f})" if v["worst"] is not None else "")
        rrows = "".join(f"<tr><td>{e(r)}</td><td>{cell(v['measured'])}</td><td>{cell(v['corrected'])}</td>"
                        f"<td>{'removed' if r in rc['removed'] else '<b>introduced</b>' if r in rc['introduced'] else ''}</td></tr>"
                        for r, v in rc["per_rule"].items())
        rule_html = (f"<h2>Posture rules ({e(rc['rules'])}) on the corrected motion</h2>"
                     + (f"<p class='banner'>The correction introduces: {e(', '.join(rc['introduced']))}.</p>" if rc["introduced"] else "")
                     + f"<table><tr><th>rule</th><th>measured: violations</th><th>corrected: violations</th><th></th></tr>{rrows}</table>"
                     f"<p class='muted'>{e(rc['note'])}</p>")
    banner = ("<p class='banner'><b>ILLUSTRATION ONLY.</b> Computed on a generic (Tier "
              f"{e(summary['twin_tier'])}) skeleton — docs/accuracy.md forbids using it as a correction target "
              "or for feedback. It shows what the requested change implies for the rest of the body.</p>"
              if summary["twin_tier"] != "A" else
              "<p class='banner'><b>Tier A correction target.</b> Clinician review required before use.</p>")
    doc = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Correction {e(summary['spec'])}</title>
<style>{_CSS}</style></head><body>
<h1>Correction view — {e(summary['spec'])}</h1>
{banner}
<p>{e(summary['rationale'])} <span class="muted">Spec author: {e(summary['spec_author'])}.</span></p>
<div class="kv"><span>admissible: <b>{'yes' if summary['admissible'] else 'no'}</b> ({e(summary['admissible_rule'])})</span>
<span>feet drift: mean {drift['mean']} m, max {drift['max']} m</span></div>
{_player(skeleton, skeleton_corrected, ref_label="corrected", ref_color="#059669", align_pelvis=False)}
{''.join(charts)}
<h2>What changed</h2>
<table><tr><th>coordinate</th><th>kind</th><th>max change (°)</th><th></th></tr>{rows}</table>
<h2>Range-of-motion check</h2><ul>{viol}</ul>
{rule_html}
<p class="muted">Files: {e(summary['measured_motion'])} (measured), {e(summary['corrected_motion'])} (corrected), correction.json.</p>
</body></html>"""
    Path(path).write_text(doc)
    return path


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
        flag = (" ⚠ imputed frames" if r["contains_imputed_frames"] else "") + (
            " ⚠ missing markers" if r.get("contains_missing_markers") else "")
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
    gaps = sorted(((n, g) for n, g in qc.get("imputed_by_marker", {}).items() if g["imputed_spans"] or g["missing_spans"]),
                  key=lambda ng: -(ng[1]["imputed_s"] + ng[1]["missing_s"]))
    gap_html = "" if not gaps else (
        f"<p class='muted'>Marker gaps in {len(gaps)} of {len(qc['imputed_by_marker'])} markers (bridged up to "
        f"{qc.get('filter', {}).get('max_gap_s', '?')} s, longer gaps left without an IK target): "
        + "; ".join(f"{e(n)} {g['imputed_s']} s bridged, {g['missing_s']} s missing" for n, g in gaps[:5])
        + (f"; {len(gaps) - 5} more in qc.json" if len(gaps) > 5 else "") + ".</p>")
    un = qc.get("unsolved", {})
    if un.get("frames"):
        gap_html += (f"<p class='muted'>{un['frames']} frames not solved: fewer than {un['min_target_weight']:.0%} of "
                     f"the IK marker weight had a target there ({len(un['spans'])} spans, see qc.json).</p>")
    seg = qc.get("analysed_segment")
    if seg and seg["of"] > 1:
        gap_html += (f"<p class='muted'><b>Metrics cover segment {seg['segment']} of {seg['of']} only</b>, "
                     f"{seg['start_s']}–{seg['stop_s']} s ({seg['fraction']:.0%} of the {seg['trial_s']} s trial): "
                     "reps outside it are not counted.</p>")
    val_html = ""
    if validation:
        gate_rows = "".join(f"<tr><td>{e(g)}</td><td><span class='b {v}'>{v}</span></td></tr>"
                            for g, v in validation["gates"].items() if v != "not-tested")
        cov = validation.get("coverage")
        cov_html = "" if not cov else (
            f" Compared {cov['compared_s']} s of the {cov['overlap_s']} s both systems recorded ({cov['fraction']:.0%}).")
        val_html = (f"<h2>Validation against reference</h2><p>Reference: {e(validation['reference_system'])}. "
                    f"Approved for: <b>{e(', '.join(validation['approved_for']) or 'nothing')}</b>.{cov_html} "
                    f"{e(validation.get('notes', ''))}</p>"
                    f"<table><tr><th>gate</th><th>result</th></tr>{gate_rows}</table>")
    doc = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Session {e(session['session_id'])}</title>
<style>{_CSS}</style></head><body>
<h1>Session {e(session['session_id'])} — {e(metrics['exercise'])}{' (SYNTHETIC)' if synthetic else ''}</h1>
<p class="banner"><b>Tier {tier}.</b> {e(metrics['claims'])} Research prototype, not a medical device.</p>
<div class="kv muted"><span>reps: <b>{metrics['n_reps']}</b></span><span>detection rate: {qc.get('detection_rate')}</span>
<span>imputed frames: {len(qc.get('imputed_frames', []))}</span><span>gravity: {e(str(fr.get('up_source')))}</span>
<span>IK marker RMS: {ik.get('marker_rms_m', {}).get('mean')} m (p95 {ik.get('marker_rms_m', {}).get('p95')})</span></div>
{gap_html}
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
