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


def _file_contains_any(path, anchors) -> bool:
    """transcript .jsonl 是否含任一锚（逐行子串匹配，不整文件入内存）。"""
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                for a in anchors:
                    if a and a in line:
                        return True
    except OSError:
        return False
    return False


def resolve_marker_verified(state_dir, anchors, projects_dir=None) -> dict:
    """resolve_marker + **内容校验 / 并发错会话自动恢复**。

    修 `.current-transcript` 单槽全局指针在**同 repo 并发多会话**下被互相覆盖，导致
    recorder 他评溯源读到并发的另一会话（G 20260708-215209 的 2026-07-12 复现根因）。

    ``anchors``：期望出现在"正确会话" transcript 里的锚（commit sha 优先——recorder 手里
    的 `commit_shas`；正确会话的 transcript 必含这些 git 输出，错会话不含）。

    - 候选（`resolve_marker`）内容含任一 anchor → **采信**（``verified``）。
    - 候选不含且 anchors 非空 → 扫 ``projects_dir``（缺省=候选 transcript 的父目录，并发会话
      同 cwd 共享该目录）兄弟 `*.jsonl` 找含 anchor 者 → **恢复**（``recovered``，`since_offset=0`
      从头读恢复会话）。多命中取最新 mtime 并标歧义；无命中 → **降级**（``degraded``）。
    - anchors 空（zero-commit step）→ 退回裸 `resolve_marker`，标 ``verified=False``（向后兼容）。

    返回在 `resolve_marker` 基础上加 ``verified`` / ``recovered`` / ``degraded`` / ``note``。
    """
    base = resolve_marker(state_dir)
    anchors = [a for a in (anchors or []) if a]
    out = {**base, "verified": False, "recovered": False, "degraded": False, "note": ""}
    if not anchors:
        out["note"] = "no-anchors：zero-commit step，退回裸 resolve_marker（未校验，向后兼容）"
        return out

    cand = base.get("transcript_path", "") or ""
    if cand and _file_contains_any(cand, anchors):
        out["verified"] = True
        return out

    # 候选未命中锚 → 指针可能被并发会话覆盖，扫兄弟找真会话
    pdir = Path(projects_dir) if projects_dir else (Path(cand).parent if cand else None)
    uniq = {}
    if pdir and pdir.is_dir():
        for jf in sorted(pdir.glob("*.jsonl")):
            if _file_contains_any(jf, anchors):
                uniq.setdefault(jf.stem, jf)
    if len(uniq) == 1:
        real = next(iter(uniq.values()))
        out.update(transcript_path=str(real), since_offset=0, switched=True, recovered=True,
                   note="recovered：指针指向并发/错误会话，已按 commit 锚恢复到正确会话")
    elif len(uniq) > 1:
        real = max(uniq.values(), key=lambda p: p.stat().st_mtime)
        out.update(transcript_path=str(real), since_offset=0, switched=True, recovered=True,
                   note=f"recovered-ambiguous：{len(uniq)} 个会话含锚，取最新 mtime")
    else:
        out["degraded"] = True
        out["note"] = "degraded：无任何 transcript 含给定 commit 锚（或未落盘），他评应显式降级"
    return out


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
