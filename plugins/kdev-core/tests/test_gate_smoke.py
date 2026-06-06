"""Integration smoke — full gate loop over persisted R1 + R2 (review FAIL->reflow->PASS, and escalate)."""
from kdev_core.flow_state import init_state, read_state, write_state
from kdev_core.node_machine import load_node_table
from kdev_core.gate import make_gate_result, record_gate_persist

TABLE = load_node_table({
    "flow": "coding-flow",
    "max_retries": 2,
    "terminal_fail": "failed",
    "nodes": [
        {"id": "n-tdd", "kind": "action", "gate": "g-code", "next": ["g-code"]},
        {"id": "g-code", "kind": "gate", "next": ["n-ship", "n-tdd"]},
        {"id": "n-ship", "kind": "action", "next": ["done"]},
        {"id": "done", "kind": "terminal", "next": []},
        {"id": "failed", "kind": "terminal", "next": []},
    ],
})
SPECS = {"g-code": {"kind": "review", "on_pass": "n-ship", "on_reflow": "n-tdd"}}
FLOW = "coding-flow"


def _seed(tmp, slug):
    init_state(tmp, FLOW, slug, display_name="X", initial_node="g-code")


def test_fail_then_pass_persisted(tmp_workspace):
    _seed(tmp_workspace, "auth")
    r_fail = make_gate_result("g-code", "review", node="g-code", verdict="FAIL", request_id="r1")
    st = record_gate_persist(tmp_workspace, FLOW, "auth", r_fail, table=TABLE, gate_specs=SPECS)
    assert st["current_node"] == "n-tdd"
    assert st["gate_iters"]["g-code"] == 1
    assert st["status"] == "in_progress"

    from kdev_core.node_machine import advance_persist
    advance_persist(tmp_workspace, FLOW, "auth", "g-code", table=TABLE)
    r_pass = make_gate_result("g-code", "review", node="g-code", verdict="PASS", request_id="r2")
    final = record_gate_persist(tmp_workspace, FLOW, "auth", r_pass, table=TABLE, gate_specs=SPECS)
    assert final["current_node"] == "n-ship"
    assert final["gate_iters"]["g-code"] == 0
    assert len(final["history"]) == 2
    assert final["gate_calls"] == 2


def test_escalate_persisted(tmp_workspace):
    _seed(tmp_workspace, "auth2")
    r1 = make_gate_result("g-code", "review", node="g-code", verdict="FAIL", request_id="r1")
    record_gate_persist(tmp_workspace, FLOW, "auth2", r1, table=TABLE, gate_specs=SPECS)
    from kdev_core.node_machine import advance_persist
    advance_persist(tmp_workspace, FLOW, "auth2", "g-code", table=TABLE)
    r2 = make_gate_result("g-code", "review", node="g-code", verdict="FAIL", request_id="r2")
    final = record_gate_persist(tmp_workspace, FLOW, "auth2", r2, table=TABLE, gate_specs=SPECS)
    assert final["status"] == "blocked"
    assert final["current_node"] == "g-code"
    assert final["gate_iters"]["g-code"] == 2
