# Benchmark Report: SKILL.md 精简 discriminating eval

**Eval ID**: eval-12-skill-simplification
**Iteration**: 20260429-01-skill-simplification
**日期**: 2026-04-29
**目的**: 验证 SKILL.md 精简后行为一致性 + token 节省效果

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

## 逐场景结果

### Scenario-1: Step Completion

| Config | Tokens | Tool Uses | Duration | Assertions | Grade |
|--------|--------|-----------|----------|------------|-------|
| baseline | 44,782 | 20 | 224,466ms | 7/7 | PASS |
| with_simplification | 44,776 | 14 | 174,572ms | 7/7 | PASS |

**差异**: tokens -6 (-0.01%), tool_uses -6 (-30%), duration -49,894ms (-22%)

### Scenario-2: Gotcha Record

| Config | Tokens | Tool Uses | Duration | Assertions | Grade |
|--------|--------|-----------|----------|------------|-------|
| baseline | 44,672 | 11 | 123,721ms | 3/3 | PASS |
| with_simplification | 44,683 | 16 | 164,396ms | 3/3 | PASS |

**差异**: tokens +11 (+0.02%), tool_uses +5 (+45%), duration +40,675ms (+33%)

### Scenario-3: Daily Summary

| Config | Tokens | Tool Uses | Duration | Assertions | Grade |
|--------|--------|-----------|----------|------------|-------|
| baseline | 44,740 | 16 | 190,833ms | 3/3 | PASS |
| with_simplification | 45,081 | 14 | 160,247ms | 3/3 | PASS |

**差异**: tokens +341 (+0.76%), tool_uses -2 (-12.5%), duration -30,586ms (-16%)

---

## 验证假设检查

| 假设 | 验证结果 |
|------|----------|
| 精简不逆转 iter-7 的显式化收益 | ✅ 行为一致，Step 四段完整性保持 |
| tool_uses 不增加 | ✅ 总 tool_uses -6.4% (47→44) |
| 核心规则（闸门+动作链）保留 | ✅ 所有 assertions PASS |

---

## SKILL.md 词数对比

| 版本 | 词数 | 变化 |
|------|------|------|
| Baseline (git HEAD) | 1326 | — |
| With Simplification | 944 | -382 (-28.8%) |

精简后词数 944 < skill-creator <5k 词限制，符合规范。

---

## 运行详情

**Baseline Runs**:
- run-1 (scenario-1): [grading.json](eval-12-skill-simplification/baseline/run-1/grading.json), [timing.json](eval-12-skill-simplification/baseline/run-1/timing.json)
- run-2 (scenario-2): [grading.json](eval-12-skill-simplification/baseline/run-2/grading.json), [timing.json](eval-12-skill-simplification/baseline/run-2/timing.json)
- run-3 (scenario-3): [grading.json](eval-12-skill-simplification/baseline/run-3/grading.json), [timing.json](eval-12-skill-simplification/baseline/run-3/timing.json)

**With Simplification Runs**:
- run-1 (scenario-1): [grading.json](eval-12-skill-simplification/with_simplification/run-1/grading.json), [timing.json](eval-12-skill-simplification/with_simplification/run-1/timing.json)
- run-2 (scenario-2): [grading.json](eval-12-skill-simplification/with_simplification/run-2/grading.json), [timing.json](eval-12-skill-simplification/with_simplification/run-2/timing.json)
- run-3 (scenario-3): [grading.json](eval-12-skill-simplification/with_simplification/run-3/grading.json), [timing.json](eval-12-skill-simplification/with_simplification/run-3/timing.json)

---

## 结论

**✅ 合入判定**: SKILL.md 精简方案验证通过。

- 行为一致性: 100% assertions 通过，无 regression
- Token 效率: 总体无显著差异 (+0.26%)，单场景有波动
- Tool use 效率: 总体略降 (-6.4%)，符合预期
- Duration 效率: 总体略降 (-7.4%)
- 词数达标: 944 词 < 5k 词限制

**建议**: 合入精简版本，符合 skill-creator 规范且不损失行为质量。

---

*Generated: 2026-04-29*