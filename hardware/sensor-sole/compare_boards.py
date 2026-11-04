#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors
# SPDX-License-Identifier: CERN-OHL-S-2.0
"""Compare two boards of the same sole item by item, not byte by byte: what changed in the copper, the outline,
the keep-outs, the coverlay openings, the contact map, the identity and the rules. Run with KiCad's Python.

A regenerated board differs in bytes whenever its provenance stamp does (generator hashes, git revision), and
its ID changes whenever the design hash does. This reports those separately from the geometry, so a geometric
change cannot hide behind a stamp change, and a stamp change is not mistaken for one.

  python3 compare_boards.py OLD.kicad_pcb NEW.kicad_pcb [--maps OLD_MAP.json NEW_MAP.json] [--json OUT.json]

Copper is compared per footprint and net (the merged pad copper, as XOR area), tracks and vias as exact
multisets (to the nanometre). Differences below 1e-4 mm2 are reported as rounding.
"""
import argparse
import collections
import json
import re
from pathlib import Path

import pcbnew

NM = 1e6
TOL_MM2 = 1e-4


def poly_area(q):
    return q.Area() / NM ** 2


def xor_area(a, b):
    """Area of (a - b) and of (b - a), in mm2."""
    d1 = pcbnew.SHAPE_POLY_SET(a); d1.BooleanSubtract(b, pcbnew.SHAPE_POLY_SET.PM_FAST)
    d2 = pcbnew.SHAPE_POLY_SET(b); d2.BooleanSubtract(a, pcbnew.SHAPE_POLY_SET.PM_FAST)
    return poly_area(d1), poly_area(d2)


def union(polys):
    u = pcbnew.SHAPE_POLY_SET()
    for q in polys:
        u.BooleanAdd(q, pcbnew.SHAPE_POLY_SET.PM_FAST)
    return u


def pad_copper(p):
    q = pcbnew.SHAPE_POLY_SET()
    p.MergePrimitivesAsPolygon(q)
    q.Move(p.GetPosition())
    return q


def local_to_board(q, fp):
    q = pcbnew.SHAPE_POLY_SET(q)
    q.Move(fp.GetPosition())
    return q


def text_items(b):
    out = {}
    for d in b.GetDrawings():
        if d.GetClass() in ("PCB_TEXT", "PTEXT"):
            out.setdefault(b.GetLayerName(d.GetLayer()), []).append(d.GetText())
    return out


def config(b):
    for d in b.GetDrawings():
        if d.GetClass() in ("PCB_TEXT", "PTEXT") and d.GetText().startswith("sensor-sole-config "):
            return json.loads(d.GetText()[len("sensor-sole-config "):])
    return None


def describe(path):
    b = pcbnew.LoadBoard(str(path))
    edge = pcbnew.SHAPE_POLY_SET()
    b.GetBoardPolygonOutlines(edge)
    tracks, vias = collections.Counter(), collections.Counter()
    for t in b.GetTracks():
        if t.GetClass() == "PCB_VIA":
            vias[(t.GetNetname(), t.GetPosition().x, t.GetPosition().y, t.GetWidth(), t.GetDrillValue())] += 1
        else:
            tracks[(b.GetLayerName(t.GetLayer()), t.GetNetname(), t.GetStart().x, t.GetStart().y, t.GetEnd().x,
                    t.GetEnd().y, t.GetWidth())] += 1
    copper, masks, contacts, pads_n = {}, {}, {}, collections.Counter()
    for fp in b.GetFootprints():
        name = fp.GetValue()
        if fp.GetReference() == "J1":
            for p in fp.Pads():
                contacts[p.GetNumber()] = p.GetNetname()
            continue
        for p in fp.Pads():
            copper.setdefault((name, p.GetNetname()), []).append(pad_copper(p))
            pads_n[(name, p.GetNetname())] += 1
        ms = [local_to_board(g.GetPolyShape(), fp) for g in fp.GraphicalItems()
              if g.GetLayer() == pcbnew.F_Mask and g.GetShape() == pcbnew.SHAPE_T_POLY]
        if ms:
            masks[name] = union(ms)
    zones = collections.defaultdict(list)
    for z in b.Zones():
        zones[re.sub(r"_\d+$", "", z.GetZoneName()) or "(unnamed)"].append(pcbnew.SHAPE_POLY_SET(z.Outline()))
    tb = b.GetTitleBlock()
    return dict(board=b, edge=edge, tracks=tracks, vias=vias, copper={k: union(v) for k, v in copper.items()},
                pads_n=pads_n, masks=masks, contacts=contacts, zones={k: union(v) for k, v in zones.items()},
                texts=text_items(b), config=config(b), title=[tb.GetComment(i) for i in range(4)])


def project_rules(pcb):
    pro = Path(pcb).with_suffix(".kicad_pro")
    if not pro.exists():
        return None
    d = json.loads(pro.read_text())
    return dict(board=d.get("board", {}).get("design_settings"), net_settings=d.get("net_settings"))


