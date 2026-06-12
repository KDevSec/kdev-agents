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


def test_cli_statusline(tmp_workspace, seed):
    seed(tmp_workspace, display_name="用户管理模块",
         stories=[{"id": "s1", "title": "a", "status": "done"},
                  {"id": "s2", "title": "b", "status": "pending"}])
    rc, out = _run(["statusline", "--workspace", str(tmp_workspace)])
    assert rc == 0
    assert "KDev 团队" in out and "用户管理模块" in out
    assert out.count("\n") <= 1  # 单行


def test_cli_render_writes_hud_html(tmp_workspace, seed):
    seed(tmp_workspace, display_name="用户管理模块")
    rc, out = _run(["render", "--workspace", str(tmp_workspace)])
    assert rc == 0
    out_path = tmp_workspace / ".kdev" / "hud.html"
    assert out_path.exists()
    html = out_path.read_text(encoding="utf-8")
    assert "<html" in html and "用户管理模块" in html
    assert str(out_path) in out  # 打印产物路径


def test_cli_render_never_writes_features(tmp_workspace, seed):
    slug = seed(tmp_workspace)
    fs = tmp_workspace / ".kdev" / "features" / slug / "flow-state.json"
    before = fs.read_text(encoding="utf-8")
    _run(["render", "--workspace", str(tmp_workspace)])
    assert fs.read_text(encoding="utf-8") == before  # features/ 零写入


def test_cli_statusline_consumes_stdin(tmp_workspace, monkeypatch, seed):
    seed(tmp_workspace, display_name="用户管理模块")
    monkeypatch.setattr("sys.stdin", io.StringIO('{"cwd":"%s"}' % str(tmp_workspace)))
    # 不传 --workspace，从 stdin JSON 的 cwd 取
    rc, out = _run(["statusline"])
    assert rc == 0 and "用户管理模块" in out


def _write_malformed(ws, slug="bad"):
    d = ws / ".kdev" / "features" / slug
    d.mkdir(parents=True, exist_ok=True)
    # stories 是字符串而非 list → 派生层会 AttributeError
    (d / "flow-state.json").write_text(
        json.dumps({"slug": slug, "display_name": "坏数据", "status": "in_progress",
                    "stories": "oops", "active": None}),
        encoding="utf-8")


def test_cli_statusline_degrades_on_malformed(tmp_workspace):
    _write_malformed(tmp_workspace)
    rc, out = _run(["statusline", "--workspace", str(tmp_workspace)])
    assert rc == 0
    assert "KDev 团队" in out
    assert out.count("\n") <= 1  # 仍单行、无 traceback


def test_cli_render_degrades_on_malformed(tmp_workspace):
    _write_malformed(tmp_workspace)
    rc, out = _run(["render", "--workspace", str(tmp_workspace)])
    assert rc == 0
    out_path = tmp_workspace / ".kdev" / "hud.html"
    assert out_path.exists() and "<html" in out_path.read_text(encoding="utf-8")
