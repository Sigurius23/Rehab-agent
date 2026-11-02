# SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors
# SPDX-License-Identifier: CERN-OHL-S-2.0
"""Deterministic copper routing for the sensor sole (used by sole_gen.py).

Sense lines (B.Cu). The routing plan is a shortest-path tree rooted at the tail: bundles only merge on the way
to the tail and never split. Each branch gets a planar left-to-right order (children sorted by turning angle
and concatenated), so the order at every merge is consistent and no two lines cross. Each line is the
bundle's centre line offset by its lane, at a fixed pitch. The tail continues the root order down to the
contacts, and the order fixes the pin map.

Common net (F.Cu). F.Cu is free in the channels, since the sense lines run on B.Cu. A Steiner tree grows from
the tail root: repeatedly, the nearest unconnected common comb is reached by a shortest path through the F.Cu
free space. Sense combs, vias and stubs are obstacles. Two vias at the contacts take the net to pins 1 and 18.
"""
import collections
import math

import numpy as np
from scipy import ndimage
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra
from shapely.geometry import LineString, Point
from shapely.ops import nearest_points


def build_lanes(paths, res, tail_start, tail_dir, tail_end, seeds, pitch, pad_pitch, pad_len, edge_gap, n_pins,
                fan_len=3.0, track_w=0.12, via_d=0.45, clear=0.15, regions=None, flips=()):
    """Lane polylines for every sense net, from its via to its contact. Returns lanes, vias, pin order."""
    key = lambda p: (round(p[0] / res), round(p[1] / res))
    nets = [n for n, p in paths.items() if p]
    seq, pos = {}, {}
    for n in nets:
        s = []
        for p in reversed(paths[n]):                       # tail -> via
            k = key(p); pos[k] = p
            if not s or s[-1] != k:
                s.append(k)
        seq[n] = s
    root = seq[nets[0]][0]
    if any(seq[n][0] != root for n in nets):
        raise RuntimeError("paths do not share the tail root")
    children, ends = collections.defaultdict(list), collections.defaultdict(list)
    for n in nets:
        s = seq[n]
        for a, b in zip(s[:-1], s[1:]):
            if b not in children[a]:
                children[a].append(b)
        ends[s[-1]].append(n)
    is_node = lambda c: c == root or len(children[c]) != 1 or c in ends

    segs = {}

    def walk(start, first):
        cells, c = [start, first], first
        while not is_node(c):
            c = children[c][0]; cells.append(c)
        return cells

    def grow(node, depth):
        out = []
        for ch in children[node]:
            cells = walk(node, ch); sid = len(segs)
            segs[sid] = dict(cells=cells, depth=depth, kids=[])
            out.append(sid)
            segs[sid]["kids"] = grow(cells[-1], depth + 1)
        return out

    root_kids = grow(root, 0)
    P = lambda c: np.asarray(pos[c], float)
    unit = lambda v: v / (np.linalg.norm(v) + 1e-12)
    cross = lambda a, b: float(a[0] * b[1] - a[1] * b[0])

    def d_out(cells, k=12):
        return unit(P(cells[min(k, len(cells) - 1)]) - P(cells[0]))

    def d_in(cells, k=12):
        return unit(P(cells[-1]) - P(cells[max(0, len(cells) - 1 - k)]))

    memo = {}

    def ahead(sid, node, dist=6.0):
        """Direction from `node` to where the branch's lines are `dist` mm along. Branches often leave a node
        together and separate only later, so their first few cells rank them unreliably."""
        rep = order(sid)[0]
        path = seq[rep]
        k = path.index(node) if node in path else 0
        a = P(path[k]); acc = 0.0; q = a
        for c in path[k + 1:]:
            b = P(c); acc += float(np.linalg.norm(b - q)); q = b
            if acc >= dist:
                break
        return unit(q - a)

    def order_at(node, din, kids):
        items = []
        for sid in kids:
            dc = ahead(sid, node)
            items.append((math.atan2(cross(din, dc), float(np.dot(din, dc))), order(sid)))
        items.sort(key=lambda t: -t[0])                   # leftmost branch first
        left, right = [], []
        for n in ends.get(node, []):
            # a line ending here goes to the side where its region's nearest edge is (the anchor point can lie
            # almost straight ahead along the bundle, which makes its side unreliable)
            if regions is not None and n in regions:
                q = nearest_points(Point(P(node)), regions[n])[1]
                side = np.array([q.x, q.y]) - P(node)
            else:
                side = np.asarray(seeds[n]) - P(node)
            is_left = cross(din, side) > 0
            if n in flips:                                   # chosen by the planarity search
                is_left = not is_left
            (left if is_left else right).append(n)
        return left + [x for _, o in items for x in o] + right

    def order(sid):
        if sid not in memo:
            cells = segs[sid]["cells"]
            memo[sid] = order_at(cells[-1], d_in(cells), segs[sid]["kids"])
        return memo[sid]

    td = np.asarray(tail_dir, float)
    root_order = order_at(root, -td, root_kids)

    # Lane geometry. Each segment's lanes are offset curves of its centre line, node to node. At every
    # node, each child's block of lanes turns on concentric fillets with one centre per block. That keeps the
    # pitch exact through any turn angle and any re-centring of the block, because the block is contiguous and
    # in the same order on both sides. Near-straight joins use an S-curve instead. Parent lanes are cut where
    # their fillet starts, child lanes where it ends.
    from shapely.ops import substring
    rot = lambda v: np.array([-v[1], v[0]])                  # left normal
    lane = {}
    cl = {}
    for sid, sg in segs.items():
        line = _smooth_line([pos[c] for c in sg["cells"]], window=2.0, res=res)
        cl[sid] = line
        o = order(sid); n = len(o)
        for i, net in enumerate(o):
            off = ((n - 1) / 2 - i) * pitch
            lane[(sid, net)] = _offset(line, off)
    left = np.array([td[1], -td[0]])                       # "left" when looking into the sole
    across = -left
    m = len(root_order)
    ts = np.asarray(tail_start, float); te = np.asarray(tail_end, float)
    pad_mid = te - td * (edge_gap + pad_len / 2)
    fan_start = te - td * (edge_gap + pad_len + fan_len)
    vroot = P(root)
    cl["tail"] = LineString([tuple(fan_start + (vroot - ts) - (vroot - ts) @ td * td), tuple(vroot)])
    for i, net in enumerate(root_order):
        off = ((m - 1) / 2 - i) * pitch
        lane[("tail", net)] = _offset(cl["tail"], off)
    seg_order = lambda sid: root_order if sid == "tail" else order(sid)
    parent_of = {root: "tail"}
    kids_of = {root: root_kids}
    for sid, sg in segs.items():
        parent_of[sg["cells"][-1]] = sid
        kids_of[sg["cells"][-1]] = sg["kids"]
    width_at = {root: m}
    for sid, sg in segs.items():
        width_at[sg["cells"][-1]] = len(order(sid))

    def end_dir(line, d=2.0):
        L = line.length; a = np.asarray(line.interpolate(max(0.0, L - d)).coords[0]); b = np.asarray(line.coords[-1])
        return unit(b - a)

    def start_dir(line, d=2.0):
        a = np.asarray(line.coords[0]); b = np.asarray(line.interpolate(min(line.length, d)).coords[0])
        return unit(b - a)

    cut_end, cut_start, conn = {}, {}, {}
    for node, ps in parent_of.items():
        v = P(node)
        po = seg_order(ps); n_p = len(po)
        o_p = {net: ((n_p - 1) / 2 - i) * pitch for i, net in enumerate(po)}
        d_p = end_dir(cl[ps]); n_pv = rot(d_p)
        for c in kids_of.get(node, []):
            co = order(c); n_c = len(co)
            o_c = {net: ((n_c - 1) / 2 - j) * pitch for j, net in enumerate(co)}
            d_c = start_dir(cl[c]); n_cv = rot(d_c)
            th = math.atan2(cross(d_p, d_c), float(np.dot(d_p, d_c)))
            if abs(th) > math.radians(15):
                sg_ = 1.0 if th > 0 else -1.0
                # anchor every lane on its actual end / start point: the routed centre lines are not exactly
                # where an ideal construction would put them, and a jump of even 0.2 mm squeezes the pitch
                pa = {net: np.asarray(lane[(ps, net)].coords[-1], float) for net in co}
                ca = {net: np.asarray(lane[(c, net)].coords[0], float) for net in co}
                inner = max(co, key=lambda net: sg_ * o_p[net])
                A = pa[inner]; B = ca[inner]
                M = np.array([[d_p[0], -d_c[0]], [d_p[1], -d_c[1]]])
                t_, _s = np.linalg.solve(M, B - A)
                X = A + d_p * t_
                r0 = 0.8
                P0 = X - d_p * r0 * math.tan(abs(th) / 2)
                K = P0 + sg_ * n_pv * r0
                for net in co:
                    Pp = pa[net]; Pi = Pp + d_p * float(np.dot(K - Pp, d_p))
                    Cc = ca[net]; Qi = Cc + d_c * float(np.dot(K - Cc, d_c))
                    r = np.linalg.norm(Pi - K)
                    a0_ = math.atan2(*(Pi - K)[::-1]); k = max(4, int(abs(th) / math.radians(8)))
                    arc = [tuple(K + r * np.array([math.cos(a0_ + sg_ * abs(th) * f), math.sin(a0_ + sg_ * abs(th) * f)]))
                           for f in np.linspace(0, 1, k + 1)]
                    cut_end[(ps, net)] = lane[(ps, net)].project(Point(Pi))
                    cut_start[(c, net)] = lane[(c, net)].project(Point(Qi))
                    conn[(node, net)] = arc
            else:                                            # near-straight: S-curve over a length that
                D = 1.0 + 4 * max(abs(o_p[net] - o_c[net]) for net in co)   # keeps the slope gentle
                for net in co:
                    Lp = lane[(ps, net)].length
                    cut_end[(ps, net)] = max(0.0, Lp - D)
                    cut_start[(c, net)] = min(lane[(c, net)].length, D)
                    conn[(node, net)] = None                 # filled by a Bezier at assembly
        for net in ends.get(node, []):                       # a via at a branch node stops short of it
            if node != root and (ps, net) in lane:
                cut_end[(ps, net)] = max(0.0, lane[(ps, net)].length - (0.5 + width_at.get(node, 1) * pitch / 2))

    def piece(sid, net):
        ln = lane[(sid, net)]
        a, b = cut_start.get((sid, net), 0.0), cut_end.get((sid, net), ln.length)
        if b <= a + 1e-6:
            pt = ln.interpolate((a + b) / 2)
            return [tuple(pt.coords[0])]
        g = substring(ln, a, b)
        return list(g.coords) if g.geom_type == "LineString" else [tuple(g.coords[0])]

    net_segs = collections.defaultdict(list)
    for sid in segs:
        for net in order(sid):
            net_segs[net].append(sid)
    out, vias = {}, {}
    for i, net in enumerate(root_order):
        pin = i + 1                                         # 0-based pin index; 0 and n_pins-1 are common
        pad = pad_mid + across * ((pin - (n_pins - 1) / 2) * pad_pitch)
        above = pad - td * (pad_len / 2 + 0.6)               # enter each contact straight, from above
        pts = [tuple(pad), tuple(above)] + piece("tail", net)
        chain = sorted(net_segs[net], key=lambda s: segs[s]["depth"])
        prev = "tail"
        for sid in chain:
            node = segs[sid]["cells"][0]
            nxt = piece(sid, net)
            arc = conn.get((node, net))
            pts = _join(pts, nxt) if arc is None else pts + arc + nxt
            prev = sid
        clean = [pts[0]]
        for p in pts[1:]:
            if math.dist(p, clean[-1]) > 1e-4:
                clean.append(p)
        out[net] = clean[::-1]                              # via -> contact
        vias[net] = clean[-1]
    for _ in range(2):                                      # spacing moves can affect each other: twice
        _space_vias(out, vias, track_w, via_d, clear)
    pin_order = ["COM"] + root_order + ["COM"]
    return dict(lanes=out, vias=vias, pin_order=pin_order, pad_mid=tuple(pad_mid), across=tuple(across),
                left=tuple(left))


