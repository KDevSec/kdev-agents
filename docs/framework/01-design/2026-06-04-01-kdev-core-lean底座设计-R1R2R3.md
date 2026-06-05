# kdev-core lean 底座设计 — R1 状态机 / R2 节点机 / R3 三类 gate 统一抽象

| 项 | 值 |
|---|---|
| 文档状态 | **DESIGN DRAFT v0.1 — 可实施级（R1/R2/R3）** |
| 日期 | 2026-06-04 |
| 范围 | 只设计 lean 底座的三块（[Q-007] C-3~C-5 最缺）：R1 flow-state 泛化 / R2 通用节点状态机 / **R3 三类 gate 统一抽象**。R4–R7 暂不展开 |
| 依据 | [C-1 现状盘点](./2026-06-03-02-底座R1-R7现状盘点-flows差异表.md)（从 design-flow/coding-flow 反推） |
| 关联 | [Q-007 底座决策](../../.kdev/memory/决策日志.md) · [详细设计 v0.2 §0.1](./2026-05-28-03-kdev-core-v0.1-详细设计.md) |

---

## 0. 核心范围约定（守 lean / L2）

底座**只管状态机 + 闸门记账 + 节点流转**，**不做判断本身**（AI 评审 / E2E 跑测 / 路线决策都在 flow 侧执行，由 AI prompt 或人完成）——执行完把**结果**喂给底座，底座据此**记录 + 解析下一节点**。

> 这条边界保证底座 lean、语言模型无关，且复用现有 `review-gate-prompt.md` 等 prompt 资产。

---

## 1. R1 — flow-state 泛化（金种子来自 `flow_state.py`）

把 design-flow 的 `lib/flow_state.py` 从 4-段写死泛化成 **flow-agnostic**。

### 1.1 Schema

```json
{
  "flow": "design-flow",            // 哪个数字员工 flow
  "slug": "user-auth",
  "display_name": "用户登录鉴权",
  "status": "in_progress",          // in_progress | completed | aborted
  "active": true,                   // [OMC借鉴] stale guard：crash 时写 false 而非删，resume 据此判
  "current_node": "n3-prototype",   // 节点 id（字符串，不再写死 int）
  "created_at": "2026-06-04T..Z",
  "updated_at": "2026-06-04T..Z",
  "config": { "review_mode": "ai", "auto_mode": false },   // flow 私有配置
  "history": [                       // R3 闸门结果流水（见 §3.4）
    { "node": "n1-sr", "gate": "g-sr", "kind": "review",
      "iter": 1, "verdict": "FAIL", "by": "ai", "ts": "..." },
    { "node": "n1-sr", "gate": "g-sr", "kind": "review",
      "iter": 2, "verdict": "PASS", "by": "ai", "ts": "..." }
  ]
}
```

### 1.2 路径 + 原子写（沿用金种子）

- 路径：`.kdev/flows/<flow>/<slug>/flow-state.json`（原 `.kdev/design-flow/<slug>/` 泛化）
- 写：tmp + `os.replace` 原子写（**直接搬 flow_state.py 第 71-85 行**）
- 读不存在/损坏 → `FlowStateError`（搬）

### 1.3 API（`kdev_core/flow_state.py`）

```python
def init(flow, slug, *, display_name, node_table, config=None) -> dict   # 校验 slug 唯一
def read(flow, slug) -> dict                                             # 不存在抛 FlowStateError
def write(flow, slug, state) -> None                                     # 原子写 + 刷 updated_at
def advance(flow, slug, to_node) -> dict                                 # R2：移动 current_node（带校验）
def record_gate(flow, slug, gate_result) -> dict                         # R3：history.append + 解析流转
```

> coding-flow 接上 R1 = **白捡 resume**（它现在没有）。

---

## 2. R2 — 通用 n 节点状态机（节点表由 flow 声明）

不写死段数（design 4 / coding 13）。每个 flow 声明一张**节点表**，底座提供流转引擎。

