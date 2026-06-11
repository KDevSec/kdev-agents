# P-Core-FF — kdev-core R1 存储层 feature-first 重构 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 kdev-core 的 R1 存储层从 `.kdev/flows/<flow>/<slug>/flow-state.json`（history 内嵌、active 布尔）翻转为 feature-first 的 `.kdev/features/<slug>/`（台账 `runs[]` + 用户故事 `stories[]` + 单棒控制态 `active{}` + 事实流水 `events.jsonl`），**且不改动 R2/R3 纯函数**。

**Architecture（载重设计）：R1 当「翻译适配层」。** R2(`node_machine.advance`)/R3(`gate.record_gate`) 是纯函数，读写**扁平顶层**字段（`current_node`/`gate_iters`/`status`/`retries`/`phase_history`/`history`）。新 schema 把控制态收进 `active{}`、把 `history`/`phase_history` 挪去 `events.jsonl`。为守住「R2/R3 不动」，R1 的 `read_state`/`write_state` 做双向翻译：

- **磁盘上**：嵌套 feature-first（`active{}`/`runs[]`/`stories[]`/`origin`）+ 同目录 `events.jsonl`。
- **内存里**（R2/R3 看到的，不变）：扁平 dict，控制态全在顶层；`history`/`phase_history` 走「**只带增量**」——`read_state` 永远返回 `[]`，`write_state` 把内存里这两个列表当本次新增、虹吸进 `events.jsonl`。
- **成立前提（不变量）**：所有持久化都是「read → 单次 op → write」（`advance_persist`/`record_gate_persist`/`init`/`complete` 全遵守），故内存里 `history`/`phase_history` 永远只装当次 op 的增量。**callers MUST read→mutate→write，绝不在不重读的情况下二次 write_state**。

**Tech Stack:** Python 3.12 stdlib（`json`/`pathlib`/`tempfile`/`os`/`datetime`），pytest，PyYAML（CLI 读 node-table）。无新增三方依赖。

---

## 契约参考（先看这一节——下游 P-A / kdev-hud build on 它）

### A. 磁盘 schema：`.kdev/features/<slug>/flow-state.json`

字段名/语义严格照「编排底座合稿 v1.0 §2.1」，下面是**完整**落地版（§2.1 示例是子集，控制态补齐 R2/R3 机械必需的 `gate_calls`/`retries`/`blocked_reason`，均为现有代码已产出的字段，非自创）：

```json
{
  "slug": "user-auth",
  "display_name": "用户认证",
  "origin": "决策日志#Q-012",
  "relates_to": null,
  "status": "in_progress",
  "stories": [
    {"id": "US-1", "title": "账号登录", "status": "done"},
    {"id": "US-2", "title": "找回密码", "status": "in_progress"}
  ],
  "runs": [
    {"flow": "design", "run": 1, "status": "completed",
     "final_node": "n-done", "ended_at": "2026-06-10T12:00:00+00:00"}
  ],
  "active": {
    "flow": "design",
    "run": 2,
    "current_node": "n4-plan-review",
    "status": "in_progress",
    "gate_iters": {"g-plan-review": 1},
    "gate_calls": 3,
    "retries": {"n-tdd": 1},
    "blocked_reason": null,
    "config": {"review_mode": "ai", "auto_mode": false},
    "started_at": "2026-06-10T12:01:00+00:00"
  },
  "created_at": "2026-06-10T11:00:00+00:00",
  "updated_at": "2026-06-10T12:30:00+00:00",
  "_meta": {"written_at": "2026-06-10T12:30:00+00:00", "step_id": null}
}
```

- **两级 status**：顶层 `status` = **feature** 级（in_progress | completed | aborted），`active.status` = **run** 级（in_progress | completed | aborted | blocked）。run 完 ≠ feature 完（Q3 拍板）。
- **`active` 是对象或 `null`**：无在跑棒次时 `active: null`（布尔 stale-guard 已废弃，Q2 拍板：可续 = `active` 非 null 且 `active.status=="in_progress"`）。
- `_meta` 仍是写侧管道（读时 strip），保持现状。

### B. 内存扁平视图（`read_state` 返回；R2/R3 看到的，**保持不变**）

```python
{
  # —— R2/R3 读写的控制态（顶层）——
  "flow": "design",            # = active.flow（无 active 时 None）
  "current_node": "n4-plan-review",   # = active.current_node（无 active 时 None）
  "status": "in_progress",     # = active.status（run 级；R3 写 "blocked" 落这里）
  "gate_iters": {...},         # = active.gate_iters
  "gate_calls": 3,             # = active.gate_calls
  "retries": {...},            # = active.retries
  "blocked_reason": None,      # = active.blocked_reason
  "config": {...},             # = active.config
  "history": [],               # 只带增量：read 永远 []
  "phase_history": [],         # 只带增量：read 永远 []
  # —— feature 台账（顶层；R2/R3 原样透传不读）——
  "slug": "user-auth",
  "display_name": "用户认证",
  "origin": "...", "relates_to": None,
  "feature_status": "in_progress",   # = 磁盘顶层 status
  "stories": [...],
  "runs": [...],
  "run": 2,                    # = active.run（无 active 时 None）
  "created_at": "...", "updated_at": "...",
  # —— 私有翻译标记（write 时消费并 strip，R2/R3 不碰）——
  "_has_active": True,
  "_active_started_at": "...",
}
```

**关键命名对齐**：内存 `status` ⟷ 磁盘 `active.status`（run 级，R3 的 `state["status"]="blocked"` 必须落 run）；内存 `feature_status` ⟷ 磁盘顶层 `status`（feature 级）。R2/R3 只碰 `status`，永不碰 `feature_status`。

### C. events.jsonl 行 schema（Q1 拍板：去归一化·自包含行）

`.kdev/features/<slug>/events.jsonl`，append-only，每行一个 JSON 对象。两类（P-Core-FF 范围内）：

```jsonl
{"ts":"...","type":"transition","actor":"system","slug":"user-auth","flow":"design","run":2,"from":"n3","to":"n4","reflow":false,"forced_fail":false,"reason":"sr-done"}
{"ts":"...","type":"gate","actor":"ai","slug":"user-auth","flow":"design","run":2,"gate":"g-plan-review","kind":"review","node":"n4","verdict":"PASS","iter":1,"by":"ai","request_id":"pr-1","issues":[],"revisions":[]}
```

- **actor**：`gate` 事件取 `GateResult.by`；`transition` 事件取 `"system"`（引擎机械流转，HUD「员工在忙啥」主要靠 gate 事件 + active）。
- 每行自带 `slug`/`flow`/`run`，HUD 扫 events 不用回查上下文。
- `派单(dispatch)` 事件留 P-B handoff，本步不产出。

### D. CLI 兼容策略（D2 拍板：保留 `<flow> <slug>` 签名）

现有消费方调用 `python -m kdev_core init coding-flow <slug> ...` / `advance coding-flow <slug> <to_node> ...`（见 kdev-team `dev-engineer-orchestrator.md`）。**不做破坏性 slug-only 改造**：路径内部只按 `features/<slug>/` 路由，`flow` 改存进 `active.flow`。`flow` 位置参数对 `advance`/`record-gate`/`show`/`complete` 仍接受但以 state 里 `active.flow` 为准（不一致时以传入为信息性，不报错）。新增命令 `start-run` / `add-story` / `set-story-status` / `list-features` / `events` / `migrate` / `handoff-path` 是增量。`list-flows` 重命名为 `list-features`（保留 `list-flows` 作 deprecated 别名指向同实现）。

### E. 范围红线

- **不动** `node_machine.py`(R2) / `gate.py`(R3) 纯函数（Q-012 拍板8）。`advance_persist`/`record_gate_persist`（在 R2/R3 文件里但只调 `flow_state.read/write`）零改动验证。
- 文件名保留 `flow-state.json`（不要 `feature.json`，拍板4）。
- 不提前加锁（拍板5）；feature 间分目录、feature 内单棒即够。
- slug **v0.1 仍调用方直传**（拍板6 + §2.2 deferral）：不做自动 mint / 防撞 / 重命名。只加 `origin`(可选，记录回链) + `relates_to`(可选)。
- 不顺手做 deferred 缺口：request_id 只存不校验 / `GateResult.iter↔gate_iters` 双源一致性 / blocked 入 schema 注释。
- kdev-team `PYTHONPATH=$FRAMEWORK_REPO/...` → cache 路径的 rewiring 标 **follow-up**，本步不动 kdev-team。

---

## File Structure

**kdev-core 内：**
- Modify: `plugins/kdev-core/kdev_core/flow_state.py` — R1 适配层（核心；路径翻转 + 嵌套 schema + 扁平翻译 + 事件虹吸 + runs/stories/feature-status 生命周期）
- Create: `plugins/kdev-core/kdev_core/events.py` — events.jsonl 读写 API + 事件行构造（actor 注入）
- Create: `plugins/kdev-core/kdev_core/migrate.py` — 旧布局 → feature-first 迁移（幂等 + 同 slug 跨 flow 合并 + history→events）
- Modify: `plugins/kdev-core/kdev_core/cli.py` — 路径/新 schema + 新增命令
- Modify: `plugins/kdev-core/kdev_core/__init__.py` — 加 `__version__`
- Create: `plugins/kdev-core/.claude-plugin/plugin.json` — marketplace 插件 manifest（Q4 拍板：升 marketplace 插件）
- Create: `plugins/kdev-core/CHANGELOG.md`
- Modify: `.claude-plugin/marketplace.json` — 加 kdev-core 条目

**测试：**
- Modify: `plugins/kdev-core/tests/conftest.py`（docstring 路径注释）
- Rewrite: `tests/test_flow_state.py`（路径 + active 对象 + 两级 status）
- Update: `tests/test_cli.py` / `tests/test_cli_smoke.py` / `tests/test_new_cli.py` / `tests/test_smoke_lifecycle.py` / `tests/test_flow_lifecycle.py` / `tests/test_node_smoke.py` / `tests/test_gate_smoke.py`（features/ 路径 + 新输出字段）
- **Unchanged（验证仍绿）**：`tests/test_advance.py` / `tests/test_record_gate.py` / `tests/test_node_table.py` / `tests/test_gate_result.py`（纯函数，扁平 dict）
- Create: `tests/test_events.py` / `tests/test_runs_lifecycle.py` / `tests/test_stories.py` / `tests/test_migrate.py` / `tests/test_handoffs.py`

**文档（收尾）：**
- Modify: `docs/framework/01-design/...roadmap...` §1.5.2（P-Core-FF ✅）
- Modify: `.kdev/memory/决策日志.md` Q-012 落地状态（设计→实现）— 注：`.kdev/memory/` 是本地工程记忆，在**主 checkout** 而非 worktree；收尾时由主会话处理。

---

## Task 1: events.py — 事件流写入/读取 API

