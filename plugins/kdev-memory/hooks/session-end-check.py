#!/usr/bin/env python3
"""kdev-memory SessionEnd hook（v0.8 转 Python，逻辑沿用 v0.7 mtime 机制）

会话真正结束时的兜底：用 mtime 比对替代 git status。
检测 .kdev/memory/ 下有无比 .last-flush 更新的文件 → 若有则写 WARN。
v0.7 立场反转后 .kdev/ 默认 gitignore，git status 拿不到 .kdev/ 变化，必须换机制。
"""

from __future__ import annotations

import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import List

SCRIPT_DIR = Path(__file__).resolve().parent
LIB_DIR = SCRIPT_DIR / "lib"
sys.path.insert(0, str(LIB_DIR))

from migrate import kdev_memory_migrate  # noqa: E402
from coexist import defer_to_ieidev  # noqa: E402
import step_log  # noqa: E402  # JSONL 主账读封装（dual-read 迁移第 1 步）
import fallback_step  # noqa: E402  # 兜底：LLM 缺席关口机械落降级 Step
from scope import shared_dir  # noqa: E402
from status_schema import is_fallback_status  # noqa: E402


def _find_newer(kdev_dir: Path, flush_file: Path, max_items: int = 20) -> List[str]:
    """跨平台等价 ``find $KDEV_DIR -newer $FLUSH_FILE -type f``。

    排除 .last-flush / WARN-未记录-* / checkpoints / state。
    """
    try:
        flush_mtime = flush_file.stat().st_mtime
    except OSError:
        return []

    results: List[str] = []
    for p in kdev_dir.rglob("*"):
        if not p.is_file():
            continue
        # 排除项
        if p.name == ".last-flush":
            continue
        if p.name.startswith("WARN-未记录-"):
            continue
        # checkpoints / state 子目录
        rel_parts = p.relative_to(kdev_dir).parts
        if "checkpoints" in rel_parts or "state" in rel_parts:
            continue

        try:
            if p.stat().st_mtime > flush_mtime:
                results.append(str(p))
                if len(results) >= max_items:
                    break
        except OSError:
            continue

    return results


def _git_porcelain_kdev() -> List[str]:
    """v0.6 fallback：git status --porcelain -uall 过滤 .kdev/memory/ 路径。"""
    try:
        in_repo = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            capture_output=True, text=True, check=False,
            encoding="utf-8", errors="replace",
        )
    except (OSError, FileNotFoundError):
        return []
    if in_repo.returncode != 0:
        return []

    try:
        r = subprocess.run(
            ["git", "status", "--porcelain", "-uall"],
            capture_output=True, text=True, check=False,
            encoding="utf-8", errors="replace",
        )
    except (OSError, FileNotFoundError):
        return []
    if r.returncode != 0:
        return []

    return [line for line in r.stdout.splitlines() if ".kdev/memory/" in line]


def main() -> int:
    # ieidev 让位守卫：.ieidev/memory 在场 → kdev 整体让位、全静默（return，不打字、不写 WARN）。
    # 置于 migrate 之前，确保让位时 kdev 原文件零改动。
    if defer_to_ieidev():
        return 0

    kdev_memory_migrate()

    kdev_dir = Path(".kdev/memory")
    if not kdev_dir.is_dir():
        return 0

    shared = shared_dir(kdev_dir)
    today = date.today().isoformat()
    log_file = shared / "执行日志.md"
    flush_file = kdev_dir / ".last-flush"
    warn_file = kdev_dir / f"WARN-未记录-{today}.md"

    # 执行日志今天已有条目 → 无需警告（dual-read：md 今日态 ∪ jsonl 主账今日 Step）
    # jsonl 空 → steps_for_date 返回 [] → 仅看 md，行为字节级不变。
    if log_file.is_file():
        try:
            text = log_file.read_text(encoding="utf-8")
        except OSError:
            text = ""
        if today in text:
            return 0
    # 排除 auto-fallback 降级 Step：只有"今日有合格 Step"才免警告，否则第一次兜底后
    # hook 会被自己落的降级 Step 骗成"已有 Step"、再不提示升格（spec §5「别被自己骗」）。
    try:
        qualified = [s for s in step_log.steps_for_date(today, root=kdev_dir)
                     if not is_fallback_status(s.get("status", ""))]
        if qualified:
            return 0
    except Exception:
        pass

    # 检测变化
    if flush_file.is_file():
        changed = _find_newer(kdev_dir, flush_file)
    else:
        # fallback v0.6 行为
        changed = _git_porcelain_kdev()

    if not changed:
        return 0

    # 兜底（LLM 缺席关口）：机械落一条降级 Step 保证"不丢"，待下会话 SessionStart 提示升格。
    # 永不抛/永不阻塞——失败也继续写 WARN 作人读兜底信号。
    fb_ok = False
    try:
        fb = fallback_step.make_fallback_step(Path("."), "session-end", root=kdev_dir)
        fb_ok = bool(fb.get("ok"))
    except Exception:
        fb_ok = False

    # 写 WARN（覆盖同日旧警告）
    fb_line = (
        "✅ **已机械落一条降级 Step（`status: auto-fallback`）到执行日志.jsonl 兜底**——骨架"
        "（commits/files/transcript 指针）已留住，**不会丢**。下次进入项目时由主会话**升格**成正式 Step。"
        if fb_ok else
        "⚠️ 降级 Step 兜底未成功（见 stderr），仅靠本 WARN 提示补记。"
    )
    body_lines: List[str] = [
        f"# ⚠️ 未记录警告：{today}",
        "",
        f"会话结束时检测到：**执行日志今天无合格 Step**，但 `.kdev/memory/` 有未落盘的变更。",
        "",
        fb_line,
        "",
        "下次进入项目时（升格降级 Step / 补记）：",
        "1. 读降级 Step 的 `fallback` 块（commits/files/transcript_path+since_offset）回忆本会话干了什么",
        f"2. 主会话据此补 title/决策/key_facts，走正常 recorder 落一条正式 Step（旧降级条标 voided-superseded）",
        "3. 如有关键决策/踩坑/改进信号，补记到对应的 Q/G/R 日志",
        f"4. 完成后 `touch {flush_file}` 重置并 `rm {warn_file}`",
        "",
        "## 比 .last-flush 更新的文件",
        "",
        "```",
    ]
    body_lines.extend(changed)
    body_lines.extend([
        "```",
        "",
        "_本文件由 kdev-memory SessionEnd hook (v0.8) 自动生成。_",
    ])

    try:
        warn_file.write_text("\n".join(body_lines) + "\n", encoding="utf-8")
    except OSError:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
