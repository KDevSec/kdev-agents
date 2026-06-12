# 评审专家(reviewer) 数字员工 · 接入设计（阶段3 第一刀 / L3 起步）

| 项 | 值 |
|---|---|
| 文档性质 | **brainstorming 设计稿 v0.2**（v0.2 对齐 [Q-017](../../../.kdev/memory/决策日志.md)：记忆 Step 深度他评移交蒸馏 audit stage，评审专家收为**单 mode**；v0.1 = 双 mode 初稿。本任务**只设计不实施**，不进 writing-plans）|
| lifecycle | design |
| 日期 | 2026-06-12 |
| 范围 | 把第 4 个员工**评审专家**从 sketch（搬 X3 的 checklist + 冲突仲裁）补到**实施级接入设计**：① 形态=canonical callee 员工 ② 本期实现「有 caller gate」的 6 评审能力子集 ③ 兑现 dev-engineer 3 deferred + req-architect 3 self gate 翻 reviewer-expert ④ 定位 = **项目产物评审单 mode**（记忆 Step 深度他评已由 [Q-017](../../../.kdev/memory/决策日志.md) 移交蒸馏 audit stage，**非评审专家职责**）⑤ 发函边界硬规。**defer**：核心 10 余 4（需求方向/迭代拆分/测试设计/测试执行）随 caller 员工建成补 · 扩展 6 默认关|
| 承 | [Q-011 阶段2 接入打法](../../../.kdev/memory/决策日志.md) · **[Q-016 本设计拍板](../../../.kdev/memory/决策日志.md)** · **[Q-017](../../../.kdev/memory/决策日志.md)**（修订 Q-016 fork-2：摘 mode-2，记忆 Step 他评移交蒸馏管道质量闸）· [Q-015 P-C1b 三层他评](../../../.kdev/memory/决策日志.md)（层1 基线 recorder / 层2 蒸馏闸）|
| 配套 | [概念模型与员工能力 合稿 v1.0 §8/§9/§12](../../framework/01-design/2026-06-10-02-KDev数字员工-概念模型与员工能力-合稿-v1.0.md) · [编排底座 合稿 v1.0 §2.1/§2.5/R3](../../framework/01-design/2026-06-10-03-KDev数字员工-编排底座-合稿-v1.0.md) · [记忆底座 合稿 v1.0 §5.2](../../framework/01-design/2026-06-10-05-KDev数字员工-记忆底座-合稿-v1.0.md) · [roadmap §6/§1.5.7/§1.5.8](../../framework/01-design/2026-06-06-01-数字员工整体设计路线图roadmap-v1.0.md) · [阶段2 接入设计 §0.5](./2026-06-07-阶段2-第二员工+记忆scope-design.md) |
| 复用 | 阶段1/2 已验证：kdev-core 底座(R1/R2/R3 + record-gate) · B 轨 handoff 协议（request/handoff json + run_in_background + handoff-read）· 通用 kdev-flow-driver（**仅 caller 复用，reviewer 自身不复用**）· canonical 员工形态（staff.yml + agents + standards） |
| X3 参考 | spike `/home/lyadmin/Projects/kdev-agents-x3/plugins/kdev-cluster-x3/`：12 评审节点 · 10 评审员 checklist · 冲突仲裁 SOP（搬范式，**不照抄二元 1-FAIL=总 FAIL**，用合稿百分制双重条件）|

---

## 0. 一句话

给集群加**第 4 个员工评审专家**——但它**不是 flow-owner**（不像 dev-engineer/req-architect 拥有线性 SOP flow），而是**被其他员工的 R3 review gate 发函调用**的 callee：被调时 fan-out 到对应评审能力、各出百分制评分表、inline 仲裁冲突、聚合成一个 gate verdict 回函。本期只建「有现成 caller gate」的 6 评审能力，兑现两个已建员工的 6 个评审 gate（dev 3 deferred + req 3 self → reviewer-expert）。评审专家**只做项目产物评审（单 mode）**——MQ-2 的「记忆 Step 他评」已由 [Q-017](../../../.kdev/memory/决策日志.md) 移交蒸馏管道质量闸（层2），不在评审专家职责内（详见 §2.4 / §7）。

---

