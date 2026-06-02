# R-001 kdev-step-recorder 集成 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 kdev-step-recorder prototype 集成进 kdev-memory v0.12.0 的主路径——SKILL.md / CLAUDE.md 教模型用 dispatch，commit hook 累积 pending-commits + 阈值软提醒兜底主会话遗忘，SessionStart brief 顺手监测 SKILL.md 升级 staleness（R-005）。

**Architecture:** 新增 3 个 lib（pending_commits / skill_version）+ 1 个新 hook（commit-tracker）+ 2 个 hook 扩展（stop-check / session-start-brief）+ 7 处 docs 改写（SKILL.md inline 30 行 + § 下游 拆分 + CLAUDE.md 第 1 条铁规改写 + template + agents/kdev-step-recorder.md YAML schema 加 1 字段 + CHANGELOG）。所有 state 文件落 `.kdev/memory/state/`，跟现有 step-counter-*.txt 共生。

**Tech Stack:** Python 3.7+（stdlib 为主：subprocess / json / re / time / pathlib / hashlib），pytest。

**Spec source:** [docs/skills/kdev-memory/specs/2026-05-29-r-001-step-recorder-integration.md](../specs/2026-05-29-r-001-step-recorder-integration.md)

---

## 文件结构

| 文件 | 角色 | 改动类型 |
|------|------|----------|
| `plugins/kdev-memory/hooks/lib/pending_commits.py` | pending-commits.json CRUD + age/threshold/format helpers | 新增 |
| `plugins/kdev-memory/tests/test_pending_commits.py` | TDD 测试 | 新增 |
| `plugins/kdev-memory/hooks/lib/skill_version.py` | R-005 SKILL.md SHA cache + drift detection | 新增 |
| `plugins/kdev-memory/tests/test_skill_version.py` | TDD 测试 | 新增 |
| `plugins/kdev-memory/hooks/commit-tracker.py` | PostToolUse Bash hook—检测 git commit + 累积 pending | 新增 |
| `plugins/kdev-memory/tests/test_commit_tracker.py` | TDD 测试（含 task N/M suppress） | 新增 |
| `plugins/kdev-memory/tests/test_step_recorder_e2e.py` | dispatch step-recorder + verify step landed e2e | 新增 |
| `plugins/kdev-memory/hooks/hooks.json` | 注册 PostToolUse + 把 commit-tracker 接入 | 修改 |
| `plugins/kdev-memory/hooks/stop-check.py` | 加 pending-commits threshold 软提醒注入 | 修改 |
| `plugins/kdev-memory/hooks/session-start-brief.py` | brief 注入 pending 状态 + R-005 SHA drift | 修改 |
| `plugins/kdev-memory/agents/kdev-step-recorder.md` | YAML schema 加 `commits_batch_id` 选填 + clear after step 协议明确化 | 修改 |
| `plugins/kdev-memory/skills/kdev-memory/SKILL.md` | inline §"用 kdev-step-recorder dispatch 落 step (v0.12+)" + § 下游 拆分 | 修改 |
| `plugins/kdev-memory/skills/kdev-memory/references/初始化-claude-md-模板.md` | 同步第 1 条铁规改写 | 修改 |
| `CLAUDE.md`（项目根） | 第 1 条铁规重写"实时 dispatch step-recorder 落盘" | 修改 |
| `plugins/kdev-memory/CHANGELOG.md` | bump v0.12.0 + 完整 entry | 修改 |

---

## Task 1: `pending_commits.py` lib + CRUD + threshold helpers

**Files:**
- Create: `plugins/kdev-memory/hooks/lib/pending_commits.py`
- Test: `plugins/kdev-memory/tests/test_pending_commits.py`

**契约**:
- `read(state_dir: Path) -> dict` — 返回 `{"since_step_id": str, "since_ts": int, "commits": list}`；missing/损坏 → `{"since_step_id": "", "since_ts": 0, "commits": []}`
- `append(state_dir, sha, subject, ts)` — atomic append；自动初始化 since_step_id/since_ts 若 commits 为空
- `clear(state_dir, new_since_step_id, new_since_ts)` — 重置为空 commits + 更新 since
- `count(state_dir) -> int`、`oldest_age(state_dir, now) -> int` — 阈值检查辅助
- `format_brief_hint(state_dir, now, threshold_count=3, threshold_age_sec=1800) -> str | None`

- [ ] **Step 1: Write failing tests**

```python
# plugins/kdev-memory/tests/test_pending_commits.py
"""test pending_commits.py: CRUD + threshold + brief format。R-001 v1 task 1。"""
from __future__ import annotations

import sys
from pathlib import Path

LIB_DIR = Path(__file__).parent.parent / "hooks" / "lib"
sys.path.insert(0, str(LIB_DIR))

from pending_commits import (  # noqa: E402
    append, clear, count, format_brief_hint, oldest_age, read,
)


def test_read_missing_file_returns_empty(tmp_path):
    out = read(tmp_path)
    assert out == {"since_step_id": "", "since_ts": 0, "commits": []}


def test_append_creates_file_and_initializes_since(tmp_path):
    append(tmp_path, "abc1234", "fix(x): y", 1716903456)
    state = read(tmp_path)
    assert state["since_ts"] == 1716903456
    assert state["commits"] == [
        {"sha": "abc1234", "subject": "fix(x): y", "ts": 1716903456}
    ]


def test_append_accumulates(tmp_path):
    append(tmp_path, "a", "subj-a", 100)
    append(tmp_path, "b", "subj-b", 200)
    append(tmp_path, "c", "subj-c", 300)
    state = read(tmp_path)
    assert len(state["commits"]) == 3
    assert state["since_ts"] == 100  # earliest commit


def test_clear_resets_and_updates_since(tmp_path):
    append(tmp_path, "a", "subj-a", 100)
    clear(tmp_path, "main-15", 500)
    state = read(tmp_path)
    assert state["since_step_id"] == "main-15"
    assert state["since_ts"] == 500
    assert state["commits"] == []


def test_count_helper(tmp_path):
    assert count(tmp_path) == 0
    append(tmp_path, "a", "subj", 100)
    append(tmp_path, "b", "subj", 200)
    assert count(tmp_path) == 2


def test_oldest_age_helper(tmp_path):
    append(tmp_path, "a", "subj", 1000)
    append(tmp_path, "b", "subj", 1500)
    assert oldest_age(tmp_path, now=2000) == 1000


def test_oldest_age_empty(tmp_path):
    assert oldest_age(tmp_path, now=2000) == 0


def test_format_brief_hint_silent_when_empty(tmp_path):
    assert format_brief_hint(tmp_path, now=1000) is None


def test_format_brief_hint_silent_below_threshold(tmp_path):
    append(tmp_path, "a", "subj-a", 1000)
    append(tmp_path, "b", "subj-b", 1100)
    # count=2 < 3, age=200 < 1800 → silent
    assert format_brief_hint(tmp_path, now=1200) is None


def test_format_brief_hint_fires_by_count(tmp_path):
    append(tmp_path, "a", "subj-a", 1000)
    append(tmp_path, "b", "subj-b", 1100)
    append(tmp_path, "c", "subj-c", 1200)
    hint = format_brief_hint(tmp_path, now=1300)
    assert hint is not None
    assert "3 commit" in hint
    assert "subj-c" in hint or "subj-a" in hint


def test_format_brief_hint_fires_by_age(tmp_path):
    append(tmp_path, "a", "subj-a", 1000)
    # count=1 < 3, but age = 5000-1000 = 4000 > 1800 → fire
    hint = format_brief_hint(tmp_path, now=5000)
    assert hint is not None
    assert "1 commit" in hint
```

