# Changelog

## 0.3.0 — 2026-06-12

**P-A：第二个数字员工「需求架构师 req-architect」接 kdev-core 底座**

- 新增 `orchestration/req-architect.node-table.yml`：design-flow SOP（IR→SR→AR→原型→方案 5 业务阶段 + 3 评审 gate + 聚合收尾，11 节点）。复用通用 `kdev-flow-driver`，kdev-core 零改。
- 新增 6 个 `req-architect-*` agent（1 编排 + 5 业务：clarify/spec/decompose/prototype/design），瘦 persona 真 CC frontmatter。
- `staff.yml` 追加 req-architect 词条（flow_skill=kdev-design-flow）。
- `kdev-flow-driver/references/` 追加 req-architect 路由 + gate 判据段（driver 本体通用不改）。
- 3 评审 gate 阶段1 全 `reviewer=self`（复刻 design-flow 自评 SOP，非 deferred）；评审 FAIL 有界 → blocked 升人。

## 0.2.0 — 2026-06-07

**P-0：dev-engineer 员工集中 kdev-team，接 kdev-core 底座**

- 新建 `plugins/kdev-team/`（plugin.json v0.1.0 → v0.2.0 + marketplace 注册）
- 7 个 `dev-engineer-*` persona → 真 CC frontmatter agent（canonical id，可 `Agent({subagent_type})` 直派）
- `orchestration/dev-engineer.node-table.yml`（coding-flow SOP node-table）
- `staff.yml` 花名册初版（dev-engineer 词条）
- `kdev-coding-flow` SKILL 回归纯方法论（编排指令归 `dev-engineer-orchestrator` agent）
- 测试 kdev-team 11 + kdev-core 76 全绿

## 0.1.0 — 2026-06-07

- Initial release（plugin 骨架，kdev-team 命名空间建立）
