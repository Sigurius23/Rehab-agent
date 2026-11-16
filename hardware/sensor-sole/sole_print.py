#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors
# SPDX-License-Identifier: CERN-OHL-S-2.0
"""The printed prototype of the sensor sole, matching the flex sole's sensing (owner's decision, 2026-11-17).

From the same generator output as the flex board (outline with toe tabs and tail, sensing regions, routing plan),
this script writes everything the prototype is made of. The stack is the flex sole's, layer for layer:

  carrier.stl     printed TPU: wire channels on the underside along the routing plan, and a closed floor with one
                  hole per sense wire and one for the common wire. Its top is flat.
  electrodes.dxf  cut from copper foil and laid on the carrier (layers SENSE, COMMON, HOLES, OUTLINE):
                    - per region, two interleaved combs (shunt mode, as on the flex board), fingers parallel to the
                      toe-joint bend line;
                    - each sense comb is an island; its wire comes up through its hole (the flex board's via);
                    - all common combs are one piece with a web that runs under the spacer's walls to the tail
                      root (the flex board's common net), with one wire.
  spacer.dxf      cut from double-sided adhesive film: a frame with one window per region (the region inset).
  film.dxf        one pressure-sensitive film patch per window, fixed under the cover.
  cover.stl       a thin printed TPU skin with the same outline.

Also, beyond the flex design as it stands:
  - a reference cell "ref" on the tail, outside the loaded sole: the same combs and film, never pressed, read on
    its own wire, for temperature and humidity drift;
  - venting: each window opens through its wire hole into the underside channels, which run to the tail's end, so
    no cell is sealed. The holes must not be potted. The report checks the path for every cell.

Comb fingers and gaps are 0.6 mm by default, which a desktop cutter can make; the flex board's are 0.2 mm. The
principle, regions, film and readout are the same. Nothing has been printed, cut, bought or measured.

Usage (the generator's Python plus manifold3d and ezdxf):
  python sole_print.py out/sole_EU42_R.board.json -o print/
Options: --channel 0.5 --floor 0.5 --inset 0.6 --cover 0.4 --wire 0.35 --finger 0.6 --gap 0.6 --bed 256x256 (mm)
Walls narrower than 0.8 mm (two 0.4 mm nozzle widths) are removed on purpose in each printed layer and reported.
"""
import argparse
import json
import math
import struct
from pathlib import Path

import numpy as np
from shapely import affinity
from shapely.geometry import LineString, MultiPolygon, Point, Polygon, box
from shapely.ops import nearest_points, unary_union


def stl(mesh, path, name):
    """Binary STL from a manifold3d mesh."""
    v = np.asarray(mesh.vert_properties)[:, :3]
    t = np.asarray(mesh.tri_verts)
    with open(path, "wb") as f:
        f.write(name.encode()[:80].ljust(80, b" "))
        f.write(struct.pack("<I", len(t)))
        for a, b, c in t:
            p, q, r = v[a], v[b], v[c]
            n = np.cross(q - p, r - p); ln = np.linalg.norm(n)
            n = n / ln if ln else n
            f.write(struct.pack("<12fH", *n, *p, *q, *r, 0))


def solid(poly, z0, h):
    """A shapely polygon (or multipolygon) extruded from z0 to z0 + h, as a manifold."""
    import manifold3d as M
    poly = poly.simplify(0.02, preserve_topology=True)        # 20 um: far below what a 0.4 mm nozzle resolves
    parts = poly.geoms if isinstance(poly, MultiPolygon) else [poly]
    loops = []
    for g in parts:
        loops.append(np.asarray(g.exterior.coords)[:-1])
        loops += [np.asarray(h_.coords)[:-1] for h_ in g.interiors]
    cs = M.CrossSection(loops, M.FillRule.EvenOdd)
    return M.Manifold.extrude(cs, h).translate((0, 0, z0))


