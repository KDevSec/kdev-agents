---
name: kdev-flow-driver
description: 通用数字员工编排驱动循环——读 staff.yml 路由员工 → 读 node-table 驱动 kdev-core 引擎走 SOP（next-step → 派 agent / 判 gate → advance → 循环），直到 terminal 或 BLOCKED。Use when 用户说"用开发工程师跑 X"、"用 XX 员工跑这个任务"、"按 SOP 开发"、"自主跑完这个需求"、"用数字员工跑"，或 `/kdev-flow-driver dev-engineer --task "..." --auto`，或任何涉及"员工 × 任务 × 编排流程"的组合请求。也用于断点续跑（session 中断后恢复）和 BLOCKED 解除后重新推进。
---

# kdev-flow-driver：通用数字员工编排驱动循环

把"一个数字员工按自己的 SOP 走完一个任务"变成一条可自驱的循环。你（顶层主控）扮演编排角色，读员工的花名册（staff.yml）确定路由，读引擎状态（next-step）确定当前位置，然后逐节点推进——派业务 agent 执行动作、自己判断 gate、调 CLI 落账、循环直到终点。

## 为什么需要这个 skill

kdev-core 引擎能记账（R1/R2/R3），node-table 能定义节点图，agent .md 能定义人设——但三者之间没有运行时胶水。一个人类主控需要粘贴 ~60 行提示词才能手动描述整个流程。这个 skill 就是那段胶水：把引擎查询、agent 派单、gate 判断串成一个自动循环，让用户只需一句自然语言就能启动。

## 关键约束（贯穿整个循环）

1. **子 agent 不能再开子 agent**：这是 Claude Code 的硬限制。编排角色必须由顶层 session 扮演——你就是编排器，不要试图把编排下放给 dev-engineer-orchestrator agent 自跑。

2. **每个节点/gate 必须调 CLI 落账**：kdev-core 引擎是状态的唯一权威。跳过 CLI = 状态漂移 = 下次 resume 出错。这在循环中是自动化完成的，但你要确保不跳过。

3. **第三方评审 gate 阶段1 全 deferred**：reviewer-expert 的 gate（g-plan-review / g-code-review / g-sec-review）阶段1没有真人评审，直接记 `PASS --by deferred:阶段3-评审专家`，不冒充第三方。

4. **回流有界**：verify / e2e / deploy gate FAIL 后回流到 n6b 重做，最多重试 2 次（总共 3 次尝试），第 3 次引擎自动 escalate 为 blocked。blocked 时输出报告停住，不死循环。

5. **派 agent 时给足上下文**：每个业务 agent 拿到的 prompt 要包含——任务描述、当前节点目标、前序产物路径、UED/materials 等约束。不要只派一个空 prompt。

---

## 1. Bootstrap（从零启动）

用户给你任务描述 + 员工名（或通过 `/kdev-flow-driver` 命令传入参数）。你需要：

### 1.1 解析参数

```
/kdev-flow-driver <employee-id> --task <task-desc-or-path> [--auto] [--slug <slug>]
```

- `<employee-id>`：员工 canonical id（如 `dev-engineer`），从 staff.yml 反查
- `--task`：任务描述文本，或考题/需求文档的路径
- `--auto`：auto_mode=true，所有 gate 自决不停等用户确认
- `--slug`：flow slug（默认从任务描述自动生成一个 filesystem-safe 名称）

如果是自然语言触发（"用开发工程师跑这个考题"），从对话上下文推断 employee-id 和 task。

### 1.2 读 staff.yml 路由

```bash
# staff.yml 在框架仓的 kdev-team 里
FRAMEWORK_REPO=$(find ~ -maxdepth 3 -name "kdev-agents" -type d 2>/dev/null | head -1)
# 或从环境变量 / 已知路径获取
```

读 `$FRAMEWORK_REPO/plugins/kdev-team/staff.yml`，找到 employee 对应的：
- `node_table`：编排定义路径（相对于 kdev-team 目录）
- `agents`：可用业务 agent 列表
- `runtime_model`：推荐模型
- `flow_skill`：方法论参考（只作知识引用，不调用）

设定关键路径：
```bash
export PYTHONPATH=$FRAMEWORK_REPO/plugins/kdev-core
NT=$FRAMEWORK_REPO/plugins/kdev-team/<node_table 路径>
FLOW=$(python3 -c "import yaml; print(yaml.safe_load(open('$NT'))['flow'])")
```

### 1.3 探断点或初始化

