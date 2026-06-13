"""test session-start-brief 分支显示（Step ID 前缀行已移除，v0.17+）。"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HOOK = Path(__file__).parent.parent / "hooks" / "session-start-brief.py"


def _init_repo_with_kdev(tmp_path: Path, branch: str = "main") -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", branch], cwd=repo, check=True)
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-q", "--allow-empty", "-m", "init"],
        cwd=repo, check=True,
    )
    (repo / ".kdev" / "memory").mkdir(parents=True)
    (repo / ".kdev" / "memory" / "执行日志.md").write_text("# 执行日志\n", encoding="utf-8")
    return repo


def _run_hook(repo: Path, source: str = "startup") -> dict:
    payload = json.dumps({"source": source})
    r = subprocess.run(
        [sys.executable, str(HOOK)],
        cwd=str(repo), input=payload, capture_output=True, text=True,
    )
    return json.loads(r.stdout) if r.stdout.strip() else {}


def test_brief_shows_branch_name(tmp_path):
    """brief 显示当前分支名，但不再显示 Step ID 前缀行（v0.17+ 时间戳方案）。"""
    repo = _init_repo_with_kdev(tmp_path, "main")
    out = _run_hook(repo)
    ctx = out.get("hookSpecificOutput", {}).get("additionalContext", "")
    assert "当前分支" in ctx
    assert "main" in ctx
    # v0.17+：brief 不再显示「本次 Step ID 前缀」
    assert "本次 Step ID 前缀" not in ctx


def test_brief_shows_feature_branch_name(tmp_path):
    """feature 分支名出现在 brief 中，但无前缀行。"""
    repo = _init_repo_with_kdev(tmp_path, "main")
    subprocess.run(["git", "checkout", "-q", "-b", "feature/cluster-x1"], cwd=repo, check=True)
    out = _run_hook(repo)
    ctx = out.get("hookSpecificOutput", {}).get("additionalContext", "")
    assert "feature/cluster-x1" in ctx
    assert "本次 Step ID 前缀" not in ctx


import json as _json
import time as _time


def test_brief_shows_pending_commits_when_above_threshold(tmp_path):
    # P-C1b：age 为主——commit 累积超过 age 阈值（最早 > 1800s）才 nudge
    repo = _init_repo_with_kdev(tmp_path, "main")
    state = repo / ".kdev" / "memory" / "state"
    state.mkdir(parents=True, exist_ok=True)
    now = int(_time.time())
    state.joinpath("pending-commits.json").write_text(_json.dumps({
        "since_step_id": "main-15",
        "since_ts": now - 2000,
        "commits": [
            {"sha": "a"*40, "subject": "s1", "ts": now - 2000},  # age=2000 > 1800
            {"sha": "b"*40, "subject": "s2", "ts": now - 1000},
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
