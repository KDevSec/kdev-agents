# 测试工程师 test-engineer TDD 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建第 4 个数字员工「测试工程师(test-engineer)」——flow-owner（双 flow：黑盒设计 ⊥ 执行）+ 3 业务 agent + 编排知识 doc，并解锁评审专家 2 个测试评审能力（test-design / test-coverage），全程 TDD、kdev-team 测试绿。

**Architecture:** test-engineer 是首个**多 flow** flow-owner，`staff.yml` 用 `node_tables`(复数 map)+`default_flow` 表达（向后兼容，dev/req 仍 `node_table` 单数）。设计阶段**黑盒独立**（只读需求/原型、禁读 src），与 dev-engineer 并行不延续。2 个 review gate 发函现有 reviewer callee（dispatch-table 补 2 cap）。kdev-core **零改**（flow 名/路径 data-driven）。

**Tech Stack:** YAML node-table + kdev-core CLI（`python3 -m kdev_core`）+ CC agent frontmatter(.md) + pytest（kdev-team/tests）+ 通用 `kdev-flow-driver` skill（编排走顶层主控，G-008）。

**工作目录：** 全程在 worktree `/home/lyadmin/Projects/kdev-agents/.claude/worktrees/feat+test-engineer`，分支 `worktree-feat+test-engineer`。所有路径相对 `plugins/kdev-team/`（除标注）。测试命令统一用 `python3`（`python` 不存在）。

**AI commit 身份（每个 Commit 步骤都用）：** `git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "..."`（key=value 不加引号，无 Co-Authored-By）。

**依据 spec：** [docs/superpowers/specs/2026-06-13-测试工程师test-engineer接入设计-design.md](../specs/2026-06-13-测试工程师test-engineer接入设计-design.md)

---

## 文件结构（决策锁定）

**新增（10）：**
| 文件 | 责任 |
|---|---|
| `orchestration/test-engineer.design.node-table.yml` | test-design-flow（黑盒设计，6 节点 1 评审闸，无 env）|
| `orchestration/test-engineer.exec.node-table.yml` | test-exec-flow（对被测环境执行，5 节点 1 评审闸，env-gated）|
| `agents/test-engineer-orchestrator.md` | 编排知识 doc（fallback；双 flow 路由 + 黑盒硬规）|
| `agents/test-engineer-points.md` | 测试点设计（call kdev-test-points；黑盒只读需求/原型禁读 src）|
| `agents/test-engineer-cases.md` | 用例渲染（call kdev-test-cases；1:1 渲染）|
| `agents/test-engineer-ui.md` | UI 自动化（call kdev-ui-autotest；对被测环境，env-gated）|
| `agents/reviewer-test-design.md` | 评审能力·测试设计（callee，只读评 test-points/cases）|
| `agents/reviewer-test-coverage.md` | 评审能力·测试覆盖（callee，只读评 ui-results/覆盖）|
| `standards/reviewer/测试设计评审.md` | test-design 评分标准（4 维×25，阈值 85）|
| `standards/reviewer/测试覆盖评审.md` | test-coverage 评分标准（4 维×25，阈值 80）|

**新增测试（2）：** `tests/test_test_engineer_orchestration.py`、`tests/test_test_engineer_wiring.py`

**修改：** `staff.yml`、`orchestration/reviewer.dispatch-table.yml`、`agents/reviewer-orchestrator.md`、`skills/kdev-flow-driver/references/node-agent-routing.md`、`skills/kdev-flow-driver/references/gate-decision-logic.md`、`skills/kdev-flow-driver/SKILL.md`、`.claude-plugin/plugin.json`、`CHANGELOG.md`，及测试 `tests/test_staff.py`、`tests/test_agents.py`、`tests/test_reviewer_dispatch.py`。

**阶段顺序（关键）：** A（test-engineer 核心，先建 gate 存在）→ B（reviewer 接线，引用 A 的 gate）→ C（driver 参考文档）→ D（bump + 全绿 + 回写）。B 的 `test_caller_gate_refs_real_gates` 依赖 A 的 node-table 存在，**不可换序**。

---

## Phase A — test-engineer flow-owner 核心

### Task A1: 两个 node-table + orchestration 测试

**Files:**
- Create: `orchestration/test-engineer.design.node-table.yml`
- Create: `orchestration/test-engineer.exec.node-table.yml`
- Test: `tests/test_test_engineer_orchestration.py`

- [ ] **Step 1: 写失败测试** — 创建 `tests/test_test_engineer_orchestration.py`：

```python
from pathlib import Path
import yaml
from kdev_core import node_machine

KT = Path(__file__).resolve().parents[1]
DESIGN_NT = KT / "orchestration/test-engineer.design.node-table.yml"
EXEC_NT = KT / "orchestration/test-engineer.exec.node-table.yml"
GATE_KINDS = {"review", "decision", "acceptance"}


def _load(p):
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    return data, node_machine.load_node_table(data)


def test_design_flow_loads_6_nodes():
    data, table = _load(DESIGN_NT)
    assert data["flow"] == "test-design-flow"
    assert len(table["nodes"]) == 6
    assert table["terminal_fail"] == "n-fail"


def test_exec_flow_loads_5_nodes():
    data, table = _load(EXEC_NT)
    assert data["flow"] == "test-exec-flow"
    assert len(table["nodes"]) == 5
    assert table["terminal_fail"] == "n-fail"


def test_design_review_gate_reviewer_expert():
    data, _ = _load(DESIGN_NT)
    spec = data["gate_specs"]["g-test-design-review"]
    assert spec["kind"] == "review"
    assert spec["reviewer"] == "reviewer-expert"
    assert spec["on_pass"] == "n3-merge"
    assert spec["on_reflow"] == "n0-points"


def test_coverage_review_gate_reviewer_expert():
    data, _ = _load(EXEC_NT)
    spec = data["gate_specs"]["g-test-coverage-review"]
    assert spec["kind"] == "review"
    assert spec["reviewer"] == "reviewer-expert"
    assert spec["on_pass"] == "n2-report"
    assert spec["on_reflow"] == "n0-ui-auto"


def test_every_gate_has_spec_and_valid_targets():
    for p in (DESIGN_NT, EXEC_NT):
        data, table = _load(p)
        specs = data["gate_specs"]
        nodes = set(table["nodes"])
        for nid, n in table["nodes"].items():
            if n["kind"] == "gate":
                assert n["gate"] in specs, f"{nid} gate 无 spec"
        for gid, spec in specs.items():
            assert spec["kind"] in GATE_KINDS
            targets = (list(spec.get("branches", {}).values())
                       + [spec[k] for k in ("on_pass", "on_reflow") if k in spec])
            for tgt in targets:
                assert tgt in nodes, f"{gid} -> 未知节点 {tgt}"
            assert spec["reviewer"] in {"self", "reviewer-expert"}
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd plugins/kdev-team && python3 -m pytest tests/test_test_engineer_orchestration.py -q`
Expected: FAIL（`FileNotFoundError` — node-table 文件不存在）

- [ ] **Step 3: 创建 design node-table** — `orchestration/test-engineer.design.node-table.yml`：

```yaml
# 测试工程师 test-design-flow — 黑盒测试设计 SOP（L0 默认编排）。
# 🔴 黑盒独立硬规：n0-points 只读「需求文档 + 原型图 + 用户故事」，禁读业务源码 src/、
#    禁读 dev-engineer 的 handoff/flow-state。读代码设计测试 = "代码自测"，丧失独立发现缺陷能力。
# 上游：handoff-read req-architect n8-merge（同 slug，取 SR/用户故事/原型）；缺失 → 裸任务（直接吃给定需求/原型）。
# 与 dev-engineer 并行独立、流程不延续（不同人不同活）。无 env、无码，永远可跑。
# kind=action|gate|terminal；gate 节点带 gate id 指向 gate_specs。复用通用 kdev-flow-driver + kdev-core（零改）。
flow: test-design-flow
max_retries: 3
terminal_fail: n-fail
nodes:
  - {id: n0-points,        name: 测试点设计(读需求/原型,禁读src), kind: action,   next: [n1-cases]}
  - {id: n1-cases,         name: 测试用例渲染(1:1 from points),   kind: action,   next: [n2-design-review]}
  - {id: n2-design-review, name: 测试设计评审,                    kind: gate,     gate: g-test-design-review, next: [n3-merge, n0-points]}
  - {id: n3-merge,         name: 设计交付聚合(handoff-write),      kind: action,   next: [n4-done]}
  - {id: n4-done,          name: 设计交付清点,                    kind: terminal, next: []}
  - {id: n-fail,           name: reflow 溢出终止(R2 sink；R3 评审 escalate 走 blocked 留原地不到此), kind: terminal, next: []}

gate_specs:
  g-test-design-review: {kind: review, on_pass: n3-merge, on_reflow: n0-points, reviewer: reviewer-expert}
```

