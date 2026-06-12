# P-A 需求架构师(req-architect)接 kdev-core 底座 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 落地第二个数字员工「需求架构师 req-architect」——复刻 dev-engineer 的当前 canonical 打法（通用 kdev-flow-driver + per-员工 node-table + 瘦 persona agent），并把 kdev-design-flow 的自带 flow_state（golden seed）迁到 kdev-core 引擎，保 SOP 行为不破。

**Architecture:**
- 编排走**通用 `kdev-flow-driver` skill**（顶层主控执行循环，CC 限制子 agent 不再开子 agent），按 `staff.yml` 路由 `req-architect`，读 `orchestration/req-architect.node-table.yml` 驱动 kdev-core CLI 走 `IR→SR→AR→原型→方案` SOP。
- req-architect = **5 业务能力 agent + 1 编排 agent**（瘦 persona，真 CC frontmatter）；`req-architect-orchestrator` 是**编排知识/fallback 文档**，不写成自跑执行器。
- kdev-core 引擎**零改**——它已是 design-flow flow_state 的泛化超集（`review_mode` ai/both/human、review gate escalate→blocked、`stories[]`、`handoff_dir` 均已具备）。迁移 = 用 node-table 表达 SOP + 把 design-flow SKILL 回归方法论 + 删除其自带 `lib/flow_state.py`。
- 运行时存储落 `.kdev/features/<slug>/`（feature-first，P-Core-FF 已建）；产物落 `handoffs/req-architect/`（运行时）+ `.kdev/memory/staff/req-architect/`（记忆 scope，P-C1 已建）。

**Tech Stack:** Python (pytest) + YAML node-table + Markdown agent/skill 文档。kdev-core CLI（`python3 -m kdev_core`）。

---

## 关键设计决策（已从「保 SOP 行为不破」约束推导）

1. **3 评审 gate，全 `reviewer: self`**（不 deferred）。design-flow 的 SOP 行为是 `--review=ai` 默认 = Claude 按 `review-gate-prompt.md` 判据真自评（可 PASS/FAIL/3 次重试/升人）。若做成 dev-engineer 的 `reviewer-expert + deferred`（自动 PASS、不跑判据），**SOP 行为就破了**（evals 兜的就是这个）。阶段1 无「评审专家」员工，故全 self；待评审专家建成后由 L1 config 翻成 reviewer-expert。`config.review_mode`（ai/both/human）控制档位，kdev-core 已原生承载。
2. **3 gate 位置复刻 design-flow**：Gate1=SR 评审、Gate2=AR+原型共评（design-flow「Stage2+Stage3 共用 Gate2」）、Gate3=方案/设计闸。概念模型 doc 的更细 gate（R1.5 方向评审/R2.5 迭代拆分评审/R4.1 可访问性）属未来 L1 可配，本步**不加**（保 design-flow 3 闸 SOP，evals 兜）。
3. **删除 `kdev-design-flow/lib/flow_state.py` + `tests/test_flow_state.py`**（被 kdev-core 引擎取代——kdev-core `flow_state.py` 已覆盖原子写/损坏检测/拒重写/review_mode 校验等同等行为，且有更全测试）。**保留 `lib/slug.py` + `tests/test_slug.py`**（kdev-core 无 slug 模块，init 的 slug 仍调用方直传，slugify 仍是 design-flow 职责）。
4. **kdev-core 不动**（R1/R2/R3 + CLI 已是超集）。只消费，不改。
5. **不碰 `marketplace.json`**（它只存 name+source 无 version）——避免与并行 kdev-hud worktree 撞车；版本只 bump 各 `plugin.json`。

## req-architect 能力 → agent → 节点 → design-flow 阶段 映射

| 能力（概念模型 doc）| agent canonical id | 节点 | 产出 | 复刻 design-flow | 调用的 skill |
|---|---|---|---|---|---|
| 编排 | `req-architect-orchestrator` | (派单/判 gate/聚合) | 阶段聚合报告 | 全程 | — |
| 需求澄清 | `req-architect-clarify` | n0-clarify | `ir.md` | （design-flow 无显式 IR，新增）| superpowers:brainstorming（澄清）|
| 需求计划 | `req-architect-spec` | n1-spec | `sr.md` | Stage1 SR | 内置 stage1-sr-prompt/template |
| 需求拆解 | `req-architect-decompose` | n3-decompose | 迭代计划 + 用户故事列表 | Stage2 AR | spec-kit:specify |
| 原型设计 | `req-architect-prototype` | n4-prototype | `prototype/` | Stage3 | frontend-design:frontend-design |
| 方案设计 | `req-architect-design` | n6-design | `design.md` | Stage4 | spec-kit:plan |

---

## File Structure

**新建：**
- `plugins/kdev-team/orchestration/req-architect.node-table.yml` — req-architect 的 design-flow SOP node-table
- `plugins/kdev-team/agents/req-architect-orchestrator.md` — 编排能力（fallback 文档）
- `plugins/kdev-team/agents/req-architect-clarify.md` — 需求澄清
- `plugins/kdev-team/agents/req-architect-spec.md` — 需求计划 SR
- `plugins/kdev-team/agents/req-architect-decompose.md` — 需求拆解 AR
- `plugins/kdev-team/agents/req-architect-prototype.md` — 原型设计
- `plugins/kdev-team/agents/req-architect-design.md` — 方案设计
- `plugins/kdev-team/tests/test_req_architect_orchestration.py` — node-table 校验测试
- `plugins/kdev-design-flow/tests/test_skill_base_migration.py` — design-flow 接底座迁移测试

**修改：**
- `plugins/kdev-team/tests/test_agents.py` — 加 `REQ_AGENTS` + 并行断言
- `plugins/kdev-team/tests/test_staff.py` — 加 `test_req_architect_entry`
- `plugins/kdev-team/staff.yml` — 追加 req-architect 词条
- `plugins/kdev-team/skills/kdev-flow-driver/references/node-agent-routing.md` — 追加 req-architect 路由段
- `plugins/kdev-team/skills/kdev-flow-driver/references/gate-decision-logic.md` — 追加 req-architect gate 判据段
- `plugins/kdev-team/.claude-plugin/plugin.json` — version 0.2.0→0.3.0
- `plugins/kdev-team/CHANGELOG.md` — 0.3.0 条目
- `plugins/kdev-design-flow/skills/kdev-design-flow/SKILL.md` — 回归方法论参考（去自跑状态机）
- `plugins/kdev-design-flow/.claude-plugin/plugin.json` — version 0.2.0→0.3.0
- `plugins/kdev-design-flow/CHANGELOG.md` — 0.3.0 条目
- `docs/framework/01-design/2026-06-06-01-数字员工整体设计路线图roadmap-v1.0.md` — §1.5.2 P-A 状态回写

**删除：**
- `plugins/kdev-design-flow/lib/flow_state.py`
- `plugins/kdev-design-flow/tests/test_flow_state.py`

**测试运行方式**（各 plugin 自带 `tests` 包，须各自从 plugin 根跑，不能一锅端——`tests.conftest` 包名冲突）：
```bash
cd plugins/kdev-team        && python3 -m pytest tests -q
cd plugins/kdev-design-flow && python3 -m pytest tests -q
cd plugins/kdev-core        && python3 -m pytest tests -q   # 回归基线，不应变
```
基线：core 126 / design-flow 33 / team 12 = 171 绿。

