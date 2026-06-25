# tests/test_events.py
"""Tests for kdev_core.events — events.jsonl append-only stream (R1 流水通道)."""
import json
from pathlib import Path

import pytest

from kdev_core import events


def _events_file(ws: Path, slug: str) -> Path:
    return ws / ".kdev" / "features" / slug / "events.jsonl"


def test_append_event_creates_file_and_appends_line(tmp_workspace):
    events.append_event(tmp_workspace, "user-auth",
                        {"type": "gate", "actor": "ai", "gate": "g1"})
    f = _events_file(tmp_workspace, "user-auth")
    assert f.exists()
    lines = f.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert rec["type"] == "gate" and rec["actor"] == "ai" and rec["gate"] == "g1"
    assert "ts" in rec  # ts auto-injected when absent


def test_append_event_is_append_only(tmp_workspace):
    events.append_event(tmp_workspace, "user-auth", {"type": "transition", "to": "n2"})
    events.append_event(tmp_workspace, "user-auth", {"type": "transition", "to": "n3"})
    recs = events.read_events(tmp_workspace, "user-auth")
    assert [r["to"] for r in recs] == ["n2", "n3"]


def test_read_events_missing_returns_empty(tmp_workspace):
    assert events.read_events(tmp_workspace, "ghost") == []


def test_append_event_preserves_given_ts(tmp_workspace):
    events.append_event(tmp_workspace, "user-auth",
                        {"type": "gate", "ts": "2026-06-10T00:00:00+00:00"})
    assert events.read_events(tmp_workspace, "user-auth")[0]["ts"] == "2026-06-10T00:00:00+00:00"


def test_transition_event_line_from_phase_entry():
    line = events.transition_event(
        slug="user-auth", flow="design", run=2,
        entry={"from": "n3", "to": "n4", "reflow": False,
               "forced_fail": False, "reason": "sr-done",
               "entered_at": "2026-06-10T00:00:00+00:00"})
    assert line == {
        "ts": "2026-06-10T00:00:00+00:00", "type": "transition", "actor": "system",
        "slug": "user-auth", "flow": "design", "run": 2,
        "from": "n3", "to": "n4", "reflow": False, "forced_fail": False, "reason": "sr-done",
    }


def test_gate_event_line_from_gate_result():
    gr = {"gate": "g-plan-review", "kind": "review", "node": "n4", "request_id": "pr-1",
          "iter": 1, "verdict": "PASS", "by": "ai", "issues": [], "revisions": [],
          "ts": "2026-06-10T00:00:00+00:00"}
    line = events.gate_event(slug="user-auth", flow="design", run=2, gate_result=gr)
    assert line == {
        "ts": "2026-06-10T00:00:00+00:00", "type": "gate", "actor": "ai",
        "slug": "user-auth", "flow": "design", "run": 2,
        "gate": "g-plan-review", "kind": "review", "node": "n4", "verdict": "PASS",
        "iter": 1, "by": "ai", "request_id": "pr-1", "issues": [], "revisions": [],
    }
