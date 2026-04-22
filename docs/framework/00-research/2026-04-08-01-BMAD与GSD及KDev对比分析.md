# BMAD vs GSD vs KDev-Agent 对比分析

> 生成日期：2026-04-07
> 目的：分析三种 Spec-Driven Development 方案的特点，为 KDev-Agent 优化提供参考

---

## 一、方案概览

| 方案 | 定位 | 核心理念 |
|------|------|----------|
| **BMAD** | 企业级规范化 | "完整的软件工程流程，AI辅助执行" |
| **GSD** | 极简高效 | "No enterprise roleplay bullshit. Just get shit done." |
| **KDev-Agent** | 人机协同 | "AI主导执行，人来主导规则" |

---

## 二、核心差异对比

### 2.1 流程复杂度

| 维度 | BMAD | GSD | KDev-Agent |
|------|------|-----|------------|
| **流程阶段** | 多阶段（5+阶段） | 6步主流程 | 五层架构 |
| **仪式活动** | Sprint ceremonies、retrospectives、stakeholder syncs | 无 | 人工门控点 |
| **任务估算** | Story points、Jira workflows | 自动分解 | Task + Step 双层 |
| **角色扮演** | 企业团队角色模拟 | 无角色扮演 | Agent角色分工 |

### 2.2 规格管理

| 维度 | BMAD | GSD | KDev-Agent |
|------|------|-----|------------|
| **规格类型** | 完整PRD + Story | PROJECT.md + REQUIREMENTS.md | constitution.md + specs/ |
| **变更管理** | Sprint计划、正式流程 | Phase插入/移除 | /kdev-change Delta Spec |
| **版本追踪** | Jira集成 | ROADMAP.md + STATE.md | questions-log.md + archive/ |

### 2.3 执行机制

| 维度 | BMAD | GSD | KDev-Agent |
|------|------|-----|------------|
| **执行单元** | Story → Task | Phase → Plan → Task | Task → TDD Step |
| **并行策略** | 团队协作模式 | Wave并行执行 | Subagent并行 |
| **上下文管理** | 多角色会议 | Fresh context per plan | Subagent上下文隔离 |
| **TDD集成** | 可选 | 内置（可选） | 强制TDD循环 |

### 2.4 质量保障

| 维度 | BMAD | GSD | KDev-Agent |
|------|------|-----|------------|
| **测试层次** | UT + IT + E2E | 计划内验证步骤 | 测试金字塔（UT/IT/E2E） |
| **评审机制** | Code Review + Retrospective | /gsd:verify-work UAT | 两阶段评审 + 安全审计 |
| **门禁策略** | Sprint验收 | Phase verification | Hard-gate + correctionLoop |

### 2.5 记忆与追溯

| 维度 | BMAD | GSD | KDev-Agent |
|------|------|-----|------------|
| **决策追溯** | Sprint文档、会议记录 | STATE.md + todos/ | questions-log.md |
| **跨会话记忆** | 项目文档库 | threads/ + seeds/ | .kdev/memory/ |
| **知识沉淀** | Retrospective输出 | 自动归档 | Claudeception技能化 |

---

## 三、GSD 关键特性详解

### 3.1 核心流程

```
/gsd:new-project → /gsd:discuss-phase → /gsd:plan-phase → /gsd:execute-phase → /gsd:verify-work → /gsd:ship
```

**关键创新：**

1. **Context Engineering** - 解决"context rot"（上下文窗口质量退化）
2. **Wave Execution** - 依赖感知的并行执行
3. **Fresh Context Per Plan** - 每个Plan在独立subagent中执行（200k tokens纯净上下文）
4. **Atomic Git Commits** - 每个Task独立commit

### 3.2 XML Prompt Formatting

```xml
<task type="auto">
  <name>Create login endpoint</name>
  <files>src/app/api/auth/login/route.ts</files>
  <action>Use jose for JWT...</action>
  <verify>curl -X POST localhost:3000/api/auth/login returns 200</verify>
  <done>Valid credentials return cookie</done>
</task>
```

**优势：** 精确指令、无猜测、验证内置

### 3.3 Multi-Agent Orchestration

