# KDev 命名与 License 合规性分析

> 生成日期：2026-04-08
> 目的：解决三个核心问题 —— BMAD 替代 speckit、License 合规、命令命名规范

---

## 一、BMAD vs Speckit/OpenSpec 规格文档对比

### 1.1 BMAD 规格文档体系

BMAD 的规格文档**强制且有明确规范**：

| 阶段 | 必需文档 (★) | 命令 | 存储位置 |
|------|-------------|------|----------|
| **Phase 2 规划** | PRD ★ | `/bmad-create-prd` | `_bmad-output/planning-artifacts/prd.md` |
| | Architecture ★ | `/bmad-create-architecture` | `_bmad-output/planning-artifacts/architecture.md` |
| | Epics & Stories ★ | `/bmad-create-epics-and-stories` | `_bmad-output/planning-artifacts/epics-stories.md` |
| **Phase 3 方案** | Implementation Readiness ★ | `/bmad-check-implementation-readiness` | 检查清单 |
| **Phase 4 实现** | Sprint Planning ★ | `/bmad-sprint-planning` | `_bmad-output/implementation-artifacts/sprint-status.yaml` |
| | Dev Story ★ | `/bmad-dev-story` | `_bmad-output/implementation-artifacts/stories/` |

**门控机制**：
```
★ = 必需步骤，不可跳过
每个阶段有明确的验证点：
- PRD 完成后才能进入方案阶段
- Architecture + Epics + Readiness Check 完成后才能进入实现阶段
- Sprint Planning 完成后才能开发故事
```

### 1.2 Speckit 规格流程

Speckit 的规格流程**较简单**：

| 步骤 | 命令/概念 | 说明 |
|------|----------|------|
| Constitution | `constitution.md` | 项目原则、约定 |
| Specify | 需求规格 | 功能需求 |
| Plan | 技术设计 | 架构决策 |
| Tasks | 任务分解 | 原子任务 |

**问题**：
- ❌ 无明确门控机制
- ❌ 无验证步骤
- ❌ 较 BMAD 缺少 Epics/Stories 层级

### 1.3 结论：BMAD 可替代 Speckit

**可以替代**，且 BMAD 更完善：

| 对比项 | BMAD | Speckit |
|--------|------|---------|
| 规格强制性 | ✅ ★ 必需步骤 | ❌ 无强制 |
| 门控机制 | ✅ Readiness Check | ❌ 无 |
| 文档规范 | ✅ 有模板和验证器 | ⚠️ 较弱 |
| 任务层级 | ✅ Epic → Story → Task | ⚠️ 只有 Task |
| 纠偏机制 | ✅ `/bmad-correct-course` | ❌ 无 |

---

## 二、License 合规性分析

### 2.1 BMAD License

```
MIT License

Copyright (c) 2025 BMad Code, LLC

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software... to use, copy, modify, merge, publish, distribute,
sublicense, and/or sell copies of the Software...

TRADEMARK NOTICE:
BMad™, BMad Method™, and BMad Core™ are trademarks of BMad Code, LLC.
```

**关键限制**：

| 允许 | 不允许 |
|------|--------|
| ✅ 使用、复制、修改、分发代码 | ❌ 使用 BMad 作为产品名 |
| ✅ 出售包含 BMad 代码的产品 | ❌ 使用 BMad 商标作为品牌 |
| ✅ Fork 并用不同名称分发 | ❌ 声称官方认证/授权 |
| ✅ 描述兼容性（"兼容 BMad Method"） | ❌ 注册 BMad 相关域名 |

### 2.2 所有项目 License 确认结果

