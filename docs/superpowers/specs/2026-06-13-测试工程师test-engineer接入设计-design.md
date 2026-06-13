# 测试工程师（test-engineer）数字员工接入设计

- 日期：2026-06-13
- 分支：`feat/test-engineer`（worktree）
- 状态：design（待 writing-plans）
- 作者：ly + ly-AI
- 关联：
  - 员工能力蓝图 `docs/framework/01-design/_archive/2026-05-28-01-KDev数字员工架构-员工能力专项-v1.5.md` §员工3 + §5.1.3（T-flow）
  - 评审专家接入 `docs/superpowers/specs/2026-06-12-评审专家reviewer接入设计-design.md`（§test-design/test-coverage deferred）+ Q-016 / Q-017
  - 编排底座合稿 `docs/framework/01-design/2026-06-10-03-KDev数字员工-编排底座-合稿-v1.0.md` §2.1（feature-first）
  - 通用驱动 `plugins/kdev-team/skills/kdev-flow-driver/SKILL.md`（§2.4ter 跨员工交付 / §2.4quater 发函硬规）
  - 范本：dev-engineer / req-architect（flow-owner）+ reviewer（callee）

---

## 0. 决策摘要（Q-NNN，本 spec 固化）

| ID | 决策点 | 结论 |
|---|---|---|
| **Q-A 形态** | 员工形态 | **flow-owner**，但持 **2 个 node-table**（`node_tables` 复数 schema 扩展，向后兼容）：`test-design-flow` ⊥ `test-exec-flow` |
| **Q-B 能力数** | 业务能力数 | **3 个业务 agent**（测试点设计 / 用例渲染 / UI 自动化）；**API 自动化 deferred**（等 `kdev-api-autotest` 执行层 skill 建成） |
| **Q-C 黑盒独立** | 设计来源 + 与 dev 关系 | **测试黑盒独立硬规**：设计阶段只读「需求文档 + 原型图」，**禁读 `src/`**（防"代码自测"污染）；**dev-engineer ⊥ test-engineer 并行独立、流程不延续**（不同人、不同活，互不读对方 flow-state/代码） |
| **Q-D 接 reviewer** | 测试评审能力接法 | **2 个独立 review gate × 1 cap**：`g-test-design-review`→`test-design`(85)、`g-test-coverage-review`→`test-coverage`(80)；均发函 `reviewer-expert`，L1 可回退 `self` |
| **Q-E env 边界** | 被测环境依赖 | 用 **拆 flow** 表达：design-flow 永远可跑（无 env、无码）；exec-flow 仅当测试人员提供「被测环境 URL」时才 `start-run`。**建员工基础设施本步不需 env，仅真实测试任务的 exec-flow 才需** |

> 守 [G-008]（编排走通用 driver，不下放 orchestrator agent）、Q-008（执行留 flow / 编排=主控驱动）、kdev-core 零改（参 reviewer 接入）。

---

## 1. 集群拓扑与黑盒独立原则

### 1.1 拓扑：req → (dev ∥ test) 并行，dev 与 test 不连

```
req-architect (design-flow)
   产出: SR / AR / 用户故事 / 原型图   ── n8-merge handoff
        │
        ├──────────► dev-engineer (coding-flow)        读需求/方案 → 写代码 → 部署"被测环境"
        │                                              （test 绝不读它的代码/handoff/flow-state）
        │
        └──────────► test-engineer (test-design-flow)  读需求/原型 → 设计黑盒测试
                          产出: test-points.md / test-cases.md
                                   │ （同 slug 接力 baton，但同一员工内部）
                                   └──► test-engineer (test-exec-flow)  对"被测环境URL"跑黑盒UI自动化
                                          ▲ 被测环境URL = 运行时输入（测试人员提供；
                                            恰好可以是 dev 部署的 app，但 test 把它当不透明黑盒，
                                            穿 UI 验收，不读 dev 的源码/flow）
```

- **dev ⊥ test**：并行、独立。两者**都**独立消费 req-architect 的需求产物，但**互不读对方**。**不**在同一 slug 上把 test 建成 dev coding-flow 的延续 baton。
- **test 的设计上游 = req-architect 的需求/原型**（不是 dev 的代码）。
- test-design-flow → test-exec-flow 是**同一员工内部**的两棒接力（同 slug 新 baton），exec 读 design 产出的 `test-cases.md`。这与"dev⊥test"不冲突——它是 test 员工自己的两段工序。

### 1.2 两种使用模式（对应"测试人员可单独使用"）

