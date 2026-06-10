"""test recorder scope helpers：目标日志路径 + slug 解析（recorder prompt 据此落盘）。"""
from __future__ import annotations

import sys
from pathlib import Path

LIB_DIR = Path(__file__).parent.parent / "hooks" / "lib"
sys.path.insert(0, str(LIB_DIR))

from scope import recorder_target_log, resolve_step_slug  # noqa: E402


def test_shared_scope_target_is_shared_log(tmp_path):
    root = tmp_path / "memory"
    (root / "shared").mkdir(parents=True)
    assert recorder_target_log("shared", root) == root / "shared" / "执行日志.md"
    assert recorder_target_log(None, root) == root / "shared" / "执行日志.md"


def test_staff_scope_target_is_staff_log(tmp_path):
    root = tmp_path / "memory"
    (root / "shared").mkdir(parents=True)
    (root / "staff" / "dev-engineer").mkdir(parents=True)
    assert recorder_target_log("dev-engineer", root) == root / "staff" / "dev-engineer" / "执行日志.md"


def test_flat_target_is_root_log(tmp_path):
    """flat（无 shared/）：任何 scope 都落 root 执行日志（向后兼容）。"""
    root = tmp_path / "memory"; root.mkdir()
    assert recorder_target_log(None, root) == root / "执行日志.md"
    assert recorder_target_log("shared", root) == root / "执行日志.md"
    # 员工 canonical id 在 flat 布局下也兜底回 root 执行日志（向后兼容，scope.py 末分支）
    assert recorder_target_log("dev-engineer", root) == root / "执行日志.md"
