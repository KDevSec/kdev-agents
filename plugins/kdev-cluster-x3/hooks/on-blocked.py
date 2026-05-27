#!/usr/bin/env python3
"""kdev-cluster-x3 BLOCKED event hook.

Trigger: any time events.log is appended (PostToolUse on Write).
Effect: if last line is `blocked` and not yet dispatched (dedup via state file),
print a dispatch directive to stdout — Claude Code will inject this as a user-side message,
so the main session's 主控员 then dispatches the relevant group lead.

Dedup: tracks last-handled line offset in .kdev/.on-blocked-cursor.
"""
from __future__ import annotations
from pathlib import Path
import sys

THIS = Path(__file__).resolve()
sys.path.insert(0, str(THIS.parent))
from lib.event_router import lead_for  # noqa: E402

EVENTS_LOG = Path(".kdev/events.log")
CURSOR = Path(".kdev/.on-blocked-cursor")


def main() -> int:
    if not EVENTS_LOG.exists():
        return 0
    text = EVENTS_LOG.read_text(encoding="utf-8")
    if not text.strip():
        return 0
    last_offset = CURSOR.read_text(encoding="utf-8").strip() if CURSOR.exists() else ""
    current_offset = str(EVENTS_LOG.stat().st_size)
    if last_offset == current_offset:
        return 0
    last_line = text.rstrip("\n").splitlines()[-1]
    parts = last_line.split("\t", 3)
    if len(parts) != 4:
        CURSOR.write_text(current_offset, encoding="utf-8")
        return 0
    ts, agent, event_type, msg = parts
    if event_type != "blocked":
        CURSOR.write_text(current_offset, encoding="utf-8")
        return 0
    lead = lead_for(agent)
    if lead is None:
        CURSOR.write_text(current_offset, encoding="utf-8")
        return 0
    # Emit a directive — Claude Code captures stdout and surfaces it.
    print(f"""
\U0001f6a8 **BLOCKED 自动应急** ({ts})

工作 agent **{agent}** 写入 blocked 事件：
> {msg}

主控员：请立即派 **{lead}** 介入决策。建议 prompt 模板：

```
Agent({{
  subagent_type: "{lead}",
  prompt: "组员 BLOCKED：agent={agent} msg={msg} 评审轮数=<请补>"
}})
```

待 {lead} 返回决策后，按其指引执行（重派 / 升档 / 通知用户 / 标污染）。
""".strip())
    CURSOR.write_text(current_offset, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
