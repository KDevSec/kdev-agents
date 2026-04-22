# kdev-memory 文档

工程记忆插件的专属文档。插件代码在 [plugins/kdev-memory/](../../../plugins/kdev-memory/)。

## 目录

| 文档 | 内容 |
|------|------|
| [开发历程.md](开发历程.md) | 从 token-statistics Sprint 0 自用脚手架 → 插件 0.3.0 的 10 天 4 迭代实战故事。真实案例锚点，[meta/skill-开发通用流程.md](../../meta/skill-开发通用流程.md) 多处引用本文 |
| [dev-notes/](dev-notes/) | 版本迭代期间的专题笔记（见下） |

## dev-notes 清单

| 日期 | 主题 | 对应版本/事件 |
|------|------|---------------|
| [2026-04-19](dev-notes/2026-04-19-跨会话记忆与压缩保护-方案对比.md) | 跨会话记忆与压缩保护方案对比（6 家框架） | 0.2.0 PreCompact hook 设计依据 |
| [2026-04-21](dev-notes/2026-04-21-三方记忆方案对比-官方auto-memory-vs-claude-remember-vs-kdev-memory.md) | 三方收敛对比：官方 auto-memory vs claude-remember vs kdev-memory | 0.3.0 定位声明 |
| [2026-04-22](dev-notes/2026-04-22-skill-CLAUDEmd模板漂移审计-token-statistics与KDevSec对照.md) | CLAUDE.md 模板在 token-statistics 和 KDevSec 之间的漂移审计 | iter-3 前置调查 |
| [2026-04-22](dev-notes/2026-04-22-审计修订对账-session-end-state.md) | 上一份审计的修订对账 + session 结束态归档 | iter-3 收尾 |

## 开发方法论

看 [../../meta/](../../meta/)——kdev-memory 就是那份方法论的第一个真实案例。
