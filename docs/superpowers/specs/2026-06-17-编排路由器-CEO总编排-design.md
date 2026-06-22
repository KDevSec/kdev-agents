# 编排路由器 / CEO 总编排层 — 设计提案

| 项 | 值 |
|---|---|
| 文档状态 | 🟡 设计提案（推荐设计已定，MVP plan 待起）|
| 日期 | 2026-06-17 |
| 关联决策 | [Q 20260617-182851-ly1989abc](../../../.kdev/memory/决策日志.md)（定调 + 5 决策按推荐拍定）|
| 产出方式 | 8-agent 设计 workflow（ground→3候选→评审→综合，opus）|
| 承 | 概念合稿 §8（CEO 派单/阶段聚合/顶层约束能力 = 已设计未建）· 接缝评审 接缝7 编排一致性 |
| 解决的问题 | 当前只能人敲 `/kdev-flow-driver <员工id>` 一次驱一个员工，跨员工生命周期（需求→开发→测试）靠人脑编排。要"1 个总的去编排，不靠人"——LLM 在**现有**编排资产上路由选择（类比 ultracode 但非从零写脚本）→ 呈现编排结论 → 人确认 → 派发 |

---

## 0. 锁定决策（用户"决策先按你的推荐"，2026-06-17）

| # | 决策 | 取值 | 理由 |
|---|---|---|---|
| 0 | 总体取向 | **P3 骨架 + P1/P2 嫁接，否决 P2 自由 DAG** | flow-config L1 即真相、复用最干净；模板防非法 plan；lint 校验 |
| 1 | 模板目录 vs 自由 DAG | **模板 + 校验器** | 防 LLM 产非法 plan、确认屏可读、扩展零代码 |
| 2 | loop 落点 A/B/C | **C 后台驱动 + HUD 当前台** | 沿用已验证 B 轨、复用 HUD、不淹 CEO↔用户对话 |
| 3 | 评审开关 | **MVP 降级 review-mode 三档，per-gate merge 列下一刀** | 引擎现不消费 per-gate L1（诚实债）|
| 4 | 跨员工链状态 | **MVP 声明不可恢复，下一刀补 delivery-state cursor** | 链级状态暂只活主会话内存 |
| 5 | MVP 范围 | **先 full-delivery 三段（非两段）** | 一次性验 test 黑盒读 req@n8-merge 最易错 handoff 边 |

---

## 1. 一句话定位 + 总体取向

**`/kdev-team <高层目标>` 主会话 skill：LLM 把目标对号入座到命名生命周期模板，渲染一屏可读编排结论，人确认/微调后主会话顺序链式调现有 `/kdev-flow-driver`，全程零新引擎、零新原语。**

骨架取 **P3「flow-config L1 即真相 + LLM 填空」**（复用最干净、loop 选 C 与已验证 B 轨一致）。嫁接三处：
- **从 P1**：声明式 `lifecycles/*.yml` 命名模板目录 + `when` + `confidence` + 强制 `runner_up`——降级为 P3 的 seed 模板/合法候选域（不是独立第二真相）。LLM 在模板上受控微调（开关评审、增删段），不自由生成顺序。
- **从 P2**：`drive` 前一道 **lint 校验器**（非自由 DAG），逐字段对 staff.yml / dispatch-table / 跨员工 handoff 契约硬校验，不过禁止进确认屏。
- **从 confirm-ux 视角**：确认屏评审项**从 node-table `gate_specs` 真实生成**（不手写），`human_gates` 作一等公民可编辑字段。

**P2 自由 DAG 否决**——三视角一致：违背"在现有资产上路由、非 ultracode 自写编排"，且主会话顺序派单下"并行 DAG"是假象。

## 2. 入口与运行形态

- **命令**：`/kdev-team <高层目标>`（别名 `/kdev-ceo`）。
- **跑在哪**：**纯主会话 skill**，不是 `Agent()` 派出的 CEO agent——守硬约束（子 agent 不能再开子 agent，派出去就无法再派员工编排）。三段主 loop：`plan`（LLM 分类，主会话自身推理，不开 subagent）→ `confirm`（渲染+人编辑）→ `drive`（主会话顺序 for-loop 调 N 次 flow-driver）。
- 唯一会派 subagent 的是主会话 + flow-driver（也跑主会话）；员工 cap agent 是叶子不再下派；CEO 决策点永远留主 loop。

