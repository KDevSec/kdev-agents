# 阶段1 接入设计 · P5：开发工程师 coding-flow 接 kdev-core 底座

| 项 | 值 |
|---|---|
| 文档性质 | **brainstorming 设计稿 v0.1**（待用户复核 → 转 writing-plans 起实施计划）|
| lifecycle | design |
| 日期 | 2026-06-06 |
| 范围 | 阶段1 = 开发工程师 coding-flow（13 节点 SOP）接 kdev-core lean 底座（R1/R2/R3）+ UED 6.0 改造 dogfood 首测。**本稿定接入设计的全部架构决策**，writing-plans 据此起 P5 实施计划 |
| Pass1 范围 | **T0 全局主题 + T1 登录页**（验底座端到端、不追分）|
| 关联决策 | [Q-004 起步 roadmap](../../../.kdev/memory/决策日志.md) · [Q-007 抽共性底座](../../../.kdev/memory/决策日志.md) · [Q-008 结构进底座/执行留flow](../../../.kdev/memory/决策日志.md) · [Q-009 git 托管](../../../.kdev/memory/决策日志.md) |
| 配套 | [起步 roadmap v0.1 §4](../../framework/01-design/2026-06-06-01-数字员工整体设计路线图roadmap-v1.0.md) · [底座设计总纲 v1.0](../../framework/01-design/2026-06-05-01-kdev-core底座设计总纲-v1.0.md) · [员工能力专项 v1.5 §2.3/§3.2](../../framework/01-design/2026-05-28-01-KDev数字员工架构-员工能力专项-v1.5.md) · [BMAD Agent 借鉴点](../../framework/04-references/2026-06-05-08-BMAD-Agent体系借鉴点-员工编排prompt骨架.md) |
| 引擎现状 | `plugins/kdev-core/kdev_core/`：R1 flow_state · R2 node_machine · R3 gate（66 测试绿，main 已 push）|
| 被接对象 | `plugins/kdev-coding-flow/skills/kdev-coding-flow/SKILL.md`（13 节点 SOP，现纯 prompt、无状态机）|
| dogfood 题 | `测试题目/EXAM-PROMPT.md` + `01-pic/`（3 原型）+ `02-ued6.0/`（UED 硬约束+§10 自检）|

---

## 0. 一句话

把开发工程师的**编排能力**（coding-flow 的 13 节点 SOP）从"prose 隐式编排"换成 **kdev-core 引擎显式驱动**（经一层薄 CLI），并按 BMAD persona 模型把这个员工落成 **1 编排 Agent + N 业务 Agent**；在 UED 6.0 改造 dogfood 的 T0+T1 小切片上端到端跑通，证明 R1/R2/R3 真在驱动（resume / 有界回流 / 三类 gate / escalate）。

---

## 1. 本轮 brainstorming 拍板（决策摘要）

| # | 决策点 | 拍板 |
|---|---|---|
| 1 | 接入形态 | **node-table config + 薄 driver，SKILL.md 加「接底座入口」节**（不重写方法论正文）|
| 2 | Agent 模型 | **Agent = BMAD persona（带技能菜单的角色），≠ skill**；开发工程师 = 1 编排 + 6 业务 Agent |
| 3 | Agent 实例化粒度 | **切片驱动 + 轻量 persona**：建编排 + T0/T1 真用到的业务 Agent，安全扫描走轻量 |
| 4 | 驱动机制 | **CLI 做编排**（harness-中立、可被自主接管）+ **hook 阶段3 当护栏** + **自动档 = policy 开关** |
| 5 | gate 评审归属 | **自评 vs 第三方评审分离**：自评→开发工程师本人；第三方评审→评审专家 Agent（阶段1 defer）；gate 带 `reviewer` 绑定，升级只翻绑定 |
| 6 | node 9 拆分 | **拆 9a 代码/质量评审（review）+ 9b Per-Increment E2E（acceptance）** |
| 7 | 视觉改造验证 | 非 TDD → 走「前端/视觉验证支路」：build + UED §10 机检 + 视觉 diff + 功能冒烟，全自评可机检 |

