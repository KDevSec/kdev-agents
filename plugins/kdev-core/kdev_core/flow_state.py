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


def unblock_state(workspace, flow, slug, *, to_node):
    """Clear a blocked flow: reset status to in_progress, clear blocked_reason,
    and optionally move current_node to to_node. Returns the updated state."""
    state = read_state(workspace, flow, slug)
    if state["status"] != "blocked":
        raise FlowStateError(
            f"flow {flow}/{slug!r} is not blocked (status={state['status']!r})"
        )
    state["status"] = "in_progress"
    state["blocked_reason"] = None
    if to_node is not None:
        state["current_node"] = to_node
    write_state(workspace, flow, slug, state)
    return read_state(workspace, flow, slug)


def list_flows(workspace):
    """List all flows in the workspace's .kdev/flows/ directory.

    Returns a list of dicts: {flow, slug, status, active, current_node}.
    """
    flows_dir = Path(workspace) / ".kdev" / "flows"
    if not flows_dir.exists():
        return []
    result = []
    for flow_dir in sorted(flows_dir.iterdir()):
        if not flow_dir.is_dir():
            continue
        for slug_dir in sorted(flow_dir.iterdir()):
            state_path = slug_dir / "flow-state.json"
            if not state_path.exists():
                continue
            try:
                data = json.loads(state_path.read_text(encoding="utf-8"))
                data.pop("_meta", None)
                result.append({
                    "flow": data.get("flow"),
                    "slug": data.get("slug"),
                    "status": data.get("status"),
                    "active": data.get("active"),
                    "current_node": data.get("current_node"),
                })
            except (json.JSONDecodeError, KeyError):
                continue  # skip corrupt files
    return result
