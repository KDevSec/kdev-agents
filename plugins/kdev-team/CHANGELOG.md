# Changelog

## 0.9.0 — 编排路由器（CEO 总编排）MVP：kdev_team python 包 + `/kdev-team` skill（plan/confirm/drive 三段）

- 新增 `kdev_team` python 包（lifecycle / roster / delivery_plan / lint / confirm / drive）+ `lifecycles/full-delivery.yml` 模板。
- `/kdev-team` skill & command：plan/confirm/drive 三段式——plan 读 delivery-plan.yml + lint 校验；confirm 等用户确认节点清单；drive 按链序 dispatch 各节点编排 agent。
- `node-table` 加 `delivery_node` 字段：编排路由器据此识别节点在交付链中的位置。
- MVP 仅兑现 full-delivery 一模板；两笔诚实债（评审开关 per-gate 自动化未建；链级进度无断点续跑、不达 L3）见 SKILL.md §5。

> G-004：本次改了 plugin version/skill/command/agent，用户需刷 marketplace（/plugin 更新或重装）+ 重启 session 才生效。

## 0.8.1 — reviewer 回函契约收口：裸文件交接 ≠ CLI flow-state handoff（Q 候选 2 + G 候选 3）

- 🔴 **修契约混用（Q 候选 2）**：reviewer 发函回函文件族（`handoffs/reviewer/<gate>.{request,*.score.md,arbitration.md,handoff.json}`）是 **裸 `Write`/`Read` 文件**，schema 自定义、**不含** CLI flow-state handoff 的 `node_id/employee/status/summary` 必填键。原文档让 caller 用 CLI `handoff-read` 取回函 verdict——真走会 `FlowStateError: missing required key 'node_id'`。统一改成 **caller/reviewer 用普通 `Read` 取**，CLI `handoff-write/read` 只服务 intra-flow(a) / P-B 跨员工(b) 两用（生产方持 `node_id` 的 flow-owner 节点）。
- **契约注落地**：`kdev-flow-driver/references/node-agent-routing.md`「reviewer 发函 dispatch」段加「一机三用」对照表 + 禁用 `kdev_core handoff-read` 读裸文件；`reviewer-orchestrator.md` / `gate-decision-logic.md` / `SKILL.md` / `dev-engineer-orchestrator.md` 措辞统一为 `Read`；reviewer 接入 spec §5 流程图勘误 + 决策说明落 `docs/superpowers/reviews/2026-06-14-Q候选2-reviewer-handoff契约-决策.md`。
- **修悬空指令（G 候选 3）**：`reviewer-orchestrator.md` 原「两能力相反结论 → 在 caller `events.jsonl` 留痕」无落地通道（callee 不碰 kdev-core 状态机、core 无 anomaly 事件类型）。改为异常落 `<gate>.arbitration.md` + 回函新增 `anomaly?` 结构化字段，**由 caller 决定**是否转 kdev-core 事件。
- **测试**：`tests/test_reviewer_wiring.py` +6（裸回函喂 CLI reader 必 `FlowStateError` 钉死契约方向 / 文档不得指令 CLI 读裸文件 / 契约注存在 / G 候选 3 anomaly 通道）。kdev-core **零改**。

## 0.8.0 — 第 4 个数字员工：测试工程师 test-engineer + 评审专家测试维度补齐

- **test-engineer（flow-owner，多 flow）**：staff.yml `node_tables`(test-design-flow ⊥ test-exec-flow) + `default_flow`；4 agent（orchestrator + 测试点设计/用例渲染/UI自动化，call kdev-test-points/cases/ui-autotest）。
- 🔴 **黑盒独立硬规**：测试设计只读需求/原型禁读 src；dev-engineer ⊥ test-engineer 并行不延续（写进 orchestrator/points agent/routing/gate-decision-logic/SKILL §2.4ter）。
- **2 个 node-table**：design-flow（黑盒设计 6 节点 1 评审闸，无 env）+ exec-flow（对被测环境执行 5 节点 1 评审闸，env-gated）。
- **评审专家解锁 2 测试能力（核心 10 余 4 → 余 2）**：dispatch-table +test-design(85)/test-coverage(80)；reviewer-orchestrator 路由 +2；reviewer-test-design/test-coverage agent + 2 standards；staff reviewer agents 7→9。
- env 边界用拆 flow 表达（design 永远可跑 / exec 需被测环境 URL）；本期"建好 + 单测绿"，exec-flow 实跑待真实测试任务（诚实标注）。
- kdev-core 零改。依赖声明/packaging（装员工连带装 skill）defer 进 roadmap Q-018。
- 测试：test_test_engineer_orchestration + test_test_engineer_wiring 新增；staff/agents/reviewer_dispatch 扩展。

## 0.7.0 — 2026-06-13

**跨员工直接发函硬规收口（v1.5 硬规 2/7）+ 评审专家活体 dogfood 验证**

