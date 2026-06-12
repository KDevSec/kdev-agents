# kdev-memory 会话污染治理 + 评分模式可配 设计稿

| 项 | 值 |
|---|---|
| 文档性质 | **设计稿 v0.5**（§5.8/§6：层2 深度他评归位 **蒸馏管道质量闸**（Q-017）；v0.4：per-step 后台 recorder + **模型他评替换自评**；待 §5.6 spike 后起实施）|
| lifecycle | design |
| 日期 | 2026-06-13（v0.5：层2 归蒸馏质量闸 Q-017）/ 2026-06-12（v0.4：他评替换自评 · v0.3：variant 拍板 + §5.6 去风险）/ 2026-06-10（v0.2）/ 2026-06-09（v0.1）|
| 范围 | 治理 kdev-memory 对主会话的侵入（评分动作链打断工作流为核心痛点），评分模式可配，落盘 transcript 溯源化 |
| 承 | [Q-002 本项目跳过用户评分](../../../.kdev/memory/决策日志.md) · [Q-011 阶段2接入设计](./2026-06-07-阶段2-第二员工+记忆scope-design.md) · [kdev-memory SKILL v0.13.0](../../../plugins/kdev-memory/skills/kdev-memory/SKILL.md) |
| defer | 他评智能体（移入后续 roadmap）· P-C2 JSONL 操作层 · P-C3 并发写锁 · scope 分离（另见阶段2 P-C1 spec）|

---

## 0. 一句话

把 kdev-memory 对主会话的侵入从"每 Step 必追问用户评分的硬性闸门"降为"可配三档评分模式"，并把 Step 落盘从"主会话手写事实 YAML"改为"recorder 读 transcript 原件溯源"，让主会话只管干活。

---

## 0.5 v0.2 修订说明（相对 v0.1 初稿）

v0.1 经一轮对抗式评审 + 用户讨论收敛，做了如下纠正：

| # | v0.1 的问题 | v0.2 纠正 |
|---|---|---|
| 1 | 当 greenfield 设计，未提 Q-002 | 承接 Q-002（本项目 2026-05-27 已拍板"只走模型自评"）。P-C0.5 重新定位为"把 Q-002 这条软决策做成 hook 层能机读遵守的机制" |
| 2 | model-only 下"拷贝自评值到用户评分段（source: model）"= 伪造用户评分 | 改为**用户评分段留空 + 标 voided-faded**，对齐 Q-002 既定做法，不污染下游 misalignment 数据 |
| 3 | config 用两级嵌套 `rating: → peer_review: → enabled:` | 现有 `memory_config.py` parser 只支持一层嵌套 → **扁平化 flat dot-key**（`rating.mode: model-only`）|
| 4 | P-C1b = "独立记忆智能体"完整架构（SessionEnd → `claude -p`）| **塌缩为「transcript 溯源的会话内 fire-and-forget dispatch」**——砍掉 `claude -p`、cron、跨会话补录。理由见 §5.6 |
| 5 | 把"commit"当 step 边界 | **commit 绝不当 step 边界**（粒度规则：Step 比 commit 粗）。切分权威仍是主会话的"工作单元完成"判断，与今天一致。TDD/subagent-driven 爆量 commit 塌缩在一个 Step 内。见 §5.4 |
| 6 | 含 P-C2 他评智能体 | **他评移入后续 roadmap**，不在本 spec 范围；config 不预留 peer_review 字段 |

---

## 0.6 v0.3 修订说明（相对 v0.2，仅动 §5/§6）

v0.2 把 P-C1b 定为"transcript 溯源的会话内 fire-and-forget dispatch"，但 §5.6 把"transcript 路径怎么递给 subagent"留作待验证，且未对比"per-step dispatch (a)"与后来提出的"workflow-batch (b)"两 variant。v0.3 经一轮 brainstorming 收敛：

| # | v0.2 留白 | v0.3 收敛 |
|---|---|---|
| 1 | (a) per-step vs (b) workflow-batch 未拍板 | **拍板 (a)**（[Q-015](../../../.kdev/memory/决策日志.md)）。(b) 在自评无源/切分重建/显式 launch 可靠性/丢实时性四笔代价上输，且是 §5.3 否掉的 variant C 的表亲。详见新增 §5.0 |
| 2 | workflow-batch 这个直觉无处安放 | **reframe 到他评**：workflow-batch 的 fan-out 形态（显式 opt-in / on-demand / 独立读者 / 批量）正是未来「他评/评审专家」(MQ-2) 的形状，不是 Step落盘的。详见改写的 §6 |
| 3 | §5.6 "路径怎么递给 subagent" 待验证 | **解法 + spike-gate**：hook 把 `transcript_path`+offset stash 进 state 文件，recorder 从文件读、不经 dispatch prompt。但实施前先跑 spike 实测三件事（见新 §5.6），承本项目 G-008/R-009「先核代码再信设计」教训 |
| 4 | 溯源与 MQ-2 自评 confabulate 的关系没点明 | **新增 §5.8**：溯源免费部分买下 MQ-2（杀事实性 confab），残留敞口收窄到 self_eval 数字一项 → 他评补最后一公里 |

---

## 0.7 v0.4 修订说明（相对 v0.3，再动 §5/§6）

