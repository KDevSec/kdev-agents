# 阶段1 P5：开发工程师 coding-flow 接 kdev-core 底座 — 实施计划（框架侧）

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 给 kdev-core 加一层 harness-中立的薄 CLI，让"开发工程师-编排"persona Agent 能在节点上显式驱动 R1/R2/R3 引擎；并落 coding-flow 的 13 节点 node-table + gate_specs（含 reviewer 绑定 + node9 拆 9a/9b）+ 7 个轻量 persona + SKILL 接底座入口节。

**Architecture:** CLI（`python -m kdev_core <cmd>`）是 R1/R2/R3 现有纯函数 + `*_persist` 的薄 argparse 壳；node-table（含 gate_specs 段）是 YAML 数据，CLI 用 PyYAML 读 + `node_machine.load_node_table` 验。引擎、node-table、gate 逻辑全 harness-中立；CC 只承担"发 Bash 命令的 LLM"。**本计划只做框架侧 TDD 建设，不含 Pass1 dogfood 实跑**（后续阶段）。

**Tech Stack:** Python 3 · argparse · PyYAML 6.0.1 · pytest（`cd plugins/kdev-core && python3 -m pytest`，conftest 已把 `plugins/kdev-core` 放 sys.path）。

**配套**：设计稿 [docs/superpowers/specs/2026-06-06-阶段1-coding-flow接底座-design.md](../specs/2026-06-06-阶段1-coding-flow接底座-design.md)。引擎源码：`plugins/kdev-core/kdev_core/{flow_state,node_machine,gate}.py`。

**Commit 身份硬规（每个 commit 步骤必须照用）**：AI commit 必须覆盖身份且 `-c` 的 `key=value` **不加引号**（项目 block-unattributed-commit hook 字面校验，带引号会 deny；见 G-001/G-002）：
```
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "..."
```
**不要 push**（push 由用户确认；本计划全程只 commit）。

---

## File Structure

**kdev-core（引擎 + CLI）**
- Create `plugins/kdev-core/kdev_core/cli.py` — argparse CLI：`init/show/resume/advance/record-gate` 子命令，调 R1/R2/R3 的 `*_persist`，PyYAML 读 node-table。
- Create `plugins/kdev-core/kdev_core/__main__.py` — `python -m kdev_core` 入口（`sys.exit(cli.main())`）。
- Create `plugins/kdev-core/tests/test_cli.py` — 各子命令单测。
- Create `plugins/kdev-core/tests/test_cli_smoke.py` — CLI 集成 smoke（full-lifecycle + resume + reflow + escalate）。

**kdev-coding-flow（编排配置 + persona）**
- Create `plugins/kdev-coding-flow/skills/kdev-coding-flow/orchestration/node-table.yml` — 16 节点（13 逻辑 + node9 拆 9a/9b + 2 terminal）+ `gate_specs` 段（kind/on_pass/on_reflow/branches/reviewer）。
- Create `plugins/kdev-coding-flow/tests/conftest.py` — 把 `plugins/kdev-core` 放 sys.path（复用引擎做校验）。
- Create `plugins/kdev-coding-flow/tests/test_orchestration_config.py` — node-table.yml 载入 + 一致性校验。
- Create `plugins/kdev-coding-flow/skills/kdev-coding-flow/personas/{开发工程师-编排,环境准备,实施计划,前端实现,E2E视觉验收,部署上线,安全扫描}.md` — 7 轻量 persona。
- Create `plugins/kdev-coding-flow/tests/test_personas.py` — persona 结构校验。
- Modify `plugins/kdev-coding-flow/skills/kdev-coding-flow/SKILL.md` — 加「接 kdev-core 底座入口」节。

**文档回写**
- Modify `docs/framework/01-design/2026-06-06-01-数字员工集群-起步roadmap-Q004细化-v0.1.md` §1.5 — P5 框架侧 done。

---

## Task 1: CLI 骨架 + `show` 子命令 + `python -m kdev_core` 入口

**Files:**
- Create: `plugins/kdev-core/kdev_core/cli.py`
- Create: `plugins/kdev-core/kdev_core/__main__.py`
- Test: `plugins/kdev-core/tests/test_cli.py`

- [ ] **Step 1: 写失败测试**（`tests/test_cli.py`）

```python
import json
import pytest
from kdev_core import cli, flow_state

FLOW = "coding-flow"


def test_show_prints_current_node(tmp_workspace, capsys):
    flow_state.init_state(tmp_workspace, FLOW, "auth",
                          display_name="Auth", initial_node="n0-env")
    rc = cli.main(["show", FLOW, "auth", "--workspace", str(tmp_workspace)])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert out["current_node"] == "n0-env"
    assert out["status"] == "in_progress"
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd plugins/kdev-core && python3 -m pytest tests/test_cli.py -v`
Expected: FAIL（`ModuleNotFoundError: No module named 'kdev_core.cli'`）

- [ ] **Step 3: 写最小实现**（`kdev_core/cli.py`）

