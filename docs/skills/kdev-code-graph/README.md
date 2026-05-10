# kdev-code-graph 设计文档

> Claude Code plugin — 基于 Understand-Anything 上游 + kdev-secure-coding 安全规范覆盖层

## 文档索引

### 当前生效（v2 路径）

| 文档 | 说明 |
|---|---|
| [2026-05-10-实施计划-v2.md](2026-05-10-实施计划-v2.md) | **当前实施计划**——Spike 验证 + 12 个 TDD 任务 |

### 历史归档

| 文档 | 说明 |
|---|---|
| [2026-04-27-产品需求文档.md](2026-04-27-产品需求文档.md) | PRD v1.1.0 |
| [2026-04-27-架构设计方案.md](2026-04-27-架构设计方案.md) | v1 架构（部分仍适用） |
| [2026-04-28-调研报告.md](2026-04-28-调研报告.md) | 一次调研 |
| [2026-04-28-实施计划.md](2026-04-28-实施计划.md) | **已归档**——CRG 路径，被 v2 取代 |
| [2026-04-28-评审方案.md](2026-04-28-评审方案.md) | v1 评审结论 |
| [2026-04-28-文档综合评审报告-by灵码.md](2026-04-28-文档综合评审报告-by灵码.md) | 灵码评审 |
| [2026-04-28-文档二次评审报告-by灵码.md](2026-04-28-文档二次评审报告-by灵码.md) | 灵码复审 |

### 二次调研

| 文档 | 说明 |
|---|---|
| [references/README.md](references/README.md) | 4 项目调研下载指引 |
| [references/COMPARATIVE_ANALYSIS.md](references/COMPARATIVE_ANALYSIS.md) | 4 项目综合对比 |
| [references/FEATURE_FIT_ANALYSIS.md](references/FEATURE_FIT_ANALYSIS.md) | 4 需求适配度（UA 20/20） |
| [references/DISCUSSION_AGENDA.md](references/DISCUSSION_AGENDA.md) | 5 个待决策问题 |

## 核心功能（v2）

| 功能 | Skill | 实现 |
|---|---|---|
| 建图 + 安全规范灌入 | `/kdev-graph-build` | UA `/understand` + kdev-ingestor |
| 规范 ↔ 代码追溯 | `/trace-security` | 查图谱 `kdev:security_rule` 节点 |
| 变更爆炸半径 | `/security-impact` | UA `/understand-diff` + 安全节点过滤 |
| 文档代码同步 | `/doc-code-sync` | UA `document` 节点 + 时间戳比对 |

## 实施状态（v2）

| 维度 | 状态 |
|---|---|
| 设计文档 | ✅ v2 完整 |
| Spike 验证 | ✅ 通过（UA 21 节点 + 35 边 + passthrough） |
| 实施计划 | ✅ 12 个 TDD 任务 |
| 实施代码 | ✅ Tasks 0-12 完成 |