```bash
# 先探有没有已存在的 flow
python3 -m kdev_core resume $FLOW <slug> --workspace <workspace>
```

- 如果 resume 成功 → 有断点，从 `current_node` 继续
- 如果 resume 报 "not resumable" 或 "no flow-state.json" → 初始化新 flow：
  ```bash
  python3 -m kdev_core init $FLOW <slug> --display-name "<任务名>" \
    [--auto-mode] --initial-node <第一个节点 id>
  ```
  第一个节点 id 从 node-table 的 nodes 列表找（通常是 `n0-env` 或类似）

- 如果 resume 报 "status=blocked" → 先 `unblock`：
  ```bash
  python3 -m kdev_core unblock $FLOW <slug> --to-node <想要回到的节点>
  ```

### 1.4 进入 Driving Loop

初始化/恢复完成后，进入下面的主循环。

---

## 2. Driving Loop（主循环）

每轮循环做一件事：**问引擎我在哪 → 判断该做什么 → 做完 → 推进到下一轮**。

```
LOOP:
  ┌─ 查询当前位置 ──────────────────────────────────────────┐
  │  python3 -m kdev_core next-step $FLOW <slug> --table $NT │
  └──────────────────────────────────────────────────────────┘
          │
          ▼
  ┌─ 判断 node_kind ─────────────────────────────────────────┐
  │                                                          │
  │  terminal → complete → 输出总结 → STOP                   │
  │                                                          │
  │  blocked → 输出 BLOCKED 报告 → STOP                      │
  │                                                          │
  │  action → 派业务 agent → advance → GOTO LOOP             │
  │                                                          │
  │  gate → 判断 gate → record-gate → GOTO LOOP              │
  │                                                          │
  └──────────────────────────────────────────────────────────┘
```

### 2.1 查询当前位置

```bash
python3 -m kdev_core next-step $FLOW <slug> --table $NT --workspace <workspace>
```

返回 JSON 含 `current_node`、`node_kind`、`node_name`、`next_actions`、`gate_spec`、`is_blocked`。这是你每轮唯一的决策依据。

### 2.2 terminal 节点 → 完结

```bash
python3 -m kdev_core complete $FLOW <slug> --workspace <workspace>
```

输出总结：列出 phase_history（经过的节点）、gate_calls（判断过的 gate）、最终状态。完结后 STOP——不再循环。

### 2.3 blocked 状态 → 停住报告

输出 BLOCKED 报告给用户：
- 哪个 gate escalate 的
- blocked_reason 内容
- 当前节点 id
- 建议：`kdev-core unblock $FLOW <slug> --to-node <建议节点>` 来恢复

STOP——等用户决定是否 unblock 后重新启动。

### 2.4 action 节点 → 派业务 agent（后台 + 文件交接）

从 `next_actions` 得到下一步节点 id，但当前 action 节点本身需要先完成工作。派单逻辑（B 轨：执行甩后台、决策留主控）：

1. **读 Node→Agent 路由表**（见 `references/node-agent-routing.md`）确定当前节点对应哪个 `subagent_type`
2. **算交接目录**：
   ```bash
   python3 -m kdev_core handoff-path $FLOW <slug> --employee <canonical-id> --workspace <workspace>
   # → .kdev/features/<slug>/handoffs/<员工>/
   ```
3. **构造派单上下文**（§4 模板）：prompt 里必含——任务描述、当前节点目标、前序产物路径、工作目录、相关约束（UED/原型图等），**末尾必含「完成后写交接文件」指令**（见 §2.4bis + §4 模板）
4. **后台派 agent**（🔴 `subagent_type` 必须是插件全名 `kdev-team:<agent-id>`，裸 id not-found——见 `references/node-agent-routing.md` 顶部「派单标识」；🔴 `run_in_background: true` 是 B 轨核心）：
   ```
   Agent({
     subagent_type: "kdev-team:dev-engineer-env",
     run_in_background: true,
     prompt: "<构造的上下文 + 写交接文件指令>"
   })
   ```
   `run_in_background: true` 让 subagent 的工具调用、内联渲染、大段 result 全在后台 sidechain，**不灌主会话**——这是 B 轨压掉"派单刷屏"的核心。runtime_model 按 staff.yml（当前阶段1统一 opus）。
