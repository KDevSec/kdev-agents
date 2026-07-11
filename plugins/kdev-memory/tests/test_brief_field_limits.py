"""test memory_config.read_brief_field_limits（brief 三字段长度闸阈值）。"""
from __future__ import annotations

import sys
from pathlib import Path

LIB = Path(__file__).parent.parent / "hooks" / "lib"
sys.path.insert(0, str(LIB))

from memory_config import read_brief_field_limits


def test_defaults_when_no_config(tmp_path):
    limits = read_brief_field_limits(tmp_path)  # 无 config.yaml
    assert limits["current_step"] == 400
    assert limits["pending_decisions"] == 1200
    assert limits["unresolved_gotchas"] == 800


def test_config_override(tmp_path):
    (tmp_path / "config.yaml").write_text(
        "brief.limit_current_step: 100\n"
        "brief.limit_pending_decisions: 500\n"
        "brief.limit_unresolved_gotchas: 300\n",
        encoding="utf-8",
    )
    limits = read_brief_field_limits(tmp_path)
    assert limits["current_step"] == 100
    assert limits["pending_decisions"] == 500
    assert limits["unresolved_gotchas"] == 300


def test_invalid_value_fails_open_to_default(tmp_path):
    (tmp_path / "config.yaml").write_text(
        "brief.limit_current_step: notanumber\n", encoding="utf-8")
    limits = read_brief_field_limits(tmp_path)
    assert limits["current_step"] == 400  # fail-open


def test_underscore_key_variant(tmp_path):
    (tmp_path / "config.yaml").write_text(
        "brief_limit_pending_decisions: 999\n", encoding="utf-8")
    limits = read_brief_field_limits(tmp_path)
    assert limits["pending_decisions"] == 999
