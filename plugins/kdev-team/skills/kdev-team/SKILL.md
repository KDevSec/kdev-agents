---
name: kdev-team
description: CEO 总编排——把一个高层目标端到端跑通需求到测试的跨数字员工交付流水线。你（主控）扮演 CEO 总编排角色：把目标 LLM 对号入座到命名生命周期模板（lifecycle）→ 渲染一屏编排结论让人确认/微调 → 冻结 delivery-plan → 主会话顺序链式调 /kdev-flow-driver 跑各段（需求→开发→测试），段间同 slug 接力、停人闸停人。Use when 用户说"总编排 / CEO 总编排 / 一个目标跑通需求到测试 / 把这个需求从头跑到测试 / 端到端交付 X / 编排一条跨员工流水线"，或 `/kdev-team <高层目标>`（别名 `/kdev-ceo`），或任何"一个高层目标 × 跨多个数字员工 × 端到端交付"的组合请求。单员工单任务请改用 /kdev-flow-driver。
---

# kdev-team：CEO 总编排（一个目标跑通需求到测试）

把"一个高层目标"端到端编排成跨数字员工的交付流水线。你（顶层主控）扮演 CEO 总编排角色：先把目标路由到一个命名的**生命周期模板**（lifecycle），产出一份**delivery-plan**（封闭 schema 的交付计划）；渲染一屏编排结论给人确认/微调；确认后冻结计划，再在**主会话**里**顺序**调 `/kdev-flow-driver`，让每个数字员工按自己的 SOP 跑完一段，段间同 slug 接力，到停人闸停下向人汇报。

整个编排分三段：**plan → confirm → drive**。本 skill 不引入任何新引擎、新原语——它只是把已建的 lifecycle / lint / delivery_plan / confirm / drive 五个纯函数模块、kdev-core CLI、`/kdev-flow-driver`、reviewer-orchestrator、HUD 串成一条主会话循环。

---

## §0 硬约束（贯穿整个编排，先读再动）

🔴 **子 agent 不能再开子 agent**（Claude Code 硬限制）。后果链：

1. **总编排只能主会话跑**。CEO 总编排角色必须由顶层 session 扮演——你就是总编排器，不要把整段编排下放给某个 agent 自跑。
2. **drive 段在主会话里顺序调 `/kdev-flow-driver`**。`/kdev-flow-driver` 本身也跑在主会话（它是另一层主控编排循环），**它内部**才会派 capability agent（如 `dev-engineer-orchestrator` / 各 reviewer-cap）。
3. 🔴 **绝不**把 `/kdev-flow-driver` 当 `Agent()` 子 agent 派出去。一旦把它派成子 agent，它就降为"子 agent"，无法再派 capability agent，整条 flow 当场断掉。正确做法是：主会话**自己**执行 `/kdev-flow-driver <emp> ...`（即把控制权交给那段 flow-driver 循环），它跑完回到主会话，再进下一段。

一句话：CEO（本 skill）顺序"接力跑"各段 flow-driver，全程不开任何编排 subagent。

---

## §1 plan 段：目标 → 生命周期模板 → delivery-plan

用户给一个高层目标（如"做用户认证功能"）。你要把它**对号入座**到一个命名生命周期模板，产出 delivery-plan dict。

### 1.1 读模板与花名册

```python
from kdev_team import lifecycle
templates = lifecycle.list_templates()          # 列 lifecycles/*.yml 的 template_id
tpl = lifecycle.load_template("full-delivery")   # 取某模板 dict（不存在 → TemplateError）
```

每个模板 dict 含：`template_id` / `display` / `when`（命中条件，给 LLM 对号入座用）/ `stages`（每段 `{emp, flow, handoff_from}`）/ `reviews_default` / `human_gates_default`。同时读 `staff.yml` 拿到合法 emp 集合。

> **MVP 范围**：当前只兑现 `full-delivery` 一模板（需求→开发→测试三段）。其余模板（design-only / design+build / test-only / build-only）是后续纯加 YAML 即生效——不要在本 skill 里硬编码它们的逻辑。

### 1.2 LLM 对号入座

你（LLM）读各模板的 `when`，结合目标语义判断命中哪个模板，给出：

- `confidence`（0–1，对路由判断的把握）
- `reasoning`（一句话为什么是这个模板）
- 命中模板的 `stages`（照模板 seed，可逐段 `on: true/false` 增删、可改 `review_overrides` / `human_gates`）
- **当 `confidence < 0.6` 或目标同时贴近两个模板时，必填 `runner_up: {template_id, why_not}`**（次优模板 + 为什么没选它），供确认屏并列展示。

### 1.3 组装 delivery-plan dict

按 `kdev_team.delivery_plan` 的 schema 组装（字段示例见模块 docstring / 任务简报）：

