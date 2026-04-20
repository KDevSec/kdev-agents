# kdev-commit

AI commit + push 一体化插件：skill 引导 AI 按正确身份 commit、hook 硬校验身份覆盖、push 前弹权限框让用户确认。

## 解决什么问题

智能体（Claude Code / Copilot CLI / Codex / 自建 Agent 等）默认用仓库的 git 身份 commit 和 push，带来两个痛点：

1. **作者混淆**：人工 commit 和 AI 代写 commit 的作者信息一模一样，`git log` / `git blame` / code review 都分不清
2. **推送失控**：AI 可能在用户没明确同意的情况下把代码推到远端

## 核心机制（v0.2.0）

### 1. skill：`kdev-commit`

用户说"帮我提交 / commit 一下 / 提交本次代码 / ship 一下"时触发，引导 AI 按固定流程走：
读 `git config user.name` + `user.email` → 派生 AI 身份 → 带 `-c` 覆盖参数 commit → 询问用户是否 push → push。

### 2. hook：commit 身份硬校验

`PreToolUse/Bash` 拦截 AI 会话里的 `git commit` 调用。要求命令里同时含：
- `-c user.name=<git-user.name>-AI`
- `-c user.email=<git-user.email>`

两者缺一 → `deny` 并把正确命令写进 reason，AI 看到后自动重试。用户自己在终端敲的 commit 不受影响（hook 只在 agent 会话里 fire）。

### 3. hook：push 前用户确认

`PreToolUse/Bash` 拦截 AI 会话里的 `git push` 调用，返回 `permissionDecision: "ask"` → Claude Code 弹出 IDE 权限对话框，用户一键 allow / deny。`--force`（非 `--force-with-lease`）会在弹窗 reason 里高亮警告。

### 4. 运行时动态派生 AI 身份

hook 不硬编码任何值。每次触发时读当前仓库的 `git config user.name` / `user.email`（遵守 local > global > system 优先级）。团队成员换名字 / 不同项目用不同身份都自动适配，无需重装。

### 零外部依赖

两个 hook 都是纯 Node 脚本（Claude Code 自带 Node 运行时），不需要 jq、python、bash 之外的任何工具。Windows / macOS / Linux 表现一致。

## 身份策略（v0.2.0 反转设计）

| 字段 | 值 | 说明 |
|---|---|---|
| AI commit 的 author.name | `<本地 user.name>-AI` | ASCII 规范化后加 `-AI` 后缀 |
| AI commit 的 author.email | `<本地 user.email>` 真实邮箱 | **不改邮箱**，GitHub 头像仍是本人 |

> **v0.1.0 → v0.2.0 的变化**：v0.1.0 用 `<name>-AI@noreply.local` 伪邮箱（GitHub 灰头像），v0.2.0 改用真实邮箱（GitHub 头像是本人）。靠作者名后缀 `-AI` 区分 AI 产出，不再靠头像。

**为什么反转**：灰头像方案让 AI commit 在 GitHub 贡献图 / PR 页面完全不计入本人贡献 —— 对部分用户来说这是缺点（AI 协助产出也是自己的工作成果）。v0.2.0 让贡献仍归属本人，但 `git log` 作者名清楚写着 `-AI`，review 时一眼可辨。

## 安装

```bash
# 第一次使用者：注册 marketplace
claude plugin marketplace add KDevSec/kdev-agents

# 安装插件 —— hook 和 skill 随插件自动注册
claude plugin install kdev-commit@kdev-agents
```

**前置条件**：本机需配好 git 身份：

```bash
git config --global user.name "你的名字"
git config --global user.email "you@example.com"
```

两者缺一，AI commit 会被 hook deny 并提示先配置。

## 典型交互

用户说：**"帮我提交本次代码并推到远端"**

AI 会（受 skill 引导）：

1. 跑 `git config user.name` / `user.email` 读身份（比如拿到 `ly` / `ly@example.com`）
2. 派生 AI_NAME = `ly-AI`
3. 跑 `git status` / `git diff --staged` 看改动
4. 生成 commit message
5. 跑：
   ```bash
   git -c user.name=ly-AI -c user.email=ly@example.com commit -m "<message>"
   ```
   hook 校验通过 → 放行
6. 问你："要 push 到远端吗？"
7. 你答"要" → AI 跑 `git push` → **Claude Code 弹出权限框**：
   ```
   AI 请求执行 push：
     git push
   是否确认？
   ```
   你点 allow → 推送成功

## 效果

```
$ git log --format='%an <%ae>' | head
ly-AI <ly@example.com>    ← AI commit，名字带 -AI，GitHub 头像仍是你
ly-AI <ly@example.com>
ly <ly@example.com>       ← 你本人 commit
ly-AI <ly@example.com>
```

按作者名过滤统计 AI 产出：

```bash
git log --author='-AI' --oneline   # 只看 AI commit
git log --author='^ly <' --oneline   # 只看你本人（正则排除 -AI）
```

## 设计边界

- **不决定** commit message 格式 / commit 粒度（那是项目约定，skill 只提醒 AI 跟项目既有风格走）
- **不做** 代码量仪表盘
- **不改** 任何 git config —— 仅读取，永不写入
- **不自动 push** —— push 必须经用户在 IDE 权限框里确认

## 从 v0.1.0 升级

- 旧的 `@noreply.local` commit 历史不动
- 升级后，新 AI commit 会用真实邮箱，`git log` 里会同时看到两种风格
- 如果坚持灰头像方案，锁在 v0.1.0：`claude plugin install kdev-commit@kdev-agents@0.1.0`

## 更新

```bash
claude plugin update kdev-commit@kdev-agents
```
