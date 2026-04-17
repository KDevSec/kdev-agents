---
name: kdev-commit
description: 安装 AI commit 身份强制隔离机制——让智能体 git commit 时自动走独立身份（如 ly-AI），用户手动 commit 保持本人身份。通过 Agent 运行时的 PreToolUse/Bash hook（或等价的工具调用拦截器）实现硬拦截，未覆盖 AI 身份直接 block，不依赖模型自觉。触发时机：用户说"装 AI 提交隔离 / kdev-commit / AI commit 身份 / 区分 AI 提交 / 分开统计人和 AI 代码"、团队新成员入职需要统一配置、用户抱怨"GitHub 分不清哪些 commit 是 AI 写的"、项目需要按邮箱分别统计人/AI 代码量；或用户已有配置想修改 AI 身份名称/邮箱。不管 commit message 格式、不管 commit 粒度（那是各项目约定的事）——只管"用什么身份 commit"这一件事。
---

# kdev-commit：AI 提交身份隔离

## 这个 skill 解决的问题

智能体（Claude Code / Copilot CLI / Codex / 自建 Agent 等）默认用仓库的 git 身份 commit，导致 git log 上"人工 commit"和"AI 代写 commit"混在一起：

- **GitHub 页面分不清**：两种 commit 都显示同一个头像和用户名
- **code review 难定责**：不知道哪段代码是人写的、哪段是 AI 写的
- **贡献统计失真**：团队管理层看不出 AI 的实际产能占比

这个 skill 通过**一个 PreToolUse Bash Hook** 解决——智能体每次跑 `git commit` 时，hook 检查命令里是否带 `-c user.email=<AI_EMAIL>`，没带就直接 block 并在 deny 消息里告诉 Claude 正确的 `-c` 参数，Claude 立刻重试即可。

不写任何项目文档规则——hook 的 deny 消息本身就是**运行时自文档**，首次被拦截时 Claude 就学到了怎么干，无需提前在 CLAUDE.md 里塞一份静态说明（还会随 hook 派生规则变化而过期）。

**关键设计决策**：
- Hook 只在智能体执行工具调用时 fire（Claude Code、Copilot CLI 等都支持 PreToolUse/Bash 或等价机制），用户自己在终端敲 `git commit` 不受影响——人工/AI 自然分流
- AI 身份用**不关联任何 GitHub 账号**的邮箱（如 `ly-AI@noreply.local`），GitHub 页面会显示灰色默认头像 + AI 名字，视觉一眼可区分
- AI 邮箱不是 `<id>+ly-AI@users.noreply.github.com` 格式——那个会被 GitHub 归进你账号导致头像相同

## 触发本 skill 要做的事

按下面顺序执行，每步做完 TodoWrite 打勾：

### Step 1：检查 git 身份前置条件

**不要问用户自己填 AI 身份**——hook 会在 commit 发生时**动态**从 `git config user.name` 派生，这样能天然尊重 git 的配置优先级（仓库级 > 全局级），一个人在不同项目用不同身份的情况也能正确区分。

**执行检查**（仅全局级，作为兜底）：

```bash
git config --global user.name
git config --global user.email
```

两个都非空 → 前置条件满足，进入 Step 2。

**如果任一为空**：

说明用户还没配过 git 身份。中断 skill 流程，明确提醒：

> 检测到你没配 git 全局身份。这是让 AI commit 隔离生效的前提——hook 需要读 `user.name` 来派生 AI 名字。请先跑：
>
> ```
> git config --global user.name "<你的名字>"
> git config --global user.email "<你的邮箱>"
> ```
>
> 配完重跑本 skill。

**仓库级 config 的特殊说明**：如果用户当前在一个项目里，且 `git config user.name`（不带 `--global`）返回值与全局不同（仓库级覆盖），**不用管**——动态 hook 在那个项目里执行时会自动用仓库级的值。skill 层只需保证全局有兜底身份即可。

### Step 2：写 hook 脚本（运行时动态派生 AI_EMAIL）

路径：`~/.claude/hooks/block-unattributed-commit.sh`

**关键设计**：hook 不硬编码 AI_EMAIL，每次 commit 触发时现场跑 `git config user.name` 派生。好处：
- 团队成员换 git 名字无需重装 skill
- 在不同项目（仓库级 user.name 不同）自动适配
- 安装脚本零配置参数

