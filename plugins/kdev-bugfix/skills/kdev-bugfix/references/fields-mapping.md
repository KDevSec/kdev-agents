# fields-mapping

OpenSpec 模式 vs 纯模式字段交叉对照表 + 模式互译。

## 字段落点对照表

| bugfix 字段 | OpenSpec 模式落点 | 纯模式落点 |
|------------|------------------|-----------|
| Symptom | `proposal.md` `## Why` + `Bug Context` 段 | `bug-report.md` |
| Steps_to_Reproduce | `proposal.md` `Bug Context` 段 | `bug-report.md` |
| Environment | `proposal.md` `Bug Context` 段 | `bug-report.md` |
| Root_Cause | `design.md` | `fix.md` |
| Fix_Description | `design.md` | `fix.md` |
| Files_Changed | `proposal.md` `What Changes` + `tasks.md` T2/T3 | `fix.md` |
| Testing_Strategy | `tasks.md` T1/T4 备注 | `fix.md` |
| Spec_Impact | `design.md` + `specs/<capability>/spec.md`（如命中） | `fix.md`（仅口头记） |
| Risks | `design.md` | `fix.md` |
| Follow_Up | `design.md` | `fix.md` |
| Capabilities | `proposal.md` `Capabilities` 段 | 纯模式无此概念 |
| Spec delta | `specs/<capability>/spec.md` | 纯模式无此概念（口头记在 `fix.md` Spec_Impact 段）|
| bug_source | `proposal.md` frontmatter | `bug-report.md` frontmatter |
| Zentao 元数据（id / url / severity / opened_by） | `proposal.md` frontmatter | `bug-report.md` frontmatter |
| Review_Decisions（步骤 6 评审落档） | `design.md` 末尾 `## Review_Decisions` 段 | `fix.md` 末尾 `## Review_Decisions` 段 |

## 模式迁移：纯模式 → OpenSpec 模式

适用场景：项目后期引入 openspec，希望把已有的 `docs/bugfix/<bug-id>/` 历史 bugfix 迁到 `openspec/changes/<bug-id>/` 容器。

```bash
# 1. 在 repo 根 init openspec（如尚未 init）
openspec init . --tools claude

# 2. 对每个待迁移 <bug-id>：
for bug_id in $(ls docs/bugfix/); do
  # 2.1 创建 openspec change 容器
  SYMPTOM=$(grep -A 1 "^## Symptom" docs/bugfix/$bug_id/bug-report.md | tail -1)
  openspec new change "$bug_id" --description "$SYMPTOM"

  # 2.2 手工把字段重组（按本文对照表）：
  #   bug-report.md 的 Symptom + Why + Bug Context 段 → openspec/changes/$bug_id/proposal.md
  #   fix.md 的 Root_Cause + Fix_Description + Risks + Follow_Up → openspec/changes/$bug_id/design.md
  #   fix.md 的 Files_Changed + Testing_Strategy → openspec/changes/$bug_id/tasks.md（按 fields-tasks.md T1-T12）
  #   如有 Spec_Impact 命中 → openspec/changes/$bug_id/specs/<capability>/spec.md
  
  # 2.3 验证
  openspec validate "$bug_id"
  
  # 2.4 archive（如该 bug 已修完）
  openspec archive "$bug_id"
done

# 3. 保留旧 docs/bugfix/ 作为只读历史归档，或直接删（视项目习惯）
```

迁移**不是自动的**——需要人工把字段语义重组。原因：

- `bug-report.md` 的内容要拆到 `proposal.md` 的 Why / What Changes / Capabilities / Bug Context 四段
- `fix.md` 的内容要拆到 `design.md`（根因 + 风险）+ `tasks.md`（任务清单）两份
- 命名相同的字段（Root_Cause / Risks / Follow_Up）可直接复制；上下文需要重新组织

## 模式迁移：OpenSpec → 纯模式

反向迁移不常见（一般是项目初期跑过 openspec，后来想简化）。手工把：

- `proposal.md` Why + Bug Context → `bug-report.md`
- `design.md` 全部段 → `fix.md`（去 Capabilities 段）
- `tasks.md` 内容 → 弃用，纯模式不持久化任务清单

最后删 `openspec/changes/<bug-id>/`。

## 不要混用模式

⚠️ **同一 `<bug-id>` 不能同时存在于 `openspec/changes/<bug-id>/` 和 `docs/bugfix/<bug-id>/`**——必然不一致，违反 SKILL.md「不要做的事」末尾条目。

skill 启动时校验：发现混用 → BLOCKED 报错，要求用户明确选一个模式（删另一份）。
