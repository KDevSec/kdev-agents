---
name: kdev-commit
description: 用 AI 身份（本地 git user.name + -AI 后缀，email 沿用本地真实邮箱）完成 commit，并在 push 前让用户确认的标准流程。触发时机：用户说"帮我提交 / commit 一下 / 提交本次代码 / 提交并推送 / 推到 GitHub / ship 一下 / 收工 / 提交吧"时；或完成一段代码改动后用户表达"落盘 / 归档 / 入库"意图时。核心约束：AI 必须用 `git -c user.name=<NAME>-AI -c user.email=<真实邮箱> commit ...` 覆盖身份（kdev-commit hook 会硬校验，漏任一项就 deny）；push 由 confirm-push hook 弹权限框让用户点确认。
---

# kdev-commit skill

## 这个 skill 负责什么

**一件事**：把"用户说帮我提交"翻译成正确的 `git` 命令序列——读身份 → 派生 AI 身份 → 带覆盖参数 commit → 询问并 push。

**这个 skill 不管**：
- commit message 的具体模板（跟项目 commit 历史风格走）
- commit 粒度（用户说怎么分就怎么分，不主动拆/合）
- push 的权限弹窗（confirm-push.js hook 处理）
- 身份校验失败的兜底（block-unattributed-commit.js hook 处理）

## 身份策略（v0.2.0）

- `AI_NAME = <git user.name>-AI`（ASCII 规范化：空格 → `-`，去掉非 ASCII 字符）
- `AI_EMAIL = <git user.email>` —— **真实邮箱直接用，不拼 `@noreply.local`**
- 效果：GitHub 头像仍是本人，但作者名后缀 `-AI` 清楚标记 AI 产出

## 标准流程（AI 执行步骤）

### 步骤 1：读本地 git 身份

```bash
git config user.name
git config user.email
```

两个都非空才能继续。任一为空 → 告诉用户先配置（例：`git config --global user.email you@example.com`），不要自作主张写入 config。

### 步骤 2：派生 AI_NAME

- 规范化：把空格替换为 `-`，只保留 ASCII 字母数字/`_`/`-`
- 加后缀：`AI_NAME = <safe_name>-AI`
- 纯非 ASCII（如中文名） → 告诉用户先给 git 配一个 ASCII 别名

### 步骤 3：看改动

```bash
git status
git diff --staged   # 已暂存的改动
git diff            # 未暂存（决定是否需要 git add）
git log --oneline -5   # 参考项目 commit 风格
```

### 步骤 4：准备 commit message

- 按项目最近几条 commit 的风格写（conventional commits / 自由式 / 带 scope / 中文 / 英文等，复制项目既有习惯）
- 焦点放在 **为什么**，不要罗列 **改了什么**（diff 里已经有）
- 单行标题 ≤ 72 字符

### 步骤 5：执行 commit（带身份覆盖）

```bash
git -c user.name="$AI_NAME" -c user.email="$USER_EMAIL" commit -m "<msg>"
```

**硬约束**：`user.name` 和 `user.email` **两个都必须**用 `-c` 覆盖。block-unattributed-commit.sh hook 会校验。

如果需要多行 message，用 HEREDOC 传：

```bash
git -c user.name="$AI_NAME" -c user.email="$USER_EMAIL" commit -m "$(cat <<'EOF'
<title>

<body>
EOF
)"
```

**注意**：不要带 `Co-Authored-By` 之类的 trailer ——作者名已经是 `-AI`，不需要再声明。

### 步骤 6：询问用户是否 push

commit 完成后，用自然语言问用户："要 push 到远端吗？"

- 用户答"要 / yes / 推 / 是 / OK / 推上去" → 继续步骤 7
- 用户答"不要 / 先别 / 等等" → 停，报告 commit hash 和未推送状态

**🔴 对话层硬规（v0.3.0 起 IDE 弹窗可配置，对话层 gate 永远在）**：