def compare(old, new, maps=None):
    A, B = describe(old), describe(new)
    rep = dict(old=str(old), new=str(new), geometry={}, identity={}, rules={}, maps=None)
    g = rep["geometry"]
    g["outline_xor_mm2"] = [round(x, 6) for x in xor_area(A["edge"], B["edge"])]
    g["tracks"] = dict(old=sum(A["tracks"].values()), new=sum(B["tracks"].values()),
                       only_old=sum((A["tracks"] - B["tracks"]).values()), only_new=sum((B["tracks"] - A["tracks"]).values()))
    g["vias"] = dict(old=sum(A["vias"].values()), new=sum(B["vias"].values()),
                     only_old=sum((A["vias"] - B["vias"]).values()), only_new=sum((B["vias"] - A["vias"]).values()))
    cu = {}
    for k in sorted(set(A["copper"]) | set(B["copper"])):
        a, b = A["copper"].get(k), B["copper"].get(k)
        if a is None or b is None:
            cu[f"{k[0]}/{k[1]}"] = dict(only_in="new" if a is None else "old")
            continue
        x1, x2 = xor_area(a, b)
        cu[f"{k[0]}/{k[1]}"] = dict(area_old=round(poly_area(a), 4), area_new=round(poly_area(b), 4),
                                    lost_mm2=round(x1, 6), added_mm2=round(x2, 6),
                                    pads_old=A["pads_n"][k], pads_new=B["pads_n"][k])
    g["comb_copper"] = cu
    g["comb_copper_changed"] = sorted(k for k, v in cu.items() if "only_in" in v or v["lost_mm2"] > TOL_MM2
                                      or v["added_mm2"] > TOL_MM2)
    g["comb_pad_count_changed"] = sorted(k for k, v in cu.items() if "only_in" not in v and v["pads_old"] != v["pads_new"])
    mk = {}
    for k in sorted(set(A["masks"]) | set(B["masks"])):
        a, b = A["masks"].get(k), B["masks"].get(k)
        mk[k] = [round(x, 6) for x in xor_area(a, b)] if a is not None and b is not None else "missing"
    g["coverlay_openings_xor_mm2"] = mk
    g["coverlay_openings_changed"] = sorted(k for k, v in mk.items() if v == "missing" or max(v) > TOL_MM2)
    zn = {}
    for k in sorted(set(A["zones"]) | set(B["zones"])):
        a, b = A["zones"].get(k), B["zones"].get(k)
        zn[k] = [round(x, 6) for x in xor_area(a, b)] if a is not None and b is not None else "missing"
    g["rule_areas_xor_mm2"] = zn
    g["contacts_same"] = A["contacts"] == B["contacts"]
    if not g["contacts_same"]:
        g["contacts"] = dict(old=A["contacts"], new=B["contacts"])
    i = rep["identity"]
    ca, cb = A["config"] or {}, B["config"] or {}
    keys = sorted(set(ca) | set(cb))
    i["config_differs_in"] = [k for k in keys if ca.get(k) != cb.get(k)]
    i["board_id"] = dict(old=ca.get("board_id"), new=cb.get("board_id"))
    i["design_hash"] = dict(old=ca.get("design_hash"), new=cb.get("design_hash"))
    i["title_block_differs_in_comment"] = [n for n in range(4) if A["title"][n] != B["title"][n]]
    i["title_block"] = dict(old=A["title"], new=B["title"])
    i["texts_differ_on_layers"] = sorted(L for L in set(A["texts"]) | set(B["texts"])
                                         if sorted(A["texts"].get(L, [])) != sorted(B["texts"].get(L, [])))
    ra, rb = project_rules(old), project_rules(new)
    rep["rules"] = dict(same=ra == rb, old_present=ra is not None, new_present=rb is not None)
    if maps:
        ma, mb = (json.loads(Path(m).read_text()) for m in maps)
        # identity and provenance fields change with the design hash and the check run; the mapping must not
        ident = {"board_id", "design_hash", "map_sha256", "verified", "provenance"}
        rep["maps"] = dict(contacts_same=ma.get("map") == mb.get("map") and ma.get("contacts") == mb.get("contacts"),
                           regions_same=ma.get("regions") == mb.get("regions"),
                           side_same=ma.get("side") == mb.get("side"),
                           other_fields_differ=sorted(k for k in set(ma) | set(mb) if k not in ident |
                                                      {"map", "contacts", "regions", "side"} and ma.get(k) != mb.get(k)),
                           ids=dict(old=ma.get("board_id"), new=mb.get("board_id")))
    geometric = (max(g["outline_xor_mm2"]) > TOL_MM2 or g["tracks"]["only_old"] or g["tracks"]["only_new"]
                 or g["vias"]["only_old"] or g["vias"]["only_new"] or g["comb_copper_changed"]
                 or g["coverlay_openings_changed"] or not g["contacts_same"]
                 or any(v == "missing" or max(v) > TOL_MM2 for v in zn.values()))
    rep["verdict"] = "geometry differs" if geometric else "same geometry (within 1e-4 mm2)"
    return rep


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("old"); ap.add_argument("new")
    ap.add_argument("--maps", nargs=2)
    ap.add_argument("--json")
    a = ap.parse_args()
    r = compare(a.old, a.new, a.maps)
    g, i = r["geometry"], r["identity"]
    print(f"{Path(a.old).name} -> {Path(a.new).name}: {r['verdict']}")
    print(f"  outline XOR {g['outline_xor_mm2']} mm2; tracks {g['tracks']}; vias {g['vias']}")
    print(f"  comb copper changed: {g['comb_copper_changed'] or 'none'}; pad counts changed: {g['comb_pad_count_changed'] or 'none'}")
    print(f"  coverlay openings changed: {g['coverlay_openings_changed'] or 'none'}; rule areas XOR {g['rule_areas_xor_mm2']}")
    print(f"  contacts same: {g['contacts_same']}; project rules same: {r['rules']['same']}")
    print(f"  ID {i['board_id']['old']} -> {i['board_id']['new']}; config differs in {i['config_differs_in']}; "
          f"title block comments differ: {i['title_block_differs_in_comment']}")
    if r["maps"]:
        print(f"  map: contact-to-region map same {r['maps']['contacts_same']}, regions same {r['maps']['regions_same']}, "
              f"side same {r['maps']['side_same']}, "
              f"other fields differ {r['maps']['other_fields_differ']}")
    if a.json:
        Path(a.json).write_text(json.dumps(r, indent=1, default=str) + "\n")


if __name__ == "__main__":
    main()
