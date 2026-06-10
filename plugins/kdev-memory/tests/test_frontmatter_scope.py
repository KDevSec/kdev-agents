"""test frontmatter.py scope 解析：scoped 时从 shared/ 读 当前状态.md。"""
from __future__ import annotations

import sys
from pathlib import Path

LIB_DIR = Path(__file__).parent.parent / "hooks" / "lib"
sys.path.insert(0, str(LIB_DIR))

import frontmatter  # noqa: E402

_FM = """---
phase: stage2
current_step: dev-engineer-3
---
body
"""


def test_flat_reads_root(tmp_path, monkeypatch):
    (tmp_path / ".kdev" / "memory").mkdir(parents=True)
    (tmp_path / ".kdev" / "memory" / "当前状态.md").write_text(_FM, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert frontmatter.read_state_field("current_step") == "dev-engineer-3"


def test_scoped_reads_shared(tmp_path, monkeypatch):
    shared = tmp_path / ".kdev" / "memory" / "shared"
    shared.mkdir(parents=True)
    (tmp_path / ".kdev" / "memory" / "staff" / "dev-engineer").mkdir(parents=True)
    (shared / "当前状态.md").write_text(_FM, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert frontmatter.read_state_field("phase") == "stage2"
    assert frontmatter.has_state_frontmatter() is True