**幂等原则**：
- 如果文件已存在且内容与下面模板一致 → 跳过，不动文件
- 如果不存在 → 按模板创建
- 如果存在但脚本逻辑不同（比如旧版硬编码了 AI_EMAIL）→ **先读出来告诉用户"检测到旧版 hook，是否升级为动态派生版本？"**，用户确认后覆盖

模板：

```bash
#!/usr/bin/env bash
# Block git commit from any AI agent when AI identity override is missing.
# Fires as a PreToolUse/Bash hook (or the agent runtime's equivalent tool
# invocation interceptor). Reads hook JSON on stdin, inspects tool_input.command.
# Human terminal commits are unaffected (hook only runs inside agent sessions).
#
# AI_EMAIL 运行时从 git config user.name 动态派生——
# 尊重 git 的 local>global>system 优先级，
# 团队成员换名字 / 不同项目用不同身份都能自动适配。
set -euo pipefail

cmd=$(jq -r '.tool_input.command // ""')

# Not a git commit invocation → allow silently
if ! printf '%s' "$cmd" | grep -qE '(^|[;&|[:space:]])git([[:space:]]+-c[[:space:]]+[^[:space:]]+)*[[:space:]]+commit([[:space:]]|$)'; then
  exit 0
fi

# 派生 AI 身份：取当前 git user.name（遵守 local > global 优先级），加 -AI 后缀
USER_NAME=$(git config user.name 2>/dev/null || true)

# 无 git 身份 → 让用户先配置，不阻 commit（commit 自己会失败得更明显）
if [ -z "$USER_NAME" ]; then
  jq -n '{
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: "deny",
      permissionDecisionReason: "git user.name 未配置，无法派生 AI 身份。请先 git config --global user.name <name>"
    }
  }'
  exit 0
fi

# 规范化：空格 → 连字符；只保留 ASCII 字母数字/_/-。非 ASCII 直接报错
SAFE_NAME=$(printf '%s' "$USER_NAME" | tr ' ' '-' | tr -cd 'A-Za-z0-9_-')
if [ -z "$SAFE_NAME" ]; then
  jq -n --arg raw "$USER_NAME" '{
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: "deny",
      permissionDecisionReason: ("git user.name=\(.$raw) 无法派生 email-safe AI 名字（全部非 ASCII）。请给 git 配一个 ASCII 别名：git config --global user.name <ascii-name>")
    }
  }'
  exit 0
fi

AI_NAME="${SAFE_NAME}-AI"
AI_EMAIL="${AI_NAME}@noreply.local"

# Has required email override → allow
if printf '%s' "$cmd" | grep -qF "user.email=$AI_EMAIL"; then
  exit 0
fi

jq -n --arg name "$AI_NAME" --arg email "$AI_EMAIL" '{
  hookSpecificOutput: {
    hookEventName: "PreToolUse",
    permissionDecision: "deny",
    permissionDecisionReason: ("AI commit 必须覆盖身份。请用：git -c user.name=" + $name + " -c user.email=" + $email + " commit ...（AI 身份按 git user.name + -AI 派生，见项目 CLAUDE.md）")
  }
}'
```

写完 `chmod +x` 加执行权限。

**无需在 skill 里做模板替换**——动态派生让 hook 脚本对所有团队成员都是同一份内容，团队分发就是一个静态文件。

### Step 3：注册到 `~/.claude/settings.json`

读现有 settings.json（可能不存在，按空对象处理）。找或建 `hooks.PreToolUse` 数组。要加的条目：

```json
{
  "matcher": "Bash",
  "hooks": [
    {
      "type": "command",
      "command": "bash ~/.claude/hooks/block-unattributed-commit.sh"
    }
  ]
}
```

**关键**：如果数组里已经有指向 `block-unattributed-commit.sh` 的条目，不要重复加——清掉旧的（可能指向错误路径）再加新的，保持幂等。

写回 settings.json 前用 `jq` 格式化（2 空格缩进），保留现有的其他 hooks 和 top-level 配置不动。

### Step 4：端到端验证