**Files:**
- Create: `plugins/kdev-core/kdev_core/events.py`
- Test: `plugins/kdev-core/tests/test_events.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_events.py
"""Tests for kdev_core.events — events.jsonl append-only stream (R1 流水通道)."""
import json
from pathlib import Path

import pytest

from kdev_core import events


def _events_file(ws: Path, slug: str) -> Path:
    return ws / ".kdev" / "features" / slug / "events.jsonl"


def test_append_event_creates_file_and_appends_line(tmp_workspace):
    events.append_event(tmp_workspace, "user-auth",
                        {"type": "gate", "actor": "ai", "gate": "g1"})
    f = _events_file(tmp_workspace, "user-auth")
    assert f.exists()
    lines = f.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert rec["type"] == "gate" and rec["actor"] == "ai" and rec["gate"] == "g1"
    assert "ts" in rec  # ts auto-injected when absent


def test_append_event_is_append_only(tmp_workspace):
    events.append_event(tmp_workspace, "user-auth", {"type": "transition", "to": "n2"})
    events.append_event(tmp_workspace, "user-auth", {"type": "transition", "to": "n3"})
    recs = events.read_events(tmp_workspace, "user-auth")
    assert [r["to"] for r in recs] == ["n2", "n3"]


def test_read_events_missing_returns_empty(tmp_workspace):
    assert events.read_events(tmp_workspace, "ghost") == []


def test_append_event_preserves_given_ts(tmp_workspace):
    events.append_event(tmp_workspace, "user-auth",
                        {"type": "gate", "ts": "2026-06-10T00:00:00+00:00"})
    assert events.read_events(tmp_workspace, "user-auth")[0]["ts"] == "2026-06-10T00:00:00+00:00"


def test_transition_event_line_from_phase_entry():
    line = events.transition_event(
        slug="user-auth", flow="design", run=2,
        entry={"from": "n3", "to": "n4", "reflow": False,
               "forced_fail": False, "reason": "sr-done",
               "entered_at": "2026-06-10T00:00:00+00:00"})
    assert line == {
        "ts": "2026-06-10T00:00:00+00:00", "type": "transition", "actor": "system",
        "slug": "user-auth", "flow": "design", "run": 2,
        "from": "n3", "to": "n4", "reflow": False, "forced_fail": False, "reason": "sr-done",
    }


def test_gate_event_line_from_gate_result():
    gr = {"gate": "g-plan-review", "kind": "review", "node": "n4", "request_id": "pr-1",
          "iter": 1, "verdict": "PASS", "by": "ai", "issues": [], "revisions": [],
          "ts": "2026-06-10T00:00:00+00:00"}
    line = events.gate_event(slug="user-auth", flow="design", run=2, gate_result=gr)
    assert line == {
        "ts": "2026-06-10T00:00:00+00:00", "type": "gate", "actor": "ai",
        "slug": "user-auth", "flow": "design", "run": 2,
        "gate": "g-plan-review", "kind": "review", "node": "n4", "verdict": "PASS",
        "iter": 1, "by": "ai", "request_id": "pr-1", "issues": [], "revisions": [],
    }
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `cd plugins/kdev-core && python3 -m pytest tests/test_events.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'kdev_core.events'`

- [ ] **Step 3: Implement events.py**

```python
# kdev_core/events.py
"""kdev-core R1 — events.jsonl append-only stream (事实流水通道).

控制态小而热（flow-state.json 的 active{}），流水长而冷（这里）。每行一个 JSON
对象、append-only、自带 actor + slug/flow/run（去归一化，HUD 扫 events 不用回查）。

两类事件（P-Core-FF 范围）：
  - transition：R2 流转（来自 phase_history 条目），actor="system"
  - gate：R3 关卡判定（来自 GateResult），actor=GateResult.by
dispatch（派单）事件留 P-B handoff。
"""
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def _events_path(workspace, slug) -> Path:
    return Path(workspace) / ".kdev" / "features" / slug / "events.jsonl"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def append_event(workspace, slug, event) -> None:
    """Append one event dict as a JSON line. Injects ts if absent. Creates file/dir."""
    path = _events_path(workspace, slug)
    path.parent.mkdir(parents=True, exist_ok=True)
    rec = dict(event)
    rec.setdefault("ts", _now_iso())
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def read_events(workspace, slug) -> list:
    """Read all event lines (oldest first). Missing file -> []. Skips blank/corrupt lines."""
    path = _events_path(workspace, slug)
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def transition_event(*, slug, flow, run, entry) -> dict:
    """Build a transition event line from an R2 phase_history entry."""
    return {
        "ts": entry.get("entered_at") or _now_iso(),
        "type": "transition",
        "actor": "system",
        "slug": slug,
        "flow": flow,
        "run": run,
        "from": entry.get("from"),
        "to": entry.get("to"),
        "reflow": bool(entry.get("reflow", False)),
        "forced_fail": bool(entry.get("forced_fail", False)),
        "reason": entry.get("reason"),
    }


def gate_event(*, slug, flow, run, gate_result) -> dict:
    """Build a gate event line from an R3 GateResult dict."""
    gr = gate_result
    return {
        "ts": gr.get("ts") or _now_iso(),
        "type": "gate",
        "actor": gr.get("by"),
        "slug": slug,
        "flow": flow,
        "run": run,
        "gate": gr.get("gate"),
        "kind": gr.get("kind"),
        "node": gr.get("node"),
        "verdict": gr.get("verdict"),
        "iter": gr.get("iter"),
        "by": gr.get("by"),
        "request_id": gr.get("request_id"),
        "issues": list(gr.get("issues", [])),
        "revisions": list(gr.get("revisions", [])),
    }
```

- [ ] **Step 4: Run tests, verify pass**

Run: `cd plugins/kdev-core && python3 -m pytest tests/test_events.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add plugins/kdev-core/kdev_core/events.py plugins/kdev-core/tests/test_events.py
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-core): events.jsonl append-only 流水通道 (transition/gate 行 + actor)"
```

---

## Task 2: flow_state.py — feature-first 适配层重构（核心）

**Files:**
- Modify: `plugins/kdev-core/kdev_core/flow_state.py`（全量重写内部，公开函数签名保 `<flow> <slug>` 兼容）
- Rewrite: `plugins/kdev-core/tests/test_flow_state.py`

### 设计要点（实现前读）

- `_feature_dir(ws, slug) = ws/.kdev/features/<slug>/`；`_state_path(ws, slug) = .../flow-state.json`。
- 公开签名仍是 `init_state(ws, flow, slug, ...)`、`read_state(ws, flow, slug)`、`write_state(ws, flow, slug, state, *, step_id=None)`、`mark_inactive`/`resume_state`/`unblock_state`/`list_flows`——**`flow` 参数保留但路径只用 `slug`**（兼容现有调用方）。`read_state`/`write_state` 的 `flow` 形参变为可选信息性（默认 `None`），实际 flow 以 state 里 `active.flow` 为准。
- `read_state`：load 磁盘嵌套 → 返回扁平视图（B 节），`history=[]`/`phase_history=[]`，注入私有 `_has_active`/`_active_started_at`，strip `_meta`。
- `write_state`：收扁平 → 重建嵌套（`active{}` from 顶层控制态 if `_has_active` else `null`；顶层 `status` = `feature_status`）→ 把 `state["phase_history"]`/`state["history"]` 增量虹吸进 `events.jsonl`（用 `events.transition_event`/`gate_event`，flow/run 取自 active）→ strip 私有键 → 原子写。

- [ ] **Step 1: Rewrite test_flow_state.py（失败测试）**

```python
# tests/test_flow_state.py
"""Tests for kdev_core.flow_state — R1 feature-first store (适配层: 嵌套盘/扁平内存 + 事件虹吸)."""
import json
from pathlib import Path
from unittest import mock

import pytest

from kdev_core.flow_state import (
    init_state, read_state, write_state, FlowStateError,
)
from kdev_core import events

FLOW = "coding-flow"


def _state_file(ws: Path, slug: str) -> Path:
    return ws / ".kdev" / "features" / slug / "flow-state.json"


def test_init_creates_feature_first_path(tmp_workspace):
    init_state(tmp_workspace, FLOW, "feat-x", display_name="Feat X", initial_node="n0")
    assert _state_file(tmp_workspace, "feat-x").exists()
    # 旧 flows/ 路径不再创建
    assert not (tmp_workspace / ".kdev" / "flows").exists()


def test_init_disk_schema_is_nested(tmp_workspace):
    init_state(tmp_workspace, FLOW, "feat-x", display_name="X", initial_node="n0",
               origin="决策日志#Q-012")
    raw = json.loads(_state_file(tmp_workspace, "feat-x").read_text(encoding="utf-8"))
    assert raw["slug"] == "feat-x"
    assert raw["display_name"] == "X"
    assert raw["origin"] == "决策日志#Q-012"
    assert raw["relates_to"] is None
    assert raw["status"] == "in_progress"          # feature 级
    assert raw["stories"] == []
    assert raw["runs"] == []
    a = raw["active"]
    assert a["flow"] == FLOW and a["run"] == 1
    assert a["current_node"] == "n0"
    assert a["status"] == "in_progress"            # run 级
    assert a["gate_iters"] == {} and a["gate_calls"] == 0 and a["retries"] == {}
    assert a["config"] == {"review_mode": "ai", "auto_mode": False}


def test_read_returns_flat_view(tmp_workspace):
    init_state(tmp_workspace, FLOW, "feat-x", display_name="X", initial_node="n0")
    st = read_state(tmp_workspace, FLOW, "feat-x")
    # R2/R3 看到的扁平顶层
    assert st["flow"] == FLOW
    assert st["current_node"] == "n0"
    assert st["status"] == "in_progress"
    assert st["gate_iters"] == {} and st["gate_calls"] == 0 and st["retries"] == {}
    assert st["config"] == {"review_mode": "ai", "auto_mode": False}
    assert st["history"] == [] and st["phase_history"] == []
    # feature 台账
    assert st["feature_status"] == "in_progress"
    assert st["stories"] == [] and st["runs"] == []
    assert st["run"] == 1
    assert "_meta" not in st


def test_write_roundtrips_control_state_into_active(tmp_workspace):
    init_state(tmp_workspace, FLOW, "feat-x", display_name="X", initial_node="n0")
    st = read_state(tmp_workspace, FLOW, "feat-x")
    st["current_node"] = "n3-tdd"
    st["gate_iters"] = {"g1": 2}
    write_state(tmp_workspace, FLOW, "feat-x", st)
    raw = json.loads(_state_file(tmp_workspace, "feat-x").read_text(encoding="utf-8"))
    assert raw["active"]["current_node"] == "n3-tdd"
    assert raw["active"]["gate_iters"] == {"g1": 2}
    # 再读扁平视图一致
    st2 = read_state(tmp_workspace, FLOW, "feat-x")
    assert st2["current_node"] == "n3-tdd" and st2["gate_iters"] == {"g1": 2}


def test_write_siphons_phase_history_to_events(tmp_workspace):
    init_state(tmp_workspace, FLOW, "feat-x", display_name="X", initial_node="n0")
    st = read_state(tmp_workspace, FLOW, "feat-x")
    # 模拟 R2 advance 产出的增量
    st["current_node"] = "n1"
    st["phase_history"] = [{"from": "n0", "to": "n1", "reflow": False,
                            "forced_fail": False, "reason": "go",
                            "entered_at": "2026-06-10T00:00:00+00:00"}]
    write_state(tmp_workspace, FLOW, "feat-x", st)
    # 不进 flow-state.json
    raw = json.loads(_state_file(tmp_workspace, "feat-x").read_text(encoding="utf-8"))
    assert "phase_history" not in raw and "phase_history" not in raw["active"]
    # 进 events.jsonl
    evs = events.read_events(tmp_workspace, "feat-x")
    assert len(evs) == 1
    assert evs[0]["type"] == "transition" and evs[0]["from"] == "n0" and evs[0]["to"] == "n1"
    assert evs[0]["actor"] == "system" and evs[0]["flow"] == FLOW and evs[0]["run"] == 1


def test_write_siphons_history_gate_to_events(tmp_workspace):
    init_state(tmp_workspace, FLOW, "feat-x", display_name="X", initial_node="n0")
    st = read_state(tmp_workspace, FLOW, "feat-x")
    st["history"] = [{"gate": "g1", "kind": "review", "node": "n0", "request_id": "r1",
                      "iter": 1, "verdict": "PASS", "by": "ai", "issues": [], "revisions": [],
                      "ts": "2026-06-10T00:00:00+00:00"}]
    write_state(tmp_workspace, FLOW, "feat-x", st)
    evs = events.read_events(tmp_workspace, "feat-x")
    assert len(evs) == 1
    assert evs[0]["type"] == "gate" and evs[0]["actor"] == "ai" and evs[0]["verdict"] == "PASS"


def test_read_always_returns_empty_history_delta_model(tmp_workspace):
    init_state(tmp_workspace, FLOW, "feat-x", display_name="X", initial_node="n0")
    st = read_state(tmp_workspace, FLOW, "feat-x")
    st["history"] = [{"gate": "g1", "kind": "review", "node": "n0", "request_id": "r1",
                      "iter": 1, "verdict": "PASS", "by": "ai", "issues": [], "revisions": []}]
    write_state(tmp_workspace, FLOW, "feat-x", st)
    # 第二次 read：history 又是空（增量模型），不会把旧事件读回来
    st2 = read_state(tmp_workspace, FLOW, "feat-x")
    assert st2["history"] == []


