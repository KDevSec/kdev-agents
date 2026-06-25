"""Tests for hooks/lib/kdev_sync.py — Q-009 git 托管自举."""
import importlib.util
import os
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


def test_decide_pull_when_has_git_and_remote():
    # .kdev/.git present AND a remote configured -> pull (fetch latest).
    assert kdev_sync.decide_action(has_git=True, kdev_nonempty=True, remote="r") == "pull"


def test_decide_remind_when_has_git_but_no_remote():
    # 本地仓已建但无远程 → 持续提醒去建远程仓（不再 pull）。
    assert kdev_sync.decide_action(has_git=True, kdev_nonempty=True, remote=None) == "remind"
    assert kdev_sync.decide_action(has_git=True, kdev_nonempty=False, remote=None) == "remind"


def test_decide_clone_when_empty_and_remote():
    assert kdev_sync.decide_action(has_git=False, kdev_nonempty=False, remote="r") == "clone"


def test_decide_init_when_existing_content_and_remote():
    assert kdev_sync.decide_action(has_git=False, kdev_nonempty=True, remote="r") == "init"


def test_decide_init_local_when_nonempty_no_remote():
    # 无仓、.kdev/ 已有本地内容、无 remote → 本地建独立仓（init-local）。
    assert kdev_sync.decide_action(has_git=False, kdev_nonempty=True, remote=None) == "init-local"


def test_decide_remind_when_empty_no_remote():
    assert kdev_sync.decide_action(has_git=False, kdev_nonempty=False, remote=None) == "remind"


import subprocess as _sp


def _git(args, cwd):
    return _sp.run(["git", *args], cwd=str(cwd), capture_output=True, text=True,
                    encoding="utf-8", errors="replace")


def _bare_remote(tmp_path):
    """Create a bare repo to act as the memory remote; return its path."""
    bare = tmp_path / "mem-remote.git"
    _git(["init", "--bare", str(bare)], cwd=tmp_path)
    return bare


def _write_yml(repo_root, remote):
    (repo_root / "kdev-sync.yml").write_text(f"memory_repo: {remote}\nbranch: main\n", encoding="utf-8")


def test_remind_when_empty_no_yml(tmp_path):
    # 空 .kdev/ + 无 kdev-sync.yml（无 remote）→ 原"尚未 git 托管"初始化提醒。
    (tmp_path / ".kdev").mkdir()
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


# ── 件 1：init-local — 无 remote 但 .kdev/ 非空 → 本地建独立 nested 仓 ──

def test_init_local_when_no_yml_nonempty(tmp_path):
    # 非空 .kdev/ + 无 kdev-sync.yml（无 remote）→ 本地建独立仓 + 提醒建远程。
    (tmp_path / ".kdev").mkdir()
    (tmp_path / ".kdev" / "x.md").write_text("local", encoding="utf-8")
    res = kdev_sync.bootstrap(tmp_path)
    assert res["action"] == "init-local" and res["ok"], res
    assert (tmp_path / ".kdev" / ".git").exists()          # 本地建仓
    assert (tmp_path / ".kdev" / ".gitignore").exists()    # 机器本地 .gitignore
    assert "远程" in res["message"]                          # 提醒建远程仓


def test_init_local_then_remind_no_remote(tmp_path):
    # 续跑：已 init-local（has_git=True）+ 仍无 remote → remind（持续提醒建远程）。
    (tmp_path / ".kdev").mkdir()
    (tmp_path / ".kdev" / "x.md").write_text("local", encoding="utf-8")
    kdev_sync.bootstrap(tmp_path)
    res2 = kdev_sync.bootstrap(tmp_path)
    assert res2["action"] == "remind", res2


def test_remind_after_local_init_points_to_remote(tmp_path):
    # 本地仓已建（has_git）但无 remote → remind 文案应指向"建远程仓"，非"尚未 git 托管"。
    (tmp_path / ".kdev").mkdir()
    (tmp_path / ".kdev" / "x.md").write_text("local", encoding="utf-8")
    kdev_sync.bootstrap(tmp_path)            # run1 → init-local 建 .kdev/.git
    res = kdev_sync.bootstrap(tmp_path)       # run2 → remind
    assert res["action"] == "remind"
    assert res["message"] == kdev_sync.remote_reminder_text()
    assert "远程" in res["message"]


