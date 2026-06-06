"""Tests for kdev_core.node_machine.load_node_table — validation + adjacency."""
import pytest

from kdev_core.node_machine import load_node_table, NodeMachineError


def _toy():
    return {
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
    }


def test_load_returns_normalized_table():
    t = load_node_table(_toy())
    assert t["flow"] == "toy"
    assert t["max_retries"] == 2
    assert t["terminal_fail"] == "failed"
    assert set(t["nodes"]) == {"n1", "g1", "n2", "done", "failed"}
    assert t["adjacency"]["n1"] == ["g1"]
    assert t["adjacency"]["g1"] == ["n2", "n1"]
    assert t["adjacency"]["done"] == []


def test_default_max_retries_is_3():
    src = _toy()
    del src["max_retries"]
    assert load_node_table(src)["max_retries"] == 3


def test_node_defaults_kind_action_and_name():
    t = load_node_table({"nodes": [{"id": "only", "next": []}]})
    assert t["nodes"]["only"]["kind"] == "action"
    assert t["nodes"]["only"]["name"] == "only"


def test_missing_nodes_raises():
    with pytest.raises(NodeMachineError, match="'nodes'"):
        load_node_table({"flow": "x"})


def test_empty_nodes_raises():
    with pytest.raises(NodeMachineError, match="non-empty"):
        load_node_table({"nodes": []})


def test_duplicate_id_raises():
    with pytest.raises(NodeMachineError, match="duplicate node id"):
        load_node_table({"nodes": [{"id": "a", "next": []}, {"id": "a", "next": []}]})


def test_invalid_kind_raises():
    with pytest.raises(NodeMachineError, match="invalid kind"):
        load_node_table({"nodes": [{"id": "a", "kind": "weird", "next": []}]})


def test_dangling_next_raises():
    with pytest.raises(NodeMachineError, match="unknown node"):
        load_node_table({"nodes": [{"id": "a", "next": ["ghost"]}]})


def test_terminal_with_next_raises():
    with pytest.raises(NodeMachineError, match="terminal node"):
        load_node_table({"nodes": [{"id": "a", "kind": "terminal", "next": ["a"]}]})


def test_terminal_fail_must_be_terminal():
    src = {
        "terminal_fail": "n1",
        "nodes": [{"id": "n1", "kind": "action", "next": []}],
    }
    with pytest.raises(NodeMachineError, match="terminal_fail"):
        load_node_table(src)


def test_negative_max_retries_raises():
    with pytest.raises(NodeMachineError, match="max_retries"):
        load_node_table({"max_retries": -1, "nodes": [{"id": "a", "next": []}]})
