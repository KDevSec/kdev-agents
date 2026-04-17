# kdev-commit

AI commit 身份强制隔离插件 —— 让智能体的 commit 和用户本人的 commit 在 git log 和 GitHub 页面天然分开。

## 解决什么问题

智能体（Claude Code / Copilot CLI / Codex / 自建 Agent 等）默认用仓库的 git 身份 commit，导致：

- GitHub 页面上"人工 commit"和"AI 代写 commit"头像/用户名相同，肉眼分不清
- `git log` / `git blame` 里作者列一模一样，code review 难定责
- 贡献统计失真，团队看不出 AI 的实际产能占比

## 核心机制

安装时跑一次 skill，完成两件事：

1. **PreToolUse Bash Hook**：智能体每次跑 `git commit` 时，hook 检查命令里是否带 `-c user.email=<AI_EMAIL>` 覆盖。没带就直接 block 并返回具体指令，Claude 立即重试。用户自己在终端敲的 commit 不受影响——hook 只在智能体会话里 fire。
2. **运行时动态派生 AI 身份**：hook 不硬编码邮箱，每次触发时读 `git config user.name`（仓库级 > 全局级）加 `-AI` 后缀派生。团队成员换名字 / 不同项目用不同身份都自动适配。

AI 邮箱固定用 `<name>-AI@noreply.local` 格式——不关联任何 GitHub 账号，页面显示灰色默认头像 + AI 名字，和本人头像**视觉一眼可区分**。

## 安装

```bash
# 第一次使用者：注册 marketplace
claude plugin marketplace add KDevSec/kdev-agents

# 安装插件
claude plugin install kdev-commit@kdev-agents
```

装完在任意项目里说一句"帮我装 AI 提交隔离"即可，skill 会：
- 检查 `git config --global user.name/user.email` 是否已配（没配提醒你先配）
- 写 hook 到 `~/.claude/hooks/block-unattributed-commit.sh`
- 注册到 `~/.claude/settings.json` 的 PreToolUse
- 跑 3 个 hook 场景验证通过

## 效果

安装后：

```
$ git log --format='%an <%ae>' | head
ly-AI <ly-AI@noreply.local>       ← 智能体 commit，灰头像
ly-AI <ly-AI@noreply.local>       ← 智能体 commit
ly <ly1989abc@126.com>            ← 你本人 commit，正常头像
ly-AI <ly-AI@noreply.local>
```

GitHub API 按邮箱过滤，人/AI 代码量分别统计轻松搞定：

```bash
# 只看 AI 产能
gh api "repos/OWNER/REPO/commits?author=ly-AI@noreply.local&per_page=100"
# 只看你本人
gh api "repos/OWNER/REPO/commits?author=你的邮箱&per_page=100"
```

## 设计边界

- **不决定** commit message 格式 / commit 粒度（那是项目约定）
- **不做** 代码量仪表盘（只提供可分别统计的 attribution 基础）
- **不改** 任何 git config —— 仅读 `user.name` 派生，永不写入

## 更新

```bash
claude plugin update kdev-commit@kdev-agents
```
