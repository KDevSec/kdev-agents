#!/usr/bin/env python3
"""kdev-memory SessionStart hook（v0.8 转 Python，逻辑沿用 v0.7.1+）

新会话启动时向 Claude 注入 .kdev/memory/ 当前状态摘要 + ⚠️ 待处理事项。
按 source 分档：
  - startup / clear：完整摘要
  - resume：精简（Claude 已有前文上下文）
  - compact：提醒 checkpoint 在哪

输出格式：JSON (hookSpecificOutput.additionalContext) 注入。
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import List, Optional

SCRIPT_DIR = Path(__file__).resolve().parent
LIB_DIR = SCRIPT_DIR / "lib"
sys.path.insert(0, str(LIB_DIR))

from migrate import kdev_memory_migrate  # noqa: E402
from frontmatter import read_state_field  # noqa: E402
from missing_summaries import list_missing_past_summaries  # noqa: E402
from worktree_link import worktree_link_kdev  # noqa: E402
from promote_scan import scan_promote_candidates  # noqa: E402

SUPPRESS = json.dumps({"continue": True, "suppressOutput": True})


def _read_source() -> str:
    if sys.stdin.isatty():
        return "startup"
    try:
        raw = sys.stdin.read()
    except OSError:
        return "startup"
    if not raw:
        return "startup"
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return "startup"
    return data.get("source") or "startup"


def _git_branch() -> str:
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, check=False,
        )
    except (OSError, FileNotFoundError):
        return ""
    if r.returncode != 0:
        return ""
    return r.stdout.strip()


def _glob_warn_files(kdev_dir: Path, max_items: int = 5) -> List[str]:
    return sorted(str(p) for p in kdev_dir.glob("WARN-*.md"))[:max_items]


def _glob_checkpoint_files(kdev_dir: Path, max_items: int = 3) -> List[str]:
    cp_dir = kdev_dir / "checkpoints"
    if not cp_dir.is_dir():
        return []
    files = [p for p in cp_dir.glob("压缩前-*.md") if p.is_file()]
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return [str(p) for p in files[:max_items]]


def _log_today_status(log_file: Path, today: str) -> str:
    if not log_file.is_file():
        return "空"
    try:
        text = log_file.read_text(encoding="utf-8")
    except OSError:
        return "空"
    if today not in text:
        return "空"
    step_count = sum(1 for line in text.splitlines() if line.startswith("## Step "))
    return f"今日有 {step_count} 条 Step（含历史）"


def _last_heading(path: Path, prefix: str) -> str:
    if not path.is_file():
        return ""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return ""
    last = ""
    for line in text.splitlines():
        if line.startswith(prefix):
            last = line
    return last


def _claude_md_drift_hint() -> str:
    """跑 claude_md_lint.run_lint，返回 brief hint 或空字符串。"""
    contract_file = SCRIPT_DIR.parent / "skills" / "kdev-memory" / "references" / "初始化-claude-md-模板.md"
    lint_lib = LIB_DIR / "claude_md_lint.py"
    claude_md = Path("CLAUDE.md")
    if not (claude_md.is_file() and contract_file.is_file() and lint_lib.is_file()):
        return ""
    try:
        spec = importlib.util.spec_from_file_location("claude_md_lint", lint_lib)
        if spec is None or spec.loader is None:
            return ""
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        result = mod.run_lint(contract_file, claude_md)
        return mod.format_hint_for_brief(result) or ""
    except Exception:
        return ""


def _step_hint(log_file: Path, today: str) -> str:
    """跑 step_completeness.run_check + format_hint_for_brief。"""
    lint_lib = LIB_DIR / "step_completeness.py"
    if not (log_file.is_file() and lint_lib.is_file()):
        return ""
    try:
        spec = importlib.util.spec_from_file_location("step_completeness", lint_lib)
        if spec is None or spec.loader is None:
            return ""
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        result = mod.run_check(log_file, today)
        return mod.format_hint_for_brief(result) or ""
    except Exception:
        return ""


def _build_brief(
    mode: str,
    today: str,
    git_branch: str,
    warn_files: List[str],
    checkpoint_files: List[str],
    log_today: str,
    summary_today_status: str,
    missing_past: str,
    drift_hint: str,
    step_hint: str,
    promote_hint: str,
    state_phase: str,
    state_iter: str,
    state_step: str,
    state_last: str,
    state_pending: str,
    state_unresolved: str,
    recent_step: str,
    recent_q: str,
    recent_g: str,
) -> str:
    """按 mode 组装 brief 文本。返回带换行的 markdown 字符串。"""

    # ---- 三层分层共享计算 ----
    p0_lines: List[str] = []
    p1_lines: List[str] = []
    p2_lines: List[str] = []

    # P0: WARN 文件 + 今日半残 Step
    for w in warn_files:
        p0_lines.append(f"  - {w}")
    if step_hint and "今日" in step_hint:
        p0_lines.append(step_hint)

    # P1: 跨天汇总缺失 / CLAUDE.md 漂移 / 历史半残 / 沉淀提醒
    if missing_past:
        p1_lines.append(
            f"  - 过去日期缺每日汇总（跨天会话遗漏）：{missing_past} —— "
            f"调用 kdev-memory skill 按日聚合源文件补写，严禁回翻会话上下文"
        )
    if drift_hint:
        p1_lines.append(drift_hint)
    if step_hint and "今日" not in step_hint:
        p1_lines.append(step_hint)
    if promote_hint:
        p1_lines.append(promote_hint.rstrip("\n"))

    # P2: checkpoint references
    for c in checkpoint_files:
        p2_lines.append(f"  - {c}")

    p0_block = "\n".join(p0_lines) + ("\n" if p0_lines else "")
    p1_block = "\n".join(p1_lines) + ("\n" if p1_lines else "")
    p2_block = "\n".join(p2_lines) + ("\n" if p2_lines else "")

    parts: List[str] = []

    if mode == "resume":
        parts.append("项目有 .kdev/ 工程记忆。本次会话是 resume（Claude 已有前文上下文）。")
        if p0_block or p1_block:
            parts.append("⚠️ 待处理：")
            if p0_block:
                parts.append("🔴 " + p0_block.rstrip("\n"))
            if p1_block:
                parts.append("🟡 " + p1_block.rstrip("\n"))
    elif mode == "compact":
        parts.append("项目有 .kdev/ 工程记忆。刚从压缩中恢复。")
        if checkpoint_files:
            parts.append("📦 压缩前 checkpoint（可回读细节）：")
            parts.extend(f"  - {c}" for c in checkpoint_files)
        if p0_block:
            parts.append("🔴 未处理的 P0 阻塞：\n" + p0_block.rstrip("\n"))
        if p1_block:
            parts.append("🟡 需核对：\n" + p1_block.rstrip("\n"))
    else:
        # startup / clear / default
        parts.append(f"项目有 .kdev/ 工程记忆。当前状态（{today}）：\n")
        if p0_block:
            parts.append("🔴 **P0 硬阻塞（立刻处理）**：\n" + p0_block)
        if p1_block:
            parts.append("🟡 **P1 需核对**：\n" + p1_block)
        if p2_block:
            parts.append("⚪ **P2 参考**：\n" + p2_block)

        prog = ["📊 **今日进度**：", f"- 执行日志：{log_today}", f"- 每日汇总：{summary_today_status}"]
        if git_branch:
            prog.append(f"- 当前分支：{git_branch}")
        parts.append("\n".join(prog))

        if state_phase or state_iter or state_step:
            state_block = ["", "🎯 **项目状态（来自 当前状态.md frontmatter）**："]
            if state_phase:
                state_block.append(f"- phase: {state_phase}")
            if state_iter:
                state_block.append(f"- iteration: {state_iter}")
            if state_step:
                state_block.append(f"- current_step: {state_step}")
            if state_last:
                state_block.append(f"- last_updated: {state_last}")
            if state_pending:
                state_block.append(f"- pending_decisions: {state_pending}")
            if state_unresolved:
                state_block.append(f"- unresolved_gotchas: {state_unresolved}")
            parts.append("\n".join(state_block))

        if recent_step or recent_q or recent_g:
            recent = ["", "📝 **最近条目**："]
            if recent_step:
                recent.append(f"- {recent_step}")
            if recent_q:
                recent.append(f"- {recent_q}")
            if recent_g:
                recent.append(f"- {recent_g}")
            parts.append("\n".join(recent))

        parts.append("\n💡 **建议**：如需详细上下文，Read .kdev/memory/当前状态.md 和最近的 .kdev/memory/每日汇总/*.md。")

    return "\n".join(parts)


def main() -> int:
    # 自动迁移
    kdev_memory_migrate()

    # secondary worktree 自动 symlink/junction
    try:
        worktree_link_kdev()
    except Exception:
        pass

    kdev_dir = Path(".kdev/memory")
    today = date.today().isoformat()
    git_branch = _git_branch()

    if not kdev_dir.is_dir():
        print(SUPPRESS)
        return 0

    source = _read_source()

    # 数据收集
    warn_files = _glob_warn_files(kdev_dir)
    checkpoint_files = _glob_checkpoint_files(kdev_dir)
    log_file = kdev_dir / "执行日志.md"
    log_today = _log_today_status(log_file, today)
    summary_today_status = "已生成" if (kdev_dir / "每日汇总" / f"{today}.md").is_file() else "未生成"
    missing_past = list_missing_past_summaries(str(kdev_dir), today)
    drift_hint = _claude_md_drift_hint()
    step_hint = _step_hint(log_file, today)
    promote_hint = scan_promote_candidates(str(kdev_dir), today)

    state_phase = read_state_field("phase")
    state_iter = read_state_field("iteration")
    state_step = read_state_field("current_step")
    state_last = read_state_field("last_updated")
    state_pending = read_state_field("pending_decisions")
    state_unresolved = read_state_field("unresolved_gotchas")

    recent_step = _last_heading(log_file, "## Step ")
    recent_q = _last_heading(kdev_dir / "决策日志.md", "## Q-")
    recent_g = _last_heading(kdev_dir / "踩坑日志.md", "## G-")

    brief = _build_brief(
        mode=source,
        today=today,
        git_branch=git_branch,
        warn_files=warn_files,
        checkpoint_files=checkpoint_files,
        log_today=log_today,
        summary_today_status=summary_today_status,
        missing_past=missing_past,
        drift_hint=drift_hint,
        step_hint=step_hint,
        promote_hint=promote_hint,
        state_phase=state_phase,
        state_iter=state_iter,
        state_step=state_step,
        state_last=state_last,
        state_pending=state_pending,
        state_unresolved=state_unresolved,
        recent_step=recent_step,
        recent_q=recent_q,
        recent_g=recent_g,
    )

    if not brief.strip():
        print(SUPPRESS)
        return 0

    full = f"<kdev-memory-brief>\n{brief}\n</kdev-memory-brief>"

    print(json.dumps({
        "continue": True,
        "suppressOutput": True,
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": full,
        },
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
