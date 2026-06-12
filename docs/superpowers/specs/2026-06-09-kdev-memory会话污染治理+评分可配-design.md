# kdev-memory 会话污染治理 + 评分模式可配 设计稿

| 项 | 值 |
|---|---|
| 文档性质 | **设计稿 v0.3**（§5/§6 头脑风暴收敛 → variant 拍板 Q-015；待 §5.6 spike 后起实施计划）|
| lifecycle | design |
| 日期 | 2026-06-12（v0.3：P-C1b variant 拍板 + §5.6 去风险）/ 2026-06-10（v0.2 修订）/ 2026-06-09（v0.1 初稿）|
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
| 7 | Step 落盘机制 | **variant (a) per-step + transcript 溯源 + 会话内 fire-and-forget**（[Q-015](../../../.kdev/memory/决策日志.md)；否 (b) workflow-batch，见 §5.0）；**§5.6 transcript 可达性 spike-gate 先验后建** | 干掉主会话手写 YAML；(b) 自评无源/切分重建/launch 不可靠/丢实时四败；污染 ~1500 tok/会话（可忽略，§5.3 已判）|
| 8 | Step 切分 | **沿用现有粒度（工作单元，比 commit 粗）；commit 不当边界** | TDD/subagent-driven 爆量 commit 必须塌缩在一个 Step 内 |
| 9 | 他评 | **移入后续 roadmap**；形态采 **workflow-batch fan-out**（承接 (b) 的直觉，§6）| right-size 先验证 P-C0.5/1a/1b；他评 = 独立读者读真 transcript/diff，正是 workflow-batch 的天职 |

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

## 5. P-C1b：Step 落盘 transcript 溯源化（会话内 fire-and-forget）

**前置**：P-C1a

这是 v0.1「独立记忆智能体」塌缩后的形态——**不是新架构，是现有 dispatch 模型的一次精简 + 溯源化**。

### 5.0 机制 variant 拍板：(a) per-step 溯源 ✅ vs (b) workflow-batch ❌（Q-015）

头脑风暴提出两条路。**拍板 (a)**，理由是 (b) 在四个维度付代价、只在一条已判可忽略的轴上赢：

| 维度 | **(a) per-step + 溯源 ✅** | (b) workflow-batch ❌ |
|---|---|---|
| 形态 | 主会话工作单元边界写 ~5 行指针 + fire-and-forget dispatch；recorder 读该段 transcript | commit 锚点切段 → 主会话 launch 1 Workflow → 后台 fan-out N recorder → 批量写 |
| **自评分来源** | 主会话**当场第一人称**给（在上下文里）| **无源**：要么会话末补写 N 份自评（= 要干掉的 YAML 延后），要么 workflow 从 transcript 生成（滑向他评 + segmenter 判它没目击的工作）|
| **切分权威** | 主会话**在场当场**划边界（§5.4 / G-008）| 事后 batch segmenter 须**重建从未目击的工作单元边界**；commit≠工作单元（G-008）→ 错更多 |
| **可靠性** | hook nudge + fire-and-forget，**环境常驻** | Workflow 须**显式 opt-in launch、一次性脚本、hook 拉不起**：会话末批量→崩/关即丢（= §5.3 否掉的"末会话永不补录"）；on-demand→用户得记着喊；下会话补录→§5.3 已否 |
| 实时性 | 实时，下会话 brief 天然准 | 延迟，丢实时 |
| 主上下文污染 | ~600–1500 tok/会话（§5.3 判可忽略）| 1 launch + 1 通知，更低——但**赢在已判可忽略的轴上** |

**结论**：(b) 唯一赢点是边际的，论证形状跟 §5.3 否掉 variant C（跨会话补录）一模一样——**workflow-batch 是 C 的表亲**。但 (b) 的 fan-out 直觉没浪费：它 **reframe 到他评**（显式 / on-demand / 独立读者 / 批量正是他评的天职），见 §6。

> ⚠️ **字母别混**：§5.3 用 (B)/(C) 是另一根轴——其 **(B) 会话内 dispatch ≈ 本节 (a)**（都是会话内实时）；本节 **(b) workflow-batch 像的是 §5.3 的 (C) 跨会话补录**（显式 launch / 延迟 / 末会话丢失同病），故称"表亲"。

### 5.1 与今天的唯一区别

| | 今天 | 改后 |
|---|---|---|
| 触发 | commit-tracker 攒 pending + brief/Stop nudge | **不变**（复用，见 §5.5 调参）|
| 切分权威 | 主会话"工作单元完成 → dispatch"判断 | **不变**（见 §5.4）|
| 主控付出 | 写 ~30 行事实 YAML 喂 subagent | 写 ~5 行**指针**（自评分&扣分项 + 标题意图 + Q/G 指针；transcript 范围/路径 recorder 自取，见 §5.2/§5.6）|
| subagent 取数 | 从 YAML | **读 transcript 原件**自行抽执行事实 |
| 返回 | 审计摘要 | 一行确认 |