- [ ] **Step 2: Run, confirm fail**

Run: `cd plugins/kdev-memory && python3 -m pytest tests/test_pending_commits.py -v`
Expected: ModuleNotFoundError: No module named 'pending_commits'

- [ ] **Step 3: Implement `pending_commits.py`**

```python
# plugins/kdev-memory/hooks/lib/pending_commits.py
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
```

- [ ] **Step 4: Run tests, all pass**

Run: `cd plugins/kdev-memory && python3 -m pytest tests/test_pending_commits.py -v`
Expected: 11 passed

- [ ] **Step 5: Commit**

```bash
git add plugins/kdev-memory/hooks/lib/pending_commits.py plugins/kdev-memory/tests/test_pending_commits.py
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-memory): add pending_commits lib for R-001 v1 hook (task 1/14)"
```

---

## Task 2: `skill_version.py` lib + SHA cache + drift detection (R-005)

**Files:**
- Create: `plugins/kdev-memory/hooks/lib/skill_version.py`
- Test: `plugins/kdev-memory/tests/test_skill_version.py`

**契约**:
- `read_cache(session_id, state_dir) -> str | None` — 读 session 启动时缓存的 SKILL.md SHA
- `write_cache(session_id, sha, state_dir) -> None` — 缓存当前 SHA
- `current_skill_sha(repo_root, skill_relpath="plugins/kdev-memory/skills/kdev-memory/SKILL.md") -> str | None` — `git log -1 --format=%H -- <path>` 拿到当前 SHA；非 git 仓库或文件不存在返回 None
- `detect_drift(session_id, repo_root, state_dir) -> tuple[str|None, str|None]` — 返回 (cached, current)；cached is None 或 cached==current 表示无 drift（None, None）；不等则返回 (cached_sha, current_sha)
- cache 文件：`<state_dir>/skill-version-cache-<session_id>.json`，schema `{"skill_sha": "..."}`

- [ ] **Step 1: Write failing tests**

```python
# plugins/kdev-memory/tests/test_skill_version.py
"""test skill_version.py: SHA cache + drift detection (R-001 v1 task 2 / R-005)。"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

LIB_DIR = Path(__file__).parent.parent / "hooks" / "lib"
sys.path.insert(0, str(LIB_DIR))

from skill_version import (  # noqa: E402
    current_skill_sha, detect_drift, read_cache, write_cache,
)


def test_read_cache_missing_returns_none(tmp_path):
    assert read_cache("sess-1", tmp_path) is None


def test_write_then_read_roundtrip(tmp_path):
    write_cache("sess-1", "abc123def", tmp_path)
    assert read_cache("sess-1", tmp_path) == "abc123def"


def test_cache_per_session_isolated(tmp_path):
    write_cache("sess-1", "sha-a", tmp_path)
    write_cache("sess-2", "sha-b", tmp_path)
    assert read_cache("sess-1", tmp_path) == "sha-a"
    assert read_cache("sess-2", tmp_path) == "sha-b"


def _init_repo_with_file(tmp_path: Path, content: str) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    target = repo / "SKILL.md"
    target.write_text(content, encoding="utf-8")
    subprocess.run(["git", "add", "SKILL.md"], cwd=repo, check=True)
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-q", "-m", "init"],
        cwd=repo, check=True,
    )
    return repo


def test_current_skill_sha_non_git_returns_none(tmp_path):
    assert current_skill_sha(tmp_path, skill_relpath="SKILL.md") is None


def test_current_skill_sha_returns_hash(tmp_path):
    repo = _init_repo_with_file(tmp_path, "v1 content")
    sha = current_skill_sha(repo, skill_relpath="SKILL.md")
    assert sha is not None
    assert len(sha) == 40  # full SHA-1


def test_detect_drift_first_call_no_drift_signal(tmp_path):
    repo = _init_repo_with_file(tmp_path, "v1")
    state = tmp_path / "state"
    cached, current = detect_drift("sess-1", repo, state, skill_relpath="SKILL.md")
    assert cached is None  # no prior cache → no drift signal
    assert current is not None  # but current SHA is captured


def test_detect_drift_same_sha_returns_no_drift(tmp_path):
    repo = _init_repo_with_file(tmp_path, "v1")
    state = tmp_path / "state"
    detect_drift("sess-1", repo, state, skill_relpath="SKILL.md")  # cache it
    cached, current = detect_drift("sess-1", repo, state, skill_relpath="SKILL.md")
    assert cached == current  # equal → no drift fires
    assert cached is not None


def test_detect_drift_different_sha_returns_drift_signal(tmp_path):
    repo = _init_repo_with_file(tmp_path, "v1")
    state = tmp_path / "state"
    cached_first, _ = detect_drift("sess-1", repo, state, skill_relpath="SKILL.md")
    sha_v1 = current_skill_sha(repo, skill_relpath="SKILL.md")
    # bump file + new commit → new SHA
    (repo / "SKILL.md").write_text("v2 content", encoding="utf-8")
    subprocess.run(["git", "add", "SKILL.md"], cwd=repo, check=True)
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-q", "-m", "v2"],
        cwd=repo, check=True,
    )
    cached, current = detect_drift("sess-1", repo, state, skill_relpath="SKILL.md")
    assert cached == sha_v1
    assert current != sha_v1
    assert current is not None
```

- [ ] **Step 2: Run, confirm fail**

Run: `cd plugins/kdev-memory && python3 -m pytest tests/test_skill_version.py -v`
Expected: ModuleNotFoundError on `skill_version`

- [ ] **Step 3: Implement `skill_version.py`**

```python
# plugins/kdev-memory/hooks/lib/skill_version.py
"""SKILL.md SHA cache + drift detection (R-001 v1 / R-005)。

每个 session 启动时缓存当前 SKILL.md 的 git SHA；之后 SessionStart 再触发时
比对缓存 vs 当前——不等则说明 skill 在会话期间被升级，brief 提醒重启。
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Optional, Tuple

DEFAULT_SKILL_RELPATH = "plugins/kdev-memory/skills/kdev-memory/SKILL.md"

# session_id 可能含特殊字符，sanitize 后用作文件名
_SAFE_ID_RE = re.compile(r"[^A-Za-z0-9_-]+")


def _sanitize_id(session_id: str) -> str:
    return _SAFE_ID_RE.sub("-", session_id)[:64] or "unknown"


def _cache_path(session_id: str, state_dir: Path) -> Path:
    return state_dir / f"skill-version-cache-{_sanitize_id(session_id)}.json"


def read_cache(session_id: str, state_dir: Path) -> Optional[str]:
    p = _cache_path(session_id, state_dir)
    if not p.is_file():
        return None
    try:
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
        sha = data.get("skill_sha")
        return sha if isinstance(sha, str) and sha else None
    except (OSError, ValueError):
        return None


def write_cache(session_id: str, sha: str, state_dir: Path) -> None:
    state_dir.mkdir(parents=True, exist_ok=True)
    p = _cache_path(session_id, state_dir)
    tmp = p.with_suffix(p.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"skill_sha": sha}, f)
    os.replace(tmp, p)


def current_skill_sha(
    repo_root: Path,
    skill_relpath: str = DEFAULT_SKILL_RELPATH,
) -> Optional[str]:
    """git log -1 --format=%H -- <skill_relpath>；非 git / 文件无 commit → None。"""
    try:
        r = subprocess.run(
            ["git", "log", "-1", "--format=%H", "--", skill_relpath],
            cwd=str(repo_root), capture_output=True, text=True, check=False,
        )
    except (OSError, FileNotFoundError):
        return None
    if r.returncode != 0:
        return None
    out = r.stdout.strip()
    return out if out else None


def detect_drift(
    session_id: str,
    repo_root: Path,
    state_dir: Path,
    skill_relpath: str = DEFAULT_SKILL_RELPATH,
) -> Tuple[Optional[str], Optional[str]]:
    """返回 (cached_before_this_call, current)。
    First call: cached=None (no signal) + 写入 current。
    Subsequent: cached=cached_sha, current=current_sha；caller 判 == 决定 drift。
    """
    cached = read_cache(session_id, state_dir)
    current = current_skill_sha(repo_root, skill_relpath)
    if current is not None and cached != current:
        write_cache(session_id, current, state_dir)
    return cached, current
```

