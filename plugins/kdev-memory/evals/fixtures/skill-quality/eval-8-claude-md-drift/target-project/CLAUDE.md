# legacy-service

长期维护的订单服务。2026-02 装了 kdev-memory skill（当时还是 0.2.0 时代），
之后 skill 升级到新接口但 CLAUDE.md 没跟上。

## 开发惯例

- Node.js 22 + TypeScript
- 提交前 `npm test`

## 智能体自动记录规则

本项目启用 kdev-memory 工程记忆制度。

### 贯穿 session 铁规

🔴 **实时落盘**：每做完一步立刻追加到 .kdev/memory/ 对应文件
🔴 **文件聚合不翻会话**：写汇总从 .kdev/memory/ 读当天条目

（缺第 3 条"优先处理 hook 产出"铁规；缺 <kdev-memory-brief> 和
<kdev-memory-recall> 注入响应；缺 WARN 文件和 checkpoint 响应）

### 召唤 kdev-memory skill 的时机

- 初始化 / 每日汇总 / 切档 / 规则升级