| 项目 | License | Copyright | 二次开发 | GitHub |
|------|---------|-----------|----------|--------|
| **BMAD** | ✅ MIT | BMad Code, LLC (2025) | ✅ 支持（有商标限制） | [bmad-builder](https://github.com/bmad-code-org/bmad-builder) |
| **OMC** | ✅ MIT | Yeachan Heo (2025) | ✅ 支持 | [oh-my-claudecode](https://github.com/Yeachan-Heo/oh-my-claudecode) |
| **Superpowers** | ✅ MIT | Jesse Vincent (2025) | ✅ 支持 | [superpowers](https://github.com/obra/superpowers) |
| **Gstack** | ✅ MIT | Garry Tan (2026) | ✅ 支持 | [gstack](https://github.com/garrytan/gstack) |
| **Spec-Kit** | ✅ MIT | GitHub, Inc. | ✅ 支持 | [spec-kit](https://github.com/github/spec-kit) |
| **OpenSpec** | ✅ MIT | OpenSpec Contributors (2024) | ✅ 支持 | [OpenSpec](https://github.com/Fission-AI/OpenSpec) |

**结论**：所有项目均为 MIT License，完全支持二次开发。

**唯一限制**：BMAD 有商标保护，不能使用 "BMad" 作为产品名。

### 2.3 设计文档中引用的 Skill

根据 `docs/01-design/2026-03-31-spec-coding-research-design.md`，涉及以下 skill：

| Skill 来源 | Skill 名称 | 用途 | License |
|-----------|-----------|------|---------|
| **Superpowers** | `brainstorming` | 需求澄清、方案探索 | MIT |
| **Superpowers** | `writing-plans` | TDD 计划编写 | MIT |
| **Superpowers** | `subagent-driven-development` | Subagent 执行 | MIT |
| **Superpowers** | `test-driven-development` | TDD 循环 | MIT |
| **Speckit** | `constitution` | 项目原则 | MIT |
| **Speckit** | `specify` | 需求规格 | MIT |
| **Speckit** | `plan` | 技术设计 | MIT |
| **Speckit** | `tasks` | 任务分解 | MIT |
| **OpenSpec** | `delta-spec` | 增量规格变更 | MIT |
| **Gstack** | `/qa` | QA 测试 | MIT |
| **Gstack** | `/cso` | 安全审计 | MIT |
| **Gstack** | `/browse` | 浏览器测试 | MIT |

**融合映射**：

```
原设计文档融合方案:
┌─────────────────────────────────────────────────────────────────┐
│  Layer 1 规格引擎: superpowers:brainstorming + speckit + openspec │
│  Layer 2 计划引擎: speckit Plan + superpowers:writing-plans      │
│  Layer 3 执行引擎: superpowers:subagent-driven-development + TDD │
│  Layer 4 质量保障: superpowers:TDD + gstack:/qa + gstack:/cso    │
└─────────────────────────────────────────────────────────────────┘

新融合方案（BMAD 替代 Speckit/OpenSpec）:
┌─────────────────────────────────────────────────────────────────┐
│  Layer 1 规格引擎: /kdev:brainstorm + /kdev:prd                  │
│  Layer 2 计划引擎: /kdev:arch + /kdev:epics                      │
│  Layer 3 执行引擎: /kdev:sprint + /kdev:dev + superpowers:TDD    │
│  Layer 4 质量保障: /kdev:test + /kdev:review + gstack:/cso       │
└─────────────────────────────────────────────────────────────────┘
```

### 2.4 二次开发合规建议

**命名规范**：
```
❌ 不可使用：KDev-BMAD, BMad-KDev, BMadMethod-Agent
✅ 可以使用：KDev-Agent, KDev-Method, "兼容 BMad Method"
```

**License 声明格式**：
```markdown
# License

KDev-Agent incorporates code from the following projects:

1. **BMad Method** (MIT License, BMad Code, LLC)
   - Source: https://github.com/bmad-code-org/bmad-builder
   - Note: BMad trademarks not licensed; used only to describe compatibility

2. **oh-my-claudecode** (MIT License, Yeachan Heo)
   - Source: https://github.com/Yeachan-Heo/oh-my-claudecode
   - Components: State management, Team Pipeline

[继续列出其他来源...]
```

---

## 三、KDev 命令命名体系

### 3.1 命名原则

```
原则 1：所有命令以 /kdev: 开头
原则 2：语义清晰，避免歧义
原则 3：与 BMAD 命令对应但使用 KDev 品牌名
```

### 3.2 命令映射表

#### Phase 1：分析阶段

| BMAD 命令 | KDev 命令 | 说明 |
|-----------|----------|------|
| `/bmad-brainstorm` | `/kdev:brainstorm` | 头脑风暴 |
| `/bmad-market-research` | `/kdev:research --market` | 市场研究 |
| `/bmad-domain-research` | `/kdev:research --domain` | 领域研究 |
| `/bmad-technical-research` | `/kdev:research --tech` | 技术研究 |
| `/bmad-product-brief` | `/kdev:brief` | 产品简报 |

#### Phase 2：规划阶段

| BMAD 命令 | KDev 命令 | 说明 |
|-----------|----------|------|
| `/bmad-create-prd` ★ | `/kdev:prd` ★ | PRD 生成 |
| `/bmad-validate-prd` | `/kdev:prd --validate` | PRD 验证 |
| `/bmad-edit-prd` | `/kdev:prd --edit` | PRD 编辑 |
| `/bmad-create-ux-design` | `/kdev:ux` | UX 设计 |

#### Phase 3：方案阶段

| BMAD 命令 | KDev 命令 | 说明 |
|-----------|----------|------|
| `/bmad-create-architecture` ★ | `/kdev:arch` ★ | 架构设计 |
| `/bmad-create-epics-and-stories` ★ | `/kdev:epics` ★ | Epic/Story 生成 |
| `/bmad-check-implementation-readiness` ★ | `/kdev:ready` ★ | 就绪检查 |

#### Phase 4：实现阶段

| BMAD 命令 | KDev 命令 | 说明 |
|-----------|----------|------|
| `/bmad-sprint-planning` ★ | `/kdev:sprint` ★ | Sprint 规划 |
| `/bmad-sprint-status` | `/kdev:status` | Sprint 状态 |
| `/bmad-create-story` | `/kdev:story` | 创建故事 |
| `/bmad-dev-story` ★ | `/kdev:dev` ★ | 开发故事 |
| `/bmad-code-review` | `/kdev:review` | 代码审查 |
| `/bmad-qa-test` | `/kdev:test` | QA 测试 |

#### 辅助命令

| BMAD 命令 | KDev 命令 | 说明 |
|-----------|----------|------|
| `/bmad-help` | `/kdev:help` | 帮助导航 |
| `/bmad-correct-course` | `/kdev:correct` | 纠偏导航 |
| `/bmad-quick-dev` | `/kdev:quick` | 快速开发 |
| `/bmad-document-project` | `/kdev:doc` | 项目文档 |
| `/bmad-generate-project-context` | `/kdev:context` | 上下文生成 |

#### OMC 融合命令

| OMC 功能 | KDev 命令 | 说明 |
|----------|----------|------|
| `notepad` | `/kdev:note` | 工作记忆 |
| `project-memory` | `/kdev:memory` | 项目记忆 |
| Team Pipeline | `/kdev:team` | 团队编排 |
| autopilot | `/kdev:auto` | 自动执行（可选） |

#### 记忆系统命令（新增）

| 功能 | KDev 命令 | 说明 |
|------|----------|------|
| Compound Engineering | `/kdev:compound` | 增值复盘 |
| Questions Log | `/kdev:questions` | 决策记录 |
| Gotchas | `/kdev:gotchas` | 陷阱记录 |

### 3.3 命令体系结构图

```
/kdev: 根命令
│
├── 分析 (Research)
│   ├── /kdev:brainstorm
│   ├── /kdev:research [--market|--domain|--tech]
│   └── /kdev:brief
│
├── 规划 (Planning) ★
│   ├── /kdev:prd [--validate|--edit]
│   └── /kdev:ux
│
├── 方案 (Solutioning) ★
│   ├── /kdev:arch
│   ├── /kdev:epics
│   └── /kdev:ready  ← 门控点
│
├── 实现 (Implementation) ★
│   ├── /kdev:sprint
│   ├── /kdev:story
│   ├── /kdev:dev
│   ├── /kdev:review
│   └── /kdev:test
│
├── 辅助 (Utilities)
│   ├── /kdev:help
│   ├── /kdev:status
│   ├── /kdev:correct
│   ├── /kdev:quick
│   ├── /kdev:doc
│   └── /kdev:context
│
├── 记忆 (Memory)
│   ├── /kdev:note
│   ├── /kdev:memory
│   ├── /kdev:compound
│   ├── /kdev:questions
│   └── /kdev:gotchas
│
└── 编排 (Orchestration)
│   ├── /kdev:team
│   └── /kdev:auto (可选)
```

---

## 四、总结与建议

### 4.1 核心决策

| 问题 | 结论 | 行动 |
|------|------|------|
| BMAD 能否替代 Speckit | ✅ **可以替代**，BMAD 更完善 | 移除 Speckit 概念，采用 BMAD 规格体系 |
| License 是否支持二次开发 | ✅ MIT 支持 | 需遵守商标限制，使用 KDev 独立品牌 |
| 命令命名 | ✅ 全部改为 `/kdev:` 前缀 | 更新所有文档和 Skill 定义 |

### 4.2 后续行动

1. **更新架构文档**：将 BMAD 命令替换为 KDev 命令
2. **补充 License 声明**：确认 OMC、Superpowers、Gstack 的 License
3. **创建 KDev Skill 文件**：按新命名体系编写 Skill 定义

---

## 五、已完成确认

| 项目 | 状态 | License |
|------|------|---------|
| OMC License | ✅ 已确认 | MIT (Yeachan Heo) |
| Superpowers License | ✅ 已确认 | MIT (Jesse Vincent) |
| Gstack License | ✅ 已确认 | MIT (Garry Tan) |
| Spec-Kit License | ✅ 已确认 | MIT (GitHub, Inc.) |
| OpenSpec License | ✅ 已确认 | MIT (OpenSpec Contributors) |
| BMAD License | ✅ 已确认 | MIT (BMad Code, LLC) + 商标限制 |

---

## 参考链接

- [BMad Builder GitHub](https://github.com/bmad-code-org/bmad-builder)
- [BMad License](https://raw.githubusercontent.com/bmad-code-org/bmad-builder/main/LICENSE)
- [BMad Trademark Guidelines](https://raw.githubusercontent.com/bmad-code-org/bmad-builder/main/TRADEMARK.md)
- [oh-my-claudecode GitHub](https://github.com/Yeachan-Heo/oh-my-claudecode)
- [Superpowers GitHub](https://github.com/obra/superpowers)
- [Gstack GitHub](https://github.com/garrytan/gstack)
- [Spec-Kit GitHub](https://github.com/github/spec-kit)
- [OpenSpec GitHub](https://github.com/Fission-AI/OpenSpec)