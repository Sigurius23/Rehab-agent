#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors
# SPDX-License-Identifier: CERN-OHL-S-2.0
"""Sensor sole v0: a five-toe pressure-sensing sole, generated from the foot.

One passive flex circuit lies in the shoe; the electronics sit in a pod outside it. This script makes
the sole's geometry for any size and any foot:

  foot spec  -> outline with five toe tabs (or a toe-less variant)
             -> sensing regions anchored to anatomy (heel, midfoot, five metatarsal heads, five toes)
             -> a flex tail leaving the sole at the medial arch (default) or the heel
             -> a routing plan: every region's signal line to the tail, through channels between regions,
                with the channels widened where the bundle needs it
             -> checks (fit, clearances, toe widths, bundle capacity, bend zone)
             -> SVG, DXF (for KiCad), JSON and a PNG preview

Frame: the foot frame of the twin. x runs from the heel point along the heel -> 2nd-toe axis; z is the
foot's own rightward axis. A right foot is generated (lateral = +z); a left foot is its mirror.
All lengths are millimetres. Proportions are population defaults, every one of them overridable by
a person's scan landmarks (--foot). They are a starting shape, not a measurement.

Usage:
  sole_gen.py --size 42 --out OUT/            # EU 42, default proportions
  sole_gen.py --length 268 --width 103 ...    # measured foot
  sole_gen.py --foot person.json ...          # landmarks and sensor choices from a scan
"""
import argparse, hashlib, json, math, subprocess
from pathlib import Path

import numpy as np
from scipy import ndimage
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra
from shapely import affinity
from shapely.geometry import LineString, MultiPolygon, Point, Polygon, box
from shapely.ops import unary_union, voronoi_diagram

# ----------------------------------------------------------------------------------------------- defaults
FAB = dict(                      # flex-circuit rules (conservative for 2-layer polyimide)
    edge_margin=2.0,             # copper-free border along the outline
    region_gap=1.2,              # minimum gap between two sensing regions
    pitch=0.40,                  # lane pitch in a bundle (0.12 mm track + 0.28 mm space; >= the router's clearance incl. grid error)
    route_clear=0.8,             # bundle to region clearance (room for vias and for lines that must bend)
    min_toe_region=6.0,          # narrowest toe region worth sensing
    comb_finger=0.20, comb_gap=0.20,   # interdigitated electrode (shunt-mode sensor) finger / gap
    ffc_pitch=0.5,               # connector pitch at the end of the tail
    tail_len=70.0,               # tail length outside the sole, to the pod
    bend_band=12.0,              # half-width of the metatarsophalangeal bend zone (no vias)
)

DEFAULT_SENSORS = [             # name, zone, anchor (see seeds()); 16 channels like OpenGo
    "heel_post", "heel_med", "heel_lat",
    "arch_med", "mid_lat_prox", "mid_lat_dist",
    "mt1", "mt2", "mt3", "mt4", "mt5",
    "toe1", "toe2", "toe3", "toe4", "toe5",
]


def eu_to_length(eu):
    """EU size -> foot length (mm). An approximation (Vibram EU 42 fits ~264-273 mm); measure when you can."""
    return 6.67 * eu - 10.0


def foot_spec(length=None, width=None, size=None, over=None):
    """Landmarks of a right foot in the foot frame. `over` replaces any default (from a scan)."""
    L = length or eu_to_length(size or 42)
    W = width or 0.385 * L                     # ball width
    Wh = 0.255 * L                             # heel width
    s = dict(L=L, W=W, Wh=Wh,
             mt1=(0.725 * L, -0.40 * W), mt5=(0.635 * L, 0.60 * W),        # medial / lateral ball edges
             # toes: tip x (fraction of L), width (fraction of W), web x behind the toe's medial side
             toes=[dict(tip=1.000, w=0.250), dict(tip=0.985, w=0.155), dict(tip=0.955, w=0.145),
                   dict(tip=0.920, w=0.140), dict(tip=0.870, w=0.140)],
             webs=[0.775, 0.790, 0.775, 0.745],                            # web x / L between toes i, i+1
             toe_gap=2.0,                                                  # slit width between toe tabs
             toe_tabs=[True] * 5)                                          # False: stop at the web
    if over:
        for k, v in over.items():
            s[k] = v
    return s


# ------------------------------------------------------------------------------------------------ outline
def outline(s):
    """Sole outline (shapely Polygon), toe tab polygons and the web points."""
    L, W, Wh = s["L"], s["W"], s["Wh"]
    zmed_ball, zlat_ball = s["mt1"][1], s["mt5"][1]
    # toe tabs: laid side by side from the medial ball edge, each a rounded strip from its web to its tip
    widths = [t["w"] * W for t in s["toes"]]
    span = sum(widths) + s["toe_gap"] * 4
    z0 = zmed_ball + 0.02 * W                       # hallux medial edge just inside the ball edge
    if z0 + span > zlat_ball:                       # keep the toes within the ball width
        z0 = zlat_ball - span
    toes, centers, z = [], [], z0
    web_x = [w * L for w in s["webs"]]
    for i, (t, w) in enumerate(zip(s["toes"], widths)):
        base = min(web_x[max(0, i - 1)], web_x[min(i, 3)]) - 12.0      # overlaps the body: no gap
        tip = t["tip"] * L
        r = w / 2
        strip = box(base, z, tip - r, z + w).union(Point(tip - r, z + r).buffer(r, 32))
        toes.append(strip); centers.append(z + r); z += w + s["toe_gap"]
    # body: one ordered loop -- heel arc (lateral half), lateral edge, front at the toe bases, medial edge,
    # heel arc (medial half). Straight segments, then rounded by an open/close buffer (no spline overshoot).
    hc = Wh / 2
    arc = lambda a0, a1: [(hc + hc * math.cos(a), hc * math.sin(a)) for a in np.linspace(a0, a1, 10)]
    lat = [(0.30 * L, Wh / 2 + 0.05 * W), (0.48 * L, 0.46 * W), (s["mt5"][0], zlat_ball)]
    lat_front = (web_x[3] - 2, z0 + span)                          # lateral side of the 5th toe base
    med_front = (web_x[0] - 2, zmed_ball + 0.01 * W)               # medial side of the hallux base
    med = [(s["mt1"][0], zmed_ball), (0.50 * L, -0.33 * W), (0.30 * L, -Wh / 2 - 0.01 * W)]
    pts = arc(math.pi, math.pi / 2) + lat + [lat_front, med_front] + med + arc(-math.pi / 2, -math.pi)
    body = Polygon(pts).buffer(0).buffer(8, 32).buffer(-8, 32)
    # webs: the sole between two toe tabs ends at the web; cut a slit from the web forward
    sole = body
    for i, t in enumerate(toes):
        sole = sole.union(t) if s["toe_tabs"][i] else sole
    for i in range(4):
        if not (s["toe_tabs"][i] and s["toe_tabs"][i + 1]):
            continue
        zg = centers[i] + widths[i] / 2 + s["toe_gap"] / 2
        sole = sole.difference(box(web_x[i], zg - s["toe_gap"] / 2, L + 5, zg + s["toe_gap"] / 2))
    front_cut = box(max(web_x) + 1, -W, L + 10, W)      # nothing beyond the webs except toe tabs
    keep = unary_union([t for t, on in zip(toes, s["toe_tabs"]) if on] + [box(-10, -W, max(web_x) + 1, W)])
    sole = sole.difference(front_cut.difference(keep))
    sole = sole.buffer(1.0).buffer(-1.0)               # round off corners
    if isinstance(sole, MultiPolygon):
        sole = max(sole.geoms, key=lambda g: g.area)
    return sole, [t if on else None for t, on in zip(toes, s["toe_tabs"])], centers, web_x


# ------------------------------------------------------------------------------------------------ sensors
def seeds(s, centers):
    """Anatomical anchor of every sensing region (right foot)."""
    L, W, Wh = s["L"], s["W"], s["Wh"]
    (x1, z1), (x5, z5) = s["mt1"], s["mt5"]
    mt = {f"mt{k}": (x1 + (x5 - x1) * f, z1 + (z5 - z1) * f) for k, f in zip(range(1, 6), (0.13, 0.33, 0.52, 0.70, 0.87))}
    mt = {k: (x - 0.035 * L, z) for k, (x, z) in mt.items()}            # head centres, behind the ball edge line
    out = dict(heel_post=(0.055 * L, 0.0), heel_med=(0.15 * L, -0.22 * Wh), heel_lat=(0.15 * L, 0.22 * Wh),
               arch_med=(0.42 * L, -0.17 * W), mid_lat_prox=(0.36 * L, 0.33 * W), mid_lat_dist=(0.52 * L, 0.40 * W),
               **mt)
    for i, t in enumerate(s["toes"]):
        out[f"toe{i + 1}"] = (t["tip"] * L - (0.55 if i == 0 else 0.6) * t["w"] * W, centers[i])
    return out


