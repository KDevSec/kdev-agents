# kdev-core R2 (node machine) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build kdev-core's R2 layer — a generic node machine: a validated node-table (flow SOP) + a pure `advance` transition with adjacency check, guard, and bounded reflow (retry++ → forced terminal-fail), plus a thin persistence wrapper over R1.

**Architecture:** A stdlib-only module `kdev_core/node_machine.py` built on top of R1 (`kdev_core/flow_state.py`). `load_node_table` validates+normalizes a node-table into nodes + an adjacency map. `advance(state, to_node, ...)` is a **pure function** (state dict → new state dict, or raises) implementing the OMC three-step transition (adjacency → guard → immutable update appending `phase_history`), extended with bounded reflow. `advance_persist` wraps `advance` with `flow_state.write_state`. R2 adds two state fields — `phase_history` (transition log) and `retries` (per-node reflow counter) — and never touches R1's `history` (reserved for R3 GateResults).

**Tech Stack:** Python 3 (stdlib only: `datetime`), pytest. Builds on the kdev-core package created in the R1 plan.

**Source of truth:**
- Pattern reference: OMC Team Pipeline [transitions.ts](../../framework/04-references/_repos/oh-my-claudecode/src/hooks/team-pipeline/transitions.ts) (adjacency `ALLOWED` + guard separated from edges + immutable `phase_history` append).
- Target spec: [底座设计总纲 §4.2 + §7](../../framework/01-design/2026-06-05-01-kdev-core底座设计总纲-v1.0.md) (advance 三段式 + 有界回流+幂等豁免+强制failed).
- Builds on: [R1 plan](./2026-06-06-kdev-core-R1-flow-state.md) (`flow_state.py`).

**Out of scope for P2 (deferred):** L0+L1 orchestration merge (SOP §6) — a later plan or folded into the 阶段1 coding-flow refit. R3 gates (GateResult/record_gate) — separate plan P3.

**Environment note:** `python` is NOT on PATH — use **`python3`**. Commits MUST use the AI-identity override (`git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit ...`, **no quotes** on `-c key=value`, no `Co-Authored-By`).

---

## File Structure

| File | Responsibility |
|---|---|
| `plugins/kdev-core/kdev_core/node_machine.py` | `load_node_table` / `advance` / `advance_persist` + `NodeMachineError` + `NODE_KINDS` |
| `plugins/kdev-core/tests/test_node_table.py` | node-table validation + adjacency tests (pure) |
| `plugins/kdev-core/tests/test_advance.py` | `advance` adjacency/guard + bounded-reflow tests (pure) |
| `plugins/kdev-core/tests/test_node_smoke.py` | `advance_persist` + integration smoke over R1 (filesystem) |

Run from repo root: `python3 -m pytest plugins/kdev-core/tests -q`.

---

## Task 1: node-table loader — validation + adjacency

**Files:**
- Create: `plugins/kdev-core/tests/test_node_table.py`
- Create: `plugins/kdev-core/kdev_core/node_machine.py`

- [ ] **Step 1: Write the failing test module**

Create `plugins/kdev-core/tests/test_node_table.py`:

```python
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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest plugins/kdev-core/tests/test_node_table.py -q`
Expected: import error — `ModuleNotFoundError: No module named 'kdev_core.node_machine'`.

- [ ] **Step 3: Write the implementation**

Create `plugins/kdev-core/kdev_core/node_machine.py`:

