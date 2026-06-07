# 阶段2 接入设计 · 第二员工(需求架构师) + 记忆 scope 分离 + 员工目录合规

| 项 | 值 |
|---|---|
| 文档性质 | **brainstorming 设计稿 v0.1**（待用户复核 → writing-plans）|
| lifecycle | design |
| 日期 | 2026-06-07 |
| 范围 | 阶段2 = ① P-0 员工目录结构整改(agents/ 合规) ② P-C1 记忆 scope 分离 ③ P-A 需求架构师接底座 ④ P-B 跨员工 handoff。**defer**：P-C2 JSONL 操作层 / P-C3 并发写锁 / 完整编码重跑 / kdev-agents 自身记忆迁移 / 评审专家(阶段3) |
| 承 | [Q-004 walking-skeleton](../../../.kdev/memory/决策日志.md) · [Q-007 抽共性](../../../.kdev/memory/决策日志.md) · [Q-008 状态/记忆分离](../../../.kdev/memory/决策日志.md) · [Q-009 git托管](../../../.kdev/memory/决策日志.md) · [Q-010 接入打法](../../../.kdev/memory/决策日志.md) |
| 配套 | [起步 roadmap §5](../../framework/01-design/2026-06-06-01-数字员工集群-起步roadmap-Q004细化-v0.1.md) · [记忆架构 §3/§4/§5/§9.6](../../framework/01-design/2026-06-05-02-数字员工记忆架构-分层+scope拓扑-v0.1.md) · [员工能力专项 v1.5 §2.3](../../framework/01-design/2026-05-28-01-KDev数字员工架构-员工能力专项-v1.5.md) · [阶段1 接入设计](./2026-06-06-阶段1-coding-flow接底座-design.md) |
| 复用 | 阶段1 已验证：kdev-core 底座(R1/R2/R3 + CLI) + 接入打法(node-table + persona + CLI 驱动)；M1 首次实测跑通 |

---

## 0. 一句话

给集群加**第二个员工（需求架构师 = kdev-design-flow 接底座，复刻阶段1 打法）** + 让 kdev-memory **scope-aware**（两员工记忆干净分离，不糊在一起）+ 打通**需求→开发 handoff**；并先做 **P-0 员工目录合规整改**（personas → 标准 `agents/` 真 CC agent），把阶段1 自创的非标结构纠正，避免带歪第二员工。

---

## 1. 本轮 brainstorming 拍板（决策摘要）