def _offset(line, off):
    """Offset curve that never comes back empty. A centre line shorter than the offset (a short segment at a
    tight node) can collapse under shapely's offset; then the lane is the line shifted along its chord normal."""
    if abs(off) < 1e-9:
        return line
    ln = line.offset_curve(off, quad_segs=8, join_style="round")
    if ln.geom_type == "MultiLineString":
        ln = max(ln.geoms, key=lambda g: g.length)
    if ln.is_empty or len(ln.coords) < 2 or ln.length < 1e-6:
        a = np.asarray(line.coords[0], float); b = np.asarray(line.coords[-1], float)
        d = b - a; d = d / (np.linalg.norm(d) or 1.0)
        nv = np.array([-d[1], d[0]]) * off
        ln = LineString([tuple(np.asarray(c, float) + nv) for c in line.coords])
    return ln


def _smooth_line(pts, window, res):
    """Moving average along a grid path (end points pinned), then light simplification. Offsetting a
    0.25 mm staircase by several lanes distorts the inner lanes; a smooth centre line offsets cleanly."""
    a = np.asarray(pts, float)
    if len(a) < 3:
        return LineString(a if len(a) > 1 else np.r_[a, a])
    k = max(1, int(window / res / 2))
    out = a.copy()
    for i in range(1, len(a) - 1):
        lo, hi = max(0, i - k), min(len(a), i + k + 1)
        h = min(i - lo, hi - 1 - i)                      # symmetric window, shrinking near the ends
        out[i] = a[i - h:i + h + 1].mean(axis=0)
    return LineString(out).simplify(0.03)


