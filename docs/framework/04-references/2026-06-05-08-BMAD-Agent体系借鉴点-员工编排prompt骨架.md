# BMAD Agent 体系借鉴点 — 员工编排 prompt 骨架（参考资料）

| 项 | 值 |
|---|---|
| 文档性质 | **参考资料 / 调研依据**（对照 BMAD agent 体系，给员工能力专项的 prompt 层补范本；正文设计不写借鉴来源）|
| 日期 | 2026-06-05 |
| 范围 | BMAD（`bmad-agent-builder` 元工具 + `bmad-agent-*` persona agents）作为**单 agent 创作层**对 KDev 数字员工的借鉴；**不引入 BMAD 运行时/模块** |
| 关联 | [员工能力专项 v1.5](../01-design/2026-05-28-01-KDev数字员工架构-员工能力专项-v1.5.md) · [整体架构](../01-design/2026-05-28-02-KDev-staff-整体架构-v0.1.md) · [BMAD 使用指南](./2026-04-08-01-BMAD使用指南.md) |
| 源码位置 | `~/.claude/skills/bmad-agent-builder/`、`~/.claude/skills/bmad-agent-{dev,architect,pm,...}/`（系统已装，不在本仓）|

---

## 0. 定位（关键边界）

BMAD 的 "agent" **≠** KDev 的"员工集群"。BMAD agent 是**一个带人格的 skill，用户直接对话**（"talk to Amelia"），它再路由到子 skill；所有 agent 是**用户手动切换的平级专家**，没有 CEO 编排的分层集群。

所以借鉴只卡在 **「单个员工 agent 怎么写」** 这一层，**不**往「集群怎么编排」那层套——后者（CEO 单一对外 + 员工作为 subagent + 员工间发函 + R3 gate + 评审百分制循环 + CQO 元监督）BMAD 整个体系里**没有对应物**（party-mode 只是圆桌聊天，非受治理流水线），那恰是 KDev 已超出 BMAD 的部分。

---

## 1. BMAD agent 三形态梯度 → 员工记忆形态决策框架

BMAD 把 agent 分三档梯度（非硬分叉，按特性决策）：

| 形态 | 结构 | KDev 映射 |
|---|---|---|
| **Stateless** | 全在 SKILL.md，无记忆 | 大部分**业务能力**（per-flow 一次性，无跨 session 关系） |
| **Memory** | 瘦 bootloader + sanctum 6 文件 + First Breath 开场校准 | **评审专家**（评审经验记忆 §6.1）、**CQO**（跨流程合规基线） |
| **Autonomous** | Memory + PULSE 后台自运行 | **CQO 模式 d 常驻监听** + kdev-memory 蒸馏策展 |

**借鉴**：BMAD 的判定问句很干净——"如果每天用一个月，第 30 次会话跟第 1 次不同吗？不同就要记忆"。可用来给 39 个 agent 逐个定形态，避免无脑全部塞记忆。

---

## 2. persona agent 骨架 → 员工编排 prompt 模板（最高价值 ⭐⭐⭐⭐⭐）

v1.5 把"编排能力"的**职责**讲清楚了（§3.2 四 meta 职责），但**没给 agent prompt 长什么样**。BMAD persona 模板正好补这个洞。统一骨架（见 `bmad-agent-dev` / Amelia）：

```
Identity            # 一句话身份
Communication Style # 沟通风格（Amelia: "speaks in file paths and AC IDs"）
Principles          # 不可破的原则（红线）
Critical Actions    # 激活即执行的硬动作（READ 整个 story / 按序执行 / 测试 100% 过）
Capabilities 表     # 路由菜单：| Code | Description | Skill |  →  DS→bmad-dev-story
On Activation       # 1.加载config 2.greet+presentmenu 3.STOP and WAIT，按 code/编号派单
```

**直接落地**：
- **员工编排 agent** = persona 骨架。Amelia 的 Capabilities 表（DS/QD/QA/CR/SP/CS/ER → skill 名）就是"开发工程师 6 业务能力菜单"的现成皮。
- `On Activation` 的 **"STOP and WAIT，不自动执行菜单项，按 code/编号/模糊匹配派单"** 模式，对齐 KDev"编排 → 内嵌派单业务能力"。
- "**must not break character / 用户调 skill 时人格贯穿**"——对应 KDev 员工身份在跨 skill 调用时保持。

---

## 3. Outcome-driven + 剪枝纪律 → 控制 39 agent / 18 standards prompt 膨胀（⭐⭐⭐⭐⭐）

BMAD agent-builder 的北极星：**capability prompt 只写 WHAT（要达成什么 + "What Success Looks Like"），persona 管 HOW**。Phase 4 剪枝硬检查：

> 对每条指令问：**只给 persona + 期望产出，LLM 自己能做对吗？能就删。**
> 重点删：① capability 里 LLM 能推断的分步流程 ② 重复 SKILL.md 已有的身份/风格 ③ 能合并的多个 capability 文件 ④ 讲 LLM 已知常识的 reference。

**对 KDev 的价值**：39 个 agent + 18 份评审 standards 模板，最大风险是 prompt 集体臃肿。这条剪枝纪律可直接纳入 **§5.5 评审模板 standards 规约** 和员工能力 prompt 编写规范。配套可借 `bmad-agent-builder` 的 quality-scan-*（over-specification / persona-capability 对齐 / execution-efficiency）给已写 agent 做体检。

---

## 4. First Breath 配置式开场 → CEO 顶层约束制定（⭐⭐⭐ 中）

BMAD memory agent 用 **First Breath** 首次开场把 agent 校准到 owner，分两风格：

- **calibration**（深关系 companion）——KDev 不取
- **configuration**（domain 专家，暖但高效）——**对应 CEO「顶层约束制定」**：首次对话引导用户生成 flow-config.yml（哪些评审开/阈值/CQO 触发模式/人类介入通道）。

借鉴：configuration-style 的"warm but efficient 引导设置"节奏，可作 CEO 首次对话 UX 范本。

---

## 5. PULSE 后台 + 记忆策展 → CQO 常驻 + kdev-memory 蒸馏（⭐⭐⭐ 中）

BMAD autonomous agent 的 PULSE：`--headless` 无任务时**优先做记忆策展**——"MEMORY.md 保持 <200 行，从 session 日志蒸馏精华、剪枝陈旧"。

借鉴：① 对齐 CQO 模式 d 常驻后台监听的"无人值守也产出价值"定位；② "session 原始日志 → 蒸馏进 MEMORY.md、过期剪枝"的策展纪律，跟 kdev-memory 的每日汇总/蒸馏管道同构，可互参。

---

## 6. 借鉴边界

| | 借 | 不借 |
|---|---|---|
| 创作层 | persona 骨架 / Capabilities 路由表 / On Activation STOP-and-WAIT / outcome-driven 剪枝 / 三形态梯度 / quality-scan 体检 | —— |
| 编排层 | 无（BMAD 无集群编排范本） | party-mode 圆桌当流水线 |
| 叙事 | configuration-style 开场节奏 | **Three Laws / Sacred Truth / sanctum「重生」叙事**（companion 玩法，跟企业 SDLC 不搭，剥掉）|
| 运行时 | 无 | BMAD 模块/config 体系 / `_bmad/` 目录约定 |

---

## 7. 待办（如需）

- [ ] 把 §2 骨架落成一个可套用的 **KDev 员工编排 prompt 模板**（参 `bmad-agent-builder/references/sample-capability-prompt.md` + `quality-scan-prompt-craft.md`）
- [ ] §3 剪枝清单纳入 §5.5 standards 规约
