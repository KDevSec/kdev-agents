# KDev 数字员工 — HUD 驾驶舱（kdev-hud）设计 v1.0

| 项 | 值 |
|---|---|
| 文档状态 | 🟢 **CANONICAL 设计**（第 4 个 plugin：观测层 kdev-hud。从 kdev-core v0.1 详细设计 §2 抽出 + feature-first 重对齐 + 演讲示意定稿）|
| lifecycle | design（⏳ 阶段3 实施，当前只设计 + 演讲示意）|
| 日期 | 2026-06-10 |
| 范围 | 本文档回答："HUD 是什么 / 为什么独立成一个 plugin / 三通道各是什么 / 数据从哪来 / 怎么刷新 / 跟底座什么关系"<br>**不回答**："底座怎么记账"（→ [编排底座 合稿](./2026-06-10-03-KDev数字员工-编排底座-合稿-v1.0.md)）/ "员工有什么能力"（→ [概念与能力 合稿](./2026-06-10-02-KDev数字员工-概念模型与员工能力-合稿-v1.0.md)）|
| 配套产物 | 演讲示意：[架构总览演讲 HTML](./KDev数字员工架构总览_演讲原型_v1.0.html) 第 6 页「HUD 驾驶舱」（三通道 + 网页仪表盘，方案 A 视觉稿）|
| 写法 | **演讲式逐层递进**：第 0 层一句话 → 第 1 层三通道大白话 → 第 2 层怎么运转 → 第 3 层边界与现状 |
| 关联决策 | 承 [Q-012 feature-first 存储](../../../.kdev/memory/决策日志.md)（HUD 的数据源就是它定的 `features/<slug>/`）|

---

## 第 0 层 · 一句话：HUD 是什么

> **kdev-hud = 把底座的"账本"变成一块实时驾驶舱，让一支 6 人 AI 团队的进度随时可见。**

它是账本的**纯只读消费者**：不记账、不流转、不判断——只把底座已经记下的东西（`features/<slug>/` 里的状态 + 事件流）渲染成人能一眼看懂的视图。所以它**单独成一个 plugin（第 4 件：观测）**，跟底座（调度）、员工（干活）、记忆（记得住）并列。

### 为什么独立成 kdev-hud（不塞进底座）

| # | 理由 |
|---|---|
| 1 | **守底座铁律**：底座只记账+流转。HUD 不记账、是只读消费者，塞进去 lean 就破了 |
| 2 | **依赖方向天然干净**：kdev-hud → 只读 `features/<slug>/`（flow-state.json + events.jsonl）。契约就是文件格式（合稿03 已 canonical 化），拆出去零额外接口；底座可 headless 单装、无反向依赖 |
| 3 | **技术栈独立演进**：展示技术（statusline 命令 / HTML 热刷新 / 未来 SSE 推送）跟状态引擎迭代节奏完全不同，捆一起互相拖累 |
| 4 | **可选性 = plugin 形状**：不装照跑、装了更爽——跟 kdev-memory 单装一个逻辑，符合现有多 plugin 分工哲学 |
| 5 | **现有 3-plugin 分工补全**：干活(kdev-team) / 调度(kdev-core) / 记忆(kdev-memory) → 加第四件 **观测(kdev-hud)** |

---

## 第 1 层 · 三通道：各是什么、给谁看

HUD 不是一块屏，是**三个通道**，各管一种"看"的场景：

| 通道 | 是什么 | 给谁、什么时候看 | 归谁 |
|---|---|---|---|
| **① 命令行状态栏** | 一行速览（终端 statusline）| 干活时余光瞄一眼"现在跑到哪、有没有告警" | **kdev-hud** |
| **② 网页实时仪表盘** | 一屏全景（自包含 hud.html）| 想细看时打开：完成度 / 员工在忙啥 / 评审 PASS/FAIL（数字分暂未上事件流，FF-3）/ 监督告警（CQO L4 未落地）/ 事件流 | **kdev-hud** |
| **③ CEO 对话播报** | 聊天里主动汇报（阶段聚合 / 升级时）| 关键节点 CEO 找你 + 请你拍板 | **CEO（kdev-team）**，不是 HUD |