def regions(sole, toes, web_x, s, names, mode="region", disc=None):
    """Sensing regions: Voronoi tiles of the anchors clipped to the sole (region mode) or discs (point mode)."""
    sd = seeds(s, [c for c in s["_centers"]])
    inner = sole.buffer(-FAB["edge_margin"])
    own_web = [max(web_x[max(0, i - 1)], web_x[min(i, 3)]) for i in range(5)]   # a toe starts at its higher web
    toe_zone = {f"toe{i + 1}": t.intersection(box(own_web[i] + 2, -999, 999, 999)).buffer(0) if t is not None else None
                for i, t in enumerate(toes)}
    body_zone = inner.difference(unary_union([z.buffer(0.5) for z in toe_zone.values() if z is not None]))
    out = {}
    if mode == "point":
        d = disc or {}
        for n in names:
            r = d.get(n, 16 if "heel" in n else 14 if n.startswith("mt") or "mid" in n or "arch" in n else 12) / 2
            out[n] = Point(sd[n]).buffer(r, 48).intersection(inner)
        return out, sd
    body_names = [n for n in names if not n.startswith("toe")]
    from shapely.geometry import MultiPoint
    vor = voronoi_diagram(MultiPoint([sd[n] for n in body_names]), envelope=box(-50, -200, 400, 200))
    for cell in vor.geoms:                       # full cells, no gaps yet: routing runs along their borders
        for n in body_names:
            if cell.contains(Point(sd[n])):
                out[n] = cell.intersection(body_zone)
    for n in names:
        if n.startswith("toe"):
            z = toe_zone.get(n)
            if z is not None and not z.is_empty:
                out[n] = z.intersection(inner)
    return out, sd


# ------------------------------------------------------------------------------------------------ routing
def tail_geometry(sole, s, n_lines, exit="arch"):
    """Tail strip leaving the sole perpendicular to its edge; width from the conductor count."""
    L = s["L"]
    w = n_lines * FAB["ffc_pitch"] + 2 * 1.5
    if exit == "heel":
        p, d = np.array([0.0, 0.0]), np.array([-1.0, 0.0])
    else:                                            # medial arch: highest point of the arch, least load
        x = 0.42 * L
        line = LineString([(x, 0), (x, -400)])
        q = line.intersection(sole.exterior)
        q = min([q] if q.geom_type == "Point" else list(q.geoms), key=lambda g: abs(g.y))
        p, d = np.array([q.x, q.y]), np.array([0.0, -1.0])
    a = p - d * 4                                    # start a little inside the sole
    b = p + d * FAB["tail_len"]
    n = np.array([-d[1], d[0]]) * w / 2
    strip = Polygon([a + n, b + n, b - n, a - n])
    return strip, tuple(a), tuple(p), w, (tuple(b), tuple(d))


def _relocate_vias(names, full_idx, paths, load, lab, free, idx, X, Y, xx, yy, res, sense, side, band, margin=0.3,
                   window=20.0):
    """Move every via that sits inside or beside a bundle into its own region, clear of the bundle; its line
    follows it there. Returns {net: mm moved}.

    The tree is grown one region at a time, and each via is chosen next to the tree before the bundle there has
    its final width. With 10 or more lines passing, a via then lies inside the bundle or on the outside of
    its turn, and the lines that continue past it must squeeze by (EU 37 and EU 46 failed that way). Once every
    path is known, the load of each tree cell is final, so the room a via needs is known too:
      - from a cell carrying L lines: half the bundle, (L - 1) / 2 pitches, plus half a track, the clearance, the
        via's radius and a margin for smoothing (all in mm);
      - from another via: room for a line to pass between the two.
    The new via is the nearest such cell in the same region, outside the bend band, preferring the sense side
    of its comb. The extension runs inside the region and keeps a line's clearance from other bundles. Every via
    is then a leaf beyond the edge of the bundle it leaves, so the lane order at each branch is planar.
    """
    pitch, tw, cl, vd = FAB["pitch"], CONTACT["sense_w"], CONTACT["clear"], CONTACT["via_d"]
    ny, nx = lab.shape
    r_via = lambda L: (L - 1) / 2 * pitch + tw / 2 + cl + vd / 2 + margin
    r_lane = lambda L: L / 2 * pitch + tw / 2 + cl
    r_vv = vd + cl + 2 * (tw + cl)
    w = int(window / res)
    moved = {}
    for n in names:
        if n not in full_idx:
            continue
        k = names.index(n)
        own = full_idx[n]
        v0 = own[0]
        ci, cj = int(yy[v0]), int(xx[v0])
        i0, i1, j0, j1 = max(0, ci - w), min(ny, ci + w + 1), max(0, cj - w), min(nx, cj + w + 1)
        L_win = load[i0:i1, j0:j1]
        own_mask = np.zeros((ny, nx), bool); own_mask[yy[own], xx[own]] = True
        own_win = own_mask[i0:i1, j0:j1]
        private = own_win & (L_win == 1)                    # cells only this line uses (its own leaf)
        other = (L_win > 0) & ~private
        forb_via = np.zeros(L_win.shape, bool); forb_lane = np.zeros(L_win.shape, bool)
        for L in np.unique(L_win[other]):
            m = other & (L_win == L)
            d = ndimage.distance_transform_edt(~m) * res
            forb_via |= d < r_via(int(L)); forb_lane |= d < r_lane(int(L))
        vmask = np.zeros(L_win.shape, bool)
        for m2 in names:
            if m2 != n and m2 in full_idx:
                q = full_idx[m2][0]
                if i0 <= yy[q] < i1 and j0 <= xx[q] < j1:
                    vmask[yy[q] - i0, xx[q] - j0] = True
        if vmask.any():
            forb_via |= ndimage.distance_transform_edt(~vmask) * res < r_vv
        if not forb_via[ci - i0, cj - j0]:
            continue                                         # already clear
        region = (lab[i0:i1, j0:j1] == k) & free[i0:i1, j0:j1]
        # The extension starts beside the bundle, so it must be free to leave the bundle's clearance zone; it
        # pays for every cell inside it (so it leaves straight away) and may never cross another line's path.
        barrier = ndimage.binary_dilation(other, structure=np.ones((3, 3), bool))
        allowed = (region | private) & ~barrier
        allowed[ci - i0, cj - j0] = True
        pen = np.where(forb_lane, 20.0, 1.0)
        gx, gy = np.meshgrid(X[j0:j1], Y[i0:i1])
        target = allowed & region & ~forb_via
        if band is not None:
            bp, nrm, hw = band
            target &= np.abs((gx - bp[0]) * nrm[0] + (gy - bp[1]) * nrm[1]) >= hw
        if not target.any():
            moved[n] = "no room in its region"; continue
        # shortest extension from the old via through allowed cells (8-connected)
        li = -np.ones(L_win.shape, int); af = np.flatnonzero(allowed.ravel()); li.ravel()[af] = np.arange(len(af))
        hh, ww = L_win.shape
        rr, cc, ws = [], [], []
        for dy, dx in ((0, 1), (1, 0), (1, 1), (1, -1)):
            a = li[0:hh - dy, max(0, -dx):ww - max(0, dx)]
            b = li[dy:hh, max(0, dx):ww - max(0, -dx)]
            ok = (a >= 0) & (b >= 0)
            st = res * math.hypot(dx, dy)
            pa, pb = pen.ravel()[af[a[ok]]], pen.ravel()[af[b[ok]]]
            wgt = 0.5 * (pa + pb) * st
            rr += [a[ok], b[ok]]; cc += [b[ok], a[ok]]; ws += [wgt, wgt]
        G = csr_matrix((np.concatenate(ws), (np.concatenate(rr), np.concatenate(cc))), shape=(len(af), len(af)))
        s0 = li[ci - i0, cj - j0]
        Dd, pr = dijkstra(G, indices=s0, return_predecessors=True)
        cand = li[target]
        cand = cand[np.isfinite(Dd[cand])]
        if len(cand) == 0:
            moved[n] = "no path into its region"; continue
        # prefer the sense side of the comb (short stub), then the shortest move
        tier = np.zeros(len(cand))
        if sense is not None and n in sense:
            t, split = sense[n]
            sg = side.get(n, 1)
            ty, tx = np.unravel_index(af[cand], (hh, ww))
            sd = sg * (X[j0 + tx] * t[0] + Y[i0 + ty] * t[1] - split)
            tier = np.where(sd >= 1.5, 0, np.where(sd >= 0.5, 1, 2))
        best = cand[np.lexsort((Dd[cand], tier))[0]]
        ext = [best]
        while ext[-1] != s0:
            ext.append(pr[ext[-1]])
        ey, ex = np.unravel_index(af[np.asarray(ext)], (hh, ww))
        cells = [int(idx[i0 + a, j0 + b]) for a, b in zip(ey, ex)]          # new via ... old via
        new_full = cells[:-1] + list(own)
        full_idx[n] = new_full
        paths[n] = [(X[xx[q]], Y[yy[q]]) for q in new_full]
        load[yy[cells[:-1]], xx[cells[:-1]]] += 1
        moved[n] = round(float(np.hypot(X[j0 + ex[0]] - X[cj], Y[i0 + ey[0]] - Y[ci])), 2)
    return moved