### 2.1 节点表 Schema（flow 静态声明）

```yaml
# 各 flow 自带（如 design-flow/node-table.yml）
flow: design-flow
nodes:
  - { id: n1-sr,        name: SR 需求,   kind: action, gate: g-sr }
  - { id: n2-ar,        name: AR 拆解,   kind: action, gate: g-ar }
  - { id: n3-prototype, name: 高保真原型, kind: action, gate: g-proto }
  - { id: n4-design,    name: 概要+详设, kind: action, gate: g-design }
gates: [ ...见 §3... ]
```

- `kind: action` = 产出动作（产出后过 `gate`）；`kind: gate` = 纯判断点（如 coding Gate-A 关联度，无产物）。
- coding-flow 同样声明 13 节点（节点 1/5/9 带 gate，其余 action）。

### 2.2 流转引擎

```python
def advance(flow, slug, to_node):
    # 校验 to_node ∈ node_table；只能 顺进 或 gate 指定的回流目标
    ...
```

- **顺进**：action 节点过 gate=PASS → current_node = 下一节点。
- **回流**：gate=FAIL → current_node = gate.on_fail（如 coding Gate-C FAIL → 回流 n7-tdd）。

> **[OMC借鉴] advance 三段式（照 Team Pipeline `transitions.ts`）**：① 邻接表查 `ALLOWED[from]→[to]` 合法性 → ② 守卫 `guard(state)→str|null`（null 过 / 非 null 是拒因，与边解耦）→ ③ 不可变变更 + 原子写 + 追加 `phase_history`。
> **有界回流 + 幂等豁免**：gate 回流（gate→同 action）须**显式标"回流"= retry++**（非幂等重入，否则计数失效）；retry 溢出 `max_retries` → 强制 advance 到 terminal-fail，禁无限回流。
- 全部节点 done + 末节点 gate PASS → `status=completed`。

---

## 3. R3 — 三类 gate 统一抽象（核心难点）

C-1 发现 gate 有三类。**统一为一个 Gate schema + 一个 GateResult + 一套解析逻辑**，三类靠 `kind` 区分。

### 3.1 三类 gate 本质

| kind | 谁评 | verdict | 不过怎么办 | 来源 |
|---|---|---|---|---|
| **review**（评审重试）| ai / both / human | PASS / FAIL | 改 → 重试（max N iter）| design-flow 4 闸门 |
| **decision**（路线判断）| **ai 默认 / human 编排可接管** | 分支选择（如 高/低）| 无重试，选分支即流转 | coding Gate-A/B |
| **acceptance**（验收）| test（自动跑 E2E）| PASS / FAIL | 回流 fix 节点 | coding Gate-C / Per-Increment E2E |

### 3.1.1 「谁来判」= 编排可覆盖的统一旋钮

每类 gate 的"谁来判"都是**编排可配旋钮，默认 AI/自动，人按需接管**——人有最终决定权，但默认不挡路：

| kind | 默认 | 编排可改 |
|---|---|---|
| review | ai | both / human |
| **decision** | **ai** | **human（指定岔路口人接管）** |
| acceptance | test（自动跑） | + human 复核 |

- **理由**：关联度/复杂度这类判断，AI 往往判得不比人差、甚至更稳；**默认 AI 决策、不停顿**，人只在自己想掌控的岔路口（编排标 `decider: human`）才介入。
- **Auto Mode 联动**：自主推进时**只在 `decider: human` 的 gate 停靠**交还给人，其余 AI 自己过——**哪里停由编排决定**（不再写死 coding 的"3 个 Gate 必停"）。
- **跟自主度挂钩**：低自主默认多挂 human，高自主（L4 自治）默认全 AI。

### 3.2 Gate Schema（统一，flow 声明）

