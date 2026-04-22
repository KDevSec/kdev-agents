# analytics-service

分析服务后端，Node.js 22 + Postgres。

## 智能体自动记录规则

（kdev-memory 触发规则段已装入）

- 实时落盘到 .kdev/memory/
- 每日汇总从文件聚合不翻会话
- 如果 .kdev/memory/ 当天条目为空，**坦白报告**，不要凭印象补写