> **边界澄清（重要）**：通道③ 是 **CEO 员工的行为**（阶段聚合本就是 CEO/评审专家编排的内置动作，见概念合稿），不是 HUD 组件。**kdev-hud 只管 ①②**——把 events/state 渲染成状态栏和网页。通道③ 在这里列出只是为了"三通道"叙事完整。

---

## 第 2 层 · 怎么运转

### 2.1 数据从哪来：只读 feature-first 三摊

kdev-hud 不自己存任何东西，全靠**只读** Q-012 定的 `features/<slug>/`：

| HUD 要展示的 | 读哪 | 怎么算 |
|---|---|---|
| **需求完成度**（"用户认证 48%"）| `flow-state.json` 的 `stories[]` | 完成的用户故事数 / 总数（跟跑了几轮无关）|
| **当前阶段 / 节点** | `flow-state.json` 的 `active`（flow + current_node）| 直接读 |
| **员工在忙什么** | `events.jsonl` 按 `actor` 过滤 + `active` | 谁在跑哪个节点、第几轮、派了谁的单 |
| **评审流水**（数字分暂未上事件流）| `events.jsonl` 的 gate 事件 | 各闸 **PASS/FAIL + iter + issues 数**。⚠️ **FF-3**：评审专家**仍打百分制分**（PASS/FAIL 本就是「分 vs 阈值 85」派生），但当前 gate 事件**不写 `score` 字段** → HUD 暂渲染 PASS/FAIL、**不显示也不编造数字分**；`score` 是**计划内 deferred 的未来加字段**（events 行前向兼容，加一个 key 不改 shape），非取消（roadmap §1.5.5）|
| **CQO 告警**（⚠️ L4 未落地）| `blocked` ← `flow-state.json` 的 `active.status` **状态派生**（非事件）；`cqo` 事件**不存在**（CQO 为 L4 未落地，零 cqo 事件被 emit）| 合规率 + 待处理告警（待 CQO 落地）|
| **多功能队列** | 扫 `features/*/flow-state.json` | 哪些功能在跑 / 排队 |

> 全是**派生**：HUD 不是另一套真相，崩了重读文件即可重建，永远跟实际进度一致。

### 2.2 怎么刷新：三方案（推荐 A）

| 方案 | 怎么做 | 适用 |
|---|---|---|
| **★ A 自包含 hud.html + 热刷新** | 底座事件触发时重生成 `hud.html`（内联 CSS、无外部依赖）；VSCode 用官方 Live Preview / Simple Browser 打开，文件一变自动热刷新 | **阶段3 即可落地**：复用"事件触发重生成"、零常驻进程、样式完全可控 |
| B hud.html 外壳 + 轮询 JSON | 外壳不变，JS 每 2 秒 fetch `hud-state.json`；底座只更新 JSON | 刷新更平滑；但 `file://` fetch 受限，需走 localhost |
| C `kdev hud serve` + SSE 推送 | 起极小本地服务，事件一来就 push | **L3+ 升级项**：体验最佳但要常驻进程，跟 lean 哲学权衡 |

> 取代旧设计的 `.kdev/hud.md`（markdown 预览）——markdown 预览样式受限、做不出仪表盘质感，已废弃，改 HTML。

### 2.3 通道① 命令行状态栏（statusline）

`kdev-hud statusline` 输出单行（≤80 字），接 Claude Code 原生 statusLine：

```
🏢 KDev 团队 │ 开发阶段·代码评审 ✏️第2轮 │ 开发工程师 忙·评审专家 忙 │ ⚠ 1
```
字段：项目/团队 → 当前阶段·节点(状态 icon) → 员工忙闲摘要 → 待处理告警数。

### 2.4 通道② 网页实时仪表盘（hud.html）