```yaml
gates:
  # ① review 型
  - id: g-sr
    kind: review
    reviewer: ai            # ai | both | human（取自 config.review_mode）
    max_retries: 3
    criteria_ref: references/stage1-sr-criteria.md   # 成功标准（复用现有 prompt 资产）
    on_pass: "@next"        # 下一节点
    on_fail: "@self"        # 回流本节点改（默认）

  # ② decision 型
  - id: g-a-relevance
    kind: decision
    decider: ai            # 默认 ai 决策；编排时可改 human 接管该岔路口（Auto Mode 仅在 human 处停靠）
    branches:
      - { choice: "高", next: n2-single-branch }
      - { choice: "低", next: n2-worktree }

  # ③ acceptance 型
  - id: g-c-e2e
    kind: acceptance
    runner: e2e             # 自动跑（flow 提供跑法）
    pass_rule: "100% PASS"
    max_retries: 3          # 可选；超限升级人工
    on_pass: "@next"
    on_fail: n7-tdd         # 回流 fix
```

### 3.3 GateResult（flow 执行完喂给底座）

```json
{
  "gate": "g-sr", "kind": "review", "node": "n1-sr",
  "request_id": "uuid-…",             // [OMC借鉴] approval 锁：approval 须携匹配 uuid，防跨轮串扰
  "iter": 2,                          // review/acceptance 用；decision 省
  "verdict": "PASS",                  // review/acceptance: PASS|FAIL；decision: 分支 choice 字符串
  "by": "ai",                         // ai|both|human|test
  "issues": [], "revisions": [],      // review FAIL 时（来自 review-gate-prompt.md 输出）
  "ts": "..."
}
```

### 3.4 解析逻辑（`record_gate` 内，三类统一）

```
record_gate(flow, slug, result):
    state.history.append(result)
    gate = node_table.gate(result.gate)
    match gate.kind:
        review | acceptance:
            if result.verdict == PASS:  next = gate.on_pass
            else:
                if result.iter >= gate.max_retries:  next = ESCALATE(升级人工/CEO)
                else:                                 next = gate.on_fail   # 回流改/fix
        decision:
            next = gate.branches[result.verdict].next                       # 按选择分支
    advance(flow, slug, resolve(next))     # @next/@self 解析成具体节点
```

> **三类共用** history 记录 + next_node 解析；差异只在 verdict 语义（PASS/FAIL vs 分支）+ 是否重试。**这就是统一抽象成立的关键**。

### 3.5 验证：两个 flow 都能用此抽象表达

| flow 现有 gate | 映射 |
|---|---|
| design-flow 4 评审闸门（ai/both/human×3）| 4 个 `kind: review` gate，reviewer 取 config.review_mode |
| coding Gate-A 关联度（高/低）| `kind: decision`，branches 高→单分支 / 低→worktree |
| coding Gate-B 复杂度（简单/复杂）| `kind: decision`，branches 简单→主控 / 复杂→subagent |
| coding Gate-C E2E 通行证（100% PASS）| `kind: acceptance`，runner=e2e，on_fail=回流 n7 |
| coding Per-Increment E2E | 同上，每增量一次 |

✅ 三类抽象**装下了两个 flow 的全部 gate**——抽象成立。

### 3.6 编排 = 可配的 SOP（三层覆盖 + 自演进预留）

R2 节点表 + R3 gates 合起来 = **一个 flow 的 SOP**。这套 SOP **不写死、可编排**，分三层覆盖：

| 层 | 谁编排 | 位置 | 时机 | 改什么 |
|---|---|---|---|---|
| **L0 默认** | flow 作者（我们）| flow 内 `node-table.yml` | ship | 默认 SOP（我们这套节点表 + gates）|
| **L1 用户编排** | 用户 | `.kdev/flows/<flow>/orchestration.yml` | 安装 / 项目初始化 | override：开关 gate · `decider` ai↔human · retry 数 · 跳过/重排节点 |
| **L2 自主编排**（未来）| 数字员工自己 | 同上（employee 写）| 运行中 / 自演进 | 基于经验提议 SOP 优化 |

