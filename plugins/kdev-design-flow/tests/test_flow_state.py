"""Tests for lib.flow_state — flow-state.json read/write/recovery."""
import json
from pathlib import Path

import pytest

from lib.flow_state import init_state, read_state, write_state, FlowStateError


def _state_dir(workspace: Path, slug: str) -> Path:
    return workspace / ".kdev" / "design-flow" / slug


def test_init_state_creates_directory_and_file(tmp_workspace):
    init_state(tmp_workspace, "feat-x", review_mode="ai", feature_name="Feat X")

    f = _state_dir(tmp_workspace, "feat-x") / "flow-state.json"
    assert f.exists()
    data = json.loads(f.read_text(encoding="utf-8"))
    assert data["slug"] == "feat-x"
    assert data["feature_name"] == "Feat X"
    assert data["review_mode"] == "ai"
    assert data["current_stage"] == 1
    assert data["current_iter"] == 1
    assert data["status"] == "in_progress"
    assert "created_at" in data


def test_read_state_returns_dict(tmp_workspace):
    init_state(tmp_workspace, "feat-x", review_mode="ai", feature_name="Feat X")
    state = read_state(tmp_workspace, "feat-x")
    assert state["slug"] == "feat-x"


def test_read_state_missing_raises(tmp_workspace):
    with pytest.raises(FlowStateError, match="no flow-state.json"):
        read_state(tmp_workspace, "does-not-exist")


def test_write_state_overwrites(tmp_workspace):
    init_state(tmp_workspace, "feat-x", review_mode="ai", feature_name="Feat X")
    state = read_state(tmp_workspace, "feat-x")
    state["current_stage"] = 3
    write_state(tmp_workspace, "feat-x", state)

    again = read_state(tmp_workspace, "feat-x")
    assert again["current_stage"] == 3


def test_write_state_atomic_via_tempfile(tmp_workspace):
    """Writes go through tempfile + rename, so partial writes can't corrupt."""
    init_state(tmp_workspace, "feat-x", review_mode="ai", feature_name="Feat X")
    state = read_state(tmp_workspace, "feat-x")
    state["current_stage"] = 2
    write_state(tmp_workspace, "feat-x", state)

    # No leftover .tmp files
    state_dir = _state_dir(tmp_workspace, "feat-x")
    leftover = list(state_dir.glob("*.tmp"))
    assert leftover == []


def test_read_corrupt_state_raises(tmp_workspace):
    init_state(tmp_workspace, "feat-x", review_mode="ai", feature_name="Feat X")
    f = _state_dir(tmp_workspace, "feat-x") / "flow-state.json"
    f.write_text("{ this is not valid json", encoding="utf-8")
    with pytest.raises(FlowStateError, match="corrupt"):
        read_state(tmp_workspace, "feat-x")


def test_init_state_refuses_to_overwrite_existing(tmp_workspace):
    init_state(tmp_workspace, "feat-x", review_mode="ai", feature_name="Feat X")
    with pytest.raises(FlowStateError, match="already exists"):
        init_state(tmp_workspace, "feat-x", review_mode="ai", feature_name="Feat X")


def test_invalid_review_mode_raises(tmp_workspace):
    with pytest.raises(ValueError, match="review_mode"):
        init_state(tmp_workspace, "feat-x", review_mode="psychic", feature_name="X")