5. **等完成通知 → 读交接文件**（不读 subagent 内联返回）：
   - 后台 agent 完成时主循环收到 **completion 通知**。
   - 读结构化状态：
     ```bash
     python3 -m kdev_core handoff-read $FLOW <slug> --employee <id> --node <current_node> --workspace <workspace>
     # → {node_id, employee, status, summary, artifacts, gate_input, reason}
     ```
   - `status=done` → 取 `artifacts` / `gate_input` 作下一步（gate）输入。
   - `status=blocked` / `needs_context` → **不 advance**，按 BLOCKED 处理（§2.3，或带 `reason` 升人）。
   - ⚠️ **可观测**：completion 通知 + 交接文件 `status` 双信号；`handoff-read` 报 `handoff status not found / unreadable`（FlowStateError）= 该节点没干完，**不静默 advance**——按未完成处理（重派或升人）。
6. **推进到下一节点**（仅 `status=done`）：
   ```bash
   python3 -m kdev_core advance $FLOW <slug> <to_node> --table $NT \
     --reason "<node_name> 完成" --workspace <workspace>
   ```
   `to_node` 取 `next_actions[0].to_node`（action 节点通常只有一个 next）

### 2.4bis 文件交接协议（B 轨核心，最小够用）

业务 agent **不把产出大段 result 回灌主会话**，而是写一个结构化状态文件，主循环读它。

- **路径**：`.kdev/features/<slug>/handoffs/<员工 canonical-id>/<node_id>.handoff.json`（目录由 kdev-core `handoff_dir` 约定，P-Core-FF 已建；**不自创新目录**）。
- **schema**（kdev-core `write_handoff_status` 落、`read_handoff_status` 校验）：

  | 字段 | 含义 |
  |---|---|
  | `node_id` | 当前节点 id |
  | `employee` | 员工 canonical id |
  | `status` | `done` / `blocked` / `needs_context` |
  | `summary` | 一句人话（必填） |
  | `artifacts` | 产物路径列表（可空） |
  | `gate_input` | 给下一 gate 的结构化信号，可 `null` |
  | `reason` | `status != done` 时必填 |

- **agent 怎么写**：派单 prompt 末尾注入指令（见 §4 模板），让 agent 收尾调 `kdev_core handoff-write ...`。
- **主循环怎么读**：`handoff-read`（见 §2.4 step 5）。
- **为什么文件而非 result 回灌**：result 回灌刷屏主会话（连 recorder 的机器块都被反馈嫌吵，见 MQ-1）；文件交接 = 主循环只读它要的几个字段，编排叙述清爽。**gate 判断仍在主循环**（B 轨守界：执行甩后台、决策留主控）。

### 2.4ter 跨员工 handoff（上游交付 → 下游 spec 输入）

§2.4bis 是**同一 flow 内**主循环↔业务 agent 的交接（按 `current_node` 读）。本段是**跨员工跨 flow**的交接：上游员工（如需求架构师 req-architect）design-flow 的交付，喂给下游员工（开发工程师 dev-engineer）coding-flow 的 spec/plan 输入。**机制纯复用 B 轨 `handoff-write`/`handoff-read`，不新增原语。**

**join 键 = 同一 feature slug。** 一个 feature 一个 slug：req-architect 在 slug X 上跑 design-flow、落产物到 `.kdev/features/X/handoffs/req-architect/`；dev-engineer 在**同一 slug X** 上跑 coding-flow，读这里当输入。

**生产方（上游）落交付 manifest**：在其**聚合/交付节点**收尾时调一次：

```bash
python3 -m kdev_core handoff-write design-flow <slug> --workspace <ws> \
  --employee req-architect --node n8-merge --status done \
  --summary "<一句话：交付了什么>" \
  --artifact .kdev/features/<slug>/handoffs/req-architect/sr.md \
  --artifact .kdev/features/<slug>/handoffs/req-architect/ar.md \
  --artifact .kdev/features/<slug>/handoffs/req-architect/prototype/ \
  --artifact .kdev/features/<slug>/handoffs/req-architect/design.md \
  --gate-input '{"sr":"<sr 路径>","ar":"<ar 路径>","prototype":"<prototype 路径>","design":"<design 路径>"}'
```
- `artifacts` = 产物路径列表（人/机都能顺着取）；`gate_input` = role→path 结构化指针（消费方按角色精确取 sr/ar/prototype/design）。

**生产方 → 交付节点映射**（消费方据此知道读哪个 `--node`）：

| 生产方（员工）| 交付节点 `--node` | 交付内容 |
|---|---|---|
| `req-architect` | `n8-merge` | SR / AR(迭代+用户故事) / 原型 / 方案 |