- **独立模式（裸任务，主用）**：测试人员直接给一份「需求文档路径 + 原型图路径」，test-engineer 据此设计黑盒测试，无上游 handoff。
- **集成模式**：与 req-architect 同 feature slug 时，`handoff-read req-architect n8-merge` 取 SR/用户故事/原型作设计输入。
- 消费逻辑：先试 `handoff-read req-architect n8-merge`（同 slug）；报 `handoff status not found`（FlowStateError）→ 回退裸任务（吃直接给定的需求/原型）。**两模式都绝不读 dev-engineer**。

### 1.3 黑盒独立性硬规（核心原则）

> 🔴 **测试设计黑盒独立**：test-engineer 在**设计阶段**（测试点 / 用例）只读「需求文档 + 原型图 + 用户故事」，**禁读业务源码 `src/`、禁读 dev-engineer 的 handoff/flow-state**。理由：读代码设计测试 = "代码自测"，测试退化为复述实现、丧失独立发现缺陷的能力。
>
> **边界澄清**：UI 自动化**脚本编写期**用 `webapp-testing` 读**运行时 DOM** 拿选择器/定位 = 看"用户可见的渲染结果"（黑盒），**不算**读源码，允许；禁的是读业务逻辑源码来反推预期。

落地：写进 `test-engineer-orchestrator.md`（Principles）、`test-engineer-points.md`（Critical Actions）、`node-agent-routing.md`（test 段）、driver SKILL §2.4ter（test 消费方注记）。

---

## 2. 员工形态（staff.yml）

flow-owner，但首个**多 flow** flow-owner。对 staff schema 做**最小向后兼容扩展**：新增 `node_tables`（复数 map）+ `default_flow`，与现有 `node_table`（单数，dev/req 用）互斥并存。

```yaml
test-engineer:
  display: 测试工程师
  kind: flow-owner
  flow_skill: null                 # 方法论分散在 3 个能力 skill，无统一 flow-skill（同 reviewer 的 null 合法）
  node_tables:                     # ★ 多 flow flow-owner（dev/req 仍用单数 node_table，不改）
    test-design-flow: orchestration/test-engineer.design.node-table.yml
    test-exec-flow:   orchestration/test-engineer.exec.node-table.yml
  default_flow: test-design-flow   # driver 默认入口（黑盒设计，永远可跑、无 env）
  runtime_model: opus
  agents:
    - test-engineer-orchestrator   # 编排知识 doc（fallback；编排仍由顶层主控 driver 驱动，G-008）
    - test-engineer-points         # 测试点设计 → kdev-test-points（读需求/原型，禁读 src）
    - test-engineer-cases          # 用例渲染   → kdev-test-cases
    - test-engineer-ui             # UI 自动化  → kdev-ui-autotest（对被测环境，env-gated）
```

**schema 不变量（更新 `test_staff.py`）**：每个 flow-owner 有且仅有 `node_table`（单数）**或** `node_tables`（复数）之一；callee 两者都无（用 `dispatch_table`）。

---

## 3. 两个 node-table（L0 默认编排）

两表均 `max_retries: 3`、`terminal_fail: n-fail`，gate kind ∈ {review, decision, acceptance}，reviewer ∈ {self, reviewer-expert}（与现有引擎/测试约束一致）。

### 3.1 `orchestration/test-engineer.design.node-table.yml`（黑盒设计，无 env、无码）

```yaml
flow: test-design-flow
max_retries: 3
terminal_fail: n-fail
nodes:
  - {id: n0-points,        name: 测试点设计(读需求/原型,禁读src), kind: action, next: [n1-cases]}
  - {id: n1-cases,         name: 测试用例渲染(1:1 from points),   kind: action, next: [n2-design-review]}
  - {id: n2-design-review, name: 测试设计评审,                    kind: gate,   gate: g-test-design-review, next: [n3-merge, n0-points]}
  - {id: n3-merge,         name: 设计交付聚合(handoff-write),      kind: action, next: [n4-done]}
  - {id: n4-done,          name: 设计交付清点,                    kind: terminal, next: []}
  - {id: n-fail,           name: reflow 溢出终止(R2 sink；R3 评审 escalate 走 blocked 留原地), kind: terminal, next: []}

gate_specs:
  g-test-design-review: {kind: review, on_pass: n3-merge, on_reflow: n0-points, reviewer: reviewer-expert}
```

- `n0-points`：`test-engineer-points` 先 `handoff-read req-architect n8-merge`（缺失→裸任务），据需求/原型设计 `test-points.md`。**禁读 src**。
- `n2-design-review` 发函 reviewer-expert（cap=`test-design`，target=test-points.md + test-cases.md，阈值 85）。FAIL 回流 `n0-points`（重设计）。
- `n3-merge`：编排 `handoff-write test-design-flow <slug> --employee test-engineer --node n3-merge`，产物 test-points/test-cases，供 exec-flow + 下游读。

