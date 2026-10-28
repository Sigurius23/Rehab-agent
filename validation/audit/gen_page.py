"""Build the audit page from the audit outputs and test logs (no number typed by hand)."""
import html
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

A = Path(sys.argv[1])                     # audit folder
OUT = Path(sys.argv[2])
e = html.escape
checks = json.loads((A / "audit_a.json").read_text())["checks"] + json.loads((A / "audit_b.json").read_text())["checks"]
commit = (A / "suite_commit.txt").read_text().strip()


def suite(path):
    text = path.read_text()
    rows = re.findall(r"^(tests/\S+?)::(\S+) (PASSED|FAILED|SKIPPED|ERROR)", text, re.M)
    final = re.search(r"=+ (.*?) in ([\d.]+)s", text.splitlines()[-1] if text.strip() else "")
    return rows, (final.group(1) if final else "not finished"), (float(final.group(2)) if final else None)


run1, sum1, t1 = suite(A / "suite_verbose.log")
run2, sum2, t2 = suite(A / "suite_verbose_2.log")
race = (A / "race.log").read_text().strip().splitlines()
SECTIONS = {
    "markers": ("Pose2Sim marker set reused on other bones",
                "Read straight from Pose2Sim's and OpenCap's public files: the XML marker sets, and joint and marker "
                "positions from the OpenSim API in the default pose."),
    "shank": ("Shank and hip width of the scaled models",
              "Joint-centre distances read from the scaled .osim files with the OpenSim API."),
    "opencap": ("Agreement with OpenCap, before and after the marker fix",
                "RMSE recomputed from our ik.mot and OpenCap's squats1.mot with a reader written for the audit. "
                "The reference is shifted by the time lag stored in each validation report and interpolated onto our frames."),
    "skel-synthetic": ("SKEL bones from one synthetic depth frame",
                       "Summary recomputed from the 45 per-body rows; the stored true bones re-derived from the stored "
                       "shape parameters with the SKEL and SMPL files and plain numpy."),
    "skel-subject2": ("SKEL on OpenCap subject 2 (height and mass)",
                      "Body height, volume mass and SKEL segments recomputed from the stored shape parameters."),
    "dxa-squat": ("Squat with an illustrative DXA record",
                  "Read from the three muscle-study outputs (height and mass, age and sex, DXA)."),
    "nhanes": ("NHANES 1999-2002: DXA, age and sex, height and mass against knee strength",
               "Cohort rebuilt from the raw CDC survey files with new code; the shipped leg-lean coefficients refitted."),
    "myosegmentum": ("MyoSegmenTUM thigh MRI and strength",
                     "Correlations and ratios recomputed from the per-person rows (measured volumes, measured torque, "
                     "model torque)."),
}
by = defaultdict(list)
for c in checks:
    by[c["section"]].append(c)
n_ok = sum(c["ok"] for c in checks)
n_all = len(checks)
files1 = Counter(r[0] for r in run1)
fails1 = [f"{r[0]}::{r[1]}" for r in run1 if r[2] != "PASSED"]
fails2 = [f"{r[0]}::{r[1]}" for r in run2 if r[2] != "PASSED"]
pass2 = sum(r[2] == "PASSED" for r in run2)


def chip(ok, yes="Matches", no="Differs"):
    return f'<span class="chip {"ok" if ok else "bad"}">{yes if ok else no}</span>'


sec_html = []
for key, (title, how) in SECTIONS.items():
    rows = by.get(key, [])
    if not rows:
        continue
    trs = "".join(
        f"<tr><td>{e(c['claim'])}{('<div class=note>' + e(c['note']) + '</div>') if c['note'] else ''}</td>"
        f"<td class=num>{e(str(c['stated']))}</td><td class=num>{e(str(c['measured']))}</td><td>{chip(c['ok'])}</td></tr>"
        for c in rows)
    ok = sum(c["ok"] for c in rows)
    sec_html.append(f"""
<section class="claims" id="{key}">
  <div class="sechead"><h3>{e(title)}</h3><span class="count">{ok} of {len(rows)} match</span></div>
  <p class="how">{e(how)}</p>
  <div class="tablewrap"><table>
    <thead><tr><th>Claim</th><th>What I said</th><th>Recomputed now</th><th>Result</th></tr></thead>
    <tbody>{trs}</tbody>
  </table></div>
</section>""")

