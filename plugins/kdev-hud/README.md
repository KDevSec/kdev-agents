# kdev-hud —— 数字员工观测层（第 4 plugin，纯只读）

把 kdev-core feature-first 账本（`.kdev/features/<slug>/` 的 `flow-state.json` + `events.jsonl`）渲染成两个通道。**纯只读**：不记账、不流转、不判断，**绝不写 `features/`**；底座可 headless 单装、无反向依赖。

## 三通道里 kdev-hud 只做 ①②
- **① 命令行状态栏**：单行速览（接 Claude Code statusLine）
- **② 网页实时仪表盘 `hud.html`**：一屏全景（自包含 HTML，热刷新）
- ③ CEO 对话播报 —— 归 kdev-team CEO，**不在本 plugin**

## 用法
```bash
# 通道①：单行状态栏（workspace 缺省取 stdin.cwd 或当前目录）
python3 -m kdev_hud statusline --workspace /path/to/project

# 通道②：生成 hud.html（写 <workspace>/.kdev/hud.html，不在 features/ 下）
python3 -m kdev_hud render --workspace /path/to/project
```

## 一键接入

**首选**：在 Claude Code 主会话中运行 `/kdev-hud-setup`，或直接执行：

```bash
# 项目级（默认，写 <workspace>/.claude/settings.json）
python3 -m kdev_hud setup --project

# 用户级（写 ~/.claude/settings.json，全局生效）
python3 -m kdev_hud setup --user

# 强制覆盖他者 statusLine（先备份 settings.json.bak）
python3 -m kdev_hud setup --project --force
```

命令幂等：重跑无副作用；只动 `statusLine` 一键；他者条目默认跳过（`--force` 覆盖并备份）。

写入的命令采用**绝对路径**形式（`__main__.py` 启动时自举父目录到 `sys.path`，绕开 PYTHONPATH / FF-2）：
```
python3 "/abs/.../kdev_hud/__main__.py" statusline --workspace ${workspaceFolder}
```

> **G-004**：改完 settings.json 后，需在 Claude Code 刷新 marketplace（重装/更新插件）并重启 session，新 statusLine 命令才会激活。

## 接 Claude Code statusLine（手动回退方式）
```json
{ "statusLine": { "type": "command",
  "command": "python3 -m kdev_hud statusline --workspace ${workspaceFolder}" } }
```
（或指向插件目录：`python3 <plugin>/kdev_hud/__main__.py statusline`。）

## 看仪表盘
`render` 写出 `.kdev/hud.html` 后，VSCode 用 **Live Preview / Simple Browser** 打开；
文件随 `render` 重生成、页面内嵌 2s auto-reload 自动刷新。可在底座事件后重跑 `render`。

## 数据契约（以 kdev-core 实现为准）
- 完成度 ← `stories[]` done/总
- 当前活动 ← `active{}` 单棒（flow·node·run·status）。**员工级派单/忙闲事件待 P-B handoff**，当前不渲染多员工忙闲网格。
- 评审流水 ← `events.jsonl` gate 行：**PASS/FAIL + iter + issues 数**（FF-3：暂无 `score`，未来加字段前向兼容）
- 告警 ← `active.status==blocked` + gate FAIL
- 多功能队列 ← 扫 `features/*/`

## 边界（铁律）
纯只读 · 派生非真相（崩了重读文件重建、坏数据降级不崩） · headless 友好（不装照跑） · 零第三方运行时依赖（纯 stdlib）。

## 测试
```bash
cd plugins/kdev-hud && python3 -m pytest tests/ -v
```
fixture 用 kdev_core 真实写 API 生成（防格式漂移，R-009）。

## WP-B（未实现）：statusLine 缓存包装 + 事件刷新

> TODO(WP-B) — 本次 defer，不实现。

**背景**：CC v2.1.x 不会持续重拉 `statusLine`——只有用户与状态栏面板交互时才触发一次轮询。因此当前实现每次都实时计算，但用户几乎看不到变化。

**未来方案**：
- `statusline` 命令改为**快读缓存**：读 `.kdev/hud/statusline.<session>.txt`，毫秒级返回，避免每次重算。
- HUD 计算（重开销）由 hook / 后台异步写缓存文件；可复用触发 `hud.html` 重生成的同一信号顺带写缓存。
- 新增 `--cached` 参数：强制读缓存（跳过实时计算），搭配 `--cached=false` 强制实时。
- 探索 `refreshInterval`（若 CC 未来支持）定期拉取，保持状态栏准实时。
