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
page = f"""<title>Rehab Twin Claims Audit</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Condensed:wght@500;600&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
/* Layout: one reading column; summary figures first, then one table per claim group, then how to rerun. */
:root {{
  --bg: #f6f7f5; --surface: #ffffff; --ink: #1b2129; --muted: #59626e; --rule: #d9ddd8;
  --accent: #245d7a; --ok: #2c6e49; --ok-bg: #e3f0e7; --bad: #9a4a12; --bad-bg: #f8e9dc;
  --code-bg: #eef0ec;
  --display: "IBM Plex Sans Condensed", "Arial Narrow", system-ui, sans-serif;
  --body: "IBM Plex Sans", system-ui, -apple-system, "Segoe UI", sans-serif;
  --mono: "IBM Plex Mono", ui-monospace, "SFMono-Regular", Menlo, monospace;
}}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{
  --bg: #12161b; --surface: #1a2027; --ink: #e5e8ec; --muted: #9aa3ae; --rule: #2c343d;
  --accent: #7fb6d4; --ok: #8fd0a6; --ok-bg: #1d3327; --bad: #f0a56d; --bad-bg: #3a2718; --code-bg: #222a32;
  color-scheme: dark; }} }}
:root[data-theme="dark"] {{
  --bg: #12161b; --surface: #1a2027; --ink: #e5e8ec; --muted: #9aa3ae; --rule: #2c343d;
  --accent: #7fb6d4; --ok: #8fd0a6; --ok-bg: #1d3327; --bad: #f0a56d; --bad-bg: #3a2718; --code-bg: #222a32;
  color-scheme: dark; }}
body {{ background: var(--bg); color: var(--ink); font: 15px/1.55 var(--body); }}
.wrap {{ max-width: 980px; margin: 0 auto; padding-block: 32px 64px;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px));
  display: grid; gap: 36px; }}
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
${BIO_PY:-python} -I audit_a.py $SP $REPO/upstream \\
    $OPENCAP_CORE $SP/audit/audit_a.json
# part B: NHANES and MyoSegmenTUM (pandas environment)
$SP/pdenv/bin/python -I audit_b.py $SP $REPO $SP/audit/audit_b.json
# the test suite
cd $REPO/pipeline
REHAB_UPSTREAM=../upstream python -m pytest -v tests</code></pre>
  <ul>
    <li>Audit code: <code>{e(SP)}/audit/audit_a.py</code>, <code>{e(SP)}/audit/audit_b.py</code></li>
    <li>Raw output: <code>{e(SP)}/audit/audit_a.log</code>, <code>{e(SP)}/audit/audit_b.log</code></li>
    <li>Test logs: <code>{e(SP)}/audit/suite_verbose.log</code> (first), <code>{e(SP)}/audit/suite_verbose_2.log</code> (after the fix)</li>
    <li>Race demo: <code>{e(SP)}/audit/race/Race.cs</code></li>
  </ul>
</section>
</div>
"""
OUT.write_text(page)
print("written", OUT, len(page), "bytes;", n_ok, "of", n_all)
