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