先读一次当前项目的 `git config user.name`，算出本机/本项目应有的 `AI_EMAIL`（记为 `$EXPECTED`）。然后跑 3 个场景验证 hook 逻辑：

```bash
# 先算出当前上下文应有的 AI_EMAIL（跟 hook 派生逻辑保持一致）
EXPECTED_NAME=$(git config user.name | tr ' ' '-' | tr -cd 'A-Za-z0-9_-')
EXPECTED="${EXPECTED_NAME}-AI@noreply.local"

# T1：带正确 AI 覆盖 → 应该 exit 0 无输出
echo "{\"tool_input\":{\"command\":\"git -c user.email=$EXPECTED commit -m test\"}}" \
  | bash ~/.claude/hooks/block-unattributed-commit.sh
echo "T1 exit=$?"

# T2：没覆盖 → 应该输出 deny JSON（带具体期望邮箱），exit 0
echo '{"tool_input":{"command":"git commit -m test"}}' \
  | bash ~/.claude/hooks/block-unattributed-commit.sh
echo "T2 exit=$?"

# T3：非 commit 命令（例如 git push）→ 应该 exit 0 无输出
echo '{"tool_input":{"command":"git push origin master"}}' \
  | bash ~/.claude/hooks/block-unattributed-commit.sh
echo "T3 exit=$?"
```

T1/T3 输出为空，T2 输出包含 `"permissionDecision": "deny"` 且提示邮箱等于 `$EXPECTED`——全对算通过。

### Step 5：收尾汇报

告诉用户：
- Hook 路径 `~/.claude/hooks/block-unattributed-commit.sh`，已注册到 PreToolUse/Bash
- AI 身份是**运行时动态派生**的，规则：取 `git config user.name`（仓库级优先），加 `-AI` 后缀和 `@noreply.local` 域名
- 当前全局派生值是什么（基于 `git config --global user.name`），本项目派生值是什么（基于当前 repo 的 `user.name`）
- 用户自己在终端敲 commit 不受影响
- 以后换 git 身份 / 仓库级 config 变化自动生效，**不用重跑 skill**
- 想换规则（比如想用 `-copilot` 后缀而不是 `-AI`），直接改 hook 脚本里的 `AI_NAME="${SAFE_NAME}-AI"` 那行

## 常见误用和坑

**坑 1：用 GitHub noreply 邮箱**

有人会想：`<id>+ly-AI@users.noreply.github.com` 可以让 AI commit 的贡献图还计入本人——听起来很美，但 **GitHub 按数字 ID 匹配账号，后缀 `+ly-AI` 被忽略**，最终 commit 显示本人头像，和目标"视觉区分"南辕北辙。如果团队成员坚持要走 noreply 方向，告诉他们：API 按邮箱过滤依然能分开统计，但**页面上看不出区别**。视觉区分必须用非 GitHub 邮箱。

**坑 2：仓库级 git config 改 user.email**

这也分不清——仓库默认身份影响的是所有在这个 repo 下跑 commit 的人，包括用户本人手动 commit。硬拦截的价值就是"只管 Claude 的 commit，不动用户的"。本 skill 绝对不改仓库级 `user.email`。

**坑 3：用 `git config --global` 配 hook**

Git 自身的 pre-commit hook 对所有 commit 生效（不区分 AI/人），而且每个 repo 要单独装。Agent 运行时的 PreToolUse hook 只在智能体会话里 fire，正是我们要的精确边界。不要用 git-level hook 替代。

**坑 4：忘了 `chmod +x`**

hook 脚本没执行权限的话，Agent 运行时触发时会静默失败（不 block 也不报错），commit 会漏网。Step 2 务必补 `chmod +x`。

## 设计边界

- 本 skill 不决定 commit message 格式、commit 粒度——那是项目 CLAUDE.md 或 conventions 的事
- 本 skill 不做代码量统计仪表盘——配好 hook 后，用户自己跑 `git shortlog -sn --author=-AI@noreply.local` 或 GitHub API 按邮箱过滤即可
- 本 skill 不管签名、GPG——如果项目要求 signed commit，`-c` 身份覆盖和 `-S` 签名可以叠加使用，不冲突
- 本 skill 不改任何 git config（全局或仓库级）——仅读取，决不写入