def route(sole, regs, tail_start, res=0.25, sense=None, band=None, relocate=True):
    """Route every region's signal line to the tail along region borders; carve the bundles out.

    A label raster of the regions gives the borders (and the sole edge). The path cost rises steeply with
    distance from a border, so lines run in the seams between regions, as on a hand-routed insole, and
    bundles form where seams meet. One Dijkstra from the tail entry gives every region's shortest path; each
    path ends at the border point of its own region nearest the tail (the via). Bundles are then carved out of
    the regions at their real width: n lines x pitch + clearance on both sides.
    """
    from matplotlib.path import Path as MP
    minx, miny, maxx, maxy = sole.bounds
    nx, ny = int((maxx - minx) / res) + 3, int((maxy - miny) / res) + 3
    X = minx - res + np.arange(nx) * res; Y = miny - res + np.arange(ny) * res
    gx, gy = np.meshgrid(X, Y); pts_all = np.c_[gx.ravel(), gy.ravel()]
    def rast(geom):
        m = np.zeros(ny * nx, bool)
        for g in ([geom] if geom.geom_type == "Polygon" else list(getattr(geom, "geoms", []))):
            if g.is_empty:
                continue
            inside = MP(np.asarray(g.exterior.coords)).contains_points(pts_all)
            for h in g.interiors:
                inside &= ~MP(np.asarray(h.coords)).contains_points(pts_all)
            m |= inside
        return m.reshape(ny, nx)
    # bundles may run along the sole's edge (a perimeter channel), so their centre line keeps half the widest
    # bundle plus clearance inside the copper-free margin
    # Inset from the edge: room for a full-width bundle wherever a path runs along the edge. (A small inset
    # plus a soft edge cost was tried: a weak cost let wide bundles spill past the copper-free margin, a strong
    # one sent the heel lines on a detour through the midfoot that tangled them with other lines.)
    half = (len(regs) + 1) * FAB["pitch"] / 2 + FAB["route_clear"]
    hard = half                                      # a full-width bundle fits along any edge it uses
    inner = rast(sole.buffer(-FAB["edge_margin"] - hard))
    d_edge = ndimage.distance_transform_edt(inner) * res + hard     # distance to the copper-free margin
    names = [n for n, r in regs.items() if not r.is_empty]
    lab = np.full((ny, nx), -1, int)
    for k, n in enumerate(names):
        lab[rast(regs[n]) & inner] = k
    free = inner.copy()
    # borders: label changes between neighbours, or the edge of the usable sole
    edge = np.zeros_like(free)
    for sh in ((0, 1), (1, 0), (0, -1), (-1, 0)):
        nb = np.roll(np.roll(lab, sh[0], 0), sh[1], 1)
        ninner = np.roll(np.roll(inner, sh[0], 0), sh[1], 1)
        edge |= free & ((nb != lab) | ~ninner)
    bd = ndimage.distance_transform_edt(~edge) * res                  # mm from the nearest border
    cost = np.where(free, 1.0 + 15.0 * bd, np.inf)
    idx = -np.ones((ny, nx), int); fi = np.flatnonzero(free.ravel()); idx.ravel()[fi] = np.arange(len(fi))
    rows, cols, w = [], [], []
    for dy, dx in ((0, 1), (1, 0), (1, 1), (1, -1)):                 # 8-connected grid, each edge once
        a = idx[0:ny - dy, max(0, -dx):nx - max(0, dx)]
        b = idx[dy:ny, max(0, dx):nx - max(0, -dx)]
        ok = (a >= 0) & (b >= 0)
        ai, bi = a[ok], b[ok]
        cw = 0.5 * (cost.ravel()[fi[ai]] + cost.ravel()[fi[bi]]) * res * math.hypot(dx, dy)
        rows += [ai, bi]; cols += [bi, ai]; w += [cw, cw]
    rows, cols, w0 = np.concatenate(rows), np.concatenate(cols), np.concatenate(w)
    G = csr_matrix((w0, (rows, cols)), shape=(len(fi), len(fi)))
    cand = np.argwhere(free)
    i0, j0 = (tail_start[1] - Y[0]) / res, (tail_start[0] - X[0]) / res
    src = idx[tuple(cand[np.argmin((cand[:, 0] - i0) ** 2 + (cand[:, 1] - j0) ** 2)])]
    D, pred = dijkstra(G, indices=src, return_predecessors=True)
    yy, xx = np.unravel_index(fi, (ny, nx))

    def endpoints(k, n, sgn=1):
        """Via candidates of region k on one side (sgn) of its comb split, and how well they clear the split
        (0 best). The sense comb's spine runs along that side, so the via's stub to it stays short."""
        ends = idx[(lab == k) & (bd <= 0.6) & free]
        ends = ends[np.isfinite(D[ends])]
        ex, ey = X[xx[ends]], Y[yy[ends]]
        keep = np.ones(len(ends), bool)
        if band is not None:                         # no via in the toe-joint bend band
            bp, nrm, hw = band
            keep &= np.abs((ex - bp[0]) * nrm[0] + (ey - bp[1]) * nrm[1]) >= hw
        tier = 0
        if sense is not None and n in sense:         # the via sits beside the sense comb's spine
            t, split = sense[n]
            for tier, margin in enumerate((1.5, 0.5, -1e9)):
                ok = keep & (sgn * (ex * t[0] + ey * t[1] - split) >= margin)
                if ok.any():
                    keep = ok; break
        return (ends[keep], tier) if keep.any() else (ends, 3)

    def both_sides(k, n):
        """Via candidates and the comb side they belong to (+1: the default sense side).

        A toe's via belongs at the base of its tab, where the trunk passes: a line that runs up the tab to a
        via splits the toe's comb, and the fingers cut off from their spine stop sensing (toe2 at EU 42 kept
        38 % of its tile that way). The comb split runs parallel to the oblique bend line, so on a narrow toe
        the default side can have no cell near the base at all; then the toe takes the other side there, and
        its comb swaps spines to match. Every other region keeps the default side."""
        ends, tier = endpoints(k, n, 1)
        if not n.startswith("toe") or sense is None or n not in sense or band is None:
            return ends, np.ones(len(ends), int)
        bp, nrm, _hw = band
        along = lambda e: X[xx[e]] * nrm[0] + Y[yy[e]] * nrm[1]
        cells = idx[(lab == k) & free]
        base = float(np.min(along(cells))) + 10.0         # the first 10 mm of the toe region
        pick = []
        for sg in (1, -1):
            e, tr = endpoints(k, n, sg)
            e = e[along(e) <= base]
            if len(e):
                pick.append((tr, -sg, e, sg))                # better tier first, then the default side
        if not pick:
            return ends, np.ones(len(ends), int)
        tr, _, e, sg = min(pick, key=lambda q: (q[0], q[1]))
        return e, np.full(len(e), sg)

    # Grow one tree from the tail, farthest region first. Each new path runs to the nearest point of the
    # tree (every tree cell is a source at distance 0) and is penalised for running close beside it without
    # joining, so parallel lines share one bundle instead of shadowing each other. Vias stay off the tree.
    order_k = sorted(range(len(names)), key=lambda k: -float(np.min(D[both_sides(k, names[k])[0]], initial=np.inf))
                     if len(both_sides(k, names[k])[0]) else 0)
    parent = {src: -1}
    via_cells = set()
    paths, load, side, full_idx = {}, np.zeros((ny, nx), int), {}, {}
    near_r = 1.5                                     # mm: "beside the tree"
    pitch, tw, cl_, vd = FAB["pitch"], CONTACT["sense_w"], CONTACT["clear"], CONTACT["via_d"]
    r_via = lambda L: L / 2 * pitch + tw / 2 + cl_ + vd / 2 + 0.3        # via to the centre of L lines, counting
                                                                         # the line that will join them
    r_vv = vd + cl_ + 2 * (tw + cl_) + 0.3                               # via to via: a line fits between
    via_keep = vd / 2 + cl_ + tw / 2 + 0.2                               # no later line this close to a via
    via_fallback = []
    for k in order_k:
        n = names[k]
        ends, sgns = both_sides(k, n)
        if len(ends) == 0:
            paths[n] = None; continue
        tree_mask = np.zeros((ny, nx), bool)
        tl = np.fromiter(parent.keys(), int)
        tree_mask[yy[tl], xx[tl]] = True
        # A via must not sit on the tree, nor so close to it that the bundle there would have to squeeze past:
        # it keeps the bundle's half-width (from the lines already through each tree cell) plus via clearance,
        # and keeps room for a line from every other via. A cell on the tree costs nothing to reach, so without
        # this a via was often chosen on the trunk itself, inside the bundle.
        forb = np.zeros((ny, nx), bool)
        for L in np.unique(load[load > 0]):
            forb |= ndimage.distance_transform_edt(load != L) * res < r_via(int(L))
        vm = np.zeros((ny, nx), bool)
        if via_cells:
            vc = np.fromiter(via_cells, int); vm[yy[vc], xx[vc]] = True
            dv = ndimage.distance_transform_edt(~vm) * res
            forb |= dv < r_vv
        ok_end = ~forb[yy[ends], xx[ends]]
        if ok_end.any():
            ends, sgns = ends[ok_end], sgns[ok_end]
        else:
            via_fallback.append(n)                    # no clear cell in its region: keep the nearest
        near = (ndimage.distance_transform_edt(~tree_mask) * res <= near_r) & ~tree_mask
        f = np.where(near[yy, xx], 3.0, 1.0)
        if via_cells:                                 # later lines keep off earlier vias entirely
            f = np.where(dv[yy, xx] < via_keep, np.inf, f)
        Gk = csr_matrix((w0 * np.maximum(f[rows], f[cols]), (rows, cols)), shape=(len(fi), len(fi)))
        blocked_via = set()
        for v in via_cells:                          # never join the tree at (or right next to) a via
            vy, vx = yy[v], xx[v]
            for dy in range(-3, 4):
                for dx in range(-3, 4):
                    j = idx[min(max(vy + dy, 0), ny - 1), min(max(vx + dx, 0), nx - 1)]
                    if j >= 0:
                        blocked_via.add(int(j))
        sources = [c for c in parent if c not in blocked_via]
        Dk, pk, _ = dijkstra(Gk, indices=sources, return_predecessors=True, min_only=True)
        ie = int(np.argmin(Dk[ends])); e = ends[ie]
        if not np.isfinite(Dk[e]):
            paths[n] = None; continue
        side[n] = int(sgns[ie])
        seq = [e]
        while seq[-1] not in parent and pk[seq[-1]] >= 0:
            seq.append(pk[seq[-1]])
        for a, b2 in zip(seq[:-1], seq[1:]):
            parent.setdefault(a, b2)
        full = list(seq)
        while parent.get(full[-1], -1) >= 0:          # down the existing tree to the tail
            full.append(parent[full[-1]])
        via_cells.add(e)
        paths[n] = [(X[xx[q]], Y[yy[q]]) for q in full]
        full_idx[n] = full
        load[yy[full], xx[full]] += 1
    relocated = _relocate_vias(names, full_idx, paths, load, lab, free, idx, X, Y, xx, yy, res, sense, side, band) \
        if relocate else {}
    # bundle corridors at their true width; how much each region gives up to them
    disks = []
    for n, pts in paths.items():
        if not pts:
            continue
        for p in pts[::3]:
            i, j = round((p[1] - Y[0]) / res), round((p[0] - X[0]) / res)
            disks.append(Point(p).buffer(load[i, j] * FAB["pitch"] / 2 + FAB["route_clear"], 8))
    for n, pts in paths.items():                     # room for each via beside its bundle
        if pts:
            disks.append(Point(pts[0]).buffer(0.45 / 2 + 0.15 + FAB["pitch"] + FAB["route_clear"], 16))
    # room at the root, where every bundle merges and turns into the tail: the lanes turn on fillets that cut
    # inside the coarse path, so a region carved only along the path can poke into the turn (the personalised
    # foot, whose trunk meets the tail at an angle)
    n_routed = sum(1 for p in paths.values() if p)
    disks.append(Point(tail_start).buffer(n_routed * FAB["pitch"] / 2 + FAB["route_clear"] + 2.0, 32))
    carve = unary_union(disks) if disks else Polygon()
    # capacity: the corridor must stay inside the usable sole wherever it runs
    usable = sole.buffer(-FAB["edge_margin"] + FAB["route_clear"])
    spill = carve.difference(usable).area
    worst = {"corridor_outside_sole_mm2": round(spill, 1), "vias_moved_clear_of_bundles": relocated,
             "vias_without_clear_cell": via_fallback}
    return paths, load, worst, carve, (X, Y, res), side


