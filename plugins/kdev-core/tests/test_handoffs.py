# tests/test_handoffs.py
"""Tests for handoffs/<员工>/ 目录约定 (最小: 路径生成; 协议留 P-B)."""
from kdev_core.flow_state import handoff_dir


def test_handoff_dir_path_and_creates(tmp_workspace):
    p = handoff_dir(tmp_workspace, "user-auth", "req-architect")
    assert p == tmp_workspace / ".kdev" / "features" / "user-auth" / "handoffs" / "req-architect"
    assert p.is_dir()  # mkdir -p


def test_handoff_dir_idempotent(tmp_workspace):
    handoff_dir(tmp_workspace, "user-auth", "req-architect")
    p = handoff_dir(tmp_workspace, "user-auth", "req-architect")  # 第二次不报错
    assert p.is_dir()
