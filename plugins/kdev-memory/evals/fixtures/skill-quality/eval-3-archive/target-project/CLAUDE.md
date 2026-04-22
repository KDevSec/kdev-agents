# blog-app

博客平台 / Next.js + Postgres / 个人项目

## 智能体自动记录规则

（kdev-memory 触发规则段已装入，此处模拟简化版）

- 实时落盘
- 每日汇总从 .kdev/memory/ 聚合不翻会话
- 每次完成 Step 顺手改 frontmatter
- 看到 Stop hook 归档提醒 → 问用户再切档
