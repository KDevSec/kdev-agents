import json
import pytest
from kdev_core import cli, flow_state

FLOW = "coding-flow"


def test_show_prints_current_node(tmp_workspace, capsys):
    flow_state.init_state(tmp_workspace, FLOW, "auth",
                          display_name="Auth", initial_node="n0-env")
    rc = cli.main(["show", FLOW, "auth", "--workspace", str(tmp_workspace)])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert out["current_node"] == "n0-env"
    assert out["status"] == "in_progress"


def test_init_creates_state(tmp_workspace, capsys):
    rc = cli.main(["init", FLOW, "ued6", "--display-name", "UED6 改造",
                   "--initial-node", "n0-env", "--auto-mode",
                   "--workspace", str(tmp_workspace)])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert out["current_node"] == "n0-env"
    st = flow_state.read_state(tmp_workspace, FLOW, "ued6")
    assert st["display_name"] == "UED6 改造"
    assert st["config"]["auto_mode"] is True


def test_resume_returns_current_node(tmp_workspace, capsys):
    flow_state.init_state(tmp_workspace, FLOW, "auth",
                          display_name="Auth", initial_node="n0-env")
    st = flow_state.read_state(tmp_workspace, FLOW, "auth")
    st["current_node"] = "n6b-impl-subagent"
    flow_state.write_state(tmp_workspace, FLOW, "auth", st)
    rc = cli.main(["resume", FLOW, "auth", "--workspace", str(tmp_workspace)])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert out["current_node"] == "n6b-impl-subagent"  # 不从头


def test_resume_on_completed_errors(tmp_workspace, capsys):
    flow_state.init_state(tmp_workspace, FLOW, "auth",
                          display_name="Auth", initial_node="n0-env")
    flow_state.mark_inactive(tmp_workspace, FLOW, "auth", status="completed")
    rc = cli.main(["resume", FLOW, "auth", "--workspace", str(tmp_workspace)])
    assert rc == 1
    assert "not resumable" in capsys.readouterr().err


def _write_table(tmp_workspace):
    table_path = tmp_workspace / "nt.yml"
    table_path.write_text(
        "flow: coding-flow\n"
        "max_retries: 3\n"
        "terminal_fail: n-fail\n"
        "nodes:\n"
        "  - {id: n0, kind: action, next: [n1]}\n"
        "  - {id: n1, kind: action, next: [n0, n-fail]}\n"
        "  - {id: n-fail, kind: terminal, next: []}\n",
        encoding="utf-8")
    return str(table_path)


def test_advance_moves_node(tmp_workspace, capsys):
    flow_state.init_state(tmp_workspace, FLOW, "a",
                          display_name="A", initial_node="n0")
    table = _write_table(tmp_workspace)
    rc = cli.main(["advance", FLOW, "a", "n1", "--table", table,
                   "--reason", "go", "--workspace", str(tmp_workspace)])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert out["current_node"] == "n1"


def test_advance_reflow_overflow_forces_terminal_fail(tmp_workspace, capsys):
    flow_state.init_state(tmp_workspace, FLOW, "a",
                          display_name="A", initial_node="n0")
    table = _write_table(tmp_workspace)
    cli.main(["advance", FLOW, "a", "n1", "--table", table,
              "--workspace", str(tmp_workspace)])
    # n1 -> n0 reflow x4 (> max_retries 3) 强制 terminal_fail
    # 前 3 次 reflow（counter 到 3，<= cap，不强制）+ 回 n-rev 模式回 n1，
    # 第 4 次 reflow（counter 到 4，> 3）才强制 terminal_fail。
    for _ in range(3):
        cli.main(["advance", FLOW, "a", "n0", "--table", table, "--reflow",
                  "--workspace", str(tmp_workspace)])
        cli.main(["advance", FLOW, "a", "n1", "--table", table,
                  "--workspace", str(tmp_workspace)])
    capsys.readouterr()
    cli.main(["advance", FLOW, "a", "n0", "--table", table, "--reflow",
              "--workspace", str(tmp_workspace)])
    out = json.loads(capsys.readouterr().out)
    assert out["current_node"] == "n-fail"


def _write_gate_table(tmp_workspace):
    table_path = tmp_workspace / "gt.yml"
    table_path.write_text(
        "flow: coding-flow\n"
        "max_retries: 3\n"
        "nodes:\n"
        "  - {id: n-impl, kind: action, next: [n-rev]}\n"
        "  - {id: n-rev, kind: gate, gate: g-rev, next: [n-acc, n-impl]}\n"
        "  - {id: n-acc, kind: gate, gate: g-acc, next: [n-done, n-impl]}\n"
        "  - {id: n-done, kind: terminal, next: []}\n"
        "gate_specs:\n"
        "  g-rev: {kind: review, on_pass: n-acc, on_reflow: n-impl, reviewer: self}\n"
        "  g-acc: {kind: acceptance, on_pass: n-done, on_reflow: n-impl, reviewer: self}\n",
        encoding="utf-8")
    return str(table_path)


def _init_at(tmp_workspace, node):
    flow_state.init_state(tmp_workspace, FLOW, "g",
                          display_name="G", initial_node=node)


def test_record_gate_review_pass_advances(tmp_workspace, capsys):
    _init_at(tmp_workspace, "n-rev")
    t = _write_gate_table(tmp_workspace)
    rc = cli.main(["record-gate", FLOW, "g", "--gate", "g-rev", "--kind", "review",
                   "--verdict", "PASS", "--request-id", "r1",
                   "--table", t, "--workspace", str(tmp_workspace)])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert out["current_node"] == "n-acc"
    assert out["history_len"] == 1


def test_record_gate_review_fail_reflows_then_escalates(tmp_workspace, capsys):
    _init_at(tmp_workspace, "n-rev")
    t = _write_gate_table(tmp_workspace)
    # FAIL #1,#2 -> reflow 回 n-impl（每次回前要先回到 n-rev）
    for i in (1, 2):
        cli.main(["record-gate", FLOW, "g", "--gate", "g-rev", "--kind", "review",
                  "--verdict", "FAIL", "--request-id", f"r{i}",
                  "--table", t, "--workspace", str(tmp_workspace)])
        cli.main(["advance", FLOW, "g", "n-rev", "--table", t,
                  "--workspace", str(tmp_workspace)])
    capsys.readouterr()
    # FAIL #3 >= max_retries(3) -> escalate blocked，不 advance、不 force-accept
    cli.main(["record-gate", FLOW, "g", "--gate", "g-rev", "--kind", "review",
              "--verdict", "FAIL", "--request-id", "r3",
              "--table", t, "--workspace", str(tmp_workspace)])
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "blocked"
    assert out["current_node"] == "n-rev"  # 没 force 过闸
