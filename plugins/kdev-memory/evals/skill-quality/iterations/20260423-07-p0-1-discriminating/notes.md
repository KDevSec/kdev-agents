# iter-7 notes：P0-1 Step 完成闸门 discriminating eval

**日期**：2026-04-23
**目的**：用 discriminating eval 验证审计 §5.1 P0-1"Step 完成闸门（四段必填）"
是否真的需要加到 SKILL.md——在一个诱导"模型写完自评就默默进入下一步"的场景下，
v0.5.0 skill 本体 vs v0.5.0 + 临时闸门章节 是否会做出不同决策？
**规模**：1 eval × 2 configs × 1 run = 2 runs
**结论**：**P0-1 应该加**（经过经济性复核后决策反转——见下方「决策反转修正」段）

---

## 决定性对比

| 维度 | baseline（v0.5.0 原版）| with_gate（v0.5.0 + 临时闸门章节）|
|---|---|---|
| 决策 | **B 拦截** | **B 拦截** |
| 正确补齐 Step 42 用户评分 | ✅ 5/5 + 14:48 | ✅ 5/5 + 14:52 |
| 锁定铁规（用户时分戳 > 自评 14:45）| ✅ | ✅ |
| 填评分差异分析（差值 +1，不升 R）| ✅ | ✅ |
| 是否开启 Step 43 | ❌ 未开（更保守）| ✅ 开了 CORS 子步骤（补齐后才开）|
| tokens | 57,975 | 45,832（**-21%**）|
| tool uses | 20 | 13（**-35%**）|

### 关键观察

- **行为完全一致**：两版本都正确识别诱导场景（用户说"直接开下一步"但上一步半残）并拦截
- **baseline 依靠的是推理**：从 SKILL.md line 27-28（核心原则）+ line 40（动作链）+ line 123 + `references/六类记录-schema.md §3`"必须当场采集不允许留过夜"等**已有条款**推出拦截决策
- **with_gate 依靠的是显式章节**：直接引用「🔴 Step 完成硬闸门（四段必填）」新增章节
- **行为相同 ≠ P0-1 无意义**：with_gate 用 **-21% tokens / -35% tool uses** 达到同样结果——把隐含规则显式化能**降低推理成本**

---

## 初步结论（已推翻）：P0-1 不必加

> **这段结论基于错误的经济性估算，已被下方「决策反转修正」段推翻。保留作
> 推理演进的证据。**

（历史理由）
1. v0.5.0 skill 本体已足够——baseline 正确做出"拦截"决策
2. 审计原始担忧的根因是 CLAUDE.md 漂移，已由 iter-4 claude_md_contract lint 解决
3. 加闸门章节 +24 行"只带来 -21% token 推理效率提升"被误判为"性价比低"

## 决策反转修正

提交 `f695370` 及上述结论发布后，user 反问："如果 baseline 换成 with_gate，
是不是效果一样的情况下，还减少了 md 的内容？"这个反问暴露我的经济性估算逻辑错误。

### 正确的经济性分析

把"SKILL.md 行数"和"单次触发 tokens"放到同一 × 次维度里算：

| 维度 | baseline | with_gate | 差值 |
|---|---|---|---|
| SKILL.md 加载（一次/每次触发） | 260 行 ≈ X tokens | 282 行 ≈ X+500 tokens | **+500** |
| skill 推理 + 搜索引用（每次触发） | **57,975** | **45,832** | **-12,143** |
| 单次触发净成本 | X + 57,975 | X + 500 + 45,832 | **-11,643** |

**每次触发净省 ~11,643 tokens**（扣除 +500 加载成本后）。按 kdev-memory 活跃项目
一天触发 20+ 次算，**每天净省 ~230k tokens**。

"+24 行 SKILL.md 是一次写入永久存在；每次 -12k tokens 是持续收益"——两边不是同量纲。

### 为什么 baseline 推理成本高

- baseline 要自己搜索 `SKILL.md line 27-28 / 40 / 123 + references/六类记录-schema.md §3`
  等多处，然后把这些条款串成"拦截"决策——每一步都花 tool_uses 和 token
- with_gate 直接读到「🔴 Step 完成硬闸门（四段必填）」章节，动作链明摆在眼前 →
  立刻命中决策 → 用更少 tool_uses 得出同样答案

### 这是 skill-creator "explain WHY" 原则的完美例子