## 0.5 命名规范（沿用 [阶段2 §0.5](./2026-06-07-阶段2-第二员工+记忆scope-design.md)）

canonical id **`reviewer`** / 中文 display **评审专家**（§0.5 已预留）。agent id = `reviewer-<cap>`；记忆 scope `.kdev/memory/staff/reviewer/`；handoff `handoffs/reviewer/`。所有机器路径用 `reviewer`，中文名只出现在 display 处。

---

## 1. 本轮 brainstorming 拍板（Q-016 决策摘要）

| # | 决策点 | 拍板 | 取舍依据 |
|---|---|---|---|
| 1 | **形态** | **canonical callee 员工**：是 kdev-team 员工（staff.yml/agents/standards），但 `node_table` 由 `dispatch_table` 取代，不跑自有 flow-state、不复用 kdev-flow-driver；被 caller gate 调用、寄生 caller flow 贡献 verdict | 评审是「请同事 review」的协作、不是线性工序；review episode = fan-out+aggregate，硬塞假 node-table 反误导（§2.1）|
| 2 | **承载他评（⟲ Q-017 修订）** | **单 mode**：评审专家只做项目产物评审。MQ-2「记忆 Step 深度他评」**摘除 mode-2**、移交蒸馏管道 audit stage（[Q-017](../../../.kdev/memory/决策日志.md) 层2）| 评审专家 6+1 标准评的是产物不是「记忆诚不诚实」（别扭嫁接）；蒸馏闸同节奏同语料 + 污染正好在蒸馏处放大 + 复活 Q-002 死的 misalignment 切片（§2.4 / §7）|
| 3 | **本期范围** | **有 caller 的 6 能力子集**：SR / 用户故事 / 原型 / 方案+架构 / 代码+质量 / 安全；核心 10 余 4（需求方向/迭代拆分/测试设计/测试执行）声明在案、随 caller 员工建成补；扩展 6 默认关留接口 | YAGNI：测试工程师未建→测试评审无 caller；req node-table 无 R1.5/R2.5 gate→需求方向/迭代拆分无 caller。建了也没人调（§2.2）|
| 4 | **接 gate** | **dev3 + req3**：dev-engineer 3 deferred（plan/code/sec）兑现真发函；req-architect 3 self（SR/AR+原型/方案）翻 reviewer-expert；机制统一 = L1 flow-config per-gate `reviewer: self\|reviewer-expert\|both`（默认 reviewer-expert，可回退 self）| 正对 MQ-2「自评不可信」动机；req 自评翻第三方才是他评的点；L1 可回退留逃生门（§2.3 / §5）|
| 5 | **发函边界** | **建议为主、拦截经 gate**：评审专家只产出评分表+分级建议、从不直接命令 caller；🔴阻断经双重通过条件强制 FAIL（有牙齿），但兑现走 caller flow 的有界回流+escalate（kdev-core 执行）| 守硬规 4/5（评审能力不直接对外）；质量底线由 gate `status=blocked` 不 force-accept 守（§8）|

---

## 2. 关键取舍 + 依据（⭐ 别丢）

### 2.1 为何 callee 而非 flow-owner（形态根因）

dev-engineer/req-architect 是 **flow-owner**：各自拥有一条线性 SOP（coding-flow / design-flow），`reviewer-orchestrator` 复用通用 `kdev-flow-driver` 驱动 kdev-core 引擎逐节点推进，自有 `.kdev/features/<slug>/flow-state.json`。

评审专家**结构不同**：它没有「IR→SR→AR→原型→方案」式线性工序。一次评审 = caller 到某个 R3 review gate 时，对**那一份产物**做 fan-out（多评审能力并行）+ 汇总 + 仲裁 + 回 verdict。这是**请求驱动**不是**流程驱动**。

| 维度 | flow-owner | reviewer(callee) |
|---|---|---|
| 自有 SOP flow | 有（线性 node-table）| **无** |
| 驱动 | reviewer-orchestrator 复用 kdev-flow-driver 推 kdev-core | **不复用 kdev-flow-driver**；被 caller gate 发函调用 |
| 账落哪 | 自己的 feature flow-state | **寄生 caller flow-state**，只贡献一个 gate verdict |
| `staff.yml` 字段 | `node_table:` SOP 序列 | `dispatch_table:` 评审路由清单（能力→agent→standards→阈值→评对象）|