# ------------------------------------------------------------------------------------------------ build
def build(s, names, mode, exit, side="R"):
    sole, toes, centers, web_x = outline(s)
    s["_centers"] = centers
    regs, sd = regions(sole, toes, web_x, s, names, mode)
    # names whose toe tab is off or too narrow are dropped with a reason
    dropped = {}
    for n in list(regs):
        r = regs[n]
        if r is None or r.is_empty:
            dropped[n] = "no room (toe tab off or region empty)"; regs.pop(n); continue
        if n.startswith("toe"):
            w = float(np.ptp(np.asarray(r.minimum_rotated_rectangle.exterior.coords)[:, 1]))
            if w < FAB["min_toe_region"]:
                dropped[n] = f"toe region {w:.1f} mm wide < {FAB['min_toe_region']} mm"; regs.pop(n)
    n_lines = len(regs) + 2                          # one signal per region + common + spare
    tail, tail_start, tail_exit, tail_w, (tail_end, tail_dir) = tail_geometry(sole, s, n_lines, exit)
    m1, m5 = np.array(sd["mt1"]), np.array(sd["mt5"])          # metatarsophalangeal bend line: through the
    t = (m1 - m5) / np.linalg.norm(m1 - m5); nrm = np.array([t[1], -t[0]])   # MT heads, 8 mm distal
    if nrm[0] < 0:
        nrm = -nrm
    bend_pt = m5 + nrm * 8.0
    split = {n: float(np.dot(np.asarray(r.centroid.coords[0]), t)) for n, r in regs.items()}
    paths, load, spill, carve, _grid, sense_side = route(sole, regs, tail_start, sense={n: (t, split[n]) for n in regs},
                                             band=(bend_pt, nrm, FAB["bend_band"]))
    # final regions: the gap between neighbours, then room for the bundles; keep the largest piece
    before = {n: r.area for n, r in regs.items()}
    regs = {n: r.buffer(-FAB["region_gap"] / 2) for n, r in regs.items()}
    if not carve.is_empty:
        regs = {n: r.difference(carve) for n, r in regs.items()}
    for n, r in list(regs.items()):
        if isinstance(r, MultiPolygon):
            regs[n] = max(r.geoms, key=lambda g: g.area)
    # Fillets where the tail meets the sole. A sharp inside corner in a flex outline is where it starts to
    # tear, and the copper-free margin along both edges of a sharp corner left a bundle arriving at an angle no
    # room to turn into the tail (the personalised foot). The fillet adds outline, so the margin follows it.
    plate0 = sole.union(tail)
    flare = plate0.buffer(TAIL_FILLET, 32).buffer(-TAIL_FILLET, 32).difference(plate0) \
        .intersection(Point(tail_exit).buffer(tail_w / 2 + TAIL_FILLET + 1.0, 32))
    # keep the two fillets only: closing also leaves hair-thin slivers along the curved edge, which made the
    # exported outline self-intersect once rounded (KiCad: invalid_outline)
    flare = unary_union([g for g in getattr(flare, "geoms", [flare]) if g.geom_type == "Polygon" and g.area > 0.5])
    body = sole.union(flare).buffer(0.02).buffer(-0.02)      # the sole including the fillets: routing, margin
    plate = plate0.union(flare).buffer(0.02).buffer(-0.02)
    if plate.geom_type != "Polygon" or not plate.is_valid:
        raise RuntimeError("board outline is not a single valid polygon")
    # checks
    vias = {n: pts[0] for n, pts in paths.items() if pts}
    in_bend = [n for n, v in vias.items() if abs(np.dot(np.array(v) - bend_pt, nrm)) < FAB["bend_band"]]
    cover = sum(r.area for r in regs.values()) / sole.area
    kept = {n: r.area / before[n] for n, r in regs.items() if before.get(n)}
    unrouted = [n for n, p in paths.items() if not p]
    checks = dict(
        regions=len(regs), dropped=dropped, unrouted=unrouted,
        coverage_pct=round(100 * cover, 1),
        max_bundle=int(load.max()),
        corridor_outside_sole_mm2=spill["corridor_outside_sole_mm2"],
        vias_moved_clear_of_bundles_mm=spill.get("vias_moved_clear_of_bundles", {}),
        vias_without_clear_cell=spill.get("vias_without_clear_cell", []),
        smallest_region=min(((n, round(r.area)) for n, r in regs.items()), key=lambda x: x[1]),
        least_area_kept=min(((n, round(100 * v)) for n, v in kept.items()), key=lambda x: x[1]),
        vias_in_bend_zone=in_bend,
        tail_width_mm=round(tail_w, 1), connector_pins=n_lines,
        regions_inside=all(sole.buffer(-FAB["edge_margin"] + 0.05).contains(r) for r in regs.values()),
        min_region_gap_mm=round(min((a.distance(b) for i, a in enumerate(regs.values()) for b in list(regs.values())[i + 1:]), default=0), 2),
    )
    copper = {n: combs(r, t, split=split[n], flip=sense_side.get(n, 1) < 0) for n, r in regs.items()} \
        if mode == "region" else {}
    if copper:
        checks["comb_connected"] = all(getattr(a, 'geom_type', '') == 'Polygon' and getattr(b, 'geom_type', '') == 'Polygon'
                                         for a, b in copper.values())
        checks["comb_min_spacing_mm"] = round(min(a.distance(b) for a, b in copper.values()), 3)
        fill = {n: (a.area + b.area) / regs[n].area for n, (a, b) in copper.items()}
        checks["comb_copper_fill_pct"] = [round(100 * min(fill.values())), round(100 * max(fill.values()))]
        # sensing area: where both combs interleave. Copper of one comb alone (fingers cut off from their partner
        # by a line through the region) does not sense, so this is what a region really keeps of its tile.
        act = {n: active_area(a, b, regs[n]) for n, (a, b) in copper.items()}
        checks["sensing_area"] = {n: dict(tile_mm2=round(before[n]), active_mm2=round(act[n]),
                                          pct_of_tile=round(100 * act[n] / before[n])) for n in copper}
        checks["least_sensing_area"] = min(((n, v["pct_of_tile"]) for n, v in checks["sensing_area"].items()),
                                           key=lambda x: x[1])
    routing = route_copper(body, tail, regs, copper, paths, sd, tail_start, tail_end, tail_dir, n_lines, checks) \
        if copper else None
    if routing:                                       # copper on both layers inside the toe-joint bend zone
        C = CONTACT; ext = 400.0                      # stiffens the flex where it bends (the "I-beam" effect)
        bandp = Polygon([bend_pt - t * ext - nrm * FAB["bend_band"], bend_pt + t * ext - nrm * FAB["bend_band"],
                         bend_pt + t * ext + nrm * FAB["bend_band"], bend_pt - t * ext + nrm * FAB["bend_band"]])
        ls = lambda pts, w: LineString(pts).buffer(w / 2) if len(pts) > 1 else Polygon()
        bcu = unary_union([ls(v, C["sense_w"]) for v in routing["lanes"].values()] +
                          [ls(v, C["sense_w"]) for _, v in routing["lanes_extra"]] +
                          [ls(v, C["com_w"]) for v in routing["com_pin_stubs"]])
        fcu = unary_union([ls(v, C["com_w"]) for v in routing["com"]] + [ls(v, C["sense_w"]) for v in routing["stubs"].values()]
                          + [ls(j["fcu"], C["sense_w"]) for j in routing["jumpers"]])
        checks["routing"]["stacked_copper_in_bend_mm2"] = round(bcu.intersection(fcu).intersection(bandp).area, 2)
        margin_zone = body.difference(body.buffer(-FAB["edge_margin"])).difference(tail)
        checks["routing"]["copper_in_edge_margin_mm2"] = round(bcu.union(fcu).intersection(margin_zone).area, 2)
        checks["regions_in_bend_pct"] = {n: round(100 * r.intersection(bandp).area / r.area) for n, r in regs.items()
                                         if r.intersects(bandp)}
    geo = dict(sole=sole, body=body, tail=tail, plate=plate, regions=regs, seeds=sd, paths=paths, toes=toes, web_x=web_x,
               bend=(bend_pt, t), tail_exit=tail_exit, copper=copper, routing=routing,
               tail_info=dict(end=tail_end, dir=tail_dir, width=tail_w, lines=n_lines))
    if side == "L":                                   # mirror: z -> -z
        m = lambda g: affinity.scale(g, 1, -1, origin=(0, 0))
        geo = dict(geo, mirrored=True, sole=m(sole), body=m(body), tail=m(tail), plate=m(plate), regions={k: m(v) for k, v in regs.items()},
                   copper={k: (m(a), m(b)) for k, (a, b) in copper.items()},
                   tail_info=dict(end=(tail_end[0], -tail_end[1]), dir=(tail_dir[0], -tail_dir[1]), width=tail_w,
                                  lines=n_lines),
                   bend=((bend_pt[0], -bend_pt[1]), np.array([t[0], -t[1]])),
                   seeds={k: (v[0], -v[1]) for k, v in sd.items()},
                   paths={k: [(p[0], -p[1]) for p in v] if v else v for k, v in paths.items()},
                   tail_exit=(tail_exit[0], -tail_exit[1]),
                   routing=_mirror_routing(routing))
    return geo, checks