def test_meta_persisted_and_step_id(tmp_workspace):
    init_state(tmp_workspace, FLOW, "feat-x", display_name="X", initial_node="n0")
    st = read_state(tmp_workspace, FLOW, "feat-x")
    write_state(tmp_workspace, FLOW, "feat-x", st, step_id="Step main-99")
    raw = json.loads(_state_file(tmp_workspace, "feat-x").read_text(encoding="utf-8"))
    assert raw["_meta"]["step_id"] == "Step main-99" and "written_at" in raw["_meta"]


def test_atomic_write_no_tmp_leftover(tmp_workspace):
    init_state(tmp_workspace, FLOW, "feat-x", display_name="X", initial_node="n0")
    st = read_state(tmp_workspace, FLOW, "feat-x")
    st["current_node"] = "n2"
    write_state(tmp_workspace, FLOW, "feat-x", st)
    state_dir = _state_file(tmp_workspace, "feat-x").parent
    assert list(state_dir.glob("*.tmp")) == []


def test_write_failure_leaves_original_intact(tmp_workspace):
    init_state(tmp_workspace, FLOW, "feat-x", display_name="X", initial_node="n1")
    f = _state_file(tmp_workspace, "feat-x")
    before = f.read_text(encoding="utf-8")
    st = read_state(tmp_workspace, FLOW, "feat-x")
    st["current_node"] = "n2"
    with mock.patch("kdev_core.flow_state.json.dump", side_effect=RuntimeError("disk full")):
        with pytest.raises(RuntimeError, match="disk full"):
            write_state(tmp_workspace, FLOW, "feat-x", st)
    assert "flow-state.json" in [p.name for p in f.parent.iterdir()]
    assert not list(f.parent.glob("*.tmp"))
    assert f.read_text(encoding="utf-8") == before


def test_read_missing_raises(tmp_workspace):
    with pytest.raises(FlowStateError, match="no flow-state.json"):
        read_state(tmp_workspace, FLOW, "ghost")


def test_read_corrupt_raises(tmp_workspace):
    init_state(tmp_workspace, FLOW, "feat-x", display_name="X", initial_node="n0")
    _state_file(tmp_workspace, "feat-x").write_text("{ not json", encoding="utf-8")
    with pytest.raises(FlowStateError, match="corrupt"):
        read_state(tmp_workspace, FLOW, "feat-x")


def test_init_refuses_overwrite(tmp_workspace):
    init_state(tmp_workspace, FLOW, "feat-x", display_name="X", initial_node="n0")
    with pytest.raises(FlowStateError, match="already exists"):
        init_state(tmp_workspace, FLOW, "feat-x", display_name="X", initial_node="n0")


def test_invalid_review_mode_raises(tmp_workspace):
    with pytest.raises(ValueError, match="review_mode"):
        init_state(tmp_workspace, FLOW, "feat-x", display_name="X", review_mode="psychic")


def test_same_slug_is_same_feature(tmp_workspace):
    """新语义：同 slug = 同 feature（不再按 flow 隔离）。第二次 init 同 slug 应拒绝。"""
    init_state(tmp_workspace, "coding-flow", "feat-x", display_name="X", initial_node="n0")
    with pytest.raises(FlowStateError, match="already exists"):
        init_state(tmp_workspace, "design-flow", "feat-x", display_name="X", initial_node="n0")
```

- [ ] **Step 2: Run, verify fail**

Run: `cd plugins/kdev-core && python3 -m pytest tests/test_flow_state.py -v`
Expected: FAIL（旧实现用 flows/ 路径 + 布尔 active）

- [ ] **Step 3: Implement flow_state.py（全量重写）**

```python
# kdev_core/flow_state.py
"""kdev-core R1 — feature-first flow-state store (适配层).

磁盘：.kdev/features/<slug>/flow-state.json（嵌套：台账 runs[]+stories[]+单棒 active{}）
      + 同目录 events.jsonl（流水，见 kdev_core.events）。
内存：read_state 返回扁平视图（控制态在顶层），R2/R3 纯函数不变地读写它。

适配层不变量：所有持久化都是 read→单次 op→write。read_state 永远返回
history=[]/phase_history=[]（增量模型）；write_state 把内存里这两个列表当本次新增、
虹吸进 events.jsonl，绝不存进 flow-state.json。

两级 status：磁盘顶层 status=feature 级；active.status=run 级。
内存扁平 status ⟷ active.status（R3 写 blocked 落 run）；内存 feature_status ⟷ 顶层 status。
active 是对象或 null（无在跑棒次时 null）——布尔 stale-guard 已废弃，可续 = active 非 null 且 active.status==in_progress。
"""
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from kdev_core import events as _events

VALID_REVIEW_MODES = {"ai", "both", "human"}
_FEATURE_STATUSES = {"in_progress", "completed", "aborted"}


class FlowStateError(Exception):
    """Raised when flow-state.json is missing, corrupt, or in an invalid state."""


def _feature_dir(workspace, slug) -> Path:
    return Path(workspace) / ".kdev" / "features" / slug


def _state_path(workspace, slug) -> Path:
    return _feature_dir(workspace, slug) / "flow-state.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def init_state(workspace, flow, slug, *, display_name,
               review_mode="ai", auto_mode=False, initial_node=None,
               origin=None, relates_to=None):
    """立项：建 features/<slug>/flow-state.json，run 1 进 active{}。slug 仍调用方直传(v0.1)。"""
    if review_mode not in VALID_REVIEW_MODES:
        raise ValueError(
            f"review_mode must be one of {sorted(VALID_REVIEW_MODES)}, got {review_mode!r}"
        )
    path = _state_path(workspace, slug)
    if path.exists():
        raise FlowStateError(
            f"flow-state.json already exists for feature {slug!r}; resume or pick a different slug"
        )
    now = _now_iso()
    doc = {
        "slug": slug,
        "display_name": display_name,
        "origin": origin,
        "relates_to": relates_to,
        "status": "in_progress",
        "stories": [],
        "runs": [],
        "active": {
            "flow": flow,
            "run": 1,
            "current_node": initial_node,
            "status": "in_progress",
            "gate_iters": {},
            "gate_calls": 0,
            "retries": {},
            "blocked_reason": None,
            "config": {"review_mode": review_mode, "auto_mode": auto_mode},
            "started_at": now,
        },
        "created_at": now,
        "updated_at": now,
    }
    _write_doc(workspace, slug, doc)
    return read_state(workspace, slug=slug)


def _flatten(doc) -> dict:
    """嵌套磁盘 doc -> 扁平内存视图（R2/R3 看到的）。history/phase_history 永远 []。"""
    active = doc.get("active")
    flat = {
        # feature 台账（透传）
        "slug": doc.get("slug"),
        "display_name": doc.get("display_name"),
        "origin": doc.get("origin"),
        "relates_to": doc.get("relates_to"),
        "feature_status": doc.get("status"),
        "stories": doc.get("stories", []),
        "runs": doc.get("runs", []),
        "created_at": doc.get("created_at"),
        "updated_at": doc.get("updated_at"),
        # 增量模型
        "history": [],
        "phase_history": [],
    }
    if active is not None:
        flat.update({
            "flow": active.get("flow"),
            "run": active.get("run"),
            "current_node": active.get("current_node"),
            "status": active.get("status"),
            "gate_iters": dict(active.get("gate_iters", {})),
            "gate_calls": active.get("gate_calls", 0),
            "retries": dict(active.get("retries", {})),
            "blocked_reason": active.get("blocked_reason"),
            "config": active.get("config"),
            "_has_active": True,
            "_active_started_at": active.get("started_at"),
        })
    else:
        flat.update({
            "flow": None, "run": None, "current_node": None, "status": None,
            "gate_iters": {}, "gate_calls": 0, "retries": {}, "blocked_reason": None,
            "config": None, "_has_active": False, "_active_started_at": None,
        })
    return flat


def read_state(workspace, flow=None, slug=None):
    """读 feature 状态，返回扁平视图。flow 形参兼容旧签名(忽略)，slug 必给。"""
    if slug is None:  # 兼容 read_state(ws, flow, slug) 旧位置参数
        slug = flow
    path = _state_path(workspace, slug)
    if not path.exists():
        raise FlowStateError(f"no flow-state.json at {path}")
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise FlowStateError(f"corrupt flow-state.json at {path}: {exc}") from exc
    doc.pop("_meta", None)
    return _flatten(doc)


def _rebuild_doc(workspace, slug, flat) -> dict:
    """扁平内存视图 -> 嵌套磁盘 doc（不含 _meta；事件虹吸由 write_state 负责）。"""
    if flat.get("_has_active"):
        active = {
            "flow": flat.get("flow"),
            "run": flat.get("run"),
            "current_node": flat.get("current_node"),
            "status": flat.get("status"),
            "gate_iters": dict(flat.get("gate_iters", {})),
            "gate_calls": flat.get("gate_calls", 0),
            "retries": dict(flat.get("retries", {})),
            "blocked_reason": flat.get("blocked_reason"),
            "config": flat.get("config"),
            "started_at": flat.get("_active_started_at"),
        }
    else:
        active = None
    return {
        "slug": flat.get("slug") or slug,
        "display_name": flat.get("display_name"),
        "origin": flat.get("origin"),
        "relates_to": flat.get("relates_to"),
        "status": flat.get("feature_status", "in_progress"),
        "stories": flat.get("stories", []),
        "runs": flat.get("runs", []),
        "active": active,
        "created_at": flat.get("created_at") or _now_iso(),
    }