1. **AI 永不擅自 push**：用户未在**当前对话**里说出 push / 推 / 推送 / yes / 是 / OK / 推到 X / 推上去 等显式肯定信号前，绝对不执行 `git push`。`KDEV_COMMIT_PUSH_CONFIRM=off` 只关 IDE 那道，**这道永远不关**。
2. **"提交并推送" ≠ 永久授权**：即使用户原话含"提交并推送"，下一次提交（下一轮请求循环）仍要重新询问。
3. **commit ≠ push**：用户原话只说"提交 / commit"没说"推 / push"时，commit 后必须停下报告 hash + 未推状态，**不要默认连推**。
4. **例外——自主推进态（v0.4.0）**：用户**显式说出自主推进触发词**授予 standing 授权后，本态内可连续 push 不再每次问（详见下「自主推进模式」小节）。这是对第 1/2 条的**唯一例外**，且裸 `--force` **不在**例外内。

### 自主推进模式（v0.4.0）—— 对话授权后跳过 IDE 弹窗

用户**显式说出下列触发词之一**时，进入「自主推进」standing 态：

> **触发集**：自主推进 / 自动推进 / 自主执行 / 自动执行 / 无人值守 / 全自动 / 自动跑 / 自己跑完 / 一路到底 / 不用问我 / 不用每次确认（含"不用确认"）

进入态后：

1. **盖令牌**：给**每一条** `git push` 命令追加 ` # 自主推进` 注释——confirm-push hook 认这个令牌就跳过 IDE 弹窗。例：

   ```bash
   git push # 自主推进
   git push -u origin HEAD # 自主推进
   ```

2. **不再每次问**：自主推进态内不必每条 push 前都问"要 push 吗"——用户已给 standing 授权（步骤 6 硬规第 4 条的例外，仅本态成立）。
3. **撤销**：用户说 停 / 暂停 / 手动 / 我来确认 / 退出自主 / 接管 → **立刻退出**，恢复每次询问 + 不再盖令牌。
4. **`--force` 例外**：即便在自主推进态，强推仍需用户**另说"强推"**，且 IDE 弹窗仍会出现（令牌**永不**放行裸 `--force`，这是不可逆操作的最后一道关）。
5. **歧义即回落**：拿不准是否还在自主推进态（隔了很久 / 话题切换 / 不确定是否已撤销）→ **保守按"弹窗 + 问"处理**，不盖令牌。
6. **AI 不得自授**：自主推进态**只能由用户说触发词进入**，AI 绝不自行宣布进入或自己给自己授权。

**令牌只是把"你在对话里给的授权"机械地带到命令上**——替代不了授权本身。没有用户触发词，就不盖令牌。

### 步骤 7：执行 push

```bash
git push
```

如果报 `no upstream`，改用：

```bash
git push -u origin HEAD
```

**confirm-push hook 会弹 IDE 权限对话框**让用户再确认一次——用户点 allow 才真的推上去。这是第二道保险，正常现象，不要觉得是故障。

**自主推进态例外**：带 ` # 自主推进` 令牌的普通 push 会跳过这个弹窗（普通 push only；裸 `--force` 仍弹）。

**永远不要**：
- 用 `--force`（除非用户明确说"强推"，且优先建议 `--force-with-lease`）
- 在用户没说"push"的情况下擅自推
- **`--force` 在 `off` 配置下擅自推**：即使 hook 不弹框，AI 在对话里仍要单独提示一次"这是 `--force`，会覆盖远端历史"，等用户再确认一次才推

### 步骤 8：报告

- commit hash（`git log -1 --format=%H`）
- push 到的 remote/branch
- 如果还有未 push 的 commit，提醒用户

## 异常处理

- **commit hook deny**：按 deny reason 给的命令重试即可，不要改策略
- **push 被拒（auth）**：原样报错给用户，不重试、不绕开
- **push 被拒（non-fast-forward）**：提醒用户先 `git pull --rebase` 或手动决策，不要自己 rebase
- **无 remote**：只完成 commit，告诉用户"没有配置 remote，跳过 push"

## 不要做的事

- **不要改 `git config`**：只读不写，永远
- **不要用伪邮箱**：v0.1.0 用过 `@noreply.local`，v0.2.0 已废弃
- **不要绕 hook**：hook deny 一定有原因，按提示重试
- **不要主动 stage 所有文件**：用户让提交"这次改动"≠ `git add -A`。除非用户明确说"全部加进去"，否则只提交已暂存的改动；如果暂存区空而工作区有改动，问用户要不要 `git add` 哪些文件