## 3. LLM 决策契约

**输入**：`{goal, context?: {repo_slug?, origin_feature?, 约束, 已有产物?}}` + 注入 `staff.yml`（候选全集）+ `lifecycles/*.yml`（模板域）。

**模板目录**（新建 `plugins/kdev-team/lifecycles/*.yml`，预置 5）：`design-only` / `design+build` / `full-delivery` / `test-only` / `build-only`。每个声明 `when`（语义触发）/ `stages`（员工×flow×handoff_from）/ `reviews_default`。

**输出契约**（封闭 schema，`reviews` 值域受 §1 校验器钉死）：

```yaml
template_id: full-delivery
slug: user-auth                   # 全链 join 键；校验器钉死所有 stage 同 slug
goal: "做用户认证功能"
confidence: 0.86
reasoning: "全新功能+无现成SR+安全敏感+需可测交付 → 全交付三段"
stages:                           # 模板基础上微调（开关段，不自由排序）
  - {emp: req-architect, flow: design-flow,      on: true, handoff_from: null}
  - {emp: dev-engineer,  flow: coding-flow,      on: true, handoff_from: req-architect@n8-merge}
  - {emp: test-engineer, flow: test-design-flow, on: true, handoff_from: req-architect@n8-merge}  # 黑盒读req，禁dev→test边
review_overrides:
  dev-engineer: {g-sec-review: reviewer-expert}   # 认证敏感→自评上调专审
human_gates: [after-req, after-dev]               # L2→L3停人闸，确认屏可编辑
runner_up: {template_id: design+build, why_not: "含'功能'隐含可交付→需测试段"}
```

**LLM 怎么判**：匹配各模板 `when` → 选 `template_id`；只在该模板上开关评审 / 增删段，不发明顺序、不增删框外员工、不下沉节点级。`confidence<0.6` 或贴两模板 → 必填 `runner_up`，确认屏并列双候选。

## 4. 「编排结论」人确认样例（目标=做用户认证功能）

> 评审项从 node-table `gate_specs` 真实生成（req 实际 3 个 review gate：g-sr-review / g-ar-proto-review / g-design-review，原型与 AR/story 共用 g-ar-proto-review 一闸）。

```
━━━ kdev 编排结论 · 待你确认  slug: user-auth ━━━━━━━━━━━━━━━━━━
目标：做用户认证功能
归类：full-delivery（全交付）   置信度 0.86
理由：全新功能·无现成需求·安全敏感·需可测交付 → 需求→开发→测试三段
⚠️ 按依赖串行驱动，非真并发（②③ 不同时跑）

拟派流水线（同 slug=user-auth 串联）：
  [1] ✓ 需求架构师  req-architect · design-flow
         评审： SR评审=专家   AR/原型评审=专家   方案评审=专家
         交付 n8-merge ──handoff──┐
  [2] ✓ 开发工程师  dev-engineer · coding-flow      ◄── 读[1]交付 req@n8-merge
         评审： 方案评审=专家   代码评审=专家   安全评审=专家 ⚠️(默认self,已上调)
  [3] ✓ 测试工程师  test-engineer · test-design-flow ◄── 读[1]交付 req@n8-merge（黑盒,不读dev代码）
         评审： 测试设计评审=专家
         ⚠️ test 依赖[1]完成；若 req 未跑到 n8 → handoff not-found 静默回退裸任务

人介入闸（停人）：  needs after-req · after-dev   + 评审3次不过升你裁决
次选：design+build（无测试段）—— 因你说"功能"隐含可交付，未选

你可以：
  [Enter] 照此派发        [d 3] 关掉第3条（删测试段）
  [r dev g-sec-review=self] 调评审开关   [g +after-test] 加停人闸
  [t design+build] 换模板   [s 改slug]
> r dev g-sec-review=self          ← 人把安全评审改回自评
> Enter
```

每个动作 = 对底层 YAML 结论的结构化编辑 → 重跑校验器(lint) → 重渲染。**防习惯性 Enter 退化成 L4**：模板被降级丢段 或 `confidence<0.6` 时该屏**禁一键 Enter，强制二次确认**。这是 L2→L3 human-in-loop 闸，绝不全自动直发。

