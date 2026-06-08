"""Tests for new CLI subcommands: next-step, gate-lookup, unblock, list-flows,
and enriched _print_state output."""
import json
import pytest
from kdev_core import cli, flow_state, node_machine, gate

FLOW = "coding-flow"


# ── fixtures ──────────────────────────────────────────────────────────────

def _write_gate_table(tmp_workspace):
    """Write a node-table with action + gate + decision nodes."""
    table_path = tmp_workspace / "nt.yml"
    table_path.write_text(
        "flow: coding-flow\n"
        "max_retries: 3\n"
        "terminal_fail: n-fail\n"
        "nodes:\n"
        "  - {id: n0-env, name: 环境准备, kind: action, next: [n1-relevance]}\n"
        "  - {id: n1-relevance, name: 关联度自检, kind: gate, gate: g-relevance, next: [n3-plan, n2-worktree]}\n"
        "  - {id: n2-worktree, name: 新建worktree, kind: action, next: [n3-plan]}\n"
        "  - {id: n3-plan, name: 写计划, kind: action, next: [n4-review]}\n"
        "  - {id: n4-review, name: 方案评审, kind: gate, gate: g-plan-review, next: [n5-complexity, n3-plan]}\n"
        "  - {id: n5-complexity, name: 复杂度判断, kind: gate, gate: g-complexity, next: [n6a, n6b]}\n"
        "  - {id: n6a, name: 主控实现, kind: action, next: [n8-verify]}\n"
        "  - {id: n6b, name: subagent实现, kind: action, next: [n8-verify]}\n"
        "  - {id: n8-verify, name: 完成验证, kind: gate, gate: g-verify, next: [n9a, n6b]}\n"
        "  - {id: n9a, name: 代码评审, kind: gate, gate: g-code-review, next: [n-done, n6b]}\n"
        "  - {id: n-done, name: 完成, kind: terminal, next: []}\n"
        "  - {id: n-fail, name: 失败终止, kind: terminal, next: []}\n"
        "gate_specs:\n"
        "  g-relevance: {kind: decision, branches: {high: n3-plan, low: n2-worktree}, reviewer: self}\n"
        "  g-plan-review: {kind: review, on_pass: n5-complexity, on_reflow: n3-plan, reviewer: reviewer-expert, stage1: deferred}\n"
        "  g-complexity: {kind: decision, branches: {simple: n6a, complex: n6b}, reviewer: self}\n"
        "  g-verify: {kind: review, on_pass: n9a, on_reflow: n6b, reviewer: self}\n"
        "  g-code-review: {kind: review, on_pass: n-done, on_reflow: n6b, reviewer: reviewer-expert, stage1: deferred}\n",
        encoding="utf-8")
    return str(table_path)


def _init_at(tmp_workspace, node):
    flow_state.init_state(tmp_workspace, FLOW, "t",
                          display_name="Test", initial_node=node)


# ── next-step ─────────────────────────────────────────────────────────────

def test_next_step_at_action_node(tmp_workspace, capsys):
    _init_at(tmp_workspace, "n0-env")
    table = _write_gate_table(tmp_workspace)
    rc = cli.main(["next-step", FLOW, "t", "--table", table,
                   "--workspace", str(tmp_workspace)])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert out["current_node"] == "n0-env"
    assert out["node_kind"] == "action"
    assert out["node_name"] == "环境准备"
    assert len(out["next_actions"]) == 1
    assert out["next_actions"][0]["to_node"] == "n1-relevance"
    assert out["gate_spec"] is None
    assert out["is_blocked"] is False


def test_next_step_at_decision_gate(tmp_workspace, capsys):
    _init_at(tmp_workspace, "n1-relevance")
    table = _write_gate_table(tmp_workspace)
    rc = cli.main(["next-step", FLOW, "t", "--table", table,
                   "--workspace", str(tmp_workspace)])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert out["node_kind"] == "gate"
    assert out["gate_spec"]["kind"] == "decision"
    assert out["gate_spec"]["gate"] == "g-relevance"
    assert len(out["next_actions"]) == 2
    labels = {a["label"] for a in out["next_actions"]}
    assert labels == {"high", "low"}


def test_next_step_at_review_gate(tmp_workspace, capsys):
    _init_at(tmp_workspace, "n4-review")
    table = _write_gate_table(tmp_workspace)
    rc = cli.main(["next-step", FLOW, "t", "--table", table,
                   "--workspace", str(tmp_workspace)])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert out["gate_spec"]["kind"] == "review"
    assert out["gate_spec"]["reviewer"] == "reviewer-expert"
    labels = {a["label"] for a in out["next_actions"]}
    assert labels == {"PASS", "FAIL"}


def test_next_step_at_terminal_node(tmp_workspace, capsys):
    _init_at(tmp_workspace, "n-done")
    table = _write_gate_table(tmp_workspace)
    rc = cli.main(["next-step", FLOW, "t", "--table", table,
                   "--workspace", str(tmp_workspace)])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert out["node_kind"] == "terminal"
    assert out["next_actions"] == []


