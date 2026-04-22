# KDev-Agent

> AI 驱动的敏捷开发工作流框架
> 核心理念：**AI 主导执行，人来主导规则**

KDev-Agent 把 BMAD、OMC、Superpowers、Gstack 等开源框架融合成一套六层架构，以 **Compound Engineering（复利工程）** 为核心 —— 让每一次迭代都让下一次更容易。

---

## 当前状态

📐 **设计与文档阶段，正进入 Sprint 0。**

当前仓库尚未包含源码，所有产出物都是架构文档，位于 [docs/](docs/)。权威文档：

- **架构设计**：[2026-04-08-03-KDev融合架构设计.md](docs/01-design/2026-04-08-03-KDev融合架构设计.md) (v3.0.1)
- **Sprint 0 计划**：[2026-04-10-01-Sprint0计划.md](docs/01-design/2026-04-10-01-Sprint0计划.md)
- **参考工作流**：`kdev-skill/docs/standardized-dev-flow.md`（IR→SR→AR→TDD）

---

## 核心理念

### Compound Engineering（复利工程）

> Each unit of engineering work should make subsequent units easier—not harder.

```
Plan (80%) → Work (20%) → Review → Compound → Repeat
                                      ↑
                                知识沉淀
```

每一个 bug、决策、模式都会被捕获和沉淀，使下一次迭代的起点更高。

### AI / 人职责边界

| AI 负责 | 人负责 |
|---------|--------|
| 需求澄清、规格生成、计划分解 | 设计审批、规格验收 |
| 代码实现（TDD 循环） | 任务确认、最终验收 |
| 质量检查、代码审查、安全审计 | 关键决策点 (HARD-GATE) |

---

## 六层融合架构

| 层 | 名称 | 职责 | 来源框架 |
|----|------|------|----------|
| 1 | 规格引擎 Spec Engine | 需求澄清、规格生成 | BMAD + Superpowers |
| 2 | 计划引擎 Planning Engine | 任务分解、TDD 计划 | BMAD + Superpowers |
| 3 | 执行门控 Execution Gate | HARD-GATE：用户审批 | Superpowers |
| 4 | 执行引擎 Execution Engine | Subagent TDD 循环 | Superpowers + OMC |
| 5 | 质量保障 Quality Assurance | UT/IT/E2E、安全审计 | Superpowers + Gstack |
| 6 | 记忆系统 Memory System | 知识持久化、复利学习 | OMC + Gstack + KDev |

---

## 命令体系（14 条，对齐 IR→SR→AR 流程）

### Phase 1 规划

| 命令 | 用途 | 产出 |
|------|------|------|
| `/kdev:ir` | 收集初始需求 | IR 文档 |
| `/kdev:sr` | Story 需求 + 粗粒度 AR | SR CSV + 粗粒度 AR CSV |
| `/kdev:prototype` | 概览 UI 原型 | HTML 原型 |
| `/kdev:review` | 人工评审门（SR + AR + 原型） | 评审批准 |
| `/kdev:plan` | 输出迭代计划 | 迭代计划文档 |

### Phase 2 执行（按迭代）

| 命令 | 用途 | 产出 |
|------|------|------|
| `/kdev:ar` | 详细 AR + 高保真原型 + 技术设计 | AR CSV + HTML + 设计文档 |
| `/kdev:align` | 需求对齐（O-S-U-R-A）+ 修订 | 对齐确认 |
| `/kdev:dev` | TDD 全循环（Red→Green→Refactor） | 测试 + 实现代码 |
| `/kdev:e2e` | E2E 系统测试 | 测试报告 |
| `/kdev:accept` | 系统验收 + 代码审查 | 验收报告 |

### 横切命令

| 命令 | 用途 |
|------|------|
| `/kdev:start` | 入口：检查 state.md，选择阶段 |
| `/kdev:ship` | 发布 |
| `/kdev:recap` | 复盘 + 知识蒸馏 |
| `/kdev:security` | 安全审计 |

### 状态机

```
Phase 1: INIT → P1-IR → P1-SR → P1-PROTOTYPE → P1-REVIEW → P1-PLAN
                                                     ↑
                                                [人工门控]

Phase 2: E1-AR → E2-ALIGN → E4-DEV → E6-E2E → E7-ACCEPT → NEXT-ITERATION
```

---

## 关键设计概念

### HARD-GATE（硬门控）

用户批准设计之前，**不写代码、不搭脚手架、不调用任何实现类 Skill**。该门位于 Phase 1（规划）与 Phase 2（执行）之间。

### 三层需求模型（IR → SR → AR）

- **IR**（Initial Requirements）：原始用户需求，通过 brainstorming 收集
- **SR**（Story Requirements）：结构化 Story，含验收标准、优先级、Story Points
- **AR**（Acceptance Requirements）：详细 GWT 场景、UI 原型、技术设计 —— 按迭代产出

### 五层记忆架构

| 层级 | 内容 |
|------|------|
| Level 0 | 运行时内存（会话级） |
| Level 1 | 知识图谱（`.kdev/knowledge-graph/`） |
| Level 2 | 学习沉淀（`.kdev/learnings/`） |
| Level 3 | 项目记忆（`questions-log.md`、`gotchas.md`、`state.md`、`daily-logs/`） |
| Level 4 | 技能库（`.kdev/skills/`） |
| Level 5 | 全局记忆（`~/.kdev/`） |

---

## 仓库结构

```
docs/
├── 00-research/    # 框架对比、生态分析（9 文档）
├── 01-design/      # 架构与设计决策（6 文档，v3.0.1 + Sprint 0 计划）
├── 02-reviews/     # 多模型评审报告（7 文档）
├── 03-archive/     # 已被取代的实施方案（3 文档）
└── 04-references/  # BMAD 使用指南、参考工作流
```

命名规范：`YYYY-MM-DD-NN-标题.md`。所有文档为中文（技术术语保留英文）。

---

## 框架融合角色

| 框架 | 在 KDev 中的角色 |
|------|------------------|
| **BMAD** | 核心工作流骨架 —— 敏捷阶段、门控、交付物 |
| **OMC**（oh-my-claudecode） | 技术基础设施 —— hooks、状态机、跨会话持久化 |
| **Superpowers** | 执行质量 —— TDD、brainstorming、writing-plans、subagent-driven-dev、HARD-GATE |
| **Gstack** | 多角色阶段评审 + `/qa` + `/cso` + `/ship` + `/learn` |

---

## 规划中的技术栈

- **运行时**：Node.js / TypeScript
- **构建输出**：`dist/`、`bridge/*.cjs`
- **测试**：vitest (UT)、supertest (IT)、Playwright (E2E)
- **项目状态**：`.kdev/` 目录（记忆、状态、技能）
- **全局配置**：`~/.kdev/`（用户偏好）

---

## Sprint 0：验证设计

Sprint 0 以 **token-statistics** 为 dogfood 项目，通过手动编排已有插件（BMAD + Gstack + Superpowers）验证 v3.0.1 架构。

**路径**：最小记录框架（`.kdev/` 含 state.md、questions-log、gotchas、journal）+ 手动插件编排跑通完整工作流。

**Sprint 0 之后**：评审报告 → 修订 v3.0.1 设计 → 决定技术形态 → 实现首批 KDev 特性 → 用 KDev 开发 kdevsec（1→N 验证）。

详见 [Sprint 0 计划](docs/01-design/2026-04-10-01-Sprint0计划.md)。

---

## License

TBD