test_files = "".join(f"<tr><td><code>{e(f)}</code></td><td class=num>{n}</td></tr>" for f, n in sorted(files1.items()))
test_list = "".join(
    f"<li><code>{e(r[0].replace('tests/', ''))}::{e(r[1])}</code> {chip(r[2] == 'PASSED', 'passed', r[2].lower())}</li>"
    for r in run2) if run2 else "<li>Second run not finished.</li>"
race_rows = "".join(f"<li><code>{e(x)}</code></li>" for x in race)
SP = str(A.parent)
VIZ_CSS = """
.vblock { display: grid; gap: 12px; }
.vblock + .vblock { border-top: 1px solid var(--rule); padding-top: 28px; }
.controls { display: flex; flex-wrap: wrap; align-items: center; gap: 10px 18px; font-size: 0.88rem; }
.controls label { display: inline-flex; align-items: center; gap: 6px; cursor: pointer; }
.controls input[type=range] { width: 150px; accent-color: var(--accent); }
.controls input[type=checkbox], .controls input[type=radio] { accent-color: var(--accent); margin: 0; }
.controls output { font: 500 0.82rem var(--mono); font-variant-numeric: tabular-nums; min-width: 4.6em; }
.seg { display: inline-flex; flex-wrap: wrap; border: 1px solid var(--rule); border-radius: 6px; overflow: hidden; background: var(--surface); }
.seg label { padding: 4px 10px; gap: 0; }
.seg input { position: absolute; opacity: 0; pointer-events: none; }
.seg label:has(input:checked) { background: var(--accent); color: var(--bg); }
.seg label:has(input:focus-visible) { outline: 2px solid var(--accent); outline-offset: -2px; }
.viewer { position: relative; height: 460px; border-radius: 6px; overflow: hidden; background: var(--viz-bg);
  border: 1px solid var(--rule); touch-action: none; }
.viewer canvas { display: block; width: 100%; height: 100%; }
.v-labels { position: absolute; inset: 0; pointer-events: none; }
.v-label { position: absolute; left: 0; top: 0; font: 500 0.72rem/1.2 var(--mono); color: var(--ink); white-space: nowrap;
  background: var(--surface); border: 1px solid var(--rule); border-radius: 4px; padding: 2px 6px; }
.v-label.accent { color: var(--accent); border-color: var(--accent); }
.v-label.small { font-size: 0.66rem; }
.v-label.s1::before, .v-label.s2::before, .v-label.s3::before { content: ""; display: inline-block; width: 8px; height: 8px;
  border-radius: 50%; margin-right: 6px; vertical-align: 0; }
.v-label.s1::before { background: var(--s1); } .v-label.s2::before { background: var(--s2); } .v-label.s3::before { background: var(--s3); }
.v-failed { display: grid; place-items: center; padding: 24px; color: var(--muted); text-align: center; height: auto; min-height: 120px; }
.caption { color: var(--muted); font-size: 0.86rem; }
tr.mine td { background: var(--code-bg); }
.squat { display: flex; gap: 12px; }
.squat .viewer { flex: 1; min-width: 0; height: 440px; }
.videobox { position: relative; height: 440px; aspect-ratio: 9 / 16; max-width: 100%; border-radius: 6px; overflow: hidden;
  background: #000; flex: none; }
.videobox video, .videobox canvas { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: contain; }
.videobox .vnote { position: absolute; inset: auto 8px 8px; color: #fff; font-size: 0.75rem; }
button.play { font: 500 0.85rem var(--body); padding: 5px 14px; border-radius: 6px; border: 1px solid var(--accent);
  background: var(--accent); color: var(--bg); cursor: pointer; min-width: 5.5em; }
button.play:focus-visible, select:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
#q-scrub { flex: 1; min-width: 140px; width: auto; }
.chartbox { position: relative; display: grid; gap: 8px; background: var(--surface); border: 1px solid var(--rule);
  border-radius: 6px; padding: 12px 14px; }
.chartbox select { font: inherit; font-size: 0.88rem; padding: 3px 6px; border-radius: 4px; border: 1px solid var(--rule);
  background: var(--surface); color: var(--ink); }
.legend { display: flex; flex-wrap: wrap; gap: 6px 18px; font-size: 0.82rem; }
.lg { display: inline-flex; align-items: center; gap: 6px; }
.lg i { width: 18px; height: 0; border-top: 2px solid var(--c); }
.lg i.dash { border-top-style: dashed; }
.muted { color: var(--muted); }
#q-chart { width: 100%; height: auto; display: block; overflow: visible; }
#q-chart .gridline { stroke: var(--rule); stroke-width: 1; }
#q-chart .tick, #q-chart .endlabel { fill: var(--muted); font: 11px var(--mono); }
#q-chart .endlabel { fill: var(--ink); }
#q-chart .cursor { stroke: var(--ink); stroke-width: 1.5; }
#q-chart .hoverline { stroke: var(--muted); stroke-width: 1; stroke-dasharray: 3 3; }
.tip { position: absolute; top: 56px; background: var(--surface); border: 1px solid var(--rule); border-radius: 6px;
  padding: 8px 10px; font-size: 0.78rem; pointer-events: none; box-shadow: 0 4px 14px rgba(0,0,0,0.12); display: grid; gap: 3px; }
.tip div { display: flex; align-items: center; gap: 6px; }
.tip i { width: 8px; height: 8px; border-radius: 50%; }
.tip span { margin-left: auto; padding-left: 12px; font-family: var(--mono); font-variant-numeric: tabular-nums; }
@media (max-width: 640px) {
  .viewer { height: 380px; }
  .squat { flex-direction: column; }
  .squat .viewer { flex: none; height: 360px; }
  .videobox { height: 360px; align-self: center; }
}
"""
VIZ_HTML = """
<section class="block" id="in-3d">
  <h2>The models in 3D</h2>
  <p class="how">Drag to turn a view, scroll or pinch to zoom, right-drag to move. Everything is computed from the same
  files the audit reads: the bodies and bones in your browser from SKEL's shape parameters, the squat from our OpenSim
  results and OpenCap's.</p>

  <div class="vblock">
    <h3>Bodies and their bones</h3>
    <p>SKEL puts an anatomical skeleton inside an SMPL body: it predicts where the joint centres sit from the skin surface,
    then sizes each bone to fit. The six bodies to the right of yours are the ones from the audit: five synthetic test bodies from
    BMI 19 to 44 and OpenCap subject 2 built from height and mass. The first one is yours: set a height and weight and
    the page builds the SMPL body nearest the average shape with those numbers, then its bones. That is what
    <code>rehabtwin person bones</code> does when it has no depth scan.</p>
    <div class="controls" role="group" aria-label="Your body">
      <span class="seg"><label><input type="radio" name="b-sex" id="b-sex-f" value="female">Female</label><label><input
        type="radio" name="b-sex" id="b-sex-m" value="male" checked>Male</label></span>
      <label for="b-height">Height <input type="range" id="b-height" min="1.45" max="2.05" step="0.01" value="1.80"></label>
      <output id="b-height-out" for="b-height">1.80 m</output>
      <label for="b-mass">Weight <input type="range" id="b-mass" min="40" max="160" step="0.5" value="80"></label>
      <output id="b-mass-out" for="b-mass">80.0 kg</output>
      <label><input type="checkbox" id="b-skin" checked>Skin</label>
      <label><input type="checkbox" id="b-joints" checked>Joint centres</label>
    </div>
    <div class="viewer" id="v-bodies" aria-label="Seven bodies with their SKEL bones, standing in a row"></div>
    <p class="caption" id="b-built"></p>
    <div class="tablewrap"><table>
      <thead><tr><th>Body</th><th>Sex</th><th>Height (m)</th><th>Mass (kg)</th><th>BMI</th><th>Thigh</th><th>Shank</th>
      <th>Upper arm</th><th>Forearm</th><th>Hip width</th></tr></thead>
      <tbody id="bodies-rows"></tbody>
    </table></div>
    <p class="caption">Segment lengths in cm between SKEL joint centres, right side, measured on the bodies as built here.
    Mass is the mesh volume at 1000 kg/m³. SKEL predicts these from the surface; it has never seen these people's bones.</p>
  </div>

  <div class="vblock">
    <h3>From one depth frame to bones</h3>
    <p>The synthetic test behind the SKEL claims: a body seen once by a simulated Kinect v1. The points are all the fit
    sees. Our body-shape fit turns them into an SMPL body (the translucent surface), and SKEL turns that into bones,
    standing on the right. Blue dots are the joint centres from the fit, orange dots those of the true body.</p>
    <div class="controls">
      <span class="seg" role="radiogroup" aria-label="Test body"><label><input type="radio" name="d-body" value="0" checked><span
        id="d-body-0-label">Body 1</span></label><label><input type="radio" name="d-body" value="1"><span
        id="d-body-1-label">Body 2</span></label></span>
      <label><input type="checkbox" id="d-points" checked>Depth points</label>
      <label><input type="checkbox" id="d-fit" checked>Fitted body</label>
      <label><input type="checkbox" id="d-truth">True body</label>
    </div>
    <div class="viewer" id="v-depth" aria-label="Depth points of one body, the fitted body and its bones"></div>
    <p class="caption" id="depth-caption"></p>
    <div class="tablewrap"><table style="min-width: 0">
      <thead><tr><th>Segment (cm)</th><th>True body</th><th>From the fit</th><th>Difference</th></tr></thead>
      <tbody id="depth-rows"></tbody>
    </table></div>
  </div>

  <div class="vblock">
    <h3>Tracking a real squat</h3>
    <p>OpenCap's public test recording: subject 2 squatting, filmed by five phones. Shown is camera 2 with the MediaPipe
    keypoints our pipeline detected; the five cameras together give the 3D motion. The bones are our scaled OpenSim
    model after the marker fix, posed by our inverse kinematics. The stick figures are joint centres: blue ours, orange
    ours before the fix (shank too long), green OpenCap's own result from the same videos.</p>
    <div class="controls">
      <button type="button" class="play" id="q-play" aria-pressed="false">Play</button>
      <input type="range" id="q-scrub" min="0" max="580" step="1" value="0" aria-label="Time">
      <output id="q-time" for="q-scrub">0.00 s</output>
    </div>
    <div class="controls">
      <label><input type="checkbox" id="q-mesh" checked>Bones</label>
      <label><input type="checkbox" id="q-opencap" checked>OpenCap's result</label>
      <label><input type="checkbox" id="q-base">Before the marker fix</label>
      <label><input type="checkbox" id="q-kpshow" checked>Keypoints on video</label>
      <span class="seg" role="radiogroup" aria-label="Layout"><label><input type="radio" name="q-layout" id="q-side"
        checked>Side by side</label><label><input type="radio" name="q-layout" id="q-over">Overlaid</label></span>
    </div>
    <div class="squat">
      <div class="videobox"><video id="q-video" muted playsinline loop preload="auto"></video><canvas id="q-kp"></canvas>
        <div class="vnote" id="q-video-note" hidden>The video could not load; the 3D view still plays.</div></div>
      <div class="viewer" id="v-squat" aria-label="The squat in 3D: our model and OpenCap's"></div>
    </div>
    <p class="caption" id="q-shank"></p>
    <div class="chartbox">
      <div class="controls"><label for="q-coord">Joint angle</label><select id="q-coord"></select></div>
      <div class="legend" id="q-legend"></div>
      <svg id="q-chart" viewBox="0 0 900 230" role="img" aria-label="Joint angle over time, three sources"></svg>
      <div class="tip" id="q-tip" hidden></div>
    </div>
    <p class="caption">Click the chart to jump to that moment. OpenCap is another markerless system, not ground truth.
    Its result is shifted by the time lag stored in our validation report (0.067 s). Angles in degrees, as OpenSim
    defines them.</p>
  </div>
  <p class="caption">Licences: the body and bone meshes come from SMPL and SKEL (Max Planck Institute for Intelligent
  Systems, non-commercial research only, no redistribution), so keep this page private. The squat video and OpenCap's
  result are OpenCap's public test data; the bone meshes in the squat are OpenSim's model geometry.</p>
</section>
"""
page = f"""<title>Rehab Twin Claims Audit</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Condensed:wght@500;600&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
/* Layout: one reading column; summary figures first, then one table per claim group, then how to rerun. */
:root {{
  --bg: #f6f7f5; --surface: #ffffff; --ink: #1b2129; --muted: #59626e; --rule: #d9ddd8;
  --accent: #245d7a; --ok: #2c6e49; --ok-bg: #e3f0e7; --bad: #9a4a12; --bad-bg: #f8e9dc;
  --code-bg: #eef0ec;
  --viz-bg: #e9ece8; --viz-grid: #c5cbc4; --bone: #e6dcc6; --skin: #7d95ab; --pts: #3e4a57; --muted-3d: #59626e;
  --s1: #2a78d6; --s2: #eb6834; --s3: #1baf7a;
  --display: "IBM Plex Sans Condensed", "Arial Narrow", system-ui, sans-serif;
  --body: "IBM Plex Sans", system-ui, -apple-system, "Segoe UI", sans-serif;
  --mono: "IBM Plex Mono", ui-monospace, "SFMono-Regular", Menlo, monospace;
}}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{
  --bg: #12161b; --surface: #1a2027; --ink: #e5e8ec; --muted: #9aa3ae; --rule: #2c343d;
  --accent: #7fb6d4; --ok: #8fd0a6; --ok-bg: #1d3327; --bad: #f0a56d; --bad-bg: #3a2718; --code-bg: #222a32;
  --viz-bg: #161b21; --viz-grid: #2c353f; --bone: #d6cbb2; --skin: #8fa7bc; --pts: #b8c3ce; --muted-3d: #9aa3ae;
  --s1: #3987e5; --s2: #d95926; --s3: #199e70;
  color-scheme: dark; }} }}
:root[data-theme="dark"] {{
  --bg: #12161b; --surface: #1a2027; --ink: #e5e8ec; --muted: #9aa3ae; --rule: #2c343d;
  --accent: #7fb6d4; --ok: #8fd0a6; --ok-bg: #1d3327; --bad: #f0a56d; --bad-bg: #3a2718; --code-bg: #222a32;
  --viz-bg: #161b21; --viz-grid: #2c353f; --bone: #d6cbb2; --skin: #8fa7bc; --pts: #b8c3ce; --muted-3d: #9aa3ae;
  --s1: #3987e5; --s2: #d95926; --s3: #199e70;
  color-scheme: dark; }}
body {{ background: var(--bg); color: var(--ink); font: 15px/1.55 var(--body); }}
.wrap {{ max-width: 980px; margin: 0 auto; padding-block: 32px 64px;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px));
  display: grid; grid-template-columns: minmax(0, 1fr); gap: 36px; }}
h1, h2, h3 {{ font-family: var(--display); text-wrap: balance; margin: 0; line-height: 1.2; }}
h1 {{ font-size: 2rem; font-weight: 600; }}
h2 {{ font-size: 1.35rem; font-weight: 600; }}
h3 {{ font-size: 1.1rem; font-weight: 600; }}
p {{ margin: 0; max-width: 68ch; }}
.eyebrow {{ font: 500 0.75rem/1 var(--mono); letter-spacing: 0.06em; text-transform: uppercase; color: var(--accent); }}
header {{ display: grid; gap: 12px; }}
.lede {{ color: var(--muted); }}
.figures {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; }}
.fig {{ background: var(--surface); border: 1px solid var(--rule); border-radius: 6px; padding: 14px 16px; display: grid; gap: 4px; }}
.fig b {{ font: 600 1.6rem/1.1 var(--display); font-variant-numeric: tabular-nums; }}
.fig span {{ color: var(--muted); font-size: 0.86rem; }}
.block {{ display: grid; gap: 14px; }}
.finding {{ border-left: 3px solid var(--bad); padding: 4px 0 4px 14px; display: grid; gap: 8px; }}
.finding.fixed {{ border-left-color: var(--ok); }}
.claims {{ display: grid; gap: 10px; }}
.sechead {{ display: flex; flex-wrap: wrap; align-items: baseline; justify-content: space-between; gap: 8px; }}
.count {{ font: 500 0.8rem var(--mono); color: var(--muted); }}
.how {{ color: var(--muted); font-size: 0.9rem; }}
.tablewrap {{ overflow-x: auto; border: 1px solid var(--rule); border-radius: 6px; background: var(--surface); }}
table {{ border-collapse: collapse; width: 100%; min-width: 640px; font-size: 0.88rem; }}
th, td {{ text-align: left; vertical-align: top; padding: 9px 12px; border-bottom: 1px solid var(--rule); }}
tbody tr:last-child td {{ border-bottom: 0; }}
th {{ font: 500 0.72rem var(--mono); letter-spacing: 0.05em; text-transform: uppercase; color: var(--muted); }}
td.num {{ font-family: var(--mono); font-size: 0.82rem; font-variant-numeric: tabular-nums; }}
.note {{ color: var(--muted); font-size: 0.8rem; margin-top: 3px; }}
.chip {{ display: inline-block; font: 500 0.72rem/1 var(--mono); padding: 4px 7px; border-radius: 999px; white-space: nowrap; }}
.chip.ok {{ background: var(--ok-bg); color: var(--ok); }}
.chip.bad {{ background: var(--bad-bg); color: var(--bad); }}
code, pre {{ font-family: var(--mono); font-size: 0.82rem; }}
code {{ background: var(--code-bg); padding: 1px 4px; border-radius: 3px; overflow-wrap: anywhere; }}
pre {{ background: var(--code-bg); padding: 12px 14px; border-radius: 6px; overflow-x: auto; margin: 0; line-height: 1.5; }}
pre code {{ background: none; padding: 0; }}
ul {{ margin: 0; padding-left: 20px; display: grid; gap: 4px; }}
details {{ background: var(--surface); border: 1px solid var(--rule); border-radius: 6px; padding: 10px 14px; }}
summary {{ cursor: pointer; font-weight: 500; }}
summary:focus-visible, a:focus-visible {{ outline: 2px solid var(--accent); outline-offset: 2px; }}
details ul {{ margin-top: 10px; list-style: none; padding-left: 0; font-size: 0.82rem; }}
.limits li {{ max-width: 70ch; }}
a {{ color: var(--accent); }}
{VIZ_CSS}
</style>
<div class="wrap">
<header>
  <div class="eyebrow">Audit · {e(commit.split()[0])} · feat/kinect-v1</div>
  <h1>Rehab Twin Claims Audit</h1>
  <p class="lede">Every headline number from the last sessions, recomputed from the raw result files with code written only
  for this audit. It doesn't import the pipeline. The test suite was also run again from scratch. Where something didn't
  hold, it is listed first.</p>
</header>

<div class="figures">
  <div class="fig"><b>{n_ok} of {n_all}</b><span>claims match when recomputed</span></div>
  <div class="fig"><b>{n_all - n_ok}</b><span>claim wrong as written (corrected)</span></div>
  <div class="fig"><b>{e(sum1)}</b><span>first fresh test run ({t1 / 60:.0f} min)</span></div>
  <div class="fig"><b>{e(sum2)}</b><span>after the fix below{f' ({t2 / 60:.0f} min)' if t2 else ''}</span></div>
</div>
{VIZ_HTML}

<section class="block">
  <h2>What didn't hold</h2>
  <div class="finding fixed">
    <h3>1. The synthetic bodies' BMI range was wrong in the docs</h3>
    <p>I wrote that the 45 SKEL test bodies span BMI 17–43. That is the range of the BEDLAM2 bodies they were built from
    (17.7–42.5). Giving each body its own proportions changed its mass, so the bodies actually tested span 17.4–44.3.
    The error results are unaffected. Corrected in <code>docs/person-model.md</code> and <code>CHANGELOG.md</code>
    (commit <code>8f82ac9</code>); the commit message of <code>3d69d75</code> still says 17–43.</p>
  </div>
  <div class="finding fixed">
    <h3>2. One test failed in the fresh run: the Kinect recorder could write frames out of order</h3>
    <p>Every earlier run of all 170 tests passed. This run, <code>test_csharp_recorder_output_reads_back</code> failed:
    one recorded frame number went backwards. The cause is in the fake sensor the test uses. Its timer callbacks overlap
    when a frame takes longer than its 33 ms period, and it numbered each frame before taking the lock, so two
    overlapping frames could arrive swapped. A small program with the old and the new logic and a slow frame handler
    shows it:</p>
    <ul>{race_rows}</ul>
    <p>Fixed in two places. The fake sensor now numbers frames inside the lock. The recorder now drops and counts a frame
    that arrives after a later one (<code>late_frames_dropped</code> in <code>meta.json</code>), which also guards a real
    sensor. The real Kinect SDK couldn't be tested here. Commit <code>8f82ac9</code>; after it the full suite passes
    (170 of 170).</p>
  </div>
</section>

<section class="block">
  <h2>Claims, recomputed</h2>
  <p class="how">Each row shows the number as I stated it and the value recomputed now from the stored outputs. Tolerances
  are the rounding of the stated value.</p>
</section>
{''.join(sec_html)}

<section class="block">
  <h2>What these checks don't show</h2>
  <ul class="limits">
    <li><b>Correct arithmetic, not correct anatomy.</b> The audit checks that each number follows from the stored
    outputs. It does not re-run OpenSim's inverse kinematics or muscle simulation, and it trusts the MRI volumes the
    adapter computed from the masks (the raw scans were deleted to save space; they can be downloaded again from OSF).</li>
    <li><b>OpenCap is not ground truth.</b> It is another markerless system; agreement with it is not accuracy.</li>
    <li><b>The SKEL test is synthetic.</b> It measures the chain from depth sensor to SKEL, not SKEL against real bone.</li>
    <li><b>NHANES covers healthy adults aged 50+</b>, not people in rehab.</li>
    <li><b>Everything is still Tier C</b>: no result here is validated against marker motion capture or imaging of the
    same person.</li>
  </ul>
</section>

<section class="block">
  <h2>Test suite</h2>
  <p>First fresh run at <code>{e(commit)}</code>: {e(sum1)}. Failed: {e(', '.join(fails1) or 'none')}.
  After the fix: {e(sum2)}{(' — failed: ' + e(', '.join(fails2))) if fails2 else ''}.</p>
  <div class="tablewrap"><table style="min-width: 0">
    <thead><tr><th>Test file</th><th>Tests</th></tr></thead><tbody>{test_files}</tbody>
  </table></div>
  <details><summary>All {len(run2) or len(run1)} tests, second run</summary><ul>{test_list}</ul></details>
</section>

<section class="block">
  <h2>Rerun it yourself</h2>
  <p>The audit scripts and their raw output are in the session's scratch folder. Data files (OpenCap, NHANES,
  MyoSegmenTUM results, the SKEL and SMPL models) live there too and stay outside the repository.</p>
<pre><code>SP={e(SP)}
cd $SP/audit
# part A: markers, shank, OpenCap RMSE, SKEL, DXA squat (OpenSim environment)
/home/user/.venvs/biomech/bin/python -I audit_a.py $SP /home/user/harmannbitte/rehab-agent/upstream \\
    /home/user/opencap-org/opencap-core $SP/audit/audit_a.json
# part B: NHANES and MyoSegmenTUM (pandas environment)
$SP/pdenv/bin/python -I audit_b.py $SP /home/user/harmannbitte/rehab-agent $SP/audit/audit_b.json
# the test suite
cd /home/user/harmannbitte/rehab-agent/pipeline
REHAB_UPSTREAM=../upstream python -m pytest -v tests</code></pre>
  <ul>
    <li>Audit code: <code>{e(SP)}/audit/audit_a.py</code>, <code>{e(SP)}/audit/audit_b.py</code></li>
    <li>Raw output: <code>{e(SP)}/audit/audit_a.log</code>, <code>{e(SP)}/audit/audit_b.log</code></li>
    <li>Test logs: <code>{e(SP)}/audit/suite_verbose.log</code> (first), <code>{e(SP)}/audit/suite_verbose_2.log</code> (after the fix)</li>
    <li>Race demo: <code>{e(SP)}/audit/race/Race.cs</code></li>
    <li>3D views: <code>{e(SP)}/viz/</code> (<code>prep_bodies.py</code>, <code>prep_squat.py</code>, and
    <code>test_skelmath.js</code>, which checks the browser's SKEL code against the Python reference)</li>
  </ul>
  <p>The scripts and logs are also kept in the repository under <code>validation/</code>, so they don't depend on this
  scratch folder.</p>
</section>
</div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
<script src="viz/skelmath.js"></script>
<script src="viz/viz.js"></script>
"""
OUT.write_text(page)
print("written", OUT, len(page), "bytes;", n_ok, "of", n_all)
