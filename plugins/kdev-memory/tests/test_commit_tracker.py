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
    # 真实 Claude Code PostToolUse stdin 契约：snake_case（hooks.md Common input fields）
    payload = json.dumps({
        "tool_name": "Bash",
        "tool_input": {"command": command},
        "transcript_path": str(repo / "fake-transcript.jsonl"),
        "session_id": "test-session",
    })
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


def test_gitlab_prefix_does_not_match(tmp_path):
    """`gitlab commit` / `github-cli commit` etc. must NOT match git commit."""
    repo = _make_repo_with_commit(tmp_path, "normal")
    _run_hook(repo, "gitlab commit -m fake")
    assert _read_pending(repo)["commits"] == []


def test_git_uppercase_C_flag_handled(tmp_path):
    """`git -C <path> commit ...` must be recognized as git commit."""
    repo = _make_repo_with_commit(tmp_path, "uppercase C arg test")
    _run_hook(repo, f"git -C {repo} commit -m x")
    assert len(_read_pending(repo)["commits"]) == 1


def test_hook_does_not_bootstrap_kdev_memory_when_uninitialized(tmp_path):
    """未初始化 .kdev/memory 的工程跑 git commit → hook 必须静默退出，
    不得凭空创建 .kdev/memory/（与 session-start/end/pre-compact/post-write 一致的存在性门控）。

    回归 bug：commit-tracker 曾直接调 pending_commits.append → _write() 里
    state_dir.mkdir(parents=True) 把整个 .kdev/memory/ 自举出来，污染无关工程。
    """
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
    # 起点：确实没有 .kdev/
    assert not (repo / ".kdev").exists()
    _run_hook(repo, "git commit -m fresh")
    # 修复后：hook 不应自举 .kdev/memory/
    assert not (repo / ".kdev").exists(), (
        "commit-tracker 不应在未初始化工程里凭空创建 .kdev/memory/"
    )
    # pending 自然也不该有
    assert _read_pending(repo)["commits"] == []


def test_hook_resilient_to_missing_state_dir(tmp_path):
    """已初始化工程（.kdev/memory/ 存在）但 state 子目录还没建 → hook 照常累积，
    由 pending_commits.append 自动建 state/。这是「已初始化」路径，不受存在性门控影响。"""
    repo = tmp_path / "repo"
    repo.mkdir()
    # 关键：.kdev/memory/ 已存在（已初始化），但 state/ 子目录尚未建
    (repo / ".kdev" / "memory").mkdir(parents=True)
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


def test_commit_stashes_transcript_path(tmp_path):
    repo = _make_repo_with_commit(tmp_path, "stash transcript test")
    tp = repo / "sess.jsonl"
    tp.write_text("{}\n{}\n{}\n", encoding="utf-8")  # 3 行真实文件
    payload = json.dumps({
        "tool_name": "Bash",
        "tool_input": {"command": "git commit -m stash"},
        "transcript_path": str(tp),
        "session_id": "s1",
    })
    subprocess.run([sys.executable, str(HOOK)], cwd=str(repo), input=payload,
                   capture_output=True, text=True,
                   encoding="utf-8", errors="replace")
    pending = _read_pending(repo)
    assert pending["transcript_path"] == str(tp)
