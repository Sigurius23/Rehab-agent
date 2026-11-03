#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors
# SPDX-License-Identifier: CERN-OHL-S-2.0
"""Generate a higher-resolution candidate sole beside the 16-region baseline. Design and analysis only.

The candidate's regions come from a layout file (candidates/<name>/layout.json). sole_gen.py and sole_route.py
are used unchanged, so the baseline boards and their checks stay valid. This script supplies the layout's extra
anchors and splits a toe tab where the layout asks. It then runs the same build, routing, checks and exports.

Each candidate region names the baseline regions it comes from. A person's sensor choices therefore carry
over: a region whose source is switched off in the foot file is left out.

Usage (the generator's Python):
  sole_candidate.py candidates/T1/layout.json --size 42 --side R
  sole_candidate.py candidates/T1/layout.json --foot person_example.json --side L
Outputs go to candidates/<name>/out/ unless --out is given. The printed ID carries the candidate's name
("T1-EU42 R <hash>"), so a candidate sole cannot be mistaken for a baseline one.
"""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sole_gen as G  # noqa: E402
from shapely.geometry import MultiPolygon, box  # noqa: E402

_base_seeds, _base_regions = G.seeds, G.regions


def candidate_names(layout, base_names):
    """The layout's regions whose baseline sources are all present, in the layout's order."""
    have = set(base_names)
    return [r["name"] for r in layout["regions"] if all(f in have for f in r["from"])]


def bend_normal(sd):
    """Unit vector across the metatarsal-head line, pointing to the toes (as in sole_gen.build)."""
    m1, m5 = np.asarray(sd["mt1"]), np.asarray(sd["mt5"])
    t = (m1 - m5) / np.linalg.norm(m1 - m5)
    nrm = np.array([t[1], -t[0]])
    return -nrm if nrm[0] < 0 else nrm


def install(layout):
    """Point sole_gen at the layout: extra anchors, toe splits, and the layout's region order."""
    spec = {r["name"]: r for r in layout["regions"]}

    def seeds(s, centers):
        base = _base_seeds(s, centers)
        out = dict(base)
        nrm = bend_normal(base)
        for n, r in spec.items():
            a = r.get("anchor")
            if not a:
                continue
            if "behind" in a:                       # behind a pair of metatarsal heads, across the head line
                p = np.mean([base[k] for k in a["behind"]], axis=0) - nrm * a["back_L"] * s["L"]
                out[n] = (float(p[0]), float(p[1]))
            else:
                z = a["z_Wh"] * s["Wh"] if "z_Wh" in a else a["z_W"] * s["W"]
                out[n] = (a["x_L"] * s["L"], z)
        return out

    def regions(sole, toes, web_x, s, names, mode="region", disc=None):
        parts = {n: spec[n]["toe"] for n in names if n in spec and "toe" in spec[n]}
        base_names = []
        for n in names:
            m = f"toe{parts[n]['index']}" if n in parts else n
            if m not in base_names:
                base_names.append(m)
        out, sd = _base_regions(sole, toes, web_x, s, base_names, mode, disc)
        for parent in sorted({f"toe{p['index']}" for p in parts.values()}):
            zone = out.pop(parent, None)
            sd.pop(parent, None)
            if zone is None or zone.is_empty:
                continue
            x0, _, x1, _ = zone.bounds                 # along the toe, base to tip
            for n, p in parts.items():
                if f"toe{p['index']}" != parent:
                    continue
                cut = x0 + p["split"] * (x1 - x0)
                half = box(-999, -999, cut, 999) if p["part"] == "base" else box(cut, -999, 999, 999)
                g = zone.intersection(half)
                if isinstance(g, MultiPolygon):
                    g = max(g.geoms, key=lambda q: q.area)
                out[n] = g
                c = g.centroid
                sd[n] = (c.x, c.y)
        return {n: out[n] for n in names if n in out}, sd

    G.seeds, G.regions = seeds, regions
    G.fracture = fracture
    G.DEFAULT_SENSORS = [r["name"] for r in layout["regions"]]   # footprint order S01.. follows the layout


_base_fracture = G.fracture


