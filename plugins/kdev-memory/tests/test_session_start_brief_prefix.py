"""test session-start-brief 注入 Step ID 前缀提示。"""
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


def test_brief_shows_main_prefix(tmp_path):
    repo = _init_repo_with_kdev(tmp_path, "main")
    out = _run_hook(repo)
    ctx = out.get("hookSpecificOutput", {}).get("additionalContext", "")
    assert "本次 Step ID 前缀" in ctx
    assert "main-" in ctx


def test_brief_shows_feature_branch_prefix(tmp_path):
    repo = _init_repo_with_kdev(tmp_path, "main")
    subprocess.run(["git", "checkout", "-q", "-b", "feature/cluster-x1"], cwd=repo, check=True)
    out = _run_hook(repo)
    ctx = out.get("hookSpecificOutput", {}).get("additionalContext", "")
    assert "cluster-x1-" in ctx
