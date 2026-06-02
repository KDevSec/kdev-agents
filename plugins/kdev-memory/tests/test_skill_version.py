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
