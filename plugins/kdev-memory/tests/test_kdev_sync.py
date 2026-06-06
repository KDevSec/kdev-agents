"""Tests for hooks/lib/kdev_sync.py — Q-009 git 托管自举."""
import importlib.util
from pathlib import Path

import pytest

LIB = Path(__file__).parent.parent / "hooks" / "lib" / "kdev_sync.py"
_spec = importlib.util.spec_from_file_location("kdev_sync", LIB)
kdev_sync = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(kdev_sync)


def test_read_config_missing_file_defaults(tmp_path):
    cfg = kdev_sync.read_sync_config(tmp_path)
    assert cfg["memory_repo"] is None
    assert cfg["branch"] == "main"


def test_read_config_parses_repo_and_branch(tmp_path):
    (tmp_path / "kdev-sync.yml").write_text(
        "# memory hosting\nmemory_repo: git@github.com:org/mem.git\nbranch: trunk\n",
        encoding="utf-8",
    )
    cfg = kdev_sync.read_sync_config(tmp_path)
    assert cfg["memory_repo"] == "git@github.com:org/mem.git"
    assert cfg["branch"] == "trunk"


def test_read_config_strips_quotes_and_inline_comments(tmp_path):
    (tmp_path / "kdev-sync.yml").write_text(
        'memory_repo: "https://x/y.git"   # the remote\n', encoding="utf-8")
    assert kdev_sync.read_sync_config(tmp_path)["memory_repo"] == "https://x/y.git"


def test_read_config_blank_repo_is_none(tmp_path):
    (tmp_path / "kdev-sync.yml").write_text("memory_repo:\nbranch: main\n", encoding="utf-8")
    assert kdev_sync.read_sync_config(tmp_path)["memory_repo"] is None


def test_reminder_text_is_chinese_and_mentions_nested_repo():
    t = kdev_sync.reminder_text()
    assert "记忆仓" in t and "nested repo" in t


def test_decide_pull_when_has_git():
    # .kdev/.git present -> always pull (uses .kdev's own remote), regardless of yml remote.
    assert kdev_sync.decide_action(has_git=True, kdev_nonempty=True, remote=None) == "pull"
    assert kdev_sync.decide_action(has_git=True, kdev_nonempty=True, remote="r") == "pull"


def test_decide_clone_when_empty_and_remote():
    assert kdev_sync.decide_action(has_git=False, kdev_nonempty=False, remote="r") == "clone"


def test_decide_init_when_existing_content_and_remote():
    assert kdev_sync.decide_action(has_git=False, kdev_nonempty=True, remote="r") == "init"


def test_decide_remind_when_no_remote():
    assert kdev_sync.decide_action(has_git=False, kdev_nonempty=True, remote=None) == "remind"
    assert kdev_sync.decide_action(has_git=False, kdev_nonempty=False, remote=None) == "remind"
