# -*- coding: utf-8 -*-
"""
Data model for the "foot mapping -> last creation" capability map.

Legend for every cell:
    2 = yes / verified in source material
    1 = partial, indirect, or manual workaround required
    0 = no / not applicable to this tool class
    ? = plausible but NOT verified in the source material (must be checked)

Feature groups and their weights are used for the two composite scores:
    core  -> "can this tool take a foot and give me a printable last?"
    full  -> "can this tool take a foot and give me a printable shoe?"
"""

FEATURES = [
    # (key, group, label, short note, core_weight, full_weight)
    ("scan_in",       "A. Foot-shape input",       "Imports 3D foot scan (STL/OBJ/PLY)",
        "The single most important gate: can the tool read a real captured foot?", 3, 3),
    ("scan2d_in",     "A. Foot-shape input",       "Imports 2D scan / photo / outline trace",
        "Plan view + length/girth tape measurements instead of a full mesh.", 1, 1),
    ("measure_in",    "A. Foot-shape input",       "Takes manual measurements as input",
        "Length, ball girth, instep, heel width typed in as numbers.", 2, 2),
    ("wb",            "A. Foot-shape input",       "Weight-bearing vs non-weight-bearing handling",
        "Foot spreads 4-10 mm under load; tools that ignore this produce tight lasts.", 1, 1),
    ("clean",         "B. Mesh handling",          "Built-in scan cleanup / repair",
        "Hole filling, noise removal, decimation, orientation.", 1, 1),
    ("meas_extract",  "B. Mesh handling",          "Automatic key-measurement extraction",
        "Derives length, girths, widths from the mesh rather than asking you.", 2, 2),
    ("gait",          "B. Mesh handling",          "Pressure / gait data input",
        "Plantar pressure maps or gait capture feeding the design.", 0, 1),

    ("last_gen",      "C. Last creation",          "Generates a last from foot geometry",
        "Foot -> last conversion, not just foot -> insole.", 3, 3),
    ("last_lib",      "C. Last creation",          "Last library / base-last reuse",
        "Start from a house last and adapt it, instead of rebuilding.", 2, 2),
    ("allowances",    "C. Last creation",          "Allowances: toe, fit, sock, heel seat",
        "The offsets that turn a bare foot into a wearable last.", 3, 3),
    ("param_last",    "C. Last creation",          "Parametric last control (length / girth / width / heel)",
        "Re-drive the last by changing numbers; history-based rebuild.", 3, 3),
    ("morph",         "C. Last creation",          "Morph / deform between base last and foot",
        "Blending a standard last toward a scanned foot, region by region.", 2, 2),
    ("sculpt",        "C. Last creation",          "Freeform sculpt / surface editing on the last",
        "Manual push-pull for bunions, hammertoes, high instep.", 2, 2),
    ("ortho_corr",    "C. Last creation",          "Clinical correction (leg axis, torsion, deformity)",
        "Orthopaedic adjustments: varus/valgus, tibial torsion, hallux valgus.", 1, 1),
    ("compare",       "C. Last creation",          "Side-by-side foot-vs-last deviation analysis",
        "Colour deviation map showing where last and foot disagree.", 2, 2),

    ("pattern",       "D. Upper / pattern",        "Pattern flattening (2D pieces from the last)",
        "Tape/spring-line flattening into cuttable 2D panels.", 0, 3),
    ("grading",       "D. Upper / pattern",        "Grading / size scaling",
        "Grade the last and patterns across a size run.", 0, 2),
    ("upper",         "D. Upper / pattern",        "Upper / shoe-volume design",
        "3D upper or shoe volume, not only the hard parts.", 0, 3),

    ("sole",          "E. Sole / midsole",         "Sole / midsole / footbed design",
        "Outsole, midsole, footbed geometry tied to the last.", 1, 3),
    ("lattice",       "E. Sole / midsole",         "Lattice / cellular structures",
        "TPMS, gyroid, variable-density lattices for cushioning and mass reduction.", 0, 2),
    ("insole",        "E. Sole / midsole",         "Anatomical insole generation",
        "Scan-driven contoured insole, variable density.", 1, 2),

    ("print_check",   "F. Print readiness",        "Wall-thickness / manifold / print checks",
        "Watertightness, minimum wall, self-intersection, orientation analysis.", 2, 2),
    ("export_am",     "F. Print readiness",        "Direct AM export (STL / 3MF / AMF)",
        "Exports a format a slicer or printer can consume, in millimetres.", 3, 3),
    ("print_service", "F. Print readiness",        "Print / fulfilment service attached",
        "The vendor prints and ships the result for you.", 0, 1),

    ("cloud",         "G. Access & licence",       "Cloud / web based",
        "Runs in a browser; no Windows workstation or licence server needed.", 0, 0),
    ("oss",           "G. Access & licence",       "Open source",
        "Source available; scriptable and free of licence lock-in.", 0, 0),
    ("cost",          "G. Access & licence",       "Entry cost (indicative)",
        "Free / low / commercial quote / legacy. Free-text, not scored.", 0, 0),
]

