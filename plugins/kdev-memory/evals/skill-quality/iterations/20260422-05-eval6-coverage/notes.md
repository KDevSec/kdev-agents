# iter-5 notes：补跑 eval-6 跨会话续航场景

**日期**：2026-04-22
**目的**：补齐 skill description 里明确列出、但 iter-1~iter-4 都未验证的
「跨会话续航」触发场景
**规模**：1 eval × 1 config × 1 run（单配置：仅跑 v0.5.0 版，不对照 baseline）
**为什么只跑 1 个 config**：此轮目标是**场景覆盖**，不是版本对比——iter-2
已验证 Phase 1 重构零 regression，iter-3/4 已覆盖解耦 + lint 的对照。跨
会话续航从 v0.1 起就是 kdev-memory 的核心用例，不需要对比 baseline

---

## 结果

- Pass rate: **8/8 (100%)**
- Tokens: 44,746
- Time: 154.7s
- Tool uses: 14

### 验证点逐一对应

| assertion | 通过证据 |
|---|---|
| 正确识别昨天 Step 17/18 | REPORT (a) 列 Step 18 细节 + 末尾背景段交代 Step 17 是上游 |
| 引用 frontmatter（phase/current_step） | REPORT (b) 原文引用 `phase: exec / current_step: 18 / last_updated: 2026-04-21` |
| 指出下一步 Step 19 token bucket 限流 | REPORT (c) 原文 "Step 19：推送限流 / token bucket 按订阅者 IP 限流" |
| 列出读取的文件 ≥ 3 核心文件 | 实际读 7 个：当前状态 / 每日汇总 2 份 / 执行日志 / 决策 / 踩坑 / 改进建议 |
| 不翻会话 / 不让用户复述 | REPORT 开篇铁规声明 + 所有引用都 pinpoint 到具体文件行段 |
| 识别 Step 18 弱正信号（差值 +1）| REPORT (a) 原文 "模型自评 3/5... 用户评分 4/5... 差值 +1，弱正信号" |
| 识别 Step 19 评审点"限流阈值" | REPORT (c) 指出"Q-012 候选——智能体不应替用户拍板" |
| 未新增 .kdev/memory/ 文件（只读）| sandbox 只有 fixture 原样 + outputs 根目录 REPORT.md，.kdev/ 下文件 byte-identical |

---

## 关键观察

1. **skill 严格遵守"只读回读"铁规**：subagent 读了 7 个文件但没改任何 .kdev/memory/，
   REPORT 每条结论都 pinpoint 到源文件行段，无一项基于会话推断
2. **多层证据交叉印证**：subagent 读了前一天（2026-04-20）的每日汇总和昨天（04-21）
   的每日汇总，加上执行日志——三处交叉验证"下一步是 Step 19"的一致性
3. **敏感度够用**：evaluator 识别出了 `pending_decisions: []` 和 `unresolved_gotchas: []`
   表示"状态干净，无悬而未决"，而不是只报最近 Step——这是对 frontmatter 的**语义
   理解**，不是机械引用
4. **主动升级信号**：REPORT 把"限流阈值怎么设"标为 Q-012 候选（用户拍板前不替决定），
   这是按 skill "Q-NNN 决策日志"流程的主动应用——skill 价值在此显现

---

## 该轮的定位

这是**补齐 skill description 承诺的场景覆盖**，不引入新的架构/设计改动。
v0.5.0 的 5 个核心触发场景至此全部验证：

| skill description 触发场景 | 验证 iteration | 状态 |
|---|---|---|
| "建立工程记忆 / 加 .kdev" | iter-1/2/3 | ✅ |
| "写今天总结 / 生成每日汇总" | iter-1/2 | ✅ |
| "切档 / 归档一下" | iter-2 | ✅ |
| "这条以后都要遵守 / 升级成铁规" | iter-1/2 | ✅ |
| **"昨天做到哪了 / 继续上次的工作"** | **iter-5**（本轮） | ✅ |
| "修 CLAUDE.md 漂移"（0.5.0 新增） | iter-4 | ✅ |

---

## 下一步（后续 session）

1. **P0-1 discriminating eval 设计**（~1-2h）——验证 Step 完成闸门是否真必要
2. **P1-5/6 hook 语义扫描**（~2h）——Stop hook check-step-completeness + brief 加欠评 Step 告警
3. **v0.5.x / v0.6.0 scope 决策**——Step schema 加 skill 事实列表（按 dev-note 决策：单一评分 + `使用的 skill` 列表字段，不走分双维度路线）

---

## 文件清单

- `benchmark.json` / `benchmark.md`
- `eval-6-cross-session-resume/eval_metadata.json`
- `eval-6-cross-session-resume/with_skill/run-1/grading.json`
- `eval-6-cross-session-resume/with_skill/run-1/timing.json`
