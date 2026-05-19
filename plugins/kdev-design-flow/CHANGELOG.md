# Changelog

## 0.2.0 — 2026-05-19

**Stage 3 反发散修复：原型生成必须吃项目宪法 UI 规范**

之前 Stage 3 给 `frontend-design:frontend-design` 的 prompt 是硬编码的泛化约束，
没读 `.specify/memory/constitution.md`，导致原型脱离项目宪法（UED 6.0 / 8px 栅格 /
token 颜色 / AAA 对比度等）跑偏，每次输出方向都不一样。

- **新增 [stage3-prototype-prompt.md](skills/kdev-design-flow/references/stage3-prototype-prompt.md)**：
  Stage 3 prompt 模板化，含 `{{constitution_ui_block}}` / `{{design_system_refs_block}}` /
  `{{ar_content}}` 等占位符；要求 frontend-design 完成后写 `self-check.md` 自检报告
- **SKILL.md Stage 3 加"步骤 0"**：
  - 探测 `.specify/memory/constitution.md`，抽取所有提及"前端/视觉/原型/UI/UED/token/
    栅格/字号/字阶/行高/间距/颜色/对比度/字体/画板/8px/24 列/hex/px"的段落
  - 扫描 `references/*ued*/` / `references/*design-system*/` / `docs/design-system/` 等设计系统目录
  - 把上述内容**填进模板再调** frontend-design（不允许把空占位符发下去）
- **review-gate-prompt.md 加 C-2.6**：Gate 2 评审新增"宪法 UI 约束遵从"硬条款，
  覆盖 token 颜色 / 具体数值 / 对比度 / 唯一权威来源目录一致性；宪法不存在则标 `N/A`
- **新增 2 个回归 lint 测试**：
  - `test_stage3_extracts_constitution_ui_rules` —— 防止 Stage 3 退化回硬编码 prompt
  - `test_gate2_has_constitution_compliance_criterion` —— 防止 C-2.6 被误删

迁移：已在跑的 flow（`status == "in_progress"`）`--resume` 后会进入新版 Stage 3 步骤 0，
不影响已通过 Gate 2 的产物。

## 0.1.1 — 2026-05-08

iter-1 eval 的 P0 修复（详见 [evals/iteration-1/REPORT.md](evals/iteration-1/REPORT.md)）：

- **Description 区分 `--resume` 和 `superpowers:executing-plans`**（修 T07 漏触发）
  - 显式说"恢复 / 继续 / resume 之前被中断的 kdev-design-flow 流程"属于本 skill
  - 把 SKIP 子句里的"执行已有计划"明确限定为"已写好的 plan.md 文件"
  - 期望 trigger 准确度从 93.75% → ~100%
- **恢复模式段加 step 0 处理 `FlowStateError`**（修 B02 真 bug）
  - 用户跑 `--resume <wrong-slug>` 时不再撞未捕获 traceback
  - 提供可执行的下一步建议（检查 slug 拼写 / 检查工作目录 / 新建流程命令）
  - 同时补全 `status == "completed"` 分支的提示
- 加 2 个回归 lint 测试（test_resume_section_handles_missing_state + test_description_clarifies_resume_belongs_here），防止后续退化

## 0.1.0 — 2026-05-07

- Initial release
- 4 stages + 3 review gates + 1 merge step orchestration
- 3 review modes (ai / both / human), default ai
- Intermediate artifacts in `.kdev/design-flow/`, final in `docs/design-flow/`
- `--resume` to continue interrupted flow
- Hard dependency check on `spec-kit` plugin
