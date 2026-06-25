"""Tests for flow lifecycle ops — mark_inactive + resume_state."""
import pytest

from kdev_core.flow_state import (
    init_state, mark_inactive, resume_state, FlowStateError,
)

FLOW = "coding-flow"


def test_mark_inactive_defaults_to_aborted(tmp_workspace):
    init_state(tmp_workspace, FLOW, "f", display_name="F")
    st = mark_inactive(tmp_workspace, FLOW, "f")
    # active run folded -> no active; terminal disposition lives at feature level.
    assert st["_has_active"] is False
    assert st["feature_status"] == "aborted"
    assert st["runs"][-1]["status"] == "aborted"


def test_mark_inactive_completed(tmp_workspace):
    init_state(tmp_workspace, FLOW, "f", display_name="F")
    st = mark_inactive(tmp_workspace, FLOW, "f", status="completed")
    assert st["_has_active"] is False
    assert st["feature_status"] == "completed"
    assert st["runs"][-1]["status"] == "completed"


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


def test_mark_inactive_missing_raises(tmp_workspace):
    with pytest.raises(FlowStateError, match="no flow-state.json"):
        mark_inactive(tmp_workspace, FLOW, "ghost")


def test_resume_missing_raises(tmp_workspace):
    with pytest.raises(FlowStateError, match="no flow-state.json"):
        resume_state(tmp_workspace, FLOW, "ghost")