> **诚实优先**：硬给评审专家造一个假 node-table（n0-intake→n1-fanout→n2-arbitrate→n3-report）能保对称，但它不是真 SOP——为 fan-out+aggregate 套一层 flow-state、与 caller gate 形成双层 flow、handoffs/feature-first 落位还要额外设计。callee 形态承认结构差异、最省机件（被否的「自有 review-flow」备选见 §10）。

### 2.2 为何只建 6 能力（本期范围根因）

评审能力**只有「有现成 caller gate」的才真能被调用**。当前已建 flow-owner 只有 dev-engineer + req-architect，其 review gate 决定了哪些评审能力本期有 caller：

- req-architect 现 node-table 只有 3 个 review gate：`g-sr-review`(sr.md) / `g-ar-proto-review`(AR+原型，**一闸两能力**) / `g-design-review`(design.md)。**无** R1.5(需求方向) / R2.5(迭代拆分) gate。
- dev-engineer 现 3 个 deferred reviewer-expert gate：`g-plan-review`(plan.md) / `g-code-review`(src+diff) / `g-sec-review`(security.md)。

去重后落 **6 评审能力**（见 §4）。核心 10 余 4 = 需求方向(无 gate) / 迭代拆分(无 gate) / 测试设计 / 测试执行覆盖度（测试工程师未建）→ 声明为目标能力集、随 caller 员工建成补，**本期不建空挂 agent**。

### 2.3 为何 dev3 + req3 都翻（接 gate 根因）

MQ-2 的活体实证是「**模型自评会 confabulate**」——self-review 与被评产物同一生成过程、共享盲区。req-architect 现 3 gate 是 `reviewer: self`（真自评），正是 MQ-2 警示的风险面；翻成第三方 `reviewer-expert` 才是「他评」的兑现点。dev 3 个本就标 `reviewer-expert` 但**阶段1 deferred**（record PASS --by deferred），现在兑现真发函。L1 flow-config 留 `self|reviewer-expert|both` 旋钮：env 受限或想省 token 时一行配置回退 self，不锁死。

### 2.4 记忆 Step 他评归属：Q-017 移交蒸馏 audit stage（评审专家单 mode）⭐

v0.1 曾把「记忆 Step 他评」设计成评审专家 mode-2（workflow-batch fan-out，承 Q-015）。[Q-017](../../../.kdev/memory/决策日志.md)（2026-06-13 用户拍板）**否掉这个嫁接**：记忆 Step 深度他评移交 `/kdev-memory-distill` 的 audit/质量闸，评审专家**只保留 mode-1（项目产物评审）**。

**三层他评定型**（各一节奏一职责，[P-C1b spec §5.8](2026-06-09-kdev-memory会话污染治理+评分可配-design.md)）：

| 层 | 谁 | 何时 | 职责 |
|---|---|---|---|
| 层1 基线 | P-C1b recorder（每步顺手）| **写入时**·每步实时 | 读真 transcript 出 `### 模型他评`（替换自评）、逮明显 confab |
| 层2 深度 | **蒸馏 audit stage**（归 `/kdev-memory-distill`）| **导出时**·批量跨步 | 跨步系统性失真审计、校准/推翻层1 分、标剔污染样本、复活 misalignment 信号 |
| 评审专家 | reviewer 6 能力（mode-1）| caller gate 驱动 | 评**项目产物**（SR/code/design…），**不评「记忆诚不诚实」** |

**为何 mode-2 摘除归蒸馏（Q-017 三理由）**：① **同节奏同语料**——蒸馏低频/批量/跨步读全量记忆，层2 深审同 cadence，本就该一趟跑；② **污染正好在蒸馏处放大**——失真在导出成训练数据那刻兑现伤害，质量闸该装 garbage-in 入口；③ **评审专家 6+1 标准是评产物的，不是评记忆诚不诚实的**——记忆审计用另一把刀（证据锚定/confab 检测/分数校准）。附带复活被 Q-002 打死的 `dataset-misalignment` 切片（层1 vs 层2 gap 作新对齐信号）。

