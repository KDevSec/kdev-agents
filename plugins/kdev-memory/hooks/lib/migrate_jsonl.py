# hooks/lib/migrate_jsonl.py
"""一次性硬切换：执行日志.md（per-Step markdown）→ 执行日志.jsonl 主账 + 冻结归档（Q-20260617）。

幂等：迁完即把 md 改名 执行日志.archive.md；二次跑找不到 md → 0。
旧 main-N / 顺序 ID 逐字进 record_id（parse_record_id 双认认旧形式 = 冻结历史）。

⚠️ 手动 CLI 工具：不自动跑、不接任何 hook、不被 migrate.py 自动调用。
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import List, Optional, Union

import step_log
from scope import recorder_target_log
from step_completeness import parse_steps, _extract_section, _extract_field

PathLike = Union[Path, str]
DEFAULT_ROOT = Path(".kdev/memory")

_INT_RE = re.compile(r"-?\d+")
_DIFF_RE = re.compile(r"差值\s*(?:[:：]\s*)?([+-]?\d+(?:\.\d+)?)")
_FIELD_AFTER_HEAD = {  # heading 后 inline 字段
    "triggers": re.compile(r"^triggers\s*[:：]\s*(.+?)\s*$", re.MULTILINE),
    "about": re.compile(r"^about\s*[:：]\s*(.+?)\s*$", re.MULTILINE),
}


def _first_int(text: Optional[str], default: int = 0) -> int:
    if not text:
        return default
    m = _INT_RE.search(text)
    return int(m.group(0)) if m else default


def _parse_triggers(body: str) -> List[str]:
    m = _FIELD_AFTER_HEAD["triggers"].search(body)
    if not m:
        return []
    raw = m.group(1).strip().strip("[]")
    return [t.strip().strip('"').strip("'") for t in raw.split(",") if t.strip()]


_CSV_SEP_RE = re.compile(r"[，、,]")  # 半角逗号 / 全角逗号 / 顿号


def _split_csv(facts: str, field_name: str) -> List[str]:
    """单行逗号/顿号分隔字段（关键 commit / 涉及文件 / 使用的 skill / 相关条目）→ list。
    缺字段 → []；空值 → []；逐元素 strip，过滤空串。"""
    raw = _extract_field(facts, field_name)
    if not raw:
        return []
    return [p.strip() for p in _CSV_SEP_RE.split(raw) if p.strip()]


# 「关键决策：」行（行尾可能带同行值）后续的缩进子条目 `  - <决策>`
# 注意：冒号后只吃同行空白（[^\S\n]*），不可跨行，否则会把下一行子条目当 inline 值吃掉
_KEY_DECISIONS_HEAD_RE = re.compile(
    r"^[^\S\n]*[\-\*]?[^\S\n]*关键决策[:：][^\S\n]*(.*?)[^\S\n]*$", re.MULTILINE
)


def _extract_key_decisions(facts: str) -> List[str]:
    """关键决策特例：值通常空在同行、真正决策在后续缩进子条目 `  - <决策>` 上。
    - 同行有值 → 该值作为一条
    - 紧随的缩进子条目（带前导空白的 `- `）逐条收集
    - 都没有 → []"""
    m = _KEY_DECISIONS_HEAD_RE.search(facts)
    if not m:
        return []
    out: List[str] = []
    inline = m.group(1).strip()
    if inline:
        out.append(inline)
    # 从「关键决策：」行之后逐行扫缩进子条目，遇到非缩进行/非子条目即止
    rest = facts[m.end():]
    for line in rest.splitlines():
        if not line.strip():
            continue  # 容忍中间空行
        # 缩进的 list 子条目：行首有空白 + `- ` / `* `
        sub = re.match(r"^\s+[\-\*]\s+(.*\S)\s*$", line)
        if sub:
            out.append(sub.group(1).strip())
            continue
        break  # 到了同级字段（如 `- 相关条目：`）或下一段，停
    return out


def md_step_to_record(step: dict) -> dict:
    """parse_steps 单条 → JSONL record。缺字段给安全默认；原 body 不丢（archive 冻结兜底）。"""
    body = step["body"]
    facts = _extract_section(body, "### 执行事实") or ""
    me = _extract_section(body, "### 模型他评") or _extract_section(body, "### 模型自评") or ""
    ur = _extract_section(body, "### 用户评分") or ""
    sd = _extract_section(body, "### 评分差异分析") or ""

    about_m = _FIELD_AFTER_HEAD["about"].search(body)
    deduction = (_extract_field(me, "本步最值得扣分项") or _extract_field(me, "扣分项") or "迁移：原条目未填").strip()
    smooth_raw = _extract_field(ur, "顺畅度")
    diff_m = _DIFF_RE.search(sd)

    return {
        "schema_version": step_log.SCHEMA_VERSION,
        "record_id": step["label"],                # 逐字保留（冻结历史）
        "type": "Step",
        "title": step.get("title") or "(迁移：无标题)",
        "date": step.get("date") or "1970-01-01",
        "about": (about_m.group(1).strip() if about_m else "project"),
        "triggers": _parse_triggers(body) or ["迁移", "历史", "占位", "archive", "legacy"],
        "status": step.get("status") or "scored",
        "key_facts": {
            "tools_invoked_count": max(1, _first_int(_extract_field(facts, "工具调用次数"), 1)),
            "errors_hit": max(0, _first_int(_extract_field(facts, "报错次数"), 0)),
            "detours": max(0, _first_int(_extract_field(facts, "绕路次数"), 0)),
            "token_feel": (_extract_field(facts, "token 消耗感") or "medium").strip(),
            "skills_used": _split_csv(facts, "使用的 skill"),
            "commit_shas": _split_csv(facts, "关键 commit"),
            "files_touched": _split_csv(facts, "涉及文件"),
            "key_decisions": _extract_key_decisions(facts),
            "related": _split_csv(facts, "相关条目"),
        },
        "model_eval": {
            "quality": _first_int(_extract_field(me, "执行质量"), 3),
            "deduction": deduction or "迁移：原条目未填",
            "skills_invoked": [], "subagents": [],
        },
        "user_rating": {
            "completed_at": _extract_field(ur, "完成时间"),
            "smoothness": (_first_int(smooth_raw) if smooth_raw and "—" not in smooth_raw else None),
            "comment": _extract_field(ur, "用户评价"),
        },
        "score_diff": ({"delta": int(float(diff_m.group(1))), "note": ""} if diff_m else None),
        "_migrated_raw": body.strip(),             # 安全兜底：原文随条目带（零数据丢失）
    }


def migrate(*, scope: Optional[str] = None, root: PathLike = DEFAULT_ROOT) -> dict:
    root = Path(root)
    md_path = recorder_target_log(scope, root)     # 执行日志.md
    if not md_path.is_file():
        return {"migrated": 0, "archive": None}
    steps = parse_steps(md_path.read_text(encoding="utf-8"))
    n = 0
    for step in steps:
        rec = md_step_to_record(step)
        # validate 容忍迁移占位：跳过 validate（archive 冻结兜底完整性），直接写
        path = step_log.jsonl_path(scope, root)
        path.parent.mkdir(parents=True, exist_ok=True)
        import json as _json
        with open(path, "a", encoding="utf-8") as f:
            f.write(_json.dumps(rec, ensure_ascii=False) + "\n")
        n += 1
    archive = md_path.with_name("执行日志.archive.md")
    md_path.rename(archive)                          # 冻结归档（硬切换）
    return {"migrated": n, "archive": archive}


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(DEFAULT_ROOT))
    args = ap.parse_args(argv)
    res = migrate(root=args.root)
    sys.stdout.write(f"[migrate_jsonl] migrated={res['migrated']} archive={res['archive']}\n")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    raise SystemExit(main())
