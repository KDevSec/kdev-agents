# kdev-memory 文档目录概览

## 目录结构

```
docs\skills\kdev-memory\
|-- README.md
|-- kdev-memory 开发历程技术分享.md
|-- dev-notes\
|   |-- 2026-04-19-跨会话记忆与压缩保护-方案对比.md
|   |-- 2026-04-21-三方记忆方案对比-官方auto-memory-vs-claude-remember-vs-kdev-memory.md
|   |-- 2026-04-22-skill-CLAUDEmd模板漂移审计-token-statistics与KDevSec对照.md
|   |-- 2026-04-22-skill使用记录与体验评分维度缺口.md
|   |-- 2026-04-22-审计修订对账-session-end-state.md
|   |-- 2026-04-24-brief-hook-欠评step误报-褪色补录占位识别缺口.md
|   |-- 2026-04-24-kdev-memory-git托管立场反转-过程vs产物分家.md
|   |-- 2026-04-24-step粒度从phase到自然停顿点的认知演进.md
|   |-- 2026-04-24-todowrite跨会话接力缺口.md
|   |-- 2026-04-24-多会话同项目编号冲突.md
|   |-- 2026-04-25-WINDOWS-COMPAT-REPORT.md
|   |-- 2026-04-27-windows-python3-hook兼容性问题.md
|   |-- 2026-04-28-kdev-memory-subagent记录模式方案.md
|   |-- 2026-04-28-kdev-memory-subagent方案评审意见.md
|   |-- 2026-04-29-kdev-memory-subagent记录模式方案-修订版.md
|-- plans\
    |-- 2026-04-24-kdev-memory-v0.7.md
```

## 文档主题摘要

### 主目录文件

| 文档 | 主题摘要 |
|------|----------|
| **README.md** | kdev-memory 文档索引，列出开发历程、dev-notes 清单、skill-quality eval 迭代记录及开发方法论入口。 |
| **kdev-memory 开发历程技术分享.md** | 完整记录插件从 v0.1.0 到 v0.6.0 的演进故事，包括设计起源、版本迭代过程、横向调研要点和可借鉴的设计范式。 |

### dev-notes 目录

| 文档 | 主题摘要 |
|------|----------|
| **2026-04-19-跨会话记忆与压缩保护-方案对比.md** | 横向调研 6 家记忆框架的 PreCompact/SessionStart 方案，推荐中等档方案（checkpoint 快照 + source 分档注入）。 |
| **2026-04-21-三方记忆方案对比.md** | 对比官方 auto-memory、claude-remember、kdev-memory 三家定位差异，明确三者正交而非替代关系。 |
| **2026-04-22-skill-CLAUDEmd模板漂移审计.md** | 审计 token-statistics 与 KDevSec 两项目的 CLAUDE.md 模板漂移，识别 8 个干扰点并提出分层修订建议。 |
| **2026-04-22-skill使用记录与体验评分维度缺口.md** | 分析 Step schema 缺失"使用的 skill"字段问题，最终决策采纳方案 A（事实层加 skill 名单，评分维持单一维度）。 |
| **2026-04-22-审计修订对账-session-end-state.md** | 对账审计问题修复进度，记录 4 个 commit 产出及 P0/P1/P2 各项状态。 |
| **2026-04-24-brief-hook-欠评step误报.md** | 发现 brief hook 把"褪色补录占位"误报为欠评 Step，提出启发式识别方案修复。 |
| **2026-04-24-kdev-memory-git托管立场反转.md** | **重大决策反转**：`.kdev/` 从"应 git 托管"改为"默认 gitignore"，核心理念是过程与产物分离。 |
| **2026-04-24-step粒度认知演进.md** | 记录 Step 粒度定义从"phase=Step 硬规则"到"自然停顿点三信号"的认知演进过程。 |
| **2026-04-24-todowrite跨会话接力缺口.md** | 分析 TodoWrite 数据跨会话丢失问题，决策采用方案 ②（约定级 body 同步，不写 hook）。 |
| **2026-04-24-多会话同项目编号冲突.md** | 分析多会话并发时编号冲突问题，横比 6 种方案，决策采用方案 V（git 原生 + 文档约定）。 |
| **2026-04-25-WINDOWS-COMPAT-REPORT.md** | v0.8.0 Windows 兼容性验证报告，记录纯 Python 化重构后 123 tests pass，解决 GBK 编码等问题。 |
| **2026-04-27-windows-python3-hook兼容性问题.md** | 解决 Windows 上 python3 命令指向无效 stub 的问题，采用 polyglot wrapper 方案。 |
| **2026-04-28-subagent记录模式方案.md** | 提出用 Subagent 两阶段调用降低主会话上下文占用的方案设计。 |
| **2026-04-28-subagent方案评审意见.md** | 灵码对 subagent 方案的评审意见，综合评分 8.2/10，指出 P0 问题需修复。 |
| **2026-04-29-subagent方案-修订版.md** | v3.0 推翻 Subagent 方案（全局 token +213%），转向 D+E 方案（精简 SKILL.md + 延迟加载）。 |

### plans 目录

| 文档 | 主题摘要 |
|------|----------|
| **2026-04-24-kdev-memory-v0.7.md** | v0.7 版本规划，涉及 git 托管立场反转、worktree 共享机制等改动。 |

## 文档分类概览

1. **方案调研类**：跨会话记忆对比、三方方案对比
2. **问题诊断类**：CLAUDE.md 漂移审计、欠评误报、TodoWrite 缺口、编号冲突
3. **决策记录类**：git 托管立场反转、Step 粒度演进、评分维度决策
4. **技术评审类**：subagent 方案设计及评审意见、修订版
5. **平台兼容类**：Windows 兼容报告、python3 hook 问题
6. **版本规划类**：v0.7 规划文档
7. **历史总结类**：开发历程技术分享、README 索引