---

## 2. 关键设计取舍 + 依据（⭐ 别丢：这是对话磨出来的，不是拍脑袋）

### 2.1 Agent ≠ skill —— BMAD persona 模型

**Agent = 带人格的角色 + 一张技能菜单**（BMAD §2 骨架：`Identity / Communication Style / Principles / Critical Actions / Capabilities 路由表 / On Activation`）；**Capabilities 表里每项才路由到 skill**。所以 Agent 是"谁"、skill 是"它会的招"，**单个 Agent 调多个 skill**。

对到 v1.5 §2.3：**开发工程师 = 1 编排 Agent + 6 业务能力 Agent = 7 个 agent**：

| | Agent | 产出 | 内部会调的 skill（示例）|
|---|---|---|---|
| 编排 | 开发工程师-编排 | 阶段聚合报告 | 调度 6 业务 + 跨员工发函 + §3.2 监督/标准/聚合/应急 |
| 业务 | 环境准备 | env.md | — |
| 业务 | 实施计划 | plan.md | writing-plans · plan-eng-review |
| 业务 | TDD 实现 | src/+tests/ | test-driven-development · subagent-driven-development |
| 业务 | E2E 验收 | e2e-results | gstack-qa · playwright |
| 业务 | 安全扫描 | security.md | kdev-secure-coding |
| 业务 | 部署上线 | release notes | finishing-a-development-branch |

> "接底座" = coding-flow 这个**编排 Agent** 把隐式编排（prose "下一步去节点X"）换成 kdev-core 引擎显式驱动，并按 **SOP 三层**（L0 node-table + L1 flow-config + L2 自主，v1.5 §6.2）派自家业务 Agent（硬规5：业务能力只对自家编排）。

### 2.2 CLI vs hook —— 选 CLI 的三层依据

**(a) 对 Claude Code 的依赖度**：要分清**引擎**（kdev-core 纯 Python，真 harness-中立）和**驱动者**（决定"何时推进"的 LLM，仍在 harness）。CLI 让引擎脱离 harness，并把耦合压到最薄一层——"能发一条 shell 命令"，任何 harness（CC/Gemini/Copilot/SDK/人）都满足；换 harness 引擎+node-table+gate 逻辑一行不改。hook 把推进逻辑焊进 CC 的 `hooks.json` + runtime 事件生命周期，换 harness 要重写。**耦合深度差一个数量级**（CLI≈二进制/REST 接口，hook≈编译进某 App 私有 ABI 的插件）。

**(b) 自主编排（替代内置 SOP）**：自主性住在"**谁写 node-table**"（L0 内置 → L2 自主生成），不在引擎机制。CLI 把流程图当**数据**（`load_node_table(dict)` + 纯函数 `advance`），员工可现生成/覆盖 node-table → 天然支持；引擎安全不变量（有界回流 / escalate 不 force-accept / 双重计数）照旧兜底。hook 把推进当**代码**焊在 runtime 配置里，Agent 没法干净替换 → 反而堵死自主编排。

**(c) 升自动档**：「自动档」是 **policy 属性**（gate 谁来拍：人 vs Agent 自决），**不是 mechanism 属性**。两档调同一条 CLI：
```
手动档 (L2)：  到 gate → 停(awaiting_human) → 人确认 → Agent 调 CLI advance → 继续
自动档 (Auto)： 到 gate → Agent 自拍 verdict(decider:ai) → Agent 调 CLI advance → 循环到 terminal
```
CLI 把 Agent 留在驾驶位 = 真自主的底材；把 hook 升成编排器才会把 Agent 踢出驾驶位、挡自动档。coding-flow 现有的 Auto Mode 本就和"调 CLI/hook"正交。