## 5. 派发执行模型 + 评审开关诚实方案

确认即冻结结论落 `features/<slug>/delivery-plan.yml` + 写各员工 `flow-config.yml`(L1)。主会话顺序消费 `stages[]`：

1. **不外层 init**（防双 init 撞 flow-state）：只调 `/kdev-flow-driver <emp> --task <slug>`，由其 bootstrap 负责 init/resume；`context.origin_feature` 存在则透传 `--origin/--relates-to`。
2. **段间 handoff 零新增**：上游 flow-driver 在 `n8-merge` 已 `handoff-write`；下游 bootstrap `handoff-read` 同 slug 取（缺失回退裸任务）。仅保证串行顺序 + 同 slug 透传。
3. **评审发函路由器不碰**：reviewer gate 走 node-table `gate_specs.reviewer` 字段触发 `reviewer-orchestrator`（硬规：只派 orchestrator）。
4. **停人**：`human_gates` 标的阶段交界 + 评审3次不过/BLOCKED 升 CEO 屏。其余节点级 gate 各 flow-driver 内自决。

**🔴 评审开关诚实方案（三候选全漏标）**：引擎当前**不消费 per-gate L1 flow-config**（只有 `init --review-mode {ai,both,human}` flow 级开关，无 per-gate merge）。两条路：
- **(a) MVP 降级**（决策3）：评审开关只表达 `--review-mode` 三档（flow 级）+ 手改 node-table `reviewer` 字段回退。确认屏 per-gate 专家/自评仅作**意图展示**，落地靠手改——诚实标注「per-gate 自动化待补」。
- **(b) 真新增**：补 flow-driver bootstrap 读 `flow-config.yml` per-gate reviewer + `merge(L0,L1,L2)` 引擎能力（=「已设计未建」那块，列下一刀）。

**loop 落点 = C（后台驱动 + HUD 当前台）**（决策2）：顶层 dispatch 决策留主会话（硬约束：后台 agent 不能再派员工编排），每棒 flow-driver 执行甩 `run_in_background`；进度不自造——`delivery-plan.yml` 丢进 `features/<slug>/` 让 HUD 多渲一行「链进度 1/3」，主对话只剩 CEO↔用户决策语句。

## 6. 复用 vs 新建 + MVP 第一刀

**直接复用（零改）**：`/kdev-flow-driver`、`staff.yml`、per-员工 node-table、`handoff-write/read`、`reviewer-orchestrator`+dispatch-table、kdev-core CLI、HUD。

**新建（最小）**：① `lifecycles/*.yml`（5 个声明式文件，扩展=纯加 YAML）；② `/kdev-team` skill（plan/confirm/drive 三段 + 分类 prompt + 渲染）；③ `delivery-plan.yml` schema + lint 校验器；④ per-gate flow-config merge 引擎能力（真新增，MVP defer 走 §5(a)）。

**MVP 第一刀**（决策5）：兑现 `full-delivery` 一模板，跑通 **「目标→LLM分类→一屏确认→Enter→req→dev→test 三段同 slug 链自动接力 + 一道 after-req 停人闸」**。选三段验 test 黑盒读 req@n8-merge 最易错 handoff 边。评审开关 MVP 走 (a)。绿了，其余 4 模板纯加 YAML。

## 7. 两笔必须明示的诚实债

1. **评审开关 per-gate 自动化引擎未建**（决策3）：MVP 确认屏开关是意图展示、靠手改 node-table。
2. **跨员工链级进度漂引擎账外、无断点续跑**（决策4）：`stages[]` 顺序只活主会话 for-loop 内存，崩了/换 session 无 `delivery-resume`，擦边「引擎是状态唯一权威」。推 L3 自跑前必补 delivery-state cursor，MVP 可忍但不得宣称达 L3。

二者都是「已设计未建」的真账，列下一刀，不计入「零新机器」。

---

## 后续

- follow-up：起 MVP plan（full-delivery 一模板）。
- 关联记忆决策：[Q 20260617-182852-ly1989abc](../../../.kdev/memory/决策日志.md)（员工记忆 JSONL 主账化——与本编排层正交但同期拍定）。
