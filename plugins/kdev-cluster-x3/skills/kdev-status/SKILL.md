---
name: kdev-status
description: KDev 多智能体集群状态快照（与 CLI statusLine 等效，单行）。Use when 用户问"一句话告诉我现在到哪了 / 简短进度 / status"。输出格式：`KDev | reqs:icon dev:icon test:icon review:icon | <slug>`。
---

# kdev-status

## 工作流

跑 `plugins/kdev-cluster-x3/skills/kdev-statusline/kdev-statusline.sh .kdev/state.md` 并把输出原样放到对话流。

```bash
bash plugins/kdev-cluster-x3/skills/kdev-statusline/kdev-statusline.sh .kdev/state.md
```

如果 `.kdev/state.md` 不存在 → 直接输出 `KDev | 还没启动任何 feature。用 /kdev:start-feature <需求> 开始。`
