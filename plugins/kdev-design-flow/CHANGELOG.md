# Changelog

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