def test_remind_when_empty_uses_preinit_text(tmp_path):
    # 无仓且无 remote（空 .kdev/）→ 仍用原"尚未 git 托管"初始化提醒。
    (tmp_path / ".kdev").mkdir()
    res = kdev_sync.bootstrap(tmp_path)
    assert res["action"] == "remind"
    assert res["message"] == kdev_sync.reminder_text()


# ── 件 2：sync: off — 项目级永久静默 ──

def test_read_config_parses_sync_off(tmp_path):
    (tmp_path / "kdev-sync.yml").write_text("sync: off\n", encoding="utf-8")
    assert kdev_sync.read_sync_config(tmp_path)["sync"] == "off"
    assert kdev_sync.is_sync_off(tmp_path) is True


def test_sync_on_by_default(tmp_path):
    assert kdev_sync.read_sync_config(tmp_path)["sync"] == "on"
    assert kdev_sync.is_sync_off(tmp_path) is False


def test_bootstrap_optout_when_sync_off(tmp_path):
    """sync: off → bootstrap 静默退出：不建仓、不联网、不提示。"""
    (tmp_path / "kdev-sync.yml").write_text(
        "memory_repo: file:///some/remote\nsync: off\n", encoding="utf-8")
    (tmp_path / ".kdev").mkdir()
    res = kdev_sync.bootstrap(tmp_path)
    assert res["action"] == "optout" and res["ok"] is True and res["message"] == ""
    assert not (tmp_path / ".kdev" / ".git").exists()  # 没建仓


def test_sync_push_skips_when_sync_off(tmp_path):
    (tmp_path / "kdev-sync.yml").write_text("sync: off\n", encoding="utf-8")
    res = kdev_sync.sync_push(tmp_path)
    assert res["ok"] is True and res["pushed"] is False and "sync off" in res["message"]


def test_reminders_mention_optout_via_project_repo():
    """每条提醒都带退出说明：sync: off 写进 kdev-sync.yml 并提交到项目仓。"""
    for t in (kdev_sync.reminder_text(),
              kdev_sync.remote_reminder_text(),
              kdev_sync.sync_failed_reminder_text("pull")):
        assert "sync: off" in t and "kdev-sync.yml" in t and "提交到本项目仓" in t


# ── 件 3：失败会话内提示 — pull/clone 失败 → <kdev-sync-reminder> 中文引导 ──

def test_sync_failed_reminder_text_is_in_session_guidance():
    """同步失败提示：中文、提凭据、给登录指引、带详情——这是替代 GUI 弹窗的会话内文案。"""
    t = kdev_sync.sync_failed_reminder_text("pull", "fatal: Authentication failed")
    assert "凭据" in t
    assert "gh auth login" in t or "git pull" in t
    assert "不影响" in t and "不再弹窗" in t
    assert "Authentication failed" in t  # 透传详情


def test_clone_failure_returns_not_ok_no_hang(tmp_path):
    """坏远程（file:// 不存在）→ clone 失败应快速返回 ok=False（hook 据此在会话内提示，不弹 GUI、不挂起）。"""
    (tmp_path / "kdev-sync.yml").write_text(
        "memory_repo: file:///nonexistent/kdev-memory-repo\n", encoding="utf-8")
    (tmp_path / ".kdev").mkdir()  # 空 .kdev + 有 remote → decide_action=clone
    res = kdev_sync.bootstrap(tmp_path)
    assert res["action"] == "clone"
    assert res["ok"] is False


def test_bootstrap_hook_emits_sync_reminder_on_clone_failure(tmp_path):
    """bootstrap hook 脚本：clone 失败 → stdout 输出 <kdev-sync-reminder>…</kdev-sync-reminder>（会话内可见）。"""
    import subprocess as _subp
    import sys
    hook = Path(__file__).parent.parent / "hooks" / "kdev-sync-bootstrap.py"
    (tmp_path / "kdev-sync.yml").write_text(
        "memory_repo: file:///nonexistent/kdev-memory-repo\n", encoding="utf-8")
    (tmp_path / ".kdev").mkdir()  # 空 .kdev + 有 remote → clone → 失败
    env = dict(os.environ)
    env["CLAUDE_PROJECT_DIR"] = str(tmp_path)
    r = _subp.run([sys.executable, str(hook)], capture_output=True, text=True,
                  encoding="utf-8", errors="replace", env=env)
    assert "<kdev-sync-reminder>" in r.stdout and "</kdev-sync-reminder>" in r.stdout
    assert "凭据" in r.stdout
