#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors
# SPDX-License-Identifier: CERN-OHL-S-2.0
"""Check a sensor-sole KiCad board before anything is sent to fabrication (KiCad 7 Python, i.e. the Python
that ships pcbnew).

  0. Configuration: the regions and number of contacts the board was built for (a text the exporter writes on
     Cmts.User). Everything below is checked against it, so a personal sole with 14 regions is checked as 14.
  1. Design-rule check with the board's own project rules. The net classes (via size, clearance, track width)
     live in the .kicad_pro beside the board; without it KiCad falls back to its defaults and the result means
     nothing, so a missing project file is a failure. The check fails closed: if KiCad cannot write the
     report, or a section is missing, or the number of entries in a section differs from its header, the board
     fails. The only entries accepted are "footprint not in a library" warnings for the board's own generated
     footprints (each region and J1, each exactly once); they are listed one by one in the result.
  2. Region-to-contact map from the physical copper, without trusting net names: tracks, vias and pads that
     touch (on the same copper layer, or through a via) are joined. Each sense contact must reach exactly one
     region's sense comb and nothing else; the two common contacts must reach every common comb and nothing
     else; every comb piece must be reached. The map is then compared with the net names.
  3. Contact numbering: pad numbers must follow the physical order, the same on both feet. Look at the exposed
     contacts with the tail end pointing up: contact 1 is on the left.
  4. Coverlay: each region's opening must lie on that region, and the comb copper it leaves covered is measured
     from the actual pad geometry (copper minus opening), per region and per comb. More than 2 % of a region's
     copper covered fails.
  5. Provenance: sha256 of the board and project files, and the generator hashes in the title block against
     the generator files beside this script. The channel map in the result is tied to the board's sha256 and
     the ID printed on its tail.

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


COVERED_COPPER_MAX_PCT = 2.0                        # comb copper a region may lose under coverlay


def run_drc(board, pcb_path, generated_refs):
    """Write and parse the DRC report. Returns (summary, problems); fails closed on anything unexpected."""
    problems = []
    rpt = pcb_path.with_suffix(".drc.rpt")
    if rpt.exists():
        rpt.unlink()                                    # never read a report from an earlier run
    ok = pcbnew.WriteDRCReport(board, str(rpt), pcbnew.EDA_UNITS_MILLIMETRES, False)
    summary = dict(report=rpt.name, written=bool(ok))
    if not ok:
        problems.append("KiCad says the DRC report could not be written")
    if not rpt.exists() or rpt.stat().st_size == 0:
        problems.append("DRC report missing or empty")
        return summary, problems
    lines = rpt.read_text().splitlines()
    if lines and lines[0].startswith("** Drc report for "):   # keep local paths out of the report
        lines[0] = f"** Drc report for {pcb_path.name} **"
        rpt.write_text("\n".join(lines) + "\n")
    heads = {}
    for i, ln in enumerate(lines):
        m = re.match(r"\*\* Found (\d+) (DRC violations|unconnected pads|Footprint errors) \*\*$", ln)
        if m:
            heads[m.group(2)] = (i, int(m.group(1)))
        if ln.strip() == "** End of Report **":
            heads["end"] = (i, None)
    need = ["DRC violations", "unconnected pads", "Footprint errors", "end"]
    if any(k not in heads for k in need) or [heads[k][0] for k in need] != sorted(heads[k][0] for k in need):
        problems.append(f"DRC report not in the expected form (sections found: {sorted(heads)})")
        return summary, problems

    def entries(a, b):
        out, cur = [], None
        for ln in lines[a + 1:b]:
            m = re.match(r"^\[(\w+)\]: (.*)$", ln)
            if m:
                cur = dict(type=m.group(1), message=m.group(2), severity=None, items=[]); out.append(cur)
            elif cur is not None and ln.strip():
                sv = re.search(r"Severity: (\w+)", ln)
                if sv:
                    cur["severity"] = sv.group(1)
                elif ln.strip().startswith("@("):
                    cur["items"].append(ln.strip())
        return out
    sec = {k: entries(heads[k][0], heads[nxt][0]) for k, nxt in zip(need[:-1], need[1:])}
    for k in need[:-1]:
        if len(sec[k]) != heads[k][1]:
            problems.append(f"DRC report: '{k}' header says {heads[k][1]}, {len(sec[k])} entries parsed")
    # library warnings: one per generated footprint, nothing else
    lib, other = [], []
    for e in sec["DRC violations"]:
        if e["type"] == "lib_footprint_issues" and e["severity"] == "warning" and "'sensor_sole'" in e["message"] \
                and len(e["items"]) == 1 and re.search(r": Footprint (\S+)$", e["items"][0]):
            lib.append(re.search(r": Footprint (\S+)$", e["items"][0]).group(1))
        else:
            other.append(e)
    expected = sorted(generated_refs)
    if sorted(lib) != expected:
        problems.append(f"library warnings for {sorted(lib)}, expected exactly one for each of {expected}")
    if other:
        kinds = collections.Counter(f"{e['type']} ({e['severity']})" for e in other)
        problems.append(f"DRC: {dict(kinds)}")
    if sec["unconnected pads"]:
        problems.append(f"DRC: {len(sec['unconnected pads'])} unconnected")
    if sec["Footprint errors"]:
        problems.append(f"DRC: {len(sec['Footprint errors'])} footprint errors")
    summary.update(violations=heads["DRC violations"][1], unconnected=heads["unconnected pads"][1],
                   footprint_errors=heads["Footprint errors"][1],
                   by_type=dict(collections.Counter(e["type"] for e in sec["DRC violations"])),
                   library_warnings=sorted(lib), other_entries=[f"{e['type']}: {e['message']}" for e in other][:50])
    return summary, problems


def board_config(board):
    """The configuration the exporter wrote on Cmts.User, or None."""
    for d in board.GetDrawings():
        if d.GetClass() in ("PCB_TEXT", "PTEXT") and d.GetLayer() == pcbnew.Cmts_User:
            t = d.GetText()
            if t.startswith("sensor-sole-config "):
                try:
                    return json.loads(t[len("sensor-sole-config "):])
                except ValueError:
                    return None
    return None


def board_id(board):
    ids = [d.GetText() for d in board.GetDrawings()
           if d.GetClass() in ("PCB_TEXT", "PTEXT") and d.GetLayer() == pcbnew.F_SilkS]
    return ids[0] if len(ids) == 1 else None


def pad_poly(p):
    """A pad's copper in board coordinates (custom pads: their merged primitives)."""
    q = pcbnew.SHAPE_POLY_SET()
    p.MergePrimitivesAsPolygon(q)
    q.Move(p.GetPosition())
    return q


