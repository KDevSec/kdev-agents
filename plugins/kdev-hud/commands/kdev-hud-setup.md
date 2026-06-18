---
description: 把 kdev-hud statusLine 幂等接入 Claude Code settings.json（只动 statusLine 一键、不 clobber 其他键；检测所有权——已有本插件条目就原位刷新；他者 statusLine 默认跳过，--force 覆盖前自动备份 settings.json.bak）。完成后提示用户重载/重启 session 才生效。
---

# /kdev-hud-setup

把 kdev-hud 状态栏接入当前项目的 `settings.json`（幂等、安全、不动其他键）。

## 你的任务

在**主会话**中执行以下命令（项目级，默认）：

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/kdev_hud/__main__.py" setup --project
```

命令执行后：
1. 查看输出（`✅ 已写入` / `✅ 已更新` / `未改动：已有他者 statusLine`）。
2. 把结果告知用户，并提示：**需要刷新 marketplace（重装/更新插件）并重启 Claude Code session，新 statusLine 命令才会生效（G-004）。**

## 选项说明

| 选项 | 含义 |
|------|------|
| `--project`（默认） | 写入 `<workspace>/.claude/settings.json` |
| `--user` | 写入 `~/.claude/settings.json`（用户级，全局生效） |
| `--force` | 覆盖已有的他者 statusLine（执行前自动备份原文件至同目录 `settings.json.bak`） |

## 行为细节

- **只动 `statusLine` 一个键**：settings.json 中的其余所有键（permissions、hooks 等）原样保留。
- **幂等**：重复运行不会产生副作用——本插件写入的 statusLine 条目会原位刷新到最新路径，不重复堆叠。
- **所有权检测**：command 字符串含 `kdev_hud` → 视为本插件所有，允许覆盖；否则视为他者。
- **他者保护（默认）**：检测到他者 statusLine 时**不改动**，提示用户加 `--force` 参数。
- **`--force` 备份**：强制覆盖前，原 `settings.json` 备份至同目录 `settings.json.bak`，可随时手动恢复。
- **文件不存在**：自动创建目录 + 新建 `settings.json`，只含 `{ "statusLine": {...} }`。
- **写入命令形式**：绝对路径（`python3 "/abs/.../kdev_hud/__main__.py" statusline --workspace ${workspaceFolder}`）；`__main__.py` 启动时自举父目录到 `sys.path`，无需配置 PYTHONPATH（FF-2 修复）。