v0.3 拍板了 "(a) per-step + 主会话当场给 self_eval"，并把 workflow-batch 整体推给"未来他评"。用户复盘后修正方向（[Q-015 修正](../../../.kdev/memory/决策日志.md)）：

| # | v0.3 的判断 | v0.4 修正 |
|---|---|---|
| 1 | self_eval 必须主会话当场第一人称给（这是 (a) 胜出的核心论据）| **解耦**：把评估从 self-eval 换成 **后台 recorder 读 transcript 出「模型他评」**。我 v0.3 把"self_eval 必绑主会话"错耦进 (a)——(a)/(b) 是**假对立**。一松绑，(a) 的实时 + (b) 的客观后台他评**合成一个更好的设计**。详见改写 §5.0 |
| 2 | 评估锚定主会话 self_eval（MQ-2 只"部分买下"，残留 self_eval 数字同进程偏差）| **他评替换自评**：`### 模型自评` → `### 模型他评`（独立 recorder 读真 transcript 出执行质量评分）。MQ-2 在**记录层**修掉，不只"部分买下"。承 Q-002（本项目无人评）+ 用户选「他评替换自评」 |
| 3 | 主控付出 ~5 行指针（含 self_eval）| **主控付出 → 近零**：边界处发**近乎空的 dispatch**（recorder 全程从 transcript 自取事实 + 出他评）+ 靠 hook 必要提醒。诚实地板：hook 不能自主拉起后台 worker（只主循环能调 Agent），故最小 = 1 行触发 + 可选意图 hint |
| 4 | 载体未细分；workflow-batch 整体推未来 | **载体 = 升级现有 fire-and-forget 后台 dispatch（每步实时）**；重型 Claude Code Workflow fan-out **留给** Q-016 评审专家 mode-2（深度批量他评，L3）。两层他评见 §5.8 |
| 5 | 他评整体"移入后续 roadmap，本 spec 不做" | **拆两层**：**轻量 per-step 他评落 P-C1b（本设计）**；**重型深度他评 = Q-016 mode-2 评审专家**（workflow-batch / 全标准/评分/仲裁 / L3）。P-C1b 不再"不做他评"，它做**基线层** |

> 与 [Q-016 评审专家](../../../.kdev/memory/决策日志.md) 的关系是本次的关键对齐点，独立成 §5.8 讲清，避免两个决策对"谁做他评"打架。

---

## 0.8 v0.5 微修订（层2 归位，Q-017）

v0.4 把"两层他评"的层2 安成 Q-016 评审专家 mode-2。用户提"第二层评审可与蒸馏结合"，复盘采纳（[Q-017](../../../.kdev/memory/决策日志.md)）：**层2 深度他评改归 `/kdev-memory-distill` 的 audit/质量闸**，从 Q-016 摘掉 mode-2。理由：同节奏同语料 + 污染正好在蒸馏处放大 + 评审专家 6+1 标准评的是产物不是"记忆诚不诚实"（别扭嫁接）+ 顺带复活被 [Q-002](../../../.kdev/memory/决策日志.md) 打死的 `dataset-misalignment` 切片。仅改 §5.8 表/关系厘清 + §6；层1（P-C1b per-step 他评）不动。

---

## 1. 问题诊断：污染源定位

### 1.1 校正后的污染源分层

用户反馈"会话污染"后逐项排查，发现注入/召回是有用的（跨 session 续接），**核心污染源只有评分动作链**：

| 行为 | 性质 | 主会话侵入 | 处理 |
|---|---|---|---|
| `<kdev-memory-brief>` 注入 | ✅ 有用 — 跨 session 续接 | 中 | 保留，P-C1a 加 verbosity 分级 |
| `<kdev-memory-recall>` 召回 | ✅ 有用 — 按需召回相关知识 | 低（去重+限额，~90 token/次）| 保留不动 |
| Step 落盘 dispatch | ⚠️ 中性 — hybrid 下主会话写 ~30 行 YAML | 中 | P-C1b transcript 溯源化，干掉 YAML |
| **评分动作链** | 🔴 **核心污染源** | **高** — 每 Step 追问用户 1~2 轮，打断心流 | **P-C0.5 治本** |
| stop-check 半残提醒 | ⚠️ 评分的衍生问题 — 44 条半残触发反复提醒 | 低~中 | 随评分模式联动降级 |

### 1.2 Q-002：根因其实两周前就该被解决

本项目 **2026-05-27 已拍板 Q-002**：选项 B「跳过用户评分，仅模型自评」，用户原话*"后面我不再评分，你来自评即可"*（见 F-001）。

但 Q-002 是写在**决策日志**里的"软决策"——`step_completeness.py` / brief / stop-check 这层 hook **根本不知道它存在**，所以一直把缺用户评分的 Step 当半残 nag。这就是 **44 条半残**的真正根因。

**所以 P-C0.5 的真正价值不是"新增一个配置选项"，而是"让 hook 层能机读地遵守 Q-002 这条已存在的决策"。**

Q-002 的落地约束已经规定了正确做法，本 spec 全程对齐：
- 用户评分段**不主动追问**，但保留段落骨架以便用户随时插入回填
- 模型自评段仍**必填扣分项**（防讨好式满分）
- 已开未评的旧 Step 标 `voided-faded`，不回头补
- 这条不写 CLAUDE.md（属本项目偏好；其他项目沿用 kdev-memory 默认）

