"""Tests for kdev_core.flow_state — R1 feature-first store (适配层: 嵌套盘/扁平内存 + 事件虹吸)."""
import json
from pathlib import Path
from unittest import mock

import pytest

from kdev_core.flow_state import (
    init_state, read_state, write_state, FlowStateError,
    resume_state, mark_inactive,
)
from kdev_core import events

FLOW = "coding-flow"


def _state_file(ws: Path, slug: str) -> Path:
    return ws / ".kdev" / "features" / slug / "flow-state.json"


def test_init_creates_feature_first_path(tmp_workspace):
    init_state(tmp_workspace, FLOW, "feat-x", display_name="Feat X", initial_node="n0")
    assert _state_file(tmp_workspace, "feat-x").exists()
    # 旧 flows/ 路径不再创建
    assert not (tmp_workspace / ".kdev" / "flows").exists()


def test_init_disk_schema_is_nested(tmp_workspace):
    init_state(tmp_workspace, FLOW, "feat-x", display_name="X", initial_node="n0",
               origin="决策日志#Q-012")
    raw = json.loads(_state_file(tmp_workspace, "feat-x").read_text(encoding="utf-8"))
    assert raw["slug"] == "feat-x"
    assert raw["display_name"] == "X"
    assert raw["origin"] == "决策日志#Q-012"
    assert raw["relates_to"] is None
    assert raw["status"] == "in_progress"          # feature 级
    assert raw["stories"] == []
    assert raw["runs"] == []
    a = raw["active"]
    assert a["flow"] == FLOW and a["run"] == 1
    assert a["current_node"] == "n0"
    assert a["status"] == "in_progress"            # run 级
    assert a["gate_iters"] == {} and a["gate_calls"] == 0 and a["retries"] == {}
    assert a["config"] == {"review_mode": "ai", "auto_mode": False}


def test_read_returns_flat_view(tmp_workspace):
    init_state(tmp_workspace, FLOW, "feat-x", display_name="X", initial_node="n0")
    st = read_state(tmp_workspace, FLOW, "feat-x")
    # R2/R3 看到的扁平顶层
    assert st["flow"] == FLOW
    assert st["current_node"] == "n0"
    assert st["status"] == "in_progress"
    assert st["gate_iters"] == {} and st["gate_calls"] == 0 and st["retries"] == {}
    assert st["config"] == {"review_mode": "ai", "auto_mode": False}
    assert st["history"] == [] and st["phase_history"] == []
    # feature 台账
    assert st["feature_status"] == "in_progress"
    assert st["stories"] == [] and st["runs"] == []
    assert st["run"] == 1
    assert "_meta" not in st


def test_write_roundtrips_control_state_into_active(tmp_workspace):
    init_state(tmp_workspace, FLOW, "feat-x", display_name="X", initial_node="n0")
    st = read_state(tmp_workspace, FLOW, "feat-x")
    st["current_node"] = "n3-tdd"
    st["gate_iters"] = {"g1": 2}
    write_state(tmp_workspace, FLOW, "feat-x", st)
    raw = json.loads(_state_file(tmp_workspace, "feat-x").read_text(encoding="utf-8"))
    assert raw["active"]["current_node"] == "n3-tdd"
    assert raw["active"]["gate_iters"] == {"g1": 2}
    # 再读扁平视图一致
    st2 = read_state(tmp_workspace, FLOW, "feat-x")
    assert st2["current_node"] == "n3-tdd" and st2["gate_iters"] == {"g1": 2}


def test_write_siphons_phase_history_to_events(tmp_workspace):
    init_state(tmp_workspace, FLOW, "feat-x", display_name="X", initial_node="n0")
    st = read_state(tmp_workspace, FLOW, "feat-x")
    # 模拟 R2 advance 产出的增量
    st["current_node"] = "n1"
    st["phase_history"] = [{"from": "n0", "to": "n1", "reflow": False,
                            "forced_fail": False, "reason": "go",
                            "entered_at": "2026-06-10T00:00:00+00:00"}]
    write_state(tmp_workspace, FLOW, "feat-x", st)
    # 不进 flow-state.json
    raw = json.loads(_state_file(tmp_workspace, "feat-x").read_text(encoding="utf-8"))
    assert "phase_history" not in raw and "phase_history" not in raw["active"]
    # 进 events.jsonl
    evs = events.read_events(tmp_workspace, "feat-x")
    assert len(evs) == 1
    assert evs[0]["type"] == "transition" and evs[0]["from"] == "n0" and evs[0]["to"] == "n1"
    assert evs[0]["actor"] == "system" and evs[0]["flow"] == FLOW and evs[0]["run"] == 1


def test_write_siphons_history_gate_to_events(tmp_workspace):
    init_state(tmp_workspace, FLOW, "feat-x", display_name="X", initial_node="n0")
    st = read_state(tmp_workspace, FLOW, "feat-x")
    st["history"] = [{"gate": "g1", "kind": "review", "node": "n0", "request_id": "r1",
                      "iter": 1, "verdict": "PASS", "by": "ai", "issues": [], "revisions": [],
                      "ts": "2026-06-10T00:00:00+00:00"}]
    write_state(tmp_workspace, FLOW, "feat-x", st)
    evs = events.read_events(tmp_workspace, "feat-x")
    assert len(evs) == 1
    assert evs[0]["type"] == "gate" and evs[0]["actor"] == "ai" and evs[0]["verdict"] == "PASS"


