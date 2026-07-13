#!/usr/bin/env python3
"""当前会话 transcript 指针：让 recorder 的模型他评溯源永远指向当前会话。

根因（0.19.8 前）：pending-commits 的 transcript_path/since_offset 只由 commit-tracker 在
commit 时更新、且 worktree commit（无 .kdev/memory）直接 skip → 指针冻结在老会话；
since_offset 是老会话 EOF 行号，套新会话越界读空 → recorder 他评静默降级成主会话自评。

修法：UserPromptSubmit / SessionStart（高频、每轮 hook input 都带当前会话 transcript_path）
stash 到 `state/.current-transcript`；recorder 用 `resolve_marker` 优先取当前会话，
换会话时 since_offset 重置 0（读当前会话全部，不套旧行号）。commit-tracker 继续只管攒 commits。

0.24.0（修 0.23.0 的 resolve_marker_verified 设计缺陷）：
- **分槽根治**：`.current-transcript` 单槽在同 repo 并发多会话下互相覆盖。改为每会话独占槽
  `.current-transcript.<session_id>`（session_id = transcript 文件名 stem，恰好等于 subagent
  也能读到的 `CLAUDE_CODE_SESSION_ID` 环境变量）→ recorder 直接解出**自己那一槽**，
  不再需要靠内容反推。legacy 单槽继续写，供无 session_id 的老调用方 fallback。
- **sha 锚不可单独采信**：commit sha 会被 kdev-memory 自己的 `<kdev-memory-brief>` 注入和
  Claude Code 的 gitStatus `Recent commits` 写进**每一个**新会话的 transcript（实测本 repo
  一个 sha 命中 4 个会话）→ 光"含 sha"完全无区分性。内容 fallback 路径要求**写操作强判据**：
  会话须含针对 `files_touched` 的 Edit/Write/NotebookEdit tool_use（开发会话必有，讨论会话没有）。
- **多命中不猜**：0.23.0 的 `recovered-ambiguous` 取最新 mtime 系统性偏向"事后谈论它的会话"
  （讨论/评审/排查必然晚于开发），且把猜测标成 `recovered=True` 让 recorder 采信 → 复制了它
  本要消灭的"静默错评"，还多盖一个权威戳。现在多命中一律 `degraded`。
- **扫描有界**：size cap + mtime 窗口；指针为空时按 cwd 推导 projects 目录（空指针恰是最该恢复的场景）。
"""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

import pending_commits

_CURRENT = ".current-transcript"

#: 内容 fallback 扫描的边界——避免对整个 projects 目录（实测 67 文件 / 131M）无界整读。
SCAN_MAX_BYTES = 16 * 1024 * 1024
SCAN_MAX_AGE_S = 7 * 24 * 3600

#: 会话独占槽的存活期——超期即回收，避免 state/ 里按会话无限堆积。
SLOT_TTL_S = 7 * 24 * 3600

#: 视为"这个会话真的动过代码"的写工具。
_WRITE_TOOLS = {"Edit", "Write", "NotebookEdit", "MultiEdit"}

_SAFE_ID = re.compile(r"[^A-Za-z0-9._-]")


def _session_of(transcript_path: str) -> str:
    """从 transcript 路径提会话 id（Claude Code 会话 JSONL 文件名 = <session>.jsonl 的 stem）。"""
    if not transcript_path:
        return ""
    return Path(transcript_path).stem


def _slot(state_dir, session_id: str) -> Path:
    return Path(state_dir) / f"{_CURRENT}.{_SAFE_ID.sub('-', session_id)[:64]}"


def current_session_id() -> str:
    """本进程所属会话 id。subagent 的 Bash 继承父会话的 `CLAUDE_CODE_SESSION_ID`，
    且其值 == 父会话 transcript 的文件名 stem——recorder 据此认领自己那一槽。"""
    return os.environ.get("CLAUDE_CODE_SESSION_ID", "") or ""


def default_projects_dir() -> Path:
    """cwd 对应的 Claude Code transcript 目录：~/.claude/projects/<cwd 绝对路径 / 换成 ->。"""
    slug = str(Path.cwd().resolve()).replace("/", "-")
    return Path.home() / ".claude" / "projects" / slug


