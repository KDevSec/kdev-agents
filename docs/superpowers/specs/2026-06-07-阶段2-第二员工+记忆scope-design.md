# 阶段2 接入设计 · 第二员工(需求架构师) + 记忆 scope 分离 + 员工集中 kdev-team

| 项 | 值 |
|---|---|
| 文档性质 | **brainstorming 设计稿 v0.1**（待用户复核 → writing-plans）|
| lifecycle | design |
| 日期 | 2026-06-07 |
| 范围 | 阶段2 = ① P-0 员工集中 kdev-team(agents 合规) ② P-C1 记忆 scope 分离 ③ P-A 需求架构师接底座 ④ P-B 跨员工 handoff。**defer**：P-C2 JSONL 操作层 / P-C3 并发写锁 / 完整编码重跑 / kdev-agents 自身记忆迁移 / 评审专家(阶段3) |
| 承 | [Q-004 walking-skeleton](../../../.kdev/memory/决策日志.md) · [Q-007 抽共性](../../../.kdev/memory/决策日志.md) · [Q-008 状态/记忆分离](../../../.kdev/memory/决策日志.md) · [Q-009 git托管](../../../.kdev/memory/决策日志.md) · [Q-010 接入打法](../../../.kdev/memory/决策日志.md) |
| 配套 | [起步 roadmap §5](../../framework/01-design/2026-06-06-01-数字员工整体设计路线图roadmap-v1.0.md) · [记忆架构 §3/§4/§5/§9.6](../../framework/01-design/2026-06-05-02-数字员工记忆架构-分层+scope拓扑-v0.1.md) · [员工能力专项 v1.5 §2.3](../../framework/01-design/2026-05-28-01-KDev数字员工架构-员工能力专项-v1.5.md) · [阶段1 接入设计](./2026-06-06-阶段1-coding-flow接底座-design.md) |
| 复用 | 阶段1 已验证：kdev-core 底座(R1/R2/R3 + CLI) + 接入打法(node-table + persona + CLI 驱动)；M1 首次实测跑通 |

---

## 0. 一句话

给集群加**第二个员工（需求架构师 = kdev-design-flow 接底座，复刻阶段1 打法）** + 让 kdev-memory **scope-aware**（两员工记忆干净分离）+ 打通**需求→开发 handoff**；并先做 **P-0 员工集中到 `kdev-team` 插件**（agent 落标准 `agents/` 真 CC agent），把阶段1 自创的非标结构纠正，避免带歪第二员工。

---

## 0.5 命名规范（canonical id 全处统一 + 中文 display）⭐

**规则**：每员工一个 ASCII **canonical id**（机器用）+ **中文 display name**（人读用）。所有机器路径（subagent_type / node-table / 记忆 scope / Step ID / handoff）一律用 canonical id；中文名只出现在 display 处（frontmatter `description` / `staff.yml` / Step 条目标题 / brief）。

| canonical id | 中文 display | 状态 |
|---|---|---|
| `dev-engineer` | 开发工程师 | 阶段1 已建（P-0 搬迁）|
| `req-architect` | 需求架构师 | 阶段2 新建 |
| `test-engineer` / `reviewer` / `ceo` / `cqo` | 测试工程师 / 评审专家 / CEO / CQO | 后续阶段 |

**agent id（= subagent_type，`<canonical>-<cap>`）**：
- 开发工程师：`dev-engineer-orchestrator` `dev-engineer-env` `dev-engineer-plan` `dev-engineer-frontend` `dev-engineer-e2e` `dev-engineer-deploy` `dev-engineer-sec`
- 需求架构师：`req-architect-orchestrator` `req-architect-clarify` `req-architect-spec` `req-architect-decompose` `req-architect-prototype` `req-architect-design`

**带员工名的机器路径（全用 canonical id）**：node-table `kdev-team/orchestration/<id>.node-table.yml` · 记忆 scope `.kdev/memory/staff/<id>/` · Step `Step <id>-N` · handoff `.kdev/features/<slug>/handoffs/<id>/`（⚠️ **以 Q-012 feature-first 为准**；本稿原写扁平 `.kdev/handoffs/<id>/` 早于翻转，已陈旧）。

