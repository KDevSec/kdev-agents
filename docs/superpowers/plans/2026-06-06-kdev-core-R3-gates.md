# kdev-core R3 (three-kind gate) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build kdev-core's R3 layer — a structured `GateResult` + a `record_gate` dispatcher that unifies the three gate kinds (review / acceptance / decision), appends verdicts to R1's `history`, maintains double counters, and drives the resulting transition through R2's `advance` — with escalate-on-exhaustion that never force-accepts.

**Architecture:** A stdlib-only module `kdev_core/gate.py` on top of R1 (`flow_state`) + R2 (`node_machine.advance`). `make_gate_result` builds+validates a structured verdict (no regex). `record_gate(state, gate_result, *, table, gate_specs)` is a **pure function** (state → state): it appends the GateResult to `state["history"]` (R1's field, distinct from R2's `phase_history`), bumps the double counters (`gate_iters[gate]` + flow-total `gate_calls`), and dispatches by kind — review/acceptance PASS → advance to `on_pass`; FAIL within cap → advance to `on_reflow`; FAIL at cap → escalate (`status="blocked"`, no advance, **no force-accept**); decision → advance to `branches[verdict]`. `record_gate_persist` wraps it with flow_state I/O. **R2 is untouched** — gate semantics ride in a separate `gate_specs` arg, and all transition targets are still validated by R2's adjacency.

**Tech Stack:** Python 3 (stdlib only: `datetime`), pytest. Builds on R1+R2 (both merged to main).

**Source of truth:**
- Target spec: [底座设计总纲 §4.3 + §4.4](../../framework/01-design/2026-06-05-01-kdev-core底座设计总纲-v1.0.md) (GateResult + record_gate 三类 + escalate 不 force-accept + 双重计数 + request_id).
- OMC avoid-patterns: escalate ≠ force-accept; structured verdict ≠ regex ([底座总纲 §7](../../framework/01-design/2026-06-05-01-kdev-core底座设计总纲-v1.0.md)).
- Builds on: [R1 plan](./2026-06-06-kdev-core-R1-flow-state.md) (`flow_state`) + [R2 plan](./2026-06-06-kdev-core-R2-node-machine.md) (`node_machine.advance`).

**Design decisions baked in:**
1. Gate semantics in a separate `gate_specs` arg (`{gate_id: {...}}`) — R2 `node_machine.py` is NOT modified.
2. GateResults append to R1's `history`; R2's `phase_history` is for transitions. Distinct fields.
3. Review/acceptance bounding = R3 escalate (`gate_iters` ≥ max → `status="blocked"`, no force-accept). `record_gate` calls `advance(reflow=False)` always — R3 owns the bound, distinct from R2's mechanical reflow→terminal_fail.
4. Double counting maintained by `record_gate` (per-gate `gate_iters` + flow-total `gate_calls`) — base counts, doesn't trust caller's reported `iter`.
5. `request_id` recorded for traceability; full open/approval LOCK enforcement DEFERRED (noted).

**Out of scope (deferred):** request_id open/approval lock enforcement; SOP L0+L1 merge; CQO/meta-review. Those land later or in 阶段1.

**Environment note:** use `python3`. Commits MUST use the AI-identity override (`git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit ...`, no quotes on `-c key=value`, no `Co-Authored-By`).

---

## File Structure

| File | Responsibility |
|---|---|
| `plugins/kdev-core/kdev_core/gate.py` | `make_gate_result` / `record_gate` / `record_gate_persist` + `GateError` + `GATE_KINDS` / `GATE_VERDICTS` |
| `plugins/kdev-core/tests/test_gate_result.py` | GateResult builder + validation tests (pure) |
| `plugins/kdev-core/tests/test_record_gate.py` | `record_gate` review/acceptance/decision + escalate + counters (pure) |
| `plugins/kdev-core/tests/test_gate_smoke.py` | `record_gate_persist` + full gate-loop integration over R1+R2 |

