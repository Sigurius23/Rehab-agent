#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors
# SPDX-License-Identifier: CERN-OHL-S-2.0
"""Check a sensor-sole KiCad board before anything is sent to fabrication (KiCad 7 Python, i.e. the Python
that ships pcbnew).

  1. Design-rule check with the board's own project rules. The net classes (via size, clearance, track width)
     live in the .kicad_pro beside the board; without it KiCad falls back to its defaults and the result means
     nothing, so a missing project file is a failure.
  2. Region-to-contact map from the physical copper, without trusting net names: tracks, vias and pads that
     touch (on the same copper layer, or through a via) are joined. Each sense contact must reach exactly one
     region's sense comb and nothing else; the two common contacts must reach every common comb and nothing
     else; every comb piece must be reached. The map is then compared with the net names.
  3. Contact numbering: pad numbers must follow the physical order, the same on both feet. Look at the exposed
     contacts with the tail end pointing up: contact 1 is on the left.
  4. Provenance: sha256 of the board and project files, and the generator hashes in the title block against
     the generator files beside this script.

Writes <board>.drc.rpt and <board>.check.json beside the board; exit status 1 if any check fails.
Usage: python3 verify_board.py kicad/sole_EU42_R.kicad_pcb [more boards ...]
"""
import collections
import hashlib
import json
import os
import re
import sys
from pathlib import Path

import pcbnew

HERE = Path(__file__).resolve().parent
NM = 1e6                                            # KiCad internal units per mm


def sha(path, n=None):
    h = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    return h[:n] if n else h


def source_hashes():
    return {f: sha(HERE / f"{f}.py", 12) for f in ("sole_gen", "sole_route", "kicad_export")}


def run_drc(board, pcb_path):
    rpt = pcb_path.with_suffix(".drc.rpt")
    cwd = os.getcwd()
    os.chdir(pcb_path.parent)                       # the report names the board by the path it is given
    try:
        ok = pcbnew.WriteDRCReport(board, rpt.name, pcbnew.EDA_UNITS_MILLIMETRES, False)
    finally:
        os.chdir(cwd)
    txt = rpt.read_text()
    found = lambda what: int((re.search(r"\*\* Found (\d+) " + what, txt) or [0, 0])[1])
    types = collections.Counter(re.findall(r"^\[(\w+)\]", txt, re.M))
    sev = collections.Counter(re.findall(r"Severity: (\w+)", txt))
    return dict(report=rpt.name, written=bool(ok), violations=found("DRC violations"), unconnected=found("unconnected pads"),
                footprint_errors=found("Footprint errors"), by_type=dict(types), by_severity=dict(sev))


def copper_items(board):
    """(owner description, layer, SHAPE, bbox) for every copper item on F.Cu/B.Cu; item ids join layers."""
    items, owner = [], []
    for t in board.GetTracks():
        is_via = t.GetClass() == "PCB_VIA"
        layers = (pcbnew.F_Cu, pcbnew.B_Cu) if is_via else (t.GetLayer(),)
        k = len(owner); owner.append(("via" if is_via else "track", t.GetNetname(), None, None))
        for L in layers:
            items.append((k, L, t.GetEffectiveShape(L)))
    for fp in board.GetFootprints():
        for p in fp.Pads():
            k = len(owner); owner.append(("pad", p.GetNetname(), fp.GetReference(), (fp.GetValue(), p.GetNumber(), p)))
            for L in (pcbnew.F_Cu, pcbnew.B_Cu):
                if p.IsOnLayer(L):
                    items.append((k, L, p.GetEffectiveShape(L)))
    return items, owner