---

## Task 1: req-architect node-table + 校验测试

**Files:**
- Create: `plugins/kdev-team/orchestration/req-architect.node-table.yml`
- Test: `plugins/kdev-team/tests/test_req_architect_orchestration.py`

- [ ] **Step 1: 写失败测试** `plugins/kdev-team/tests/test_req_architect_orchestration.py`

```python
from pathlib import Path
import yaml
from kdev_core import node_machine

NT = Path(__file__).resolve().parents[1] / "orchestration/req-architect.node-table.yml"
GATE_KINDS = {"review", "decision", "acceptance"}


def _load():
    data = yaml.safe_load(NT.read_text(encoding="utf-8"))
    return data, node_machine.load_node_table(data)


def test_node_table_loads_and_has_11_nodes():
    data, table = _load()
    # 6 action(n0/n1/n3/n4/n6/n8) + 3 gate(n2/n5/n7) + 2 terminal(n9-done/n-fail)
    assert len(table["nodes"]) == 11
    assert table["flow"] == "design-flow"
    assert table["terminal_fail"] == "n-fail"


def test_sop_chain_ir_sr_ar_proto_design():
    """IR→SR→(SR评审)→AR→原型→(AR+原型评审)→方案→(方案评审)→聚合→done。"""
    data, table = _load()
    adj = table["adjacency"]
    assert adj["n0-clarify"] == ["n1-spec"]
    assert adj["n1-spec"] == ["n2-sr-review"]
    assert adj["n3-decompose"] == ["n4-prototype"]
    assert adj["n4-prototype"] == ["n5-ar-proto-review"]
    assert adj["n6-design"] == ["n7-design-review"]
    assert adj["n8-merge"] == ["n9-done"]


def test_three_review_gates_all_self_reviewer():
    """复刻 design-flow 3 闸门，全 reviewer=self（保 SOP：真自评，非 deferred）。"""
    data, table = _load()
    specs = data["gate_specs"]
    assert set(specs) == {"g-sr-review", "g-ar-proto-review", "g-design-review"}
    for gid, spec in specs.items():
        assert spec["kind"] == "review", f"{gid} 应是 review gate"
        assert spec["reviewer"] == "self", f"{gid} 阶段1 应 self 自评（非 deferred）"


def test_gate_pass_reflow_targets():
    data, table = _load()
    specs = data["gate_specs"]
    assert specs["g-sr-review"]["on_pass"] == "n3-decompose"
    assert specs["g-sr-review"]["on_reflow"] == "n1-spec"
    assert specs["g-ar-proto-review"]["on_pass"] == "n6-design"
    assert specs["g-ar-proto-review"]["on_reflow"] == "n4-prototype"
    assert specs["g-design-review"]["on_pass"] == "n8-merge"
    assert specs["g-design-review"]["on_reflow"] == "n6-design"


def test_every_gate_node_has_a_gate_spec():
    data, table = _load()
    specs = data["gate_specs"]
    for nid, n in table["nodes"].items():
        if n["kind"] == "gate":
            assert n["gate"] in specs, f"gate {n['gate']} not in gate_specs"


def test_gate_specs_targets_valid_and_reviewer_bound():
    data, table = _load()
    nodes = set(table["nodes"])
    for gid, spec in data["gate_specs"].items():
        assert spec["kind"] in GATE_KINDS
        targets = (list(spec.get("branches", {}).values())
                   + [spec[k] for k in ("on_pass", "on_reflow") if k in spec])
        for tgt in targets:
            assert tgt in nodes, f"{gid} -> unknown node {tgt}"
        assert spec["reviewer"] in {"self", "reviewer-expert"}
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd plugins/kdev-team && python3 -m pytest tests/test_req_architect_orchestration.py -q`
Expected: FAIL（FileNotFoundError / node-table 不存在）

- [ ] **Step 3: 写 node-table** `plugins/kdev-team/orchestration/req-architect.node-table.yml`

```yaml
# 需求架构师 req-architect 的 design-flow SOP node-table（L0 默认编排）。
# 复用通用 kdev-flow-driver skill + kdev-core 引擎（零改）。员工 canonical id=req-architect。
# kind=action|gate|terminal；gate 节点带 gate id 指向 gate_specs。
#
# reviewer: self=需求架构师自评（按 design-flow review-gate-prompt.md 判据自评，
#   config.review_mode 控制 ai/both/human 三档）。阶段1 无第三方「评审专家」员工，故 3 闸
#   全 self（真自评，非 deferred）；待评审专家建成后由 L1 config 翻成 reviewer-expert。
#
# 3 评审 gate 复刻 kdev-design-flow 的 3 闸门（保 SOP 行为不破，evals 兜）：
#   g-sr-review       = design-flow Gate1（SR 需求评审）
#   g-ar-proto-review = design-flow Gate2（AR+原型共评；Stage2+Stage3 共用一闸）
#   g-design-review   = design-flow Gate3（方案/设计闸）
# 评审 FAIL 有界回流：gate_iters 达 max_retries(3) → status=blocked 升人（复刻 design-flow
#   「3 次仍 FAIL → abort 升人」；引擎用 blocked 表达 escalate，不强过、不冒充第三方）。
# 产物：运行时落 .kdev/features/<slug>/handoffs/req-architect/；记忆 scope .kdev/memory/staff/req-architect/。
flow: design-flow
max_retries: 3
terminal_fail: n-fail
nodes:
  - {id: n0-clarify,         name: 需求澄清 IR,                kind: action,   next: [n1-spec]}
  - {id: n1-spec,            name: 需求计划 SR,                kind: action,   next: [n2-sr-review]}
  - {id: n2-sr-review,       name: SR 需求评审,                kind: gate,     gate: g-sr-review, next: [n3-decompose, n1-spec]}
  - {id: n3-decompose,       name: 需求拆解 AR(迭代+用户故事),  kind: action,   next: [n4-prototype]}
  - {id: n4-prototype,       name: 高保真原型,                 kind: action,   next: [n5-ar-proto-review]}
  - {id: n5-ar-proto-review, name: AR+原型 评审,               kind: gate,     gate: g-ar-proto-review, next: [n6-design, n4-prototype]}
  - {id: n6-design,          name: 方案设计,                   kind: action,   next: [n7-design-review]}
  - {id: n7-design-review,   name: 方案评审(设计闸),            kind: gate,     gate: g-design-review, next: [n8-merge, n6-design]}
  - {id: n8-merge,           name: 产物聚合+合并交付,           kind: action,   next: [n9-done]}
  - {id: n9-done,            name: 交付清点+阶段聚合报告,        kind: terminal, next: []}
  - {id: n-fail,             name: reflow 溢出终止(R2 有界回流 sink；R3 评审 gate escalate 走 status=blocked 留原地不到此), kind: terminal, next: []}

gate_specs:
  g-sr-review:       {kind: review, on_pass: n3-decompose, on_reflow: n1-spec,      reviewer: self}
  g-ar-proto-review: {kind: review, on_pass: n6-design,    on_reflow: n4-prototype, reviewer: self}
  g-design-review:   {kind: review, on_pass: n8-merge,     on_reflow: n6-design,    reviewer: self}
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd plugins/kdev-team && python3 -m pytest tests/test_req_architect_orchestration.py -q`
Expected: PASS（6 passed）

