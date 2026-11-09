# -*- coding: utf-8 -*-
"""Generate the interactive capability map (single self-contained HTML) + CSV."""
import csv, html, os
from data import FEATURES, TOOLS, ORDERED_TOOLS, BANDS, DATA, NOTES, score

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
NCOL = len(TOOLS) + 2          # tool columns + 2 score columns

COL = {2: ("#1a7f4b", "#e7f6ed", "&#10003;", "yes"),
       1: ("#a5701a", "#fdf3e0", "&#9681;", "partial"),
       0: ("#b9bec6", "#ffffff", "&#183;", "no"),
       "?": ("#8b62b0", "#f4eefb", "?", "unverified")}

STAGES = [
    ("1", "Capture the foot", "Get geometry that represents the real, loaded foot",
     "#2f6f8f",
     [("Volumental", "Clinical 3D foot scanner"),
      ("RSscan / Footscan", "Pressure + morphology platform"),
      ("Avatar Feet", "Smartphone capture app"),
      ("Xesto Fit", "iPhone TrueDepth capture app"),
      ("FitStation (HP)", "Retail scan + gait"),
      ("Structured-light scanner", "Generic: Revscan, EinScan, Artec"),
      ("Photogrammetry / tape", "Fallback when no scanner is available")]),
    ("2", "Clean &amp; measure the mesh", "Turn a raw scan into a usable, dimensioned shape",
     "#3d7d5f",
     [("MeshLab", "Repair, decimate, fill holes, remesh"),
      ("CloudCompare", "Align, compute deviation maps"),
      ("Open3D", "Scriptable Python pipeline"),
      ("Netfabb", "Mesh repair + analysis"),
      ("Materialise 3-matic", "Repair, thicken, prepare for AM")]),
    ("3", "Derive the last", "Foot shape &rarr; wearable last: allowances, girths, corrections",
     "#8a5a2b",
     [("3DShoemaker", "Foot STL &rarr; parametric last (Rhino)"),
      ("Shoemaster", "Last library + scan adaptation + comparison"),
      ("ICad3D+ / IcadPAN", "Last preparation + anatomical insole"),
      ("Romans CAD", "Cloud last, upper, sole, grading"),
      ("PROTIQ Configurator", "Free web orthopaedic last"),
      ("Open Shoe Designer", "GPLv3 last + flattened pattern"),
      ("Crispin ShoeMaker", "Legacy footwear CAD/CAM"),
      ("Rhino + Grasshopper", "Scripted last from a mesh"),
      ("Fusion 360 / FreeCAD / OpenSCAD", "General parametric CAD")]),
    ("4", "Build sole, midsole, upper", "Everything that wraps or supports the last",
     "#6b4a86",
     [("nTop", "Lattice soles / midsoles"),
      ("Gensole", "Parametric insole, AMF export"),
      ("Materialise Phits", "Clinical insole / orthosis"),
      ("Blender", "Organic upper sculpting"),
      ("Shoemaster / Romans CAD / ICad3D+", "Patterns, grading, upper"),
      ("Grasshopper weaver scripts", "Knit / woven upper geometry")]),
    ("5", "Validate for printing", "Watertight, thick enough, oriented right, right units",
     "#a5383f",
     [("Netfabb", "Wall thickness, manifold, orientation"),
      ("Materialise 3-matic", "AM-oriented checks and fixes"),
      ("MeshLab", "Hole filling, manifold inspection"),
      ("nTop / Fusion 360", "Built-in lattice and mesh analysis")]),
    ("6", "Slice, print, fit-test", "TPU 85A&ndash;95A for wearable parts; iterate on one sole first",
     "#3f5d75",
     [("PrusaSlicer", "Slicer"),
      ("Ultimaker Cura", "Slicer"),
      ("Orca Slicer", "Slicer"),
      ("PROTIQ / Materialise", "Print + fulfilment service"),
      ("Shoefactory.ai / Fitasy", "Consumer scan-to-print services")]),
]