> **本次 cross-check 结论**：评审专家 spec 与 P-C1b spec v0.5 现已一致——评审专家不碰记忆他评；记忆他评分层 = P-C1b 层1（写时）+ 蒸馏层2（读时）。roadmap §1.5.8 line 189 此前记的「评审专家 形态 = workflow-batch」**仅适用于已摘除的 mode-2**；roadmap 该行已由 Q-016 回写为 callee 形态 + 标注 mode-2 移交（line 189 现指 callee per-gate，不再 workflow-batch）。

### 2.5 X3 搬什么、不搬什么

| X3 范式 | 搬法 |
|---|---|
| 10 评审员独立 read-only agent（无 Write/Edit，物理隔离生产者）| **搬**：评审能力 agent 只读、不改产物（守硬规：修复是被评审员工的事）|
| 12 评审节点 R/D/T/F + 阻断/告警 + D2 并行 | **搬映射**：本期 6 能力对应 6 现有 gate；D2「代码+质量并行」对应 `g-code-review` 内 fan-out |
| checklist 每项 PASS/FAIL、1-FAIL=总 FAIL（二元零容忍）| **不照抄**：换合稿**百分制 + 双重通过条件**（总分≥阈值 AND 🔴=0），更细、能表达 tech-debt |
| 审查组长（轻组长）做冲突仲裁 | **不另设**：合稿已把仲裁收进 `reviewer-orchestrator`（§6）；X3 3 步 SOP 落为编排 inline |
| 评审员 model:opus | **沿用**：评审是高确定性设计判断，评审能力 agent + 编排 = opus |

---

## 3. 形态与契约：canonical callee 员工

### 3.1 staff.yml 条目（含 schema delta）

```yaml
employees:
  # ... dev-engineer / req-architect 不变 ...
  reviewer:
    display: 评审专家
    kind: callee                              # ⭐ 新增判别字段（flow-owner | callee）
    flow_skill: null                          # callee 无方法论 flow-skill
    dispatch_table: orchestration/reviewer.dispatch-table.yml   # ⭐ 取代 node_table
    standards_dir: standards/reviewer/        # 评审标准 markdown 根
    runtime_model: opus
    agents:
      - reviewer-orchestrator
      - reviewer-sr
      - reviewer-story
      - reviewer-prototype
      - reviewer-design
      - reviewer-code
      - reviewer-security
```

**schema delta（唯一动既有契约处）**：
- 新增 `kind: flow-owner | callee`（既有两员工补 `kind: flow-owner`，向后兼容——缺省视为 flow-owner）。
- callee 用 `dispatch_table` 取代 `node_table`（互斥）；新增 `standards_dir`。
- `test_staff.py` 须放宽「每员工有 node_table」断言为「flow-owner 有 node_table / callee 有 dispatch_table」。

### 3.2 dispatch-table（评审路由清单，非 flow）

`orchestration/reviewer.dispatch-table.yml`——声明式「评审能力 → agent → standards → 默认阈值 → 评对象 → caller gate」，是 reviewer 版的 node-agent-routing（不是会被 kdev-core 推进的 node-table）：

```yaml
# 评审专家 dispatch 路由（callee；被 caller R3 review gate 发函调用，不跑自有 flow）
capabilities:
  - {cap: sr,        agent: reviewer-sr,        standards: standards/reviewer/SR需求评审.md,   threshold: 80, target: sr.md,            caller_gate: [req-architect:g-sr-review]}
  - {cap: story,     agent: reviewer-story,     standards: standards/reviewer/用户故事评审.md, threshold: 80, target: 用户故事列表,        caller_gate: [req-architect:g-ar-proto-review]}
  - {cap: prototype, agent: reviewer-prototype, standards: standards/reviewer/原型评审.md,     threshold: 75, target: prototype/,         caller_gate: [req-architect:g-ar-proto-review]}
  - {cap: design,    agent: reviewer-design,    standards: standards/reviewer/方案架构评审.md, threshold: 85, target: [design.md, plan.md], caller_gate: [req-architect:g-design-review, dev-engineer:g-plan-review]}
  - {cap: code,      agent: reviewer-code,      standards: standards/reviewer/代码质量评审.md, threshold: 85, target: [src/, tests/, diff], caller_gate: [dev-engineer:g-code-review]}
  - {cap: security,  agent: reviewer-security,  standards: standards/reviewer/安全评审.md,     threshold: 85, target: [security.md, diff], caller_gate: [dev-engineer:g-sec-review]}
# deferred（随 caller 员工建成补，本期不建 agent）:
#   need-direction(需求方向) / iteration-split(迭代拆分)  ← req-architect 须先加 R1.5/R2.5 gate
#   test-design(测试设计) / test-coverage(测试执行覆盖度) ← 测试工程师建成后
# 扩展 6（默认关，留接口）: deploy / perf / docs / compliance / observability / a11y
```

