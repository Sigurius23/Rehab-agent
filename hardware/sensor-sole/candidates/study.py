#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors
# SPDX-License-Identifier: CERN-OHL-S-2.0
"""Compare three ways of sensing the same five-toe sole. Geometry and arithmetic only; nothing here is
fabricated, fitted or measured.

  baseline   the 16-region sole (kicad/, out/): one line per region, routed and checked
  T1         the targeted higher-resolution candidate (candidates/T1/out/): the same method, more regions
  matrix     a row/column matrix laid over the same outline: NOT routed. Counts are first-order estimates under
             the assumptions below, to show what a matrix would ask of the sole, the tail and the readout.

Matrix assumptions (stated, not verified with a fabricator or a prototype):
  - two-layer flex as for the baseline: rows on B.Cu, columns on F.Cu;
  - each cell is a shunt-mode comb pair on F.Cu under the film: one comb on its column, the other reaching its
    row through one via (no components on the sole, so no diode per cell);
  - square cells at pitch p, with cell side p - 1.2 mm (the baseline's region gap);
  - a cell is kept when at least half of it lies inside the copper-free margin (2 mm);
  - rows run across the foot and columns along it. Swapping the layers changes nothing below: whichever lines
    cross the foot are cut by the toe slits, so each toe's piece of a crossing line needs a line of its own back
    to the tail, or a link behind the slits.

Spatial measure. For each sensing element (a region or a cell): the RMS distance from its centroid of a point
load placed uniformly at random inside it (its radius of gyration). It is the localisation error left when all
that is known is which element is loaded. It ignores how evenly an element responds, and the gaps between
elements; it is a property of the geometry, not a measured accuracy.

Usage (the generator's Python):  python3 candidates/study.py   -> candidates/study.json and a summary
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
import sole_gen as G  # noqa: E402
from shapely.geometry import Point, Polygon, box  # noqa: E402

CONFIGS = {                       # name: (baseline stem, T1 stem, foot spec kwargs)
    "EU37": ("sole_EU37_R", "cand_T1_EU37_R", dict(size=37)),
    "EU42": ("sole_EU42_R", "cand_T1_EU42_R", dict(size=42)),
    "EU46": ("sole_EU46_R", "cand_T1_EU46_R", dict(size=46)),
    "synthetic foot": ("sole_person_example_R", "cand_T1_person_example_R", "person_example.json"),
}
PITCHES = (5.0, 7.5, 10.0)
ZONE = lambda n: ("heel" if n.startswith("heel") else "toes" if n.startswith("toe")
                  else "forefoot" if n.startswith(("mt", "ffp")) else "midfoot")


def spec_for(arg):
    if isinstance(arg, str):
        cfg = json.loads((ROOT / arg).read_text())
        return G.foot_spec(cfg.get("length"), cfg.get("width"), None, cfg.get("landmarks", {})), cfg.get("sensors")
    return G.foot_spec(None, None, arg["size"]), None


def r_gyration(poly, step=0.25):
    """RMS distance of a uniform point in the polygon from its centroid (mm), by sampling."""
    x0, y0, x1, y1 = poly.bounds
    xs, ys = np.meshgrid(np.arange(x0, x1, step) + step / 2, np.arange(y0, y1, step) + step / 2)
    from matplotlib.path import Path as MP
    pts = np.c_[xs.ravel(), ys.ravel()]
    m = MP(np.asarray(poly.exterior.coords)).contains_points(pts)
    for h in poly.interiors:
        m &= ~MP(np.asarray(h.coords)).contains_points(pts)
    p = pts[m]
    if len(p) == 0:
        return float("nan")
    c = p.mean(axis=0)
    return float(np.sqrt(((p - c) ** 2).sum(axis=1).mean()))


def toe_zones(s):
    """The toe tabs beyond their webs (+2 mm), where the pockets hold them; right foot."""
    sole, toes, centers, web_x = G.outline(s)
    own_web = [max(web_x[max(0, i - 1)], web_x[min(i, 3)]) for i in range(5)]
    return [t.intersection(box(own_web[i] + 2, -999, 999, 999)) if t is not None else None for i, t in enumerate(toes)]


def bend(sd):
    m1, m5 = np.asarray(sd["mt1"]), np.asarray(sd["mt5"])
    t = (m1 - m5) / np.linalg.norm(m1 - m5)
    nrm = np.array([t[1], -t[0]])
    nrm = -nrm if nrm[0] < 0 else nrm
    return m5 + nrm * 8.0, nrm


def matrix(s, p):
    """Cells of a row/column matrix on the sole of spec s at pitch p, and what wiring them would take."""
    sole, toes, centers, web_x = G.outline(s)
    s["_centers"] = centers
    inner = sole.buffer(-G.FAB["edge_margin"])
    own_web = [max(web_x[max(0, i - 1)], web_x[min(i, 3)]) for i in range(5)]
    toe_zone = [t.intersection(box(own_web[i] + 2, -999, 999, 999)) if t is not None else None
                for i, t in enumerate(toes)]
    base_regs, sd = G.regions(sole, toes, web_x, s, list(G.DEFAULT_SENSORS), "region")
    bp, nrm = bend(sd)
    c = p - G.FAB["region_gap"]
    x0, y0, x1, y1 = inner.bounds
    cells = []
    for i, x in enumerate(np.arange(x0 + p / 2, x1, p)):
        for j, y in enumerate(np.arange(y0 + p / 2, y1, p)):
            sq = box(x - c / 2, y - c / 2, x + c / 2, y + c / 2)
            a = sq.intersection(inner)
            if a.area < 0.5 * c * c:
                continue
            a = a if a.geom_type == "Polygon" else max(a.geoms, key=lambda g: g.area)
            toe = next((k for k, z in enumerate(toe_zone) if z is not None and z.contains(Point(x, y))), None)
            zone = "toes" if toe is not None else next((ZONE(n) for n, r in base_regs.items()
                                                        if r is not None and r.contains(Point(x, y))), "midfoot")
            cells.append(dict(i=i, j=j, x=x, y=y, poly=a, toe=toe, zone=zone,
                              in_band=abs(float(np.dot(np.array([x, y]) - bp, nrm))) < G.FAB["bend_band"]))
    across, along = "i", "j"                                   # lines at one x cross the foot; lines at one y run along it
    body = [q for q in cells if q["toe"] is None]
    crossing = len({q[across] for q in body}) + sum(len({q[across] for q in cells if q["toe"] == k}) for k in range(5))
    crossing_linked = len({q[across] for q in cells})            # toe pieces joined behind the slits instead
    lengthwise = len({q[along] for q in cells})
    lines = crossing + lengthwise
    # Reaching the tail (medial arch, as for the baseline). Crossing lines are reached at their medial end and run
    # along the medial edge to the tail; lengthwise lines at the heel end, around the heel. Toe pieces cannot run
    # down the tab on the crossing layer without crossing the body's lines there, so they leave on the other
    # layer between the lengthwise lines and change layer once to reach the edge: one extra via each.
    x_tail = 0.42 * s["L"]
    xs = {q[across]: q["x"] for q in cells}
    distal = sum(1 for k, x in xs.items() if x > x_tail and not any(q["toe"] is not None and q[across] == k for q in cells))
    distal += sum(len({q[across] for q in cells if q["toe"] == k}) for k in range(5))
    proximal = sum(1 for k, x in xs.items() if x <= x_tail) + lengthwise
    width = lambda n: round((n - 1) * G.FAB["pitch"] + 0.12 + G.FAB["route_clear"], 1) if n else 0.0
    toe_pieces = sum(len({q[across] for q in cells if q["toe"] == k}) for k in range(5))
    # copper in the tabs, first order: each lengthwise line from the web to its last cell; each crossing piece
    # across its tab plus its way back down the tab to the web
    tab_mm = 0.0
    for k in range(5):
        tc = [q for q in cells if q["toe"] == k]
        if not tc:
            continue
        w0 = own_web[k] + 2
        tab_mm += sum(max(q["x"] for q in tc if q[along] == a) + c / 2 - w0 for a in {q[along] for q in tc})
        z = toe_zone[k]
        tab_w = z.bounds[3] - z.bounds[1]
        tab_mm += sum(tab_w + (x - w0) for x in {q["x"] for q in tc})
    toe_cells = [sum(1 for q in cells if q["toe"] == k) for k in range(5)]
    toe_lengthwise = [len({q[along] for q in cells if q["toe"] == k}) for k in range(5)]
    return dict(
        pitch_mm=p, cell_side_mm=round(c, 2), cells=len(cells),
        cells_per_zone={z: sum(1 for q in cells if q["zone"] == z) for z in ("heel", "midfoot", "forefoot", "toes")},
        toe_cells=toe_cells, toe_lengthwise_lines=toe_lengthwise,
        lines_crossing=crossing, lines_crossing_if_toe_pieces_linked=crossing_linked, lines_lengthwise=lengthwise,
        lines_total=lines, contacts=lines, tail_width_mm=round(lines * G.FAB["ffc_pitch"] + 3.0, 1),
        vias=len(cells) + toe_pieces, vias_in_bend_band=sum(q["in_band"] for q in cells),
        row_column_crossings_in_bend_band=sum(q["in_band"] for q in cells),
        toe_piece_lines=toe_pieces,
        line_in_toe_tabs_mm=round(tab_mm), vias_in_toe_tabs=sum(1 for q in cells if q["toe"] is not None) + toe_pieces,
        edge_channel_at_tail_mm=dict(distal_side=width(distal), proximal_side=width(proximal)),
        cell_area_pct_of_sole=round(100 * sum(q["poly"].area for q in cells) / sole.area, 1),
        conversions_per_s_per_foot_at_100Hz=100 * len(cells),
        r_gyration_mm={z: round(float(np.median([r_gyration(q["poly"]) for q in cells if q["zone"] == z])), 1)
                       for z in ("heel", "midfoot", "forefoot", "toes") if any(q["zone"] == z for q in cells)},
        _cells=cells)


def direct(stem, folder, s=None):
    """A routed direct-wired sole (baseline or candidate) from its board and check files."""
    bj = folder / f"{stem}.board.json"
    js = folder / f"{stem}.json"
    if not bj.exists():
        return None
    d = json.loads(bj.read_text())
    regs = {n: Polygon(r["outline"]) for n, r in d["regions"].items()}
    sole_area = Polygon(d["outline"]).area
    chk = json.loads(js.read_text()).get("checks", {}) if js.exists() else {}
    tab_mm, tab_vias = None, None
    if s is not None and d["side"] == "R":            # board coordinates are the right foot's frame
        from shapely.geometry import LineString
        from shapely.ops import unary_union
        tabs = unary_union([z for z in toe_zones(dict(s)) if z is not None])
        R = d["copper_routing"]
        segs = list(R["lanes"].values()) + list(R["stubs"].values()) + list(R["com"])
        tab_mm = round(sum(LineString(v).intersection(tabs).length for v in segs if len(v) > 1))
        tab_vias = sum(1 for v in list(R["vias"].values()) + list(R["com_vias"]) if tabs.contains(Point(v)))
    zones = {}
    for n, r in regs.items():
        zones.setdefault(ZONE(n), []).append(r_gyration(r))
    return dict(
        board_id=d["board_id"], regions=len(regs),
        regions_per_zone={z: len(v) for z, v in zones.items()},
        contacts=d["config"]["n_contacts"], tail_width_mm=d["tail"]["width"],
        vias=(chk.get("routing") or {}).get("vias"), region_area_pct_of_sole=round(100 * sum(r.area for r in regs.values()) / sole_area, 1),
        conversions_per_s_per_foot_at_100Hz=100 * len(regs),
        r_gyration_mm={z: round(float(np.median(v)), 1) for z, v in zones.items()},
        least_sensing_area=chk.get("least_sensing_area"), vias_in_bend_zone=chk.get("vias_in_bend_zone"),
        line_in_toe_tabs_mm=tab_mm, vias_in_toe_tabs=tab_vias)


def figure(path, cfg="EU42", pitch=7.5):
    """Baseline, T1 and the matrix side by side on one outline (right foot)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    b_stem, t_stem, arg = CONFIGS[cfg]
    s, _ = spec_for(arg)
    fig, axes = plt.subplots(1, 3, figsize=(15, 5.2))
    panels = [("Baseline: 16 regions (routed, checked)", ROOT / "out" / f"{b_stem}.board.json"),
              ("T1: targeted (routed, checked)", HERE / "T1" / "out" / f"{t_stem}.board.json"),
              (f"Matrix at {pitch:g} mm: cells only (not routed)", None)]
    for ax, (title, bj) in zip(axes, panels):
        ax.set_aspect("equal"); ax.axis("off")
        if bj is not None:
            if not bj.exists():
                ax.set_title(title + " - missing", fontsize=9); continue
            d = json.loads(bj.read_text())
            ax.plot(*Polygon(d["outline"]).exterior.xy, color="#222", lw=0.6)
            for n, r in d["regions"].items():
                poly = Polygon(r["outline"])
                ax.fill(*poly.exterior.xy, fc="#9db8c7", ec="white", lw=0.6)
                c = poly.centroid
                ax.text(c.x, c.y, n, fontsize=4.5, ha="center", va="center")
            for v in d["copper_routing"]["lanes"].values():
                ax.plot(*zip(*v), color="#c2410c", lw=0.25)
            ax.set_title(f"{title}\n{d['board_id']}, {len(d['regions'])} regions, tail {d['tail']['width']:g} mm",
                         fontsize=9)
        else:
            m = matrix(dict(s), pitch)
            sole, *_ = G.outline(s)
            ax.plot(*sole.exterior.xy, color="#222", lw=0.6)
            for q in m["_cells"]:
                col = "#d97706" if q["in_band"] else ("#7c9a5b" if q["toe"] is not None else "#9db8c7")
                ax.fill(*q["poly"].exterior.xy, fc=col, ec="white", lw=0.3)
            ax.set_title(f"{title}\n{m['cells']} cells, {m['contacts']} lines, tail about {m['tail_width_mm']:g} mm; "
                         f"orange: via in the bend band; green: in a toe tab", fontsize=9)
    fig.suptitle(f"{cfg}, right foot. Design and analysis only: nothing fabricated, fitted or measured", fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main():
    res = {}
    for name, (b_stem, t_stem, arg) in CONFIGS.items():
        s, _ = spec_for(arg)
        row = dict(baseline=direct(b_stem, ROOT / "out", s), T1=direct(t_stem, HERE / "T1" / "out", s))
        for p in PITCHES:
            m = matrix(dict(s), p)
            m.pop("_cells")
            row[f"matrix_{p:g}mm"] = m
        res[name] = row
    (HERE / "study.json").write_text(json.dumps(res, indent=1) + "\n")
    figure(HERE / "compare_EU42.png")
    for name, row in res.items():
        print(f"== {name}")
        for k, v in row.items():
            if v is None:
                print(f"  {k}: not generated"); continue
            n = v.get("regions", v.get("cells"))
            print(f"  {k:28s} elements {n:4d}  contacts {v['contacts']:4d}  tail {v['tail_width_mm']:5.1f} mm  "
                  f"vias {v['vias']:4d}{'  in bend ' + str(v['vias_in_bend_band']) if 'vias_in_bend_band' in v else ''}"
                  f"  r_g {v['r_gyration_mm']}")


if __name__ == "__main__":
    main()
