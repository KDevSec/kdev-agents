# kdev-explorer Benchmark - Iteration 1

## Summary

| Test | with-skill | baseline | Δ |
|------|------------|----------|---|
| eval-1 文档探索 | 4/4 ✓ | 4/4 ✓ | 0 |
| eval-2 网页抓取 | 3/4 ⚠ | 3/4 ⚠ | 0 |
| eval-3 代码搜索 | 4/4 ✓ | 3/4 ⚠ | +1 |

**with-skill 总计:** 11/12 (92%)
**baseline 总计:** 10/12 (83%)

---

## Timing

| Test | with-skill (s) | baseline (s) | Δ |
|------|----------------|--------------|---|
| eval-1 | 154.24 | 150.02 | +4.22 |
| eval-2 | 122.97 | 156.44 | -33.47 |
| eval-3 | 200.31 | 135.79 | +64.52 |

**with-skill 平均:** 158.84s
**baseline 平均:** 147.42s
**Δ:** +11.42s (with-skill 稍慢)

---

## Token Usage

| Test | with-skill | baseline | Δ |
|------|------------|----------|---|
| eval-1 | 44,093 | 43,855 | +238 |
| eval-2 | 44,324 | 49,117 | -4,793 |
| eval-3 | 43,979 | 43,855 | +124 |

**with-skill 平均:** 44,132 tokens
**baseline 平均:** 45,626 tokens
**Δ:** -1,494 tokens (with-skill 稍省)

---

## Analysis

### with-skill 优势
1. **eval-3 代码搜索** 输出更简洁（50行 vs 79行）
2. **eval-2 网页抓取** 节省 33s 和 4,793 tokens

### baseline 优势
1. **eval-1** 稍快（-4s）
2. **eval-3** 稍快（-65s）

### 问题
1. **网页抓取任务** 两者输出都过长（约100行），skill 需要强化"简洁"约束
2. **tool_uses 差异** eval-3 with-skill 只用了 4 个工具，baseline 用了 24 个（可能与 skill 指导有关）

---

## Recommendations

1. **强化 Do NOT 约束** - 网页抓取模板需要更明确的简洁要求
2. **评估 skill 价值** - 当前 skill 对结果质量提升有限，主要差异在执行效率