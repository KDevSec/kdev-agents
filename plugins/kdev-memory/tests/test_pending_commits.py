"""test pending_commits.py: CRUD + threshold + brief format。R-001 v1 task 1。"""
from __future__ import annotations

import sys
from pathlib import Path

LIB_DIR = Path(__file__).parent.parent / "hooks" / "lib"
sys.path.insert(0, str(LIB_DIR))

from pending_commits import (  # noqa: E402
    append, clear, count, format_brief_hint, oldest_age, read,
)


def test_read_missing_file_returns_empty(tmp_path):
    out = read(tmp_path)
    assert out == {"since_step_id": "", "since_ts": 0, "commits": []}


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
    # count=2 < 3, age=200 < 1800 → silent
    assert format_brief_hint(tmp_path, now=1200) is None


def test_format_brief_hint_fires_by_count(tmp_path):
    append(tmp_path, "a", "subj-a", 1000)
    append(tmp_path, "b", "subj-b", 1100)
    append(tmp_path, "c", "subj-c", 1200)
    hint = format_brief_hint(tmp_path, now=1300)
    assert hint is not None
    assert "3 commit" in hint
    assert "subj-c" in hint or "subj-a" in hint


def test_format_brief_hint_fires_by_age(tmp_path):
    append(tmp_path, "a", "subj-a", 1000)
    # count=1 < 3, but age = 5000-1000 = 4000 > 1800 → fire
    hint = format_brief_hint(tmp_path, now=5000)
    assert hint is not None
    assert "1 commit" in hint
