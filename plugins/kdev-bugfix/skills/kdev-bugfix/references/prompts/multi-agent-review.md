# multi-agent-review prompt template

bugfix 步骤 6.2 `--review-mode=multi` 派 subagent 用的 prompt 模板。

## 用法

主 Claude 调 subagent 时，**Read 本文件**作为 prompt 主体，按下表替换占位符：

| 占位符 | 替换为 |
|--------|--------|
| `<BUG_ID>` | 实际 `<bug-id>`（如 `zentao-12345` 或 `login-button-error`）|
| `<BUG_SOURCE>` | `zentao #<id>` 或 `direct` |
| `<MODE>` | `OpenSpec` 或 `纯` |
| `<ARTIFACT_PATH>` | `openspec/changes/<bug-id>/` 或 `docs/bugfix/<bug-id>/` |
| `<SEVERITY>` | `P0` / `P1` / `P2` |
| `<UPGRADE_REASON>` | 如适用：`P0` / `鉴权` / `跨模块` / `数据迁移` / `文件数 > 3`；无升档写 `N/A` |

派单代码示例：

```python
prompt_template = Read("references/prompts/multi-agent-review.md")
# 主 Claude 做占位符替换后传给 Agent
prompt = (prompt_template
    .replace("<BUG_ID>", "zentao-12345")
    .replace("<BUG_SOURCE>", "zentao #12345")
    .replace("<MODE>", "OpenSpec")
    .replace("<ARTIFACT_PATH>", "openspec/changes/zentao-12345/")
    .replace("<SEVERITY>", "P1")
    .replace("<UPGRADE_REASON>", "鉴权"))

Agent({
  model: "opus",
  description: "Independent bugfix review",
  subagent_type: "general-purpose",
  prompt: prompt
})
```

## prompt 主体（subagent 收到的内容，从下方 `## 评审任务` 之后开始）

---

## 评审任务

独立评审本次 bugfix 修复。**不要假设主 Claude 的根因/方案是对的**——你的任务是当 second pair of eyes。

### 评审上下文

- bug-id: `<BUG_ID>`
- bug_source: `<BUG_SOURCE>`
- 模式：`<MODE>`
- 产物路径：`<ARTIFACT_PATH>`
- 严重度：`<SEVERITY>`
- 升档理由（如适用）：`<UPGRADE_REASON>`

### 你的任务

Read 以下产物：

- `<ARTIFACT_PATH>proposal.md`（OpenSpec 模式）或 `<ARTIFACT_PATH>bug-report.md`（纯模式）
- `<ARTIFACT_PATH>design.md`（OpenSpec 模式）或 `<ARTIFACT_PATH>fix.md`（纯模式）
- `<ARTIFACT_PATH>tasks.md`（OpenSpec 模式，纯模式跳过）
- 如有 `<ARTIFACT_PATH>specs/`（OpenSpec 模式 Spec_Impact 命中），也 Read

跑：

- `git diff <base>..HEAD`（或 `git diff --staged`，看具体状态）

### 评审维度（每项独立给 PASS / FAIL + 一句话理由）

1. **根因对准**：Root_Cause 与 diff 实际改动是否一致？是治本还是治标？是否落在 Symptom 的根源上？
2. **回归测试有效**：实际跑一遍 `git stash && pytest <regression-test> && git stash pop`（或对应栈命令），看回归测试是否在没 fix 时**真的失败**。如果一直 PASS → 测试有问题
3. **验证闸门充分**：tasks.md 的 T3-T9（type-check / lint / 既有测试 / 安全复核 / E2E）覆盖是否够。如缺关键档（如改了鉴权但没跑 kdev-secure-coding）→ FAIL
4. **新回归风险**：diff 是否引入新的回归点？具体指出哪行、为什么。Risks 段是否诚实地写了
5. **夹带改动**：是否有与 bug 无关的改动（顺手重构、改 lint warning、改命名）？diff 净度
6. **Spec_Impact 判定准确性**：如果 design.md 说 Spec_Impact = none，验证一下确实如此（不是漏判）

### 输出格式

```
## Multi-agent Review for <BUG_ID>

### 维度
1. 根因对准：PASS / FAIL — <理由>
2. 回归测试有效：PASS / FAIL — <理由>
3. 验证闸门充分：PASS / FAIL — <理由>
4. 新回归风险：PASS / FAIL — <理由>
5. 夹带改动：PASS / FAIL — <理由>
6. Spec_Impact 判定：PASS / FAIL — <理由>

### 终评
- 决定：APPROVE / REJECT
- 理由：<一句话>
- 建议修复方向（如 REJECT）：<具体建议>
- 跟进项（如 APPROVE 但有非阻塞改进点）：<bullet 列表>
```

### 重要约束

- **不要修改任何文件**。只读 + 评审
- **不要调禅道 API**（subagent 不持有 token，不需要也不应该）
- **不要看主 Claude 的对话历史**——保持独立判断（这是 multi-agent 评审的核心价值）
- 6 维度任一 FAIL → 终评 REJECT，**不投票多数决**
- 如发现严重问题（如测试根本不卡根因 / diff 含 secrets / 越权改了别的模块）→ 终评 REJECT 并显式标记 `⚠️ CRITICAL`
