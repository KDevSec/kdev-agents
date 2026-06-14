# 决策：reviewer 回函 schema 与 handoff CLI reader 契约混用（Q 候选 2 / G 候选 3）

- 日期：2026-06-14
- 分支：`fix/reviewer-handoff-contract`
- 上游评审：`docs/superpowers/reviews/2026-06-14-四插件整体架构接缝评审.md`（Q 候选 2 🔴 + G 候选 3 🟡）
- 决策人：主控（opus），用户事后审

## 问题（独立复核已确认）

kdev handoff 机制现"一机三用"：

| 用法 | 生产方 | 机制 | schema | 状态 |
|---|---|---|---|---|
| (a) intra-flow 主循环↔业务 agent | flow-owner 节点（持 node_id）| CLI `handoff-write/read` | `node_id/employee/status/summary[/artifacts/gate_input/reason]` | 健康 |
| (b) P-B 跨员工交付 | flow-owner n8-merge（持 node_id）| CLI `handoff-write/read` | 同上 | 健康 |
| (c) reviewer 发函回函 | **callee（无 flow-state、无 node_id）** | **裸 `Write`/`Read`** | `{verdict,scores,counts,revisions,by,request_id}` | **混用（本次修）** |

证据：
- reviewer 裸 Write 产 `handoffs/reviewer/<gate>.handoff.json` —— `plugins/kdev-team/agents/reviewer-orchestrator.md:29`，缺 `node_id/employee/status/summary` 四键。
- CLI reader 硬要求那四键 + `status∈{done,blocked,needs_context}` —— `plugins/kdev-core/kdev_core/flow_state.py:440-460`，缺任一 raise `FlowStateError`。
- 但文档让 caller 走 CLI 读它：`reviewer-orchestrator.md:35` / `SKILL.md:291` / `gate-decision-logic.md:135` / `node-agent-routing.md:190` 都写 caller `handoff-read` 取 `<gate>.handoff.json` 的 verdict → 真走 CLI 必 `FlowStateError: missing required key 'node_id'`。
  - 对称还有 **request 读**：`gate-decision-logic.md:132` / `node-agent-routing.md:188` 把 reviewer 读自己的 `<gate>.request.json`（同样裸文件、自定义 schema）也写成 `handoff-read` —— 同一处混用。
- `plugins/kdev-team/tests/test_reviewer_wiring.py` 不覆盖该读取路径（假绿）。

## 二选一与裁定

- **方案 A**：reviewer 回函改走 CLI `handoff-write`（verdict 塞 `gate_input`，`status=done`），caller `handoff-read` 取 `data['gate_input']['verdict']`。
- **方案 B（采纳）**：显式承认 reviewer 回函是"裸文件交接"（与 CLI `handoff-*` 平级、不同物），文档 CLI 动词 `handoff-read` 改普通 `Read <gate>.handoff.json`，caller 实现用 `Read`。

**裁定 = 方案 B（并扩到对称的 request 读 + 补契约注 + 补契约测试）。** 三条判据同向：

1. **真实调用语义**：设计反复钉死 reviewer 是 callee，**不持 flow-state、不碰 kdev-core 状态机**（`reviewer-orchestrator.md:11/35`、`SKILL.md:261`）。方案 A 反而逼 callee 去调 `kdev_core handoff-write`（一个 kdev-core flow-state CLI 操作）——**违背 callee 本身的核心原则**。`handoffs/reviewer/<gate>.*`（request / score.md / arbitration.md / handoff.json）整族本就是 reviewer 裸 `Write`/`Read` 的自定义 schema 文件，回函只是其一。
2. **"复用 CLI 强校验"是伪命题**：CLI 校验的是 **flow 信封**（node_id/employee/status/summary），**不是**评审 schema（verdict/counts）。方案 A 校验错了对象，且 `status=done` 沦为恒量、verdict 被埋进 `gate_input` 嵌套。verdict(PASS/FAIL) 与 status(done/blocked/needs_context) 是**正交两轴**（评审"做完了"但 verdict=FAIL 是常态），强塞一处是语义异味。
3. **改动面 + 不破坏两用契约**：方案 B 不动**任何** Python 生产代码、不动 CLI / flow-schema —— intra-flow(a) 与 P-B(b) 完全不受影响。方案 A 会让 `handoff-read --employee reviewer` 变"合法"但返回信封包裹的 verdict，**污染前两用的心智模型**。

**方案 B 唯一弱点**（少一层 CLI 运行时强校验）的兜底：
- 补**契约行为测试**：同一份裸回函喂 `json.load` 能取 `verdict`，喂 `read_handoff_status` 必 `FlowStateError`（钉死"两者不同物"+ 防回归方案 A）。
- 补**契约注**（`node-agent-routing.md`「reviewer 发函 dispatch」段）：明示 `handoffs/reviewer/` 是裸文件交接、**不可用 `kdev_core handoff-read`**；CLI `handoff-write/read` 仅服务 (a)/(b)。

**未做 rename**（保留文件名 `<gate>.handoff.json`）：用户 Option B 原话即"把 CLI 动词改普通 Read `<gate>.handoff.json`"，文件名沿用；`.handoff.json` 后缀与 CLI 文件同名的潜在撞车风险，靠契约注 + 契约测试（喂 CLI reader 必失败）显式拦住，无需更大改面。

## G 候选 3 一并修（同接缝悬空指令）

`reviewer-orchestrator.md:55` 原"发现两能力相反结论 → 在 caller `events.jsonl` 留痕（标元评审异常）"——reviewer 是 callee、不碰 kdev-core 状态机、core 也无 anomaly 事件类型，**无落地通道、悬空**。

改为：异常写进 reviewer 本就产出的 `handoffs/reviewer/<gate>.arbitration.md` + 回函结构化 `anomaly` 字段；**由 caller 决定**是否转 kdev-core 事件（caller 持 `events.jsonl`，callee 不碰）。回函 schema 增 `anomaly` 可选字段。

## 改动清单

- 文档（kdev-team）：`reviewer-orchestrator.md`、`skills/kdev-flow-driver/SKILL.md`、`.../references/gate-decision-logic.md`、`.../references/node-agent-routing.md`、`agents/dev-engineer-orchestrator.md` —— reviewer 回函/请求读改 `Read`、加契约注、回函 schema 加 `anomaly`、修 G 候选 3 anomaly 通道。
- 测试：`plugins/kdev-team/tests/test_reviewer_wiring.py` —— 加契约行为测试 + 文档一致性测试 + G 候选 3 测试。
- 版本（G-004）：kdev-team `0.8.0 → 0.8.1` + CHANGELOG。
- kdev-core：**零改**（守"复用别重造"反向——本次是"别把不该进 CLI 的塞进 CLI"）。