```python
"""kdev-core CLI — drive a flow's R1/R2/R3 engine from the shell.

Thin argparse shell over flow_state (R1) / node_machine (R2) / gate (R3): the
orchestration Agent calls these subcommands at each node. The engine + node-table
stay harness-agnostic; the CLI is just a portable seam. node-table (+ its
`gate_specs` section) is data loaded from a YAML file.
"""
import argparse
import json
import sys
from pathlib import Path

import yaml

from kdev_core import flow_state, node_machine, gate


def _load_table(path):
    """Load a node-table YAML -> (validated table, gate_specs dict)."""
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    table = node_machine.load_node_table(data)
    return table, data.get("gate_specs", {})


def _print_state(state):
    print(json.dumps({
        "flow": state["flow"],
        "slug": state["slug"],
        "status": state["status"],
        "active": state["active"],
        "current_node": state["current_node"],
        "gate_calls": state.get("gate_calls", 0),
        "history_len": len(state.get("history", [])),
    }, ensure_ascii=False, indent=2))


def cmd_show(args):
    _print_state(flow_state.read_state(args.workspace, args.flow, args.slug))
    return 0


def _common(sub, name):
    """A subparser with the shared --workspace + flow/slug positionals."""
    sp = sub.add_parser(name)
    sp.add_argument("flow")
    sp.add_argument("slug")
    sp.add_argument("--workspace", default=".", help="workspace root (default: cwd)")
    return sp


def build_parser():
    p = argparse.ArgumentParser(prog="kdev_core",
                                description="Drive a flow's R1/R2/R3 engine.")
    sub = p.add_subparsers(dest="cmd", required=True)

    ps = _common(sub, "show")
    ps.set_defaults(func=cmd_show)

    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (flow_state.FlowStateError, node_machine.NodeMachineError,
            gate.GateError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
```

`kdev_core/__main__.py`：

```python
import sys

from kdev_core.cli import main

if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd plugins/kdev-core && python3 -m pytest tests/test_cli.py -v`
Expected: PASS

- [ ] **Step 5: 验 `python -m kdev_core` 入口可跑**

Run: `cd plugins/kdev-core && python3 -m kdev_core show coding-flow nope --workspace /tmp 2>&1; echo "rc=$?"`
Expected: `error: no flow-state.json at ...`（rc=1，证明入口 + 错误处理通）

- [ ] **Step 6: Commit**

```bash
git add plugins/kdev-core/kdev_core/cli.py plugins/kdev-core/kdev_core/__main__.py plugins/kdev-core/tests/test_cli.py
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-core): CLI 骨架 + show 子命令 + python -m kdev_core 入口"
```

---

## Task 2: `init` 子命令

**Files:**
- Modify: `plugins/kdev-core/kdev_core/cli.py`
- Test: `plugins/kdev-core/tests/test_cli.py`

- [ ] **Step 1: 写失败测试**（追加到 `test_cli.py`）

```python
def test_init_creates_state(tmp_workspace, capsys):
    rc = cli.main(["init", FLOW, "ued6", "--display-name", "UED6 改造",
                   "--initial-node", "n0-env", "--auto-mode",
                   "--workspace", str(tmp_workspace)])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert out["current_node"] == "n0-env"
    st = flow_state.read_state(tmp_workspace, FLOW, "ued6")
    assert st["display_name"] == "UED6 改造"
    assert st["config"]["auto_mode"] is True
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd plugins/kdev-core && python3 -m pytest tests/test_cli.py::test_init_creates_state -v`
Expected: FAIL（`invalid choice: 'init'`）

- [ ] **Step 3: 写最小实现**（`cli.py`：加 `cmd_init` + 注册 subparser）

```python
def cmd_init(args):
    flow_state.init_state(args.workspace, args.flow, args.slug,
                          display_name=args.display_name,
                          review_mode=args.review_mode,
                          auto_mode=args.auto_mode,
                          initial_node=args.initial_node)
    _print_state(flow_state.read_state(args.workspace, args.flow, args.slug))
    return 0
```

在 `build_parser()` 的 `sub` 后加：

```python
    pi = _common(sub, "init")
    pi.add_argument("--display-name", required=True)
    pi.add_argument("--review-mode", default="ai", choices=["ai", "both", "human"])
    pi.add_argument("--auto-mode", action="store_true")
    pi.add_argument("--initial-node", default=None)
    pi.set_defaults(func=cmd_init)
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd plugins/kdev-core && python3 -m pytest tests/test_cli.py -v`
Expected: PASS（2 passed）

- [ ] **Step 5: Commit**

```bash
git add plugins/kdev-core/kdev_core/cli.py plugins/kdev-core/tests/test_cli.py
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-core): CLI init 子命令"
```

---

## Task 3: `resume` 子命令

**Files:**
- Modify: `plugins/kdev-core/kdev_core/cli.py`
- Test: `plugins/kdev-core/tests/test_cli.py`

- [ ] **Step 1: 写失败测试**

```python
def test_resume_returns_current_node(tmp_workspace, capsys):
    flow_state.init_state(tmp_workspace, FLOW, "auth",
                          display_name="Auth", initial_node="n0-env")
    st = flow_state.read_state(tmp_workspace, FLOW, "auth")
    st["current_node"] = "n6b-impl-subagent"
    flow_state.write_state(tmp_workspace, FLOW, "auth", st)
    rc = cli.main(["resume", FLOW, "auth", "--workspace", str(tmp_workspace)])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert out["current_node"] == "n6b-impl-subagent"  # 不从头


def test_resume_on_completed_errors(tmp_workspace, capsys):
    flow_state.init_state(tmp_workspace, FLOW, "auth",
                          display_name="Auth", initial_node="n0-env")
    flow_state.mark_inactive(tmp_workspace, FLOW, "auth", status="completed")
    rc = cli.main(["resume", FLOW, "auth", "--workspace", str(tmp_workspace)])
    assert rc == 1
    assert "not resumable" in capsys.readouterr().err
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd plugins/kdev-core && python3 -m pytest tests/test_cli.py -k resume -v`
Expected: FAIL（`invalid choice: 'resume'`）