def union(polys):
    u = pcbnew.SHAPE_POLY_SET()
    for q in polys:
        u.BooleanAdd(q, pcbnew.SHAPE_POLY_SET.PM_FAST)
    return u


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

    # 0. the configuration the board was built for
    cfg = board_config(board)
    res["config"] = cfg
    res["board_id"] = board_id(board)
    if res["board_id"] is None:
        problems.append("no single ID text on F.SilkS (the tail's printed board ID)")
    fps = list(board.GetFootprints())
    region_fps = [f for f in fps if f.GetReference() != "J1"]
    if cfg is None:
        problems.append("no sensor-sole-config text on Cmts.User: nothing to check the board against")
    else:
        if sorted(f.GetValue() for f in region_fps) != sorted(cfg["regions"]):
            problems.append(f"regions on the board {sorted(f.GetValue() for f in region_fps)} differ from its "
                            f"configuration {sorted(cfg['regions'])}")
        j1_ = [f for f in fps if f.GetReference() == "J1"]
        if len(j1_) != 1 or len(list(j1_[0].Pads())) != cfg["contacts"]:
            problems.append(f"J1 should have {cfg['contacts']} contacts")
    generated = [f.GetReference() for f in fps if str(f.GetFPID().GetLibNickname()) == "sensor_sole"]
    if len(generated) != len(fps):
        problems.append("footprints from other libraries on the board")

    # 1. DRC with the project's rules
    drc, drc_problems = run_drc(board, pcb_path, generated)
    res["drc"] = drc
    problems += drc_problems

    # coverlay: one opening per region, over that region's combs. Exported footprint polygons have been
    # misplaced by KiCad's local coordinates before, and DRC alone would not notice an opening in the wrong place.
    # Each opening is compared with its region's outline (the B.Cu keep-out zone of the same name):
    #   - it must lie on the region: at least 95 % of its area, and inside the region outline;
    #   - the comb copper it leaves covered (notches where F.Cu tracks land or run along the region's edge) is
    #     measured from the pads' geometry; more than COVERED_COPPER_MAX_PCT of the region's copper fails.
    bad_open, open_pct, coverlay = [], {}, {}
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
        # the copper the opening leaves covered, from the pads' real geometry
        cov = {}
        for num, name in (("1", "sense"), ("2", "common")):
            cu = union(pad_poly(p) for p in fp.Pads() if p.GetNumber() == num)
            hid = pcbnew.SHAPE_POLY_SET(cu)
            hid.BooleanSubtract(poly, pcbnew.SHAPE_POLY_SET.PM_FAST)
            cov[name] = (cu.Area() / NM ** 2, hid.Area() / NM ** 2)
        total = sum(c for c, _ in cov.values()); hidden = sum(h for _, h in cov.values())
        pct = 100 * hidden / total if total else 100.0
        coverlay[fp.GetValue()] = dict(copper_mm2=round(total, 1), covered_mm2=round(hidden, 2),
                                       covered_pct=round(pct, 2), sense_covered_mm2=round(cov["sense"][1], 2),
                                       common_covered_mm2=round(cov["common"][1], 2),
                                       opening_pct_of_region=open_pct[fp.GetValue()])
        if pct > COVERED_COPPER_MAX_PCT:
            bad_open.append(f"{fp.GetValue()}: {hidden:.1f} mm² ({pct:.1f} %) of its comb copper under coverlay")
    res["coverlay_openings_ok"] = not bad_open
    res["coverlay"] = coverlay
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
    if cfg is not None and regions != sorted(cfg["regions"]):
        problems.append(f"regions reached through the copper {regions} differ from the configuration")
    # the channel map, valid only for this exact board file (sha256) and the sole printed with this ID
    res["channel_map"] = dict(board_sha256=res["sha256"], board_id=res["board_id"],
                              side=(re.search(r"side (\w)", stamp[3] or "") or [None, None])[1],
                              contact_to_region={c["contact"]: (c["sense_regions"][0] if len(c["sense_regions"]) == 1
                                                                else ("COM" if c["net"] == "COM" else None))
                                                 for c in contacts})
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
        print(f"{r['board']}: {'OK' if r['ok'] else 'FAIL'}  drc {r['drc'].get('by_type')} unconnected {r['drc'].get('unconnected')}"
              f"  source matches files: {r['source_matches_files']}\n  contacts {cmap}")
        cov = r.get("coverlay", {})
        if cov:
            worst = max(cov.items(), key=lambda kv: kv[1]["covered_pct"])
            print(f"  coverlay: most covered {worst[0]} {worst[1]['covered_mm2']} mm² ({worst[1]['covered_pct']} %);"
                  f" library warnings for {len(r['drc'].get('library_warnings', []))} generated footprints")
        for pr in r["problems"]:
            print("  problem:", pr)
        bad += not r["ok"]
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
