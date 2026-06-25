# tests/test_step_dualread.py
"""test step_dualread.py: JSONL Step → md 投影合成器（dual-read 汇聚层）。

核心保证：
- 空输入 → 空输出（安全不变式根基）
- 合成 body 含各下游 md helper grep 的全部锚点子串
"""
from __future__ import annotations

import sys
from pathlib import Path

LIB_DIR = Path(__file__).parent.parent / "hooks" / "lib"
sys.path.insert(0, str(LIB_DIR))

import step_dualread  # noqa: E402


def _full_record():
    return {
        "record_id": "Step 20260625-101010-ly",
        "type": "Step",
        "title": "合成器测试 Step",
        "date": "2026-06-25",
        "about": "project",
        "status": "scored",
        "model_eval": {"quality": 3, "deduction": "某处不熟练"},
        "user_rating": {"completed_at": "10:10", "smoothness": 4, "comment": None},
        "score_diff": {"delta": 2, "note": "差值"},
    }


def test_empty_input_yields_empty():
    assert step_dualread.jsonl_steps_as_parse_steps([]) == []
    assert step_dualread.jsonl_steps_as_parse_entries([]) == []
    assert step_dualread.jsonl_step_dates([]) == []


def test_body_contains_all_grep_anchors():
    body = step_dualread.record_to_md_body(_full_record())
    assert "## Step 20260625-101010-ly: 合成器测试 Step" in body
    assert "日期：2026-06-25" in body
    assert "status: scored" in body
    assert "about: project" in body
    assert "### 用户评分" in body
    assert "完成时间：10:10" in body
    assert "顺畅度：4/5" in body
    assert "### 模型他评" in body
    assert "扣分项：某处不熟练" in body
    assert "### 评分差异分析" in body
    assert "差值：2" in body


def test_parse_steps_shape():
    out = step_dualread.jsonl_steps_as_parse_steps([_full_record()])
    assert len(out) == 1
    e = out[0]
    assert e["label"] == "Step 20260625-101010-ly"
    assert e["title"] == "合成器测试 Step"
    assert e["date"] == "2026-06-25"
    assert e["status"] == "scored"
    assert "顺畅度：4/5" in e["body"]


def test_parse_entries_shape():
    out = step_dualread.jsonl_steps_as_parse_entries([_full_record()])
    assert len(out) == 1
    e = out[0]
    assert e["title"] == "Step 20260625-101010-ly: 合成器测试 Step"
    assert e["date"] == "2026-06-25"
    assert "差值：2" in e["body"]


def test_missing_fields_omit_sections():
    rec = {"record_id": "Step x", "title": "无评分", "date": "2026-06-25",
           "about": "project", "status": "open"}
    body = step_dualread.record_to_md_body(rec)
    # 缺用户评分 / 模型他评 / 差值段 → 整段省略
    assert "### 用户评分" not in body
    assert "### 模型他评" not in body
    assert "### 评分差异分析" not in body
    # 但 heading / 日期 / status / about 仍在
    assert "日期：2026-06-25" in body
    assert "status: open" in body


def test_step_dates_dedup_preserve_order():
    recs = [
        {"date": "2026-06-25"}, {"date": "2026-06-24"}, {"date": "2026-06-25"},
        {"date": None}, {},
    ]
    assert step_dualread.jsonl_step_dates(recs) == ["2026-06-25", "2026-06-24"]
