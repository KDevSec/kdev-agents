# hooks/lib/daily_render.py
"""JSONL 叙事主账 → 人读日总结 markdown（承重墙，Q-20260617）。

确定性渲染：脚本输出可独立成稿。LLM 加料（叙事概述 / 明日计划）是可选叠加层，
永不进关键路径。md Q/G/R 仍读 markdown（决策/踩坑留 md）。

kdev-memory 独立插件：只渲染通用段（完成的工作含双评分摘要 / 未完成项 /
明日计划占位 / 当日新增 Q/G/R 索引 / 负面评价观察 score_diff.delta≤-1），
不含任何 team / 委派 / handoff / CQO 多员工字段。
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import List, Optional, Union

import step_log
from scope import shared_dir
from status_schema import is_fallback_status
from step_id import id_label_fragment

PathLike = Union[Path, str]
DEFAULT_ROOT = Path(".kdev/memory")
_DATE_FIELD = re.compile(r"^\s*日期\s*[：:]\s*(\d{4}-\d{2}-\d{2})", re.MULTILINE)


def _md_titles_for_date(path: Path, kind: str, date: str) -> List[str]:
    """读 md 文件里当日 `## <ID>：title` 条目的标题（双认 legacy + 时间戳）。"""
    if not path.is_file():
        return []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []
    head = re.compile(rf"^##\s+({id_label_fragment(kind)})(?:\s*[：:]\s*(.+?))?\s*$", re.MULTILINE)
    heads = list(head.finditer(text))
    out: List[str] = []
    for i, m in enumerate(heads):
        start = m.start()
        end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        body = text[start:end]
        dm = _DATE_FIELD.search(body)
        if dm and dm.group(1) == date:
            label = m.group(1).strip()
            title = (m.group(2) or "").strip()
            out.append(f"{label}：{title}" if title else label)
    return out


def _score_brief(rec: dict) -> str:
    q = (rec.get("model_eval") or {}).get("quality")
    s = (rec.get("user_rating") or {}).get("smoothness")
    parts = []
    if q is not None:
        parts.append(f"模型 {q}")
    if s is not None:
        parts.append(f"用户 {s}")
    return f"（{' / '.join(parts)}）" if parts else ""


def render_daily(date: str, *, root: PathLike = DEFAULT_ROOT) -> str:
    root = Path(root)
    steps = step_log.steps_for_date(date, root=root)
    base = shared_dir(root)

    # auto-fallback 降级 Step 是 hook 机械骨架、未经 LLM 提炼——不当"完成的工作"，单列"待升格"。
    qualified = [s for s in steps if not is_fallback_status(s.get("status", ""))]
    fallback = [s for s in steps if is_fallback_status(s.get("status", ""))]

    lines: List[str] = [f"# 每日汇总：{date}", ""]

    lines.append("## 完成的工作")
    if qualified:
        for s in qualified:
            mark = "✓" if s.get("status") == "scored" else ""
            lines.append(f"- {s.get('title', '')} {mark}{_score_brief(s)}".rstrip())
    else:
        lines.append("- （今日无 Step）")
    lines.append("")

    if fallback:
        lines.append("## ⚠️ 待升格降级 Step（hook 机械兜底，未经 LLM 提炼，勿当正式工作）")
        for s in fallback:
            lines.append(f"- 🔺 {s.get('title', '')}（{s.get('record_id', '')}）")
        lines.append("")

    lines.append("## 未完成项")
    open_steps = [s for s in steps if s.get("status") == "open"]
    if open_steps:
        for s in open_steps:
            lines.append(f"- {s.get('title', '')}（未闭环）")
    else:
        lines.append("- 无")
    lines.append("")

    lines.append("## 明日计划")
    lines.append("- （此段留 LLM 加料 / 手填）")
    lines.append("")

    lines.append("## 本日新增踩坑 / 决策 / 改进信号")
    added: List[str] = []
    added += _md_titles_for_date(base / "决策日志.md", "Q", date)
    added += _md_titles_for_date(base / "踩坑日志.md", "G", date)
    added += _md_titles_for_date(base / "改进建议.md", "R", date)
    if added:
        for a in added:
            lines.append(f"- {a}")
    else:
        lines.append("- 无")
    lines.append("")

    lines.append("## 负面评价观察")
    neg = [s for s in steps if (s.get("score_diff") or {}).get("delta") is not None
           and s["score_diff"]["delta"] <= -1]
    if neg:
        for s in neg:
            lines.append(f"- {s.get('title', '')}（差值 {s['score_diff']['delta']}）")
    else:
        lines.append("- 无")
    return "\n".join(lines) + "\n"


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--root", default=str(DEFAULT_ROOT))
    ap.add_argument("--stdout", action="store_true")
    args = ap.parse_args(argv)
    md = render_daily(args.date, root=args.root)
    if args.stdout:
        sys.stdout.write(md)
        return 0
    out_dir = shared_dir(Path(args.root)) / "每日汇总"
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"{args.date}.md"
    mode = "a" if target.is_file() else "w"
    with open(target, mode, encoding="utf-8") as f:
        f.write(md)
    sys.stdout.write(f"[daily_render] 写 {target}\n")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    raise SystemExit(main())
