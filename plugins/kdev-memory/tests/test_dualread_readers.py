# tests/test_dualread_readers.py
"""dual-read 集成测试（JSONL 主账迁移第 1 步）。

每个改过的 reader 两类断言：
  (a) jsonl 空时行为与改前一致（回归保护 / 安全不变式）
  (b) 构造一条只存在于 jsonl 的 Step，断言该 reader 能读到它（证明 dual-read 真生效）

覆盖 reader：step_completeness / weekly / distill / distill_trigger /
trigger-match / promote-list / missing_summaries /
session-start-brief / stop-check / session-end-check / pre-compact-check
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

LIB = Path(__file__).parent.parent / "hooks" / "lib"
HOOKS = Path(__file__).parent.parent / "hooks"
sys.path.insert(0, str(LIB))

import step_log  # noqa: E402


def _load(modname: str, filename: str):
    spec = importlib.util.spec_from_file_location(modname, LIB / filename)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[modname] = mod
    spec.loader.exec_module(mod)
    return mod


def _jsonl_record(rid="Step 20260625-090000-ly", today=None, *, title="只在 jsonl 的 Step",
                  smoothness=2, delta=2, status="scored", about="project",
                  triggers=None, deduction="某处不熟练"):
    today = today or date.today().isoformat()
    return {
        "schema_version": 1, "type": "Step", "record_id": rid, "title": title,
        "date": today, "about": about, "status": status,
        "triggers": triggers or ["jsonl 专属 trigger A", "jsonl 专属 trigger B",
                                 "dual-read 验证", "并集召回", "唯一锚点 xyz"],
        "key_facts": {"tools_invoked_count": 5, "errors_hit": 0, "detours": 0,
                      "token_feel": "low", "skills_used": [], "commit_shas": [],
                      "files_touched": [], "key_decisions": ["走 dual-read"], "related": []},
        "model_eval": {"quality": 4, "deduction": deduction, "skills_invoked": [], "subagents": []},
        "user_rating": {"completed_at": None, "smoothness": smoothness, "comment": None},
        "score_diff": {"delta": delta, "note": "差值锚点"},
    }


# ============================================================
# step_completeness.run_check
# ============================================================

def test_step_completeness_jsonl_empty_regression(tmp_path):
    """jsonl 空 → 仅 md 解析，no-log-file 终态不变。"""
    sc = _load("step_completeness", "step_completeness.py")
    log = tmp_path / "执行日志.md"
    # md + jsonl 都不存在 → no-log-file
    r = sc.run_check(log, date.today().isoformat())
    assert r["status"] == "no-log-file"
    assert r["total_scanned"] == 0


def test_step_completeness_reads_jsonl_only_step(tmp_path):
    """只存在于 jsonl 的半残 Step（user-required 下缺顺畅度/完成时间）被扫到。"""
    sc = _load("step_completeness", "step_completeness.py")
    today = date.today().isoformat()
    step_log.append_step(_jsonl_record(today=today, smoothness=None), root=tmp_path)
    log = tmp_path / "执行日志.md"  # md 不存在
    r = sc.run_check(log, today, rating_mode="user-required")
    assert r["total_scanned"] == 1
    assert r["status"] == "has_half_complete"
    assert any("090000" in s["step_label"] for s in r["half_complete_steps"])


# ============================================================
# weekly.py (subprocess CLI)
# ============================================================

def _weekly(project: Path):
    env = {**os.environ, "LANG": "en_US.UTF-8", "LC_ALL": "en_US.UTF-8",
           "PYTHONIOENCODING": "utf-8"}
    r = subprocess.run([sys.executable, str(LIB / "weekly.py")],
                       cwd=str(project), capture_output=True, env=env)
    return r.stdout.decode("utf-8", errors="replace")


def test_weekly_jsonl_empty_regression(tmp_path):
    """jsonl 空 + 仅 md Step → 计数只含 md。"""
    k = tmp_path / ".kdev" / "memory"
    k.mkdir(parents=True)
    today = date.today().isoformat()
    (k / "执行日志.md").write_text(
        f"## Step 1: md 条目\n日期：{today}\n\n### 用户评分\n- 顺畅度：4/5\n",
        encoding="utf-8")
    out = _weekly(tmp_path)
    assert "**Step**：1 条" in out


def test_weekly_reads_jsonl_only_step(tmp_path):
    """只存在于 jsonl 的 Step 计入 weekly Step 总数 + 差值教训段。"""
    k = tmp_path / ".kdev" / "memory"
    k.mkdir(parents=True)
    today = date.today().isoformat()
    step_log.append_step(_jsonl_record(today=today, delta=2, smoothness=2), root=k)
    out = _weekly(tmp_path)
    assert "**Step**：1 条" in out
    # 差值 2 ≥ 1.5 → 问题教训段出现评分差值
    assert "评分差值" in out


def test_weekly_md_jsonl_union(tmp_path):
    """md 1 条 + jsonl 1 条（不同 Step）→ 并集计 2 条。"""
    k = tmp_path / ".kdev" / "memory"
    k.mkdir(parents=True)
    today = date.today().isoformat()
    (k / "执行日志.md").write_text(
        f"## Step 1: md 条目\n日期：{today}\n\n### 用户评分\n- 顺畅度：4/5\n",
        encoding="utf-8")
    step_log.append_step(_jsonl_record(today=today), root=k)
    out = _weekly(tmp_path)
    assert "**Step**：2 条" in out


# ============================================================
# distill.collect_entries / export
# ============================================================

def test_distill_jsonl_empty_regression(tmp_path):
    distill = _load("distill", "distill.py")
    k = tmp_path / ".kdev" / "memory"
    k.mkdir(parents=True)
    entries = distill.collect_entries(k)
    assert entries == []


def test_distill_reads_jsonl_only_step(tmp_path):
    distill = _load("distill", "distill.py")
    k = tmp_path / ".kdev" / "memory"
    k.mkdir(parents=True)
    today = date.today().isoformat()
    step_log.append_step(_jsonl_record(today=today, delta=2), root=k)
    entries = distill.collect_entries(k)
    step_entries = [e for e in entries if e.entry_id.startswith("Step")]
    assert len(step_entries) == 1
    # misalignment 切片：差值 2 ≥ 1.5 + about=project → 命中
    assert distill.is_misalignment_step(step_entries[0])


# ============================================================
# distill_trigger._count_misalign_after
# ============================================================

def test_distill_trigger_misalign_jsonl_empty_regression(tmp_path):
    dt = _load("distill_trigger", "distill_trigger.py")
    log = tmp_path / "执行日志.md"
    assert dt._count_misalign_after(log, None, root=tmp_path) == 0


def test_distill_trigger_misalign_reads_jsonl(tmp_path):
    dt = _load("distill_trigger", "distill_trigger.py")
    today = date.today().isoformat()
    step_log.append_step(_jsonl_record(today=today, delta=2), root=tmp_path)
    log = tmp_path / "执行日志.md"
    assert dt._count_misalign_after(log, None, root=tmp_path) == 1


# ============================================================
# trigger-match.scan_step_entries (subprocess, stdin JSON)
# ============================================================

def _trigger_match(project: Path, prompt: str, today: str):
    env = {**os.environ, "LANG": "en_US.UTF-8", "LC_ALL": "en_US.UTF-8",
           "PYTHONIOENCODING": "utf-8", "KDEV_TRIGGER_TODAY": today}
    payload = json.dumps({"prompt": prompt, "session_id": "s-dualread"})
    r = subprocess.run([sys.executable, str(LIB / "trigger-match.py")],
                       cwd=str(project), input=payload.encode("utf-8"),
                       capture_output=True, env=env)
    return r.stdout.decode("utf-8", errors="replace")


def test_trigger_match_jsonl_empty_regression(tmp_path):
    k = tmp_path / ".kdev" / "memory"
    k.mkdir(parents=True)
    today = date.today().isoformat()
    out = _trigger_match(tmp_path, "随便说点什么完全不匹配", today)
    data = json.loads(out)
    assert data.get("suppressOutput") is True
    assert "additionalContext" not in data.get("hookSpecificOutput", {})


def test_trigger_match_reads_jsonl_only_step(tmp_path):
    k = tmp_path / ".kdev" / "memory"
    k.mkdir(parents=True)
    today = date.today().isoformat()
    step_log.append_step(_jsonl_record(today=today), root=k)
    out = _trigger_match(tmp_path, "我想验证唯一锚点 xyz 召回", today)
    data = json.loads(out)
    ctx = data.get("hookSpecificOutput", {}).get("additionalContext", "")
    assert "090000" in ctx  # 命中 jsonl Step 的 record_id


# ============================================================
# promote-list (subprocess CLI)
# ============================================================

def _promote(project: Path):
    env = {**os.environ, "LANG": "en_US.UTF-8", "LC_ALL": "en_US.UTF-8",
           "PYTHONIOENCODING": "utf-8"}
    r = subprocess.run([sys.executable, str(LIB / "promote-list.py")],
                       cwd=str(project), capture_output=True, env=env)
    return r.stdout.decode("utf-8", errors="replace")


def test_promote_jsonl_empty_regression(tmp_path):
    k = tmp_path / ".kdev" / "memory"
    k.mkdir(parents=True)
    (k / "执行日志.md").write_text(
        "## Step 1: md Step 候选\n日期：2026-06-25\n", encoding="utf-8")
    out = _promote(tmp_path)
    assert "md Step 候选" in out


def test_promote_reads_jsonl_only_step(tmp_path):
    k = tmp_path / ".kdev" / "memory"
    k.mkdir(parents=True)
    step_log.append_step(_jsonl_record(title="jsonl 专属沉淀候选"), root=k)
    out = _promote(tmp_path)
    assert "jsonl 专属沉淀候选" in out


# ============================================================
# missing_summaries.list_missing_past_summaries
# ============================================================

def test_missing_summaries_jsonl_empty_regression(tmp_path):
    ms = _load("missing_summaries", "missing_summaries.py")
    k = tmp_path / ".kdev" / "memory"
    k.mkdir(parents=True)
    out = ms.list_missing_past_summaries(str(k), date.today().isoformat())
    assert out == ""


def test_missing_summaries_reads_jsonl_date(tmp_path):
    ms = _load("missing_summaries", "missing_summaries.py")
    k = tmp_path / ".kdev" / "memory"
    k.mkdir(parents=True)
    # 一个过去日期，仅存在于 jsonl，且无每日汇总 → 应被列为缺失
    past = "2026-06-20"
    step_log.append_step(_jsonl_record(rid="Step 20260620-080000-ly", today=past), root=k)
    out = ms.list_missing_past_summaries(str(k), "2026-06-25")
    assert past in out


# ============================================================
# session-start-brief (subprocess, stdin JSON) — _log_today_status
# ============================================================

def _brief(project: Path):
    env = {**os.environ, "LANG": "en_US.UTF-8", "LC_ALL": "en_US.UTF-8",
           "PYTHONIOENCODING": "utf-8"}
    payload = json.dumps({"source": "startup", "session_id": "s-brief"})
    r = subprocess.run([sys.executable, str(HOOKS / "session-start-brief.py")],
                       cwd=str(project), input=payload.encode("utf-8"),
                       capture_output=True, env=env)
    out = r.stdout.decode("utf-8", errors="replace")
    try:
        return json.loads(out).get("hookSpecificOutput", {}).get("additionalContext", "")
    except (ValueError, AttributeError):
        return out


def test_brief_jsonl_empty_regression(tmp_path):
    k = tmp_path / ".kdev" / "memory"
    k.mkdir(parents=True)
    ctx = _brief(tmp_path)
    # 无任何 Step → 今日进度执行日志为"空"
    assert "执行日志：空" in ctx


def test_brief_reads_jsonl_today_step(tmp_path):
    k = tmp_path / ".kdev" / "memory"
    k.mkdir(parents=True)
    today = date.today().isoformat()
    step_log.append_step(_jsonl_record(today=today), root=k)
    ctx = _brief(tmp_path)
    assert "今日有 1 条 Step" in ctx


# ============================================================
# stop-check (subprocess, stdin JSON) — 今日空提醒
# ============================================================

def _stop(project: Path):
    env = {**os.environ, "LANG": "en_US.UTF-8", "LC_ALL": "en_US.UTF-8",
           "PYTHONIOENCODING": "utf-8"}
    payload = json.dumps({"stop_hook_active": False})
    r = subprocess.run([sys.executable, str(HOOKS / "stop-check.py")],
                       cwd=str(project), input=payload.encode("utf-8"),
                       capture_output=True, env=env)
    return r.stdout.decode("utf-8", errors="replace")


def test_stop_jsonl_empty_regression(tmp_path):
    k = tmp_path / ".kdev" / "memory"
    k.mkdir(parents=True)
    out = _stop(tmp_path)
    # 今日 md+jsonl 都空 → 出"今天没有任何条目"提醒
    assert "今天没有任何条目" in out


def test_stop_jsonl_today_step_suppresses_empty_reminder(tmp_path):
    k = tmp_path / ".kdev" / "memory"
    k.mkdir(parents=True)
    today = date.today().isoformat()
    step_log.append_step(_jsonl_record(today=today), root=k)
    out = _stop(tmp_path)
    assert "今天没有任何条目" not in out


# ============================================================
# session-end-check (subprocess) — WARN 抑制
# ============================================================

def _session_end(project: Path):
    env = {**os.environ, "LANG": "en_US.UTF-8", "LC_ALL": "en_US.UTF-8",
           "PYTHONIOENCODING": "utf-8"}
    subprocess.run([sys.executable, str(HOOKS / "session-end-check.py")],
                   cwd=str(project), input=b"{}", capture_output=True, env=env)


def _session_end_setup_unsaved(k: Path):
    """制造"有未落盘变更"信号：写一个比 .last-flush 新的非日志文件。"""
    import time
    (k / ".last-flush").write_text("", encoding="utf-8")
    time.sleep(0.02)
    (k / "决策日志.md").write_text("## Q-001\n", encoding="utf-8")


def test_session_end_no_step_writes_warn(tmp_path):
    """负控：今日无 Step（md+jsonl 皆空）+ 有未落盘变更 → 写 WARN。"""
    k = tmp_path / ".kdev" / "memory"
    k.mkdir(parents=True)
    today = date.today().isoformat()
    _session_end_setup_unsaved(k)
    _session_end(tmp_path)
    assert (k / f"WARN-未记录-{today}.md").exists()


def test_session_end_jsonl_today_step_suppresses_warn(tmp_path):
    """dual-read：今日 Step 仅在 jsonl → 抑制 WARN。"""
    k = tmp_path / ".kdev" / "memory"
    k.mkdir(parents=True)
    today = date.today().isoformat()
    _session_end_setup_unsaved(k)
    # 今日 Step 仅在 jsonl → 应抑制 WARN
    step_log.append_step(_jsonl_record(today=today), root=k)
    _session_end(tmp_path)
    warn = k / f"WARN-未记录-{today}.md"
    assert not warn.exists()


# ============================================================
# pre-compact-check (subprocess) — 未落盘警告区块
# ============================================================

def _git_repo_with_unstaged(project: Path):
    """在 project 起一个 git 仓库 + 一处未提交变更（让 porcelain 非空）。"""
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    for cmd in (["git", "init", "-q"], ["git", "config", "user.email", "t@t"],
                ["git", "config", "user.name", "t"]):
        subprocess.run(cmd, cwd=str(project), capture_output=True, env=env)
    (project / "work.txt").write_text("uncommitted business change\n", encoding="utf-8")


def _pre_compact(project: Path):
    env = {**os.environ, "LANG": "en_US.UTF-8", "LC_ALL": "en_US.UTF-8",
           "PYTHONIOENCODING": "utf-8"}
    subprocess.run([sys.executable, str(HOOKS / "pre-compact-check.py")],
                   cwd=str(project), input=json.dumps({"trigger": "manual"}).encode("utf-8"),
                   capture_output=True, env=env)


def test_pre_compact_no_step_shows_unsaved_warning(tmp_path):
    """负控：今日无 Step（md+jsonl 皆空）+ 工作区有变更 → 出"未落盘警告"区块。"""
    k = tmp_path / ".kdev" / "memory"
    k.mkdir(parents=True)
    _git_repo_with_unstaged(tmp_path)
    _pre_compact(tmp_path)
    cps = list((k / "checkpoints").glob("压缩前-*.md"))
    assert cps, "checkpoint 应被写出"
    body = cps[0].read_text(encoding="utf-8")
    assert "未落盘警告" in body


def test_pre_compact_jsonl_today_step_no_unsaved_warning(tmp_path):
    """dual-read：今日 Step 仅在 jsonl + 工作区有变更 → log_empty_today=False → 无"未落盘警告"。"""
    k = tmp_path / ".kdev" / "memory"
    k.mkdir(parents=True)
    _git_repo_with_unstaged(tmp_path)
    today = date.today().isoformat()
    step_log.append_step(_jsonl_record(today=today), root=k)
    _pre_compact(tmp_path)
    cps = list((k / "checkpoints").glob("压缩前-*.md"))
    assert cps, "checkpoint 应被写出"
    body = cps[0].read_text(encoding="utf-8")
    assert "未落盘警告" not in body