- [ ] **Step 4: Run tests, all pass**

Run: `cd plugins/kdev-memory && python3 -m pytest tests/test_skill_version.py -v`
Expected: 8 passed

- [ ] **Step 5: Commit**

```bash
git add plugins/kdev-memory/hooks/lib/skill_version.py plugins/kdev-memory/tests/test_skill_version.py
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-memory): add skill_version lib for R-005 SHA drift detection (task 2/14)"
```

---

## Task 3: `commit-tracker.py` hook + task N/M suppress

**Files:**
- Create: `plugins/kdev-memory/hooks/commit-tracker.py`
- Test: `plugins/kdev-memory/tests/test_commit_tracker.py`

**契约**:
- stdin 读 hook 输入 JSON（PostToolUse on Bash）
- 检查 `toolInput.command` 是否以 `git commit` 开头（容忍前后空格）
- 不是 → 静默返回 SUPPRESS JSON
- 是 → `git log -1 --format=%H%n%s` 拿 SHA + subject
- 若 subject 含 regex `\(.*?task\s+\d+/\d+.*?\)`（case-insensitive） → suppress（不计入 pending）
- 否则 `pending_commits.append(.kdev/memory/state, sha, subject, now)`
- 任何情况下 stdout 输出 SUPPRESS JSON（hook 不影响主会话）

- [ ] **Step 1: Write failing tests**

```python
# plugins/kdev-memory/tests/test_commit_tracker.py
"""test commit-tracker.py hook script: detect git commit + suppress task N/M。"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HOOK = Path(__file__).parent.parent / "hooks" / "commit-tracker.py"


def _make_repo_with_commit(tmp_path: Path, msg: str) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".kdev" / "memory" / "state").mkdir(parents=True)
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    (repo / "f.txt").write_text("x", encoding="utf-8")
    subprocess.run(["git", "add", "f.txt"], cwd=repo, check=True)
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-q", "-m", msg],
        cwd=repo, check=True,
    )
    return repo


def _run_hook(repo: Path, command: str) -> dict:
    payload = json.dumps({"toolInput": {"command": command}})
    r = subprocess.run(
        [sys.executable, str(HOOK)],
        cwd=str(repo), input=payload, capture_output=True, text=True,
    )
    out = r.stdout.strip()
    return json.loads(out) if out else {}


def _read_pending(repo: Path) -> dict:
    p = repo / ".kdev" / "memory" / "state" / "pending-commits.json"
    if not p.is_file():
        return {"commits": []}
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def test_non_git_command_does_nothing(tmp_path):
    repo = _make_repo_with_commit(tmp_path, "normal commit")
    # initial pending should be empty
    assert _read_pending(repo)["commits"] == []
    _run_hook(repo, "ls -la")
    # still empty after non-git command
    assert _read_pending(repo)["commits"] == []


def test_git_commit_appends_to_pending(tmp_path):
    repo = _make_repo_with_commit(tmp_path, "fix(x): single-commit work")
    _run_hook(repo, "git commit -m fix")
    pending = _read_pending(repo)
    assert len(pending["commits"]) == 1
    assert pending["commits"][0]["subject"] == "fix(x): single-commit work"


def test_task_pattern_in_message_suppresses(tmp_path):
    repo = _make_repo_with_commit(tmp_path, "feat(x): batch step (Q-003 task 3/13)")
    _run_hook(repo, "git commit -m batch")
    pending = _read_pending(repo)
    assert pending["commits"] == []  # suppressed


def test_q_xxx_task_pattern_suppresses_any_q_number(tmp_path):
    repo = _make_repo_with_commit(tmp_path, "release(x): bump (Q-100 task 14/14)")
    _run_hook(repo, "git commit -m release")
    pending = _read_pending(repo)
    assert pending["commits"] == []


def test_task_pattern_inside_parens_only(tmp_path):
    # message contains "task 1/2" but NOT in parens → should NOT suppress
    repo = _make_repo_with_commit(tmp_path, "wip: task 1/2 incomplete")
    _run_hook(repo, "git commit -m wip")
    pending = _read_pending(repo)
    assert len(pending["commits"]) == 1  # treated as normal


def test_git_commit_with_extra_args(tmp_path):
    repo = _make_repo_with_commit(tmp_path, "regular commit msg")
    _run_hook(repo, "git -c user.name=ly-AI commit -m regular")
    pending = _read_pending(repo)
    assert len(pending["commits"]) == 1


def test_hook_resilient_to_missing_state_dir(tmp_path):
    """state dir doesn't exist yet → hook should auto-create via pending_commits.append."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    (repo / "f.txt").write_text("x", encoding="utf-8")
    subprocess.run(["git", "add", "f.txt"], cwd=repo, check=True)
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-q", "-m", "fresh"],
        cwd=repo, check=True,
    )
    _run_hook(repo, "git commit -m fresh")
    pending = _read_pending(repo)
    assert len(pending["commits"]) == 1


def test_hook_silent_when_no_commit_exists(tmp_path):
    """git commit command fired but no commit was actually created (e.g., aborted) →
    git log fails gracefully, hook doesn't crash."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".kdev" / "memory" / "state").mkdir(parents=True)
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    r = _run_hook(repo, "git commit --allow-empty -m none")
    # no crash + no entry (since git log fails on a repo with no commits)
    pending = _read_pending(repo)
    assert pending["commits"] == []
```

- [ ] **Step 2: Run, confirm fail**

Run: `cd plugins/kdev-memory && python3 -m pytest tests/test_commit_tracker.py -v`
Expected: FileNotFoundError on `commit-tracker.py`

- [ ] **Step 3: Implement `commit-tracker.py`**

