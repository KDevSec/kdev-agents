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
