#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors
# SPDX-License-Identifier: CERN-OHL-S-2.0
"""Sensor sole -> KiCad board (KiCad 7 Python API; run with the Python that ships pcbnew).

Reads the `<stem>.board.json` that sole_gen.py writes and builds a two-layer flex board:

  Edge.Cuts   the sole outline with its five toe tabs and the tail
  F.Cu        one footprint per sensing region: the sense comb (pad 1) and the common comb (pad 2) as
              custom-shaped SMD pads, open in F.Mask so the piezoresistive film touches them; at the
              tail end, 18 exposed contacts at 0.5 mm pitch for a ZIF flat-flex connector (J1)
  B.Cu        reserved for routing in the channels between regions: a rule area under every region
              keeps tracks and vias out, so the regions keep an even backing
  rule area   no vias within the toe-joint bend band
  Cmts.User   the generator's routing plan, as a guide
  F.Fab       notes: stack, stiffener under the contacts, licence and source location

Usage:
  python3 kicad_export.py out/sole_EU42_R_region.board.json kicad/sole_EU42_R.kicad_pcb
"""
import hashlib
import json
import math
import sys
from pathlib import Path

import pcbnew

MM = pcbnew.FromMM
X0, Y0 = 60.0, 150.0                 # place the foot frame on the page: X = x + X0, Y = Y0 - z


def V(p):
    return pcbnew.VECTOR2I(MM(p[0] + X0), MM(Y0 - p[1]))


def poly_shape(board, pts, layer, width=0.1, filled=False):
    sh = pcbnew.PCB_SHAPE(board)
    sh.SetShape(pcbnew.SHAPE_T_POLY)
    sh.SetLayer(layer)
    sh.SetWidth(MM(width))
    sh.SetFilled(filled)
    v = pcbnew.VECTOR_VECTOR2I()
    for p in pts:
        v.append(V(p))
    sh.SetPolyPoints(v)
    board.Add(sh)
    return sh


def rule_area(board, pts, layers, name, tracks=True, vias=True):
    z = pcbnew.ZONE(board)
    z.SetIsRuleArea(True)
    z.SetDoNotAllowTracks(tracks)
    z.SetDoNotAllowVias(vias)
    z.SetDoNotAllowCopperPour(True)
    z.SetDoNotAllowPads(False)
    z.SetDoNotAllowFootprints(False)
    ls = pcbnew.LSET()
    for layer in layers:
        ls.AddLayer(layer)
    z.SetLayerSet(ls)
    z.SetZoneName(name)
    o = z.Outline()
    o.NewOutline()
    for p in pts:
        o.Append(V(p).x, V(p).y)
    board.Add(z)
    return z


def text(board, s, pos, layer, size=1.2):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(s)
    t.SetPosition(V(pos))
    t.SetLayer(layer)
    t.SetTextSize(pcbnew.VECTOR2I(MM(size), MM(size)))
    t.SetTextThickness(MM(size * 0.15))
    t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_LEFT)
    board.Add(t)


def custom_pad(fp, number, net, piece):
    pts, (ax, ay) = piece["pts"], piece["anchor"]          # anchor: a point inside the piece
    pad = pcbnew.PAD(fp)
    pad.SetNumber(number)
    pad.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
    pad.SetShape(pcbnew.PAD_SHAPE_CUSTOM)
    pad.SetAnchorPadShape(pcbnew.PAD_SHAPE_CIRCLE)
    pad.SetSize(pcbnew.VECTOR2I(MM(0.1), MM(0.1)))
    ls = pcbnew.LSET(); ls.AddLayer(pcbnew.F_Cu); ls.AddLayer(pcbnew.F_Mask)
    pad.SetLayerSet(ls)
    pad.SetPosition(V((ax, ay)))
    pad.SetLocalCoord()                             # KiCad 7: store the position relative to the footprint
    a = V((ax, ay))
    v = pcbnew.VECTOR_VECTOR2I()
    for p in pts:
        q = V(p)
        v.append(pcbnew.VECTOR2I(q.x - a.x, q.y - a.y))
    pad.AddPrimitivePoly(v, 0, True)
    pad.SetNet(net)
    pad.SetLocalClearance(MM(0.15))
    fp.Add(pad)
    return pad