- [ ] **Step 3: 写最小实现**

```python
def cmd_resume(args):
    _print_state(flow_state.resume_state(args.workspace, args.flow, args.slug))
    return 0
```

`build_parser()` 加：

```python
    pr = _common(sub, "resume")
    pr.set_defaults(func=cmd_resume)
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd plugins/kdev-core && python3 -m pytest tests/test_cli.py -k resume -v`
Expected: PASS（2 passed）

- [ ] **Step 5: Commit**

```bash
git add plugins/kdev-core/kdev_core/cli.py plugins/kdev-core/tests/test_cli.py
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-core): CLI resume 子命令"
```

---

## Task 4: node-table YAML 载入 + `advance` 子命令

**Files:**
- Modify: `plugins/kdev-core/kdev_core/cli.py`
- Test: `plugins/kdev-core/tests/test_cli.py`

> `_load_table` 已在 Task 1 写好。本任务加 `advance` 子命令 + 用一个 tmp fixture node-table 验。

- [ ] **Step 1: 写失败测试**（含一个写 tmp node-table 的 helper）

```python
def _write_table(tmp_workspace):
    table_path = tmp_workspace / "nt.yml"
    table_path.write_text(
        "flow: coding-flow\n"
        "max_retries: 3\n"
        "terminal_fail: n-fail\n"
        "nodes:\n"
        "  - {id: n0, kind: action, next: [n1]}\n"
        "  - {id: n1, kind: action, next: [n0, n-fail]}\n"
        "  - {id: n-fail, kind: terminal, next: []}\n",
        encoding="utf-8")
    return str(table_path)


def test_advance_moves_node(tmp_workspace, capsys):
    flow_state.init_state(tmp_workspace, FLOW, "a",
                          display_name="A", initial_node="n0")
    table = _write_table(tmp_workspace)
    rc = cli.main(["advance", FLOW, "a", "n1", "--table", table,
                   "--reason", "go", "--workspace", str(tmp_workspace)])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert out["current_node"] == "n1"


def test_advance_reflow_overflow_forces_terminal_fail(tmp_workspace, capsys):
    flow_state.init_state(tmp_workspace, FLOW, "a",
                          display_name="A", initial_node="n0")
    table = _write_table(tmp_workspace)
    cli.main(["advance", FLOW, "a", "n1", "--table", table,
              "--workspace", str(tmp_workspace)])
    # n1 -> n0 reflow x4 (> max_retries 3) 强制 terminal_fail
    for _ in range(4):
        cli.main(["advance", FLOW, "a", "n0", "--table", table, "--reflow",
                  "--workspace", str(tmp_workspace)])
        cli.main(["advance", FLOW, "a", "n1", "--table", table,
                  "--workspace", str(tmp_workspace)])
    capsys.readouterr()
    cli.main(["advance", FLOW, "a", "n0", "--table", table, "--reflow",
              "--workspace", str(tmp_workspace)])
    out = json.loads(capsys.readouterr().out)
    assert out["current_node"] == "n-fail"
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd plugins/kdev-core && python3 -m pytest tests/test_cli.py -k advance -v`
Expected: FAIL（`invalid choice: 'advance'`）

- [ ] **Step 3: 写最小实现**

```python
def cmd_advance(args):
    table, _ = _load_table(args.table)
    state = node_machine.advance_persist(
        args.workspace, args.flow, args.slug, args.to_node,
        table=table, reflow=args.reflow, reason=args.reason)
    _print_state(state)
    return 0
```

`build_parser()` 加：

```python
    pa = _common(sub, "advance")
    pa.add_argument("to_node")
    pa.add_argument("--table", required=True)
    pa.add_argument("--reflow", action="store_true")
    pa.add_argument("--reason", default=None)
    pa.set_defaults(func=cmd_advance)
```

> 注意：`_common` 加的是 `flow slug`，`advance` 还需位置参数 `to_node`——`_common` 返回的 subparser 上再 `add_argument("to_node")` 即可（argparse 位置参数按声明顺序：flow, slug, to_node）。

- [ ] **Step 4: 跑测试确认通过**

Run: `cd plugins/kdev-core && python3 -m pytest tests/test_cli.py -k advance -v`
Expected: PASS（2 passed）

- [ ] **Step 5: Commit**

```bash
git add plugins/kdev-core/kdev_core/cli.py plugins/kdev-core/tests/test_cli.py
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-core): CLI advance 子命令 + node-table YAML 载入"
```

---

## Task 5: `record-gate` 子命令（review/decision/acceptance + escalate）

**Files:**
- Modify: `plugins/kdev-core/kdev_core/cli.py`
- Test: `plugins/kdev-core/tests/test_cli.py`

- [ ] **Step 1: 写失败测试**（带 gate_specs 的 fixture table）