ROUTES = [
    ("A", "Direct scan &rarr; last",
     "Import the foot mesh, apply allowances, let the tool derive the last.",
     "3DShoemaker &middot; Shoemaster &middot; PROTIQ &middot; Materialise",
     "Fastest path to a genuinely custom shape. Demands a decent scan; a bad scan becomes a bad last with no warning.",
     "#1a7f4b"),
    ("B", "Base last &rarr; morph to the foot",
     "Start from a house last and deform it region by region toward the scan.",
     "Shoemaster &middot; 3DShoemaker (morph) &middot; Rhino/Grasshopper &middot; nTop",
     "Keeps the styling, toe shape and heel seat of a proven last; only fit-critical zones move. Best route for a wearable, good-looking shoe.",
     "#2f6f8f"),
    ("C", "Measurements &rarr; parametric last",
     "Length, ball girth, instep, heel width drive a parametric last model.",
     "Open Shoe Designer &middot; ICad3D+ &middot; Romans CAD &middot; Crispin &middot; OpenSCAD",
     "No scanner needed and fully reproducible, but you inherit the average shape behind the numbers. Weakest on unusual feet.",
     "#8a5a2b"),
    ("D", "Scan &rarr; surface / insole only",
     "Skip the last; build the interface layer that actually touches the foot.",
     "Gensole &middot; Materialise Phits &middot; IcadPAN &middot; nTop",
     "Highest comfort return per hour of work. Does not give you a shoe &mdash; you still need an upper and an outsole.",
     "#6b4a86"),
    ("E", "Scan &rarr; service prints it",
     "You supply the capture; the vendor owns the whole design pipeline.",
     "Shoefactory.ai &middot; Fitasy &middot; FitStation &middot; PROTIQ print service",
     "Zero CAD skill required. You get an artefact, not a model &mdash; no parametric control, no reusable last, limited styles.",
     "#a5383f"),
]


def cell_html(tool_id, key, val):
    note = NOTES.get((tool_id, key), "")
    if key == "cost":
        return f'<td class="cost"><span>{html.escape(val)}</span></td>'
    colour, bg, glyph, word = COL[val] if val in COL else COL["?"]
    tip = f' title="{html.escape(note, quote=True)}"' if note else ""
    return (f'<td class="c" style="background:{bg};" data-v="{1 if val == "?" else val}"{tip}>'
            f'<span class="g" style="color:{colour};">{glyph}</span></td>')


def bar(points, mx, colour):
    pct = round(100 * points / mx) if mx else 0
    return (f'<div class="bar"><div class="fill" style="width:{pct}%;background:{colour};"></div>'
            f'<span class="pct">{pct}%</span><span class="raw">{points}/{mx}</span></div>')


def coverage(tool_id):
    """How many weighted cells are actually verified (not '?')."""
    total = unknown = 0
    for f in FEATURES:
        key, wc, wf = f[0], f[4], f[5]
        if wc == 0 and wf == 0:
            continue
        total += 1
        if not isinstance(DATA[tool_id].get(key), int):
            unknown += 1
    return total, unknown


def build_matrix():
    # ---- header row 1: corner (rowspan 2) + tool bands + score band ----
    h1 = '<tr class="grp"><th class="sticky corner" rowspan="2">Feature</th>'
    for title, colour, ids in BANDS:
        h1 += (f'<th colspan="{len(ids)}" class="gt band" style="border-bottom:3px solid {colour};">'
               f'{title}<span class="bn">{len(ids)}</span></th>')
    h1 += '<th colspan="2" class="gt score-col">Composite score</th></tr>'

    # ---- header row 2: individual tools + the two sortable score headers ----
    h2 = '<tr>'
    for tid, name, cls, role in ORDERED_TOOLS:
        h2 += (f'<th class="tool" title="{html.escape(role, quote=True)}">'
               f'<span class="tn">{html.escape(name)}</span>'
               f'<span class="tc">{html.escape(cls)}</span></th>')
    h2 += ('<th class="sc sortable" data-kind="core" title="Last-creation pipeline only: click to sort">'
           'Last<br>core</th>'
           '<th class="sc sortable" data-kind="full" title="Whole-shoe pipeline: click to sort">'
           'Shoe<br>full</th></tr>')

    # ---- body: feature groups become full-width section rows ----
    body, cur = "", None
    for f in FEATURES:
        key, grp, label, note, wc, wf = f
        if grp != cur:
            cur = grp
            body += (f'<tr class="secrow"><th class="sec" colspan="{NCOL + 1}">{html.escape(grp)}</th></tr>')
        weights = " ".join(x for x in (f"core &times;{wc}" if wc else "",
                                       f"full &times;{wf}" if wf else "") if x)
        body += (f'<tr data-key="{key}"><th class="sticky feat" title="{html.escape(note, quote=True)}">'
                 f'{html.escape(label)}'
                 f'<span class="wt">{weights or "&mdash;"}</span></th>')
        for tid, *_ in ORDERED_TOOLS:
            body += cell_html(tid, key, DATA[tid].get(key))
        body += '<td class="score blank"></td>' * 2 + "</tr>"

    # per-tool score rows pinned at the bottom of the body
    for kind, label, colour, tip in (("core", "Last-creation score", "#8a5a2b",
                                      "Weighted on last-critical features only"),
                                     ("full", "Full-shoe score", "#6b4a86",
                                      "Weighted on the entire shoe pipeline")):
        body += (f'<tr class="scorerow" data-kind="{kind}">'
                 f'<th class="sticky feat" title="{tip}">{label}</th>')
        for tid, *_ in ORDERED_TOOLS:
            p, m = score(tid, kind)
            body += f'<td class="score" data-v="{round(100 * p / m) if m else 0}">{bar(p, m, colour)}</td>'
        body += '<td class="score"></td><td class="score"></td></tr>'
    return h1 + h2, body