```yaml
template_id: full-delivery
slug: user-auth
goal: "做用户认证功能"
confidence: 0.86
reasoning: "全新功能+无现成SR+安全敏感+需可测交付 → 全交付三段"
stages:
  - {emp: req-architect, flow: design-flow,      on: true, handoff_from: null}
  - {emp: dev-engineer,  flow: coding-flow,      on: true, handoff_from: req-architect@n8-merge}
  - {emp: test-engineer, flow: test-design-flow, on: true, handoff_from: req-architect@n8-merge}
review_overrides:
  dev-engineer: {g-sec-review: reviewer-expert}
human_gates: [after-req]
runner_up: {template_id: design+build, why_not: "含'功能'隐含可交付→需测试段"}
```

此时 plan 还**只在内存里**（未落盘、未冻结）——进 §2 校验。

---

## §2 confirm 段：lint 校验 → 渲染一屏 → 人确认/微调

### 2.1 校验先行（非空不进确认屏）

```python
from kdev_team import lint
errors = lint.validate(plan, staff=staff)   # 返回 list[str]；空 = 合法
```

🔴 **`errors` 非空 → 据错修正 plan 重出，绝不带着错误进确认屏**（避免人确认一份非法计划）。修正后重跑 `validate`，直到返回空列表。

### 2.2 渲染一屏编排结论

```python
from kdev_team import confirm
screen = confirm.render_screen(plan, staff=staff)
print(screen)
```

`render_screen` 打印这一屏：路由到哪个模板 + confidence + reasoning + runner_up（若有）+ 各段 emp/flow/on + per-gate 评审意图（专家/自评）+ 链级停人闸（human_gates）。**per-gate 评审项只是意图展示**（见 §5 诚实债 1）。

### 2.3 人确认/微调循环

读人输入：

- 人按 **Enter**（无修改）→ 接受当前 plan，进 §3。
- 人给一条编辑命令 → `confirm.apply_edit(plan, command)` 应用（非法命令 → `EditError`）→ 回到 §2.1 重跑 `validate` + 重渲一屏 → 再读人输入。如此循环，直到人 Enter。

🔴 **禁一键 Enter 的两种情形**（强制二次确认，不让人闭眼放行）：

1. `confidence < 0.6`（路由判断本身没把握）；
2. 计划**丢段**（某关键 stage `on: false` 导致交付链不完整，如有"功能"目标却砍掉测试段）。

这两种情形下，明确向人指出风险点，要人**显式输入确认词**（而非空 Enter）才放行。

---

## §3 drive 段：冻结 → build_sequence → 逐段接力跑 flow-driver

### 3.1 冻结落盘（写一次、之后不变）

```python
from kdev_team import delivery_plan
delivery_plan.write(workspace, plan)   # 落 features/<slug>/delivery-plan.yml
```

冻结后该 yml 不再改——它是本次链级编排的权威快照，HUD 读它渲链进度（§6）。

### 3.2 取有序步骤

```python
from kdev_team import drive
steps = drive.build_sequence(plan)   # list[step]
```

每个 step 含：`stage_index` / `emp` / `flow` / `dispatch_id` / `handoff_from` / `driver_cmd` / `dispatch_start_cmd` / `dispatch_done_cmd` / `human_gate_after`。`dispatch_start_cmd` / `dispatch_done_cmd` 是给 `python3 -m kdev_core` 的参数列表；`driver_cmd` 是要在主会话执行的 `/kdev-flow-driver ...` 命令串。

### 3.3 逐段循环（按 steps 顺序，主会话内）

对每个 step：

1. **写派单 start 事件**：`python3 -m kdev_core <step.dispatch_start_cmd...>`
   （即 `dispatch-start <flow> <slug> --emp <e> --dispatch-id <id> --stage-index N`）→ 向 `features/<slug>/events.jsonl` append `phase=start` 事件。
2. **主会话执行 `driver_cmd`**：在**主会话**里跑 `step.driver_cmd`（`/kdev-flow-driver <emp> --task <slug> --slug <slug>`），让该员工的 flow-driver 循环跑到 terminal（完成）或 BLOCKED。**不要 `Agent()` 派它**（§0 硬约束）。
3. **写派单 done 事件**：`python3 -m kdev_core <step.dispatch_done_cmd...>`
   （即 `dispatch-done <flow> <slug> --emp <e> --dispatch-id <id> --status done`）→ append `phase=done`。
   usage 三字段（`--subagent-tokens` / `--tool-uses` / `--duration-s`）**能观测多少填多少，观测不到就不填（落 null）**——flow-driver 跑主会话、整段 usage 取不到一个 usage 对象（见 §5）。BLOCKED 时 `--status blocked`，停下报告，不进下一段。
4. **停人闸**：若 `step.human_gate_after` 非 null（如 `after-req`），跑完本段后**停下**，向人汇报该段交付产物，等人确认再进下一 step。