def _write_doc(workspace, slug, doc, *, step_id=None) -> None:
    """原子写一个完整嵌套 doc（注入 updated_at + _meta）。内部用，不做事件虹吸。"""
    path = _state_path(workspace, slug)
    path.parent.mkdir(parents=True, exist_ok=True)
    to_write = {k: v for k, v in doc.items() if k != "_meta"}
    to_write["updated_at"] = _now_iso()
    to_write["_meta"] = {"written_at": _now_iso(), "step_id": step_id}
    fd, tmp_path = tempfile.mkstemp(prefix=".flow-state-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(to_write, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def write_state(workspace, flow, slug=None, state=None, *, step_id=None):
    """写扁平 state：重建嵌套 doc + 虹吸 history/phase_history 增量进 events.jsonl。

    兼容旧位置签名 write_state(ws, flow, slug, state)。新式可 write_state(ws, slug=..., state=...)。
    """
    # 兼容位置参数：write_state(ws, flow, slug, state)
    if state is None and slug is not None and not isinstance(slug, str):
        state, slug = slug, flow  # 不该走到；显式签名优先
    if state is None:
        raise ValueError("write_state requires a state dict")
    if slug is None:
        slug = state.get("slug") or flow
    flat = state
    flow_id = flat.get("flow")
    run_id = flat.get("run")
    # 1. 虹吸增量 → events.jsonl（先盘后状态文件：事件丢一行可容忍，状态文件是真相源）
    for entry in flat.get("phase_history", []) or []:
        _events.append_event(workspace, slug,
                             _events.transition_event(slug=slug, flow=flow_id, run=run_id, entry=entry))
    for gr in flat.get("history", []) or []:
        _events.append_event(workspace, slug,
                             _events.gate_event(slug=slug, flow=flow_id, run=run_id, gate_result=gr))
    # 2. 重建嵌套 doc 并原子写
    doc = _rebuild_doc(workspace, slug, flat)
    _write_doc(workspace, slug, doc, step_id=step_id)


def mark_inactive(workspace, flow, slug=None, *, status="aborted", step_id=None):
    """[兼容旧 API] 终结当前在跑棒次：等价 complete_run。fold active→runs[] + 清空 active。

    旧语义是 active=False + 顶层 status。新语义：run 级终态 + 折叠台账；feature 级 status
    仅在 completed 时一并置（保最小兼容：旧调用方 complete 即视作功能完结）。
    """
    if slug is None:
        slug = flow
    if status not in {"completed", "aborted"}:
        raise ValueError(
            f"mark_inactive status must be 'completed' or 'aborted', got {status!r}"
        )
    return complete_run(workspace, slug, status=status, close_feature=True, step_id=step_id)


def resume_state(workspace, flow, slug=None):
    """可续 = active 非 null 且 active.status == in_progress（布尔 stale-guard 已废弃）。"""
    if slug is None:
        slug = flow
    state = read_state(workspace, slug=slug)
    if not state["_has_active"] or state["status"] != "in_progress":
        raise FlowStateError(
            f"feature {slug!r} not resumable: no active run in_progress "
            f"(active={state['_has_active']}, run_status={state['status']!r})"
        )
    return state


def unblock_state(workspace, flow, slug=None, *, to_node=None):
    """清 blocked：active.status 回 in_progress，清 blocked_reason，可选移 current_node。"""
    if slug is None:
        slug = flow
    state = read_state(workspace, slug=slug)
    if not state["_has_active"] or state["status"] != "blocked":
        raise FlowStateError(
            f"feature {slug!r} active run is not blocked (status={state['status']!r})"
        )
    state["status"] = "in_progress"
    state["blocked_reason"] = None
    if to_node is not None:
        state["current_node"] = to_node
    write_state(workspace, flow, slug=slug, state=state)
    return read_state(workspace, slug=slug)


def list_flows(workspace):
    """[兼容别名] = list_features。"""
    return list_features(workspace)


def list_features(workspace):
    """扫 .kdev/features/*/flow-state.json，返回每 feature 概要（HUD 多功能队列用）。"""
    features_dir = Path(workspace) / ".kdev" / "features"
    if not features_dir.exists():
        return []
    result = []
    for feat_dir in sorted(features_dir.iterdir()):
        state_path = feat_dir / "flow-state.json"
        if not state_path.exists():
            continue
        try:
            doc = json.loads(state_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        doc.pop("_meta", None)
        active = doc.get("active")
        stories = doc.get("stories", [])
        done = sum(1 for s in stories if s.get("status") == "done")
        result.append({
            "slug": doc.get("slug"),
            "display_name": doc.get("display_name"),
            "feature_status": doc.get("status"),
            "active_flow": active.get("flow") if active else None,
            "active_node": active.get("current_node") if active else None,
            "active_run": active.get("run") if active else None,
            "runs_count": len(doc.get("runs", [])),
            "stories_done": done,
            "stories_total": len(stories),
        })
    return result


# complete_run / start_run / stories API 在 Task 3 / Task 4 追加到本模块。
```

> 注：`complete_run` / `start_run` 在 Task 3 实现；`mark_inactive`/`list_flows` 已前向引用 `complete_run`/`list_features`。本 Task 先实现到 `list_features` 为止——`complete_run` 暂以最小桩补足让 Task 2 测试过（见下），Task 3 替换为完整版。

- [ ] **Step 3b: 临时桩 complete_run（仅为 Task 2 绿；Task 3 替换）**

在 `flow_state.py` 末尾追加（Task 3 会重写）：

```python
def complete_run(workspace, slug, *, status="completed", close_feature=False, step_id=None):
    state = read_state(workspace, slug=slug)
    if not state["_has_active"]:
        raise FlowStateError(f"feature {slug!r} has no active run to complete")
    run_summary = {
        "flow": state["flow"], "run": state["run"], "status": status,
        "final_node": state["current_node"], "ended_at": _now_iso(),
    }
    state["runs"] = [*state.get("runs", []), run_summary]
    state["_has_active"] = False
    if close_feature:
        state["feature_status"] = status
    write_state(workspace, None, slug=slug, state=state)
    return read_state(workspace, slug=slug)
```

- [ ] **Step 4: Run flow_state + events + 纯函数回归**

Run: `cd plugins/kdev-core && python3 -m pytest tests/test_flow_state.py tests/test_events.py tests/test_advance.py tests/test_record_gate.py tests/test_node_table.py tests/test_gate_result.py -v`
Expected: PASS（纯函数 4 个文件零改动仍绿 = 适配层成功；flow_state + events 绿）

- [ ] **Step 5: Commit**

```bash
git add plugins/kdev-core/kdev_core/flow_state.py plugins/kdev-core/tests/test_flow_state.py
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "refactor(kdev-core)!: R1 翻转 feature-first 适配层 (features/<slug>/ + active{} 嵌套盘/扁平内存 + 事件虹吸)"
```

---

## Task 3: runs 台账生命周期 — complete_run + start_run（补活）

**Files:**
- Modify: `plugins/kdev-core/kdev_core/flow_state.py`（替换 Task 2 的 `complete_run` 桩 + 加 `start_run`）
- Test: `plugins/kdev-core/tests/test_runs_lifecycle.py`

### 语义（Q3 拍板：run 完 ≠ feature 完）
- `complete_run(ws, slug, *, status, close_feature=False)`：active.status=status → fold 成 `runs[]` 一行摘要 `{flow,run,status,final_node,ended_at}` → 清空 active（`_has_active=False`）。`close_feature=True` 才把 feature 级 `status` 一并置。
- `start_run(ws, flow, slug, *, initial_node, review_mode, auto_mode)`：补活。要求 feature 存在且**无在跑棒次**（单棒约束，拍板5）。run 号 = `max(runs[].run, 0)+1`。填 active；若 feature 已 completed/aborted，重开把 feature 级 status 拨回 in_progress。
- `close_feature(ws, slug, *, status="completed")`：显式收口 feature 级（无在跑棒次时才允许）。

- [ ] **Step 1: 失败测试**

```python
# tests/test_runs_lifecycle.py
"""Tests for run 台账生命周期 — complete_run / start_run / close_feature (Q3: run≠feature)."""
import pytest

from kdev_core.flow_state import (
    init_state, read_state, complete_run, start_run, close_feature,
    resume_state, FlowStateError,
)

FLOW = "coding-flow"


def test_complete_run_folds_active_into_runs_and_clears(tmp_workspace):
    init_state(tmp_workspace, FLOW, "f", display_name="F", initial_node="n0")
    st = read_state(tmp_workspace, FLOW, "f")
    st["current_node"] = "n-done"
    from kdev_core.flow_state import write_state
    write_state(tmp_workspace, FLOW, slug="f", state=st)
    out = complete_run(tmp_workspace, "f", status="completed")
    assert out["_has_active"] is False
    assert out["current_node"] is None
    assert len(out["runs"]) == 1
    r = out["runs"][0]
    assert r == {"flow": FLOW, "run": 1, "status": "completed",
                 "final_node": "n-done", "ended_at": r["ended_at"]}
    # Q3: feature 级仍 in_progress（run 完 ≠ feature 完）
    assert out["feature_status"] == "in_progress"


def test_completed_run_not_resumable(tmp_workspace):
    init_state(tmp_workspace, FLOW, "f", display_name="F", initial_node="n0")
    complete_run(tmp_workspace, "f", status="completed")
    with pytest.raises(FlowStateError, match="not resumable"):
        resume_state(tmp_workspace, FLOW, "f")


def test_start_run_opens_new_run_with_incremented_number(tmp_workspace):
    init_state(tmp_workspace, FLOW, "f", display_name="F", initial_node="n0")
    complete_run(tmp_workspace, "f", status="completed")
    out = start_run(tmp_workspace, "design-flow", "f", initial_node="d0")
    assert out["_has_active"] is True
    assert out["run"] == 2
    assert out["flow"] == "design-flow"
    assert out["current_node"] == "d0"
    assert out["status"] == "in_progress"
    assert len(out["runs"]) == 1  # 上一棒还在台账里


def test_start_run_refuses_while_active(tmp_workspace):
    init_state(tmp_workspace, FLOW, "f", display_name="F", initial_node="n0")
    with pytest.raises(FlowStateError, match="active run"):
        start_run(tmp_workspace, FLOW, "f", initial_node="x")  # 单棒约束


def test_start_run_requires_feature_exists(tmp_workspace):
    with pytest.raises(FlowStateError, match="no flow-state.json"):
        start_run(tmp_workspace, FLOW, "ghost", initial_node="x")


def test_close_feature_sets_feature_status(tmp_workspace):
    init_state(tmp_workspace, FLOW, "f", display_name="F", initial_node="n0")
    complete_run(tmp_workspace, "f", status="completed")
    out = close_feature(tmp_workspace, "f", status="completed")
    assert out["feature_status"] == "completed"


def test_close_feature_refuses_with_active_run(tmp_workspace):
    init_state(tmp_workspace, FLOW, "f", display_name="F", initial_node="n0")
    with pytest.raises(FlowStateError, match="active run"):
        close_feature(tmp_workspace, "f", status="completed")


def test_start_run_reopens_closed_feature(tmp_workspace):
    init_state(tmp_workspace, FLOW, "f", display_name="F", initial_node="n0")
    complete_run(tmp_workspace, "f", status="completed")
    close_feature(tmp_workspace, "f", status="completed")
    out = start_run(tmp_workspace, FLOW, "f", initial_node="n0b")  # 补活
    assert out["feature_status"] == "in_progress"
    assert out["run"] == 2
```

- [ ] **Step 2: Run, verify fail**

Run: `cd plugins/kdev-core && python3 -m pytest tests/test_runs_lifecycle.py -v`
Expected: FAIL（`start_run`/`close_feature` 未定义；桩 complete_run 不全）

- [ ] **Step 3: 替换 complete_run 桩 + 加 start_run / close_feature**

把 Task 2 Step 3b 的桩替换为：

```python
def complete_run(workspace, slug, *, status="completed", close_feature=False, step_id=None):
    """终结当前在跑棒次：fold active → runs[] 一行摘要 + 清空 active。Q3: 默认不动 feature 级。"""
    if status not in {"completed", "aborted"}:
        raise ValueError(f"complete_run status must be completed|aborted, got {status!r}")
    state = read_state(workspace, slug=slug)
    if not state["_has_active"]:
        raise FlowStateError(f"feature {slug!r} has no active run to complete")
    run_summary = {
        "flow": state["flow"],
        "run": state["run"],
        "status": status,
        "final_node": state["current_node"],
        "ended_at": _now_iso(),
    }
    state["runs"] = [*state.get("runs", []), run_summary]
    state["_has_active"] = False
    if close_feature:
        state["feature_status"] = status
    write_state(workspace, None, slug=slug, state=state, step_id=step_id)
    return read_state(workspace, slug=slug)


def start_run(workspace, flow, slug, *, initial_node=None,
              review_mode="ai", auto_mode=False, step_id=None):
    """补活：feature 已存在且无在跑棒次时，开新 run 填 active（run 号自增）。单棒约束。"""
    if review_mode not in VALID_REVIEW_MODES:
        raise ValueError(f"review_mode must be one of {sorted(VALID_REVIEW_MODES)}, got {review_mode!r}")
    state = read_state(workspace, slug=slug)  # 不存在 → FlowStateError(no flow-state.json)
    if state["_has_active"]:
        raise FlowStateError(
            f"feature {slug!r} already has an active run (run {state['run']}); "
            f"complete it before starting a new one (单棒约束)"
        )
    next_run = max((r.get("run", 0) for r in state.get("runs", [])), default=0) + 1
    state["_has_active"] = True
    state["_active_started_at"] = _now_iso()
    state["flow"] = flow
    state["run"] = next_run
    state["current_node"] = initial_node
    state["status"] = "in_progress"
    state["gate_iters"] = {}
    state["gate_calls"] = 0
    state["retries"] = {}
    state["blocked_reason"] = None
    state["config"] = {"review_mode": review_mode, "auto_mode": auto_mode}
    if state.get("feature_status") in {"completed", "aborted"}:
        state["feature_status"] = "in_progress"  # 补活重开
    write_state(workspace, flow, slug=slug, state=state, step_id=step_id)
    return read_state(workspace, slug=slug)


def close_feature(workspace, slug, *, status="completed", step_id=None):
    """显式收口 feature 级 status（无在跑棒次时才允许）。"""
    if status not in {"completed", "aborted"}:
        raise ValueError(f"close_feature status must be completed|aborted, got {status!r}")
    state = read_state(workspace, slug=slug)
    if state["_has_active"]:
        raise FlowStateError(
            f"feature {slug!r} has an active run; complete it before closing the feature"
        )
    state["feature_status"] = status
    write_state(workspace, None, slug=slug, state=state, step_id=step_id)
    return read_state(workspace, slug=slug)
```

- [ ] **Step 4: Run, verify pass**

Run: `cd plugins/kdev-core && python3 -m pytest tests/test_runs_lifecycle.py tests/test_flow_state.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add plugins/kdev-core/kdev_core/flow_state.py plugins/kdev-core/tests/test_runs_lifecycle.py
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-core): run 台账生命周期 (complete_run 折叠 runs[] + start_run 补活 + close_feature)"
```

---

## Task 4: stories 用户故事 API（HUD 完成度分母）

**Files:**
- Modify: `plugins/kdev-core/kdev_core/flow_state.py`（加 `add_story` / `set_story_status`）
- Test: `plugins/kdev-core/tests/test_stories.py`

- [ ] **Step 1: 失败测试**

```python
# tests/test_stories.py
"""Tests for stories[] 用户故事 API — HUD 需求完成度的分母 (合稿 §2.1)."""
import pytest

from kdev_core.flow_state import (
    init_state, read_state, add_story, set_story_status, FlowStateError,
)

FLOW = "coding-flow"
VALID_STORY = {"pending", "in_progress", "done"}


def test_add_story_appends(tmp_workspace):
    init_state(tmp_workspace, FLOW, "f", display_name="F", initial_node="n0")
    out = add_story(tmp_workspace, "f", story_id="US-1", title="账号登录")
    assert out["stories"] == [{"id": "US-1", "title": "账号登录", "status": "pending"}]


def test_add_story_with_status(tmp_workspace):
    init_state(tmp_workspace, FLOW, "f", display_name="F", initial_node="n0")
    out = add_story(tmp_workspace, "f", story_id="US-1", title="X", status="in_progress")
    assert out["stories"][0]["status"] == "in_progress"


def test_add_story_rejects_duplicate_id(tmp_workspace):
    init_state(tmp_workspace, FLOW, "f", display_name="F", initial_node="n0")
    add_story(tmp_workspace, "f", story_id="US-1", title="X")
    with pytest.raises(FlowStateError, match="already exists"):
        add_story(tmp_workspace, "f", story_id="US-1", title="Y")


def test_add_story_rejects_bad_status(tmp_workspace):
    init_state(tmp_workspace, FLOW, "f", display_name="F", initial_node="n0")
    with pytest.raises(ValueError, match="status"):
        add_story(tmp_workspace, "f", story_id="US-1", title="X", status="bogus")


def test_set_story_status_updates(tmp_workspace):
    init_state(tmp_workspace, FLOW, "f", display_name="F", initial_node="n0")
    add_story(tmp_workspace, "f", story_id="US-1", title="X")
    out = set_story_status(tmp_workspace, "f", story_id="US-1", status="done")
    assert out["stories"][0]["status"] == "done"


def test_set_story_status_unknown_id_raises(tmp_workspace):
    init_state(tmp_workspace, FLOW, "f", display_name="F", initial_node="n0")
    with pytest.raises(FlowStateError, match="no story"):
        set_story_status(tmp_workspace, "f", story_id="US-9", status="done")


def test_stories_survive_run_lifecycle(tmp_workspace):
    """stories 是 feature 级，跨 run 不丢。"""
    from kdev_core.flow_state import complete_run, start_run
    init_state(tmp_workspace, FLOW, "f", display_name="F", initial_node="n0")
    add_story(tmp_workspace, "f", story_id="US-1", title="X", status="done")
    complete_run(tmp_workspace, "f", status="completed")
    start_run(tmp_workspace, FLOW, "f", initial_node="n0b")
    assert read_state(tmp_workspace, FLOW, "f")["stories"][0]["status"] == "done"
```

- [ ] **Step 2: Run, verify fail**

Run: `cd plugins/kdev-core && python3 -m pytest tests/test_stories.py -v`
Expected: FAIL（`add_story`/`set_story_status` 未定义）

- [ ] **Step 3: 实现 add_story / set_story_status**

在 `flow_state.py` 追加：

```python
_VALID_STORY_STATUSES = {"pending", "in_progress", "done"}


def add_story(workspace, slug, *, story_id, title, status="pending", step_id=None):
    """追加一个用户故事到 stories[]（feature 级，HUD 完成度分母）。id 不可重复。"""
    if status not in _VALID_STORY_STATUSES:
        raise ValueError(f"story status must be one of {sorted(_VALID_STORY_STATUSES)}, got {status!r}")
    state = read_state(workspace, slug=slug)
    if any(s.get("id") == story_id for s in state.get("stories", [])):
        raise FlowStateError(f"story {story_id!r} already exists in feature {slug!r}")
    state["stories"] = [*state.get("stories", []),
                        {"id": story_id, "title": title, "status": status}]
    write_state(workspace, None, slug=slug, state=state, step_id=step_id)
    return read_state(workspace, slug=slug)


def set_story_status(workspace, slug, *, story_id, status, step_id=None):
    """更新某用户故事状态（HUD 完成度分子）。"""
    if status not in _VALID_STORY_STATUSES:
        raise ValueError(f"story status must be one of {sorted(_VALID_STORY_STATUSES)}, got {status!r}")
    state = read_state(workspace, slug=slug)
    stories = [dict(s) for s in state.get("stories", [])]
    for s in stories:
        if s.get("id") == story_id:
            s["status"] = status
            break
    else:
        raise FlowStateError(f"no story {story_id!r} in feature {slug!r}")
    state["stories"] = stories
    write_state(workspace, None, slug=slug, state=state, step_id=step_id)
    return read_state(workspace, slug=slug)
```

- [ ] **Step 4: Run, verify pass**

Run: `cd plugins/kdev-core && python3 -m pytest tests/test_stories.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add plugins/kdev-core/kdev_core/flow_state.py plugins/kdev-core/tests/test_stories.py
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-core): stories[] 用户故事 API (add_story/set_story_status, HUD 完成度分母)"
```

---

## Task 5: handoffs/<员工>/ 目录约定（最小：路径生成）

**Files:**
- Modify: `plugins/kdev-core/kdev_core/flow_state.py`（加 `handoff_dir`）
- Test: `plugins/kdev-core/tests/test_handoffs.py`

> 范围：只定目录约定 + 路径生成，**内容/协议留 P-B**（任务 #4）。

- [ ] **Step 1: 失败测试**

```python
# tests/test_handoffs.py
"""Tests for handoffs/<员工>/ 目录约定 (最小: 路径生成; 协议留 P-B)."""
from kdev_core.flow_state import handoff_dir


