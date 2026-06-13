# 评审专家(reviewer) 活体接线 · 轻 dogfood 验证记录

| 项 | 值 |
|---|---|
| 文档性质 | dogfood 验证留证（对 [评审专家接入设计 v0.2 §11 轻 dogfood](./2026-06-12-评审专家reviewer接入设计-design.md) 的兑现）|
| 日期 | 2026-06-13 |
| 分支 | `feat/l3-review-dogfood`（worktree）|
| 被测 | kdev-team v0.6.0 已激活（reviewer-* agent 可派单）|
| 范围 | 跑通**一条真实 review gate**：req-architect `g-sr-review` → 发函 `kdev-team:reviewer-sr` → 百分制评分表 → caller 双重条件判 gate → 真 `record-gate` |
| workspace | 临时 `/tmp/l3-review-dogfood-ws`（不污染真实 `.kdev` store，验毕可删）|

---

## 1. 验证目标（spec §11 轻 dogfood + 任务 #3/#4）

1. req-architect flow 到 `g-sr-review` → 发函 `reviewer-sr` → reviewer-sr 读 SR 产物出百分制评分表。
2. gate 按**双重通过条件**（总分≥阈值 AND 阻断性 🔴=0）判定。
3. 验证 reviewer **callee 不 own flow**、只被调用产评分；评分**落对位置**；caller gate **正确消费**。

---

## 2. 执行步骤（真实 kdev-core 引擎 + 真实 reviewer-sr agent）

| # | 动作 | 命令/产物 |
|---|---|---|
| 1 | init design-flow + 起 run 到入口节点 | `kdev_core init design-flow sr-demo --initial-node n0-clarify --auto-mode --review-mode ai` |
| 2 | 落 SR 产物（模拟 req-architect n1-spec 产出）| `handoffs/req-architect/sr.md`（34 行：看板「截止提醒」MVP，FR-1~5 / NFR-1~2 / AC-1~4）|
| 3 | advance 动作节点到 gate | `advance … n1-spec` → `advance … n2-sr-review` |
| 4 | `next-step` 确认到达 gate | `current_node=n2-sr-review, kind=gate, gate_spec.reviewer=reviewer-expert, gate=g-sr-review` ✅ |
| 5 | caller 写发函 request | `handoffs/reviewer/g-sr-review.request.json`（target_paths/caps[sr]/thresholds{sr:80}/request_id=n2-sr-review/caller=req-architect）|
| 6 | **发函真实 `kdev-team:reviewer-sr`**（callee）| agent 读 sr.md + `standards/reviewer/SR需求评审.md` → 出评分表 |
| 7 | reviewer 写评分表 | `handoffs/reviewer/g-sr-review.sr.score.md`（spec §4.2 schema）|
| 8 | caller 消费 verdict → 真 `record-gate` | `record-gate … --gate g-sr-review --kind review --verdict PASS --request-id n2-sr-review --by reviewer-expert` |
| 9 | `next-step` 确认 gate advance | `current_node=n3-decompose`（= gate_spec.on_pass）✅ |

---

## 3. 关键证据

### 3.1 评分表（reviewer-sr 真实产出，节选）

```yaml
cap: sr
target: .kdev/features/sr-demo/handoffs/req-architect/sr.md
total: 84/100
dimensions:
  - {name: 完整性,   score: 23/25}
  - {name: 清晰性,   score: 20/25}
  - {name: 可验收性, score: 19/25}
  - {name: 方向对齐, score: 22/25}
verdict: PASS        # total 84≥80 AND 🔴=0 → PASS
```
- 问题计数：🔴×0 · 🟡×3 · ⚪×3（🟡：FR-2 自定义节奏未规格化 / NFR-2 无可测 AC / FR-5 删除路径无 AC）。
- reviewer-sr **机械推出 verdict**：明确评估双重条件两臂（`total 84≥80` AND `🔴阻断=0`）→ PASS。

### 3.2 双重通过条件兑现

- ✅ 总分臂：84 ≥ 阈值 80。
- ✅ 阻断臂：🔴=0。
- 两臂 AND → PASS。（reviewer-sr 在评分表内显式写出条件推导，非主观拍。）

### 3.3 callee 不 own flow（核心契约）

- 全 workspace 仅 1 个 `flow-state.json` = **caller** 的 `features/sr-demo/flow-state.json`；reviewer **未写任何 flow-state**、无自有 feature/flow 目录。
- reviewer 产物只落 `handoffs/reviewer/`（request + score），与 caller 的 `handoffs/req-architect/` 平级、不混。
- `sr.md` 评后仍 34 行**原样未改**（只读隔离：修复是 req-architect 的事）。

### 3.4 caller 正确消费 + 入账归 caller

最终 flow-state：
```json
{"current_node": "n3-decompose", "gate_calls": 1, "gate_iters": {"g-sr-review": 0}}
```
gate 事件（`by=reviewer-expert`，入账由 caller 调 `record-gate`，reviewer 不碰状态机）：
```json
{"type": "gate", "actor": "reviewer-expert", "gate": "g-sr-review", "kind": "review",
 "verdict": "PASS", "by": "reviewer-expert", "request_id": "n2-sr-review"}
```
gate advance 到 `on_pass`（n3-decompose）= node-table `g-sr-review.on_pass` 一致。✅

---

## 4. 结论

✅ **评审专家 callee 活体接线跑通**：真实 review gate（req `g-sr-review`）发函真实 `reviewer-sr`，出百分制评分表（84/100，双重条件 PASS），caller 用真 `record-gate --by reviewer-expert` 入账并 advance。callee 不 own flow、评分落对位置、caller 正确消费三项契约全部成立。

## 5. 边界/限制（已记，非阻断）

- **recall 不可用**：subagent 环境无 recall 工具，reviewer-sr 跳过 `subject:review:sr` 历史尺度校准、按 standards 静态打分（已在评分表注明）。后续若需历史校准，需让 reviewer cap agent 能触达 recall（hook 或 CLI 形式）。
- **ir.md 缺失**：dogfood 跳过 clarify 阶段，方向对齐维度以 sr.md 头部「来源 IR」摘要作锚点，存在 IR 硬约束盲区——非接线缺陷，仅 dogfood 取样简化。
- **单 cap 路径**：`g-sr-review` 是单能力 gate，本次 fan-out 退化为 1 个 cap；多能力聚合/仲裁（`g-ar-proto-review` story+prototype）与 reviewer-orchestrator 嵌套 fan-out（受「子 agent 不能再开子 agent」约束）未在本轮覆盖，留后续 dogfood。本轮顶层 session 扮演单 cap 编排聚合角色（符合 kdev-flow-driver 关键约束 1：编排角色由顶层 session 扮演）。