```python
"""kdev-core R2 — node machine (node-table + advance: adjacency/guard/bounded-reflow).

Builds on R1 (kdev_core.flow_state). A node-table is a flow's SOP: nodes + allowed
transitions. `advance` is a PURE function (state dict -> new state dict, or raises);
it does not touch the filesystem. `advance_persist` wraps it with flow_state.write_state.

Borrows OMC Team Pipeline (src/hooks/team-pipeline/transitions.ts): an adjacency map
separated from a guard(state, next)->str|None, plus an immutable update appending a
phase_history entry. Adds bounded reflow (retry++ on a gate->action loop) with a forced
terminal-fail on overflow — the [OMC-avoid] "never loop forever" rule.

R2 adds two state fields: `phase_history` (transition log) and `retries` (per-node reflow
counter). It never touches R1's `history` field (reserved for R3 GateResults).
"""
from datetime import datetime, timezone

NODE_KINDS = {"action", "gate", "terminal"}
DEFAULT_MAX_RETRIES = 3


class NodeMachineError(Exception):
    """Malformed node-table, illegal transition, or guard failure."""


def _now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_node_table(table):
    """Validate + normalize a node-table dict.

    Returns {flow, max_retries, terminal_fail, nodes: {id: node}, adjacency: {id: [next_ids]}}.
    """
    if not isinstance(table, dict) or "nodes" not in table:
        raise NodeMachineError("node-table must be a dict with a 'nodes' list")
    nodes_list = table["nodes"]
    if not isinstance(nodes_list, list) or not nodes_list:
        raise NodeMachineError("node-table 'nodes' must be a non-empty list")

    nodes = {}
    for n in nodes_list:
        nid = n.get("id")
        if not nid:
            raise NodeMachineError(f"node missing 'id': {n!r}")
        if nid in nodes:
            raise NodeMachineError(f"duplicate node id: {nid!r}")
        kind = n.get("kind", "action")
        if kind not in NODE_KINDS:
            raise NodeMachineError(
                f"node {nid!r} has invalid kind {kind!r} (must be one of {sorted(NODE_KINDS)})"
            )
        nxt = n.get("next", [])
        if not isinstance(nxt, list):
            raise NodeMachineError(f"node {nid!r} 'next' must be a list")
        nodes[nid] = {
            "id": nid,
            "name": n.get("name", nid),
            "kind": kind,
            "gate": n.get("gate"),
            "next": list(nxt),
        }

    for nid, n in nodes.items():
        for tgt in n["next"]:
            if tgt not in nodes:
                raise NodeMachineError(f"node {nid!r} points to unknown node {tgt!r}")
        if n["kind"] == "terminal" and n["next"]:
            raise NodeMachineError(
                f"terminal node {nid!r} must have empty 'next', got {n['next']!r}"
            )

    terminal_fail = table.get("terminal_fail")
    if terminal_fail is not None:
        if terminal_fail not in nodes:
            raise NodeMachineError(f"terminal_fail {terminal_fail!r} is not a node")
        if nodes[terminal_fail]["kind"] != "terminal":
            raise NodeMachineError(f"terminal_fail {terminal_fail!r} must be a terminal node")

    max_retries = table.get("max_retries", DEFAULT_MAX_RETRIES)
    if not isinstance(max_retries, int) or isinstance(max_retries, bool) or max_retries < 0:
        raise NodeMachineError(f"max_retries must be a non-negative int, got {max_retries!r}")

    return {
        "flow": table.get("flow"),
        "max_retries": max_retries,
        "terminal_fail": terminal_fail,
        "nodes": nodes,
        "adjacency": {nid: list(n["next"]) for nid, n in nodes.items()},
    }
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest plugins/kdev-core/tests/test_node_table.py -q`
Expected: all tests PASS (11 passed).

- [ ] **Step 5: Commit**

```bash
git add plugins/kdev-core/kdev_core/node_machine.py plugins/kdev-core/tests/test_node_table.py
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-core): R2 node-table loader + validation + adjacency (P2 Task1)"
```

---

## Task 2: `advance` — adjacency + guard (pure, no reflow yet)

**Files:**
- Create: `plugins/kdev-core/tests/test_advance.py`
- Modify: `plugins/kdev-core/kdev_core/node_machine.py` (append `advance`)

- [ ] **Step 1: Write the failing test module**

Create `plugins/kdev-core/tests/test_advance.py`:

```python
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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m pytest plugins/kdev-core/tests/test_advance.py -q`
Expected: FAIL — `ImportError: cannot import name 'advance'`.

- [ ] **Step 3: Append the implementation**

Append to `plugins/kdev-core/kdev_core/node_machine.py`:

```python
def advance(state, to_node, *, table, guard=None, reason=None):
    """Pure transition: returns a NEW state dict, or raises NodeMachineError.

    Three steps (OMC pattern):
      1. adjacency: to_node must be in adjacency[current_node] (else raise).
      2. guard: if given, guard(state, to_node) -> str|None; non-None -> raise(reason).
      3. immutable update: new current_node + append a phase_history entry.
    """
    current = state.get("current_node")
    if current is None:
        raise NodeMachineError("cannot advance: state has no current_node")
    adjacency = table["adjacency"]
    if current not in adjacency:
        raise NodeMachineError(f"current_node {current!r} is not in the node-table")
    if to_node not in adjacency[current]:
        raise NodeMachineError(f"illegal transition: {current!r} -> {to_node!r}")

    if guard is not None:
        greason = guard(state, to_node)
        if greason is not None:
            raise NodeMachineError(f"guard rejected {current!r} -> {to_node!r}: {greason}")

    new_state = dict(state)
    new_state["current_node"] = to_node
    entry = {
        "from": current,
        "to": to_node,
        "reflow": False,
        "forced_fail": False,
        "reason": reason,
        "entered_at": _now_iso(),
    }
    new_state["phase_history"] = [*state.get("phase_history", []), entry]
    return new_state
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest plugins/kdev-core/tests/test_advance.py -q`
Expected: all tests PASS (6 passed).

- [ ] **Step 5: Commit**

```bash
git add plugins/kdev-core/kdev_core/node_machine.py plugins/kdev-core/tests/test_advance.py
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-core): R2 advance — adjacency + guard, pure (P2 Task2)"
```

---

## Task 3: bounded reflow + forced terminal-fail + idempotent exemption

**Files:**
- Modify: `plugins/kdev-core/kdev_core/node_machine.py` (extend `advance` with `reflow`)
- Modify: `plugins/kdev-core/tests/test_advance.py` (append reflow tests)

- [ ] **Step 1: Append the failing reflow tests**

Append to `plugins/kdev-core/tests/test_advance.py`:

```python
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
```

- [ ] **Step 2: Run to verify the new tests fail**

Run: `python3 -m pytest plugins/kdev-core/tests/test_advance.py -q`
Expected: FAIL — `advance()` has no `reflow` keyword (TypeError) on the new tests.

- [ ] **Step 3: Replace `advance` with the reflow-aware version**

Replace the entire `advance` function in `plugins/kdev-core/kdev_core/node_machine.py` with:

```python
def advance(state, to_node, *, table, guard=None, reflow=False, reason=None):
    """Pure transition: returns a NEW state dict, or raises NodeMachineError.

    Three steps (OMC pattern):
      1. adjacency: to_node must be in adjacency[current_node] (else raise).
      2. guard: if given, guard(state, to_node) -> str|None; non-None -> raise(reason).
      3. immutable update: new current_node + append a phase_history entry.

    Bounded reflow: reflow=True (a gate->action retry) increments retries[to_node];
    if it exceeds table["max_retries"], the transition is forced to table["terminal_fail"]
    (or raises if no terminal_fail is configured). Forward advances (reflow=False) never
    touch the retry counter — the idempotent exemption.
    """
    current = state.get("current_node")
    if current is None:
        raise NodeMachineError("cannot advance: state has no current_node")
    adjacency = table["adjacency"]
    if current not in adjacency:
        raise NodeMachineError(f"current_node {current!r} is not in the node-table")
    if to_node not in adjacency[current]:
        raise NodeMachineError(f"illegal transition: {current!r} -> {to_node!r}")

    if guard is not None:
        greason = guard(state, to_node)
        if greason is not None:
            raise NodeMachineError(f"guard rejected {current!r} -> {to_node!r}: {greason}")

    retries = dict(state.get("retries", {}))
    target = to_node
    forced_fail = False
    if reflow:
        retries[to_node] = retries.get(to_node, 0) + 1
        if retries[to_node] > table["max_retries"]:
            tf = table.get("terminal_fail")
            if tf is None:
                raise NodeMachineError(
                    f"retry overflow at {to_node!r} (> {table['max_retries']}) "
                    f"and no terminal_fail configured"
                )
            target = tf
            forced_fail = True

    new_state = dict(state)
    new_state["current_node"] = target
    new_state["retries"] = retries
    entry = {
        "from": current,
        "to": target,
        "reflow": bool(reflow),
        "forced_fail": forced_fail,
        "reason": reason,
        "entered_at": _now_iso(),
    }
    new_state["phase_history"] = [*state.get("phase_history", []), entry]
    return new_state
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m pytest plugins/kdev-core/tests/test_advance.py -q`
Expected: all tests PASS (11 passed: 6 from Task 2 + 5 reflow).