### 1.3 设计约束

- **注入和召回保留**——它们增强跨 session 续接，不是污染源
- **transcript 是实时落盘的真正载体**——Claude Code 本身在持续 verbatim 落盘会话 transcript，保真度满分；"实时落盘"要保的是事实保真度，让 recorder 读 transcript 原件即可，无需主会话趁热手写副本
- **向后兼容**——现有 `user-required` 行为作为可选项保留；插件默认降为 `user-opt-in`；本项目 config 设 `model-only`（= Q-002）

---

## 2. 拍板决策

| # | 决策点 | 拍板 | 依据 |
|---|---|---|---|
| 1 | 评分是否可跳过 | **可配三档**：model-only / user-opt-in / user-required | Q-002 已验证"不想评分"是真实诉求；硬闸门制造半残而非质量信号 |
| 2 | 插件默认模式 | **user-opt-in**（自评后轻提一句，不回应就过）| 比 user-required 温和；保留采集真实用户感受的机会 |
| 3 | 本项目模式 | **model-only**（= Q-002 机读化）| 承接已有决策 |
| 4 | model-only 下用户评分段 | **留空 + 标 voided-faded**，不伪填 | 伪填 source:model = 假用户评分，污染 misalignment 数据；对齐 Q-002 |
| 5 | 一句话切换 | 用户说"关掉评分" → Claude 写 config → 立即生效 | 零摩擦 |
| 6 | 首次体验 | SessionStart brief 检测无 `rating.mode` 键 → 一次性提示可配 | 让用户知道选项，但不默认 user-required |
| 7 | Step 落盘机制 | **后台 recorder 读 transcript 客观采集 + 模型他评（每步实时 fire-and-forget，升级现有 dispatch）**（[Q-015 修正](../../../.kdev/memory/决策日志.md)；(a)/(b) 假对立→合题，见 §5.0）；**§5.6 spike-gate 先验后建** | 主控付出降到近零（无 YAML、无 self_eval）；他评比自评客观、在记录层修 MQ-2；重型 Workflow fan-out 留给 Q-016 mode-2 |
| 8 | Step 切分 | **沿用现有粒度（工作单元，比 commit 粗）；commit 不当边界** | TDD/subagent-driven 爆量 commit 必须塌缩在一个 Step 内 |
| 9 | 他评分层 | **两层**：基线 per-step 他评落 **P-C1b**（§5.8 层1，本期）；深度/专家/批量他评 = **Q-016 评审专家 mode-2**（workflow-batch，L3）| 承用户「他评替换自评」+ 对齐 Q-016 不打架；类比 linter-every-commit vs 周期专家 audit |

---

## 3. P-C0.5：评分模式可配（机读化 Q-002，立即可做）

### 3.1 config.yaml 新字段（flat dot-key，单层）

```yaml
# 评分模式：model-only | user-opt-in | user-required
# 现有 parser 只支持单层，用 flat dot-key
rating.mode: model-only      # 本项目 = Q-002；插件默认 user-opt-in
```

> ⚠️ **不要写两级嵌套**（`rating:` → `mode:` 是一层，OK；但任何 `rating: → x: → y:` 两层 parser 读不到）。当前只需 `rating.mode` 单键，扁平写法最稳。

### 3.2 三档行为对比

| 行为 | `model-only` | `user-opt-in` | `user-required`（现行） |
|---|---|---|---|
| 模型自评（含扣分项）| ✅ 写入并锁定 | ✅ 写入并锁定 | ✅ 写入并锁定 |
| 追问用户 | ❌ 不问 | 轻提一句，不回应即跳过 | 必须追问 |
| 用户评分段 | **留空 + status: voided-faded** | 有则填（source 隐含 user），无则留空 | 必须用户填写 |
| 半残检测 | 不触发（voided-faded 跳过）| 不触发（无值=正常）| 触发（如缺失）|
| stop-check | 跳过半残检测 | 只软提醒（不阻塞）| 现行行为 |
| 心流打断 | **零** | **极低** | **高** |

### 3.3 model-only 下用户评分段处理（对齐 Q-002，不伪填）

```markdown
### 用户评分
- 完成时间：—
- 顺畅度：—/5
- 用户评价：
> 半残销账：rating.mode=model-only（承 Q-002），用户评分段保留骨架不主动采集
```

Step frontmatter 标 `status: voided-faded`。`step_completeness.py` 现有逻辑已对 `voided-*` 跳过欠评扫描——**复用，不新增逻辑**。这样既不伪造数据，又不触发半残 nag。用户随时主动给分 → 当场回填 + 改 status: scored，恢复闭环。

> **与 P-C1b 的术语演进（别误读为冲突）**：本节「模型自评」是**评分模式**层面（谁评：model vs user；model-only = 不追问用户、模型自己评）。P-C1b（§5.8）改的是**模型那一评怎么产出**——从主会话 self-eval 升级为 recorder 独立读 transcript 出 `### 模型他评`。评分模式仍 model-only，只是"模型评"由自评变他评、更客观；P-C1b 落地时把 `### 模型自评` 段迁为 `### 模型他评`。

### 3.4 首次提示（session-start-brief 新增）

