# Changelog

本插件遵循语义化版本。格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/)。

## [0.4.0] - 2026-06-20

### 新增
- **自主推进令牌**：用户在对话里授予「自主推进」后，AI 给每条 `git push` 盖 `# 自主推进` 注释令牌（正则 `/#\s*自主推进/`），`confirm-push.js` 认令牌即跳过 IDE 弹窗——把"对话点头 + IDE 点击"两道确认收成一道。
  - 触发集（SKILL.md 识别）：自主推进 / 自动推进 / 自主执行 / 自动执行 / 无人值守 / 全自动 / 自动跑 / 自己跑完 / 一路到底 / 不用问我 / 不用每次确认
  - 撤销集：停 / 暂停 / 手动 / 我来确认 / 退出自主 / 接管
  - 比 `off` 更安全：没盖令牌的 push（手动模式 / AI 漏问擅自推）仍弹窗兜底
  - 裸 `--force` 即便带令牌也**仍弹窗**（不可逆操作保留最后一道关）
  - 强制 `#` 注释前缀，防 branch 名 / commit message 里"自主推进"字样误触

### 不变（向后兼容）
- 默认无令牌行为与 v0.3.0 完全一致；`off` / `warn-force` 档行为零改动
- `block-unattributed-commit.js` 身份校验完全不变

### 测试
- `confirm-push.test.js` 续写 T10–T17（令牌放行 / `--force` 兜底 / 防误触 / `\s*` 容错），合计 24 条全绿

### 设计
- spec：`docs/superpowers/specs/2026-06-20-kdev-commit-自主推进令牌放行-design.md`
- 旧 spec `2026-05-18-push-confirm-config-design.md` 加 R-009 重定向锚（自主推进态对"每次重新问"开例外）

## [0.3.0]

### 新增
- 可配置 push 弹窗三档：`ask`（默认）/ `warn-force` / `off`，经 `KDEV_COMMIT_PUSH_CONFIRM` env 或 `~/.config/kdev-commit/config.json` 设置

## [0.2.0]

### 变更
- 身份策略反转：AI commit 用 `<本地 user.name>-AI` + **真实邮箱**（不再用 `@noreply.local` 伪邮箱），GitHub 头像仍归本人

## [0.1.0]

### 新增
- 首版：AI 身份 commit（`-AI` 后缀）+ commit 身份硬校验 hook + push 前确认 hook
