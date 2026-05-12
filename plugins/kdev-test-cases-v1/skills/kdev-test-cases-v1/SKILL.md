---
name: kdev-test-cases-v1
description: Pure 1:1 RENDERER that converts an upstream 测试点 .md (typically produced by `kdev-test-points-v1`'s feature-spec-lite mode, or any SP15/SOP-测试点-formatted markdown) into Playwright-friendly fielded TEST CASES — code-block blocks shaped `- 用例编号：TC-AR...` / `- 用例名称：...` / `- 需求编号：...` / `- 前置条件：...` / `- 测试步骤：1...2...3...` / `- 测试数据：...` / `- 预期结果：...` plus pass-through fields (用例类型 / 优先级 / 是否准入 / UI 自动化 / API 自动化). Governed by a strict byte-equality + arithmetic-equality contract: 用例名称 == 测试点标题 verbatim (no paraphrase, no prefix drop, no typo "fix"); 用例编号 == deterministic `TC-AR<8-digit AR concat>-<3-digit row>`; 用例类型/优先级/准入/UI/API automation flags copied as-is; 预期结果 numbered list preserved same-order, append-only for 异常流 "平台数据保持不变". Only 测试步骤 + 前置条件 + 测试数据 are generative — and only inferred from 测试点 标题 + 预期 following Playwright handoff conventions (【菜单】 for menu items, ""按钮 for buttons, default admin/admin123 + business params named in the title). Use whenever the user says "把测试点写成测试用例", "render test points as test cases", "测试用例编写", "test points to fielded cases", "把 测试点.md 渲染成 Playwright 用例", "SOP_测试用例MOD-style fielded blocks", "生成 fielded 用例 / 给我 Playwright 用例骨架 / 把 ARs 一行一行变成代码块", "把 测试点 .md 落成测试用例 .md" — or whenever the user provides BOTH an upstream 测试点 .md (with `### AR-[A-Z]+-\d{2}\.\d{3}\.\d{3}` headers + numbered table rows) AND a fielded-block-style example template. DO NOT use when the input is a raw spec / PRD / API contract / 原型 / 需求文档 — that is `kdev-test-points-v1`'s job (test-point design upstream). This skill never re-designs, re-judges, or re-prioritizes; it renders.
allowed-tools: Read, Write, Glob, Grep, Bash
---

# Test Case Renderer — 测试点 → Playwright-Handoff Fielded Test Cases

This skill is **a renderer, not a designer**. It takes a 测试点 .md that's already been through 29119-4 + 25000.51 design (typically the output of `kdev-test-points-v1` in `feature-spec-lite` mode) and emits fielded code-block test cases that downstream Playwright generators consume.

The byte-equality contract is the entire reason this skill exists as a separate skill. Other test-case tools generate from spec and have judgment latitude — they decide what to test, how to phrase it, how to prioritize. This skill explicitly **does not** make those decisions. Its only judgment is filling in 测试步骤 + 前置条件 + 测试数据 from the source row, under tight constraints. Everything else is a verbatim copy or a deterministic derivation.

Why the rigor: the downstream Playwright generator (e.g. `kdev-ui-autotest`, `testcases-to-playwright-pipeline`) hashes `用例名称` to test-function names and matches `用例编号` against test-result rows. Silent paraphrase or ID drift here breaks the entire **test → run → defect-triage chain** — far more damaging than the savings from "polishing" a few sentences.

---

## 1. Pre-flight: confirm this is the right skill

Before doing anything else, **verify the input shape**. Reject and redirect early if the input is the wrong artifact.

| Check | If true | If false |
|---|---|---|
| `--input` resolves to a markdown file containing both `### AR-[A-Z]+-\d{2}\.\d{3}\.\d{3}` headers and numbered table rows shaped `\| # \| 测试点标题 \| 预期结果 \| ...` | Continue | Stop. Tell user: "This looks like a raw spec / PRD / API contract — use `kdev-test-points-v1` to design test points first, then feed the resulting 测试点 .md back into this skill." |
| `--example` resolves to a markdown file whose §二 / §样例 contains a fielded code block with `用例编号` / `用例名称` / `需求编号` lines (e.g. `SOP_测试用例MOD`-style) | Continue | Stop. Tell user: "Need an `--example` pointing at a fielded-block template (e.g. `SOP_测试用例MOD.md`) so the rendering layout is anchored." |
| `--input` and `--example` are clearly distinct artifacts — input has numbered table rows, example has fielded blocks | Continue | Stop. Likely user passed the wrong file as `--input`. |

If all three pass, announce: `Mode: testpoints-to-cases (pure renderer) — input has N AR sections totaling M numbered rows; output will be M fielded blocks in 1:1 mapping.`

---

## 2. Arguments

```
/kdev-test-cases-v1 [--input <path-to-测试点.md>]      # required
                    [--example <path-to-fielded-template.md>]  # required
                    [--output <path>]                  # if absent, return inline
                    [free-form prompt]
```

- `--input <path>` — the upstream 测试点 .md (typically `kdev-test-points-v1` output).
- `--example <path>` — fielded-block template (e.g. `SOP_测试用例MOD.md`). The §二 / §样例 code block layout is what every output block must follow byte-faithfully.
- `--output <path>` — output file. If absent, return inline.

No `--mode` flag. This skill is single-mode by design — split out from `kdev-test-case` precisely so this contract has its own home and can't be polluted by spec-design judgment.

---

## 3. The contract (read this twice — these are correctness invariants, not stylistic preferences)

### 3.1 Cardinality

```
count(output 用例编号 lines) == count(input 测试点 numbered rows)
```

One numbered table row in the input → exactly one fielded code block in the output. No aggregation across rows. No skipping. No invented rows.

Verifiable: `grep -c "^- 用例编号：" <output>.md` must equal the total `^| <number> |` row count across all AR tables in the input. Re-run after every edit. If the numbers diverge, the output is broken — stop and report.

### 3.2 Title preservation (byte-equal)

```
output[i].用例名称 == input[i].测试点标题   # byte-for-byte
```

**Do not paraphrase. Do not drop prefixes. Do not "fix" typos. Do not shorten parentheticals.**

The traceability chain (测试点 → 用例 → Playwright test name → defect ticket) depends on byte-equal name match. If the title looks suboptimal ("超级管理员登录，..." feels redundant; the parenthetical is verbose), that's an **upstream 测试点 issue** — stop, report it back to the user, and let them fix the 测试点 .md before re-running. Silently rewriting is the failure mode this whole skill exists to prevent.

### 3.3 用例编号 — deterministic derivation

```
output[i].用例编号 == "TC-AR" + concat(AR.XX, AR.YYY, AR.ZZZ) + "-" + zfill(row_n, 3)
```

Concrete: for AR-SATP-04.001.001 row 7 → `TC-AR04001001-007`. For AR-SATP-99.001.003 row 12 → `TC-AR99001003-012`.

This makes IDs a **pure function of input** — re-running the skill produces byte-identical IDs. Downstream pipelines get a stable handle. Never introduce session-scoped, random, or model-generated IDs.

Regex to verify every emitted ID matches: `^TC-AR\d{8}-\d{3}$`.

### 3.4 Pass-through fields — not re-judged

These fields are copied verbatim from the input row to the output block:

```
output[i].用例类型      = input[i].用例类型      # 基本流 / 异常流
output[i].优先级        = input[i].优先级        # 1 / 2 / 3 / P0 / P1 / ...
output[i].是否准入      = input[i].是否准入      # 是 / 否
output[i].UI 自动化     = input[i].UI 自动化     # 是 / 否
output[i].API 自动化    = input[i].API 自动化    # 是 / 否
```

If you disagree with the upstream judgment ("this should be P1, not P2"; "this clearly is 准入, not 否"), that's a 测试点 issue — surface it as a notice in the output footer, but **do not rewrite the field**. Re-judging is a class of silent drift that breaks downstream agreement between test design, test execution, and defect-rate accounting.

### 3.5 预期结果 — preserved, append-only

```
output[i].预期结果 == input[i].预期结果   # same numbered items, same order
```

Keep the source's numbered list verbatim and in the same order.

**Only allowed mutation**: for 异常流 rows, if the source list omits the "平台数据保持不变" assertion, append it as a **new trailing bullet**. Never overwrite an existing bullet. Never reorder. Never collapse two bullets into one. Never add new bullets to 基本流 rows.

### 3.6 Generative fields (步骤 / 前置 / 数据) — tightly constrained

These three fields are the **only** fields you fill in generatively. Constraints:

- **Inferred from 测试点 标题 + 预期 only.** Do not pull from outside knowledge or from `--example`'s example rows.
- **Follow Playwright handoff conventions** (see `references/playwright-handoff.md`):
  - Menu items wrapped in `【...】`: `点击【项目管理】→【产品线管理】`.
  - Button labels in Chinese quotes: `点击"新增"按钮`, `点击"确认"按钮`.
  - Direct field names: `填写"名称"字段为 "测试产品线A"`.
- **Default credentials**: `admin` / `admin123` unless the 测试点 标题 explicitly names a different account.
- **Business parameters**: only what the 测试点 标题 mentions. If the title says "新增顶级产品线", use a plausible 产品线 name + 描述 — do **not** invent additional optional fields the title didn't promise.
- **Never** add a precondition or step that the 测试点 didn't promise. If the title says "新增产品线（接口主路径）", do not add "先创建一个组织" or "先登录二次确认" unless the 预期 list mentions them.

When in doubt, prefer fewer steps over more. Empty 测试数据 is acceptable when the row doesn't need data ("点击查看按钮，看到列表" needs no data).

### 3.7 No re-design

This skill **does not emit**:

- §6.1 Header / 范围与参数表 / 测试基础
- §6.2 Quality Coverage Matrix
- §6.3 COND tables
- §6.4 CI tables
- §6.7 Coverage Summary
- §6.8 Conformity Evaluation
- §6.9 RTM (full)
- §6.11 Risk segment

The 测试点 .md and its `<stem>-audit.md` companion already carry that ceremony upstream. Regenerating it here would (a) bloat the output for no benefit, (b) risk drifting from the upstream judgment, (c) violate the single-responsibility split between this skill and `kdev-test-points-v1`.

The output's *only* non-block content is: section headers grouped by AR (一/二/三/...), a final "用例集合统计" table, and the 自检清单.

---

## 4. Output skeleton

```markdown
# <被测对象> 测试用例（fielded, Playwright-handoff）

> 来源测试点：<path-to-input-测试点.md>
> 渲染模板：<path-to-example>
> 生成方式：kdev-test-cases-v1 — 1:1 renderer (no re-design)

## 一、AR-SATP-04.001.001 — <AR 标题原文>

- 用例编号：TC-AR04001001-001
- 用例名称：<= 测试点标题 byte-equal>
- 需求编号：<= AR 编号 + FR 编号（如 AR-SATP-04.001.001 / FR-007）>
- 用例类型：<= 用例类型 字段>
- 优先级：<= 优先级 字段>
- 是否准入：<= 是否准入 字段>
- UI 自动化：<= UI 自动化 字段>
- API 自动化：<= API 自动化 字段>
- 前置条件：<generative, constrained>
- 测试数据：<generative, constrained>
- 测试步骤：
  1. <generative, Playwright-friendly>
  2. ...
- 预期结果：
  1. <= 预期结果 第 1 条 byte-equal>
  2. <= 预期结果 第 2 条 byte-equal>
  ...
  N. 平台数据保持不变  ← 仅 异常流 且 源缺失时追加

---

- 用例编号：TC-AR04001001-002
...

---

## 二、AR-SATP-04.001.002 — <下一个 AR 标题>

...

---

## 用例集合统计

| 指标 | 数值 |
|---|---|
| AR 数 | N |
| TC 总数 | M |
| 准入用例数 | ... |
| 基本流 | ... |
| 异常流 | ... |
| UI 自动化候选 | ... |
| API 自动化候选 | ... |

## 自检清单

（来自 SOP_测试用例MOD.md §七 — 按字面复制，不要改写）
```

For the full §四 / §五 Playwright handoff conventions and the example's exact §七 self-check items, see [references/playwright-handoff.md](references/playwright-handoff.md) and [references/output-skeleton.md](references/output-skeleton.md).

---

## 5. Workflow

1. **Pre-flight (§1)**: verify input is a 测试点 .md, example is a fielded-block template, the two are distinct. Reject early if not.
2. **Index input**: parse all `### AR-...` headers and within each, count + read numbered rows. Record the total row count `M` — this is your output cardinality target.
3. **Read example** §二 / §样例 to confirm the field order + indentation + bullet style. Match it byte-faithfully in your output blocks.
4. **Render**: for each input row in order, emit one block. Apply §3.1–§3.6 contracts. Use the §4 skeleton.
5. **Append statistics table** (AR count, TC count, 准入数, 基本/异常 split, UI/API automation candidates).
6. **Append self-check** verbatim from the example's §七 (if present).
7. **Verify** before returning — run the §6 self-check.

---

## 6. Self-check (run before returning — §3.3 contract verification)

**Cardinality + ID**

- [ ] `grep -c "^- 用例编号：" <output>.md` equals the total numbered-row count across all AR tables in the input 测试点 .md? (use exact equality — not "approximately")
- [ ] Every `用例编号` matches the regex `^TC-AR\d{8}-\d{3}$`, and the 8-digit prefix concatenates the AR编号's three segments without dots?
- [ ] Spot-check ≥ 5 random output blocks: `用例编号` row number == its position within the AR (1-indexed, zero-padded to 3)?

**Title + pass-through preservation (byte-equality)**

- [ ] Spot-check ≥ 5 random output blocks: `用例名称` is byte-equal to the corresponding input row's `测试点标题` column (including the "超级管理员登录，" prefix if present, including any parenthetical, including any typo)?
- [ ] `用例类型 / 优先级 / 是否准入 / UI 自动化 / API 自动化` not re-judged versus input — even when the upstream judgment seems wrong?

**预期结果 preservation**

- [ ] `预期结果` numbered list preserved same-order; `平台数据保持不变` added only as a new trailing bullet for 异常流 rows when absent in source — not overwriting any existing bullet, not added to 基本流?

**Generative-field discipline**

- [ ] Steps reference only objects/fields named in the 测试点 标题 or 预期 list? No invented preconditions, accounts, or test data?
- [ ] Steps follow Playwright handoff conventions (`【菜单】`, `"按钮"`, direct field names)?
- [ ] Default credentials `admin` / `admin123` unless title explicitly names another account?

**No re-design**

- [ ] Output **does not** contain §6.1 Header / §6.2 Quality Matrix / §6.3 COND / §6.4 CI / §6.7–§6.11? (Those live with the upstream 测试点 .md.)
- [ ] No new ARs / no merged ARs / no resorted rows — input order preserved 1:1?

**Output hygiene**

- [ ] Block field order matches the example's §二 / §样例 exactly?
- [ ] Statistics table at end matches actual counts?
- [ ] Self-check copied verbatim from example §七 (if present)?

Any No → fix and re-emit. Do **not** "fix" the upstream — surface the issue back to the user and let them fix the 测试点 .md, then re-run this skill.

---

## 7. Output language

Default 中文 (matches the upstream 测试点 .md). Output file path defaults to `--output`; if absent return inline.

ARGUMENTS: $ARGUMENTS
