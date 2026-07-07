"""test SessionEnd hook 的 mtime-based WARN 生成逻辑（v0.7 / v0.8 转 Python）

v0.6: git status --porcelain 检测 .kdev/ dirty → 生成 WARN
v0.7: .last-flush mtime 比对 → 生成 WARN（立场反转后 .kdev/ 不 git tracked 也能工作）
v0.8: hook 从 session-end-check.sh 转为 session-end-check.py，三平台一致
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from datetime import date
from pathlib import Path

HOOK = Path(__file__).parent.parent / "hooks" / "session-end-check.py"


def _setup_kdev(tmp_path: Path) -> Path:
    """造一个最小 .kdev/memory/ 结构，返回 project root。"""
    project = tmp_path / "project"
    (project / ".kdev" / "memory").mkdir(parents=True)
    (project / ".kdev" / "memory" / "执行日志.md").write_text("# 执行日志\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=project, check=True)
    subprocess.run(["git", "add", "."], cwd=project, check=True)
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "init"],
        cwd=project,
        check=True,
    )
    return project


def _utf8_env() -> dict:
    return {**os.environ, "LANG": "en_US.UTF-8", "LC_ALL": "en_US.UTF-8"}


def _run_hook(project: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(HOOK)],
        cwd=str(project), capture_output=True, env=_utf8_env(),
    )


def test_warn_generated_when_kdev_modified_after_last_flush(tmp_path):
    """.last-flush 存在、有比它新的 .kdev/memory/ 文件 → 应生成 WARN。"""
    project = _setup_kdev(tmp_path)
    flush = project / ".kdev" / "memory" / ".last-flush"
    flush.touch()
    old_time = time.time() - 3600
    os.utime(flush, (old_time, old_time))
    (project / ".kdev" / "memory" / "执行日志.md").write_text(
        "# 执行日志\n\n## Step 1\n", encoding="utf-8"
    )
    r = _run_hook(project)
    assert r.returncode == 0, f"hook failed: {r.stderr.decode('utf-8', errors='replace')}"
    warn = project / ".kdev" / "memory" / f"WARN-未记录-{date.today().isoformat()}.md"
    assert warn.exists(), "SessionEnd 应生成 WARN（mtime 机制），但 WARN 文件不存在"


def test_no_warn_when_last_flush_newer(tmp_path):
    """.last-flush 最新（说明落盘都已刷新）→ 不应生成 WARN。"""
    project = _setup_kdev(tmp_path)
    (project / ".kdev" / "memory" / "执行日志.md").write_text(
        "# 执行日志\n\n## Step 1\n", encoding="utf-8"
    )
    time.sleep(0.5)
    (project / ".kdev" / "memory" / ".last-flush").touch()
    r = _run_hook(project)
    assert r.returncode == 0
    warn = project / ".kdev" / "memory" / f"WARN-未记录-{date.today().isoformat()}.md"
    assert not warn.exists(), "last-flush 比 .kdev/ 都新 → 不应有 WARN"


def test_no_warn_when_no_last_flush_and_no_changes(tmp_path):
    """无 .last-flush 且 .kdev/memory/ 基本无变化（init 后刚 commit）→ 无 WARN。"""
    project = _setup_kdev(tmp_path)
    r = _run_hook(project)
    assert r.returncode == 0
    warn = project / ".kdev" / "memory" / f"WARN-未记录-{date.today().isoformat()}.md"
    assert not warn.exists(), "初始化空项目不应有 WARN"


def test_works_without_git_repo(tmp_path):
    """立场反转后：非 git 项目也要能正常工作（不 crash、不误报）。"""
    project = tmp_path / "nogit"
    (project / ".kdev" / "memory").mkdir(parents=True)
    (project / ".kdev" / "memory" / "执行日志.md").write_text(
        "# 执行日志\n\n## Step 1\n", encoding="utf-8"
    )
    r = _run_hook(project)
    assert r.returncode == 0, f"hook 异常退出: {r.stderr.decode('utf-8', errors='replace')}"


import json as _json  # noqa: E402


def test_session_end_records_fallback_step(tmp_path):
    """兜底：有变更且今日无合格 Step → SessionEnd 落一条 auto-fallback 降级 Step + WARN。"""
    project = _setup_kdev(tmp_path)
    mem = project / ".kdev" / "memory"
    state = mem / "state"
    state.mkdir(parents=True, exist_ok=True)
    (state / "pending-commits.json").write_text(_json.dumps({
        "since_step_id": "", "since_ts": 0, "since_offset": 0,
        "transcript_path": "/t/s.jsonl",
        "commits": [{"sha": "abc1234", "subject": "fix(x): y", "ts": 1000}],
    }), encoding="utf-8")
    flush = mem / ".last-flush"
    flush.touch()
    old = time.time() - 3600
    os.utime(flush, (old, old))
    (mem / "执行日志.md").write_text("# 执行日志\n\n变更\n", encoding="utf-8")

    r = _run_hook(project)
    assert r.returncode == 0, r.stderr.decode("utf-8", errors="replace")

    jsonl = mem / "执行日志.jsonl"
    assert jsonl.exists(), "降级 Step 应落到 执行日志.jsonl"
    recs = [_json.loads(x) for x in jsonl.read_text(encoding="utf-8").splitlines() if x.strip()]
    fb = [x for x in recs if x.get("status") == "auto-fallback"]
    assert len(fb) == 1, recs
    assert "fix(x): y" in fb[0]["title"]
    assert fb[0]["fallback"]["transcript_path"] == "/t/s.jsonl"
    warn = mem / f"WARN-未记录-{date.today().isoformat()}.md"
    assert warn.exists() and "auto-fallback" in warn.read_text(encoding="utf-8")


def test_session_end_no_fallback_when_qualified_step_today(tmp_path):
    """今日已有合格 Step（jsonl scored）→ 提前 return，不落降级 Step、不 WARN。"""
    project = _setup_kdev(tmp_path)
    mem = project / ".kdev" / "memory"
    (mem / "执行日志.jsonl").write_text(_json.dumps({
        "type": "Step", "record_id": "Step real-1", "title": "真实合格 Step",
        "date": date.today().isoformat(), "about": "project", "status": "scored",
    }) + "\n", encoding="utf-8")
    flush = mem / ".last-flush"
    flush.touch()
    old = time.time() - 3600
    os.utime(flush, (old, old))
    (mem / "执行日志.md").write_text("# 执行日志\n\n变更\n", encoding="utf-8")

    r = _run_hook(project)
    assert r.returncode == 0
    warn = mem / f"WARN-未记录-{date.today().isoformat()}.md"
    assert not warn.exists(), "今日有合格 Step 时不该兜底/告警"
    # 也没多落降级 Step
    recs = [_json.loads(x) for x in (mem / "执行日志.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    assert not [x for x in recs if x.get("status") == "auto-fallback"]
