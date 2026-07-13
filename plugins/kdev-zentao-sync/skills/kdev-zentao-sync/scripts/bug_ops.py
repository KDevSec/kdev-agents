# scripts/bug_ops.py
"""纯函数：bug 过滤（query-bugs）+ junit 结果解析 + 回归对照（regress-bugs）。

全部无网络、无文件 IO（parse_junit_text 吃字符串），便于离线单测。
IO（拉 bug、读 junit 文件、落报告）留在 sync.py 的 cmd_* 编排里。

设计要点：
- **规范化 TC 键**：禅道 bug 标题里是 `TC-AR0100100-G3-003` / 多条 `TC-API-AR0300100-G2-006/007/008`；
  junit testcase name 是 `test_ar0100100_g3_003_xxx`。两者规范化到同一 canonical 键
  `AR{arnum}-G{g}-{nnn}`（去掉 TC-/API- 前缀、g 去前导零、nnn 补三位）→ 才能对照。
  规范化**刻意抹掉 API- 泳道标记**：同一 AR-G-用例在 UI/API 两泳道结构相同，泳道隔离由
  调用方给对的 junit + `--tc-prefix` 过滤 bug 保证，不靠 canonical 键区分。
- **多 TC bug**：`G2-006/007/008` 展开成三条 canonical；bug 回归判定按最坏态聚合。
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET

# 禅道 bug 标题里的 TC 段：单条或斜杠多条尾号，含可选 API- 泳道标记。
_BUG_AR_RE = re.compile(r"\[TC-(?:API-)?AR(\d+)-G(\d+)-(\d+(?:/\d+)*)\]")
_BUG_TC_RE = re.compile(r"\[TC-(\d+)\]")  # 旧式 test_tcNNN
# junit testcase name 里的 AR 段（对齐 playwrighttest/apitest conftest `_extract_tc`）。
_NODE_AR_RE = re.compile(r"test_ar(\d+)_g(\d+)_(\d+)")
_NODE_TC_RE = re.compile(r"test_tc(\d+)")

_STATUS_RANK = {"failed": 3, "skipped": 2, "passed": 1}  # 同键多 testcase 取最坏


def account_of(v):
    """禅道字段 openedBy/resolvedBy 可能是 dict（含 account）或裸字符串 → 归一成账号字符串。"""
    if isinstance(v, dict):
        return v.get("account") or v.get("realname") or v.get("name") or ""
    return v or ""


def bug_tc_id(title: str) -> str:
    """bug 标题里的第一个 TC-ID 原文（展示用，保留 TC-/API- 前缀）；无则空串。"""
    m = re.search(r"\[(TC-[^\]]+?)\]", title or "")
    return m.group(1) if m else ""


def canon_bug_tcs(title: str) -> list[str]:
    """bug 标题 → 规范化 canonical TC 键列表（多条/斜杠范围已展开）。"""
    out: list[str] = []
    for m in _BUG_AR_RE.finditer(title or ""):
        ar, g, tail = m.group(1), m.group(2), m.group(3)
        for n in tail.split("/"):
            out.append(f"AR{ar}-G{int(g)}-{int(n):03d}")
    for m in _BUG_TC_RE.finditer(title or ""):
        out.append(f"TC{int(m.group(1))}")
    return out


def canon_node(name: str) -> str | None:
    """junit testcase name → 规范化 canonical TC 键；不匹配返回 None。"""
    m = _NODE_AR_RE.match(name or "")
    if m:
        return f"AR{m.group(1)}-G{int(m.group(2))}-{int(m.group(3)):03d}"
    m = _NODE_TC_RE.match(name or "")
    if m:
        return f"TC{int(m.group(1))}"
    return None


# ---------------------------------------------------------------- query 过滤
def filter_bugs(bugs, *, status="", opened_by="", module=None,
                tc_prefix="", title_contains="", resolution=""):
    """按 status/opened_by/module/tc_prefix/title_contains/resolution 过滤 bug 列表。

    status/resolution 支持逗号分隔多值；空 = 不过滤该维度。tc_prefix 匹配 bug 标题里的
    TC-ID 原文前缀（如 `TC-AR` 只留 UI 泳道、`TC-API` 只留 API 泳道）。
    """
    status_set = {s.strip() for s in status.split(",") if s.strip()}
    reso_set = {s.strip() for s in resolution.split(",") if s.strip()}
    out = []
    for b in bugs:
        if status_set and b.get("status") not in status_set:
            continue
        if reso_set and (b.get("resolution") or "") not in reso_set:
            continue
        if opened_by and account_of(b.get("openedBy")) != opened_by:
            continue
        if module is not None and str(b.get("module")) != str(module):
            continue
        title = b.get("title", "") or ""
        if title_contains and title_contains not in title:
            continue
        if tc_prefix and not bug_tc_id(title).startswith(tc_prefix):
            continue
        out.append(b)
    return out


# ---------------------------------------------------------------- junit 解析
def parse_junit_text(xml_text: str) -> dict[str, dict]:
    """junit XML 文本 → {canonical TC 键: {"status": passed|failed|skipped, "message": str, "node": name}}。

    同一 canonical 键出现多个 testcase 时取最坏态（failed>skipped>passed）。
    无法解析出 canonical 的 testcase（非 AR/tc 命名）跳过、计入 unmatched（调用方可 surface）。
    """
    root = ET.fromstring(xml_text)
    out: dict[str, dict] = {}
    for tc in root.iter("testcase"):
        name = tc.get("name", "")
        key = canon_node(name)
        if key is None:
            continue
        child = tc.find("failure")
        if child is None:
            child = tc.find("error")
        if child is not None:
            status, message = "failed", (child.get("message") or "").strip()
        else:
            sk = tc.find("skipped")
            if sk is not None:
                status, message = "skipped", (sk.get("message") or "").strip()
            else:
                status, message = "passed", ""
        prev = out.get(key)
        if prev is None or _STATUS_RANK[status] > _STATUS_RANK[prev["status"]]:
            out[key] = {"status": status, "message": message, "node": name}
    return out


def junit_unmatched_count(xml_text: str) -> int:
    """junit 里无法映射到 canonical 键的 testcase 数（命名不符 AR/tc 规则）——供 Fail Loud surface。"""
    root = ET.fromstring(xml_text)
    return sum(1 for tc in root.iter("testcase") if canon_node(tc.get("name", "")) is None)


# ---------------------------------------------------------------- 回归对照
# 聚合优先级：任一 FAIL→未过；否则任一 MISSING→用例不在本次结果；否则任一 SKIP→无法回归；全 PASS→通过。
_VERDICT = {
    "FAIL": "🔴 回归未过（修复未生效或被其它缺陷阻挡）",
    "MISSING": "❓ 用例不在本次结果（换套件/未跑该用例）",
    "SKIP": "⚪ 无法回归（依赖未就绪，如环境/数据）",
    "PASS": "✅ 回归通过（可关单）",
    "NO_TC": "⚠️ bug 标题无可解析 TC（人工核对）",
}


def _aggregate(per_tc: list[tuple]) -> str:
    """per_tc = [(canon, result_or_None), ...] → 聚合 verdict 码。"""
    if not per_tc:
        return "NO_TC"
    statuses = [r["status"] if r else "missing" for _, r in per_tc]
    if "failed" in statuses:
        return "FAIL"
    if "missing" in statuses:
        return "MISSING"
    if "skipped" in statuses:
        return "SKIP"
    return "PASS"


def correlate_regression(bugs, results: dict[str, dict]) -> list[dict]:
    """已修复 bug 列表 × junit 结果 → 每条 bug 一个回归判定记录。

    返回 [{id, title, tc_id, canon_tcs, per_tc, verdict_code, verdict_text}, ...]。
    per_tc = [{canon, status, message, node}]，status='missing' 表示该 TC 不在本次 junit。
    """
    out = []
    for b in bugs:
        title = b.get("title", "") or ""
        canon = canon_bug_tcs(title)
        per = [(c, results.get(c)) for c in canon]
        code = _aggregate(per)
        per_tc = [{
            "canon": c,
            "status": (r["status"] if r else "missing"),
            "message": (r["message"] if r else ""),
            "node": (r["node"] if r else ""),
        } for c, r in per]
        out.append({
            "id": b.get("id"),
            "title": title,
            "tc_id": bug_tc_id(title),
            "canon_tcs": canon,
            "per_tc": per_tc,
            "verdict_code": code,
            "verdict_text": _VERDICT[code],
        })
    return out


def verdict_text(code: str) -> str:
    return _VERDICT.get(code, code)
