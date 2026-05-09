# kdev-memory 文档目录总结

## 目录结构

```
docs/skills/kdev-memory/
├── README.md                              # 目录索引
├── kdev-memory 开发历程技术分享.md           # 完整演进历程
├── plans/
│   └── 2026-04-24-kdev-memory-v0.7.md     # v0.7 版本规划
└── dev-notes/                             # 设计笔记目录
    ├── 2026-04-19-跨会话记忆与压缩保护-方案对比.md
    ├── 2026-04-21-三方记忆方案对比-官方auto-memory-vs-claude-remember-vs-kdev-memory.md
    ├── 2026-04-22-skill-CLAUDEmd模板漂移审计-token-statistics与KDevSec对照.md
    ├── 2026-04-22-skill使用记录与体验评分维度缺口.md
    ├── 2026-04-22-审计修订对账-session-end-state.md
    ├── 2026-04-24-brief-hook-欠评step误报-褪色补录占位识别缺口.md
    ├── 2026-04-24-kdev-memory-git托管立场反转-过程vs产物分家.md
    ├── 2026-04-24-step粒度从phase到自然停顿点的认知演进.md
    ├── 2026-04-24-todowrite跨会话接力缺口.md
    ├── 2026-04-24-多会话同项目编号冲突.md
    ├── 2026-04-25-WINDOWS-COMPAT-REPORT.md
    ├── 2026-04-27-windows-python3-hook兼容性问题.md
    ├── 2026-04-28-kdev-memory-subagent记录模式方案.md
    ├── 2026-04-28-kdev-memory-subagent方案评审意见.md
    └── 2026-04-29-kdev-memory-subagent记录模式方案-修订版.md
```

## 文档主题总结

### 核心文档

| 文档 | 主题概述 |
|------|----------|
| **README.md** | 目录索引文档，列出插件主要文档清单和 dev-notes 设计笔记 |
| **kdev-memory 开发历程技术分享.md** | 从 0.1.0 到 0.6.0 的完整演进历程，包括实战验证抽象过程、版本迭代决策和设计范式 |
| **plans/2026-04-24-kdev-memory-v0.7.md** | v0.7 版本规划文档 |

### dev-notes 设计笔记

| 文档 | 主题概述 |
|------|----------|
| **2026-04-19-跨会话记忆与压缩保护-方案对比.md** | 调研 6 家记忆框架的 PreCompact/SessionStart 策略，推荐中等档方案用于压缩保护 |
| **2026-04-21-三方记忆方案对比** | 对比官方 auto-memory、claude-remember、kdev-memory 三家定位，明确正交互补关系 |
| **2026-04-22-CLAUDEmd模板漂移审计** | 审计两个项目的 CLAUDE.md 漂移问题，发现规则层漂移、Step 无闸门等核心问题 |
| **2026-04-22-skill使用记录与体验评分维度缺口.md** | 分析 Step schema 缺 skill 字段问题，决定事实层加名单而不增评分维度 |
| **2026-04-22-审计修订对账** | 记录审计修订对账结果，追踪各优先级问题处理状态 |
| **2026-04-24-brief-hook欠评误报** | 发现 brief hook 对"褪色补录占位"的误报，建议启发式识别已销账状态 |
| **2026-04-24-git托管立场反转** | 核心立场反转：`.kdev/` 改为本地过程目录默认 gitignore，过程与产物分离 |
| **2026-04-24-step粒度认知演进** | Step 粒度从 phase 硬规则演进到自然停顿点三信号（时长/干预/验收） |
| **2026-04-24-todowrite跨会话接力** | TodoWrite 跨会话缺口分析，采用约定级方案而非自动化 hook |
| **2026-04-24-多会话编号冲突** | 多会话编号冲突分析，推荐 git 原生 + 文档约定方案 |
| **2026-04-25-WINDOWS-COMPAT-REPORT** | Windows 兼容性报告，v0.8.0 纯 Python 化后不再需 Git Bash |
| **2026-04-27-windows-python3兼容性** | Windows python3 是 stub 的问题，采用 polyglot wrapper 修复 |
| **2026-04-28-subagent记录模式方案** | 提出 Subagent 两阶段调用方案降低主会话上下文占用 |
| **2026-04-28-subagent方案评审意见** | 灵码评审意见，评分 8.2/10，提出 P0/P1 问题修复建议 |
| **2026-04-29-subagent方案修订版** | v3.0 推翻 Subagent 方案（全局 token +213%），提出 D+E 替代方案 |

## 文档分类

### 方案调研类
- 跨会话记忆与压缩保护方案对比
- 三方记忆方案对比
- Subagent 记录模式方案系列（方案 → 评审 → 修订推翻）

### 问题审计类
- CLAUDEmd 模板漂移审计
- 审计修订对账

### 设计演进类
- Git 托管立场反转
- Step 粒度认知演进
- Skill 使用记录维度缺口
- Todowrite 跨会话接力
- 多会话编号冲突

### 跨平台兼容类
- Windows 兼容性报告
- Windows python3 hook 兼容性

### Hook 问题类
- Brief hook 欠评误报