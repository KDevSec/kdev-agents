# CQO 监督员（元监督 / Chief Quality Officer）— 设计提案（草案）

| 项 | 值 |
|---|---|
| 文档状态 | 🟡 **草案（待用户评审）** —— 只设计、不实现、不改代码 |
| 日期 | 2026-06-18 |
| 作者 | ly（设计对齐：opus 主控） |
| 关联路线图 | roadmap-v1.0 §1.5.9 矩阵「CQO 元监督/合规审计 ❌ L4 defer」+ §阶段4「CQO + 自演进 + 跨IDE（L4 北极星）」 |
| 研究依据 | [架构补遗 §四 自演进 + §五 Worker Preamble §222](../../framework/04-references/2026-05-30-05-数字员工架构补遗-多agent+自演进+跨IDE.md)（plateau/circuit-breaker 双信号 + self-improve 算法骨架 + recall(/staff/*) + `cqo_supervision:` config 骨架 §368）· [CrewAI 借鉴 §4 Event Bus](../../framework/04-references/2026-06-05-09-CrewAI架构借鉴点-员工记忆Scope+委派+事件总线.md)（常驻监听「每条事件抽查」+ 20+ 事件 taxonomy） |
| 依赖前置 | **实施排在「kdev 单插件化 refactor 结构合并之后」**（[单插件化 spec](2026-06-18-kdev单插件化+去第三方+bootstrap安装-design.md)）——直接建进单插件 `kdev/` 结构，不先建后迁。见 §9 |
| 现状坐实 | kdev-core `events.py`（transition/gate/dispatch 三事件类）· `gate.py`（R3 escalate=status=blocked，无 force-accept）· hud `datasource.py`（已有 `_alerts`：blocked + gate_fail）· CEO 编排路由器（主会话 skill，非 Agent）· reviewer 回函 `anomaly.escalate=CQO` 字段已埋 |

---

# 0. 一句话定位

**CQO 是治理层，不是又一个 gate 评审员。** 评审专家（reviewer）管「**单个产物在 gate 上的质量**」（打分、PASS/FAIL）；CQO 管「**整条流水线的过程 / 行为质量 + 自演进信号**」——gate 有没有真过、TDD 有没有真刷绿、员工有没有跑偏、反复失败该不该断路升人。CQO 补集群当前缺失的**监督象限**（roadmap §1.5.9 矩阵「监督象限无人」），消费**现有基础设施**（events.jsonl / kdev-memory / hud），**不重造**。

---

# 1. 概要

CQO（Chief Quality Officer / 元监督）是 kdev 数字员工集群里**已设计、未建**的第 6 个角色（6 人愿景 = CEO + CQO + 4 业务员工，roadmap §1.5.9）。本提案设计它的**形态、监听机制、双信号、动作、scope 与集成边界**，回答研究里悬而未答的核心张力——「常驻后台监听」在 Claude Code（无真 daemon）里**到底怎么落地**。

核心设计选择（每条都指回真实文件 / 研究结论）：

1. **形态 = 抽查审计员（callee 类），不是 flow-owner，也不是常驻进程。** 结构上类比 reviewer（被发函、无自有 flow），但**职能正交**：reviewer 评产物，CQO 评过程。
2. **「常驻监听」= hook 驱动的批量抽查 + checkpoint 节点发函**，三层落地（§4）。**否决**「真 daemon 轮询」（CC 没有常驻进程模型）。
3. **双信号拆开**（架构补遗 §4.1 self-improve 算法骨架）：**plateau（停滞）**→ 提示/解阻；**circuit-breaker（反复失败）**→ 断路升人。circuit-breaker 的一半**引擎里已经有**（`gate.py` FAIL≥cap → `status=blocked`），CQO 是它的**消费者 + 跨 flow 聚合者**，不重造。
4. **消费现有事件账，不造第二本账**（承 P-C2 spec「不造第二本账」原则）：CQO 读 `events.jsonl`（actor 过滤）+ kdev-memory Step/记录 + reviewer 回函 `anomaly` 字段。产物 = 审计报告写 `staff/cqo/` scope（roadmap 已为 CQO 留此 scope）。
5. **审计结果回给 CEO，不直接拦流。** CQO 出告警 / 建议 / verdict，处置权（回流 / 升人 / 放行）在 CEO 编排——与 reviewer「建议非拦截」同范式。

---

# 2. 背景与驱动

## 2.1 监督象限当前无人

roadmap §1.5.9 能力矩阵明确：4 业务员工（dev / req / test / reviewer）+ CEO 总编排 MVP 已建，**CQO「❌ L4 defer」**，且 2026-06-14 接缝评审 接缝10 确认「监督象限无人」。当前集群能跑完一条 R→D→T→F 全链，但**没有任何角色对「这条链跑得对不对」负责**——只有 reviewer 在每个 gate 上点头，没有人看「gate 是不是被糊弄过去了 / TDD 是不是假绿 / 同一个错误是不是已经撞了 3 次该升人了」。

## 2.2 研究里 CQO 的设计意图（逐条坐实）

| 来源 | CQO 相关设计意图 |
|---|---|
| 架构补遗 §2.3 / §8.2 + CrewAI 借鉴 §1.1 | scope `/staff/cqo`、`recall(scope=/staff/*)` 跨员工查询（CEO/CQO 专属跨 scope 视野） |
| 架构补遗 §4.1 表 `self-improve` 行 | **「self-improve = CQO 监督的算法骨架」**：终止条件 = `plateau OR circuit-breaker OR max_iter` |
| 架构补遗 §4.2 表「Plateau + circuit breaker 双信号」行 | **「CQO 监督拆两种信号——停滞 vs 反复失败，触发不同动作」** |
| 架构补遗 §8.3 `cqo_supervision:` config 骨架（≈368 行） | `signals: {plateau: {threshold, window, action: prompt_user_for_unblock}, circuit_breaker: {threshold:3, action: escalate_to_ceo}}` |
| CrewAI 借鉴 §4 + 架构补遗 §七 | **「CQO 元监督（常驻后台监听『每条事件都抽查』）+ HUD 实时事件订阅都需要一个事件分类体系」**，CrewAI 20+ 事件类是现成 taxonomy 参考 |
| reviewer-orchestrator.md / 通用评分模板 §冲突仲裁 | reviewer 仲裁裁不动 → `anomaly.escalate=CQO`（元评审异常告警通道**已埋**，等 CQO 来消费） |

## 2.3 可消费的现有基础设施（已坐实存在）

- **kdev-core `events.jsonl`**（per-feature，append-only）：3 事件类 `transition`（R2 流转）/ `gate`（R3 判定，带 verdict/iter/issues/by）/ `dispatch`（CEO 派单 start/done + usage）。CLI `python3 -m kdev_core events <slug>` 可读。
- **kdev-core `gate.py`**：FAIL 且 `iter>=cap` → `status="blocked"` + `blocked_reason`，**绝不 force-accept**（circuit-breaker 的引擎侧一半已落地）。
- **kdev-hud `datasource._alerts()`**：已从 events 派生 `blocked` + `gate_fail` 两类 alert。CQO 与 HUD **配对消费同一份 events**（HUD 渲染当前态，CQO 审计行为质量）。
- **kdev-memory**：`staff/cqo/` scope 已在目录模型里预留（P-C2 spec「staff 稀疏：仅 reviewer + cqo」）；`recall(scope=/staff/*)` 跨员工查询设计已定。
- **reviewer 回函 `anomaly` 字段**：`{type: meta-review-conflict|arbitration-undecided, escalate: CEO|CQO}` 已是 reviewer-orchestrator 回函 schema 一部分。

---

# 3. 定位与边界

## 3.1 CQO vs 评审专家（reviewer）对照表 ⭐

| 维度 | 评审专家 reviewer | CQO 监督员 |
|---|---|---|
| **管什么** | 单个**产物**在 gate 上的质量（sr.md / code / design…） | 整条**流水线**的过程 / 行为质量 + 自演进信号 |
| **问的问题** | 「这份产物达标吗？」（打分 PASS/FAIL） | 「gate 真过了吗？TDD 真绿吗？员工跑偏了吗？该断路升人吗？」 |
| **触发** | caller 的 review gate **发函**（请求驱动，逐产物） | 事件流抽查 + checkpoint 发函（过程驱动，跨 gate / 跨 flow） |
| **输入** | `target_paths[]` + standards + 阈值 | `events.jsonl` + reviewer 回函 + kdev-memory Step + transcript 指针 |
| **输出** | 百分制评分表 + 🔴/🟡/⚪ + gate verdict | 审计报告 + 双信号判定（continue/retry/escalate）+ 告警 |
| **形态** | callee（被发函，无自有 flow，寄生 caller flow） | **callee 类**（被发函 / hook 触发，无自有 flow，寄生集群运行） |
| **有牙齿吗** | 🔴 经双重通过条件强制该 gate FAIL（兑现走 caller 有界回流） | **建议非拦截**——告警 + verdict 回 CEO，处置权在 CEO |
| **视野 scope** | `/staff/reviewer`（评审经验） + 当前产物 | `/staff/cqo` + `recall(/staff/*)` **跨员工全景** |
| **层级** | 质量闸（gate 上的一道关） | **治理层**（盯所有 gate + 所有 flow 的元层） |

**一句话区分**：reviewer 是「**质检员**」站在每道工序的关口验货；CQO 是「**质量总监**」翻生产记录看「这批货的工序流程本身有没有问题、要不要停线」。CQO **不重新评 reviewer 已评过的产物**（不当二审），它评的是「评审 / 开发 / 测试这些**过程动作**的合规与健康度」。

## 3.2 CQO 形态 = callee 类（不是 flow-owner，不是 daemon）

承 staff.yml 的 `kind` 模型（flow-owner vs callee）。CQO 结构上**最接近 reviewer 的 callee**：

- **不 own flow**：不复用 `kdev-flow-driver`、不持有自己的 `flow-state.json`、不写 `features/<slug>/` 流程账（与 reviewer 同，守 G-008 不造假 node-table）。
- **被驱动，不主动跑**：要么被 hook 触发批量抽查，要么被 CEO checkpoint 发函（§4）。
- **产物落自己 scope**：审计报告写 `staff/cqo/`，告警经回函 / 事件指针交 CEO，**不碰别人状态机**（与 reviewer「不碰 caller events.jsonl」对称）。

但与 reviewer 有**两点关键不同**：
1. reviewer 由 caller 的 review gate 一对一发函；CQO 的触发更**广谱**（跨 gate / 跨 flow / hook 批量），不绑单一 gate。
2. reviewer 只读单一产物目录；CQO 有 `recall(/staff/*)` **跨员工视野**（与 CEO 同档的特权 scope）。

> **未决 D-1**：CQO 是否进 `staff.yml` 当第 6 个 `employees:` 条目（`kind: callee` 新变体，如 `kind: supervisor`）？还是它根本不是「员工」而是底座 / CEO 的一个**附属审计能力**？倾向前者（保持「6 人团队」隐喻一致 + 复用 callee 派单基建），但 `kind` 取值需用户拍。

---

# 4. 架构：「常驻监听」在 Claude Code 怎么落地（核心张力的解）⭐

## 4.1 张力陈述

研究反复写 CQO「**常驻后台监听、每条事件都抽查**」（CrewAI 借鉴 §4）。但 **Claude Code 的 subagent 不是真正的常驻 daemon**——没有一个一直活着、订阅事件总线、逐条 push 触发的进程。`events.jsonl` 是 file-based append-only 流（不是 in-memory pub/sub）。所以「常驻监听」必须翻译成 CC 原生机制。**否决**「起一个后台 python 进程 tail events.jsonl」——它脱离 CC 会话生命周期、跨平台脆、且违背「主会话是状态唯一权威」。

## 4.2 三层落地机制（推荐：分层组合，非三选一）

| 层 | 机制 | 触发时机 | 抽查粒度 | 落地依据 |
|---|---|---|---|---|
| **L-a 逐事件 hook 抽查（轻）** | CC `PostToolUse` hook（matcher=`Bash`）拦截 `python3 -m kdev_core record-gate / advance` 调用后，跑一段**纯 python、零 LLM** 的规则检查（读刚写入的 events 尾 + flow-state），命中可疑模式 → 写 `staff/cqo/WARN-*.md` 信号文件 | 每次 gate 判定 / 流转落账后 | 单事件级，规则匹配 | **kdev-memory 已有同款 hook 范式**：`PostToolUse` matcher=`Bash` → `commit-tracker.py`。CQO 复用同一 hook framework（单插件化后 hooks.json 同根） |
| **L-b checkpoint 批量审计（重）** | CEO 编排在**特定节点**（阶段交界 / human_gate / flow 收尾）发函 `kdev:cqo-orchestrator`，CQO 一次性读该段 events + reviewer 回函 + Step，跑 LLM 深度抽查，出审计报告 | 阶段交界 / 收尾 / 用户问「这条链健康吗」 | 一段流水线，LLM 研判 | 编排路由器 spec §4「human_gates 停人闸」是天然 checkpoint；CEO 已是发函中枢 |
| **L-c 信号汇聚（CEO 侧）** | CEO 主 loop 在每棒之间读 `staff/cqo/WARN-*.md` + events alert，决定是否插入一次 L-b 深审 / 提示用户 / 升级 | CEO for-loop 每棒间隙 | 跨棒次聚合 | CEO 编排已是主会话 for-loop（spec §5），有天然「棒间」决策点 |

**为什么三层而非纯 hook 或纯发函**：
- 纯 hook（L-a）便宜但**不能跑 LLM**（hook 是同步阻塞、5s 超时，kdev-memory hook 全是纯 python）——只能做规则匹配，抓不了「TDD 是不是假绿」这种需要读 transcript 推理的事。
- 纯发函（L-b）能深审但**贵且不连续**——不可能每条事件都发一次 subagent（token 爆炸 + 违背抽查的「抽」）。
- **组合**：L-a 当「烟雾报警器」（便宜、广覆盖、只报不审）→ 攒信号 → L-c 决策 → L-b 当「消防员」（贵、按需、深审）。这正是研究「**每条事件抽查**」的工程化诚实翻译——**「监听每条」由 L-a 廉价规则承担，「深度抽查」由 L-b 按信号触发**。

> **未决 D-2**：L-a 的 hook 是否本期就建？它要求 CQO 进 hooks.json（目前只有 kdev-memory 带 hook）。MVP 可**只做 L-b（checkpoint 发函）**，L-a 逐事件 hook 作下一刀——先验「深审能产出有用审计」，再上「廉价烟雾报警」。倾向 MVP = L-b only，但需用户拍 MVP 边界。

## 4.3 双信号机制（拆两种信号 → 两种动作）

借架构补遗 §4.1 self-improve 算法骨架 + §8.3 `cqo_supervision:` config 骨架。CQO 把事件流归纳成两个正交信号：

### 信号 1：circuit-breaker（反复失败）—— 引擎已有一半，CQO 聚合 + 升级

- **定义**：同一 gate / 同一问题连续失败 N 次（默认 3）。
- **引擎侧现状**：`gate.py` 单 gate FAIL `iter>=cap` 已 → `status="blocked"`（这是 circuit-breaker 的**单 gate 局部实现**）。
- **CQO 增量**：① **跨 gate / 跨 flow 聚合**——单个 flow 每个 gate 都没到 cap，但整条链反复在「评审→改→又被打回」打转，引擎看不出来，CQO 从 events 全景看得出来；② **语义去重**——「同一个错误」引擎只会数 `iter`（机械计数），CQO 读 issues 文本判「是不是同一根因撞了 3 次」（架构补遗 §4.2「同一错误连续 3 次」需要语义判断）。
- **动作**：`escalate_to_ceo`（config 骨架默认值）——CQO 出告警，CEO 编排决定升人 / 换策略。**CQO 不直接拦**（callee 不碰状态机）。

### 信号 2：plateau（停滞）—— 全新，CQO 独有

- **定义**：连续 window 轮迭代「进步幅度 < threshold」（config 骨架默认 `threshold: 0.05` 进步<5%、`window: 3`）。典型场景：评审分数在 80-82 之间反复横跳没真改进、增量循环空转、改了 3 版方案分数原地踏步。
- **引擎侧现状**：**无**——引擎只认 PASS/FAIL 二值，不认「在缓慢但无效地挣扎」。这是 CQO **填的真空白**。
- **进步幅度怎么算**：需要分数序列。当前 events `gate` 行**不带 score**（FF-3 留了字段未填，FF-4 待排期）。**plateau 信号的精度依赖 FF-4 数字分落地**——没有 score 序列，plateau 只能靠粗代理（iter 次数 / issues 数趋势）。见 §6 集成 + §10 未决。
- **动作**：`prompt_user_for_unblock`（config 骨架默认值）——提示用户「这条链卡住了、在原地打转，要不要换方向 / 降范围 / 人工介入」。比 circuit-breaker 温和（不是失败，是无效挣扎）。

> **借 self-improve 算法骨架的边界**：只借**信号定义 + 终止条件结构**（`plateau OR circuit-breaker OR max_iter`），**不引入 OMC self-improve 的 tournament / 候选排名运行时**（那是评审 retry 多方案才用，与 CQO 监督正交，且守「不引运行时依赖」哲学）。

## 4.4 CQO 的动作菜单（信号 → 动作映射）

| 信号 | 严重度 | CQO 动作 | 谁兑现 |
|---|---|---|---|
| 规则命中（L-a，如 gate verdict=PASS 但对应产物文件不存在 / TDD 节点没有测试文件） | 🟡 可疑 | 写 `staff/cqo/WARN-*.md` 信号 + 标 events 指针 | CEO 棒间读到 → 决定深审 |
| circuit-breaker（跨 flow 反复失败 / 同根因 3 次） | 🔴 阻断级 | 审计报告 + 回函 `verdict: escalate, signal: circuit-breaker` | **CEO**：升人 / 换策略（CQO 不拦） |
| plateau（停滞无进步） | 🟡 治理级 | 审计报告 + 回函 `verdict: prompt, signal: plateau` | **CEO**：提示用户解阻 / 降范围 |
| 过程合规问题（评审走过场 / 漏评 / 员工跑偏越权） | 🟡/🔴 | 审计报告 + 元评审异常告警 | **CEO**：决定回流 / 警示 |
| 健康（抽查无异常） | ⚪ | 简短 OK 记录入 `staff/cqo/`（可选，防噪默认不写） | —— |

**有牙齿吗**：与 reviewer 同范式——**建议非拦截**。CQO 的 🔴 不直接 `status=blocked`（那是引擎 / gate 的权力），而是**升 CEO 由 CEO 兑现**。理由：callee 不碰状态机（守集群一致约束）；且 CQO 误判成本高（停整条线），把处置权留给 CEO + 人，比 CQO 自动拦更稳。

---

# 5. Scope 与产物（消费 kdev-memory，不重造）

## 5.1 CQO 的 scope

承 CrewAI MemoryScope 路径前缀模型（架构补遗 §2.3 / P-C2 spec）：

```
.kdev/memory/
├── shared/                  ← 全员工共享（决策日志 / 踩坑日志…）CQO 只读参考
└── staff/
    └── cqo/                 ← scope="/staff/cqo"（CQO 审计报告 + 信号文件）
        ├── 审计报告/         ← L-b checkpoint 深审产物
        └── WARN-*.md         ← L-a 逐事件规则命中信号（CEO 棒间消费后 rm）
```

- **写**：只写自己的 `/staff/cqo`（审计报告 + WARN 信号），与 reviewer 只写 `/staff/reviewer` 对称。
- **读（特权跨 scope）**：`recall(scope="/staff/*")` —— CQO 与 CEO 是仅有的两个有**跨员工全景视野**的角色（架构补遗 §2.3 显式列 CEO/CQO 跨 scope 查询）。这是 CQO 能看出「跨 flow 反复失败」的前提。

## 5.2 产物形态

- **审计报告**（markdown，落 `staff/cqo/审计报告/`）：被审段标识 + 双信号判定 + 🔴/🟡/⚪ + 证据指针（events 行号 / reviewer 回函 / Step ID）+ 给 CEO 的建议。**只放指针不抄正文**（守「不造第二本账」）。
- **WARN 信号文件**（L-a 产，CEO 消费后删）：复用 kdev-memory `WARN-未记录-*.md` 的「hook 留信号 → 主控优先处理 → rm」范式（CLAUDE.md 铁规 3「优先处理 hook 产出」已是集群肌肉记忆）。
- **回函**（L-b checkpoint 给 CEO）：裸文件交接 `handoffs/cqo/<checkpoint>.handoff.json`，schema 仿 reviewer 回函（`{verdict, signal, severity, report_ref, evidence[], by:"cqo"}`），CEO 普通 `Read` 取。

---

# 6. 与现有基础设施集成

| 基础设施 | CQO 怎么用 | 是否需改它 |
|---|---|---|
| **kdev-core `events.jsonl`** | 主数据源：读 transition/gate/dispatch 行做抽查。actor 过滤拿「谁做的」 | **不改**（只读消费）。CLI `events <slug>` 已够；若要 tail-n 性能可后续加 `events --last N`（架构补遗旧设计提过 `read_last`） |
| **kdev-core `gate.py` escalate** | circuit-breaker 的引擎侧信号源：`status=blocked` + `blocked_reason` 是现成的「单 gate 撞墙」事实 | **不改**。CQO 聚合多个 + 加语义去重 |
| **kdev-hud `datasource._alerts()`** | CQO 与 HUD **配对消费同一 events**：HUD 渲染当前态告警，CQO 做行为审计。CQO 的 plateau/circuit 信号可**喂回 HUD 多渲一类 alert**（如 `alerts` 加 `kind: cqo-plateau`） | **可选改 hud**（加 cqo alert 类型）——下一刀，非 MVP |
| **kdev-memory `recall` / scope** | `recall(/staff/*)` 跨员工读 Step；`staff/cqo/` 写报告 | **不改 memory 引擎**；只是新增一个 scope 的使用者（scope 模型已支持） |
| **reviewer `anomaly.escalate=CQO`** | 现成的「元评审异常」入口——reviewer 裁不动时把球踢给 CQO | **不改 reviewer**；CQO 消费这个已埋的字段 |
| **FF-4 数字分（gate score）** | plateau 信号的进步幅度计算依赖 score 序列 | **依赖 FF-4 落地**（待排期）。FF-4 未落则 plateau 走粗代理（iter/issues 趋势），精度打折——见 §10 未决 |

**关键集成原则**：CQO **是现有事件账的新消费者，不是新生产者**（除自己 scope 的报告）。它不往 events.jsonl 写（callee 无写通道 + 不造第二本账），它把判定写自己 scope + 回函 CEO。

---

# 7. 与 CEO / reviewer 的关系

## 7.1 CQO vs CEO（编排 vs 监督）

| | CEO（总编排） | CQO（元监督） |
|---|---|---|
| 干什么 | **路由 / 派单 / 阶段聚合 / 决策**（往前推进度） | **审计 / 信号 / 告警**（盯进度推得对不对） |
| 形态 | 主会话 skill（`/kdev-team`，非 Agent） | callee 类（被 hook 触发 / 被 CEO checkpoint 发函） |
| 关系 | **CQO 寄生 CEO 的编排生命周期，但不寄生 CEO 的 flow-state**——CEO 在 checkpoint 发函 CQO，CQO 审完回函 CEO；CQO 的告警**回给 CEO**，由 CEO 兑现 | |
| 触发回流 / 升人？ | **CEO 能**（编排有处置权） | **CQO 不能直接**——出 verdict/告警，CEO 兑现（建议非拦截） |

**寄生关系澄清**：CQO **不寄生 CEO 的 flow**（CEO 本身也没有 flow-state，它是主会话 skill 顺序消费 stages）。准确说 CQO **寄生「集群运行」**——L-a hook 挂在任何员工的 CLI 调用上（不分 CEO 在不在场）；L-b 由 CEO checkpoint 主动发函。即：**有 CEO 编排时 CEO 是 CQO 的发函主；无 CEO（人手动单驱一个员工）时 L-a hook 仍在岗**，CQO 不死绑 CEO。

> **未决 D-3**：L-b checkpoint 发函由谁触发？候选：(a) CEO 编排在 human_gate / 阶段交界硬编码发函 CQO；(b) CQO checkpoint 作为 lifecycle 模板里一个可开关的「审计段」（编排路由器 §3 `stages[]` 加一类 `emp: cqo` 的审计 stage）。倾向 (a)（轻、不改 lifecycle schema），但 (b) 更声明式可配。用户拍。

## 7.2 CQO vs reviewer（元监督 vs 质检）

- **CQO 不重评 reviewer 评过的产物**（不当二审，避免标准漂移 + token 重复）。CQO 评的是「reviewer 这次评审动作本身合不合规」——有没有走过场、该 fan-out 的 cap 漏了没、阈值有没有被偷偷放水。这是**元评审**（评审「评审」）。
- reviewer 的 `anomaly.escalate=CQO` 是二者**唯一直接接口**：reviewer 仲裁裁不动 → 标元评审异常给 CQO。其余时候 CQO 通过 events 里的 `gate` 行（reviewer 是 `by` 字段）**旁路观察** reviewer 行为，不打扰 reviewer。

---

# 8. 多 agent 调用约束（防套娃，承架构补遗 §222 Worker Preamble Protocol）

架构补遗 §五（§213-238，§222 为该节核心句）：**「6 员工 × 多业务能力 = 39 agent。如果不限制，开发工程师可能调评审专家，评审专家又调 CQO，套娃出去 token 爆炸。」** CQO 是套娃链的**最末端典型受害点**，必须显式约束：

1. **CQO 不开子 agent**（Worker Preamble Protocol）：CQO 审计能力 agent 是**叶子**，直接执行抽查（读 events / Read / Grep / recall），**不再 dispatch 任何 subagent**。frontmatter 表达 `allow_delegation: false` / `delegation_max_depth: 0`（沿用研究 §8.4/§8.5 员工 frontmatter 范式；CC 是否识别该字段是已知未决，见架构补遗 §九-1/-4）。
2. **谁能发函 CQO**：只有 **CEO 主会话**（L-b checkpoint）+ **hook**（L-a，机械触发非 agent 发函）。**业务员工 / reviewer 不直接发函 CQO**（守硬规 4/5「业务能力不直接对外」）——reviewer 的元评审异常走 `anomaly` 字段经 caller→CEO 中转，不是 reviewer 直 dispatch CQO。
3. **CQO 不反向命令任何人**：与 reviewer callee 同——CQO 只回函 CEO，从不直接命令员工、不 halt 任何 flow、不跨员工联络。处置权在 CEO + 人。
4. **L-a hook 零 LLM 零派单**：hook 是纯 python 规则匹配（同 kdev-memory 全部 hook），**不在 hook 里起 agent**（hook 同步阻塞 + 5s 超时，起 agent 必爆）。

> 这条约束链让套娃在 CQO 这一端**结构性闭合**：CQO 是叶子（不下派）+ 只被 CEO/hook 触发（入边受控）+ 不反向命令（不制造新边）。

---

# 9. 实施时序与依赖

- 🔴 **硬依赖：实施排在「kdev 单插件化 refactor 结构合并之后」。** 直接把 CQO 建进单插件 `kdev/` 结构（`agents/cqo-orchestrator.md` + 审计能力 agent + `staff.yml` 加 cqo 条目 + 若做 L-a 则进集群 `hooks.json`），**不在旧多插件结构建完再迁**（迁移即返工 + 命名空间二次改写）。依据：单插件化 spec §8 迁移节奏「直接建进单插件结构」+ CLAUDE.md「CQO 实现放在单插件化之后」。
- **软依赖（影响精度非阻塞）**：FF-4 数字分（gate score）落地 → plateau 信号精度。FF-4 未落可先上 circuit-breaker + 规则抽查（不依赖 score），plateau 走粗代理。
- **前置已就绪**：events.jsonl（P-Core-FF done）+ scope 模型 + reviewer anomaly 字段 + CEO 编排 MVP——CQO 要消费的基础设施都已在位。
- **建议 MVP 边界**：L-b checkpoint 深审一条（circuit-breaker 信号 + 过程合规抽查）+ `staff/cqo/` scope + 回函 CEO。**L-a 逐事件 hook + plateau 信号 + HUD cqo-alert 作下一刀**（见 §4.2/§10 未决）。

---

# 10. 风险

| 风险 | 说明 | 缓解 |
|---|---|---|
| **抽查 = 走过场** | CQO 自己变成「点头机器」——审计报告千篇一律「无异常」，没真发现问题 | 双信号是**机械可验**的（circuit-breaker 数次数 / plateau 算趋势），不靠 LLM 自由发挥；规则命中（L-a）是确定性的 |
| **plateau 精度依赖 FF-4** | 无 score 序列时 plateau 靠 iter/issues 粗代理，可能误报 / 漏报 | MVP 先不强上 plateau；标注「FF-4 落地前 plateau 是 best-effort」 |
| **误判停整条线** | CQO 🔴 若直接拦流，误判成本 = 整条交付停摆 | **建议非拦截**——CQO 不拦，升 CEO + 人兑现（§4.4） |
| **token 成本** | L-b 深审每次 = 一个 subagent，频繁 checkpoint 会贵 | 抽查的「抽」= 按信号触发非每事件；L-a 廉价规则当前置过滤器 |
| **套娃复发** | CQO 若不慎下派子 agent → token 爆炸 | §8 结构性闭合（叶子 + 入边受控 + 不反向命令） |
| **hook 阻塞会话** | L-a hook 同步 + 5s 超时，规则写复杂了拖慢每次 CLI 调用 | 沿用 kdev-memory hook 纪律（纯 python、轻、超时降级）；L-a 列下一刀可避开此风险 |
| **与 HUD 职责重叠** | HUD `_alerts` 已报 blocked/gate_fail，CQO 别重复造 alert | 明确分工：HUD 报**当前态事实**（这棒 blocked 了），CQO 报**行为研判**（这是第 3 次同根因了 / 在原地打转）——后者是前者的语义升级，喂回 HUD 渲染 |

---

# 11. 范围外 / 未决（待用户拍板）

## 11.1 需用户拍板的关键未决点

- **D-1 CQO 的 `kind` 与归属**：进 `staff.yml` 当第 6 个 employee（新 `kind: supervisor`？还是复用 `kind: callee`？），还是当 CEO / 底座的附属审计能力不入花名册？（§3.2）
- **D-2 MVP 监听层边界**：MVP 只做 L-b（checkpoint 发函深审），还是同时做 L-a（逐事件 hook 规则抽查）？L-a 要 CQO 进 `hooks.json`（目前只有 memory 带 hook，单插件化后 hooks 同根）。倾向 MVP=L-b only。（§4.2）
- **D-3 L-b 发函触发方式**：CEO 编排硬编码在 human_gate / 阶段交界发函 CQO（a），还是 lifecycle 模板加一类可开关的 `emp: cqo` 审计 stage（b）？（§7.1）
- **D-4 plateau 信号是否进 MVP**：依赖 FF-4 数字分。FF-4 未落 → plateau 走粗代理（精度打折）或 MVP 不上 plateau、只上 circuit-breaker？（§4.3 / §6）
- **D-5 双信号阈值取值**：沿用 config 骨架默认（plateau `threshold:0.05 / window:3`、circuit-breaker `threshold:3`）还是先观察 dogfood 再定？阈值落 `cqo_supervision:` config（落在哪个文件——集群 config / per-flow flow-config / staff.yml？）。

## 11.2 明确范围外

- **OMC self-improve 的 tournament / 候选排名运行时**——只借信号定义骨架，不引该运行时（评审 retry 多方案才用，正交）。
- **自演进闭环**（CQO 发现问题 → 自动改 skill / 改 prompt）——架构补遗把「自演进」与「CQO」并列在阶段4，但本 spec **只设计监督 / 审计**，自演进执行是更后一层，范围外。
- **跨 IDE 的 CQO**（多客户端审计聚合）——阶段4 北极星另一支（Continue 三层 / OpenMemory），范围外。
- **CQO 直接拦流 / 自动回流**——明确否决（建议非拦截，§4.4），处置权恒在 CEO + 人。
- **events.jsonl 加 `cqo_audit` 事件类**——旧 v0.1 详细设计（已归档）提过 `cqo_audit` 事件；本 spec **否决**（守「不造第二本账」，CQO 判定落自己 scope + 回函，不往集群事件账写）。若未来要让 HUD 渲 CQO 信号，走 hud datasource 派生（§6）而非新事件类。

---

# 12. 影响的 canonical 文档（R-009 回写清单）

本 spec 被采纳 / 实施收尾时须回写或加重定向锚：

- roadmap-v1.0 §1.5.9 矩阵「CQO ❌ L4 defer」行 → 改状态 + 加「已起设计 spec」锚。
- roadmap-v1.0 §阶段4「CQO + 自演进 + 跨IDE」→ CQO 部分提前出设计的说明锚。
- `staff.yml` → 若 D-1 定为入花名册，加 cqo 条目（`kind` 待定）。
- 单插件化 spec §5 打包形态 → 若做 L-a，集群 `hooks.json` 增 CQO hook 来源说明。
- reviewer 通用评分模板 / reviewer-orchestrator 的 `anomaly.escalate=CQO` → 从「等 CQO 来消费」改为「CQO 消费契约见本 spec §7.2」。