def stash_current_transcript(state_dir, transcript_path: str, session_id: str = "") -> None:
    """UserPromptSubmit / SessionStart 调：记当前会话 transcript_path。永不抛。

    同时写**每会话独占槽**（抗并发覆盖）和 legacy 单槽（向后兼容）。
    """
    if not transcript_path:
        return
    sid = session_id or _session_of(transcript_path)
    payload = json.dumps({"transcript_path": transcript_path, "session": sid},
                         ensure_ascii=False)
    try:
        sd = Path(state_dir)
        sd.mkdir(parents=True, exist_ok=True)
        if sid:
            _slot(sd, sid).write_text(payload, encoding="utf-8")
        (sd / _CURRENT).write_text(payload, encoding="utf-8")
        _gc_slots(sd, keep=sid)
    except OSError:
        pass


def _gc_slots(state_dir: Path, keep: str = "") -> None:
    """回收过期的会话独占槽——槽按会话生长，不清会在 state/ 里无限堆积。永不抛。"""
    keeper = _slot(state_dir, keep).name if keep else ""
    cutoff = time.time() - SLOT_TTL_S
    for p in state_dir.glob(f"{_CURRENT}.*"):
        if p.name == keeper:
            continue
        try:
            if p.stat().st_mtime < cutoff:
                p.unlink()
        except OSError:
            pass


def _read_slot(path: Path) -> str:
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
        return d.get("transcript_path", "") if isinstance(d, dict) else ""
    except (OSError, ValueError):
        return ""


def read_current_transcript(state_dir, session_id: str = "") -> str:
    """给了 session_id 且该会话有独占槽 → 用独占槽（不受并发会话覆盖影响）；否则回落 legacy 单槽。"""
    sd = Path(state_dir)
    if session_id:
        own = _read_slot(_slot(sd, session_id))
        if own:
            return own
    return _read_slot(sd / _CURRENT)


def _scannable(path: Path, now: float) -> bool:
    try:
        st = path.stat()
    except OSError:
        return False
    return st.st_size <= SCAN_MAX_BYTES and (now - st.st_mtime) <= SCAN_MAX_AGE_S


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


def _line_writes_any(line: str, names: list[str]) -> bool:
    """这一行是不是对 names 里某个文件的写工具调用（Edit/Write/…）。"""
    if '"tool_use"' not in line:
        return False
    try:
        rec = json.loads(line)
    except ValueError:
        return False
    content = ((rec.get("message") or {}).get("content")) or []
    if not isinstance(content, list):
        return False
    for blk in content:
        if not isinstance(blk, dict) or blk.get("type") != "tool_use":
            continue
        if blk.get("name") not in _WRITE_TOOLS:
            continue
        fp = str((blk.get("input") or {}).get("file_path") or "")
        if fp and any(n and (n in fp or fp.endswith(n)) for n in names):
            return True
    return False


def _file_has_write_evidence(path, files_touched) -> bool:
    """会话是否真的动过这些文件——**开发会话必有写工具调用，讨论/评审/排查会话没有**。

    这是 sha 之外的强判据：sha 会被 `<kdev-memory-brief>` 注入和 gitStatus `Recent commits`
    灌进每一个新会话的 transcript，单靠它无法区分"产出该 commit 的会话"和"事后谈论它的会话"。
    """
    names = [n for n in (files_touched or []) if n]
    if not names:
        return False
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                if _line_writes_any(line, names):
                    return True
    except OSError:
        return False
    return False


def _scan_candidates(pdir: Path, anchors, files_touched) -> dict:
    """扫兄弟 transcript 找"产出本次 commit 的会话"。有 files_touched → 要求写操作强判据。"""
    now = time.time()
    hits = {}
    for jf in sorted(pdir.glob("*.jsonl")):
        if not _scannable(jf, now):
            continue
        if not _file_contains_any(jf, anchors):
            continue
        if files_touched and not _file_has_write_evidence(jf, files_touched):
            continue          # 只是提到 sha，没动过这些文件 → 不是开发会话
        hits.setdefault(jf.stem, jf)
    return hits


