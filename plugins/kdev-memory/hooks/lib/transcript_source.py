#!/usr/bin/env python3
"""当前会话 transcript 指针：让 recorder 的模型他评溯源永远指向当前会话。

根因（0.19.8 前）：pending-commits 的 transcript_path/since_offset 只由 commit-tracker 在
commit 时更新、且 worktree commit（无 .kdev/memory）直接 skip → 指针冻结在老会话；
since_offset 是老会话 EOF 行号，套新会话越界读空 → recorder 他评静默降级成主会话自评。

修法：UserPromptSubmit / SessionStart（高频、每轮 hook input 都带当前会话 transcript_path）
stash 到 `state/.current-transcript`；recorder 用 `resolve_marker` 优先取当前会话，
换会话时 since_offset 重置 0（读当前会话全部，不套旧行号）。commit-tracker 继续只管攒 commits。
"""
from __future__ import annotations

import json
from pathlib import Path

import pending_commits

_CURRENT = ".current-transcript"


def _session_of(transcript_path: str) -> str:
    """从 transcript 路径提会话 id（Claude Code 会话 JSONL 文件名 = <session>.jsonl 的 stem）。"""
    if not transcript_path:
        return ""
    return Path(transcript_path).stem


def stash_current_transcript(state_dir, transcript_path: str) -> None:
    """UserPromptSubmit / SessionStart 调：记当前会话 transcript_path（覆盖，永远最新）。永不抛。"""
    if not transcript_path:
        return
    try:
        sd = Path(state_dir)
        sd.mkdir(parents=True, exist_ok=True)
        (sd / _CURRENT).write_text(
            json.dumps({"transcript_path": transcript_path,
                        "session": _session_of(transcript_path)}, ensure_ascii=False),
            encoding="utf-8")
    except OSError:
        pass


def read_current_transcript(state_dir) -> str:
    try:
        d = json.loads((Path(state_dir) / _CURRENT).read_text(encoding="utf-8"))
        return d.get("transcript_path", "") if isinstance(d, dict) else ""
    except (OSError, ValueError):
        return ""


def resolve_marker(state_dir) -> dict:
    """recorder 调（替代裸 pending_commits.get_transcript_marker）：返回
    ``{transcript_path, since_offset, switched}``，保证 transcript 指向当前会话。

    - 无 `.current-transcript` → fallback pending（旧行为，向后兼容）。
    - 当前会话 == pending 记的会话 → 用当前路径 + pending 增量 offset（同会话续读）。
    - 换会话（当前会话 != pending 会话）→ 用当前路径 + **since_offset=0**（读当前会话全部，
      不把老会话 EOF 行号套到新会话导致越界读空）；`switched=True`。
    """
    sd = Path(state_dir)
    pend = pending_commits.get_transcript_marker(sd)   # {transcript_path, since_offset}
    pend_path = pend.get("transcript_path", "") or ""
    pend_offset = int(pend.get("since_offset", 0) or 0)
    cur = read_current_transcript(sd)
    if not cur:
        return {"transcript_path": pend_path, "since_offset": pend_offset, "switched": False}
    if _session_of(cur) != _session_of(pend_path):
        return {"transcript_path": cur, "since_offset": 0, "switched": True}
    return {"transcript_path": cur, "since_offset": pend_offset, "switched": False}
