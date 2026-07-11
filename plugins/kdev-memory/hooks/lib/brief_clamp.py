"""kdev-memory brief 三字段长度闸（防 verbatim 无界 frontmatter 撑爆开局上下文）。

见 docs/superpowers/specs/2026-07-10-brief三字段长度闸-design.md。
"""
from __future__ import annotations

from typing import List, Tuple


def clamp_field(value: str, limit: int) -> str:
    """超 limit 则头部保留 + 尾部折叠指针。

    - Python str 按 code point 切片，UTF-8 不裂多字节。
    - limit <= 0 视为不限（no-op），防误配 0 把字段全砍。
    """
    if limit <= 0 or len(value) <= limit:
        return value
    folded = len(value) - limit
    return value[:limit] + f"…⟨+{folded} 字符已折叠，完整见 .kdev/memory/当前状态.md⟩"


def format_bloat_hint(bloat: List[Tuple[str, int, int]]) -> str:
    """bloat = [(field_name, orig_len, limit), ...]。空 → ""；否则一条 P1 hint 行。

    调用方保证 limit > 0（见 session-start-brief 接入点），故 orig // lim 不除零。
    """
    if not bloat:
        return ""
    items = "；".join(
        f"{name} 已 {orig} 字符（超阈值 {lim} 的 {orig // lim}×）"
        for name, orig, lim in bloat
    )
    return (
        f"  - 📈 frontmatter 字段膨胀：{items} —— "
        f"建议把旧条目归档进 每日汇总/，current_step/pending 只留短指针"
        f"（详见 dev-note 上下文消耗诊断）"
    )