TAIL_FILLET = 5.0                                    # mm, fillet radius where the tail meets the sole
CONTACT = dict(pad_len=4.0, pad_w=0.30, edge_gap=0.5, sense_w=0.12, com_w=0.20, via_d=0.45, via_drill=0.20, clear=0.15)


def route_copper(sole, tail, regs, copper, paths, seeds, tail_start, tail_end, tail_dir, n_pins, checks):
    """Real copper: sense lanes on B.Cu, stubs and the common net on F.Cu, vias, contact pads (sole_route.py)."""
    import sys
    here = str(Path(__file__).resolve().parent)
    if here not in sys.path:                                  # also under `python -I`
        sys.path.insert(0, here)
    from sole_route import build_lanes, crossings, maze_refine, odd_crossings, route_common, stubs_to_combs
    C = CONTACT
    plan = lambda flips: build_lanes({n: paths[n] for n in regs if paths.get(n)}, 0.25, tail_start, tail_dir,
                                     tail_end, seeds, FAB["pitch"], FAB["ffc_pitch"], C["pad_len"], C["edge_gap"],
                                     n_pins, track_w=C["sense_w"], via_d=C["via_d"], clear=C["clear"],
                                     regions=regs, flips=flips)
    # planarity search: a line ending where its bundle continues may sit on either side of it; flip sides
    # while that reduces the pairs that cross an odd number of times (crossings no router can remove)
    flips = set()
    lan = plan(flips); odd = odd_crossings(lan["lanes"])
    for _ in range(12):
        if not odd:
            break
        best = None
        for n in sorted({x for pair in odd for x in pair}):
            f2 = flips ^ {n}
            l2 = plan(f2); o2 = odd_crossings(l2["lanes"])
            if len(o2) < len(odd) and (best is None or len(o2) < len(best[2])):
                best = (f2, l2, o2)
        if best is None:
            break
        flips, lan, odd = best
    # copper stays out of the sole's copper-free margin (as regions, the routing plan and the common net do);
    # 0.3 mm to the edge applies only in the tail. Allowing the margin let the fine-grid pass take shortcuts
    # along the outline that bypass the planned lane order, so lines crossed (the personalised foot).
    allowed = sole.buffer(-FAB["edge_margin"]).union(tail.buffer(-0.3))
    keepout = unary_union(list(regs.values()))                        # no B.Cu under the sensing regions
    order = lan["pin_order"][1:-1]
    planned = lan["lanes"]
    tdv = np.asarray(tail_dir, float); acv = np.asarray(lan["across"])
    fs = np.asarray(tail_end, float) - tdv * (C["edge_gap"] + C["pad_len"] + 3.0)     # fan start line
    contact_zone = Polygon([fs - acv * 20 + tdv * 0.05, fs + acv * 20 + tdv * 0.05,
                            fs + acv * 20 + tdv * 30, fs - acv * 20 + tdv * 30])
    lanes, maze_failed = maze_refine(planned, lan["vias"], order, allowed, keepout,
                                     track_w=C["sense_w"], clear=C["clear"], via_d=C["via_d"],
                                     no_go=contact_zone)
    # a crossing forced by where two vias sit: one line hops over the other on F.Cu (two vias, one jumper)
    jumpers, extra, no_region_via = [], [], set()
    for n, m in crossings(lanes):
        jumped = {j["net"] for j in jumpers}
        if m in jumped and n not in jumped:              # a line crossed twice: let the other one hop
            n, m = m, n
        if m in jumped or len(lanes[m]) < 4 or len(lanes[n]) < 4:
            continue                                     # left for the B.Cu crossing check below
        A, B = LineString(lanes[n][:-2]), LineString(lanes[m][:-2])
        c = A.intersection(B)
        pts_c = [g for g in getattr(c, "geoms", [c]) if g.geom_type == "Point" and not g.is_empty]
        if not pts_c:                                    # no longer crossing here
            continue
        c = pts_c[0]
        L = B.length; sc = B.project(c)
        need = C["via_d"] / 2 + C["clear"] + C["sense_w"] / 2       # via to any other line
        need_v = C["via_d"] + C["clear"]                               # via to any other via
        others = unary_union([LineString(lanes[k][:-2]) for k in lanes if k != m and len(lanes[k]) > 3] +
                             [LineString(v) for k, v in extra if k != m and len(v) > 1])
        placed = [np.asarray(v) for k, v in lan["vias"].items() if k != m] + \
                 [np.asarray(v) for j in jumpers for v in j["vias"]]
        ok_via = lambda p: others.distance(p) >= need and all(np.linalg.norm(q - (p.x, p.y)) >= need_v
                                                              for q in placed)
        start_jump = sc < C["via_d"] + C["clear"] + 0.8              # crossing right at its own via
        for d in np.arange(0.8, 4.01, 0.1):
            s1 = 0.0 if start_jump else max(0.05, sc - d)
            s2 = min(L - 0.05, sc + d)
            p1, p2 = B.interpolate(s1), B.interpolate(s2)
            if (start_jump or ok_via(p1)) and ok_via(p2):
                break
        from shapely.ops import substring as _sub
        tail_ = _sub(B, s2, L)
        if start_jump:                                   # the jumper starts on F.Cu right at the comb stub:
            lanes[m] = [lanes[m][0]]                     # the region via is not needed
            jvias = [(p2.x, p2.y)]
            no_region_via.add(m)
        else:
            lanes[m] = list(_sub(B, 0, s1).coords)
            jvias = [(p1.x, p1.y), (p2.x, p2.y)]
        extra.append((m, list(tail_.coords) + list(lanes_full_end(planned, m))))
        jumpers.append(dict(net=m, over=n, fcu=[(p1.x, p1.y), (p2.x, p2.y)], vias=jvias))
    lan["lanes"] = lanes
    # whatever still crosses on B.Cu (a line crossed by two others, a jumper tail crossing again) is reported;
    # the board would short there, and DRC flags it too
    bcu = [(k, LineString(v)) for k, v in lanes.items() if len(v) > 1] + [(k, LineString(v)) for k, v in extra if len(v) > 1]
    still = sorted({tuple(sorted((a, b))) for i, (a, la) in enumerate(bcu) for b, lb in bcu[i + 1:]
                    if a != b and la.intersects(lb)})
    common = {n: copper[n][0] for n in copper}; sense = {n: copper[n][1] for n in copper}
    stubs, near_common = stubs_to_combs(lan["vias"], sense, common, C["sense_w"], C["clear"])
    td, pm, ac = np.asarray(tail_dir, float), np.asarray(lan["pad_mid"]), np.asarray(lan["across"])
    half = (n_pins - 1) / 2 * FAB["ffc_pitch"]
    pads = [(k + 1, tuple(pm + ac * ((k - (n_pins - 1) / 2) * FAB["ffc_pitch"]))) for k in range(n_pins)]
    lvl = pm - td * (C["pad_len"] / 2 + 0.8)                   # common vias just above the contacts
    v1, vN = lvl - ac * (half + 0.35), lvl + ac * (half + 0.35)
    ts = np.asarray(tail_start, float)
    com_tail = [[tuple(ts), tuple(lvl)], [tuple(lvl), tuple(v1)], [tuple(lvl), tuple(vN)]]
    obstacles = [Point(v).buffer(C["via_d"] / 2, 16) for j in jumpers for v in j["vias"]] + \
                [LineString(j["fcu"]).buffer(C["sense_w"] / 2) for j in jumpers] + \
                [Point(v).buffer(C["via_d"] / 2, 16) for v in lan["vias"].values()] + \
                [LineString(st).buffer(C["sense_w"] / 2) for st in stubs.values() if LineString(st).length > 0]
    com_lines, unreached, start_xy = route_common(sole.buffer(-FAB["edge_margin"]), sense.values(), common,
                                                  obstacles, tuple(ts), C["com_w"], C["clear"])
    com_tail[0][0] = start_xy                                   # the tail run starts where the tree starts
    checks["routing"] = dict(
        sense_routed=len(lan["lanes"]) - len(maze_failed), maze_failed=maze_failed,
        negotiation_rounds=getattr(maze_refine, "rounds_used", None),
        jumpers=[(j["net"], j["over"]) for j in jumpers], unresolved_crossings=[list(x) for x in still],
        side_flips=sorted(flips),
        planned_odd_crossings=odd,
        common_unreached=unreached, stubs_near_common=near_common,
        longest_stub_mm=round(max((LineString(v).length for v in stubs.values()), default=0), 2),
        vias=len(lan["vias"]) + 2 + sum(len(j["vias"]) for j in jumpers))
    return dict(lanes=lan["lanes"], vias={k: v for k, v in lan["vias"].items() if k not in no_region_via},
                stubs=stubs, com=com_lines + com_tail,
                com_vias=[tuple(v1), tuple(vN)], com_pin_stubs=[[tuple(v1), pads[0][1]], [tuple(vN), pads[-1][1]]],
                pin_order=lan["pin_order"], pads=pads, lanes_extra=extra, jumpers=jumpers)


