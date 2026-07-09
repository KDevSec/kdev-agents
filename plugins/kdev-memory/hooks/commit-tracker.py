#!/usr/bin/env python3
"""kdev-memory PostToolUse hook on Bash: 检测 git commit + 累积 pending-commits.json。

R-001 v1 task 3。

Suppress 规则：commit message 含 regex `\\(.*?task\\s+\\d+/\\d+.*?\\)`
（即圆括号内有 "task N/M"）→ 视为 subagent-driven 高频 batch，不计入 pending。
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
LIB_DIR = SCRIPT_DIR / "lib"
sys.path.insert(0, str(LIB_DIR))

from _utf8 import force_utf8_stdio  # noqa: E402
force_utf8_stdio()

from pending_commits import append  # noqa: E402
from coexist import defer_to_ieidev  # noqa: E402

SUPPRESS = json.dumps({"continue": True, "suppressOutput": True})

# regex 抓"圆括号内含 task N/M"——commit message 末尾常见 "(Q-003 task 3/13)" 形式
_TASK_BATCH_RE = re.compile(r"\(.*?task\s+\d+/\d+.*?\)", re.IGNORECASE)


def _is_git_commit(cmd: str) -> bool:
    """识别 `git commit` 形式，允许前置 `-c k=v` / `-C <path>` 配置参数。

    严格按 token 比对 `parts[0] == "git"`，杜绝 `gitlab commit` / `github-cli commit`
    等前缀误判。
    """
    parts = cmd.strip().split()
    if not parts or parts[0] != "git":
        return False
    i = 1  # skip 'git'
    while i < len(parts):
        tok = parts[i]
        if tok in ("-c", "-C") and i + 1 < len(parts):
            i += 2
            continue
        if tok.startswith("--"):
            i += 1
            continue
        return tok == "commit"
    return False


def _git_query(repo: Path, *args: str):
    try:
        r = subprocess.run(
            ["git", *args],
            cwd=str(repo), capture_output=True, text=True, check=False,
            encoding="utf-8", errors="replace",
        )
    except (OSError, FileNotFoundError):
        return None
    if r.returncode != 0:
        return None
    return r.stdout.strip()


def main() -> int:
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw else {}
    except (ValueError, OSError):
        print(SUPPRESS)
        return 0

    cmd = (data.get("tool_input") or {}).get("command", "")
    transcript_path = data.get("transcript_path", "")
    if not _is_git_commit(cmd):
        print(SUPPRESS)
        return 0

    repo = Path.cwd()
    # ieidev 让位守卫：.ieidev/memory 在场 → kdev 整体让位、全静默（print(SUPPRESS)，
    # 不累积 pending-commits）。与下面 .kdev/memory 存在性门控同构、紧挨着。
    if defer_to_ieidev(repo):
        print(SUPPRESS)
        return 0
    # 存在性门控：未初始化 .kdev/memory/ 的工程不得凭空自举该目录
    # （与 session-start-brief / session-end-check / pre-compact-check / post-write-check
    # 一致：只有用户显式 /kdev-memory setup 或配了 sync remote clone 才会产生该目录）。
    # 否则 pending_commits.append → _write() 的 state_dir.mkdir(parents=True) 会把
    # 整个 .kdev/memory/ 自举出来，污染与本插件无关的工程。
    if not (repo / ".kdev" / "memory").is_dir():
        print(SUPPRESS)
        return 0

    sha = _git_query(repo, "log", "-1", "--format=%H")
    subject = _git_query(repo, "log", "-1", "--format=%s")
    if not sha or subject is None:
        print(SUPPRESS)
        return 0

    if _TASK_BATCH_RE.search(subject):
        print(SUPPRESS)
        return 0

    state_dir = repo / ".kdev" / "memory" / "state"
    try:
        append(state_dir, sha, subject, int(time.time()), transcript_path=transcript_path or None)
    except Exception:
        pass
    print(SUPPRESS)
    return 0


if __name__ == "__main__":
    sys.exit(main())