config 无 `rating.mode` 键 → 视为新用户/老版本升级 → brief 末尾追加一次性提示：

```xml
<kdev-memory-rating-setup>
kdev-memory 评分模式可配置。当前默认 user-opt-in（自评后轻提一句，不回应就过）。
• 说"关掉评分"→ model-only（只模型自评，零追问）
• 说"严格评分"→ user-required（每 Step 必追问）
• 随时一句话切换，Claude 改 config.yaml 立即生效。
</kdev-memory-rating-setup>
```

> 本项目已有 Q-002，config 应直接写 `rating.mode: model-only`，此提示对本项目不出现。

### 3.5 44 条半残的批量销账迁移

P-C0.5 落地时，对本项目 Q-002（2026-05-27）之后的所有欠评 Step **批量标 `status: voided-faded`** + 追加销账注释（一次性脚本，幂等）。清掉 backlog，brief 不再 nag。

### 3.6 需改的文件清单

| 文件 | 改动 |
|---|---|
| `hooks/lib/memory_config.py` | 加 `read_rating_mode()`，读 `rating.mode`，默认 `user-opt-in` |
| `hooks/lib/step_completeness.py` | 读 `rating.mode`：`model-only`/`user-opt-in` 下用户评分段空不算半残（voided-faded 本已跳过，补 model-only 的空值豁免）|
| `hooks/stop-check.py` | `model-only` 跳过半残检测；`user-opt-in` 只软提醒不阻塞 |
| `hooks/session-start-brief.py` | 首次（config 无 `rating.mode`）→ 加 `<kdev-memory-rating-setup>` |
| `skills/kdev-memory/SKILL.md` | 评分动作链按 `rating.mode` 三分支重写 |
| `skills/kdev-memory/references/六类记录-schema.md` | 注明 model-only 下用户评分段留空 + voided-faded 的标准做法 |
| `.kdev/memory/config.yaml` | 加 `rating.mode: model-only` |
| 一次性迁移脚本 | 批量销账 Q-002 后的半残 Step |

### 3.7 测试

- `test_rating_mode_config.py`：三种模式下半残检测行为不同
- 改 `test_step_completeness.py`：model-only 下空用户评分段不算半残
- 改 `test_stop_check.py`：model-only 跳过半残的 case
- **跑 skill-quality evals 验行为变更不回归**（注意 [run_eval 在 Claude Code 嵌套环境的已知限制](../../../.claude/projects/.../skill-creator-run-eval-limitation.md)，可能需手验）

### 3.8 预估工作量

~4-6 小时（纯 SKILL/配置 + 迁移脚本）

---

## 4. P-C1a：brief 分级 + subagent 输出精简

**前置**：P-C0.5

### 4.1 brief verbosity 分级

```yaml
brief.verbosity: normal      # compact | normal | verbose
```

`compact` 只注入：⚠️ WARN 文件 + pending_decisions + 今日进度一行。其余（半残清单/distill 候选/promote 候选）→ 写 `.kdev/memory/brief-detail.md` 供主动查阅。

### 4.2 subagent 返回精简到一行

`kdev-step-recorder.md` agent prompt：详细输出写 `.kdev/memory/` 文件，stdout 只回一行确认（"Step main-42 recorded"）+ 极简审计字段。

### 4.3 stop-check 按评分模式降级

| `rating.mode` | stop-check 行为 |
|---|---|
| `model-only` | 跳过半残检测，只查漏汇总/跨期 |
| `user-opt-in` | 半残只软提醒（stdout），不阻塞 |
| `user-required` | 现行（soft + strict 阻塞）|

### 4.4 预估工作量

~4-6 小时

---

## 5. P-C1b：Step 落盘 = 后台 recorder 读 transcript 客观采集 + 模型他评（每步实时 fire-and-forget）

**前置**：P-C1a

这是 v0.1「独立记忆智能体」塌缩后的形态——**不是新架构，是现有 fire-and-forget dispatch 的一次精简 + 溯源化 + 评估换他评**。

### 5.0 形态收敛：(a)/(b) 是假对立 → 合题（Q-015 修正）

v0.3 摆出两条路并拍了 (a)：

- **(a) per-step**：主会话边界写指针（**含主会话 self_eval**）+ fire-and-forget dispatch；recorder 读 transcript 抽事实。
- **(b) workflow-batch**：commit 锚点切段 → 显式 launch Workflow → 后台 fan-out N recorder → 批量写。

当时判 (a) 胜，**核心论据是"self_eval 必须主会话当场第一人称给"**。复盘发现这是个**没拆开的耦合假设**：一旦把评估从 self-eval 换成 **后台 recorder 读 transcript 出「模型他评」**，(a) 那张表里"自评无源/切分重建/显式 launch"的胜负手要么失效要么不再重要——所以 (a)/(b) 是**假对立**。

**合题（v0.4 拍板）**：

| 取 (a) 的 | 取 (b) 的 | 弃两者的 |
|---|---|---|
| **每步实时**（fire-and-forget 后台 dispatch，环境常驻、hook nudge、每步完成即落、续航天然准）| **客观后台采集 + 他评**（recorder 独立读真 transcript 出事实 + 执行质量他评，更客观）| **(a) 的主会话 self_eval**（换他评）；**(b) 的重型 Workflow + 显式 launch + segmenter**（每步实时不需要 fan-out，且 Workflow hook 拉不起、会话末批量崩即丢）|

