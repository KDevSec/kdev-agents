# kdev-memory 会话污染治理 + 评分模式可配 设计稿

| 项 | 值 |
|---|---|
| 文档性质 | **设计稿 v0.2**（讨论收敛 → writing-plans 起实施计划）|
| lifecycle | design |
| 日期 | 2026-06-10（v0.2 修订）/ 2026-06-09（v0.1 初稿）|
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
| 7 | Step 落盘 | **transcript 溯源 + 会话内 fire-and-forget dispatch** | 干掉主会话手写 YAML；污染降到 ~1500 tok/会话（可忽略）；保留实时性，避免跨会话补录的复杂度 |
| 8 | Step 切分 | **沿用现有粒度（工作单元，比 commit 粗）；commit 不当边界** | TDD/subagent-driven 爆量 commit 必须塌缩在一个 Step 内 |
| 9 | 他评 | **移入后续 roadmap**，本 spec 不做 | right-size，先验证 P-C0.5/1a/1b |

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

### 5.1 与今天的唯一区别

| | 今天 | 改后 |
|---|---|---|
| 触发 | commit-tracker 攒 pending + brief/Stop nudge | **不变**（复用，见 §5.5 调参）|
| 切分权威 | 主会话"工作单元完成 → dispatch"判断 | **不变**（见 §5.4）|
| 主控付出 | 写 ~30 行事实 YAML 喂 subagent | 写 ~5 行**指针**（transcript 范围 + 自评分&扣分项 + 标题意图 + Q/G 指针）|
| subagent 取数 | 从 YAML | **读 transcript 原件**自行抽执行事实 |
| 返回 | 审计摘要 | 一行确认 |

那 ~30 行事实 YAML（最大 token 源）消失，换成 ~5 行指针。新增的唯一机制：**commit-tracker hook 多记一个 transcript offset**（commit 那刻 transcript 写到哪），作为范围素材。

### 5.2 dispatch 载荷（主控付出的全部）

```yaml
transcript_range: <上次已记录 offset> → <当前>   # recorder 读这段抽事实
title_intent: <一句话，模型知道这步在干嘛>
self_eval_score: 4                               # model-only 下唯一绑主会话的
self_eval_deduction: <扣分项，必填>
key_decision_pointers: [Q-012, G-005]            # 编号或一句话，非全文
```

recorder 读 transcript 范围 → 抽工具数/报错/绕路/文件/commit SHA → 写四段（model-only：用户评分段按 §3.3 留空 voided-faded）→ 一行返回。

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

### 5.6 取舍

| 优点 | 缺点/风险 |
|---|---|
| 干掉 30 行 YAML，主会话付出降一档 | recorder 读 transcript 抽错 → 高置信度垃圾（靠 8 hard-gate + 不确定字段显式标注兜）|
| 实时，续航天然准，无跨会话延迟 | recorder 读长 transcript 在**其自身**上下文有成本（一次性，可按 offset 只读增量段优化）|
| 小改动、低风险（复用现有 nudge）| transcript 偏移量记录需 commit-tracker hook 改造 + 实测 |
| 无 `claude -p` / cron / 跨会话机制 | — |

### 5.7 预估工作量

~6-8 小时（commit-tracker offset 改造 + step-recorder prompt 改 transcript 溯源 + nudge 调参 + 测试）

---

## 6. 他评智能体（移入后续 roadmap，本 spec 不做）

模型自评有锚定偏差（倾向自我表扬），未来可加"调另一模型读 transcript 做独立评审"的能力，产出 `peer_score` / `peer_verdict` 落 Step。但：

- 当前 right-size 优先验证 P-C0.5/1a/1b
- 涉及额外 token、评审深度（只能读文字不能看代码）等取舍，需独立设计
- **→ 记入数字员工集群后续 roadmap，届时单独起 spec**

本 spec 的 config **不预留** peer_review 字段（避免 schema 提前复杂化）。

---

## 7. 执行时间线

| 阶段 | 做什么 | 预估 | 依赖 | 主会话侵入变化 |
|---|---|---|---|---|
| **P-C0.5** | `rating.mode` 可配（机读化 Q-002）+ 默认 user-opt-in + 首次提醒 + 44 半残销账 | 4-6h | 无 | 从"每 Step 必追问"降到 model-only 零追问 / opt-in 轻提一句 |
| **P-C1a** | brief verbosity 分级 + subagent 只回一行 + stop-check 按模式降级 | 4-6h | P-C0.5 | brief 可 compact；subagent 不回长文 |
| **P-C1b** | Step 落盘 transcript 溯源化（会话内 fire-and-forget；commit offset；粒度不变）| 6-8h | P-C1a | 干掉 30 行 YAML，dispatch 付出降一档 |
| 他评 | 移入后续 roadmap | — | — | — |

### 与阶段2其他 P 的关系

- **P-0**（员工集中 kdev-team）：✅ 已完成
- **P-C0.5/1a/1b**（本方案）：独立于 P-C1（scope 分离），可先行落地减痛
- **P-A**（需求架构师）：依赖 P-C1（scope 分离），不依赖本方案
- **建议**：P-C0.5 立刻起 plan → P-C1a → P-C1b 顺序推进；可与 P-C1 scope 分离并行（都在改 kdev-memory，注意 Step schema 改动的合并顺序）

---

## 8. 非目标（defer，防镀金）

- **他评智能体** → 后续 roadmap
- **跨会话补录 / cron / `claude -p` 独立进程** → 否（§5.3 论证）
- P-C2 JSONL 操作层（token 痛才上）
- P-C3 并发写锁（阶段3 并行员工）
- scope 分离（另见阶段2 P-C1 spec）
- 评分"对错"判定（kdev-memory 只管如实捕获主观感受）
- 给 recorder 补 git diff 等代码上下文以加深评审深度（属他评 roadmap）
