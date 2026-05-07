---
name: kdev-design-flow
description: Use when 用户明确请求"把这个需求走一遍设计流程 / 帮我从需求到设计完整跑一遍 / 走 kdev 设计流程 / 完整需求分析+原型+设计 / 需求到方案一条龙 / 一站式跑需求分析"等表达，且明确希望产出 SR 文档 + AR 用户故事 + 高保真原型 + 概要详细设计这一整套交付物时触发。**SKIP**：用户只是在探讨想法 / 在判断是否值得做（应让 superpowers:brainstorming 或 office-hours 处理）；用户只想做单点设计或只要求其中一个产物（直接调对应 skill 即可）；用户在执行已有计划（应让 superpowers:executing-plans 处理）。本 skill 编排：内置 SR 分析 → spec-kit:specify (AR) → frontend-design (高保真原型) → spec-kit:plan (概要+详细设计)，3 个评审闸门，每闸门最多 3 次重试，3 档评审模式（默认 ai = Claude 自评）。
---

# kdev-design-flow Skill

把"原始需求 → SR 需求文档 → AR 用户故事 → 高保真原型 → 概要+详细设计"这条工程链路固化为一个可复跑的 skill，串联已有 spec-kit 和 frontend-design 插件，并嵌入 3 个评审闸门避免方向漂移。

## 调用方式

通常通过 `/kdev-design-flow` 斜杠命令触发，不是 description 自动捕获（除非用户语气非常明确）。

## 工作流总览

| 阶段 | 用什么 | 输入 | 输出位置 |
|------|--------|------|----------|
| Stage 1 | 内置 prompt（references/stage1-sr-prompt.md） | 用户原始需求 | `.kdev/design-flow/<slug>/stage-1-sr/iter-N.md` |
| Gate 1 | 评审机制 | SR 文档 | (PASS / FAIL + 反馈) |
| Stage 2 | `Skill` 调 `spec-kit:specify` | 上一步通过的 SR 文档 | `.kdev/design-flow/<slug>/stage-2-ar/iter-N.md` |
| Stage 3 | `Skill` 调 `frontend-design:frontend-design` | 上一步通过的 AR 用户故事 | `.kdev/design-flow/<slug>/stage-3-prototype/iter-N/` |
| Gate 2 | 评审机制 | AR + 原型 | (PASS / FAIL + 反馈) |
| Stage 4 | `Skill` 调 `spec-kit:plan` | 上一步通过的 AR + 原型 | `.kdev/design-flow/<slug>/stage-4-plan/iter-N.md` |
| Gate 3 | 评审机制 | 设计方案 | (PASS / FAIL + 反馈) |
| Merge | 见 references/output-merge-rules.md | 各阶段最终通过版本 | `docs/design-flow/<slug>/` |

## 启动顺序

(详见后续 Task 6-12 各章节)