→ 落地形态：**升级现有 step-recorder 后台 dispatch**（即你刚见的 main-73 那种 "1 launch + 1 通知" 模式），让它 ① 从 state 文件自取 `{transcript_path, range}` 读真 transcript（§5.6）② 客观抽事实 ③ 出 `### 模型他评`（§5.8）。**主会话付出塌到近零**（§5.1/§5.2）。

**为什么不用重型 Workflow fan-out 做本 recorder**：per-step 实时只处理"当前这一步"，不需要并行 fan-out；而 Workflow 须显式 opt-in launch（hook 拉不起）、一次性脚本、会话末批量崩即丢——对"每步常驻实时"是净负担。**重型 Workflow fan-out 留给 [Q-016 评审专家 mode-2](../../../.kdev/memory/决策日志.md)**（按需深度批量他评 / 多步审计 / 全标准评分 / 仲裁，L3）。两层他评见 §5.8。

> 字母小提示：§5.3 另用 (B)/(C) 指"会话内 dispatch vs 跨会话补录"，是另一根轴——其 (B) 会话内 ≈ 本节选的"每步实时"，(C) 跨会话仍被否（§5.3）。

### 5.1 主控付出塌到近零

| | 今天 | 改后 |
|---|---|---|
| 触发 | commit-tracker 攒 pending + brief/Stop nudge | **不变**（复用，见 §5.5 调参）|
| 切分权威 | 主会话"工作单元完成 → dispatch"判断 | **不变**（见 §5.4；边界标记从"30 行 YAML"瘦成"近空触发"）|
| **主控付出** | 写 ~30 行事实 YAML（含 self_eval）喂 subagent | **写近乎空的 dispatch**：1 行触发 + 可选 1 行意图 hint；**不再写事实、不再写 self_eval** |
| subagent 取数 | 从 YAML | **读 transcript 原件**自抽事实 |
| **评估** | 主会话侧 `### 模型自评`（同进程，MQ-2 会 confab）| recorder 独立读真 transcript 出 `### 模型他评`（§5.8）|
| 返回 | 审计摘要 | 一行确认 |

那 ~30 行事实 YAML（最大 token 源）+ 主会话 self_eval 一起消失，主控只剩"边界处发个近空触发"。新增的唯一机制：**commit-tracker hook 在 commit 那刻多记 `transcript_path` + offset** 进 state 文件，作为范围素材 + 路径来源（§5.6 解 v0.2 待验证点）。

**诚实地板**：想做到主会话"零动作"全自动后台录，平台不允许——hook 只能跑命令、不能拉起 Agent/Workflow（只主模型循环能调）。最小可达 = 主会话边界发个近空 dispatch + hook 必要提醒。这条地板也是选"每步实时（主循环顺手发）"而非"会话末批量（须主循环临终记得 launch，更易漏）"的理由之一。

### 5.2 dispatch 载荷（主控付出的全部 = 近乎空）

```yaml
# transcript_path + offset 范围 recorder 从 state 文件自取（§5.6），不经此指针
title_intent: <可选·一句话意图 hint，让 recorder 不把 side-quest 当主线；省略则 recorder 从 transcript 自行归纳>
# 不再有 self_eval_*（评估改由 recorder 出他评，§5.8）
# key_decision_pointers 也可省——recorder 能从 transcript 抽 Q/G 编号；留着只是给个锚
```

recorder 从 state 文件取 `{transcript_path, range}` → 用 Bash `sed`+`jq` 切片（§5.6 spike 结论①）→ 客观抽：**工具数 / 报错(`is_error`+原文) / 绕路 / 文件 / commit SHA / Q-G 决策 + `skills_invoked`（调了哪些 skill / plugin / subagent，语义而非计数）+ `subject`（Step 主题；遇 skill 反馈走 F-NNN 评分裂解，承[蒸馏决策1「subject 必明」](../../../.claude/projects/-home-lyadmin-Projects-kdev-agents/memory/kdev-memory-distillation-design.md)；溯源使 L1/L2 自动推断变易——L2 定义就是"取最近调的 skill/工具"，transcript 全有）** → 出 `### 模型他评`（§5.8）→ 写四段（model-only：用户评分段按 §3.3 留空 voided-faded）→ 一行返回。**主控真正必填的只有"触发"本身**；title_intent 是可选润滑，不是负担。

### 5.3 为什么不做跨会话补录 / cron / claude -p（污染对比）

讨论中量化了"会话内 dispatch (B)" vs "跨会话补录 (C)"（token 为估算）：

| 维度 | 会话内 dispatch (B) ✅ | 跨会话补录 (C) |
|---|---|---|
| 产出会话永久 token | ~250–350/次 × 2–5 次 = **600–1500/会话**（context 的 0.1–0.7%）| ~0 + 前瞻指针 ~50–100 |
| 心流打断 | 几乎零（fire-and-forget，不等返回）| 零 |
| 实时性 / 续航 | 实时，下会话 brief 天然准 | 延迟一会话，须拆"前瞻指针 vs 史料"才不断续航 |
| 末会话/崩溃 | 本会话内已落 | 末会话可能永不补录，需兜底 + 手动补录 |
| 架构改动 / 风险 | **小 / 低**（复用现有 nudge）| **大 / 中**（跨会话 offset / 孤儿检测 / 前瞻拆分 / transcript 跨会话传路径待验证）|