# tool id, name, class, one-line role
TOOLS = [
    # --- Band 1: footwear-specific last & shoe CAD ---
    ("3dshoemaker",  "3DShoemaker",            "Footwear-specific",  "Rhino plug-in: foot mesh -> parametric last, footbed, shoe volume"),
    ("shoemaster",   "Shoemaster",             "Footwear CAD/CAM",   "Professional last library, scan import, pattern adaptation, grading"),
    ("icad3d",       "ICad3D+ / IcadPAN",      "Footwear CAD",       "Last preparation, 3D footwear design, 3D anatomical insole"),
    ("romanscad",    "Romans CAD",             "Footwear CAD",       "Cloud footwear design: last, upper, sole, grading, prototyping"),
    ("crispin",      "Crispin ShoeMaker",      "Footwear CAD/CAM",   "Legacy Delcam/Autodesk hybrid 3D-printed shoe workflow"),
    ("protiq",       "PROTIQ Last Configurator","Last configurator",  "Free web orthopaedic last from a 2D/3D scan, printed on demand"),
    ("openshoe",     "Open Shoe Designer",     "Open-source footwear","GPLv3 manufacturing-first design: last, sole, flattened pattern"),
    # --- Band 2: insole / orthotics specialists ---
    ("gensole",      "Gensole",                "Insole generator",   "Free web parametric insole from a scan, AMF export"),
    ("materialise",  "Materialise (3-matic / Phits / Footscan)", "Orthotics suite",
                                                                     "Clinical scan -> custom insole/orthosis, 3D-printed"),
    ("fitstation",   "FitStation powered by HP","Scan-to-print service", "HP/Materialise scan + gait -> custom insole/footwear"),
    # --- Band 3: general & parametric CAD ---
    ("rhino_gh",     "Rhino + Grasshopper",    "General CAD",        "Parametric/implicit definition built by you around a foot mesh"),
    ("ntop",         "nTop",                    "Implicit modeling",  "Scan-driven lattice soles and midsoles, field-driven design"),
    ("fusion360",    "Fusion 360",             "General CAD",        "Parametric solids plus mesh workspace; soles, lasts, prototypes"),
    ("freecad",      "FreeCAD",                "Open-source CAD",    "Parametric solid/mesh CAD; lasts and components"),
    ("openscad",     "OpenSCAD",               "Open-source CAD",    "Code-driven parametric geometry; no scan import"),
    ("blender",      "Blender",                "Open-source 3D",     "Organic sculpt of uppers and soft geometry from a scan"),
    # --- Band 4: consumer scan-to-print services ---
    ("shoefactory",  "Shoefactory.ai",         "Consumer service",   "Volumental-scan-to-print custom shoe service"),
    ("fitasy",       "Fitasy",                 "Consumer service",   "Smartphone-scan-to-print custom shoe service"),
    # --- Band 5: utilities, no design capability ---
    ("meshtools",    "MeshLab / CloudCompare / Open3D", "Mesh processing", "Scan cleanup, repair, alignment, deviation analysis"),
    ("slicers",      "PrusaSlicer / Cura / Orca Slicer", "Slicer",   "Print preparation; TPU profiles for wearable parts"),
]