def test_read_always_returns_empty_history_delta_model(tmp_workspace):
    init_state(tmp_workspace, FLOW, "feat-x", display_name="X", initial_node="n0")
    st = read_state(tmp_workspace, FLOW, "feat-x")
    st["history"] = [{"gate": "g1", "kind": "review", "node": "n0", "request_id": "r1",
                      "iter": 1, "verdict": "PASS", "by": "ai", "issues": [], "revisions": []}]
    write_state(tmp_workspace, FLOW, "feat-x", st)
    # 第二次 read：history 又是空（增量模型），不会把旧事件读回来
    st2 = read_state(tmp_workspace, FLOW, "feat-x")
    assert st2["history"] == []


def test_meta_persisted_and_step_id(tmp_workspace):
    init_state(tmp_workspace, FLOW, "feat-x", display_name="X", initial_node="n0")
    st = read_state(tmp_workspace, FLOW, "feat-x")
    write_state(tmp_workspace, FLOW, "feat-x", st, step_id="Step main-99")
    raw = json.loads(_state_file(tmp_workspace, "feat-x").read_text(encoding="utf-8"))
    assert raw["_meta"]["step_id"] == "Step main-99" and "written_at" in raw["_meta"]


def test_atomic_write_no_tmp_leftover(tmp_workspace):
    init_state(tmp_workspace, FLOW, "feat-x", display_name="X", initial_node="n0")
    st = read_state(tmp_workspace, FLOW, "feat-x")
    st["current_node"] = "n2"
    write_state(tmp_workspace, FLOW, "feat-x", st)
    state_dir = _state_file(tmp_workspace, "feat-x").parent
    assert list(state_dir.glob("*.tmp")) == []


def test_write_failure_leaves_original_intact(tmp_workspace):
    init_state(tmp_workspace, FLOW, "feat-x", display_name="X", initial_node="n1")
    f = _state_file(tmp_workspace, "feat-x")
    before = f.read_text(encoding="utf-8")
    st = read_state(tmp_workspace, FLOW, "feat-x")
    st["current_node"] = "n2"
    with mock.patch("kdev_core.flow_state.json.dump", side_effect=RuntimeError("disk full")):
        with pytest.raises(RuntimeError, match="disk full"):
            write_state(tmp_workspace, FLOW, "feat-x", st)
    assert "flow-state.json" in [p.name for p in f.parent.iterdir()]
    assert not list(f.parent.glob("*.tmp"))
    assert f.read_text(encoding="utf-8") == before


def test_read_missing_raises(tmp_workspace):
    with pytest.raises(FlowStateError, match="no flow-state.json"):
        read_state(tmp_workspace, FLOW, "ghost")


def test_read_corrupt_raises(tmp_workspace):
    init_state(tmp_workspace, FLOW, "feat-x", display_name="X", initial_node="n0")
    _state_file(tmp_workspace, "feat-x").write_text("{ not json", encoding="utf-8")
    with pytest.raises(FlowStateError, match="corrupt"):
        read_state(tmp_workspace, FLOW, "feat-x")


def test_init_refuses_overwrite(tmp_workspace):
    init_state(tmp_workspace, FLOW, "feat-x", display_name="X", initial_node="n0")
    with pytest.raises(FlowStateError, match="already exists"):
        init_state(tmp_workspace, FLOW, "feat-x", display_name="X", initial_node="n0")


def test_invalid_review_mode_raises(tmp_workspace):
    with pytest.raises(ValueError, match="review_mode"):
        init_state(tmp_workspace, FLOW, "feat-x", display_name="X", review_mode="psychic")


def test_same_slug_is_same_feature(tmp_workspace):
    """新语义：同 slug = 同 feature（不再按 flow 隔离）。第二次 init 同 slug 应拒绝。"""
    init_state(tmp_workspace, "coding-flow", "feat-x", display_name="X", initial_node="n0")
    with pytest.raises(FlowStateError, match="already exists"):
        init_state(tmp_workspace, "design-flow", "feat-x", display_name="X", initial_node="n0")


def test_resume_state_returns_in_progress_active(tmp_workspace):
    init_state(tmp_workspace, FLOW, "f", display_name="F", initial_node="n0")
    st = resume_state(tmp_workspace, FLOW, "f")
    assert st["_has_active"] is True and st["status"] == "in_progress"


def test_mark_inactive_folds_run_and_closes_feature(tmp_workspace):
    init_state(tmp_workspace, FLOW, "f", display_name="F", initial_node="n0")
    out = mark_inactive(tmp_workspace, FLOW, "f", status="completed")
    assert out["_has_active"] is False
    assert out["feature_status"] == "completed"
    assert len(out["runs"]) == 1
    with pytest.raises(FlowStateError, match="not resumable"):
        resume_state(tmp_workspace, FLOW, "f")
