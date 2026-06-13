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
from step_id import mint_record_id, parse_record_id  # noqa: E402


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

    # Recorder action: mint next ID via timestamp primitive (Q-020)
    minted = mint_record_id("Step", state)
    assert minted.startswith("Step ")
    parsed = parse_record_id(minted)
    assert parsed is not None
    assert parsed["scheme"] == "timestamp"

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
    # since_step_id is the timestamp ID portion (strip "Step " prefix)
    assert pending["since_step_id"] == minted[len("Step "):]
    assert minted in log.read_text(encoding="utf-8")

    # No counter file written — timestamp IDs have no counter (Q-020)
    assert not list(state.glob("step-counter-*.txt"))
