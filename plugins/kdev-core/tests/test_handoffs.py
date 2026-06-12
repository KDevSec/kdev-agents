# tests/test_handoffs.py
"""Tests for handoffs/<员工>/ 目录约定 + 交接状态读写协议."""
import pytest
from kdev_core.flow_state import (
    FlowStateError,
    handoff_dir,
    read_handoff_status,
    write_handoff_status,
)


def test_handoff_dir_path_and_creates(tmp_workspace):
    p = handoff_dir(tmp_workspace, "user-auth", "req-architect")
    assert p == tmp_workspace / ".kdev" / "features" / "user-auth" / "handoffs" / "req-architect"
    assert p.is_dir()  # mkdir -p


def test_handoff_dir_idempotent(tmp_workspace):
    handoff_dir(tmp_workspace, "user-auth", "req-architect")
    p = handoff_dir(tmp_workspace, "user-auth", "req-architect")  # 第二次不报错
    assert p.is_dir()


def test_write_read_handoff_status_roundtrip(tmp_workspace):
    p = write_handoff_status(
        tmp_workspace, "user-auth", "dev-engineer", "n3-plan",
        "done", "PLAN.md 写完",
        artifacts=["delivery/PLAN.md"], gate_input={"build": "pass"})
    assert p.name == "n3-plan.handoff.json"
    assert p.parent.name == "dev-engineer"
    data = read_handoff_status(tmp_workspace, "user-auth", "dev-engineer", "n3-plan")
    assert data["node_id"] == "n3-plan"
    assert data["employee"] == "dev-engineer"
    assert data["status"] == "done"
    assert data["summary"] == "PLAN.md 写完"
    assert data["artifacts"] == ["delivery/PLAN.md"]
    assert data["gate_input"] == {"build": "pass"}
    assert data["reason"] is None


def test_write_handoff_status_rejects_bad_status(tmp_workspace):
    with pytest.raises(FlowStateError):
        write_handoff_status(tmp_workspace, "s", "e", "n", "finished", "x")


def test_write_handoff_status_requires_reason_when_not_done(tmp_workspace):
    with pytest.raises(FlowStateError):
        write_handoff_status(tmp_workspace, "s", "e", "n", "blocked", "stuck")
    write_handoff_status(tmp_workspace, "s", "e", "n", "blocked", "stuck",
                         reason="env missing")
    assert read_handoff_status(tmp_workspace, "s", "e", "n")["reason"] == "env missing"


def test_write_handoff_status_requires_summary(tmp_workspace):
    with pytest.raises(FlowStateError):
        write_handoff_status(tmp_workspace, "s", "e", "n", "done", "")


def test_read_handoff_status_missing_raises(tmp_workspace):
    with pytest.raises(FlowStateError):
        read_handoff_status(tmp_workspace, "nope", "e", "n")


def test_read_handoff_status_malformed_raises(tmp_workspace):
    d = handoff_dir(tmp_workspace, "s", "e")
    (d / "n.handoff.json").write_text("{not json", encoding="utf-8")
    with pytest.raises(FlowStateError):
        read_handoff_status(tmp_workspace, "s", "e", "n")
