# kdev-change 文档

变更提案 skill 的设计规划。**本 skill 尚未实现**——本目录只存设计文档和讨论记录，未来真正落地前请先读 [meta/skill-开发通用流程.md](../../meta/skill-开发通用流程.md) §二/三（痛点驱动，不按路线图）。

## 目录

| 文档 | 状态 | 内容 |
|------|------|------|
| [2026-04-22-01-kdev-change-变更提案skill设计.md](2026-04-22-01-kdev-change-变更提案skill设计.md) | 规划中（未实现） | 源起 token-statistics 8 轮迭代后发现 PRD/SR 漂移现象，借鉴 OpenSpec 思路拟新增 `kdev-change` + 一个配套 skill。未决策项见文档 §6 |

## 合理的下一步

按方法论 §一（先在真项目里自用，不以"做通用插件"起步）：

1. 在 token-statistics 或 KDevSec 里以 `.kdev/` 脚手架形式跑 `kdev-change` 的核心逻辑 1-2 周
2. 实时采集失败证据（见方法论 §二）
3. 证据充分后再抽成插件，走 `superpowers:writing-skills` 流程
