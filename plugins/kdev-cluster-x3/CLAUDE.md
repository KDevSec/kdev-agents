# kdev-cluster-x3 插件使用指引

## 装上插件后，项目根 CLAUDE.md 应包含

> 本段是给"装上 kdev-cluster-x3 的下游项目"的 CLAUDE.md 模板。这是**协议**——主控员 + 30 agent 都会在 prompt 里强制 Read 项目根 CLAUDE.md。

### 1. 项目硬约束

把项目的不可妥协规则写到 CLAUDE.md（如 UED 6.0 / 12 大原则 / 触发路由表）。**插件不在自身写规则**——所有 agent 顶部强制读项目 CLAUDE.md，把项目当规则源。

### 2. 启动命令

```
/kdev:start-feature <需求描述>
```

主控员（= 当前 session）按 X3 矩阵式编排 reqs → dev → test → review。

### 3. 查看进度

```
/kdev:hud           # 完整 markdown 面板
/kdev:status        # 单行快照
```

CLI 用户可以加 statusLine：
```jsonc
// .claude/settings.json
{
  "statusLine": {
    "type": "command",
    "command": "bash ${HOME}/.claude/plugins/cache/kdev-cluster-x3/skills/kdev-statusline/kdev-statusline.sh"
  }
}
```

### 4. 跨 session 续航

新 session 启动时说"继续上次的工作 / resume"。主控员会读 `.kdev/state.md` 报告"上次到哪里"。

## 协议约束

🔴 **铁规 1**：主控员 / 30 agent 不直接对话用户。用户只跟当前 session 的主控员说话。
🔴 **铁规 2**：`.kdev/` 目录由插件管理（state.md / events.log / handoffs/）。不要手动改 — 改了会被下次 agent 派单覆盖。
🔴 **铁规 3**：评审循环 3 轮上限。第 4 轮自动 events.log `blocked` 触发组长介入（on-blocked hook）。
🔴 **铁规 4**：AR 编号格式 `AR-{DOMAIN}-{MAJOR:02d}.{MINOR:03d}.{PATCH:03d}`。需求拆解师产出 ar.csv 时强校验。

## 故障 / 应急

| 症状 | 排查 |
|---|---|
| events.log 写了 blocked 但组长没派 | 检查 hooks/on-blocked.py 是否可执行；检查 hooks.json 已被 Claude Code 加载 |
| state.md 损坏 | rm `.kdev/state.md`，新 session 用 `/kdev:start-feature` 重启（之前的 handoffs/ 保留可参考）|
| 评审员意见冲突 | 主控员调审查组长（慢路径）做仲裁，参考 standards/review/conflict-arbitration.md |
| 跨 session 续航失败 | 检查 .kdev/state.md 的 4 组 section 是否完整；若损坏，从最近 events.log step_complete 重建 |
