"""tests/test_setup.py — 纯函数层 setup.py 的单元测试。

TDD RED→GREEN：先写测试，实现后应全绿。
所有路径均 tmp 下，不碰真实 ~/.claude/ 或 .claude/。
"""
import json
import os
from pathlib import Path

import pytest

from kdev_hud import setup


# ─── resolve_plugin_root ──────────────────────────────────────────────────────

def test_resolve_plugin_root_env(monkeypatch):
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", "/x/y")
    assert setup.resolve_plugin_root() == Path("/x/y")


def test_resolve_plugin_root_fallback(monkeypatch):
    monkeypatch.delenv("CLAUDE_PLUGIN_ROOT", raising=False)
    root = setup.resolve_plugin_root()
    # 要么 root 目录名是 kdev-hud，要么其下存在 kdev_hud/ 子目录
    assert root.name == "kdev-hud" or (root / "kdev_hud").is_dir()


# ─── build_statusline_command ─────────────────────────────────────────────────

def test_build_statusline_command():
    root = Path("/some/plugin/root")
    cmd = setup.build_statusline_command(root)
    assert "kdev_hud/__main__.py" in cmd
    assert "statusline" in cmd
    assert "${workspaceFolder}" in cmd
    # 脚本路径被双引号包裹
    assert f'"{root}/kdev_hud/__main__.py"' in cmd


# ─── is_kdev_statusline ───────────────────────────────────────────────────────

def test_is_kdev_statusline():
    # 本插件 dict（command 含 kdev_hud）→ True
    assert setup.is_kdev_statusline({"command": "python3 /a/kdev_hud/__main__.py statusline"})
    # 他者 dict → False
    assert not setup.is_kdev_statusline({"command": "echo hello"})
    # 本插件 str → True
    assert setup.is_kdev_statusline("python3 /a/kdev_hud/__main__.py statusline")
    # 他者 str → False
    assert not setup.is_kdev_statusline("echo hello")
    # None → False
    assert not setup.is_kdev_statusline(None)
    # falsy 空字符串 → False
    assert not setup.is_kdev_statusline("")
    # dict 无 command 键 → False
    assert not setup.is_kdev_statusline({"type": "command"})
    # dict command 非 str → False
    assert not setup.is_kdev_statusline({"command": 42})


# ─── resolve_settings_path ────────────────────────────────────────────────────

def test_resolve_settings_path_project(tmp_path):
    ws = str(tmp_path / "my_ws")
    path = setup.resolve_settings_path("project", ws)
    assert path == Path(ws) / ".claude" / "settings.json"


def test_resolve_settings_path_user():
    path = setup.resolve_settings_path("user")
    assert path == Path.home() / ".claude" / "settings.json"


# ─── install_statusline ───────────────────────────────────────────────────────

KDEV_CMD = "python3 /x/kdev_hud/__main__.py statusline --workspace ${workspaceFolder}"
FOREIGN_CMD = "echo hello_foreign"


def test_install_creates_new_file(tmp_path):
    sp = tmp_path / ".claude" / "settings.json"
    result = setup.install_statusline(sp, KDEV_CMD)
    assert result["action"] == "created"
    assert result["path"] == str(sp)
    assert result["backup"] is None
    assert sp.exists()
    data = json.loads(sp.read_text(encoding="utf-8"))
    assert "kdev_hud" in data["statusLine"]["command"]


def test_install_merges_without_clobber(tmp_path):
    """预置有其他键的文件（无 statusLine）→ created 且原有键不丢。"""
    sp = tmp_path / ".claude" / "settings.json"
    sp.parent.mkdir(parents=True, exist_ok=True)
    sp.write_text(json.dumps({"theme": "dark", "env": {"A": "1"}}, indent=2), encoding="utf-8")

    result = setup.install_statusline(sp, KDEV_CMD)
    assert result["action"] == "created"
    data = json.loads(sp.read_text(encoding="utf-8"))
    assert data["theme"] == "dark"
    assert data["env"] == {"A": "1"}
    assert "statusLine" in data


def test_install_bad_json_raises_and_no_write(tmp_path):
    sp = tmp_path / ".claude" / "settings.json"
    sp.parent.mkdir(parents=True, exist_ok=True)
    bad_content = "{ not json }"
    sp.write_text(bad_content, encoding="utf-8")

    with pytest.raises(setup.SetupError):
        setup.install_statusline(sp, KDEV_CMD)
    # 文件字节不变
    assert sp.read_text(encoding="utf-8") == bad_content


def test_install_skips_foreign_without_force(tmp_path):
    sp = tmp_path / ".claude" / "settings.json"
    sp.parent.mkdir(parents=True, exist_ok=True)
    original = json.dumps({"statusLine": {"command": FOREIGN_CMD}}, indent=2)
    sp.write_text(original, encoding="utf-8")

    result = setup.install_statusline(sp, KDEV_CMD)
    assert result["action"] == "skipped_foreign"
    # 文件未改动
    assert sp.read_text(encoding="utf-8") == original
    # 无备份文件
    bak = sp.parent / (sp.name + ".bak")
    assert not bak.exists()


def test_install_force_backs_up_and_overwrites_foreign(tmp_path):
    sp = tmp_path / ".claude" / "settings.json"
    sp.parent.mkdir(parents=True, exist_ok=True)
    original = json.dumps({"statusLine": {"command": FOREIGN_CMD}}, indent=2)
    sp.write_text(original, encoding="utf-8")

    result = setup.install_statusline(sp, KDEV_CMD, force=True)
    assert result["action"] == "forced"
    bak = sp.parent / (sp.name + ".bak")
    assert bak.exists()
    assert bak.read_text(encoding="utf-8") == original
    data = json.loads(sp.read_text(encoding="utf-8"))
    assert "kdev_hud" in data["statusLine"]["command"]


def test_install_updates_own_idempotent(tmp_path):
    sp = tmp_path / ".claude" / "settings.json"
    sp.parent.mkdir(parents=True, exist_ok=True)
    sp.write_text(json.dumps({
        "theme": "x",
        "statusLine": {"command": "python3 /old/kdev_hud/__main__.py statusline"}
    }, indent=2), encoding="utf-8")

    result = setup.install_statusline(sp, KDEV_CMD)
    assert result["action"] == "updated"
    data = json.loads(sp.read_text(encoding="utf-8"))
    assert data["theme"] == "x"
    assert result["backup"] is None

    # 再调一次仍 updated，文件里只有一个 statusLine
    result2 = setup.install_statusline(sp, KDEV_CMD)
    assert result2["action"] == "updated"
    data2 = json.loads(sp.read_text(encoding="utf-8"))
    text = sp.read_text(encoding="utf-8")
    assert text.count('"statusLine"') == 1
