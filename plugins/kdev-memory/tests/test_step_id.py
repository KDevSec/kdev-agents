"""test step_id.py: branch slug 计算 + counter atomic 递增 + mint_next_step_id。"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

LIB_DIR = Path(__file__).parent.parent / "hooks" / "lib"
sys.path.insert(0, str(LIB_DIR))

from step_id import compute_branch_slug  # noqa: E402


def _git_init(tmp_path: Path, branch: str = "main") -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", branch], cwd=repo, check=True)
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-q", "--allow-empty", "-m", "init"],
        cwd=repo, check=True,
    )
    return repo


def _git_checkout(repo: Path, branch: str) -> None:
    subprocess.run(["git", "checkout", "-q", "-b", branch], cwd=repo, check=True)


def test_slug_main(tmp_path, monkeypatch):
    repo = _git_init(tmp_path, "main")
    monkeypatch.chdir(repo)
    assert compute_branch_slug() == "main"


def test_slug_master(tmp_path, monkeypatch):
    repo = _git_init(tmp_path, "master")
    monkeypatch.chdir(repo)
    assert compute_branch_slug() == "master"


def test_slug_feature_prefix_stripped(tmp_path, monkeypatch):
    repo = _git_init(tmp_path)
    _git_checkout(repo, "feature/cluster-x1")
    monkeypatch.chdir(repo)
    assert compute_branch_slug() == "cluster-x1"


def test_slug_feat_prefix_stripped(tmp_path, monkeypatch):
    repo = _git_init(tmp_path)
    _git_checkout(repo, "feat/foo/bar")
    monkeypatch.chdir(repo)
    assert compute_branch_slug() == "foo-bar"


def test_slug_bugfix_prefix_kept(tmp_path, monkeypatch):
    repo = _git_init(tmp_path)
    _git_checkout(repo, "bugfix/issue-42")
    monkeypatch.chdir(repo)
    assert compute_branch_slug() == "bugfix-issue-42"


def test_slug_detached_head(tmp_path, monkeypatch):
    repo = _git_init(tmp_path)
    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True, check=True
    ).stdout.strip()
    subprocess.run(["git", "checkout", "-q", sha], cwd=repo, check=True)
    monkeypatch.chdir(repo)
    assert compute_branch_slug() == "detached"


def test_slug_not_in_repo(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert compute_branch_slug() == "unknown"


def test_slug_sanitize_unicode(tmp_path, monkeypatch):
    repo = _git_init(tmp_path)
    _git_checkout(repo, "实验/中文分支")
    monkeypatch.chdir(repo)
    slug = compute_branch_slug()
    assert "/" not in slug
    assert all(c.isascii() and (c.isalnum() or c in "-_") for c in slug)