| # | 决策点 | 拍板 |
|---|---|---|
| 1 | sequencing | **P-0 → P-C1 → P-A → P-B**（地基先行，不要 flat-then-migrate 返工）|
| 2 | P-C 拆法（按真实驱动力）| **P-C1 scope 分离**(2 员工就咬 → 建) / **P-C2 JSONL 操作层**(token 痛才咬 → defer) / **P-C3 并发写锁**(并行员工才咬 → defer 阶段3) |
| 3 | scope-aware 形态 | **opt-in 向后兼容**：flat 默认(= 现状)，有 staff 才 scoped；**kdev-agents 自身记忆保持 flat 不迁** |
| 4 | 员工目录结构 | **就地合规 agents/**：员工 = 其 *-flow 插件；personas → `plugins/<flow>/agents/*.md`（真 CC frontmatter agent，可直接 subagent_type 派）；SKILL 回归纯方法论；遗留能力 skill 不动 |
| 5 | 验证 | **轻 dogfood**：需求架构师产 SR/AR(落 staff scope) → handoff 接进 coding-flow 输入；**不重跑完整编码**（Pass1 已验 + env 限制）|
| 6 | P-A 形态 | **kdev-design-flow 接底座**（复刻阶段1）：迁自带 flow_state → kdev-core 引擎 + node-table + agents + SKILL 接口节 |

---

## 2. 关键取舍 + 依据（⭐ 别丢）

### 2.1 sequencing：为何 P-0/P-C1 先于员工（而非纯 walking-skeleton employee-first）

用户反问点中要害：**过度抽象与过度简化是对称的坑**。纯"employee-first，defer 全部基建"会过度简化——第二员工建在 flat 记忆上 → 归属乱 + 后续 flat→scoped 迁移(§4)= 返工。所以**按真实驱动力拆 P-C**（决策 #2）：scope 分离是"2 员工就咬"的真需求（与并发无关），必须随第二员工一起建；只有 JSONL 优化(token 痛)和并发锁(并行)才是 defer 对象。P-0 同理——结构不合规会带歪第二员工，先纠。

### 2.2 P-C1 是 scope-aware **opt-in**，不是无条件 scoped

记忆架构 §4：单装 kdev-memory = flat 默认(现状)；装了 staff = 多 scope。所以 P-C1 = 让 kdev-memory **有能力** scoped，**默认仍 flat**——无 staff 时路径+行为完全不变。**kdev-agents 框架仓自己的 `.kdev` 保持 flat**（主控单轨），只有多员工 dogfood 用 scoped。否则砸了框架仓自身记忆 + 所有现有 kdev-memory 用户。

### 2.3 员工目录：阶段1 自创结构的纠正（P-0 由来）

阶段1 把员工 persona 塞进 `skills/kdev-coding-flow/personas/`（自创非标位置），且**不是真 CC frontmatter agent**（无 name/description/tools YAML）→ 不能 `Agent({subagent_type})` 直接派 → **这是 Pass1 主控只能"兼演编排 + general-purpose 喂 persona 文本"降级的根因**。CC 约定 = 插件根 `agents/`（本仓 kdev-memory 已用 agents/）。P-0 纠正：personas → `plugins/<flow>/agents/` 真 CC agent，员工可干净派单，SKILL 回归纯方法论，不污染遗留 skill。

---

## 3. P-0 员工目录结构整改（前置，含 kdev-coding-flow 回溯）

**目标结构**（员工 = 自包含插件）：
```
plugins/kdev-coding-flow/            ← 开发工程师（回溯整改）
├── agents/                          ← 新：7 个真 CC frontmatter agent（迁自 skills/.../personas/）
│   ├── <编排>.md  <环境准备>.md  <实施计划>.md  <前端实现>.md
│   ├── <E2E视觉验收>.md  <部署上线>.md  <安全扫描>.md
├── skills/kdev-coding-flow/
│   ├── SKILL.md                     ← 回归纯方法论（「接底座入口」节保留，指向 ../../agents/ + orchestration/）
│   ├── orchestration/node-table.yml ← 留（编排 config）
│   └── references/ ...
└── tests/  (orchestration + agents 结构校验)
```

- **agent frontmatter**（真 CC agent）：
  ```yaml
  ---
  name: <ascii-id>          # CC subagent_type 标识（ASCII，如 dev-frontend-impl）
  description: <中文角色 + when to use>
  model: opus              # 运行时模型（阶段1 暂 Opus，可配）
  ---
  ## Identity / Principles / Critical Actions / Capabilities  (persona 正文)
  ```
  > **命名考量**：CC subagent_type 用 ASCII id（中文角色名进 description/正文）。精确 id 映射 writing-plans 定。
- **迁移**：`skills/kdev-coding-flow/personas/*.md` → `agents/*.md`（加 frontmatter）；删空 personas/；SKILL 的「接底座入口」节路径引用改 `agents/`；test_personas.py 改指 agents/。
- **约定确立**：以后每员工 = `plugins/<员工flow>/{agents/, skills/.../{SKILL.md, orchestration/}, tests/}`。遗留能力 skill 插件不动。
- 验证：kdev-coding-flow 测试仍绿；（可选）主控能 `Agent({subagent_type:<业务agent id>})` 直接派（验证降级根因已除）。

---

## 4. P-C1 记忆 scope 分离（kdev-memory，最重）

- **布局**（§4/§5.3）：`.kdev/memory/{shared/, staff/<员工>/}`。shared = 决策/踩坑/skill-feedback/当前状态/执行日志(项目时间线)；`staff/<员工>/` = per-员工执行 rollup。
- **scope 解析层**：kdev-memory hooks 加 scope 解析——**默认 `default`/flat（无 staff 时路径+行为=现状，向后兼容）**；检测 staff 注册 → scoped。
- **per-scope counter**：Step ID 从 per-branch(`Step main-N`)泛化 per-scope(`Step <员工>-N`)，复用 step_id 现有 slug 雏形。
- **scoped 召回/brief/rollup**：UserPromptSubmit 召回 + SessionStart brief + rollup 按 scope 过滤（agent 召回自己 scope + shared）。涉及 hook：path 解析 / step_id / trigger-match(召回) / session-start-brief / rollup(weekly/distill) / frontmatter / missing_summaries 等（~精确清单 writing-plans 定）。
- **迁移脚本**：dogfood 的 flat `.kdev/memory/*` → `memory/shared/` + 开 `memory/staff/<员工>/`（一次性，幂等）。**kdev-agents 自身不迁**。
- **bump kdev-memory version**（避 G-004 cache stale）。
- right-size：只建 2 员工 + shared 的最小 scope 机制，**不上 JSONL/锁**。

---

## 5. P-A 需求架构师接底座（kdev-design-flow，复刻阶段1）

kdev-design-flow 已有 SR→评审 gate→prototype 多阶段 SOP + **自带 flow_state（R1 金种子原型）** → 迁到 kdev-core：

- **node-table + gate_specs**：SOP（需求澄清 IR→需求计划 SR→需求拆解 AR→原型设计→方案设计 + 评审 gate）映射 R2 node-table + R3 gate（reviewer 绑定：自评 vs 第三方 deferred）。精确 node 映射 writing-plans 细化。
- **agents/**（P-0 合规）：1 编排（需求架构师-编排）+ 5 业务（需求澄清/需求计划/需求拆解/原型设计/方案设计），真 CC frontmatter agent。
- **SKILL 加「接 kdev-core 底座入口」节** + 复用 kdev-core CLI（通用零改）。
- ⚠️ 比 coding-flow 多一步：design-flow **有自带 flow_state 要换掉**（coding-flow 原本无状态）——保其 SOP 行为不破（它有 evals/tests）；其 flow_state 是 R1 金种子，kdev-core 是其泛化超集，迁移可行。
- 产物：IR/SR/AR/prototype/design.md，落 `staff/需求架构师/` scope。

---

## 6. P-B 跨员工 handoff

- 需求架构师 SR/AR → `.kdev/handoffs/需求架构师/`（kdev-core 运行时，§5.3 #12）→ 开发工程师 coding-flow 节点0/3 把 SR/AR 当 spec 输入读。
- **handoff = 结构化产物指针**（谁产了啥 + 路径 + 状态）；coding-flow 入口接受"上游 SR/AR"作 spec.md/plan.md 来源（阶段1 coding-flow 节点0 本就吃 spec+plan+prototype 三件套，SR/AR/prototype 正好对位）。
- handoff 格式 + 读写接口 writing-plans 细化（最小：一个 manifest 指针文件 + 产物路径约定）。

---

## 7. 验证（轻 dogfood）

需求架构师对一个**小需求**产 SR/AR（落 `staff/需求架构师/` scope）→ handoff → 验 coding-flow 节点0/3 能读到 SR/AR。**验收**：
1. **需求架构师经 kdev-core 驱动跑通**：node-table 流转 + gate（≥1 decision + ≥1 review）+ flow-state resume-across-process。
2. **scope 分离落对位置**：`staff/需求架构师/` vs `staff/开发工程师/` 各自 rollup + per-scope Step counter(`Step 需求架构师-N`) + shared 共享(决策/踩坑) + 召回按 scope 过滤。
3. **handoff 接线通**：SR/AR 从 需求架构师 scope 流到 coding-flow 输入（节点0/3 读到）。
4. **P-0 合规验证**：业务 agent 可 `Agent({subagent_type})` 直接派（降级根因已除）。
- **不重跑完整编码**（Pass1 已验 + 无 MySQL env 限制）。

---

## 8. 非目标（defer，防镀金）

P-C2 JSONL 操作层(token 痛才上) · P-C3 并发写锁(阶段3 并行员工) · 完整编码 dogfood 重跑 · **kdev-agents 自身记忆迁移(保 flat)** · 评审专家(阶段3) · rollup 触发时机深细化(够用即可) · 遗留能力 skill 插件改动。

---

## 9. 文件布局

- **kdev-coding-flow**（P-0 回溯）：新 `agents/*.md`(7) · 删 `skills/.../personas/` · SKILL 路径引用改 · tests 改指 agents/。
- **kdev-memory**（P-C1）：scope 解析层 + 受影响 hooks 改造（path/step_id/召回/brief/rollup/frontmatter…）+ migrate 脚本 + bump version + CHANGELOG + 测试。
- **kdev-design-flow**（P-A）：node-table.yml + gate_specs + `agents/*.md`(6) + SKILL 接口节 + 迁 flow_state→kdev-core + 测试。
- **handoff**（P-B）：格式定义 + coding-flow 入口接 SR/AR + （kdev-core handoffs 目录约定）。
- dogfood（验证）：独立 workspace（`~/Projects/kdev-dogfood-stage2` 或复用现有），不进框架仓。

---

## 10. sequencing + 下一步

**实施序**：P-0（结构整改）→ P-C1（scope 地基）→ P-A（需求架构师接底座，落 staff scope）→ P-B（handoff）→ 轻 dogfood 验证。

1. 用户复核本稿 → 转 **writing-plans** 起阶段2 实施计划（可能拆多个 plan：P-0+P-C1 基建 / P-A+P-B 员工+协作）。
2. 决策沉淀：本轮拍板补 Q-NNN（sequencing / scope-aware opt-in / 员工目录 agents/ 合规）。
3. 回写 roadmap §1.5 阶段2 行。