**消费方（下游）读上游交付**：下游员工在其入口节点按上表读**同 slug** 的上游交付：

```bash
python3 -m kdev_core handoff-read coding-flow <slug> --workspace <ws> \
  --employee req-architect --node n8-merge
# → {node_id, employee, status, summary, artifacts, gate_input, reason}
```
- `status=done` → 取 `gate_input` 的 role→path 指针 / `artifacts` 作下游 spec/plan 输入（dev-engineer n0-env 读 SR+背景；n3-plan 读 AR+方案切增量）。
- **上游缺失**（`handoff-read` 报 `handoff status not found` = FlowStateError）→ 该 slug 没有上游交付，**回退裸任务**：dev-engineer 按现状（clone+蒸馏 / 自己定增量）走，不阻断、不报错。

**为什么不另起原语**：B 轨 `write/read_handoff_status` 已是「谁产了啥+路径+状态」结构化指针，跨员工只是换 `employee`/`slug` join 维度，零扩展即覆盖（守「复用别重造」）。**gate 判断仍在主循环**（同 §2.4bis 边界：执行甩文件、决策留主控）。

### 2.5 gate 节点 → 判断

从 `next-step` 返回的 `gate_spec` 确定判断逻辑。四种情况：

#### a. reviewer=self + auto_mode=true → 自判

你（主控）根据 gate 判定逻辑（见 `references/gate-decision-logic.md`）自行判断 verdict，直接调 CLI：

```bash
python3 -m kdev_core record-gate $FLOW <slug> \
  --gate <gate_id> --kind <decision|review|acceptance> \
  --verdict <verdict_value> --request-id <current_node> \
  --table $NT --workspace <workspace>
```

- decision gate：verdict 取 `gate_spec.branches` 的某个 key
- review/acceptance gate：verdict 取 `PASS` 或 `FAIL`

#### b. reviewer=self + auto_mode=false → 自判 + 问用户确认

先按 a 的逻辑自判，但**停下来问用户确认**："我判断 g-xxx = Y，你确认吗？" 用户确认后才调 record-gate。

#### c. reviewer=reviewer-expert + stage1=deferred → 直接记 PASS

不需要判断，直接记 PASS 并标注 deferred：

```bash
python3 -m kdev_core record-gate $FLOW <slug> \
  --gate <gate_id> --kind review \
  --verdict PASS --request-id <current_node> \
  --by "deferred:阶段3-评审专家" \
  --table $NT --workspace <workspace>
```

#### d. reviewer=reviewer-expert + !deferred → 问用户

停下来问用户："这个第三方评审 gate 需要你的判断，PASS 还是 FAIL？" 用户给出 verdict 后调 record-gate。

### 2.6 回到 LOOP

record-gate 或 advance 完成后，回到 2.1 重新查询 next-step，开始下一轮。

---

## 3. 特殊场景处理

### 3.1 断点续跑（session 中断恢复）

如果 session 中断了，下次新 session 里用户说"继续上次的工作"：

```bash
python3 -m kdev_core resume $FLOW <slug> --workspace <workspace>
```

从 `current_node` 继续，进入 Driving Loop。不需要重新 init。

### 3.2 BLOCKED 解除

```bash
python3 -m kdev_core unblock $FLOW <slug> --to-node <回到哪个节点>
```

然后重新进入 Driving Loop。建议 `--to-node` 设为回流目标节点（如 n6b），而不是停在原来 escalate 的 gate 节点。

### 3.3 增量 vs 实现工序（别踩 G-005 的坑）

**先分清两件事**（详见 `references/gate-decision-logic.md` 顶部）：

- **增量 = 能独立过 e2e 的纵向切片**（如"购物车""支付"各自可独立验收）→ 走 g-increment 循环
- **实现工序 = 一个增量内部的横向分层**（如 T0 主题 → T1 登录 → T2 仪表盘，是一套视觉系统的分层）→ 在**单个 n6b 节点内部**做完，可多次派 frontend 分批建，**中间不跑 gate 链**

**两种循环别混**：

| 想干什么 | 走哪条路 |
|---|---|
| 一个增量内部分批写代码（T0→T4） | n6b 内部多次派 frontend，**不经过 gate** |
| 一个增量没做好要重做 | g-verify/g-e2e **FAIL 回流** → n6b |
| 这个增量过了 e2e，做下一个纵向切片 | g-e2e PASS → **g-increment more** → n6b |
| 所有增量都过了 e2e | g-increment **done** → 收尾链（n10→n11→n12，跑一次） |