| Stage | Orchestrator | Agents |
|-------|--------------|--------|
| Research | 协调、汇总 | 4并行researcher |
| Planning | 验证、迭代 | Planner + Checker |
| Execution | Wave分组、追踪 | Executors并行 |
| Verification | 结果呈现、路由 | Verifier + Debuggers |

**结果：** 主上下文保持30-40%，重负载在subagent中

---

## 四、BMAD 特点（基于GSD描述）

根据GSD README对BMAD的描述：

> "Other spec-driven development tools exist; BMAD, Speckit... But they all seem to make things way more complicated than they need to be (sprint ceremonies, story points, stakeholder syncs, retrospectives, Jira workflows) or lack real big picture understanding of what you're building."

**BMAD特点推断：**

1. **企业级流程** - Sprint ceremonies、retrospectives、stakeholder syncs
2. **Jira集成** - Story points、任务追踪
3. **角色模拟** - 团队角色扮演（如模拟50人团队）
4. **完整流程** - 覆盖软件工程全生命周期

**适用场景：** 大型团队、正式项目管理、需要企业合规

**潜在问题：**
- 流程复杂度高
- "Enterprise theater" - 过度仪式化
- 对solo developer可能过重

---

## 五、KDev-Agent 当前设计

### 5.1 五层架构

| Layer | 功能 | 融合来源 |
|-------|------|----------|
| 1: 规格引擎 | 需求澄清、规格生成、评审 | brainstorming + speckit + openspec |
| 2: 计划引擎 | Task分解、TDD计划 | speckit Plan + writing-plans |
| 3: 执行引擎 | Subagent执行、两阶段评审 | subagent-driven + TDD |
| 4: 质量保障 | UT/IT/E2E、安全审计 | TDD + gstack /qa /cso |
| 5: 记忆系统 | 纠正参考、知识提取 | questions-log + Claudeception |

### 5.2 核心命令

```
/kdev-spec → /kdev-plan → /kdev-exec → /kdev-test → /kdev-review → /kdev-verify
```

### 5.3 独特特性

1. **questions-log追溯** - 所有决策记录可回溯纠正
2. **Hard-gate机制** - 关键节点人工确认
3. **Delta Spec** - 增量变更管理
4. **双Agent模式** - Agent1执行 + Agent2审查

---

## 六、对比总结

### 6.1 定位差异

```
BMAD:      ████████████████████  企业级、完整流程、仪式化
GSD:       ██                    极简、高效、无仪式
KDev:      ████████              平衡、人机协同、门控点
```

### 6.2 适用场景

| 场景 | 推荐方案 |
|------|----------|
| Solo Developer / 小团队 | GSD |
| 企业项目 / 合规需求 | BMAD |
| 人机协同 / 可追溯 | KDev-Agent |

### 6.3 可借鉴点

| 来源 | 可借鉴特性 | KDev集成建议 |
|------|------------|--------------|
| **GSD** | Wave Execution | 已有Subagent并行，可增强依赖感知 |
| **GSD** | Fresh Context | 已有上下文隔离，可优化token管理 |
| **GSD** | Atomic Commits | 已有commit策略，可细化 |
| **GSD** | XML Prompt | 可在Plan中引入结构化格式 |
| **BMAD** | 完整流程覆盖 | 可参考阶段定义完整性 |
| **BMAD** | Sprint验收 | 可增强milestone管理 |

---

## 七、下一步讨论方向

1. **KDev-Agent 是否应该简化？** - 借鉴GSD的极简理念
2. **Wave Execution 是否值得引入？** - 依赖感知并行执行
3. **XML Prompt Formatting 是否适合？** - 结构化Plan格式
4. **仪式活动是否需要？** - Sprint ceremonies vs Hard-gate
5. **记忆系统优化** - GSD threads/seeds vs KDev questions-log

---

## 参考来源

- [GSD README](https://github.com/gsd-2/get-shit-done) - Get Shit Done官方文档
- `docs/plans/2026-03-31-spec-coding-research-design.md` - KDev-Agent设计文档
- BMAD相关信息来自GSD README的对比描述