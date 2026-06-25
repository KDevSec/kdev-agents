# P-C2 JSONL 操作层 / token 优化 设计稿

| 项 | 值 |
|---|---|
| 文档性质 | **brainstorming 设计稿 v1.0**（待用户复核 → writing-plans）|
| lifecycle | design |
| 日期 | 2026-06-13 |
| 范围 | kdev-memory 如何在「多员工 + 跨会话 + 多写手」下记 Step：两层表示（事实流水复用 / 叙事派生）+ 收窄叙事到 CEO + 目录生命周期 + 会话身份 + 多写手轴 + **Step ID 换时间戳原语**。**只设计不实施。** |
| 承 | [Q-011 阶段2 接入设计](./2026-06-07-阶段2-第二员工+记忆scope-design.md)（§8 把 P-C2 列 defer）· [Q-015 P-C1b transcript 溯源+模型他评](../../../.kdev/memory/决策日志.md) · [G-011 worktree slug 撞号](../../../.kdev/memory/踩坑日志.md) · [R-009 先核代码再信设计](../../../.kdev/memory/改进建议.md) |
| 配套 | [记忆底座 合稿 v1.0 §3/§4/§5/§6/§7/§9.6](../../framework/01-design/2026-06-10-05-KDev数字员工-记忆底座-合稿-v1.0.md) · [P-C1b 污染治理 spec v0.5](./2026-06-09-kdev-memory会话污染治理+评分可配-design.md) · [roadmap §1.5.8](../../framework/01-design/2026-06-06-01-数字员工整体设计路线图roadmap-v1.0.md) |
| 产出决策 | **Q-019**（P-C2 核心：边界/收窄/触发/他评/时机）· **Q-020**（Step ID 换时间戳 + slug 退役 + 冻结迁移）|
| defer（不在本期实施）| P-C3 并发写锁 · 多协作者 collaborator scope 实建 · 跨机 machine-id 进 ID · 蒸馏质量闸（Q-017）|

---

## ⚠️ 实施状态（2026-06-25 回写，spec→canonical 铁规）

> 本 spec 原为 **design 稿（只设计不实施）**。其 **JSONL 主账部分已在 kdev-memory 落地**，本节记录实施现状与**与本稿设计的关键分叉**，正文 §1–§9 保留为原始设计意图（**勿删**），以本节为实施口径的权威覆盖。

| 项 | 现状 |
|---|---|
| **JSONL 操作层 + 叙事 Step 主账** | **已实施**（Phase A 基座 `step_log.py` 7 hard-gate + dual-read `step_dualread.py`；Phase B recorder→jsonl + `daily_render.py` 承重墙，commits a8377a6→5953083 区间的 P2 部分）|
| **md↔jsonl 切换立场** | ⚠️ **kdev 采 C1「永久 dual-read」，故意分叉本稿/ieidev 的硬切**（**Q 20260625-173847-ly1989abc**）：历史 Step 留 `执行日志.md` **冻结·经 `step_dualread.py` 与 jsonl 永久 dual-read（md∪jsonl 并集）**，**存量 md 不迁移、md-read 不退、md 不重命名为 archive**。ieidev 同源迁移走 jsonl-only 硬切（丢 md）——两插件**立场相反**，kdev 是 deliberate 分叉，不是同步落后 |
| **Step ID 撞号（G-011）** | ✅ **根因已随 Q-020 时间戳 minting 退役（live）**：`mint_record_id` 用 `<YYYYMMDD-HHMMSS>-<who>`，slug/counter 退役；多 worktree/多机/多会话不再撞号 |
| **执行日志月度切档** | **已下线**（无 jsonl 月度 rotation 通道，`archive_hint.py` 的 Step 月度 gate off；决策/踩坑季度 markdown 切档仍照常）|
| **存量 md 迁移 + 版本 0.19.0 发布** | **待另一会话 BUG 修复后统一做**（本次只做代码落地 + 文档对齐 C1）|