### 3.3 agent 文件（7 个，照 canonical 形态）

每个 `plugins/kdev-team/agents/reviewer-*.md`，frontmatter `name`(裸 canonical id) + `description`(中文 display + 触发) + `model: opus`，正文 Identity / Principles / Critical Actions / Capabilities（同 req-architect-* 范本）。

- **reviewer-orchestrator**：被 caller 发函的入口。读 request → fan-out 对应 `reviewer-<cap>` → 收评分表 → inline 仲裁（§6）→ 双重条件聚合 verdict → 写 handoff。内置**终审聚合**（隐藏能力：汇总各节点已出分→交付报告，不重评）。**不复用 kdev-flow-driver**（无自有 flow）。
- **reviewer-<cap>**（6 个）：只读评审能力。Critical Actions = ① Read 产物 + standards + `recall(scope=/staff/reviewer, subject:review:<cap>)` ② 按 standards 维度打百分制分 + 标 🔴/🟡/⚪ + 写修订建议 ③ 出评分表（schema 见 §4.2）④ **不改产物**（守只读隔离）。

### 3.4 standards 落点（解既有契约缺口）

编排底座合稿 v1.0 **无** `standards_dir` 的 kdev-core 加载机制（探查确认「无」）。本设计**不引入加载魔法**：standards 是**插件内 markdown**，评审能力 agent 在 Critical Actions 里直接 `Read`（路径走约定 `${CLAUDE_PLUGIN_ROOT}/standards/reviewer/<cap>.md` 或 request 传入），与 req-architect agent Read design-flow references 同款。

```
plugins/kdev-team/standards/reviewer/
├── 通用评分模板.md        ← 100分制 schema + 双重通过条件 + 评审循环规则 + 🔴/🟡/⚪ 分级标准（所有能力共用）
├── SR需求评审.md          ├── 用户故事评审.md      ├── 原型评审.md
├── 方案架构评审.md        ├── 代码质量评审.md      └── 安全评审.md
```

每 cap standards 含：评审目的 · 评审对象 · 评分维度(3-5 项 + 每项 checklist) · 通过阈值(可覆盖默认) · 问题分级标准 · 评分表输出 schema（合稿 §12.6 规约）。

---

## 4. 本期 6 评审能力子集 + 评分 schema

### 4.1 能力 → caller gate 映射

| agent id | 评审能力 | 对应 caller gate | 评对象 | 阈值 | 备注 |
|---|---|---|---|---|---|
| `reviewer-sr` | SR 需求评审 | req `g-sr-review` | sr.md | 80 | 完整/清晰/可验收/方向对齐 |
| `reviewer-story` | 用户故事评审 | req `g-ar-proto-review`(AR) | 用户故事列表 | 80 | 粒度/可独立验收/回溯 SR/无漏无重 |
| `reviewer-prototype` | 原型评审 | req `g-ar-proto-review`(原型) | prototype/ | 75 | 可用性/一致性/UED/交互 |
| `reviewer-design` | 方案+架构评审（多触点）| req `g-design-review` + dev `g-plan-review` | design.md / plan.md | 85 | 事前方案可行 + plan 与 design 一致/Gate-A·B 合理 |
| `reviewer-code` | 代码+质量评审 | dev `g-code-review` | src/+tests/+diff | 85 | spec 一致/正确性/边界/TDD 真过 + 风格/抽象/命名 + **架构一致性事后** |
| `reviewer-security` | 安全评审 | dev `g-sec-review` | security.md+diff | 85 | OWASP/认证授权/数据安全/输入校验 |

