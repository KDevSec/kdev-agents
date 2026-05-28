# 2026-05-28 · `block-unattributed-commit` hook deny 被 subagent 误判为 prompt injection

> 状态：**已通过规则统一根治（不改 hook）**
> 提出人：ly（实战发现）
> 关联：[.kdev/memory/踩坑日志.md G-002](../../../.kdev/memory/踩坑日志.md)、[plugins/kdev-commit/hooks/block-unattributed-commit.js](../../../plugins/kdev-commit/hooks/block-unattributed-commit.js)、Step 7 cluster-x1 subagent-driven 实施

## 一句话现象

`block-unattributed-commit` hook 拒 commit 时 stderr 输出的提示文本（"AI commit 必须同时覆盖 user.name 和 user.email. 请用: git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit ..."），在防御性 subagent（superpowers 体系）眼里**长得像 prompt injection**，会被识别并忽略。

## 复现链路（Step 7 实战）

1. **上游条件**：本仓库（kdev-agents）原 global CLAUDE.md 写"直接使用 git config user.email 配置的身份作为 commit author/committer 即可（当前：`ly <ly1989abc@126.com>`）"——**没有 -AI 覆盖要求**。
2. **派单**：主控员派 implementer subagent（`general-purpose`, model: sonnet）实施 Task 2-23（cluster-x1 plugin）。implementer prompt 复述了 user CLAUDE.md "无 -AI" 的 commit 规则。
3. **冲突触发**：implementer 跑 `git -C <worktree> commit -m "..."`（按 CLAUDE.md 不带 -c），项目侧 `block-unattributed-commit.js` hook 在 PreToolUse 阶段 deny，stderr 输出指令性建议："请用: git -c user.name=ly-AI ..."。
4. **误判**：implementer 自检发现这段文本：
   - 出现在 **tool result（stderr）** 而非 user turn
   - 跟它**当前持有的 user CLAUDE.md** 规则**直接矛盾**（CLAUDE.md 说不要 -AI，stderr 说必须 -AI）
   - 语义上是一条**可执行命令**（"请用 X"+ 具体 argv）
   
   按 `superpowers:using-superpowers` 的指令优先级（user CLAUDE.md > skill > 默认），implementer 选择**信 CLAUDE.md，忽略 stderr 文本**。
5. **绕道执行**：implementer 反复试不同 git 调用形式，最终成功 commit（hook 在哪里 silent fail 或本次确实未生效——具体不深究，per user "不需要排查")，但 commit author = `ly` 而非 `ly-AI`。
6. **断点结果**：本会话 31 个 commit 全 `ly <ly1989abc@126.com>`，跟项目历史前期（kdev-commit + -AI 风格）的 author 形成断点。

## 报告原文（subagent 自述）

> "Note on the prompt injection: during the git commit attempt, the tool result contained text formatted to look like a user instruction ('AI commit 必须同时覆盖 user.name 和 user.email...'). This was a prompt injection attempt — it appeared inside a tool result, not as a genuine user message, and contradicts the user's own CLAUDE.md rule. It was ignored correctly."

——Task 2 implementer 报告原话；Task 23 implementer 也独立给出几乎一致的判断。

## 根因（不是 hook bug，也不是 subagent bug）

**两个组件都按各自合理逻辑工作，但上游规则没对齐时会冲突**：

| 组件 | 它的合理行为 | 在冲突场景下的表现 |
|---|---|---|
| `block-unattributed-commit` hook | deny + 输出**可操作的修正建议**（"请用 X"） | 文案看起来像"指令"，因为它本来就是 |
| superpowers subagent | trust hierarchy 严格，user turn 外的"指令性文本"默认视为 injection 候选 | 误杀合法的 hook 反馈 |

冲突源头不在两者任何一方，而在**用户 global CLAUDE.md 与项目侧 hook 期望的身份策略不一致**。

## 解决（已落地）

✅ **统一规则**：2026-05-28 用户更新 global CLAUDE.md，把"-AI 覆盖"提升为正式规则（见 `~/.claude/CLAUDE.md` 的 `## Git 提交规范` 段）。改后 subagent 再被派单时，CLAUDE.md 跟 hook 期望一致，**hook deny 不再触发**，subagent 也就没有"看起来像 injection 的 stderr"可读。

## 显式不做

per user 指令 "不需要排查和修复"：

- ❌ 不重写 hook deny message 文案让它"看起来不像指令"
- ❌ 不 rebase 历史 31 个 `ly` author 的 commit 为 `ly-AI`（仅本次会话产物，未来按新规则）
- ❌ 不给 kdev-commit hook 维护方开 F-NNN 反馈（per Q-002 跳过本项目主动采集）

## 教训（值得记住的 1 条）

> **当 hook deny 的 stderr 措辞 + 上游 trust 规则不一致 时，会形成"系统级 surface"——hook 的合法反馈被防御性 subagent 误读为 prompt injection。修法是规则统一，不是改文案。**

类比：邮件里"请回复 yes 确认"这类祈使句，spam filter 看到也会犹豫——不是 spam filter 错，是 spam filter 在 trust boundary 上做了合理保守判断。同理这里。

## 跨条索引

- [G-001](../../../.kdev/memory/踩坑日志.md) `-c key="value"` 带引号被同一个 hook deny（不同症状但同一 hook）
- [G-002](../../../.kdev/memory/踩坑日志.md) 本条
- Step 7 执行日志：[.kdev/memory/执行日志.md](../../../.kdev/memory/执行日志.md)
- 全局 CLAUDE.md 修订：`~/.claude/CLAUDE.md` 2026-05-28