Run from repo root: `python3 -m pytest plugins/kdev-core/tests -q`.

---

## Task 1: `make_gate_result` — structured verdict builder + validation

**Files:**
- Create: `plugins/kdev-core/tests/test_gate_result.py`
- Create: `plugins/kdev-core/kdev_core/gate.py`

- [ ] **Step 1: Write the failing test module**

Create `plugins/kdev-core/tests/test_gate_result.py`:

```python
"""Tests for kdev_core.gate.make_gate_result — structured verdict builder + validation."""
import pytest

from kdev_core.gate import make_gate_result, GateError, GATE_KINDS


def test_build_review_result_has_all_fields():
    r = make_gate_result("g-code", "review", node="n-tdd", verdict="PASS", request_id="req-1")
    assert r["gate"] == "g-code"
    assert r["kind"] == "review"
    assert r["node"] == "n-tdd"
    assert r["verdict"] == "PASS"
    assert r["request_id"] == "req-1"
    assert r["by"] == "ai"          # default
    assert r["iter"] == 1           # default
    assert r["issues"] == []
    assert r["revisions"] == []
    assert "ts" in r


def test_build_with_overrides():
    r = make_gate_result("g", "acceptance", node="n", verdict="FAIL", request_id="r2",
                         by="human", iter=3, issues=["x"], revisions=["y"], ts="2026-01-01T00:00:00+00:00")
    assert r["by"] == "human" and r["iter"] == 3
    assert r["issues"] == ["x"] and r["revisions"] == ["y"]
    assert r["ts"] == "2026-01-01T00:00:00+00:00"


def test_decision_verdict_is_freeform_branch_key():
    r = make_gate_result("g-route", "decision", node="n", verdict="rework", request_id="r3")
    assert r["verdict"] == "rework"   # decision verdicts are branch keys, not PASS/FAIL


def test_invalid_kind_raises():
    with pytest.raises(GateError, match="kind"):
        make_gate_result("g", "weird", node="n", verdict="PASS", request_id="r")


def test_missing_request_id_raises():
    with pytest.raises(GateError, match="request_id"):
        make_gate_result("g", "review", node="n", verdict="PASS", request_id="")


def test_review_verdict_must_be_pass_or_fail():
    with pytest.raises(GateError, match="PASS/FAIL"):
        make_gate_result("g", "review", node="n", verdict="MAYBE", request_id="r")


def test_acceptance_verdict_must_be_pass_or_fail():
    with pytest.raises(GateError, match="PASS/FAIL"):
        make_gate_result("g", "acceptance", node="n", verdict="ok", request_id="r")


def test_gate_kinds_constant():
    assert GATE_KINDS == {"review", "decision", "acceptance"}
```

- [ ] **Step 2: Run to verify they fail**

Run: `python3 -m pytest plugins/kdev-core/tests/test_gate_result.py -q`
Expected: `ModuleNotFoundError: No module named 'kdev_core.gate'`.

- [ ] **Step 3: Write the implementation**

Create `plugins/kdev-core/kdev_core/gate.py`:

