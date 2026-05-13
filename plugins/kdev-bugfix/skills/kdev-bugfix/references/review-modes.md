# review-modes

bugfix 步骤 6 评审闸门的 3 档模式详解。

## 模式总览

| 模式 | 触发 | 评审员 | 用时 | 适用 |
|------|------|--------|------|------|
| `ai`（默认） | `--review-mode=ai` 或不指定 | 主 Claude + superpowers:code-reviewer | ~30s | 日常 P2/P1 bug |
| `multi` | `--review-mode=multi` 或强制升级条件命中 | AI 自评 + 独立 subagent（opus）| ~2-3min | P0 / 跨模块 / 安全相关 |
| `human` | `--review-mode=human` | 主 Claude 输出摘要 → 暂停等用户 | 取决于用户 | 生产数据相关 / 合规要求 / 用户特别在意 |
| `both` | `--review-mode=both` | multi 完 → human 串行 | multi 时长 + 用户时长 | 极高风险（线上挂、数据迁移、鉴权重做）|

## 强制升级条件（自动从 ai 升到 multi）

即便用户传了 `--review-mode=ai`，**命中以下任一条**自动升档（向用户报告升档理由）：

1. **P0 严重度**（线上挂 / 数据损坏 / 安全漏洞 / 用户全量受影响）
2. **鉴权 / 权限 / 会话**相关代码改动
3. **跨模块状态协调**（动 ≥3 个核心实体的强引用 / 状态机 / 事务）
4. **数据迁移**（schema 变 / 索引调整 / 约束变更 / 批处理）
5. **修改文件数 > 3**（小修复一般 1-3 文件，超出说明面铺大了）

人工评审（human / both）是用户显式要求才走，**不**自动升级。

## §1 AI 自评

**调用方式**：主 Claude 委派 `Skill: superpowers:code-reviewer`。

**评审输入**：

```
评审对象：bugfix change <bug-id>
模式：OpenSpec / 纯
产物路径：openspec/changes/<bug-id>/ 或 docs/bugfix/<bug-id>/
diff：<git diff 全文>

关键产物：
- proposal.md / bug-report.md（Bug Context + Why + What Changes + Capabilities）
- design.md / fix.md（Root_Cause + Fix_Description + Risks + Spec_Impact）
- tasks.md（如有）
```

**评审维度**（superpowers:code-reviewer 自身已覆盖，本 skill 只追加 bugfix 特定关注点）：

1. 根因对准：Root_Cause 与 diff 是否一致；是治本还是治标
2. 测试有效性：回归测试是否真能 cover 同类问题（不只是卡住这一行）
3. 验证覆盖：type-check / lint / 安全 / E2E 是否充分
4. 夹带改动：是否有与本 bug 无关的修改混入
5. 风险声明：Risks 段是否诚实

**输出**：`PASS` 或 `FAIL <一句话理由>`。

## §2 多智能体评审（multi 模式）

派**独立 subagent** 走第二意见。重点是**不让 subagent 看主 Claude 的根因结论**——独立判断。

**派单流程**：

1. **Read** [prompts/multi-agent-review.md](prompts/multi-agent-review.md) 拿 prompt 模板
2. 按模板顶部"用法"段的占位符表替换 `<BUG_ID>` / `<BUG_SOURCE>` / `<MODE>` / `<ARTIFACT_PATH>` / `<SEVERITY>` / `<UPGRADE_REASON>`
3. 把替换后的 prompt 传给 `Agent({model: "opus", subagent_type: "general-purpose", prompt: ...})`

完整派单代码示例见 [prompts/multi-agent-review.md 用法段](prompts/multi-agent-review.md)。

**子文件抽取的理由**：

- prompt 模板**完整文本要原样传给 LLM**，专门成文件便于改动审计
- 占位符替换规则集中在一处定义，不在 review-modes.md / SKILL.md 各处散落
- 未来加 evals 时可对 prompt 模板单独做回归测试
- subagent 派单代码 + prompt 模板分离，调用方只关心占位符 → 输入

**评审结果处理**：

- subagent 返回 APPROVE → 推进步骤 7
- subagent 返回 REJECT → 落到 design.md `Review_Decisions` 段，回步骤 5.2（按 subagent 建议改）
- AI APPROVE 但 subagent REJECT → **以 subagent 为准**（保守路线）；不投票，不"少数服从多数"
- AI REJECT 但 subagent APPROVE → 主 Claude 应说明自己的 FAIL 是误判（少见情况）；保守仍按 FAIL 处理

## §3 人工评审（human 模式）

