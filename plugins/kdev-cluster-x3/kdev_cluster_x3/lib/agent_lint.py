"""Lint rules for agent definition .md files under an agents/ directory."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import re

ALLOWED_MODELS = {"opus", "sonnet", "haiku"}
REQUIRED_FIELDS = {"name", "description", "tools", "model"}


@dataclass(frozen=True)
class LintError:
    path: Path
    msg: str


def lint_agent_dir(root: Path) -> list[LintError]:
    root = Path(root)
    issues: list[LintError] = []
    if not root.exists():
        return issues
    for md in sorted(root.rglob("*.md")):
        issues.extend(_lint_one(md))
    return issues


def _lint_one(path: Path) -> list[LintError]:
    text = path.read_text(encoding="utf-8")
    issues: list[LintError] = []
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not m:
        issues.append(LintError(path, "missing yaml frontmatter (---/---)"))
        return issues
    fm = _parse(m.group(1))
    missing = REQUIRED_FIELDS - set(fm)
    if missing:
        issues.append(LintError(path, f"frontmatter missing fields: {sorted(missing)}"))
    model = fm.get("model", "")
    if model and model not in ALLOWED_MODELS:
        issues.append(LintError(path, f"model {model!r} not in {sorted(ALLOWED_MODELS)}"))
    name = fm.get("name", "")
    if name and path.stem != name:
        issues.append(LintError(path, f"filename {path.stem!r} vs frontmatter name {name!r}: name mismatch"))
    return issues


def _parse(block: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for raw in block.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        k, _, v = line.partition(":")
        out[k.strip()] = v.strip()
    return out
