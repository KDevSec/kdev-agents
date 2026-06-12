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

## 接 Claude Code statusLine（settings.json）
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