> **命名消歧**：员工插件 = `plugins/kdev-team/`（agent 定义）；记忆分区 = `.kdev/memory/staff/<id>/`（kdev-memory 管）。二者不同物、不同命名空间（plugin 改名 kdev-team 即为避开 staff 撞名）。

---

## 1. 本轮 brainstorming 拍板（决策摘要）

| # | 决策点 | 拍板 |
|---|---|---|
| 1 | sequencing | **P-0 → P-C1 → P-A → P-B**（地基先行，不要 flat-then-migrate 返工）|
| 2 | P-C 拆法（按真实驱动力）| **P-C1 scope 分离**(2 员工就咬 → 建) / **P-C2 JSONL 操作层**(token 痛才咬 → defer) / **P-C3 并发写锁**(并行员工才咬 → defer 阶段3) |
| 3 | scope-aware 形态 | **opt-in 向后兼容**：flat 默认(= 现状)，有 staff 才 scoped；**kdev-agents 自身记忆保持 flat 不迁** |
| 4 | 员工目录结构 | **集中 `kdev-team` 总目录**：新建 `plugins/kdev-team/` 收所有员工 agent + per-员工 node-table；flow-skill 插件(kdev-coding-flow/kdev-design-flow)回归**纯方法论参考**(不含 agents/orchestration)；遗留能力 skill 不动。理由：agent↔flow-skill 是**参考非调用绑定**→无需同插件→集中=统一可扩展的员工组织 |
| 5 | 验证 | **轻 dogfood**：需求架构师产 SR/AR(落 scope) → handoff 接进 coding-flow 输入；**不重跑完整编码**（Pass1 已验 + env 限制）|
| 6 | P-A 形态 | **kdev-design-flow 接底座**（复刻阶段1）：迁自带 flow_state → kdev-core 引擎 + node-table + agents + SKILL 接口节 |
| 7 | 命名 | **ASCII canonical id 全处统一 + 中文 display**（§0.5）；员工插件改名 `kdev-team` 避 staff 撞名 |

---

## 2. 关键取舍 + 依据（⭐ 别丢）

### 2.1 sequencing：为何 P-0/P-C1 先于员工（而非纯 walking-skeleton employee-first）

用户反问点中要害：**过度抽象与过度简化是对称的坑**。纯"employee-first，defer 全部基建"会过度简化——第二员工建在 flat 记忆上 → 归属乱 + 后续 flat→scoped 迁移(§4)= 返工。所以**按真实驱动力拆 P-C**（决策 #2）：scope 分离是"2 员工就咬"的真需求（与并发无关），必须随第二员工一起建；只有 JSONL 优化(token 痛)和并发锁(并行)才是 defer 对象。P-0 同理——结构不合规会带歪第二员工，先纠。

### 2.2 P-C1 是 scope-aware **opt-in**，不是无条件 scoped

记忆架构 §4：单装 kdev-memory = flat 默认(现状)；装了 staff = 多 scope。所以 P-C1 = 让 kdev-memory **有能力** scoped，**默认仍 flat**——无 staff 时路径+行为完全不变。**kdev-agents 框架仓自己的 `.kdev` 保持 flat**（主控单轨），只有多员工 dogfood 用 scoped。否则砸了框架仓自身记忆 + 所有现有 kdev-memory 用户。

### 2.3 员工目录：集中到 kdev-team（P-0 由来）

阶段1 把员工 persona 塞进 `skills/kdev-coding-flow/personas/`（自创非标位置）且非真 CC frontmatter agent → 不能 `Agent({subagent_type})` 直接派 → **Pass1 主控只能"兼演编排 + general-purpose 喂 persona 文本"降级的根因**。纠正方向**不是**塞回各 flow 插件的 `agents/`，而是**集中到新建 `plugins/kdev-team/`**：因 agent↔flow-skill 是**参考关系非调用绑定**（编排 = agent 按 node-table 调度，flow-skill 只是方法论/模板参考），员工无需与 flow-skill 同插件。集中给**统一、可扩展**的员工组织（6 员工进一个总目录），并让 flow-skill 插件彻底回归纯方法论（不被员工结构污染）。

