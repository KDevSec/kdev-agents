"""fallback_step.make_fallback_step + step_log.append_fallback_step 单测。"""
from __future__ import annotations

import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest

_LIB = Path(__file__).resolve().parents[1] / "hooks" / "lib"
sys.path.insert(0, str(_LIB))

import fallback_step        # noqa: E402
import pending_commits      # noqa: E402
import scope as _scope      # noqa: E402
import step_log             # noqa: E402
from step_log import StepValidationError  # noqa: E402


WHEN = datetime(2026, 7, 7, 12, 0, 0)


def _kdev(tmp_path):
    kdev = tmp_path / ".kdev" / "memory"
    _scope.state_dir(kdev).mkdir(parents=True)
    return kdev


# ---- step_log.append_fallback_step：宽松写入 ----

def test_append_fallback_step_writes_without_strict_gate(tmp_path):
    kdev = _kdev(tmp_path)
    rec = {
        "record_id": "Step 20260707-120000-x",
        "title": "[待升格·session-end] 机械占位标题",  # 过泛，正常 append_step 会拒
        "date": "2026-07-07",
        "about": "project",
        "status": "auto-fallback",
        "key_facts": {"tools_invoked_count": 1, "errors_hit": 0},
    }
    step_log.append_fallback_step(rec, root=kdev)   # 不因缺 triggers/model_eval/user_rating 报错
    steps = step_log.steps_for_date("2026-07-07", root=kdev)
    assert len(steps) == 1 and steps[0]["status"] == "auto-fallback"


def test_append_fallback_step_rejects_non_fallback_status(tmp_path):
    kdev = _kdev(tmp_path)
    rec = {"record_id": "Step x", "title": "t", "date": "2026-07-07",
           "about": "project", "status": "scored"}
    with pytest.raises(StepValidationError):
        step_log.append_fallback_step(rec, root=kdev)


# ---- fallback_step.make_fallback_step：端到端组装 ----

def test_make_fallback_step_from_pending_commits(tmp_path):
    kdev = _kdev(tmp_path)
    sd = _scope.state_dir(kdev)
    pending_commits.append(sd, "abc1234", "fix(x): y", 1000, transcript_path="/t/s.jsonl")
    pending_commits.append(sd, "def5678", "feat(z): w", 1001)

    res = fallback_step.make_fallback_step(
        tmp_path, "session-end", root=kdev, when=WHEN, porcelain_cwd=tmp_path)
    assert res["ok"], res

    steps = step_log.steps_for_date("2026-07-07", root=kdev)
    fb = [s for s in steps if s["status"] == "auto-fallback"]
    assert len(fb) == 1
    s = fb[0]
    assert "fix(x): y" in s["title"] and "等 2 提交" in s["title"]   # commit subject 当种子
    assert s["fallback"]["source"] == "session-end"
    assert s["fallback"]["commit_shas"] == ["abc1234", "def5678"]
    assert s["fallback"]["transcript_path"] == "/t/s.jsonl"          # 留给升格
    # drain：pending 已清空，第二个丢失关口无料可重复兜底
    assert pending_commits.count(sd) == 0


def test_make_fallback_step_no_pending_still_records(tmp_path):
    """无 commit（纯 Edit 工作）仍落一条降级 Step（D4：兜）。"""
    kdev = _kdev(tmp_path)
    res = fallback_step.make_fallback_step(
        tmp_path, "pre-compact", root=kdev, when=WHEN, porcelain_cwd=tmp_path)
    assert res["ok"], res
    fb = [s for s in step_log.steps_for_date("2026-07-07", root=kdev)
          if s["status"] == "auto-fallback"]
    assert len(fb) == 1
    assert "pre-compact" in fb[0]["title"]


def test_make_fallback_step_never_raises_on_bad_root(tmp_path):
    res = fallback_step.make_fallback_step("/nonexistent/xyz", "session-end",
                                           when=WHEN)
    assert res["ok"] is False and "fallback" in res["message"]
