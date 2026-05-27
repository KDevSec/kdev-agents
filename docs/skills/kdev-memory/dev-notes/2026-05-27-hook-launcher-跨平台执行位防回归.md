# 2026-05-27 · hook launcher 跨平台执行位防回归

**触发事件**：v0.10.1 patch（commit f0fbcad + 562704f）修了 `hooks/run-python-hook.cmd` 缺 +x 位的 bug——Linux/macOS 上每个 hook 事件（SessionStart / UserPromptSubmit / Stop / PostToolUse / PreCompact / SessionEnd）都报 `/bin/sh: ... .cmd: Permission denied`（non-blocking 但日志噪声大）。

**根因结构**：这个 `.cmd` 文件是 polyglot 启动器，开头 `: << 'PYBLOCK'` 让 bash 把 Windows cmd 部分作为 here-doc 字符串吃掉，下面是 unix bash 代码。`hooks.json` 直接把它当可执行文件调用（`"${CLAUDE_PLUGIN_ROOT}/hooks/run-python-hook.cmd" xxx.py`）。在两个平台同时成立要满足两个独立条件：
1. 内容里的 polyglot 前缀（这条由文件内容保证）
2. git tree mode 100755（这条由文件权限保证）

两条之间没有任何机制互相约束——任何一次提交意外把 mode 改回 644（比如在 Windows 检出后再 add 之类），bug 立刻回归而且 review 时几乎看不出来。

## 改进点 #1（短期推荐）：CI 校验 launcher 文件必须 100755

最小成本防回归。在 GitHub Actions / pre-commit 加一条断言：

```bash
git ls-files -s 'plugins/*/hooks/*.cmd' 'plugins/*/hooks/*.sh' \
  | awk '$1!="100755"{print "missing +x:",$4; bad=1} END{exit bad}'
```

任何 hook launcher 文件（`.cmd` 或 `.sh`）只要 mode ≠ 100755 就让 CI 红。

**优点**：

- 一行就能落地，无外部依赖
- 跟现有发版流程零冲突
- 错误信息显式，PR 阶段就拦下

**缺点 / 边界**：

- 只防 launcher 这一类入口。`hooks.json` 里如果以后引入其它直 exec 的脚本（比如 .ps1 / 别的 .sh），要顺手把 glob 扩展进来。

**预期实施成本**：< 30 分钟。

## 改进点 #2（中长期）：launcher 按平台拆分

polyglot 启动器读起来 cute，但隐性约束多（内容前缀 + 权限位 + 两个平台都得验）。一个更直白的设计是按平台拆开：

```
hooks/
  run-python-hook.sh     # Linux/macOS，必须 +x（CI 强制）
  run-python-hook.cmd    # Windows，不依赖 +x
```

`hooks.json` 根据平台选其中一个：

```json
"command": "${CLAUDE_PLUGIN_ROOT}/hooks/run-python-hook.${EXT}"
```

或在 hooks 配置里写平台分支（取决于 Claude Code 的 hooks schema 支持度）。

**优点**：

- 每个文件单一职责，新手 review 时一眼能看懂
- 内容 diff 跟权限位的耦合解开，CI 校验也更精确
- polyglot 那套 here-doc 技巧不再需要维护

**缺点 / 阻塞点**：

- **依赖 Claude Code hooks schema 支持平台分支或环境变量替换**——目前 `hooks.json` 只有静态 `command` 字段，没有平台条件。要么等官方加，要么用 wrapper 脚本来选（但 wrapper 自己又落回平台分流问题）。
- 实施成本明显大于 #1，并且要双平台都测一遍

**预期实施成本**：1-2 天（含双平台回归测）。

## 落地建议

- **先做 #1**：低成本、高确定性、立刻锁住 v0.10.1 修复成果不被偶然回滚。
- **#2 留作 backlog**：要做的话排到下一个 minor（0.11.x）里和别的跨平台改进打包。当前 v0.10.x 不必动。

## 相关

- 修复 commit：`f0fbcad`（mode 100644 → 100755）
- 发版 commit：`562704f`（plugin.json 0.10.0 → 0.10.1 + CHANGELOG）
- 同类历史笔记：[2026-04-25-WINDOWS-COMPAT-REPORT.md](2026-04-25-WINDOWS-COMPAT-REPORT.md)、[2026-04-27-windows-python3-hook兼容性问题.md](2026-04-27-windows-python3-hook兼容性问题.md)
