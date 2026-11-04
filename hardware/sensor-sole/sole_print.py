#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors
# SPDX-License-Identifier: CERN-OHL-S-2.0
"""A 3D-printable first prototype of the sensor sole, from the same generator output as the flex board.

The first physical prototype is printed, not a flex circuit. This script turns a sole design (the generator's
board file: outline with toe tabs and tail, sensing regions, routing plan) into two printable parts:

  carrier  TPU sole, three layers (bottom to top):
             - wire channels on the underside, along the routing plan to the tail, widened by the wires they carry
               (one sense wire per region plus one common wire);
             - a closed layer with one hole per region, through which its wire comes up into its pocket;
             - one pocket per region on top, inset from the region so pockets keep printable walls between
               them. The common wire comes up through a wall near the tail root, outside every pocket.
  cover    a thin TPU skin with the same outline, laid on top

Per region, in its pocket, bottom to top (a proposal; nothing chosen, bought or printed):
  sense electrode (copper tape or conductive fabric, with its wire) -> pressure-sensitive film patch
  (Velostat class, one patch per region) -> shared common electrode (conductive fabric covering every pocket,
  one common wire) -> cover.
This is through-mode sensing, unlike the flex design's shunt-mode combs. Its response, hysteresis and
crosstalk are unknown until measured (coupon test). Sensing, fit and durability are untested.

The parts are thicker than the flex sole (about 1.5 mm + 0.4 mm instead of 0.4 mm). In a five-toe shoe that is a
fit question for the fit test, not a settled fact.

Usage (the generator's Python plus manifold3d):
  python sole_print.py out/sole_EU42_R.board.json -o print/          # carrier + cover STL and a report
Options: --channel 0.5 --floor 0.5 --pocket 0.5 --inset 0.6 --cover 0.4 --wire 0.35 --bed 256x256 (mm)
Walls narrower than 0.8 mm (two 0.4 mm nozzle widths) are removed on purpose in each layer and reported.
"""
import argparse
import json
import math
import struct
from pathlib import Path

import numpy as np
from shapely import affinity
from shapely.geometry import LineString, MultiPolygon, Point, Polygon
from shapely.ops import unary_union


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


def channels(d, wire, clearance):
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
    n_all = len(lines) + 1
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