def lanes_full_end(planned, n):
    """The fixed fan-out and contact of a planned lane (its last two points)."""
    return planned[n][-2:]


def _mirror_routing(r):
    if not r:
        return r
    mp = lambda p: (p[0], -p[1])
    ml = lambda pts: [mp(p) for p in pts]
    return dict(r, lanes={k: ml(v) for k, v in r["lanes"].items()}, vias={k: mp(v) for k, v in r["vias"].items()},
                stubs={k: ml(v) for k, v in r["stubs"].items()}, com=[ml(v) for v in r["com"]],
                com_vias=ml(r["com_vias"]), com_pin_stubs=[ml(v) for v in r["com_pin_stubs"]],
                pads=[(k, mp(p)) for k, p in r["pads"]],
                lanes_extra=[(n, ml(v)) for n, v in r.get("lanes_extra", [])],
                jumpers=[dict(j, fcu=ml(j["fcu"]), vias=ml(j["vias"])) for j in r.get("jumpers", [])])


# ------------------------------------------------------------------------------------------------ copper
def combs(region, bend_dir, finger=None, gap=None, spine=0.3, split=None, flip=False):
    """Two interleaved electrode combs filling a region (shunt-mode force-sensing resistor).

    Fingers run parallel to the bend line (`bend_dir`), so bending at the toe joints strains them least.
    Returns (common, sense): common fingers join the spine on the low side of `split` (along `bend_dir`),
    sense fingers the spine on the high side; `flip` swaps the sides (the routing chose the low side).
    A piezoresistive film over the region bridges the two combs; its conductance rises with load.
    """
    finger = finger or FAB["comb_finger"]; gap = gap or FAB["comb_gap"]
    ang = math.degrees(math.atan2(bend_dir[1], bend_dir[0]))
    R = affinity.rotate(region, -ang, origin=(0, 0))           # fingers along the local x axis
    if R.is_empty or R.area < 4:
        return Polygon(), Polygon()
    minx, miny, maxx, maxy = R.bounds
    band = R.difference(R.buffer(-(spine + gap)))                # outer band holds the two spines
    # spines on opposite ends of the fingers (low x / high x halves of the band)
    xc = R.centroid.x if split is None else split    # the routing put each via on the sense side
    spA = band.intersection(box(minx - 1, miny - 1, xc - gap / 2, maxy + 1))
    spB = band.intersection(box(xc + gap / 2, miny - 1, maxx + 1, maxy + 1))
    core = R.buffer(-(spine + gap))
    fa, fb = [], []
    y, k = miny, 0
    while y < maxy:
        strip = box(minx - 1, y, maxx + 1, y + finger)
        if k % 2 == 0:
            fa.append(strip.intersection(R).difference(spB.buffer(gap)).intersection(core.union(spA)))
        else:
            fb.append(strip.intersection(R).difference(spA.buffer(gap)).intersection(core.union(spB)))
        y += finger + gap; k += 1
    A = unary_union([spA] + fa); B = unary_union([spB] + fb)
    # fingers that cannot reach their spine (sloping or concave corners) would float: keep the connected comb
    big = lambda g: max(g.geoms, key=lambda q: q.area) if g.geom_type == "MultiPolygon" else g
    # trim copper slivers: anything narrower than 0.1 mm (acute finger tips at slanted borders) cannot be
    # etched reliably and may lift off a flexing sole
    trim = lambda g: big(big(g).buffer(-0.05, 16).buffer(0.05, 16))
    back = lambda g: affinity.rotate(g, ang, origin=(0, 0))
    A, B = back(trim(A)), back(trim(B))
    return (B, A) if flip else (A, B)


def active_area(common, sense, region, reach=None):
    """Area (mm²) where the two combs interleave: within one finger pitch of both. A film patch there sees
    both electrodes; elsewhere it touches one comb or none and adds nothing to the reading."""
    reach = reach or (FAB["comb_finger"] + FAB["comb_gap"] + 0.05)
    if common.is_empty or sense.is_empty:
        return 0.0
    return common.buffer(reach, 4).intersection(sense.buffer(reach, 4)).intersection(region).area