```python
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

SUPPRESS = json.dumps({"continue": True, "suppressOutput": True})

# regex 抓"圆括号内含 task N/M"——commit message 末尾常见 "(Q-003 task 3/13)" 形式
_TASK_BATCH_RE = re.compile(r"\(.*?task\s+\d+/\d+.*?\)", re.IGNORECASE)


def _is_git_commit(cmd: str) -> bool:
    """识别 `git commit` 形式，允许前置 `-c k=v` 配置参数。"""
    # 去前置空格
    s = cmd.strip()
    # 必须以 git 开头
    if not s.startswith("git"):
        return False
    # 寻找 'commit' 作为独立 token
    parts = s.split()
    # 找到第一个非 -c key=value / -X / --xxx 的 git 子命令
    i = 1  # 跳过 'git'
    while i < len(parts):
        tok = parts[i]
        if tok == "-c" and i + 1 < len(parts):
            i += 2
            continue
        if tok.startswith("--"):
            # global flag like --no-pager
            i += 1
            continue
        return tok == "commit"
    return False


def _git_query(repo: Path, *args: str):
    try:
        r = subprocess.run(
            ["git", *args],
            cwd=str(repo), capture_output=True, text=True, check=False,
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

    cmd = (data.get("toolInput") or {}).get("command", "")
    if not _is_git_commit(cmd):
        print(SUPPRESS)
        return 0

    repo = Path.cwd()
    sha = _git_query(repo, "log", "-1", "--format=%H")
    subject = _git_query(repo, "log", "-1", "--format=%s")
    if not sha or subject is None:
        # commit didn't actually land (aborted, hook-rejected, etc.)
        print(SUPPRESS)
        return 0

    if _TASK_BATCH_RE.search(subject):
        # subagent-driven batch → suppress
        print(SUPPRESS)
        return 0

    state_dir = repo / ".kdev" / "memory" / "state"
    try:
        append(state_dir, sha, subject, int(time.time()))
    except Exception:
        # hook 必须健壮，任何异常都不该污染主会话
        pass
    print(SUPPRESS)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Make hook executable + run tests**

```bash
chmod +x plugins/kdev-memory/hooks/commit-tracker.py
cd plugins/kdev-memory && python3 -m pytest tests/test_commit_tracker.py -v
```

Expected: 8 passed

- [ ] **Step 5: Commit**

```bash
git add plugins/kdev-memory/hooks/commit-tracker.py plugins/kdev-memory/tests/test_commit_tracker.py
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-memory): add commit-tracker PostToolUse hook with task N/M suppress (task 3/14)"
```

---

## Task 4: 注册 PostToolUse hook in `hooks.json`

**Files:**
- Modify: `plugins/kdev-memory/hooks/hooks.json`

- [ ] **Step 1: Inspect current hooks.json**

Run: `cat plugins/kdev-memory/hooks/hooks.json | head -60`

Look for the existing structure (likely a JSON object with `hooks: {SessionStart: [...], Stop: [...], ...}`).

- [ ] **Step 2: Add PostToolUse entry**

Use Edit to add a new key `PostToolUse` under the `hooks` object, matching the project's existing conventions for command shape (some hooks use `run-python-hook.cmd <script>`, others use a direct python invocation — check what the existing SessionStart entry uses and mirror it).

Example shape (adapt to actual hooks.json indentation/structure):

```json
"PostToolUse": [
  {
    "matcher": "Bash",
    "hooks": [
      {
        "type": "command",
        "command": "<same launcher used by SessionStart> commit-tracker.py"
      }
    ]
  }
]
```

- [ ] **Step 3: Validate JSON parse**

Run:
```bash
python3 -c "import json; json.load(open('plugins/kdev-memory/hooks/hooks.json')); print('OK')"
```
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add plugins/kdev-memory/hooks/hooks.json
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-memory): register commit-tracker as PostToolUse hook on Bash (task 4/14)"
```

---

## Task 5: stop-check.py 加 pending-commits 阈值提醒

**Files:**
- Modify: `plugins/kdev-memory/hooks/stop-check.py`

- [ ] **Step 1: Read current stop-check.py structure to find injection point**

Run: `head -100 plugins/kdev-memory/hooks/stop-check.py`

Locate the function that builds the final hint string for Stop hook output (search for `format_hint_for_stop` or similar).

- [ ] **Step 2: Add import + threshold check**

Near the top, add:
```python
from pending_commits import format_brief_hint as pending_format  # noqa: E402
```

In the hint-building flow, after existing hints, add:
```python
import time
pending_hint = pending_format(Path(".kdev/memory/state"), now=int(time.time()))
if pending_hint:
    hint_lines.append(pending_hint)
```

(Adapt variable names to match actual structure in stop-check.py.)

- [ ] **Step 3: Add a test (or extend existing test file)**

Test: ensure that if pending-commits.json has 3+ entries, the Stop hook output contains the pending hint.

Create `plugins/kdev-memory/tests/test_stop_check_pending.py` if not extending an existing test file:

```python
"""test stop-check.py 注入 pending-commits hint."""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

HOOK = Path(__file__).parent.parent / "hooks" / "stop-check.py"


def _setup_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-q", "--allow-empty", "-m", "init"],
        cwd=repo, check=True,
    )
    (repo / ".kdev" / "memory" / "state").mkdir(parents=True)
    return repo


def _run_hook(repo: Path) -> str:
    r = subprocess.run(
        [sys.executable, str(HOOK)],
        cwd=str(repo), input="{}", capture_output=True, text=True,
    )
    return r.stdout + r.stderr


def test_stop_hook_silent_when_no_pending(tmp_path):
    repo = _setup_repo(tmp_path)
    out = _run_hook(repo)
    assert "pending step-recorder" not in out


def test_stop_hook_warns_when_3_pending(tmp_path):
    repo = _setup_repo(tmp_path)
    state = repo / ".kdev" / "memory" / "state"
    now = int(time.time())
    state.joinpath("pending-commits.json").write_text(json.dumps({
        "since_step_id": "main-15",
        "since_ts": now - 100,
        "commits": [
            {"sha": "a"*40, "subject": "s1", "ts": now - 100},
            {"sha": "b"*40, "subject": "s2", "ts": now - 50},
            {"sha": "c"*40, "subject": "s3", "ts": now - 10},
        ],
    }), encoding="utf-8")
    out = _run_hook(repo)
    assert "pending step-recorder" in out
    assert "3 commit" in out
```

- [ ] **Step 4: Run tests**

```bash
cd plugins/kdev-memory && python3 -m pytest tests/test_stop_check_pending.py -v
```
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add plugins/kdev-memory/hooks/stop-check.py plugins/kdev-memory/tests/test_stop_check_pending.py
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-memory): Stop hook injects pending-commits threshold hint (task 5/14)"
```

---

## Task 6: session-start-brief.py 加 pending + R-005 SHA drift

**Files:**
- Modify: `plugins/kdev-memory/hooks/session-start-brief.py`

- [ ] **Step 1: Locate the startup-mode prog list builder**

Run: `grep -n 'prog = \[' plugins/kdev-memory/hooks/session-start-brief.py`

This finds the line where `prog = ["📊 **今日进度**："...]` is constructed in startup mode (~line 302 per Q-003 task 5 history).

- [ ] **Step 2: Add imports near top of session-start-brief.py (after other lib imports)**

```python
from pending_commits import format_brief_hint as pending_format  # noqa: E402
from skill_version import detect_drift as skill_detect_drift  # noqa: E402
```

- [ ] **Step 3: Augment the startup mode prog list**

After the existing `if git_branch: prog.append(...)` block that adds "本次 Step ID 前缀" line (from Q-003 task 5), insert:

```python
import time
pending_hint = pending_format(kdev_dir / "state", now=int(time.time()))
if pending_hint:
    prog.append(f"- {pending_hint}")

# R-005: SKILL.md SHA drift check
session_id = data.get("session_id", "unknown") if isinstance(data, dict) else "unknown"
cached, current = skill_detect_drift(session_id, Path.cwd(), kdev_dir / "state")
if cached is not None and current is not None and cached != current:
    prog.append(
        f"- ⚠️ SKILL.md 在你会话启动后被升级"
        f"（cached={cached[:7]} → current={current[:7]}）— "
        f"建议 /clear restart 加载新 skill"
    )
```

Note: `data` is the parsed JSON from `_read_source()`. If `_read_source()` only returns `source` string, capture `data` parsing in main() instead — adapt to actual code. If `session_id` isn't available in input JSON, fall back to a stable per-cwd hash.

- [ ] **Step 4: Extend `tests/test_session_start_brief_prefix.py`**

Append two test cases:

```python
import json as _json
import time as _time


