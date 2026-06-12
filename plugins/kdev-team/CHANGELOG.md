# Changelog

## 0.4.0 — 2026-06-12

**B 轨：编排派单 run_in_background 化 + 文件交接（§1.5.6 B done）**

- `kdev-flow-driver/SKILL.md` §2.4 业务派单：前台同步 `Agent({...})` → `run_in_background: true` + 约定路径 JSON 文件交接，去掉内联渲染 + 大段 result 回灌（~80% 混杂），压"派单刷屏主会话"主痛点。
- 新增 §2.4bis 文件交接协议（schema + 路径 + 读写 CLI），复用 kdev-step-recorder 已验 fire-and-forget 思路 + kdev-core `handoff-write`/`handoff-read`（v0.3.0）。
- §4 上下文模板加「完成后写交接文件」指令（注入派单 prompt 末尾；**不改 agent persona 定义**）。
- 主循环靠 completion 通知 + `handoff-read` 拿"干完没 + 产物路径 + gate 输入"；交接文件缺/坏 = 显式失败不静默 advance。
- **gate 判断仍在主循环**（§2.5 不后台化）——守 §1.5.6 B 轨边界：执行甩后台、决策留主控。
- 测试：新增 `test_bg_dispatch.py`（4 散文不变量，含「gate 不被后台化」硬守）。
- ⚠️ G-004：用户须刷 marketplace（`/plugin` 更新/重装）+ 重启 session 才生效。

## 0.3.1 — 2026-06-12

**修复：派单 `subagent_type` 裸名 → 插件全名 `kdev-team:<id>`（员工起不来 BUG）**

- 根因：CC agent 注册表只认插件命名空间全名 `kdev-team:<agent-id>`，裸 canonical id 报 not-found；而 `kdev-flow-driver` SKILL/路由文档/orchestrator 的派单示例用的是裸名 → 主控按 SKILL 派单 not-found，业务 agent 起不来。
- `references/node-agent-routing.md` 顶部新增「派单标识」规则（一律 `kdev-team:<id>`），并把 `subagent_type` 列、gate 检查列全部改全名。
- `kdev-flow-driver/SKILL.md` 的 `Agent({subagent_type})` 示例 + n6b 派单提示改全名，并加 🔴 全名提醒。
- `dev-engineer-orchestrator` / `req-architect-orchestrator` 的 Capabilities（派单）表改全名。
- `references/gate-decision-logic.md` 的 e2e/deploy 派单引用改全名。
- **未改**（保持裸 canonical id，插件系统负责加前缀）：agent `.md` frontmatter `name:`、`staff.yml` `agents:` 花名册、node-table.yml node/gate id。
- 纯标识修正，不改任何编排行为/节点逻辑；测试 22 全绿。
- ⚠️ G-004：用户须刷 marketplace（`/plugin` 更新/重装）+ 重启 session 才生效。

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
