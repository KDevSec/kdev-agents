"""test trigger-match.py scoped 召回：shared + staff Step 都能召回，staff 打 scope 标签。"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

LIB_DIR = Path(__file__).parent.parent / "hooks" / "lib"


def _load_tm():
    spec = importlib.util.spec_from_file_location("trigger_match", LIB_DIR / "trigger-match.py")
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(LIB_DIR))
    spec.loader.exec_module(mod)
    return mod


_STEP_BLOCK = """---

## {sid}: {title}
triggers: [{trig}]
日期：{date}
about: {about}

### 执行事实
- 工具调用次数：1
"""


def test_scoped_step_recall_shared_and_staff(tmp_path, monkeypatch):
    root = tmp_path / ".kdev" / "memory"
    (root / "shared").mkdir(parents=True)
    (root / "staff" / "dev-engineer").mkdir(parents=True)
    today = "2026-06-10"
    (root / "shared" / "执行日志.md").write_text(
        _STEP_BLOCK.format(sid="Step main-9", title="CEO 主线", trig="ceo-mainline-kw", date=today, about="project"),
        encoding="utf-8")
    (root / "staff" / "dev-engineer" / "执行日志.md").write_text(
        _STEP_BLOCK.format(sid="Step dev-engineer-2", title="员工活", trig="dev-scope-kw", date=today, about="feature/x"),
        encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("KDEV_TRIGGER_TODAY", today)

    tm = _load_tm()
    entries = tm.scan_step_entries()
    ids = {e["id"] for e in entries}
    assert "Step main-9" in ids
    assert "Step dev-engineer-2" in ids
    staff_entry = next(e for e in entries if e["id"] == "Step dev-engineer-2")
    assert staff_entry.get("scope") == "dev-engineer"


def test_flat_step_recall_unchanged(tmp_path, monkeypatch):
    """flat 模式：执行日志在 root，无 staff，行为与现状一致。"""
    root = tmp_path / ".kdev" / "memory"
    root.mkdir(parents=True)
    today = "2026-06-10"
    (root / "执行日志.md").write_text(
        _STEP_BLOCK.format(sid="Step main-9", title="活", trig="flat-kw", date=today, about="project"),
        encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("KDEV_TRIGGER_TODAY", today)
    tm = _load_tm()
    ids = {e["id"] for e in tm.scan_step_entries()}
    assert ids == {"Step main-9"}


def test_scoped_tiegui_recall_from_shared(tmp_path, monkeypatch):
    root = tmp_path / ".kdev" / "memory"
    (root / "shared").mkdir(parents=True)
    (root / "staff" / "dev-engineer").mkdir(parents=True)
    (root / "shared" / "方法论铁规.md").write_text(
        "## 实时落盘\ntriggers: [tiegui-scoped-kw, 落盘]\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    tm = _load_tm()
    entries = tm.scan_tiegui_entries()
    assert any("tiegui-scoped-kw" in e["triggers"] for e in entries), \
        "铁规 recall must read from shared/ in scoped layout"
