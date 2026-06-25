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


import json


def test_cross_employee_handoff_cli_roundtrip(run_cli):
    """P-B：生产方 req-architect 在 design-flow 落交付，消费方 dev-engineer
    在同 slug 上 coding-flow 读到——证明 B 轨原语零扩展覆盖跨员工跨 flow。"""
    slug = "user-auth"
    # 生产方写交付 manifest（artifacts + gate_input role→path 指针）
    gi = json.dumps({
        "sr": f".kdev/features/{slug}/handoffs/req-architect/sr.md",
        "ar": f".kdev/features/{slug}/handoffs/req-architect/ar.md",
        "design": f".kdev/features/{slug}/handoffs/req-architect/design.md",
    })
    out = run_cli([
        "handoff-write", "design-flow", slug,
        "--employee", "req-architect", "--node", "n8-merge",
        "--status", "done", "--summary", "SR/AR/方案 交付",
        "--artifact", f".kdev/features/{slug}/handoffs/req-architect/sr.md",
        "--artifact", f".kdev/features/{slug}/handoffs/req-architect/ar.md",
        "--gate-input", gi,
    ])
    assert "n8-merge.handoff.json" in out  # 落在生产方交接目录

    # 消费方（不同 flow / 同 slug / 指生产方 employee+node）读回
    read_out = run_cli([
        "handoff-read", "coding-flow", slug,
        "--employee", "req-architect", "--node", "n8-merge",
    ])
    data = json.loads(read_out)
    assert data["employee"] == "req-architect"
    assert data["status"] == "done"
    assert f".kdev/features/{slug}/handoffs/req-architect/sr.md" in data["artifacts"]
    assert json.loads(data["gate_input"] if isinstance(data["gate_input"], str)
                      else json.dumps(data["gate_input"]))["ar"].endswith("ar.md")


def test_cross_employee_missing_upstream_returns_nonzero(tmp_workspace):
    """消费方读不存在的上游交付 → cli.main 捕获 FlowStateError 返回 rc=1
    （已核 cli.py:368-371 catch+return 1，非抛异常）。编排据此回退裸任务，不静默成功。
    不走 run_cli（它断言 rc==0），直接调 cli.main。"""
    from kdev_core.cli import main as _cli_main
    rc = _cli_main([
        "handoff-read", "coding-flow", "no-such-feature",
        "--employee", "req-architect", "--node", "n8-merge",
        "--workspace", str(tmp_workspace),
    ])
    assert rc == 1
