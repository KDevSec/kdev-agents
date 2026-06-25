#!/usr/bin/env python3
"""kdev-memory promote-list（v0.8 改写为 Python）

给 /kdev-memory-distill 命令的 promote 阶段调用：列出 .kdev/memory/ 下所有
promote_status != done 的条目，附推荐沉淀去向。

历史命令名 /kdev-memory-promote 已合并到 /kdev-memory-distill（2026-05-15）——
promote（人工挑选 → docs/）和 dataset（全量打包 → .kdev/memory/dataset/）两步
合一个命令，因为 markdown 既给人看也给机器看。

最低 Python 版本：3.7。
"""

from __future__ import annotations

import sys
import time
from datetime import date
from pathlib import Path
from typing import List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import step_log  # noqa: E402  # JSONL 主账读封装（dual-read 迁移第 1 步）


SOURCES: List[Tuple[str, str]] = [
    ("改进建议.md", "建议"),
    ("conventions.md", "R-NNN 规则"),
    ("决策日志.md", "Q-NNN"),
    ("踩坑日志.md", "G-NNN"),
    ("执行日志.md", "Step"),
]

RECOMMENDATION_TABLE = """| 来源 | 推荐 docs/ 去向 |
|---|---|
| 改进建议.md | docs/05-报告/实战总结-<项目名>.md 反思章节 |
| conventions.md §11 R-NNN | docs/08-开发规范.md |
| 决策日志.md Q-NNN | docs/04-架构/ADR-NNN.md |
| 踩坑日志.md G-NNN 高频类 | docs/04-架构/踩坑索引.md |
| 执行日志.md Step 4.5+ | docs/05-报告/实战项目总结.md |"""


def days_since_promote(kdev_dir: Path) -> str:
    """返回距上次 .last-promote touch 的天数（字符串），从未 touch 返回 "never"。"""
    flush = kdev_dir / ".last-promote"
    if not flush.exists():
        return "never"
    try:
        ft = flush.stat().st_mtime
    except OSError:
        return "never"
    if ft <= 0:
        return "never"
    return str(int((time.time() - ft) // 86400))


def list_pending_entries(md_path: Path, max_items: int = 30) -> List[str]:
    """扫 markdown 文件的 ## 二级标题条目；返回 promote_status != done|skipped 的标题列表（最多 max_items）。"""
    if not md_path.is_file():
        return []
    lines = md_path.read_text(encoding="utf-8").splitlines()

    pending: List[str] = []
    title: str = ""
    status: str = ""

    def flush() -> None:
        if title and status not in ("done", "skipped"):
            actual = status if status else "pending"
            pending.append(f"- {title}  [{actual}]")

    for line in lines:
        if line.startswith("## "):
            flush()
            title = line
            status = ""
        else:
            stripped = line.strip()
            if stripped.startswith("promote_status:"):
                value = stripped.split(":", 1)[1].strip()
                if value in ("done", "skipped", "pending"):
                    status = value
    # last item
    flush()
    return pending[:max_items]


def list_pending_steps_jsonl(kdev_dir: Path, md_step_text: str = "", max_items: int = 30) -> List[str]:
    """dual-read：从 执行日志.jsonl 主账浮出非销账 Step 沉淀候选。

    jsonl record 无 promote_status 字段（与 md `## Step` 等价口径），故浮出所有
    非销账（voided-*）Step，附 status 标注。去重：record 标题已内嵌在某 md Step
    行里则跳过（substring 判定，防 md+jsonl 双源同 Step 重复列出）。
    jsonl 空 → read_steps 返回 [] → 返回 []，行为不变。
    """
    try:
        records = step_log.read_steps(root=kdev_dir)
    except Exception:
        return []
    pending: List[str] = []
    for rec in records:
        status = str(rec.get("status") or "").strip()
        if status.startswith("voided"):
            continue
        title = str(rec.get("title") or "").strip()
        if not title or (title and title in md_step_text):
            continue
        rid = str(rec.get("record_id") or "").strip()
        label = f"{rid}: {title}" if rid else title
        pending.append(f"- {label}  [{status or 'pending'}]")
        if len(pending) >= max_items:
            break
    return pending


def main() -> int:
    kdev_dir = Path(".kdev/memory")
    if not kdev_dir.is_dir():
        print("[kdev-memory] 当前项目无 .kdev/memory/，无候选可沉淀。")
        return 0

    today = date.today().isoformat()
    days = days_since_promote(kdev_dir)

    print("# /kdev-memory-distill promote 阶段：沉淀候选列表")
    print("")
    print(f"- 扫描时间：{today}")
    print(f"- 距上次沉淀：{days} 天")
    print("")

    for filename, label in SOURCES:
        path = kdev_dir / filename
        is_step = filename == "执行日志.md"
        # Step 走 dual-read：md 缺失但 jsonl 有 Step 时仍需出该 section
        if not path.is_file() and not is_step:
            continue

        if is_step:
            md_entries = list_pending_entries(path) if path.is_file() else []
            md_step_text = "\n".join(md_entries)
            # dual-read：jsonl 主账 Step 候选（record 标题已内嵌在某 md 行里则跳过）
            jsonl_entries = list_pending_steps_jsonl(kdev_dir, md_step_text=md_step_text)
            if not (md_entries or jsonl_entries):
                continue
            print(f"## {label}（{kdev_dir}/{filename} + 执行日志.jsonl）")
            print("")
            for entry in md_entries:
                print(entry)
            for entry in jsonl_entries:
                print(entry)
            print("")
            continue

        print(f"## {label}（{kdev_dir}/{filename}）")
        print("")
        for entry in list_pending_entries(path):
            print(entry)
        print("")

    print("---")
    print("")
    print("## 推荐沉淀去向")
    print("")
    print(RECOMMENDATION_TABLE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
