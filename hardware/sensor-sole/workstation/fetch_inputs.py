#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors
# SPDX-License-Identifier: CERN-OHL-S-2.0
"""Fetch the external inputs of the foot-model comparison at their pinned commits, and check them against
foot_models/PROVENANCE.json. Standard library and git only; run it with `python3 -I`.

Each repository is fetched as one commit, with only the paths needed checked out (git sparse checkout), into
DATA/inputs/<name>/. Downloaded files are only hashed here, never executed or imported. If any recorded sha256
differs, the script stops with an error and writes no inputs.env, so nothing runs on an unchecked file.

  python3 -I workstation/fetch_inputs.py --data ~/rehab-agent-data/sensor-sole

Writes DATA/inputs/inputs.env (shell exports for the tests and runners) and DATA/inputs/fetched.json (what was
fetched, from where, and what was checked).
"""
import argparse
import hashlib
import json
import shlex
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROVENANCE = ROOT / "foot_models" / "PROVENANCE.json"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def git(*args, cwd=None):
    subprocess.run(["git", *args], cwd=cwd, check=True)


def fetch(url, commit, paths, dest):
    """One commit of url, with only `paths` checked out, at dest. Reuses dest if it already holds that commit."""
    dest = Path(dest)
    if (dest / ".git").exists():
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=dest, capture_output=True, text=True).stdout.strip()
        if head == commit:
            git("sparse-checkout", "set", "--no-cone", *[f"/{p}" for p in paths], cwd=dest)
            return
        raise SystemExit(f"{dest} holds commit {head or '(none)'}, not {commit}: move it away and run again")
    dest.mkdir(parents=True, exist_ok=True)
    git("init", "-q", cwd=dest)
    git("remote", "add", "origin", url, cwd=dest)
    git("sparse-checkout", "set", "--no-cone", *[f"/{p}" for p in paths], cwd=dest)
    git("fetch", "-q", "--depth", "1", "--filter=blob:none", "origin", commit, cwd=dest)
    git("-c", "advice.detachedHead=false", "checkout", "-q", commit, cwd=dest)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", required=True, help="data folder outside the repository")
    a = ap.parse_args()
    prov = json.loads(PROVENANCE.read_text())
    inputs = Path(a.data).expanduser().resolve() / "inputs"
    if ROOT.resolve().parent.parent in (inputs, *inputs.parents):
        raise SystemExit("--data must be outside the repository: these files are not to be committed")
    (inputs / "inputs.env").unlink(missing_ok=True)    # a failed run leaves none, not an older one
    dh, syn, kin, two = prov["dhondt"], prov["synergy"], prov["kinematics"], prov["two_segment"]
    expected = {}                                   # (source name, path) -> sha256

    sources = {
        "3dpredictsim": dict(url=dh["repository"], commit=dh["commit_full"],
                             files={**dh["models"],
                                    **{k: v for k, v in dh["saved_function"].items() if k != "evaluated_with"},
                                    **dh["transcribed_from"]}),
        "synergy-based-foot-model-opensim": dict(url=syn["repository"], commit=syn["commit"], files=dict(syn["model"]),
                                                 extra=["generic_foot_model_r/Geometry"]),
        "opencap-processing": dict(url=kin["repository"], commit=kin["commit"], files={kin["file"]: kin["sha256"]}),
        "upstream/perfanalytics/pose2sim": dict(url=two["upstream"]["repository"], commit=two["upstream"]["commit"],
                                                files={}, extra=[two["upstream"]["path"]]),
    }
    record = dict(provenance=str(PROVENANCE.relative_to(ROOT)), sources={})
    for name, s in sources.items():
        dest = inputs / name
        print(f"fetching {s['url']} at {s['commit'][:12]} -> {dest}", flush=True)
        fetch(s["url"], s["commit"], list(s["files"]) + s.get("extra", []), dest)
        checked = {}
        for rel, want in s["files"].items():
            got = sha256(dest / rel)
            if got != want:
                raise SystemExit(f"sha256 mismatch for {name}/{rel}: {got}, recorded {want}. No inputs.env written.")
            checked[rel] = got
            expected[(name, rel)] = got
        record["sources"][name] = dict(url=s["url"], commit=s["commit"], checked_sha256=checked)

    # the Synergy model's bone meshes: one digest over (file name, sha256), files sorted by name
    geom = sorted((inputs / "synergy-based-foot-model-opensim" / "generic_foot_model_r" / "Geometry").glob("*.stl"))
    h = hashlib.sha256()
    for g in geom:
        h.update(g.name.encode()); h.update(sha256(g).encode())
    want = syn["geometry_digest"]
    if len(geom) != want["files"] or h.hexdigest() != want["sha256_of_names_and_hashes"]:
        raise SystemExit(f"Synergy geometry: {len(geom)} files, digest {h.hexdigest()}; recorded {want['files']} "
                         f"files, {want['sha256_of_names_and_hashes']}. No inputs.env written.")
    record["sources"]["synergy-based-foot-model-opensim"]["geometry_digest"] = h.hexdigest()

    nominal = inputs / "3dpredictsim" / "OpenSimModel" / "Nominal models"
    env = dict(DHONDT_NOMINAL_DIR=nominal,
               DHONDT_EXP5=inputs / "3dpredictsim" / next(k for k in dh["saved_function"] if k != "evaluated_with"),
               SYNERGY_MODEL=inputs / "synergy-based-foot-model-opensim" / next(iter(syn["model"])),
               SQUAT_MOT=inputs / "opencap-processing" / kin["file"],
               REHAB_UPSTREAM=inputs / "upstream")
    (inputs / "fetched.json").write_text(json.dumps(record, indent=1) + "\n")
    (inputs / "inputs.env").write_text("# written by workstation/fetch_inputs.py; every file checked against "
                                       "foot_models/PROVENANCE.json\n"
                                       + "".join(f"export {k}={shlex.quote(str(v))}\n" for k, v in env.items()))
    print(f"all {len(expected)} recorded hashes and the Synergy geometry digest match; wrote {inputs / 'inputs.env'}")


if __name__ == "__main__":
    sys.exit(main())
