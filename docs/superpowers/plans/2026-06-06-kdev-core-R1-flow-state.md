# kdev-core R1 (flow-state store) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build kdev-core's R1 layer — a generalized, multi-flow `flow-state.json` store (init / read / write / resume) with atomic writes and an `active` / `_meta` stale-guard — by generalizing the kdev-design-flow golden seed.

**Architecture:** A single stdlib-only Python module `kdev_core/flow_state.py` exposes pure functions (no classes) that persist one JSON state file per flow-run at `.kdev/flows/<flow>/<slug>/flow-state.json`. Writes go through `tempfile` + `os.replace` (atomic). `_meta` (written_at, step_id) is injected on write and stripped on read — it is write-side plumbing, not logical state. R2 (node machine) and R3 (gates) will build on this store in later plans; R1 only stores `current_node` and a `history` list, it does not validate transitions or gate verdicts.

**Tech Stack:** Python 3 (stdlib only: `json`, `os`, `tempfile`, `pathlib`, `datetime`), pytest.

**Source of truth:**
- Golden seed (generalize from): [plugins/kdev-design-flow/lib/flow_state.py](../../../plugins/kdev-design-flow/lib/flow_state.py) + [its tests](../../../plugins/kdev-design-flow/tests/test_flow_state.py)
- Target schema: [底座设计总纲 §4.1](../../framework/01-design/2026-06-05-01-kdev-core底座设计总纲-v1.0.md)
- Roadmap context: [起步 roadmap §3.1 阶段0](../../framework/01-design/2026-06-06-01-数字员工集群-起步roadmap-Q004细化-v0.1.md)

