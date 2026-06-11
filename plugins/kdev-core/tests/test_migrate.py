"""Tests for kdev_core.migrate — 旧 flows/ → feature-first (幂等 + 同slug合并 + history→events)."""
import json
from pathlib import Path

import pytest

from kdev_core import migrate, events
from kdev_core.flow_state import read_state


def _old_flow(ws: Path, flow, slug, doc):
    p = ws / ".kdev" / "flows" / flow / slug / "flow-state.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    return p


def _old_doc(flow, slug, status="completed", node="n-done", history=None):
    return {
        "flow": flow, "slug": slug, "display_name": slug.upper(),
        "status": status, "active": status == "in_progress", "current_node": node,
        "created_at": "2026-06-07T00:00:00+00:00", "updated_at": "2026-06-07T01:00:00+00:00",
        "config": {"review_mode": "ai", "auto_mode": False},
        "history": history or [],
    }


def test_migrate_single_completed_flow(tmp_workspace):
    _old_flow(tmp_workspace, "coding-flow", "ued6", _old_doc(
        "coding-flow", "ued6", history=[
            {"gate": "g1", "kind": "review", "node": "n4", "request_id": "r1", "iter": 1,
             "verdict": "PASS", "by": "ai", "issues": [], "revisions": [],
             "ts": "2026-06-07T00:30:00+00:00"}]))
    report = migrate.migrate_workspace(tmp_workspace)
    assert report["migrated"] == ["ued6"]
    st = read_state(tmp_workspace, slug="ued6")
    assert st["feature_status"] == "completed"
    assert st["_has_active"] is False
    assert st["runs"] == [{"flow": "coding-flow", "run": 1, "status": "completed",
                           "final_node": "n-done", "ended_at": st["runs"][0]["ended_at"]}]
    assert st["origin"] == "migrated:.kdev/flows"
    evs = events.read_events(tmp_workspace, "ued6")
    assert len(evs) == 1 and evs[0]["type"] == "gate" and evs[0]["verdict"] == "PASS"


def test_migrate_in_progress_flow_keeps_active(tmp_workspace):
    _old_flow(tmp_workspace, "coding-flow", "wip", _old_doc(
        "coding-flow", "wip", status="in_progress", node="n3"))
    migrate.migrate_workspace(tmp_workspace)
    st = read_state(tmp_workspace, slug="wip")
    assert st["_has_active"] is True
    assert st["current_node"] == "n3" and st["status"] == "in_progress"
    assert st["feature_status"] == "in_progress"
    assert st["runs"] == []


def test_migrate_same_slug_two_flows_merges(tmp_workspace):
    _old_flow(tmp_workspace, "design-flow", "auth", _old_doc(
        "design-flow", "auth", node="d-done"))
    _old_flow(tmp_workspace, "coding-flow", "auth", _old_doc(
        "coding-flow", "auth", status="in_progress", node="c3"))
    migrate.migrate_workspace(tmp_workspace)
    st = read_state(tmp_workspace, slug="auth")
    # design 折叠进 runs[]，coding(in_progress) 进 active
    assert len(st["runs"]) == 1 and st["runs"][0]["flow"] == "design-flow"
    assert st["_has_active"] is True and st["flow"] == "coding-flow"
    assert st["run"] == 2


def test_migrate_idempotent(tmp_workspace):
    _old_flow(tmp_workspace, "coding-flow", "ued6", _old_doc("coding-flow", "ued6"))
    r1 = migrate.migrate_workspace(tmp_workspace)
    r2 = migrate.migrate_workspace(tmp_workspace)
    assert r1["migrated"] == ["ued6"]
    assert r2["migrated"] == [] and r2["skipped"] == ["ued6"]
    # events 不重复
    assert len(events.read_events(tmp_workspace, "ued6")) == 0  # 该 doc history 空


def test_migrate_dry_run_writes_nothing(tmp_workspace):
    _old_flow(tmp_workspace, "coding-flow", "ued6", _old_doc("coding-flow", "ued6"))
    report = migrate.migrate_workspace(tmp_workspace, dry_run=True)
    assert report["migrated"] == ["ued6"]
    assert not (tmp_workspace / ".kdev" / "features").exists()


def test_migrate_remove_old(tmp_workspace):
    _old_flow(tmp_workspace, "coding-flow", "ued6", _old_doc("coding-flow", "ued6"))
    migrate.migrate_workspace(tmp_workspace, remove_old=True)
    assert not (tmp_workspace / ".kdev" / "flows" / "coding-flow" / "ued6").exists()
    assert (tmp_workspace / ".kdev" / "features" / "ued6" / "flow-state.json").exists()


def test_migrate_empty_workspace(tmp_workspace):
    report = migrate.migrate_workspace(tmp_workspace)
    assert report == {"migrated": [], "skipped": [], "dry_run": False}