- [ ] **Step 5: Commit**

```bash
git -c user.name=ly-AI -c user.email=ly1989abc@126.com add \
  plugins/kdev-team/orchestration/req-architect.node-table.yml \
  plugins/kdev-team/tests/test_req_architect_orchestration.py
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-team): req-architect.node-table.yml — design-flow SOP 接 kdev-core (IR→SR→AR→原型→方案 + 3 self 评审 gate)"
```

---

## Task 2: 6 个 req-architect agent + test_agents 扩展

**Files:**
- Modify: `plugins/kdev-team/tests/test_agents.py`
- Create: `plugins/kdev-team/agents/req-architect-orchestrator.md` + 5 业务 agent

- [ ] **Step 1: 改 `test_agents.py` 加 REQ_AGENTS 断言（失败测试）**

在 `DEV_AGENTS` 定义之后追加：

```python
REQ_AGENTS = [
    "req-architect-orchestrator", "req-architect-clarify", "req-architect-spec",
    "req-architect-decompose", "req-architect-prototype", "req-architect-design",
]


def test_all_6_req_agents_exist():
    names = {p.stem for p in AGENTS.glob("req-architect-*.md")}
    for a in REQ_AGENTS:
        assert a in names, f"缺 agent: {a}"


def test_each_req_agent_has_frontmatter_and_sections():
    for a in REQ_AGENTS:
        text = (AGENTS / f"{a}.md").read_text(encoding="utf-8")
        fm = _frontmatter(text)
        assert fm, f"{a} 缺 YAML frontmatter"
        assert f"name: {a}" in fm, f"{a} frontmatter name 不匹配文件名"
        assert "description:" in fm and "model:" in fm, f"{a} frontmatter 缺 description/model"
        for sec in SECTIONS:
            assert sec in text, f"{a} 缺段落 {sec}"


def test_req_orchestrator_drives_via_cli_and_node_table():
    text = (AGENTS / "req-architect-orchestrator.md").read_text(encoding="utf-8")
    assert "node-table" in text
    assert "kdev_core" in text and "record-gate" in text
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd plugins/kdev-team && python3 -m pytest tests/test_agents.py -q`
Expected: FAIL（req-architect-* 文件不存在）

- [ ] **Step 3: 写 6 个 agent 文件**

`plugins/kdev-team/agents/req-architect-orchestrator.md`：

```markdown
---
name: req-architect-orchestrator
description: 需求架构师·编排能力 — 读 req-architect.node-table.yml 驱动 kdev-core 引擎走需求设计 SOP（IR→SR→AR→原型→方案 5 业务阶段 + 3 评审 gate + 聚合收尾），按编排在节点派业务 agent、gate 收结构化判定。Use when 主控派需求架构师端到端跑设计 flow。
model: opus
---
# 需求架构师-编排

## Identity
需求架构师的编排能力。读 design-flow 的 node-table，用 kdev-core CLI 驱动 R1/R2/R3 引擎走需求设计 SOP（IR→SR→AR→原型→方案 5 业务阶段 + 3 评审 gate + 聚合收尾），在工作节点派自家业务能力 Agent，在 gate 节点收结构化判定。**本文档是编排知识/fallback 参考——真正的运行时编排由通用 `kdev-flow-driver` skill（顶层主控执行循环）承载，不在此自跑。**

## Principles
- 守 Q-008「执行留 flow」：编排决定何时推进 + 派谁，引擎只记账。
- 守「自评 vs 第三方」：本员工 3 评审 gate 阶段1 全 `reviewer=self`（按 design-flow review-gate-prompt.md 判据自评，`config.review_mode` 控 ai/both/human）。无「评审专家」员工时不冒充第三方；待其建成由 L1 config 翻 reviewer-expert。
- 评审 FAIL 有界：gate_iters 达 max_retries(3) → status=blocked 升人（复刻 design-flow「3 次 FAIL→abort 升人」；引擎用 blocked 表达，不强过）。
- 聚合职责：每阶段产 阶段聚合报告；终点 n8-merge 按 design-flow output-merge-rules.md 合并交付。
- 业务能力只对自家编排（硬规5），不外联其他员工。

## Critical Actions

flow=`design-flow`，table=`orchestration/req-architect.node-table.yml`。每过一个节点/gate **必须**调 CLI 落账（薄 CLI，harness-中立）：

- **启动**：先 `python3 -m kdev_core resume design-flow <slug>` 探断点；无则 `python3 -m kdev_core init design-flow <slug> --display-name ... --review-mode ai [--auto-mode] --initial-node n0-clarify`。
- **动作节点完成** → `python3 -m kdev_core advance design-flow <slug> <to_node> --table orchestration/req-architect.node-table.yml --reason ...`。
- **gate 判完** → `python3 -m kdev_core record-gate design-flow <slug> --gate g-xxx --kind review --verdict PASS|FAIL --request-id <node> --table orchestration/req-architect.node-table.yml`。
- **用户故事入账**：n3-decompose 出的用户故事 → `python3 -m kdev_core add-story design-flow <slug> --id US-N --title ...`（填 stories[]，HUD 完成度分母）。
- **终结（terminal 节点）** → `python3 -m kdev_core complete design-flow <slug>`。BLOCKED → 出报告升主控。
- **Auto Mode 正交**：node-table 驱动与 `auto_mode` 正交——true 时 gate 自决续跑、不停等人；false 时 gate 停靠等主控确认（review_mode both/human 同理停等）。

## Capabilities
| 节点 | 派哪个业务 Agent（subagent_type）| 干什么 |
|---|---|---|
| n0-clarify | `req-architect-clarify`（需求澄清）| 澄清原始需求 → ir.md |
| n1-spec | `req-architect-spec`（需求计划）| SR 需求规格 → sr.md |
| n3-decompose | `req-architect-decompose`（需求拆解）| 迭代拆分 + 用户故事 → ar |
| n4-prototype | `req-architect-prototype`（原型设计）| 高保真原型 → prototype/ |
| n6-design | `req-architect-design`（方案设计）| 技术方案 → design.md |
| n2/n5/n7 | 自判（不派 agent）| 评审 gate：按 design-flow 判据自评 PASS/FAIL |
| n8-merge | 自做（编排聚合）| 阶段聚合报告 + 合并交付（output-merge-rules.md）|
```

`plugins/kdev-team/agents/req-architect-clarify.md`：

```markdown
---
name: req-architect-clarify
description: 需求架构师·需求澄清 — IR：澄清原始需求的意图/边界/约束/验收方向，产 ir.md。Use when design-flow 节点0 需求澄清。
model: opus
---
# 需求澄清

## Identity
需求架构师的需求澄清能力（节点 n0-clarify）。把原始（常含糊）需求澄清成结构化 IR（意图/边界/约束/已知未知/验收方向），产 `ir.md` 作为后续 SR 需求计划的输入。

## Principles
- 澄清不臆造：拿不准的需求点标「待澄清」，不脑补；该问用户的列成问题清单。
- 先发散后收敛：意图/隐含约束/非目标都过一遍，再收敛成 IR。
- 只对自家编排负责（硬规5），不外联其他员工。

## Critical Actions
- 产出 `ir.md`：原始需求复述 + 意图 + 边界（in/out scope）+ 约束 + 待澄清问题 + 验收方向草案。
- 自验：IR 覆盖原始需求每条、无脑补、待澄清项显式列出。
- 产物落 `.kdev/features/<slug>/handoffs/req-architect/ir.md`（运行时）。
- 完成 → 回编排，由编排 advance 进 n1-spec。

## Capabilities
- `superpowers:brainstorming` — 澄清意图/边界/隐含约束（按需）。
运行时模型暂 Opus（L1 flow-config 可配）。
```

