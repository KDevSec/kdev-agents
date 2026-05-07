"""flow-state.json read/write/init for kdev-design-flow.

State schema (v0.1):
{
    "slug": str,                    # feature slug (filesystem-safe)
    "feature_name": str,            # original user-provided name (for display)
    "review_mode": "ai"|"both"|"human",
    "current_stage": int,           # 1..4
    "current_iter": int,            # 1..3 within current stage
    "status": "in_progress"|"completed"|"aborted",
    "created_at": str (ISO-8601),
    "updated_at": str (ISO-8601),
    "history": list[dict],          # gate decisions; each {"stage": int, "iter": int, "verdict": "PASS"|"FAIL", "reviewer": str}
}
"""
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

VALID_REVIEW_MODES = {"ai", "both", "human"}


class FlowStateError(Exception):
    """Raised when flow-state.json is missing, corrupt, or in an invalid transition."""


def _state_path(workspace: Path, slug: str) -> Path:
    return workspace / ".kdev" / "design-flow" / slug / "flow-state.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def init_state(workspace: Path, slug: str, *, review_mode: str, feature_name: str) -> dict:
    if review_mode not in VALID_REVIEW_MODES:
        raise ValueError(f"review_mode must be one of {sorted(VALID_REVIEW_MODES)}, got {review_mode!r}")

    path = _state_path(workspace, slug)
    if path.exists():
        raise FlowStateError(f"flow-state.json already exists for slug {slug!r}; use --resume or pick a different name")

    path.parent.mkdir(parents=True, exist_ok=True)
    state = {
        "slug": slug,
        "feature_name": feature_name,
        "review_mode": review_mode,
        "current_stage": 1,
        "current_iter": 1,
        "status": "in_progress",
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "history": [],
    }
    write_state(workspace, slug, state)
    return state


def read_state(workspace: Path, slug: str) -> dict:
    path = _state_path(workspace, slug)
    if not path.exists():
        raise FlowStateError(f"no flow-state.json at {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise FlowStateError(f"corrupt flow-state.json at {path}: {exc}") from exc


def write_state(workspace: Path, slug: str, state: dict) -> None:
    path = _state_path(workspace, slug)
    path.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = _now_iso()

    # Atomic write: write to .tmp in same dir, then rename
    fd, tmp_path = tempfile.mkstemp(prefix=".flow-state-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise
