# Stage 3 — 高保真原型生成 Prompt（供 frontend-design 接力）

> 本模板由 kdev-design-flow Stage 3 在调用 `frontend-design:frontend-design` 前**完整填充**后注入。
> 占位符 `{{...}}` 必须全部替换；不要把空白占位符直接发给 frontend-design。

---

为下面这组用户故事设计一个**高保真原型**（HTML/CSS/必要的 JS），目标是评审用、不是生产用。

## 用户故事（AR）

<<<AR
{{ar_content}}
AR>>>

## 🔴 项目宪法约束（**最高优先级，必须遵守**）

{{constitution_ui_block}}

> 若上述约束与"通用 Web 设计最佳实践"冲突，**以宪法为准**。
> 若任一具体数值（如字号 / 栅格 / 颜色 token）在宪法中明确给出，原型 **MUST** 使用该具体数值，不得自由发挥。

## 设计系统参考资料（**MUST 先 Read 再动笔**）

{{design_system_refs_block}}

## 通用约束（在不违反宪法的前提下生效）

- 可在浏览器直接打开（单 HTML 文件或带 `index.html` 的目录）
- 涵盖核心交互路径（不需要每个 edge case 都画）
- 视觉语言要和产品语境匹配（**不要**默认浏览器原生灰色按钮、不要 Bootstrap 默认蓝、不要"AI 风"渐变 hero）
- **不要**内嵌真实凭证 / 内部 URL / 敏感数据 / 真实用户姓名邮箱
- 输出落盘到 `.kdev/design-flow/{{slug}}/stage-3-prototype/iter-{{iter}}/`，至少包含 `index.html`
- 多页面时用同目录下的相对链接互跳（不要绝对路径）

## 反发散自检清单（**完成后必须逐条对照**）

提交前你 **MUST** 自检并在产物根目录写一份 `self-check.md`：

- [ ] 颜色：未使用未在宪法/设计系统中声明的裸 `#hex`；token 化覆盖率（注释或 CSS 变量形式都算）
- [ ] 间距：未使用违反栅格（如宪法要求 8px 网格则不得出现 `padding: 7px` 之类）
- [ ] 字号 / 行高：基线值与宪法一致
- [ ] 字体：未引入未授权字体（system-ui / 宪法明列字体之外的不允许）
- [ ] 对比度：正文文本对比度 ≥ 宪法要求阈值（如 7:1 AAA）
- [ ] 画板：在宪法要求的最小宽度（如 1366px）下不出现横向滚动条或元素重叠
- [ ] 交互：所有 AR 中标注的核心路径都可点击演示（即使是 mock 数据）

> 若某条无法满足（例如宪法未声明阈值），在 `self-check.md` 显式标注"N/A — 宪法未声明"，**不要**静默跳过。

## 反馈循环（仅 iter > 1 时适用）

如果是第 2 或 3 次迭代（`iter > 1`），上一轮 Gate 2 的评审反馈在：
`.kdev/design-flow/{{slug}}/stage-3-prototype/iter-{{prev_iter}}-review.md`

读它，然后**针对每条不通过点修订**，不要从头重写。