> ⚠️ 文档已对齐 C1：[SKILL.md](../../../plugins/kdev-memory/skills/kdev-memory/SKILL.md) + references（[六类记录-schema.md §3](../../../plugins/kdev-memory/skills/kdev-memory/references/六类记录-schema.md) / [切档与归档.md](../../../plugins/kdev-memory/skills/kdev-memory/references/切档与归档.md) / [markdown-切片导出.md](../../../plugins/kdev-memory/skills/kdev-memory/references/markdown-切片导出.md) / [自动化机制-hooks.md](../../../plugins/kdev-memory/skills/kdev-memory/references/自动化机制-hooks.md)）均加 Phase 2 · C1 声明，引用本决策号。
>
> 📌 与本稿 §0.5 row3「Step ID 退役 slug/counter，换时间戳原语」一致（已实施）；本稿其余收窄设计（员工叙事砍掉、staff 稀疏、events 只读复用）仍属 **defer**，未在本次 JSONL 主账迁移实施范围内。

---

## 0. 一句话

P-C2 把 kdev-memory 的记账拆成**两层表示**——廉价**事实流水**（**只读复用** kdev-core 的 `events.jsonl`，按 `actor` 过滤出员工视图，不造第二本账）供 agent 高频低成本召回；重 **markdown 叙事 Step 退化成「仅 CEO/shared 一根、从 events+handoffs+transcript 周期性派生」的薄加料层**（只承载机器给不了的他评/评分/经验/续航 + 兜 off-flow）。配套把 **Step ID 从「顺序整数」换成「时间戳 + 人前缀」**，从根上消除分布式写手的撞号问题（G-011）。

---

## 0.5 本稿与既有设计的关系（修订了什么）

| # | 既有设计 | 本稿修订 | 理由 |
|---|---|---|---|
| 1 | 记忆底座 §5.3 row3：Step 执行 rollup 落 `/staff/<员工>/` + shared | **砍掉 per-员工叙事 rollup**：叙事仅 CEO/shared；员工 = events + handoffs（无叙事 Step）| 落地产物在 handoffs（md 可读）、员工内部「做了啥」在 events——员工不需要叙事；叙事只为人（CEO 呈现）|
| 2 | 记忆底座 §4 目录图：`staff/{ceo,req,dev,test,reviewer,cqo}/` 全家桶 | **staff 稀疏**：仅 `reviewer`（F-NNN 评审经验）+ `cqo`（审计报告）；dev/req = 机器侧无 kdev-memory 足迹；ceo = shared | 收窄后只有「有真·非机器记录」的 scope 才建目录 |
| 3 | v0.11 `Step <branch-slug>-N`（step_id.py）+ 记忆底座 §4 line113 / §9.6 #5 | **Step ID 退役 slug/counter，换时间戳原语**（Q-020）| 顺序整数假设单一发号权威，架构刻意分布式（counter 机器本地 + 条目 git 同步 + 多写手）→ 全局序号不可满足；G-011 是其实锤 |
| 4 | 记忆底座 §6「N 员工 × M 动作 × 600 token 爆炸」需两层缓解 | **爆炸被结构消除**（员工压根不写重 Step），非「拆分缓解」；P-C2 价值收窄到 recall 效率 + CEO 叙事覆盖委派 + ID 硬化 | 收窄模型下 token 痛不再是主驱动力 |

> 与「markdown 主存不引入 JSONL」旧决策不冲突（记忆底座 §8）：那条管**叙事/蒸馏层**（markdown 仍是该层主存）；P-C2 是**只读消费** kdev-core 既有 JSONL 操作层，不新写。

---

## 1. 问题陈述：P-C2 解决什么

从「单人单轨」走向「多员工并行 + 跨会话」时：

1. **token 经济性**：每个工作单元手写一条 ~500-600 token 的 4 段重 Step（执行事实/他评/评分/差异），单轨低频没问题，但其中**大半是机器事实**（做了哪步/过了哪 gate/谁干的），agent 召回根本不需要 4 段叙事。
2. **撞号/分裂**：Step ID 顺序整数 + slug 按 cwd 现算 → 多 worktree/多机/多会话下 ID 自相矛盾、不连号、孤儿（G-011 实锤）。
3. **身份含糊**：「新会话是 CEO 还是单人」「2 个会话并行咋记」「装了员工 memory 怎么变」没有明确答案。

P-C2 一次性回答这三件，地基焊死后再谈实施。

---

## 2. 收窄模型：三本账，各归其位（核心）

