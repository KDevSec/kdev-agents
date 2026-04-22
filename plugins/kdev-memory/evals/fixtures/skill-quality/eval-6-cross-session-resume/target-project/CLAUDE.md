# chat-service

即时通讯后端 / Go + Redis + Postgres

## 智能体自动记录规则

（kdev-memory 触发规则段已装入）

- 实时落盘到 .kdev/memory/
- 每日汇总从文件聚合不翻会话
- 新会话问"昨天做到哪了"→ 从 .kdev/memory/ 当前状态.md + 最近几天汇总 + 执行日志回读
