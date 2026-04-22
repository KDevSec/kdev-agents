# user-service

用户服务后端 / Node.js + TypeScript + Express

## 智能体自动记录规则

（kdev-memory 触发规则段已装入）

- 实时落盘到 .kdev/memory/
- **新会话进入项目先看 .kdev/memory/WARN-未记录-*.md**：SessionEnd hook 兜底的未落盘变更警告
  - 看到就**优先处理**：读快照 → 向用户核对 → 补记 Step → rm 文件
  - 不要忽略它往下做别的事
- 每日汇总从文件聚合不翻会话
