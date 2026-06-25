# hooks/lib/step_log.py
"""kdev-memory 叙事 Step JSONL 主账唯一读写封装点（Q-20260617）。

格式只有这一处知道：所有 reader / recorder / 迁移 / checkpoint 都过它，
防 7 处各写 JSON 解析。路径解析复用 scope.py（flat / scoped 不变量）。
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import List, Optional, Union

import scope as _scope

PathLike = Union[Path, str]
DEFAULT_ROOT = Path(".kdev/memory")
SCHEMA_VERSION = 1

_ABOUT_RE = re.compile(r"^(project|feature/.+|bugfix/.+)$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_GENERIC_TITLE_RE = re.compile(r"^(实现|完成|添加|做了|搞)了?$")
_PLACEHOLDER_DEDUCTION = {"", "无", "无明显问题", "待补", "TBD", "—", "-"}
_WATER_DECISIONS = {"按既有规范", "按 plan", "无特殊决策", "见 commit"}
_STATUS_OK = {"open", "scored", "voided-faded"}


class StepValidationError(ValueError):
    """Step record 不满足 schema / hard-gate。"""


def jsonl_path(scope: Optional[str] = None, root: PathLike = DEFAULT_ROOT) -> Path:
    return _scope.recorder_target_jsonl(scope, root).with_name("执行日志.jsonl")


def _status_ok(status: str) -> bool:
    return status in _STATUS_OK or status.startswith("voided-r-")


def validate(record: dict) -> None:
    """7 hard-gate 的确定性子集 + 结构守门。语义判断（ghost SHA 等 git IO）留 recorder。"""
    if record.get("type") != "Step":
        raise StepValidationError("type 必须为 'Step'")
    for key in ("record_id", "title", "date", "about", "status"):
        if not isinstance(record.get(key), str) or not record[key].strip():
            raise StepValidationError(f"缺字段或非字符串：{key}")
    if not _DATE_RE.match(record["date"]):
        raise StepValidationError(f"date 格式应为 YYYY-MM-DD：{record['date']}")
    if not _ABOUT_RE.match(record["about"]):  # gate 7
        raise StepValidationError(f"about 不合 schema（project|feature/<x>|bugfix/<x>）：{record['about']}")
    if _GENERIC_TITLE_RE.match(record["title"].strip()):  # gate 1
        raise StepValidationError(f"title 过泛（无具体对象）：{record['title']}")
    triggers = record.get("triggers")
    if not isinstance(triggers, list) or len(triggers) < 5:  # gate 4
        raise StepValidationError("triggers 须为 list 且 ≥5 个关键词")
    kf = record.get("key_facts")
    if not isinstance(kf, dict):
        raise StepValidationError("缺 key_facts 对象")
    if not isinstance(kf.get("tools_invoked_count"), int) or kf["tools_invoked_count"] < 1:  # gate 6a
        raise StepValidationError("key_facts.tools_invoked_count 须为 ≥1 的整数")
    if not isinstance(kf.get("errors_hit"), int) or kf["errors_hit"] < 0:  # gate 6b
        raise StepValidationError("key_facts.errors_hit 须为非负整数")
    kd = kf.get("key_decisions") or []
    if kd and all(str(d).strip() in _WATER_DECISIONS for d in kd):  # gate 5
        raise StepValidationError("key_decisions 全是水话（按既有规范 / 见 commit 等）")
    me = record.get("model_eval")
    if not isinstance(me, dict):
        raise StepValidationError("缺 model_eval 对象")
    if str(me.get("deduction", "")).strip() in _PLACEHOLDER_DEDUCTION:  # gate 2
        raise StepValidationError("model_eval.deduction 为空/占位")
    if not isinstance(record.get("user_rating"), dict):
        raise StepValidationError("缺 user_rating 对象")
    if not _status_ok(record["status"]):
        raise StepValidationError(f"status 非法枚举：{record['status']}")


def append_step(record: dict, *, scope: Optional[str] = None, root: PathLike = DEFAULT_ROOT) -> None:
    record.setdefault("schema_version", SCHEMA_VERSION)
    record.setdefault("type", "Step")
    validate(record)
    path = jsonl_path(scope, root)
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, ensure_ascii=False, sort_keys=False) + "\n"
    # 单行 O_APPEND 在 POSIX 上对 < PIPE_BUF 的写是原子的，避免并发交错
    with open(path, "a", encoding="utf-8") as f:
        f.write(line)


def read_steps(*, scope: Optional[str] = None, root: PathLike = DEFAULT_ROOT) -> List[dict]:
    path = jsonl_path(scope, root)
    if not path.is_file():
        return []
    out: List[dict] = []
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except ValueError:
            continue  # 坏行跳过（健壮性）
        if isinstance(obj, dict):
            out.append(obj)
    return out


def steps_for_date(date: str, *, scope: Optional[str] = None, root: PathLike = DEFAULT_ROOT) -> List[dict]:
    return [s for s in read_steps(scope=scope, root=root) if s.get("date") == date]