**CLI 唯一短板**：靠 Agent 自觉调（忘了调→状态脱节）→ 用 persona 的 Critical Actions 纪律 + 完成验证 gate 兜，**阶段3 加 hook 当强制护栏**（catch "干了活没 record_gate""想 force-accept"）。R3 escalate(FAIL≥max→BLOCKED) 已内置，自动档开箱安全。

> **成熟架构 = CLI 做编排（可移植、可被自主接管）+ hook（阶段3）做强制护栏 + 自动档=policy 开关**，全叠在 CLI 上。

### 2.3 自评 vs 第三方评审 —— gate 的 reviewer 绑定演进

🔴 **开发工程师可以自评，但第三方评审必须来自评审专家员工的 Agent 能力**（用户定）。落到 gate = 每个 review/acceptance gate 带一个 `reviewer` 绑定：

| gate | 类型 | reviewer（阶段1）| reviewer（阶段3 升级）|
|---|---|---|---|
| node 8 完成验证（build/lint/UED 机检）| **自评** | 开发工程师本人 | 不变 |
| UED §10 自检清单 → CHECKLIST.md | **自评** | 开发工程师本人 | 不变 |
| node 9b / 12 acceptance（build+视觉diff+冒烟）| **自评** | 开发工程师本人 | 不变 |
| node 4 方案评审 | **第三方** | ⏸️ defer | 评审专家·方案评审 |
| node 9a 代码/质量评审 | **第三方** | ⏸️ defer | 评审专家·代码/质量评审 |
| node 10 安全评审 | **第三方** | ⏸️ defer | 评审专家·安全评审 |

**设计红利**：node-table 的 gate **结构不变**，升级只把 `reviewer` 从「自评」翻成「评审专家.<能力>」——干净演进路径。**阶段1 R3 三类全靠开发工程师自己的 gate 跑通**（decision=Gate-A/B · review=node8+UED§10 自评 · acceptance=node9b/12 自评），**完全不需要评审专家、也不假装有**。

---

## 3. 架构三层（阶段1 态，无 CEO/CQO）

```
主控(阶段1 兼 CEO 角色)
  └─ Agent({subagent_type:"开发工程师-编排"})        ← coding-flow = 这个编排 persona Agent
       ├─ 读 node-table.yml（SOP 结构, L0）
       ├─ 用薄 CLI 驱动 kdev-core 引擎 (R1 flow-state / R2 advance / R3 record_gate)
       └─ 在工作节点内嵌派自家业务 Agent
  gate 节点 → awaiting_human 停靠 → 回主控 L2 确认（自动档=去掉这一停）
```

- **引擎层**：kdev-core 纯 Python (R1/R2/R3) + 新增薄 CLI（harness-中立）。
- **编排层**：开发工程师-编排 persona Agent。
- **业务层**：轻量 persona Agent（切片驱动）。

---

## 4. Persona Agent 集（切片驱动 + 轻量 persona）

轻量 persona 结构 = `Identity / Principles / Critical Actions / Capabilities 菜单`（省 BMAD 的 First Breath / 记忆形态 / Communication Style 长篇）。

| Agent（subagent_type）| 角色 | 阶段1 用到 | 运行时模型 |
|---|---|---|---|
| **开发工程师-编排** | 驱动引擎 + 派业务 + 阶段聚合 | ✅ | opus |
| 环境准备 | clone RuoYi + 读 UED materials + 蒸馏 rules.md → env.md | ✅ | **opus（暂）** |
| 实施计划 | Gate-A/B 输入 + PLAN.md | ✅ | **opus（暂）** |
| 前端实现 | 改 src（视觉改造，非红绿）| ✅ | **opus（暂）** |
| E2E视觉验收 | build+视觉diff+冒烟 | ✅ | **opus（暂）** |
| 部署上线 | 合并 + 起被测环境 | ✅ | **opus（暂）** |
| 安全扫描 | 纯视觉改→轻量一趟 security.md | ⚠️轻量 | **opus（暂）** |

