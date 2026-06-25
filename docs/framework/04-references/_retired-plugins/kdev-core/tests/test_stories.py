# tests/test_stories.py
"""Tests for stories[] 用户故事 API — HUD 需求完成度的分母 (合稿 §2.1)."""
import pytest

from kdev_core.flow_state import (
    init_state, read_state, add_story, set_story_status, FlowStateError,
)

FLOW = "coding-flow"
VALID_STORY = {"pending", "in_progress", "done"}


def test_add_story_appends(tmp_workspace):
    init_state(tmp_workspace, FLOW, "f", display_name="F", initial_node="n0")
    out = add_story(tmp_workspace, "f", story_id="US-1", title="账号登录")
    assert out["stories"] == [{"id": "US-1", "title": "账号登录", "status": "pending"}]


def test_add_story_with_status(tmp_workspace):
    init_state(tmp_workspace, FLOW, "f", display_name="F", initial_node="n0")
    out = add_story(tmp_workspace, "f", story_id="US-1", title="X", status="in_progress")
    assert out["stories"][0]["status"] == "in_progress"


def test_add_story_rejects_duplicate_id(tmp_workspace):
    init_state(tmp_workspace, FLOW, "f", display_name="F", initial_node="n0")
    add_story(tmp_workspace, "f", story_id="US-1", title="X")
    with pytest.raises(FlowStateError, match="already exists"):
        add_story(tmp_workspace, "f", story_id="US-1", title="Y")


def test_add_story_rejects_bad_status(tmp_workspace):
    init_state(tmp_workspace, FLOW, "f", display_name="F", initial_node="n0")
    with pytest.raises(ValueError, match="status"):
        add_story(tmp_workspace, "f", story_id="US-1", title="X", status="bogus")


def test_set_story_status_updates(tmp_workspace):
    init_state(tmp_workspace, FLOW, "f", display_name="F", initial_node="n0")
    add_story(tmp_workspace, "f", story_id="US-1", title="X")
    out = set_story_status(tmp_workspace, "f", story_id="US-1", status="done")
    assert out["stories"][0]["status"] == "done"


def test_set_story_status_unknown_id_raises(tmp_workspace):
    init_state(tmp_workspace, FLOW, "f", display_name="F", initial_node="n0")
    with pytest.raises(FlowStateError, match="no story"):
        set_story_status(tmp_workspace, "f", story_id="US-9", status="done")


def test_stories_survive_run_lifecycle(tmp_workspace):
    """stories 是 feature 级，跨 run 不丢。"""
    from kdev_core.flow_state import complete_run, start_run
    init_state(tmp_workspace, FLOW, "f", display_name="F", initial_node="n0")
    add_story(tmp_workspace, "f", story_id="US-1", title="X", status="done")
    complete_run(tmp_workspace, "f", status="completed")
    start_run(tmp_workspace, FLOW, "f", initial_node="n0b")
    assert read_state(tmp_workspace, FLOW, "f")["stories"][0]["status"] == "done"