def test_handoff_dir_path_and_creates(tmp_workspace):
    p = handoff_dir(tmp_workspace, "user-auth", "req-architect")
    assert p == tmp_workspace / ".kdev" / "features" / "user-auth" / "handoffs" / "req-architect"
    assert p.is_dir()  # mkdir -p


def test_handoff_dir_idempotent(tmp_workspace):
    handoff_dir(tmp_workspace, "user-auth", "req-architect")
    p = handoff_dir(tmp_workspace, "user-auth", "req-architect")  # 第二次不报错
    assert p.is_dir()
```

- [ ] **Step 2: Run, verify fail**

Run: `cd plugins/kdev-core && python3 -m pytest tests/test_handoffs.py -v`
Expected: FAIL（`handoff_dir` 未定义）

- [ ] **Step 3: 实现 handoff_dir**

在 `flow_state.py` 追加：

```python
def handoff_dir(workspace, slug, employee):
    """返回（并 mkdir -p）.kdev/features/<slug>/handoffs/<employee>/。

    最小约定：只生成目录路径，内容由员工填、handoff 协议留 P-B。
    """
    p = _feature_dir(workspace, slug) / "handoffs" / employee
    p.mkdir(parents=True, exist_ok=True)
    return p
```

- [ ] **Step 4: Run, verify pass**

Run: `cd plugins/kdev-core && python3 -m pytest tests/test_handoffs.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add plugins/kdev-core/kdev_core/flow_state.py plugins/kdev-core/tests/test_handoffs.py
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-core): handoffs/<员工>/ 目录约定 (路径生成; 协议留 P-B)"
```

---

## Task 6: 持久化 smoke 测试更新 + 确认 R2/R3 端到端走新盘

**Files:**
- Update: `plugins/kdev-core/tests/test_smoke_lifecycle.py` / `tests/test_flow_lifecycle.py` / `tests/test_node_smoke.py` / `tests/test_gate_smoke.py`
- Modify: `plugins/kdev-core/tests/conftest.py`（docstring 注释路径）

> 这些测试调 `advance_persist`/`record_gate_persist`（R2/R3 文件里、只调 R1 read/write），跑端到端流转。**R2/R3 源码零改动**，但断言里的旧路径/旧字段要改。

- [ ] **Step 1: 先看现状跑红**

Run: `cd plugins/kdev-core && python3 -m pytest tests/test_smoke_lifecycle.py tests/test_flow_lifecycle.py tests/test_node_smoke.py tests/test_gate_smoke.py -v`
Expected: 多数 FAIL（旧 `.kdev/flows/` 路径断言 + `active is True` + `read_state(...)["history"]` 取全量历史）

- [ ] **Step 2: 机械迁移规则（逐文件套用）**

对这 4 个文件应用以下替换规则，**不改被测行为、只改路径/字段断言**：

1. 路径 helper：`ws/".kdev"/"flows"/flow/slug/"flow-state.json"` → `ws/".kdev"/"features"/slug/"flow-state.json"`。
2. `init_state(ws, flow, slug, ...)` 调用**保持不变**（签名兼容），但若断言 `st["active"] is True` → 改断言 `st["_has_active"] is True`。
3. 取节点：`read_state(...)["current_node"]` **不变**（扁平视图仍有）。
4. **历史断言改读 events**：凡断言 `read_state(...)["history"]` 含某 GateResult / `phase_history` 含某流转的，改为：
   ```python
   from kdev_core import events
   evs = events.read_events(ws, slug)
   gate_evs = [e for e in evs if e["type"] == "gate"]
   trans_evs = [e for e in evs if e["type"] == "transition"]
   # 断言改用 gate_evs / trans_evs（字段：verdict/gate/from/to/...）
   ```
5. `mark_inactive(...)` 调用不变；若断言终态后 `st["active"] is False` → 改 `st["_has_active"] is False`，且终结后 `current_node is None`（已折叠），原"最后节点"改从 `st["runs"][-1]["final_node"]` 取。
6. 终结后再 `resume_state` 期望抛错——`match=` 从旧文案改 `"not resumable"`。

**示例（test_smoke_lifecycle.py 典型片段改造前后）：**

改造前：
```python
init_state(ws, "coding-flow", "demo", display_name="Demo", initial_node="n0")
state = advance_persist(ws, "coding-flow", "demo", "n1", table=TABLE)
assert read_state(ws, "coding-flow", "demo")["current_node"] == "n1"
assert len(read_state(ws, "coding-flow", "demo")["phase_history"]) == 1
```
改造后：
```python
from kdev_core import events
init_state(ws, "coding-flow", "demo", display_name="Demo", initial_node="n0")
state = advance_persist(ws, "coding-flow", "demo", "n1", table=TABLE)
assert read_state(ws, "coding-flow", "demo")["current_node"] == "n1"
trans = [e for e in events.read_events(ws, "demo") if e["type"] == "transition"]
assert len(trans) == 1 and trans[0]["to"] == "n1"
```

- [ ] **Step 3: 应用规则，逐文件改**

按 Step 2 规则编辑 4 个文件。`conftest.py` 的 fixture docstring 注释 `.kdev/flows/<flow>/<slug>/` → `.kdev/features/<slug>/`。

- [ ] **Step 4: Run 全 R1/R2/R3 测试（除 CLI）**

Run: `cd plugins/kdev-core && python3 -m pytest tests/ -v --ignore=tests/test_cli.py --ignore=tests/test_cli_smoke.py --ignore=tests/test_new_cli.py`
Expected: PASS。**关键验证**：`test_advance.py`/`test_record_gate.py`/`test_node_table.py`/`test_gate_result.py` 全绿且**未被编辑**（git status 确认这 4 个文件无改动）= 适配层守住了 R2/R3 契约。

- [ ] **Step 5: Commit**

```bash
git add plugins/kdev-core/tests/
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "test(kdev-core): persist smoke 测试迁移 feature-first 路径 + events 断言 (R2/R3 源码/纯测试零改动)"
```

---

## Task 7: CLI 重构（路径 + 新 schema + 新增命令）

**Files:**
- Modify: `plugins/kdev-core/kdev_core/cli.py`
- Update: `plugins/kdev-core/tests/test_cli.py` / `tests/test_cli_smoke.py` / `tests/test_new_cli.py`

### CLI 变更清单
- `_print_state` 输出对齐扁平视图：`flow`(=active.flow)/`current_node`/`status`(run级)/`feature_status`/`active`(=`_has_active` 布尔)/`run`/`gate_calls`/`gate_iters`/`stories`/`runs` 概要/`blocked_reason`/`events_len`(=len(events.read_events))。**去掉** `history_len`/`phase_history`（改 `events_len`）。
- `init`：加 `--origin` / `--relates-to`（可选）。位置参数 `flow slug` 不变。
- `complete`：改调 `mark_inactive`（兼容：仍 fold+close_feature）。位置参数不变。
- 新增子命令：`start-run <flow> <slug> --initial-node ... [--review-mode] [--auto-mode]`、`add-story <flow> <slug> --id ... --title ... [--status]`、`set-story-status <flow> <slug> --id ... --status ...`、`close-feature <flow> <slug> [--status]`、`list-features`（`list-flows` 保留别名）、`events <flow> <slug>`、`handoff-path <flow> <slug> --employee ...`、`migrate [--workspace] [--dry-run] [--remove-old]`（Task 8 接 migrate 实现，本 Task 先留 `cmd_migrate` 调 `migrate.migrate_workspace`）。

> 注：`add-story`/`start-run` 等用 `_common`（带 `flow slug` 位置参数）保持签名一致；`flow` 对 stories 类命令是冗余但无害（统一签名优先）。

- [ ] **Step 1: 看 CLI 测试现状跑红 + 读现有断言**

Run: `cd plugins/kdev-core && python3 -m pytest tests/test_cli.py tests/test_cli_smoke.py tests/test_new_cli.py -v`
Expected: 多数 FAIL。先读这 3 个文件，记录每个测试断言的输出字段。

- [ ] **Step 2: 改 `_print_state` + 加新命令（失败测试先行）**

在 `test_new_cli.py` 末尾加新命令的失败测试（完整）：

```python
def test_cli_start_run_after_complete(tmp_workspace, run_cli):
    run_cli(["init", "coding-flow", "f", "--display-name", "F", "--initial-node", "n0"])
    run_cli(["complete", "coding-flow", "f"])
    out = run_cli(["start-run", "design-flow", "f", "--initial-node", "d0"])
    import json
    data = json.loads(out)
    assert data["run"] == 2 and data["flow"] == "design-flow"
    assert data["active"] is True and data["current_node"] == "d0"