def channels(d, wire, clearance, extra=0):
    """Wire channels along the routing plan: each region's path to the tail, widened by the wires sharing it,
    then down the tail to its end. Returns (channel polygon, the most wires in one channel)."""
    plan = {n: [tuple(p) for p in pts] for n, pts in d["routing_plan"].items()}
    lines = {n: LineString(p) for n, p in plan.items() if len(p) > 1}
    samples = []
    for n, ln in lines.items():
        for s in np.arange(0, ln.length + 1e-9, 0.5):
            samples.append((n, ln.interpolate(s)))
    disks, worst = [], 1
    for n, p in samples:
        load = sum(1 for m, ln in lines.items() if ln.distance(p) < 0.6) + 1     # + the common wire
        worst = max(worst, load)
        disks.append(p.buffer(load * wire / 2 + clearance, 8))
    tail_end, tail_dir = np.asarray(d["tail"]["end"]), np.asarray(d["tail"]["dir"])
    roots = [ln.coords[-1] for ln in lines.values()]
    root = np.mean(np.asarray(roots), axis=0)
    n_all = len(lines) + 1 + extra
    trunk = LineString([tuple(root), tuple(tail_end - tail_dir * 3.0)]).buffer(n_all * wire / 2 + clearance, 8)
    return unary_union(disks + [trunk]), max(worst, n_all)


def bed_fit(outline, bed):
    """The rotation that best fits the outline on a bed (w, h) in mm, and whether it fits."""
    best = None
    for a in range(0, 180):
        g = affinity.rotate(outline, a, origin="centroid")
        x0, y0, x1, y1 = g.bounds
        w, h = x1 - x0, y1 - y0
        fits = (w <= bed[0] and h <= bed[1]) or (h <= bed[0] and w <= bed[1])
        key = (not fits, max(w, h))
        if best is None or key < best[0]:
            best = (key, a, round(w, 1), round(h, 1), fits)
    return dict(rotation_deg=best[1], size_mm=[best[2], best[3]], fits=best[4], bed_mm=list(bed))


def printable(poly, wall=0.8):
    """The polygon without parts narrower than `wall` (they do not print as walls); and the area removed."""
    kept = poly.buffer(-wall / 2, 8).buffer(wall / 2, 8).intersection(poly)
    return kept, poly.difference(kept).area


def polys(g):
    """The polygons of a geometry, largest first."""
    ps = [q for q in (g.geoms if hasattr(g, "geoms") else [g]) if isinstance(q, Polygon) and not q.is_empty]
    return sorted(ps, key=lambda q: -q.area)


def combs(window, bend_dir, toward, finger, gap, spine, edge=0.3):
    """Two interleaved combs filling a window, fingers parallel to the bend line.

    The window is turned so the bend line lies along x. Each comb has a spine along one side of the window and
    fingers reaching towards the other; the sense comb takes the side nearest ``toward`` (the region's via).
    Returns (sense, common, sense side as +1 or -1 in the turned frame's x) in the board's frame.
    """
    ang = math.degrees(math.atan2(bend_dir[1], bend_dir[0]))
    c = window.centroid
    w = affinity.rotate(window, -ang, origin=c)
    t = affinity.rotate(Point(toward), -ang, origin=c)
    inner = w.buffer(-edge, 8)
    inner = polys(inner)[0]
    x0, y0, x1, y1 = inner.bounds
    # the two spines: the boundary split at its lowest and highest points (across the fingers), so every finger
    # stripe runs from one spine to the other, also in slanted corners
    pts = list(inner.exterior.coords)[:-1]
    lo = min(range(len(pts)), key=lambda i: pts[i][1]); hi = max(range(len(pts)), key=lambda i: pts[i][1])
    i, j = sorted((lo, hi))
    chains = [pts[i:j + 1], pts[j:] + pts[:i + 1]]
    strips = [LineString(c).buffer(spine, 8).intersection(inner) for c in chains]
    strips = [polys(g)[0] for g in strips]
    order = sorted(range(2), key=lambda k: np.mean([q[0] for q in chains[k]]))
    left, right = strips[order[0]], strips[order[1]]
    side = 1.0 if t.x >= inner.centroid.x else -1.0
    band = {-1: left, +1: right}
    band[-side] = polys(band[-side].difference(band[side].buffer(gap, 8)))[0]      # the sense spine keeps the joints
    pitch = finger + gap
    out = {+1: [band[+1]], -1: [band[-1]]}
    k, y = 0, y0 + spine + gap
    while y + finger <= y1 - spine - gap + 1e-9:
        own = side if k % 2 == 0 else -side
        stripe = box(x0, y, x1, y + finger).intersection(inner)
        f = stripe.difference(band[-own].buffer(gap, 8))
        out[own] += [q for q in polys(f) if q.distance(band[own]) < 1e-6 or q.intersects(band[own])]
        k += 1; y += pitch
    sense = unary_union(out[side]); common = unary_union(out[-side]).difference(sense.buffer(gap, 8))
    sense, common = polys(sense)[0], polys(common)[0]
    back = lambda g: affinity.rotate(g, ang, origin=c)
    return back(sense), back(common), back(band[side])


