# Changelog — kdev-hud

## 0.1.0 — 2026-06-12
- 首版：第 4 plugin「观测层」，纯只读消费 kdev-core feature-first 账本。
- 通道① 命令行状态栏（单行 ANSI，字段映射真实数据）。
- 通道② 自包含 `hud.html`（完成度 / 当前活动 / 评审 PASS-FAIL / 告警 / 事件流 / 多功能队列）。
- 只读数据层：直读文件、零 kdev_core 运行时依赖、全容错降级；CLI `python3 -m kdev_hud {statusline,render}`。
- FF-3：gate 按 PASS/FAIL 渲染（无 score，未来加字段前向兼容）。
- 边界：绝不写 `features/`；render 仅写 `.kdev/hud.html`；坏数据降级不崩用户视图。
