"""test weekly.py scoped：聚合 shared + staff Step，过程资产含 per-scope 盘点。"""
from __future__ import annotations

import io
import sys
from contextlib import redirect_stdout
from datetime import date
from pathlib import Path

LIB_DIR = Path(__file__).parent.parent / "hooks" / "lib"
sys.path.insert(0, str(LIB_DIR))

import weekly  # noqa: E402

_STEP = "---\n\n## {sid}: {t}\n日期：{d}\n\n### 执行事实\n- 工具调用次数：1\n"


def _render(root):
    buf = io.StringIO()
    d = date(2026, 6, 10)
    with redirect_stdout(buf):
        weekly.render(root, d, d)
    return buf.getvalue()


def test_scoped_aggregates_staff_steps(tmp_path):
    root = tmp_path / "memory"
    (root / "shared").mkdir(parents=True)
    de = root / "staff" / "dev-engineer"; de.mkdir(parents=True)
    (root / "shared" / "执行日志.md").write_text(_STEP.format(sid="Step main-9", t="CEO", d="2026-06-10"), encoding="utf-8")
    (de / "执行日志.md").write_text(_STEP.format(sid="Step dev-engineer-1", t="员工", d="2026-06-10"), encoding="utf-8")
    out = _render(root)
    assert "**Step**：2 条" in out
    assert "dev-engineer" in out


def test_flat_unchanged(tmp_path):
    root = tmp_path / "memory"; root.mkdir()
    (root / "执行日志.md").write_text(_STEP.format(sid="Step main-9", t="活", d="2026-06-10"), encoding="utf-8")
    out = _render(root)
    assert "**Step**：1 条" in out
