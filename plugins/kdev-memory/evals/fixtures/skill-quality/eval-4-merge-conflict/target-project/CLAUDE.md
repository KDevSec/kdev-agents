# legacy-api 项目指南

长期维护的内部 API 项目。本 CLAUDE.md 有一部分是旧版 kdev-memory skill（v0.2.0 时代）的遗留。

## 开发惯例

- Node.js 18 + Express
- 提交前必须跑 `npm test`

## 智能体自动记录规则

（以下为 v0.2.0 时代写入，与当前 skill 不完全对齐——这是故意留着的，用来测试合并策略）

- 每完成一个任务，在 `.kdev/执行日志.md` 追加一条记录（注意：v0.2.0 的文件位置，不是 .kdev/memory/）
- 决策记在 `.kdev/决策.md`
- 踩坑记在 `.kdev/坑.md`
- 编号规则：Step 按迭代内递增（Sprint 1 开始的时候定下来的）
- 不需要写每日汇总（v0.2.0 没有这个概念）
- 不需要 triggers 字段（v0.2.0 没有召回机制）

### 评分机制

每步打 1-5 顺畅度分，不需要用户评分，模型自评即可。

## 其他约束

- 数据库 schema 变更必须先过 code review
- 发布前必须 tag
