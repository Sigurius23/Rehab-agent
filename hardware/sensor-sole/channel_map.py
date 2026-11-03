#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors
# SPDX-License-Identifier: CERN-OHL-S-2.0
"""Deployed channel maps: which region each tail contact (and pod channel) reads, for one exact sole.

A sole carries a printed ID on its tail: a label (EU size, measured length or foot file), the side, and the
first 10 hex digits of its design hash, e.g. "EU42 R 3f9a1c07b2". verify_board.py writes one map package per
board that passed its checks; the pod or host resolves the printed ID to that package. Resolution fails
closed:
  - an ID that is not of that form;
  - no package with that ID, or more than one;
  - a package for the other side;
  - a package whose content does not match its own hash (edited or damaged);
  - a package whose map is inconsistent (COM not on the first and last contact, a region missing, twice or
    unknown);
  - any unreadable file among the packages (it could have been the right one).
Plain Python, no KiCad needed. Usage:
  python3 channel_map.py resolve "EU42 R 3f9a1c07b2" --side R --maps maps/
  python3 channel_map.py check maps/
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

FORMAT = "sensor-sole-channel-map/1"
ID_RE = re.compile(r"^(\S+) ([LR]) ([0-9a-f]{10})$")


class MapError(Exception):
    """No single, intact, matching map: do not label channels by region."""


def content_hash(pkg):
    body = {k: v for k, v in pkg.items() if k != "map_sha256"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def file_name(board_id):
    if not ID_RE.match(board_id or ""):
        raise MapError(f"not a board ID: {board_id!r}")
    return board_id.replace(" ", "_") + ".json"


def normalise_id(text):
    """An ID as read off a sole: surrounding space and repeated spaces removed; nothing else is guessed."""
    t = " ".join((text or "").split())
    if not ID_RE.match(t):
        raise MapError(f"not a board ID: {text!r} (expected '<label> <L|R> <10 hex digits>')")
    return t


def validate(pkg, source="package"):
    if pkg.get("format") != FORMAT:
        raise MapError(f"{source}: unknown format {pkg.get('format')!r}")
    if pkg.get("map_sha256") != content_hash(pkg):
        raise MapError(f"{source}: content does not match its hash (edited or damaged)")
    bid = pkg.get("board_id")
    m = ID_RE.match(bid or "")
    if not m:
        raise MapError(f"{source}: bad board ID {bid!r}")
    if m.group(2) != pkg.get("side"):
        raise MapError(f"{source}: ID side {m.group(2)} differs from package side {pkg.get('side')}")
    if not (pkg.get("design_hash") or "").startswith(m.group(3)):
        raise MapError(f"{source}: ID does not match the design hash")
    n = pkg.get("contacts")
    mp = pkg.get("map") or {}
    if sorted(mp, key=int) != [str(i) for i in range(1, (n or 0) + 1)]:
        raise MapError(f"{source}: map does not cover contacts 1..{n}")
    if mp["1"] != "COM" or mp[str(n)] != "COM":
        raise MapError(f"{source}: COM is not on contacts 1 and {n}")
    sense = [mp[str(i)] for i in range(2, n)]
    if sorted(sense) != sorted(pkg.get("regions") or []) or len(set(sense)) != len(sense):
        raise MapError(f"{source}: sense contacts do not name each region exactly once")
    return pkg


def load_all(maps_dir):
    maps_dir = Path(maps_dir)
    if not maps_dir.is_dir():
        raise MapError(f"no map directory {maps_dir}")
    out = []
    for f in sorted(maps_dir.glob("*.json")):
        try:
            pkg = json.loads(f.read_text())
        except (OSError, ValueError) as e:
            raise MapError(f"{f.name}: unreadable ({e}); refusing to resolve with a damaged map set")
        out.append((f, validate(pkg, f.name)))
    return out


def resolve(printed_id, side, maps_dir):
    """The one map package for this sole, or MapError."""
    bid = normalise_id(printed_id)
    if side not in ("L", "R"):
        raise MapError(f"side must be L or R, not {side!r}")
    if ID_RE.match(bid).group(2) != side:
        raise MapError(f"sole {bid!r} is a {ID_RE.match(bid).group(2)} sole, worn on the {side} foot")
    hits = [(f, p) for f, p in load_all(maps_dir) if p["board_id"] == bid]
    if not hits:
        raise MapError(f"no verified map for {bid!r}")
    if len(hits) > 1:
        raise MapError(f"{len(hits)} maps for {bid!r} ({', '.join(f.name for f, _ in hits)}): ambiguous")
    return hits[0][1]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("resolve"); r.add_argument("board_id"); r.add_argument("--side", required=True)
    r.add_argument("--maps", required=True)
    c = sub.add_parser("check"); c.add_argument("maps")
    a = ap.parse_args()
    try:
        if a.cmd == "resolve":
            pkg = resolve(a.board_id, a.side, a.maps)
            print(json.dumps(dict(board_id=pkg["board_id"], board_sha256=pkg["verified"]["board_sha256"],
                                  map=pkg["map"]), indent=1))
        else:
            pkgs = load_all(a.maps)
            ids = [p["board_id"] for _, p in pkgs]
            dup = sorted({i for i in ids if ids.count(i) > 1})
            if dup:
                raise MapError(f"IDs with more than one map: {dup}")
            print(f"{len(pkgs)} maps, all intact and unambiguous")
    except MapError as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