# Column bands for the matrix header: (band title, colour, [tool ids in display order])
BANDS = [
    ("Footwear-specific CAD &amp; last tools", "#8a5a2b",
     ["3dshoemaker", "shoemaster", "icad3d", "romanscad", "crispin", "protiq", "openshoe"]),
    ("Insole &amp; orthotics specialists", "#6b4a86",
     ["gensole", "materialise", "fitstation"]),
    ("General &amp; parametric CAD", "#2f6f8f",
     ["rhino_gh", "ntop", "fusion360", "freecad", "openscad", "blender"]),
    ("Consumer scan-to-print services", "#a5383f",
     ["shoefactory", "fitasy"]),
    ("Utilities (no design)", "#5c6169",
     ["meshtools", "slicers"]),
]

# Display order of tools, flattened from the bands.
ORDER = [tid for _, _, ids in BANDS for tid in ids]
BY_ID = {t[0]: t for t in TOOLS}
ORDERED_TOOLS = [BY_ID[tid] for tid in ORDER]
assert len(ORDERED_TOOLS) == len(TOOLS), "every tool must appear in exactly one band"


# Cell values keyed by feature key. "cost" and some cells carry free text.
DATA = {
"3dshoemaker": dict(
    scan_in=2, scan2d_in=1, measure_in=2, wb="?", clean=1, meas_extract=1, gait=0,
    last_gen=2, last_lib=2, allowances=2, param_last=2, morph=2, sculpt=2, ortho_corr=1, compare=1,
    pattern=0, grading=0, upper=1, sole=2, lattice=1, insole=2,
    print_check=1, export_am=2, print_service=0, cloud=0, oss=0,
    cost="Commercial: $99 personal / $349 business, + Rhino licence; Windows only"),

"shoemaster": dict(
    scan_in=2, scan2d_in=2, measure_in=2, wb="?", clean=1, meas_extract=2, gait=0,
    last_gen=2, last_lib=2, allowances=2, param_last=2, morph=2, sculpt=2, ortho_corr=1, compare=2,
    pattern=2, grading=2, upper=2, sole=2, lattice=1, insole=1,
    print_check="?", export_am=1, print_service=0, cloud=0, oss=0,
    cost="Commercial, on quote; professional seat + training"),

"icad3d": dict(
    scan_in=2, scan2d_in=2, measure_in=2, wb="?", clean=1, meas_extract=1, gait=0,
    last_gen=2, last_lib=2, allowances=2, param_last=2, morph=1, sculpt=1, ortho_corr=1, compare=1,
    pattern=2, grading=1, upper=2, sole=2, lattice=0, insole=2,
    print_check="?", export_am=1, print_service=0, cloud=0, oss=0,
    cost="Commercial; basic package from ~$30, full on quote"),

"romanscad": dict(
    scan_in=1, scan2d_in=1, measure_in=2, wb="?", clean=0, meas_extract=1, gait=0,
    last_gen=2, last_lib=2, allowances=2, param_last=2, morph=1, sculpt=1, ortho_corr=0, compare=1,
    pattern=2, grading=2, upper=2, sole=2, lattice=0, insole=1,
    print_check="?", export_am="?", print_service=0, cloud=2, oss=0,
    cost="Commercial, on quote; cloud subscription"),

"crispin": dict(
    scan_in="?", scan2d_in=1, measure_in=2, wb=0, clean=0, meas_extract=1, gait=0,
    last_gen=2, last_lib=2, allowances=2, param_last=2, morph=1, sculpt=1, ortho_corr=0, compare=1,
    pattern=2, grading=2, upper=2, sole=2, lattice=0, insole=1,
    print_check="?", export_am="?", print_service=0, cloud=0, oss=0,
    cost="Legacy commercial; availability unclear after Autodesk/Delcam changes"),

"protiq": dict(
    scan_in=2, scan2d_in=2, measure_in=2, wb="?", clean=0, meas_extract=2, gait=0,
    last_gen=2, last_lib=1, allowances=2, param_last=2, morph=1, sculpt=0, ortho_corr=2, compare=1,
    pattern=0, grading=0, upper=0, sole=0, lattice=1, insole=1,
    print_check=2, export_am=1, print_service=2, cloud=2, oss=0,
    cost="Free web configurator; you pay for the printed last"),

"openshoe": dict(
    scan_in=1, scan2d_in=1, measure_in=2, wb=0, clean=0, meas_extract=0, gait=0,
    last_gen=2, last_lib=1, allowances=2, param_last=2, morph=0, sculpt=0, ortho_corr=0, compare=0,
    pattern=2, grading=0, upper=0, sole=2, lattice=0, insole=1,
    print_check=0, export_am=1, print_service=0, cloud=0, oss=2,
    cost="Free, GPLv3; early-stage C++/wxWidgets"),

"gensole": dict(
    scan_in=2, scan2d_in=1, measure_in=1, wb=1, clean=0, meas_extract=1, gait=0,
    last_gen=0, last_lib=0, allowances=1, param_last=1, morph=0, sculpt=0, ortho_corr=1, compare=0,
    pattern=0, grading=0, upper=0, sole=2, lattice=2, insole=2,
    print_check=1, export_am=2, print_service=0, cloud=2, oss=0,
    cost="Free for non-commercial makers/researchers; AMF export"),

"shoefactory": dict(
    scan_in=2, scan2d_in=0, measure_in=0, wb=1, clean=0, meas_extract=2, gait="?",
    last_gen=2, last_lib=1, allowances=2, param_last="?", morph="?", sculpt=0, ortho_corr=0, compare=0,
    pattern="?", grading=0, upper=2, sole=2, lattice=2, insole=2,
    print_check=2, export_am=1, print_service=2, cloud=2, oss=0,
    cost="Commercial service; price per pair, limited styles"),

"fitasy": dict(
    scan_in=2, scan2d_in=0, measure_in=0, wb=1, clean=0, meas_extract=1, gait="?",
    last_gen=2, last_lib=1, allowances=2, param_last="?", morph="?", sculpt=0, ortho_corr=0, compare=0,
    pattern="?", grading=0, upper=2, sole=2, lattice=1, insole=2,
    print_check=2, export_am=1, print_service=2, cloud=2, oss=0,
    cost="Commercial service; smartphone scan, patent-pending"),

"rhino_gh": dict(
    scan_in=2, scan2d_in=1, measure_in=2, wb=1, clean=1, meas_extract=1, gait=0,
    last_gen=2, last_lib=1, allowances=2, param_last=2, morph=2, sculpt=2, ortho_corr=1, compare=1,
    pattern=1, grading=1, upper=2, sole=2, lattice=2, insole=2,
    print_check=1, export_am=2, print_service=0, cloud=0, oss=0,
    cost="Commercial Rhino licence; Grasshopper included; high skill requirement"),

"ntop": dict(
    scan_in=2, scan2d_in=0, measure_in=1, wb=1, clean=2, meas_extract=0, gait=1,
    last_gen=1, last_lib=0, allowances=1, param_last=2, morph=2, sculpt=1, ortho_corr=1, compare=2,
    pattern=0, grading=0, upper=1, sole=2, lattice=2, insole=2,
    print_check=2, export_am=2, print_service=0, cloud=0, oss=0,
    cost="Commercial, on quote; steep learning curve"),

"fusion360": dict(
    scan_in=1, scan2d_in=1, measure_in=2, wb=0, clean=1, meas_extract=0, gait=0,
    last_gen=1, last_lib=0, allowances=1, param_last=2, morph=1, sculpt=1, ortho_corr=0, compare=1,
    pattern=0, grading=1, upper=1, sole=2, lattice=1, insole=1,
    print_check=2, export_am=2, print_service=0, cloud=1, oss=0,
    cost="Free personal tier / commercial subscription"),

"freecad": dict(
    scan_in=1, scan2d_in=1, measure_in=2, wb=0, clean=1, meas_extract=0, gait=0,
    last_gen=1, last_lib=0, allowances=1, param_last=2, morph=1, sculpt=1, ortho_corr=0, compare=1,
    pattern=0, grading=1, upper=1, sole=2, lattice=1, insole=1,
    print_check=1, export_am=2, print_service=0, cloud=0, oss=2,
    cost="Free, open source"),

"openscad": dict(
    scan_in=0, scan2d_in=0, measure_in=2, wb=0, clean=0, meas_extract=0, gait=0,
    last_gen=1, last_lib=0, allowances=2, param_last=2, morph=0, sculpt=0, ortho_corr=0, compare=0,
    pattern=0, grading=1, upper=0, sole=2, lattice=1, insole=1,
    print_check=1, export_am=2, print_service=0, cloud=0, oss=2,
    cost="Free, open source; code-only, no scan import"),

"blender": dict(
    scan_in=2, scan2d_in=1, measure_in=1, wb=0, clean=2, meas_extract=0, gait=0,
    last_gen=1, last_lib=0, allowances=1, param_last=1, morph=2, sculpt=2, ortho_corr=0, compare=1,
    pattern=0, grading=0, upper=2, sole=2, lattice=1, insole=1,
    print_check=1, export_am=2, print_service=0, cloud=0, oss=2,
    cost="Free, open source; not parametric"),

"materialise": dict(
    scan_in=2, scan2d_in=2, measure_in=1, wb=2, clean=2, meas_extract=2, gait=2,
    last_gen=1, last_lib=0, allowances=2, param_last=2, morph=2, sculpt=2, ortho_corr=2, compare=2,
    pattern=0, grading=0, upper=0, sole=2, lattice=2, insole=2,
    print_check=2, export_am=2, print_service=2, cloud=1, oss=0,
    cost="Commercial, on quote; healthcare/orthotics pricing"),

"fitstation": dict(
    scan_in=2, scan2d_in=1, measure_in=1, wb=1, clean=1, meas_extract=2, gait=2,
    last_gen=1, last_lib=1, allowances=2, param_last=1, morph=1, sculpt=0, ortho_corr=1, compare=1,
    pattern=0, grading=0, upper=1, sole=2, lattice=1, insole=2,
    print_check=2, export_am=1, print_service=2, cloud=1, oss=0,
    cost="Commercial service (HP / Materialise); retail deployment"),

"meshtools": dict(
    scan_in=2, scan2d_in=2, measure_in=0, wb=1, clean=2, meas_extract=1, gait=0,
    last_gen=0, last_lib=0, allowances=0, param_last=0, morph=1, sculpt=1, ortho_corr=0, compare=2,
    pattern=0, grading=0, upper=0, sole=0, lattice=0, insole=0,
    print_check=2, export_am=2, print_service=0, cloud=0, oss=2,
    cost="Free, open source; processing only, no design"),

"slicers": dict(
    scan_in=1, scan2d_in=0, measure_in=0, wb=0, clean=1, meas_extract=0, gait=0,
    last_gen=0, last_lib=0, allowances=0, param_last=0, morph=0, sculpt=0, ortho_corr=0, compare=0,
    pattern=0, grading=0, upper=0, sole=0, lattice=1, insole=0,
    print_check=2, export_am=2, print_service=0, cloud=0, oss=2,
    cost="Free, open source; print preparation only"),
}