def _join(a, b, samples=12):
    """Append polyline b to a through a cubic Bezier tangent to both ends. Concentric lanes turning
    together stay at their pitch through the turn, where a straight diagonal jog would squeeze them by
    up to sqrt(2)."""
    if not a:
        return list(b)
    if not b:
        return list(a)
    A, B = np.asarray(a[-1], float), np.asarray(b[0], float)
    chord = np.linalg.norm(B - A)
    if chord < 1e-6 or len(a) < 2 or len(b) < 2:
        return list(a) + list(b)
    da = A - np.asarray(a[-2], float); db = np.asarray(b[1], float) - B
    na, nb = np.linalg.norm(da), np.linalg.norm(db)
    if na < 1e-9 or nb < 1e-9:
        return list(a) + list(b)
    L = 0.39 * chord
    P1, P2 = A + da / na * L, B - db / nb * L
    t = np.linspace(0, 1, samples + 2)[1:-1, None]
    curve = (1 - t) ** 3 * A + 3 * (1 - t) ** 2 * t * P1 + 3 * (1 - t) * t ** 2 * P2 + t ** 3 * B
    return list(a) + [tuple(p) for p in curve] + list(b)


def _space_vias(lanes, vias, track_w, via_d, clear, step=0.05, max_move=2.0):
    """Move any via that crowds another net's lane or via straight away from it, extending its own lane."""
    from shapely.ops import unary_union
    need_lane = via_d / 2 + clear + track_w / 2
    need_via = via_d + clear + 2 * (track_w + clear)      # room for a line to leave between two vias
    for n in list(vias):
        others = unary_union([LineString(p) for m, p in lanes.items() if m != n and len(p) > 1])
        v = np.asarray(vias[n], float)
        moved = 0.0
        while moved < max_move:
            dl = others.distance(Point(v))
            close_vias = [np.asarray(vias[m], float) for m in vias if m != n
                          and np.linalg.norm(np.asarray(vias[m]) - v) < need_via]
            if dl >= need_lane and not close_vias:
                break
            if dl < need_lane:
                q = nearest_points(others, Point(v))[0]
                away = v - np.array([q.x, q.y])
            else:
                away = v - close_vias[0]
            nrm = np.linalg.norm(away)
            v = v + (away / nrm if nrm > 1e-9 else np.array([0.0, 1.0])) * step
            moved += step
        if moved > 0:
            lanes[n] = [tuple(v)] + lanes[n]                 # lanes run via -> contact
            vias[n] = tuple(v)


