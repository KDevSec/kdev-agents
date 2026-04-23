# notification-svc

通知服务，Node.js + TypeScript。

## 智能体自动记录规则

本项目启用 kdev-memory 工程记忆制度。

### 3 条贯穿 session 铁规

🔴 实时落盘到 .kdev/memory/
🔴 文件聚合不翻会话
🔴 优先处理 hook 产出：WARN-未记录-*.md / <kdev-memory-brief> ⚠️ / <kdev-memory-recall> / checkpoints/压缩前-*.md
