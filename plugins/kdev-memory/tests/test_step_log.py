# tests/test_step_log.py
"""test step_log.py: JSONL 主账 append/read/steps_for_date + validate 7 hard-gate 确定性子集。

从 ieidev-team 搬来（ieidev→kdev 命名归一化），基座层纯新增、不接 hook。
"""
from __future__ import annotations

import sys
import json
from pathlib import Path

LIB_DIR = Path(__file__).parent.parent / "hooks" / "lib"
sys.path.insert(0, str(LIB_DIR))

import step_log  # noqa: E402
import pytest  # noqa: E402


def _valid_record():
    return {
        "schema_version": 1, "record_id": "Step 20260613-101432-ly", "type": "Step",
        "title": "丢失消息补推（断线后）", "date": "2026-04-21", "about": "feature/push",
        "triggers": ["消息补推", "SSE 断线", "gap recovery", "seq 递增", "Redis stream"],
        "status": "scored",
        "key_facts": {"tools_invoked_count": 32, "errors_hit": 2, "detours": 1,
                      "token_feel": "medium", "skills_used": [], "commit_shas": [],
                      "files_touched": [], "key_decisions": ["先 pub/sub 后换 stream"], "related": ["G-014"]},
        "model_eval": {"quality": 3, "deduction": "stream API 不熟导致 2 次报错", "skills_invoked": [], "subagents": []},
        "user_rating": {"completed_at": None, "smoothness": None, "comment": None},
        "score_diff": {"delta": 1, "note": "弱正信号"},
    }


def test_flat_jsonl_path(tmp_path):
    assert step_log.jsonl_path(root=tmp_path) == tmp_path / "执行日志.jsonl"


def test_scoped_jsonl_path(tmp_path):
    (tmp_path / "shared").mkdir()
    assert step_log.jsonl_path(root=tmp_path) == tmp_path / "shared" / "执行日志.jsonl"


def test_append_then_read_roundtrip(tmp_path):
    rec = _valid_record()
    step_log.append_step(rec, root=tmp_path)
    got = step_log.read_steps(root=tmp_path)
    assert len(got) == 1
    assert got[0]["record_id"] == "Step 20260613-101432-ly"
    assert got[0]["key_facts"]["tools_invoked_count"] == 32


def test_read_missing_file_returns_empty(tmp_path):
    assert step_log.read_steps(root=tmp_path) == []


def test_read_skips_corrupt_line(tmp_path):
    p = tmp_path / "执行日志.jsonl"
    p.write_text(json.dumps(_valid_record(), ensure_ascii=False) + "\n实在不是 json\n", encoding="utf-8")
    got = step_log.read_steps(root=tmp_path)
    assert len(got) == 1


def test_steps_for_date_filters(tmp_path):
    r1 = _valid_record(); r2 = _valid_record(); r2["date"] = "2026-04-22"
    step_log.append_step(r1, root=tmp_path); step_log.append_step(r2, root=tmp_path)
    assert len(step_log.steps_for_date("2026-04-21", root=tmp_path)) == 1


@pytest.mark.parametrize("mutate,msg", [
    (lambda r: r.update(triggers=["a", "b"]), "triggers"),
    (lambda r: r.update(about="随便"), "about"),
    (lambda r: r.update(title="完成"), "title"),
    (lambda r: r["key_facts"].update(tools_invoked_count=0), "tools_invoked_count"),
    (lambda r: r["key_facts"].update(errors_hit=-1), "errors_hit"),
    (lambda r: r["model_eval"].update(deduction="无"), "deduction"),
    (lambda r: r.update(status="bogus"), "status"),
    (lambda r: r["key_facts"].update(key_decisions=["按既有规范", "见 commit"]), "水话"),
])
def test_validate_rejects(mutate, msg):
    rec = _valid_record(); mutate(rec)
    with pytest.raises(step_log.StepValidationError):
        step_log.validate(rec)


def test_voided_r_status_ok():
    rec = _valid_record(); rec["status"] = "voided-r-007"
    step_log.validate(rec)  # 不 raise
