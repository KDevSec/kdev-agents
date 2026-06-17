# plugins/kdev-team/tests/test_router_lint.py
import pytest
from kdev_team import roster


def test_flow_owner_vs_callee():
    assert roster.is_flow_owner("req-architect") is True
    assert roster.is_flow_owner("dev-engineer") is True
    assert roster.is_flow_owner("reviewer") is False    # callee
    assert roster.is_flow_owner("no-such-emp") is False


def test_flows_for_single_and_multi_flow_owner():
    assert roster.flows_for("req-architect") == ["design-flow"]
    assert roster.flows_for("dev-engineer") == ["coding-flow"]
    assert set(roster.flows_for("test-engineer")) == {"test-design-flow", "test-exec-flow"}


def test_gate_specs_and_delivery_node_resolved_from_node_table():
    gs = roster.gate_specs("req-architect", "design-flow")
    assert gs["g-sr-review"]["reviewer"] == "reviewer-expert"
    assert roster.delivery_node("req-architect", "design-flow") == "n8-merge"
    assert roster.delivery_node("test-engineer", "test-design-flow") == "n3-merge"


def test_unknown_flow_for_employee_raises():
    with pytest.raises(roster.RosterError):
        roster.node_table_data("req-architect", "coding-flow")
