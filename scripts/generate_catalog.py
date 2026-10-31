#!/usr/bin/env python3
"""Regenerate repos.csv, repos.yaml and docs/catalog.md from catalog/repos.json (source of truth). Stdlib only."""
import csv, io, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
D=json.loads((ROOT/"catalog"/"repos.json").read_text())
repos=D["repos"]
# CSV
buf=io.StringIO(); wr=csv.writer(buf)
wr.writerow(["id","slug","url","category","tier","pipeline_stages","language","license","stars_snapshot","forks_snapshot","updated_snapshot","private","tags","description","notes","upstream_path"])
for r in repos:
    wr.writerow([r["id"],r["slug"],r["url"],r["category"],r["tier"],"|".join(r["pipeline_stages"]),r["language"] or "",r["license"],r["stars_snapshot"] if r["stars_snapshot"] is not None else "",r["forks_snapshot"] if r["forks_snapshot"] is not None else "",r["updated_snapshot"],r["private"],"|".join(r["tags"]),r["description"],r["notes"],r["upstream_path"]])
(ROOT/"catalog"/"repos.csv").write_text(buf.getvalue(),encoding="utf-8")
# YAML (simple, quoted scalars — generated, do not hand-edit)
def q(v):
    if v is None: return "null"
    if isinstance(v,bool): return "true" if v else "false"
    return '"' + str(v).replace("\\","\\\\").replace('"','\\"') + '"'
lines=["# GENERATED from catalog/repos.json by scripts/generate_catalog.py — do not hand-edit.","repos:"]
for r in repos:
    lines.append(f"  - slug: {q(r['slug'])}")
    for k in ["url","category","tier","language","license","updated_snapshot","description","notes","upstream_path"]:
        lines.append(f"    {k}: {q(r.get(k))}")
    lines.append(f"    stars_snapshot: {r['stars_snapshot'] if r['stars_snapshot'] is not None else 'null'}")
    lines.append(f"    forks_snapshot: {r['forks_snapshot'] if r['forks_snapshot'] is not None else 'null'}")
    lines.append(f"    private: {q(r['private'])}")
    lines.append("    pipeline_stages: [" + ", ".join(q(s) for s in r["pipeline_stages"]) + "]")
    lines.append("    tags: [" + ", ".join(q(s) for s in r["tags"]) + "]")
(ROOT/"catalog"/"repos.yaml").write_text("\n".join(lines)+"\n",encoding="utf-8")
# Markdown catalog: summary tables grouped by category, then full per-repo documentation
out=[f"# Full catalog — all {len(repos)} repositories","",
"Generated from `catalog/repos.json` by `scripts/generate_catalog.py`. Do not hand-edit this file; edit the JSON and regenerate.","","## Documentation standard","",
D.get("documentation_standard",""),
"",
"Stars/forks/updated are dated snapshots, **not live data** (see the `snapshot_note` in `catalog/repos.json`). "
"Licenses were verified against the GitHub API or the repo-root license file on the date in each entry's `license_source`; "
"a repo with **no license file is all-rights-reserved by default** and must not be copied/redistributed until cleared. "
"Model weights and datasets frequently carry separate terms from code — the entry's notes flag known cases.",""]
for cat,label in D["categories"].items():
    rows=[r for r in repos if r["category"]==cat]
    if not rows: continue
    out.append(f"## {cat} — {label} ({len(rows)})\n")
    out.append("| # | Repository | Tier | Stages | Lang | License | ★ snapshot | Description |")
    out.append("|---:|---|---|---|---|---|---:|---|")
    for r in rows:
        stages=", ".join(r["pipeline_stages"])
        lic=r["license"].split(" (")[0]
        out.append(f"| {r['id']} | [{r['slug']}]({r['url']}){' 🔒' if r['private'] else ''} | {r['tier']} | {stages} | {r['language'] or '—'} | {lic} | {r['stars_snapshot'] if r['stars_snapshot'] is not None else '—'} | {r['description']} |")
    out.append("")
out.append("## Repository details — every repo, fully documented\n")
for r in repos:
    out.append(f"### {r['id']}. [{r['slug']}]({r['url']}){' 🔒 private' if r['private'] else ''}")
    out.append("")
    out.append(f"- **What it is:** {r['description']}")
    out.append(f"- **Why it's in this catalog:** {r['notes']}")
    out.append(f"- **Category / tier:** {r['category']} / {r['tier']}")
    out.append(f"- **Pipeline stages:** {', '.join(r['pipeline_stages'])}")
    out.append(f"- **Tags:** {', '.join(r['tags'])}")
    out.append(f"- **Primary language (GitHub):** {r['language'] or 'none reported'}")
    out.append(f"- **License:** {r['license']} _(source: {r.get('license_source','not recorded')})_")
    stars = r['stars_snapshot'] if r['stars_snapshot'] is not None else 'not recorded'
    forks = r['forks_snapshot'] if r['forks_snapshot'] is not None else 'not recorded'
    out.append(f"- **Snapshot:** ★ {stars} · forks {forks} · upstream updated {r['updated_snapshot']}")
    out.append(f"- **Clone target when vendored:** `{r['upstream_path']}` (never commit upstream code to this repo)")
    out.append("")
(ROOT/"docs").mkdir(exist_ok=True)
(ROOT/"docs"/"catalog.md").write_text("\n".join(out),encoding="utf-8")
print(f"Generated catalog/repos.csv, catalog/repos.yaml, docs/catalog.md from {len(repos)} repos.")