`plugins/kdev-team/agents/req-architect-spec.md`：

```markdown
---
name: req-architect-spec
description: 需求架构师·需求计划 — SR：把 IR 写成需求规格文档，喂 SR 评审 gate。Use when design-flow 节点1 需求计划。
model: opus
---
# 需求计划

## Identity
需求架构师的需求计划能力（节点 n1-spec）。吃 IR，按 kdev-design-flow 的 Stage1 方法论（references/stage1-sr-prompt.md + stage1-sr-template.md）产出 SR 需求规格 `sr.md`，供 SR 评审 gate 收口。

## Principles
- SR 落到可评审粒度：每条需求有意图 + 验收信号，避免「TBD/TODO」占位。
- 显式列「不做清单」：边界外的事写清，防 scope 蔓延。
- 只对自家编排负责（硬规5）。

## Critical Actions
- 读 design-flow `references/stage1-sr-prompt.md` + `stage1-sr-template.md`，填占位符产出 SR。
- 产出 `sr.md`：需求项 + 优先级 + 验收标准 + 显式不做清单。
- 自验：SR 覆盖 IR 每条、无占位、不做清单完整。
- 产物落 `.kdev/features/<slug>/handoffs/req-architect/sr.md`。
- 完成 → 回编排，进 n2-sr-review（SR 评审，self 自评）。

## Capabilities
- 参 kdev-design-flow `references/stage1-sr-prompt.md` / `stage1-sr-template.md`（方法论模板）。
运行时模型暂 Opus（L1 flow-config 可配）。
```

`plugins/kdev-team/agents/req-architect-decompose.md`：

```markdown
---
name: req-architect-decompose
description: 需求架构师·需求拆解 — AR：迭代拆分（批次/里程碑）+ 用户故事列表（可独立验收），调 spec-kit:specify。Use when design-flow 节点3 需求拆解。
model: opus
---
# 需求拆解

## Identity
需求架构师的需求拆解能力（节点 n3-decompose）。吃通过 SR 评审的 sr.md，按 kdev-design-flow Stage2 方法论调 `spec-kit:specify`，产出迭代计划 + 用户故事列表（AR）。用户故事由编排 `add-story` 入 kdev-core stories[]（HUD 完成度分母）。

## Principles
- **用户故事 = 能独立验收的纵向切片**，每条带验收标准，覆盖每个 SR。
- 迭代拆分按批次/里程碑切，不照抄 SR 的实现工序当切片。
- 只对自家编排负责（硬规5）。

## Critical Actions
- 调 `spec-kit:specify` 把 SR 细化成用户故事（每条带 acceptance criteria）。
- 产出迭代计划 + 用户故事列表，落 `.kdev/features/<slug>/handoffs/req-architect/`（如 ar.md / 用户故事列表）。
- 自验：用户故事覆盖每个 SR、每条可独立验收、不重复 SR 的不做清单。
- 完成 → 回编排：编排 `add-story` 入账 + advance 进 n4-prototype（与原型共用 n5 评审 gate）。

## Capabilities
- `spec-kit:specify` — SR → AR 用户故事细化。
运行时模型暂 Opus（L1 flow-config 可配）。
```

`plugins/kdev-team/agents/req-architect-prototype.md`：

```markdown
---
name: req-architect-prototype
description: 需求架构师·原型设计 — 高保真 HTML 原型，先抽项目宪法 UI 约束再调 frontend-design（防发散）。Use when design-flow 节点4 原型设计。
model: opus
---
# 原型设计

## Identity
需求架构师的原型设计能力（节点 n4-prototype）。吃 AR 用户故事，按 kdev-design-flow Stage3 方法论产出高保真 HTML 原型 `prototype/`，与 AR 共用 n5 评审 gate。

## Principles
- **反发散**：frontend-design 是通用 skill，不知项目宪法。调它前 **必须**先抽 `.specify/memory/constitution.md` 的前端 UI 约束（token/8px 栅格/字阶/对比度/字体白名单）注入 prompt，不假定它会自己翻。
- 一切对照 AR + 宪法约束，不凭印象。
- 只对自家编排负责（硬规5）。

## Critical Actions
- 步骤0（不可跳）：探 `.specify/memory/constitution.md`，抽 UI 约束块；扫 references/ 设计系统目录。
- 调 `frontend-design:frontend-design`，把宪法约束块 + AR 填进 design-flow `references/stage3-prototype-prompt.md` 模板后传入。
- 产出 `prototype/`（含 index.html + self-check.md），落 `.kdev/features/<slug>/handoffs/req-architect/prototype/`。
- 完成 → 回编排进 n5-ar-proto-review（AR+原型共评，self）；FAIL reflow 回本节点重做。

## Capabilities
- `frontend-design:frontend-design` — 高保真原型生成。
- 参 kdev-design-flow `references/stage3-prototype-prompt.md`（含宪法 UI 约束注入模板）。
运行时模型暂 Opus（L1 flow-config 可配）。
```

`plugins/kdev-team/agents/req-architect-design.md`：

```markdown
---
name: req-architect-design
description: 需求架构师·方案设计 — 概要+详细技术方案（架构/接口/数据模型/风险），调 spec-kit:plan。Use when design-flow 节点6 方案设计。
model: opus
---
# 方案设计

## Identity
需求架构师的方案设计能力（节点 n6-design）。吃通过评审的 AR + 原型，按 kdev-design-flow Stage4 方法论调 `spec-kit:plan` 产出概要 + 详细技术方案 `design.md`，喂方案/设计闸。

## Principles
- 方案落到可实施粒度：架构图 + 模块划分 + 关键接口签名 + 数据模型 + 关键算法/状态机。
- 实现风险 ≥ 3 项 + 缓解，不回避。
- 只对自家编排负责（硬规5）。

## Critical Actions
- 调 `spec-kit:plan` 为 AR + 原型 产出概要 + 详细设计。
- 产出 `design.md`：概要（架构/模块/数据流）+ 详细（接口签名/数据模型/算法）+ 风险与缓解。
- 自验：方案覆盖每个用户故事、接口/类型自洽、风险项齐。
- 产物落 `.kdev/features/<slug>/handoffs/req-architect/design.md`。
- 完成 → 回编排进 n7-design-review（方案/设计闸，self）；FAIL reflow 回本节点。

## Capabilities
- `spec-kit:plan` — AR+原型 → 概要+详细设计方案。
运行时模型暂 Opus（L1 flow-config 可配）。
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd plugins/kdev-team && python3 -m pytest tests/test_agents.py -q`
Expected: PASS（含原 dev-engineer 断言 + 新 3 个 req 断言全绿）