def test_cli_add_story_and_list_features(tmp_workspace, run_cli):
    run_cli(["init", "coding-flow", "f", "--display-name", "F", "--initial-node", "n0"])
    run_cli(["add-story", "coding-flow", "f", "--id", "US-1", "--title", "登录"])
    run_cli(["set-story-status", "coding-flow", "f", "--id", "US-1", "--status", "done"])
    import json
    feats = json.loads(run_cli(["list-features"]))
    assert feats[0]["slug"] == "f"
    assert feats[0]["stories_done"] == 1 and feats[0]["stories_total"] == 1


def test_cli_events_after_advance(tmp_workspace, run_cli, toy_table_file):
    run_cli(["init", "toy", "f", "--display-name", "F", "--initial-node", "n1"])
    run_cli(["advance", "toy", "f", "g1", "--table", str(toy_table_file)])
    import json
    evs = json.loads(run_cli(["events", "toy", "f"]))
    assert any(e["type"] == "transition" and e["to"] == "g1" for e in evs)


def test_cli_handoff_path(tmp_workspace, run_cli):
    run_cli(["init", "coding-flow", "f", "--display-name", "F", "--initial-node", "n0"])
    out = run_cli(["handoff-path", "coding-flow", "f", "--employee", "req-architect"]).strip()
    assert out.endswith("/.kdev/features/f/handoffs/req-architect")
    from pathlib import Path
    assert Path(out).is_dir()
```

> `run_cli` / `toy_table_file` fixture：若 `test_new_cli.py` 已有 CLI 调用 helper 沿用；否则在 `conftest.py` 加（见 Step 3）。

- [ ] **Step 3: 加 conftest fixture（若缺）**

若现有 CLI 测试没有可复用的 `run_cli`/`toy_table_file`，在 `conftest.py` 追加：

```python
import io
import json as _json
from contextlib import redirect_stdout

import pytest
import yaml as _yaml

from kdev_core.cli import main as _cli_main


@pytest.fixture
def run_cli(tmp_workspace, monkeypatch):
    def _run(argv):
        # 所有命令注入 --workspace（list-features/migrate 用 --workspace；其余 _common 也支持）
        if "--workspace" not in argv:
            argv = argv + ["--workspace", str(tmp_workspace)]
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = _cli_main(argv)
        assert rc == 0, f"CLI {argv} exited {rc}"
        return buf.getvalue()
    return _run


@pytest.fixture
def toy_table_file(tmp_path):
    table = {
        "flow": "toy", "max_retries": 2, "terminal_fail": "failed",
        "nodes": [
            {"id": "n1", "kind": "action", "next": ["g1"]},
            {"id": "g1", "kind": "gate", "next": ["n2", "n1"]},
            {"id": "n2", "kind": "action", "next": ["done"]},
            {"id": "done", "kind": "terminal", "next": []},
            {"id": "failed", "kind": "terminal", "next": []},
        ],
    }
    p = tmp_path / "toy.node-table.yml"
    p.write_text(_yaml.safe_dump(table), encoding="utf-8")
    return p
```

> 若现有 helper 命名不同，复用现有的、删掉本 fixture 以免重复（DRY）。

- [ ] **Step 4: 改 cli.py**

`_print_state` 改为：

```python
def _print_state(state):
    from kdev_core import events
    slug = state.get("slug")
    print(json.dumps({
        "slug": slug,
        "flow": state.get("flow"),
        "display_name": state.get("display_name"),
        "feature_status": state.get("feature_status"),
        "status": state.get("status"),            # run 级
        "active": state.get("_has_active", False),
        "run": state.get("run"),
        "current_node": state.get("current_node"),
        "config": state.get("config"),
        "gate_calls": state.get("gate_calls", 0),
        "gate_iters": state.get("gate_iters", {}),
        "blocked_reason": state.get("blocked_reason"),
        "stories": state.get("stories", []),
        "runs": state.get("runs", []),
        "events_len": len(events.read_events(state.get("_workspace", "."), slug))
            if state.get("_workspace") else None,
    }, ensure_ascii=False, indent=2))
```

> `events_len` 需要 workspace——简化：`_print_state` 改签名 `_print_state(state, workspace)`，各 `cmd_*` 传 `args.workspace`。各 cmd 读 state 后调 `_print_state(state, args.workspace)`。`events_len = len(events.read_events(workspace, state["slug"]))`。

各命令体改造（核心几个，其余照搬模式）：

```python
def cmd_init(args):
    flow_state.init_state(args.workspace, args.flow, args.slug,
                          display_name=args.display_name,
                          review_mode=args.review_mode, auto_mode=args.auto_mode,
                          initial_node=args.initial_node,
                          origin=args.origin, relates_to=args.relates_to)
    _print_state(flow_state.read_state(args.workspace, slug=args.slug), args.workspace)
    return 0


def cmd_start_run(args):
    flow_state.start_run(args.workspace, args.flow, args.slug,
                         initial_node=args.initial_node,
                         review_mode=args.review_mode, auto_mode=args.auto_mode)
    _print_state(flow_state.read_state(args.workspace, slug=args.slug), args.workspace)
    return 0


def cmd_add_story(args):
    flow_state.add_story(args.workspace, args.slug, story_id=args.id,
                         title=args.title, status=args.status)
    _print_state(flow_state.read_state(args.workspace, slug=args.slug), args.workspace)
    return 0


def cmd_set_story_status(args):
    flow_state.set_story_status(args.workspace, args.slug, story_id=args.id, status=args.status)
    _print_state(flow_state.read_state(args.workspace, slug=args.slug), args.workspace)
    return 0


def cmd_close_feature(args):
    flow_state.close_feature(args.workspace, args.slug, status=args.status)
    _print_state(flow_state.read_state(args.workspace, slug=args.slug), args.workspace)
    return 0


def cmd_complete(args):
    flow_state.mark_inactive(args.workspace, args.flow, args.slug, status=args.status)
    _print_state(flow_state.read_state(args.workspace, slug=args.slug), args.workspace)
    return 0


def cmd_list_features(args):
    print(json.dumps(flow_state.list_features(args.workspace), ensure_ascii=False, indent=2))
    return 0


def cmd_events(args):
    from kdev_core import events
    print(json.dumps(events.read_events(args.workspace, args.slug), ensure_ascii=False, indent=2))
    return 0


def cmd_handoff_path(args):
    p = flow_state.handoff_dir(args.workspace, args.slug, args.employee)
    print(str(p))
    return 0


def cmd_migrate(args):
    from kdev_core import migrate
    report = migrate.migrate_workspace(args.workspace, dry_run=args.dry_run,
                                        remove_old=args.remove_old)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0
```

其余 `cmd_show`/`cmd_resume`/`cmd_advance`/`cmd_record_gate`/`cmd_next_step`/`cmd_gate_lookup`/`cmd_unblock`：把 `flow_state.read_state(args.workspace, args.flow, args.slug)` 保持（位置兼容），`_print_state(state)` → `_print_state(state, args.workspace)`。`advance`/`record_gate`/`next_step`/`gate_lookup` 调 `read_state` 用扁平视图，逻辑不变（`state.get("current_node")`/`state.get("gate_iters")` 仍在顶层）。

`build_parser` 追加子命令（用 `_common` 复用 `flow slug` 位置参数）：

```python
    pi.add_argument("--origin", default=None)
    pi.add_argument("--relates-to", default=None)

    psr = _common(sub, "start-run")
    psr.add_argument("--initial-node", default=None)
    psr.add_argument("--review-mode", default="ai", choices=["ai", "both", "human"])
    psr.add_argument("--auto-mode", action="store_true")
    psr.set_defaults(func=cmd_start_run)

    pas = _common(sub, "add-story")
    pas.add_argument("--id", required=True)
    pas.add_argument("--title", required=True)
    pas.add_argument("--status", default="pending", choices=["pending", "in_progress", "done"])
    pas.set_defaults(func=cmd_add_story)

    pss = _common(sub, "set-story-status")
    pss.add_argument("--id", required=True)
    pss.add_argument("--status", required=True, choices=["pending", "in_progress", "done"])
    pss.set_defaults(func=cmd_set_story_status)

    pcf = _common(sub, "close-feature")
    pcf.add_argument("--status", default="completed", choices=["completed", "aborted"])
    pcf.set_defaults(func=cmd_close_feature)

    pev = _common(sub, "events")
    pev.set_defaults(func=cmd_events)

    php = _common(sub, "handoff-path")
    php.add_argument("--employee", required=True)
    php.set_defaults(func=cmd_handoff_path)

    plf2 = sub.add_parser("list-features")
    plf2.add_argument("--workspace", default=".")
    plf2.set_defaults(func=cmd_list_features)

    pmg = sub.add_parser("migrate")
    pmg.add_argument("--workspace", default=".")
    pmg.add_argument("--dry-run", action="store_true")
    pmg.add_argument("--remove-old", action="store_true")
    pmg.set_defaults(func=cmd_migrate)