### 3.2 `orchestration/test-engineer.exec.node-table.yml`（对被测环境黑盒执行，env-gated）

```yaml
flow: test-exec-flow
max_retries: 3
terminal_fail: n-fail
nodes:
  - {id: n0-ui-auto,         name: UI自动化(读test-cases+被测环境URL),  kind: action, next: [n1-coverage-review]}
  - {id: n1-coverage-review, name: 测试覆盖评审,                        kind: gate,   gate: g-test-coverage-review, next: [n2-report, n0-ui-auto]}
  - {id: n2-report,          name: 测试报告聚合(handoff-write),         kind: action, next: [n3-done]}
  - {id: n3-done,            name: 测试执行清点,                        kind: terminal, next: []}
  - {id: n-fail,             name: reflow 溢出终止(R2 sink；R3 评审 escalate 走 blocked 留原地), kind: terminal, next: []}

gate_specs:
  g-test-coverage-review: {kind: review, on_pass: n2-report, on_reflow: n0-ui-auto, reviewer: reviewer-expert}
```

- `n0-ui-auto`：`test-engineer-ui` 读上一棒 `test-cases.md`（同 slug，`handoff-read test-engineer n3-merge`）+ 被测环境 URL，调 `kdev-ui-autotest`（Playwright+pytest）产 `ui-results`。
- `n1-coverage-review` 发函 reviewer-expert（cap=`test-coverage`，target=ui-results + 覆盖报告，阈值 80）。FAIL 回流 `n0-ui-auto`。
- **env 边界**：exec-flow 仅在测试人员提供被测环境 URL 时由编排 `start-run`（新 baton，同 slug）。无 env → 止于 design-flow 交付。
- **API 扩展点**：将来 `kdev-api-autotest` 建成，在 `n0-ui-auto` 与 `n1-coverage-review` 间插 `n?-api-auto` 节点 + `test-engineer-api` agent，不动其余。

### 3.3 不加 in-flow env 闸的理由

env 边界由"拆 flow"表达（design 永远可跑 / exec 才需 env），不在 node-table 内加 `g-env-check` decision gate——避免给 design-flow 引入它不需要的 env 概念，且 exec-flow 的启动判断本就在编排（start-run 前置）。

---

## 4. agent 清单（瘦 persona + 调 skill）

沿用范式：**业务 agent 调方法论 skill；orchestrator 调 CLI+派单不调 skill**。canonical id 全 ASCII，中文名只在 display/description。

| agent (canonical id) | 角色 | 调的 skill / 工具 | 黑盒约束 |
|---|---|---|---|
| `test-engineer-orchestrator` | 编排知识 doc（fallback）| kdev-core CLI + 派业务 agent + 发函 reviewer | 写黑盒独立硬规 |
| `test-engineer-points` | 测试点设计（n0-points）| `kdev-test-points:kdev-test-points` | 🔴 只读需求/原型，禁读 src |
| `test-engineer-cases` | 用例渲染（n1-cases）| `kdev-test-cases:kdev-test-cases` | 1:1 渲染 points，不重新设计 |
| `test-engineer-ui` | UI 自动化（exec n0-ui-auto）| `kdev-ui-autotest:kdev-ui-autotest` + `webapp-testing`/`kdev-env-recon` | 黑盒穿 UI；读 DOM 拿选择器允许，不读业务源码 |

`test-engineer-orchestrator.md` 的 Capabilities 表登记两 flow 的节点→业务 agent 路由（design: n0-points/n1-cases；exec: n0-ui-auto），gate 节点不派业务 agent（发函 reviewer 或自判）。

---

## 5. 接评审专家（reviewer callee，dispatch-table + 2 cap）

### 5.1 dispatch-table 补 2 行（`orchestration/reviewer.dispatch-table.yml`）

```yaml
- {cap: test-design,   agent: reviewer-test-design,   standards: standards/reviewer/测试设计评审.md, threshold: 85, target: [test-points.md, test-cases.md], caller_gate: [test-engineer:g-test-design-review]}
- {cap: test-coverage, agent: reviewer-test-coverage, standards: standards/reviewer/测试覆盖评审.md, threshold: 80, target: [ui-results, coverage-report],  caller_gate: [test-engineer:g-test-coverage-review]}
```
从 deferred 注释移除 test-design/test-coverage；保留 need-direction / iteration-split（仍卡 req-architect 加 R1.5/R2.5 gate）。**核心 10 余 4 → 余 2**。

