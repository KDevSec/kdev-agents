"""Tests for run 台账生命周期 — complete_run / start_run / close_feature (Q3: run≠feature)."""
import pytest

from kdev_core.flow_state import (
    init_state, read_state, complete_run, start_run, close_feature,
    resume_state, FlowStateError,
)

FLOW = "coding-flow"


def test_complete_run_folds_active_into_runs_and_clears(tmp_workspace):
    init_state(tmp_workspace, FLOW, "f", display_name="F", initial_node="n0")
    st = read_state(tmp_workspace, FLOW, "f")
    st["current_node"] = "n-done"
    from kdev_core.flow_state import write_state
    write_state(tmp_workspace, FLOW, slug="f", state=st)
    out = complete_run(tmp_workspace, "f", status="completed")
    assert out["_has_active"] is False
    assert out["current_node"] is None
    assert len(out["runs"]) == 1
    r = out["runs"][0]
    assert r == {"flow": FLOW, "run": 1, "status": "completed",
                 "final_node": "n-done", "ended_at": r["ended_at"]}
    # Q3: feature 级仍 in_progress（run 完 ≠ feature 完）
    assert out["feature_status"] == "in_progress"


def test_completed_run_not_resumable(tmp_workspace):
    init_state(tmp_workspace, FLOW, "f", display_name="F", initial_node="n0")
    complete_run(tmp_workspace, "f", status="completed")
    with pytest.raises(FlowStateError, match="not resumable"):
        resume_state(tmp_workspace, FLOW, "f")


def test_start_run_opens_new_run_with_incremented_number(tmp_workspace):
    init_state(tmp_workspace, FLOW, "f", display_name="F", initial_node="n0")
    complete_run(tmp_workspace, "f", status="completed")
    out = start_run(tmp_workspace, "design-flow", "f", initial_node="d0")
    assert out["_has_active"] is True
    assert out["run"] == 2
    assert out["flow"] == "design-flow"
    assert out["current_node"] == "d0"
    assert out["status"] == "in_progress"
    assert len(out["runs"]) == 1  # 上一棒还在台账里


def test_start_run_refuses_while_active(tmp_workspace):
    init_state(tmp_workspace, FLOW, "f", display_name="F", initial_node="n0")
    with pytest.raises(FlowStateError, match="active run"):
        start_run(tmp_workspace, FLOW, "f", initial_node="x")  # 单棒约束


def test_start_run_requires_feature_exists(tmp_workspace):
    with pytest.raises(FlowStateError, match="no flow-state.json"):
        start_run(tmp_workspace, FLOW, "ghost", initial_node="x")


def test_close_feature_sets_feature_status(tmp_workspace):
    init_state(tmp_workspace, FLOW, "f", display_name="F", initial_node="n0")
    complete_run(tmp_workspace, "f", status="completed")
    out = close_feature(tmp_workspace, "f", status="completed")
    assert out["feature_status"] == "completed"


def test_close_feature_refuses_with_active_run(tmp_workspace):
    init_state(tmp_workspace, FLOW, "f", display_name="F", initial_node="n0")
    with pytest.raises(FlowStateError, match="active run"):
        close_feature(tmp_workspace, "f", status="completed")


def test_start_run_reopens_closed_feature(tmp_workspace):
    init_state(tmp_workspace, FLOW, "f", display_name="F", initial_node="n0")
    complete_run(tmp_workspace, "f", status="completed")
    close_feature(tmp_workspace, "f", status="completed")
    out = start_run(tmp_workspace, FLOW, "f", initial_node="n0b")  # 补活
    assert out["feature_status"] == "in_progress"
    assert out["run"] == 2
