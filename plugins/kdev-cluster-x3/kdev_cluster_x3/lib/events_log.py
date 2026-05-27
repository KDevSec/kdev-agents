"""events.log append/tail/filter and agent-name → group routing."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional


class EventType(str, Enum):
    STEP_START = "step_start"
    STEP_COMPLETE = "step_complete"
    GATE_PASS = "gate_pass"
    GATE_FAIL = "gate_fail"
    BLOCKED = "blocked"
    COMPLETE = "complete"
    NOTE = "note"


@dataclass(frozen=True)
class Event:
    ts: str
    agent: str
    event_type: str
    msg: str


# 30-agent group routing table. Update in lockstep with agents/ directory.
AGENT_GROUP: dict[str, str] = {
    # orchestrator (1)
    "主控员": "orchestrator",
    # reqs group: 1 TL + 5 workers (6)
    "需求组长": "reqs",
    "需求澄清师": "reqs",
    "需求规格师": "reqs",
    "需求拆解师": "reqs",
    "原型设计师": "reqs",
    "方案设计师": "reqs",
    # dev group: 1 TL + 6 workers (7)
    "开发组长": "dev",
    "环境对齐员": "dev",
    "实施计划师": "dev",
    "TDD实现员": "dev",
    "E2E验收员": "dev",
    "安全扫描员": "dev",
    "部署上线员": "dev",
    # test group: 1 TL + 4 workers (5)
    "测试组长": "test",
    "测试点设计师": "test",
    "测试用例渲染员": "test",
    "UI自动化工程师": "test",
    "API自动化工程师": "test",
    # review group: 1 TL + 10 workers (11)
    "审查组长": "review",
    "SR评审员": "review",
    "原型评审员": "review",
    "方案设计评审员": "review",
    "代码评审员": "review",
    "质量评审员": "review",
    "安全评审员": "review",
    "测试设计评审员": "review",
    "CEO视角评审员": "review",
    "架构评审员": "review",
    "终审聚合员": "review",
}

# Sanity check: table must have exactly 30 entries
assert len(AGENT_GROUP) == 30, f"AGENT_GROUP has {len(AGENT_GROUP)} entries, expected 30"


def agent_to_group(agent: str) -> str:
    if agent not in AGENT_GROUP:
        raise KeyError(f"unknown agent {agent!r}; update AGENT_GROUP table")
    return AGENT_GROUP[agent]


class EventsLog:
    def __init__(self, path: Path):
        self.path = Path(path)

    def append(self, *, agent: str, event_type: EventType, msg: str, ts: Optional[datetime] = None) -> None:
        when = (ts or datetime.now(timezone.utc)).isoformat()
        line = f"{when}\t{agent}\t{event_type.value}\t{msg.replace(chr(10), ' ')}\n"
        with self.path.open("a", encoding="utf-8") as f:
            f.write(line)

    def read_all(self) -> list[Event]:
        if not self.path.exists():
            return []
        events: list[Event] = []
        for raw in self.path.read_text(encoding="utf-8").splitlines():
            if not raw.strip():
                continue
            parts = raw.split("\t", 3)
            if len(parts) != 4:
                continue
            events.append(Event(ts=parts[0], agent=parts[1], event_type=parts[2], msg=parts[3]))
        return events

    def tail(self, n: int) -> list[Event]:
        all_ = self.read_all()
        return all_[-n:]

    def filter(self, *, agent: Optional[str] = None, event_type: Optional[EventType] = None) -> list[Event]:
        out = self.read_all()
        if agent is not None:
            out = [e for e in out if e.agent == agent]
        if event_type is not None:
            out = [e for e in out if e.event_type == event_type.value]
        return out
