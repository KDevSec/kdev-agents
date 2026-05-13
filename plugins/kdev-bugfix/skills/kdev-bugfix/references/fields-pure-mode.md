# fields-pure-mode

纯模式（无 `openspec/`）— `docs/bugfix/<bug-id>/{bug-report.md, fix.md}` 双文件字段模板。

字段命名与 OpenSpec 模式 [fields-proposal.md](fields-proposal.md) / [fields-design.md](fields-design.md) **完全对齐**——便于将来从纯模式迁移到 OpenSpec 模式（迁移命令见 [fields-mapping.md](fields-mapping.md)）。

---

## §A `docs/bugfix/<bug-id>/bug-report.md`

### frontmatter（YAML 段，必须）

```yaml
---
bug_source: zentao | direct
zentao_bug_id: 12345              # 仅 bug_source=zentao
zentao_url: https://...            # 仅 bug_source=zentao
zentao_severity: 2                 # 仅 bug_source=zentao
---
```

详见 [zentao-integration.md §2](zentao-integration.md)。

### 正文模板

```markdown
# Bug Report：`<bug-id>`

## Symptom
<一两句描述用户能直接感知到的现象>

## Steps_to_Reproduce
1. <第 1 步>
2. <第 2 步>
3. <第 N 步>

**前置条件**：
- <如：用户已注册但未验证邮箱>

## Expected_Behavior
<应当发生什么。一句话>

## Actual_Behavior
- **错误信息**：
  ```
  <stack trace / 控制台输出 / 错误码 / HTTP response>
  ```
- **截图**：`./screenshots/<filename>.png`（如适用）
- **日志摘录**：
  ```
  <时间戳 + 关键日志行>
  ```

## Environment
| 维度 | 值 |
|------|----|
| OS / 平台 | <如 macOS 14.5 / Ubuntu 22.04> |
| 浏览器（如适用） | <Chrome 124 / Safari 17> |
| 运行时 | <如 Python 3.11.7 / Node 20.11> |
| 项目版本（git sha 或 tag） | <如 v1.2.3 / abc1234> |
| 部署环境 | <本地 dev / 测试 / 生产> |
| 复现率 | <100% / 偶发 ~30% / 仅一次> |

## Initial_Hypothesis（可选）
<填写前的初步猜测。这只是「假设」，不是「根因」。根因写到 fix.md>

## Workaround（可选）
<用户当前能用什么临时绕开>

---
**生成时间**：`<YYYY-MM-DD>`
**生成方式**：`kdev-bugfix` skill（纯模式）
```

---

## §B `docs/bugfix/<bug-id>/fix.md`

字段与 OpenSpec 模式 `design.md` + `tasks.md` 内容合并（无 `Capabilities` / `specs delta` 段，因为纯模式没有 openspec 容器）。

### 完整模板

```markdown
# Fix：`<bug-id>`

## Root_Cause
<真正的根因。回答「为什么这段代码会产生 Symptom」。两到四句话，必须能让一年后的同事看完就懂>

**好例子 / 坏例子参考 [fields-design.md](fields-design.md) Root_Cause 段**

## Fix_Description
- **改动 1**：`<文件路径>` <如何改> ← <理由>
- **改动 2**：<同上>

## Files_Changed
**src/**
- <file1>
- <file2>

**tests/**
- <regression-test-file> ← 步骤 4.4 写的回归测试

**docs/**
- docs/bugfix/<bug-id>/bug-report.md
- docs/bugfix/<bug-id>/fix.md（本文件）

## Testing_Strategy
- **回归测试**：`<test 名>` 覆盖 <根因 + 等价类列表>
- **既有测试**：全量 PASS
- **type-check / lint / E2E**：详见 commit 记录

## Spec_Impact（可选）
<判断 bug 是否暴露了 spec/PRD 错误。仅当命中时填>

- **Affected_Spec**：`<spec 文件路径>` 或 `None`
- **Change_Type**：`update` / `add` / `remove` / `none`
- **Description**：<spec 里哪一句话需要改成什么>
- **Justification**：<为什么 spec 需要改而不是只改代码>

⚠️ 纯模式没有 openspec 容器，spec delta **不能**落到产物里——仅在本段口头记录；真实 spec 修改另起 `kdev-change` 流程。

## Risks（可选）
<本次修复可能引入的回归 / 性能 / 兼容性风险>

## Follow_Up（可选）
<本次发现但不修的相关项。开 chore/refactor issue 跟踪>

## Review_Decisions
<步骤 6 评审完成后追加，详细格式见 [review-modes.md §5](review-modes.md)>

---
**生成时间**：`<YYYY-MM-DD>`
**生成方式**：`kdev-bugfix` skill（纯模式）
**关联 commit**：`<git sha>`（kdev-commit 输出）
```

---

## 与 OpenSpec 模式的语义差异

| 维度 | OpenSpec 模式 | 纯模式 |
|------|--------------|--------|
| 容器 | `openspec/changes/<bug-id>/` 子树 | `docs/bugfix/<bug-id>/` 子目录 |
| artifacts 数 | 3-4（proposal + design + [specs/] + tasks）| 2（bug-report + fix）|
| schema 校验 | `openspec validate <bug-id>` 必过 | 无 schema 校验 |
| 任务追踪 | `tasks.md` T1-T12 物化 | TodoWrite 内部跟踪，不落文件 |
| spec delta | `specs/<capability>/spec.md` 可写 | 仅在 `fix.md` Spec_Impact 段口头记 |
| archive | `openspec archive <bug-id>` 可走 | 产物永久留在 `docs/bugfix/<bug-id>/` |
