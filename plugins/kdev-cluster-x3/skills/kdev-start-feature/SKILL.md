---
name: kdev-start-feature
description: KDev 多智能体集群 X3 矩阵式入口。Use when 用户说"用 KDev 跑一个新需求 / 启动新 feature / start-feature <需求>"。本 skill 仅做初始化 + 派出需求组工作 agent（**主控员 = 当前 session**，不另起 agent）；后续阶段聚合 / 慢路径 / 异常应急走 agents/ 下的 30 个 agent definition。
---

# kdev-start-feature

> 这是 KDev cluster-x3 的入口 skill。本 skill 完成后，**当前 session 就是主控员**——按 `agents/主控员.md` 的工作流继续编排。

## 输入

`$ARGUMENTS` = 用户提供的原始需求文本（中文/英文均可）。

## 工作流（init + 第一派单）

### 1. 解析需求 → slug

```bash
slug=$(python3 -c "from kdev_cluster_x3.lib.slug import slugify; print(slugify('$ARGUMENTS'))")
```

### 2. 初始化 .kdev/

```bash
mkdir -p .kdev/handoffs/{reqs,dev,test,review}
python3 -c "
from datetime import datetime, timezone
from pathlib import Path
from kdev_cluster_x3.lib.state_md import StateMd
StateMd.init(
    Path('.kdev/state.md'),
    feature='$ARGUMENTS',
    slug='$slug',
    started_at=datetime.now(timezone.utc),
)
"
touch .kdev/events.log
```

### 3. 通知用户

输出到对话流（≤200 字）：

```
✅ feature 已启动
- slug: <slug>
- 状态文件: .kdev/state.md
- 事件流: .kdev/events.log

我会按 X3 矩阵式编排：
1. 先派需求澄清师做 IR 澄清
2. 然后规格师 / 拆解师 / 原型 / 方案设计 — 每个阻断节点会同步派评审员
3. 全 reqs 完成后调需求组长做阶段聚合 → 你确认后进 dev
4. 你随时可以问 `/kdev:hud` 看进度，或打断我换方向

⏳ 现在派需求澄清师……
```

### 4. 第一派单：需求澄清师

```
Agent({
  subagent_type: "需求澄清师",
  prompt: "feature_slug=<slug>\n原始需求：<$ARGUMENTS>\n参考项目 CLAUDE.md。完成后写 .kdev/handoffs/reqs/ir.md。",
  run_in_background: true
})
```

### 5. 进入主控员主循环

读 `agents/主控员.md` 的「工作流」段，按状态机继续编排。

## 关键约束

- 本 skill 只跑一次（init 期间）。后续不要重复进入。
- 如已存在 `.kdev/state.md`（同 slug），询问用户是续跑还是覆盖（参考主控员的「跨 session 续航」段）。