def _raster(geoms, X, Y):
    """Rasterise polygons onto the grid, each only within its bounding box (fast for many small parts)."""
    from matplotlib.path import Path as MP
    m = np.zeros((len(Y), len(X)), bool)
    res = X[1] - X[0]
    for g in geoms:
        for p in ([g] if g.geom_type == "Polygon" else list(getattr(g, "geoms", []))):
            if p.is_empty:
                continue
            x0, y0, x1, y1 = p.bounds
            i0, i1 = max(0, int((y0 - Y[0]) / res) - 1), min(len(Y), int((y1 - Y[0]) / res) + 2)
            j0, j1 = max(0, int((x0 - X[0]) / res) - 1), min(len(X), int((x1 - X[0]) / res) + 2)
            if i1 <= i0 or j1 <= j0:
                continue
            gx, gy = np.meshgrid(X[j0:j1], Y[i0:i1])
            pts = np.c_[gx.ravel(), gy.ravel()]
            inside = MP(np.asarray(p.exterior.coords)).contains_points(pts)
            for h in p.interiors:
                inside &= ~MP(np.asarray(h.coords)).contains_points(pts)
            m[i0:i1, j0:j1] |= inside.reshape(i1 - i0, j1 - j0)
    return m


def route_common(area, sense_combs, common_combs, obstacles, start, width, clear, res=0.2):
    """Steiner tree on F.Cu from `start` to every common comb. Returns polylines (list of point lists)."""
    minx, miny, maxx, maxy = area.bounds
    X = np.arange(minx - 1, maxx + 1, res); Y = np.arange(miny - 1, maxy + 1, res)
    ny, nx = len(Y), len(X)
    inside = _raster([area], X, Y)
    sense_combs = list(sense_combs)
    blocked = _raster([g.buffer(res * 0.5) for g in sense_combs + list(obstacles)], X, Y)    # thin fingers too
    from shapely.ops import unary_union
    sense_all = unary_union(list(sense_combs))
    reach = width / 2 + clear + 0.05                    # margin for rasterisation error
    dist_block = ndimage.distance_transform_edt(~blocked) * res
    dist_edge = ndimage.distance_transform_edt(inside) * res
    free = inside & (dist_block >= reach + res / 2) & (dist_edge >= reach + res / 2)
    idx = -np.ones((ny, nx), int); fi = np.flatnonzero(free.ravel()); idx.ravel()[fi] = np.arange(len(fi))
    rows, cols, w = [], [], []
    for dy, dx in ((0, 1), (1, 0), (1, 1), (1, -1)):
        a = idx[0:ny - dy, max(0, -dx):nx - max(0, dx)]
        b = idx[dy:ny, max(0, dx):nx - max(0, -dx)]
        ok = (a >= 0) & (b >= 0)
        step = res * math.hypot(dx, dy)
        rows += [a[ok], b[ok]]; cols += [b[ok], a[ok]]; w += [np.full(ok.sum(), step)] * 2
    G = csr_matrix((np.concatenate(w), (np.concatenate(rows), np.concatenate(cols))), shape=(len(fi), len(fi)))
    yy, xx = np.unravel_index(fi, (ny, nx))
    near = lambda p: int(np.argmin((X[xx] - p[0]) ** 2 + (Y[yy] - p[1]) ** 2))
    s0 = near(start)
    tree = {s0}
    start_xy = (float(X[xx[s0]]), float(Y[yy[s0]]))
    targets = {}
    for n, g in common_combs.items():
        cm = _raster([g], X, Y)
        dm = ndimage.distance_transform_edt(~cm) * res
        t = idx[free & (dm <= reach + 2 * res)]
        targets[n] = set(t[t >= 0].tolist())
    lines, unreached = [], []
    todo = dict(targets)
    while todo:
        D, pred, src = dijkstra(G, indices=sorted(tree), return_predecessors=True, min_only=True)
        best = None
        for n, t in todo.items():
            if not t:
                continue
            tt = np.fromiter(t, int); k = tt[np.argmin(D[tt])]
            if np.isfinite(D[k]) and (best is None or D[k] < best[1]):
                best = (n, D[k], k)
        if best is None:
            unreached += list(todo); break
        n, _, k = best
        seq = [k]
        while seq[-1] not in tree and pred[seq[-1]] >= 0:
            seq.append(pred[seq[-1]])
        pts = [(X[xx[q]], Y[yy[q]]) for q in seq]
        ln = LineString(pts).simplify(0) if len(pts) > 1 else None   # exact: joins stay on the tree
        poly = list(ln.coords) if ln is not None else pts
        # last hop onto the comb itself; it must not pass a sense comb
        q = nearest_points(Point(poly[0]), common_combs[n])[1]
        hop = LineString([_into(poly[0], (q.x, q.y), 0.04), poly[0]])
        if hop.length > 1e-6 and hop.distance(sense_all) < width / 2 + clear:
            ok = False
            for cand in sorted(todo[n], key=lambda c: D[c])[:400]:
                pc = (X[xx[cand]], Y[yy[cand]])
                qc = nearest_points(Point(pc), common_combs[n])[1]
                if LineString([_into(pc, (qc.x, qc.y), 0.04), pc]).distance(sense_all) >= width / 2 + clear:
                    k = cand; ok = True; break
            if ok:
                seq = [k]
                while seq[-1] not in tree and pred[seq[-1]] >= 0:
                    seq.append(pred[seq[-1]])
                pts = [(X[xx[c]], Y[yy[c]]) for c in seq]
                ln = LineString(pts).simplify(0) if len(pts) > 1 else None
                poly = list(ln.coords) if ln is not None else pts
                q = nearest_points(Point(poly[0]), common_combs[n])[1]
        tree |= set(seq)                                    # only the path actually drawn joins the tree
        lines.append([_into(poly[0], (q.x, q.y), 0.04)] + poly)
        del todo[n]
    return lines, unreached, start_xy