- **底座加载有效 SOP = merge(L0 默认, L1 用户, [L2 自主])**；R2/R3 都吃这份合并后的配置。`§3.1.1` 的「谁来判」旋钮就是 L1 编排的一个子项。
- **编排方法必须文档化**（用户要求"告知编排的方法"）：每个 flow 配一份**编排指南**，说明 `orchestration.yml` 能改什么、怎么改、改了的后果（哪些 gate 可关、关了的风险）。
- **L2 自主编排 = L4 自治 / 自演进**：概念模型 ③ 持续升级飞轮**不止反哺"能力"，也反哺"SOP 本身"**——员工跑多了，发现某 gate 总是白过、某节点顺序更优 → **提议改 SOP**。**当前 L2 不实施，设计预留挂钩**：`orchestration.yml` 每项留 `source: default|user|self` 标记，self 变更需人确认（守"人有最终决定权"）。
- **跟自主度挂钩**：L1–L2 = 默认 + 用户编排（人配）；L3–L4 = 数字员工自主编排/优化（自演进）。

---

## 4. 落地（对应详细设计 §7）

| 步 | 内容 | 产物 |
|---|---|---|
| **C-3 / R1** | 泛化 `flow_state.py` → `kdev_core/flow_state.py`（+ 搬单测）| flow-agnostic 状态机 |
| **C-4 / R2** | 节点表 loader（**merge L0 默认 + L1 用户 `orchestration.yml`**）+ `advance` 流转引擎 + 单测 | 通用 n 节点机 + 用户可编排 |
| **C-5 / R3** | Gate schema 校验 + `record_gate` 三类解析 + 单测（三类各一例）| 统一闸门引擎 |
| **C-6 改造** | design-flow 声明 node-table.yml + 改调底座；coding-flow 同（白捡 R1 resume）| dogfood 验证 |
| **C-7 编排指南** | 每个 flow 配「编排指南」文档：orchestration.yml 能改什么/怎么改/风险 | 告知用户编排方法 |

**测试基线**：R1 原子写/损坏恢复；R2 顺进/回流/完成；R3 三类各一条 PASS + 一条 FAIL/分支 + 重试超限升级。

---

## 5. 待用户拍板

| # | 决策 | 倾向 |
|---|---|---|
| D1 | 底座只记账不执行评审/E2E（§0 边界）| ✅ 守 lean |
| D2 | gate 三类（review/decision/acceptance）够不够覆盖？| 已验证覆盖两 flow，够 |
| D3 | flow-state 路径 `.kdev/flows/<flow>/<slug>/` | ✅ |
| D4 | 先实施 C-3(R1) 还是 C-5(R3)？ | 建议 C-5 设计已定→可并行 C-3(易)+C-5(难) |
| D5 | gate「谁来判」默认 AI、编排可改 human（§3.1.1）；Auto Mode 仅在 human gate 停靠 | ✅ 用户定 |
| D6 | SOP 三层可编排（§3.6）：默认 / 用户 orchestration.yml / 自主（L4 预留）+ 编排指南文档 | ✅ 用户定 |
| D7 | 折入 [OMC借鉴]（详见 [2026-06-04-03 对照 doc](./2026-06-04-03-OMC源码借鉴对照-底座R1-R7.md)）：R1 `active`/`_meta` · R2 邻接表+守卫+幂等豁免 · R3 `request_id`+escalate(胜OMC force-accept)+双重计数+awaiting_human TTL · structured verdict(不学OMC正则) | ✅ 落实 Q-007 借范本 |

---

## 6. 引用
- [C-1 现状盘点](./2026-06-03-02-底座R1-R7现状盘点-flows差异表.md)
- 金种子：`plugins/kdev-design-flow/lib/flow_state.py`
- 评审 prompt 资产：`plugins/kdev-design-flow/skills/kdev-design-flow/references/review-gate-prompt.md`
- coding gate：`plugins/kdev-coding-flow/skills/kdev-coding-flow/SKILL.md`（Gate-A/B/C + Per-Increment E2E）
