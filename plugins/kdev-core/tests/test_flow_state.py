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
