"""tests/test_setup_cli.py — CLI 层 setup 子命令测试。

复用 _run 模式（cli.main([...]) 捕获 stdout）。
所有路径均 tmp 下，不碰真实 ~/.claude/ 或 .claude/。
"""
import io
import json
from contextlib import redirect_stdout
from pathlib import Path

from kdev_hud import cli


def _run(argv):
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = cli.main(argv)
    return rc, buf.getvalue()


def test_cli_setup_project_writes_settings(tmp_path):
    ws = tmp_path / "my_project"
    ws.mkdir()
    rc, out = _run(["setup", "--project", "--workspace", str(ws)])
    assert rc == 0
    sp = ws / ".claude" / "settings.json"
    assert sp.exists()
    data = json.loads(sp.read_text(encoding="utf-8"))
    assert "kdev_hud" in data["statusLine"]["command"]
    assert "statusline" in data["statusLine"]["command"]


def test_cli_setup_idempotent(tmp_path):
    ws = tmp_path / "my_project"
    ws.mkdir()
    rc1, _ = _run(["setup", "--project", "--workspace", str(ws)])
    rc2, _ = _run(["setup", "--project", "--workspace", str(ws)])
    assert rc1 == 0
    assert rc2 == 0
    # 最终只一个 statusLine
    sp = ws / ".claude" / "settings.json"
    text = sp.read_text(encoding="utf-8")
    assert text.count('"statusLine"') == 1


def test_cli_setup_foreign_skipped_then_force(tmp_path):
    ws = tmp_path / "my_project"
    ws.mkdir()
    sp = ws / ".claude" / "settings.json"
    sp.parent.mkdir(parents=True, exist_ok=True)
    foreign_content = json.dumps({"statusLine": {"command": "echo hello_foreign"}}, indent=2)
    sp.write_text(foreign_content, encoding="utf-8")

    # 不带 --force：rc 0 且 statusLine 仍是他者，无 .bak
    rc1, out1 = _run(["setup", "--project", "--workspace", str(ws)])
    assert rc1 == 0
    data_after_skip = json.loads(sp.read_text(encoding="utf-8"))
    assert "kdev_hud" not in data_after_skip["statusLine"].get("command", "")
    bak = sp.parent / (sp.name + ".bak")
    assert not bak.exists()

    # 带 --force：rc 0、.bak 出现、statusLine 变本插件
    rc2, out2 = _run(["setup", "--project", "--workspace", str(ws), "--force"])
    assert rc2 == 0
    assert bak.exists()
    data_after_force = json.loads(sp.read_text(encoding="utf-8"))
    assert "kdev_hud" in data_after_force["statusLine"]["command"]
