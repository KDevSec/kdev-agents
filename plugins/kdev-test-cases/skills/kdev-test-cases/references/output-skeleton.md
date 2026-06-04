# Output Skeleton — fielded test cases (1:1 from 测试点 .md)

This file shows the full output layout. SKILL.md §4 references this for the exact structure.

## File-level layout

```markdown
# <被测对象> 测试用例（fielded, Playwright-handoff）

> 来源测试点：<absolute path-to-input-测试点.md>
> 渲染模板：<absolute path-to-example>
> 生成方式：kdev-test-cases — 1:1 renderer (no re-design)
> 上游契约：用例名称 / 用例编号 / 用例类型 / 优先级 / 是否准入 / UI 自动化 / API 自动化 / 预期结果 均逐字透传，不再判
> 仅生成：测试步骤 / 前置条件 / 测试数据（按 Playwright 接驳约定派生）

---

## 一、AR-SATP-04.001.001 — <AR 标题原文>

<block 1>

---

<block 2>

---

## 二、AR-SATP-04.001.002 — <下一个 AR 标题>

<block N>

---

...

---

## 用例集合统计

<table>

## 自检清单

<from example §七 verbatim>
```

## Block layout (one block per upstream row — byte-faithful to `--example`'s §二)

```
- 用例编号：TC-AR<8 digits>-<3 digits>
- 用例名称：<= 测试点标题 byte-equal>
- 需求编号：<AR-XXX-YY.YYY.ZZZ> / <FR-NNN if available>
- 用例类型：<基本流 | 异常流>
- 优先级：<1|2|3|P0|P1|...>
- 是否准入：<是|否>
- UI 自动化：<是|否>
- API 自动化：<是|否>
- 前置条件：<one-liner or multi-line bullets, generative, constrained>
- 测试数据：<one-liner or sub-bullets, generative, constrained>
- 测试步骤：
  1. <step 1>
  2. <step 2>
  ...
- 预期结果：
  1. <= 源 预期结果 第 1 条 byte-equal>
  2. <= 源 预期结果 第 2 条 byte-equal>
  ...
```

**Field-order rule**: match the example's §二 / §样例 block exactly. If the example puts `需求编号` before `用例类型`, do the same. If it puts pass-through fields as a single one-line `元数据：...` row, do that. The downstream parser is regex-based and field-order-sensitive.

## Block separator

Every block ends with `\n---\n`. The last block before a new `##` AR header also ends with `\n---\n` (consistency > visual tightness — parsing tools want a stable trailer).

## Per-AR header

```
## <一|二|三|...> 、 <AR编号 byte-equal from input> — <AR 标题原文 from input>
```

The Chinese number (一/二/三/...) is purely cosmetic; downstream tooling ignores it. The AR编号 and AR 标题 must match the input exactly.

## Statistics table

```
| 指标 | 数值 |
|---|---|
| AR 数 | N |
| TC 总数 | M |
| 准入用例数 | sum where 是否准入==是 |
| 基本流 | sum where 用例类型==基本流 |
| 异常流 | sum where 用例类型==异常流 |
| UI 自动化候选 | sum where UI 自动化==是 |
| API 自动化候选 | sum where API 自动化==是 |
```

Numbers are **computed from the actual emitted blocks**, not from the input — these are sanity-check numbers. If they don't match the input's totals, the cardinality contract (§3.1) is broken; stop and report.

## Self-check

Copy the example's §七 self-check verbatim if present (do not paraphrase). If the example has no §七, omit this section — do **not** invent one.

## Reporting upstream issues

When you find an issue you cannot fix (e.g. duplicate 测试点标题 within an AR — which would yield duplicate 用例名称, breaking downstream test-function-name hashing), append a "⚠️ 上游问题待回流" section at the end:

```
## ⚠️ 上游问题待回流（renderer 不修，需要上游 kdev-test-points 调整）

- 重复标题：AR-SATP-04.001.001 第 3 行与第 5 行的 测试点标题 完全一致 → 会生成同名 用例名称，downstream Playwright 函数名冲突。建议第 5 行加上区分性后缀（如 "（含子产品线）"）。
- 优先级缺失：AR-SATP-05.001.002 第 2 行 优先级 字段为空 → 已透传为空，建议补 P0/P1/P2。
- 自动化标记互斥嫌疑：AR-SATP-99.001.001 标题为接口验证类但 UI 自动化 == 是 / API 自动化 == 否；请上游确认。
```

This keeps the byte-equality contract intact (no silent fixes) while surfacing what needs human attention.
