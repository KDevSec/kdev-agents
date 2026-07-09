"""kdev↔ieidev 共存守卫（让位协议）测试。

协议：一个仓里只要 `.ieidev/memory/` 存在，kdev 就整体让位、全静默——
每个钉了 Claude Code 事件的 hook 都要「零输出（或仅 SUPPRESS）、零写盘、零催建」。
对照组只有 `.kdev/memory`（无 ieidev）→ 原行为逐字不变。

结构：先测 helper 本身，再逐 hook（defer + 对照）。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import date
from pathlib import Path

HOOKS = Path(__file__).parent.parent / "hooks"
LIB = HOOKS / "lib"
sys.path.insert(0, str(LIB))

import coexist  # noqa: E402

SUPPRESS = json.dumps({"continue": True, "suppressOutput": True})


def _utf8_env(**extra) -> dict:
    e = {**os.environ, "LANG": "en_US.UTF-8", "LC_ALL": "en_US.UTF-8"}
    e.update(extra)
    return e


def _git(args, cwd):
    subprocess.run(["git", *args], cwd=str(cwd), check=True,
                   capture_output=True, text=True)


def _init_code_repo(root: Path) -> None:
    _git(["init", "-q", "-b", "main"], root)


def _mk_kdev(root: Path) -> Path:
    mem = root / ".kdev" / "memory"
    mem.mkdir(parents=True)
    return mem


def _mk_ieidev(root: Path) -> Path:
    mem = root / ".ieidev" / "memory"
    mem.mkdir(parents=True)
    return mem


def _run(hook: str, cwd: Path, *, stdin: str = "", env=None):
    return subprocess.run(
        [sys.executable, str(HOOKS / hook)],
        cwd=str(cwd), input=stdin, capture_output=True, text=True,
        env=env or _utf8_env(),
    )


# ---------------------------------------------------------------------------
# helper 本体
# ---------------------------------------------------------------------------

def test_defer_false_when_no_ieidev(tmp_path, monkeypatch):
    _mk_kdev(tmp_path)
    monkeypatch.chdir(tmp_path)
    assert coexist.defer_to_ieidev() is False


def test_defer_true_when_ieidev_memory_present(tmp_path, monkeypatch):
    _mk_kdev(tmp_path)
    _mk_ieidev(tmp_path)
    monkeypatch.chdir(tmp_path)
    assert coexist.defer_to_ieidev() is True


def test_defer_true_even_without_kdev(tmp_path, monkeypatch):
    """让位无条件：ieidev 在场即让位，哪怕 .kdev 不存在。"""
    _mk_ieidev(tmp_path)
    monkeypatch.chdir(tmp_path)
    assert coexist.defer_to_ieidev() is True


def test_defer_true_on_migrated_marker(tmp_path, monkeypatch):
    """加分项：ieidev 迁移器留的 marker 也短路（.ieidev/memory 尚未落地窗口）。"""
    mem = _mk_kdev(tmp_path)
    (mem / ".migrated-to-ieidev").write_text("", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert coexist.defer_to_ieidev() is True


def test_defer_respects_root_param(tmp_path):
    _mk_kdev(tmp_path)
    _mk_ieidev(tmp_path)
    # cwd 无关，显式 root 命中
    assert coexist.defer_to_ieidev(root=tmp_path) is True
    assert coexist.defer_to_ieidev(root=tmp_path / ".kdev") is False


# ---------------------------------------------------------------------------
# commit-tracker.py（PostToolUse Bash · 静默形态 = print(SUPPRESS)）
# ---------------------------------------------------------------------------

def _commit_repo(root: Path) -> str:
    (root / ".kdev" / "memory" / "state").mkdir(parents=True, exist_ok=True)
    _init_code_repo(root)
    (root / "f.txt").write_text("x", encoding="utf-8")
    _git(["add", "f.txt"], root)
    _git(["-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "feat: normal"], root)
    return "git -c user.email=t@t -c user.name=t commit -q -m x"


def _pending(root: Path) -> dict:
    p = root / ".kdev" / "memory" / "state" / "pending-commits.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {"commits": []}


def test_commit_tracker_defers(tmp_path):
    cmd = _commit_repo(tmp_path)
    _mk_ieidev(tmp_path)
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd},
                          "transcript_path": str(tmp_path / "t.jsonl")})
    r = _run("commit-tracker.py", tmp_path, stdin=payload)
    assert r.stdout.strip() == SUPPRESS
    assert r.stderr.strip() == ""
    assert _pending(tmp_path)["commits"] == []  # 零写盘：未累积 pending


def test_commit_tracker_control(tmp_path):
    cmd = _commit_repo(tmp_path)  # 无 .ieidev
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd},
                          "transcript_path": str(tmp_path / "t.jsonl")})
    r = _run("commit-tracker.py", tmp_path, stdin=payload)
    assert r.stdout.strip() == SUPPRESS
    assert len(_pending(tmp_path)["commits"]) == 1  # 原行为：累积 1 条


# ---------------------------------------------------------------------------
# post-write-check.py（PostToolUse Write/Edit · 静默形态 = return，不打字）
# ---------------------------------------------------------------------------

def _milestone_payload(root: Path) -> str:
    fp = root / "docs" / "adr" / "0001-x.md"
    return json.dumps({"tool_name": "Write", "tool_input": {"file_path": str(fp)}})


def test_post_write_defers_milestone_reminder(tmp_path):
    _mk_kdev(tmp_path)
    _mk_ieidev(tmp_path)
    r = _run("post-write-check.py", tmp_path, stdin=_milestone_payload(tmp_path))
    assert r.stdout.strip() == ""       # 零催建
    assert r.stderr.strip() == ""


def test_post_write_control_milestone_reminder(tmp_path):
    _mk_kdev(tmp_path)
    r = _run("post-write-check.py", tmp_path, stdin=_milestone_payload(tmp_path))
    assert "里程碑" in r.stdout          # 原行为：软提醒


def test_post_write_defers_last_flush_touch(tmp_path):
    _mk_kdev(tmp_path)
    _mk_ieidev(tmp_path)
    fp = tmp_path / ".kdev" / "memory" / "执行日志.md"
    payload = json.dumps({"tool_name": "Write", "tool_input": {"file_path": str(fp)}})
    _run("post-write-check.py", tmp_path, stdin=payload)
    assert not (tmp_path / ".kdev" / "memory" / ".last-flush").exists()  # 零写盘


def test_post_write_control_last_flush_touch(tmp_path):
    _mk_kdev(tmp_path)
    fp = tmp_path / ".kdev" / "memory" / "执行日志.md"
    payload = json.dumps({"tool_name": "Write", "tool_input": {"file_path": str(fp)}})
    _run("post-write-check.py", tmp_path, stdin=payload)
    assert (tmp_path / ".kdev" / "memory" / ".last-flush").exists()


# ---------------------------------------------------------------------------
# session-start-brief.py（SessionStart · 静默形态 = print(SUPPRESS)）
# ---------------------------------------------------------------------------

def _brief_stdin(root: Path) -> str:
    return json.dumps({"source": "startup", "session_id": "t",
                       "transcript_path": str(root / "t.jsonl")})


def test_session_start_brief_defers(tmp_path):
    mem = _mk_kdev(tmp_path)
    (mem / "当前状态.md").write_text("---\nphase: x\n---\n", encoding="utf-8")
    _mk_ieidev(tmp_path)
    r = _run("session-start-brief.py", tmp_path, stdin=_brief_stdin(tmp_path))
    assert r.stdout.strip() == SUPPRESS  # 仅 SUPPRESS，无 brief 注入
    # 零写盘：未 stash transcript 指针
    assert not (tmp_path / ".kdev" / "memory" / "state" / ".current-transcript").exists()


def test_session_start_brief_control(tmp_path):
    mem = _mk_kdev(tmp_path)
    (mem / "当前状态.md").write_text("---\nphase: x\n---\n", encoding="utf-8")
    r = _run("session-start-brief.py", tmp_path, stdin=_brief_stdin(tmp_path))
    assert "additionalContext" in r.stdout  # 原行为：注入 brief


# ---------------------------------------------------------------------------
# user-prompt-trigger.py（UserPromptSubmit · 静默形态 = print(SUPPRESS)）
# ---------------------------------------------------------------------------

def _prompt_stdin(root: Path) -> str:
    return json.dumps({"prompt": "hello", "transcript_path": str(root / "t.jsonl")})


def _stash_file(root: Path) -> Path:
    return root / ".kdev" / "memory" / "state" / ".current-transcript"


def test_user_prompt_trigger_defers(tmp_path):
    _mk_kdev(tmp_path)
    _mk_ieidev(tmp_path)
    r = _run("user-prompt-trigger.py", tmp_path, stdin=_prompt_stdin(tmp_path))
    assert r.stdout.strip() == SUPPRESS
    assert not _stash_file(tmp_path).exists()  # 零写盘：未 stash


def test_user_prompt_trigger_control(tmp_path):
    _mk_kdev(tmp_path)
    _run("user-prompt-trigger.py", tmp_path, stdin=_prompt_stdin(tmp_path))
    assert _stash_file(tmp_path).exists()  # 原行为：stash 了 transcript 指针


# ---------------------------------------------------------------------------
# session-end-check.py（SessionEnd · 静默形态 = return，不打字）
# ---------------------------------------------------------------------------

def _end_setup(root: Path):
    mem = _mk_kdev(root)
    (mem / "执行日志.md").write_text("# 执行日志\n", encoding="utf-8")
    _init_code_repo(root)
    flush = mem / ".last-flush"
    flush.touch()
    old = time.time() - 3600
    os.utime(flush, (old, old))
    (mem / "执行日志.md").write_text("# 执行日志\n\n## Step 1\n", encoding="utf-8")


def _warn_file(root: Path) -> Path:
    return root / ".kdev" / "memory" / f"WARN-未记录-{date.today().isoformat()}.md"


def test_session_end_defers(tmp_path):
    _end_setup(tmp_path)
    _mk_ieidev(tmp_path)
    r = _run("session-end-check.py", tmp_path)
    assert r.stdout.strip() == ""
    assert not _warn_file(tmp_path).exists()  # 零写盘：无 WARN


def test_session_end_control(tmp_path):
    _end_setup(tmp_path)
    _run("session-end-check.py", tmp_path)
    assert _warn_file(tmp_path).exists()  # 原行为：写 WARN


# ---------------------------------------------------------------------------
# pre-compact-check.py（PreCompact · 静默形态 = return，不打字）
# ---------------------------------------------------------------------------

def _checkpoints(root: Path):
    d = root / ".kdev" / "memory" / "checkpoints"
    return list(d.glob("压缩前-*.md")) if d.is_dir() else []


def test_pre_compact_defers(tmp_path):
    mem = _mk_kdev(tmp_path)
    (mem / "执行日志.md").write_text("# 执行日志\n", encoding="utf-8")
    _init_code_repo(tmp_path)
    _mk_ieidev(tmp_path)
    r = _run("pre-compact-check.py", tmp_path, stdin=json.dumps({"trigger": "auto"}))
    assert r.stdout.strip() == ""
    assert _checkpoints(tmp_path) == []  # 零写盘：不写 checkpoint


def test_pre_compact_control(tmp_path):
    mem = _mk_kdev(tmp_path)
    (mem / "执行日志.md").write_text("# 执行日志\n", encoding="utf-8")
    _init_code_repo(tmp_path)
    _run("pre-compact-check.py", tmp_path, stdin=json.dumps({"trigger": "auto"}))
    assert len(_checkpoints(tmp_path)) == 1  # 原行为：写 checkpoint


# ---------------------------------------------------------------------------
# stop-check.py（Stop · 静默形态 = return，不打字）
# ---------------------------------------------------------------------------

def test_stop_check_defers(tmp_path):
    mem = _mk_kdev(tmp_path)
    (mem / "执行日志.md").write_text("# 执行日志\n", encoding="utf-8")
    _mk_ieidev(tmp_path)
    r = _run("stop-check.py", tmp_path, stdin=json.dumps({}))
    assert r.stdout.strip() == ""
    assert r.stderr.strip() == ""


def test_stop_check_control(tmp_path):
    mem = _mk_kdev(tmp_path)
    (mem / "执行日志.md").write_text("# 执行日志\n", encoding="utf-8")
    r = _run("stop-check.py", tmp_path, stdin=json.dumps({}))
    assert "[kdev-memory]" in r.stdout  # 原行为：软提醒


# ---------------------------------------------------------------------------
# kdev-sync-bootstrap.py（SessionStart · 静默形态 = return，不打字；催建 reminder 必须闭嘴）
# ---------------------------------------------------------------------------

def test_sync_bootstrap_defers(tmp_path):
    _mk_kdev(tmp_path)  # kdev 非空、无 .kdev/.git、无 remote → 正常会 init-local + 催建
    _mk_ieidev(tmp_path)
    env = _utf8_env(CLAUDE_PROJECT_DIR=str(tmp_path))
    r = _run("kdev-sync-bootstrap.py", tmp_path, env=env)
    assert r.stdout.strip() == ""                       # 零催建
    assert not (tmp_path / ".kdev" / ".git").exists()   # 零写盘：不自举记忆仓


def test_sync_bootstrap_control(tmp_path):
    _mk_kdev(tmp_path)
    env = _utf8_env(CLAUDE_PROJECT_DIR=str(tmp_path))
    r = _run("kdev-sync-bootstrap.py", tmp_path, env=env)
    # 原行为：init-local 建本地记忆仓 + 弹催建提醒
    assert (tmp_path / ".kdev" / ".git").exists()
    assert "kdev-sync-reminder" in r.stdout


# ---------------------------------------------------------------------------
# kdev-sync-push.py（SessionEnd · 静默形态 = return，不打字）
# ---------------------------------------------------------------------------

def _init_memory_repo(root: Path) -> int:
    """在 .kdev 建 nested memory repo，提交一次，返回当前 commit 数。"""
    kdev = root / ".kdev"
    _git(["init", "-q", "-b", "main"], kdev)
    _git(["-c", "user.email=k@k", "-c", "user.name=k", "commit", "--allow-empty", "-q", "-m", "init"], kdev)
    return int(subprocess.run(["git", "rev-list", "--count", "HEAD"], cwd=kdev,
                              capture_output=True, text=True).stdout.strip())


def _head_count(root: Path) -> int:
    r = subprocess.run(["git", "rev-list", "--count", "HEAD"], cwd=root / ".kdev",
                       capture_output=True, text=True)
    return int(r.stdout.strip() or "0")


def test_sync_push_defers(tmp_path):
    _mk_kdev(tmp_path)
    n0 = _init_memory_repo(tmp_path)
    (tmp_path / ".kdev" / "memory" / "new.md").write_text("x", encoding="utf-8")  # dirty
    _mk_ieidev(tmp_path)
    env = _utf8_env(CLAUDE_PROJECT_DIR=str(tmp_path))
    r = _run("kdev-sync-push.py", tmp_path, env=env)
    assert r.stdout.strip() == ""
    assert _head_count(tmp_path) == n0  # 零写盘：未 commit（HEAD 不前进）
    assert not (tmp_path / ".kdev" / "memory" / f"WARN-记忆未推送-{date.today().isoformat()}.md").exists()


def test_sync_push_control(tmp_path):
    _mk_kdev(tmp_path)
    n0 = _init_memory_repo(tmp_path)
    (tmp_path / ".kdev" / "memory" / "new.md").write_text("x", encoding="utf-8")
    env = _utf8_env(CLAUDE_PROJECT_DIR=str(tmp_path))
    _run("kdev-sync-push.py", tmp_path, env=env)
    assert _head_count(tmp_path) == n0 + 1  # 原行为：commit 了新变更（HEAD 前进）