那 ~30 行事实 YAML（最大 token 源）消失，换成 ~5 行指针。新增的唯一机制：**commit-tracker hook 在 commit 那刻多记 `transcript_path` + offset**（写到哪了）进 state 文件，作为范围素材 + 路径来源（详见 §5.6 解 v0.2 待验证点）。

### 5.2 dispatch 载荷（主控付出的全部）

```yaml
# transcript_path + offset 范围由 recorder 从 state 文件自取（见 §5.6），不经此指针传
title_intent: <一句话，模型知道这步在干嘛>
self_eval_score: 4                               # model-only 下唯一绑主会话的；MQ-2 残留敞口仅此项（§5.8）
self_eval_deduction: <扣分项，必填——主会话当场给，比今天 subagent 从 summary 反推更不易 confab>
key_decision_pointers: [Q-012, G-005]            # 编号或一句话，非全文
```

recorder 从 state 文件取 `{transcript_path, range}` → 读该段 → 抽工具数/报错/绕路/文件/commit SHA → 写四段（model-only：用户评分段按 §3.3 留空 voided-faded）→ 一行返回。指针只剩 3 项语义（标题/自评/决策指针），transcript 范围与路径都不再手填。

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

1. **hook 侧 stash**——commit-tracker（PostToolUse on Bash，已在每次 commit 写 `state/pending-commits.json`）**顺手把 `transcript_path` + 当前 offset 也写进同一 state 文件**。hook 的 stdin 本就含 `transcript_path`（subagent 拿不到、hook 拿得到——这正是必须由 hook 捕获的原因）。
2. **recorder 侧自取**——recorder 从 state 文件读 `{transcript_path, last_recorded_offset → current_offset}`，自行 `Read` 该段 JSONL。主会话指针里**不出现路径**。
3. **offset 语义**——transcript 是 JSONL（一行一 message）。offset 取行数（commit 那刻 `wc -l`）即可；range = [上次已记录, 当前]。粒度是工作单元（粗），±几条 message 的 slop 可容忍。

**⚠️ spike-gate（实施前必跑，承 [G-008](../../../.kdev/memory/踩坑日志.md) / R-009「先核代码再信设计」）**——本项目实地发现 hooks 里 `toolInput`(commit-tracker) 与 `tool_input`/`session_id`(别处) **驼峰/蛇形混用**，是"hook 输入契约从没对真实 harness 核过"的直接物证。故 P-C1b 起 plan **前**先跑一个小 spike 实测三件事，过了再建：

| # | 验什么 | 通过判据 |
|---|---|---|
| 1 | PostToolUse hook stdin 真有 `transcript_path`，且确认字段真名（顺带纠 `toolInput`/`tool_input` 混用）| 打印 stdin 见到该键且指向真实存在文件 |
| 2 | transcript JSONL 能按 offset 切段读出该工作单元的工具调用/报错/文件 | 取一段已知工作单元，offset range 读出内容与记忆吻合 |
| 3 | fire-and-forget 派出的 subagent 能 `Read` 那个路径（权限/路径可达）| subagent 成功读回该段并抽出 ≥1 个真实 commit SHA |

spike FAIL（如路径不可达 / 格式不可解）→ P-C1b 退回讨论，不硬上。

**残留取舍**（机制确定后仍在的）：

| 优点 | 缺点/风险 |
|---|---|
| 干掉 30 行 YAML，主会话付出降一档 | recorder 读 transcript 抽错 → 高置信度垃圾（靠 8 hard-gate + 不确定字段显式标注兜）|
| 实时，续航天然准，无跨会话延迟 | recorder 读长 transcript 在**其自身**上下文有成本（按 offset 只读增量段优化）|
| 小改动、低风险（复用现有 commit-tracker + state 模式）| offset 精度：PostToolUse hook 触发时 transcript 可能尚未 flush 最末几条（slop 可容忍，spike #2 量化）|
| 无 `claude -p` / cron / 跨会话机制 | — |

### 5.7 预估工作量

- **spike（gate，前置）**：~1-2h（实测 §5.6 三件事）
- **实施（spike 过后）**：~6-8h（commit-tracker stash transcript_path+offset 改造 + step-recorder prompt 改 transcript 溯源 + nudge 调参 + 测试）

### 5.8 溯源对 MQ-2（自评 confabulate）的买下（连 §6 他评）

[roadmap §1.5.7 MQ-2](../../framework/01-design/2026-06-06-01-数字员工整体设计路线图roadmap-v1.0.md) 实证：Step main-69 的模型自评**凭空编造**一个扣分项，根因是 subagent 写自评时**没读真实 transcript、据 summary 反推"听起来合理"**。

溯源(a) 直接消掉这个根因：

