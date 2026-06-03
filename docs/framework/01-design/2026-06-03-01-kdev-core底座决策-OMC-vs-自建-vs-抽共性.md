# kdev-core 底座决策 — 采用 OMC vs 自建 vs 抽共性渐进

| 项 | 值 |
|---|---|
| 文档状态 | **DECISION DRAFT v0.1 — 待用户拍板** |
| 日期 | 2026-06-03 |
| 决策点 | 数字员工的「运行时底座」怎么来：① 采用 OMC ② 自建 lean kdev-core ③ 从现有 flows 抽共性渐进 |
| 方法 | 用「现有 design-flow / coding-flow 实际需要底座提供什么」反推需求，再对照三选项 |
| 关联 | [整体架构 v0.1](./2026-05-28-02-KDev-staff-整体架构-v0.1.md) · [kdev-core v0.1 详细设计](./2026-05-28-03-kdev-core-v0.1-详细设计.md) · [kdev-memory-vs-OMC 源码对比](../04-references/2026-05-30-06-kdev-memory-vs-OMC源码层对比.md) · [架构补遗](../04-references/2026-05-30-05-数字员工架构补遗-多agent+自演进+跨IDE.md) · [Q-004 从低等级起步](../../.kdev/memory/决策日志.md) |

---

## 0. 为什么这是个未决问题

文档自己打架，从没正式拍板：

| 文档 | 对 OMC 底座的立场 |
|---|---|
| **整体架构 v0.1（2026-05-28）** | "**不 fork OMC、自建 kdev-core**、OMC 仅作架构参考" |
| **kdev-memory-vs-OMC 对比（2026-05-30）** | 开篇即"**以 OMC 为 Claude Code plugin 运行时底座的前提下**…" |

5/28 拐成"自建"，5/30 又回到"OMC 当底座前提"，中间没收口。本文档负责收口。

---

## 1. 底座到底要提供什么（从现有 flows 反推）

**关键事实**：`kdev-design-flow` 和 `kdev-coding-flow` **不是原子能力，是流程编排类——已经是数字员工雏形**，各自造了一套底座机制：

| 机制 | design-flow | coding-flow | = 底座该统一提供的 |
|---|---|---|---|
| **流程状态 / resume** | flow-state.json + `--resume <slug>` | slug-based flow state | **R1 状态机持久化 + 断点续跑** |
| **多节点状态机** | SR→AR→原型→详设 4 段 | 13 节点 SOP | **R2 节点/阶段编排引擎** |
| **评审闸门** | 3 闸门 × 3 retry ×（ai/both/human）| 3 判断 Gate + Per-Increment E2E Gate | **R3 评审闸门 + 重试 + 人介入档位** |
| **自主推进** | — | Auto Mode 完全自主 | **R4 自主模式（跑到 Gate 才停）** |
| **派单分工** | sonnet/opus | CLAUDE.md 二档分工 | **R5 模型分工派单** |
| **产物 / handoff** | 三件套产物 | spec/plan/prototype → 部署 | **R6 产物总线 + 阶段交接** |
| **能力调用** | 串 spec-kit / frontend-design | 串多能力 | **R7 调度已有能力插件** |

> **结论**：底座的真正职责 = **R1–R7 的编排引擎**（状态机 + 闸门 + 自主 + 派单 + 产物 + 调度）。
> 注意：kdev-core v0.1 设计偏「state/记忆/hook 管道」，**对 R2 节点状态机 / R4 自主模式这两块编排引擎核心着墨不足**——而这正是 flows 已经各自实现、最该被统一的部分。

---

## 2. 三选项 × 需求对照

| | ① 采用 OMC | ② 自建 lean kdev-core | ③ 抽共性渐进 |
|---|---|---|---|
| R1 状态持久化 | ✅ state-manager + SQLite | 🔨 v0.1 已设计 state.md | ✅ flows 已有 flow-state.json，抽出即可 |
| R2 节点状态机 | ✅ Team Pipeline / 8+ mode | 🔨 v0.1 着墨不足，要补 | ✅ flows 已有（13 节点 / 4 段），抽出 |
| R3 评审闸门 | ✅ verify mode | 🔨 v0.1 评审素材记忆有记录、缺引擎 | ✅ flows 已有 3 闸门 + retry，抽出 |
| R4 自主模式 | ✅ autopilot / ralph | 🔨 v0.1 没有 | ✅ coding-flow 已有 Auto Mode，抽出 |
| R5 派单分工 | ✅ models.ts tier | 🔨 要建 | ✅ CLAUDE.md 二档已在用 |
| R6 产物总线 | ✅ .omc/state/sessions | 🔨 handoffs 已设计 | ✅ flows 已有产物约定 |
| R7 调度能力 | ✅ 但要把 KDev 能力包成 OMC plugin | 🔨 plugin 注册要建 | ✅ flows 已在 `/skill` 调用 |
| **栈/哲学** | ❌ TypeScript 3.3MB 编译运行时，跟 KDev Python/markdown 冲突 | ✅ Python/markdown 原生 | ✅ Python/markdown 原生 |
| **fork/维护/license** | ❌ fork 外来 3.3MB TS + 持续追上游 + license 审查 | ✅ 自有 | ✅ 自有 |
| **从低起步（Q-004）** | ❌ 一次性吞下完整 L4 运行时 | 🔶 按 v0.1 偏全，可砍 | ✅ 从已跑通的抽，最低风险 |
| **工作量** | 中（适配/包装）但**承诺重**（栈绑定） | 大（重建引擎） | 小（抽取 + 收敛重复） |