### 5.2 reviewer-orchestrator.md Capabilities 路由表补 2 行

```
| test-engineer:g-test-design-review   | test-design   | kdev-team:reviewer-test-design   | 85 |
| test-engineer:g-test-coverage-review | test-coverage | kdev-team:reviewer-test-coverage | 80 |
```

### 5.3 staff.yml reviewer `agents`：7 → 9

追加 `reviewer-test-design` + `reviewer-test-coverage`（更新 `test_staff.py` 的 `len(agents)==7` → `9`）。

### 5.4 两个 standards（`standards/reviewer/`，4 维×25=100，照现有范式）

**测试设计评审.md（cap: test-design，阈值 85）**
| 维度 | 满分 | checklist 要点 |
|---|---|---|
| 需求覆盖完整性 | 25 | 测试点↔用户故事/需求双向追溯、无遗漏需求、无悬空测试点 |
| 用例设计质量 | 25 | 边界/等价类/异常/负测覆盖、组合合理 |
| 可执行+可验证 | 25 | 用例自含、预期明确、断言可机器跑、自动化标记合理 |
| 与需求/原型一致 | 25 | 无擅自加戏、无冗余、（按需）29119 类规范 |

🔴=关键需求零对应测试 / 用例无法执行 / 永真断言造假；🟡=边界遗漏(有质量风险)/描述不清；⚪=命名/冗余/格式。

**测试覆盖评审.md（cap: test-coverage，阈值 80）**
| 维度 | 满分 | checklist 要点 |
|---|---|---|
| 行/分支覆盖率 | 25 | 量化指标达标、无大块未覆盖 |
| 关键路径+核心业务覆盖 | 25 | 主流程/核心场景全覆盖 |
| 回归覆盖 | 25 | 变更面有 test 护住 |
| 测试健壮性 | 25 | 无空跑/注释假断言/flaky |

🔴=核心路径零覆盖 / 测试造假；🟡=覆盖率明显不足/flaky 未治；⚪=非关键补充建议。
两 standards 共用骨架引 `通用评分模板.md`，硬规启动 `recall(/staff/reviewer, subject:review:test-design|test-coverage)`。

### 5.5 两个 reviewer-`<cap>` agent（callee 形，照 reviewer-code.md 范本）

`reviewer-test-design.md` / `reviewer-test-coverage.md`：frontmatter(name/description/model:opus) + Identity/Principles/Critical Actions/Capabilities；只读、出 `handoffs/reviewer/<gate>.<cap>.score.md`、双重通过条件 `total≥阈值 AND 🔴=0`。

---

## 6. §2.4ter 跨员工 handoff 接线（只连 req，显式不连 dev）

driver SKILL §2.4ter 生产方映射表**追加** test-engineer 两棒，并注记消费方黑盒约束：

| 生产方（员工）| 交付节点 `--node` | 交付内容 | 消费方 |
|---|---|---|---|
| `req-architect` | `n8-merge` | SR/AR/用户故事/原型 | dev-engineer（代码）+ **test-engineer（黑盒测试设计）各自独立读** |
| `test-engineer` | `n3-merge`（design-flow）| test-points / test-cases | test-engineer exec-flow（同 slug 下一棒）+ 下游/QA |
| `test-engineer` | `n2-report`（exec-flow）| ui-results / 覆盖报告 | 下游/QA/HUD |

- **test-engineer 消费**：`handoff-read req-architect n8-merge`（同 slug）→ 需求/原型作设计输入；缺失→裸任务。
- 🔴 **显式不建 `dev-engineer → test-engineer` handoff 边**；并在 §2.4ter test 段写黑盒独立硬规（test 不读 dev 代码/flow）。
- 被测环境 URL：运行时参数（非 handoff 依赖），由测试人员/编排传给 exec-flow。

---

## 7. env 依赖：建好 vs 实跑（诚实标注）

| 阶段 | env 依赖 | 本步（建员工基础设施）|
|---|---|---|
| 建 staff/node-table/agent/standards/dispatch-table + 测试绿 | **无** | ✅ 本步全部完成、可测试验证 |
| 跑 test-design-flow（真任务）| **无**（黑盒，读需求/原型）| 真任务时可跑，无需 env |
| 跑 test-exec-flow（真任务）| **需被测环境 URL + 浏览器**（kdev-ui-autotest 依赖 webapp-testing + recon/menu_list.md）| 仅真实测试任务、有被测环境时；本步**不**活体验证 exec-flow（参 UED6 dogfood 曾无 MySQL env-blocked）|

边界结论：**本步交付"建好"的全套基础设施 + 单测绿；exec-flow 的"实跑"留待有被测环境的真实测试任务**，spec/agent/路由如实标注 env-gated。