- [ ] **Step 5: Commit**

```bash
git add plugins/kdev-core/kdev_core/node_machine.py plugins/kdev-core/tests/test_advance.py
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-core): R2 bounded reflow + forced terminal-fail + idempotent exemption (P2 Task3)"
```

---

## Task 4: `advance_persist` (R1 integration) + integration smoke

**Files:**
- Modify: `plugins/kdev-core/kdev_core/node_machine.py` (append `advance_persist`)
- Create: `plugins/kdev-core/tests/test_node_smoke.py`

- [ ] **Step 1: Write the failing integration test**

Create `plugins/kdev-core/tests/test_node_smoke.py`:

```python
"""Integration smoke — node machine driving persisted R1 flow-state end to end."""
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
    assert len(final["phase_history"]) == 3
    assert [e["to"] for e in final["phase_history"]] == ["g1", "n2", "done"]


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
    assert final["phase_history"][-1]["forced_fail"] is True
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m pytest plugins/kdev-core/tests/test_node_smoke.py -q`
Expected: FAIL — `ImportError: cannot import name 'advance_persist'`.

- [ ] **Step 3: Append `advance_persist`**

Append to `plugins/kdev-core/kdev_core/node_machine.py`:

```python
def advance_persist(workspace, flow, slug, to_node, *, table, guard=None,
                    reflow=False, reason=None, step_id=None):
    """advance() + persist via R1 flow_state.write_state. Returns the persisted state."""
    from kdev_core import flow_state

    state = flow_state.read_state(workspace, flow, slug)
    new_state = advance(state, to_node, table=table, guard=guard, reflow=reflow, reason=reason)
    flow_state.write_state(workspace, flow, slug, new_state, step_id=step_id)
    return flow_state.read_state(workspace, flow, slug)
```

- [ ] **Step 4: Run the smoke + full suite**

Run: `python3 -m pytest plugins/kdev-core/tests/test_node_smoke.py -q`
Expected: 3 passed.

Run: `python3 -m pytest plugins/kdev-core/tests -q`
Expected: all PASS (**47**: R1 22 + node-table 11 + advance 11 + smoke 3).

- [ ] **Step 5: Commit**

```bash
git add plugins/kdev-core/kdev_core/node_machine.py plugins/kdev-core/tests/test_node_smoke.py
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-core): R2 advance_persist + integration smoke over R1 (P2 Task4)"
```

---

## Done criteria

- `python3 -m pytest plugins/kdev-core/tests -q` → all green (R1 22 + R2 node-table 11 + advance 11 + smoke 3).
- `node_machine.py` exposes: `load_node_table`, `advance`, `advance_persist`, `NodeMachineError`, `NODE_KINDS`.
- node-table validation rejects: missing/empty nodes, duplicate ids, invalid kind, dangling `next`, terminal-with-next, non-terminal `terminal_fail`, negative `max_retries`.
- `advance` is pure (no input mutation), enforces adjacency + guard, appends `phase_history`, and never touches R1's `history`.
- Bounded reflow: reflow increments `retries[to_node]`; overflow forces `terminal_fail` (or raises if unconfigured); forward advances never increment (idempotent exemption).
- `advance_persist` correctly round-trips through R1's atomic write.

**Next plan (after P2 executes):** P3 — R3 three-kind gates (GateResult `{request_id, iter, verdict}` + `record_gate` for review/decision/acceptance + escalate-no-force-accept), appending to R1's `history` and driving R2 reflow on FAIL.
</content>