def test_brief_shows_pending_commits_when_above_threshold(tmp_path):
    repo = _init_repo_with_kdev(tmp_path, "main")
    state = repo / ".kdev" / "memory" / "state"
    state.mkdir(parents=True, exist_ok=True)
    now = int(_time.time())
    state.joinpath("pending-commits.json").write_text(_json.dumps({
        "since_step_id": "main-15",
        "since_ts": now - 60,
        "commits": [
            {"sha": "a"*40, "subject": "s1", "ts": now - 60},
            {"sha": "b"*40, "subject": "s2", "ts": now - 30},
            {"sha": "c"*40, "subject": "s3", "ts": now - 5},
        ],
    }), encoding="utf-8")
    out = _run_hook(repo)
    ctx = out.get("hookSpecificOutput", {}).get("additionalContext", "")
    assert "pending step-recorder" in ctx
    assert "3 commit" in ctx


def test_brief_shows_drift_when_skill_sha_changes(tmp_path):
    repo = _init_repo_with_kdev(tmp_path, "main")
    # create a fake SKILL.md inside repo (we'll point detect_drift at it)
    skill_dir = repo / "plugins" / "kdev-memory" / "skills" / "kdev-memory"
    skill_dir.mkdir(parents=True)
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text("v1", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-q", "-m", "add skill"],
        cwd=repo, check=True,
    )
    # first run primes cache
    _run_hook(repo)
    # bump SKILL.md + commit
    skill_md.write_text("v2", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-q", "-m", "bump skill"],
        cwd=repo, check=True,
    )
    # second run should detect drift
    out = _run_hook(repo)
    ctx = out.get("hookSpecificOutput", {}).get("additionalContext", "")
    assert "SKILL.md 在你会话启动后被升级" in ctx
```

- [ ] **Step 5: Run all tests**

```bash
cd plugins/kdev-memory && python3 -m pytest tests/test_session_start_brief_prefix.py -v
```
Expected: 4 passed (2 from Q-003 task 5 + 2 new)

- [ ] **Step 6: Commit**

```bash
git add plugins/kdev-memory/hooks/session-start-brief.py plugins/kdev-memory/tests/test_session_start_brief_prefix.py
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-memory): SessionStart brief shows pending-commits + SKILL.md drift (task 6/14)"
```

---

## Task 7: `kdev-step-recorder.md` 加 `commits_batch_id` schema 字段 + clear protocol

**Files:**
- Modify: `plugins/kdev-memory/agents/kdev-step-recorder.md`

- [ ] **Step 1: Locate Input contract YAML schema in the template**

Run: `grep -n "^## Input contract" plugins/kdev-memory/agents/kdev-step-recorder.md`

- [ ] **Step 2: Add `commits_batch_id` field**

Find the YAML schema block under "## Input contract" and append a new line at the bottom of the YAML before the closing triple-backtick:

```yaml
commits_batch_id: <str | null>   # subagent-driven batch 时设为 Q-NNN 或 plan slug；普通工作 null
```

Also add an entry to the Schema's narrative explanation:

> `commits_batch_id` (v0.3 新增, optional): 反向溯源信号。当 dispatch 由 plan-driven batch 触发（commit subject 含 `(Q-XXX task N/M)` 模式），设为 batch 标识；否则 null。不参与 hard-gate 校验。

- [ ] **Step 3: Update action sequence step 5 (clear pending-commits)**

Find the "Action sequence" section's step 5. Replace its body with the more explicit v1 protocol:

```markdown
5. **Clear pending-commits.json**: regardless of whether it existed before, call

   ```python
   import sys; sys.path.insert(0, "plugins/kdev-memory/hooks/lib")
   from pending_commits import clear
   from pathlib import Path
   import time
   clear(Path(".kdev/memory/state"), <minted_id>, int(time.time()))
   ```

   This signals the soft-reminder loop that step is up to date. `<minted_id>` is the
   `Step <slug>-<N>` string you just minted in step 1.
```

- [ ] **Step 4: Update the ✅ Accept-this-summary anti-laziness example**

Find the "✅ Accept this summary (高质量正例)" block. Append `commits_batch_id: null` (since the example is a single-Step dogfood scenario, not a batch).

- [ ] **Step 5: Commit**

```bash
git add plugins/kdev-memory/agents/kdev-step-recorder.md
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "docs(kdev-memory): kdev-step-recorder schema adds commits_batch_id + clear protocol (task 7/14)"
```

---

## Task 8: SKILL.md inline 段 §"用 kdev-step-recorder dispatch 落 step (v0.12+)"

**Files:**
- Modify: `plugins/kdev-memory/skills/kdev-memory/SKILL.md`

- [ ] **Step 1: Locate insertion point**

Run: `grep -n '^## ' plugins/kdev-memory/skills/kdev-memory/SKILL.md | head -20`

Find the line of `## 多 worktree 并发场景：Step ID 加分支前缀（v0.11+）` (currently around line 351). The new section goes immediately after this section's content (before the next `##` header).

- [ ] **Step 2: Insert new section**

