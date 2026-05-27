"""handoffs/<group>/COMPLETE.md write+read with yaml-style frontmatter."""
from __future__ import annotations
from datetime import datetime
from pathlib import Path
import re

GROUPS = ("reqs", "dev", "test", "review")
_TPL_DIR = Path(__file__).parent.parent / "templates" / "handoffs"


class HandoffMissing(FileNotFoundError): pass
class HandoffMalformed(ValueError): pass


def write_complete(path: Path, *, group: str, completed_at: datetime, **fields) -> None:
    if group not in GROUPS:
        raise ValueError(f"unknown group {group!r}; must be one of {GROUPS}")
    tpl = (_TPL_DIR / f"{group}.complete.md.tpl").read_text(encoding="utf-8")
    text = tpl.format(completed_at=completed_at.isoformat(), **fields)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def read_complete(path: Path) -> dict:
    p = Path(path)
    if not p.exists():
        raise HandoffMissing(str(p))
    text = p.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not m:
        raise HandoffMalformed(f"no frontmatter in {p}")
    return _parse_yaml_ish(m.group(1))


def _parse_yaml_ish(block: str) -> dict:
    # minimal yaml: top-level k: v; nested k:\n  k2: v2; lists [a, b, c]
    out: dict = {}
    lines = block.splitlines()
    i = 0
    while i < len(lines):
        raw = lines[i]
        if not raw.strip() or raw.strip().startswith("#"):
            i += 1
            continue
        if ":" not in raw:
            i += 1
            continue
        key, _, val = raw.partition(":")
        key = key.strip()
        val = val.strip()
        if val == "" and i + 1 < len(lines) and lines[i + 1].startswith("  "):
            sub: dict = {}
            i += 1
            while i < len(lines) and lines[i].startswith("  "):
                sk, _, sv = lines[i].strip().partition(":")
                sub[sk.strip()] = sv.strip()
                i += 1
            out[key] = sub
            continue
        if val.startswith("[") and val.endswith("]"):
            out[key] = [x.strip() for x in val[1:-1].split(",") if x.strip()]
        else:
            out[key] = val
        i += 1
    return out