- `kdev-flow-driver/SKILL.md` 新增 §2.4quater「跨员工直接发函硬规」：把概念合稿 §10.1 通信硬规 2/4/5 + spec §8 从设计稿收口成**编排 runtime 契约**，钉三不变量——① who→whom（编排↔编排直接发函不经 CEO；业务/评审能力不直接对外、跨员工走编排，只 dispatch 对方 `<employee>-orchestrator`）② 发函=结构化 request（caller+caps+target+产物指针，走 B 轨，非自由对话）③ 边界=评审给建议非拦截、🔴 经双重通过条件 FAIL 走 caller 有界回流+escalate、**处置权+入账都在 caller**。
- `references/node-agent-routing.md` reviewer 发函段 + `staff.yml` 头注释（callee 语义）+ `dev-engineer-orchestrator.md`/`req-architect-orchestrator.md` Principles 补对称指针/边界 prose（防散落漂移，硬规边界单一权威=§2.4quater）。
- 新增 `tests/test_dispatch_hard_rule.py`（9 用例）硬校验三不变量 + G-008 + canonical 回链（TDD 红→绿，全量 61 passed）。
- 守 **G-008 / YAGNI**：编排仍走通用 kdev-flow-driver，reviewer callee 不复用 driver/不 own flow；**不建任意「员工 A 主动发函员工 B」新原语**（现无调用方）。
- 附 **评审专家 reviewer 活体接线轻 dogfood 跑通**：临时 workspace 跑一条真实 `req-architect:g-sr-review` → 发函真实 `kdev-team:reviewer-sr` → 百分制评分表(84/100，双重条件 PASS) → caller `record-gate --by reviewer-expert` advance（验 callee 不 own flow / 评分落位 / caller 消费）。验证记录见 `docs/superpowers/specs/2026-06-13-评审专家reviewer-dogfood验证.md`。
- ⚠️ G-004：用户须刷 marketplace（`/plugin` 更新/重装）+ 重启 session 才生效（本期 prose+测试改动；dogfood 已在 v0.6.0 激活态跑过，不依赖 v0.7.0 激活）。

## 0.6.0 — 2026-06-13

**评审专家(reviewer) callee 员工上线（承 Q-016/Q-017，mode-2 已归蒸馏）**

- `staff.yml` 新增 reviewer callee 员工条目（`kind` + `dispatch_table`），花名册纳入第三方评审角色。
- 新增 `reviewer.dispatch-table`（6 能力：方案/代码/质量/安全/SR/AR-proto-design 评审），按能力路由到对应 cap agent。
- 新增 7 个 agent：`reviewer-orchestrator` 编排 + 6 个 cap agent（瘦 persona，发函 6 步收结构化判定）。
- 新增 7 份 standards（评审标准），cap agent 按对应 standard 出百分制评分表 + PASS/FAIL 判定（双重通过条件 total≥阈值 AND 🔴=0）+ 证据；FAIL 的回流（on_reflow）由 caller flow 路由。
- dev3/req3 评审 gate 兑现 `reviewer-expert`：`req-architect.node-table.yml` 3 闸（g-sr-review/g-ar-proto-review/g-design-review）+ `dev-engineer.node-table.yml` 3 闸（g-plan-review/g-code-review/g-sec-review）发函 `kdev-team:reviewer-orchestrator`（B 轨 handoff）。
- `dev-engineer.node-table.yml` 去 `stage1: deferred` 残留 + 头注释由「阶段1 deferred」改为「已建·发函评审专家」，与 req node-table 头注释一致（编排 prose 去 deferred）。
- ⚠️ G-004：用户须刷 marketplace（`/plugin` 更新/重装）+ 重启 session 才生效。

## 0.5.0 — 2026-06-12

**P-B：跨员工 handoff（需求架构师 SR/AR → 开发工程师 coding-flow 输入，M2 收口）**

- `kdev-flow-driver/SKILL.md` 新增 §2.4ter「跨员工 handoff（上游交付 → 下游 spec 输入）」：纯复用 B 轨 `handoff-write`/`handoff-read`，**join 键=同一 feature slug**；定义生产方→交付节点映射（`req-architect → n8-merge`）+ 上游缺失裸任务回退。**不新增 kdev-core 原语**（守「复用别重造」）。
- `references/node-agent-routing.md`：req-architect `n8-merge` 行加「收尾写交付 handoff」；dev-engineer `n0-env`/`n3-plan` 行加「先读同 slug 上游 req-architect 交付」。
- `dev-engineer-env`/`dev-engineer-plan` persona：加读上游交付（SR+背景 / AR+方案切增量），缺失回退裸任务。
- `req-architect-orchestrator` n8-merge + `req-architect.node-table.yml` 注释：补「落跨员工交付 handoff」生产侧契约。
- 编排仍走通用 `kdev-flow-driver`（G-008，不下放 orchestrator agent）；接 feature-first，不碰旧 `.kdev/flows/`。
- 测试：新增 `test_cross_employee_handoff.py`（9 个 SKILL/routing/persona/生产侧 契约不变量）；kdev-core `test_handoffs.py` 加跨员工 CLI 往返机制锁（2 个，零生产代码）。
- ⚠️ G-004：用户须刷 marketplace（`/plugin` 更新/重装）+ 重启 session 才生效。

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
