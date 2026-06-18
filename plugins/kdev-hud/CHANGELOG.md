# Changelog — kdev-hud

## 0.3.0 — 2026-06-18
- `setup` 子命令（`python3 -m kdev_hud setup [--project|--user] [--force]`）+ `/kdev-hud-setup` slash 命令：幂等合并 `statusLine` 进 `settings.json`（只动该键，不 clobber 其他键；所有权检测——command 含 `kdev_hud` 视为本插件、允许原位刷新；他者 statusLine 默认跳过；`--force` 覆盖前自动备份 `settings.json.bak`；`--project` 写项目级、`--user` 写用户级）。
- 修 `__main__.py` 自举父目录到 `sys.path`：按绝对路径直跑 `__main__.py` 时可正确 import `kdev_hud` 包，绕开 PYTHONPATH 缺失问题（FF-2 修复；setup 写出的 statusLine 命令正是这一绝对路径形式）。

> G-004：本次改了 plugin version/command，用户需刷 marketplace（/plugin 更新或重装）+ 重启 session 才生效。

## 0.2.0 — 2026-06-18
- 派单可视化：datasource 读 `delivery-plan.yml`（guarded yaml）+ dispatch 事件配对派生。
- dashboard 渲染交付链进度（链进度 i/N）/ 派单流 / 员工忙闲。
- 自包含 `hud.html` `:target` 折叠钻入面板（location.hash 扛 2s 自动刷新，零外链）。

> G-004：本次改了 plugin version/skill/command/agent，用户需刷 marketplace（/plugin 更新或重装）+ 重启 session 才生效。

## 0.1.0 — 2026-06-12
- 首版：第 4 plugin「观测层」，纯只读消费 kdev-core feature-first 账本。
- 通道① 命令行状态栏（单行 ANSI，字段映射真实数据）。
- 通道② 自包含 `hud.html`（完成度 / 当前活动 / 评审 PASS-FAIL / 告警 / 事件流 / 多功能队列）。
- 只读数据层：直读文件、零 kdev_core 运行时依赖、全容错降级；CLI `python3 -m kdev_hud {statusline,render}`。
- FF-3：gate 按 PASS/FAIL 渲染（无 score，未来加字段前向兼容）。
- 边界：绝不写 `features/`；render 仅写 `.kdev/hud.html`；坏数据降级不崩用户视图。