| 账 | 内容 | 谁产 | 形态 | 给谁看 | 落位 |
|---|---|---|---|---|---|
| **events.jsonl** | 做了啥（机器事实，行内 actor）| 全员工 | JSONL 廉价 | agent 召回 | kdev-core `features/<slug>/`（已存在）|
| **state.json** | 在哪步 / resume（控制态）| 编排 | JSON | 引擎续跑 / brief 扫活动 feature | kdev-core `features/<slug>/flow-state.json` |
| **handoffs/<员工>/** | 产出啥（交付物）| 全员工 | **md 可读** | 人 + 下游员工接力 | kdev-core `features/<slug>/handoffs/` |
| **markdown Step** | 讲给人听（叙事 + 加料）| **仅 CEO/shared** | 4 段重 | CEO 呈现给人 | kdev-memory（flat root / shared）|

**关键命题**：
- **机器三件套（events + state + handoffs）= 完整的机器任务过程**，权威，agent 召回/resume/审计够用 → **别再 markdown 重叙一遍**（§7 不造第二本账）。
- **叙事 Step ≠ 重记任务过程**，是「在机器过程之上，加机器**结构上发不出来**的四样 + 链回机器三件套」：
  1. **质量信号**（模型他评/用户评分）——`gate PASS` 只说过了、不说"够呛但放过、差在 X"；
  2. **理由/经验**（为什么这么决策、踩了什么坑）——机器流里没有"为什么"；
  3. **人读的蒸馏续航**（brief/每日汇总/训练原料）——raw events 人读不动、蒸馏不出带标签数据；
  4. **off-flow 工作**——没跑 kdev-core flow 的活（CEO↔人对话/随手改）根本没有 events/state。
- ⚠️ `state.json`（kdev-core 机器任务态 `current_node`/resume）**≠** `当前状态.md`（kdev-memory 的 CEO 续航 `current_step`/pending/给人看）——两个 "current" 不同物，不合并（记忆底座 §0.5 row6）。

---

## 3. P-C2 真正建什么（4 件）

收窄后体量小了一圈，落到四件：

1. **Recall reader**：`recall(scope, node)` 跨 `features/*/events.jsonl` 按 `actor==scope` + `node` 过滤捞行，返回廉价事实切片；agent/CEO 不再 load 重 markdown。**flat / off-flow 无 events → 退回 transcript**（P-C1b 路径），不报错。
2. **CEO recorder 升级（读 events + handoffs）**：多人模式下 CEO 委派给 subagent，**细节不在 CEO 自己 transcript 里**，而在 events + handoffs。故 CEO 叙事 Step 的「执行事实」改从 **events + handoffs manifest 派生（委派工作）+ transcript（CEO 自己的推理/决策）**。这是 P-C1b 的延伸。
3. **Step ID 时间戳化 + slug 退役**（§11 / Q-020）。
4. **Workflow cache 借鉴**：rollup 派生做成**幂等 + 可续跑的 range-keyed 派生缓存**（§6）。

---

## 4. 两层表示 + 粒度分流铁律

| 层 | 谁写 | 内容 | 粒度 | token |
|---|---|---|---|---|
| 事实流水 = `events.jsonl` | kdev-core（零改）| transition / gate，行内 actor | flow 节点/gate 级（≈Step 粗，~10-20/run）| ~30/行 |
| 叙事 rollup = markdown Step | kdev-memory（派生）| 4 段（执行事实+他评+评分+差异）| 工作单元（比 commit 粗，承 P-C1b §5.4）| ~500-600 |

**分流铁律（§7「不双记」落地）**：
- **凡镜像机器原始态**（做了哪步/过了哪 gate/谁干的）→ 已在 `events.jsonl`，**不再单独成 Step、不再叙述第二遍**。
- **凡是「加料」维度**（他评/评分/经验/叙事）→ 机器流水给不了，**才**进 markdown Step。
- **commit 绝不当 Step 边界**（承 P-C1b）；切分权威仍是「工作单元完成」判断。TDD/subagent 爆量动作塌缩进一个 Step。

> **接受 events = flow-节点粒度**（Q-019），不给 kdev-core 加 capability 级事件：细粒度 tool 调用活在各 subagent transcript（短暂、不需跨会话持久），需要持久的是 flow 骨架 + handoff 产物，events 已 captured。

---

## 5. Recall reader

- **scoped/体系内**：读 `events.jsonl`（actor 过滤 = 员工 canonical id，与 events 行内 actor 同轴）+ transcript 补「人↔CEO」段。
- **flat / off-flow（无 events）**：退回 transcript（P-C1b），不报错。
- `actor` 用 canonical 员工 id（kdev-core 写的，稳定）→ 跟 memory scope 同一根稳定轴。
- **效率赢点**：agent 醒来「我在这 feature 干到哪了」= 读廉价 events 切片，不 load 247KB+ 重 markdown。

---

## 6. Rollup deriver + 触发 + Workflow cache 借鉴

**派生一次** = 读某 scope 自上次 rollup 以来的 events（actor 过滤）+ handoffs manifest + transcript 段 → 出**一条** CEO 叙事 Step（执行事实蒸馏 + 加料）→ 写 shared/执行日志.md。

**触发（主 + 备）**：
1. **阶段边界**（主）：node 里程碑 / gate PASS——自然停顿，对齐「工作单元」。
2. **每日**（兜底）：跨整天会话用。
3. **按需**：用户说「写总结」/ agent 显式请求。
4. **事件阈值**（backstop）：单 scope 累积 ≥N events 未 rollup → 提醒（防长流程漏派生）。N 实施期定。

**Workflow cache 借鉴 —— 幂等可续跑的 range-keyed 派生缓存**：
- rollup 是 append-only 事件流上的派生 → 新 rollup 只需「上次 offset 之后的 events」，正是 Workflow「最长未变前缀只跑增量」那套，把 `(prompt,opts)→cached-result` 搬到 `(events offset 区间)→派生 rollup`。
- **P-C1b 已有原语**：hook 把 `transcript_path + since_offset` stash 进 state（pending-commits.json）。P-C2 泛化：从 transcript-offset 扩到 events-offset，并让派生结果可缓存 → rollup **幂等 + 可续跑**（dispatch 中途挂了从上次 offset 续，不重派 LLM）。
- ⚠️ **机制换、语义借**：Workflow journal 是内存/同会话/runId 域；kdev-memory 要跨会话 + 跨机（git 同步）+ **落盘**。故盘 disk-backed 在 `state/`（像 pending-commits.json），不套 workflow runtime。
- prompt-cache 5min TTL = 机会主义小赢（rollup 多稀疏、多半冷），不当设计支柱。

> 深层 parallel：Workflow = 廉价确定性控制流 + 只在 agent() 点付昂贵 LLM、memoize；P-C2 两层拆分 = 同一形状落到记忆——廉价确定性事件流 + 只在 rollup 点付 LLM、按 range memoize。借 cache 不是 bolt-on，是认出 P-C2 本就是 Workflow 哲学的记忆版。

---

## 7. 他评归位

- **高频 JSONL 动作零他评。** 给每条 event 配他评 = 把省下的 token 又烧回去，否。
- 他评只活在 **Step rollup 粒度**：
  - **P-C1b**（已 done）= per-step recorder 读 transcript 出**轻量模型他评**（基线层/层1）；
  - **层2 深度他评** = 蒸馏管道质量闸（[Q-017](../../../.kdev/memory/决策日志.md)，导出时审计）。
- 两层他评都吃 **Step**，不吃 raw events。

---

## 8. 目录结构 + 生命周期（安装 / 启用 / 迁移）

### 8.1 两状态，切换认「启用」不认「安装」

| 状态 | kdev-team | memory 布局 |
|---|---|---|
| 状态0 | 没装 / **装了但没启用** | **flat**（root 直放，= 现状）|
| 状态1 | **启用**（显式跑 `migrate_scope.py` / 首次跑员工 flow）| **scoped**（shared/ + staff/）|

- **切换闸 = 「启用」（显式迁移），不是「安装」**。装 kdev-team 对 memory **零副作用**。
- **本就是现状**：`migrate_scope.py` 手动、不自动跑、不在框架仓跑；本框架仓此刻装着/正在开发 kdev-team，memory 却故意 flat（阶段2 决策#3）——「装了 ≠ scoped」的活证据。
- 理由：装插件不该悄悄重构 memory 目录（侵入/意外）；flat→scoped 是「我要上多员工了」的有意动作；也允许「装着但继续单轨用」。

### 8.2 收窄后的稀疏目录

```
.kdev/
├── memory/                              ← kdev-memory（叙事/经验层）
│   │  【锚1·永远在】人面向叙事轨 = 主控/CEO 单轨（off-flow 兜底全集）
│   ├── (flat)   执行日志.md 决策日志.md 踩坑日志.md skill-feedback.md 当前状态.md 改进建议.md
│   └── (scoped) shared/<上述同款>        ← flat 迁移后整体变这里
│   │  【按需·稀疏】只为有「非机器记录」的 scope 而建（scoped 才有）
│   ├── staff/reviewer/                   ← F-NNN 评审经验（飞轮，记忆底座 §5.2）
│   ├── staff/cqo/                        ← 审计报告
│   │     （✘ 无 dev/req/ceo —— dev/req 机器侧无足迹；ceo = shared）
│   │  【多人才有】每协作者一根叙事续航轨（§10）
│   ├── collaborators/<email-prefix>/     ← per-人续航；单人时塌进 shared
│   └── state/ checkpoints/ dataset/ config.yaml   ← 机器本地 plumbing，恒在 root
└── features/<slug>/                      ← kdev-core（机器层）；【按需·0..N】开 feature 才出现
    ├── flow-state.json · events.jsonl · handoffs/<员工>/