---

## 3. 推荐：③ 抽共性渐进（Python 原生，借 OMC 设计不 fork）

**理由**：

1. **R2/R4 这俩底座核心，flows 里已经有可工作实现**——OMC 当底座（①）等于丢掉自己跑通的、去吞一个 3.3MB TS 外来运行时；自建（②）等于无视已有实现从 v0.1 设计重画。**从已跑通的 design-flow/coding-flow 抽公共编排层最省、最稳、最贴 [Q-004 从低起步]**。
2. **守 KDev 的 Python + markdown 哲学**（[Q-004] 同源原则、跟 13 插件 + kdev-memory 同栈），不引入 TS 运行时的 fork / 维护 / license 负担。
3. **OMC 不浪费**：把 OMC 的 mode/state-machine/Team Pipeline 当**设计范本借鉴**（5/30 源码对比已摸到代码层），抽共性时照其结构，但**不 fork 源码**——这恰是 v0.1 §4 "OMC 仅参考" 的正解，只是这次**有了 flows 实际需求做锚**。
4. **不foreclose ①**：到 **L3 自主 / L4 自治 / 跨 IDE（v2.x）** 真要完整多 agent 运行时 + 跨 IDE 时，**重新评估采用/借用 OMC**（补遗已把 Continue 三层 + OMC 列为 v2.x 范本）。现在 L2，不提前下注。

**一句话**：底座 = 从 design-flow / coding-flow 抽出 R1–R7 公共编排层（`kdev-core` lean，Python），照 OMC 范本但不 fork；L3+ 再决定是否上 OMC。

---

## 4. 落地路径（推荐项 ③）

| 步 | 内容 |
|---|---|
| 1 | **盘点 R1–R7 在 design-flow/coding-flow 的现有实现**（flow-state schema / 节点机 / 闸门 / Auto Mode 代码），列差异 |
| 2 | **抽公共层** `plugins/kdev-core/`（lean）：先做 R1 状态机持久化 + R2 节点编排 + R3 闸门 三块（L2 最缺的） |
| 3 | **design-flow / coding-flow 改造**为调用 kdev-core 公共层（消除各自重复），dogfood 验证 |
| 4 | R4 自主模式 / R5 派单 / R6 产物 / R7 调度 按需补 |
| 5 | 评审素材记忆 / flow-config / CQO（v0.1 §4 重型块）**defer 到 L3** |

> kdev-core v0.1 详细设计（848 行）**不作废**——其中 state.md/events.log/hook/plugin 注册的 schema 仍可复用；但**重心从"管道"挪到"R2/R4 编排引擎"**，并以 flows 现状校准。

---

## 5. 待用户拍板

| # | 决策 | 状态 |
|---|---|---|
| B1 | 底座路线 = ③ 抽共性渐进（Python 原生，借 OMC 不 fork） | ⏳ 待确认推荐 |
| B2 | ① 采用 OMC 推迟到 L3/L4/跨 IDE 再评估 | ⏳ |
| B3 | 落地第 1 步先做「R1–R7 现有实现盘点」 | ⏳ |
| B4 | kdev-core v0.1 详细设计 重心从"管道"挪到"R2/R4 编排引擎" | ⏳ |

---

## 6. 引用
- [kdev-memory-vs-OMC 源码对比](../04-references/2026-05-30-06-kdev-memory-vs-OMC源码层对比.md)（OMC 运行时能力清单）
- [架构补遗](../04-references/2026-05-30-05-数字员工架构补遗-多agent+自演进+跨IDE.md)（OMC self-improve/team mode + Continue 跨 IDE = v2.x 范本）
- 现有 flows：`plugins/kdev-design-flow/`、`plugins/kdev-coding-flow/`
- [概念模型 v0.5](./2026-06-02-01-KDev数字员工概念模型-双轴+等级阶梯-v0.1.md)（能力→数字员工→持续升级；当前 L2）
