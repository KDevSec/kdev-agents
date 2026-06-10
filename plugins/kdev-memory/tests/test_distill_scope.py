"""test distill scope：collect_entries 收 shared + staff Step；trigger 走 shared。"""
from __future__ import annotations

import sys
from pathlib import Path

LIB_DIR = Path(__file__).parent.parent / "hooks" / "lib"
sys.path.insert(0, str(LIB_DIR))

import distill  # noqa: E402

_STEP = "---\n\n## {sid}: {t}\ntriggers: [a,b,c,d,e]\n日期：2026-06-10\nabout: project\n\n### 执行事实\n- 工具调用次数：1\n"


def test_collect_includes_staff_steps(tmp_path):
    root = tmp_path / "memory"
    (root / "shared").mkdir(parents=True)
    de = root / "staff" / "dev-engineer"; de.mkdir(parents=True)
    (root / "shared" / "执行日志.md").write_text(_STEP.format(sid="Step main-9", t="CEO"), encoding="utf-8")
    (de / "执行日志.md").write_text(_STEP.format(sid="Step dev-engineer-1", t="员工"), encoding="utf-8")
    entries = distill.collect_entries(root)
    ids = {e.entry_id for e in entries}
    assert "Step main-9" in ids
    assert "Step dev-engineer-1" in ids


def test_collect_flat_unchanged(tmp_path):
    root = tmp_path / "memory"; root.mkdir()
    (root / "执行日志.md").write_text(_STEP.format(sid="Step main-9", t="活"), encoding="utf-8")
    ids = {e.entry_id for e in distill.collect_entries(root)}
    assert ids == {"Step main-9"}