def mask_opening(fp, pts):
    """One coverlay/mask opening over a whole region. Per-pad openings would leave 0.2 mm coverlay webs between
    the comb fingers: too fine to cut, and 50 µm of coverlay there would hold the film off the copper."""
    sh = pcbnew.FP_SHAPE(fp)
    sh.SetShape(pcbnew.SHAPE_T_POLY)
    sh.SetLayer(pcbnew.F_Mask)
    sh.SetFilled(True)
    sh.SetWidth(0)
    o = fp.GetPosition()                            # KiCad 7 keeps footprint polygons relative to the footprint
    v = pcbnew.VECTOR_VECTOR2I()
    for p in pts:
        q = V(p)
        v.append(pcbnew.VECTOR2I(q.x - o.x, q.y - o.y))
    sh.SetPolyPoints(v)
    fp.Add(sh)
    return sh


def track(board, pts, layer, net, width):
    for p, q in zip(pts[:-1], pts[1:]):
        if abs(p[0] - q[0]) < 1e-6 and abs(p[1] - q[1]) < 1e-6:
            continue
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(V(p)); t.SetEnd(V(q)); t.SetWidth(MM(width)); t.SetLayer(layer); t.SetNet(net)
        board.Add(t)


def via(board, p, net, d, drill):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(V(p)); v.SetWidth(MM(d)); v.SetDrill(MM(drill)); v.SetNet(net)
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    board.Add(v)


