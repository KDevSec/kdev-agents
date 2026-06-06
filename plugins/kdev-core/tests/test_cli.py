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