```python
def _write_gate_table(tmp_workspace):
    table_path = tmp_workspace / "gt.yml"
    table_path.write_text(
        "flow: coding-flow\n"
        "max_retries: 3\n"
        "nodes:\n"
        "  - {id: n-impl, kind: action, next: [n-rev]}\n"
        "  - {id: n-rev, kind: gate, gate: g-rev, next: [n-acc, n-impl]}\n"
        "  - {id: n-acc, kind: gate, gate: g-acc, next: [n-done, n-impl]}\n"
        "  - {id: n-done, kind: terminal, next: []}\n"
        "gate_specs:\n"
        "  g-rev: {kind: review, on_pass: n-acc, on_reflow: n-impl, reviewer: self}\n"
        "  g-acc: {kind: acceptance, on_pass: n-done, on_reflow: n-impl, reviewer: self}\n",
        encoding="utf-8")
    return str(table_path)


def _init_at(tmp_workspace, node):
    flow_state.init_state(tmp_workspace, FLOW, "g",
                          display_name="G", initial_node=node)


def test_record_gate_review_pass_advances(tmp_workspace, capsys):
    _init_at(tmp_workspace, "n-rev")
    t = _write_gate_table(tmp_workspace)
    rc = cli.main(["record-gate", FLOW, "g", "--gate", "g-rev", "--kind", "review",
                   "--verdict", "PASS", "--request-id", "r1",
                   "--table", t, "--workspace", str(tmp_workspace)])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert out["current_node"] == "n-acc"
    assert out["history_len"] == 1


def test_record_gate_review_fail_reflows_then_escalates(tmp_workspace, capsys):
    _init_at(tmp_workspace, "n-rev")
    t = _write_gate_table(tmp_workspace)
    # FAIL #1,#2 -> reflow 回 n-impl（每次回前要先回到 n-rev）
    for i in (1, 2):
        cli.main(["record-gate", FLOW, "g", "--gate", "g-rev", "--kind", "review",
                  "--verdict", "FAIL", "--request-id", f"r{i}",
                  "--table", t, "--workspace", str(tmp_workspace)])
        cli.main(["advance", FLOW, "g", "n-rev", "--table", t,
                  "--workspace", str(tmp_workspace)])
    capsys.readouterr()
    # FAIL #3 >= max_retries(3) -> escalate blocked，不 advance、不 force-accept
    cli.main(["record-gate", FLOW, "g", "--gate", "g-rev", "--kind", "review",
              "--verdict", "FAIL", "--request-id", "r3",
              "--table", t, "--workspace", str(tmp_workspace)])
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "blocked"
    assert out["current_node"] == "n-rev"  # 没 force 过闸
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd plugins/kdev-core && python3 -m pytest tests/test_cli.py -k record_gate -v`
Expected: FAIL（`invalid choice: 'record-gate'`）

- [ ] **Step 3: 写最小实现**

```python
def cmd_record_gate(args):
    table, gate_specs = _load_table(args.table)
    gr = gate.make_gate_result(
        args.gate, args.kind, node=args.node, verdict=args.verdict,
        request_id=args.request_id, by=args.by, iter=args.iter,
        issues=args.issues or [])
    state = gate.record_gate_persist(
        args.workspace, args.flow, args.slug, gr,
        table=table, gate_specs=gate_specs)
    _print_state(state)
    return 0
```

`build_parser()` 加：

```python
    pg = _common(sub, "record-gate")
    pg.add_argument("--gate", required=True)
    pg.add_argument("--kind", required=True,
                    choices=["review", "decision", "acceptance"])
    pg.add_argument("--verdict", required=True)
    pg.add_argument("--node", default=None)
    pg.add_argument("--request-id", required=True)
    pg.add_argument("--by", default="ai")
    pg.add_argument("--iter", type=int, default=1)
    pg.add_argument("--issues", action="append")
    pg.set_defaults(func=cmd_record_gate)
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd plugins/kdev-core && python3 -m pytest tests/test_cli.py -v`
Expected: PASS（全部）

- [ ] **Step 5: Commit**

```bash
git add plugins/kdev-core/kdev_core/cli.py plugins/kdev-core/tests/test_cli.py
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-core): CLI record-gate 子命令（三类 gate + escalate）"
```

---

## Task 6: CLI 集成 smoke（full-lifecycle + resume + reflow + escalate）

**Files:**
- Test: `plugins/kdev-core/tests/test_cli_smoke.py`

> 纯黑盒，全程只经 CLI `main()`，断言落盘的 flow-state。证明设计稿 §8 的底座证据 1/2/3/4 经 CLI 端到端成立。

- [ ] **Step 1: 写 smoke 测试**