- [ ] **Step 5: Commit**

```bash
git -c user.name=ly-AI -c user.email=ly1989abc@126.com add \
  plugins/kdev-team/agents/req-architect-*.md plugins/kdev-team/tests/test_agents.py
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-team): 6 req-architect agent（1 编排 + 5 业务，瘦 persona 真 CC frontmatter）"
```

---

## Task 3: staff.yml 追加 req-architect 词条 + test_staff

**Files:**
- Modify: `plugins/kdev-team/staff.yml`
- Modify: `plugins/kdev-team/tests/test_staff.py`

- [ ] **Step 1: 改 `test_staff.py` 加失败测试**

文件末尾追加：

```python
def test_req_architect_entry():
    d = yaml.safe_load(STAFF.read_text(encoding="utf-8"))
    emp = d["employees"]["req-architect"]
    assert emp["display"] == "需求架构师"
    assert emp["flow_skill"] == "kdev-design-flow"
    assert emp["node_table"] == "orchestration/req-architect.node-table.yml"
    assert len(emp["agents"]) == 6
    for a in emp["agents"]:
        assert (AGENTS / f"{a}.md").exists(), f"花名册引用的 agent 不存在: {a}"
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd plugins/kdev-team && python3 -m pytest tests/test_staff.py -q`
Expected: FAIL（`KeyError: 'req-architect'`）

- [ ] **Step 3: 改 `staff.yml`** — 把末行注释 `# req-architect 阶段2 P-A 追加` 替换为：

```yaml
  req-architect:
    display: 需求架构师
    flow_skill: kdev-design-flow          # 方法论参考（非编排器）
    node_table: orchestration/req-architect.node-table.yml
    runtime_model: opus
    agents:
      - req-architect-orchestrator
      - req-architect-clarify
      - req-architect-spec
      - req-architect-decompose
      - req-architect-prototype
      - req-architect-design
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd plugins/kdev-team && python3 -m pytest tests/test_staff.py -q`
Expected: PASS（2 passed）

- [ ] **Step 5: Commit**

```bash
git -c user.name=ly-AI -c user.email=ly1989abc@126.com add plugins/kdev-team/staff.yml plugins/kdev-team/tests/test_staff.py
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-team): staff.yml 追加 req-architect 词条（kdev-design-flow flow_skill + node_table + 6 agent）"
```

---

## Task 4: kdev-flow-driver references 追加 req-architect 段（路由 + gate 判据）

**Files:**
- Modify: `plugins/kdev-team/skills/kdev-flow-driver/references/node-agent-routing.md`
- Modify: `plugins/kdev-team/skills/kdev-flow-driver/references/gate-decision-logic.md`

> kdev-flow-driver SKILL 本体通用，**不改**。只在两个 reference 追加 req-architect 段（两文件本就声明「其他员工会有自己的路由表/判据」）。这两个文件无专门 pytest 断言，验证靠 grep + 跑 kdev-team 全量不回归。

- [ ] **Step 1: 在 `node-agent-routing.md` 末尾追加**

```markdown

---

# req-architect（需求架构师）design-flow 路由

适用于 `req-architect` 员工的 design-flow（node-table=`orchestration/req-architect.node-table.yml`）。

## 路由映射

| 节点 id | 节点名称 | subagent_type | agent 中文名 | 干什么 | 需传的上下文 |
|---|---|---|---|---|---|
| n0-clarify | 需求澄清 IR | `req-architect-clarify` | 需求架构师·需求澄清 | 澄清原始需求 → ir.md | 原始需求文本/路径, **产物根=`<workspace>/.kdev/features/<slug>/handoffs/req-architect/`** |
| n1-spec | 需求计划 SR | `req-architect-spec` | 需求架构师·需求计划 | 写 SR（参 design-flow stage1-sr-prompt/template）→ sr.md | ir.md 路径, 产物根 |
| n3-decompose | 需求拆解 AR | `req-architect-decompose` | 需求架构师·需求拆解 | 迭代拆分 + 用户故事（调 spec-kit:specify）；用户故事回编排 `add-story` 填 stories[] | sr.md 路径, 产物根 |
| n4-prototype | 高保真原型 | `req-architect-prototype` | 需求架构师·原型设计 | 高保真原型（先抽宪法 UI 约束再调 frontend-design）→ prototype/ | AR 路径, `.specify/memory/constitution.md`, 产物根 |
| n6-design | 方案设计 | `req-architect-design` | 需求架构师·方案设计 | 概要+详细方案（调 spec-kit:plan）→ design.md | AR+prototype 路径, 产物根 |
| n8-merge | 产物聚合+合并交付 | **编排自做（不派）** | 需求架构师·编排 | 阶段聚合报告 + 合并交付（参 design-flow output-merge-rules.md）→ docs/design-flow/<slug>/ | 各阶段终版路径 |

## Gate 节点（n2-sr-review / n5-ar-proto-review / n7-design-review）

由编排器（你）按 design-flow 判据自判，不派业务 agent。判据见 `gate-decision-logic.md` 的 req-architect 段。

## ⚠️ 产物落 handoffs/req-architect/（同 dev-engineer 的 delivery/ 教训，G-006）

派 req-architect 业务 agent 时，**必须在上下文写死「产物根 = `<workspace>/.kdev/features/<slug>/handoffs/req-architect/`」**，所有 ir/sr/ar/prototype/design 都落这里，不套用全局 `screenshots/` 规则。最终合并交付落 `docs/design-flow/<slug>/`。
```

- [ ] **Step 2: 在 `gate-decision-logic.md` 末尾追加**

```markdown

---

# req-architect（需求架构师）gate 判据

适用于 `req-architect` 员工的 design-flow。3 评审 gate 复刻 kdev-design-flow 的 3 闸门，**阶段1 全 `reviewer=self`**——主控按 design-flow `skills/kdev-design-flow/references/review-gate-prompt.md` 的成功标准自评，`config.review_mode` 控档：

- **ai**（默认）：主控自评 → 输出 VERDICT/ISSUES → PASS/FAIL，直接 record-gate。
- **both**：自评后 `AskUserQuestion` 让用户确认/覆盖，再 record-gate。
- **human**：直接 `AskUserQuestion` 让用户判 PASS/FAIL。

| Gate | 节点 | 复刻 design-flow | 评审对象 | 判据来源 |
|---|---|---|---|---|
| g-sr-review | n2-sr-review | Gate1 | sr.md | review-gate-prompt.md Stage1 成功标准 |
| g-ar-proto-review | n5-ar-proto-review | Gate2（AR+原型共评）| ar + prototype/ | review-gate-prompt.md Stage2 成功标准（含 C-2.6 宪法合规）|
| g-design-review | n7-design-review | Gate3 | design.md | review-gate-prompt.md Stage3/4 成功标准 |

## 回流有界（复刻 design-flow「3 次 FAIL → 升人」）

FAIL 时引擎自动 `gate_iters++`；达 `max_retries(3)` → `status=blocked` 留原地升人（不强过、不冒充第三方）。回流目标：

- g-sr-review FAIL → n1-spec（重写 SR）
- g-ar-proto-review FAIL → n4-prototype（重做原型；AR 本身要返工时编排升级回 n3-decompose）
- g-design-review FAIL → n6-design（重做方案）

> 注：这是 review gate 的 R3 escalate（→ blocked），不是 R2 机械 reflow（→ terminal_fail n-fail）。req-architect 全 review gate，正常不触达 n-fail。
```