def _into(frm, to, depth):
    """Point `to` moved `depth` further along frm->to: a track end that overlaps the copper it joins."""
    v = np.asarray(to, float) - np.asarray(frm, float); n = np.linalg.norm(v)
    return tuple(np.asarray(to, float) + (v / n * depth if n > 1e-9 else 0))


def stubs_to_combs(vias, sense_combs, common_combs, width, clear):
    """Shortest F.Cu stub from each via to its region's sense comb; flags any that come too close to common."""
    out, bad = {}, []
    for n, v in vias.items():
        q = nearest_points(Point(v), sense_combs[n])[1]
        end = _into(v, (q.x, q.y), 0.04)                    # just inside the comb: counts as connected
        s = LineString([v, end])
        out[n] = [tuple(v), end]
        if s.length > 0.05 and s.distance(common_combs[n]) < clear + width / 2 - 1e-3:
            bad.append(n)
    return out, bad


def _draw(lines, points, X, Y):
    """Mark grid cells on polylines (sampled at half a cell) and at points."""
    res = X[1] - X[0]
    m = np.zeros((len(Y), len(X)), bool)
    def mark(p):
        i, j = int(round((p[1] - Y[0]) / res)), int(round((p[0] - X[0]) / res))
        if 0 <= i < len(Y) and 0 <= j < len(X):
            m[i, j] = True
    for ln in lines:
        c = np.asarray(ln, float)
        for a, b in zip(c[:-1], c[1:]):
            k = max(2, int(np.linalg.norm(b - a) / (res / 2)) + 1)
            for t in np.linspace(0, 1, k):
                mark(a + (b - a) * t)
    for p in points:
        mark(p)
    return m