```

`list-flows` 别名：保留原 `plf`/`cmd_list_flows`，让 `cmd_list_flows` 内部调 `list_features`。`main` 的 except 子句加 `ValueError`（stories/status 校验）：`except (flow_state.FlowStateError, node_machine.NodeMachineError, gate.GateError, ValueError) as exc`。

- [ ] **Step 5: 改现有 CLI 测试断言**

`test_cli.py`/`test_cli_smoke.py`/`test_new_cli.py` 里：路径 `.kdev/flows/...` → `.kdev/features/<slug>/`；`history_len` → `events_len`；`active` 仍是 bool（现在来自 `_has_active`），断言不变或按需调整；终结后 `current_node` 改期望 `None`（已折叠）。

- [ ] **Step 6: Run 全 CLI + 全量**

Run: `cd plugins/kdev-core && python3 -m pytest tests/ -v`
Expected: 全 PASS（≥ 原 88 + 新增）。

- [ ] **Step 7: Commit**

```bash
git add plugins/kdev-core/kdev_core/cli.py plugins/kdev-core/tests/
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-core): CLI 对齐 feature-first (路径/新 schema 输出 + start-run/add-story/list-features/events/handoff-path)"
```

---

## Task 8: 迁移脚本（旧 flows/ → features/，幂等 + 合并 + history→events）

**Files:**
- Create: `plugins/kdev-core/kdev_core/migrate.py`
- Test: `plugins/kdev-core/tests/test_migrate.py`

### 语义
- 扫 `<ws>/.kdev/flows/<flow>/<slug>/flow-state.json`（旧布局）。
- 按 `slug` 分组（**同 slug 跨多 flow → 合并进一个 feature 的 runs[]/events**）。
- 每组按 `created_at` 排序：除最后一个外都折叠成 `runs[]` 摘要；最后一个若 `status=="in_progress"` 进 `active{}`，否则也折叠（active=null）。每个旧 flow 的 `history[]`→gate 事件、`phase_history[]`(若有)→transition 事件，写进该 feature 的 `events.jsonl`。
- feature 级 `status`：任一 run in_progress → in_progress；否则取最后一 run 的 status。
- `origin = "migrated:.kdev/flows"`；`stories=[]`。
- **幂等**：目标 `features/<slug>/flow-state.json` 已存在 → 跳过（report 标 skipped）。
- 非破坏：默认保留旧 `flows/`；`--remove-old` 才删。
- `dry_run`：只返回 report，不写盘。

- [ ] **Step 1: 失败测试**

```python
# tests/test_migrate.py
"""Tests for kdev_core.migrate — 旧 flows/ → feature-first (幂等 + 同slug合并 + history→events)."""
import json
from pathlib import Path

import pytest

from kdev_core import migrate, events
from kdev_core.flow_state import read_state


def _old_flow(ws: Path, flow, slug, doc):
    p = ws / ".kdev" / "flows" / flow / slug / "flow-state.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    return p


def _old_doc(flow, slug, status="completed", node="n-done", history=None):
    return {
        "flow": flow, "slug": slug, "display_name": slug.upper(),
        "status": status, "active": status == "in_progress", "current_node": node,
        "created_at": "2026-06-07T00:00:00+00:00", "updated_at": "2026-06-07T01:00:00+00:00",
        "config": {"review_mode": "ai", "auto_mode": False},
        "history": history or [],
    }


def test_migrate_single_completed_flow(tmp_workspace):
    _old_flow(tmp_workspace, "coding-flow", "ued6", _old_doc(
        "coding-flow", "ued6", history=[
            {"gate": "g1", "kind": "review", "node": "n4", "request_id": "r1", "iter": 1,
             "verdict": "PASS", "by": "ai", "issues": [], "revisions": [],
             "ts": "2026-06-07T00:30:00+00:00"}]))
    report = migrate.migrate_workspace(tmp_workspace)
    assert report["migrated"] == ["ued6"]
    st = read_state(tmp_workspace, slug="ued6")
    assert st["feature_status"] == "completed"
    assert st["_has_active"] is False
    assert st["runs"] == [{"flow": "coding-flow", "run": 1, "status": "completed",
                           "final_node": "n-done", "ended_at": st["runs"][0]["ended_at"]}]
    assert st["origin"] == "migrated:.kdev/flows"
    evs = events.read_events(tmp_workspace, "ued6")
    assert len(evs) == 1 and evs[0]["type"] == "gate" and evs[0]["verdict"] == "PASS"


def test_migrate_in_progress_flow_keeps_active(tmp_workspace):
    _old_flow(tmp_workspace, "coding-flow", "wip", _old_doc(
        "coding-flow", "wip", status="in_progress", node="n3"))
    migrate.migrate_workspace(tmp_workspace)
    st = read_state(tmp_workspace, slug="wip")
    assert st["_has_active"] is True
    assert st["current_node"] == "n3" and st["status"] == "in_progress"
    assert st["feature_status"] == "in_progress"
    assert st["runs"] == []


def test_migrate_same_slug_two_flows_merges(tmp_workspace):
    _old_flow(tmp_workspace, "design-flow", "auth", _old_doc(
        "design-flow", "auth", node="d-done"))
    _old_flow(tmp_workspace, "coding-flow", "auth", _old_doc(
        "coding-flow", "auth", status="in_progress", node="c3"))
    migrate.migrate_workspace(tmp_workspace)
    st = read_state(tmp_workspace, slug="auth")
    # design 折叠进 runs[]，coding(in_progress) 进 active
    assert len(st["runs"]) == 1 and st["runs"][0]["flow"] == "design-flow"
    assert st["_has_active"] is True and st["flow"] == "coding-flow"
    assert st["run"] == 2


def test_migrate_idempotent(tmp_workspace):
    _old_flow(tmp_workspace, "coding-flow", "ued6", _old_doc("coding-flow", "ued6"))
    r1 = migrate.migrate_workspace(tmp_workspace)
    r2 = migrate.migrate_workspace(tmp_workspace)
    assert r1["migrated"] == ["ued6"]
    assert r2["migrated"] == [] and r2["skipped"] == ["ued6"]
    # events 不重复
    assert len(events.read_events(tmp_workspace, "ued6")) == 0  # 该 doc history 空


def test_migrate_dry_run_writes_nothing(tmp_workspace):
    _old_flow(tmp_workspace, "coding-flow", "ued6", _old_doc("coding-flow", "ued6"))
    report = migrate.migrate_workspace(tmp_workspace, dry_run=True)
    assert report["migrated"] == ["ued6"]
    assert not (tmp_workspace / ".kdev" / "features").exists()


def test_migrate_remove_old(tmp_workspace):
    _old_flow(tmp_workspace, "coding-flow", "ued6", _old_doc("coding-flow", "ued6"))
    migrate.migrate_workspace(tmp_workspace, remove_old=True)
    assert not (tmp_workspace / ".kdev" / "flows" / "coding-flow" / "ued6").exists()
    assert (tmp_workspace / ".kdev" / "features" / "ued6" / "flow-state.json").exists()


def test_migrate_empty_workspace(tmp_workspace):
    report = migrate.migrate_workspace(tmp_workspace)
    assert report == {"migrated": [], "skipped": [], "dry_run": False}
```

- [ ] **Step 2: Run, verify fail**

Run: `cd plugins/kdev-core && python3 -m pytest tests/test_migrate.py -v`
Expected: FAIL（`migrate` 模块未建）

- [ ] **Step 3: 实现 migrate.py**

```python
# kdev_core/migrate.py
"""kdev-core 迁移：旧 .kdev/flows/<flow>/<slug>/ → feature-first .kdev/features/<slug>/.

幂等（目标已存在则跳过）；同 slug 跨多 flow 合并进一个 feature 的 runs[]+events；
旧 history[]→gate 事件、phase_history[]→transition 事件。非破坏（--remove-old 才删旧）。
"""
import json
import shutil
from pathlib import Path

from kdev_core import events as _events
from kdev_core import flow_state as _fs


def _old_flows_root(workspace) -> Path:
    return Path(workspace) / ".kdev" / "flows"


def _scan_old(workspace):
    """收集旧 flow-state：{slug: [(flow, doc), ...]}，按 created_at 排序。"""
    root = _old_flows_root(workspace)
    by_slug = {}
    if not root.exists():
        return by_slug
    for flow_dir in sorted(root.iterdir()):
        if not flow_dir.is_dir():
            continue
        for slug_dir in sorted(flow_dir.iterdir()):
            sp = slug_dir / "flow-state.json"
            if not sp.exists():
                continue
            try:
                doc = json.loads(sp.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            doc.pop("_meta", None)
            by_slug.setdefault(slug_dir.name, []).append((flow_dir.name, doc))
    for slug in by_slug:
        by_slug[slug].sort(key=lambda fd: fd[1].get("created_at", ""))
    return by_slug


def _run_summary(flow, run_no, doc):
    return {
        "flow": flow, "run": run_no, "status": doc.get("status", "completed"),
        "final_node": doc.get("current_node"), "ended_at": doc.get("updated_at"),
    }


def _emit_events(workspace, slug, flow, run_no, doc):
    for entry in doc.get("phase_history", []) or []:
        _events.append_event(workspace, slug,
                             _events.transition_event(slug=slug, flow=flow, run=run_no, entry=entry))
    for gr in doc.get("history", []) or []:
        _events.append_event(workspace, slug,
                             _events.gate_event(slug=slug, flow=flow, run=run_no, gate_result=gr))


def migrate_workspace(workspace, *, dry_run=False, remove_old=False):
    """迁移整个 workspace。返回 {migrated:[slug], skipped:[slug], dry_run:bool}。"""
    by_slug = _scan_old(workspace)
    migrated, skipped = [], []
    for slug, flows in by_slug.items():
        target = _fs._state_path(workspace, slug)
        if target.exists():
            skipped.append(slug)
            continue
        if dry_run:
            migrated.append(slug)
            continue
        first_flow, first_doc = flows[0]
        display_name = first_doc.get("display_name", slug)
        created_at = first_doc.get("created_at") or _fs._now_iso()
        config = first_doc.get("config", {"review_mode": "ai", "auto_mode": False})
        runs, active = [], None
        feature_in_progress = False
        run_no = 0
        for idx, (flow, doc) in enumerate(flows):
            run_no += 1
            is_last = idx == len(flows) - 1
            _emit_events(workspace, slug, flow, run_no, doc)
            if is_last and doc.get("status") == "in_progress":
                active = {
                    "flow": flow, "run": run_no,
                    "current_node": doc.get("current_node"),
                    "status": "in_progress",
                    "gate_iters": {}, "gate_calls": 0, "retries": {},
                    "blocked_reason": None, "config": doc.get("config", config),
                    "started_at": doc.get("created_at") or created_at,
                }
                feature_in_progress = True
            else:
                runs.append(_run_summary(flow, run_no, doc))
        if feature_in_progress:
            feature_status = "in_progress"
        else:
            feature_status = flows[-1][1].get("status", "completed")
        out_doc = {
            "slug": slug, "display_name": display_name,
            "origin": "migrated:.kdev/flows", "relates_to": None,
            "status": feature_status, "stories": [], "runs": runs, "active": active,
            "created_at": created_at,
        }
        _fs._write_doc(workspace, slug, out_doc)
        if remove_old:
            for flow, _doc in flows:
                shutil.rmtree(_old_flows_root(workspace) / flow / slug, ignore_errors=True)
        migrated.append(slug)
    return {"migrated": sorted(migrated), "skipped": sorted(skipped), "dry_run": dry_run}
```

- [ ] **Step 4: Run, verify pass**

Run: `cd plugins/kdev-core && python3 -m pytest tests/test_migrate.py -v`
Expected: PASS（8 tests）

- [ ] **Step 5: Commit**

```bash
git add plugins/kdev-core/kdev_core/migrate.py plugins/kdev-core/tests/test_migrate.py
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-core): 迁移脚本 flows/→features/ (幂等 + 同slug合并 + history→events.jsonl)"
```

---

## Task 9: 跑迁移 + 全量回归 + 打包（plugin.json / marketplace / CHANGELOG / version）

**Files:**
- Create: `plugins/kdev-core/.claude-plugin/plugin.json`
- Create: `plugins/kdev-core/CHANGELOG.md`
- Modify: `plugins/kdev-core/kdev_core/__init__.py`
- Modify: `.claude-plugin/marketplace.json`

- [ ] **Step 1: 全量回归**

Run: `cd plugins/kdev-core && python3 -m pytest tests/ -v`
Expected: 全 PASS。记录总数（应 ≥ 88 + 新增 ≈ 120+）。

- [ ] **Step 2: 确认 R2/R3 源码 + 纯测试零改动**

Run:
```bash
cd /home/lyadmin/Projects/kdev-agents/.claude/worktrees/p-core-ff
git log --oneline -p -- plugins/kdev-core/kdev_core/node_machine.py plugins/kdev-core/kdev_core/gate.py | grep -c "^+++" 
git diff 02e4d10 -- plugins/kdev-core/kdev_core/node_machine.py plugins/kdev-core/kdev_core/gate.py
git diff 02e4d10 -- plugins/kdev-core/tests/test_advance.py plugins/kdev-core/tests/test_record_gate.py plugins/kdev-core/tests/test_node_table.py plugins/kdev-core/tests/test_gate_result.py
```
Expected: **空 diff**（R2/R3 源码 + 4 个纯函数测试文件零改动 = 适配层守约的硬证据）。若非空 → 违反拍板8，回退重做。

- [ ] **Step 3: 加 `__version__`**

`kdev_core/__init__.py` 加（保留现有内容，追加）：

```python
__version__ = "0.2.0"
```

- [ ] **Step 4: 建 plugin.json**

`plugins/kdev-core/.claude-plugin/plugin.json`：

```json
{
  "name": "kdev-core",
  "description": "KDev 数字员工编排底座（R1 状态记录 / R2 流转引擎 / R3 三类关卡）。feature-first 存储：.kdev/features/<slug>/（台账 runs[] + 用户故事 stories[] + 单棒控制态 active{} + 事实流水 events.jsonl）。薄引擎只记账+流转、不做判断；R2/R3 纯函数、断点续跑、有界回流 + escalate 不降级。被 kdev-team orchestrator 经 `python -m kdev_core` CLI 驱动。",
  "version": "0.2.0",
  "author": { "name": "ly" },
  "license": "MIT",
  "keywords": ["orchestration", "state-machine", "feature-first", "flow-state", "events", "kdev"]
}
```

- [ ] **Step 5: 建 CHANGELOG.md**

`plugins/kdev-core/CHANGELOG.md`：

```markdown
# Changelog · kdev-core