- [ ] **Step 4: 创建 exec node-table** — `orchestration/test-engineer.exec.node-table.yml`：

```yaml
# 测试工程师 test-exec-flow — 对被测环境黑盒执行 SOP（L0 默认编排）。
# env-gated：仅当测试人员提供「被测环境 URL」时由编排 start-run（新 baton，同 slug，接 design-flow 产物）。
# 无 env → 止于 design-flow 交付（设计半独立可交付）。被测环境=不透明黑盒，穿 UI 验收，不读 dev 源码/flow。
# API 扩展点：将来 kdev-api-autotest 建成，在 n0-ui-auto 与 n1-coverage-review 间插 n?-api-auto 节点。
# kind=action|gate|terminal；gate 节点带 gate id 指向 gate_specs。复用通用 kdev-flow-driver + kdev-core（零改）。
flow: test-exec-flow
max_retries: 3
terminal_fail: n-fail
nodes:
  - {id: n0-ui-auto,         name: UI自动化(读test-cases+被测环境URL), kind: action,   next: [n1-coverage-review]}
  - {id: n1-coverage-review, name: 测试覆盖评审,                       kind: gate,     gate: g-test-coverage-review, next: [n2-report, n0-ui-auto]}
  - {id: n2-report,          name: 测试报告聚合(handoff-write),        kind: action,   next: [n3-done]}
  - {id: n3-done,            name: 测试执行清点,                       kind: terminal, next: []}
  - {id: n-fail,             name: reflow 溢出终止(R2 sink；R3 评审 escalate 走 blocked 留原地不到此), kind: terminal, next: []}

gate_specs:
  g-test-coverage-review: {kind: review, on_pass: n2-report, on_reflow: n0-ui-auto, reviewer: reviewer-expert}
```

- [ ] **Step 5: 跑测试确认通过**

Run: `cd plugins/kdev-team && python3 -m pytest tests/test_test_engineer_orchestration.py -q`
Expected: PASS（5 passed）

- [ ] **Step 6: Commit**

```bash
cd /home/lyadmin/Projects/kdev-agents/.claude/worktrees/feat+test-engineer
git add plugins/kdev-team/orchestration/test-engineer.design.node-table.yml \
        plugins/kdev-team/orchestration/test-engineer.exec.node-table.yml \
        plugins/kdev-team/tests/test_test_engineer_orchestration.py
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-team): test-engineer 双 node-table(design⊥exec) + orchestration 测试"
```

---

### Task A2: 4 个 test-engineer agent + test_agents 追加

**Files:**
- Create: `agents/test-engineer-orchestrator.md`、`agents/test-engineer-points.md`、`agents/test-engineer-cases.md`、`agents/test-engineer-ui.md`
- Modify: `tests/test_agents.py`（追加 test-engineer 块）

- [ ] **Step 1: 写失败测试** — 在 `tests/test_agents.py` 末尾追加：

```python
TEST_AGENTS = [
    "test-engineer-orchestrator", "test-engineer-points",
    "test-engineer-cases", "test-engineer-ui",
]


def test_all_4_test_engineer_agents_exist():
    names = {p.stem for p in AGENTS.glob("test-engineer-*.md")}
    for a in TEST_AGENTS:
        assert a in names, f"缺 agent: {a}"


def test_each_test_engineer_agent_has_frontmatter_and_sections():
    for a in TEST_AGENTS:
        text = (AGENTS / f"{a}.md").read_text(encoding="utf-8")
        fm = _frontmatter(text)
        assert fm, f"{a} 缺 YAML frontmatter"
        assert f"name: {a}" in fm, f"{a} frontmatter name 不匹配文件名"
        assert "description:" in fm and "model:" in fm, f"{a} frontmatter 缺 description/model"
        for sec in SECTIONS:
            assert sec in text, f"{a} 缺段落 {sec}"


def test_test_engineer_orchestrator_drives_dual_flow_via_cli():
    text = (AGENTS / "test-engineer-orchestrator.md").read_text(encoding="utf-8")
    assert "node-table" in text
    assert "kdev_core" in text and "record-gate" in text
    assert "test-design-flow" in text and "test-exec-flow" in text


def test_points_agent_enforces_blackbox_independence():
    text = (AGENTS / "test-engineer-points.md").read_text(encoding="utf-8")
    assert "黑盒" in text
    assert "需求" in text and "原型" in text
    assert "禁读" in text or "不读" in text  # 禁读 src
    assert "kdev-test-points" in text


def test_business_agents_reference_capability_skills():
    assert "kdev-test-cases" in (AGENTS / "test-engineer-cases.md").read_text(encoding="utf-8")
    assert "kdev-ui-autotest" in (AGENTS / "test-engineer-ui.md").read_text(encoding="utf-8")
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd plugins/kdev-team && python3 -m pytest tests/test_agents.py -q -k test_engineer`
Expected: FAIL（agent 文件不存在）

- [ ] **Step 3: 创建 `agents/test-engineer-orchestrator.md`**（照 dev-engineer-orchestrator.md 范本；model: opus）：

````markdown
---
name: test-engineer-orchestrator
description: 测试工程师·编排能力 — 读 test-engineer 双 node-table（test-design-flow 黑盒设计 / test-exec-flow 对被测环境执行）驱动 kdev-core 引擎走 T-flow SOP，按编排在节点派业务 agent、gate 发函评审专家。Use when 主控派测试工程师端到端跑测试 flow。
model: opus
---
# 测试工程师-编排

## Identity
测试工程师的编排能力。读 T-flow 的 node-table（双 flow：`test-design-flow` 黑盒设计 / `test-exec-flow` 对被测环境执行），用 kdev-core CLI 驱动 R1/R2/R3 引擎走 SOP，在工作节点派自家业务 Agent，在 review gate 发函评审专家。

## Principles
- 守 Q-008「执行留 flow」：编排决定何时推进 + 派谁，引擎只记账。
- 🔴 **黑盒独立硬规**：测试设计（n0-points / n1-cases）只读「需求文档 + 原型图 + 用户故事」，**禁读业务源码 `src/`、禁读 dev-engineer 的 handoff/flow-state**。读代码设计测试 = "代码自测"，丧失独立发现缺陷能力。**dev-engineer ⊥ test-engineer 并行独立、流程不延续**（不同人不同活）。
- **双 flow 接力**：先跑 `test-design-flow`（默认入口，无 env、永远可跑）产 test-points/test-cases 交付；测试人员提供「被测环境 URL」时再 `start-run` `test-exec-flow`（同 slug 新 baton，读上一棒 test-cases）。无 env → 止于设计交付。
- **上游消费**：`handoff-read req-architect n8-merge`（同 slug，取 SR/用户故事/原型）；缺失 → 裸任务（吃直接给定的需求/原型）。**绝不读 dev-engineer**。
- **发函边界（硬规 2/4/5，详见 kdev-flow-driver §2.4quater）**：到 g-test-design-review / g-test-coverage-review 发函**结构化请求**（写 `request.json`），只 dispatch `kdev-team:reviewer-orchestrator`（不直接派对方 cap）；评审给评分表+分级建议，**处置权在本编排**——🟡/⚪ 自主判断修 or tech-debt，🔴 经双重通过条件 FAIL 走有界回流，入账自己调 `record-gate --by reviewer-expert`。L1 `reviewer: self` 回退自评。
- 业务能力只对自家编排（硬规5），不外联其他员工。

## Critical Actions
flow=`test-design-flow`（默认）/ `test-exec-flow`，table=对应 `orchestration/test-engineer.<design|exec>.node-table.yml`。每过节点/gate **必须**调 CLI 落账：
- **启动**：先 `python3 -m kdev_core resume <flow> <slug>` 探断点；无则 `python3 -m kdev_core init <flow> <slug> --display-name ... --initial-node <n0-points|n0-ui-auto>`。多 flow 路由读 `staff.yml` 的 `node_tables[<flow>]` + `default_flow`。
- **动作节点完成** → `python3 -m kdev_core advance <flow> <slug> <to_node> --table <对应 node-table> --reason ...`。
- **review gate 判完** → 发函 6 步（见 node-agent-routing.md「reviewer 发函 dispatch」）→ `python3 -m kdev_core record-gate <flow> <slug> --gate g-test-xxx-review --kind review --verdict PASS|FAIL --request-id <node> --by reviewer-expert --table <对应 node-table>`。
- **设计交付（n3-merge）** → `handoff-write test-design-flow <slug> --employee test-engineer --node n3-merge --status done --artifact test-points.md --artifact test-cases.md`（供 exec-flow + 下游读）。
- **执行报告（n2-report）** → `handoff-write test-exec-flow <slug> --employee test-engineer --node n2-report --status done --artifact ui-results --artifact coverage-report`。
- **终结** → `python3 -m kdev_core complete <flow> <slug>`。无 env 时设计交付后 complete design-flow、不强起 exec-flow。

