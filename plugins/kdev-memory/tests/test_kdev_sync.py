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


import subprocess as _sp


def _git(args, cwd):
    return _sp.run(["git", *args], cwd=str(cwd), capture_output=True, text=True)


def _bare_remote(tmp_path):
    """Create a bare repo to act as the memory remote; return its path."""
    bare = tmp_path / "mem-remote.git"
    _git(["init", "--bare", str(bare)], cwd=tmp_path)
    return bare


def _write_yml(repo_root, remote):
    (repo_root / "kdev-sync.yml").write_text(f"memory_repo: {remote}\nbranch: main\n", encoding="utf-8")


def test_remind_when_no_yml(tmp_path):
    (tmp_path / ".kdev").mkdir()
    (tmp_path / ".kdev" / "x.md").write_text("local", encoding="utf-8")
    res = kdev_sync.bootstrap(tmp_path)
    assert res["action"] == "remind"
    assert "记忆仓" in res["message"]


def test_init_existing_then_pull_roundtrip(tmp_path):
    bare = _bare_remote(tmp_path)
    repo_a = tmp_path / "A"
    (repo_a / ".kdev").mkdir(parents=True)
    (repo_a / ".kdev" / "执行日志.md").write_text("step 1\n", encoding="utf-8")
    _write_yml(repo_a, str(bare))
    res = kdev_sync.bootstrap(repo_a)
    assert res["action"] == "init" and res["ok"], res
    assert (repo_a / ".kdev" / ".git").exists()

    repo_b = tmp_path / "B"
    repo_b.mkdir()
    _write_yml(repo_b, str(bare))
    res_b = kdev_sync.bootstrap(repo_b)
    assert res_b["action"] == "clone" and res_b["ok"], res_b
    assert (repo_b / ".kdev" / "执行日志.md").read_text(encoding="utf-8") == "step 1\n"


def test_sync_push_then_pull_propagates(tmp_path):
    bare = _bare_remote(tmp_path)
    repo_a = tmp_path / "A"
    (repo_a / ".kdev").mkdir(parents=True)
    (repo_a / ".kdev" / "执行日志.md").write_text("step 1\n", encoding="utf-8")
    _write_yml(repo_a, str(bare))
    kdev_sync.bootstrap(repo_a)

    repo_b = tmp_path / "B"
    repo_b.mkdir()
    _write_yml(repo_b, str(bare))
    kdev_sync.bootstrap(repo_b)

    (repo_a / ".kdev" / "执行日志.md").write_text("step 1\nstep 2\n", encoding="utf-8")
    push = kdev_sync.sync_push(repo_a, message="sync step 2")
    assert push["ok"] and push["pushed"], push
    pull = kdev_sync.bootstrap(repo_b)
    assert pull["action"] == "pull" and pull["ok"], pull
    assert "step 2" in (repo_b / ".kdev" / "执行日志.md").read_text(encoding="utf-8")


def test_sync_push_noop_when_no_changes(tmp_path):
    bare = _bare_remote(tmp_path)
    repo_a = tmp_path / "A"
    (repo_a / ".kdev").mkdir(parents=True)
    (repo_a / ".kdev" / "执行日志.md").write_text("step 1\n", encoding="utf-8")
    _write_yml(repo_a, str(bare))
    kdev_sync.bootstrap(repo_a)
    res = kdev_sync.sync_push(repo_a)
    assert res["ok"] and res["pushed"] is False


def test_sync_push_skips_when_untracked(tmp_path):
    (tmp_path / ".kdev").mkdir()
    res = kdev_sync.sync_push(tmp_path)
    assert res["ok"] and res["pushed"] is False


def test_init_writes_gitignore_and_excludes_machine_local(tmp_path):
    bare = _bare_remote(tmp_path)
    repo = tmp_path / "A"
    (repo / ".kdev" / "memory" / "state").mkdir(parents=True)
    (repo / ".kdev" / "memory" / "state" / "counter.txt").write_text("7", encoding="utf-8")
    (repo / ".kdev" / "memory" / "执行日志.md").write_text("step 1\n", encoding="utf-8")
    _write_yml(repo, str(bare))
    assert kdev_sync.bootstrap(repo)["ok"]
    assert (repo / ".kdev" / ".gitignore").exists()
    tracked = _git(["ls-files"], cwd=repo / ".kdev").stdout
    assert "执行日志.md" in tracked
    assert "counter.txt" not in tracked   # machine-local state/ excluded from the hosted repo
