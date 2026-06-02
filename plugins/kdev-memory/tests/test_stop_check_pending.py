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
