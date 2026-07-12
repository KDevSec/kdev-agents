# docs/

KDev-agents 文档总索引。按"属于什么"分三层：

| 目录 | 内容 | 何时翻 |
|-----|------|--------|
| [framework/](framework/) | KDev 整体框架的调研、设计、评审、归档、参考资料 | 想了解 KDev 架构愿景、命令体系、记忆模型等**不属于单个 skill** 的决策 |
| [skills/](skills/) | 每个 skill 的专属调研、设计、开发笔记、案例 | 开发/迭代某个 skill；了解一个 skill 是怎么长出来的 |
| [meta/](meta/) | 跨 skill 的**方法论**——官方 skill 开发流程 + 作者实战补充 | 要做新 skill 时先读，不限具体 skill |

## 快速跳转

**读一份就够（当前最权威）**：
- 架构：[framework/01-design/2026-04-15-02-KDev架构设计v3.0.2修订.md](framework/01-design/2026-04-15-02-KDev架构设计v3.0.2修订.md)
- 开发方法论：[meta/skill-开发通用流程.md](meta/skill-开发通用流程.md)

**工程记忆蒸馏沉淀（2026-07-10 首次 promote，长效项目资产）**：
- 架构决策记录：[framework/架构决策日志-ADR.md](framework/架构决策日志-ADR.md) — 23 条 ADR + 决策演进/取代链
- 踩坑索引：[framework/踩坑索引.md](framework/踩坑索引.md) — 13 条速查，「先核代码再信设计」案例群领衔
- 方法论反思：[meta/方法论沉淀-实战反思.md](meta/方法论沉淀-实战反思.md) — 5 条可操作规则，R-009 领衔

**已实现的 skill**：
- [skills/kdev-memory/](skills/kdev-memory/) — 工程记忆插件
- [skills/kdev-commit/](skills/kdev-commit/) — AI commit + push 插件（文档待补）

**规划中的 skill**：
- [skills/kdev-change/](skills/kdev-change/) — 变更提案 skill（2026-04-22 起草设计）

## 新增 skill 的落地位置

开一个新 skill（比如 `kdev-foo`）时：
1. 代码落在 `plugins/kdev-foo/`（插件主体）
2. 调研/设计/开发笔记落在 `docs/skills/kdev-foo/`（本目录下新建）
3. 跨 skill 共用的方法论沉淀到 `meta/`