**Acceptance (maps to roadmap §4.3 #1 + §3.1 R1):** atomic write (no `.tmp` leftover) · corrupt-file recovery raises cleanly · resume returns last `current_node` (not from scratch) · multi-flow path isolation.

---

## File Structure

| File | Responsibility |
|---|---|
| `plugins/kdev-core/kdev_core/__init__.py` | package marker (empty) |
| `plugins/kdev-core/kdev_core/flow_state.py` | the R1 store: `init_state` / `read_state` / `write_state` / `mark_inactive` / `resume_state` + `FlowStateError` |
| `plugins/kdev-core/tests/__init__.py` | package marker (empty) |
| `plugins/kdev-core/tests/conftest.py` | `sys.path` insert + `tmp_workspace` fixture |
| `plugins/kdev-core/tests/test_flow_state.py` | store CRUD + schema + atomic + `_meta` tests |
| `plugins/kdev-core/tests/test_flow_lifecycle.py` | `mark_inactive` + `resume_state` tests |
| `plugins/kdev-core/tests/test_smoke_lifecycle.py` | full-lifecycle + resume-after-interrupt integration smoke |

> `plugin.json` / skills / hooks for kdev-core are **out of scope for R1** (added when kdev-core grows a runtime surface). P1 is the Python lib + tests only.

Tests run from repo root via: `python -m pytest plugins/kdev-core/tests -q` (the `conftest.py` puts `plugins/kdev-core` on `sys.path` so `import kdev_core` resolves).

---

## Task 1: Scaffold kdev-core package + test harness

**Files:**
- Create: `plugins/kdev-core/kdev_core/__init__.py`
- Create: `plugins/kdev-core/tests/__init__.py`
- Create: `plugins/kdev-core/tests/conftest.py`

- [ ] **Step 1: Create the package marker files (empty)**

Create `plugins/kdev-core/kdev_core/__init__.py` with no content (empty file).
Create `plugins/kdev-core/tests/__init__.py` with no content (empty file).

- [ ] **Step 2: Create the test harness `conftest.py`**

Create `plugins/kdev-core/tests/conftest.py`:

```python
import sys
from pathlib import Path

import pytest

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PLUGIN_ROOT))


@pytest.fixture
def tmp_workspace(tmp_path: Path) -> Path:
    """Temp dir simulating a project workspace.

    `.kdev/flows/<flow>/<slug>/` is created on demand by the code under test.
    """
    return tmp_path
```

- [ ] **Step 3: Verify the package imports**

Run: `PYTHONPATH=plugins/kdev-core python -c "import kdev_core; print('pkg ok')"`
Expected: prints `pkg ok` (exit 0).

- [ ] **Step 4: Commit**

```bash
git add plugins/kdev-core/kdev_core/__init__.py plugins/kdev-core/tests/__init__.py plugins/kdev-core/tests/conftest.py
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-core): scaffold package + pytest harness (R1 P1 Task1)"
```

> Note: commits MUST use the AI-identity override (`-c user.name=ly-AI -c user.email=ly1989abc@126.com`, **no quotes** on the `-c key=value`) — the `block-unattributed-commit` hook hard-rejects otherwise.

---

## Task 2: flow-state store — init / read / write + schema + atomic + `_meta`

**Files:**
- Create: `plugins/kdev-core/tests/test_flow_state.py`
- Create: `plugins/kdev-core/kdev_core/flow_state.py`

- [ ] **Step 1: Write the failing test module**

Create `plugins/kdev-core/tests/test_flow_state.py`:

```python
"""Tests for kdev_core.flow_state — R1 flow-state store (CRUD + schema + atomic + _meta)."""
import json
from pathlib import Path

import pytest

from kdev_core.flow_state import init_state, read_state, write_state, FlowStateError

FLOW = "coding-flow"


def _state_file(ws: Path, flow: str, slug: str) -> Path:
    return ws / ".kdev" / "flows" / flow / slug / "flow-state.json"


def test_init_creates_file_with_schema(tmp_workspace):
    st = init_state(tmp_workspace, FLOW, "feat-x", display_name="Feat X")
    assert _state_file(tmp_workspace, FLOW, "feat-x").exists()
    assert st["flow"] == FLOW
    assert st["slug"] == "feat-x"
    assert st["display_name"] == "Feat X"
    assert st["status"] == "in_progress"
    assert st["active"] is True
    assert st["current_node"] is None
    assert st["config"] == {"review_mode": "ai", "auto_mode": False}
    assert st["history"] == []
    assert "created_at" in st and "updated_at" in st


def test_init_with_initial_node_and_config(tmp_workspace):
    st = init_state(tmp_workspace, FLOW, "feat-y", display_name="Y",
                    review_mode="both", auto_mode=True, initial_node="n0-env")
    assert st["current_node"] == "n0-env"
    assert st["config"] == {"review_mode": "both", "auto_mode": True}


def test_read_returns_logical_state_without_meta(tmp_workspace):
    init_state(tmp_workspace, FLOW, "feat-x", display_name="X")
    st = read_state(tmp_workspace, FLOW, "feat-x")
    assert st["slug"] == "feat-x"
    assert "_meta" not in st  # _meta is write-side plumbing, stripped on read


def test_meta_persisted_on_disk(tmp_workspace):
    init_state(tmp_workspace, FLOW, "feat-x", display_name="X")
    raw = json.loads(_state_file(tmp_workspace, FLOW, "feat-x").read_text(encoding="utf-8"))
    assert "_meta" in raw and "written_at" in raw["_meta"]


def test_write_injects_step_id_into_meta(tmp_workspace):
    init_state(tmp_workspace, FLOW, "feat-x", display_name="X")
    st = read_state(tmp_workspace, FLOW, "feat-x")
    write_state(tmp_workspace, FLOW, "feat-x", st, step_id="Step main-99")
    raw = json.loads(_state_file(tmp_workspace, FLOW, "feat-x").read_text(encoding="utf-8"))
    assert raw["_meta"]["step_id"] == "Step main-99"


def test_write_overwrites_current_node(tmp_workspace):
    init_state(tmp_workspace, FLOW, "feat-x", display_name="X")
    st = read_state(tmp_workspace, FLOW, "feat-x")
    st["current_node"] = "n3-tdd"
    write_state(tmp_workspace, FLOW, "feat-x", st)
    assert read_state(tmp_workspace, FLOW, "feat-x")["current_node"] == "n3-tdd"


def test_write_is_atomic_no_tmp_leftover(tmp_workspace):
    init_state(tmp_workspace, FLOW, "feat-x", display_name="X")
    st = read_state(tmp_workspace, FLOW, "feat-x")
    st["current_node"] = "n2"
    write_state(tmp_workspace, FLOW, "feat-x", st)
    state_dir = _state_file(tmp_workspace, FLOW, "feat-x").parent
    assert list(state_dir.glob("*.tmp")) == []


def test_read_missing_raises(tmp_workspace):
    with pytest.raises(FlowStateError, match="no flow-state.json"):
        read_state(tmp_workspace, FLOW, "ghost")


def test_read_corrupt_raises(tmp_workspace):
    init_state(tmp_workspace, FLOW, "feat-x", display_name="X")
    _state_file(tmp_workspace, FLOW, "feat-x").write_text("{ not json", encoding="utf-8")
    with pytest.raises(FlowStateError, match="corrupt"):
        read_state(tmp_workspace, FLOW, "feat-x")


def test_init_refuses_overwrite(tmp_workspace):
    init_state(tmp_workspace, FLOW, "feat-x", display_name="X")
    with pytest.raises(FlowStateError, match="already exists"):
        init_state(tmp_workspace, FLOW, "feat-x", display_name="X")


def test_invalid_review_mode_raises(tmp_workspace):
    with pytest.raises(ValueError, match="review_mode"):
        init_state(tmp_workspace, FLOW, "feat-x", display_name="X", review_mode="psychic")


def test_two_flows_same_slug_isolated(tmp_workspace):
    init_state(tmp_workspace, "coding-flow", "feat-x", display_name="X")
    init_state(tmp_workspace, "design-flow", "feat-x", display_name="X")
    assert read_state(tmp_workspace, "coding-flow", "feat-x")["flow"] == "coding-flow"
    assert read_state(tmp_workspace, "design-flow", "feat-x")["flow"] == "design-flow"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest plugins/kdev-core/tests/test_flow_state.py -q`
Expected: collection/import error — `ModuleNotFoundError: No module named 'kdev_core.flow_state'` (module not created yet).

- [ ] **Step 3: Write the implementation**

Create `plugins/kdev-core/kdev_core/flow_state.py`:

```python
"""kdev-core R1 — flow-state.json store (init / read / write / resume).

Generalized from the kdev-design-flow golden seed
(plugins/kdev-design-flow/lib/flow_state.py):
- path generalized to .kdev/flows/<flow>/<slug>/flow-state.json (multi-flow)
- schema generalized to node-based (current_node) + config + active/_meta stale guard
- atomic write preserved (tempfile + os.replace)

State schema (as returned by read_state, with _meta stripped):
{
    "flow": str,                    # flow id, e.g. "coding-flow"
    "slug": str,                    # feature slug (filesystem-safe)
    "display_name": str,            # original human-provided name
    "status": "in_progress"|"completed"|"aborted",
    "active": bool,                 # [OMC] stale guard: True while running/crashed,
                                    #       False once cleanly stopped
    "current_node": str | None,     # node id (R2 advances it); None until first advance
    "created_at": str,              # ISO-8601
    "updated_at": str,              # ISO-8601, refreshed each write
    "config": {"review_mode": "ai"|"both"|"human", "auto_mode": bool},
    "history": list[dict],          # GateResult entries (R3 appends; R1 only stores)
}

On disk an extra "_meta": {"written_at": str, "step_id": str|None} is injected on
write and stripped on read — write-side plumbing, not part of the logical state.
"""
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

VALID_REVIEW_MODES = {"ai", "both", "human"}


class FlowStateError(Exception):
    """Raised when flow-state.json is missing, corrupt, or in an invalid state."""


def _state_path(workspace: Path, flow: str, slug: str) -> Path:
    return Path(workspace) / ".kdev" / "flows" / flow / slug / "flow-state.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def init_state(workspace, flow, slug, *, display_name,
               review_mode="ai", auto_mode=False, initial_node=None):
    if review_mode not in VALID_REVIEW_MODES:
        raise ValueError(
            f"review_mode must be one of {sorted(VALID_REVIEW_MODES)}, got {review_mode!r}"
        )
    path = _state_path(workspace, flow, slug)
    if path.exists():
        raise FlowStateError(
            f"flow-state.json already exists for {flow}/{slug!r}; resume or pick a different slug"
        )
    state = {
        "flow": flow,
        "slug": slug,
        "display_name": display_name,
        "status": "in_progress",
        "active": True,
        "current_node": initial_node,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "config": {"review_mode": review_mode, "auto_mode": auto_mode},
        "history": [],
    }
    write_state(workspace, flow, slug, state)
    return read_state(workspace, flow, slug)


def read_state(workspace, flow, slug):
    path = _state_path(workspace, flow, slug)
    if not path.exists():
        raise FlowStateError(f"no flow-state.json at {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise FlowStateError(f"corrupt flow-state.json at {path}: {exc}") from exc
    data.pop("_meta", None)  # write-side plumbing, not logical state
    return data


def write_state(workspace, flow, slug, state, *, step_id=None):
    path = _state_path(workspace, flow, slug)
    path.parent.mkdir(parents=True, exist_ok=True)

    to_write = {k: v for k, v in state.items() if k != "_meta"}
    to_write["updated_at"] = _now_iso()
    to_write["_meta"] = {"written_at": _now_iso(), "step_id": step_id}

    # Atomic write: tempfile in same dir, then os.replace (rename is atomic on POSIX).
    fd, tmp_path = tempfile.mkstemp(prefix=".flow-state-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(to_write, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest plugins/kdev-core/tests/test_flow_state.py -q`
Expected: all tests PASS (12 passed).

- [ ] **Step 5: Commit**

```bash
git add plugins/kdev-core/kdev_core/flow_state.py plugins/kdev-core/tests/test_flow_state.py
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-core): R1 flow-state store init/read/write + atomic + _meta (P1 Task2)"
```

---

## Task 3: lifecycle ops — `mark_inactive` + `resume_state`

**Files:**
- Create: `plugins/kdev-core/tests/test_flow_lifecycle.py`
- Modify: `plugins/kdev-core/kdev_core/flow_state.py` (append two functions)

- [ ] **Step 1: Write the failing test module**

Create `plugins/kdev-core/tests/test_flow_lifecycle.py`:

```python
"""Tests for flow lifecycle ops — mark_inactive + resume_state."""
import pytest

from kdev_core.flow_state import (
    init_state, mark_inactive, resume_state, FlowStateError,
)

FLOW = "coding-flow"


def test_mark_inactive_defaults_to_aborted(tmp_workspace):
    init_state(tmp_workspace, FLOW, "f", display_name="F")
    st = mark_inactive(tmp_workspace, FLOW, "f")
    assert st["active"] is False
    assert st["status"] == "aborted"


def test_mark_inactive_completed(tmp_workspace):
    init_state(tmp_workspace, FLOW, "f", display_name="F")
    st = mark_inactive(tmp_workspace, FLOW, "f", status="completed")
    assert st["active"] is False
    assert st["status"] == "completed"


def test_mark_inactive_rejects_bad_status(tmp_workspace):
    init_state(tmp_workspace, FLOW, "f", display_name="F")
    with pytest.raises(ValueError, match="completed.*aborted"):
        mark_inactive(tmp_workspace, FLOW, "f", status="in_progress")


def test_resume_in_progress_returns_state(tmp_workspace):
    init_state(tmp_workspace, FLOW, "f", display_name="F", initial_node="n1")
    st = resume_state(tmp_workspace, FLOW, "f")
    assert st["status"] == "in_progress"
    assert st["current_node"] == "n1"


def test_resume_completed_raises(tmp_workspace):
    init_state(tmp_workspace, FLOW, "f", display_name="F")
    mark_inactive(tmp_workspace, FLOW, "f", status="completed")
    with pytest.raises(FlowStateError, match="not resumable"):
        resume_state(tmp_workspace, FLOW, "f")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest plugins/kdev-core/tests/test_flow_lifecycle.py -q`
Expected: FAIL — `ImportError: cannot import name 'mark_inactive'` (and `resume_state`).

- [ ] **Step 3: Append the implementation**

Append to `plugins/kdev-core/kdev_core/flow_state.py` (after `write_state`):

```python
def mark_inactive(workspace, flow, slug, *, status="aborted", step_id=None):
    """Cleanly stop a flow: active=False + terminal status (completed | aborted)."""
    if status not in {"completed", "aborted"}:
        raise ValueError(
            f"mark_inactive status must be 'completed' or 'aborted', got {status!r}"
        )
    state = read_state(workspace, flow, slug)
    state["active"] = False
    state["status"] = status
    write_state(workspace, flow, slug, state, step_id=step_id)
    return read_state(workspace, flow, slug)


def resume_state(workspace, flow, slug):
    """Return the state if it is resumable (status == in_progress), else raise.

    A left-behind in_progress state (active still True after a crash) is exactly
    the resumable case — the caller picks up at `current_node`.
    """
    state = read_state(workspace, flow, slug)
    if state["status"] != "in_progress":
        raise FlowStateError(
            f"flow {flow}/{slug!r} not resumable: status={state['status']!r}"
        )
    return state
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest plugins/kdev-core/tests/test_flow_lifecycle.py -q`
Expected: all tests PASS (5 passed).

- [ ] **Step 5: Commit**

```bash
git add plugins/kdev-core/kdev_core/flow_state.py plugins/kdev-core/tests/test_flow_lifecycle.py
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-core): R1 lifecycle mark_inactive + resume_state (P1 Task3)"
```

---

## Task 4: integration smoke — full lifecycle + resume-after-interrupt

**Files:**
- Create: `plugins/kdev-core/tests/test_smoke_lifecycle.py`

- [ ] **Step 1: Write the failing smoke test**

Create `plugins/kdev-core/tests/test_smoke_lifecycle.py`:

```python
"""Integration smoke — full flow lifecycle + resume-after-interrupt.

Mirrors the X3 spike smoke pattern (full lifecycle + resume after a simulated
interrupt). Validates roadmap §4.3 #1: R1 truly drives state and resume picks
up at the last node, not from scratch.
"""
from kdev_core.flow_state import (
    init_state, read_state, write_state, mark_inactive, resume_state,
)

FLOW = "coding-flow"


def test_full_lifecycle(tmp_workspace):
    init_state(tmp_workspace, FLOW, "auth", display_name="Auth", initial_node="n0-env")
    for node in ["n1-plan", "n2-tdd", "n3-e2e"]:
        st = read_state(tmp_workspace, FLOW, "auth")
        st["current_node"] = node
        write_state(tmp_workspace, FLOW, "auth", st)
    assert read_state(tmp_workspace, FLOW, "auth")["current_node"] == "n3-e2e"

    done = mark_inactive(tmp_workspace, FLOW, "auth", status="completed")
    assert done["status"] == "completed"
    assert done["active"] is False


def test_resume_after_interrupt(tmp_workspace):
    # A run advances to n2 then the process dies (no mark_inactive called).
    init_state(tmp_workspace, FLOW, "auth", display_name="Auth", initial_node="n0-env")
    st = read_state(tmp_workspace, FLOW, "auth")
    st["current_node"] = "n2-tdd"
    write_state(tmp_workspace, FLOW, "auth", st)

    # A "new session" resumes: still in_progress + active True -> resumable at n2.
    resumed = resume_state(tmp_workspace, FLOW, "auth")
    assert resumed["status"] == "in_progress"
    assert resumed["active"] is True
    assert resumed["current_node"] == "n2-tdd"  # NOT reset to n0
```

- [ ] **Step 2: Run the smoke test to verify it passes**

Run: `python -m pytest plugins/kdev-core/tests/test_smoke_lifecycle.py -q`
Expected: all tests PASS (2 passed). (Both functions already exist from Tasks 2-3, so this test should pass immediately — it is an integration guard, not new behavior.)

- [ ] **Step 3: Run the full kdev-core suite**

Run: `python -m pytest plugins/kdev-core/tests -q`
Expected: all tests PASS (19 passed: 12 store + 5 lifecycle + 2 smoke).

- [ ] **Step 4: Commit**

```bash
git add plugins/kdev-core/tests/test_smoke_lifecycle.py
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "test(kdev-core): R1 integration smoke — lifecycle + resume-after-interrupt (P1 Task4)"
```

---

## Done criteria

- `python -m pytest plugins/kdev-core/tests -q` → all green (19 tests).
- `flow_state.py` exposes: `init_state`, `read_state`, `write_state`, `mark_inactive`, `resume_state`, `FlowStateError`, `VALID_REVIEW_MODES`.
- Atomic write verified (no `.tmp` leftover) · corrupt recovery raises `FlowStateError` · resume returns last `current_node` · multi-flow paths isolated.

**Next plan (after P1 executes):** P2 — R2 node machine (`node-table` loader + `advance` adjacency/guard), building on this store's `write_state` to persist `current_node` + `history`.
</content>
