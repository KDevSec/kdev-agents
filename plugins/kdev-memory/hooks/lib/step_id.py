"""kdev-memory v0.11 Step ID 加分支前缀机制。

提供：
- compute_branch_slug(): 把当前 git 分支名转成可放在文件名/Step ID 里的 slug
- read_counter(slug, state_dir): 读取分支独立计数器（后续 task 实现）
- increment_counter(slug, state_dir): atomic 递增（后续 task 实现）
- mint_next_step_id(state_dir): 一站式（后续 task 实现）

被 SKILL.md 引用：模型在写 Step 条目前调用 mint_next_step_id() 拿 ID。
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Optional


STRIPPED_PREFIXES = ("feature/", "feat/")


def _git_query(*args: str) -> Optional[str]:
    try:
        r = subprocess.run(
            ["git", *args], capture_output=True, text=True, check=False,
        )
    except (OSError, FileNotFoundError):
        return None
    if r.returncode != 0:
        return None
    return r.stdout.strip()


def _sanitize_slug(s: str) -> str:
    """非 [a-zA-Z0-9\\-_] 一律转 -，连续 - 合并，去首尾 -。空字符串 fallback 'unknown'。"""
    s = re.sub(r"[^a-zA-Z0-9\-_]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s or "unknown"


def compute_branch_slug() -> str:
    """当前 git 分支 → slug。"""
    branch = _git_query("rev-parse", "--abbrev-ref", "HEAD")
    if branch is None:
        return "unknown"
    if branch == "HEAD":
        return "detached"
    for prefix in STRIPPED_PREFIXES:
        if branch.startswith(prefix):
            branch = branch[len(prefix):]
            break
    return _sanitize_slug(branch)