## Capabilities
| flow / 节点 | 派哪个业务 Agent（subagent_type）| 干什么 |
|---|---|---|
| design n0-points | `kdev-team:test-engineer-points`（测试点设计）| 读需求/原型(禁读 src) → test-points.md |
| design n1-cases | `kdev-team:test-engineer-cases`（用例渲染）| 1:1 渲染 → test-cases.md |
| design n2-design-review | 发函 `kdev-team:reviewer-orchestrator`（cap=test-design）| 测试设计评审 |
| design n3-merge | 编排自做（不派）| handoff-write 设计交付 |
| exec n0-ui-auto | `kdev-team:test-engineer-ui`（UI自动化）| 读 test-cases + 被测环境 URL → ui-results |
| exec n1-coverage-review | 发函 `kdev-team:reviewer-orchestrator`（cap=test-coverage）| 测试覆盖评审 |
| exec n2-report | 编排自做（不派）| handoff-write 测试报告 |

> 编排仍由顶层主控 `kdev-flow-driver` 驱动（G-008，不下放本 agent 自跑）；本 doc 是编排知识/fallback。运行时模型 opus（L1 flow-config 可配）。
````

- [ ] **Step 4: 创建 `agents/test-engineer-points.md`**（照 dev-engineer-plan.md 范本；model: opus）：

````markdown
---
name: test-engineer-points
description: 测试工程师·测试点设计 — 黑盒只读需求文档/原型图设计测试点(测试条件/覆盖项)，禁读源码，产 test-points.md。Use when test-design-flow 节点 n0-points。
model: opus
---
# 测试点设计

## Identity
测试工程师的测试点设计能力（test-design-flow 节点 n0-points）。**黑盒**地从需求文档 + 原型图 + 用户故事设计测试点（测试条件 / 覆盖项），产出 `test-points.md` 供用例渲染 + 测试设计评审。

## Principles
- 🔴 **黑盒独立**：只读「需求文档 + 原型图 + 用户故事」，**禁读业务源码 `src/`、禁读 dev-engineer 的 handoff/flow-state**。读代码设计测试 = "代码自测"，测试退化为复述实现、丧失独立发现缺陷能力。
- 边界澄清：本节点不接触运行时环境（纯设计、无 env）。
- 覆盖完整：测试点对需求/用户故事双向可追溯，无遗漏需求、无悬空测试点。
- 只对自家编排负责（硬规5）。