# ------------------------------------------------------------------------------------------------ export
COL = dict(sole="#1f2937", tail="#6b7280", region="#2f6f8f", route="#c2410c", seed="#111827", bend="#a16207")


def _poly_paths(g):
    gs = [g] if g.geom_type == "Polygon" else list(getattr(g, "geoms", []))
    out = []
    for p in gs:
        for ring in [p.exterior] + list(p.interiors):
            c = np.asarray(ring.coords)
            out.append("M" + " L".join(f"{x:.2f},{-y:.2f}" for x, y in c) + " Z")
    return " ".join(out)


def to_svg(geo, path, title):
    minx, miny, maxx, maxy = geo["plate"].bounds
    pad = 6
    vb = f"{minx - pad:.1f} {-maxy - pad:.1f} {maxx - minx + 2 * pad:.1f} {maxy - miny + 2 * pad + 8:.1f}"
    el = [f'<path d="{_poly_paths(geo["plate"])}" fill="#f3f4f6" stroke="{COL["sole"]}" stroke-width="0.3"/>']
    for n, r in geo["regions"].items():
        el.append(f'<path d="{_poly_paths(r)}" fill="{COL["region"]}" fill-opacity="0.35" stroke="{COL["region"]}" stroke-width="0.2"><title>{n}</title></path>')
    for n, pts in geo["paths"].items():
        if pts:
            el.append('<polyline points="' + " ".join(f"{x:.2f},{-y:.2f}" for x, y in pts[::2]) +
                      f'" fill="none" stroke="{COL["route"]}" stroke-width="0.25" stroke-opacity="0.8"/>')
    for n, (x, z) in geo["seeds"].items():
        if n in geo["regions"]:
            el.append(f'<text x="{x:.1f}" y="{-z + 1:.1f}" font-size="3" text-anchor="middle" font-family="sans-serif" fill="{COL["seed"]}">{n}</text>')
    el.append(f'<text x="{minx:.1f}" y="{-miny + pad + 4:.1f}" font-size="4" font-family="sans-serif">{title}</text>')
    path.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}" width="{(maxx - minx + 2 * pad):.0f}mm" '
                    f'height="{(maxy - miny + 2 * pad + 8):.0f}mm">' + "".join(el) + "</svg>")


def to_dxf(geo, path):
    import ezdxf
    doc = ezdxf.new(); msp = doc.modelspace()
    for layer in ("Edge.Cuts", "F.Cu.regions", "F.Cu.common", "F.Cu.sense", "Routing.plan", "Seeds"):
        doc.layers.add(layer)
    def add(g, layer):
        gs = [g] if g.geom_type == "Polygon" else list(getattr(g, "geoms", []))
        for p in gs:
            for ring in [p.exterior] + list(p.interiors):
                msp.add_lwpolyline(list(ring.coords), close=True, dxfattribs={"layer": layer})
    add(geo["plate"], "Edge.Cuts")
    for r in geo["regions"].values():
        add(r, "F.Cu.regions")
    for a, b in geo.get("copper", {}).values():
        add(a, "F.Cu.common"); add(b, "F.Cu.sense")
    for pts in geo["paths"].values():
        if pts:
            msp.add_lwpolyline(pts[::2], dxfattribs={"layer": "Routing.plan"})
    for n, (x, z) in geo["seeds"].items():
        if n in geo["regions"]:
            msp.add_text(n, dxfattribs={"layer": "Seeds", "height": 2}).set_placement((x, z))
    doc.saveas(path)


def to_json(geo, checks, s, args, path):
    poly = lambda g: [list(map(lambda c: [round(c[0], 2), round(c[1], 2)], np.asarray(p.exterior.coords)))
                      for p in ([g] if g.geom_type == "Polygon" else list(g.geoms))]
    out = dict(
        generator="sole_gen v0", frame="foot frame: x heel->2nd toe, z rightward; mm",
        side=args.side, mode=args.mode, tail_exit=args.exit,
        foot={k: v for k, v in s.items() if not k.startswith("_")},
        fab=FAB, checks=checks,
        regions={n: dict(seed=[round(v, 2) for v in geo["seeds"][n]], area_mm2=round(r.area, 1), polygon=poly(r))
                 for n, r in geo["regions"].items()},
        outline=poly(geo["plate"]),
        routing_plan={n: [[round(x, 2), round(y, 2)] for x, y in pts[::2]] for n, pts in geo["paths"].items() if pts},
    )
    path.write_text(json.dumps(out, indent=1))


def to_png(geo, checks, path, title):
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(11, 5.2))
    def fill(g, **kw):
        for p in ([g] if g.geom_type == "Polygon" else list(getattr(g, "geoms", []))):
            ax.fill(*p.exterior.xy, **kw)
    fill(geo["plate"], fc="#f3f4f6", ec=COL["sole"], lw=0.8)
    for n, r in geo["regions"].items():
        fill(r, fc=COL["region"], alpha=0.45, ec=COL["region"], lw=0.5)
        x, z = geo["seeds"][n]; ax.text(x, z, n, fontsize=6, ha="center", va="center")
    for pts in geo["paths"].values():
        if pts:
            a = np.asarray(pts); ax.plot(a[:, 0], a[:, 1], color=COL["route"], lw=0.6, alpha=0.8)
    bp, bt = np.asarray(geo["bend"][0]), np.asarray(geo["bend"][1])
    seg = np.array([bp - bt * 45, bp + bt * 45])
    ax.plot(seg[:, 0], seg[:, 1], color=COL["bend"], ls=":", lw=0.9)
    ax.set_aspect("equal"); ax.set_title(title, fontsize=9)
    ax.text(0.01, 0.01, ", ".join(f"{k}={v}" for k, v in checks.items() if k in
            ("regions", "coverage_pct", "max_bundle", "least_area_kept", "tail_width_mm", "vias_in_bend_zone")),
            transform=ax.transAxes, fontsize=7)
    fig.tight_layout(); fig.savefig(path, dpi=110); plt.close(fig)


def fracture(poly):
    """Split a polygon with holes into hole-free pieces (KiCad custom pads need hole-free outlines).
    Each split runs through a hole, so no copper is lost; the pieces touch and stay one net."""
    from shapely.ops import split
    if poly.is_empty:
        return []
    if not poly.interiors:
        return [poly]
    x = Polygon(poly.interiors[0]).representative_point().x
    minx, miny, maxx, maxy = poly.bounds
    out = []
    for part in split(poly, LineString([(x, miny - 1), (x, maxy + 1)])).geoms:
        if part.geom_type == "Polygon" and part.area > 1e-4:
            out += fracture(part)
    return out


def pad_pieces(poly, overlap=0.02):
    """Hole-free pieces that overlap by `overlap` mm, so KiCad sees one connected copper shape."""
    out = []
    for p in fracture(poly):
        q = p.buffer(overlap, 8).intersection(poly)          # overlap only inside the comb: spacing unchanged
        for g in ([q] if q.geom_type == "Polygon" else list(getattr(q, "geoms", []))):
            if g.geom_type == "Polygon" and not g.interiors and g.area > 1e-4:
                out.append(g)
            elif g.geom_type == "Polygon":
                out += fracture(g)
    return out


def _source_at_start():
    """Hashes of the generator files and the git state, taken when the generator starts: a run takes minutes,
    and a file edited meanwhile must not end up in the stamp of a board it did not make."""
    here = Path(__file__).resolve().parent
    h = lambda f: hashlib.sha256(Path(f).read_bytes()).hexdigest()[:12]
    files = {f: h(here / f) for f in ("sole_gen.py", "sole_route.py")}
    git = lambda *a: subprocess.run(["git", "-C", str(here), *a], capture_output=True, text=True, timeout=20).stdout.strip()
    try:
        rev = git("rev-parse", "--short=12", "HEAD") or None
        dirty = bool(git("status", "--porcelain", "--", "sole_gen.py", "sole_route.py"))
    except Exception:
        rev, dirty = None, None
    import platform
    from importlib import metadata
    tools = {"python": platform.python_version()}
    for pkg in ("numpy", "scipy", "shapely", "matplotlib", "ezdxf"):
        try:
            tools[pkg] = metadata.version(pkg)
        except metadata.PackageNotFoundError:
            tools[pkg] = None
    return files, rev, dirty, tools


_SOURCE = _source_at_start()


def source_stamp(args):
    """What produced a board: hashes of the generator files and the foot file, the git revision, the options.
    The KiCad exporter copies it into the title block, and verify_board.py checks it against the files."""
    files, rev, dirty, tools = _SOURCE
    foot = {"path": Path(args.foot).name, "sha256": hashlib.sha256(Path(args.foot).read_bytes()).hexdigest()} \
        if args.foot else None
    return dict(files=files, git=rev, generator_files_modified=dirty, foot=foot, tools=tools,
                options=dict(size=args.size, length=args.length, width=args.width, side=args.side, exit=args.exit,
                             mode=args.mode))