---

## 8. kdev-core 零改 / 复用 / 落地清单

### 8.1 零改 + 复用
- **kdev-core 零改**：`cli.py` flow 名为位置串、node-table 走 `--table` 路径，无注册表、无 flow 名枚举（已验：`_common()` 注册 `flow`/`slug` positional；`_load_table(path)` 读任意 yaml）。加 test-flow 无需碰 kdev-core。
- **复用**：通用 `kdev-flow-driver`（G-008，编排不下放）、B 轨 handoff write/read 原语、`kdev-test-points`/`kdev-test-cases`/`kdev-ui-autotest` 能力 skill、reviewer callee 框架 + 通用评分模板。

### 8.2 落地清单（实施 plan 的输入）
**新增文件（10）**：
- node-table（2）：`orchestration/test-engineer.design.node-table.yml`、`orchestration/test-engineer.exec.node-table.yml`
- test-engineer agent（4）：`agents/test-engineer-orchestrator.md`、`agents/test-engineer-points.md`、`agents/test-engineer-cases.md`、`agents/test-engineer-ui.md`
- reviewer-`<cap>` agent（2）：`agents/reviewer-test-design.md`、`agents/reviewer-test-coverage.md`
- standards（2）：`standards/reviewer/测试设计评审.md`、`standards/reviewer/测试覆盖评审.md`

**改文件**：
- `staff.yml`：+test-engineer 条目（`node_tables`/`default_flow`）、reviewer `agents` 7→9
- `orchestration/reviewer.dispatch-table.yml`：+2 行、改 deferred 注释
- `agents/reviewer-orchestrator.md`：Capabilities 路由表 +2 行
- `skills/kdev-flow-driver/references/node-agent-routing.md`：+test-engineer 路由段 + reviewer 发函 dispatch 补 2 cap
- `skills/kdev-flow-driver/references/gate-decision-logic.md`：+test-engineer gate 判据段（含 2 发函 gate + 黑盒注记）
- `skills/kdev-flow-driver/SKILL.md`：§2.4ter 生产方表 +test-engineer + 黑盒独立硬规注记
- `.claude-plugin/plugin.json` + `CHANGELOG.md`：bump kdev-team version（G-004 提示刷 marketplace）

### 8.3 测试（TDD，跑绿）
- `test_staff.py`：+`test_test_engineer_entry`（node_tables 双 flow / default_flow / agents 文件存在）；reviewer agents 7→9；flow-owner 不变量改为「node_table XOR node_tables」。
- 新 `test_test_engineer_orchestration.py`：两 node-table loads、节点数、每 gate 有 spec、gate targets 合法、reviewer 绑定合法（照 `test_orchestration_config.py` / `test_req_architect_orchestration.py`）。
- `test_reviewer_dispatch.py` / `test_reviewer_wiring.py`：+test-design/test-coverage 词条与 agent 存在性、caller_gate、阈值。
- `test_agents.py`：新 6 个 agent 的 frontmatter（name/description/model）合法。
- `test_plugin_manifest.py`：plugin.json bump 后仍合法。

---

## 9. 非目标 / 后续

- **不建** `kdev-api-autotest` 执行层 skill（API 业务 agent + exec-flow T4 节点 deferred 到该 skill 建成）。
- **不改** dev-engineer / req-architect 的 flow；**不建** dev→test handoff 边。
- **不做** exec-flow 活体验证（需被测环境）；本步只到"建好 + 单测绿"。
- **不做依赖声明 / packaging**（Q-018 已 defer 进 roadmap §1.5.8）：装数字员工时连带安装其用到的全部 skill（kdev-team `plugin.json` 补 `dependencies` 自动传递安装 + 修 marketplace 条目名 `-v1` 错配 + 外部 marketplace skill 前置）属 kdev-team 全局 packaging 关注，单列专项（宜与 FF-2 合并），**本期 test-engineer 工作不碰** `kdev-team/plugin.json` 的 dependencies / marketplace.json。机制已查实：CC 支持 `dependencies` 自动安装，**声明不 bundle**。
- per-flow / per-gate reviewer 的 engine 级 config-merge 沿用现状（L0 node-table 字段生效，L1 手改回退 self）。
- 后续：reviewer 余 2 能力（need-direction / iteration-split）随 req-architect 加 R1.5/R2.5 gate 再补。

---

## 10. 回写（落地后）
- roadmap §1.5.8（测试工程师 done）+ 阶段3 行（评审专家 核心 10 余 4 → 余 2）。
- kdev-team CHANGELOG + version bump；G-004：提示用户刷 marketplace。