def test_next_step_when_blocked(tmp_workspace, capsys):
    _init_at(tmp_workspace, "n8-verify")
    table = _write_gate_table(tmp_workspace)
    # Trigger block: 3x FAIL on g-verify
    for i in range(1, 4):
        cli.main(["record-gate", FLOW, "t", "--gate", "g-verify", "--kind", "review",
                  "--verdict", "FAIL", "--request-id", f"r{i}",
                  "--table", table, "--workspace", str(tmp_workspace)])
        # After FAIL reflow, we need to advance back to n8-verify (except on escalate)
        if i < 3:
            st = flow_state.read_state(tmp_workspace, FLOW, "t")
            if st["current_node"] == "n6b":
                cli.main(["advance", FLOW, "t", "n8-verify", "--table", table,
                          "--workspace", str(tmp_workspace)])
    capsys.readouterr()
    rc = cli.main(["next-step", FLOW, "t", "--table", table,
                   "--workspace", str(tmp_workspace)])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert out["is_blocked"] is True
    assert out["next_actions"] == []


# ── gate-lookup ───────────────────────────────────────────────────────────

def test_gate_lookup_at_gate_node(tmp_workspace, capsys):
    _init_at(tmp_workspace, "n5-complexity")
    table = _write_gate_table(tmp_workspace)
    rc = cli.main(["gate-lookup", FLOW, "t", "--table", table,
                   "--workspace", str(tmp_workspace)])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert out["gate"] == "g-complexity"
    assert out["kind"] == "decision"
    assert out["branches"] == {"simple": "n6a", "complex": "n6b"}
    assert out["current_iter"] == 0
    assert out["max_retries"] == 3


def test_gate_lookup_at_action_node_errors(tmp_workspace, capsys):
    _init_at(tmp_workspace, "n0-env")
    table = _write_gate_table(tmp_workspace)
    rc = cli.main(["gate-lookup", FLOW, "t", "--table", table,
                   "--workspace", str(tmp_workspace)])
    assert rc == 1


# ── unblock ───────────────────────────────────────────────────────────────

def test_unblock_clears_blocked_status(tmp_workspace, capsys):
    _init_at(tmp_workspace, "n8-verify")
    table = _write_gate_table(tmp_workspace)
    # Block the flow: 3x FAIL
    for i in range(1, 4):
        cli.main(["record-gate", FLOW, "t", "--gate", "g-verify", "--kind", "review",
                  "--verdict", "FAIL", "--request-id", f"r{i}",
                  "--table", table, "--workspace", str(tmp_workspace)])
        if i < 3:
            st = flow_state.read_state(tmp_workspace, FLOW, "t")
            if st["current_node"] == "n6b":
                cli.main(["advance", FLOW, "t", "n8-verify", "--table", table,
                          "--workspace", str(tmp_workspace)])
    capsys.readouterr()
    # Unblock and redirect to n6b
    rc = cli.main(["unblock", FLOW, "t", "--to-node", "n6b",
                   "--workspace", str(tmp_workspace)])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert out["status"] == "in_progress"
    assert out["current_node"] == "n6b"
    assert out.get("blocked_reason") is None


def test_unblock_non_blocked_errors(tmp_workspace, capsys):
    _init_at(tmp_workspace, "n0-env")
    rc = cli.main(["unblock", FLOW, "t", "--workspace", str(tmp_workspace)])
    assert rc == 1
    assert "not blocked" in capsys.readouterr().err


# ── list-flows ────────────────────────────────────────────────────────────

def test_list_flows_empty(tmp_workspace, capsys):
    rc = cli.main(["list-flows", "--workspace", str(tmp_workspace)])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert out == []


def test_list_flows_with_entries(tmp_workspace, capsys):
    flow_state.init_state(tmp_workspace, FLOW, "auth",
                          display_name="Auth", initial_node="n0")
    flow_state.init_state(tmp_workspace, FLOW, "ued6",
                          display_name="UED6", initial_node="n0")
    rc = cli.main(["list-flows", "--workspace", str(tmp_workspace)])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert len(out) == 2
    slugs = {e["slug"] for e in out}
    assert slugs == {"auth", "ued6"}
    for entry in out:
        assert entry["status"] == "in_progress"
        assert entry["active"] is True


# ── enriched _print_state ────────────────────────────────────────────────

def test_show_includes_config_and_blocked_reason(tmp_workspace, capsys):
    flow_state.init_state(tmp_workspace, FLOW, "e",
                          display_name="E", initial_node="n0",
                          auto_mode=True)
    rc = cli.main(["show", FLOW, "e", "--workspace", str(tmp_workspace)])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert out["config"]["auto_mode"] is True
    assert out["display_name"] == "E"
    assert out["blocked_reason"] is None
    assert "gate_iters" in out
    assert "phase_history" in out
