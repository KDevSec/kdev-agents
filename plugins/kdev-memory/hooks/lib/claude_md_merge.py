#!/usr/bin/env python3
"""
CLAUDE.md 托管块合并（marker 化 insert-or-replace）
==================================================

kdev-memory 托管 CLAUDE.md 的「## 智能体自动记录规则」段，用一对 HTML 注释
marker 包住，使升级可以**幂等地** insert-or-replace 块内正文，绝不破坏 marker
外的用户内容（spec-kit 风格的 managed-block 惯例）。

marker（稳定可正则、配对、含 plugin 标识 `kdev-memory`）：
    <!-- BEGIN kdev-memory:智能体自动记录规则 (managed · 勿手改正文，升级会覆盖) -->
    ...managed 正文...
    <!-- END kdev-memory:智能体自动记录规则 -->

`merge_managed_section(text, managed_body)` 三分支：
  1. 有配对 marker     → 替换块内正文为 managed_body（升级路径）
  2. 无 marker 有裸段   → retrofit：把裸 `## 智能体自动记录规则` 段原样包 marker
                          （**正文语义不动**，managed_body 不参与——给老项目迁移用）
  3. 都没有            → 末尾追加 wrap_with_markers(managed_body)

无外部依赖；纯字符串操作。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

MARKER_BEGIN = "<!-- BEGIN kdev-memory:智能体自动记录规则 (managed · 勿手改正文，升级会覆盖) -->"
MARKER_END = "<!-- END kdev-memory:智能体自动记录规则 -->"

# 稳定前缀匹配——容忍 BEGIN 行尾注释（managed · ...）将来微调
_RE_BEGIN = re.compile(r"<!--\s*BEGIN kdev-memory:智能体自动记录规则.*?-->")
_RE_END = re.compile(r"<!--\s*END kdev-memory:智能体自动记录规则\s*-->")

# 裸段标题（无 marker 时的 retrofit/兼容入口）
_RE_SECTION_HEAD = re.compile(r"^##\s+智能体自动记录规则\s*$", re.MULTILINE)


def wrap_with_markers(body: str) -> str:
    """把一段正文用 BEGIN/END marker 包住（正文两端各留一行）。"""
    return f"{MARKER_BEGIN}\n{body.strip()}\n{MARKER_END}"


def _find_bare_section_span(text: str) -> tuple[int, int] | None:
    """找裸 `## 智能体自动记录规则` 段的 [start, end) 字符区间。

    end = 下一个同级/更高级标题（`# ` 或 `## `，且不是本段标题）行首，或文末。
    找不到返回 None。
    """
    m = _RE_SECTION_HEAD.search(text)
    if not m:
        return None
    start = m.start()
    rest = text[m.end():]
    nxt = re.search(r"^#{1,2}\s+\S", rest, re.MULTILINE)
    if nxt:
        end = m.end() + nxt.start()
    else:
        end = len(text)
    return (start, end)


def merge_managed_section(claude_md_text: str, managed_body: str) -> str:
    """insert-or-replace 托管块，幂等。三分支见模块 docstring。"""
    bm = _RE_BEGIN.search(claude_md_text)
    em = _RE_END.search(claude_md_text)

    # 场景 1：有配对 marker（BEGIN 在 END 之前）→ 替换块内正文
    if bm and em and bm.start() < em.end():
        before = claude_md_text[:bm.start()]
        after = claude_md_text[em.end():]
        return before + wrap_with_markers(managed_body) + after

    # 场景 2：无 marker 但有裸段 → retrofit 包住（正文不动）
    span = _find_bare_section_span(claude_md_text)
    if span:
        start, end = span
        section = claude_md_text[start:end].rstrip("\n")
        wrapped = wrap_with_markers(section)
        before = claude_md_text[:start]
        after = claude_md_text[end:]
        sep = "" if after.startswith("\n") or after == "" else "\n"
        return before + wrapped + sep + after

    # 场景 3：都没有 → 末尾追加
    base = claude_md_text.rstrip("\n")
    block = wrap_with_markers(managed_body)
    if base:
        return f"{base}\n\n{block}\n"
    return f"{block}\n"


def extract_managed_body(claude_md_text: str) -> str | None:
    """从已 marker 化的文本里取出块内正文（不含 marker）。无 marker 返回 None。"""
    bm = _RE_BEGIN.search(claude_md_text)
    em = _RE_END.search(claude_md_text)
    if bm and em and bm.end() < em.start():
        return claude_md_text[bm.end():em.start()].strip("\n")
    return None


def main() -> int:
    """CLI：`claude_md_merge.py <claude.md> <managed-body-file>` → stdout 合并结果。"""
    if len(sys.argv) != 3:
        print("usage: claude_md_merge.py <claude.md> <managed-body-file>", file=sys.stderr)
        return 2
    claude_md = Path(sys.argv[1])
    body_file = Path(sys.argv[2])
    text = claude_md.read_text(encoding="utf-8") if claude_md.is_file() else ""
    body = body_file.read_text(encoding="utf-8")
    sys.stdout.write(merge_managed_section(text, body))
    return 0


if __name__ == "__main__":
    sys.exit(main())