> **一闸两能力**：`g-ar-proto-review` 同时触发 `reviewer-story` + `reviewer-prototype`，编排 fan-out 两个 agent 再聚合（验证多能力 gate）。**多触点单能力**：`reviewer-design` 被两个 gate 调用（req 评 design.md 事前 / dev 评 plan.md），standards 同源、评对象随 request。

### 4.2 评分表 schema（百分制 + 双重通过条件，合稿 §12.4）

每 `reviewer-<cap>` 输出（写 `handoffs/reviewer/<gate>.<cap>.score.md`）：

```
cap: code
target: <diff_range 或产物路径>
total: 82/100
dimensions:
  - {name: spec一致性, score: 22/25, notes: ...}
  - {name: 正确性+边界, score: 18/25, issues: [🔴 ...]}
  - {name: 风格抽象命名, score: 21/25}
  - {name: 架构一致性,   score: 21/25}
issues:
  - {level: 🔴阻断, file: src/x.py, line: 42, desc: ..., suggest: ...}
  - {level: 🟡重要, ...}
  - {level: ⚪轻微, ...}
verdict: FAIL          # 通过 = total≥阈值 AND 🔴=0；此处 🔴≠0 → FAIL
```

默认阈值（standards 可覆盖）：大部分 80 / 关键(代码·安全·方案) 85 / 创意(原型) 75 / 高风险(部署，扩展) 90。

---

## 5. 接 gate 机制：发函协作 6 步

复用 **B 轨 handoff 协议 + kdev-core record-gate**（零新引擎）：

```
caller 编排（产物 COMPLETE，到 review gate，merged config reviewer=reviewer-expert）
 ① 写 review 请求 → handoffs/reviewer/<gate>.request.json
     {target_paths[], caps[], standards_refs[], thresholds, request_id:<gate-node>,
      caller:<员工id>, diff_range?, transcript_ref?}
 ② 发函 dispatch kdev-team:reviewer-orchestrator（run_in_background:true，B 轨）
 ──────────────────────── reviewer-orchestrator ────────────────────────
 ③ handoff-read request → 并行 fan-out 对应 kdev-team:reviewer-<cap>
     每 cap: Read 产物 + standards + recall(/staff/reviewer, subject:review:<cap>)
             → 出百分制评分表（§4.2）
 ④ 收齐评分表 → inline 仲裁冲突（§6）→ 双重条件聚合 gate verdict
 ⑤ 写结果 → handoffs/reviewer/<gate>.handoff.json
     {verdict:PASS|FAIL, scores:[refs], counts:{🔴,🟡,⚪}, revisions:[分级建议], 仲裁:[...], by:reviewer-expert}
 ────────────────────────────────────────────────────────────────────────
 caller（completion 通知）⑥ handoff-read →
     python3 -m kdev_core record-gate <flow> <slug> --gate g-xxx --kind review
       --verdict PASS|FAIL --request-id <node> --by reviewer-expert --table <caller node-table>
```

**caller 侧改写（设计层，不实施）**：

| 文件 | 现状 | 改成 |
|---|---|---|
| `dev-engineer.node-table.yml` gate_specs | g-plan/code/sec-review `reviewer: reviewer-expert`（阶段1 deferred 处理）| 真发函（去 deferred）|
| `gate-decision-logic.md`「Reviewer-Expert Gate（阶段1 全 deferred）」节 | record PASS --by deferred | 改为「发函 reviewer 6 步 + record 真 verdict」|
| `req-architect.node-table.yml` gate_specs | 3 gate `reviewer: self` | `reviewer: reviewer-expert`（默认）|
| req-architect gate 判据节 | self 自评判据 | reviewer-expert 发函；self 判据保留作 L1 回退分支 |
| `node-agent-routing.md` | — | 追加 reviewer dispatch 段（caller→reviewer 发函上下文构造）|

**L1 flow-config 旋钮**：per-gate `reviewer: self | reviewer-expert | both`。`merged = merge(L0 node-table, L1 flow-config)` 决定本节点发不发函（编排底座 §2.5 SOP 三层）。默认 reviewer-expert；`both` = 发函 + 自评后 AskUserQuestion 复核；回退 `self` = 不发函（env 受限 / 省 token 逃生门）。

---

## 6. 冲突仲裁 + 评审循环

### 6.1 仲裁 inline 进 reviewer-orchestrator（不另设审查组长）