def to_board_json(geo, s, args, path, requested=None, checks=None):
    """Everything the KiCad exporter needs, in the foot frame (mm)."""
    ring = lambda r: [[round(x, 4), round(y, 4)] for x, y in np.asarray(r.coords)[:-1]]
    regions = {}
    # a fixed region order (heel to toes, as in DEFAULT_SENSORS), so footprint references S01..S16 name the same
    # regions on every run; dict order inside the generator can vary with Python's string hashing
    rank = {n: i for i, n in enumerate(DEFAULT_SENSORS)}
    # Coverlay: one opening per region, notched where an F.Cu track (common line, sense stub, jumper) lands on a
    # comb or passes closer than the rule, so the joint stays covered and every track keeps 0.16 mm from the
    # opening (published flex rule: coverlay opening to trace >= 0.15 mm; DRC checks 0.15 mm). A wider margin
    # would also trim the comb's spine wherever a common line runs along a region's edge.
    R_ = geo.get("routing") or {}
    fcu = [(pts, CONTACT["com_w"]) for pts in R_.get("com", [])] + \
          [(pts, CONTACT["sense_w"]) for pts in R_.get("stubs", {}).values()] + \
          [(j["fcu"], CONTACT["sense_w"]) for j in R_.get("jumpers", [])]
    notch = unary_union([LineString(p).buffer(w / 2 + 0.16, 8) for p, w in fcu if len(p) > 1]) if fcu else Polygon()

    def opening(r):
        o = r.difference(notch) if not notch.is_empty else r
        return max(o.geoms, key=lambda g: g.area) if o.geom_type == "MultiPolygon" else o
    for n, r in sorted(geo["regions"].items(), key=lambda kv: (rank.get(kv[0], len(rank)), kv[0])):
        common, sense = geo["copper"].get(n, (Polygon(), Polygon()))
        via = geo["paths"].get(n)
        regions[n] = dict(
            outline=ring(r.exterior),
            opening=ring(opening(r).exterior),
            common=[dict(pts=ring(p.exterior), anchor=list(p.representative_point().coords[0])) for p in pad_pieces(common)],
            sense=[dict(pts=ring(p.exterior), anchor=list(p.representative_point().coords[0])) for p in pad_pieces(sense)],
            via_hint=[round(v, 3) for v in via[0]] if via else None)
    bp, bt = geo["bend"]
    bp, bt = np.asarray(bp, float), np.asarray(bt, float)
    nrm = np.array([bt[1], -bt[0]]); hw = FAB["bend_band"]; ext = 400.0
    band = Polygon([bp - bt * ext - nrm * hw, bp + bt * ext - nrm * hw, bp + bt * ext + nrm * hw, bp - bt * ext + nrm * hw])
    band = band.intersection(geo["sole"].buffer(1.0))
    band = max(band.geoms, key=lambda g: g.area) if band.geom_type == "MultiPolygon" else band
    # the configuration the board was built for: verify_board.py checks the board against it (a personal sole
    # can have fewer regions than the default 16)
    config = dict(sensors_requested=list(requested or []), regions_built=list(regions),
                  dropped=dict((checks or {}).get("dropped", {})), n_contacts=len(regions) + 2)
    outline_ring = ring(geo["plate"].exterior)
    if not Polygon(outline_ring).is_valid:                    # as KiCad will read it, after rounding
        from shapely.validation import explain_validity
        raise RuntimeError(f"exported outline is invalid: {explain_validity(Polygon(outline_ring))}")
    # copper-free margin as keep-out polygons (hole-free pieces), so KiCad's DRC itself flags copper in it
    margin = geo["plate"].difference(geo["body"].buffer(-FAB["edge_margin"]).union(geo["tail"]))
    margin_parts = [g for g in getattr(margin, "geoms", [margin]) if g.geom_type == "Polygon" and g.area > 1e-3]
    margin_keepout = [ring(p.exterior) for g in margin_parts for p in fracture(g)]
    out = dict(generator="sole_gen v0", source=source_stamp(args), config=config, side=args.side, foot_length=s["L"], ball_width=s["W"],
               outline=outline_ring, margin_keepout=margin_keepout, fab=FAB, regions=regions,
               bend=dict(point=[float(bp[0]), float(bp[1])], dir=[float(bt[0]), float(bt[1])], half_width=FAB["bend_band"],
                         band=ring(band.exterior)),
               tail=dict(end=list(geo["tail_info"]["end"]), dir=list(geo["tail_info"]["dir"]),
                         width=geo["tail_info"]["width"], lines=geo["tail_info"]["lines"]),
               routing_plan={n: [[round(x, 3), round(y, 3)] for x, y in pts[::2]] for n, pts in geo["paths"].items() if pts},
               contact=CONTACT, copper_routing=geo.get("routing"))
    # Identity. The design hash covers everything that defines the copper and the channel map (outline,
    # regions, combs, routing, pin order, configuration, side, rules) and nothing about how or when it was
    # made. Two different designs never share it; regenerating the same design gives the same hash, so the
    # printed ID resolves to exactly one map. The label in front is for people only.
    design = {k: v for k, v in out.items() if k not in ("generator", "source")}
    dh = hashlib.sha256(json.dumps(design, sort_keys=True, separators=(",", ":"), default=float).encode()).hexdigest()
    src = out["source"]
    if src.get("foot"):
        label = "F" + src["foot"]["sha256"][:6]
    elif args.length:
        label = f"L{args.length:.0f}" + (f"W{args.width:.0f}" if args.width else "")
    else:
        label = f"EU{args.size:g}"
    out["design_hash"] = dh
    out["board_id"] = f"{label} {args.side} {dh[:10]}"
    path.write_text(json.dumps(out))


def to_png_zoom(geo, path, name="mt2", half=9.0):
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    if name not in geo.get("copper", {}):
        return
    a, b = geo["copper"][name]; c = geo["regions"][name].centroid
    fig, ax = plt.subplots(figsize=(6, 6))
    for g, col in ((a, "#2f6f8f"), (b, "#c2410c")):
        for p in ([g] if g.geom_type == "Polygon" else list(g.geoms)):
            ax.fill(*p.exterior.xy, fc=col, ec="none")
            for h in p.interiors:
                ax.fill(*h.xy, fc="white", ec="none")
    ax.set_xlim(c.x - half, c.x + half); ax.set_ylim(c.y - half, c.y + half); ax.set_aspect("equal")
    ax.set_title(f"{name}: common comb (blue) and sense comb (orange), finger/gap {FAB['comb_finger']}/{FAB['comb_gap']} mm", fontsize=8)
    fig.tight_layout(); fig.savefig(path, dpi=120); plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--size", type=float, default=42, help="EU size (used when --length is not given)")
    ap.add_argument("--length", type=float, help="measured foot length, mm")
    ap.add_argument("--width", type=float, help="measured ball width, mm")
    ap.add_argument("--foot", help="JSON with landmark overrides and sensor choices (from a scan)")
    ap.add_argument("--side", choices=("R", "L"), default="R")
    ap.add_argument("--mode", choices=("region", "point"), default="region")
    ap.add_argument("--exit", choices=("arch", "heel"), default="arch")
    ap.add_argument("--out", required=True)
    ap.add_argument("--name", default=None)
    a = ap.parse_args()
    over, names = {}, list(DEFAULT_SENSORS)
    if a.foot:
        cfg = json.loads(Path(a.foot).read_text())
        over = cfg.get("landmarks", {})
        names = cfg.get("sensors", names)
        for k in ("length", "width", "side", "mode", "exit"):
            if k in cfg and getattr(a, k) in (None, ap.get_default(k)):
                setattr(a, k, cfg[k])
    s = foot_spec(a.length, a.width, a.size, over)
    geo, checks = build(s, names, a.mode, a.exit, a.side)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    stem = a.name or f"sole_{f'EU{a.size:g}' if not a.length else f'L{a.length:.0f}'}_{a.side}_{a.mode}"
    title = f"{stem}: foot length {s['L']:.0f} mm, ball width {s['W']:.0f} mm, {len(geo['regions'])} regions, tail exit {a.exit}"
    to_svg(geo, out / f"{stem}.svg", title); to_dxf(geo, out / f"{stem}.dxf")
    to_json(geo, checks, s, a, out / f"{stem}.json"); to_png(geo, checks, out / f"{stem}.png", title)
    to_png_zoom(geo, out / f"{stem}_comb_mt2.png")
    if a.mode == "region":
        to_board_json(geo, s, a, out / f"{stem}.board.json", requested=names, checks=checks)
    print(json.dumps(dict(stem=stem, **checks), indent=1))


if __name__ == "__main__":
    main()
