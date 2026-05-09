# kdev-memory 文档目录总结

## 目录结构

```
kdev-memory/
├── README.md                      # 文档索引
├── kdev-memory 开发历程技术分享.md   # 长文分享
├── dev-notes/                     # 开发笔记（14 个文件）
├── plans/                         # 规划文档（1 个文件）
```

## 文档主题

### 根目录

| 文件 | 主题 |
|------|------|
| README.md | 文档索引 + skill-quality eval 7轮迭代记录 |
| kdev-memory 开发历程技术分享.md | 从 token-statistics Sprint 0 自用脚手架到插件 0.6.0 的演进故事 |

### dev-notes/ 开发笔记

| 文件 | 主题 |
|------|------|
| 2026-04-19-跨会话记忆与压缩保护-方案对比.md | 对比 6 家框架的记忆保护方案，为 PreCompact hook 设计提供依据 |
| 2026-04-21-三方记忆方案对比-官方auto-memory-vs-claude-remember-vs-kdev-memory.md | 三家记忆方案正交定位声明 |
| 2026-04-22-skill-CLAUDEmd模板漂移审计-token-statistics与KDevSec对照.md | CLAUDE.md 模板漂移审计，驱动 0.5.0 解耦改造 |
| 2026-04-22-审计修订对账-session-end-state.md | 0.5.0 发布前状态对账 |
| 2026-04-22-skill使用记录与体验评分维度缺口.md | Step schema 缺"使用的 skill"字段分析 |
| 2026-04-24-brief-hook-欠评step误报-褪色补录占位识别缺口.md | Brief hook 误报问题分析 |
| 2026-04-24-kdev-memory-git托管立场反转-过程vs产物分家.md | git 托管立场反转论证 |
| 2026-04-24-step粒度从phase到自然停顿点的认知演进.md | Step 粒度定义演进 |
| 2026-04-24-todowrite跨会话接力缺口.md | TodoWrite 跨会话接力问题 |
| 2026-04-24-多会话同项目编号冲突.md | 多会话编号冲突问题 |
| 2026-04-25-WINDOWS-COMPAT-REPORT.md | Windows 兼容性报告 |
| 2026-04-27-windows-python3-hook兼容性问题.md | Windows Python3 hook 兼容性问题 |
| 2026-04-28-kdev-memory-subagent方案评审意见.md | Subagent 记录模式评审意见 |
| 2026-04-28-kdev-memory-subagent记录模式方案.md | Subagent 记录模式方案设计 |
| 2026-04-29-kdev-memory-subagent记录模式方案-修订版.md | Subagent 方案修订版 |

### plans/ 规划文档

| 文件 | 主题 |
|------|------|
| 2026-04-24-kdev-memory-v0.7.md | v0.7 立场反转 + Brief 三层分层 + 销账语义重构实施计划 |

## 总体定位

工程记忆插件 kdev-memory 的开发文档，记录从 0.1.0 → 0.7.0 的设计决策、方案对比、踩坑日志及迭代规划。