def physical_nets(board, cell=1.0):
    """Union-find over items whose copper touches; returns (component of each owner, owners)."""
    items, owner = copper_items(board)
    parent = list(range(len(owner)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]; a = parent[a]
        return a

    grid = collections.defaultdict(list)
    boxes = []
    for i, (k, L, s) in enumerate(items):
        bb = s.BBox()
        x0, y0, x1, y1 = bb.GetX(), bb.GetY(), bb.GetX() + bb.GetWidth(), bb.GetY() + bb.GetHeight()
        boxes.append((x0, y0, x1, y1))
        for gx in range(int(x0 / NM / cell), int(x1 / NM / cell) + 1):
            for gy in range(int(y0 / NM / cell), int(y1 / NM / cell) + 1):
                grid[(L, gx, gy)].append(i)
    tested = set()
    for cellitems in grid.values():
        for a_ in range(len(cellitems)):
            i = cellitems[a_]
            ki, Li, si = items[i]; bi = boxes[i]
            for j in cellitems[a_ + 1:]:
                kj, Lj, sj = items[j]
                if ki == kj or find(ki) == find(kj):
                    continue
                key = (i, j) if i < j else (j, i)
                if key in tested:
                    continue
                tested.add(key)
                bj = boxes[j]
                if bi[2] < bj[0] or bj[2] < bi[0] or bi[3] < bj[1] or bj[3] < bi[1]:
                    continue
                if si.Collide(sj, 0):
                    parent[find(ki)] = find(kj)
    return [find(k) for k in range(len(owner))], owner


def contact_order(j1, tail_up):
    """Pads of J1 sorted left to right as seen looking at the exposed contacts with the tail end pointing up."""
    pads = list(j1.Pads())
    bottom = all(p.IsOnLayer(pcbnew.B_Cu) for p in pads)
    ux, uy = tail_up                                  # page coordinates, Y down
    left = (-uy, ux) if bottom else (uy, -ux)         # seen from below, left and right swap
    return sorted(pads, key=lambda p: -(p.GetPosition().x * left[0] + p.GetPosition().y * left[1])), bottom


def check(pcb_path):
    pcb_path = Path(pcb_path).resolve()
    pro = pcb_path.with_suffix(".kicad_pro")
    problems = []
    if not pro.exists():
        problems.append(f"{pro.name} missing: the design rules would be KiCad defaults")
    board = pcbnew.LoadBoard(str(pcb_path))
    board.BuildConnectivity()
    tb = board.GetTitleBlock()
    stamp = [tb.GetComment(i) for i in range(4)]
    res = dict(board=pcb_path.name, sha256=sha(pcb_path), project_sha256=sha(pro) if pro.exists() else None,
               kicad=pcbnew.GetBuildVersion(), title=tb.GetTitle(), title_block=stamp)

    # provenance: generator hashes written by kicad_export into comment 3 ("sole_gen <h> sole_route <h> kicad_export <h>")
    m = dict(re.findall(r"(sole_gen|sole_route|kicad_export) ([0-9a-f]{12})", stamp[2] or ""))
    now = source_hashes()
    res["source_in_board"] = m or None
    res["source_matches_files"] = bool(m) and all(m.get(f) == h for f, h in now.items())
    if not m:
        problems.append("no generator hashes in the title block (board made by an older exporter)")
    elif not res["source_matches_files"]:
        problems.append(f"generator files changed since this board was made: board {m}, files {now}")

    # 1. DRC with the project's rules
    drc = run_drc(board, pcb_path)
    res["drc"] = drc
    errors = {k: v for k, v in drc["by_type"].items() if k != "lib_footprint_issues"}
    if errors or drc["unconnected"] or drc["footprint_errors"]:
        problems.append(f"DRC: {errors}, unconnected {drc['unconnected']}, footprint errors {drc['footprint_errors']}")

    # coverlay: one opening per region, over that region's combs. Exported footprint polygons have been
    # misplaced by KiCad's local coordinates before, and DRC alone would not notice an opening in the wrong place.
    # Each opening is compared with its region's outline (the B.Cu keep-out zone of the same name):
    #   - it must lie on the region: at least 95 % of its area, and inside the region outline;
    #   - the comb pieces must lie in it (anchor points; one small piece may sit in a notch).
    # Notches where F.Cu tracks land or run along a region's edge cover a little of the comb (EU 42: at most
    # 1.5 % of a region's sensing area; DESIGN.md, section 10).
    bad_open, open_pct = [], {}
    zones = {z.GetZoneName()[len("keepout_"):]: z for z in board.Zones() if z.GetZoneName().startswith("keepout_")}
    for fp in board.GetFootprints():
        if fp.GetReference() == "J1":
            continue
        shapes = [g for g in fp.GraphicalItems() if g.GetLayer() == pcbnew.F_Mask]
        if len(shapes) != 1:
            bad_open.append(f"{fp.GetValue()}: {len(shapes)} openings"); continue
        poly = pcbnew.SHAPE_POLY_SET(shapes[0].GetPolyShape())   # stored relative to the footprint
        poly.Move(fp.GetPosition())
        z = zones.get(fp.GetValue())
        if z is None:
            bad_open.append(f"{fp.GetValue()}: no region outline (keep-out zone) to compare with"); continue
        region = pcbnew.SHAPE_POLY_SET(z.Outline())
        inter = pcbnew.SHAPE_POLY_SET(poly)
        inter.BooleanIntersection(region, pcbnew.SHAPE_POLY_SET.PM_FAST)
        a_reg, a_open, a_in = region.Area(), poly.Area(), inter.Area()
        open_pct[fp.GetValue()] = round(100 * a_open / a_reg, 1) if a_reg else 0.0
        if a_reg <= 0 or a_open < 0.95 * a_reg or a_in < 0.999 * a_open:
            bad_open.append(f"{fp.GetValue()}: opening {a_open / NM ** 2:.0f} mm², {a_in / NM ** 2:.0f} mm² of it on the "
                            f"region of {a_reg / NM ** 2:.0f} mm²")
        pads = list(fp.Pads())
        outside = sum(1 for p in pads if not poly.Contains(p.GetPosition()))
        if outside > max(1, 0.1 * len(pads)):
            bad_open.append(f"{fp.GetValue()}: {outside} of {len(pads)} comb pieces outside the opening")
    res["coverlay_openings_ok"] = not bad_open
    res["coverlay_opening_pct_of_region"] = open_pct
    if bad_open:
        problems.append(f"coverlay openings: {bad_open}")

    # 2. physical connectivity
    comp, owner = physical_nets(board)
    j1 = next(f for f in board.GetFootprints() if f.GetReference() == "J1")
    region_pads = collections.defaultdict(list)       # component -> [(region, pad number)]
    all_pieces = collections.Counter()
    for k, (kind, net, ref, extra) in enumerate(owner):
        if kind == "pad" and ref != "J1":
            region_pads[comp[k]].append((extra[0], extra[1]))
            all_pieces[(extra[0], extra[1])] += 1
    j1_comp = {}
    for k, (kind, net, ref, extra) in enumerate(owner):
        if kind == "pad" and ref == "J1":
            j1_comp[extra[1]] = (comp[k], net)
    # tail direction (page coordinates): from the sole's centre to J1
    bb = board.GetBoardEdgesBoundingBox()
    cx, cy = bb.GetCenter().x, bb.GetCenter().y
    jx, jy = j1.GetPosition().x, j1.GetPosition().y
    n_ = ((jx - cx) ** 2 + (jy - cy) ** 2) ** 0.5
    order, bottom = contact_order(j1, ((jx - cx) / n_, (jy - cy) / n_))
    numbering_ok = [p.GetNumber() for p in order] == [str(i + 1) for i in range(len(order))]
    if not numbering_ok:
        problems.append("J1 pad numbers do not follow the physical contact order "
                        f"(left to right: {[p.GetNumber() for p in order]})")
    contacts, reached = [], collections.Counter()
    n_pins = len(order)
    for p in order:
        num = p.GetNumber()
        c, net = j1_comp[num]
        hits = region_pads.get(c, [])
        sense = sorted({r for r, padnum in hits if padnum == "1"})
        common = sorted({r for r, padnum in hits if padnum == "2"})
        for r, padnum in hits:
            reached[(r, padnum)] += 1
        others = sorted(q for q, (cc, _) in j1_comp.items() if cc == c and q != num)
        contacts.append(dict(contact=int(num), net=net, sense_regions=sense, common_regions=len(common),
                             shares_copper_with_contacts=others))
        if num in ("1", str(n_pins)):
            if net != "COM" or sense or others != [("1" if num == str(n_pins) else str(n_pins))]:
                problems.append(f"contact {num}: expected common only, got net {net}, sense {sense}, joined to {others}")
        else:
            if len(sense) != 1 or common or others or net != f"S_{sense[0] if sense else '?'}":
                problems.append(f"contact {num}: net {net} reaches sense {sense}, {len(common)} common combs, "
                                f"other contacts {others}")
    regions = sorted({r for r, _ in all_pieces})
    com_c = j1_comp["1"][0]
    com_regions = sorted({r for r, padnum in region_pads.get(com_c, []) if padnum == "2"})
    if com_regions != regions:
        problems.append(f"common combs not reached from contact 1: {sorted(set(regions) - set(com_regions))}")
    # every piece of a comb must sit in the contact's component (pieces are separate pads in KiCad)
    piece_comp = collections.defaultdict(set)
    for k, (kind, net, ref, extra) in enumerate(owner):
        if kind == "pad" and ref != "J1":
            piece_comp[(extra[0], extra[1])].add(comp[k])
    split = sorted(f"{r}/{pn}" for (r, pn), cs in piece_comp.items() if len(cs) > 1)
    unreached = sorted(f"{r}/{pn}" for (r, pn), cs in piece_comp.items()
                       if not cs & {c for c, _ in j1_comp.values()})
    if split:
        problems.append(f"comb pieces not all connected: {split}")
    if unreached:
        problems.append(f"combs reached from no contact: {unreached}")
    res.update(contacts_seen_from="exposed contacts facing the viewer, tail end up; contact 1 on the left",
               contacts_on="B.Cu" if bottom else "F.Cu", contact_numbering_physical=numbering_ok,
               contacts=contacts, regions=regions)
    res["problems"] = problems
    res["ok"] = not problems
    out = pcb_path.with_suffix(".check.json")
    out.write_text(json.dumps(res, indent=1) + "\n")
    return res


def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(2)
    bad = 0
    for p in sys.argv[1:]:
        r = check(p)
        cmap = ", ".join(f"{c['contact']}:{c['sense_regions'][0] if c['sense_regions'] else 'COM'}" for c in r["contacts"])
        print(f"{r['board']}: {'OK' if r['ok'] else 'FAIL'}  drc {r['drc']['by_type']} unconnected {r['drc']['unconnected']}"
              f"  source matches files: {r['source_matches_files']}\n  contacts {cmap}")
        for pr in r["problems"]:
            print("  problem:", pr)
        bad += not r["ok"]
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
