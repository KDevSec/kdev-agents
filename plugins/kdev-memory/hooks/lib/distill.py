"""kdev-memory markdown 切片导出（决策 3 落地，详见 references/markdown-切片导出.md）

产出三个独立 markdown 切片包到 `<kdev_dir>/dataset/`：

1. `dataset-full.md` —— 全量条目按日期升序交织（Step + Q + G + F + R），每条前加来源标记
2. `dataset-misalignment.md` —— 差值 ≥ 1.5 的 Step（顶级对齐数据）
3. `dataset-skill-feedback-by-subject/<slug>.md` —— F-NNN 按 subject 切片（每 subject 一个文件）

**不引入 JSONL**——架构终态决策，markdown 主存 + markdown 切片包是直接喂蒸馏管道的形态。

CLI：`python3 distill.py [<kdev_dir>] [--out <dir>] [--no-sanitize]`
- kdev_dir 默认 `.kdev/memory`
- out 默认 `<kdev_dir>/dataset/`
- --no-sanitize 仅用于测试 / debug，绝不应在分享数据集时使用
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Iterable

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from _utf8 import force_utf8_stdio  # noqa: E402
force_utf8_stdio()

import scope as _scope  # noqa: E402
import step_log  # noqa: E402  # JSONL 主账读封装（dual-read 迁移第 1 步）
import step_dualread  # noqa: E402  # JSONL Step → md 投影合成器
from sanitize import sanitize_text, verify_no_leaks  # noqa: E402
from scope import shared_dir, staff_log_files  # noqa: E402
from status_schema import is_fallback_status, is_voided_status, warn_unknown_status  # noqa: E402
from step_id import id_label_fragment  # noqa: E402
from memory_config import read_rating_mode  # noqa: E402


# ==================== Entry 数据结构 ====================

@dataclass
class Entry:
    """统一抽象：一个 markdown 条目（Step / Q / G / F / R）。

    body 含 frontmatter 行 + heading + body 全文（原样保留，便于 self-contained 切片）。
    """
    entry_id: str        # "Step 12" / "Q-001" / "G-003" / "F-001" / "R-001"
    title: str           # heading 剩余部分
    date: str | None     # YYYY-MM-DD（缺则 None）
    source_file: str     # 原 markdown 文件名（短名，如 "执行日志.md"）
    raw: str             # heading + body 全文
    fields: dict[str, str] = field(default_factory=dict)  # 解析出来的 inline frontmatter


# ==================== 文件扫描 + 条目切分 ====================

# heading 正则（Step / Q-NNN / G-NNN / F-NNN / R-NNN，以及新时间戳形式）
# MULTILINE 让 ^/$ 跨行匹配（finditer 扫整个文件文本）
# 冒号 + 标题部分是可选 —— 容错"## Step 1"（无冒号无标题）和"## Step 1: 标题"两种格式
# ID 文法（双认 legacy + 时间戳）由 step_id.id_label_fragment 单一托管，避免漂移。
_HEAD_FILES = {
    "Step": "执行日志.md",
    "Q":    "决策日志.md",
    "G":    "踩坑日志.md",
    "F":    "skill-feedback.md",
    "R":    "改进建议.md",
}
HEAD_PATTERNS: dict[str, tuple[str, re.Pattern[str]]] = {
    kind: (
        filename,
        re.compile(
            rf"^##\s+({id_label_fragment(kind)})(?:\s*[：:]\s*(.+?))?\s*$",
            re.MULTILINE,
        ),
    )
    for kind, filename in _HEAD_FILES.items()
}

# inline frontmatter 行（key: value）—— 用于解析 date / subject / status 等
RE_INLINE_FIELD = re.compile(r"^([A-Za-z_一-鿿][A-Za-z0-9_一-鿿]*)\s*[:：]\s*(.+?)\s*$")


def _strip_field_value(raw: str) -> str:
    """剥字段值：引号包裹的取引号内内容（保护 verbatim 原话里合法的 `#`）；
    非引号值剥掉行内 ` #` 注释（YAML 惯例：`#` 前需空白）。

    修 `subject_confidence: high   # L1 显式提及…` 被读成 `high   # …` → 漏筛 F 的 bug。
    """
    raw = raw.strip()
    if raw[:1] in ('"', "'"):
        q = raw[0]
        end = raw.find(q, 1)
        return raw[1:end] if end != -1 else raw[1:]
    m = re.search(r"\s#", raw)
    if m:
        raw = raw[: m.start()]
    return raw.strip().strip('"').strip("'")


def _parse_entry_fields(body: str) -> dict[str, str]:
    """解析条目顶部的 frontmatter / inline 字段。

    支持两种格式：
    - **inline**：heading 后紧跟 `key: value` 行，遇空行或 `###` 停（schema 文档示例风格）
    - **YAML frontmatter 块**：heading 后 `---` ... `---` 包围（fixture / 实际 F-NNN 风格）

    解析器先跳过空行找内容，遇 `---` 进入 frontmatter 块模式，关闭后继续扫 inline 字段
    直到遇 `###` 子标题。同一字段后写覆盖前写。
    """
    fields: dict[str, str] = {}
    lines = body.splitlines()[1:]  # 跳过 heading 那行
    i = 0
    n = len(lines)

    # 先跳过开头空行
    while i < n and not lines[i].strip():
        i += 1

    # 如果是 YAML frontmatter 块（--- 包围）
    if i < n and lines[i].strip() == "---":
        i += 1
        while i < n:
            line = lines[i]
            if line.strip() == "---":
                i += 1
                break
            m = RE_INLINE_FIELD.match(line)
            if m:
                key = m.group(1).strip()
                value = _strip_field_value(m.group(2))
                fields[key] = value
            i += 1

    # 继续扫 inline 字段（遇 ### / 第二个空行块 / 第二个 --- 停）
    saw_blank = False
    while i < n:
        line = lines[i]
        if line.startswith("###"):
            break
        if line.strip() == "---":
            # body 中的水平线（条目分隔），停止
            break
        if not line.strip():
            if saw_blank:
                break  # 第二个连续空行 = 内容结束
            saw_blank = True
            i += 1
            continue
        saw_blank = False
        m = RE_INLINE_FIELD.match(line)
        if m:
            key = m.group(1).strip()
            value = _strip_field_value(m.group(2))
            # 已存在的字段不覆盖（frontmatter 优先）
            fields.setdefault(key, value)
        i += 1

    return fields


def _split_entries(text: str, head_re: re.Pattern[str], source_file: str) -> list[Entry]:
    """按 heading 切分条目，每条含 heading + body 直到下一个同级 heading。"""
    heads = list(head_re.finditer(text))
    result: list[Entry] = []
    for i, m in enumerate(heads):
        start = m.start()
        end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        raw = text[start:end].rstrip() + "\n"
        fields = _parse_entry_fields(raw)
        # 日期字段（中英文 key 都试）
        entry_date = fields.get("日期") or fields.get("date") or None
        if entry_date:
            # 兜底校验
            try:
                date.fromisoformat(entry_date)
            except ValueError:
                entry_date = None
        result.append(Entry(
            entry_id=m.group(1),
            title=m.group(2) or "",  # 容错：可选标题缺失时是 None
            date=entry_date,
            source_file=source_file,
            raw=raw,
            fields=fields,
        ))
    return result


def _record_to_entry(record: dict) -> Entry:
    """JSONL Step record → distill `Entry`（dual-read 迁移第 1 步，叠加 md 不替换）。

    raw body 经 step_dualread 合成，含 render_full / render_misalignment / diff_score
    grep 的子串（`差值：<delta>` / `顺畅度：<n>`）；fields 填 about/status 供
    is_misalignment_step / step_about 读取。source_file 标 jsonl 以区分来源。
    """
    rec_date = record.get("date")
    rec_date = rec_date if isinstance(rec_date, str) else None
    about = str(record.get("about") or "project")
    status = str(record.get("status") or "")
    return Entry(
        entry_id=str(record.get("record_id") or "Step ?"),
        title=str(record.get("title") or ""),
        date=rec_date,
        source_file="执行日志.jsonl",
        raw=step_dualread.record_to_md_body(record),
        fields={"about": about, "status": status,
                **({"日期": rec_date} if rec_date else {})},
    )


def _iter_memory_files(kdev_dir: Path, prefix: str) -> Iterable[Path]:
    """主文件（shared 解析）+ 归档目录下同前缀 markdown。"""
    base = shared_dir(kdev_dir)
    main = base / f"{prefix}.md"
    if main.is_file():
        yield main
    archive = base / "归档"
    if archive.is_dir():
        yield from sorted(archive.glob(f"{prefix}-*.md"))


def collect_entries(kdev_dir: Path) -> list[Entry]:
    """扫所有核心 markdown + 归档（shared 解析）+ per-员工 Step 日志。"""
    entries: list[Entry] = []
    for kind, (filename, head_re) in HEAD_PATTERNS.items():
        prefix = filename.removesuffix(".md")
        for path in _iter_memory_files(kdev_dir, prefix):
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            entries.extend(_split_entries(text, head_re, path.name))
    # per-员工 scope Step（flat 下 staff_log_files 返回 []）
    step_head_re = HEAD_PATTERNS["Step"][1]
    for scope_id, path in staff_log_files("执行日志.md", kdev_dir):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        entries.extend(_split_entries(text, step_head_re, path.name))

    # dual-read：jsonl 主账 Step 叠加（md 不替换；jsonl 空 → read_steps 返回 [] → 零叠加）。
    # 去重键 = (entry_id, date)，md 优先；shared + 每个 staff scope 都并入。
    seen_steps = {(e.entry_id, e.date) for e in entries if e.entry_id.split()[:1] == ["Step"]}
    for rec in step_log.read_steps(root=kdev_dir):
        if is_fallback_status(str(rec.get("status") or "")):
            continue   # 降级 Step 是机械骨架、未经 LLM 提炼，不进任何数据集切片（升格后才有价值）
        e = _record_to_entry(rec)
        if (e.entry_id, e.date) in seen_steps:
            continue
        seen_steps.add((e.entry_id, e.date))
        entries.append(e)
    if _scope.is_scoped(kdev_dir):
        for scope_id in _scope.list_staff(kdev_dir):
            for rec in step_log.read_steps(scope=scope_id, root=kdev_dir):
                e = _record_to_entry(rec)
                if (e.entry_id, e.date) in seen_steps:
                    continue
                seen_steps.add((e.entry_id, e.date))
                entries.append(e)
    return entries


# ==================== 切片过滤器 ====================

# 差值字段：支持"差值：+2"和"差值 +2"两种格式（冒号可选）
RE_DIFF_VALUE = re.compile(r"差值\s*(?:[:：]\s*)?([+-]?\d+(?:\.\d+)?)")


def diff_score(body: str) -> float | None:
    """从评分差异分析段提取差值，绝对值返回。"""
    m = RE_DIFF_VALUE.search(body)
    return abs(float(m.group(1))) if m else None


def step_about(entry: Entry) -> str:
    """Step 的 about 字段（缺省 project）。"""
    return entry.fields.get("about", "project")


def is_misalignment_step(entry: Entry, threshold: float = 1.5) -> bool:
    """筛 misalignment Step：差值 ≥ threshold + subject = project + 未 voided。"""
    if entry.entry_id.split()[0] != "Step":
        return False
    if step_about(entry) != "project":
        return False
    _status = entry.fields.get("status", "")
    warn_unknown_status(_status, entry_id=entry.entry_id)
    if is_voided_status(_status):
        return False
    diff = diff_score(entry.raw)
    return diff is not None and diff >= threshold


def is_skill_feedback_high(entry: Entry) -> bool:
    """筛 skill-feedback 切片：F 条目 + subject != unknown + subject_confidence=high + verbatim 非空。"""
    # 双认 legacy `F-001` 与时间戳形 `F 20260613-…`，与本文件 ~380 行计数口径一致（Q-020）
    if not (entry.entry_id.startswith("F-") or entry.entry_id.startswith("F ")):
        return False
    subject = entry.fields.get("subject", "").strip()
    if not subject or subject == "unknown":
        return False
    if entry.fields.get("subject_confidence", "").lower() != "high":
        return False
    verbatim = entry.fields.get("verbatim", "").strip()
    if not verbatim or verbatim in ('""', "''", "null"):
        return False
    return True


def subject_slug(subject: str) -> str:
    """subject 标识符 → 文件名 safe slug。

    `plugin:kdev-memory` → `plugin-kdev-memory`
    `skill:brainstorming` → `skill-brainstorming`
    `plugin:kdev-memory/skill:kdev-memory` → `plugin-kdev-memory--skill-kdev-memory`
    """
    s = subject.replace("/", "--").replace(":", "-")
    # 容错：移除非法文件名字符
    s = re.sub(r"[^\w.-]+", "-", s, flags=re.UNICODE)
    return s.strip("-").lower()


# ==================== 渲染器 ====================

def _entry_sort_key(entry: Entry) -> tuple[date, str]:
    """按日期升序，同日按 entry_id 字典序。无日期的排到最末（用一个未来日期）。"""
    if entry.date:
        try:
            d = date.fromisoformat(entry.date)
        except ValueError:
            d = date(9999, 12, 31)
    else:
        d = date(9999, 12, 31)
    return (d, entry.entry_id)


def render_full(entries: list[Entry]) -> str:
    """dataset-full.md：全量按日期排，每条加来源标记。"""
    sorted_entries = sorted(entries, key=_entry_sort_key)
    parts: list[str] = [
        "# kdev-memory dataset-full",
        "",
        f"全量条目按日期升序交织。共 {len(sorted_entries)} 条。",
        "",
        "格式：每条前用 `### [来源：<文件>]` 标记原文件。条目原文 self-contained 保留 frontmatter 字段。",
        "",
        "---",
        "",
    ]
    for entry in sorted_entries:
        parts.append(f"### [来源：{entry.source_file}]")
        parts.append("")
        parts.append(entry.raw.rstrip())
        parts.append("")
    return "\n".join(parts) + "\n"


def render_misalignment(entries: list[Entry], rating_mode: str = "user-opt-in") -> str:
    """dataset-misalignment.md：差值 ≥ 1.5 的 Step。

    rating_mode=model-only 时无用户评分数据源 → 切片通常为空，追加自解释说明
    （防"空文件像坏了"误导：这是预期行为，切 user-required 人介入评分后才有料）。
    """
    misalign = sorted(
        (e for e in entries if is_misalignment_step(e)),
        key=_entry_sort_key,
    )
    parts: list[str] = [
        "# kdev-memory dataset-misalignment",
        "",
        f"差值 ≥ 1.5 的 Step（模型自评 vs 用户真实评分的 gap），含完整双评分 + 评分差异分析。共 {len(misalign)} 条。",
        "",
        "**用途**：顶级对齐数据（RLHF / DPO 偏好对 / 修正模型自我评估偏差的训练原料）。",
    ]
    if rating_mode == "model-only":
        parts += [
            "",
            "> ⚠️ **当前 `rating.mode: model-only`（纯模型评分，无用户评分）**——本切片的 gap 依赖"
            "「模型自评 vs 用户真实评分」的差值，model-only 下无用户评分数据源，通常为 0 条。"
            "**这是预期行为，非缺陷**：切 `rating.mode: user-required`（人介入评分）后才会产生 gap 数据。",
        ]
    parts += [
        "",
        "---",
        "",
    ]
    for entry in misalign:
        parts.append(entry.raw.rstrip())
        parts.append("")
    return "\n".join(parts) + "\n"


def render_skill_feedback_by_subject(entries: list[Entry]) -> dict[str, str]:
    """dataset-skill-feedback-by-subject/<slug>.md：F-NNN 按 subject 切片。

    返回 {filename: text} 字典。
    """
    by_subject: dict[str, list[Entry]] = {}
    for entry in entries:
        if not is_skill_feedback_high(entry):
            continue
        subject = entry.fields["subject"]
        by_subject.setdefault(subject, []).append(entry)

    result: dict[str, str] = {}
    for subject, items in sorted(by_subject.items()):
        slug = subject_slug(subject)
        items.sort(key=_entry_sort_key)
        parts: list[str] = [
            f"# skill-feedback: {subject}",
            "",
            f"对 `{subject}` 的反馈条目（subject_confidence=high）。共 {len(items)} 条。",
            "",
            "**用途**：该 subject 自主优化训练集。verbatim 字段保留用户原话，可直接训 RM / 提 RFE / 做指令微调。",
            "",
            "---",
            "",
        ]
        for entry in items:
            parts.append(entry.raw.rstrip())
            parts.append("")
        result[f"{slug}.md"] = "\n".join(parts) + "\n"
    return result


# ==================== 主流程 ====================

@dataclass
class ExportStats:
    files_written: list[str] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=dict)
    sanitize_counts: dict[str, int] = field(default_factory=dict)
    sanitize_status: str = "pending"     # verified | leaks_found | skipped
    leaks: list[tuple[str, str]] = field(default_factory=list)


def export_markdown_slices(
    kdev_dir: Path,
    out_dir: Path,
    do_sanitize: bool = True,
) -> ExportStats:
    """主入口：扫数据 → 渲染三个切片包 → sanitize → 写盘 → 验证。

    out_dir 不存在则创建。原 `.kdev/memory/*.md` **不**修改。
    """
    entries = collect_entries(kdev_dir)
    stats = ExportStats()
    stats.counts["total"] = len(entries)
    stats.counts["step"] = sum(1 for e in entries if e.entry_id.startswith("Step"))
    stats.counts["q"] = sum(1 for e in entries if e.entry_id.startswith("Q-") or e.entry_id.startswith("Q "))
    stats.counts["g"] = sum(1 for e in entries if e.entry_id.startswith("G-") or e.entry_id.startswith("G "))
    stats.counts["f"] = sum(1 for e in entries if e.entry_id.startswith("F-") or e.entry_id.startswith("F "))
    stats.counts["r"] = sum(1 for e in entries if e.entry_id.startswith("R-") or e.entry_id.startswith("R "))

    out_dir.mkdir(parents=True, exist_ok=True)
    by_subject_dir = out_dir / "dataset-skill-feedback-by-subject"
    by_subject_dir.mkdir(parents=True, exist_ok=True)

    # 1. 全量切片
    full_text = render_full(entries)
    # 2. misalignment 切片
    misalign_text = render_misalignment(entries, rating_mode=read_rating_mode(kdev_dir))
    # 3. by-subject 切片
    by_subject_files = render_skill_feedback_by_subject(entries)

    stats.counts["misalignment"] = sum(1 for e in entries if is_misalignment_step(e))
    stats.counts["skill_feedback_high"] = sum(1 for e in entries if is_skill_feedback_high(e))
    stats.counts["subjects"] = len(by_subject_files)

    # sanitize
    if do_sanitize:
        full_result = sanitize_text(full_text)
        misalign_result = sanitize_text(misalign_text)
        for k, v in full_result.counts.items():
            stats.sanitize_counts[k] = stats.sanitize_counts.get(k, 0) + v
        for k, v in misalign_result.counts.items():
            stats.sanitize_counts[k] = stats.sanitize_counts.get(k, 0) + v
        full_text = full_result.text
        misalign_text = misalign_result.text

        sanitized_subject_files: dict[str, str] = {}
        for fname, text in by_subject_files.items():
            res = sanitize_text(text)
            for k, v in res.counts.items():
                stats.sanitize_counts[k] = stats.sanitize_counts.get(k, 0) + v
            sanitized_subject_files[fname] = res.text
        by_subject_files = sanitized_subject_files

    # 写盘
    full_path = out_dir / "dataset-full.md"
    full_path.write_text(full_text, encoding="utf-8")
    stats.files_written.append(str(full_path))

    misalign_path = out_dir / "dataset-misalignment.md"
    misalign_path.write_text(misalign_text, encoding="utf-8")
    stats.files_written.append(str(misalign_path))

    for fname, text in by_subject_files.items():
        fpath = by_subject_dir / fname
        fpath.write_text(text, encoding="utf-8")
        stats.files_written.append(str(fpath))

    # 验证 sanitize 漏脱
    if do_sanitize:
        all_leaks: list[tuple[str, str]] = []
        for fpath in stats.files_written:
            try:
                text = Path(fpath).read_text(encoding="utf-8")
            except OSError:
                continue
            all_leaks.extend(verify_no_leaks(text))
        if all_leaks:
            stats.sanitize_status = "leaks_found"
            stats.leaks = all_leaks
        else:
            stats.sanitize_status = "verified"
    else:
        stats.sanitize_status = "skipped"

    return stats


def _write_failure_warn(kdev: Path, error_msg: str, ctx: str = "auto") -> Path:
    """蒸馏失败时写 WARN-distill-failed-*.md，下次 SessionStart brief 显眼提醒。

    格式：跟 SessionEnd 的 WARN-未记录-*.md 一致（顶层 .kdev/memory/ 文件，glob 扫描可见）。
    """
    ts = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    warn_path = kdev / f"WARN-distill-failed-{ts}.md"
    body = (
        f"# 蒸馏失败警告（{ctx}）\n\n"
        f"时间：{datetime.now().isoformat(timespec='seconds')}\n"
        f"触发场景：{ctx}（auto = 后台自动跑 / manual = 用户主动跑）\n\n"
        f"## 错误信息\n\n```\n{error_msg}\n```\n\n"
        f"## 处理建议\n\n"
        f"1. 看上面错误信息定位原因（常见：fixture 解析失败 / 写盘权限 / sanitize 漏脱）\n"
        f"2. 修复后手动跑：`python3 ${{CLAUDE_PLUGIN_ROOT}}/hooks/lib/distill.py`\n"
        f"3. 跑成功后删除本 WARN 文件\n"
    )
    try:
        warn_path.write_text(body, encoding="utf-8")
    except OSError:
        pass
    return warn_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="kdev-memory markdown 切片导出（决策 3：不引入 JSONL）",
    )
    parser.add_argument("kdev_dir", nargs="?", default=".kdev/memory")
    parser.add_argument("--out", default=None, help="输出目录（默认 <kdev_dir>/dataset）")
    parser.add_argument(
        "--no-sanitize", action="store_true",
        help="跳过 PII 脱敏（仅测试/debug 用，分享数据集前严禁开）",
    )
    parser.add_argument(
        "--auto-context", action="store_true",
        help="标记本次是自动触发（影响 WARN 文件命名 + .last-distill-auto 标记）",
    )
    parser.add_argument(
        "--skip-promote", action="store_true",
        help="占位参数（distill.py 本身只跑 dataset 阶段，promote 由命令模板处理；保留参数兼容命令模板传入）",
    )
    args = parser.parse_args()

    kdev = Path(args.kdev_dir)
    if not kdev.is_dir():
        print(f"[distill] {kdev} 不存在或不是目录", file=sys.stderr)
        return 2

    out = Path(args.out) if args.out else kdev / "dataset"
    ctx = "auto" if args.auto_context else "manual"

    try:
        stats = export_markdown_slices(kdev, out, do_sanitize=not args.no_sanitize)
    except Exception as e:
        # 失败时写 WARN 文件，让下次 SessionStart 能显眼提醒
        warn = _write_failure_warn(kdev, f"{type(e).__name__}: {e}", ctx=ctx)
        print(f"[distill] 失败：{e}", file=sys.stderr)
        print(f"[distill] 已写 WARN：{warn}", file=sys.stderr)
        return 4

    print(f"# distill 完成（{datetime.now().isoformat(timespec='seconds')}）")
    print()
    print(f"**输出目录**：{out}")
    print()
    print("## 条目统计")
    for k in ("total", "step", "q", "g", "f", "r", "misalignment", "skill_feedback_high", "subjects"):
        print(f"- {k}: {stats.counts.get(k, 0)}")
    print()
    print("## 产出文件")
    for fp in stats.files_written:
        try:
            size = Path(fp).stat().st_size
            print(f"- {fp} ({size} bytes)")
        except OSError:
            print(f"- {fp}")
    print()
    print(f"## sanitize 状态：{stats.sanitize_status}")
    if stats.sanitize_counts:
        for k, v in sorted(stats.sanitize_counts.items()):
            print(f"- {k}: {v}")
    if stats.leaks:
        print()
        print("⚠️ 漏脱（请检查 sanitize 规则）：")
        for name, snippet in stats.leaks[:10]:
            print(f"- {name}: {snippet[:60]}")

    # 成功时 touch 蒸馏时间戳（auto 模式额外 touch .last-distill-auto 标记）
    if stats.sanitize_status != "leaks_found":
        try:
            (kdev / ".last-distill").touch()
            if args.auto_context:
                (kdev / ".last-distill-auto").touch()
        except OSError as e:
            print(f"[distill] 警告：无法 touch .last-distill：{e}", file=sys.stderr)
        return 0
    return 3


if __name__ == "__main__":
    sys.exit(main())