> Critical Actions 硬写编排纪律："每过一个节点/gate，必须调 CLI `advance`/`record-gate`"——补 CLI"靠自觉"短板。
>
> **运行时模型（暂统一 Opus）**：阶段1 首测**业务 Agent 暂全用 Opus**（例外升档——承 roadmap 铁规"kdev-core 全新架构例外升档"，首跑求 max 可靠性、降 sonnet BLOCKED 风险）。模型是 **L1 `flow-config.yml` 配置项**（编排 Agent 读它 → `Agent({model})` 派单，per-Agent 可配），**用户可自行切回 CLAUDE.md 二档**（业务实现 sonnet / 编排+评审决策 opus）省 token。编排 Agent 始终 opus（二档=评审决策档）。

---

## 5. node-table.yml + gate_specs.yml（13 节点映射）

| 节点 | R2 kind | R3 gate | reviewer（阶段1 / 阶段3）| 派业务 Agent |
|---|---|---|---|---|
| 0 背景对齐 | action | — | — | 环境准备 |
| 1 关联度 Gate-A | gate | **decision** | 编排自决 | — |
| 2 worktree | action | — | — | 编排 |
| 3 写 plan | action | — | — | 实施计划 |
| 4 方案评审 | gate | review | 第三方→评审专家（阶段1 defer/config-off）| — |
| 5 复杂度 Gate-B | gate | **decision** | 编排自决 | — |
| 6·7 实现 | action | — | — | 前端实现 |
| 8 完成验证 | gate | **review** | 自评→开发工程师（build+lint+UED §10 机检）| 前端实现自验 |
| 9a 代码/质量评审 | gate | review | 第三方→评审专家（阶段1 defer）| — |
| 9b Per-Increment E2E | gate | **acceptance** | 自评→开发工程师 | E2E视觉验收 |
| 10 安全评审 | gate | review | 第三方→评审专家（阶段1 defer；安全扫描 Agent 仍出轻量 security.md）| 安全扫描 |
| 11 合并 | action | — | — | 部署上线 |
| 12 部署+金丝雀 | gate | **acceptance** | 自评→开发工程师（build+视觉diff+登录冒烟+CHECKLIST.md）| 部署上线 + E2E视觉验收 |
| 13 清点 | terminal | — | 编排 ③聚合 | — |
| terminal-fail | terminal | — | 编排 ④应急（escalate 落点）| — |

- **13 节点全留**（压测底座，Q-004 不砍节点）。
- gate_specs 形态（参 R3 gate.py）：`{gid: {kind, on_pass, on_reflow, reviewer}}`（decision 用 `branches`）。`reviewer` 是阶段1 新增字段，引擎按它决定派谁判（阶段1 自评 inline / 第三方 defer）。
- **阶段1 实跑的 gate** = decision(1,5) + 自评 review(8) + 自评 acceptance(9b,12)；第三方评审(4,9a,10) 结构在但 config-deferred。

---

## 6. 前端/视觉验证支路（非 TDD）

视觉改造主体非红绿可驱动，验证全走**客观可机检 + 自评**：

- **节点 7 前端实现**：改 Element Plus 主题 token + 全局样式（T0）+ 登录页（T1），对照 `login.png`，不假设红绿。
- **节点 8 完成验证（自评 review 闸）**：`npm run build` 通过 + lint + **UED §10 grep**（禁裸 hex/rgb · 8px 网格 · 字体白名单 · 禁"登陆"）替代"跑单测"。FAIL→reflow 节点7。
- **节点 9b / 12 验收（自评 acceptance 闸）**：build 通过 + **视觉 diff**（playwright 截图 vs `login.png`，双分辨率 1366/1920）+ **功能冒烟**（登录金丝雀：真打开登录页→填账号密码验证码→点登录→断言进首页）+ UED §10 `CHECKLIST.md` 逐项附证据。
- verdict 来源 = 机检信号 + 自评，**结构化进 GateResult**（带 request_id/iter/verdict），下游不靠正则。

