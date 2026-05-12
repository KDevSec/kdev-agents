---
description: 按 13 节点 SOP 端到端实施一个 spec/plan/prototype 三件套需求，跑到部署 + E2E 全绿；强制 TDD / Per-Increment E2E Gate / Phase 0 环境对齐
argument-hint: <specs-dir-or-feature-name> [--auto] [--bundle-strategy=auto|conservative|aggressive]
---

# /kdev-coding-flow

把"从需求到上线"这一条链路用 13 节点 SOP 固化为可复跑的 skill。主控只在 3 个人工判断 Gate 决策，其余下放 subagent。

## 用法

```
/kdev-coding-flow specs/001-user-auth
/kdev-coding-flow specs/003-checkout --auto
/kdev-coding-flow specs/004-notifications --bundle-strategy=conservative
```

## 参数

- `<specs-dir-or-feature-name>`：必填。指向含 `spec.md` + `plan.md` + `prototype` 三件套的目录或 feature slug。
- `--auto`：开启 Auto Mode，3 个 Gate 也按规则自动判断（仍受 review 4 次上限约束）。
- `--bundle-strategy=auto|conservative|aggressive`：默认 `auto`（按 SKILL.md 量化阈值决策合并粒度）。

## 你的任务

调用 `kdev-coding-flow` skill，把 `$ARGUMENTS` 透传给它。skill 自身负责：

- 节点 0 项目背景对齐 / Phase 0 环境检查
- 13 节点主循环（含 3 个人工 Gate / Per-Increment E2E Gate / 4-shot review 上限）
- 按 CLAUDE.md 二档分工派单（sonnet 编码 / opus 评审与高复杂度）
- 产出 `sop-execution-log` 收尾

参数原文：`$ARGUMENTS`

按 `kdev-coding-flow` skill 的 SKILL.md 步骤执行。
