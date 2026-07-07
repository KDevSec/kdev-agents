#!/usr/bin/env python3
"""兜底方案：hook 机械组装一条 auto-fallback 降级 Step（LLM 缺席的丢失关口用）。

SessionEnd / PreCompact 等"LLM 不在场"的关口无法产出合格 Step（title/决策需 LLM 提炼），
但可机械捕获 commits/files 骨架 + transcript 指针，落一条降级 Step 保证"不丢"，
待下会话 SessionStart 提示、由主会话 LLM 升格成正式 Step（升格走 append_step 严格 gate）。

降级 Step 走 step_log.append_fallback_step（宽松写入，status=auto-fallback），
下游消费方（step_completeness / distill / daily_render）据 is_fallback_status 隔离。
"""
from __future__ import annotations

import subprocess
import sys
import time
from datetime import date, datetime
from pathlib import Path

SCRIPT_DIR = str(Path(__file__).resolve().parent)
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import pending_commits  # noqa: E402
import step_log  # noqa: E402
from scope import state_dir as _state_dir  # noqa: E402
from step_id import mint_record_id  # noqa: E402


def _porcelain_files(cwd, limit: int = 20) -> list:
    """git status --porcelain 拿变更文件名（best-effort，失败返回 []）。"""
    try:
        r = subprocess.run(
            ["git", "status", "--porcelain"], cwd=str(cwd),
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", check=False,
        )
        if r.returncode != 0:
            return []
        files = []
        for line in r.stdout.splitlines():
            p = line[3:].strip()
            if p:
                files.append(p)
        return files[:limit]
    except (OSError, ValueError):
        return []


def _make_title(source: str, commits: list, files: list) -> str:
    if commits:
        head = (commits[0].get("subject") or "").strip() or (commits[0].get("sha") or "")[:7]
        extra = f" 等 {len(commits)} 提交" if len(commits) > 1 else ""
        return f"[待升格·{source}] {head}{extra}"
    if files:
        return f"[待升格·{source}] {len(files)} 文件变更未落盘"
    return f"[待升格·{source}] 未落盘工作（无 commit / 无变更明细）"


def make_fallback_step(repo_root, source, *, scope=None, root=None,
                       when=None, porcelain_cwd=None, dedup_window=300) -> dict:
    """组装并落一条 auto-fallback 降级 Step。返回 {ok, record_id, message}。永不抛。

    - drain pending-commits（commits/transcript_path/since_offset）作供料骨架
    - git porcelain 拿变更文件名
    - mint Step ID、组 record、step_log.append_fallback_step（宽松写）
    - 落完清空 pending（避免第二个丢失关口 PreCompact→SessionEnd 重复兜底）
    """
    try:
        repo_root = Path(repo_root)
        kdev_root = Path(root) if root is not None else repo_root / ".kdev" / "memory"
        sd = _state_dir(kdev_root)
        sd.mkdir(parents=True, exist_ok=True)   # mint_record_id 去重锚 + pending 落此
        # 双关口去重（④）：PreCompact 兜过后 SessionEnd 同场紧接触发时，pending 已 drain 空、
        # 会落一条无 commit 的空降级 Step。用 .last-fallback 时间窗跳过，防重复兜底。
        marker = sd / ".last-fallback"
        if dedup_window and marker.exists():
            try:
                if time.time() - marker.stat().st_mtime < dedup_window:
                    return {"ok": True, "skipped": True, "record_id": None,
                            "message": f"{dedup_window}s 内已兜底，跳过（防双关口重复）"}
            except OSError:
                pass
        pending = pending_commits.read(sd)
        commits = pending.get("commits", []) or []
        files = _porcelain_files(porcelain_cwd or repo_root)
        rid = mint_record_id("Step", sd, when=when)
        today = (when.date() if isinstance(when, datetime) else date.today()).isoformat()
        commit_shas = [c.get("sha", "") for c in commits]
        record = {
            "type": "Step",
            "record_id": rid,
            "title": _make_title(source, commits, files),
            "date": today,
            "about": "project",
            "status": "auto-fallback",
            "key_facts": {
                "tools_invoked_count": max(1, len(commits)),
                "errors_hit": 0,
                "commit_shas": commit_shas,
                "files_touched": files,
            },
            "fallback": {
                "source": source,
                "commit_shas": commit_shas,
                "files_touched": files,
                "transcript_path": pending.get("transcript_path", ""),
                "since_offset": pending.get("since_offset", 0),
            },
        }
        step_log.append_fallback_step(record, scope=scope, root=kdev_root)
        last_ts = commits[-1]["ts"] if commits else int(pending.get("since_ts", 0) or 0)
        pending_commits.clear(sd, new_since_step_id=rid, new_since_ts=last_ts,
                              new_since_offset=int(pending.get("since_offset", 0) or 0))
        try:
            marker.touch()   # 记本次兜底时刻，供同场另一关口去重
        except OSError:
            pass
        return {"ok": True, "record_id": rid, "message": f"fallback step 落盘（{source}）"}
    except Exception as exc:  # 兜底 helper 本身永不抛，失败也不阻塞 hook
        return {"ok": False, "record_id": None, "message": f"fallback failed: {exc}"}
