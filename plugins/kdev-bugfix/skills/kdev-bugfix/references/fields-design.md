# fields-design

OpenSpec 模式 — `openspec/changes/<bug-id>/design.md` 的 bugfix 字段补充。

upstream 默认 `design.md` 偏 feature 设计语义（架构图 / 数据流 / API 契约），bugfix 用以下字段**替代**整份内容。

**先跑 `openspec instructions design --change <bug-id>`** 拿 upstream prompt，再用本文模板覆盖。

## 完整模板

```markdown
## Root_Cause

<真正的根因。回答「为什么这段代码会产生 Symptom」。两到四句话，必须能让一年后的同事看完就懂>

**好例子**（精确到位）：
> 用户登录后，`/api/me` 请求依赖 cookie 里的 `session_id`，但 Express 4.18 默认 `cookie-parser` 中间件挂载在 `app.use(express.json())` 之后，导致 multipart 路由读不到 cookie。

**坏例子**（治标层 / 猜测）：
> 修复了 cookie 读不到的问题。
> 可能是 cookie-parser 顺序的问题，加了一下顺序就好了。

## Fix_Description

<这次具体要改什么，为什么这么改>

- **改动 1**：`<文件路径>` <如何改> ← <理由：为什么这么改而不是别的方式>
- **改动 2**：<同上>

## Alternatives_Considered（可选）

<考虑过的其他方案 + 否定理由>

- 方案 X：<描述>。否定：<理由，如「改动面太大」「破坏向后兼容」「治标不治本」>

## Spec_Impact

<判断 bug 是否暴露了 spec/PRD 错误>

- **Affected_Spec**：`<spec 文件路径>` 或 `None`
- **Change_Type**：`update` / `add` / `remove` / `none`
- **Description**：<spec 里哪一句话需要改成什么>
- **Justification**：<为什么 spec 需要改而不是只改代码>

⚠️ 如 Change_Type ≠ none，本次 PR **只**补救代码层 + 在 design.md 记录；真实 spec 文件修改另起 `kdev-change` 或 plan-eng-review，不要在 bugfix PR 里夹带。命中此条 → SKILL.md 步骤 4.2 引导走 [fields-specs.md](fields-specs.md)。

## Risks

<本次修复可能引入的回归 / 性能 / 兼容性风险。诚实写，不要"无"也不要"未知">

- <风险 1：可能影响 X，已 grep 确认无依赖；生产监控建议看 Y 24h>
- <风险 2：...>

## Follow_Up（可选）

<本次发现但不修的相关项。开 chore/refactor issue 跟踪>

- chore: <跟进项>
- refactor: <跟进项>
- docs: 追加规则到 `<repo>/docs/rules.md`：<规则一句话>

## Review_Decisions

<步骤 6 评审完成后追加。详细格式见 [review-modes.md §5](review-modes.md)>

### AI 自评（superpowers:code-reviewer）
- 决定：APPROVE / FAIL
- 关键点：<bullet 列表>
- 时间：<ISO timestamp>

### 多智能体评审（subagent opus）
- 决定：APPROVE / REJECT / N/A（如未走 multi）
- 关键点：<bullet 列表>
- 时间：<ISO timestamp>

### 人工评审（如适用）
- 评审人：<user>
- 决定：APPROVE / APPROVE WITH CHANGES / REJECT / N/A
- 评语：<原文>
- 时间：<ISO timestamp>
```