- [ ] **Step 3: 验证（grep + kdev-team 全量不回归）**

Run:
```bash
cd plugins/kdev-team
grep -q "req-architect（需求架构师）design-flow 路由" skills/kdev-flow-driver/references/node-agent-routing.md && echo "routing OK"
grep -q "req-architect（需求架构师）gate 判据" skills/kdev-flow-driver/references/gate-decision-logic.md && echo "gate OK"
python3 -m pytest tests -q
```
Expected: `routing OK` + `gate OK` + kdev-team 全绿（此时应 16 passed：原 12 + node-table 6... 实际累计，确认无回归即可）

- [ ] **Step 4: Commit**

```bash
git -c user.name=ly-AI -c user.email=ly1989abc@126.com add plugins/kdev-team/skills/kdev-flow-driver/references/
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-flow-driver): references 追加 req-architect 路由 + gate 判据段（driver 本体通用不改）"
```

---

## Task 5: 删除 design-flow 自带 flow_state（迁到 kdev-core）

**Files:**
- Delete: `plugins/kdev-design-flow/lib/flow_state.py`
- Delete: `plugins/kdev-design-flow/tests/test_flow_state.py`

> ⚠️ 本 AR 是跨模块状态迁移（用户标 opus）。kdev-core `flow_state.py` 已覆盖原子写/损坏检测/拒重写/review_mode 校验等同等行为（已核对），故删 design-flow 自带版安全。**保留 `lib/slug.py` + `test_slug.py`**（slug 仍是 design-flow 职责）。

- [ ] **Step 1: 删除前 grep 全仓确认无其它引用**

Run:
```bash
cd /home/lyadmin/Projects/kdev-agents-pa
grep -rn "lib.flow_state\|from lib import flow_state\|flow_state import" \
  plugins/kdev-design-flow --include="*.py" --include="*.md" | grep -v "tests/test_flow_state.py"
```
Expected: 仅 `SKILL.md` 步骤2/恢复模式 命中（Task 6 处理）；无其它 .py 引用。若有意外引用，先记录再继续。

- [ ] **Step 2: 删文件**

```bash
cd /home/lyadmin/Projects/kdev-agents-pa
git -c user.name=ly-AI -c user.email=ly1989abc@126.com rm \
  plugins/kdev-design-flow/lib/flow_state.py \
  plugins/kdev-design-flow/tests/test_flow_state.py
```

- [ ] **Step 3: 跑 design-flow 测试确认 slug 仍绿、无 import 残骸**

Run: `cd plugins/kdev-design-flow && python3 -m pytest tests -q`
Expected: PASS（test_slug.py 11 + test_skill_md_lint.py 12 = 23 绿；原 33 减去 test_flow_state 的 9 = 24？以实际为准——关键是无 import error、无 test_flow_state 残留收集错误）

> 注：若 `tests/conftest.py` 的 `tmp_workspace` fixture 变孤儿不影响（pytest 容忍未用 fixture）。如 conftest 顶部 import 了 `lib.flow_state` 会炸——则一并清掉该 import。

- [ ] **Step 4: Commit**

```bash
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "refactor(kdev-design-flow): 删除自带 flow_state（golden seed 迁到 kdev-core 引擎，超集已覆盖；保留 slug）"
```

---

## Task 6: design-flow SKILL 回归方法论参考（去自跑状态机）

**Files:**
- Modify: `plugins/kdev-design-flow/skills/kdev-design-flow/SKILL.md`
- Create: `plugins/kdev-design-flow/tests/test_skill_base_migration.py`

> 核心：**保留全部方法论**（Stage 1-4 / Gate 1-3 / references / 3 review 模式 / Stage3 宪法抽取 / 恢复模式错误处理——这些是 `test_skill_md_lint.py` 锁的，必须留），**只换掉自跑状态机**（lib.flow_state init/读写、current_stage/current_iter 主循环、flow-state.json 突变 prose），改为指向通用 kdev-flow-driver + kdev-core + feature-first 存储。

- [ ] **Step 1: 写迁移断言测试** `plugins/kdev-design-flow/tests/test_skill_base_migration.py`

```python
"""design-flow 接底座迁移断言：SKILL 回归方法论参考，不自跑状态机。"""
from pathlib import Path

PLUGIN = Path(__file__).resolve().parent.parent
SKILL = PLUGIN / "skills" / "kdev-design-flow" / "SKILL.md"


def _body():
    return SKILL.read_text(encoding="utf-8")


def test_skill_no_longer_imports_own_flow_state():
    """编排状态迁到 kdev-core——SKILL 不再 import/驱动自带 lib.flow_state。"""
    body = _body()
    assert "lib.flow_state" not in body
    assert "from lib.flow_state import" not in body
    assert "init_state(" not in body


def test_skill_points_to_generic_driver_and_engine():
    """编排归通用 kdev-flow-driver + kdev-core，不在 SKILL 自跑。"""
    body = _body()
    assert "kdev-flow-driver" in body
    assert "kdev_core" in body or "kdev-core" in body


def test_skill_uses_feature_first_storage():
    """运行时状态落 feature-first .kdev/features/<slug>/（非旧 .kdev/design-flow 状态机）。"""
    body = _body()
    assert ".kdev/features/" in body


def test_skill_methodology_preserved():
    """方法论（Stage/Gate）仍在——回归参考不是删内容。"""
    body = _body()
    for tok in ["Stage 1", "Stage 2", "Stage 3", "Stage 4", "Gate 1", "Gate 2", "Gate 3"]:
        assert tok in body, f"方法论 token 丢失: {tok}"
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd plugins/kdev-design-flow && python3 -m pytest tests/test_skill_base_migration.py -q`
Expected: FAIL（当前 SKILL 仍含 `lib.flow_state` / `init_state(` / 无 kdev-flow-driver 指针 / 无 `.kdev/features/`）

- [ ] **Step 3: 改 SKILL.md** —— 改动点（保留方法论，换状态机）：

**(a) 头部「调用方式」段后，插入接底座说明：**
```markdown
## 本 SKILL 的定位（接底座后）

本 SKILL 是**需求设计方法论参考**（各 Stage 的 prompt/模板、Gate 判据、合并规则），**不再自带状态机、不充当编排器**。运行时编排由 kdev-team 的**通用 `kdev-flow-driver` skill**（顶层主控执行循环）按 `req-architect`（需求架构师）员工的 `orchestration/req-architect.node-table.yml` 驱动 **kdev-core 引擎**完成；状态落 feature-first 存储 `.kdev/features/<slug>/`（含 `handoffs/req-architect/` 产物）。

- 直接跑设计流：`/kdev-flow-driver req-architect --task "<需求>"`（通用 driver 路由 req-architect）。
- 本 SKILL 被 `req-architect-*` 业务 agent 当方法论参考读（怎么写 SR / 怎么调 frontend-design / 评审判据）。
```