X3 的「冲突仲裁 3 步 SOP」落为编排 inline（合稿已把仲裁收进评审专家编排）：

1. 编排发现两能力对同产物相反结论（典型：`reviewer-code` PASS + 质量维度 FAIL，或 design vs code 架构判断矛盾）→ caller `events.jsonl` 留痕。
2. 编排读两份评分表找冲突点（同行号/同产物的相反结论）。
3. 出仲裁决策（≤200 字，写 `handoffs/reviewer/<gate>.arbitration.md`）：**偏向一方** → 被评审员工按该方修 → 重验另一方；**编排也犹豫** → 升级 CEO + 标元评审异常给 CQO。

### 6.2 评审循环（kdev-core 原生有界回流 + escalate）

- **双重通过条件**（每能力）：`通过 = total≥阈值 AND 🔴阻断=0`；**gate PASS = 所有 in-scope 能力 PASS**。
- FAIL 且 `gate_iters<3` → `on_reflow`：caller 编排读修订建议、**自主判断**哪些修(🟡/⚪ 可 tech-debt 化、🔴 必须处置)、重做 action 节点 → **增量评**（只评修订部分）→ `gate_iters++`。
- `gate_iters≥3` → `status=blocked` 升 CEO → 用户拍板 (a) 接受记 tech-debt / (b) 续修第 4 次 / (c) 推翻重做。**escalate 不 force-accept**（编排底座 R3：宁停不带病放行）。
- `request_id`（= gate-node）保证多轮评审 approval 不跨轮串扰（底座现状「只存不校验」，本设计不依赖强校验，沿用）。

---

## 7. 评审专家与 MQ-2 第三方他评：单 mode（记忆他评已外移）

评审专家**只承载一种调用 = 项目产物评审（mode-1，gate 驱动）**：

| | mode-1 项目产物评审（评审专家本期唯一职责）|
|---|---|
| 触发 | caller R3 review gate（§5）|
| 形态 | callee 同步 fan-out（§3）|
| 输入 | 产物 + standards |
| 输出 | 评分表 + verdict → handoffs/reviewer/ |
| 复用内核 | 6 评审能力 |
| 记忆落点（§5.2）| 评审经验（评得对/松/紧）→ `/staff/reviewer/` `subject:review:<cap>` **F-NNN**，蒸馏 `dataset-review-by-capability` |

**MQ-2「记忆 Step 他评」不在评审专家范围**——[Q-017](../../../.kdev/memory/决策日志.md) 已把它移交记忆侧三层质量闸（§2.4 表）：层1 = P-C1b recorder 写时 `### 模型他评`（替换自评、记录层修 MQ-2，本期 P-C1b 落地）；层2 = 蒸馏 audit stage 读时深度复评（校准层1 + 复活 misalignment，随蒸馏管道演进）。两层都在记忆/蒸馏管道里、blocked-on P-C1b 的 transcript 溯源，与评审专家**解耦**。

> v0.1 曾设 mode-2（评审专家读 transcript 出 `### 第三方他评`）——**已废**。理由见 §2.4：6+1 产物标准评不了「记忆诚不诚实」，且蒸馏才是污染放大的咽喉。评审专家保持纯粹「评产物」职责，不背记忆审计。

---

## 8. 发函边界硬规（建议 vs 拦截）

评审专家**只产出、不直接命令**另一员工（守[合稿 §10.1](../../framework/01-design/2026-06-10-02-KDev数字员工-概念模型与员工能力-合稿-v1.0.md) 硬规 4/5：评审能力不直接对外、跨员工走编排，评审专家只回函给请评审的员工编排）：

- **建议为主**：评分表 + 🔴/🟡/⚪ 分级修订建议。🟡/⚪ 由 caller 编排**自主判断**修 or tech-debt 化（「评审给建议、员工自主判断」）。
- **拦截经 gate、非评审专家单方**：🔴阻断项经**双重通过条件**强制该能力 FAIL（总分再高也不过）——有牙齿，但兑现路径是 caller flow 的**有界回流 + escalate**（kdev-core 执行），评审专家从不直接 halt/command caller。
- **3 次不过 → CEO → 用户拍板**：质量底线由 gate `status=blocked` 守，不自动降级接受。
- CQO 后台抽查这次协作是否合规（评审走过场/漏评），元评审评审专家（合稿 §11）。

