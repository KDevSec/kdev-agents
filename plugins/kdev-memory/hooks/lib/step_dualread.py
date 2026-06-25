# hooks/lib/step_dualread.py
"""JSONL Step → md-shaped 投影合成器（dual-read 汇聚层，JSONL 主账迁移第 1 步）。

**背景**：本插件叙事 Step 正从 `执行日志.md`（markdown）增量迁移到
`执行日志.jsonl`（JSONL 主账）。迁移采用 **dual-read 先行** 策略——各
「读 Step」reader 在保留既有 md 读取的基础上，**额外**并入
`执行日志.jsonl`（经 `step_log.read_steps`）的 Step，取并集。

recorder 暂不动（仍写 md），存量 md 不迁移，`执行日志.jsonl` 现为空。

**安全不变式**：`执行日志.jsonl` 为空 → `step_log.read_steps()` 返回 `[]` →
本模块所有合成器对空输入返回空 → 各 reader 的 jsonl 分支贡献零条目 →
dual-read 改造后行为与改造前**字节级一致**（零变化、零风险）。dual-read
只在 jsonl 里真有 Step 时才多出内容。

**为什么是合成器（而非把 reader 强行结构化）**：各 reader 消费的是不同
*投影*——有的 grep md body 自由文本（`顺畅度：N/5`、`差值：±N`、`扣分项：`），
有的读 record 结构化字段（record_id / status / triggers）。把 JSONL record
合成成各 reader 既有 md helper 能 grep 的 **body 文本** / **条目 dict**，
是侵入最小、丢字段风险最低的做法——md 路径完全不动，jsonl 路径只是
「合成一份等价 md 投影再喂给同一个既有 helper」。

合成器与 ieidev 同名 reader 的 `_step_to_entry` / `_record_to_entry` 同源，
但本插件保留 md 读取、jsonl 仅叠加（ieidev 是 jsonl-only 硬切，丢了 md）。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def _smoothness(record: dict) -> Optional[Any]:
    ur = record.get("user_rating") or {}
    return ur.get("smoothness") if isinstance(ur, dict) else None


def _completed_at(record: dict) -> Optional[Any]:
    ur = record.get("user_rating") or {}
    return ur.get("completed_at") if isinstance(ur, dict) else None


def _delta(record: dict) -> Optional[Any]:
    sd = record.get("score_diff") or {}
    return sd.get("delta") if isinstance(sd, dict) else None


def _deduction(record: dict) -> Optional[str]:
    me = record.get("model_eval") or {}
    if not isinstance(me, dict):
        return None
    d = me.get("deduction")
    return str(d) if d is not None else None


def record_head(record: dict) -> str:
    """合成 `## <record_id>: <title>` 的标题行内容（不含前导 `## `）。

    与 md 路径的 heading 文法对齐：record_id 后跟冒号 + title（title 缺则只留 id）。
    """
    rid = str(record.get("record_id") or "Step ?")
    title = str(record.get("title") or "")
    return rid + (f": {title}" if title else "")


def record_to_md_body(record: dict) -> str:
    """JSONL Step record → 一段合成 markdown body，含下游 md helper grep 的全部子串。

    覆盖各 reader 的 grep 锚点：
      - `## <id>: <title>`        —— heading（parse_steps / parse_entries 切条目）
      - `日期：<date>`             —— `_within_lookback` / `in_range` / 日期过滤
      - `status: <status>`        —— `_extract_inline_status` / is_voided_status（伪 frontmatter 行）
      - `about: <about>`          —— distill `step_about` / is_misalignment_step
      - `### 用户评分` + `完成时间：` + `顺畅度：<n>/5`
                                  —— step_completeness 半残检测 + weekly `user_score`
      - `### 模型他评` + `扣分项：<deduction>`
                                  —— step_completeness 扣分项空检测
      - `### 评分差异分析` + `差值：<delta>`
                                  —— weekly / distill `diff_score`

    缺字段的段落整段省略（None 不写）——与 md 路径「字段缺失即视为该信号缺失」一致。
    """
    rec_date = record.get("date")
    rec_date = rec_date if isinstance(rec_date, str) else None
    about = str(record.get("about") or "project")
    status = str(record.get("status") or "")
    smoothness = _smoothness(record)
    completed_at = _completed_at(record)
    delta = _delta(record)
    deduction = _deduction(record)

    lines: List[str] = [f"## {record_head(record)}"]
    if rec_date:
        lines.append(f"日期：{rec_date}")
    if status:
        lines.append(f"status: {status}")
    lines.append(f"about: {about}")

    # 用户评分段（完成时间 + 顺畅度）——任一存在即建段
    if smoothness is not None or completed_at is not None:
        lines.append("")
        lines.append("### 用户评分")
        if completed_at is not None:
            lines.append(f"- 完成时间：{completed_at}")
        if smoothness is not None:
            lines.append(f"- 顺畅度：{smoothness}/5")

    # 模型他评段（扣分项）
    if deduction is not None:
        lines.append("")
        lines.append("### 模型他评")
        lines.append(f"- 扣分项：{deduction}")

    # 评分差异分析段（差值）
    if delta is not None:
        lines.append("")
        lines.append("### 评分差异分析")
        lines.append(f"- 差值：{delta}")

    return "\n".join(lines) + "\n"


def jsonl_steps_as_parse_steps(records: List[dict]) -> List[Dict[str, Any]]:
    """JSONL records → step_completeness.parse_steps() 的条目 dict 形态。

    形如 `{"label", "title", "date", "body", "status"}`，与 md `parse_steps` 输出同构。
    """
    out: List[Dict[str, Any]] = []
    for rec in records:
        rec_date = rec.get("date")
        rec_date = rec_date if isinstance(rec_date, str) else None
        out.append({
            "label": str(rec.get("record_id") or "Step ?"),
            "title": str(rec.get("title") or ""),
            "date": rec_date,
            "body": record_to_md_body(rec),
            "status": (str(rec.get("status")) if rec.get("status") is not None else None),
        })
    return out


def jsonl_steps_as_parse_entries(records: List[dict]) -> List[Dict[str, Any]]:
    """JSONL records → weekly.parse_entries() 的条目 dict 形态 `{title, date, body}`。

    title 与 md `parse_entries` 一致：heading 去前导 `#` 后 strip。
    """
    out: List[Dict[str, Any]] = []
    for rec in records:
        rec_date = rec.get("date")
        rec_date = rec_date if isinstance(rec_date, str) else None
        head = record_head(rec)
        out.append({
            "title": head.strip(),
            "date": rec_date,
            "body": record_to_md_body(rec),
        })
    return out


def jsonl_step_dates(records: List[dict]) -> List[str]:
    """JSONL records 里出现过的日期（YYYY-MM-DD），去重保序。"""
    seen = set()
    out: List[str] = []
    for rec in records:
        d = rec.get("date")
        if isinstance(d, str) and d and d not in seen:
            seen.add(d)
            out.append(d)
    return out
