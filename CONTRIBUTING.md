# Contributing

## Add or re-tier a repository
1. Edit `catalog/repos.json` (one entry; keep `url` = `https://github.com/<slug>`).
2. `python3 scripts/generate_catalog.py` — regenerates CSV/YAML/`docs/catalog.md`.
3. `python3 scripts/validate_catalog.py` — must pass.
4. If re-tiering, add the evidence (install test, validation result) to `docs/evaluation.md` or `docs/roadmap.md`.

## Documentation standard (enforced by the validator + tests)
Every repo entry must document: `slug`, `url`, `description` (≥40 chars, factual),
`category`, `tier`, `pipeline_stages` (≥1), `tags` (≥2), `language` (or an explicit
"GitHub reports no primary language" note), `license` + `license_source` (verified
against the GitHub API or the repo-root license file; "none found" entries are
all-rights-reserved and must not be copied), stars/forks/updated snapshots (private
repo exempt), `notes` (≥30 chars: the repo's role in this project + caveats), and
`upstream_path`. Run `scripts/enrich_metadata.py` (with `GITHUB_TOKEN`) to refresh
live metadata; re-verify licenses whenever entries are added.

## Rules
- No upstream code, model weights, datasets, or patient data in this repo.
- Descriptions must be factual and sourced from the upstream README.
- Note license/weight gating in the entry's `notes` field whenever it exists.