def write_dxf(path, layers):
    """{layer name: [polygons]} as closed polylines (mm), one DXF layer each."""
    import ezdxf
    doc = ezdxf.new("R2010"); doc.units = ezdxf.units.MM
    msp = doc.modelspace()
    for name, geoms in layers.items():
        doc.layers.add(name)
        for g in geoms:
            for q in polys(g):
                for ring in [q.exterior] + list(q.interiors):
                    msp.add_lwpolyline(list(ring.coords)[:-1], close=True, dxfattribs={"layer": name})
    doc.saveas(path)


def build(board_json, out_dir, channel=0.5, floor=0.5, inset=0.6, cover=0.4, wire=0.35, clearance=0.3,
          hole=1.2, bed=(256, 256), finger=0.6, gap=0.6, spine=0.8, pad=0.8, web_margin=0.6, ref_cell=True):
    d = json.loads(Path(board_json).read_text())
    outline = Polygon(d["outline"]).buffer(0)
    regions = {n: Polygon(r["outline"]).buffer(0) for n, r in d["regions"].items()}
    windows = {n: polys(r.buffer(-inset, 8))[0] for n, r in regions.items() if polys(r.buffer(-inset, 8))}
    bend_dir = d["bend"]["dir"]
    ts = np.asarray(d["routing_plan"][next(iter(d["routing_plan"]))][-1], float)          # the tail root
    tail_end, tail_dir, tail_w = np.asarray(d["tail"]["end"], float), np.asarray(d["tail"]["dir"], float), float(d["tail"]["width"])
    via = {n: tuple(pts[0]) for n, pts in d["routing_plan"].items()}
    # the reference cell: on the tail, clear of the sole, never loaded
    ref = None
    if ref_cell:
        tail_len = float(np.dot(tail_end - ts, tail_dir))
        length, width = 12.0, tail_w - 4.0
        if tail_len >= 6.0 + length + 8.0 and width >= 5.0:
            cen = ts + tail_dir * (6.0 + length / 2)
            nrm = np.array([-tail_dir[1], tail_dir[0]])
            corners = [cen + tail_dir * a * length / 2 + nrm * b * width / 2 for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
            ref = Polygon([tuple(q) for q in corners]).intersection(outline.buffer(-1.5))
            ref = polys(ref)[0] if polys(ref) else None
            if ref is not None:
                windows["ref"] = ref; via["ref"] = tuple(cen)
    # electrodes: per window a sense comb with its hole and pad, and a common comb
    sense, common_c, holes, spurs, cells = {}, {}, {}, [], {}
    for n, w in windows.items():
        fdir = tail_dir if n == "ref" else bend_dir
        s_, c_, s_band = combs(w, fdir, via[n], finger, gap, spine)
        mid = polys(s_band.buffer(-min(spine / 2 - 0.05, 0.3), 4))
        target = nearest_points(mid[0] if mid else s_band, Point(via[n]))[0]
        holes[n] = Point(target.x, target.y).buffer(hole / 2, 16)
        land = Point(target.x, target.y).buffer(hole / 2 + pad, 24).intersection(w.buffer(-0.3, 8))
        s_ = polys(unary_union([s_, land]))[0]
        c_ = polys(c_.difference(s_.buffer(gap, 8)))[0]
        sense[n], common_c[n] = s_, c_
        if n != "ref":
            spurs.append(LineString([via[n], (target.x, target.y)]).buffer(wire / 2 + clearance, 8))
        else:                # the reference wire drops into the trunk channel on the tail's centre line
            foot = ts + tail_dir * float(np.dot(np.array([target.x, target.y]) - ts, tail_dir))
            spurs.append(LineString([tuple(foot), (target.x, target.y)]).buffer(wire / 2 + clearance, 8))
    common_hole = Point(tuple(ts)).buffer(hole / 2, 16)
    # the common net: a web under the spacer's walls, bridged to every common comb
    web = outline.buffer(-1.5, 8).difference(unary_union([w.buffer(web_margin, 8) for w in windows.values()]))
    web = web.difference(unary_union([s_.buffer(gap, 8) for s_ in sense.values()]))
    bridges = []
    for n, c_ in common_c.items():
        a, b = nearest_points(c_, web)
        far = max(polys(web), key=lambda q: -q.distance(c_)) if polys(web) else web
        a, b = nearest_points(c_, far)
        bridges.append(LineString([a, b]).buffer(0.5, 8))
    common = unary_union([web] + bridges + list(common_c.values()) + [common_hole.buffer(pad, 24)])
    common = common.difference(unary_union([s_.buffer(gap, 8) for s_ in sense.values()])).intersection(outline.buffer(-1.0, 8))
    pieces = polys(common)
    main = next((q for q in pieces if q.intersects(common_hole)), pieces[0])
    dropped = sum(q.area for q in pieces if q is not main)
    common = main
    # printed parts
    ch, worst = channels(d, wire, clearance, extra=1 if ref is not None else 0)
    under = unary_union([ch] + spurs + list(holes.values()) + [common_hole]).intersection(outline.buffer(-0.8))
    layer_a, cut_a = printable(outline.difference(under))
    all_holes = unary_union(list(holes.values()) + [common_hole])
    layer_b, cut_b = printable(outline.difference(all_holes))
    carrier = solid(layer_a, 0.0, channel) + solid(layer_b, channel, floor)
    cov = solid(outline, 0.0, cover)
    spacer = outline.buffer(-0.5, 8).difference(unary_union(list(windows.values())))
    film = {n: w.buffer(-0.15, 8) for n, w in windows.items()}
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    label, side, hx = d["board_id"].split()
    stem = f"{label}_{side}_{hx}"
    stl(carrier.to_mesh(), out / f"{stem}.carrier.stl", f"sensor sole carrier {d['board_id']}")
    stl(cov.to_mesh(), out / f"{stem}.cover.stl", f"sensor sole cover {d['board_id']}")
    write_dxf(out / f"{stem}.electrodes.dxf", dict(SENSE=list(sense.values()), COMMON=[common],
                                                   HOLES=list(holes.values()) + [common_hole], OUTLINE=[outline]))
    write_dxf(out / f"{stem}.spacer.dxf", dict(SPACER=[spacer], OUTLINE=[outline]))
    write_dxf(out / f"{stem}.film.dxf", dict(FILM=list(film.values()), OUTLINE=[outline]))
    # checks
    vent_net = under.intersection(outline)
    trunk_piece = next((q for q in polys(vent_net) if q.distance(Point(tuple(tail_end - tail_dir * 4.0))) < 1.0), None)
    pitch = finger + gap
    cell_rep = {}
    for n, w in windows.items():
        both = sense[n].buffer(pitch, 8).intersection(common_c[n].buffer(pitch, 8)).intersection(w)
        cell_rep[n] = dict(window_mm2=round(w.area, 1), region_mm2=round(regions[n].area, 1) if n in regions else None,
                           sense_mm2=round(sense[n].area, 1), common_comb_mm2=round(common_c[n].area, 1),
                           interleaved_share=round(both.area / w.area, 3),
                           clearance_mm=round(sense[n].distance(common), 3),
                           joined_to_common=bool(common_c[n].intersection(common).area > 0.5 * common_c[n].area),
                           hole_on_sense=bool(sense[n].contains(holes[n].centroid)),
                           vented=bool(trunk_piece is not None and holes[n].intersects(trunk_piece)))
    thick = channel + floor
    checks = dict(
        carrier_watertight=carrier.status().name == "NoError", cover_watertight=cov.status().name == "NoError",
        carrier_genus_is_holes=carrier.genus() == len(holes) + 1,
        every_sense_comb_is_one_piece=all(len(polys(s_)) == 1 for s_ in sense.values()),
        common_is_one_piece_with_its_hole=bool(common.intersects(common_hole)),
        every_common_comb_joined=all(c["joined_to_common"] for c in cell_rep.values()),
        smallest_clearance_mm=min(c["clearance_mm"] for c in cell_rep.values()),
        clearance_ok=min(c["clearance_mm"] for c in cell_rep.values()) >= gap - 0.02,
        every_hole_on_its_sense_comb=all(c["hole_on_sense"] for c in cell_rep.values()),
        every_cell_vented_to_the_tail_end=all(c["vented"] for c in cell_rep.values()),
        copper_inside_the_outline=bool(unary_union(list(sense.values()) + [common]).within(outline.buffer(-0.99, 8))),
        smallest_interleaved_share=min(c["interleaved_share"] for c in cell_rep.values()))
    checks["all_pass"] = all(v for k, v in checks.items() if isinstance(v, bool))
    wall_between = min((a.distance(b) for i, a in enumerate(windows.values()) for b in list(windows.values())[i + 1:]), default=0)
    rep = dict(
        board_id=d["board_id"], design_hash=d["design_hash"], side=d["side"],
        status="design only: not printed, cut or assembled; sensing, fit and durability untested",
        matches="the flex sole's stack and sensing (shunt-mode combs under a film patch per region, one sense line per "
                "region, one common net); comb pitch is coarser (cuttable), and wires replace the copper routing",
        parts=dict(carrier=dict(file=f"{stem}.carrier.stl", thickness_mm=thick, volume_cm3=round(carrier.volume() / 1000, 2),
                                watertight=checks["carrier_watertight"], genus=carrier.genus()),
                   cover=dict(file=f"{stem}.cover.stl", thickness_mm=cover, volume_cm3=round(cov.volume() / 1000, 2),
                              watertight=checks["cover_watertight"]),
                   electrodes=dict(file=f"{stem}.electrodes.dxf", material="copper foil on an adhesive carrier (proposed)",
                                   finger_mm=finger, gap_mm=gap, spine_mm=spine, sense_pieces=len(sense),
                                   common_area_mm2=round(common.area, 1), common_dropped_mm2=round(dropped, 2)),
                   spacer=dict(file=f"{stem}.spacer.dxf", material="double-sided adhesive film (proposed)", windows=len(windows),
                               narrowest_wall_mm=round(wall_between, 2)),
                   film=dict(file=f"{stem}.film.dxf", patches=len(film), material="pressure-sensitive film, not chosen")),
        layers=dict(underside_channels_mm=channel, floor_with_holes_mm=floor, cover_mm=cover,
                    printed_total_mm=thick + cover, window_inset_mm=inset, hole_mm=hole,
                    note="the foil, spacer and film add their own thickness (about 0.25 mm together, to be measured)",
                    material="TPU (95A class), proposed"),
        cells=cell_rep, reference_cell=("ref" in windows),
        wires=dict(sense=len(holes) - (1 if "ref" in windows else 0), reference=1 if "ref" in windows else 0, common=1,
                   conductors=len(holes) + 1, most_in_one_channel=worst, wire_diameter_mm=wire,
                   note="channels follow the routing plan; widths are wires x diameter + clearance"),
        vent="each window opens through its wire hole into the underside channels, which run to the tail's end; "
             "do not pot the holes",
        removed_thin_walls_mm2=dict(channels=round(cut_a, 2), floor=round(cut_b, 2)),
        bed=bed_fit(outline, bed), checks=checks,
        caveats=["nothing has been printed, cut, bought or measured",
                 "comb fingers and gaps are 0.6 mm here and 0.2 mm on the flex board: sensitivity will differ",
                 "thicker than the flex sole; toe-pocket fit untested",
                 "the reference cell sits on the tail: it follows the shoe's temperature only roughly"])
    (out / f"{stem}.print.json").write_text(json.dumps(rep, indent=1) + "\n")
    preview(outline, sense, common, windows, under, out / f"{stem}.print.png", d["board_id"], thick + cover)
    return rep


def preview(outline, sense, common, windows, under, path, bid, thickness):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    ax = axes[0]
    ax.fill(*outline.exterior.xy, fc="#eef1f3", ec="#222", lw=0.6)
    for q in polys(common):
        ax.fill(*q.exterior.xy, fc="#c98b2b", ec="none")
        for h in q.interiors:
            ax.fill(*h.xy, fc="#eef1f3", ec="none")
    for n, s_ in sense.items():
        ax.fill(*s_.exterior.xy, fc="#1f5f8b", ec="none")
        c = windows[n].centroid; ax.text(c.x, c.y, n, fontsize=5, ha="center", va="center", color="#111",
                                         bbox=dict(fc="white", ec="none", alpha=0.6, pad=0.3))
    ax.set_title("electrode sheet: sense combs (blue), common net and combs (copper)", fontsize=9)
    ax = axes[1]
    ax.fill(*outline.exterior.xy, fc="#5b7a8c", ec="#222", lw=0.6)
    for q in polys(under.intersection(outline)):
        ax.fill(*q.exterior.xy, fc="#c9d6df", ec="none")
    ax.set_title("carrier underside: wire channels and holes (light)", fontsize=9)
    for ax in axes:
        ax.set_aspect("equal"); ax.axis("off")
    fig.suptitle(f"Printed prototype {bid}, {thickness:g} mm printed. Design only: not printed, sensing and fit untested",
                 fontsize=9)
    fig.tight_layout(); fig.savefig(path, dpi=150); plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("board_json"); ap.add_argument("-o", required=True)
    ap.add_argument("--channel", type=float, default=0.5); ap.add_argument("--floor", type=float, default=0.5)
    ap.add_argument("--inset", type=float, default=0.6); ap.add_argument("--finger", type=float, default=0.6)
    ap.add_argument("--gap", type=float, default=0.6); ap.add_argument("--no-ref", action="store_true")
    ap.add_argument("--cover", type=float, default=0.4); ap.add_argument("--wire", type=float, default=0.35)
    ap.add_argument("--bed", default="256x256")
    a = ap.parse_args()
    bed = tuple(float(v) for v in a.bed.lower().split("x"))
    rep = build(a.board_json, a.o, a.channel, a.floor, a.inset, a.cover, a.wire, bed=bed, finger=a.finger, gap=a.gap,
                ref_cell=not a.no_ref)
    print(json.dumps({k: rep[k] for k in ("board_id", "wires", "removed_thin_walls_mm2", "bed", "checks")}, indent=1))


if __name__ == "__main__":
    main()