### 2.4 agent × skill 分工（守 Q-008，纠"flow-skill 串联"误想）

**编排 = 编排 Agent 的行为，不是"调 flow-skill 串出来的"**：编排 Agent 读 node-table(编排结构) → 按编排在每节点**调度**业务 Agent → 记 gate → 经 kdev-core CLI advance。业务 Agent 各调各业务 skill。**flow-skill = skill 调用的要求+模板参考（非编排器）**：implementer-prompt-template / 三段约束 / TDD / gate 判据 / bundle——agent 参考它"怎么调 skill"，但它不串联业务 skill。⚠️ 不可把编排逻辑埋回 SKILL prose。三者互不抢：node-table(结构) · 编排 Agent(按结构调度) · flow-skill(调用模板参考)。

---

## 3. P-0 员工集中到 kdev-team（前置，含 kdev-coding-flow 回溯搬迁）

**目标结构（四类彻底分开）**：
```
plugins/
├── kdev-team/                           ← 【数字员工集群 · 总目录】
│   ├── .claude-plugin/plugin.json
│   ├── agents/                          ← 所有员工瘦 persona agent（CC subagent，可 subagent_type 直派）
│   │   ├── dev-engineer-orchestrator.md  dev-engineer-env.md  dev-engineer-plan.md
│   │   ├── dev-engineer-frontend.md  dev-engineer-e2e.md  dev-engineer-deploy.md  dev-engineer-sec.md   (开发工程师 7)
│   │   ├── req-architect-orchestrator.md  req-architect-clarify.md  req-architect-spec.md
│   │   ├── req-architect-decompose.md  req-architect-prototype.md  req-architect-design.md             (需求架构师 6)
│   │   └── …(后续 test-engineer/reviewer/ceo/cqo 续加)
│   ├── orchestration/                   ← per-员工 node-table（编排结构）
│   │   ├── dev-engineer.node-table.yml   req-architect.node-table.yml
│   ├── staff.yml                        ← 花名册：canonical id → 中文 display + 引用哪个 flow-skill + handoff 路由 + 运行时模型
│   ├── tests/                           ← agents 结构 + node-table 一致性校验
│   └── README.md
├── kdev-coding-flow/  kdev-design-flow/  ← 【方法论 flow-skill】纯 SKILL + references（agent 参考，不含 agents/orchestration）
├── kdev-secure-coding/ kdev-test-*/ …    ← 【能力 skill】员工 call
└── kdev-core/  kdev-memory/               ← 【基建】引擎 + 记忆
```

