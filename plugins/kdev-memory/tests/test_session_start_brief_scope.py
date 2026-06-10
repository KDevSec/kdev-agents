"""test session-start-brief.py scoped：shared 读 + 员工 scope 进度 block。"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

HOOKS = Path(__file__).parent.parent / "hooks"


def _load_brief():
    spec = importlib.util.spec_from_file_location("ssb", HOOKS / "session-start-brief.py")
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(HOOKS / "lib"))
    spec.loader.exec_module(mod)
    return mod


def test_staff_scope_block(tmp_path):
    mod = _load_brief()
    root = tmp_path / "memory"
    (root / "shared").mkdir(parents=True)
    de = root / "staff" / "dev-engineer"; de.mkdir(parents=True)
    (root / "staff" / "req-architect").mkdir(parents=True)
    (de / "执行日志.md").write_text(
        "---\n\n## Step dev-engineer-1: 建模块\n日期：2026-06-10\n", encoding="utf-8")
    block = mod._staff_scope_block(root)
    assert "dev-engineer" in block
    assert "1 条" in block
    assert "req-architect" in block  # 0 条也列出


def test_staff_scope_block_empty_flat(tmp_path):
    mod = _load_brief()
    root = tmp_path / "memory"; root.mkdir()
    assert mod._staff_scope_block(root) == ""