def fracture(poly):
    """sole_gen.fracture with a guard. The shared version splits a polygon by a vertical line through its first
    hole and recurses. On the mirrored synthetic foot with T1's regions, one comb has a hole where that split
    makes no progress, and the recursion never ends. Where the vertical split works, this does exactly what
    sole_gen.fracture does. Where it makes no progress, it splits horizontally through the hole instead, then
    through the hole's centroid. If nothing works, it stops with an error rather than looping. The shared
    function is left unchanged, because the baseline boards record its hash."""
    from shapely.geometry import LineString, Polygon
    from shapely.ops import split
    if poly.is_empty:
        return []
    if not poly.interiors:
        return [poly]
    h = Polygon(poly.interiors[0])
    rp, c = h.representative_point(), h.centroid
    minx, miny, maxx, maxy = poly.bounds
    vert = lambda x: LineString([(x, miny - 1), (x, maxy + 1)])
    horz = lambda y: LineString([(minx - 1, y), (maxx + 1, y)])
    for cut in (vert(rp.x), horz(rp.y), vert(c.x), horz(c.y)):
        parts = [q for q in split(poly, cut).geoms if q.geom_type == "Polygon" and q.area > 1e-4]
        if len(parts) > 1 or (parts and len(parts[0].interiors) < len(poly.interiors)):
            break
    else:
        raise RuntimeError(f"cannot split a comb piece with {len(poly.interiors)} hole(s) into hole-free pads")
    out = []
    for q in parts:
        out += fracture(q)
    return out


def stamp_candidate_files(layout_path):
    """Add this script and the layout file to the generator stamp, so the board records what made it."""
    files, rev, dirty, tools = G._SOURCE
    h = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()[:12]
    files = dict(files, sole_candidate=h(__file__), layout=h(layout_path))
    try:
        rel = [str(Path(__file__).resolve().relative_to(HERE)), str(Path(layout_path).resolve().relative_to(HERE))]
        mod = subprocess.run(["git", "-C", str(HERE), "status", "--porcelain", "--", *rel], capture_output=True,
                             text=True, timeout=20).stdout.strip()
        dirty = bool(dirty) or bool(mod)
    except Exception:
        pass
    G._SOURCE = (files, rev, dirty, tools)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("layout")
    ap.add_argument("--size", type=float, default=42)
    ap.add_argument("--length", type=float)
    ap.add_argument("--width", type=float)
    ap.add_argument("--foot")
    ap.add_argument("--side", choices=("R", "L"), default="R")
    ap.add_argument("--exit", choices=("arch", "heel"), default="arch")
    ap.add_argument("--out")
    ap.add_argument("--name")
    a = ap.parse_args()
    a.mode = "region"
    layout = json.loads(Path(a.layout).read_text())
    install(layout)
    stamp_candidate_files(a.layout)
    over, base = {}, list(G.DEFAULT_SENSORS_BASELINE)
    if a.foot:
        cfg = json.loads(Path(a.foot).read_text())
        over = cfg.get("landmarks", {})
        base = cfg.get("sensors", base)
        for k in ("length", "width", "side", "exit"):
            if k in cfg and getattr(a, k) in (None, ap.get_default(k)):
                setattr(a, k, cfg[k])
    names = candidate_names(layout, base)
    s = G.foot_spec(a.length, a.width, a.size, over)
    geo, checks = G.build(s, names, "region", a.exit, a.side)
    out = Path(a.out) if a.out else Path(a.layout).resolve().parent / "out"
    out.mkdir(parents=True, exist_ok=True)
    who = Path(a.foot).stem if a.foot else (f"EU{a.size:g}" if not a.length else f"L{a.length:.0f}")
    stem = a.name or f"cand_{layout['name']}_{who}_{a.side}"
    title = (f"{stem}: candidate {layout['name']}, foot length {s['L']:.0f} mm, ball width {s['W']:.0f} mm, "
             f"{len(geo['regions'])} regions, tail exit {a.exit}")
    G.to_svg(geo, out / f"{stem}.svg", title); G.to_dxf(geo, out / f"{stem}.dxf")
    G.to_json(geo, checks, s, a, out / f"{stem}.json"); G.to_png(geo, checks, out / f"{stem}.png", title)
    bj = out / f"{stem}.board.json"
    G.to_board_json(geo, s, a, bj, requested=names, checks=checks)
    d = json.loads(bj.read_text())                   # the candidate's name in front of the printed label
    label, side, hx = d["board_id"].split()
    d["board_id"] = f"{layout['name']}-{label} {side} {hx}"
    # in "source", which the design hash leaves out: what made the board, not what it is
    d["source"]["candidate"] = dict(layout=layout["name"], layout_file=Path(a.layout).name,
                                    derived_from=base, regions=names)
    bj.write_text(json.dumps(d))
    print(json.dumps(dict(stem=stem, board_id=d["board_id"], **checks), indent=1))


G.DEFAULT_SENSORS_BASELINE = list(G.DEFAULT_SENSORS)

if __name__ == "__main__":
    main()
