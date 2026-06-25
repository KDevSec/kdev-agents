"""Integration smoke — node machine driving persisted R1 flow-state end to end."""
from kdev_core import events
from kdev_core.flow_state import init_state, read_state
from kdev_core.node_machine import load_node_table, advance_persist

TABLE = load_node_table({
    "flow": "coding-flow",
    "max_retries": 2,
    "terminal_fail": "failed",
    "nodes": [
        {"id": "n1", "kind": "action", "gate": "g1", "next": ["g1"]},
        {"id": "g1", "kind": "gate", "next": ["n2", "n1"]},
        {"id": "n2", "kind": "action", "next": ["done"]},
        {"id": "done", "kind": "terminal", "next": []},
        {"id": "failed", "kind": "terminal", "next": []},
    ],
})
FLOW = "coding-flow"


def test_happy_path_persisted(tmp_workspace):
    init_state(tmp_workspace, FLOW, "auth", display_name="Auth", initial_node="n1")
    advance_persist(tmp_workspace, FLOW, "auth", "g1", table=TABLE)       # n1 -> g1
    advance_persist(tmp_workspace, FLOW, "auth", "n2", table=TABLE)       # g1 -> n2 (PASS)
    final = advance_persist(tmp_workspace, FLOW, "auth", "done", table=TABLE)  # n2 -> done
    assert final["current_node"] == "done"
    # phase_history is siphoned to events.jsonl under the new model; the 3 transitions
    # must be recorded there in order with the same `to` targets.
    trans_evs = [e for e in events.read_events(tmp_workspace, "auth") if e["type"] == "transition"]
    assert len(trans_evs) == 3
    assert [e["to"] for e in trans_evs] == ["g1", "n2", "done"]


def test_reflow_then_recover_persisted(tmp_workspace):
    init_state(tmp_workspace, FLOW, "auth", display_name="Auth", initial_node="n1")
    advance_persist(tmp_workspace, FLOW, "auth", "g1", table=TABLE)               # n1 -> g1
    advance_persist(tmp_workspace, FLOW, "auth", "n1", table=TABLE, reflow=True)  # g1 -> n1 (FAIL, retry 1)
    st = read_state(tmp_workspace, FLOW, "auth")
    assert st["current_node"] == "n1"
    assert st["retries"]["n1"] == 1
    advance_persist(tmp_workspace, FLOW, "auth", "g1", table=TABLE)               # n1 -> g1 (no retry++)
    final = advance_persist(tmp_workspace, FLOW, "auth", "n2", table=TABLE)       # g1 -> n2 (PASS)
    assert final["current_node"] == "n2"
    assert final["retries"]["n1"] == 1  # forward advance did not increment


def test_reflow_overflow_persists_terminal_fail(tmp_workspace):
    init_state(tmp_workspace, FLOW, "auth", display_name="Auth", initial_node="g1")
    # Pre-load retries to the cap via reflow, then one more overflows to terminal_fail.
    advance_persist(tmp_workspace, FLOW, "auth", "n1", table=TABLE, reflow=True)  # retry 1
    advance_persist(tmp_workspace, FLOW, "auth", "g1", table=TABLE)               # back to g1
    advance_persist(tmp_workspace, FLOW, "auth", "n1", table=TABLE, reflow=True)  # retry 2
    advance_persist(tmp_workspace, FLOW, "auth", "g1", table=TABLE)               # back to g1
    final = advance_persist(tmp_workspace, FLOW, "auth", "n1", table=TABLE, reflow=True)  # retry 3 > 2 -> failed
    assert final["current_node"] == "failed"
    # The overflow transition (forced to terminal_fail) is the last transition event.
    trans_evs = [e for e in events.read_events(tmp_workspace, "auth") if e["type"] == "transition"]
    assert trans_evs[-1]["forced_fail"] is True
    assert trans_evs[-1]["to"] == "failed"
