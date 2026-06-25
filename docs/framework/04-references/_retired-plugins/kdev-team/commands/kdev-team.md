---
description: CEO 总编排——把一个高层目标 LLM 路由到命名生命周期模板，渲染一屏编排结论人确认，再主会话顺序链式调 /kdev-flow-driver 跑通跨数字员工的交付流水线（MVP：full-delivery 三段：需求→开发→测试）
argument-hint: <高层目标> （别名 /kdev-ceo）
---

# /kdev-team

把"一个高层目标"端到端编排成跨数字员工的交付流水线。调用本命令即加载 kdev-team skill（总编排 / CEO 总编排 / 一个目标跑通需求到测试）。

## 用法

```
/kdev-team 做用户认证功能
/kdev-team 给 X 项目加一个导出 CSV 的功能
/kdev-team 实现订单退款流程并出测试
```

## 参数

- `<高层目标>`：必填。一句自然语言描述的高层交付目标（不是单员工任务——单员工跑用 `/kdev-flow-driver`）。

## 三段

1. **plan**：LLM 把目标对号入座到 `lifecycles/*.yml` 模板，产 delivery-plan（封闭 schema）。confidence 低或贴两模板时必填 runner_up。
2. **confirm**：`kdev_team.lint.validate` 校验过 → `confirm.render_screen` 渲染一屏编排结论，人确认 / 微调（`apply_edit` 循环）。
3. **drive**：冻结 delivery-plan 落 `features/<slug>/delivery-plan.yml`，主会话**顺序**调 `/kdev-flow-driver` 跑各段（同 slug 接力 + 停人闸），各段评审由 flow-driver 内部按 node-table 触发。

## 硬约束

你（主控）是 CEO 总编排器，**只能主会话跑**——子 agent 不能再开子 agent，所以**绝不**把 `/kdev-flow-driver` 当 `Agent()` 子 agent 派出去（那样它就无法再派 capability agent）。drive 段在主会话里**顺序调** `/kdev-flow-driver`（它也跑主会话，内部才派 capability agent）。

参数原文：`$ARGUMENTS`

按 `kdev-team` skill 的 SKILL.md 步骤执行。