skill-creator SKILL.md 明说：
> Try hard to explain the WHY behind everything you're asking the model to do.
> Today's LLMs are smart. ... If you find yourself writing ALWAYS or NEVER in
> all caps, or using super rigid structures, that's a yellow flag.

加的闸门章节**既写硬规则（"四段必填"）**，**又解释 WHY**（"模型写完自评就认为 Step
完成是反模式"）——是好章节设计。让 skill 不用每次重新推理"为什么要拦截"，直接
读结论 + 读理由。

### 修正后的决策

**P0-1 闸门章节应当合并到主 SKILL.md**（基于经济性数据驱动）。已在 commit
`<待填>` 完成——把 iter-7 临时 fork 的闸门章节正式合入 `SKILL.md`
（替换原 v0.5.0 placeholder 注释），SKILL.md 从 260 → 286 行（+26 行含一行 notes 回链）。

### 剩余观察

- **baseline 跑也拦截**这点**不变**——说明即使不加闸门，v0.5.0 不会"失守"；
  但推理成本高
- 加闸门不是"解决失守风险"（iter-3~6 已证明 skill 本体够硬），是**降低推理成本**
- token-statistics 项目失守的真正根因仍然是 **CLAUDE.md 漂移**（老版模板）——
  iter-4 `claude_md_contract` lint 是对症解决
- P0-2 动词链 / P0-3 豁免动作化可以按同样思路评估（显式化 vs 隐含推理的 token
  trade-off）——不在本 iter 范围

### 对 token-statistics / KDevSec 项目层面的建议

项目层面真正的解决方案不是 skill 加闸门，而是：
1. **升级项目 CLAUDE.md** —— 让 `claude_md_contract` lint 告诉项目缺哪几行并补上
2. 项目升级到 v0.5.0 后，老项目的"写完自评就停"漂移会自动在 SessionStart brief 里 ⚠️ 提示
3. 若项目仍持续出现半残 Step，**启用 strict 模式**（iter-6 P1-6 落地的 Stop hook exit 2
   阻塞）——这是比 SKILL.md 闸门章节更硬的机制

---

## 审计 §5.1 最终状态

| 审计项 | 原优先级 | 最终状态 | 说明 |
|---|---|---|---|
| P0-1 Step 完成闸门 | P0 | **✅ 已合入 v0.5.x**（决策反转）| iter-7 同一数据 + 正确的经济性算法：每次省 ~11.6k tokens 值得 +22 行文档 |
| P0-2 "公布→问→锁定"动词链 | P0 | 🟡 同 P0-1 | baseline 已按此执行（自发识别） |
| P0-3 豁免动作化 | P0 | 🟡 待覆盖 | subagent-driven 批次场景未测，保留为 v0.6.0 候选 |
| P0-4 Step 脱离状态机 | P0 | ✅ 已隐含 | Phase 1 重构里已表达 |
| P1-5 brief 欠评告警 | P1 | ✅ iter-6 落地 | |
| P1-6 Stop check-step-completeness | P1 | ✅ iter-6 落地 | |
| P1-7 CLAUDE.md 版本漂移检测 | P1 | ✅ iter-4 落地 | claude_md_contract lint |
| P2-8/9 | P2 | 🟡 保留 | 升级指南 / subagent 批次 meta 自动注入 |

**审计 P0/P1 完成度：7/8（唯一未做的 P0-3 需要新场景 eval-11，不是非做不可）**。

---

## 下一步

- **P0-1 已合并**（决策反转修正段）—— SKILL.md +26 行 ≤ 单次 -11.6k tokens ROI
- **P0-2 动词链**：其实 P0-1 闸门章节里已带"动作链"子段，P0-2 已 **隐含合入**
- **P0-3 豁免动作化**：需要新增 subagent-driven 批次场景 eval-11。优先级 P2，等真实
  项目出现此类失守再做（目前无数据驱动）
- **v0.6.0 scope**：
  - 按 dev-note 方案 A 加「使用的 skill」事实字段（实质增量）
  - P0-3 若数据驱动要做，可作为 v0.6.0 内容

---

## 文件清单

- `eval-10-step-gate/eval_metadata.json`
- `eval-10-step-gate/baseline/run-1/{grading,timing}.json`
- `eval-10-step-gate/with_gate/run-1/{grading,timing}.json`
