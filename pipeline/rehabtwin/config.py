"""Stage configuration (JSON) and upstream-asset path resolution."""
from __future__ import annotations

import json
import os
from pathlib import Path

PIPELINE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PIPELINE_ROOT.parent
CONFIG_DIR = PIPELINE_ROOT / "configs"


def upstream_root() -> Path:
    """Where upstream clones live (scripts/clone.py puts them in <repo>/upstream)."""
    return Path(os.environ.get("REHAB_UPSTREAM", REPO_ROOT / "upstream"))


def resolve(path_str, base: Path | None = None) -> Path:
    """Resolve 'upstream:owner/repo/...' or a path relative to ``base``."""
    if path_str.startswith("upstream:"):
        p = upstream_root() / path_str[len("upstream:"):]
        if not p.exists():
            slug = "/".join(path_str[len("upstream:"):].split("/")[:2])
            raise FileNotFoundError(
                f"{p} not found. Clone the upstream repo first:\n"
                f"  python3 scripts/clone.py --only {slug}\n"
                f"(or set REHAB_UPSTREAM to the folder holding your clones)")
        return p
    p = Path(path_str)
    if not p.is_absolute() and base is not None:
        p = base / p
    return p


def load_config(name_or_path) -> dict:
    p = Path(name_or_path)
    if not p.suffix:
        p = CONFIG_DIR / f"{name_or_path}.json"
    cfg = json.loads(p.read_text())
    cfg["_path"] = str(p)
    for parent in cfg.get("extends", []):
        base = load_config(parent)
        merged = {**base, **{k: v for k, v in cfg.items() if k != "extends"}}
        for key in ("ik", "filter", "scaling", "frames"):
            if key in base and key in cfg:
                merged[key] = {**base[key], **cfg[key]}
        cfg = merged
    return cfg
