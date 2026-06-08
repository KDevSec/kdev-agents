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

### 2.4 action 节点 → 派业务 agent

从 `next_actions` 得到下一步节点 id，但当前 action 节点本身需要先完成工作。派单逻辑：

1. **读 Node→Agent 路由表**（见 `references/node-agent-routing.md`）确定当前节点对应哪个 `subagent_type`
2. **构造派单上下文**：给 agent 的 prompt 里必须包含：
   - 任务描述（`--task` 参数的内容，或从考题文件读取）
   - 当前节点目标（node_name + 在 SOP 中的位置说明）
   - 前序产物路径（如 env.md / rules.md / PLAN.md 的位置）
   - 工作目录 / 项目路径
   - 相关约束（UED 规范路径、原型图路径等）
3. **派 agent**：
   ```
   Agent({subagent_type: "dev-engineer-env", prompt: "<构造的上下文>"})
   ```
   runtime_model 按 staff.yml 的设定选（当前阶段1统一 opus）
4. **等 agent 返回**，检查结果是否合理
5. **推进到下一节点**：
   ```bash
   python3 -m kdev_core advance $FLOW <slug> <to_node> --table $NT \
     --reason "<node_name> 完成" --workspace <workspace>
   ```
   `to_node` 取 `next_actions[0].to_node`（action 节点通常只有一个 next）

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

### 3.3 多轮实现（frontend 需要多 increment）

考题有 T0→T1→T2→T3 四个大任务，一轮 dev-engineer-frontend 做不完。处理方式：

- n6b 节点每次派单给 frontend agent 时，明确告诉它"这一轮做哪个 increment"（如"先做 T0 全局布局 + T1 登录页"）
- 前一轮完成 → n8-verify → n9a → n9b-e2e → 回到 n6b 做下一 increment
- 这是 SOP 的正常回流路径，引擎自动处理

### 3.4 n6a vs n6b 选择

g-complexity gate 判断：
- `simple` → n6a-impl-inline（主控直接实现，不派 subagent）
- `complex` → n6b-impl-subagent（派 dev-engineer-frontend subagent）

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