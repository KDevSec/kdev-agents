"""Tests for kdev_core.gate.record_gate — review/acceptance dispatch + escalate + counters."""
import pytest

from kdev_core.node_machine import load_node_table
from kdev_core.gate import make_gate_result, record_gate, GateError

TABLE = load_node_table({
    "flow": "toy",
    "max_retries": 2,
    "terminal_fail": "failed",
    "nodes": [
        {"id": "n1", "kind": "action", "gate": "g-code", "next": ["g1"]},
        {"id": "g1", "kind": "gate", "next": ["n2", "n1"]},
        {"id": "n2", "kind": "action", "next": ["done"]},
        {"id": "done", "kind": "terminal", "next": []},
        {"id": "failed", "kind": "terminal", "next": []},
    ],
})
SPECS = {"g-code": {"kind": "review", "on_pass": "n2", "on_reflow": "n1"}}


def _state():
    return {"current_node": "g1", "status": "in_progress", "history": [], "phase_history": []}


def test_review_pass_advances_to_on_pass():
    r = make_gate_result("g-code", "review", node="g1", verdict="PASS", request_id="r1")
    out = record_gate(_state(), r, table=TABLE, gate_specs=SPECS)
    assert out["current_node"] == "n2"
    assert out["history"][-1]["verdict"] == "PASS"
    assert out["gate_calls"] == 1


def test_review_fail_within_cap_reflows():
    r = make_gate_result("g-code", "review", node="g1", verdict="FAIL", request_id="r1")
    out = record_gate(_state(), r, table=TABLE, gate_specs=SPECS)
    assert out["current_node"] == "n1"
    assert out["gate_iters"]["g-code"] == 1
    assert out["status"] == "in_progress"


def test_review_fail_at_cap_escalates_without_force_accept():
    st = _state()
    st["gate_iters"] = {"g-code": 1}
    r = make_gate_result("g-code", "review", node="g1", verdict="FAIL", request_id="r1")
    out = record_gate(st, r, table=TABLE, gate_specs=SPECS)
    assert out["status"] == "blocked"
    assert out["current_node"] == "g1"
    assert "blocked_reason" in out
    assert out["gate_iters"]["g-code"] == 2


def test_review_pass_resets_iter():
    st = _state()
    st["gate_iters"] = {"g-code": 1}
    r = make_gate_result("g-code", "review", node="g1", verdict="PASS", request_id="r1")
    out = record_gate(st, r, table=TABLE, gate_specs=SPECS)
    assert out["gate_iters"]["g-code"] == 0


def test_record_gate_is_pure():
    st = _state()
    r = make_gate_result("g-code", "review", node="g1", verdict="PASS", request_id="r1")
    record_gate(st, r, table=TABLE, gate_specs=SPECS)
    assert st["current_node"] == "g1"
    assert st["history"] == []


def test_unknown_gate_spec_raises():
    r = make_gate_result("g-ghost", "review", node="g1", verdict="PASS", request_id="r1")
    with pytest.raises(GateError, match="no gate spec"):
        record_gate(_state(), r, table=TABLE, gate_specs=SPECS)