- **杀事实性 confab**——recorder 读真 transcript，工具调用/报错白纸黑字，编不出"grep 漏看 X"。这是 MQ-2 那次失真的**精确解**。
- **recorder 本就独立于主会话**——它从 transcript 写的事实叙述已是**轻度他评**；残留同进程偏差**收窄到只剩主会话给的 self_eval 数字 + 扣分项**一项。
- **互补非替代**：溯源 = "自己读真记录"（破事实 confab，自评分仍同进程自判）；**他评 = "独立 agent 读真记录"**（连同进程判断偏差一起破，§6）。溯源是免费的**部分买下**，他评补那最后一公里——两者叠加，不互斥。

---

## 6. 他评智能体（移入后续 roadmap，本 spec 不做）—— workflow-batch 在此安家

模型自评有锚定偏差（倾向自我表扬），未来可加"调另一模型读 transcript 做独立评审"的能力，产出 `peer_score` / `peer_verdict` 落 Step。但：

- 当前 right-size 优先验证 P-C0.5/1a/1b
- 涉及额外 token、评审深度（只能读文字不能看代码）等取舍，需独立设计
- **→ 记入数字员工集群后续 roadmap（[§1.5.8 第三方他评 / 评审专家](../../framework/01-design/2026-06-06-01-数字员工整体设计路线图roadmap-v1.0.md)），届时单独起 spec**

**reframe（v0.3 新增）**：§5.0 否掉的 workflow-batch **不是没用，是指错了活**——它的 fan-out 形态正是他评的天职：

| 他评固有属性 | workflow-batch 恰好提供 |
|---|---|
| 显式按需（你想 review 才 review，非每步常驻）| Workflow 必须显式 opt-in launch ✅（对 Step落盘是缺口，对他评是**正合适**）|
| 独立读者 | 后台 fan-out N 个独立 agent，各读真 transcript/diff ✅ |
| 成批 | 对一段工作批量出 `peer_score` ✅ |

→ **§5.0 里 (b) 的 launch 时机难题（会话末/on-demand/下会话）迁到这里**：在他评里 **on-demand / 显式** 是天然 fit，那个让 Step落盘 不可靠的"显式 launch 缺口"在他评场景**自动消失**。溯源(a) 已部分买下 MQ-2（§5.8），他评补最后一公里（self_eval 数字的同进程偏差）。

本 spec 的 config **不预留** peer_review 字段（避免 schema 提前复杂化）。

---

## 7. 执行时间线

| 阶段 | 做什么 | 预估 | 依赖 | 主会话侵入变化 |
|---|---|---|---|---|
| **P-C0.5** | `rating.mode` 可配（机读化 Q-002）+ 默认 user-opt-in + 首次提醒 + 44 半残销账 | 4-6h | 无 | 从"每 Step 必追问"降到 model-only 零追问 / opt-in 轻提一句 |
| **P-C1a** | brief verbosity 分级 + subagent 只回一行 + stop-check 按模式降级 | 4-6h | P-C0.5 | brief 可 compact；subagent 不回长文 |
| **P-C1b** | Step 落盘 transcript 溯源化（**variant (a) per-step**；会话内 fire-and-forget；commit-tracker stash path+offset；粒度不变）| **spike 1-2h（gate）→ 6-8h** | P-C1a + **§5.6 spike 通过** | 干掉 30 行 YAML，dispatch 付出降一档；顺带部分买下 MQ-2（§5.8）|
| 他评 | 移入后续 roadmap | — | — | — |

### 与阶段2其他 P 的关系

- **P-0**（员工集中 kdev-team）：✅ 已完成
- **P-C0.5/1a/1b**（本方案）：独立于 P-C1（scope 分离），可先行落地减痛
- **P-A**（需求架构师）：依赖 P-C1（scope 分离），不依赖本方案
- **建议**：P-C0.5 立刻起 plan → P-C1a → P-C1b 顺序推进；可与 P-C1 scope 分离并行（都在改 kdev-memory，注意 Step schema 改动的合并顺序）

---

## 8. 非目标（defer，防镀金）

- **他评智能体** → 后续 roadmap（形态 = workflow-batch，§6）
- **workflow-batch 作 Step落盘机制** → 否（§5.0：自评无源 / 切分重建 / 显式 launch 不可靠 / 丢实时，是 §5.3 variant C 的表亲；其 fan-out 形态改投他评）
- **跨会话补录 / cron / `claude -p` 独立进程** → 否（§5.3 论证）
- P-C2 JSONL 操作层（token 痛才上）
- P-C3 并发写锁（阶段3 并行员工）
- scope 分离（另见阶段2 P-C1 spec）
- 评分"对错"判定（kdev-memory 只管如实捕获主观感受）
- 给 recorder 补 git diff 等代码上下文以加深评审深度（属他评 roadmap）
