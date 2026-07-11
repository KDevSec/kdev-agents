"""test session-start-brief：rating-setup 一次性提示 + brief.verbosity 三档（P-C0.5 / P-C1a）。"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HOOK = Path(__file__).parent.parent / "hooks" / "session-start-brief.py"


def _init(tmp_path: Path, config_text: str | None = None) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-q", "--allow-empty", "-m", "init"],
        cwd=repo, check=True,
    )
    mem = repo / ".kdev" / "memory"
    (mem / "state").mkdir(parents=True)
    (mem / "执行日志.md").write_text("# 执行日志\n", encoding="utf-8")
    (mem / "当前状态.md").write_text(
        "---\nphase: t\npending_decisions: [开 P-X]\n---\n", encoding="utf-8")
    if config_text is not None:
        (mem / "config.yaml").write_text(config_text, encoding="utf-8")
    return repo


def _ctx(repo: Path) -> str:
    r = subprocess.run([sys.executable, str(HOOK)], cwd=str(repo),
                       input=json.dumps({"source": "startup"}),
                       capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    out = json.loads(r.stdout) if r.stdout.strip() else {}
    return out.get("hookSpecificOutput", {}).get("additionalContext", "")


def test_rating_setup_prompt_shown_once_when_unconfigured(tmp_path):
    repo = _init(tmp_path, config_text=None)  # 无 rating.mode 键
    first = _ctx(repo)
    assert "<kdev-memory-rating-setup>" in first
    assert (repo / ".kdev" / "memory" / "state" / ".rating-setup-shown").is_file()
    # 第二次不再出现（marker 去重）
    second = _ctx(repo)
    assert "<kdev-memory-rating-setup>" not in second


def test_rating_setup_prompt_absent_when_configured(tmp_path):
    repo = _init(tmp_path, config_text="rating.mode: model-only\n")
    assert "<kdev-memory-rating-setup>" not in _ctx(repo)


def test_verbosity_compact_writes_detail_and_trims(tmp_path):
    repo = _init(tmp_path, config_text="rating.mode: model-only\nbrief.verbosity: compact\n")
    ctx = _ctx(repo)
    # compact：含今日进度 + pending_decisions + brief-detail 指针；不含"最近条目"全量块
    assert "brief-detail.md" in ctx
    assert "pending_decisions" in ctx or "开 P-X" in ctx
    assert "📝 **最近条目**" not in ctx
    assert (repo / ".kdev" / "memory" / "brief-detail.md").is_file()
    detail = (repo / ".kdev" / "memory" / "brief-detail.md").read_text(encoding="utf-8")
    assert "今日进度" in detail


def test_verbosity_normal_is_full(tmp_path):
    repo = _init(tmp_path, config_text="rating.mode: model-only\nbrief.verbosity: normal\n")
    ctx = _ctx(repo)
    assert "📊 **今日进度**" in ctx
    assert "brief-detail.md" not in ctx
    assert not (repo / ".kdev" / "memory" / "brief-detail.md").is_file()


def test_verbosity_verbose_is_full_no_detail_file(tmp_path):
    repo = _init(tmp_path, config_text="rating.mode: model-only\nbrief.verbosity: verbose\n")
    ctx = _ctx(repo)
    assert "📊 **今日进度**" in ctx
    assert "brief-detail.md" not in ctx
    assert not (repo / ".kdev" / "memory" / "brief-detail.md").is_file()


def test_brief_flags_fallback_step_for_upgrade(tmp_path):
    """今日 jsonl 有 auto-fallback 降级 Step → brief P0 提示升格（含 record_id + 待升格）。"""
    from datetime import date
    repo = _init(tmp_path, config_text="rating.mode: model-only\n")
    mem = repo / ".kdev" / "memory"
    rec = {
        "type": "Step", "record_id": "Step 20260707-000000-x",
        "title": "[待升格·session-end] fix(x): y", "date": date.today().isoformat(),
        "about": "project", "status": "auto-fallback",
        "fallback": {"source": "session-end"},
    }
    (mem / "执行日志.jsonl").write_text(json.dumps(rec, ensure_ascii=False) + "\n", encoding="utf-8")
    ctx = _ctx(repo)
    assert "待升格" in ctx
    assert "Step 20260707-000000-x" in ctx


def test_brief_clamps_long_pending_without_warn(tmp_path):
    """pending 1500 字符（>1200 clamp，<2400 无 WARN）→ 折叠指针出现、无膨胀 WARN。"""
    repo = _init(tmp_path, config_text="rating.mode: model-only\n")
    mem = repo / ".kdev" / "memory"
    (mem / "当前状态.md").write_text(
        f"---\nphase: t\npending_decisions: [{'x' * 1500}]\n---\n", encoding="utf-8")
    ctx = _ctx(repo)
    assert "已折叠" in ctx        # clamp 触发
    assert "字段膨胀" not in ctx  # WARN 未触发


def test_brief_warns_on_bloated_pending(tmp_path):
    """pending 2500 字符（>2400）→ 折叠指针 + P1 膨胀 WARN 同现。"""
    repo = _init(tmp_path, config_text="rating.mode: model-only\n")
    mem = repo / ".kdev" / "memory"
    (mem / "当前状态.md").write_text(
        f"---\nphase: t\npending_decisions: [{'x' * 2500}]\n---\n", encoding="utf-8")
    ctx = _ctx(repo)
    assert "已折叠" in ctx      # clamp 触发
    assert "字段膨胀" in ctx    # WARN 触发


def test_brief_compact_verbosity_clamps_and_warns(tmp_path):
    """compact 档也过长度闸：超长 pending → compact 输出含折叠指针 + 膨胀 WARN。"""
    repo = _init(tmp_path, config_text="rating.mode: model-only\nbrief.verbosity: compact\n")
    mem = repo / ".kdev" / "memory"
    (mem / "当前状态.md").write_text(
        f"---\nphase: t\npending_decisions: [{'x' * 2500}]\n---\n", encoding="utf-8")
    ctx = _ctx(repo)
    assert "已折叠" in ctx      # compact 档 clamp 触发
    assert "字段膨胀" in ctx    # compact 档 WARN 触发（compact early-return 分支的 separate append）
