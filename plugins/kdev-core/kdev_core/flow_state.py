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