**关键**：考题列的 T0/T1/T2/T3/T4 是**实现工序不是增量**——UED 视觉改造整体就是 **1 个增量**（N=1），T0-T4 在 n6b 内部一次做完，e2e PASS 后 g-increment 直接判 `done` 进收尾。**绝不要把 T0-T4 当 4 个增量去 g-increment more 循环，更不要用 g-deploy FAIL 当增量切换**（那是被根治掉的旧 bug）。

### 3.4 n6a vs n6b 选择

g-complexity gate 判断：
- `simple` → n6a-impl-inline（主控直接实现，不派 subagent）
- `complex` → n6b-impl-subagent（派 `kdev-team:dev-engineer-frontend` subagent）

绝大多数视觉改造考题是 `complex`，走 n6b。

---

## 4. 上下文构造模板

派业务 agent 时，用这个模板构造 prompt：

```
你是 <agent 中文名>（<agent canonical id>），当前在 coding-flow 的 <node_id> 节点（<node_name>）。

## 任务
<--task 参数的内容，或从文件读取的考题/需求描述>

## 当前节点目标
<从 node-table 和 agent 人设文档中提取的该节点职责描述>

## 前序产物（已存在）
- env.md: <路径>
- rules.md: <路径>
- PLAN.md: <路径>
- ...

## 约束
- UED 规范：<materials_path>/AGENTS.md
- 设计 token：<materials_path>/design-tokens.json
- 原型图：<materials_path>/01-pic/login.png 等
- ...

## 工作目录
<workspace 路径>
```

派 agent 时，在上面模板**末尾追加**下面这段「写交接文件」指令（B 轨文件交接，REQUIRED）：

```
## 完成后写交接文件（REQUIRED）

完成本节点工作后，你【必须】把结构化状态写到交接文件（**不要**把大段产出回灌——产出落 artifacts，主控只读交接文件）：

PYTHONPATH=<FRAMEWORK_REPO>/plugins/kdev-core python3 -m kdev_core handoff-write <flow> <slug> \
  --employee <你的 canonical id> --node <当前 node_id> \
  --status done \
  --summary "<一句话：这步干完了什么>" \
  --artifact <产物路径> [--artifact <更多产物>] \
  [--gate-input '<给下一 gate 的 JSON，如 {"build":"pass","lint":"clean"}>'] \
  --workspace <workspace>

若未完成 / 被阻塞：把 --status 改成 blocked（或 needs_context）并加 --reason "<为什么>"。

你的 final message 只回一句话确认（如"n3-plan 完成，详见交接文件"）——详情在交接文件 + artifacts 里，**不要长篇回灌**。
```

（主控构造 prompt 时把 `<FRAMEWORK_REPO>` / `<flow>` / `<slug>` / `<node_id>` / `<canonical id>` / `<workspace>` 全部替换成实际值再派单。）

---

## 5. CLI 快查

所有 kdev-core CLI 子命令（`--workspace` 默认 cwd，可省略）：

| 命令 | 用途 | 关键参数 |
|---|---|---|
| `init` | 初始化新 flow | `--display-name`, `--auto-mode`, `--initial-node` |
| `resume` | 探断点续跑 | 无 |
| `next-step` | 查询当前位置+可选动作 | `--table` |
| `advance` | 推进到下一节点 | `to_node`, `--table`, `--reason` |
| `record-gate` | 记录 gate 判断 | `--gate`, `--kind`, `--verdict`, `--request-id`, `--table`, `--by` |
| `complete` | 终结 flow | `--status completed|aborted` |
| `unblock` | 解除 blocked | `--to-node` |
| `list-flows` | 列出所有 flow | 无 |
| `gate-lookup` | 查当前 gate spec | `--table` |
| `show` | 看当前完整状态 | 无 |

gate verdict 规则：
- decision：取 `branches` 的 key（如 `high`/`low`、`simple`/`complex`）
- review/acceptance：`PASS` 或 `FAIL`

---

## 参考文件

本 skill 有两个 reference 文件，按需读取：

- **`references/node-agent-routing.md`**：Node→Agent 路由表——每个 action 节点对应哪个 subagent_type、需要传什么上下文。派单前读这个文件确定该派谁。
- **`references/gate-decision-logic.md`**：Gate 判定逻辑——每个 self-review gate 的具体判据。到 gate 节点时读这个文件确定怎么判。