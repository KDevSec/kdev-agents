"""Lint kdev-cluster-x3 standards/ directory."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class StandardsIssue:
    path: Path
    msg: str


def lint_standards_dir(root: Path) -> list[StandardsIssue]:
    root = Path(root)
    issues: list[StandardsIssue] = []
    if not root.exists():
        return issues
    # 1) all review checklists must have "verdict" token
    for md in sorted((root / "review").glob("*-checklist.md")):
        text = md.read_text(encoding="utf-8")
        if "verdict" not in text:
            issues.append(StandardsIssue(md, "checklist missing 'verdict' token"))
    # 2) all system-prompt-template.md must have aggregation + emergency sections
    for md in sorted(root.rglob("system-prompt-template.md")):
        text = md.read_text(encoding="utf-8")
        if "## 聚合模板" not in text:
            issues.append(StandardsIssue(md, "missing '## 聚合模板' section"))
        if "## 应急模板" not in text and "## 应急" not in text:
            issues.append(StandardsIssue(md, "missing '## 应急模板' section"))
    return issues
