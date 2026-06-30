#!/usr/bin/env python3
"""kdev-memory PreCompact hook（v0.8 转 Python，逻辑沿用 v0.7）

会话即将被压缩时触发。此时 Claude 仍有完整上下文。

行为（D4 瘦身后：checkpoint = 易失信号 + durable 指针，不再逐字重抄）：
  1. 总是写 .kdev/memory/checkpoints/压缩前-YYYY-MM-DD-HHMMSS.md
     内容 = 工作区 porcelain（易失）+ 未落盘 delta 警告（易失，不可复得）
            + durable 记忆指针（路径 + 行数 / jsonl 末条 record_id，不抄全文）
  2. 今日无 Step（md ∪ jsonl，dual-read）+ 工作区有变更 → checkpoint 加"⚠️ 未落盘"警告区块
  3. 顺手清理 7 天前的旧 checkpoint
  4. stdout 软提醒

为何不再逐字抄 durable 文件（D4）：决策/踩坑/改进/当前状态/执行日志 等 durable
文件在压缩后磁盘仍在、有召回通道、有嵌套仓 git 历史——三重冗余，逐字重抄纯属
token 浪费。唯一不可复得的是「干了活但未落盘」的易失叙事信号，故强化它 + 出指针。
注意：「今日是否未落盘」判断仍走 dual-read（md 今日态 ∪ jsonl 主账今日 Step），
D4 只指针化「durable 文件全文复制」那部分，不退回成只读 jsonl。
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path
from typing import List

SCRIPT_DIR = Path(__file__).resolve().parent
LIB_DIR = SCRIPT_DIR / "lib"
sys.path.insert(0, str(LIB_DIR))

from _utf8 import force_utf8_stdio  # noqa: E402
force_utf8_stdio()  # Windows GBK 兼容：v0.8.1+ 统一处理 emoji 编码（pre-compact 软提醒虽暂无 emoji，预防未来 reminders 含 emoji）

from migrate import kdev_memory_migrate  # noqa: E402
from checkpoint import prune_old_checkpoints  # noqa: E402
import step_log  # noqa: E402  # JSONL 主账读封装（dual-read 迁移第 1 步）
from scope import shared_dir  # noqa: E402


def _read_trigger() -> str:
    if sys.stdin.isatty():
        return "auto"
    try:
        raw = sys.stdin.read()
    except OSError:
        return "auto"
    if not raw:
        return "auto"
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return "auto"
    return data.get("trigger") or "auto"


def _git_porcelain() -> str:
    try:
        in_repo = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            capture_output=True, text=True, check=False,
        )
    except (OSError, FileNotFoundError):
        return ""
    if in_repo.returncode != 0:
        return ""
    try:
        r = subprocess.run(
            ["git", "status", "--porcelain", "-uall"],
            capture_output=True, text=True, check=False,
        )
    except (OSError, FileNotFoundError):
        return ""
    if r.returncode != 0:
        return ""
    return r.stdout.rstrip("\n")


def main() -> int:
    kdev_memory_migrate()

    kdev_dir = Path(".kdev/memory")
    if not kdev_dir.is_dir():
        return 0

    shared = shared_dir(kdev_dir)
    trigger = _read_trigger()
    today = date.today().isoformat()
    timestamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")

    checkpoint_dir = kdev_dir / "checkpoints"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_file = checkpoint_dir / f"压缩前-{timestamp}.md"

    # 判断"是否未落盘"（dual-read：md 今日态 ∪ jsonl 主账今日 Step）
    # jsonl 空 → steps_for_date 返回 [] → 仅看 md，行为字节级不变。
    log_file = shared / "执行日志.md"
    md_has_today = False
    if log_file.is_file():
        try:
            text = log_file.read_text(encoding="utf-8")
        except OSError:
            text = ""
        md_has_today = today in text
    try:
        jsonl_has_today = bool(step_log.steps_for_date(today, root=kdev_dir))
    except Exception:
        jsonl_has_today = False
    log_empty_today = not (md_has_today or jsonl_has_today)

    porcelain = _git_porcelain()

    # 拼 checkpoint 内容
    parts: List[str] = []
    parts.append(f"# 压缩前快照 — {timestamp}")
    parts.append("")
    parts.append(f"**触发方式**：{trigger} （auto=自动压缩 / manual=用户 /compact）")
    parts.append("**生成时机**：PreCompact hook，会话即将被压缩")
    parts.append("**主要用途**：压缩后 Claude 上下文会丢失细节，此文件保留原始信号。")
    parts.append("")

    jsonl = step_log.jsonl_path(root=kdev_dir)

    if log_empty_today and porcelain:
        # 易失·不可复得：干了活但没 dispatch recorder 的 Step 不在任何文件里。
        # 这是 checkpoint 唯一真正不可复得的叙事信号，故强化 + 提醒压缩后优先补记。
        parts.extend([
            "## ⚠️ 未落盘警告（易失信号·压缩后优先补记）",
            "",
            f"**执行日志今天（{today}）md 与 jsonl 主账均无任何 Step**，但工作区存在未提交变更。",
            "说明本会话已干了活、但工作单元（Step）尚未实时落盘——",
            "**这是压缩后唯一不可从磁盘/召回/git 历史复得的叙事信号**。请压缩后优先：",
            "",
            '1. 读本文件的"工作区快照"区块，回忆本会话干了什么',
            f"2. dispatch kdev-step-recorder 把对应 Step 落到 `{jsonl}`",
            "3. 补记完成后删除本 checkpoint",
            "",
        ])

    parts.extend([
        "## 工作区快照（git status --porcelain）",
        "",
        "```",
        porcelain if porcelain else "(工作区干净)",
        "```",
        "",
    ])

    # durable 文件 → 指针（不抄全文；压缩后 Read 活文件 / 召回通道 / git 历史回读）。
    # D4：durable 拷贝是三重冗余（活文件在盘 + 召回 + 嵌套仓 git 历史）。
    parts.append("## 📍 durable 记忆指针（压缩后 Read 活文件回读，不在此重抄全文）")
    parts.append("")

    # 已落盘 Step（执行日志.jsonl）→ 指针：路径 + 当日条数 + 末条 record_id
    if jsonl.is_file():
        try:
            recs = step_log.read_steps(root=kdev_dir)
        except Exception:
            recs = []
        last = recs[-1].get("record_id", "(无 record_id)") if recs else "(空)"
        try:
            today_n = len(step_log.steps_for_date(today, root=kdev_dir))
        except Exception:
            today_n = -1
        parts.append(f"- {jsonl}（当日 {today_n} 条；末条 {last}）")

    # 叙事 Step 仍 dual-read：执行日志.md 若存在（旧账 / 未迁条目）也出指针
    for name in ("执行日志.md", "决策日志.md", "踩坑日志.md", "改进建议.md", "当前状态.md"):
        p = shared / name
        if not p.is_file():
            continue
        try:
            n_lines = len(p.read_text(encoding="utf-8").splitlines())
        except OSError:
            n_lines = -1
        parts.append(f"- {p}（{n_lines} 行）")

    today_summary = shared / "每日汇总" / f"{today}.md"
    if today_summary.is_file():
        try:
            n_lines = len(today_summary.read_text(encoding="utf-8").splitlines())
        except OSError:
            n_lines = -1
        parts.append(f"- {today_summary}（今日汇总，{n_lines} 行）")

    parts.append("")

    parts.extend([
        "---",
        "",
        "_本文件由 kdev-memory PreCompact hook 自动生成。_",
        "_retention：7 天后自动清理，如需长期保留请手工 mv 出 checkpoints/ 目录。_",
    ])

    try:
        checkpoint_file.write_text("\n".join(parts) + "\n", encoding="utf-8")
    except OSError:
        return 0

    # 7 天 retention
    prune_old_checkpoints(checkpoint_dir, days=7)

    # 软提醒
    sys.stdout.write(f"[kdev-memory] 会话即将压缩。已写 checkpoint：{checkpoint_file}\n")
    sys.stdout.write(
        "[kdev-memory] 压缩后若需回忆细节，可 Read 此文件。"
        "如本会话有 Step/决策/踩坑未落盘，请**现在就**追加到 .kdev/memory/ 对应文件。\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
