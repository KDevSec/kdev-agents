"""state.md parser/writer for the 4-group KDev cluster state."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import re
from typing import Optional

GROUPS = ("reqs", "dev", "test", "review")
_GROUP_FIELDS = ("status", "current_step", "started_at", "completed_at", "last_progress")
_TEMPLATE_PATH = Path(__file__).parent.parent / "templates" / "state.md.tpl"


@dataclass
class StateMd:
    feature: str
    slug: str
    feature_started_at: str
    current_active_group: str
    groups: dict[str, dict[str, str]] = field(default_factory=dict)

    @classmethod
    def init(cls, path: Path, *, feature: str, slug: str, started_at: datetime, current_active_group: str = "reqs") -> "StateMd":
        tpl = _TEMPLATE_PATH.read_text(encoding="utf-8")
        text = tpl.format(
            feature=feature,
            slug=slug,
            started_at=started_at.isoformat(),
            current_active_group=current_active_group,
        )
        path.write_text(text, encoding="utf-8")
        return cls.read(path)

    @classmethod
    def read(cls, path: Path) -> "StateMd":
        text = Path(path).read_text(encoding="utf-8")
        return cls._parse(text)

    @classmethod
    def _parse(cls, text: str) -> "StateMd":
        header = _kv_block(text.split("##", 1)[0])
        groups: dict[str, dict[str, str]] = {}
        for g in GROUPS:
            m = re.search(rf"^## {g}\n(.*?)(?=^## |\Z)", text, re.MULTILINE | re.DOTALL)
            if not m:
                groups[g] = {f: "-" for f in _GROUP_FIELDS}
                continue
            groups[g] = _kv_block(m.group(1))
        return cls(
            feature=header.get("feature", ""),
            slug=header.get("feature_slug", ""),
            feature_started_at=header.get("feature_started_at", ""),
            current_active_group=header.get("current_active_group", "reqs"),
            groups=groups,
        )

    def update_group(self, group: str, **fields) -> None:
        if group not in GROUPS:
            raise ValueError(f"unknown group {group!r}; must be one of {GROUPS}")
        if "last_progress" in fields and fields["last_progress"]:
            fields["last_progress"] = fields["last_progress"][:80]
        self.groups.setdefault(group, {f: "-" for f in _GROUP_FIELDS}).update(fields)

    def write(self, path: Path) -> None:
        lines = [
            "# KDev State",
            "",
            f"feature: {self.feature}",
            f"feature_slug: {self.slug}",
            f"feature_started_at: {self.feature_started_at}",
            f"current_active_group: {self.current_active_group}",
            "",
        ]
        for g in GROUPS:
            lines.append(f"## {g}")
            for f in _GROUP_FIELDS:
                lines.append(f"{f}: {self.groups.get(g, {}).get(f, '-')}")
            lines.append("")
        Path(path).write_text("\n".join(lines), encoding="utf-8")


def _kv_block(block: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for raw in block.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        k, _, v = line.partition(":")
        out[k.strip()] = v.strip()
    return out