```python
"""kdev-core R3 — three-kind gate (GateResult + record_gate).

Builds on R1 (flow_state.history) + R2 (node_machine.advance). A GateResult is the
structured verdict a flow feeds back after running a gate; record_gate appends it to
state["history"], bumps the double counters, and applies the resulting transition via
R2 advance.

Three gate kinds:
  - review / acceptance: verdict PASS|FAIL.
        PASS               -> advance(on_pass), reset that gate's iter
        FAIL, iter < max   -> advance(on_reflow)              [redo]
        FAIL, iter >= max  -> escalate: status="blocked", NO advance, NO force-accept
  - decision: verdict is a branch key -> advance(branches[verdict])

Gate semantics ride in a separate `gate_specs` arg (R2's node_machine is untouched):
  gate_specs = {
    "g-code":  {"kind": "review",     "on_pass": "n-next", "on_reflow": "n-tdd"},
    "g-e2e":   {"kind": "acceptance", "on_pass": "n-ship", "on_reflow": "n-fix"},
    "g-route": {"kind": "decision",   "branches": {"go": "n-go", "rework": "n-plan"}},
  }
All transition targets are still validated by R2 adjacency (advance raises on illegal edges).

[OMC] structured verdict (no regex); escalate never force-accepts. request_id is recorded
for traceability; full open/approval LOCK enforcement is deferred.
"""
from datetime import datetime, timezone

from kdev_core.node_machine import advance

GATE_KINDS = {"review", "decision", "acceptance"}
GATE_VERDICTS = {"PASS", "FAIL"}  # review/acceptance; decision uses branch keys


class GateError(Exception):
    """Malformed GateResult, unknown gate spec, or invalid verdict."""


def _now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def make_gate_result(gate, kind, *, node, verdict, request_id,
                     by="ai", iter=1, issues=None, revisions=None, ts=None):
    """Build + validate a structured GateResult dict."""
    if not gate:
        raise GateError("GateResult requires a non-empty gate id")
    if kind not in GATE_KINDS:
        raise GateError(f"GateResult kind must be one of {sorted(GATE_KINDS)}, got {kind!r}")
    if not request_id:
        raise GateError("GateResult requires a non-empty request_id")
    if kind in ("review", "acceptance") and verdict not in GATE_VERDICTS:
        raise GateError(f"{kind} verdict must be PASS/FAIL, got {verdict!r}")
    return {
        "gate": gate,
        "kind": kind,
        "node": node,
        "request_id": request_id,
        "iter": iter,
        "verdict": verdict,
        "by": by,
        "issues": list(issues or []),
        "revisions": list(revisions or []),
        "ts": ts or _now_iso(),
    }
```

- [ ] **Step 4: Run to verify they pass**

Run: `python3 -m pytest plugins/kdev-core/tests/test_gate_result.py -q`
Expected: 8 passed.

- [ ] **Step 5: Commit**

```bash
git add plugins/kdev-core/kdev_core/gate.py plugins/kdev-core/tests/test_gate_result.py
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-core): R3 make_gate_result — structured verdict + validation (P3 Task1)"
```

---

## Task 2: `record_gate` — review/acceptance dispatch + escalate + double counters

**Files:**
- Create: `plugins/kdev-core/tests/test_record_gate.py`
- Modify: `plugins/kdev-core/kdev_core/gate.py` (append `record_gate`)

- [ ] **Step 1: Write the failing test module**

Create `plugins/kdev-core/tests/test_record_gate.py`:

```python
"""Tests for kdev_core.gate.record_gate — review/acceptance dispatch + escalate + counters."""
import pytest

from kdev_core.node_machine import load_node_table
from kdev_core.gate import make_gate_result, record_gate, GateError

# A flow where g-code (review) sits at node "g1": PASS -> n2, reflow -> n1.
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
    assert out["history"][-1]["verdict"] == "PASS"   # GateResult recorded in R1 history
    assert out["gate_calls"] == 1


def test_review_fail_within_cap_reflows():
    r = make_gate_result("g-code", "review", node="g1", verdict="FAIL", request_id="r1")
    out = record_gate(_state(), r, table=TABLE, gate_specs=SPECS)
    assert out["current_node"] == "n1"                # reflow to the action
    assert out["gate_iters"]["g-code"] == 1
    assert out["status"] == "in_progress"


def test_review_fail_at_cap_escalates_without_force_accept():
    # max_retries=2; pre-load iter=1, this FAIL makes it 2 (>= 2) -> escalate.
    st = _state()
    st["gate_iters"] = {"g-code": 1}
    r = make_gate_result("g-code", "review", node="g1", verdict="FAIL", request_id="r1")
    out = record_gate(st, r, table=TABLE, gate_specs=SPECS)
    assert out["status"] == "blocked"                 # escalate
    assert out["current_node"] == "g1"                # did NOT advance (no force-accept)
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
```

