# -*- coding: utf-8 -*-
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data import FEATURES, TOOLS, ORDERED_TOOLS, BANDS, DATA, score
from gen_part1 import (build_matrix, build_feature_detail, build_ranking, build_unknowns,
                       build_csv, build_pipeline, build_routes, SOURCES, OUT_DIR)
from assets import CSS, JS
import html as H

head2, body = build_matrix()

legend = """
<div class="legend">
  <span class="lg"><span class="sw" style="background:#e7f6ed;color:#1a7f4b;">&#10003;</span> Yes &mdash; documented capability</span>
  <span class="lg"><span class="sw" style="background:#fdf3e0;color:#a5701a;">&#9681;</span> Partial &mdash; indirect, manual, or a workaround</span>
  <span class="lg"><span class="sw" style="background:#fff;color:#b9bec6;">&#183;</span> No &mdash; not offered / not applicable</span>
  <span class="lg"><span class="sw" style="background:#f4eefb;color:#8b62b0;">?</span> Unverified &mdash; plausible, must be confirmed with the vendor</span>
</div>"""

src_list = "\n".join(f'<li><a href="{H.escape(u)}">{H.escape(n)}</a></li>' for n, u in SOURCES)

n_unver = sum(1 for t, *_ in TOOLS for f in FEATURES if DATA[t].get(f[0]) == "?")
n_cells = len(TOOLS) * (len(FEATURES) - 1)

best_core = max(ORDERED_TOOLS, key=lambda t: (score(t[0], "core")[0] / score(t[0], "core")[1]))
best_full = max(ORDERED_TOOLS, key=lambda t: (score(t[0], "full")[0] / score(t[0], "full")[1]))

HTML_DOC = f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Foot Mapping &amp; Last Creation &mdash; Capability Map</title>
<style>{CSS}</style>
</head><body><div class="wrap">

<div class="kick">Research note &middot; verified 2026-11-02</div>
<h1>From foot to printable last: a capability map of every tool</h1>
<p class="sub">Which features each package actually has, which tools they use to <b>map the foot</b>, and
which they use to <b>create the last</b>. {len(TOOLS)} tools &times; {len(FEATURES)-1} features = {n_cells} rated cells.
{n_unver} cells are flagged <b>?</b> because the source material does not confirm them &mdash; they are listed in the
verification checklist at the bottom rather than being guessed.</p>

<section class="blk">
  <h2>1 &middot; The pipeline, stage by stage</h2>
  <p class="hint">No single tool spans all six stages. Every realistic project stitches at least three of them together.</p>
  {build_pipeline()}
</section>

<section class="blk">
  <h2>2 &middot; Five ways to get from a foot to a last</h2>
  <p class="hint">The tools differ less in raw power than in which of these routes they implement. Pick the route first, the tool second.</p>
  {build_routes()}
</section>

<section class="blk">
  <h2>3 &middot; The full feature matrix</h2>
  <p class="hint">Scroll horizontally. Hover any cell for the reason behind the rating. Click <b>Last core</b> or
  <b>Shoe full</b> in the header to re-sort the tool columns by that score.</p>
  {legend}
  <div class="controls">
    <input id="q" type="search" placeholder="Filter features&hellip; e.g. girth, lattice, allowance, scan">
    <button id="coreOnly">Highlight the 15 last-critical features</button>
    <button id="reset">Reset</button>
    <span class="sp"></span>
    <span class="count" id="count"></span>
  </div>
  <div class="matrix-wrap">
    <table class="matrix" id="matrix">
      <thead>{head2}</thead>
      <tbody>{body}</tbody>
    </table>
  </div>
  <p class="hint" style="margin-top:12px">
  <b>Scoring.</b> <i>Last core</i> weights only the features that decide whether a tool can turn a foot into a printable last
  (scan import &times;3, last generation &times;3, allowances &times;3, parametric control &times;3, AM export &times;3, plus measurement,
  morphing, sculpting, clinical correction, deviation comparison and print checks).
  <i>Shoe full</i> adds pattern flattening, grading, upper design, sole/midsole and lattice work.
  Cells rated <b>?</b> are excluded from both numerator and denominator, so a score never claims credit for an unconfirmed feature.
  Best last-core: <b>{H.escape(best_core[1])}</b> &middot; best full-shoe: <b>{H.escape(best_full[1])}</b>.</p>
</section>

<section class="blk">
  <h2>4 &middot; Ranking</h2>
  <p class="hint">Click a score header to sort. <i>Rated</i> = weighted features that are actually confirmed out of the total weighted features;
  a low number means the score rests on thin evidence.</p>
  <table class="rank" id="rank">
    <thead><tr>
      <th>Tool</th><th>Class</th>
      <th data-sort="data-core" class="sortable">Last core &darr;</th>
      <th data-sort="data-full" class="sortable">Shoe full</th>
      <th>Rated</th>
    </tr></thead>
    <tbody>{build_ranking()}</tbody>
  </table>