一屏全景（详见演讲示意 HTML），分区：
- **统计磁贴**：当前阶段 · 需求完成度 · 评审通过 · 待处理告警
- **员工实时活动**：每人正在跑哪个能力 / 子任务进度 / 已用时长（忙=绿脉冲，闲=灰）
- **评审流水管线**：各评审节点（绿=已过 / 黄=评审中 / 灰=待评）⚠️ FF-3：数字分暂未上事件流（评审仍按阈值 85 打分，但 HUD 暂只显 PASS/FAIL，score 作未来加字段）
- **CQO 监督条**：合规率 + 告警 ⚠️ CQO 为 L4 未落地，本区待 CQO 实现
- **实时事件流**：时间线（流转 / 判定 / 派单 / 协作）

> **体验基准参考 — Claude Code `/workflows` 多智能体面**（2026-06-12 沉淀）：
> CC 的 ultracode/Workflow 把一次编排的**全部细节外化到独立 `/workflows` 进度树**——主会话只留**一行极简占位**（"workflow is running"），而 Phases · 每个 agent 的 `token / tools / time` · **可钻入单个 agent 详情**（面板底部 `↑↓ select · esc back · s save`）全在那张**独立可交互面板**上。这正是通道②应有的形态：**通道①/statusline 极简 + hud.html 承载全景且可钻入**。两条经验：
> 1. **"信息少"是干净的代价，也是证据**——主会话/状态栏信息越多越"混杂"，细节就该外化到通道②；编排噪音不进主面，是 HUD 价值的前提（对照"为什么主会话派单会混杂"分析：根因是编排循环跑在主 loop 里）。
> 2. **面板值不值，取决于能否交互钻入**——CC `/workflows` 在 CLI 里可点击钻入单 agent，在 VSCode 扩展里渲染较薄；通道② hud.html 要对标"**可钻入单员工 / 单节点详情**"，而非只读静态快照。

---

## 第 3 层 · 边界与现状

| 铁律 / 边界 | 说明 |
|---|---|
| **只读** | kdev-hud 永不写 `features/`；坏了不影响底座/员工 |
| **派生非真相** | 三通道全从 events/state 派生，权威源仍是底座文件 |
| **通道③ 不归 HUD** | CEO 对话播报是 kdev-team 的 CEO 行为 |
| **headless 友好** | 不装 kdev-hud，底座/员工照跑 |

**现状 vs 设计（2026-06-10）**：

| 块 | 状态 | 说明 |
|---|---|---|
| 三通道设计 | ✅ 定稿（本文档）| 视觉稿见演讲示意 HTML |
| kdev-hud plugin | ⏳ **阶段3 才建** | 主食是 events.jsonl，events 没落地前建 HUD 是空壳 |
| 依赖：events.jsonl | ⏳ 框架层未建（阶段3，归 kdev-core）| 现暂塞 flow-state.json 内嵌 |
| 依赖：feature-first 存储 | 🔨 R1 refit 待办（见合稿03）| stories[]/active/events 是 HUD 的数据契约 |

> **时机**：阶段3 跟 events.jsonl 一起做——先有事件流，再建消费它的 HUD。

---

## 取代关系 + 变更记录

**本稿抽自/取代**：
- [kdev-core v0.1 详细设计 §2 HUD 服务](./_archive/2026-05-28-03-kdev-core-v0.1-详细设计.md)（已归档）——三通道骨架来自此，本稿把"通道② 从 hud.md → hud.html"、"数据源对齐 feature-first"、"HUD 独立成 kdev-hud plugin"三处更新

| 日期 | 变更 |
|---|---|
| 2026-05-28 | HUD 三通道设计随 kdev-core v0.1 详细设计 §2（通道② 为 `.kdev/hud.md` markdown 预览，挂在底座框架层）|
| **2026-06-10** | **独立成 kdev-hud（第 4 plugin）**：① 从底座抽出、定为只读观测层（5 条理由）；② 通道② markdown 预览 → **自包含 hud.html + 热刷新（方案 A）**；③ 数据源对齐 **feature-first**（完成度←stories[]、员工活动←events 按 actor 过滤）；④ 通道③ 归 CEO 不归 HUD；⑤ 现状：阶段3 跟 events.jsonl 一起建 |
</content>
