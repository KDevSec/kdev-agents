# kdev-memory 文档目录探索结果

## 目录结构

```
docs/skills/kdev-memory/
├── README.md                               # 文档导航索引
├── kdev-memory 开发历程技术分享.md          # 技术分享长文
├── plans/
│   └── 2026-04-24-kdev-memory-v0.7.md      # 版本规划文档
└── dev-notes/
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

### 主文档

| 文档 | 主题 |
|------|------|
| **README.md** | kdev-memory 文档导航索引，列出所有 dev-notes 和 skill-quality eval 线的版本迭代历史 |
| **kdev-memory 开发历程技术分享.md** | 从 0.1.0 到 0.6.0 的完整演进故事，包括起源、设计原则、版本迭代历程、可借鉴范式和横向调研 |

### plans 目录

| 文档 | 主题 |
|------|------|
| **2026-04-24-kdev-memory-v0.7.md** | v0.7 版本规划，因 token 过大未完整读取，推测是版本功能规划文档 |

### dev-notes 目录

| 文档 | 主题 |
|------|------|
| **2026-04-19-跨会话记忆与压缩保护-方案对比.md** | 对比 6 家记忆框架的 PreCompact/SessionStart 机制，推荐方案 B（中等档）作为 kdev-memory 的实现路径 |
| **2026-04-21-三方记忆方案对比.md** | 对比官方 auto memory、claude-remember、kdev-memory 三家的定位差异，明确三者互补而非替代关系 |
| **2026-04-22-skill-CLAUDEmd模板漂移审计.md** | 全面审计 token-statistics 和 KDevSec 两项目的 CLAUDE.md 漂移问题，提出 9 条分层修订建议 |
| **2026-04-22-skill使用记录与体验评分维度缺口.md** | 提出 Step schema 缺"使用的 skill"字段问题，最终决策采纳方案 A（事实层加 skill 名单，评分维持单一维度） |
| **2026-04-22-审计修订对账-session-end-state.md** | 2026-04-22 session 结束态归档，记录审计问题的对账状态和下一步推荐入口 |
| **2026-04-24-brief-hook-欠评step误报.md** | 发现 SessionStart brief 把"褪色补录占位"误报为欠评 Step，建议方案 B（启发式跳过）修复 |
| **2026-04-24-kdev-memory-git托管立场反转.md** | 核心哲学反转：`.kdev/` 从"应该进 git"改为"本地过程目录默认 gitignore"，过程与产物分家 |
| **2026-04-24-step粒度认知演进.md** | 记录 Step 粒度从"phase=Step 硬规则"到"自然停顿点三信号"的三轮认知演进过程，展示 AI 与 user 的推理偏差 |
| **2026-04-24-todowrite跨会话接力缺口.md** | 讨论 TodoWrite 数据持久化问题，决策方案 ②（约定级）而非方案 ③（hook 自动化） |
| **2026-04-24-多会话同项目编号冲突.md** | 分析多会话并发时 Q/G/R/Step 编号冲突问题，横比 6 方案后选择方案 V（git 原生 + 文档约定） |
| **2026-04-25-WINDOWS-COMPAT-REPORT.md** | v0.8.0 Windows 跨平台兼容性测试报告，记录纯 Python 化重构后的测试结果和修复方案 |
| **2026-04-27-windows-python3-hook兼容性问题.md** | 记录 Windows 上 python3 命令指向 Windows Store stub 导致 hook 失败的问题，采用 polyglot wrapper 方案修复 |
| **2026-04-28-subagent记录模式方案.md** | 提出 Subagent 两阶段调用方案降低主会话上下文占用，待评审 |
| **2026-04-28-subagent方案评审意见.md** | Lingma 对 Subagent 方案的评审意见，综合评分 8.2/10，有条件通过需修复 P0 问题 |
| **2026-04-29-subagent方案-修订版.md** | v3.0 修订版，基于 Subagent 实际运行机制调研推翻 Subagent 方案，提出替代方案 D+E（精简 SKILL.md + 延迟加载） |

## 整体目的

kdev-memory 文档目录记录了一个工程记忆插件从 0.1.0 到 0.8.x 的完整演进历程，包括：
- 设计决策对比与横向调研
- 版本迭代中的问题发现与修复
- 核心哲学假设的反转（git 托管立场）
- 跨平台兼容性问题解决
- 降低上下文占用方案的探索与推翻

文档体现了"实战验证驱动设计"的方法论，每个 dev-note 都来源于真实项目踩坑，而非理论推演。