```python
"""CLI 集成 smoke — 全程经 cli.main()，证明 R1/R2/R3 经 CLI 真驱动。

覆盖设计稿 §8：R3 三类各跑通 · FAIL→reflow→重评 PASS · kill→resume · escalate 不 force-accept。
"""
import json
from kdev_core import cli, flow_state

FLOW = "coding-flow"


def _t(tmp):
    p = tmp / "nt.yml"
    p.write_text(
        "flow: coding-flow\n"
        "max_retries: 3\n"
        "terminal_fail: n-fail\n"
        "nodes:\n"
        "  - {id: n0, kind: action, next: [n-route]}\n"
        "  - {id: n-route, kind: gate, gate: g-route, next: [n-impl, n-skip]}\n"
        "  - {id: n-skip, kind: action, next: [n-impl]}\n"
        "  - {id: n-impl, kind: action, next: [n-rev]}\n"
        "  - {id: n-rev, kind: gate, gate: g-rev, next: [n-acc, n-impl]}\n"
        "  - {id: n-acc, kind: gate, gate: g-acc, next: [n-done, n-impl]}\n"
        "  - {id: n-done, kind: terminal, next: []}\n"
        "  - {id: n-fail, kind: terminal, next: []}\n"
        "gate_specs:\n"
        "  g-route: {kind: decision, branches: {go: n-impl, skip: n-skip}, reviewer: self}\n"
        "  g-rev: {kind: review, on_pass: n-acc, on_reflow: n-impl, reviewer: self}\n"
        "  g-acc: {kind: acceptance, on_pass: n-done, on_reflow: n-impl, reviewer: self}\n",
        encoding="utf-8")
    return str(p)


def _run(argv):
    return cli.main(argv)


def test_cli_full_lifecycle_and_resume(tmp_workspace, capsys):
    t = _t(tmp_workspace)
    ws = ["--workspace", str(tmp_workspace)]
    _run(["init", FLOW, "x", "--display-name", "X", "--initial-node", "n0"] + ws)
    _run(["advance", FLOW, "x", "n-route", "--table", t] + ws)
    # decision -> go 分支
    _run(["record-gate", FLOW, "x", "--gate", "g-route", "--kind", "decision",
          "--verdict", "go", "--request-id", "d1", "--table", t] + ws)
    assert flow_state.read_state(tmp_workspace, FLOW, "x")["current_node"] == "n-impl"

    # review FAIL -> reflow 回 n-impl，修，再回 n-rev 重评 PASS
    _run(["advance", FLOW, "x", "n-rev", "--table", t] + ws)
    _run(["record-gate", FLOW, "x", "--gate", "g-rev", "--kind", "review",
          "--verdict", "FAIL", "--request-id", "rv1", "--table", t] + ws)
    assert flow_state.read_state(tmp_workspace, FLOW, "x")["current_node"] == "n-impl"

    # kill→resume：新"会话"从 n-impl 续，不从头
    capsys.readouterr()
    _run(["resume", FLOW, "x"] + ws)
    assert json.loads(capsys.readouterr().out)["current_node"] == "n-impl"

    _run(["advance", FLOW, "x", "n-rev", "--table", t] + ws)
    _run(["record-gate", FLOW, "x", "--gate", "g-rev", "--kind", "review",
          "--verdict", "PASS", "--request-id", "rv2", "--table", t] + ws)
    assert flow_state.read_state(tmp_workspace, FLOW, "x")["current_node"] == "n-acc"

    # acceptance PASS -> terminal
    _run(["record-gate", FLOW, "x", "--gate", "g-acc", "--kind", "acceptance",
          "--verdict", "PASS", "--request-id", "ac1", "--table", t] + ws)
    final = flow_state.read_state(tmp_workspace, FLOW, "x")
    assert final["current_node"] == "n-done"
    # 三类 gate 都进了 history（decision + review*2 + acceptance = 4）
    assert len(final["history"]) == 4
```

- [ ] **Step 2: 跑 smoke 确认通过**

Run: `cd plugins/kdev-core && python3 -m pytest tests/test_cli_smoke.py -v`
Expected: PASS

- [ ] **Step 3: 全量回归**

Run: `cd plugins/kdev-core && python3 -m pytest -q`
Expected: 全绿（原 66 + 新增 CLI 测试）

- [ ] **Step 4: Commit**

```bash
git add plugins/kdev-core/tests/test_cli_smoke.py
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "test(kdev-core): CLI 集成 smoke — full-lifecycle + resume + reflow + escalate"
```

---

## Task 7: coding-flow node-table.yml（16 节点）+ 一致性校验测试

**Files:**
- Create: `plugins/kdev-coding-flow/skills/kdev-coding-flow/orchestration/node-table.yml`
- Create: `plugins/kdev-coding-flow/tests/conftest.py`
- Create: `plugins/kdev-coding-flow/tests/test_orchestration_config.py`

> 节点 = 13 逻辑节点（6·7 合为实现、按 Gate-B 分 6a/6b；9 拆 9a/9b）+ 2 terminal = 16。reviewer 绑定：自评(self) vs 第三方(reviewer-expert，阶段1 `stage1: deferred`)。

- [ ] **Step 1: 写校验测试**（先定 conftest 把引擎放 path）

`plugins/kdev-coding-flow/tests/conftest.py`：

```python
import sys
from pathlib import Path

# 复用 kdev-core 引擎做校验
KDEV_CORE = Path(__file__).resolve().parents[2] / "kdev-core"
sys.path.insert(0, str(KDEV_CORE))
```

`plugins/kdev-coding-flow/tests/test_orchestration_config.py`：

