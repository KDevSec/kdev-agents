"""test pending_commits.py: CRUD + threshold + brief format。R-001 v1 task 1。"""
from __future__ import annotations

import sys
from pathlib import Path

LIB_DIR = Path(__file__).parent.parent / "hooks" / "lib"
sys.path.insert(0, str(LIB_DIR))

from pending_commits import (  # noqa: E402
    append, clear, count, format_brief_hint, get_transcript_marker, oldest_age,
    read,
)


def test_read_missing_file_returns_empty(tmp_path):
    out = read(tmp_path)
    assert out == {
        "since_step_id": "",
        "since_ts": 0,
        "since_offset": 0,
        "transcript_path": "",
        "commits": [],
    }


def test_append_creates_file_and_initializes_since(tmp_path):
    append(tmp_path, "abc1234", "fix(x): y", 1716903456)
    state = read(tmp_path)
    assert state["since_ts"] == 1716903456
    assert state["commits"] == [
        {"sha": "abc1234", "subject": "fix(x): y", "ts": 1716903456}
    ]


def test_append_accumulates(tmp_path):
    append(tmp_path, "a", "subj-a", 100)
    append(tmp_path, "b", "subj-b", 200)
    append(tmp_path, "c", "subj-c", 300)
    state = read(tmp_path)
    assert len(state["commits"]) == 3
    assert state["since_ts"] == 100  # earliest commit


def test_clear_resets_and_updates_since(tmp_path):
    append(tmp_path, "a", "subj-a", 100)
    clear(tmp_path, "main-15", 500)
    state = read(tmp_path)
    assert state["since_step_id"] == "main-15"
    assert state["since_ts"] == 500
    assert state["commits"] == []


def test_count_helper(tmp_path):
    assert count(tmp_path) == 0
    append(tmp_path, "a", "subj", 100)
    append(tmp_path, "b", "subj", 200)
    assert count(tmp_path) == 2


def test_oldest_age_helper(tmp_path):
    append(tmp_path, "a", "subj", 1000)
    append(tmp_path, "b", "subj", 1500)
    assert oldest_age(tmp_path, now=2000) == 1000


def test_oldest_age_empty(tmp_path):
    assert oldest_age(tmp_path, now=2000) == 0


def test_format_brief_hint_silent_when_empty(tmp_path):
    assert format_brief_hint(tmp_path, now=1000) is None


def test_format_brief_hint_silent_below_threshold(tmp_path):
    append(tmp_path, "a", "subj-a", 1000)
    append(tmp_path, "b", "subj-b", 1100)
    # count=2 < 12(backstop), age=200 < 1800 → silent
    assert format_brief_hint(tmp_path, now=1200) is None


def test_format_brief_hint_fires_by_count_backstop(tmp_path):
    # P-C1b：age 为主，count 仅极端兜底（>=12）。爆 12 个 fresh commit → 触发兜底
    for i in range(12):
        append(tmp_path, f"sha{i}", f"subj-{i}", 1000 + i)
    hint = format_brief_hint(tmp_path, now=1100)  # age 仍 < 1800，靠 count 兜底
    assert hint is not None
    assert "12 commit" in hint
    assert "subj-11" in hint or "subj-0" in hint


def test_nudge_age_primary_suppresses_fresh_burst(tmp_path):
    sd = tmp_path / "state"
    now = 1000
    for i in range(8):  # TDD 爆 8 个 commit，但都在 now 前 60s 内
        append(sd, f"sha{i}", f"t {i}", now - 60)
    # age=60s 远小于 age 阈值 → 不 nudge（age 为主，count 不再单独触发）
    assert format_brief_hint(sd, now) is None


def test_nudge_age_primary_fires_when_old(tmp_path):
    sd = tmp_path / "state"
    now = 100000
    append(sd, "sha", "t", now - 2000)  # age=2000s > 1800
    assert format_brief_hint(sd, now) is not None


def test_format_brief_hint_fires_by_age(tmp_path):
    append(tmp_path, "a", "subj-a", 1000)
    # count=1 < 3, but age = 5000-1000 = 4000 > 1800 → fire
    hint = format_brief_hint(tmp_path, now=5000)
    assert hint is not None
    assert "1 commit" in hint


def test_append_stashes_transcript_path(tmp_path):
    sd = tmp_path / "state"
    append(sd, "abc1234", "fix: x", 100, transcript_path="/t/sess.jsonl")
    data = read(sd)
    assert data["transcript_path"] == "/t/sess.jsonl"


def test_clear_sets_since_offset(tmp_path):
    sd = tmp_path / "state"
    append(sd, "abc1234", "fix: x", 100, transcript_path="/t/sess.jsonl")
    clear(sd, "main-9", 200, new_since_offset=640)
    data = read(sd)
    assert data["since_offset"] == 640
    assert data["commits"] == []


def test_get_transcript_marker(tmp_path):
    sd = tmp_path / "state"
    clear(sd, "main-9", 200, new_since_offset=640)
    append(sd, "abc1234", "fix: x", 100, transcript_path="/t/sess.jsonl")
    m = get_transcript_marker(sd)
    assert m == {"transcript_path": "/t/sess.jsonl", "since_offset": 640}


def test_empty_state_has_new_fields(tmp_path):
    sd = tmp_path / "state"
    data = read(sd)
    assert data["transcript_path"] == ""
    assert data["since_offset"] == 0
