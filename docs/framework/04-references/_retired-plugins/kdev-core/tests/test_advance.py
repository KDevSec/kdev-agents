"""Tests for kdev_core.node_machine.advance — adjacency + guard (pure)."""
import pytest

from kdev_core.node_machine import load_node_table, advance, NodeMachineError

TABLE = load_node_table({
    "flow": "toy",
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


def _state(current):
    return {"current_node": current, "phase_history": []}


def test_legal_advance_updates_node_and_logs():
    out = advance(_state("n1"), "g1", table=TABLE, reason="sr-done")
    assert out["current_node"] == "g1"
    assert len(out["phase_history"]) == 1
    e = out["phase_history"][0]
    assert e["from"] == "n1" and e["to"] == "g1"
    assert e["reason"] == "sr-done"
    assert e["reflow"] is False
    assert "entered_at" in e


def test_advance_is_pure_does_not_mutate_input():
    st = _state("n1")
    advance(st, "g1", table=TABLE)
    assert st["current_node"] == "n1"
    assert st["phase_history"] == []


def test_illegal_transition_raises():
    with pytest.raises(NodeMachineError, match="illegal transition"):
        advance(_state("n1"), "n2", table=TABLE)


def test_advance_from_none_raises():
    with pytest.raises(NodeMachineError, match="no current_node"):
        advance({"current_node": None}, "g1", table=TABLE)


def test_guard_pass_proceeds():
    out = advance(_state("g1"), "n2", table=TABLE, guard=lambda s, to: None)
    assert out["current_node"] == "n2"


def test_guard_rejection_raises_with_reason():
    def guard(s, to):
        return "artifacts missing"
    with pytest.raises(NodeMachineError, match="guard rejected.*artifacts missing"):
        advance(_state("g1"), "n2", table=TABLE, guard=guard)


def _state_r(current, retries=None):
    return {"current_node": current, "phase_history": [], "retries": dict(retries or {})}


def test_reflow_increments_retry_counter():
    out = advance(_state_r("g1"), "n1", table=TABLE, reflow=True)
    assert out["current_node"] == "n1"
    assert out["retries"]["n1"] == 1
    assert out["phase_history"][0]["reflow"] is True


def test_reflow_within_cap_allowed():
    # max_retries=2; existing 1 -> becomes 2, which is NOT > 2, so still a normal reflow.
    out = advance(_state_r("g1", {"n1": 1}), "n1", table=TABLE, reflow=True)
    assert out["current_node"] == "n1"
    assert out["retries"]["n1"] == 2
    assert out["phase_history"][0]["forced_fail"] is False


def test_reflow_overflow_forces_terminal_fail():
    # existing 2 -> becomes 3, which IS > 2 -> redirect to terminal_fail.
    out = advance(_state_r("g1", {"n1": 2}), "n1", table=TABLE, reflow=True)
    assert out["current_node"] == "failed"
    assert out["retries"]["n1"] == 3
    e = out["phase_history"][0]
    assert e["to"] == "failed"
    assert e["forced_fail"] is True


def test_forward_advance_does_not_increment_retries():
    out = advance(_state_r("n1", {"n1": 1}), "g1", table=TABLE)  # reflow defaults False
    assert out["retries"] == {"n1": 1}  # unchanged (idempotent exemption)


def test_reflow_overflow_without_terminal_fail_raises():
    table_no_fail = load_node_table({
        "max_retries": 1,
        "nodes": [
            {"id": "a", "kind": "action", "next": ["g"]},
            {"id": "g", "kind": "gate", "next": ["a"]},
        ],
    })
    with pytest.raises(NodeMachineError, match="retry overflow"):
        advance({"current_node": "g", "phase_history": [], "retries": {"a": 1}},
                "a", table=table_no_fail, reflow=True)