def build(board_json, out_dir, channel=0.5, floor=0.5, pocket=0.5, inset=0.6, cover=0.4, wire=0.35, clearance=0.3,
          hole=1.2, bed=(256, 256)):
    d = json.loads(Path(board_json).read_text())
    outline = Polygon(d["outline"]).buffer(0)
    regions = {n: Polygon(r["outline"]).buffer(0) for n, r in d["regions"].items()}
    pockets = {n: r.buffer(-inset, 8) for n, r in regions.items()}
    pockets = {n: (max(g.geoms, key=lambda q: q.area) if isinstance(g, MultiPolygon) else g) for n, g in pockets.items()}
    # each wire comes up through a hole just inside its pocket, nearest the via the routing plan starts from
    holes, spurs = {}, []
    for n, pts in d["routing_plan"].items():
        if n not in pockets or pockets[n].is_empty:
            continue
        via = Point(pts[0])
        inner = pockets[n].buffer(-hole / 2 - 0.4)
        target = inner.exterior.interpolate(inner.exterior.project(via)) if not inner.is_empty else pockets[n].centroid
        holes[n] = Point(target.x, target.y).buffer(hole / 2, 16)
        spurs.append(LineString([via, target]).buffer(wire / 2 + clearance, 8))
    ts = d["routing_plan"][next(iter(d["routing_plan"]))][-1]                # the tail root
    common_hole = Point(ts).buffer(hole / 2, 16)
    ch, worst = channels(d, wire, clearance)
    under = unary_union([ch] + spurs + list(holes.values()) + [common_hole]).intersection(outline.buffer(-0.8))
    layer_a, cut_a = printable(outline.difference(under))
    all_holes = unary_union(list(holes.values()) + [common_hole])
    layer_b, cut_b = printable(outline.difference(all_holes))
    layer_c, cut_c = printable(outline.difference(unary_union(list(pockets.values()) + [all_holes])))
    carrier = solid(layer_a, 0.0, channel) + solid(layer_b, channel, floor) + solid(layer_c, channel + floor, pocket)
    cov = solid(outline, 0.0, cover)
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    label, side, hx = d["board_id"].split()
    stem = f"{label}_{side}_{hx}"
    stl(carrier.to_mesh(), out / f"{stem}.carrier.stl", f"sensor sole carrier {d['board_id']}")
    stl(cov.to_mesh(), out / f"{stem}.cover.stl", f"sensor sole cover {d['board_id']}")
    thick = channel + floor + pocket
    wall_between = min((a.distance(b) for i, a in enumerate(pockets.values()) for b in list(pockets.values())[i + 1:]),
                       default=0)
    rep = dict(
        board_id=d["board_id"], design_hash=d["design_hash"], side=d["side"],
        status="design only: not printed; sensing, fit and durability untested",
        parts=dict(carrier=dict(file=f"{stem}.carrier.stl", thickness_mm=thick, volume_cm3=round(carrier.volume() / 1000, 2),
                                watertight=carrier.status().name == "NoError", genus=carrier.genus()),
                   cover=dict(file=f"{stem}.cover.stl", thickness_mm=cover, volume_cm3=round(cov.volume() / 1000, 2),
                              watertight=cov.status().name == "NoError")),
        layers=dict(underside_channels_mm=channel, floor_with_holes_mm=floor, pockets_mm=pocket, cover_mm=cover,
                    stack_total_mm=thick + cover, pocket_inset_mm=inset, hole_mm=hole,
                    narrowest_wall_between_pockets_mm=round(wall_between, 2), material="TPU (95A class), proposed"),
        pockets={n: dict(area_mm2=round(g.area, 1), region_area_mm2=round(regions[n].area, 1)) for n, g in pockets.items()},
        wires=dict(sense=len(holes), common=1, most_in_one_channel=worst, wire_diameter_mm=wire,
                   note="channels follow the routing plan; widths are wires x diameter + clearance"),
        removed_thin_walls_mm2=dict(channels=round(cut_a, 2), floor=round(cut_b, 2), pockets=round(cut_c, 2)),
        bed=bed_fit(outline, bed),
        sensor_stack_proposal=["sense electrode per pocket (copper tape or conductive fabric), its wire up through the hole",
                               "pressure-sensitive film patch per pocket (Velostat class, about 0.1 mm)",
                               "shared conductive-fabric common electrode over the whole top, its wire up through "
                               "the hole at the tail root (outside every pocket)",
                               "printed cover"],
        caveats=["through-mode film sensing: response, hysteresis and crosstalk unmeasured",
                 "thicker than the flex sole; toe-pocket fit untested",
                 "nothing has been printed or bought"])
    (out / f"{stem}.print.json").write_text(json.dumps(rep, indent=1) + "\n")
    preview(outline, layer_c, under, regions, out / f"{stem}.print.png", d["board_id"], thick)
    return rep


def preview(outline, top, under, regions, path, bid, thickness):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(15, 5.5))
    for ax, (geom, what) in zip(axes, ((top, "top: pockets (light) and walls (dark)"),
                                       (outline.difference(under), "underside: wire channels (light)"))):
        ax.fill(*outline.exterior.xy, fc="#c9d6df", ec="#222", lw=0.6)
        for g in (geom.geoms if isinstance(geom, MultiPolygon) else [geom]):
            ax.fill(*g.exterior.xy, fc="#5b7a8c", ec="none")
            for h in g.interiors:
                ax.fill(*h.xy, fc="#c9d6df", ec="none")
        for n, r in regions.items():
            c = r.centroid; ax.text(c.x, c.y, n, fontsize=5.5, ha="center", va="center")
        ax.set_aspect("equal"); ax.axis("off"); ax.set_title(what, fontsize=9)
    fig.suptitle(f"Printed carrier {bid}, {thickness:g} mm thick. Design only: not printed, sensing and fit untested",
                 fontsize=9)
    fig.tight_layout(); fig.savefig(path, dpi=130); plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("board_json"); ap.add_argument("-o", required=True)
    ap.add_argument("--channel", type=float, default=0.5); ap.add_argument("--floor", type=float, default=0.5)
    ap.add_argument("--pocket", type=float, default=0.5); ap.add_argument("--inset", type=float, default=0.6)
    ap.add_argument("--cover", type=float, default=0.4); ap.add_argument("--wire", type=float, default=0.35)
    ap.add_argument("--bed", default="256x256")
    a = ap.parse_args()
    bed = tuple(float(v) for v in a.bed.lower().split("x"))
    rep = build(a.board_json, a.o, a.channel, a.floor, a.pocket, a.inset, a.cover, a.wire, bed=bed)
    print(json.dumps({k: rep[k] for k in ("board_id", "parts", "wires", "removed_thin_walls_mm2", "bed")}, indent=1))


if __name__ == "__main__":
    main()
