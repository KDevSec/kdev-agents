"""test brief_clamp：clamp_field 头部保留+尾部指针 + format_bloat_hint（brief 三字段长度闸）。"""
from __future__ import annotations

import sys
from pathlib import Path

LIB = Path(__file__).parent.parent / "hooks" / "lib"
sys.path.insert(0, str(LIB))

from brief_clamp import clamp_field, format_bloat_hint


def test_clamp_under_limit_unchanged():
    assert clamp_field("abc", 10) == "abc"


def test_clamp_at_limit_unchanged():
    assert clamp_field("abcde", 5) == "abcde"


def test_clamp_over_limit_truncates_with_pointer():
    out = clamp_field("a" * 100, 10)
    assert out.startswith("a" * 10)
    assert "已折叠" in out
    assert "当前状态.md" in out
    assert "+90" in out  # 100 - 10


def test_clamp_empty_string():
    assert clamp_field("", 10) == ""


def test_clamp_limit_zero_is_unlimited():
    assert clamp_field("a" * 100, 0) == "a" * 100


def test_clamp_limit_negative_is_unlimited():
    assert clamp_field("a" * 100, -5) == "a" * 100


def test_clamp_utf8_counts_code_points():
    # 中文每字 1 code point；limit=3 → 保留前 3 个汉字，折叠 3 个
    out = clamp_field("一二三四五六", 3)
    assert out.startswith("一二三")
    assert "已折叠" in out
    assert "+3" in out


def test_clamp_emoji_returns_valid_str():
    out = clamp_field("😀" * 10, 4)
    assert out.startswith("😀" * 4)
    assert isinstance(out, str)


def test_format_bloat_hint_empty():
    assert format_bloat_hint([]) == ""


def test_format_bloat_hint_single():
    hint = format_bloat_hint([("pending_decisions", 2456, 1200)])
    assert "pending_decisions" in hint
    assert "2456" in hint
    assert "归档" in hint
    assert hint.startswith("  - 📈")


def test_format_bloat_hint_multi():
    hint = format_bloat_hint([("current_step", 900, 400), ("pending_decisions", 2500, 1200)])
    assert "current_step" in hint
    assert "pending_decisions" in hint