# Notes attached to specific cells -> shown as tooltips.
NOTES = {
 ("3dshoemaker","scan_in"): "Imports an STL foot model and applies allowances to derive the last.",
 ("3dshoemaker","morph"):   "Morphing between base last and custom geometry.",
 ("3dshoemaker","sculpt"):  "Freeform sculpting for challenging feet (bunions, high instep).",
 ("3dshoemaker","pattern"): "Upper/pattern design is manual; this is a last & component tool.",
 ("3dshoemaker","cloud"):   "Windows only, runs as a Rhino plug-in.",
 ("shoemaster","compare"):  "Side-by-side last/foot comparison with key-measurement editing.",
 ("shoemaster","pattern"):  "Automatic pattern adaptation to a custom last.",
 ("shoemaster","export_am"):"Exports 3D data; confirm the exact AM format you need (STL vs 3MF).",
 ("icad3d","insole"):       "3D anatomical insole design is a headline feature (IcadPAN).",
 ("icad3d","export_am"):    "Advertises 3D print; verify STL/3MF export in your package tier.",
 ("romanscad","export_am"): "Marketed for rapid prototyping rather than print-first output.",
 ("crispin","scan_in"):     "Source material documents last measurements, not scan import.",
 ("protiq","ortho_corr"):   "Adjustments for leg axis, twists and deformations.",
 ("protiq","print_service"):"Configurator is free; PROTIQ prints and ships the last.",
 ("protiq","export_am"):    "Output is a printed last; check whether a raw STL download is offered.",
 ("openshoe","pattern"):    "Generates last, sole and a flattened pattern.",
 ("openshoe","upper"):      "Upper design not yet implemented.",
 ("openshoe","scan_in"):    "Imports STL lasts; foot-scan-driven last creation is limited.",
 ("gensole","export_am"):   "Exports AMF for 3D printing.",
 ("gensole","lattice"):     "'Solemorph' surface with variable density.",
 ("gensole","last_gen"):    "Insoles only - it does not produce a last.",
 ("shoefactory","scan_in"): "Uses Volumental 3D scanning.",
 ("fitasy","scan_in"):      "Smartphone-based capture.",
 ("rhino_gh","param_last"): "Everything is yours to build: high ceiling, high effort.",
 ("rhino_gh","pattern"):    "Flattening must be scripted (developable-surface plugins help).",
 ("ntop","lattice"):        "Implicit/field-driven lattices; strongest tool in this column.",
 ("ntop","compare"):        "Deviation and thickness analysis built in.",
 ("fusion360","scan_in"):   "Mesh workspace imports scans but is not a scan-to-last pipeline.",
 ("openscad","scan_in"):    "No foot-scan import; drive geometry from numbers only.",
 ("blender","param_last"):  "Not parametric - sculpt-driven, no history rebuild.",
 ("materialise","wb"):      "Clinical capture; weight-bearing context is part of the workflow.",
 ("materialise","gait"):    "Footscan pressure/gait platform feeds Phits insole design.",
 ("fitstation","gait"):     "3D scan plus gait data.",
 ("meshtools","compare"):   "CloudCompare computes point-to-mesh deviation maps.",
 ("meshtools","print_check"):"MeshLab: hole filling, manifold checks, decimation, remeshing.",
 ("slicers","print_check"): "Watertight/manifold repair hints, supports, TPU profiles.",
 ("3dshoemaker","wb"):      "Not documented in source material - verify with vendor.",
 ("shoemaster","wb"):       "Not documented in source material - verify with vendor.",
}

# Free-text cost cells are excluded from scoring automatically (non-int).

def score(tool_id, kind):
    """Return (points, max_points) for a tool under 'core' or 'full' weighting."""
    idx = 4 if kind == "core" else 5
    pts = mx = 0
    row = DATA[tool_id]
    for f in FEATURES:
        key, w = f[0], f[idx]
        if w == 0:
            continue
        v = row.get(key)
        if not isinstance(v, int):
            continue           # '?' and free text do not count toward either side
        mx += w * 2
        pts += w * v
    return pts, mx
