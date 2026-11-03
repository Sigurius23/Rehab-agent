#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors
# SPDX-License-Identifier: CERN-OHL-S-2.0
"""Negative controls for verify_board.py: take a board that passes, break it in one known way, and require the
checker to fail for that reason. An unbroken copy must pass.

Run with the Python that ships KiCad's pcbnew (each case runs the full check, about 2-3 minutes):
  python3 tests/test_verify_negative.py kicad/sole_EU42_R.kicad_pcb [case ...]
"""
import json
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import pcbnew  # noqa: E402
import verify_board as V  # noqa: E402

MM = pcbnew.FromMM


def j1(b):
    return next(f for f in b.GetFootprints() if f.GetReference() == "J1")


def pad(fp, num):
    return next(p for p in fp.Pads() if p.GetNumber() == str(num))


def region(b, name):
    return next(f for f in b.GetFootprints() if f.GetValue() == name)


def add_track(b, a, c, layer, net=None, width=0.12):
    t = pcbnew.PCB_TRACK(b)
    t.SetStart(a); t.SetEnd(c); t.SetLayer(layer); t.SetWidth(MM(width))
    if net is not None:
        t.SetNet(net)
    b.Add(t)


def short_two_contacts(b):
    p2, p3 = pad(j1(b), 2), pad(j1(b), 3)
    add_track(b, p2.GetPosition(), p3.GetPosition(), pcbnew.B_Cu, p2.GetNet())


def cut_one_region_off(b):
    net = b.FindNet("S_heel_post")
    for t in list(b.GetTracks()):
        if t.GetNetCode() == net.GetNetCode() and t.GetClass() != "PCB_VIA" and t.GetLayer() == pcbnew.F_Cu:
            b.Remove(t)                                       # the stub from its via to its sense comb


def float_a_comb_piece(b):
    fp = region(b, "heel_lat")
    src = next(p for p in fp.Pads() if p.GetNumber() == "1")
    dup = pcbnew.PAD(src)                                     # a copy of a sense piece, not touching its comb
    dup.SetPosition(pcbnew.VECTOR2I(src.GetPosition().x, src.GetPosition().y + MM(400)))
    fp.Add(dup)


def config_names_wrong_region(b):
    for d in b.GetDrawings():
        if d.GetClass() in ("PCB_TEXT", "PTEXT") and d.GetText().startswith("sensor-sole-config "):
            cfg = json.loads(d.GetText()[len("sensor-sole-config "):])
            cfg["regions"] = [("heel_xx" if r == "heel_post" else r) for r in cfg["regions"]]
            d.SetText("sensor-sole-config " + json.dumps(cfg, separators=(",", ":")))


def swap_contact_numbers(b):
    p2, p3 = pad(j1(b), 2), pad(j1(b), 3)
    p2.SetNumber("3"); p3.SetNumber("2")


def swap_contact_labels(b):
    p2, p3 = pad(j1(b), 2), pad(j1(b), 3)
    n2, n3 = p2.GetNet(), p3.GetNet()
    p2.SetNet(n3); p3.SetNet(n2)


def shrink_an_opening(b):
    fp = region(b, "mt2")
    sh = next(g for g in fp.GraphicalItems() if g.GetLayer() == pcbnew.F_Mask)
    poly = sh.GetPolyShape()                                  # relative to the footprint
    pts = [poly.CVertex(i) for i in range(poly.TotalVertices())]
    cx = sum(p.x for p in pts) / len(pts); cy = sum(p.y for p in pts) / len(pts)
    v = pcbnew.VECTOR_VECTOR2I()
    for p in pts:
        v.append(pcbnew.VECTOR2I(int(cx + 0.8 * (p.x - cx)), int(cy + 0.8 * (p.y - cy))))
    sh.SetPolyPoints(v)


def track_in_margin(b):
    z = next(z for z in b.Zones() if z.GetZoneName().startswith("margin_"))
    o = z.Outline()
    a = o.CVertex(0); c = o.CVertex(1)
    mid = pcbnew.VECTOR2I((a.x + c.x) // 2, (a.y + c.y) // 2)
    bb = b.GetBoardEdgesBoundingBox()
    inward = pcbnew.VECTOR2I(bb.GetCenter().x - mid.x, bb.GetCenter().y - mid.y)
    n = (inward.x ** 2 + inward.y ** 2) ** 0.5
    p = pcbnew.VECTOR2I(int(mid.x + inward.x / n * MM(1.0)), int(mid.y + inward.y / n * MM(1.0)))
    add_track(b, p, pcbnew.VECTOR2I(p.x + MM(0.5), p.y), pcbnew.B_Cu)


def alter_printed_id(b):
    for d in b.GetDrawings():
        if d.GetClass() in ("PCB_TEXT", "PTEXT") and d.GetLayer() == pcbnew.F_SilkS:
            t = d.GetText(); d.SetText(t[:-1] + ("0" if t[-1] != "0" else "1"))


def alter_generator_hash(b):
    tb = b.GetTitleBlock()
    tb.SetComment(2, tb.GetComment(2).replace("sole_route ", "sole_route 0", 1)[:len(tb.GetComment(2))])


CASES = {                       # name: (fault, text that must appear in a problem; None = must pass)
    "control (unchanged)": (None, None),
    "short between two contacts": (short_two_contacts, "other contacts"),
    "region cut off from its contact": (cut_one_region_off, "reached from no contact"),
    "comb piece disconnected": (float_a_comb_piece, "comb pieces not all connected"),
    "configuration names a wrong region": (config_names_wrong_region, "differ from its configuration"),
    "contact numbers swapped": (swap_contact_numbers, "physical contact order"),
    "contact net labels swapped (map)": (swap_contact_labels, "reaches sense"),
    "coverlay opening shrunk": (shrink_an_opening, "under coverlay"),
    "track in the copper-free margin": (track_in_margin, "DRC:"),
    "printed ID altered": (alter_printed_id, "printed ID"),
    "generator hash altered": (alter_generator_hash, "generator files changed"),
    "project rules file missing": ("no_pro", "design rules would be KiCad defaults"),
}


def main():
    src = Path(sys.argv[1]).resolve()
    only = sys.argv[2:]
    failures = 0
    for name, (fault, expect) in CASES.items():
        if only and name not in only:
            continue
        with tempfile.TemporaryDirectory() as d:
            dst = Path(d) / src.name
            board = pcbnew.LoadBoard(str(src))
            if callable(fault):
                fault(board)
            pcbnew.SaveBoard(str(dst), board)
            if fault != "no_pro":
                shutil.copy(src.with_suffix(".kicad_pro"), dst.with_suffix(".kicad_pro"))
            r = V.check(dst)
            probs = r["problems"]
            if expect is None:
                ok = r["ok"]
            else:
                ok = (not r["ok"]) and any(expect in p for p in probs)
            failures += not ok
            print(f"{'ok  ' if ok else 'FAIL'} {name}: {'passes' if r['ok'] else probs[0][:150]}"
                  + ("" if ok or expect is None else f"  (expected '{expect}'; got {[p[:80] for p in probs]})"),
                  flush=True)
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
