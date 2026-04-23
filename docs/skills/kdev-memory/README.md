# kdev-memory 文档

工程记忆插件的专属文档。插件代码在 [plugins/kdev-memory/](../../../plugins/kdev-memory/)。

## 目录

| 文档 | 内容 |
|------|------|
| [开发历程.md](开发历程.md) | **两 Part 长文**：Part 1（0.1.0 → 0.3.0）讲从 token-statistics Sprint 0 自用脚手架到插件 0.3.0 的 10 天 4 迭代；Part 2（0.3.0 → 0.5.1）讲 2026-04-22 ~ 04-23 两天内 7 轮 skill-quality iteration + iter-7 决策反转教训。[meta/skill-开发通用流程.md](../../meta/skill-开发通用流程.md) 多处引用本文 |
| [dev-notes/](dev-notes/) | 版本迭代期间的专题笔记（见下） |

## dev-notes 清单

| 日期 | 主题 | 对应版本/事件 |
|------|------|---------------|
| [2026-04-19](dev-notes/2026-04-19-跨会话记忆与压缩保护-方案对比.md) | 跨会话记忆与压缩保护方案对比（6 家框架） | 0.2.0 PreCompact hook 设计依据 |
| [2026-04-21](dev-notes/2026-04-21-三方记忆方案对比-官方auto-memory-vs-claude-remember-vs-kdev-memory.md) | 三方收敛对比：官方 auto-memory vs claude-remember vs kdev-memory | 0.3.0 定位声明 |
| [2026-04-22](dev-notes/2026-04-22-skill-CLAUDEmd模板漂移审计-token-statistics与KDevSec对照.md) | CLAUDE.md 模板在 token-statistics 和 KDevSec 之间的漂移审计 | 0.5.0 解耦改造的主驱动 |
| [2026-04-22](dev-notes/2026-04-22-审计修订对账-session-end-state.md) | 审计修订对账 + 2026-04-22 session 结束态归档 | 0.5.0 发布前的状态对账 |
| [2026-04-22](dev-notes/2026-04-22-skill使用记录与体验评分维度缺口.md) | Step schema 缺"使用的 skill"事实字段 + 评分维度取舍 | v0.6.0 候选（方案 A：事实列表 + 单一评分）|

## skill-quality eval 线（2026-04-22 起）

本 skill 的行为级测试在 [plugins/kdev-memory/evals/skill-quality/](../../../plugins/kdev-memory/evals/skill-quality/)，当前有 **7 轮 iteration**：

| iteration | 内容 | 关键结论 |
|---|---|---|
| 20260422-01 | 首轮 3 场景探索 | 演进记录 |
| 20260422-02 | 扩展 6 场景 + 升级 assertions | Phase 1 重构行为零损失，-19.6% tokens |
| 20260422-03 | CLAUDE.md 接口/实现解耦 | 规则段 57 → 38 行，边缘场景零 regression |
| 20260422-04 | `claude_md_contract` lint + 修漂移流程 | 审计 P1-7 落地 |
| 20260422-05 | eval-6 跨会话续航场景补齐 | skill 语义理解到位 |
| 20260423-06 | Step 完整度 lint（P1-5/6） | skill "坦诚反思"路线补半残 |
| 20260423-07 | **P0-1 闸门 discriminating**（**决策反转教学样本**）| 初版"不加"被 user 反问推翻；每次省 ~12k tokens 值得 +22 行文档 |

## 开发方法论

看 [../../meta/](../../meta/)——kdev-memory 就是那份方法论的第一个真实案例。

本仓库 [plugins/kdev-memory/CHANGELOG.md](../../../plugins/kdev-memory/CHANGELOG.md) 从 0.1.0 记录到 0.5.1 的全部发布。