def build_feature_detail():
    out = ""
    for f in FEATURES:
        key, grp, label, note = f[0], f[1], f[2], f[3]
        if key == "cost":
            continue
        yes, part, unk = [], [], []
        for tid, name, cls, role in ORDERED_TOOLS:
            v = DATA[tid].get(key)
            if v == 2:
                yes.append(name)
            elif v == 1:
                part.append(name)
            elif v == "?":
                unk.append(name)
        chips = lambda lst, kind: "".join(
            f'<span class="chip {kind}">{html.escape(n)}</span>' for n in lst)
        out += f'''<div class="fd">
  <div class="fd-h"><b>{html.escape(label)}</b><span class="fd-g">{html.escape(grp)}</span></div>
  <div class="fd-n">{html.escape(note)}</div>
  <div class="fd-r"><span class="lbl ok">Yes</span><div class="chips">{chips(yes,"ok") or '<span class="none">none</span>'}</div></div>
  <div class="fd-r"><span class="lbl pt">Partial</span><div class="chips">{chips(part,"pt") or '<span class="none">none</span>'}</div></div>
  {f'<div class="fd-r"><span class="lbl un">Unverified</span><div class="chips">{chips(unk,"un")}</div></div>' if unk else ""}
</div>'''
    return out


def build_ranking():
    rows = ""
    for tid, name, cls, role in ORDERED_TOOLS:
        pc, mc = score(tid, "core")
        pf, mf = score(tid, "full")
        t, u = coverage(tid)
        rows += f'''<tr data-core="{round(100*pc/mc) if mc else 0}" data-full="{round(100*pf/mf) if mf else 0}">
          <td class="rk-name"><b>{html.escape(name)}</b><span>{html.escape(role)}</span></td>
          <td class="rk-cls">{html.escape(cls)}</td>
          <td class="rk-bar">{bar(pc, mc, "#8a5a2b")}</td>
          <td class="rk-bar">{bar(pf, mf, "#6b4a86")}</td>
          <td class="rk-cov">{t-u}/{t}</td></tr>'''
    return rows


def build_unknowns():
    rows = ""
    for tid, name, cls, role in ORDERED_TOOLS:
        for f in FEATURES:
            key, label = f[0], f[2]
            if DATA[tid].get(key) == "?":
                rows += (f'<tr><td>{html.escape(name)}</td><td>{html.escape(label)}</td>'
                         f'<td><label><input type="checkbox"><span class="box"></span></label></td></tr>')
    return rows


def build_csv():
    p = os.path.join(OUT_DIR, "feature-map.csv")
    with open(p, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["feature_key", "group", "feature"] + [n for _, n, _, _ in ORDERED_TOOLS])
        for f in FEATURES:
            key, grp, label = f[0], f[1], f[2]
            w.writerow([key, grp, label] + [DATA[t].get(key, "") for t, *_ in ORDERED_TOOLS])
        w.writerow([])
        for kind in ("core", "full"):
            w.writerow([f"score_{kind}", "", f"Score ({kind})"] +
                       ["{}/{}".format(*score(t, kind)) for t, *_ in ORDERED_TOOLS])
    return p