**(b) 「步骤 2：初始化状态」** —— 把 `from lib.flow_state import init_state` 那段 python 块整段替换为指向 kdev-core 引擎：
```markdown
### 步骤 2：初始化状态（接 kdev-core 引擎）

> 接底座后状态由 kdev-core 引擎管，不再用本 skill 自带 flow_state。slug 仍由 `lib.slug.slugify(feature_name)` 生成（kdev-core 的 slug 由调用方直传）。

```bash
python3 -c "import sys; sys.path.insert(0,'${CLAUDE_PLUGIN_ROOT}'); from lib.slug import slugify; print(slugify('${feature_name}'))"
```
拿到 slug 后，由通用 kdev-flow-driver / req-architect 编排调 kdev-core 立项：
`python3 -m kdev_core init design-flow <slug> --display-name "${feature_name}" --review-mode ${review_mode} --initial-node n0-clarify`
（节点机/gate 推进/回流/blocked 升人全由 kdev-core 引擎承载，见 req-architect.node-table.yml）。
```

**(c) 「步骤 4：进入主循环」+「评审闸门通用机器」中所有 `flow-state.json` 的 `current_stage`/`current_iter` 突变 prose** —— 改为「由 kdev-core 引擎 + node-table 承载」，但**保留每个 Gate 的成功标准/review_mode 5a/5b/5c 分支判据**（这是方法论，agent 自评时用）。即：删「在 flow-state.json 设 current_stage += 1」这类引擎机械动作的 prose，留「ai/both/human 怎么判 + PASS/FAIL 后语义」。把 PASS/FAIL 后果改述为「编排 record-gate，引擎据 node-table on_pass/on_reflow 推进；连续 FAIL 达 3 次引擎 escalate 为 blocked 升人」。

**(d) 各 Stage 产物路径** —— `.kdev/design-flow/<slug>/stage-N-*/` 改为 `.kdev/features/<slug>/handoffs/req-architect/`（运行时产物）；最终 Merge 仍落 `docs/design-flow/<slug>/`。

**(e) 「恢复模式」段** —— 改为指向 kdev-core resume，但**保留 FlowStateError / 找不到 slug 错误处理**（`test_skill_md_lint.test_resume_section_handles_missing_state` 锁）：
```markdown
## 恢复模式（`--resume <slug>`）

接底座后断点续跑由 kdev-core 引擎承载：`python3 -m kdev_core resume design-flow <slug>`。

0. 先确认存在——若引擎抛 `FlowStateError`（`no flow-state.json at .kdev/features/<slug>/`），向用户输出（不继续执行）：

   ```
   ❌ 找不到 slug "<slug>" 的流程记录。
   预期路径：.kdev/features/<slug>/flow-state.json
   请检查 slug 拼写 / 是否在项目根目录执行。
   新建去掉 --resume：/kdev-design-flow <feature_name>
   ```
1. resume 成功 → 由通用 kdev-flow-driver 从 `current_node` 接着跑；blocked → 先 `kdev_core unblock`。
```

