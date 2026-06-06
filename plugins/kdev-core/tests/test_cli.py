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
