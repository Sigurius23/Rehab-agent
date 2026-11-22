#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors
# SPDX-License-Identifier: CERN-OHL-S-2.0
"""The coupon for the first build: a few cells with the printed prototype's exact stack, before a whole sole.

The coupon is a small board (115 x 80 mm, with a 60 mm tail) holding four cells and the reference cell, made by
`sole_print.build()` unchanged. So its carrier, combs, spacer, film patches, holes, vents and checks are the sole's:
  cell_s16    16 x 16 mm   about the smallest region (toe5, 249 mm2)
  cell_m30    30 x 30 mm   a mid-sized region
  cell_l45    45 x 45 mm   about the largest region (arch, 1,992 mm2)
  bend_60x12  60 x 12 mm   a long strip for the bend test (DESIGN.md section 8: baseline at a 10 mm radius)
  ref         on the tail  never loaded: drift with temperature and humidity (as on the sole)

It tests the cutting, the soldering and the film on a fraction of the material, and it is what the coupon test
(plan/nodes/t-coupon.md) measures. Nothing has been printed, cut or measured.

Usage (the generator's Python, with manifold3d and ezdxf):
  python coupon_print.py -o print/coupon                       # 0.6 mm fingers and gaps, as on the sole
  python coupon_print.py -o print/coupon_0.8 --finger 0.8 --gap 0.8   # if the cutter cannot hold 0.6 mm
"""
import argparse
import hashlib
import json
from pathlib import Path

import sole_print as SP

CELLS = {                     # name: (x0, y0, x1, y1), mm
    "cell_s16": (6, 58, 22, 74),
    "cell_m30": (28, 44, 58, 74),
    "cell_l45": (64, 29, 109, 74),
    "bend_60x12": (6, 8, 66, 20),
}
ROOT = [90.0, 3.0]            # where the wires leave the coupon for the tail
ROUTES = {                    # from each cell's hole (just outside its edge) along the gaps to the tail root
    "cell_s16": [[22.5, 60.0], [25.0, 60.0], [25.0, 26.0], [90.0, 26.0], ROOT],
    "cell_m30": [[43.0, 43.5], [43.0, 26.0], [90.0, 26.0], ROOT],
    "cell_l45": [[90.0, 28.5], [90.0, 26.0], ROOT],
    "bend_60x12": [[66.5, 14.0], [90.0, 14.0], ROOT],
}


def board():
    """The coupon as a board file that sole_print.build() reads like a sole's."""
    rect = lambda x0, y0, x1, y1: [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]
    outline = [[0, 0], [80, 0], [80, -60], [100, -60], [100, 0], [115, 0], [115, 80], [0, 80]]
    geom = dict(outline=outline, regions={n: dict(outline=rect(*c)) for n, c in CELLS.items()},
                bend=dict(point=[36.0, 14.0], dir=[0.0, 1.0]), routing_plan=ROUTES,
                tail=dict(end=[90.0, -60.0], dir=[0.0, -1.0], width=20.0))
    h = hashlib.sha256(json.dumps(geom, sort_keys=True).encode()).hexdigest()
    return dict(board_id=f"COUPON C {h[:10]}", design_hash=h, side="C", foot_length=None, ball_width=None, **geom,
                copper_routing=dict(pin_order=["COM", *CELLS, "COM"]))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-o", required=True)
    ap.add_argument("--finger", type=float, default=0.6); ap.add_argument("--gap", type=float, default=0.6)
    a = ap.parse_args()
    out = Path(a.o); out.mkdir(parents=True, exist_ok=True)
    d = board()
    bj = out / f"COUPON_C_{d['board_id'].split()[2]}.board.json"
    bj.write_text(json.dumps(d, indent=1) + "\n")
    rep = SP.build(bj, out, finger=a.finger, gap=a.gap)
    print(json.dumps({k: rep[k] for k in ("board_id", "wires", "checks")}, indent=1))
    return 0 if rep["checks"]["all_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
