"""test PreCompact hook 兜底（P2 ①）：压缩前落 auto-fallback 降级 Step + checkpoint 提示升格。"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

HOOK = Path(__file__).parent.parent / "hooks" / "pre-compact-check.py"


def _setup(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    (project / ".kdev" / "memory" / "state").mkdir(parents=True)
    (project / ".kdev" / "memory" / "执行日志.md").write_text("# 执行日志\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=project, check=True)
    # 造未提交变更 → _git_porcelain 非空（触发未落盘兜底分支）
    (project / "somefile.txt").write_text("x", encoding="utf-8")
    return project


def _run(project: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(HOOK)], cwd=str(project),
        input="", capture_output=True, text=True, encoding="utf-8", errors="replace",
        env={**os.environ, "LANG": "en_US.UTF-8", "LC_ALL": "en_US.UTF-8"},
    )


def test_precompact_records_fallback_step(tmp_path):
    project = _setup(tmp_path)
    mem = project / ".kdev" / "memory"
    (mem / "state" / "pending-commits.json").write_text(json.dumps({
        "since_step_id": "", "since_ts": 0, "since_offset": 0,
        "transcript_path": "/t/s.jsonl",
        "commits": [{"sha": "abc1234", "subject": "fix(x): y", "ts": 1000}],
    }), encoding="utf-8")

    r = _run(project)
    assert r.returncode == 0, r.stderr

    jsonl = mem / "执行日志.jsonl"
    assert jsonl.exists(), "PreCompact 应落降级 Step 到 jsonl"
    recs = [json.loads(x) for x in jsonl.read_text(encoding="utf-8").splitlines() if x.strip()]
    fb = [x for x in recs if x.get("status") == "auto-fallback"]
    assert len(fb) == 1, recs
    assert "fix(x): y" in fb[0]["title"]
    assert fb[0]["fallback"]["source"] == "pre-compact"

    cps = list((mem / "checkpoints").glob("压缩前-*.md"))
    assert cps, "应生成 checkpoint"
    assert "auto-fallback" in cps[0].read_text(encoding="utf-8")


def test_precompact_no_fallback_when_qualified_step_today(tmp_path):
    """今日已有合格 Step → 不落降级 Step（今日判定排除 auto-fallback 但认合格 Step）。"""
    from datetime import date
    project = _setup(tmp_path)
    mem = project / ".kdev" / "memory"
    (mem / "执行日志.jsonl").write_text(json.dumps({
        "type": "Step", "record_id": "Step real-1", "title": "真实合格",
        "date": date.today().isoformat(), "about": "project", "status": "scored",
    }) + "\n", encoding="utf-8")

    r = _run(project)
    assert r.returncode == 0, r.stderr
    recs = [json.loads(x) for x in (mem / "执行日志.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    assert not [x for x in recs if x.get("status") == "auto-fallback"], "今日有合格 Step 时不该兜底"