---

## 7. CLI 接口（新增，属 kdev-core）

```
python -m kdev_core init   <flow> <slug> --display-name ... [--auto-mode]
python -m kdev_core show    <flow> <slug>                  # 当前 node + history
python -m kdev_core advance <flow> <slug> <to_node> [--reflow] [--reason ...] --table node-table.yml
python -m kdev_core record-gate <flow> <slug> --gate g-xxx --kind review|decision|acceptance \
        --verdict PASS|FAIL|<branch> --request-id ... [--issues ...] --table node-table.yml
python -m kdev_core resume  <flow> <slug>                  # 校验 in_progress 并回当前 node
```

薄壳 = argparse + yaml 加载 node-table/gate_specs + 调 R1/R2/R3 的 `*_persist`。**这层就是集成 smoke 的接缝**（pytest 直接调 CLI 断言 flow-state.json）。

---

## 8. Pass1 验收 + 刻意构造的底座证据

不追分，专证"R1/R2/R3 真在驱动、不是 prompt 演戏"：

1. **R3 三类各跑通**：decision(节点1/5) · 自评 review(节点8) · 自评 acceptance(节点12)。
2. **刻意构造 1 次 FAIL→修→重评闭环**：节点8 UED grep 抓到一处裸 hex → reflow 节点7 → 修 → 重评 PASS（验 R3 gate_iters + R2 有界回流）。
3. **刻意 kill→resume**：跑到中段 kill 进程 → `resume` 从 `current_node` 正确续（非从头）。
4. **escalate 不 force-accept**：构造一次自评 review 连续 FAIL≥max → 转 BLOCKED 升人工。
5. **集成 smoke**：pytest 调 CLI 跑 full-lifecycle + resume-after-interrupt（参 X3 smoke 模式）。

---

## 9. 文件布局

**框架侧**（kdev-agents repo，提交）：
- `plugins/kdev-core/kdev_core/cli.py`（新）+ 测试
- `plugins/kdev-coding-flow/skills/kdev-coding-flow/orchestration/node-table.yml` + `gate_specs.yml`（新）
- `plugins/kdev-coding-flow/skills/kdev-coding-flow/personas/*.md`（新，6+1 轻量 persona）
- `SKILL.md` 加一节「接 kdev-core 底座入口」（不重写正文方法论）

**dogfood 侧**（独立 workspace，**不进框架 repo**，防 RuoYi 大 clone 污染）：
- 推荐 `~/Projects/kdev-dogfood-ued6/`：`RuoYi-Vue3-FastAPI/`(clone) + `materials/`(指向 `测试题目/`) + `delivery/`(七件套) + `.kdev/flows/coding-flow/ued6-restyle/flow-state.json`(运行态)

---

## 10. 非目标（防镀金）

评审专家(阶段3) · scope+JSONL 记忆(阶段2) · CQO(阶段4) · 多员工协作 · HUD 完整体(阶段3) · hook 护栏(阶段3) · L2 自主生成 node-table(不 foreclose，阶段1 不做) · 安全扫描深做(纯视觉改→轻量) · 追竞赛分(Pass2)。

---

## 11. 下一步 + 待回写

1. 用户复核本稿 → 转 **superpowers:writing-plans** 起 P5 实施计划（落 `docs/superpowers/plans/2026-06-06-阶段1-coding-flow接底座.md`）。
2. **回写 roadmap §1.5 / §4.3**：阶段1 行加本设计稿链接；§4.3 "R3 review(代码/质量)各跑通"精确化为"阶段1 R3 review 由自评 gate(节点8+UED§10)跑通，代码/质量第三方评审 defer 阶段3 评审专家"。
3. 决策沉淀：本轮 7 条拍板（§1）按需补 Q-NNN（接入形态 / Agent 模型 / CLI vs hook / 自评-第三方分离）。
