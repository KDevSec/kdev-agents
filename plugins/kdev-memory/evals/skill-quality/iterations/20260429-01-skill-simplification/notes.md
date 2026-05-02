# iter-12 notes：SKILL.md 精简 discriminating eval

**日期**：2026-04-29
**目的**：验证方案 D+E（精简 SKILL.md）的行为一致性和 token 节省效果
**背景**：SKILL.md 从 1326 词精简至 944 词，符合 skill-creator <5k 词限制

---

## 结论摘要

| 指标 | Baseline | With Simplification | 差异 |
|------|----------|--------------------|------|
| **SKILL.md 词数** | 1326 | 944 | **-28.8%** |
| **总 tokens** | 134,194 | 134,540 | +0.26% |
| **总 tool_uses** | 47 | 44 | **-6.4%** |
| **总 duration** | 539,020ms | 499,215ms | **-7.4%** |
| **Pass rate** | 100% (13/13) | 100% (13/13) | 一致 |

**核心结论**: ✅ 精简不逆转 iter-7 收益，tool_uses 略降（-6.4%），行为完全一致。

---

## 评估假设

| 假设 | 来源 | 验证结果 |
|------|------|----------|
| 精简不逆转 iter-7 的显式化收益 | iter-7 证明显式化降低推理成本 | ✅ 行为一致，100% pass |
| tool_uses 不增加 | references 已按需加载设计 | ✅ 总 tool_uses -6.4% (47→44) |
| 核心规则（闸门+动作链）保留 | 精简只移出低频内容 | ✅ Step 四段完整性保持 |

---

## 场景覆盖

| Scenario | Baseline | With Simplification | 差异 |
|----------|----------|---------------------|------|
| scenario-1-step-completion | 7/7 PASS | 7/7 PASS | tool_uses: 20→14 (-30%) |
| scenario-2-gotcha-record | 3/3 PASS | 3/3 PASS | tool_uses: 11→16 (+45%) |
| scenario-3-daily-summary | 3/3 PASS | 3/3 PASS | tool_uses: 16→14 (-12.5%) |

---

## 关键发现

1. **行为完全一致**：所有 13 个 assertions 通过，无 regression
2. **Token 效率无显著差异**：总体 +0.26%，单场景有波动但整体持平
3. **Tool use 效率略降**：总体 -6.4%，符合"精简后推理更直接"预期
4. **词数达标**：944 词 < 5k 词限制，符合 skill-creator 规范

---

## 合入判定

**✅ 合入**：精简方案验证通过。

- 行为一致性：100% pass
- Tool use 效率：略降（-6.4%）
- 词数：符合 <5k 规范

---

## 文件清单

- `eval_metadata.json`：eval 元数据（从 evals.json 拷贝）
- `benchmark.json`：聚合指标
- `benchmark.md`：可视化报告
- `baseline/run-1/grading.json`、`timing.json`
- `baseline/run-2/grading.json`、`timing.json`
- `baseline/run-3/grading.json`、`timing.json`
- `with_simplification/run-1/grading.json`、`timing.json`
- `with_simplification/run-2/grading.json`、`timing.json`
- `with_simplification/run-3/grading.json`、`timing.json`

---

*文档版本：v2.0*
*最后更新：2026-04-29*