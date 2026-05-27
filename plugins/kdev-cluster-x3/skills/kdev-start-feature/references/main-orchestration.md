# 主编排参考（kdev-start-feature 配套）

本文件为 `kdev-start-feature` skill 在初始化完成后的**主控员主循环参考**，与 `agents/主控员.md` 内容互补。

## init 后的状态

完成 `kdev-start-feature` 时：
- `.kdev/state.md` 已建（reqs=in_progress 第一 step）
- `.kdev/events.log` 已开（首条 step_start init）
- 需求澄清师 已派出（背景化跑）

## 主控员的循环步骤

当前 session 进入 `agents/主控员.md` 工作流 step 2 (reqs)：
- 等需求澄清师返回 → 派需求规格师 → 等返回 + 同步派 SR评审员 → ...
- 任何时候用户问"进度怎么样？"→ 调 `/kdev:hud`
- 收到任意 BLOCKED 事件 → 不直接处理；on-blocked hook 已被触发，会向对话流注入"派组长"指令

## 不要做

- 不要在 kdev-start-feature 阶段就派 reqs 第二/第三/... agent（那是主控员的事）。
- 不要在 kdev-start-feature 阶段就派 dev 组（reqs 全过 + reqs 组长聚合后才进 dev）。

## 退出条件

- 用户主动 abort：`Bash("TaskStop ...")` + state.md 改 status=aborted
- 全流程完成：F2 终审 verdict ∈ {pass, conditional, reject} → 主控员 ack + state.md current_active_group=idle
- 跨 session 续航：用户说"继续上次的工作" → 主控员读 state.md 报告位置 → 续跑（**不**重新进 kdev-start-feature）
