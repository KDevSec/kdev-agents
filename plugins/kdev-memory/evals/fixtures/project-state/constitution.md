---
triggers: ["架构决策", "技术选型", "不可逆"]
---

# 项目宪章

这是项目的顶层原则，所有架构决策都要按这里的准则走。

## 决策流程

1. **任何架构决策都要走 Q-NNN 流程**：写到 .kdev/memory/决策日志.md，
   列选项 + 用户选择 + 理由。不允许 Claude 私自拍板。
2. **技术选型在 MVP 阶段倾向简单**：宁可后期重写，不要前期过度设计。
3. **不可逆操作必须二次确认**：数据库迁移、删文件、force push 等。

## 当前选型

- 语言：Node.js + TypeScript
- 数据库：SQLite（MVP），后期评估切 Postgres
- 打包：pnpm workspace
- 测试：Vitest