### 3.4 段间 handoff：零新增

段间衔接**不新增任何机制**：上游 flow-driver 已在自己的交付节点 `handoff-write`（如 req-architect 在 `n8-merge` 写交接包），下游 flow-driver bootstrap 时按**同 slug** `handoff-read` 自动捡起（缺失则回退裸任务）。CEO 这层不写、不读 handoff，只负责按 `handoff_from` 顺序接力调 driver。

---

## §4 评审发函：CEO 不碰

评审 gate（reviewer-expert）的发函**完全由各 flow-driver 内部**按自己 node-table 的 `gate_specs.reviewer` 触发——到 review gate 时由 flow-driver 写 reviewer 请求 → dispatch `kdev-team:reviewer-orchestrator`（硬规：只派这一个 orchestrator，由它 fan-out 各 reviewer-cap）→ 读 verdict → `record-gate`。

🔴 **CEO 总编排这层不直接发任何评审函、不直接派任何 reviewer-cap**。评审是 flow-driver 段内的事，CEO 只在停人闸汇报里转述结果。

---

## §5 诚实债（必须对用户明示，不得越界宣称）

本 MVP 是 **L2→L3 human-in-loop 编排，不是自主 L3**。两笔账要对用户讲明白：

🔻 **诚实债 1：评审开关 per-gate 自动化引擎未建。**
确认屏上的 per-gate 专家/自评只是**意图展示**——没有 per-gate flow-config merge 引擎把"这一 gate 走专家、那一 gate 走自评"自动喂进各 flow-driver。当前评审开关只能：① 用 `/kdev-flow-driver` 的 `--review-mode {ai,both,human}` 三档做**段级**粗调；② per-gate 的细粒度切换靠**手改对应员工的 node-table**。**不要宣称 per-gate 评审自动化已工作。**

🔻 **诚实债 2：链级进度无断点续跑，崩了不可恢复。**
跨员工的链级状态（跑到第几 step、哪些段已完成）**只活在主会话内存里**——没有 `delivery-resume` cursor、没有链级断点续跑。主会话崩溃 / 换 session → 链级进度**不可恢复**（已落盘的 delivery-plan.yml 和 events.jsonl 还在，但要人工判断从哪段重起）。**因此本 MVP 不得宣称达 L3**（L3 要求无人值守可恢复的自主编排，本 MVP 不具备）。

> 注：单段 flow-driver 内部有自己的引擎断点续跑（resume 探断点），那是**段内**能力；这里说的"无断点续跑"指的是**链级**（跨段）层面。两者不要混为一谈、不要据段内能力宣称链级 L3。

---

## §6 HUD：自动渲染，零额外动作

delivery-plan.yml（§3.1 冻结写）+ dispatch 事件（§3.3 start/done append 进 `features/<slug>/events.jsonl`）落盘后，HUD **自动**多渲染出链级进度 + 派单流——CEO 这层不需要为 HUD 做任何额外动作：

```bash
python3 -m kdev_hud render
```

HUD 只读 `features/<slug>/` 下的文件、零写入、运行时不 import kdev_core（自包含、坏数据降级）；`delivery-plan.yml` 以 guarded `import yaml` 读，缺 PyYAML / 缺文件 / 坏行则降级。CEO 只管把数据按契约落到 `features/<slug>/`，渲染交给 HUD。

---

## 速查：本 skill 引用的真实 API / 命令（勿杜撰）

- `kdev_team.lifecycle`：`list_templates()` / `load_template(id)` / `TemplateError`
- `kdev_team.lint`：`validate(plan, staff=None) -> list[str]`（空=合法）
- `kdev_team.delivery_plan`：`parse(text)` / `structural_errors(plan)` / `write(workspace, plan)` / `read(workspace, slug)` / `path(workspace, slug)`
- `kdev_team.confirm`：`render_screen(plan, staff=None)` / `review_items(...)` / `apply_edit(plan, command)` / `EditError`
- `kdev_team.drive`：`build_sequence(plan) -> list[step]`（step 键：`stage_index`/`emp`/`flow`/`dispatch_id`/`handoff_from`/`driver_cmd`/`dispatch_start_cmd`/`dispatch_done_cmd`/`human_gate_after`）
- kdev-core CLI：`python3 -m kdev_core dispatch-start <flow> <slug> --emp <e> --dispatch-id <id> [--stage-index N] [--handoff-from <e@node>] [--workspace WS]`；`dispatch-done <flow> <slug> --emp <e> --dispatch-id <id> --status {done,blocked} [--subagent-tokens N] [--tool-uses N] [--duration-s N] [--workspace WS]`
- 命令：`/kdev-flow-driver <emp> --task <...> [--auto] [--slug <slug>]`（跑主会话）；`python3 -m kdev_hud render`
