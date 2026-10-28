#!/usr/bin/env python3
"""Validate catalog/repos.json against the documentation standard. Stdlib only. Exits non-zero on any problem.

Standard (also stated in repos.json `documentation_standard`): every entry documents
slug, url, description (>=40 chars), category, tier, pipeline_stages (>=1), tags (>=2),
language (or explicit exception below), license + license_source, stars/forks/updated
snapshots (private repo exempt), notes (>=30 chars), upstream_path.
"""
import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
D=json.loads((ROOT/"catalog"/"repos.json").read_text())
errs=[]
slugs=[r["slug"].lower() for r in D["repos"]]
if len(slugs)!=len(set(slugs)): errs.append("duplicate slugs")
if D["count"]!=len(D["repos"]): errs.append(f"count field {D['count']} != {len(D['repos'])} repos")
# Repos where GitHub itself reports no primary language (verified via API, 2026-10-28)
NO_LANGUAGE_OK={"andy-cheng/flex4dhuman","ntuywang103/vidihand","lnsgroup/ms-human-700","netease-gameai/choreomaster","ollieboyne/foot3d"}
for r in D["repos"]:
    s=r["slug"]
    if r["url"]!=f"https://github.com/{s}": errs.append(f"url mismatch: {s}")
    if r["category"] not in D["categories"]: errs.append(f"bad category: {s}")
    if r["tier"] not in D["tiers"]: errs.append(f"bad tier: {s}")
    if not r["pipeline_stages"]: errs.append(f"no pipeline stages: {s}")
    for st in r["pipeline_stages"]:
        if st not in D["pipeline_stages"]: errs.append(f"bad stage {st}: {s}")
    if len(r.get("description") or "")<40: errs.append(f"description too short (<40 chars): {s}")
    if len(r.get("notes") or "")<30: errs.append(f"notes too short (<30 chars): {s}")
    if len(r.get("tags") or [])<2: errs.append(f"fewer than 2 tags: {s}")
    if not r.get("license"): errs.append(f"missing license: {s}")
    if not r.get("license_source"): errs.append(f"missing license_source: {s}")
    if not r.get("updated_snapshot"): errs.append(f"missing updated_snapshot: {s}")
    if not r.get("upstream_path"): errs.append(f"missing upstream_path: {s}")
    if not r["private"]:
        if not r.get("language") and s.lower() not in NO_LANGUAGE_OK:
            errs.append(f"missing language: {s}")
        if r.get("stars_snapshot") is None: errs.append(f"missing stars_snapshot: {s}")
        if r.get("forks_snapshot") is None: errs.append(f"missing forks_snapshot: {s}")
print("\n".join(errs) if errs else f"OK: {len(D['repos'])} repos, catalog is valid and fully documented.")
sys.exit(1 if errs else 0)
