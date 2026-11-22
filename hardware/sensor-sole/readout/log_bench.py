#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors
# SPDX-License-Identifier: CERN-OHL-S-2.0
"""Log the bench readout (sole_bench.ino) to CSV, with each cell's film conductance.

  python readout/log_bench.py /dev/ttyACM0 --names cell_s16 cell_m30 cell_l45 bend_60x12
  python readout/log_bench.py COM5 --out run1.csv --seconds 60

Every frame gives raw ADC counts; the conversion is ratiometric, so the ADC reference cancels:
    G = (Vout / Vbias - 1) / Rf        (siemens; reported in microsiemens)
with Vout and Vbias in the same counts, and Rf from the firmware's header (set it with --rf if it differs:
the firmware only records the value it is told). A channel within 2 counts of full scale is flagged saturated.

Recordings of a person wearing the sole are health data: they stay outside the repository. The default output
folder is ~/rehab-agent-data/sole-bench/. Needs pyserial for the port; the parsing itself is standard library.
"""
import argparse
import csv
import datetime
import sys
import time
from pathlib import Path

FULL = 4095                      # 12-bit


def parse_header(line):
    """'H,fw=...,lines=5,...' -> dict, numbers as int where they are."""
    out = {}
    for kv in line.strip().split(",")[1:]:
        k, _, v = kv.partition("=")
        out[k] = int(v) if v.isdigit() else v
    return out


def parse_frame(line, lines):
    """'F,t,sync_n,sync_t,vbias,ref,c0..' -> dict, or None if malformed."""
    p = line.strip().split(",")
    if not p or p[0] != "F" or len(p) != 6 + lines:
        return None
    try:
        v = [int(x) for x in p[1:]]
    except ValueError:
        return None
    return dict(t_us=v[0], sync_n=v[1], sync_t_us=v[2], vbias=v[3], ref=v[4], ch=v[5:])


def conductance_us(counts, vbias, rf_ohm):
    """Film conductance in microsiemens from the amplifier's output and the bias, both in ADC counts."""
    if vbias <= 0 or rf_ohm <= 0:
        return None
    return max(counts / vbias - 1.0, 0.0) / rf_ohm * 1e6


def rows(lines_iter, names=None, rf=None, rf_ref=None):
    """Yield (header dict, row dict) per frame from an iterator of text lines."""
    hdr = None
    for line in lines_iter:
        if line.startswith("H,"):
            hdr = parse_header(line)
            continue
        if hdr is None:
            continue
        f = parse_frame(line, hdr["lines"])
        if f is None:
            continue
        r_mux, r_ref = rf or hdr["rf_ohm"], rf_ref or hdr["rf_ref_ohm"]
        nm = list(names or [])[: hdr["lines"]] + [f"ch{i}" for i in range(len(names or []), hdr["lines"])]
        row = dict(t_us=f["t_us"], sync_n=f["sync_n"], sync_t_us=f["sync_t_us"], vbias=f["vbias"], ref=f["ref"],
                   ref_uS=conductance_us(f["ref"], f["vbias"], r_ref))
        sat = []
        for n, c in zip(nm, f["ch"]):
            row[n] = c
            row[f"{n}_uS"] = conductance_us(c, f["vbias"], r_mux)
            if c >= FULL - 2:
                sat.append(n)
        row["saturated"] = " ".join(sat)
        yield hdr, row


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("port"); ap.add_argument("--names", nargs="*")
    ap.add_argument("--rf", type=float, help="multiplexed Rf, ohm, if not the firmware's")
    ap.add_argument("--rf-ref", type=float, help="reference Rf, ohm, if not the firmware's")
    ap.add_argument("--out", help="CSV path (default: ~/rehab-agent-data/sole-bench/<time>.csv)")
    ap.add_argument("--seconds", type=float, default=0, help="stop after this long (0: until Ctrl-C)")
    a = ap.parse_args()
    import serial                                                    # pyserial
    out = Path(a.out) if a.out else Path.home() / "rehab-agent-data" / "sole-bench" / (
        datetime.datetime.now().strftime("%Y%m%d-%H%M%S") + ".csv")
    out.parent.mkdir(parents=True, exist_ok=True)
    port = serial.Serial(a.port, 115200, timeout=1)
    t_end = time.time() + a.seconds if a.seconds else None

    def text():
        while t_end is None or time.time() < t_end:
            b = port.readline()
            if b:
                yield b.decode("ascii", "replace")

    n, writer, fh = 0, None, None
    try:
        for hdr, row in rows(text(), a.names, a.rf, a.rf_ref):
            if writer is None or list(row) != writer.fieldnames:
                if fh:
                    fh.close()
                fh = open(out, "a", newline="")
                fh.write("# " + " ".join(f"{k}={v}" for k, v in hdr.items()) + "\n")
                writer = csv.DictWriter(fh, fieldnames=list(row)); writer.writeheader()
            writer.writerow(row); n += 1
    except KeyboardInterrupt:
        pass
    finally:
        if fh:
            fh.close()
    print(f"{n} frames -> {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