**结论**：用户原本抱怨的污染是评分打断心流（P-C0.5 已解），不是 dispatch token。一旦 fire-and-forget + transcript 溯源，残留 ~1500 tok/会话可忽略。C 唯一赢的"产出会话零 token"换来一整套新机制，不划算。**`claude -p` 另有 recursion/auth/SIGHUP/成本风险，一并否。**

### 5.4 Step 切分：沿用现有粒度，commit 绝不当边界 ⚠️

现有规则（[六类记录-schema §3](../../../plugins/kdev-memory/skills/kdev-memory/references/六类记录-schema.md)）：**Step = 有明确边界的工作单元（一个任务/一次评审/一次实验），粒度比 commit 粗、比迭代细。**

- **切分权威 = 主会话"工作单元完成 → dispatch"的判断，与今天完全一致。** TDD / superpowers subagent-driven-development 一个工作单元内爆出的 N 个 commit → 仍是**一个** Step。**commit 数永不驱动切分。**
- **正常路径**：主控在工作单元边界 dispatch 一次 → recorder 读这一段 transcript → 写**一个** Step。recorder 不做切分。
- **补录 fallback**（主控漏 dispatch、多个工作单元堆积）：recorder 读较大范围，**按粒度规则切**（任务/评审/实验完成点、用户决策点、可 review 产出里程碑），**显式不按 commit 数切**——TDD 爆量 commit 保持塌缩。
- **commit 的角色**：① transcript 范围的原始素材 ② 现有 nudge 阈值。

### 5.5 nudge 阈值调参（避免 TDD 刷屏）

现有 pending-commits 阈值（count=3 / age=30min）在 TDD 爆量时会按 count 频繁触发软提醒。改为**以 age 为主、count 调高或可配**，避免一个工作单元内反复 nudge。主控仍在工作单元真正完成时才 dispatch 一次。

### 5.6 transcript 可达性：机制 + spike-gate（解 v0.2 "路径怎么递给 subagent" 待验证）

**根问题**：fire-and-forget subagent 拿到的是 prompt，不是 hook 的 stdin；它怎么知道 transcript 在哪、读哪段？

**解法（不经 prompt 传路径）**：

1. **hook 侧 stash**——commit-tracker（PostToolUse on Bash）**顺手把 `transcript_path` + 当前 offset 写进 `state/pending-commits.json`**。hook 的 stdin 本就含 `transcript_path`（snake_case；subagent 拿不到、hook 拿得到——这正是必须由 hook 捕获的原因）。⚠️ 但 commit-tracker 现读 `toolInput`(驼峰)=bug，必须先修（spike 结论②）。
2. **recorder 侧自取**——recorder 从 state 文件读 `{transcript_path, last_recorded_offset → current_offset}`，用 **Bash `sed -n 'A,Bp' <transcript> | jq`** 切片抽结构化事实（**不用 Read 工具**——spike 结论①）。主会话指针里**不出现路径**。
3. **offset 语义**——transcript 是 JSONL（一行一 message）。offset 取行数（commit 那刻 `wc -l`）即可；range = [上次已记录, 当前]。粒度是工作单元（粗），±几条 message 的 slop 可容忍。

**✅ spike 已跑（2026-06-13，承 [G-008](../../../.kdev/memory/踩坑日志.md) / R-009「先核代码再信设计」）—— 整体 PASS（机制成立），但纠出 3 个设计修正**

