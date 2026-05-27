"""Feature-name → safe URL/path slug. Pinyin for Chinese, ASCII passthrough otherwise."""
from __future__ import annotations
import re

try:
    from pypinyin import lazy_pinyin
    HAS_PINYIN = True
except ImportError:
    HAS_PINYIN = False


_NON_SLUG = re.compile(r"[^a-z0-9-]+")
_MULTI_DASH = re.compile(r"-{2,}")


def slugify(name: str, max_len: int = 60) -> str:
    if not name or not name.strip():
        return "feature"
    raw = name.strip()
    if HAS_PINYIN:
        raw = "-".join(lazy_pinyin(raw))
    s = raw.lower()
    s = _NON_SLUG.sub("-", s)
    s = _MULTI_DASH.sub("-", s).strip("-")
    return s[:max_len]