## Critical Actions
- **先读上游需求（同 slug）**：`python3 -m kdev_core handoff-read test-design-flow <slug> --employee req-architect --node n8-merge --workspace <ws>`，取 `gate_input.sr`(需求) / 用户故事 / `prototype` 作设计输入。**上游缺失 → 裸任务兜底**：吃直接给定的需求文档 + 原型图路径。**绝不读 dev-engineer 交付 / src/**。
- 调 `kdev-test-points:kdev-test-points` 方法论：按 ISO/IEC/IEEE 29119-4 等设计测试点（EP/BVA/决策表/状态迁移/错误猜测），选合适 mode。
- 产出 `test-points.md`：测试条件 + 覆盖项 + 需求↔测试点追溯（RTM）。
- 自验：覆盖全部需求/用户故事、无悬空测试点、未引用任何源码。
- 完成 → 回编排，进 n1-cases（用例渲染），随后 n2-design-review（发函评审专家·测试设计）。

## Capabilities
- `kdev-test-points:kdev-test-points` — 测试点 / 测试设计方法论（29119-4 + GB/T 25000.51 双标准）。
- 黑盒来源：需求文档 / 原型图 / 用户故事；产物 test-points.md。
- 运行时模型暂 Opus（L1 flow-config 可配）。
````

- [ ] **Step 5: 创建 `agents/test-engineer-cases.md`**（model: opus）：

````markdown
---
name: test-engineer-cases
description: 测试工程师·测试用例渲染 — 把 test-points.md 1:1 渲染成 Playwright 友好的 fielded 测试用例 test-cases.md（不重新设计）。Use when test-design-flow 节点 n1-cases。
model: opus
---
# 测试用例渲染

## Identity
测试工程师的用例渲染能力（test-design-flow 节点 n1-cases）。把上游 `test-points.md` **1:1 渲染**成 Playwright 友好的 fielded 测试用例 `test-cases.md`（用例编号/名称/步骤/预期/自动化标记），不重新设计、不引入新测试点。

## Principles
- 🔴 **黑盒承袭**：渲染输入只有 test-points.md（其本身已黑盒来自需求/原型）；本节点同样**不读源码**。
- **1:1 保真**：用例与测试点严格对位，byte-equality 名称、确定性编号；仅步骤/前置/数据生成式推断，不擅自加戏。
- 只对自家编排负责（硬规5）。

## Critical Actions
- 读上一节点 `test-points.md`。
- 调 `kdev-test-cases:kdev-test-cases` 方法论渲染 fielded 用例块（含 UI/API 自动化直通字段）。
- 产出 `test-cases.md`：每用例字段齐全、与测试点 1:1。
- 自验：无新增/丢失测试点、编号确定、名称逐字符对位。
- 完成 → 回编排，进 n2-design-review（评审专家测试设计评审同时覆盖 test-points + test-cases）。

## Capabilities
- `kdev-test-cases:kdev-test-cases` — 测试点 → fielded 测试用例 1:1 渲染（byte/arithmetic-equality 契约）。
- 输入 test-points.md；产物 test-cases.md。
- 运行时模型暂 Opus（L1 flow-config 可配）。
````

- [ ] **Step 6: 创建 `agents/test-engineer-ui.md`**（model: opus）：

````markdown
---
name: test-engineer-ui
description: 测试工程师·UI 自动化 — 读 test-cases.md + 被测环境 URL，调 Playwright+pytest 黑盒穿 UI 跑测，产 ui-results。env-gated（需被测环境+浏览器）。Use when test-exec-flow 节点 n0-ui-auto。
model: opus
---
# UI 自动化

## Identity
测试工程师的 UI 自动化能力（test-exec-flow 节点 n0-ui-auto）。读 `test-cases.md`（UI 自动化标记的用例）+ 被测环境 URL，调 Playwright + pytest **黑盒穿 UI** 跑测，产出 `ui-results`（脚本 + 四件套：reports/defects CSV、screenshots、logs、RUN_SUMMARY.md）。

## Principles
- 🔴 **黑盒执行**：把被测环境当**不透明黑盒**，穿 UI 验收，**不读 dev 源码/flow**。脚本编写期用 `webapp-testing` 读**运行时 DOM** 拿选择器 = 看用户可见渲染结果（黑盒，允许）；禁读业务逻辑源码反推预期。
- **env-gated**：本节点硬依赖被测环境 URL + 浏览器（`kdev-ui-autotest` STEP 0 需 `recon/menu_list.md` + `webapp-testing` 实测）。env 缺失 → 写 `--status blocked --reason 无被测环境`，编排不强跑。
- 第零原则：脚本目的是发现 BUG，不是刷通过率。
- 只对自家编排负责（硬规5）。

## Critical Actions
- 读上一棒设计交付（同 slug）：`python3 -m kdev_core handoff-read test-exec-flow <slug> --employee test-engineer --node n3-merge` 取 test-cases.md。
- 取被测环境 URL（运行时输入，编排/测试人员提供）。
- 调 `kdev-ui-autotest:kdev-ui-autotest` + `kdev-env-recon` / `webapp-testing`：实测菜单/弹窗、写 Playwright+pytest 脚本、跑测、归档四件套到 `ui-results`。
- 自验：用例覆盖、失败有诊断、四件套齐全。
- 完成 → 回编排，进 n1-coverage-review（发函评审专家·测试覆盖）。

## Capabilities
- `kdev-ui-autotest:kdev-ui-autotest` — Playwright+pytest+Element-Plus UI 自动化规范。
- `kdev-env-recon` / `webapp-testing` — 被测环境实测前置 + 运行时 DOM 真值。
- 输入 test-cases.md + 被测环境 URL；产物 ui-results。env-gated。
- 运行时模型暂 Opus（L1 flow-config 可配）。
````

- [ ] **Step 7: 跑测试确认通过**

Run: `cd plugins/kdev-team && python3 -m pytest tests/test_agents.py -q -k test_engineer`
Expected: PASS（5 passed）

- [ ] **Step 8: Commit**

```bash
cd /home/lyadmin/Projects/kdev-agents/.claude/worktrees/feat+test-engineer
git add plugins/kdev-team/agents/test-engineer-*.md plugins/kdev-team/tests/test_agents.py
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-team): test-engineer 4 agent(编排+测试点/用例/UI) + 黑盒独立硬规 + 测试"
```

---

### Task A3: staff.yml test-engineer 条目 + test_staff 追加

**Files:**
- Modify: `staff.yml`（追加 test-engineer 条目，多 flow `node_tables`）
- Modify: `tests/test_staff.py`

- [ ] **Step 1: 写失败测试** — 在 `tests/test_staff.py` 顶部 import 后加 `KT = Path(__file__).resolve().parents[1]`（若已有等价常量则复用），并追加：

```python
def test_test_engineer_entry():
    d = yaml.safe_load(STAFF.read_text(encoding="utf-8"))
    emp = d["employees"]["test-engineer"]
    assert emp["display"] == "测试工程师"
    assert emp["kind"] == "flow-owner"
    assert emp["flow_skill"] is None
    assert "node_table" not in emp, "多 flow flow-owner 用 node_tables（复数）"
    nt = emp["node_tables"]
    assert set(nt) == {"test-design-flow", "test-exec-flow"}
    assert emp["default_flow"] == "test-design-flow"
    KT = Path(__file__).resolve().parents[1]
    for path in nt.values():
        assert (KT / path).exists(), f"node_tables 路径不存在: {path}"
    assert len(emp["agents"]) == 4
    for a in emp["agents"]:
        assert (AGENTS / f"{a}.md").exists(), f"花名册引用的 agent 不存在: {a}"


def test_every_flow_owner_has_one_table_kind_callee_has_dispatch():
    d = yaml.safe_load(STAFF.read_text(encoding="utf-8"))["employees"]
    for fid, emp in d.items():
        if emp["kind"] == "flow-owner":
            has_single = "node_table" in emp
            has_multi = "node_tables" in emp
            assert has_single ^ has_multi, f"{fid}: flow-owner 须恰有 node_table 或 node_tables 之一"
            assert "dispatch_table" not in emp, f"{fid}: flow-owner 不应有 dispatch_table"
        elif emp["kind"] == "callee":
            assert "dispatch_table" in emp
            assert "node_table" not in emp and "node_tables" not in emp
```

并在 `test_kind_discriminator_on_all_employees` 里追加一行：

```python
    assert emps["test-engineer"]["kind"] == "flow-owner"
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd plugins/kdev-team && python3 -m pytest tests/test_staff.py -q`
Expected: FAIL（`KeyError: 'test-engineer'`）

- [ ] **Step 3: 改 `staff.yml`** — 在 `req-architect:` 条目后、`reviewer:` 条目前插入（注意头注释已说明 callee；这里是 flow-owner 多 flow 变体，加一句行内注释）：

```yaml
  test-engineer:
    display: 测试工程师
    kind: flow-owner
    flow_skill: null                 # 方法论分散在 kdev-test-points/cases/ui-autotest 能力 skill，无统一 flow-skill
    node_tables:                     # 多 flow flow-owner：2 个 relay flow（同 slug 接力 baton）。dev/req 仍用 node_table 单数
      test-design-flow: orchestration/test-engineer.design.node-table.yml
      test-exec-flow:   orchestration/test-engineer.exec.node-table.yml
    default_flow: test-design-flow   # driver 默认入口（黑盒设计，无 env、永远可跑）
    runtime_model: opus
    agents:
      - test-engineer-orchestrator
      - test-engineer-points
      - test-engineer-cases
      - test-engineer-ui
```

- [ ] **Step 4: 跑测试确认通过**

Run: `cd plugins/kdev-team && python3 -m pytest tests/test_staff.py -q`
Expected: PASS（全部，含原 dev/req/reviewer 用例不回归）

- [ ] **Step 5: Commit**

```bash
cd /home/lyadmin/Projects/kdev-agents/.claude/worktrees/feat+test-engineer
git add plugins/kdev-team/staff.yml plugins/kdev-team/tests/test_staff.py
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-team): staff.yml test-engineer 条目(node_tables 双flow) + flow-owner 不变量测试"
```

---

## Phase B — reviewer 接线（test-design / test-coverage）

### Task B1: 2 个 standards 文档 + dispatch CAP_STANDARDS 校验

**Files:**
- Create: `standards/reviewer/测试设计评审.md`、`standards/reviewer/测试覆盖评审.md`
- Modify: `tests/test_reviewer_dispatch.py`（`CAP_STANDARDS` 追加 2 项）

- [ ] **Step 1: 写失败测试** — 在 `tests/test_reviewer_dispatch.py` 改 `CAP_STANDARDS`：

```python
CAP_STANDARDS = ["SR需求评审", "用户故事评审", "原型评审", "方案架构评审", "代码质量评审", "安全评审",
                 "测试设计评审", "测试覆盖评审"]
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd plugins/kdev-team && python3 -m pytest tests/test_reviewer_dispatch.py::test_each_cap_standards_has_dimensions_and_threshold -q`
Expected: FAIL（缺 standards: 测试设计评审）

- [ ] **Step 3: 创建 `standards/reviewer/测试设计评审.md`**（照 代码质量评审.md 范本）：

````markdown
# 测试设计评审标准（cap: test-design）

> **硬规（启动即执行）**：评审 agent 启动须先 `recall(scope=/staff/reviewer, subject:review:test-design)` 召回测试设计评审历史校准，再据本标准打分（记忆底座 v1.0 §5.2）。
> **共用骨架**：百分制 schema / 双重通过条件 / 🔴🟡⚪ 分级 / 评分表输出格式 / 评审循环，一律遵循 [通用评分模板.md](通用评分模板.md)。
> **黑盒原则**：测试设计应追溯需求/原型（非源码）；评审锚点用需求/用户故事，不以实现代码为准。

---

## 评审对象
- **被评产物**：`test-points.md` + `test-cases.md`（测试工程师 test-design-flow 设计产出）。
- **caller gate**：`test-engineer:g-test-design-review`。
- **上游锚点**：需求文档 / 用户故事 / 原型图（黑盒来源）。

---

## 评分维度（4 维 × 25 = 100）

| 维度 | 满分 | checklist |
|---|---|---|
| **需求覆盖完整性** | 25 | □ 测试点↔用户故事/需求双向可追溯 □ 无遗漏需求 □ 无悬空测试点 □ RTM 完整 |
| **用例设计质量** | 25 | □ 边界/等价类覆盖 □ 异常/负测路径 □ 状态/组合合理 □ 高风险点有针对性用例 |
| **可执行 + 可验证** | 25 | □ 用例自含、前置/步骤/数据齐全 □ 预期明确、断言可机器跑 □ 自动化标记(UI/API)合理 □ 编号确定 |
| **与需求/原型一致** | 25 | □ 无擅自加戏(超需求) □ 无冗余重复用例 □ 与原型交互一致 □ (按需)29119 类规范 |

---

## 阈值
- **通过阈值 = 85**（设计缺陷直接放大成漏检）。
- 双重通过条件：`通过 = 总分 ≥ 85 AND 🔴阻断 = 0`。

---

## 问题分级（test-design 专属判定示例，标准见通用模板 §3）
- 🔴 **阻断**：关键需求/用户故事零对应测试 / 用例无法执行 / 测试逻辑错误致漏检 / 永真断言（假断言造假）。
- 🟡 **重要**：边界/异常路径遗漏(有质量风险) / 用例描述不清无法复现 / 与需求偏差(不致漏检) / 追溯缺口。
- ⚪ **轻微**：命名/格式 / 冗余用例 / 非关键路径补充建议。

---

## 评分表
输出 `handoffs/reviewer/g-test-design-review.test-design.score.md`，格式照 [通用评分模板.md §4](通用评分模板.md)：

```yaml
cap: test-design
target: [test-points.md, test-cases.md]
total: 88/100
dimensions:
  - {name: 需求覆盖完整性, score: 23/25}
  - {name: 用例设计质量,   score: 21/25, issues: [🟡 边界用例缺...]}
  - {name: 可执行+可验证,  score: 22/25}
  - {name: 与需求/原型一致, score: 22/25}
issues:
  - {level: 🟡重要, file: test-points.md, line: 30, desc: 边界等价类遗漏, suggest: 补 BVA 用例}
verdict: PASS        # total≥85 AND 🔴=0
```
````

- [ ] **Step 4: 创建 `standards/reviewer/测试覆盖评审.md`**（照范本）：

````markdown
# 测试覆盖评审标准（cap: test-coverage）

> **硬规（启动即执行）**：评审 agent 启动须先 `recall(scope=/staff/reviewer, subject:review:test-coverage)` 召回测试覆盖评审历史校准，再据本标准打分。
> **共用骨架**：百分制 schema / 双重通过条件 / 🔴🟡⚪ 分级 / 评分表输出格式 / 评审循环，一律遵循 [通用评分模板.md](通用评分模板.md)。

---

## 评审对象
- **被评产物**：`ui-results`（Playwright+pytest 跑测结果四件套）+ 覆盖报告（coverage-report）。
- **caller gate**：`test-engineer:g-test-coverage-review`。
- **上游锚点**：`test-cases.md` / 需求关键路径（覆盖应对需求，非对代码刷率）。

---

## 评分维度（4 维 × 25 = 100）

| 维度 | 满分 | checklist |
|---|---|---|
| **行/分支覆盖率** | 25 | □ 量化覆盖率达标 □ 无大块未覆盖 □ 覆盖报告可信(非估算) |
| **关键路径 + 核心业务覆盖** | 25 | □ 主流程全覆盖 □ 核心业务场景/边界场景有测 □ 高风险功能优先覆盖 |
| **回归覆盖** | 25 | □ 变更面有 test 护住 □ 既有功能未被破坏的回归用例 |
| **测试健壮性** | 25 | □ 无空跑/注释假断言 □ 无 flaky(随机失败)未治 □ 失败有诊断 □ 断言真有效 |

---

## 阈值
- **通过阈值 = 80**。
- 双重通过条件：`通过 = 总分 ≥ 80 AND 🔴阻断 = 0`。

---

## 问题分级（test-coverage 专属判定示例，标准见通用模板 §3）
- 🔴 **阻断**：核心路径零覆盖 / 测试造假(空跑、注释断言充数) / 覆盖报告伪造。
- 🟡 **重要**：覆盖率明显不足 / flaky 未治理 / 回归缺口(变更面无 test)。
- ⚪ **轻微**：非关键路径补充建议 / 报告格式。

---

## 评分表
输出 `handoffs/reviewer/g-test-coverage-review.test-coverage.score.md`，格式照 [通用评分模板.md §4](通用评分模板.md)：

```yaml
cap: test-coverage
target: [ui-results, coverage-report]
total: 83/100
dimensions:
  - {name: 行/分支覆盖率, score: 20/25}
  - {name: 关键路径+核心业务覆盖, score: 22/25}
  - {name: 回归覆盖, score: 21/25}
  - {name: 测试健壮性, score: 20/25, issues: [🟡 1 个 flaky 用例]}
issues:
  - {level: 🟡重要, file: ui-results/RUN_SUMMARY.md, line: 0, desc: 1 用例随机失败, suggest: 加显式等待}
verdict: PASS        # total≥80 AND 🔴=0
```
````

- [ ] **Step 5: 跑测试确认通过**

Run: `cd plugins/kdev-team && python3 -m pytest tests/test_reviewer_dispatch.py::test_each_cap_standards_has_dimensions_and_threshold -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
cd /home/lyadmin/Projects/kdev-agents/.claude/worktrees/feat+test-engineer
git add plugins/kdev-team/standards/reviewer/测试设计评审.md \
        plugins/kdev-team/standards/reviewer/测试覆盖评审.md \
        plugins/kdev-team/tests/test_reviewer_dispatch.py
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-team): reviewer 测试设计/测试覆盖 standards(4维×25, 阈值85/80)"
```

---

### Task B2: 2 个 reviewer-`<cap>` agent + test_agents reviewer 列表 7→9

**Files:**
- Create: `agents/reviewer-test-design.md`、`agents/reviewer-test-coverage.md`
- Modify: `tests/test_agents.py`（`REVIEWER_AGENTS` 7→9 + read-only 列表）

- [ ] **Step 1: 写失败测试** — 在 `tests/test_agents.py` 改 `REVIEWER_AGENTS` 加 2 项 + `test_cap_reviewers_are_read_only` 列表加 2 项：

```python
REVIEWER_AGENTS = [
    "reviewer-orchestrator", "reviewer-sr", "reviewer-story",
    "reviewer-prototype", "reviewer-design", "reviewer-code", "reviewer-security",
    "reviewer-test-design", "reviewer-test-coverage",
]
```

并把 `test_all_7_reviewer_agents_exist` 函数名与内部无关（它只遍历 REVIEWER_AGENTS，自动变 9）。在 `test_cap_reviewers_are_read_only` 的列表追加：

```python
    for a in ["reviewer-sr", "reviewer-story", "reviewer-prototype",
              "reviewer-design", "reviewer-code", "reviewer-security",
              "reviewer-test-design", "reviewer-test-coverage"]:
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd plugins/kdev-team && python3 -m pytest tests/test_agents.py -q -k reviewer`
Expected: FAIL（缺 agent: reviewer-test-design）

- [ ] **Step 3: 创建 `agents/reviewer-test-design.md`**（照 reviewer-code.md 范本；model: opus）：

````markdown
---
name: reviewer-test-design
description: 评审专家·测试设计评审能力 — 只读评 test-points.md + test-cases.md，对应 caller test-engineer:g-test-design-review。按 测试设计评审.md 4 维度（需求覆盖/用例质量/可执行可验证/与需求一致）打百分制分、标 🔴/🟡/⚪、出评分表。阈值 85。Use when reviewer-orchestrator fan-out 测试设计评审能力。
model: opus
---
# 测试设计评审能力（reviewer-test-design）

## Identity
评审专家的「测试设计评审」能力，对应 caller gate `test-engineer:g-test-design-review`。被 `reviewer-orchestrator` fan-out 调用，**只读评** `test-points.md` + `test-cases.md`（测试工程师 test-design-flow 黑盒设计产出），按 standards 维度打百分制分、出评分表回编排。

## Principles
- **只读、不改产物**（守生产者隔离）：发现问题只出分级建议，修复是被评审员工（test-engineer）的事。无 Write/Edit 改测试产物。
- **黑盒锚需求**：评审以需求/用户故事/原型为锚（非源码），核测试设计是否独立覆盖需求。
- **百分制 + 双重通过条件**：按 `测试设计评审.md` 4 维度打 0–100；`通过 = total≥85 AND 🔴阻断=0`。
- **建议须引证据**：每 issue 标 🔴/🟡/⚪ + 锚点（file+line），不空泛断言。
- **历史校准**：启动即 `recall(/staff/reviewer, subject:review:test-design)` 校准尺度防漂移。

## Critical Actions
1. **Read 产物 + standards + recall**：Read `test-points.md` + `test-cases.md`（路径来自 request）+ `standards/reviewer/测试设计评审.md` + 上游需求/用户故事锚点；启动先 `recall(scope=/staff/reviewer, subject:review:test-design)`。
2. **按维度打分**：4 维 × 25——①需求覆盖完整性 ②用例设计质量 ③可执行+可验证 ④与需求/原型一致。total = Σ 维度。
3. **出评分表**（spec §4.2 schema）：写 `handoffs/reviewer/g-test-design-review.test-design.score.md`，含 `cap/target/total/dimensions/issues/verdict`；verdict 由双重通过条件机械推出。
4. **不改产物、回编排**：评分表写完即返回 `reviewer-orchestrator`。

## Capabilities
- standards：`standards/reviewer/测试设计评审.md`（共用骨架见 `通用评分模板.md`）。
- 评对象：`test-points.md` + `test-cases.md`（caller `test-engineer:g-test-design-review`）。
- 评分维度（4 维 × 25）：需求覆盖完整性 / 用例设计质量 / 可执行+可验证 / 与需求原型一致。
- 阈值 **85**；🔴 = 关键需求零对应测试 / 用例无法执行 / 假断言造假。
````

- [ ] **Step 4: 创建 `agents/reviewer-test-coverage.md`**（model: opus）：

````markdown
---
name: reviewer-test-coverage
description: 评审专家·测试覆盖评审能力 — 只读评 ui-results + 覆盖报告，对应 caller test-engineer:g-test-coverage-review。按 测试覆盖评审.md 4 维度（行/分支覆盖/关键路径/回归/健壮性）打百分制分、标 🔴/🟡/⚪、出评分表。阈值 80。Use when reviewer-orchestrator fan-out 测试覆盖评审能力。
model: opus
---
# 测试覆盖评审能力（reviewer-test-coverage）

## Identity
评审专家的「测试覆盖评审」能力，对应 caller gate `test-engineer:g-test-coverage-review`。被 `reviewer-orchestrator` fan-out 调用，**只读评** `ui-results`（跑测四件套）+ 覆盖报告（test-exec-flow 执行产出），按 standards 维度打百分制分、出评分表回编排。

## Principles
- **只读、不改产物**（守生产者隔离）：发现问题只出分级建议，修复是被评审员工（test-engineer）的事。无 Write/Edit 改测试产物。
- **覆盖锚需求**：覆盖应对需求关键路径，不以"对代码刷率"为目的；核测试是否真发现 BUG（第零原则）。
- **百分制 + 双重通过条件**：按 `测试覆盖评审.md` 4 维度打 0–100；`通过 = total≥80 AND 🔴阻断=0`。
- **建议须引证据**：每 issue 标 🔴/🟡/⚪ + 锚点，不空泛断言。
- **历史校准**：启动即 `recall(/staff/reviewer, subject:review:test-coverage)` 校准尺度防漂移。

## Critical Actions
1. **Read 产物 + standards + recall**：Read `ui-results` + 覆盖报告（路径来自 request）+ `standards/reviewer/测试覆盖评审.md` + 上游 `test-cases.md`/需求关键路径锚点；启动先 `recall(scope=/staff/reviewer, subject:review:test-coverage)`。
2. **按维度打分**：4 维 × 25——①行/分支覆盖率 ②关键路径+核心业务覆盖 ③回归覆盖 ④测试健壮性(无空跑/假断言/flaky)。total = Σ 维度。
3. **出评分表**：写 `handoffs/reviewer/g-test-coverage-review.test-coverage.score.md`，含 `cap/target/total/dimensions/issues/verdict`；verdict 由双重通过条件机械推出。
4. **不改产物、回编排**：评分表写完即返回 `reviewer-orchestrator`。

## Capabilities
- standards：`standards/reviewer/测试覆盖评审.md`（共用骨架见 `通用评分模板.md`）。
- 评对象：`ui-results` + 覆盖报告（caller `test-engineer:g-test-coverage-review`）。
- 评分维度（4 维 × 25）：行/分支覆盖率 / 关键路径+核心业务覆盖 / 回归覆盖 / 测试健壮性。
- 阈值 **80**；🔴 = 核心路径零覆盖 / 测试造假 / 覆盖报告伪造。
````

- [ ] **Step 5: 跑测试确认通过**

Run: `cd plugins/kdev-team && python3 -m pytest tests/test_agents.py -q -k reviewer`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
cd /home/lyadmin/Projects/kdev-agents/.claude/worktrees/feat+test-engineer
git add plugins/kdev-team/agents/reviewer-test-design.md \
        plugins/kdev-team/agents/reviewer-test-coverage.md \
        plugins/kdev-team/tests/test_agents.py
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-team): reviewer-test-design/test-coverage 评审能力 agent(callee 只读)"
```

---

### Task B3: dispatch-table +2 cap + reviewer-orchestrator 路由 +2 + staff reviewer agents 7→9

**Files:**
- Modify: `orchestration/reviewer.dispatch-table.yml`
- Modify: `agents/reviewer-orchestrator.md`（Capabilities 路由表 +2 行）
- Modify: `staff.yml`（reviewer `agents` 7→9）
- Modify: `tests/test_reviewer_dispatch.py`（`EXPECTED_CAPS`→8 + caller_gate/review_gates 扩展加载 test-engineer node-table）
- Modify: `tests/test_staff.py`（`test_reviewer_callee_entry` 的 `len(agents)==7`→9）

- [ ] **Step 1: 写失败测试** — 改 `tests/test_reviewer_dispatch.py`：

  (a) `EXPECTED_CAPS` 改为 8：
```python
EXPECTED_CAPS = {"sr", "story", "prototype", "design", "code", "security",
                 "test-design", "test-coverage"}
```
  (b) `test_dispatch_table_has_6_caps_with_schema` 重命名为 `test_dispatch_table_has_8_caps_with_schema`（断言体不变，靠 EXPECTED_CAPS）。
  (c) `test_caller_gate_refs_real_gates` 扩展 `known` 加载 test-engineer 双 node-table：
```python
def test_caller_gate_refs_real_gates():
    dev = yaml.safe_load(DEV_NT.read_text(encoding="utf-8"))["gate_specs"]
    req = yaml.safe_load(REQ_NT.read_text(encoding="utf-8"))["gate_specs"]
    te_d = yaml.safe_load((ROOT / "orchestration/test-engineer.design.node-table.yml").read_text(encoding="utf-8"))["gate_specs"]
    te_e = yaml.safe_load((ROOT / "orchestration/test-engineer.exec.node-table.yml").read_text(encoding="utf-8"))["gate_specs"]
    known = ({f"dev-engineer:{g}" for g in dev} | {f"req-architect:{g}" for g in req}
             | {f"test-engineer:{g}" for g in te_d} | {f"test-engineer:{g}" for g in te_e})
    for c in _dt()["capabilities"]:
        for cg in c["caller_gate"]:
            assert cg in known, f"{c['cap']} 引用了不存在的 caller_gate: {cg}"
```
  (d) `test_review_gates_covered_by_some_cap` 同样把 test-engineer 的 reviewer-expert review gate 纳入 `review_gates`：
```python
def test_review_gates_covered_by_some_cap():
    specs_by_emp = {
        "dev-engineer": yaml.safe_load(DEV_NT.read_text(encoding="utf-8"))["gate_specs"],
        "req-architect": yaml.safe_load(REQ_NT.read_text(encoding="utf-8"))["gate_specs"],
        "test-engineer": {
            **yaml.safe_load((ROOT / "orchestration/test-engineer.design.node-table.yml").read_text(encoding="utf-8"))["gate_specs"],
            **yaml.safe_load((ROOT / "orchestration/test-engineer.exec.node-table.yml").read_text(encoding="utf-8"))["gate_specs"],
        },
    }
    review_gates = {
        f"{emp}:{g}" for emp, specs in specs_by_emp.items()
        for g, s in specs.items()
        if s["kind"] == "review" and s.get("reviewer") != "self"
    }
    claimed = set()
    for c in _dt()["capabilities"]:
        claimed |= set(c["caller_gate"])
    missing = review_gates - claimed
    assert not missing, f"这些 review gate 没有 cap 认领: {missing}"
```

  改 `tests/test_staff.py` 的 `test_reviewer_callee_entry`：`assert len(emp["agents"]) == 9`（注释改 `# orchestrator + 8 cap`）。

- [ ] **Step 2: 跑测试确认失败**

Run: `cd plugins/kdev-team && python3 -m pytest tests/test_reviewer_dispatch.py tests/test_staff.py -q`
Expected: FAIL（EXPECTED_CAPS 不匹配 / caller_gate 引用不存在 / reviewer agents 数 7≠9）

- [ ] **Step 3: 改 `orchestration/reviewer.dispatch-table.yml`** — 在 security 行后追加 2 行，并改 deferred 注释（移除 test-design/test-coverage）：

```yaml
  - {cap: test-design,   agent: reviewer-test-design,   standards: standards/reviewer/测试设计评审.md, threshold: 85, target: [test-points.md, test-cases.md], caller_gate: [test-engineer:g-test-design-review]}
  - {cap: test-coverage, agent: reviewer-test-coverage, standards: standards/reviewer/测试覆盖评审.md, threshold: 80, target: [ui-results, coverage-report],  caller_gate: [test-engineer:g-test-coverage-review]}
# deferred（随 caller 员工建成补，本期不建 agent）:
#   need-direction / iteration-split  ← req 须先加 R1.5/R2.5 gate
# 扩展 6（默认关，留接口）: deploy / perf / docs / compliance / observability / a11y
```

- [ ] **Step 4: 改 `agents/reviewer-orchestrator.md`** — Capabilities 路由表（caller gate → cap）追加 2 行：

```
| test-engineer:g-test-design-review   | test-design   | `kdev-team:reviewer-test-design`   | 85 |
| test-engineer:g-test-coverage-review | test-coverage | `kdev-team:reviewer-test-coverage` | 80 |
```

- [ ] **Step 5: 改 `staff.yml`** — reviewer 条目 `agents` 列表末尾追加 2 项：

```yaml
      - reviewer-test-design
      - reviewer-test-coverage
```

- [ ] **Step 6: 跑测试确认通过**

Run: `cd plugins/kdev-team && python3 -m pytest tests/test_reviewer_dispatch.py tests/test_staff.py -q`
Expected: PASS（全绿）

- [ ] **Step 7: Commit**

```bash
cd /home/lyadmin/Projects/kdev-agents/.claude/worktrees/feat+test-engineer
git add plugins/kdev-team/orchestration/reviewer.dispatch-table.yml \
        plugins/kdev-team/agents/reviewer-orchestrator.md \
        plugins/kdev-team/staff.yml \
        plugins/kdev-team/tests/test_reviewer_dispatch.py \
        plugins/kdev-team/tests/test_staff.py
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-team): dispatch-table +test-design/test-coverage 2 cap + orchestrator 路由 + staff reviewer 7→9 (核心10余2)"
```

---

## Phase C — driver 参考文档接线

### Task C1: node-agent-routing + gate-decision-logic + SKILL §2.4ter + wiring 测试

**Files:**
- Modify: `skills/kdev-flow-driver/references/node-agent-routing.md`（+test-engineer 路由段 + reviewer 发函 dispatch 补 2 cap）
- Modify: `skills/kdev-flow-driver/references/gate-decision-logic.md`（+test-engineer gate 判据段）
- Modify: `skills/kdev-flow-driver/SKILL.md`（§2.4ter 生产方表 +test-engineer + §1.2 node_tables 注记 + 黑盒硬规）
- Create: `tests/test_test_engineer_wiring.py`

- [ ] **Step 1: 写失败测试** — 创建 `tests/test_test_engineer_wiring.py`：

```python
from pathlib import Path

KT = Path(__file__).resolve().parents[1]
REF = KT / "skills/kdev-flow-driver/references"
NAR = REF / "node-agent-routing.md"
GDL = REF / "gate-decision-logic.md"
SKILL = KT / "skills/kdev-flow-driver/SKILL.md"
ORCH = KT / "agents/reviewer-orchestrator.md"


def test_node_routing_has_test_engineer_section():
    t = NAR.read_text(encoding="utf-8")
    assert "test-engineer" in t
    assert "kdev-team:test-engineer-points" in t
    assert "黑盒" in t and ("禁读" in t or "不读" in t)


def test_node_routing_reviewer_dispatch_lists_test_caps():
    t = NAR.read_text(encoding="utf-8")
    assert "test-design" in t and "test-coverage" in t


def test_gate_logic_has_test_engineer_gates():
    t = GDL.read_text(encoding="utf-8")
    assert "g-test-design-review" in t and "g-test-coverage-review" in t
    assert "黑盒" in t


def test_skill_24ter_lists_test_engineer_producer():
    t = SKILL.read_text(encoding="utf-8")
    assert "test-engineer" in t and "黑盒" in t


def test_reviewer_orchestrator_routes_test_caps():
    t = ORCH.read_text(encoding="utf-8")
    assert "test-design" in t and "test-coverage" in t
    assert "test-engineer:g-test-design-review" in t
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd plugins/kdev-team && python3 -m pytest tests/test_test_engineer_wiring.py -q`
Expected: FAIL（NAR/GDL/SKILL 无 test-engineer 内容；`test_reviewer_orchestrator_routes_test_caps` 已在 B3 满足，其余失败）

- [ ] **Step 3: 改 `node-agent-routing.md`** — 在 req-architect 段后追加 test-engineer 段（含黑盒硬规 + 双 flow 路由），并在「reviewer 发函 dispatch」段适用范围补 test-engineer + 列 test-design/test-coverage：

```markdown
---

# test-engineer（测试工程师）test-flow 路由

适用于 `test-engineer` 员工的双 flow（`node_tables`：test-design-flow / test-exec-flow）。

> 🔴 **黑盒独立硬规**：测试设计（n0-points/n1-cases）只读「需求文档 + 原型图 + 用户故事」，**禁读业务源码 `src/`、禁读 dev-engineer handoff/flow**。读代码设计测试 = 代码自测。dev-engineer ⊥ test-engineer 并行独立、流程不延续。UI 自动化脚本期读运行时 DOM 拿选择器(黑盒)允许，不读源码逻辑。

## 路由映射（test-design-flow，无 env）
| 节点 id | subagent_type | 干什么 | 需传上下文 |
|---|---|---|---|
| n0-points | `kdev-team:test-engineer-points` | 读需求/原型(禁读src)设计测试点 → test-points.md；**先** `handoff-read test-design-flow <slug> --employee req-architect --node n8-merge` 取 SR/用户故事/原型，缺失则裸任务 | 需求文档/原型路径, 产物根=`<ws>/.kdev/features/<slug>/handoffs/test-engineer/`, 上游 req-architect 交付(若同 slug) |
| n1-cases | `kdev-team:test-engineer-cases` | 1:1 渲染 → test-cases.md | test-points.md 路径, 产物根 |
| n3-merge | 编排自做（不派）| handoff-write 设计交付(test-points/test-cases) | — |

## 路由映射（test-exec-flow，env-gated）
| 节点 id | subagent_type | 干什么 | 需传上下文 |
|---|---|---|---|
| n0-ui-auto | `kdev-team:test-engineer-ui` | 读 test-cases + 被测环境 URL → Playwright+pytest → ui-results | test-cases.md(handoff-read n3-merge), **被测环境 URL(运行时输入)**, recon/menu_list.md, 产物根 |
| n2-report | 编排自做（不派）| handoff-write 测试报告(ui-results/覆盖) | — |

## Gate 节点（n2-design-review / n1-coverage-review）
均 `reviewer: reviewer-expert`，按「reviewer 发函 dispatch」段发函 `kdev-team:reviewer-orchestrator`（cap=test-design / test-coverage）。无 env 时 exec-flow 不 start-run，止于 design 交付。
```

并在文件末「reviewer 发函 dispatch」段的「适用范围」句补 test-engineer，且在 caller→cap 说明处加一句：`test-engineer:g-test-design-review → test-design`、`test-engineer:g-test-coverage-review → test-coverage`。

- [ ] **Step 4: 改 `gate-decision-logic.md`** — 文件末尾追加 test-engineer 段：

```markdown
---

# test-engineer（测试工程师）gate 判据

适用于 `test-engineer` 双 flow。两 review gate 均**发函评审专家**（reviewer-expert），按「Reviewer-Expert Gate（已兑现）」段 6 步发函，FAIL 有界回流（cap=3 → blocked 升人）。

> 🔴 **黑盒独立**：测试设计 gate 评的是「测试是否独立覆盖需求」，锚点用需求/原型/用户故事，**非源码**；评审专家不以实现代码为准绳。

| Gate | flow / 节点 | Kind | Reviewer | 处理 |
|---|---|---|---|---|
| g-test-design-review | design / n2-design-review | review | reviewer-expert | 发函 cap=test-design（阈值 85）；FAIL→回流 n0-points 重设计 |
| g-test-coverage-review | exec / n1-coverage-review | review | reviewer-expert | 发函 cap=test-coverage（阈值 80）；FAIL→回流 n0-ui-auto 重跑 |

**追加到「Reviewer-Expert Gate（已兑现）」总表**：
| 员工:Gate | 评审对象 | 派给（in-scope cap）|
|---|---|---|
| test-engineer:g-test-design-review | test-points.md + test-cases.md | test-design |
| test-engineer:g-test-coverage-review | ui-results + 覆盖报告 | test-coverage |
```

- [ ] **Step 5: 改 `SKILL.md`** — (a) §2.4ter 生产方映射表追加 test-engineer 两棒 + 黑盒消费注记；(b) §1.2 读 staff.yml 处加一句多 flow flow-owner 注记：

  (a) §2.4ter「生产方 → 交付节点映射」表后追加：
```markdown
| `test-engineer` | `n3-merge`（design-flow）| test-points / test-cases（黑盒设计产出）|
| `test-engineer` | `n2-report`（exec-flow）| ui-results / 覆盖报告 |

> 🔴 **test-engineer 黑盒独立**：消费方=`handoff-read req-architect n8-merge` 取需求/原型作设计输入（缺失裸任务）；**显式不建 dev-engineer→test-engineer 边**——test 不读 dev 代码/flow，避免"代码自测"污染。被测环境 URL 是运行时输入（非 handoff 依赖）。
```

  (b) §1.2「读 staff.yml 路由」处 `node_table` 项后加一句：
```markdown
- **多 flow flow-owner**（如 test-engineer）：staff.yml 用 `node_tables`(复数 map：flow→table 路径) + `default_flow`，按要跑的 flow 取对应 table；单 flow 员工仍用 `node_table`(单数)。
```

- [ ] **Step 6: 跑测试确认通过**

Run: `cd plugins/kdev-team && python3 -m pytest tests/test_test_engineer_wiring.py tests/test_reviewer_wiring.py -q`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
cd /home/lyadmin/Projects/kdev-agents/.claude/worktrees/feat+test-engineer
git add plugins/kdev-team/skills/kdev-flow-driver/references/node-agent-routing.md \
        plugins/kdev-team/skills/kdev-flow-driver/references/gate-decision-logic.md \
        plugins/kdev-team/skills/kdev-flow-driver/SKILL.md \
        plugins/kdev-team/tests/test_test_engineer_wiring.py
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-team): driver 参考补 test-engineer 路由/gate判据/§2.4ter 生产方 + 黑盒硬规"
```

---

## Phase D — bump + 全绿 + 回写

### Task D1: bump kdev-team version + CHANGELOG

**Files:**
- Modify: `.claude-plugin/plugin.json`（version 0.7.0 → 0.8.0）
- Modify: `CHANGELOG.md`（prepend 0.8.0 条目）

- [ ] **Step 1: 改 `plugin.json`** — `"version": "0.7.0"` → `"version": "0.8.0"`。

- [ ] **Step 2: 改 `CHANGELOG.md`** — 顶部按现有格式 prepend：

```markdown
## 0.8.0 — 第 4 个数字员工：测试工程师 test-engineer + 评审专家测试维度补齐

- **test-engineer（flow-owner，多 flow）**：staff.yml `node_tables`(test-design-flow ⊥ test-exec-flow) + `default_flow`；4 agent（orchestrator + 测试点设计/用例渲染/UI自动化，call kdev-test-points/cases/ui-autotest）。
- 🔴 **黑盒独立硬规**：测试设计只读需求/原型禁读 src；dev-engineer ⊥ test-engineer 并行不延续（写进 orchestrator/points agent/routing/gate-decision-logic/SKILL §2.4ter）。
- **2 个 node-table**：design-flow（黑盒设计 6 节点 1 评审闸，无 env）+ exec-flow（对被测环境执行 5 节点 1 评审闸，env-gated）。
- **评审专家解锁 2 测试能力（核心 10 余 4 → 余 2）**：dispatch-table +test-design(85)/test-coverage(80)；reviewer-orchestrator 路由 +2；reviewer-test-design/test-coverage agent + 2 standards；staff reviewer agents 7→9。
- env 边界用拆 flow 表达（design 永远可跑 / exec 需被测环境 URL）；本期"建好 + 单测绿"，exec-flow 实跑待真实测试任务（诚实标注）。
- kdev-core 零改。依赖声明/packaging（装员工连带装 skill）defer 进 roadmap Q-018。
- 测试：test_test_engineer_orchestration + test_test_engineer_wiring 新增；staff/agents/reviewer_dispatch 扩展。
```

- [ ] **Step 3: 跑 manifest 测试确认通过**

Run: `cd plugins/kdev-team && python3 -m pytest tests/test_plugin_manifest.py -q`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
cd /home/lyadmin/Projects/kdev-agents/.claude/worktrees/feat+test-engineer
git add plugins/kdev-team/.claude-plugin/plugin.json plugins/kdev-team/CHANGELOG.md
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "chore(kdev-team): bump 0.8.0 — test-engineer 员工 + 评审测试 2 能力(核心10余2)"
```

---

### Task D2: 全套测试绿（kdev-team + kdev-core 无回归）

- [ ] **Step 1: kdev-team 全绿**

Run: `cd plugins/kdev-team && python3 -m pytest tests/ -q`
Expected: PASS（原 61 + 新增；0 failures）

- [ ] **Step 2: kdev-core 无回归（确认零改未破）**

Run: `cd plugins/kdev-core && python3 -m pytest -q`
Expected: PASS（原有全绿，kdev-core 未改）

- [ ] **Step 3: 若有失败 → 修复**（systematic-debugging；不改测试迁就 bug，除非测试本身假设过期）。修复后回 Step 1。

---

### Task D3: 回写 roadmap §1.5.8 + 阶段3 行

**Files:**
- Modify: `docs/framework/01-design/2026-06-06-01-数字员工整体设计路线图roadmap-v1.0.md`

- [ ] **Step 1: §1.5.8 backlog 加 done 行** — 在评审专家行后加：

```markdown
| ✅ **done · 第4员工/L3** | **测试工程师 test-engineer** | ✅ **done（kdev-team v0.8.0，2026-06-13）**：flow-owner 多 flow（`node_tables`：test-design-flow 黑盒设计⊥test-exec-flow 执行）+ 3 业务 agent（测试点/用例/UI，call kdev-test-points/cases/ui-autotest）+ 编排 doc；🔴 黑盒独立硬规（设计只读需求/原型禁读码，dev⊥test 不延续）；2 评审 gate 发函 reviewer-expert。**评审专家解锁 test-design(85)/test-coverage(80) → 核心 10 余 2**。kdev-core 零改。TDD 全绿。env：建好+单测绿，exec-flow 实跑待真实测试任务。依赖声明 defer Q-018 | [spec](../../superpowers/specs/2026-06-13-测试工程师test-engineer接入设计-design.md) · [plan](../../superpowers/plans/2026-06-13-测试工程师test-engineer-tdd实施.md) · Q-018 |
```

- [ ] **Step 2: §1.5 进度表「阶段3」行 + §2/§5.阶段3 概要** — 把「评审专家 6 能力」更新为「+测试工程师 → 核心 10 余 2」，措辞示例：在阶段3 行追加 ` · 测试工程师 done(kdev-team v0.8.0，核心10余2)`。

- [ ] **Step 3: Commit**

```bash
cd /home/lyadmin/Projects/kdev-agents/.claude/worktrees/feat+test-engineer
git add "docs/framework/01-design/2026-06-06-01-数字员工整体设计路线图roadmap-v1.0.md"
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "docs(roadmap): 测试工程师 done 回写 §1.5.8 + 阶段3(评审核心10余2)"
```

- [ ] **Step 4: G-004 提示** — 向用户提示：kdev-team 改了 agent/staff/version，**需刷 marketplace + 重启 session** 才能激活 `subagent_type: kdev-team:test-engineer-*` 直派（G-004）。

---

## 测试命令速查

```bash
cd /home/lyadmin/Projects/kdev-agents/.claude/worktrees/feat+test-engineer/plugins/kdev-team
python3 -m pytest tests/ -q                                  # kdev-team 全套
python3 -m pytest tests/test_test_engineer_orchestration.py -q   # 双 node-table
python3 -m pytest tests/test_test_engineer_wiring.py -q          # driver 参考接线
python3 -m pytest tests/test_staff.py tests/test_agents.py tests/test_reviewer_dispatch.py -q   # 受影响的既有测试
cd ../kdev-core && python3 -m pytest -q                      # 零改回归
```

---

## Self-Review（写完即查）

- **Spec 覆盖**：§2 形态→A3 · §3 双 node-table→A1 · §4 agent→A2 · §5 reviewer 接线→B1/B2/B3 · §6 §2.4ter→C1 · §7 env 边界(拆 flow/无 in-flow env 闸)→A1 节点设计+C1 注记 · §8 零改/测试→各 Task · §9 非目标(API defer / 不连 dev / packaging defer)→A1/C1 注释 + D1 CHANGELOG。✅ 全覆盖。
- **Placeholder**：无 TBD/TODO；每个 config/agent/standards/测试均给完整内容。✅
- **类型/命名一致**：node 名（n0-points/n1-cases/n2-design-review/n3-merge/n4-done；n0-ui-auto/n1-coverage-review/n2-report/n3-done）、gate id（g-test-design-review/g-test-coverage-review）、cap（test-design/test-coverage）、agent id（test-engineer-{orchestrator,points,cases,ui}、reviewer-test-{design,coverage}）、flow（test-design-flow/test-exec-flow）跨 Task 一致。✅
- **顺序约束**：B3 的 `test_caller_gate_refs_real_gates` 依赖 A1 node-table 存在——A 在 B 前，✅。