实地验三件事 + claude-code-guide 核[官方 hook 契约](https://code.claude.com/docs/en/hooks.md)：

| # | 验什么 | 结果 | → 设计修正（已 banked） |
|---|---|---|---|
| ① | subagent 怎么读 transcript | **Read 工具不行**（25k 整文件 token 闸，offset/limit 也救不了 91k transcript→直接拒）；**Bash `sed`+`jq` 行**（实测子 agent 读 repo 外 `~/.claude/...` 无 sandbox 限制）| recorder **用 Bash sed/jq 切片+抽结构化事实**，不用 Read 工具 |
| ② | stdin 真有 `transcript_path`？字段真名？ | ✅ **有**，指向 session JSONL；字段 **snake_case**（`transcript_path`/`tool_input`...）。**但 commit-tracker 读 `toolInput`(驼峰)=bug**→永拿 `{}`→从不识别 commit→**`pending-commits.json` 从未填→"🔔 pending dispatch" nudge 一直死的** | commit-tracker **先修 `toolInput`→`tool_input`**（load-bearing：不修连 transcript_path 都读不到；**顺带复活死掉的 nudge**，记 [G-010](../../../.kdev/memory/踩坑日志.md)）|
| ③ | transcript 含的语义信号够不够 | ✅ 不只工具计数——**调了哪些 skill / subagent / MCP**、报错(`is_error`+原文)、文件、SHA 全抽得出（实证：本会话 `Skill→superpowers:brainstorming`、`Agent→general-purpose×3`）| §5.2/§5.8 **加 `skills_invoked` + `subject` 提取**（溯源还让 subject L1/L2 自动推断变易）|

> 取证方式：① 两次子 agent 实测（Read FAIL / Bash PASS）；② claude-code-guide 拉官方 docs（[hooks.md](https://code.claude.com/docs/en/hooks.md) Common input fields）+ commit-probe 经验确认（想 instrument live hook 抓真 stdin 被 auto-mode 拦——改 repo 外 live hook=未授权持久化，合理，故走文档+探针非侵入路）；③ jq 抽本会话 transcript 实测。**spike PASS：transcript 可达可解、机制成立**，实施按修正后的设计走（不再有"退回讨论"风险）。

**残留取舍**（机制确定后仍在的）：

| 优点 | 缺点/风险 |
|---|---|
| 干掉 30 行 YAML + self_eval，主会话付出降到**近零** | recorder 读 transcript 抽错/误判 → 高置信度垃圾（靠 8 hard-gate + 不确定字段显式标注兜；他评比抽事实更吃 transcript 质量）|
| 实时，续航天然准，无跨会话延迟 | recorder 读长 transcript 在**其自身**上下文有成本（按 offset 只读增量段优化）|
| 小改动、低风险（复用现有 commit-tracker + state 模式）| offset 精度：PostToolUse hook 触发时 transcript 可能尚未 flush 最末几条（slop 可容忍，spike #2 量化）|
| 无 `claude -p` / cron / 跨会话机制 | — |

### 5.7 预估工作量

- **spike（gate）**：✅ **done（2026-06-13）**——PASS + 3 修正（§5.6）
- **实施（按修正后设计）**：~8-10h ——
  ① **先修 commit-tracker `toolInput`→`tool_input`**（先决；顺带复活死掉的 nudge）+ stash `transcript_path`+offset 进 state
  ② step-recorder 改 **Bash `sed`/`jq` 切 transcript** 抽事实（含 `skills_invoked` / `subject`）**+ 出他评**
  ③ `### 模型自评`→`### 模型他评` schema 迁移（六类记录-schema / step_completeness / 模板）
  ④ nudge 调参（以 age 为主）
  ⑤ 测试：commit-tracker 字段名回归 + transcript 切片抽取（mock JSONL）+ 他评 schema + skill/subject 抽取

### 5.8 评估 = 模型他评（替换自评）+ 两层他评对齐 Q-016 评审专家

**MQ-2 实证**（[roadmap §1.5.7](../../framework/01-design/2026-06-06-01-数字员工整体设计路线图roadmap-v1.0.md)）：Step main-69 的 `### 模型自评` 凭空编造扣分项，根因 = 写自评与写代码同一生成过程、且没读真 transcript、据 summary 反推"听起来合理"。**自评无法 catch 自己的编造**——结构性盲区。

**v0.4 的解：把记录层的评估从「自评」直接换成「他评」。**

- **谁评**：recorder（独立于主会话的 subagent），**读真 transcript** 出 `### 模型他评`。两个破点同时成立：① 读真记录 → 破事实 confab（编不出"grep 漏看 X"）② 独立生成过程 → 破同进程判断偏差（main-69 那种"听起来合理"的反推没了立足点）。
- **评什么**：执行质量（客观、有据）——目标达成度 / 绕路与返工 / 报错与恢复 / 是否一遍过，**不是**主观"顺畅度"（顺畅度是第一人称，他评给不了也不该假装给）。扣分项必填且**须引 transcript 证据**（如"第 N 段 Edit 报错后才补"），无证据的扣分项按 8 hard-gate 拒。
- **去 self_eval 的代价（诚实）**：丢了"self vs peer 偏差"这个 misalignment 信号（要两者并存才测得出 confab 幅度）。但本项目 [Q-002](../../../.kdev/memory/决策日志.md) 早已放弃 misalignment 数据产出，且用户明确选「他评**替换**自评」而非并存——代价已被接受。

**两层他评（层2 归蒸馏，[Q-017](../../../.kdev/memory/决策日志.md)）**：

| | 层1 · P-C1b recorder 他评（本设计）| 层2 · 蒸馏质量闸（归 `/kdev-memory-distill`，[Q-017](../../../.kdev/memory/决策日志.md)）|
|---|---|---|
| 谁 | 轻量 general recorder（每步顺手）| 蒸馏管道的 audit stage（独立读者，跨步）|
| 何时 | **每步实时**·写时质量闸·在记录里 | **导出/按需**·读时质量闸·在蒸馏入口 |
| 形态 | 升级现有 fire-and-forget 后台 dispatch | 蒸馏批量跨步深读 transcript（workflow-batch 形态）|
| 深度 | 基线：逮明显 confab + 客观执行质量 | 专家级：跨步系统性失真审计 / 校准层1 分 / 标·剔污染样本 |
| 产出去向 | 每步 `### 模型他评` 落记录 | 校准/修正写回记忆 + 产新 misalignment 信号 + 干净切片包 |
| 类比 | 每次 commit 的 linter | 导出训练数据前的质量审计 |

**为什么层2 归蒸馏而非评审专家 mode-2（[Q-017](../../../.kdev/memory/决策日志.md)）**：v0.4 曾把层2 安成 [Q-016](../../../.kdev/memory/决策日志.md) 评审专家 mode-2，复盘改归蒸馏管道质量闸，三条结构性理由：① **同节奏同语料**——蒸馏低频/批量/跨步读全量记忆，层2 深审同 cadence，本就该一趟跑（审完再导）；② **污染正好在蒸馏处放大**——MQ-2 原话"失真会被当信号沉淀进蒸馏原料放大"，伤害在导出成训练数据那刻兑现，质量闸就该装在 garbage-in 入口；③ **mode-2 是别扭嫁接**——评审专家 6+1 标准是评代码/SR/方案的，不是评"记忆诚不诚实"的，记忆审计用的是另一把刀（证据锚定/confab 检测/分数校准）。**附带红利**：蒸馏的 `dataset-misalignment` 切片（原 = 模型自评 vs 用户评分 gap）**被 Q-002（本项目无用户评分）打死已久**，层2 用"层1 基线他评 vs 层2 深度复评"的 gap 复活它——不需要人的新对齐信号。两层仍在两个咽喉卡质量：**写入时（层1）/ 导出时（层2）**。基线 MQ-2 修复在 P-C1b 记录层就完成（不等层2）；层2 是质量升级，blocked-on P-C1b 的 transcript 管道（蒸馏 audit 也要读 transcript）。

---

## 6. 深度他评（层2）= 蒸馏管道质量闸（本 spec 不做，归 Q-017）

v0.3 把"他评"整体推给未来；v0.4 拆两层、基线 per-step 他评落 P-C1b（§5.8 层1）；**[Q-017](../../../.kdev/memory/决策日志.md) 再把层2 的家从"Q-016 评审专家 mode-2"改归蒸馏管道质量闸**（理由见 §5.8 关系厘清）。本节只剩这层"深度/批量"审计，且它已不在本 spec、也不再是评审专家的事——它是 **`/kdev-memory-distill` 的一个 audit stage**。

为什么深度审计天然长在蒸馏管道里（而非常驻评审员工）：

| 深度审计固有属性 | 蒸馏管道恰好提供 |
|---|---|
| 低频/按需（要审/要导才跑，非每步常驻）| 蒸馏本就 ~月1 低频、显式触发 ✅ |
| 跨步成批读真记录 | 蒸馏本就跨步读全量记忆 + transcript ✅ |
| 质量过滤的产物去向 = 训练数据 | 蒸馏产物就是训练切片包，质量闸装在 garbage-in 入口 ✅ |

→ blocked-on P-C1b = 等 P-C1b 的 transcript 溯源管道就绪（蒸馏 audit 也要读 transcript）。本 spec 的 config **不预留** peer_review 字段（深度审计的旋钮归蒸馏管道 / Q-017）。

---

## 7. 执行时间线

| 阶段 | 做什么 | 预估 | 依赖 | 主会话侵入变化 |
|---|---|---|---|---|
| **P-C0.5** | `rating.mode` 可配（机读化 Q-002）+ 默认 user-opt-in + 首次提醒 + 44 半残销账 | 4-6h | 无 | 从"每 Step 必追问"降到 model-only 零追问 / opt-in 轻提一句 |
| **P-C1a** | brief verbosity 分级 + subagent 只回一行 + stop-check 按模式降级 | 4-6h | P-C0.5 | brief 可 compact；subagent 不回长文 |
| **P-C1b** | Step 落盘 = 后台 recorder 读 transcript + **模型他评替换自评**（每步实时 fire-and-forget；commit-tracker stash path+offset；粒度不变）| **spike 1-2h（gate）→ 7-9h** | P-C1a + **§5.6 spike 通过** | 主控付出降到近零；记录层修 MQ-2（§5.8）；为 Q-016 mode-2 铺 transcript 管道 |
| 他评 | 移入后续 roadmap | — | — | — |

### 与阶段2其他 P 的关系

- **P-0**（员工集中 kdev-team）：✅ 已完成
- **P-C0.5/1a/1b**（本方案）：独立于 P-C1（scope 分离），可先行落地减痛
- **P-A**（需求架构师）：依赖 P-C1（scope 分离），不依赖本方案
- **建议**：P-C0.5 立刻起 plan → P-C1a → P-C1b 顺序推进；可与 P-C1 scope 分离并行（都在改 kdev-memory，注意 Step schema 改动的合并顺序）

---

## 8. 非目标（defer，防镀金）

- **深度/专家他评** → [Q-016 评审专家 mode-2](../../../.kdev/memory/决策日志.md)（基线 per-step 他评本期已落 P-C1b，§5.8 层1）
- **重型 Workflow fan-out 作每步 recorder** → 否（§5.0：每步实时不需并行 fan-out + Workflow hook 拉不起 + 会话末批量崩即丢；fan-out 形态归层2 蒸馏质量闸，Q-017）
- **self_eval 与他评并存** → 否（用户选「替换」；§5.8 已诚实记下丢"self vs peer 偏差"misalignment 信号的代价，本项目 Q-002 早已接受）
- **跨会话补录 / cron / `claude -p` 独立进程** → 否（§5.3 论证）
- P-C2 JSONL 操作层（token 痛才上）
- P-C3 并发写锁（阶段3 并行员工）
- scope 分离（另见阶段2 P-C1 spec）
- 评分"对错"判定（kdev-memory 只管如实捕获主观感受）
- 给 recorder 补 git diff 等代码上下文以加深评审深度（属他评 roadmap）