```

### 8.3 迁移语义（flat → scoped）

- **flat 内容保留、整体变 `shared/`**（`migrate_scope.py` 实测 `shutil.move`）。语义正中收窄：单人那本 memory 就是 CEO/人 单轨叙事 = 项目时间线 = shared（记忆底座 §5.1 CEO 是 shared 叙事管家）。
- **员工另起空目录、不回填**（不把旧 CEO 工作追认成员工的）。
- **plumbing（state/checkpoints/dataset/config）留 root**，不随 scope 迁。
- ⚠️ **要改两处**（实施期）：`migrate_scope.py` 的 `DEFAULT_STAFF=["dev-engineer","req-architect"]` → 稀疏/按需（reviewer、cqo，或默认空）；记忆底座 §4 全家桶目录图收窄成 §8.2。
- **启用触发** = 显式（手动 migrate / 首次员工 flow 时**提示**用户，记忆底座 §9.4 风格），**绝不 install 时静默迁**。
- **回退单人** = 不用反向迁移；scoped 优雅降级（shared/ 单人照用）。

---

## 9. 会话身份 + 开/未开 feature

### 9.1 会话身份只有一个：主控（= 有员工时叫 CEO）

- 新开会话**永远是同一个身份**：跟你对话的主循环（主控）。「CEO」不是另外的东西，是主控在「员工框架启用时」的名字。
- **不存在「这次 CEO / 那次单人」两种会话模式**——同一主循环，区别只在「员工词汇启没启用」。
- **员工（dev/req/reviewer）永远不是会话身份**，是主控会话内派的 subagent；无法「以 dev-engineer 身份开会话」。
- 新会话 = 同一主控**醒来**（SessionStart brief 读 `当前状态.md` 续上），不是换了个人。员工无需会话级上下文——其记忆是 events+handoffs（落盘 features/），下次派单自己 recall。
- ⇒ flat 的 `当前状态.md` ↔ 迁移后 `shared/当前状态.md` 无缝同一根连续轨。

### 9.2 真正变化的轴 = 开/未开 feature（与身份正交）

| | 未开 feature（off-flow）| 开 feature（in-flow）|
|---|---|---|
| 例 | 头脑风暴 / 答疑 / 随手改 / **就是本类对话** | 走 coding/design-flow 在某功能上派员工 |
| 机器记录 | **无** events/state/handoffs | features/<slug>/ 全套 |
| 留痕 | 只在 transcript → CEO 叙事 Step（P-C1b）| events+state+handoffs + 叙事链回 |
| 占比 | **今天绝大多数**（247KB 执行日志几乎全是这个）| 启用员工后才多 |

**设计铁律**：memory **不能假设每段活都有 feature/flow**。
1. 人面向叙事轨（flat root | shared/）是 **off-flow 的兜底全集**；features/ 只为 in-flow 而生、按需 0..N。
2. features/ 与 flat/scoped **正交**（kdev-core 独立于 kdev-team）——单人借 kdev-core flow 也会出现 features/。
3. `当前状态.md` **链向活动 features 不镜像**（记忆底座 §3 line71）：`current_step`（叙事）+ 列活动 feature 的 `flow-state` 指针（`current_node`），两个 current 分清。新会话 brief = 读叙事续航 + 扫 `features/*/flow-state.json` 非终态浮出活动 feature。

---

## 10. 多写手轴（多会话 / 多机 / 多协作者）

**核心解耦**：把一直被揉进「slug」的三件事彻底分家。

| 维度 | 同机·多会话 | 跨机·同人 | 多人 |
|---|---|---|---|
| **唯一性** | 时间戳 ID（§11）一律 coordination-free | 同左 | 同左 |
| **归因**（字段，不进命名空间）| email + session-id | + machine-id | + 协作者 email |
| **续航指针** | **per-会话** | per-机器/会话 | per-协作者 |
| **共享 md 安全 append** | 真并发 → **P-C3 锁**（defer）| — | P-C3 |

- **同机·多会话**：时间戳 ID 天然唯一（曾经 flock 计数器也行，但时间戳更省心）；真·并发写同一 md → P-C3 append 锁。
- **跨机·同人**：email 不区分机器；`machine-id`（每 clone 生成一次、落 state/、不进 git、非 cwd 派生）当归因；时间戳保证 ID 不撞。
- **多协作者**：= collaborator scope（per-人叙事续航轨，email keyed，§8.2）+ shared 跨切决策。**单人时塌进 shared**（那唯一的人 = CEO，叙事+决策全在 shared）。
- **同目标并发**（两人 pair 同一 feature 实时协作）= real-time 协同编辑（CRDT 级）→ **明确 out of scope**。

> 会话身份始终是「主控/CEO」角色；「几个人在用」是 scope 的并发维度，不是会话模式分叉。单人 = 1 协作者（塌进 shared）；多人 = N 协作者 scope + shared，复用同一 scope 机器 + P-C3 锁。**P-C2 把身份模型做成可插拔（轨道 key = 写手身份）但不实建多人**——随 P-C3 一起、真有并发写手才上。

---

## 11. 记录 ID 原语：时间戳化（Step + Q/G/R/F，Q-020）

### 11.1 为什么换（根因）

顺序整数 ID 成立前提 = 唯一一个串行发号权威。但架构**刻意分布式**：计数器 `state/` 机器本地不进 git（记忆底座 §5.3 #14）+ 条目 git 同步 + 多 worktree/机/协作者写手 → **「全局 1..N」数学上不可满足** → 撞号是**结构性**的（G-011 实锤）。`N` 从来不是「项目第 N 件事」，是「某写手记的第 N 件」——单写手让 local 看起来像 global，养出错误假设。**Q/G/R/F 同理**：今天 CEO 单写手让它看似安全，但多协作者/跨机一来（两个 CEO 同日各 mint `Q-019`）就是同一个结构性撞号 → **一并换，不留半修**。

### 11.2 新原语：时间戳 + 人前缀（格式 B，全记录类型）

- **格式**：`<类型> <YYYYMMDD-HHMMSS>-<who>`，例 `Step 20260613-101432-ly1989abc` / `Q 20260613-101432-ly1989abc`（Q/G/R/F 同构，`Q-NNN`→`Q <ts>-<who>`）。
  - 时间戳 = 唯一性 + 全局排序（coordination-free，跨机按时间 interleave 天然对）；
  - `<who>` = **git email 前缀（local-part），sanitize 成 ASCII slug** = 一眼看谁 + 同秒跨写手/跨协作者兜底；
  - **同写手同秒** → 追加 `.N`（`...101432-ly1989abc.2`）；`.N` 须 **atomic**（flock 校验 store 内同 `<ts>-<who>` 前缀已有数），同机多会话/并发安全。
- 🔴 **no-git 降级**：取不到 git / email → **省略 `-<who>` 后缀**，产出 `<类型> <ts>`（如 `Step 20260613-101432`），**绝不写 `-None` 或裸 `-`**。时间戳单写手下仍唯一。
- **归因字段**（条目里，不进 ID 命名空间）：`writer: <email>/<session-id>/<machine-id>`（缺则留空，不污染 ID）。
- **范围 = Step + Q/G/R/F 全换 B**（用户拍板：一致性 + 同根一并修）。统一原语 = 一个解析器、一个心智模型；时间戳**自带日期**对决策/踩坑反而是加分。

### 11.3 取舍（诚实摆）

- 同写手同秒撞 → atomic `.N` 兜底，工作单元分钟级间隔极罕见。
- 时钟偏移/回拨 → 排序 ≈ 真实序、非严格单调；**给人读的叙事/决策日志可接受**（非分布式共识）。
- **可读性/引用记忆**：`Q 20260613-101432-ly` 比 `Q-011` 长、不如「Q-011 walking-skeleton」好记——这是换 B 的**主要成本**（Q/G/R/F 在散文里被引用远多于 Step），用「自带日期 + 一致性」抵消，**用户已接受**（如更看重可引用编号，可单独保 Q/G/R/F 顺序号——off-ramp）。
- **slug 机制退役**：`compute_branch_slug()`（cwd 现算）+ per-branch counter 不再用于任何记录类型；G-011 类结构上不可能再发生。

### 11.4 冻结迁移（不重写历史）

- **冻结现存 `main-N` / `Q-NNN` / `G-NNN` / `R-NNN` / `F-NNN`** 当合法历史 ID（不动 247KB 执行日志 + 满地交叉引用）；
- **minting 从今往后切时间戳**（Step + Q/G/R/F 同步切）；
- **解析器双认**（`<类型>-\d+` 顺序形 OR `<类型> <ts>-<who>` 时间戳形）——brief/recall/distill/step_id/frontmatter 等全改双认。
- ⇒ 零历史改写、零断引用。

### 11.5 live 数据卫生债（设计外，单独处置）

store 现有 5 根碎轨（`main=87`/`kdev-hud`/`p-a-req-architect`/`p-c1-memory-scope`/`worktree-feat-l3-review-dogfood`）+ 1 条孤儿 Step。一次性 reconcile（碎轨 Step 并回单调轨 + 修 current_step）**单独做、先问用户**，不混进本 spec/实施。

### 11.6 全场景 hold 校验（方案压力测试）

把最终方案（时间戳 ID + who 后缀 + no-git 省略 + 归因字段 + per-会话续航 + collaborator scope + recall-from-events + 收窄叙事）对所有场景逐一压测：

| # | 场景 | 唯一性 | 归因 | 续航 | 目录 | 判定 |
|---|---|---|---|---|---|---|
| S1 | 单人·单会话·flat·未开 feature（今天）| ts ✓ | email 字段 | 单 当前状态 | flat root | ✅ |
| S2 | 单人·多会话顺序·flat | ts 随真实时间单调,无 counter 分歧 | email | 当前状态续+brief | flat root | ✅ |
| S3 | 单人·多 worktree 共享 store(symlink)| ts 各异/同秒 `.N`,**无 slug 分裂** | email | 顺序切=单指针 | 同 store | ✅ **G-011 修复** |
| S4 | 单人·跨机(git 同步记忆仓)| 各机 ts;合并按 ts interleave | email+machine-id 字段 | per-机/会话 | 同步仓 | ✅（同秒同人跨机=**一人不可能同秒**,machine-id 兜审计）|
| S5 | 单人·开 feature·scoped | CEO ts ID;员工只 events 无 Step | email | shared 单轨 | shared+features+staff | ✅ |
| S6 | **2 会话并行·同机·同人** | ts 各异;同秒 **atomic `.N`** | session-id 字段分 A/B | **per-会话指针** | 同 store | ✅（依赖 atomic `.N` + 真并发 md append→P-C3）|
| S7 | **2 人并行·和 CEO 对话** | ts+**who 后缀分两人**(同秒也不撞)| email 分两人 | **per-协作者**(collaborators/)| +collaborator scope | ✅（who 后缀在此立功；shared 并发→P-C3）|
| S8 | scoped·新会话恢复 feature | 新 Step ts ID | email | brief 读续航+扫 features 非终态 | — | ✅ |
| S9 | **no-git 环境** | ts 单写手唯一 | email 空/省 | session-id 仍在 | flat | ✅（后缀省略,无 `-None`）|
| S10 | 装 kdev-team 未启用 | ts ID | email | 单轨 | flat（不受装影响）| ✅ |

**三条 hold 的前提（写进实施）**：
1. **C1 atomic `.N`**：同秒同写手兜底须 flock 校验 store（S6 同机多会话刚需）。
2. **C2 跨机同秒同人**（S4）= 一个人物理上不可能同秒在两机各完成一工作单元 → 实务不可能；`machine-id` 留归因字段供审计/偏执。
3. **C3 共享文件并发 append**（S6/S7）= **P-C3 锁**（defer）；落地前真并发写同一 md 须 flock 或接受罕见 interleave。
- **who 后缀的价值验证**：S7（两人同秒）正是 `<who>` 后缀做实事的地方——纯时间戳会撞,带 who 不撞 → 印证格式 B 优于裸时间戳。

> 结论：方案在 10 个场景全 hold,唯三个工程前提（atomic `.N` / machine-id 归因 / P-C3 append 锁）需在实施期落实,其中 P-C3 本就 defer、另两个是小 plumbing。

---

## 12. 实施时机 + 范围边界

- **时机结论**（Q-019）：判定痛已临界 → **下一个排期 → writing-plans**。诚实记账：驱动力 = **架构已定 + 避免员工先污染 markdown 再回头建 recall 的返工 + G-011 live bug + 委派后 CEO 叙事会漏 subagent 工作**（同 P-C1「2 员工就咬别 flat-then-migrate」逻辑），**非「token 痛已实测」**（收窄后 N×M 爆炸已被结构消除）。
- **本期实施 = ①recall reader ②CEO recorder 读 events+handoffs ③Step ID 时间戳化 + 冻结迁移**。
- **defer**：P-C3 并发写锁 · 多协作者 collaborator scope 实建（随 P-C3）· 跨机 machine-id 进 ID · 蒸馏质量闸（Q-017）· live 碎轨 reconcile（单独专项）。

---

## 13. 影响的文档 / 代码（待同步）

- **记忆底座 合稿 v1.0**：§4 目录图收窄（§8.2）· §5.3 row3 砍 per-员工叙事 rollup · §4 line113 / §9.6 #5 Step-ID 改时间戳。
- **代码（实施期）**：`step_id.py`（时间戳 minting + 解析双认 + slug 退役）· `scope.py`（recall reader / 写手身份）· `migrate_scope.py`（DEFAULT_STAFF 稀疏化）· 受影响 hooks（brief/recall/rollup/frontmatter）· bump version（G-004）。
- **CLAUDE.md**：「v0.11+ Step ID 加分支前缀」一段改时间戳原语（接口契约对齐）。

---

## 14. 决策摘要

| Q | 拍板 |
|---|---|
| **Q-019** | P-C2 边界 = 只读复用 events + transcript 不造第二本账（不加 capability 事件）；收窄叙事到 CEO/shared（员工 = events+handoffs，砍 per-员工叙事）；rollup 触发阶段主+每日/按需/阈值备；events 零他评（只 Step rollup）；Workflow cache 借鉴幂等 range-keyed 派生缓存；时机改判下一个排期（驱动力=架构/返工/G-011，非实测痛）|
| **Q-020** | 记录 ID 换时间戳原语（格式 B `<类型> <YYYYMMDD-HHMMSS>-<who>`，who=git email 前缀；**no-git 省后缀不写 None**；同秒 atomic `.N` 兜底；归因字段 email/session-id/machine-id）；**Step + Q/G/R/F 全换 B**（一致性+同根一并修）；slug 机制退役；冻结现存顺序 ID + minting 从今切 + 解析双认（零历史改写）；目录生命周期切换认启用不认安装；会话身份唯一=主控；多写手轴唯一性归时间戳/归因归字段/续航 per-会话；**全 10 场景压测 hold**（§11.6，三前提：atomic `.N` / machine-id 归因 / P-C3 append 锁）|

---

## 15. 下一步

1. 用户复核本稿。
2. 转 **writing-plans** 起 P-C2 实施计划（①recall reader ②CEO recorder ③Step ID 时间戳化 三块，可拆 plan）。
3. live 碎轨 reconcile = 单独专项，用户点头后单独做。
