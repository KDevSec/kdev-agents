````markdown
# Stage 1 — SR 级需求分析 Prompt

你正在为一个 feature 做 SR (System Requirements) 级别的需求分析。这是从"原始需求一句话"到"用户故事 (AR)"之间的桥接层：要把模糊愿望拆成可被 spec-kit:specify 接力的清晰需求。

## 输入

用户给的原始需求（一句话或一段话）：

<<<USER_INPUT
{{user_input}}
USER_INPUT>>>

## 你要做的

1. **识别核心价值主张**：这个 feature 解决谁的什么问题？为什么现在做？
2. **拆出 3-7 个 SR**（系统需求条目），每条覆盖一个独立的功能/质量维度。命名规范：`SR-<NN>: <一句话>`。
3. **每个 SR 给出**：
   - 验收标准（Given-When-Then 或 bullet 形式）
   - 关键约束（性能/安全/合规等）
   - 与其他 SR 的依赖关系
4. **识别 3-5 个开放问题**：你不确定但用户必须澄清的（用 `OPEN-Q-NN` 编号）。
5. **不要做的事**：不要画原型、不要写 API spec、不要写代码。这些是后续阶段的事。

## 输出格式

按 `references/stage1-sr-template.md` 的结构填写，落盘到 `.kdev/design-flow/{{slug}}/stage-1-sr/iter-{{iter}}.md`。

## 反馈循环

如果是第 2 或 3 次迭代（`iter > 1`），上一轮的评审反馈在：
`.kdev/design-flow/{{slug}}/stage-1-sr/iter-{{iter-1}}-review.md`

读它，然后**针对每条不通过点修订**，不要从头重写。
````
