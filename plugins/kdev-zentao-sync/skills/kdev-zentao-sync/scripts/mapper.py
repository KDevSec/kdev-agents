"""CaseRecord / defects 行 / testtask 参数 → 禅道 v1 payload。纯映射，不碰网络。"""
from __future__ import annotations

import html

from case_md_parser import CaseRecord

CASE_TYPE_DEFAULT = "feature"          # 禅道用例 type 维度（与"基本流/异常流"不同维度）
_TITLE_MAX = 255
_BUG_TITLE_MAX = 255                    # 禅道 bug title 上限 255（超出会 loud 400）；本实例 v1 丢 steps/keywords，title 是唯一持久自由文本字段


def _html_escape(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace("\n", "<br/>"))


def _zentao_title_len(s: str) -> int:
    """禅道存储 title 时按 htmlspecialchars(ENT_QUOTES) 转义后再校验长度 ≤255。
    实测（2026-06-28）：含 `'`/`"`/`&`/`<`/`>` 的 title 转义后膨胀（如 `'`→`&#x27;` +4），
    裸 255 字符也会被拒（escaped>255）→ 截断须按转义后长度算，不能按裸字符数。"""
    return len(html.escape(s, quote=True))


def _truncate_zentao_title(title: str, limit: int = _BUG_TITLE_MAX) -> str:
    """按「转义后长度 ≤ limit」截断 raw title（[TC-ID] 锚点在最前，只切尾加省略号）。"""
    if _zentao_title_len(title) <= limit:
        return title
    lo, hi, best = 0, len(title), ""
    while lo <= hi:
        mid = (lo + hi) // 2
        cand = title[:mid].rstrip() + "…"
        if _zentao_title_len(cand) <= limit:
            best, lo = cand, mid + 1
        else:
            hi = mid - 1
    return best or "…"


def build_case_title(rec: CaseRecord) -> str:
    t = rec.title.strip()
    return t if len(t) <= _TITLE_MAX else t[: _TITLE_MAX - 1] + "…"


def base_ar(ar: str) -> str:
    """取 AR 主键（去掉标题描述/多余空白）：'AR-PRL-FUN-01.001.00：查看…' -> 'AR-PRL-FUN-01.001.00'。"""
    return ar.split("：", 1)[0].split(":", 1)[0].strip() if ar else ""


def case_to_testcase_payload(rec: CaseRecord, product: int, module_id: int,
                             ar2story: dict[str, int] | None = None,
                             name2module: dict[str, int] | None = None,
                             ar2module: dict[str, int] | None = None) -> dict:
    # 订正映射：每条测试步骤 → 一个 step 行(expect 空)；整块预期合并挂最后一步 expect。
    steps = [{"desc": s, "expect": ""} for s in rec.steps] or [{"desc": "", "expect": ""}]
    expect_block = "\n".join(f"{i}. {e}" for i, e in enumerate(rec.expects, 1))
    steps[-1]["expect"] = expect_block
    keywords = " ".join(x for x in [rec.tc_id, rec.case_kind] if x)
    try:
        pri = int(rec.pri)
    except (ValueError, TypeError):
        pri = 3
    # 所属模块：优先按 md 文本名映射到禅道模块 id；次选回退到该用例对应需求(story)所在模块
    # （用例库与 story 共用同一棵模块树，绕开 /browse 查 id）；再不行用 module_id（CLI 默认/根 0）。
    module = module_id
    if name2module and rec.module in name2module:
        module = name2module[rec.module]
    elif ar2module and base_ar(rec.ar) in ar2module:
        module = ar2module[base_ar(rec.ar)]
    # 对应需求：按 AR 主键匹配需求库 story id；未命中留 0（不关联）。
    story = (ar2story or {}).get(base_ar(rec.ar), 0)
    payload = {
        "product": product,
        "module": module,
        "title": build_case_title(rec),
        "pri": pri,
        "type": CASE_TYPE_DEFAULT,
        "precondition": "\n".join(rec.preconditions),
        "keywords": keywords,
        "steps": steps,
    }
    if story:
        payload["story"] = story
    return payload


def _bug_steps_html(row: dict) -> str:
    parts = [
        f"<p><b>用例ID</b>: {_html_escape(row.get('用例ID',''))}</p>",
        f"<p><b>用例函数</b>: {_html_escape(row.get('用例函数',''))}</p>",
        f"<p><b>原因分类</b>: {_html_escape(row.get('原因分类',''))}</p>",
        f"<p><b>失败摘要</b>:<br/>{_html_escape(row.get('失败摘要',''))}</p>",
        f"<p><b>失败时间</b>: {_html_escape(row.get('时间',''))}</p>",
    ]
    if row.get("截图"):
        # v1 REST 无文件上传端点（实测 404）→ 仅据实记路径，不假装"见附件"
        parts.append(f"<p><b>截图路径</b>(v1 无法上传附件，按路径留存): {_html_escape(row['截图'])}</p>")
    if row.get("日志文件"):
        parts.append(f"<p><b>日志</b>: {_html_escape(row['日志文件'])}</p>")
    return "".join(parts)


def bug_row_to_payload(row: dict, product: int, build: str) -> dict:
    # 本实例 v1 bug create 丢弃 steps/keywords（实测），title 是唯一持久的自由文本字段
    # → 把分诊关键信息（用例名/原因分类/失败摘要）打进 title。[TC-ID] 恒在最前(去重锚点,
    # 截断只切尾)。steps 仍构造发送：对支持 steps 的实例有效、本实例无害(被丢);全量明细另
    # 在本地 defects CSV / reports 留存。
    name = row.get("用例名称", "").strip()
    parts = [f"[{row.get('用例ID', '')}] {name}"]
    cause = row.get("原因分类", "").strip()
    summary = row.get("失败摘要", "").strip().replace("\n", " ")
    if cause:
        parts.append(cause)
    if summary:
        parts.append(summary)
    title = _truncate_zentao_title(" | ".join(parts))
    return {
        "product": product, "title": title, "type": "codeerror",
        "severity": 3, "pri": 3, "steps": _bug_steps_html(row),
        "openedBuild": build,
    }


def testtask_payload(name: str, product: int, project: int, build: str,
                     owner: str, begin: str, end: str, desc: str = "") -> dict:
    return {
        "name": name, "product": product, "project": project,
        "build": build, "owner": owner, "begin": begin, "end": end, "desc": desc,
    }