def build_pipeline():
    out = '<div class="pipe">'
    for i, (num, title, sub, colour, tools) in enumerate(STAGES):
        out += f'''<section class="stage" style="--sc:{colour};">
  <header><span class="num">{num}</span><div><h3>{title}</h3><p>{sub}</p></div></header>
  <ul>{"".join(f'<li><b>{n}</b><span>{d}</span></li>' for n, d in tools)}</ul>
  {"" if i == len(STAGES) - 1 else '<div class="arrow">&rarr;</div>'}
</section>'''
    return out + "</div>"


def build_routes():
    out = '<div class="routes">'
    for tag, title, how, tools, verdict, colour in ROUTES:
        out += f'''<article class="route" style="--rc:{colour};">
  <div class="rt-h"><span class="rt-tag">{tag}</span><h4>{title}</h4></div>
  <p class="rt-how">{how}</p>
  <p class="rt-tools">{tools}</p>
  <p class="rt-v"><b>Verdict:</b> {verdict}</p>
</article>'''
    return out + "</div>"


SOURCES = [
 ("Shoemaster", "https://atom-shoemaster.com/en/"),
 ("Shoemaster custom/tailor-made production", "https://atom-shoemaster.com/en/p/custom-production/custom-tailor-made-production/"),
 ("ICad3D+", "https://icad3dtasarim.com/?lang=en"),
 ("Romans CAD", "https://www.romanscad.com/"),
 ("Sculpteo: shoe design software overview", "https://www.sculpteo.com/en/3d-learning-hub/3d-printing-software/shoe-design-software/"),
 ("Crispin ShoeMaker (Delcam hybrid shoes)", "https://3dprint.com/40233/delcam-crispin-hybrid-shoes/"),
 ("3DShoemaker: last & component design", "https://3dshoemaker.com/3dshoemaker-shoe-last-and-component-design-software/"),
 ("3DShoemaker: importing 3D foot models", "https://3dshoemaker.com/importing-3d-models-for-designing-bespoke-and-custom-shoe-lasts/"),
 ("PROTIQ Shoe Last Configurator", "https://www.protiq.com/en/about-the-shoe-last-configurator/"),
 ("Open Shoe Designer (GitHub)", "https://github.com/Vesuvan/openshoedesigner"),
 ("Open Shoe Designer (SourceForge)", "https://sourceforge.net/projects/openshoedesigner/"),
 ("Gensole", "http://gensole.com/"),
 ("Shoefactory.ai", "https://shoefactory.ai/"),
 ("Fitasy (VoxelMatters)", "https://www.voxelmatters.com/fitasy-advances-access-to-custom-fit-3d-printed-shoes/"),
 ("Materialise Phits / Footscan", "https://www.materialise.com/en/healthcare/phits-suite/footscan"),
 ("Materialise + HP FitStation", "https://investors.materialise.com/news-releases/news-release-details/materialise-and-hp-advance-design-and-creation-customized-3d"),
 ("nTop", "https://www.ntop.com/"),
 ("Materialise / nTop partnership", "https://www.materialise.com/en/news/press-releases/ntop-partnership-push-boundaries-additive-manufacturing"),
 ("Rhino 3D", "https://www.rhino3d.com/"),
 ("Fusion 360", "https://www.autodesk.com/products/fusion-360/overview"),
 ("FreeCAD", "https://www.freecad.org/"),
 ("OpenSCAD", "https://openscad.org/"),
 ("Blender", "https://www.blender.org/"),
 ("MeshLab", "https://www.meshlab.net/"),
 ("CloudCompare", "https://www.cloudcompare.org/"),
 ("Open3D", "https://open3d.org/"),
 ("PrusaSlicer", "https://www.prusa3d.com/page/prusaslicer_424/"),
 ("Ultimaker Cura", "https://ultimaker.com/software/ultimaker-cura"),
 ("Orca Slicer", "https://github.com/SoftFever/OrcaSlicer"),
]