```python
from pathlib import Path

import yaml
from kdev_core import node_machine

NT = (Path(__file__).resolve().parents[1]
      / "skills/kdev-coding-flow/orchestration/node-table.yml")

GATE_KINDS = {"review", "decision", "acceptance"}


def _load():
    data = yaml.safe_load(NT.read_text(encoding="utf-8"))
    return data, node_machine.load_node_table(data)


def test_node_table_loads_and_has_16_nodes():
    data, table = _load()
    assert len(table["nodes"]) == 16
    assert table["terminal_fail"] == "n-fail"


def test_every_gate_node_has_a_gate_spec():
    data, table = _load()
    specs = data["gate_specs"]
    for nid, n in table["nodes"].items():
        if n["kind"] == "gate":
            assert n["gate"], f"gate node {nid} missing 'gate' id"
            assert n["gate"] in specs, f"gate {n['gate']} not in gate_specs"


def test_gate_specs_targets_are_valid_nodes():
    data, table = _load()
    nodes = set(table["nodes"])
    for gid, spec in data["gate_specs"].items():
        assert spec["kind"] in GATE_KINDS
        targets = (list(spec.get("branches", {}).values())
                   + [spec[k] for k in ("on_pass", "on_reflow") if k in spec])
        for tgt in targets:
            assert tgt in nodes, f"{gid} -> unknown node {tgt}"
        # reviewer 绑定必填：self（自评）或 reviewer-expert（第三方）
        assert spec["reviewer"] in {"self", "reviewer-expert"}


def test_third_party_review_gates_are_deferred_in_stage1():
    """第三方评审(reviewer-expert) 阶段1 必标 stage1: deferred。"""
    data, _ = _load()
    for gid, spec in data["gate_specs"].items():
        if spec["reviewer"] == "reviewer-expert":
            assert spec.get("stage1") == "deferred", f"{gid} 第三方评审须标 deferred"
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd plugins/kdev-coding-flow && python3 -m pytest tests/test_orchestration_config.py -v`
Expected: FAIL（node-table.yml 不存在）

- [ ] **Step 3: 写 node-table.yml**（`orchestration/node-table.yml`）

```yaml
# 开发工程师 coding-flow — 13 节点 SOP 的 node-table（L0 默认编排）。
# kind=action|gate|terminal；gate 节点带 gate id 指向 gate_specs。
# reviewer: self=开发工程师自评 / reviewer-expert=评审专家第三方（阶段1 deferred）。
flow: coding-flow
max_retries: 3
terminal_fail: n-fail
nodes:
  - {id: n0-env,             name: 项目背景对齐,        kind: action,   next: [n1-relevance]}
  - {id: n1-relevance,       name: 关联度自检 Gate-A,    kind: gate,     gate: g-relevance, next: [n3-plan, n2-worktree]}
  - {id: n2-worktree,        name: 新建 worktree,        kind: action,   next: [n3-plan]}
  - {id: n3-plan,            name: 写 implementation-plan, kind: action, next: [n4-plan-review]}
  - {id: n4-plan-review,     name: 方案评审,             kind: gate,     gate: g-plan-review, next: [n5-complexity, n3-plan]}
  - {id: n5-complexity,      name: 复杂度判断 Gate-B,     kind: gate,     gate: g-complexity, next: [n6a-impl-inline, n6b-impl-subagent]}
  - {id: n6a-impl-inline,    name: 主控直接实现,         kind: action,   next: [n8-verify]}
  - {id: n6b-impl-subagent,  name: subagent 派单实现(含TDD), kind: action, next: [n8-verify]}
  - {id: n8-verify,          name: 完成验证,             kind: gate,     gate: g-verify, next: [n9a-code-review, n6b-impl-subagent]}
  - {id: n9a-code-review,    name: 代码/质量评审,        kind: gate,     gate: g-code-review, next: [n9b-e2e, n6b-impl-subagent]}
  - {id: n9b-e2e,            name: Per-Increment E2E,    kind: gate,     gate: g-e2e, next: [n10-sec, n6b-impl-subagent]}
  - {id: n10-sec,            name: 安全评审,             kind: gate,     gate: g-sec-review, next: [n11-merge, n6b-impl-subagent]}
  - {id: n11-merge,          name: 合并主分支,           kind: action,   next: [n12-deploy]}
  - {id: n12-deploy,         name: 部署+金丝雀验收,       kind: gate,     gate: g-deploy, next: [n13-done, n6b-impl-subagent]}
  - {id: n13-done,           name: 产出清点+提炼,         kind: terminal, next: []}
  - {id: n-fail,             name: 升级人工(escalate 落点), kind: terminal, next: []}

gate_specs:
  g-relevance:   {kind: decision, branches: {high: n3-plan, low: n2-worktree}, reviewer: self}
  g-plan-review: {kind: review, on_pass: n5-complexity, on_reflow: n3-plan, reviewer: reviewer-expert, stage1: deferred}
  g-complexity:  {kind: decision, branches: {simple: n6a-impl-inline, complex: n6b-impl-subagent}, reviewer: self}
  g-verify:      {kind: review, on_pass: n9a-code-review, on_reflow: n6b-impl-subagent, reviewer: self}
  g-code-review: {kind: review, on_pass: n9b-e2e, on_reflow: n6b-impl-subagent, reviewer: reviewer-expert, stage1: deferred}
  g-e2e:         {kind: acceptance, on_pass: n10-sec, on_reflow: n6b-impl-subagent, reviewer: self}
  g-sec-review:  {kind: review, on_pass: n11-merge, on_reflow: n6b-impl-subagent, reviewer: reviewer-expert, stage1: deferred}
  g-deploy:      {kind: acceptance, on_pass: n13-done, on_reflow: n6b-impl-subagent, reviewer: self}
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd plugins/kdev-coding-flow && python3 -m pytest tests/test_orchestration_config.py -v`
Expected: PASS（4 passed）

- [ ] **Step 5: Commit**

```bash
git add plugins/kdev-coding-flow/skills/kdev-coding-flow/orchestration/node-table.yml plugins/kdev-coding-flow/tests/conftest.py plugins/kdev-coding-flow/tests/test_orchestration_config.py
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-coding-flow): node-table.yml 13节点 + gate_specs(reviewer绑定 + node9拆9a/9b)"
```