> **保留不动**（lint 锁）：description frontmatter（SKIP/3 review 模式/resume 归属）、Stage 1-4 标题与方法、Gate 1-3、所有 references/* 引用与文件、Stage 3 步骤0 宪法抽取（`.specify/memory/constitution.md` + `stage3-prototype-prompt.md` + design/references 扫描）、`codex` 不出现。

- [ ] **Step 4: 跑两组测试确认通过**

Run:
```bash
cd plugins/kdev-design-flow && python3 -m pytest tests/test_skill_base_migration.py tests/test_skill_md_lint.py -q
```
Expected: PASS（迁移 4 断言 + 原 lint 12 断言全绿）。若 lint 某 token 报错 → 说明改动误删 methodology token，回 Step 3 补回。

- [ ] **Step 5: 跑 design-flow 全量**

Run: `cd plugins/kdev-design-flow && python3 -m pytest tests -q`
Expected: PASS（slug 11 + lint 12 + 迁移 4 = 27 绿，0 fail）

- [ ] **Step 6: Commit**

```bash
git -c user.name=ly-AI -c user.email=ly1989abc@126.com add \
  plugins/kdev-design-flow/skills/kdev-design-flow/SKILL.md \
  plugins/kdev-design-flow/tests/test_skill_base_migration.py
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "refactor(kdev-design-flow): SKILL 回归方法论参考（编排归通用 kdev-flow-driver + kdev-core，状态落 feature-first；保 methodology+lint）"
```

---

## Task 7: bump 版本 + CHANGELOG（kdev-team + kdev-design-flow）

**Files:**
- Modify: `plugins/kdev-team/.claude-plugin/plugin.json`
- Modify: `plugins/kdev-team/CHANGELOG.md`
- Modify: `plugins/kdev-design-flow/.claude-plugin/plugin.json`
- Modify: `plugins/kdev-design-flow/CHANGELOG.md`

- [ ] **Step 1: bump kdev-team plugin.json** — `"version": "0.2.0"` → `"version": "0.3.0"`

- [ ] **Step 2: kdev-team CHANGELOG.md 顶部加条目**

```markdown
## 0.3.0 — 2026-06-12

**P-A：第二个数字员工「需求架构师 req-architect」接 kdev-core 底座**

- 新增 `orchestration/req-architect.node-table.yml`：design-flow SOP（IR→SR→AR→原型→方案 5 业务阶段 + 3 评审 gate + 聚合收尾，11 节点）。复用通用 `kdev-flow-driver`，kdev-core 零改。
- 新增 6 个 `req-architect-*` agent（1 编排 + 5 业务：clarify/spec/decompose/prototype/design），瘦 persona 真 CC frontmatter。
- `staff.yml` 追加 req-architect 词条（flow_skill=kdev-design-flow）。
- `kdev-flow-driver/references/` 追加 req-architect 路由 + gate 判据段（driver 本体通用不改）。
- 3 评审 gate 阶段1 全 `reviewer=self`（复刻 design-flow 自评 SOP，非 deferred）；评审 FAIL 有界 → blocked 升人。
```

- [ ] **Step 3: bump kdev-design-flow plugin.json** — `"version": "0.2.0"` → `"version": "0.3.0"`

- [ ] **Step 4: kdev-design-flow CHANGELOG.md 顶部加条目**

```markdown
## 0.3.0 — 2026-06-12

**接 kdev-core 底座：SKILL 回归方法论参考，自带 flow_state 退役**

- 删除自带 `lib/flow_state.py` + `tests/test_flow_state.py`——编排状态迁到 kdev-core 引擎（feature-first `.kdev/features/<slug>/`，kdev-core 是 golden seed 的泛化超集，已含 review_mode/escalate/stories）。保留 `lib/slug.py`（slug 仍本地生成）。
- SKILL.md 回归**方法论参考**（各 Stage prompt/模板、Gate 判据、合并规则），**不再自跑状态机**；运行时编排由 kdev-team 通用 `kdev-flow-driver` + `req-architect.node-table.yml` 驱动。
- SOP 行为不破：3 评审闸门 / 3 retry / 宪法 UI 抽取 / 恢复模式错误处理 均保留（lint + 迁移断言兜）。
```

- [ ] **Step 5: 验证 plugin manifest 测试 + JSON 合法**

Run:
```bash
cd plugins/kdev-team && python3 -m pytest tests/test_plugin_manifest.py -q
cd /home/lyadmin/Projects/kdev-agents-pa
python3 -c "import json; print(json.load(open('plugins/kdev-team/.claude-plugin/plugin.json'))['version'], json.load(open('plugins/kdev-design-flow/.claude-plugin/plugin.json'))['version'])"
```
Expected: PASS + `0.3.0 0.3.0`

- [ ] **Step 6: Commit**

```bash
git -c user.name=ly-AI -c user.email=ly1989abc@126.com add \
  plugins/kdev-team/.claude-plugin/plugin.json plugins/kdev-team/CHANGELOG.md \
  plugins/kdev-design-flow/.claude-plugin/plugin.json plugins/kdev-design-flow/CHANGELOG.md
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "chore: bump kdev-team 0.3.0 + kdev-design-flow 0.3.0（P-A req-architect 接底座）"
```

---

## Task 8: 全量回归 + roadmap §1.5.2 回写

**Files:**
- Modify: `docs/framework/01-design/2026-06-06-01-数字员工整体设计路线图roadmap-v1.0.md`

- [ ] **Step 1: 三套全量回归（core 不应变 / design-flow / team）**

Run:
```bash
cd /home/lyadmin/Projects/kdev-agents-pa
for p in kdev-core kdev-design-flow kdev-team; do
  echo "== $p =="; (cd plugins/$p && python3 -m pytest tests -q 2>&1 | tail -3)
done
```
Expected: kdev-core 126 绿（不变）；kdev-design-flow 27 绿；kdev-team 16+ 绿（原 12 + node-table 6 - 但 test_agents/test_staff 是扩展同文件，以实际 collected 数为准，关键 0 fail）。

- [ ] **Step 2: design-flow evals 不回归（描述触发契约保全）**

> trigger-eval 用 skill-creator run_eval 在嵌套 CC 环境失效（已知，见记忆 skill-creator-run-eval-limitation）。改为静态确认 description 触发契约未破：
```bash
cd plugins/kdev-design-flow
python3 -c "
import yaml
fm = yaml.safe_load(open('skills/kdev-design-flow/SKILL.md').read().split('---')[1])
d = fm['description']
assert 'SKIP' in d, 'SKIP 分支丢失'
assert all(m in d.lower() for m in ['ai','both','human']), '3 review 模式丢失'
assert ('resume' in d.lower() or '恢复' in d or '继续' in d), 'resume 归属丢失'
print('trigger 契约保全 OK')
"
```
Expected: `trigger 契约保全 OK`（= test_skill_md_lint 的 description 断言同源，已绿）

- [ ] **Step 3: 回写 roadmap §1.5.2** — 在路线图 §1.5.2 的 P-A 行（`P-A 需求架构师接底座（接最终契约）`）旁标 ✅，并在 §1.5.2 段落补一行实测小结（仿 P-0 风格）：

```markdown
- **✅ P-A done（2026-06-12，kdev-team v0.3.0 + kdev-design-flow v0.3.0）**：第二员工「需求架构师 req-architect」接 kdev-core 底座。`orchestration/req-architect.node-table.yml`（IR→SR→AR→原型→方案 5 阶段 + 3 self 评审 gate，复刻 design-flow 3 闸门）+ 6 `req-architect-*` agent（1 编排 + 5 业务）+ `staff.yml` 词条 + `kdev-flow-driver/references` 追加路由/判据段（**通用 driver 本体不改**，kdev-core 零改）。kdev-design-flow 自带 flow_state 退役（迁 kdev-core feature-first），SKILL 回归方法论参考。测试 **kdev-team 16+ / design-flow 27 / kdev-core 126 全绿**，design-flow 触发契约保全。分支 `feat/p-a-req-architect`。⚠️ G-004：bump version 后需用户刷 marketplace + 重启 session 才激活 `req-architect-*` subagent_type 直派。下一步 **P-B**（SR/AR → coding-flow 跨员工 handoff 协议）。
```
（同时把 §1.5.2 顶部序列图/表格里 `P-A ⏳` 改 `P-A ✅`。具体行用 grep 定位后 Edit。）

- [ ] **Step 4: Commit**

```bash
git -c user.name=ly-AI -c user.email=ly1989abc@126.com add "docs/framework/01-design/2026-06-06-01-数字员工整体设计路线图roadmap-v1.0.md"
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "docs(roadmap): §1.5.2 标 P-A ✅（req-architect 接底座；kdev-team 0.3.0 + design-flow 0.3.0）"
```

- [ ] **Step 5: 最终核对 git 状态干净 + 分支提交链**

Run:
```bash
cd /home/lyadmin/Projects/kdev-agents-pa
git status --short        # 应只剩计划文件或干净
git log --oneline 5c5c418..HEAD
```
Expected: 工作区干净（.kdev symlink 已被 worktree-local exclude 忽略）；提交链含 Task 1-8 各 commit，全 ly-AI 身份。**不 push**（待用户确认）。

---

## Self-Review（对照 spec 任务范围）

| 范围项（任务书）| 覆盖任务 |
|---|---|
| 1. req-architect 6 agent 落 kdev-team/agents（canonical id，真 frontmatter；orchestrator=编排知识非自跑）| Task 2 |
| 2. orchestration/req-architect.node-table.yml（IR→SR→AR→原型→方案 + gate_specs）| Task 1 |
| 3. node-agent-routing.md 追加 req-architect 路由段（driver 本体通用不改）| Task 4 |
| 4. design-flow 接底座（自带 flow_state 迁 kdev-core，feature-first，保 SOP+evals）| Task 5 + 6 |
| 5. design-flow SKILL 回归方法论参考（不充当编排器）| Task 6 |
| 6. staff.yml 追加 req-architect 词条（display/flow_skill/node_table/runtime_model/agents）| Task 3 |
| 7. 产物落位（记忆 scope .kdev/memory/staff/req-architect/ + handoffs/req-architect/）| Task 2（agent prose）+ Task 4（routing 写死产物根）|
| 8. bump kdev-team plugin.json + CHANGELOG | Task 7 |

| 硬约束 | 落实 |
|---|---|
| 编排走通用 kdev-flow-driver，不新建 skill/命令，不下放给 orchestrator agent | Task 1/2/4（orchestrator=fallback 文档；driver 不改）|
| 接 feature-first（.kdev/features/<slug>/），不接旧 .kdev/flows/ | Task 1（node-table）+ Task 6（SKILL 存储路径）|
| canonical ASCII id 全处，中文名只在 display | Task 2/3（id req-architect-*；display 需求架构师）|
| 守 Q-008（编排=主控按 node-table 驱动）；SKILL 不埋编排 prose | Task 6（SKILL 去状态机）|
| design-flow SOP 行为不破（evals 兜）| Task 6（lint + 迁移断言 + 触发契约）|
| handoff 协议本步不做（P-B），只落产物进 handoffs/req-architect/ 目录约定 | Task 2/4（仅产物根，不定协议）|
| 别 copy dev-engineer 文档漂移（13 vs 14 节点）| Task 2（orchestrator 用「5 阶段+3 gate」描述，不写漂移节点数）|

**额外取证**：marketplace.json 无 version 字段 → 不改 → 与并行 kdev-hud worktree 不撞车（仅 plugin.json bump）。