def resolve_marker_verified(state_dir, anchors, projects_dir=None, session_id=None,
                            files_touched=None) -> dict:
    """resolve_marker + **会话独占槽 / 内容校验 / 错会话恢复**（0.24.0 重写）。

    ``anchors``：commit sha（recorder 手里的 `commit_shas`）。
    ``files_touched``：本次 Step 改动的文件（recorder 手里就有）——用作写操作强判据。
    ``session_id``：缺省取 `CLAUDE_CODE_SESSION_ID`（subagent 继承父会话值）。

    判定顺序：

    1. **独占槽命中** → 直接采信（``verified``、``source='session-slot'``），不扫内容。
       这是根治路径：指针再被并发会话覆盖也动不了本会话自己的槽。
    2. 无独占槽（老 state / 非 Claude Code 环境）→ 回落 legacy 单槽 + 内容校验：
       - 候选含锚（且有 files_touched 时须有写证据）→ ``verified``。
       - 否则扫 ``projects_dir`` 兄弟 `*.jsonl`（size cap + mtime 窗口）：
         **恰好 1 个**含锚且有写证据 → ``recovered``（`since_offset=0`）；
         **多个** → ``degraded`` + ``ambiguous``（**不猜**：取最新 mtime 会系统性选中"事后谈论
         它的会话"，且伪造 `recovered` 权威戳 = 又一次静默错评）；**0 个** → ``degraded``。
    3. ``anchors`` 空（zero-commit step）→ 退回裸 `resolve_marker`，标 ``verified=False``。

    返回 `resolve_marker` 的键 + ``verified`` / ``recovered`` / ``degraded`` / ``ambiguous``
    / ``candidates`` / ``source`` / ``note``。
    """
    sid = current_session_id() if session_id is None else (session_id or "")
    base = resolve_marker(state_dir, session_id=sid)
    anchors = [a for a in (anchors or []) if a]
    out = {**base, "verified": False, "recovered": False, "degraded": False,
           "ambiguous": False, "candidates": 0, "source": base.get("source", ""), "note": ""}

    if out["source"] == "session-slot" and out.get("transcript_path"):
        out["verified"] = True
        out["note"] = "verified：命中本会话独占槽 .current-transcript.<session_id>，无需内容反推"
        return out

    if not anchors:
        out["note"] = "no-anchors：zero-commit step，退回裸 resolve_marker（未校验，向后兼容）"
        return out

    cand = base.get("transcript_path", "") or ""
    if cand and _file_contains_any(cand, anchors) and (
            not files_touched or _file_has_write_evidence(cand, files_touched)):
        out["verified"] = True
        out["source"] = "content-verified"
        return out

    pdir = Path(projects_dir) if projects_dir else (
        Path(cand).parent if cand else default_projects_dir())
    hits = _scan_candidates(pdir, anchors, files_touched) if pdir.is_dir() else {}
    out["candidates"] = len(hits)

    if len(hits) == 1:
        real = next(iter(hits.values()))
        out.update(transcript_path=str(real), since_offset=0, switched=True, recovered=True,
                   source="content-recovered",
                   note="recovered：指针指向并发/错误会话，已按 commit 锚 + 写操作证据恢复到开发会话")
    elif len(hits) > 1:
        out["degraded"] = True
        out["ambiguous"] = True
        out["note"] = (f"degraded-ambiguous：{len(hits)} 个会话同时满足判据，无法区分哪个产出了本次 "
                       "commit → 显式降级，不猜（猜错=带权威戳的静默错评）")
    else:
        out["degraded"] = True
        out["note"] = "degraded：无任何 transcript 满足 commit 锚 + 写操作证据，他评应显式降级"
    return out


def resolve_marker(state_dir, session_id: str = "") -> dict:
    """recorder 调（替代裸 pending_commits.get_transcript_marker）：返回
    ``{transcript_path, since_offset, switched, source}``，保证 transcript 指向当前会话。

    - 本会话有独占槽 → 用它（`source='session-slot'`，抗并发覆盖）。
    - 否则回落 legacy 单槽；无 legacy 单槽 → fallback pending（旧行为，向后兼容）。
    - 当前会话 == pending 记的会话 → 用当前路径 + pending 增量 offset（同会话续读）。
    - 换会话（当前会话 != pending 会话）→ 用当前路径 + **since_offset=0**（读当前会话全部，
      不把老会话 EOF 行号套到新会话导致越界读空）；`switched=True`。
    """
    sd = Path(state_dir)
    pend = pending_commits.get_transcript_marker(sd)   # {transcript_path, since_offset}
    pend_path = pend.get("transcript_path", "") or ""
    pend_offset = int(pend.get("since_offset", 0) or 0)

    sid = session_id or current_session_id()
    own = _read_slot(_slot(sd, sid)) if sid else ""
    cur = own or _read_slot(sd / _CURRENT)
    source = "session-slot" if own else ("legacy-slot" if cur else "pending")

    if not cur:
        return {"transcript_path": pend_path, "since_offset": pend_offset,
                "switched": False, "source": source}
    if _session_of(cur) != _session_of(pend_path):
        return {"transcript_path": cur, "since_offset": 0, "switched": True, "source": source}
    return {"transcript_path": cur, "since_offset": pend_offset,
            "switched": False, "source": source}