Use Edit. Find the last line of the multi-worktree section (the "main 分支特殊性" subsection's last paragraph). Append after it:

````markdown

## 用 kdev-step-recorder dispatch 落 step（v0.12+）

### 何时 dispatch

每完成一个 step-worthy 工作单元（任务 / 决策 / 踩坑 / 用户评分），**主会话不要自己写 Step**——
dispatch [kdev-step-recorder](../../agents/kdev-step-recorder.md) subagent 负责。

判据（满足任一即 step-worthy）：
- 至少 1 个 commit + 完成了一个独立工作单元
- 或：一个 Q-NNN 决策推到拍板态
- 或：一个 G-NNN 踩坑被发现 / 解决
- 或：用户对一个工作单元给评分

**hook 兜底**：若主会话遗忘，commit hook 会累积 pending-commits.json；SessionStart / Stop brief 会显示
`🔔 pending step-recorder dispatch: N commit 累积`——看到提醒立刻 dispatch。

### Dispatch 标准格式

```python
Agent({
  subagent_type: "general-purpose",
  model: "sonnet",
  description: "Record Step <slug>-<N>",
  prompt: """
You are kdev-step-recorder. Read plugins/kdev-memory/agents/kdev-step-recorder.md
for role + 8 hard-gates + action sequence. Work from <repo root>.

## Input (YAML)
```yaml
title: <concrete verb + concrete object>
about: project | feature/<name> | bugfix/<name>
commit_shas: [...]
files_touched: [...]
key_decisions: [...]
key_facts:
  tools_invoked_count: <int>
  errors_hit: <int>
  detours: <int>
  token_feel: light | medium | heavy
self_eval_score: 1-5
self_eval_deduction: <substantive — empty REJECTED>
triggers: [...]   # ≥ 5
references: [...]
commits_batch_id: <Q-NNN or null>
```
"""
})
```

完整 schema、8 hard-gate 规则、反例对照、action sequence 详见
[agents/kdev-step-recorder.md](../../agents/kdev-step-recorder.md)。

### 为什么 dispatch 而不是主会话自己写

主会话被任务流吸住、自然停顿点被预期下一棒吞没——遗忘是常态（R-001 痛点：5/27 实测 75% under-reporting）。
dispatch fire-and-forget = 主会话只付出 ~30 行 YAML 写作 + 立即继续，subagent 干 Read/算/Write/Edit。
比"自己 Read 执行日志 + mint + Write 4 段 + Edit 当前状态" 轻 5-10x。

````

- [ ] **Step 3: Validate YAML frontmatter still parses**

```bash
python3 -c "
import yaml
raw = open('plugins/kdev-memory/skills/kdev-memory/SKILL.md').read()
yaml.safe_load(raw.split('---', 2)[1])
print('YAML OK')
"
```
Expected: `YAML OK`

- [ ] **Step 4: Commit**

```bash
git add plugins/kdev-memory/skills/kdev-memory/SKILL.md
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "docs(kdev-memory): SKILL.md inline § dispatch step-recorder (task 8/14)"
```

---

## Task 9: SKILL.md § 下游 拆分（#1）

**Files:**
- Modify: `plugins/kdev-memory/skills/kdev-memory/SKILL.md`

**Plan**: 把现有 `## 下游：记录如何变成蒸馏原料 + 新 skill`（约 line 321）的 R-NNN→升铁规 那一条移到 `## 规则升级流程`（约 line 191）下作为子 §「原料来源」；§ 下游 改名并只讲蒸馏切片。

- [ ] **Step 1: Identify exact line ranges**

```bash
grep -n '^##' plugins/kdev-memory/skills/kdev-memory/SKILL.md | head -30
```

Find:
- `## 规则升级流程` line (currently ~191)
- `## 下游：记录如何变成蒸馏原料 + 新 skill` line (currently ~321)

- [ ] **Step 2: Append "原料来源" 子§ to § 规则升级流程**

Use Edit. Find the end of the existing § 规则升级流程 section (where it currently says `> 触发信号、必问三件事、默认位置推荐、执行步骤见 ...`). After that line, append:

```markdown

### 原料来源（v0.12+ 显式标注）

R-NNN（项目内方法论反思）→ 累积 ≥ 2 次同主题 或 用户明确"升铁规" → 走升级流程
（必问三件事见 `references/规则升级流程.md`）→ 落到 方法论铁规.md / 项目宪章 / ADR

完整流程见 `references/规则升级流程.md`。
```

- [ ] **Step 3: Rename and restrict § 下游 section**

Use Edit. Find:
```
## 下游：记录如何变成蒸馏原料 + 新 skill
```

Replace the section header + first bullet (R-NNN → 升铁规) with the new restricted form:

```markdown
## 下游：知识蒸馏（markdown 切片包）

通过 `/kdev-memory-distill` 命令按蒸馏目标 filter + sanitize 原 markdown 条目，
产出三个独立 markdown 切片包：
- `dataset-full/` — 全量记录（含 Step / G / Q / R / F），适合通用蒸馏
- `dataset-misalignment/` — 评分差值 ≥ 2 的样本，适合 RLHF
- `dataset-skill-feedback-by-subject/` — F-NNN 按 subject 路由
```

(The remaining content about "markdown 主存 + markdown 切片包导出，不引入 JSONL" architecture line should stay; the "R-NNN → 升铁规" bullet should be removed since it's now in § 规则升级流程.)

- [ ] **Step 4: Verify content shape**

```bash
grep -n '^##\|^### 原料来源' plugins/kdev-memory/skills/kdev-memory/SKILL.md | head -25
```

Should show two distinct sections with R-NNN→升铁规 lives under § 规则升级流程 and § 下游 only mentions distillation.

- [ ] **Step 5: YAML frontmatter check**

```bash
python3 -c "
import yaml
raw = open('plugins/kdev-memory/skills/kdev-memory/SKILL.md').read()
yaml.safe_load(raw.split('---', 2)[1])
print('YAML OK')
"
```

- [ ] **Step 6: Commit**

```bash
git add plugins/kdev-memory/skills/kdev-memory/SKILL.md
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "docs(kdev-memory): SKILL.md § 下游 split — rule upgrade independent from distillation (task 9/14)"
```

---

## Task 10: 初始化-claude-md-模板.md 同步第 1 条铁规

**Files:**
- Modify: `plugins/kdev-memory/skills/kdev-memory/references/初始化-claude-md-模板.md`

- [ ] **Step 1: Locate the "实时落盘" rule in the template**

```bash
grep -n "实时落盘\|追加到.*\.kdev" plugins/kdev-memory/skills/kdev-memory/references/初始化-claude-md-模板.md
```

- [ ] **Step 2: Replace the bullet content**

Use Edit. Find:
```
🔴 **实时落盘**：每做完一个有边界的步骤（任务 / 决策 / 踩坑 / 用户评分）→ **立刻**追加到 `.kdev/memory/` 对应文件。不要攒到会话末尾或"总结一下"时才补录——回忆会失真，评分会褪色。**不需要征求用户许可**即可写入 `.kdev/memory/` 下的任何文件。
```

Replace with:
```
🔴 **实时 dispatch step-recorder 落盘**：每做完一个 step-worthy 工作单元（任务 / 决策 / 踩坑 / 用户评分）→ 主会话**不要自己 Read/Write 执行日志**，而是写一段 YAML summary（schema 见 SKILL.md §用 kdev-step-recorder dispatch 落 step）+ dispatch kdev-step-recorder subagent（sonnet）。subagent 验 8 hard-gate + 写 4 段 Step 条目 + 更新当前状态.md frontmatter + 清空 pending-commits.json。dispatch 是 fire-and-forget——主会话写完 YAML、调用 Agent 后立刻继续下一棒工作，不等 subagent 返回。**Q/G/R/F-NNN 决策类条目仍由主会话直接写**——只有 Step 走 dispatch。**不需要征求用户许可**即可 dispatch + 让 subagent 写入 `.kdev/memory/`。
```

- [ ] **Step 3: Commit**

```bash
git add plugins/kdev-memory/skills/kdev-memory/references/初始化-claude-md-模板.md
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "docs(kdev-memory): init template syncs dispatch step-recorder rule (task 10/14)"
```

---

## Task 11: 项目根 `CLAUDE.md` 第 1 条铁规改写

**Files:**
- Modify: `CLAUDE.md`（worktree 根）

- [ ] **Step 1: Locate the rule in project CLAUDE.md**

```bash
grep -n "实时落盘\|追加到.*\.kdev" CLAUDE.md
```

- [ ] **Step 2: Replace with same content as Task 10's new bullet**

Use Edit with the exact same `old_string` / `new_string` pair as Task 10 (the template and project CLAUDE.md should track each other to satisfy claude-md drift lint).

- [ ] **Step 3: Run drift check**

```bash
python3 plugins/kdev-memory/hooks/lib/claude_md_lint.py plugins/kdev-memory/skills/kdev-memory/references/初始化-claude-md-模板.md CLAUDE.md 2>&1 | head -10
```
Expected: `status: ok, drift: false`

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "docs(kdev-agents): CLAUDE.md syncs dispatch step-recorder rule (task 11/14)"
```

---

## Task 12: e2e dogfood test — dispatch + verify step landed + pending cleared

**Files:**
- Create: `plugins/kdev-memory/tests/test_step_recorder_e2e.py`

This test simulates the full lifecycle without an actual subagent dispatch (which we can't run from within a pytest). Instead, it exercises the lib calls that step-recorder would make.

- [ ] **Step 1: Write the e2e test**

```python
# plugins/kdev-memory/tests/test_step_recorder_e2e.py
"""e2e: simulate step-recorder full lifecycle from input YAML through lib calls.

Doesn't dispatch an actual subagent; tests the lib-level contract that recorder
walks through: mint ID, write step entry, clear pending. R-001 v1 task 12。
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

LIB_DIR = Path(__file__).parent.parent / "hooks" / "lib"
sys.path.insert(0, str(LIB_DIR))

from pending_commits import append as pc_append, clear as pc_clear, read as pc_read  # noqa: E402
from step_id import mint_next_step_id  # noqa: E402


def _init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-q", "--allow-empty", "-m", "init"],
        cwd=repo, check=True,
    )
    (repo / ".kdev" / "memory" / "state").mkdir(parents=True)
    (repo / ".kdev" / "memory" / "执行日志.md").write_text(
        "# 执行日志\n", encoding="utf-8")
    return repo


def test_recorder_lifecycle_mint_step_clear_pending(tmp_path, monkeypatch):
    repo = _init_repo(tmp_path)
    monkeypatch.chdir(repo)

    # Simulate: 3 commits accumulated in pending
    state = repo / ".kdev" / "memory" / "state"
    now = int(time.time())
    pc_append(state, "a"*40, "fix(x): a", now - 100)
    pc_append(state, "b"*40, "fix(x): b", now - 50)
    pc_append(state, "c"*40, "fix(x): c", now - 10)
    assert len(pc_read(state)["commits"]) == 3

    # Recorder action: mint next ID (slug=main)
    minted = mint_next_step_id(state, slug="main")
    assert minted == "Step main-1"

    # Recorder action: write step entry (we just simulate the append here)
    log = repo / ".kdev" / "memory" / "执行日志.md"
    log_text = log.read_text(encoding="utf-8")
    log.write_text(log_text + f"\n## {minted}: e2e test step\n日期：2026-06-02\n",
                   encoding="utf-8")

    # Recorder action: clear pending-commits, update since
    pc_clear(state, minted.replace("Step ", ""), int(time.time()))

    # Verify final state
    pending = pc_read(state)
    assert pending["commits"] == []
    assert pending["since_step_id"] == "main-1"
    assert minted in log.read_text(encoding="utf-8")

    # counter should now read 1 (1 mint happened)
    counter = state.joinpath("step-counter-main.txt").read_text(encoding="utf-8").strip()
    assert counter == "1"
```

- [ ] **Step 2: Run**

```bash
cd plugins/kdev-memory && python3 -m pytest tests/test_step_recorder_e2e.py -v
```
Expected: 1 passed

- [ ] **Step 3: Commit**

```bash
git add plugins/kdev-memory/tests/test_step_recorder_e2e.py
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "test(kdev-memory): e2e step-recorder lifecycle (mint+write+clear) (task 12/14)"
```

---

## Task 13: CHANGELOG bump v0.12.0

**Files:**
- Modify: `plugins/kdev-memory/CHANGELOG.md`

- [ ] **Step 1: Run full test suite to get accurate count**

```bash
cd plugins/kdev-memory && python3 -m pytest tests/ -q --tb=no --deselect tests/test_distill_trigger.py::TestDistillTrigger::test_old_distill_with_new_f_triggers 2>&1 | tail -5
```

Note total passing count.

- [ ] **Step 2: Insert v0.12.0 entry at top of CHANGELOG**

Find the current top entry (likely `## [0.11.0]`). Insert above:

```markdown
## [0.12.0] — 2026-06-02

**R-001 集成：kdev-step-recorder dispatch 接入 SKILL.md / CLAUDE.md 主路径 + commit hook 兜底 + R-005 顺手。**

按 R-001 v1 spec（[docs/skills/kdev-memory/specs/2026-05-29-r-001-step-recorder-integration.md](../../docs/skills/kdev-memory/specs/2026-05-29-r-001-step-recorder-integration.md)）+ 14 task plan 实施。

### ✨ 新增

- **`hooks/lib/pending_commits.py`** — pending-commits.json CRUD + threshold helpers (count 默认 ≥3 / age 默认 ≥30min)
- **`hooks/lib/skill_version.py`** — SKILL.md SHA cache + drift detection (R-005)
- **`hooks/commit-tracker.py`** — PostToolUse Bash hook 检测 git commit + 累积 pending。**suppress 规则**：commit message 含 `\(.*?task N/M.*?\)` 圆括号模式时视为 subagent-driven batch 不计入
- **agents/kdev-step-recorder.md** YAML schema v0.3 加 `commits_batch_id` 字段（optional，不参与 hard-gate）
- **`SKILL.md §"用 kdev-step-recorder dispatch 落 step (v0.12+)"`** 新章节 ~30 行——主会话见此就知道用 dispatch
- **`SKILL.md § 下游 拆分`** — R-NNN→升铁规 移到 § 规则升级流程；§ 下游 改名"知识蒸馏"只讲蒸馏切片

### 🔄 变更

- **CLAUDE.md 第 1 条铁规重写**："实时落盘" → "实时 dispatch step-recorder 落盘"。模板同步。
- **stop-check.py** 加 pending-commits 阈值软提醒
- **session-start-brief.py** 加 (a) pending-commits 状态展示 (b) SKILL.md SHA drift ⚠️ 提醒

### 🔧 兼容

- 老历史 Step / 现有半残 Step 不迁移；新机制上线后逐步消化
- `.kdev/memory/state/pending-commits.json` + `skill-version-cache-*.json` 是 session-local 状态，跟 step-counter-*.txt 共生（继承 `.kdev/` 现状 sync 策略）
- agents/kdev-step-recorder.md v0.2 的 8 hard-gate 全保留；YAML schema 是向后兼容追加

### 📋 升级

升级到 v0.12.0：
1. 拉取代码（plugin update）
2. **重启所有运行中的 Claude Code 会话**（否则旧 session 不感知新 SKILL.md / hook；新机制 R-005 SHA drift 会在重启后 brief 提醒看到）
3. CLAUDE.md 项目根的"实时落盘"段会被自动对齐到新模板

### ✅ 测试

- `tests/test_pending_commits.py`：11 用例
- `tests/test_skill_version.py`：8 用例
- `tests/test_commit_tracker.py`：8 用例（含 task N/M suppress 矩阵）
- `tests/test_session_start_brief_prefix.py`：+2 用例（pending hint + SHA drift）
- `tests/test_stop_check_pending.py`：2 用例
- `tests/test_step_recorder_e2e.py`：1 e2e
- 完整测试套：(actual passing count from Step 1) 通过 + 1 known pre-existing 失败（[R-002](.kdev/memory/改进建议.md)）

---

```

(Replace `(actual passing count from Step 1)` with the real number.)

- [ ] **Step 3: Commit**

```bash
git add plugins/kdev-memory/CHANGELOG.md
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "release(kdev-memory): v0.12.0 — R-001 v1 step-recorder integration (task 13/14)"
```

---

## Task 14: Integration smoke test + Step main-N landing

**Files:**
- Verify: full test suite + live SessionStart brief
- Modify: real `.kdev/memory/执行日志.md` + `当前状态.md`（via dispatch）
- Modify: real `.kdev/memory/state/step-counter-main.txt`（自动）

This task uses the production-state dispatch path from the main session to record this R-001 v1 batch as a real Step (same dogfood pattern as Q-003 task 12).

- [ ] **Step 1: Full test suite**

```bash
cd plugins/kdev-memory && python3 -m pytest tests/ -q --tb=no --deselect tests/test_distill_trigger.py::TestDistillTrigger::test_old_distill_with_new_f_triggers 2>&1 | tail -5
```
Expected: All pass except 1 deselected.

- [ ] **Step 2: Live SessionStart brief smoke**

```bash
echo '{"source":"startup","session_id":"smoke-test-1"}' | python3 plugins/kdev-memory/hooks/session-start-brief.py | python3 -c "
import json, sys
data = json.loads(sys.stdin.read())
ctx = data.get('hookSpecificOutput', {}).get('additionalContext', '')
print(ctx[:500])
"
```

Expected output contains lines like:
- `- 当前分支：main`
- `- 本次 Step ID 前缀：\`main-\`...`
- Possibly `- 🔔 pending step-recorder dispatch: ...` if commit hook accumulated state
- Possibly `- ⚠️ SKILL.md 在你会话启动后被升级...` if state cache mismatches current

- [ ] **Step 3: Live commit-tracker smoke**

Make a small no-op commit to verify hook fires:
```bash
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit --allow-empty -m "chore(kdev-memory): smoke test commit-tracker hook (R-001 v1 task 14)"
cat .kdev/memory/state/pending-commits.json
```

Expected: pending-commits.json contains the new entry with subject "chore(kdev-memory): smoke test commit-tracker hook (R-001 v1 task 14)".

- [ ] **Step 4: Dispatch real step-recorder for this R-001 v1 batch**

Dispatch via Agent tool (or, if running this task inline, write the YAML and call Agent):

```yaml
title: "R-001 v1 落地 — kdev-step-recorder 集成（kdev-memory v0.12.0）"
about: project
commit_shas: [<list all 14 task commit SHAs from this branch>]
files_touched:
  - plugins/kdev-memory/hooks/lib/pending_commits.py
  - plugins/kdev-memory/hooks/lib/skill_version.py
  - plugins/kdev-memory/hooks/commit-tracker.py
  - plugins/kdev-memory/hooks/hooks.json
  - plugins/kdev-memory/hooks/stop-check.py
  - plugins/kdev-memory/hooks/session-start-brief.py
  - plugins/kdev-memory/agents/kdev-step-recorder.md
  - plugins/kdev-memory/skills/kdev-memory/SKILL.md
  - plugins/kdev-memory/skills/kdev-memory/references/初始化-claude-md-模板.md
  - CLAUDE.md
  - plugins/kdev-memory/CHANGELOG.md
  - plugins/kdev-memory/tests/test_pending_commits.py
  - plugins/kdev-memory/tests/test_skill_version.py
  - plugins/kdev-memory/tests/test_commit_tracker.py
  - plugins/kdev-memory/tests/test_step_recorder_e2e.py
  - plugins/kdev-memory/tests/test_stop_check_pending.py
key_decisions:
  - R-001 痛点 70-80% closure 目标，软提醒不硬刹车
  - commit hook 用 `(.*?task N/M.*?)` 圆括号正则识别 subagent-driven batch 并 suppress
  - SKILL.md inline ~30 行 dispatch 契约（不藏 reference 文件），新会话开箱即用
  - CLAUDE.md 第 1 条铁规重写而非加第 4 条——避免铁规数量膨胀 + 与第 1 条语义衔接
  - R-005 顺手做 SessionStart SHA drift 检测——session-local cache + sanitize session_id
  - SKILL.md § 下游 拆分（#1）——升铁规独立 § + 蒸馏独立 §
key_facts:
  tools_invoked_count: <est. 60-100>
  errors_hit: <count actual errors during execution>
  detours: <count rework loops>
  token_feel: medium
self_eval_score: 4
self_eval_deduction: "<填实施完成后回填——比如 hook 测试 mock 复杂度、跨 SKILL.md 段落迁移精度等具体扣分>"
triggers: [r-001, kdev-step-recorder, v0.12, integration, commit-hook, pending-commits, r-005, skill-staleness, dispatch, 4段硬闸门]
references: [R-001, R-002, R-005, Q-002, Q-003, F-001]
commits_batch_id: R-001-v1
```

Expected after dispatch:
- `.kdev/memory/state/step-counter-main.txt` 推 1
- `.kdev/memory/执行日志.md` 末尾追加 `## Step main-<N>: R-001 v1 落地...`
- `.kdev/memory/当前状态.md` frontmatter 改 `current_step: main-<N>`
- `.kdev/memory/state/pending-commits.json` 清空 + `since_step_id: main-<N>`

- [ ] **Step 5: Verify final state**

```bash
echo "=== counter ===" && cat .kdev/memory/state/step-counter-main.txt
echo "=== current_step ===" && grep current_step .kdev/memory/当前状态.md
echo "=== last step heading ===" && grep "^## Step " .kdev/memory/执行日志.md | tail -1
echo "=== pending cleared? ===" && cat .kdev/memory/state/pending-commits.json
```

Expected all 4 checks consistent with a newly minted Step main-N for R-001 v1 batch.

- [ ] **Step 6: Final summary**

No additional commit (state files are in `.kdev/` untracked). Report to user with summary of:
- Branch SHAs (14 commits)
- Final test count
- Step main-N minted
- Counter value
- Pending state cleared

---

## 收尾验证清单

```bash
# 1. 全测试套（排除 R-002 pre-existing）
cd plugins/kdev-memory && python3 -m pytest tests/ -q --tb=no --deselect tests/test_distill_trigger.py::TestDistillTrigger::test_old_distill_with_new_f_triggers

# 2. CLAUDE.md drift check
python3 plugins/kdev-memory/hooks/lib/claude_md_lint.py plugins/kdev-memory/skills/kdev-memory/references/初始化-claude-md-模板.md CLAUDE.md

# 3. SessionStart brief 含新 hint
echo '{"source":"startup","session_id":"verify"}' | python3 plugins/kdev-memory/hooks/session-start-brief.py | python3 -m json.tool

# 4. commit-tracker hook 路径正确
ls -la plugins/kdev-memory/hooks/commit-tracker.py  # 应有 +x

# 5. pending-commits.json 格式 valid
python3 -c "import json; print(json.load(open('.kdev/memory/state/pending-commits.json')))"
```

---

## 子决策需要在实施前向用户确认

Spec 的 Open questions 都属于 v1 外（#2+#3 + A+B 留 brainstorm 轮二），本 plan 不需要额外子决策。但实施期间若发现以下情形，**暂停 + 向用户问**：

1. **Task 4 hooks.json 结构与预期不符**（如已有 PostToolUse 节点）—— ask before overwriting
2. **Task 9 § 下游 拆分时发现段落引用别处**（如 references/ 文件提到"§ 下游"字面）—— 决定要不要级联改其他 reference 文件
3. **Task 14 dispatch 时 hard-gate 拒收** —— 调整 YAML summary 而非削弱 gate

---

## 风险登记

| 风险 | 概率 | 后果 | 缓解 |
|------|------|------|------|
| commit-tracker hook 不识别 `git commit` 某种 shell quoting 变体 | 中 | 误漏一些 commit 不计入 pending | regex token-by-token + 测试覆盖 `git -c k=v commit -m msg` / 直接 `git commit` / heredoc msg |
| stop-check.py 注入 pending hint 时 break 既有 Stop 行为 | 低-中 | Stop hook 不工作 | inject 加在既有 hint 之后；测试覆盖 silent 和 fire 两种 |
| session-start-brief 加 R-005 SHA check 在 non-git 仓库下 crash | 低 | brief 不工作 | `current_skill_sha` 返回 None 时静默；测试覆盖 |
| Task 9 § 下游 拆分时漏 R-NNN 升铁规的所有引用 | 低 | 其他 reference 文件仍指向旧 § 名 | grep 全 references/ 找 "§ 下游" 字面引用，按需级联改 |
| Task 14 dispatch 时主会话状态污染（current_step 已被并发 session 改） | 中 | gate 8 reject 或冲突写入 | 实施期间用单 worktree，避免并发；reconcile 同 Q-003 task 12 流程 |
| commit hook 累积 .kdev/state/ 但用户没看 brief → 无效兜底 | 高 | R-001 痛点封堵率不达预期 | spec 接受 20-30% 漏仔率作为 v1 trade-off；后续看实际数据决定 v2 强化 |

---

## 范围外（已知 v1 不处理）

- **`.kdev/` 多机/多人 sync 策略**（#2+#3 + A+B）—— 独立 brainstorm 轮二
- **framework design 无 commit 场景**（v1 接受 `# main-N: ...` 注释行 escape hatch）
- **历史 14 半残 Step backfill**（hook 上线后自然消化）
- **YAML hard-gate 1 (title generic) 更强结构化判定**（留 v0.3）
- **commit-tracker 识别 git amend / rebase**（只识别新 commit）