- **agent frontmatter**（真 CC agent，可 `Agent({subagent_type})` 直派）：
  ```yaml
  ---
  name: dev-engineer-frontend     # CC subagent_type（ASCII canonical-<cap>）；中文角色进 description/正文
  description: 开发工程师·前端实现能力 — <when to use>
  model: opus                     # 运行时模型（阶段1 暂 Opus，可配；亦可 staff.yml 统管）
  ---
  ## Identity / Principles / Critical Actions / Capabilities(技能菜单)   ← 瘦 persona 正文
  ```
  > agents/ 默认 flat（CC 读 agents/*.md）→ canonical 前缀(`dev-engineer-*`/`req-architect-*`)区分员工；若 CC 支持 agents/<员工>/ 嵌套则按员工分子目录（writing-plans 核实）。

- **agent × skill 分工**：见 §2.4（编排=agent 按 node-table 调度；flow-skill=调用模板参考非编排器）。

- **P-0 = 建 kdev-team + 回溯搬迁阶段1 产物**：
  1. 新建 `plugins/kdev-team/` 插件骨架（plugin.json / agents/ / orchestration/ / staff.yml / tests/）。
  2. `kdev-coding-flow/skills/.../personas/*.md` → `kdev-team/agents/dev-engineer-*.md`（加 frontmatter + canonical id）；删源 personas/。
  3. `kdev-coding-flow/skills/.../orchestration/node-table.yml` → `kdev-team/orchestration/dev-engineer.node-table.yml`；删源 orchestration/。
  4. `kdev-coding-flow` SKILL.md **回归纯方法论**：员工特定编排指令归到 `dev-engineer-orchestrator` agent，SKILL 只留方法论 + skill 调用要求/模板。
  5. test_personas.py / test_orchestration_config.py 迁 kdev-team/tests/ 改指新路径 + canonical id。
- **约定确立**：员工 = `kdev-team/{agents/<canonical-cap>, orchestration/<canonical>.node-table.yml}` + 参考其 flow-skill；flow-skill / 能力 skill / 基建 各自独立插件不混。
- 验证：kdev-team 测试绿；主控可 `Agent({subagent_type: dev-engineer-frontend})` 直派（降级根因除）。

---

## 4. P-C1 记忆 scope 分离（kdev-memory，最重）

- **布局**（记忆架构 §4/§5.3）：`.kdev/memory/{shared/, staff/<id>/}`。shared = 决策/踩坑/skill-feedback/当前状态/执行日志(项目时间线)；`staff/<id>/`（如 `staff/dev-engineer/`）= per-员工执行 rollup。
- **scope 解析层**：kdev-memory hooks 加 scope 解析——**默认 `default`/flat（无 staff 时路径+行为=现状，向后兼容）**；检测 staff 注册 → scoped。
- **per-scope counter**：Step ID 从 per-branch(`Step main-N`)泛化 per-scope(`Step <id>-N`，如 `Step dev-engineer-N`)，复用 step_id 现有 slug 雏形。
- **scoped 召回/brief/rollup**：UserPromptSubmit 召回 + SessionStart brief + rollup 按 scope 过滤（agent 召回自己 scope + shared）。涉及 hook：path 解析 / step_id / trigger-match(召回) / session-start-brief / rollup(weekly/distill) / frontmatter / missing_summaries 等（~精确清单 writing-plans 定）。
- **迁移脚本**：dogfood 的 flat `.kdev/memory/*` → `memory/shared/` + 开 `memory/staff/<id>/`（一次性，幂等）。**kdev-agents 自身不迁**。
- **bump kdev-memory version**（避 G-004 cache stale）。
- right-size：只建 2 员工 + shared 的最小 scope 机制，**不上 JSONL/锁**。

---

## 5. P-A 需求架构师接底座（kdev-design-flow，复刻阶段1）

kdev-design-flow 已有 SR→评审 gate→prototype 多阶段 SOP + **自带 flow_state（R1 金种子原型）** → 迁到 kdev-core：

- **node-table + gate_specs**：SOP（需求澄清 IR→需求计划 SR→需求拆解 AR→原型设计→方案设计 + 评审 gate）映射 R2 node-table + R3 gate（reviewer 绑定：自评 vs 第三方 deferred）。精确 node 映射 writing-plans 细化。
- **agents 落 `kdev-team`（P-0 合规）**：`kdev-team/agents/req-architect-*.md` = 1 编排(`req-architect-orchestrator`) + 5 业务(`req-architect-clarify`/`-spec`/`-decompose`/`-prototype`/`-design`)，真 CC frontmatter agent；node-table 落 `kdev-team/orchestration/req-architect.node-table.yml`。
- **kdev-design-flow SKILL = 方法论参考**（req-architect-* 参考它 + skill 调用模板）+ 复用 kdev-core CLI（通用零改）。**编排指令归 `req-architect-orchestrator` agent，不埋 SKILL prose**。
- ⚠️ 比 coding-flow 多一步：design-flow **有自带 flow_state 要换掉**（coding-flow 原本无状态）——保其 SOP 行为不破（它有 evals/tests）；其 flow_state 是 R1 金种子，kdev-core 是其泛化超集，迁移可行。
- 产物：IR/SR/AR/prototype/design.md，落 `.kdev/memory/staff/req-architect/` **记忆 scope**。

---

## 6. P-B 跨员工 handoff

- 需求架构师 SR/AR → `.kdev/features/<slug>/handoffs/req-architect/`（⚠️ **路径以 Q-012 feature-first 为准**；本稿原写扁平 `.kdev/handoffs/req-architect/` 早于翻转。kdev-core 运行时，记忆底座 §5.3 #12）→ 开发工程师 coding-flow 节点0/3 把 SR/AR 当 spec 输入读。
- **handoff = 结构化产物指针**（谁产了啥 + 路径 + 状态）；coding-flow 入口接受"上游 SR/AR"作 spec.md/plan.md 来源（阶段1 coding-flow 节点0 本就吃 spec+plan+prototype 三件套，SR/AR/prototype 正好对位）。
- handoff 格式 + 读写接口 writing-plans 细化（最小：一个 manifest 指针文件 + 产物路径约定）。

---

## 7. 验证（轻 dogfood）

需求架构师对一个**小需求**产 SR/AR（落 `.kdev/memory/staff/req-architect/` scope）→ handoff → 验 coding-flow 节点0/3 能读到 SR/AR。**验收**：
1. **需求架构师经 kdev-core 驱动跑通**：node-table 流转 + gate（≥1 decision + ≥1 review）+ flow-state resume-across-process。
2. **scope 分离落对位置**：`staff/req-architect/` vs `staff/dev-engineer/` 各自 rollup + per-scope Step counter(`Step req-architect-N`) + shared 共享(决策/踩坑) + 召回按 scope 过滤。
3. **handoff 接线通**：SR/AR 从 req-architect scope 流到 coding-flow 输入（节点0/3 读到）。
4. **P-0 合规验证**：业务 agent 可 `Agent({subagent_type: dev-engineer-frontend})` 直接派（降级根因已除）。
- **不重跑完整编码**（Pass1 已验 + 无 MySQL env 限制）。

---

## 8. 非目标（defer，防镀金）

P-C2 JSONL 操作层(token 痛才上) · P-C3 并发写锁(阶段3 并行员工) · 完整编码 dogfood 重跑 · **kdev-agents 自身记忆迁移(保 flat)** · 评审专家(阶段3) · rollup 触发时机深细化(够用即可) · 遗留能力 skill 插件改动。

---

## 9. 文件布局

- **kdev-team（P-0 新建）**：插件骨架 + 搬 kdev-coding-flow personas→`agents/dev-engineer-*.md`(7,加 frontmatter) + orchestration→`orchestration/dev-engineer.node-table.yml` + `staff.yml` 花名册 + tests。
- **kdev-coding-flow（P-0 瘦身）**：删 `skills/.../{personas,orchestration}/`；SKILL 回归纯方法论（员工特定编排指令归 `dev-engineer-orchestrator` agent）。
- **kdev-memory**（P-C1）：scope 解析层 + 受影响 hooks 改造（path/step_id/召回/brief/rollup/frontmatter…）+ migrate 脚本 + bump version + CHANGELOG + 测试。
- **kdev-design-flow（P-A）**：SKILL 加方法论参考 + 迁 flow_state→kdev-core；其 **agents(req-architect-* 6) + node-table 落 kdev-team**（非本插件）+ 测试。
- **handoff**（P-B）：格式定义 + coding-flow 入口接 SR/AR +（kdev-core handoffs 目录约定）。
- dogfood（验证）：独立 workspace（`~/Projects/kdev-dogfood-stage2` 或复用现有），不进框架仓。

---

## 10. sequencing + 下一步

**实施序**：P-0（建 kdev-team + 搬迁）→ P-C1（scope 地基）→ P-A（需求架构师接底座，落 scope）→ P-B（handoff）→ 轻 dogfood 验证。

1. 用户复核本稿 → 转 **writing-plans** 起阶段2 实施计划（可能拆多个 plan：P-0+P-C1 基建 / P-A+P-B 员工+协作）。
2. 决策沉淀：本轮拍板补 Q-NNN（sequencing / scope-aware opt-in / 员工集中 kdev-team / agent×skill 分工 / 命名规范）。
3. 回写 roadmap §1.5 阶段2 行。
