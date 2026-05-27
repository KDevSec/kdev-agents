---
name: kdev-hud
description: KDev 多智能体集群 HUD（实时状态面板）。读 .kdev/state.md + events.log 输出 3 种模式：markdown（默认，对话流）/ box（CLI ASCII）/ watch（提示用户起 `watch -n 1 kdev-statusline.sh`）。Use when 用户问"进度怎么样？/ hud / 看下状态 / 现在跑到哪了"，主控员在阶段完成时也应主动调本 skill 渲染 markdown。
---

# kdev-hud

实时状态面板。

## 输入参数

`$ARGUMENTS` 形如 `[markdown|box|watch]`。默认 `markdown`。

## 工作流

### 模式 1：markdown（默认 / VSCode 主推）

按 `references/hud-markdown.md` 的模板填充：
- Read `.kdev/state.md`（用 `lib/state_md.py::StateMd.read`）
- Read `.kdev/events.log` tail 5
- Read 4 个 `.kdev/handoffs/<g>/COMPLETE.md`（如存在）
- 把所有数据拼成 markdown 表格 + 最近事件 + 阶段产物链接，**直接输出到对话流**。

### 模式 2：box（CLI ASCII）

按 `references/hud-box.md` 模板。等宽字符画 + emoji 状态图标。

### 模式 3：watch

输出一段说明给用户：
```
请在 CLI 终端跑 `watch -n 1 plugins/kdev-cluster-x3/skills/kdev-statusline/kdev-statusline.sh .kdev/state.md` 看 1s 刷新版（VSCode 用户改用 markdown preview 看 .kdev/state.md）。
```

## 设计意图（不直接渲染给用户）

- markdown 是 VSCode 用户主推。VSCode 扩展不渲染 statusLine（v0.1 §6.3 实测）。
- box 仅 CLI 用户。
- watch 不在 skill 内部实现 — Claude 不应自己起 polling 循环。