def build(board_json, out_pcb):
    d = json.loads(open(board_json).read())
    fab = d["fab"]
    b = pcbnew.BOARD()
    b.SetCopperLayerCount(2)
    ds = b.GetDesignSettings()
    ds.m_TrackMinWidth = MM(0.1)
    ds.m_MinClearance = MM(0.15)
    ds.m_ViasMinSize = MM(0.4)
    ds.m_MinThroughDrill = MM(0.2)
    ds.m_ViasMinAnnularWidth = MM(0.1)
    ds.m_CopperEdgeClearance = MM(0.3)
    # coverlay: one opening per region exposes both combs (two nets) by design, so bridged apertures inside a
    # footprint are allowed; copper of any other item must keep 0.15 mm from an opening (published flex rule:
    # coverlay opening to trace >= 0.15 mm), and openings closer than 0.2 mm would leave an uncuttable web
    ds.m_AllowSoldermaskBridgesInFPs = True
    ds.m_SolderMaskToCopperClearance = MM(0.15)
    ds.m_SolderMaskMinWidth = MM(0.2)
    ds.m_SolderMaskExpansion = 0
    try:                                            # KiCad 7: default net class
        nc = ds.m_NetSettings.m_DefaultNetClass
        nc.SetClearance(MM(0.15)); nc.SetTrackWidth(MM(0.15))
        nc.SetViaDiameter(MM(0.45)); nc.SetViaDrill(MM(0.2))
    except Exception as e:                          # keep going; DRC will show the effective rules
        print("note: could not set the default net class:", e)

    # outline
    poly_shape(b, d["outline"], pcbnew.Edge_Cuts, width=0.05)

    # nets: COM and one sense net per region
    com = pcbnew.NETINFO_ITEM(b, "COM"); b.Add(com)
    names = list(d["regions"])
    nets = {}
    for n in names:
        nets[n] = pcbnew.NETINFO_ITEM(b, f"S_{n}"); b.Add(nets[n])

    # sensing regions
    for i, n in enumerate(names, 1):
        r = d["regions"][n]
        fp = pcbnew.FOOTPRINT(b)
        fp.SetFPID(pcbnew.LIB_ID("sensor_sole", "region"))
        fp.SetReference(f"S{i:02d}")
        fp.SetValue(n)
        cx = sum(p[0] for p in r["outline"]) / len(r["outline"])
        cy = sum(p[1] for p in r["outline"]) / len(r["outline"])
        fp.SetPosition(V((cx, cy)))
        fp.Reference().SetVisible(False); fp.Value().SetVisible(False)
        fp.SetAttributes(pcbnew.FP_SMD)
        for piece in r["sense"]:
            custom_pad(fp, "1", nets[n], piece)
        for piece in r["common"]:
            custom_pad(fp, "2", com, piece)
        mask_opening(fp, r.get("opening", r["outline"]))
        b.Add(fp)
        # no B.Cu tracks or vias under the region: even backing for the sensor
        rule_area(b, r["outline"], [pcbnew.B_Cu], f"keepout_{n}")

    # bend band: no vias across the toe-joint flex line (the generator clips it to the sole)
    rule_area(b, d["bend"]["band"], [pcbnew.F_Cu, pcbnew.B_Cu], "no_vias_bend_band", tracks=False, vias=True)

    # tail contacts: exposed pads at 0.5 mm pitch for a ZIF flat-flex connector. With copper routing they sit
    # on B.Cu (bottom contacts), where the sense lines arrive without vias.
    t = d["tail"]
    end, dr, lines = t["end"], t["dir"], t["lines"]
    across = (-dr[1], dr[0])
    C = d.get("contact", {"pad_len": 4.0, "pad_w": 0.30, "edge_gap": 0.5})
    pitch, pw, pl, edge_gap = fab["ffc_pitch"], C["pad_w"], C["pad_len"], C["edge_gap"]
    R = d.get("copper_routing")
    fp = pcbnew.FOOTPRINT(b)
    fp.SetFPID(pcbnew.LIB_ID("sensor_sole", "ffc_contacts"))
    fp.SetReference("J1"); fp.SetValue(f"FFC {lines}p 0.5 mm, ZIF, stiffener to 0.3 mm total")
    centre = (end[0] - dr[0] * (edge_gap + pl / 2), end[1] - dr[1] * (edge_gap + pl / 2))
    fp.SetPosition(V(centre))
    fp.Reference().SetVisible(False); fp.Value().SetVisible(False)
    fp.SetAttributes(pcbnew.FP_SMD)
    if R:
        order = R["pin_order"]
        pad_pos = {k: tuple(p) for k, p in R["pads"]}
        cu, mask = pcbnew.B_Cu, pcbnew.B_Mask
    else:
        order = (["COM"] + names + ["COM"] + ["NC"] * lines)[:lines]
        pad_pos = {k + 1: (centre[0] + across[0] * (k - (lines - 1) / 2) * pitch,
                           centre[1] + across[1] * (k - (lines - 1) / 2) * pitch) for k in range(lines)}
        cu, mask = pcbnew.F_Cu, pcbnew.F_Mask
    vertical = abs(dr[1]) > abs(dr[0])
    # Contact numbers follow the physical order, the same rule on both feet: look at the exposed contacts with
    # the tail end pointing up; contact 1 is on the left. The left sole is the mirror of the right, so the same
    # region sits on different contacts on the two feet (verify_board.py writes the map for each board).
    ux, uy = dr[0], -dr[1]                                   # tail direction on the page (Y down)
    left = (-uy, ux) if cu == pcbnew.B_Cu else (uy, -ux)     # seen from below, left and right swap
    pg = lambda q: (q[0] + X0, Y0 - q[1])
    phys = sorted(range(lines), key=lambda k: -(pg(pad_pos[k + 1])[0] * left[0] + pg(pad_pos[k + 1])[1] * left[1]))
    contact_no = {k: phys.index(k) + 1 for k in range(lines)}
    for k in range(lines):
        pad = pcbnew.PAD(fp)
        pad.SetNumber(str(contact_no[k]))
        pad.SetAttribute(pcbnew.PAD_ATTRIB_SMD)
        pad.SetShape(pcbnew.PAD_SHAPE_RECT)
        pad.SetSize(pcbnew.VECTOR2I(MM(pw), MM(pl)) if vertical else pcbnew.VECTOR2I(MM(pl), MM(pw)))
        ls = pcbnew.LSET(); ls.AddLayer(cu); ls.AddLayer(mask)
        pad.SetLayerSet(ls)
        pad.SetPosition(V(pad_pos[k + 1]))
        pad.SetLocalCoord()
        nm = order[k]
        if nm == "COM":
            pad.SetNet(com)
        elif nm in nets:
            pad.SetNet(nets[nm])
        fp.Add(pad)
    b.Add(fp)

    # copper routing from the generator: sense lanes (B.Cu), vias, stubs to the sense combs (F.Cu),
    # common net (F.Cu) and its two vias to contacts 1 and N (B.Cu)
    if R:
        for n, pts in R["lanes"].items():
            if len(pts) > 1:                                 # a line can start on F.Cu (jumper from its via)
                track(b, pts, pcbnew.B_Cu, nets[n], C["sense_w"])
        for n, p in R["vias"].items():
            via(b, p, nets[n], C["via_d"], C["via_drill"])
        for n, pts in R["stubs"].items():
            track(b, pts, pcbnew.F_Cu, nets[n], C["sense_w"])
        for pts in R["com"]:
            track(b, pts, pcbnew.F_Cu, com, C["com_w"])
        for p in R["com_vias"]:
            via(b, p, com, C["via_d"], C["via_drill"])
        for pts in R["com_pin_stubs"]:
            track(b, pts, pcbnew.B_Cu, com, C["com_w"])
        for n, pts in R.get("lanes_extra", []):             # sense lines continued after a jumper
            track(b, pts, pcbnew.B_Cu, nets[n], C["sense_w"])
        for j in R.get("jumpers", []):                       # one line hops over another on F.Cu
            track(b, j["fcu"], pcbnew.F_Cu, nets[j["net"]], C["sense_w"])
            for p in j["vias"]:
                via(b, p, nets[j["net"]], C["via_d"], C["via_drill"])

    # routing plan (guide only) and fabrication notes
    for n, pts in d["routing_plan"].items():
        for p, q in zip(pts[:-1], pts[1:]):
            sh = pcbnew.PCB_SHAPE(b); sh.SetShape(pcbnew.SHAPE_T_SEGMENT); sh.SetLayer(pcbnew.Cmts_User)
            sh.SetStart(V(p)); sh.SetEnd(V(q)); sh.SetWidth(MM(0.05)); b.Add(sh)
    xmin = min(p[0] for p in d["outline"]); zmax = max(p[1] for p in d["outline"])
    notes = [
        f"Sensor sole v0, {d['side']} foot, foot length {d['foot_length']:.0f} mm, ball width {d['ball_width']:.0f} mm",
        "2-layer polyimide flex, ~0.15 mm; combs ENIG, exposed (no coverlay over regions); B.Cu coverlay",
        "Stiffener under J1 contacts to 0.30 mm total thickness for a ZIF connector",
        "Piezoresistive film per region, adhesive spacer frame, top cover: see DESIGN.md",
        "CERN-OHL-S-2.0  Source: https://github.com/Sigurius23/Rehab-agent/tree/main/hardware/sensor-sole",
    ]
    for k, s in enumerate(notes):
        text(b, s, (xmin, zmax + 22 - k * 3.0), pcbnew.F_Fab)

    tb = b.GetTitleBlock()
    tb.SetTitle(f"Sensor sole v0 ({d['side']}, foot {d['foot_length']:.0f} mm)")
    tb.SetCompany("Rehab Agent meta-repo contributors")
    tb.SetComment(0, "CERN-OHL-S-2.0")
    tb.SetComment(1, "https://github.com/Sigurius23/Rehab-agent/tree/main/hardware/sensor-sole")
    # provenance, checked by verify_board.py: hashes of the generator files that made this board, git revision,
    # options and foot file
    src = d.get("source") or {}
    files = dict(src.get("files", {}))
    files["kicad_export"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:12]
    tb.SetComment(2, " ".join(f"{k.replace('.py', '')} {v}" for k, v in files.items()))
    opt = src.get("options", {})
    foot = src.get("foot")
    tb.SetComment(3, f"git {src.get('git')}{' +modified generator' if src.get('generator_files_modified') else ''}; "
                     f"side {opt.get('side')}, size {opt.get('size')}, exit {opt.get('exit')}"
                     + (f"; foot {foot['path']} {foot['sha256']}" if foot else ""))
    pi = b.GetPageSettings()
    try:
        pi.SetType("A3"); pi.SetPortrait(False); b.SetPageSettings(pi)
    except Exception:
        pass
    b.BuildConnectivity()
    pcbnew.SaveBoard(out_pcb, b)
    return b


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    build(sys.argv[1], sys.argv[2])
    print("wrote", sys.argv[2])
