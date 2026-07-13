"""解析 kdev 字段化测试用例 .md 的【测试用例信息】块为 CaseRecord 列表。纯函数，不碰网络。"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

BLOCK_MARK = "【测试用例信息】"
# 单行标量字段： "- KEY：VALUE"（全角或半角冒号）
_SCALAR = {
    "用例编号": "tc_id", "用例名称": "title", "需求编号": "ar",
    "需求点名称": "ar_name", "用例类型": "case_kind", "所属模块": "module",
    "项目进程": "process", "优先级": "pri",
}
# 多行列表字段（其后跟缩进的 "  1. ..." 或 "  - ..." 行）
_LIST = {
    "前置条件": "preconditions", "测试步骤": "steps",
    "测试数据": "test_data", "预期结果": "expects",
}
_REMARK_PREFIX = "备注"  # "- 备注（xlsx 源独有字段）：..."

_FIELD_RE = re.compile(r"^- ([^：:]+)[：:]\s*(.*)$")
_ITEM_RE = re.compile(r"^\s+(?:\d+\.|-)\s*(.*)$")  # "  1. x" 或 "  - x"


@dataclass
class CaseRecord:
    tc_id: str = ""
    title: str = ""
    ar: str = ""
    ar_name: str = ""
    case_kind: str = ""
    module: str = ""
    process: str = ""
    pri: str = ""
    preconditions: list[str] = field(default_factory=list)
    steps: list[str] = field(default_factory=list)
    test_data: list[str] = field(default_factory=list)
    expects: list[str] = field(default_factory=list)
    remark: str = ""


def _split_blocks(text: str) -> list[list[str]]:
    blocks: list[list[str]] = []
    cur: list[str] | None = None
    for line in text.splitlines():
        if line.strip() == BLOCK_MARK:
            if cur is not None:
                blocks.append(cur)
            cur = []
            continue
        if cur is not None:
            # 块在下一个 marker / 围栏 ``` / 分隔 --- 处自然结束
            if line.strip().startswith("```") or line.strip() == "---":
                blocks.append(cur)
                cur = None
                continue
            cur.append(line)
    if cur is not None:
        blocks.append(cur)
    return blocks


def _parse_block(lines: list[str]) -> CaseRecord:
    rec = CaseRecord()
    active_list: list[str] | None = None
    for line in lines:
        item = _ITEM_RE.match(line)
        if item and active_list is not None:
            val = item.group(1).strip()
            if val:
                active_list.append(val)
            continue
        m = _FIELD_RE.match(line)
        if not m:
            continue
        key, inline = m.group(1).strip(), m.group(2).strip()
        if key in _SCALAR:
            setattr(rec, _SCALAR[key], inline)
            active_list = None
        elif key in _LIST:
            active_list = getattr(rec, _LIST[key])
        elif key.startswith(_REMARK_PREFIX):
            rec.remark = inline
            active_list = None
        else:
            active_list = None
    return rec


def parse_cases(text: str) -> list[CaseRecord]:
    return [_parse_block(b) for b in _split_blocks(text) if b]
