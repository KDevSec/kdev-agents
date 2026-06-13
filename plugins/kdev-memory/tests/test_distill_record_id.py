"""T5: distill.py HEAD_PATTERNS — Q/G/R/F must recognise both legacy and timestamp IDs.

Also covers: Step pattern non-greedy change (T5), Step timestamp form (characterization).

Real API surface found in distill.py:
  - _split_entries(text, head_re, source_file) -> list[Entry]
  - Entry.entry_id  — the matched heading ID token
  - Entry.title     — text after the colon (stripped), or "" if absent
  - HEAD_PATTERNS["Q"][1] etc. are the compiled regexes

Run from plugins/kdev-memory/:
    python3 -m pytest tests/test_distill_record_id.py -v
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "hooks" / "lib"))

import distill  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _scan(type_key: str, text: str):
    """Call _split_entries using the real HEAD_PATTERNS regex for type_key."""
    _filename, head_re = distill.HEAD_PATTERNS[type_key]
    return distill._split_entries(text, head_re, _filename)


# ---------------------------------------------------------------------------
# T5: Q — new timestamp form
# ---------------------------------------------------------------------------

class TestDistillQTimestamp:

    def test_new_timestamp_q_found(self):
        text = "## Q 20260613-101432-ly: 某决策\n正文\n"
        entries = _scan("Q", text)
        assert len(entries) == 1
        assert entries[0].entry_id == "Q 20260613-101432-ly"
        assert entries[0].title == "某决策"

    def test_new_timestamp_q_no_git(self):
        """Timestamp without -who suffix."""
        text = "## Q 20260613-101432: 无git决策\n正文\n"
        entries = _scan("Q", text)
        assert len(entries) == 1
        assert entries[0].entry_id == "Q 20260613-101432"

    def test_new_timestamp_q_dup_suffix(self):
        """Timestamp with .n dup suffix."""
        text = "## Q 20260613-101432.2: 重复决策\n正文\n"
        entries = _scan("Q", text)
        assert len(entries) == 1
        assert entries[0].entry_id == "Q 20260613-101432.2"

    def test_new_timestamp_q_who_and_dup(self):
        """Timestamp with -who and .n."""
        text = "## Q 20260613-101432-ly.2: 组合形式\n正文\n"
        entries = _scan("Q", text)
        assert len(entries) == 1
        assert entries[0].entry_id == "Q 20260613-101432-ly.2"

    def test_legacy_q_still_scanned(self):
        text = "## Q-018: 老决策\n正文A\n## Q 20260613-101500-ly: 新决策\n正文B\n"
        entries = _scan("Q", text)
        assert len(entries) == 2
        ids = [e.entry_id for e in entries]
        assert "Q-018" in ids
        assert "Q 20260613-101500-ly" in ids

    def test_q_no_colon_no_title(self):
        """Q with no colon and no title — entry_id captured, title empty."""
        text = "## Q-019\n正文\n"
        entries = _scan("Q", text)
        assert len(entries) == 1
        assert entries[0].entry_id == "Q-019"
        assert entries[0].title == ""


# ---------------------------------------------------------------------------
# T5: G, F, R — spot-check each
# ---------------------------------------------------------------------------

class TestDistillGFRTimestamp:

    def test_g_new_timestamp(self):
        text = "## G 20260613-101432-ly: 某踩坑\n正文\n"
        entries = _scan("G", text)
        assert len(entries) == 1
        assert entries[0].entry_id == "G 20260613-101432-ly"
        assert entries[0].title == "某踩坑"

    def test_g_legacy_still_works(self):
        text = "## G-003: 老踩坑\n正文\n"
        entries = _scan("G", text)
        assert len(entries) == 1
        assert entries[0].entry_id == "G-003"

    def test_f_new_timestamp(self):
        text = "## F 20260613-101432-ly: 技能反馈\n正文\n"
        entries = _scan("F", text)
        assert len(entries) == 1
        assert entries[0].entry_id == "F 20260613-101432-ly"

    def test_f_legacy_still_works(self):
        text = "## F-001: 老反馈\n正文\n"
        entries = _scan("F", text)
        assert len(entries) == 1
        assert entries[0].entry_id == "F-001"

    def test_r_new_timestamp(self):
        text = "## R 20260613-101432-ly: 改进建议\n正文\n"
        entries = _scan("R", text)
        assert len(entries) == 1
        assert entries[0].entry_id == "R 20260613-101432-ly"

    def test_r_legacy_still_works(self):
        text = "## R-002: 老建议\n正文\n"
        entries = _scan("R", text)
        assert len(entries) == 1
        assert entries[0].entry_id == "R-002"

    def test_mixed_legacy_and_timestamp_g(self):
        text = (
            "## G-001: 老踩坑甲\n正文1\n"
            "## G 20260613-101432-ly: 新踩坑\n正文2\n"
            "## G-002: 老踩坑乙\n正文3\n"
        )
        entries = _scan("G", text)
        assert len(entries) == 3
        ids = [e.entry_id for e in entries]
        assert ids == ["G-001", "G 20260613-101432-ly", "G-002"]


# ---------------------------------------------------------------------------
# T5 + characterization: Step pattern (non-greedy change, should not regress)
# ---------------------------------------------------------------------------

class TestDistillStepTimestamp:

    def test_step_timestamp_form(self):
        """Step with full timestamp-who form."""
        text = "## Step 20260613-101432-ly: 做了某事\n日期：2026-06-13\n正文\n"
        entries = _scan("Step", text)
        assert len(entries) == 1
        assert entries[0].entry_id == "Step 20260613-101432-ly"
        assert entries[0].title == "做了某事"

    def test_step_no_git_dup_form(self):
        """Step with no-git + dup suffix."""
        text = "## Step 20260613-101432.1: 标题\n正文\n"
        entries = _scan("Step", text)
        assert len(entries) == 1
        assert entries[0].entry_id == "Step 20260613-101432.1"

    def test_step_legacy_slug_form(self):
        """Legacy Step slug-N form must not regress."""
        text = "## Step main-7: 旧形式\n日期：2026-06-01\n正文\n"
        entries = _scan("Step", text)
        assert len(entries) == 1
        assert entries[0].entry_id == "Step main-7"
        assert entries[0].title == "旧形式"

    def test_step_numeric_form(self):
        """Very old numeric Step N form must not regress."""
        text = "## Step 3: 数字形式\n正文\n"
        entries = _scan("Step", text)
        assert len(entries) == 1
        assert entries[0].entry_id == "Step 3"
        assert entries[0].title == "数字形式"

    def test_step_multiple_mixed(self):
        """Both legacy and timestamp Steps in one file."""
        text = (
            "## Step main-6: 旧的\n日期：2026-06-10\n正文A\n"
            "## Step 20260613-101432-ly: 新的\n日期：2026-06-13\n正文B\n"
        )
        entries = _scan("Step", text)
        assert len(entries) == 2
        assert entries[0].entry_id == "Step main-6"
        assert entries[1].entry_id == "Step 20260613-101432-ly"
