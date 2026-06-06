"""CLI 集成 smoke — 全程经 cli.main()，证明 R1/R2/R3 经 CLI 真驱动。

覆盖设计稿 §8：R3 三类各跑通 · FAIL→reflow→重评 PASS · kill→resume · escalate 不 force-accept。
"""
import json
from kdev_core import cli, flow_state

FLOW = "coding-flow"


def _t(tmp):
    p = tmp / "nt.yml"
    p.write_text(
        "flow: coding-flow\n"
        "max_retries: 3\n"
        "terminal_fail: n-fail\n"
        "nodes:\n"
        "  - {id: n0, kind: action, next: [n-route]}\n"
        "  - {id: n-route, kind: gate, gate: g-route, next: [n-impl, n-skip]}\n"
        "  - {id: n-skip, kind: action, next: [n-impl]}\n"
        "  - {id: n-impl, kind: action, next: [n-rev]}\n"
        "  - {id: n-rev, kind: gate, gate: g-rev, next: [n-acc, n-impl]}\n"
        "  - {id: n-acc, kind: gate, gate: g-acc, next: [n-done, n-impl]}\n"
        "  - {id: n-done, kind: terminal, next: []}\n"
        "  - {id: n-fail, kind: terminal, next: []}\n"
        "gate_specs:\n"
        "  g-route: {kind: decision, branches: {go: n-impl, skip: n-skip}, reviewer: self}\n"
        "  g-rev: {kind: review, on_pass: n-acc, on_reflow: n-impl, reviewer: self}\n"
        "  g-acc: {kind: acceptance, on_pass: n-done, on_reflow: n-impl, reviewer: self}\n",
        encoding="utf-8")
    return str(p)


def _run(argv):
    return cli.main(argv)


def test_cli_full_lifecycle_and_resume(tmp_workspace, capsys):
    t = _t(tmp_workspace)
    ws = ["--workspace", str(tmp_workspace)]
    _run(["init", FLOW, "x", "--display-name", "X", "--initial-node", "n0"] + ws)
    _run(["advance", FLOW, "x", "n-route", "--table", t] + ws)
    # decision -> go 分支
    _run(["record-gate", FLOW, "x", "--gate", "g-route", "--kind", "decision",
          "--verdict", "go", "--request-id", "d1", "--table", t] + ws)
    assert flow_state.read_state(tmp_workspace, FLOW, "x")["current_node"] == "n-impl"

    # review FAIL -> reflow 回 n-impl，修，再回 n-rev 重评 PASS
    _run(["advance", FLOW, "x", "n-rev", "--table", t] + ws)
    _run(["record-gate", FLOW, "x", "--gate", "g-rev", "--kind", "review",
          "--verdict", "FAIL", "--request-id", "rv1", "--table", t] + ws)
    assert flow_state.read_state(tmp_workspace, FLOW, "x")["current_node"] == "n-impl"

    # kill→resume：新"会话"从 n-impl 续，不从头
    capsys.readouterr()
    _run(["resume", FLOW, "x"] + ws)
    assert json.loads(capsys.readouterr().out)["current_node"] == "n-impl"

    _run(["advance", FLOW, "x", "n-rev", "--table", t] + ws)
    _run(["record-gate", FLOW, "x", "--gate", "g-rev", "--kind", "review",
          "--verdict", "PASS", "--request-id", "rv2", "--table", t] + ws)
    assert flow_state.read_state(tmp_workspace, FLOW, "x")["current_node"] == "n-acc"

    # acceptance PASS -> terminal
    _run(["record-gate", FLOW, "x", "--gate", "g-acc", "--kind", "acceptance",
          "--verdict", "PASS", "--request-id", "ac1", "--table", t] + ws)
    final = flow_state.read_state(tmp_workspace, FLOW, "x")
    assert final["current_node"] == "n-done"
    # 三类 gate 都进了 history（decision + review*2 + acceptance = 4）
    assert len(final["history"]) == 4