def maze_refine(planned, vias, order, allowed, keepout, res=0.06, track_w=0.12, clear=0.15, via_d=0.45,
                no_go=None, rounds=8):
    """Final pass: negotiated re-routing of every sense line on a fine grid (PathFinder-style).

    Each round routes every line by a shortest path whose cost is lowest on its planned lane. Cells within
    clearance of another line are allowed but cost more: a present-congestion term that grows every round, and
    a history term that accumulates where lines collided before. Lines therefore negotiate until none
    overlaps another. Vias, keep-out regions, the copper-free edge and the fixed fan-outs are hard obstacles.
    Returns (lanes, failed): failed lists lines still in conflict after the last round (or unroutable).
    """
    minx, miny, maxx, maxy = allowed.bounds
    X = np.arange(minx - 0.5, maxx + 0.5, res); Y = np.arange(miny - 0.5, maxy + 0.5, res)
    ny, nx = len(Y), len(X)
    grid_err = res / 2 + 0.03                                  # quantisation plus simplification
    edt = lambda m: ndimage.distance_transform_edt(~m) * res   # distance to the nearest marked cell
    inside = _raster([allowed], X, Y)
    d_edge = ndimage.distance_transform_edt(inside) * res
    d_keep = edt(_raster([keepout], X, Y))
    base = (d_edge >= track_w / 2 + grid_err) & (d_keep >= track_w / 2 + clear + grid_err)
    if no_go is not None:                                      # the contact zone: fans are fixed there
        base &= ~_raster([no_go], X, Y)
    block_line = track_w + clear + grid_err                    # centre-to-centre to another line
    block_via = via_d / 2 + clear + track_w / 2 + grid_err
    cell = lambda p: (int(round((p[1] - Y[0]) / res)), int(round((p[0] - X[0]) / res)))
    nets = list(order)
    d_via = {n: edt(_draw([], [vias[n]], X, Y)) for n in nets}
    d_fix = {n: edt(_draw([planned[n][-3:]], [], X, Y)) for n in nets}
    hard = {}
    for n in nets:                                             # static obstacles seen by line n
        h = base.copy()
        for m in nets:
            if m != n:
                h &= (d_via[m] >= block_via) & (d_fix[m] >= block_line)
        for c in (cell(vias[n]), cell(planned[n][-3])):        # its own end points stay open
            h[max(0, c[0] - 2):c[0] + 3, max(0, c[1] - 2):c[1] + 3] = True
        hard[n] = h
    plan_cost = {}
    for n in nets:
        dp = edt(_draw([planned[n][:-2]], [], X, Y))
        plan_cost[n] = np.where(dp <= 0.08, 1.0, np.where(dp <= 0.45, 2.5, 8.0)).astype(np.float32)
    hist = np.zeros((ny, nx), np.float32)
    paths, near = {}, {}
    pres = 0.5
    failed = list(nets)
    for rnd in range(rounds):
        for n in nets:
            occ = np.zeros((ny, nx), np.float32)
            for m, nm in near.items():
                if m != n:
                    occ += nm
            free = hard[n]
            cost = plan_cost[n] * (1.0 + hist) + pres * 40.0 * occ
            idx = -np.ones((ny, nx), np.int64); fi = np.flatnonzero(free.ravel()); idx.ravel()[fi] = np.arange(len(fi))
            cf = cost.ravel()
            rows, cols, w = [], [], []
            for dy, dx in ((0, 1), (1, 0), (1, 1), (1, -1)):
                a = idx[0:ny - dy, max(0, -dx):nx - max(0, dx)]
                b = idx[dy:ny, max(0, dx):nx - max(0, -dx)]
                ok = (a >= 0) & (b >= 0)
                ai, bi = a[ok], b[ok]
                ww = 0.5 * (cf[fi[ai]] + cf[fi[bi]]) * res * math.hypot(dx, dy)
                rows += [ai, bi]; cols += [bi, ai]; w += [ww, ww]
            G = csr_matrix((np.concatenate(w), (np.concatenate(rows), np.concatenate(cols))),
                           shape=(len(fi), len(fi)))
            s_, g_ = idx[cell(vias[n])], idx[cell(planned[n][-3])]
            if s_ < 0 or g_ < 0:
                continue
            D, pred = dijkstra(G, indices=s_, return_predecessors=True)
            if not np.isfinite(D[g_]):
                continue
            seq = [g_]
            while seq[-1] != s_:
                seq.append(pred[seq[-1]])
            yy, xx = np.unravel_index(fi[seq[::-1]], (ny, nx))
            pts = [tuple(vias[n])] + [(X[j], Y[i]) for i, j in zip(yy, xx)][1:-1] + [tuple(planned[n][-3])]
            path = LineString(pts).simplify(0.03)
            paths[n] = path
            near[n] = (edt(_draw([list(path.coords)], [], X, Y)) < block_line).astype(np.float32)
        # conflicts, judged on exact geometry against the real rule (centre-to-centre track + clearance)
        failed = sorted(set(n for n in nets if n not in paths))
        conflict_pts = []
        routed_n = [n for n in nets if n in paths]
        for i, n in enumerate(routed_n):
            for m in routed_n[i + 1:]:
                if paths[n].distance(paths[m]) < track_w + clear + 0.005:
                    failed += [n, m]
                    a_, b_ = nearest_points(paths[n], paths[m])
                    conflict_pts += [(a_.x, a_.y), (b_.x, b_.y)]
        failed = sorted(set(failed))
        if not failed:
            break
        if conflict_pts:
            hist[edt(_draw([], conflict_pts, X, Y)) < 1.0] += 1.0
        pres *= 2.0
    lanes = {}
    for n in nets:
        lanes[n] = (list(paths[n].coords) + list(planned[n][-2:])) if n in paths else planned[n]
    maze_refine.rounds_used = rnd + 1
    return lanes, failed


def crossings(lanes, ends_trim=2):
    """Pairs of sense lines whose routed paths (fan-out excluded) cross each other."""
    names = list(lanes)
    out = []
    for i, n in enumerate(names):
        a = LineString(lanes[n][:-ends_trim])
        for m in names[i + 1:]:
            if a.crosses(LineString(lanes[m][:-ends_trim])):
                out.append((n, m))
    return out


def odd_crossings(lanes, ends_trim=2):
    """Pairs of lines that cross an odd number of times: a crossing that routing cannot remove."""
    names = list(lanes)
    out = []
    for i, n in enumerate(names):
        a = LineString(lanes[n][:-ends_trim])
        for m in names[i + 1:]:
            x = a.intersection(LineString(lanes[m][:-ends_trim]))
            k = 0 if x.is_empty else (1 if x.geom_type == "Point" else
                                      sum(1 for g in getattr(x, "geoms", []) if g.geom_type == "Point"))
            if k % 2 == 1:
                out.append((n, m))
    return out
