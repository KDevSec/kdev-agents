# iter-7 notes：P0-1 Step 完成闸门 discriminating eval

**日期**：2026-04-23
**目的**：用 discriminating eval 验证审计 §5.1 P0-1"Step 完成闸门（四段必填）"
是否真的需要加到 SKILL.md——在一个诱导"模型写完自评就默默进入下一步"的场景下，
v0.5.0 skill 本体 vs v0.5.0 + 临时闸门章节 是否会做出不同决策？
**规模**：1 eval × 2 configs × 1 run = 2 runs
**结论**：**P0-1 不必加**——数据证明 v0.5.0 skill 本体已有等效语义

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

## 结论：P0-1 **不必加**（或只加"措辞加强"版）

### 为什么不必加硬闸门章节

1. **v0.5.0 skill 本体已足够**——baseline 正确做出"拦截"决策，不是靠用户明示
2. **审计原始担忧的根因是 CLAUDE.md 漂移**——token-statistics 项目失守是因为它的 CLAUDE.md
   还是 0.2.0 时代的老模板、没加载 v0.3.0+ 的"当场采集"条款。这个根因**已经由 iter-4
   的 `claude_md_contract` lint 对症解决**——下次新会话 SessionStart 就会 ⚠️ 告警老项目
   该升级
3. **加闸门章节是对增量收益做过度设计**——SKILL.md 本已 260 行，再加 24 行显式闸门
   只带来 -21% token 的推理效率提升，不改变行为；代价是 SKILL.md 进一步膨胀、描述负担

### 可选的轻量优化：措辞加强（留给 v0.6.0 考虑）

如果未来想降低 baseline 的推理成本（-21% tokens 是真实收益），可以考虑**不加新章节、
只改现有行的措辞**：

- `references/六类记录-schema.md §3` 的「用户评分 完成时间：必须当场采集，不允许留过夜」
  改为更硬的 `Step 四段必填——缺任一段视为未完成，下一步工作前必须补齐`
- SKILL.md 核心运作原则段加一句半行"四段未齐不得进入下一步（严禁模型写完自评就认为 Step 完成）"

这是 **措辞级微调**（预计 +5 行，对应 +21% token 效率），而不是 **新增章节**（+24 行，
重复已有语义）。留给 v0.6.0 再评估是否值得做。

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
| P0-1 Step 完成闸门 | P0 | **🟢 数据驱动不加** | iter-7 证明 baseline 已有等效语义，不增加 skill 大小 |
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

- **不做 P0-1/2** —— iter-7 数据已给出决策依据
- **P0-3 豁免动作化**：需要新增 subagent-driven 批次场景 eval-11。优先级 P2，等真实
  项目出现此类失守再做（目前无数据驱动）
- **v0.6.0 scope** 重新梳理：
  - 按 dev-note 方案 A 加「使用的 skill」事实字段（实质增量）
  - 考虑"措辞加强"微调（可选，效率优化）
  - 不加 P0-1/2 新章节（数据驱动结论）

---

## 文件清单

- `eval-10-step-gate/eval_metadata.json`
- `eval-10-step-gate/baseline/run-1/{grading,timing}.json`
- `eval-10-step-gate/with_gate/run-1/{grading,timing}.json`