- [ ] **Step 2: Run to verify they fail**

Run: `python3 -m pytest plugins/kdev-core/tests/test_record_gate.py -q`
Expected: FAIL — `ImportError: cannot import name 'record_gate'`.

- [ ] **Step 3: Append the implementation**

Append to `plugins/kdev-core/kdev_core/gate.py`:

```python
def record_gate(state, gate_result, *, table, gate_specs, max_retries=None):
    """Record a GateResult and apply the resulting transition. Pure (state -> new state).

    Appends the GateResult to state["history"] (R1's field), bumps the double counters
    (per-gate gate_iters + flow-total gate_calls), then dispatches by the gate's kind:
      review/acceptance: PASS -> advance(on_pass) + reset iter; FAIL within cap ->
        advance(on_reflow); FAIL at/over cap -> escalate (status="blocked", no advance).
      decision: advance(branches[verdict]).
    advance() is always called with reflow=False — R3 owns the review bound via gate_iters,
    distinct from R2's mechanical reflow->terminal_fail.
    """
    gid = gate_result["gate"]
    spec = gate_specs.get(gid)
    if spec is None:
        raise GateError(f"no gate spec for gate {gid!r}")
    kind = spec["kind"]
    cap = max_retries if max_retries is not None else table["max_retries"]

    new = dict(state)
    new["history"] = [*state.get("history", []), gate_result]
    new["gate_calls"] = state.get("gate_calls", 0) + 1
    gate_iters = dict(state.get("gate_iters", {}))

    verdict = gate_result["verdict"]

    if kind in ("review", "acceptance"):
        if verdict == "PASS":
            gate_iters[gid] = 0
            new["gate_iters"] = gate_iters
            return advance(new, spec["on_pass"], table=table, reason=f"{gid} PASS")
        if verdict == "FAIL":
            gate_iters[gid] = gate_iters.get(gid, 0) + 1
            new["gate_iters"] = gate_iters
            if gate_iters[gid] >= cap:
                new["status"] = "blocked"
                new["blocked_reason"] = (
                    f"{gid} failed {gate_iters[gid]}x (>= {cap}); escalate to human"
                )
                return new
            return advance(new, spec["on_reflow"], table=table,
                           reason=f"{gid} FAIL reflow#{gate_iters[gid]}")
        raise GateError(f"{kind} verdict must be PASS/FAIL, got {verdict!r}")

    if kind == "decision":
        branches = spec.get("branches", {})
        if verdict not in branches:
            raise GateError(f"decision {gid!r} verdict {verdict!r} not in branches {sorted(branches)}")
        new["gate_iters"] = gate_iters
        return advance(new, branches[verdict], table=table, reason=f"{gid} decision={verdict}")

    raise GateError(f"unknown gate kind {kind!r} for gate {gid!r}")
```

- [ ] **Step 4: Run to verify they pass**

Run: `python3 -m pytest plugins/kdev-core/tests/test_record_gate.py -q`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add plugins/kdev-core/kdev_core/gate.py plugins/kdev-core/tests/test_record_gate.py
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-core): R3 record_gate review/acceptance + escalate + double counters (P3 Task2)"
```

---

## Task 3: `record_gate` decision branch

**Files:**
- Modify: `plugins/kdev-core/tests/test_record_gate.py` (append decision tests)

(The `record_gate` implementation from Task 2 already handles `decision`; this task adds its tests + the spec-validation tests.)

- [ ] **Step 1: Append the decision tests**

Append to `plugins/kdev-core/tests/test_record_gate.py`:

```python
# A decision gate at "d1": branches choose between two actions.
DTABLE = load_node_table({
    "flow": "toy2",
    "nodes": [
        {"id": "start", "kind": "action", "next": ["d1"]},
        {"id": "d1", "kind": "gate", "next": ["go", "plan"]},
        {"id": "go", "kind": "action", "next": ["end"]},
        {"id": "plan", "kind": "action", "next": ["d1"]},
        {"id": "end", "kind": "terminal", "next": []},
    ],
})
DSPECS = {"d1": {"kind": "decision", "branches": {"approve": "go", "rework": "plan"}}}


