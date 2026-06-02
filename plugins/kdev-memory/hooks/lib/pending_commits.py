"""pending-commits.json CRUD + threshold helpers (R-001 v1)。

state schema:
{
  "since_step_id": "main-15",
  "since_ts": 1716902400,
  "commits": [{"sha": "abc1234", "subject": "fix(x): y", "ts": 1716903456}, ...]
}

落盘路径：<state_dir>/pending-commits.json
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

FILENAME = "pending-commits.json"
DEFAULT_THRESHOLD_COUNT = 3
DEFAULT_THRESHOLD_AGE_SEC = 1800  # 30 min


def _path(state_dir: Path) -> Path:
    return state_dir / FILENAME


def _empty_state() -> dict:
    return {"since_step_id": "", "since_ts": 0, "commits": []}


def read(state_dir: Path) -> dict:
    """读 state；missing/损坏 → empty。"""
    p = _path(state_dir)
    if not p.is_file():
        return _empty_state()
    try:
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict) or "commits" not in data:
            return _empty_state()
        return data
    except (OSError, ValueError):
        return _empty_state()


def _write(state_dir: Path, data: dict) -> None:
    """atomic write via tmp + replace。"""
    state_dir.mkdir(parents=True, exist_ok=True)
    p = _path(state_dir)
    tmp = p.with_suffix(p.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, p)


def append(state_dir: Path, sha: str, subject: str, ts: int) -> None:
    """累积一条 commit。空 state 自动初始化 since_ts。"""
    data = read(state_dir)
    if not data["commits"]:
        data["since_ts"] = ts
    data["commits"].append({"sha": sha, "subject": subject, "ts": ts})
    _write(state_dir, data)


def clear(state_dir: Path, new_since_step_id: str, new_since_ts: int) -> None:
    """step-recorder 落完一条 step 后调用：清空 + 更新 since。"""
    _write(state_dir, {
        "since_step_id": new_since_step_id,
        "since_ts": new_since_ts,
        "commits": [],
    })


def count(state_dir: Path) -> int:
    return len(read(state_dir)["commits"])


def oldest_age(state_dir: Path, now: int) -> int:
    """最早一条 commit 距 now 的秒数；空 → 0。"""
    commits = read(state_dir)["commits"]
    if not commits:
        return 0
    return now - commits[0]["ts"]


def format_brief_hint(
    state_dir: Path,
    now: int,
    threshold_count: int = DEFAULT_THRESHOLD_COUNT,
    threshold_age_sec: int = DEFAULT_THRESHOLD_AGE_SEC,
) -> Optional[str]:
    """SessionStart/Stop brief 注入的 hint 字符串。不到阈值返回 None。"""
    data = read(state_dir)
    commits = data["commits"]
    if not commits:
        return None
    n = len(commits)
    age = now - commits[0]["ts"]
    if n < threshold_count and age < threshold_age_sec:
        return None
    age_min = age // 60
    latest = commits[-1]
    short_sha = latest["sha"][:7]
    return (
        f"🔔 pending step-recorder dispatch: {n} commit 累积"
        f"（最早 {age_min}min，最近 {short_sha}: {latest['subject'][:50]}）"
        f" — 完成单元后请 dispatch kdev-step-recorder。"
    )
