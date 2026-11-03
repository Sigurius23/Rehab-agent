#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors
# SPDX-License-Identifier: CERN-OHL-S-2.0
"""Could a capacitance test tell a broken sense line from an unloaded region? Estimates only, from the routed
copper of a board; nothing here has been measured.

At zero load the film barely conducts, so an intact region and a region whose line is broken both read about
zero through the transimpedance readout. Their capacitance to the common net differs, though. An intact line
carries its comb, whose interleaved fingers face the common comb along a long gap. A line broken near the comb
keeps only the line's own capacitance to the common net, which runs above parts of the sense bundle on the
other layer.

Estimates per region:
  comb_pF   facing edge length between the sense and common combs x the capacitance per unit length of a
            periodic comb with equal finger and gap (metallisation ratio 0.5). For that geometry a conformal
            map gives K(k)/K(k') = 1, so C' = eps0 (eps_above + eps_below) / 2 per unit length of gap. Below:
            25 um polyimide, coverlay and then leather or air; above: the film and its spacer. Their
            permittivities are not known, so a range is given: (eps_above + eps_below) / 2 from 2.0 to 4.7.
  line_pF   the area where the region's B.Cu sense line lies under the F.Cu common net x eps0 x 3.4 / 25 um
            (parallel plate through the polyimide core), x 1.3 for fringing; plus the same-layer coupling of
            its F.Cu stub to nearby common copper, ignored here (stubs are short).
  drop      the share of the region's capacitance that is lost when the line breaks right at the comb: the
            worst case. A break nearer the tail loses more.
  neighbour the longest stretch over which another region's sense line runs beside this one at the bundle
            pitch, and the coupling that gives: adjacent 0.12 mm lines with 0.28 mm between them, about
            0.025-0.04 pF/mm (coplanar-strip estimate, polyimide on one side, coverlay on the other). This is a
            crosstalk path the readout must settle through after each switch; it is not a measured crosstalk.
The multiplexer, the connector and the cable add capacitance of their own. It is the same whether the line is
intact or not, but it has to be characterised per channel, and it sets how small a drop can be seen.

Usage: python3 candidates/open_line.py out/sole_EU42_R.board.json [more boards]   (plain Python + shapely)
"""
import json
import sys
from pathlib import Path

from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union

EPS0 = 8.854e-12          # F/m
PI_CORE_M = 25e-6         # polyimide core between the copper layers (FABRICATION.md)
EPS_PI = 3.4
EPS_MEAN = (2.0, 4.7)     # (eps_above + eps_below) / 2 for the comb's gap: low and high assumption
FRINGE = 1.3


def facing_length(sense, common, gap=0.2):
    """Length of the sense comb's edge that faces the common comb across one gap (mm)."""
    near = common.buffer(gap + 0.05, 8)
    return sense.boundary.intersection(near).length


def main(paths):
    out = {}
    for p in paths:
        d = json.loads(Path(p).read_text())
        R = d["copper_routing"]
        c = d["contact"]
        com = unary_union([LineString(v).buffer(c["com_w"] / 2, 8) for v in R["com"] if len(v) > 1])
        rows = {}
        for n, reg in d["regions"].items():
            sense = unary_union([Polygon(q["pts"]) for q in reg["sense"]])
            common = unary_union([Polygon(q["pts"]) for q in reg["common"]])
            L = facing_length(sense, common)                                  # mm
            comb = [EPS0 * e * L * 1e-3 * 1e12 for e in EPS_MEAN]              # pF
            lane = R["lanes"].get(n)
            ov = LineString(lane).buffer(c["sense_w"] / 2, 8).intersection(com).area if lane and len(lane) > 1 else 0.0
            line = EPS0 * EPS_PI * ov * 1e-6 / PI_CORE_M * FRINGE * 1e12       # pF
            length = LineString(lane).length if lane and len(lane) > 1 else 0.0
            nb = 0.0
            if lane and len(lane) > 1:
                band = LineString(lane).buffer(0.45, 8)
                for m, other in R["lanes"].items():
                    if m != n and other and len(other) > 1:
                        nb = max(nb, LineString(other).intersection(band).length)
            rows[n] = dict(facing_edge_mm=round(L), comb_pF=[round(x, 1) for x in comb],
                           line_mm=round(length), line_under_common_mm2=round(ov, 2), line_pF=round(line, 2),
                           drop_if_broken_at_comb_pct=[round(100 * x / (x + line)) for x in comb],
                           neighbour_parallel_mm=round(nb), neighbour_pF=[round(0.025 * nb, 1), round(0.04 * nb, 1)])
        worst = min(rows.items(), key=lambda kv: kv[1]["drop_if_broken_at_comb_pct"][0])
        out[d["board_id"]] = dict(regions=rows, smallest_drop=(worst[0], worst[1]["drop_if_broken_at_comb_pct"]),
                                  comb_pF_range=[min(r["comb_pF"][0] for r in rows.values()),
                                                 max(r["comb_pF"][1] for r in rows.values())],
                                  line_pF_max=max(r["line_pF"] for r in rows.values()),
                                  neighbour_pF_max=max(r["neighbour_pF"][1] for r in rows.values()))
        print(f"== {d['board_id']}")
        for n, r in rows.items():
            print(f"  {n:13s} comb {r['comb_pF'][0]:6.1f}-{r['comb_pF'][1]:6.1f} pF   line {r['line_mm']:4d} mm, "
                  f"{r['line_under_common_mm2']:6.2f} mm2 under COM, {r['line_pF']:6.2f} pF   "
                  f"drop if broken at comb {r['drop_if_broken_at_comb_pct'][0]}-{r['drop_if_broken_at_comb_pct'][1]} %   "
                  f"beside a neighbour {r['neighbour_parallel_mm']} mm, {r['neighbour_pF'][0]}-{r['neighbour_pF'][1]} pF")
    return out


if __name__ == "__main__":
    res = main(sys.argv[1:])
    Path(__file__).with_name("open_line.json").write_text(json.dumps(res, indent=1) + "\n")