</section>

<section class="blk">
  <h2>5 &middot; Feature by feature: who has it</h2>
  <p class="hint">The same data inverted &mdash; read this when you care about one capability and want every tool that offers it.</p>
  <div class="fd-grid">{build_feature_detail()}</div>
</section>

<section class="blk">
  <h2>6 &middot; Verification checklist</h2>
  <p class="hint">The {n_unver} cells marked <b>?</b>. These are the claims that need a vendor question, a trial licence, or a manual check
  before they can be relied on. Tick them as you confirm &mdash; state persists while the page is open.</p>
  <p class="count" id="chkCount">0 / {n_unver} verified</p>
  <table class="chk"><tbody>{build_unknowns()}</tbody></table>
</section>

<section class="blk">
  <h2>7 &middot; Reading the map: what actually decides fit</h2>
  <p class="hint">Six features carry almost all of the comfort outcome. Everything else is convenience.</p>
  <div class="fd-grid">
    <div class="fd"><div class="fd-h"><b>Allowances</b><span class="fd-g">make or break</span></div>
      <div class="fd-n">A foot is not a last. Toe allowance, fit allowance, sock thickness and heel-seat grip are the offsets that
      turn a scan into something wearable. Tools without them give you a plaster cast of your foot, which is unwearable.</div></div>
    <div class="fd"><div class="fd-h"><b>Weight-bearing state</b><span class="fd-g">systematically ignored</span></div>
      <div class="fd-n">A foot spreads roughly 4&ndash;10 mm in length and more in girth under load. A non-weight-bearing scan
      produces a tight shoe. Almost no tool in this map documents how it handles the difference &mdash; that is why so many
      cells read <b>?</b>.</div></div>
    <div class="fd"><div class="fd-h"><b>Deviation comparison</b><span class="fd-g">your only feedback loop</span></div>
      <div class="fd-n">A colour map of last-vs-foot tells you where the shoe will press. Without it you are iterating blind,
      printing and re-printing. Shoemaster, nTop, Materialise and CloudCompare all provide a version of this.</div></div>
    <div class="fd"><div class="fd-h"><b>Morphing vs rebuilding</b><span class="fd-g">the styling trap</span></div>
      <div class="fd-n">Deriving a last straight from a scan loses the toe shape, heel seat and lines of a real shoe.
      Morphing a proven base last toward the foot keeps the design and moves only the fit-critical zones.</div></div>
    <div class="fd"><div class="fd-h"><b>Parametric control</b><span class="fd-g">iterability</span></div>
      <div class="fd-n">Fit is found by iteration. If changing ball girth by 2 mm means re-sculpting the whole surface,
      you will stop iterating &mdash; and you will stop at a bad fit. History-based rebuild is what makes 20 attempts feasible.</div></div>
    <div class="fd"><div class="fd-h"><b>AM export</b><span class="fd-g">the quiet blocker</span></div>
      <div class="fd-n">Several professional footwear CAD packages export proprietary or NURBS-native data aimed at CNC and
      cutting, not at a slicer. Confirm STL/3MF/AMF in millimetres before buying. This is the most common dead end.</div></div>
  </div>
</section>

<section class="blk">
  <h2>8 &middot; Sources</h2>
  <ol class="src">{src_list}</ol>
</section>

<footer>Capability map generated from the 2026-11-02 research note &middot; data in <code>data.py</code>,
machine-readable copy in <code>feature-map.csv</code> &middot; ratings reflect published vendor material, not hands-on testing.</footer>

</div><script>{JS}</script></body></html>"""

# Write the map twice from the same string: the named deliverable and the
# preview root. Deriving index.html here (rather than `cp`-ing it by hand)
# guarantees the served preview can never go stale after a data.py edit.
for name in ("foot-to-last-capability-map.html", "index.html"):
    with open(os.path.join(OUT_DIR, name), "w", encoding="utf-8") as fh:
        fh.write(HTML_DOC)

csv_path = build_csv()
print("html bytes:", len(HTML_DOC))
print("csv:", csv_path)
print("tools:", len(TOOLS), "features:", len(FEATURES), "unverified cells:", n_unver)
for tid, name, cls, role in ORDERED_TOOLS:
    pc, mc = score(tid, "core"); pf, mf = score(tid, "full")
    print(f"  {name:42s} core {round(100*pc/mc):3d}%  full {round(100*pf/mf):3d}%")
