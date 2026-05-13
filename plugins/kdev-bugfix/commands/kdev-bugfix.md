---
description: Bug 修复 8 步流程（深集成 OpenSpec + 禅道双源 + 三档评审 + dry-run 演练）：禅道拉取 OR 直接对话 → openspec new change → proposal/design/specs/tasks → systematic-debugging 根因 → RED 回归测试 → GREEN 最小修复 → 验证闸门 → 评审闸门（AI/multi/human）→ openspec validate → kdev-commit → 禅道 active→resolved 状态回写。--dry-run 跑完 8 步但不动持久状态
argument-hint: <bug-id-or-symptom> [--from-zentao <id>] [--review-mode=ai|multi|human|both] [--dry-run] [--p0] [--auto] [--no-openspec] [--openspec] [--archive] [--no-zentao-update]
---

# /kdev-bugfix

显式触发 `kdev-bugfix` skill，把"用户报了一个 bug"或"禅道里有条 bug 要修"翻成一条可复跑的修复链路。**默认深集成 OpenSpec + 双源 intake + AI 自评**。

## 用法

```
# 直接对话源
/kdev-bugfix login-button-error
/kdev-bugfix "线上 500 after deploy" --p0
/kdev-bugfix issue-123 --auto --archive

# 禅道源
/kdev-bugfix --from-zentao 12345
/kdev-bugfix --from-zentao 12345 --p0 --review-mode=both
/kdev-bugfix --from-zentao 67890 --no-zentao-update   # 修但不动禅道状态

# 评审模式
/kdev-bugfix login-button-error --review-mode=multi
/kdev-bugfix order-amount-calc --review-mode=human
/kdev-bugfix data-migration-failed --review-mode=both

# 跨项目复用
/kdev-bugfix legacy-bug-id --no-openspec     # 目标项目无 openspec
/kdev-bugfix new-project-bug --openspec       # 强制初始化 openspec

# 演练（dry-run）：完整跑 8 步但不动持久状态
/kdev-bugfix --from-zentao 12345 --dry-run             # 看流程合理性
/kdev-bugfix --from-zentao 12345 --dry-run --auto      # 完全自主演练
/kdev-bugfix login-button-error --dry-run --p0         # 演练 P0 hotfix 快路径
```

## 参数

### 必填
- `<bug-id-or-symptom>`：必填（**或** `--from-zentao <id>` 替代）
  - kebab-case slug → 直接当 `<bug-id>`
  - 自然语言症状描述 → skill 生成 kebab-case `<bug-id>` 并问你确认

### bug 来源
- `--from-zentao <id>`：从禅道拉取 bug（bug_source=zentao）。需配 `ZENTAO_API_URL` + `ZENTAO_API_TOKEN`（详见 [zentao-integration.md](../skills/kdev-bugfix/references/zentao-integration.md)）

### 严重度 / 模式
- `--p0`：标 P0 严重度，走 hotfix 快路径（回归测试 + 验证闸门 + 根因 + 评审仍不能跳）
- `--auto`：Auto Mode（模式判定 / 严重度 / 评审升档 / 禅道回写**自动决策**不询问）
- `--openspec` / `--no-openspec`：强制开/关 OpenSpec 模式
- `--archive`：步骤 6.3 后自动 `openspec archive <bug-id>`

### 评审
- `--review-mode=ai`（默认）：主 Claude 用 superpowers:code-reviewer 自评
- `--review-mode=multi`：AI 自评 + 派 subagent (opus) 独立评审
- `--review-mode=human`：暂停等用户评审
- `--review-mode=both`：multi + human 串行

**强制升级**：命中 P0 / 鉴权 / 跨模块 / 数据迁移 / 修改文件数 > 3 → 自动升到 multi（即便传 `ai`），向用户报告升档理由

### 禅道回写
- `--no-zentao-update`：跳过步骤 8 禅道状态回写（仅 bug 已 commit，但禅道 active 状态不动）

### 演练
- `--dry-run`：跑完整 8 步但**不动任何持久状态**——不写产物 / 不动 src/ / 不动 git / 不 commit / 不调禅道写接口。每个"本应执行"的动作输出 `🔵 DRY-RUN \| step N: ...` 预览（含完整 artifact 内容、diff、curl 命令）
  - **底线保证**：dry-run 不会有任何文件 / git / 禅道 / commit 副作用
  - **不保证**：步骤 3 复现脚本（用户自定义命令）的副作用 + 拉禅道 GET 会在禅道 access log 留记录
  - **重要警告**：dry-run **跳过 RED 实测**——"watch it fail" 保证缺席。真跑前必须去掉 `--dry-run` 重做
  - 详见 [skills/kdev-bugfix/references/dry-run-mode.md](../skills/kdev-bugfix/references/dry-run-mode.md)

## 你的任务

调用 `kdev-bugfix` skill，把 `$ARGUMENTS` 透传给它。skill 8 步流程：

1. **Intake & Triage**（双源：禅道拉取 OR 直接对话 / 生成 bug-id / 判模式 / 判严重度）
2. **Proposal**（OpenSpec：`openspec new change` + `proposal.md`；纯模式：`bug-report.md`；禅道源 seed 字段）
3. **根因投资**（委派 `superpowers:systematic-debugging` Iron Law）
4. **Design + RED**（`design.md` + 委派 `superpowers:test-driven-development` 写回归测试）
5. **Tasks + GREEN**（`tasks.md` + 最小修复 + 委派 `superpowers:verification-before-completion`）
6. **评审闸门**（AI 自评 → multi/human 按 flag / 强制升级；任一 FAIL 回 5）
7. **Validate + Commit**（`openspec validate` + 委派 `kdev-commit`）
8. **后置动作**（bug_source=zentao 时调禅道 API `active → resolved`，失败兜底输出手动指引）

参数原文：`$ARGUMENTS`

按 `kdev-bugfix` skill 的 SKILL.md 8 步流程执行。