本插件遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [0.2.0] - 2026-06-11

### 重大变更（P-Core-FF：R1 存储层 feature-first 重构）

- **存储布局翻转**：`.kdev/flows/<flow>/<slug>/` → `.kdev/features/<slug>/`（功能当顶层）。
- **flow-state.json schema 重构**：新增 `stories[]`（用户故事，HUD 完成度分母）、`runs[]`（台账，跑完棒次摘要不可变）、`active{}`（当前单棒控制态：flow/run/current_node/status/gate_iters/config…）、`origin`/`relates_to`（slug 回链，v0.1）。两级 status（feature 级 + run 级）。布尔 stale-guard `active` 废弃，续跑由 `active{}` 生命周期推导。
- **events.jsonl 事实流水**：原内嵌 `history`/`phase_history` 挪到同目录 `events.jsonl`（append-only，行内带 actor + slug/flow/run）。新增 `kdev_core.events` 读写 API。
- **run 生命周期**：`complete_run`（折叠 active→runs[]+清空）、`start_run`（补活开新 run）、`close_feature`（显式收口 feature 级）。
- **stories API**：`add_story` / `set_story_status`。
- **handoffs/<员工>/ 目录约定**（最小：路径生成，协议留 P-B）。
- **迁移脚本**：`python -m kdev_core migrate`（幂等 + 同 slug 跨 flow 合并 + history→events）。
- **CLI**：保留 `<flow> <slug>` 兼容签名；新增 `start-run`/`add-story`/`set-story-status`/`close-feature`/`list-features`/`events`/`handoff-path`/`migrate`。
- **不变**：R2(`node_machine`)/R3(`gate`) 纯函数零改动——R1 做扁平内存/嵌套磁盘翻译适配层。

### 关联

Q-012（feature-first 存储重设计）/ Q-013（P-Core-FF 提前）。下游 P-A 需求架构师 + kdev-hud 共同前置。
```

- [ ] **Step 6: marketplace.json 加 kdev-core 条目**

在 `.claude-plugin/marketplace.json` 的 `plugins` 数组**末尾**追加（注意前一条目补逗号）：

```json
    {
      "name": "kdev-core",
      "description": "数字员工编排底座（R1 状态/R2 流转/R3 关卡）：feature-first 存储 + events.jsonl 流水。被 kdev-team 经 python -m kdev_core 驱动。",
      "category": "development",
      "source": "./plugins/kdev-core"
    }
```

校验 JSON 合法：`python3 -c "import json; json.load(open('.claude-plugin/marketplace.json')); print('ok')"`

- [ ] **Step 7: 跑框架仓自身迁移（dry-run 先看）**

```bash
cd /home/lyadmin/Projects/kdev-agents/.claude/worktrees/p-core-ff
python3 -c "import sys; sys.path.insert(0,'plugins/kdev-core'); from kdev_core import migrate; import json; print(json.dumps(migrate.migrate_workspace('.', dry_run=True)))"
```
Expected: `{"migrated": [], "skipped": [], "dry_run": true}`（框架 worktree 无 `.kdev/flows` 数据，已确认）。无需实跑。

> **dogfood 仓迁移**（`~/Projects/kdev-dogfood-ued6`，有 1 个 `coding-flow/ued6-restyle`）是独立仓，**不在本 worktree commit 范围**。收尾时单独执行（见「完成后」段），先 `--dry-run` 给用户看再实跑。

- [ ] **Step 8: 全量回归 + commit**

```bash
cd plugins/kdev-core && python3 -m pytest tests/ -q
```
Expected: 全绿。

```bash
cd /home/lyadmin/Projects/kdev-agents/.claude/worktrees/p-core-ff
git add plugins/kdev-core/.claude-plugin/plugin.json plugins/kdev-core/CHANGELOG.md \
        plugins/kdev-core/kdev_core/__init__.py .claude-plugin/marketplace.json
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "release(kdev-core): v0.2.0 feature-first 存储 (plugin.json + marketplace 注册 + CHANGELOG)"
```

---

## Task 10: 回写设计文档（roadmap §1.5.2 + Q-012 落地状态）

**Files:**
- Modify: `docs/framework/01-design/<roadmap 文件>` §1.5.2（P-Core-FF ✅）+ §「现状 vs 设计」落差表（R1 存储层 🔨→✅）
- 合稿 v1.0 §落差表：R1 存储层、events.jsonl、handoffs 状态更新（设计→已实现）。

- [ ] **Step 1: 定位 roadmap 文件**

Run: `grep -rln "P-Core-FF\|§1.5.2\|1.5.4" docs/framework/ | head`

- [ ] **Step 2: 改 roadmap §1.5.2**：P-Core-FF 标 ✅ done（v0.2.0），记完成日期 2026-06-11 + 关键交付（features/ 翻转 + events.jsonl + runs/stories + 迁移）。

- [ ] **Step 3: 改合稿 §落差表**：`R1 存储层 🔨 待 refit` → `✅ 已实现 (kdev-core v0.2.0)`；`events.jsonl ⏳ 未建` → `✅ 已建`；handoffs 标「目录约定已建，协议待 P-B」。

- [ ] **Step 4: Commit**

```bash
git add docs/framework/
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "docs(framework): roadmap §1.5.2 标 P-Core-FF ✅ + 合稿落差表 R1 存储层 设计→实现"
```

> `.kdev/memory/决策日志.md` 的 Q-012 落地状态（promote_status 等）由**主会话**在收尾时更新（`.kdev/memory/` 是本地工程记忆、在主 checkout 不在 worktree）。

---

## Self-Review（写完自查）

**1. Spec coverage**（对照任务 7 点 + 硬约束）：
- ① 路径翻转 features/<slug>/ → Task 2 ✓
- ② flow-state schema（stories/runs/active/origin + 运转规则）→ Task 2/3/4 ✓
- ③ history → events.jsonl + 写入 API → Task 1（events.py）+ Task 2（虹吸）✓
- ④ handoffs/<员工>/ 目录约定 → Task 5 ✓
- ⑤ slug mint v0.1（origin 回链 + relates_to，调用方直传）→ Task 2（init 加 origin/relates_to）✓
- ⑥ 迁移脚本（幂等 + history→events + 框架仓/dogfood）→ Task 8 + Task 9 Step 7 ✓
- ⑦ CLI 跟着改 → Task 7 ✓
- ⑧ bump version + CHANGELOG（+ Q4 升 marketplace 插件）→ Task 9 ✓
- 硬约束 R2/R3 不动 → Task 6 Step 4 + Task 9 Step 2 硬验证（空 diff）✓
- 下游契约（HUD 读 stories[]/events actor/active；P-A 落 handoffs）→ 契约参考 A/B/C 节 + 各 Task 字段严格照 §2.1 ✓

**2. Placeholder scan**：无 TBD/TODO；每个代码步给完整代码；测试给完整断言。Task 6 的"逐文件套用规则"给了规则 + 改造前后完整示例（非 placeholder，因为现有测试内容多样、规则化迁移比逐行复制更不易错）。

**3. Type consistency**：扁平视图键名（`_has_active`/`feature_status`/`status`/`current_node`/`gate_iters`/`gate_calls`/`retries`/`run`/`flow`）跨 Task 2–9 一致；`complete_run`/`start_run`/`close_feature`/`add_story`/`set_story_status`/`handoff_dir`/`migrate_workspace` 签名跨 Task 与 CLI 调用一致；events 行字段（`type`/`actor`/`slug`/`flow`/`run`/`from`/`to`/`verdict`…）跨 events.py / 虹吸 / 迁移 / 测试一致。

**4. 已知风险**：`write_state` 的位置/关键字参数兼容垫片（旧 `write_state(ws, flow, slug, state)` vs 新 `write_state(ws, flow, slug=..., state=...)`）—— 实施时优先让所有内部调用用关键字式 `write_state(ws, flow_or_None, slug=slug, state=st)`，`advance_persist`/`record_gate_persist`（不改源码）走旧位置式 `write_state(ws, flow, slug, new_state)`，垫片须同时支持两种。Task 2 实现后立即用 `test_node_smoke.py`/`test_gate_smoke.py`（走 *_persist）验证垫片正确。

---

## 完成后（收尾，超出 worktree commit 范围）

1. **dogfood 仓迁移**：`cd ~/Projects/kdev-dogfood-ued6 && PYTHONPATH=<worktree>/plugins/kdev-core python3 -m kdev_core migrate --dry-run` → 给用户看 report → 确认后去掉 `--dry-run`（可选 `--remove-old`）。
2. **主会话**更新 `.kdev/memory/决策日志.md` Q-012 `promote_status`/落地状态（设计→实现）。
3. **follow-up（不在本步）**：kdev-team `PYTHONPATH=$FRAMEWORK_REPO/...` → cache 路径 rewiring（让 marketplace-装的用户跑得起来）。
4. 用 `superpowers:finishing-a-development-branch` 决定合并方式（merge/PR）。