---

## 9. 改写清单 + 落地切分（本任务**不实施**，留后续 plan）

**本步（设计，已做）**：本 spec + Q-016 决策 + 回写 roadmap §1.5.8/line 189。

**follow-up（未做，后续单独起 implementation plan，TDD）**：
1. `kdev-team`：staff.yml 加 reviewer 条目（schema delta `kind`/`dispatch_table`/`standards_dir`）+ `orchestration/reviewer.dispatch-table.yml` + 7 个 `agents/reviewer-*.md` + 6+1 份 `standards/reviewer/*.md`。
2. caller 改写：dev-engineer.node-table 去 deferred + req-architect.node-table self→reviewer-expert + gate-decision-logic 两段重写 + node-agent-routing 加 reviewer 段。
3. kdev-core / flow-config：L1 per-gate `reviewer` 旋钮 merge（若现引擎未支持 reviewer 覆盖，补 R3 一处）。
4. 测试：`test_staff.py` 放宽 callee 断言；新增 `test_reviewer_dispatch.py`（dispatch-table 合规 + 6 能力↔caller_gate 映射 + 发函 handoff schema）；caller 改写的 evals 兜（dev/req flow 行为不破）。
5. plugin version bump + marketplace 刷（守 G-004/G-009：plugin 改 agent 须 bump version + 用全名 `kdev-team:reviewer-*` 派单）。

**defer（声明在案，不本期）**：核心 10 余 4 评审能力（随 caller 员工建成）· 扩展 6 · 跨员工直接发函硬规完整体（v1.5 硬规 2/7）· CQO 元监督。（**记忆 Step 他评不在评审专家 defer 列**——已由 Q-017 移交蒸馏 audit stage / P-C1b 层1。）

---

## 10. 被否备选 + 非目标

**被否形态备选**：
- **自有 review-flow**（给 reviewer 也建 node-table + flow-state，每次被调跑薄 flow）：保对称但为 fan-out 套 flow-state、双层 flow、handoffs 落位额外设计——过度机件，否（§2.1）。
- **不建员工·下放 inline**（评审作各员工 gate 的 inline 自评强化）：违 MQ-2（自评 confabulate 必须独立第三方）+ blueprint（评审专家是独立员工），否。

**明确非目标（防镀金）**：本期不建测试评审/需求方向/迭代拆分能力（无 caller）· 不建扩展 6 · **不做记忆 Step 他评**（Q-017 已移交蒸馏 audit stage，非评审专家范围）· 不引入 kdev-core standards 加载魔法（agent 直接 Read）· 不另设 X3 审查组长（仲裁 inline）· 不动 CQO/HUD。

---

## 11. 验证（follow-up plan 阶段，本设计仅声明）

- **单测**：dispatch-table 合规 + 评分表 schema + 发函 handoff schema + staff callee 断言。
- **evals 不破**：dev-engineer coding-flow + req-architect design-flow 既有 evals 全绿（接 reviewer 后 gate 行为变但拓扑/回流语义不破）。
- **轻 dogfood**：req-architect 产 sr.md → `g-sr-review` 发函 `reviewer-sr` → 出评分表 + verdict → record-gate 真走一遍（≥1 个 gate 端到端）；dev-engineer `g-code-review` 同理走一遍。env 受限时 reviewer-expert 仍可跑（评审只读、不需后端环境）。

---

## 变更记录

| 日期 | 版本 | 变更 |
|---|---|---|
| 2026-06-12 | **brainstorming v0.1** | 评审专家接入设计：callee 形态 + 6 能力子集 + dev3/req3 接 gate + 双 mode 他评（mode-2 blocked-on P-C1b）+ 发函边界硬规；承 Q-016 |
| 2026-06-13 | **v0.2（对齐 Q-017）** | cross-check P-C1b spec v0.5 后**摘 mode-2**：记忆 Step 深度他评移交蒸馏管道 audit stage（层2），评审专家收为**单 mode**（项目产物评审）。改 范围/承/§0/§1#2/§2.4/§7/§9/§10 + 加三层他评定位（§2.4 表）；承 Q-017 |