def _dstate():
    return {"current_node": "d1", "status": "in_progress", "history": [], "phase_history": []}


def test_decision_advances_to_chosen_branch():
    r = make_gate_result("d1", "decision", node="d1", verdict="approve", request_id="r1")
    out = record_gate(_dstate(), r, table=DTABLE, gate_specs=DSPECS)
    assert out["current_node"] == "go"
    assert out["gate_calls"] == 1
    assert out["history"][-1]["verdict"] == "approve"


def test_decision_other_branch():
    r = make_gate_result("d1", "decision", node="d1", verdict="rework", request_id="r1")
    out = record_gate(_dstate(), r, table=DTABLE, gate_specs=DSPECS)
    assert out["current_node"] == "plan"


def test_decision_unknown_verdict_raises():
    r = make_gate_result("d1", "decision", node="d1", verdict="ship-it", request_id="r1")
    with pytest.raises(GateError, match="not in branches"):
        record_gate(_dstate(), r, table=DTABLE, gate_specs=DSPECS)
```

- [ ] **Step 2: Run to verify the new tests pass**

Run: `python3 -m pytest plugins/kdev-core/tests/test_record_gate.py -q`
Expected: 9 passed (6 from Task 2 + 3 decision). (The decision logic already exists from Task 2, so these tests pass immediately — they are the decision-branch coverage.)

- [ ] **Step 3: Commit**

```bash
git add plugins/kdev-core/tests/test_record_gate.py
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "test(kdev-core): R3 record_gate decision-branch coverage (P3 Task3)"
```

---

## Task 4: `record_gate_persist` + full gate-loop integration smoke

**Files:**
- Modify: `plugins/kdev-core/kdev_core/gate.py` (append `record_gate_persist`)
- Create: `plugins/kdev-core/tests/test_gate_smoke.py`

- [ ] **Step 1: Write the failing integration test**

Create `plugins/kdev-core/tests/test_gate_smoke.py`:

```python
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
    # init at the gate node so we can record a gate verdict immediately.
    init_state(tmp, FLOW, slug, display_name="X", initial_node="g-code")


def test_fail_then_pass_persisted(tmp_workspace):
    _seed(tmp_workspace, "auth")
    r_fail = make_gate_result("g-code", "review", node="g-code", verdict="FAIL", request_id="r1")
    st = record_gate_persist(tmp_workspace, FLOW, "auth", r_fail, table=TABLE, gate_specs=SPECS)
    assert st["current_node"] == "n-tdd"           # reflowed to redo
    assert st["gate_iters"]["g-code"] == 1
    assert st["status"] == "in_progress"

    # flow goes n-tdd -> g-code again, then PASS
    from kdev_core.node_machine import advance_persist
    advance_persist(tmp_workspace, FLOW, "auth", "g-code", table=TABLE)
    r_pass = make_gate_result("g-code", "review", node="g-code", verdict="PASS", request_id="r2")
    final = record_gate_persist(tmp_workspace, FLOW, "auth", r_pass, table=TABLE, gate_specs=SPECS)
    assert final["current_node"] == "n-ship"
    assert final["gate_iters"]["g-code"] == 0      # reset on PASS
    assert len(final["history"]) == 2              # two GateResults persisted
    assert final["gate_calls"] == 2