---

## Task 8: 7 个轻量 persona Agent + 结构校验

**Files:**
- Create: `plugins/kdev-coding-flow/skills/kdev-coding-flow/personas/开发工程师-编排.md`
- Create: 其余 6 个 persona（环境准备 / 实施计划 / 前端实现 / E2E视觉验收 / 部署上线 / 安全扫描）
- Create: `plugins/kdev-coding-flow/tests/test_personas.py`

> 轻量 persona 结构（4 段必含）：`## Identity` / `## Principles` / `## Critical Actions` / `## Capabilities`。省 BMAD 的 First Breath / 记忆形态 / Communication Style。

- [ ] **Step 1: 写结构校验测试**（`tests/test_personas.py`）

```python
from pathlib import Path

PERSONA_DIR = (Path(__file__).resolve().parents[1]
               / "skills/kdev-coding-flow/personas")
REQUIRED = ["## Identity", "## Principles", "## Critical Actions", "## Capabilities"]
EXPECTED = ["开发工程师-编排", "环境准备", "实施计划",
            "前端实现", "E2E视觉验收", "部署上线", "安全扫描"]


def test_all_7_personas_exist():
    names = {p.stem for p in PERSONA_DIR.glob("*.md")}
    for e in EXPECTED:
        assert e in names, f"缺 persona: {e}"


def test_each_persona_has_required_sections():
    for p in PERSONA_DIR.glob("*.md"):
        text = p.read_text(encoding="utf-8")
        for sec in REQUIRED:
            assert sec in text, f"{p.name} 缺段落 {sec}"


def test_orchestrator_critical_action_mentions_cli():
    text = (PERSONA_DIR / "开发工程师-编排.md").read_text(encoding="utf-8")
    # 编排纪律：每过节点/gate 必调 CLI（补 CLI 靠自觉短板）
    assert "kdev_core" in text and "record-gate" in text
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd plugins/kdev-coding-flow && python3 -m pytest tests/test_personas.py -v`
Expected: FAIL（personas/ 不存在）

- [ ] **Step 3: 写 7 个 persona**

`开发工程师-编排.md`（**完整范本**，其余 6 个照此结构 + 设计稿 §4 各自职责写）：

```markdown
# 开发工程师-编排

## Identity
开发工程师的编排能力。读 coding-flow 的 node-table，用 kdev-core CLI 驱动 R1/R2/R3 引擎走 13 节点 SOP，在工作节点内嵌派自家业务能力 Agent，在 gate 节点收结构化判定。

## Principles
- 守 Q-008「执行留 flow」：编排决定何时推进 + 派谁，引擎只记账。
- 守"自评 vs 第三方"：自评 gate 自己判；第三方评审(reviewer-expert) 阶段1 deferred（记 PASS 并标 by=deferred:阶段3-评审专家），不冒充第三方。
- L2 协同：gate 默认停靠等主控确认；auto_mode=true 时自决续跑、失败 BLOCKED 不死循环。
- 业务能力只对自家编排（硬规5），不外联其他员工。

## Critical Actions
- 启动：`python -m kdev_core resume <flow> <slug>` 探断点；无则 `init`。
- **每过一个节点/gate，必须调 CLI 落账**：动作节点完成 → `python -m kdev_core advance <flow> <slug> <to_node> --table <node-table.yml> --reason ...`；gate 判完 → `python -m kdev_core record-gate <flow> <slug> --gate g-xxx --kind ... --verdict ... --request-id ... --table <node-table.yml>`。
- 终点：`mark_inactive`（completed）。BLOCKED → 出报告升主控。

## Capabilities
| 节点 | 派哪个业务 Agent（subagent_type）| 干什么 |
|---|---|---|
| n0-env | 环境准备 | clone/栈对齐/rules.md |
| n3-plan | 实施计划 | PLAN.md |
| n6a/n6b | 前端实现 | 改 src（视觉改造）|
| n8/n9b/n12 | E2E视觉验收 | build+视觉diff+冒烟 |
| n10-sec | 安全扫描 | 轻量 security.md |
| n11-merge | 部署上线 | 合并+起环境 |
```

其余 6 个 persona 各含 4 段：`## Identity`（一句话角色，照设计稿 §4 表的"角色/产出"）、`## Principles`（该能力红线，如前端实现"禁裸 hex/8px 网格/字体白名单/禁'登陆'，对照原型图"）、`## Critical Actions`（产出物 + 自验，如 E2E视觉验收"playwright 双分辨率截图 vs login.png + 登录金丝雀冒烟"）、`## Capabilities`（内部会调的 skill，照设计稿 §2.1 表，如 实施计划 → writing-plans/plan-eng-review）。运行时模型暂全 Opus（设计稿 §4，L1 flow-config 可配）。

- [ ] **Step 4: 跑测试确认通过**

Run: `cd plugins/kdev-coding-flow && python3 -m pytest tests/test_personas.py -v`
Expected: PASS（3 passed）

- [ ] **Step 5: Commit**

```bash
git add plugins/kdev-coding-flow/skills/kdev-coding-flow/personas/ plugins/kdev-coding-flow/tests/test_personas.py
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-coding-flow): 7 轻量 persona Agent（1 编排 + 6 业务）+ 结构校验"
```