主 Claude 输出评审请求摘要，**暂停**等用户回复。

**摘要格式**：

```markdown
## 🔍 人工评审请求：<bug-id>

请评审本次 bugfix。需要的信息已整理如下，详细产物在 `<openspec/changes/<bug-id>/ 或 docs/bugfix/<bug-id>/>`。

### Bug 一句话
<Symptom>

### 根因（一句话）
<Root_Cause 压缩>

### 修复方案
- <Fix_Description bullet 1>
- <Fix_Description bullet 2>

### 修改文件
- `<file1>` 第 N 行：<改动一句话>
- `<file2>` 第 M 行：<改动一句话>
- `<regression-test>`：新增

### 风险（自述）
<Risks 段；如为空写"自述无风险">

### 已跑闸门
- 回归测试：✅ PASS（test 文件路径）
- 既有单元/集成：✅ PASS
- type-check：✅
- lint：✅
- 安全复核：✅ / N/A
- E2E：✅ / N/A
- AI 自评：APPROVE / REJECT 
- 多智能体评审：APPROVE / REJECT / N/A

### 我需要你的决定

请回复以下任一：
- `APPROVE` — 通过，进 commit
- `APPROVE WITH CHANGES: <你的修改要求>` — 通过但要先调整 X
- `REJECT: <理由>` — 不通过，描述问题

### diff 摘要

```diff
<git diff --stat 或精简 diff>
```

如需完整 diff，跑：`git diff <base>..HEAD`
```

**用户回复处理**：

- `APPROVE` → 推进步骤 7
- `APPROVE WITH CHANGES: <要求>` → 主 Claude 按要求改 → 回步骤 6.1 AI 自评（不要直接进 7，需重审）
- `REJECT: <理由>` → 落到 Review_Decisions 段，回步骤 5.2 或 4.1（依 reject 理由的层次）

**超时处理**：如果用户长时间无回复，**不**自动 APPROVE。挂起，下次会话恢复时仍在评审段。

## §4 both 模式

`--review-mode=both` = multi → human 串行：

```
6.1 AI 自评（必跑）
   ↓ PASS
6.2 多智能体评审（subagent）
   ↓ APPROVE
6.3 人工评审（用户）
   ↓ APPROVE
推进步骤 7
```

任一档 FAIL/REJECT 都回流，**不**跳级。

适合：上线鉴权变更、生产数据迁移、合规要求强制双签场景。

## §5 Review_Decisions 落档

无论走哪个模式，**评审结论必须落到产物**（不止口头报告）：

- OpenSpec 模式：写到 `openspec/changes/<bug-id>/design.md` 末尾 `## Review_Decisions` 段
- 纯模式：写到 `docs/bugfix/<bug-id>/fix.md` 末尾 `## Review_Decisions` 段

格式：

```markdown
## Review_Decisions

### AI 自评（superpowers:code-reviewer）
- 决定：APPROVE
- 关键点：
  - 根因对准 ✓
  - 回归测试覆盖等价类 ✓
  - 无夹带改动 ✓
- 时间：2026-05-13T14:32:11Z

### 多智能体评审（subagent opus）
- 决定：APPROVE
- 关键点：
  - 维度 1-6 全 PASS
  - 提示：建议跟进 X（已记入 Follow_Up）
- 时间：2026-05-13T14:34:55Z

### 人工评审（如适用）
- 评审人：<user email or name>
- 决定：APPROVE / APPROVE WITH CHANGES / REJECT
- 评语：<用户原文>
- 时间：2026-05-13T14:40:00Z
```

落档目的：commit message 的 `Reviewers:` 行有据可查 + 未来 audit 能 grep 到。

## §6 评审 commit message 集成

`kdev-commit` 步骤 7.2 的 commit message 模板含 `Reviewers:` 行，**按实际走的档自动填**：

```
Reviewers: AI (PASS), multi-agent (PASS), human (N/A)
Reviewers: AI (PASS), multi-agent (PASS), human (APPROVE WITH CHANGES applied)
Reviewers: AI (FAIL→fixed→PASS), multi-agent (PASS)
```

- 括号内：每个 reviewer 的最终决定
- 多次反复（FAIL → fix → re-review）只记最终决定，不堆历史

## §7 评审模式选择速查

```
P0 / 鉴权 / 跨模块 / 数据迁移？ → 至少 multi
  └ 生产数据 / 合规要求 / 用户特别在意？ → both 或 human
  └ 否则 → multi（或 both，依用户偏好）

P1 / P2，常规改动？
  └ 文件数 > 3？ → multi（强制升级）
  └ 否则 → ai（默认）
```