def test_escalate_persisted(tmp_workspace):
    _seed(tmp_workspace, "auth2")
    # two FAILs at max_retries=2 -> second escalates to blocked.
    r1 = make_gate_result("g-code", "review", node="g-code", verdict="FAIL", request_id="r1")
    record_gate_persist(tmp_workspace, FLOW, "auth2", r1, table=TABLE, gate_specs=SPECS)
    from kdev_core.node_machine import advance_persist
    advance_persist(tmp_workspace, FLOW, "auth2", "g-code", table=TABLE)
    r2 = make_gate_result("g-code", "review", node="g-code", verdict="FAIL", request_id="r2")
    final = record_gate_persist(tmp_workspace, FLOW, "auth2", r2, table=TABLE, gate_specs=SPECS)
    assert final["status"] == "blocked"
    assert final["current_node"] == "g-code"       # not advanced (no force-accept)
    assert final["gate_iters"]["g-code"] == 2
```

- [ ] **Step 2: Run to verify it fails**

Run: `python3 -m pytest plugins/kdev-core/tests/test_gate_smoke.py -q`
Expected: FAIL — `ImportError: cannot import name 'record_gate_persist'`.

- [ ] **Step 3: Append `record_gate_persist`**

Append to `plugins/kdev-core/kdev_core/gate.py`:

```python
def record_gate_persist(workspace, flow, slug, gate_result, *, table, gate_specs,
                        max_retries=None, step_id=None):
    """record_gate() + persist via R1 flow_state.write_state. Returns the persisted state."""
    from kdev_core import flow_state

    state = flow_state.read_state(workspace, flow, slug)
    new_state = record_gate(state, gate_result, table=table, gate_specs=gate_specs,
                            max_retries=max_retries)
    flow_state.write_state(workspace, flow, slug, new_state, step_id=step_id)
    return flow_state.read_state(workspace, flow, slug)
```

- [ ] **Step 4: Run the smoke + full suite**

Run: `python3 -m pytest plugins/kdev-core/tests/test_gate_smoke.py -q`  → expect 2 passed.

Run: `python3 -m pytest plugins/kdev-core/tests -q`  → expect **66** (47 from R1+R2 + R3 19: gate_result 8 + record_gate 9 + gate_smoke 2).

- [ ] **Step 5: Commit**

```bash
git add plugins/kdev-core/kdev_core/gate.py plugins/kdev-core/tests/test_gate_smoke.py
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-core): R3 record_gate_persist + full gate-loop integration smoke (P3 Task4)"
```

---

## Done criteria

- `python3 -m pytest plugins/kdev-core/tests -q` → all green (R1+R2 47 + R3 19 = **66**).
- `gate.py` exposes: `make_gate_result`, `record_gate`, `record_gate_persist`, `GateError`, `GATE_KINDS`, `GATE_VERDICTS`.
- GateResult is structured (`gate/kind/node/request_id/iter/verdict/by/issues/revisions/ts`); validation rejects bad kind / empty request_id / non-PASS/FAIL review-acceptance verdict.
- `record_gate` is pure; appends to R1's `history` (never `phase_history`); maintains double counters (`gate_iters` + `gate_calls`); review/acceptance PASS→on_pass(+reset), FAIL<cap→on_reflow, FAIL≥cap→escalate `status="blocked"` with NO advance and NO force-accept; decision→`branches[verdict]`; unknown gate/verdict raise `GateError`.
- R2 `node_machine.py` is unmodified (gate semantics via `gate_specs`; targets validated by adjacency).
- `record_gate_persist` round-trips through R1's atomic write.

> **Tally note:** Done-criteria says 66 (47 + 8 + 9 + 2). Task 4 Step 4's draft "72" is a loose estimate — the authoritative expected total is **66**; trust the run output.

**Next:** 阶段0 core (R1+R2+R3) complete → P4 (git 托管, kdev-memory self-bootstrap), then 阶段1 (coding-flow refit onto kdev-core + first dogfood). R3's `gate_specs` + `record_gate` map directly onto coding-flow's Gate-A/B/C (decision/review) + E2E (acceptance).
</content>