---

## Task 9: SKILL.md 加「接 kdev-core 底座入口」节

**Files:**
- Modify: `plugins/kdev-coding-flow/skills/kdev-coding-flow/SKILL.md`
- Test: `plugins/kdev-coding-flow/tests/test_personas.py`（追加一个 SKILL 段落存在性检查，复用该测试文件）

> 不重写正文方法论，只在末尾加一节，把"隐式编排"接到 kdev-core 引擎。

- [ ] **Step 1: 写存在性检查**（追加到 `tests/test_personas.py`）

```python
SKILL = (Path(__file__).resolve().parents[1]
         / "skills/kdev-coding-flow/SKILL.md")


def test_skill_has_kdev_core_entry_section():
    text = SKILL.read_text(encoding="utf-8")
    assert "接 kdev-core 底座入口" in text
    assert "orchestration/node-table.yml" in text
    assert "python -m kdev_core" in text
    assert "personas/" in text
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd plugins/kdev-coding-flow && python3 -m pytest tests/test_personas.py::test_skill_has_kdev_core_entry_section -v`
Expected: FAIL

- [ ] **Step 3: 在 SKILL.md 末尾加节**（追加到文件最后）

```markdown
## 接 kdev-core 底座入口（v2 编排）

本 SOP 的 13 节点编排可由 **kdev-core 引擎**显式驱动（替代纯 prose 编排），让状态可持久化、可 resume、gate 结构化。

- **编排者**：`personas/开发工程师-编排.md`（subagent_type=开发工程师-编排），读 `orchestration/node-table.yml` 驱动。
- **引擎调用**（薄 CLI，harness-中立）：
  - `python -m kdev_core init coding-flow <slug> --display-name ... [--auto-mode] --initial-node n0-env`
  - 动作节点完成 → `python -m kdev_core advance coding-flow <slug> <to_node> --table orchestration/node-table.yml --reason ...`
  - gate 判完 → `python -m kdev_core record-gate coding-flow <slug> --gate g-xxx --kind review|decision|acceptance --verdict ... --request-id ... --table orchestration/node-table.yml`
  - 断点续跑 → `python -m kdev_core resume coding-flow <slug>`
- **业务能力 Agent**：`personas/{环境准备,实施计划,前端实现,E2E视觉验收,部署上线,安全扫描}.md`，由编排在对应节点内嵌派单。
- **gate reviewer 绑定**：`self`=开发工程师自评（节点 8/9b/12）；`reviewer-expert`=评审专家第三方（节点 4/9a/10），**阶段1 `stage1: deferred`**（编排记 PASS 并标 `--by deferred:阶段3-评审专家`，不冒充第三方）。
- **Auto Mode**：node-table 驱动与 `auto_mode` 正交——auto_mode=true 时 gate 自决续跑、不停等人；false 时 gate 停靠等主控确认（L2）。
```

- [ ] **Step 4: 跑测试 + 全量回归**

Run: `cd plugins/kdev-coding-flow && python3 -m pytest -q` 然后 `cd ../kdev-core && python3 -m pytest -q`
Expected: 两边全绿

- [ ] **Step 5: Commit**

```bash
git add plugins/kdev-coding-flow/skills/kdev-coding-flow/SKILL.md plugins/kdev-coding-flow/tests/test_personas.py
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-coding-flow): SKILL 加「接 kdev-core 底座入口」节"
```

---

## Task 10: 回写 roadmap §1.5（P5 框架侧 done）

**Files:**
- Modify: `docs/framework/01-design/2026-06-06-01-数字员工集群-起步roadmap-Q004细化-v0.1.md`

- [ ] **Step 1: 更新 §1.5 阶段1 行**

把阶段1 行从 `⏳ next` 改为标注"框架侧 done（CLI + node-table + persona + SKILL 接口）/ Pass1 dogfood 实跑待启"，附本计划链接 + 测试数 + 关键 commit 范围。

- [ ] **Step 2: Commit**

```bash
git add "docs/framework/01-design/2026-06-06-01-数字员工集群-起步roadmap-Q004细化-v0.1.md"
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "docs(framework): roadmap §1.5 回写 — 阶段1 框架侧 done（P5 coding-flow接底座）"
```

---

## Self-Review（计划自查）

- **Spec 覆盖**：①CLI(init/show/resume/advance/record-gate)=Task 1-5 ✓ ②node-table+gate_specs(reviewer+node9拆)=Task 7 ✓ ③7 persona=Task 8 ✓ ④SKILL 接口节=Task 9 ✓ ⑤集成 smoke=Task 6 ✓。Pass1 dogfood 实跑明确不在本计划（设计稿 §11 后续阶段）✓。
- **Placeholder 扫描**：无 TBD/TODO；persona 给了完整范本 + 其余按设计稿 §2.1/§4 表填（明确指向已有表，非占位）。
- **类型/签名一致**：CLI 调用严格对齐 `flow_state.init_state/read_state/write_state/mark_inactive/resume_state`、`node_machine.advance_persist/load_node_table`、`gate.make_gate_result/record_gate_persist` 的现有签名（已核源码）。node id 跨 Task 6 smoke(fixture) 与 Task 7(真表) 各自独立、Task 3 用真表 id `n6b-impl-subagent` 与 Task 7 一致 ✓。
- **依赖**：PyYAML 6.0.1 已确认可用；conftest 路径注入沿用现有模式。
