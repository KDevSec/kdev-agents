---
name: kdev-test-case
description: Design auditable test cases for features, APIs, UI flows, code, or full software products under ISO/IEC/IEEE 29119-4 (test design techniques — EP, BVA, decision tables, state transition, pairwise, MC/DC, error guessing) and GB/T 25000.51 / ISO 25051 (three-domain coverage + 8×31 quality sub-characteristics + 符合/部分符合/不符合 conformity verdict). Use whenever the user asks to "generate test cases", "write test cases for", "create test plan", "design tests for this API/feature/state machine", "boundary tests", "decision table tests", "pairwise combinations", "regression coverage", "什么测试点", "测试设计文档", "GB 25000 测试", "25051 测试", "软件产品测评", "就绪可用软件产品测试", "质量特性测试", "符合性测试", "用户文档测试", "产品说明测试" — even when they only paste a spec, an API contract, or a state diagram and say "测一下". Trigger on the artifact, not just the keyword.
allowed-tools: Read, Write, Glob, Grep, Bash
---

# Test Case Generator (ISO/IEC/IEEE 29119-4 × GB/T 25000.51)

Senior QA test analyst working to a dual standard:

- **29119-4** = the workshop. How to design tests — formal techniques + the pipeline `Test Basis → Test Conditions → Coverage Items → Test Cases → Test Procedures`.
- **GB/T 25000.51** (≡ ISO/IEC 25051) = the acceptance checklist. What must be tested + how to declare conformity — three domains × 8 characteristics × 31 sub-characteristics × 符合/部分符合/不符合 verdict.

Without 29119-4 your tests are ad-hoc. Without 25000.51 you only test functions and miss the non-functional half. Use both. Every output must be auditable on both axes.

---

## 1. Modes (declare first, gate the rest)

The volume of ceremony depends on **why** the user wants tests. Don't apply third-party-certification rigor to a feature spec, and don't ship a bare API checklist when an audit is on the line.

| Mode | When | Main file emits | Audit companion (`<stem>-audit.md`) |
|---|---|---|---|
| `testpoints-to-cases` (auto when `--input` is itself a SP15 测试点 .md AND `--example` is fielded code-block template, see §1.2) | upstream is an already-generated 测试点 .md (this skill's prior `feature-spec-lite` output) and user wants to render it as fielded test cases for Playwright generator | One fielded `【测试用例信息】` code block per 测试点 row (1:1 mapping, verbatim 用例名称) + collection-stats table + self-check | none — 测试点 .md's audit companion already exists upstream |
| `feature-spec-lite` (auto when `--example` is SP15-style, see §1.1) | internal PRD/spec **and** user provided an SP15/xmind/SOP 测试点 template | 范围与参数表 + §6.5 TC (example columns intact, **no extra columns**) + RTM + Risk + 自检清单 | §6.1 Header, §6.2 Quality Matrix (in-scope rows only), §6.3 COND, §6.4 CI, §6.7 Coverage Summary, §6.8 Conformity light, §6.11 Risk-detail |
| `feature-spec` | internal PRD/spec; software being built; no docs published yet; no SP15-style example | Header, Quality Matrix (in-scope rows), Conditions, CIs, TC core, Coverage Summary, RTM, Risk | optional |
| `api-contract` | one or more API endpoints with request/response schema | Header, Conditions, CIs, TC core, Coverage Summary, RTM | Quality Matrix collapsed to in-scope rows only; TC-DOC skipped; Conformity light |
| `full-conformity` | RUSP / COTS / 25051 软件产品测评 / 第三方测评机构验收 | All §6.1–§6.11 in [references/output-templates.md](references/output-templates.md) | none (everything in main) |

**Pick the mode in this order**: explicit `--mode` flag > user keywords (`测评`/`RUSP`/`COTS`/`25051`/`认证` → `full-conformity`; `接口`/`API`/single-endpoint paste → `api-contract`; **测试点 .md as `--input` + fielded-block example → `testpoints-to-cases`**; SP15-style example detected → `feature-spec-lite`; otherwise `feature-spec`). When ambiguous, ask once.

`--lite` further compresses any mode by writing only Header + Conditions + TC core + RTM. Use when the user wants a sketch.

### 1.1 SP15-style example auto-detection

An `--example` is SP15-style when **any** of the following match — in which case `feature-spec` auto-promotes to `feature-spec-lite` and the audit scaffolding moves to a companion file (don't bloat the main file):

- The example contains a row matching `AR-[A-Z]+-\d{2}\.\d{3}\.\d{3}` (SATP-style three-segment AR编号), **or**
- The example header has columns `测试点标题 | 预期结果 | 用例类型 | 是否准入` and total column count ≤ 9, **or**
- The example file path or content references `SOP_测试点`, `SP15`, `xmind`, `playwrightmode`.

When detected, **prefer the example's own self-check / RTM / 残余风险 sections if present** rather than emitting fresh ones — they are the user's house style.

### 1.2 `testpoints-to-cases` auto-detection (test points → fielded test cases)

This is a separate, downstream pass — different from spec → 测试点. The input is itself a SP15 测试点 .md (typically this skill's own `feature-spec-lite` output from a prior session); the user now wants to render that 测试点 .md as Playwright-friendly fielded test cases. Detect when **all three** are true:

- `--input` resolves to a markdown file containing **both** `### AR-[A-Z]+-\d{2}\.\d{3}\.\d{3}` headers **and** numbered table rows shaped `| # | 测试点标题 | 预期结果 | ...` (i.e., it's a 测试点 .md, not raw spec), **and**
- `--example` resolves to a markdown file whose §二 / §样例 contains a fielded code block with `用例编号` / `用例名称` / `需求编号` lines (i.e., `SOP_测试用例MOD`-style), **and**
- The `--input` and `--example` are clearly distinct artifacts — the input is structured as 测试点 (one row per case), the example is structured as fielded blocks (one block per case).

Mode behaviour (locked — these are correctness invariants, not stylistic preferences):

- **1:1 mapping mandatory**: each numbered table row in the input → exactly one fielded code block in the output. No aggregation across rows. No skipping. No invented rows. Verifiable: `grep -c "^- 用例编号：" 输出.md == 上游测试点行数`.
- **用例名称 = 测试点标题 verbatim**: do **not** paraphrase, do **not** drop the "超级管理员登录，" prefix, do **not** "improve" the wording. The traceability chain (测试点 → 用例 → Playwright test name) depends on byte-equal name match. If the title looks suboptimal, that's an upstream 测试点 issue — stop and report rather than silently rewrite.
- **用例编号 deterministic derivation**: `TC-AR{8 位 AR 数字串联}-{3 位行号 zero-pad}`. For `AR-SATP-04.001.001` row 7 → `TC-AR04001001-007`. This makes re-runs idempotent and gives downstream pipelines a stable handle.
- **Pass-through fields, not re-judged**: 用例类型 / 优先级 / 是否准入 / UI 自动化 / API 自动化 are copied from the 测试点 row as-is. If the generator disagrees with the upstream judgment, that's a 测试点 issue — fix the upstream, then re-run.
- **预期结果 preserved**: keep the source's numbered list verbatim and same-order. For 异常流, append "平台数据保持不变" or equivalent **as a new bullet** if the source omits it; never overwrite an existing bullet.
- **Step inference is the only generative step**: 测试步骤 + 前置条件 + 测试数据 are reconstructed from the 测试点 标题 + 预期 by following Playwright-handoff conventions (§五 of the example): `【菜单】` for menu items, `""按钮` for buttons, direct field names; default account `admin`/`admin123` plus business params named in the 测试点 标题. Do not invent steps the 测试点 didn't promise.
- **No re-design**: do not add risk sections, RTM, conformity tables, or quality-coverage matrices in this mode. The 测试点 .md and its `<stem>-audit.md` companion already carry that ceremony upstream. The output is a flat fielded-case file plus a small statistics table + 自检清单.
- **Output skeleton**: section headers grouped by AR (一/二/三/...), each AR holds its source rows in order, blocks separated by `---`, ending with a "用例集合统计" table (AR count, TC count, 准入数, 基本流/异常流, automation candidates) and the 自检清单 from `SOP_测试用例MOD.md` §七.

---

## 2. Arguments

```
/test-case-generator [--input <path>]
                     [--example <path>]
                     [--output <path>]
                     [--mode feature-spec|api-contract|full-conformity]
                     [--lite]
                     [free-form prompt]
```

- `--input <path>` — spec / requirements / API contract / source code. May be repeated.
- `--example <path>` — a template the user wants the **rendering layer** to follow (e.g., internal xmind/xlsx-aligned format). See §3.
- `--output <path>` — where to Write the result. If absent, return inline.
- `--mode` — explicit mode override. See §1.
- `--lite` — compressed output.

If only a free-form prompt is given (no flags), treat the prompt body as the test basis and infer the mode.

---

## 3. Template override rule (read this — it's the bug we're fixing)

When the user gives `--example <template>`, **the example replaces only the §6.5 Test Case rendering layer**. Everything else — Header, Quality Coverage Matrix, Test Conditions, Coverage Items, Coverage Summary, Conformity Evaluation, RTM, Risk — must still appear.

**Default placement by mode:**

| Mode | Audit scaffolding goes to |
|---|---|
| `feature-spec-lite` | **companion file `<stem>-audit.md`** (mandatory — main file stays clean for SP15/xmind round-trip) |
| `feature-spec` | appendix sections after main, or companion file (user's choice) |
| `api-contract` | appendix or companion |
| `full-conformity` | inline in main (single auditable document) |

Why companion-by-default for `feature-spec-lite`: SP15 / SOP 测试点 templates are designed for direct conversion into xmind / xlsx / playwrightmode. Stuffing dual-standard ceremony (§6.1 Header / §6.2 8×31 matrix / §6.3 COND / §6.4 CI) **into** the main file breaks the column contract and balloons the document by ~2× (observed: 336 lines without ceremony → 559 lines with it). The audit trail is non-negotiable, but its **placement** must respect the rendering contract the user picked.

### 3.1 Column contract — do not extend the example's row schema

When the example's §6.5 table has `cols ≤ 9` (typical SP15 schema is 7–8 cols: `# | 标题 | 预期 | 类型 | 准入 | UI自动化 | API自动化 | 优先级` ± `标记`):

- **Do NOT** add `覆盖CI` / `质量子特性` / `测试技术` as new right-side columns. Doing so breaks md→xmind/xlsx scripts that depend on column count.
- **Instead**, surface those four invariants (CIs / Sub-char / Domain / Technique) in one of these places, in priority order:
  1. **Companion audit file** `<stem>-audit.md` with an "AR-CI 映射表" — one row per AR (not per TC), referencing TC ranges. ← preferred
  2. Per-AR header annotation: `### AR-XXX-NN.NNN.ZZZ — 标题（覆盖 CI-001..CI-005｜功能完备性 / 正确性｜EP+DT）`
  3. Title prefix on each TC row: `[CI-EP-01,功能正确性,软件] 超级管理员登录，...`

Choose option 1 by default. Use 2/3 only when companion files are inconvenient (e.g., user asked for a single deliverable).

When the example's `cols ≥ 10` (Excel matrix style), the schema already has room — extending it with the 4 invariant columns is fine. See [references/template-override.md](references/template-override.md) for the per-family rules.

### 3.2 Hard constraints (lock these before generating, verify after)

- **AR 编号空间锁定**：grep the example for `AR-[A-Z]+-\d` patterns (or read the example's §5 已填示例 / §0 索引表). The prefix you find (e.g., `AR-SATP-`, `AR-KDevSec-`) is the **only** legal prefix for the output. **Never** invent a new prefix (no `AR-PVM-`, no `AR-MYNAME-`). If no example, default to `AR-SATP-`.
- **模块号语义锁定**：if the example's §1.5 (or equivalent) declares module-number conventions (e.g., `04=产品线 / 05=项目 / 99=通用`), reuse them. Do **not** flatten everything into one module (e.g., putting all 23 FRs under `AR-SATP-16.*`).
- **角色单一锁定**：pick one role term in the first TC and reuse it across the whole file. Default `超级管理员`. Do not switch to "管理员" / "用户" mid-file unless spec mandates per-role variants.
- **AR 内行数 ≤ 8**：if any AR table would emit ≥ 9 rows, split it into `.001` / `.002` / `.003` sub-AR by sub-capability (CRUD vs uniqueness vs delete-precondition vs list-query). Target ≈ 5 rows/AR (v0.1 shape).
- **One-FR-one-AR — do NOT merge cross-FR common test points**: even if three modules each have a "delete-precondition" check, they belong in three separate ARs (one per business module), not a single shared "通用删除前置" AR. Duplication is preferable to losing per-FR traceability.
- **Default no module 99 — disperse cross-cutting constraints inline (v2.1 lesson)**: even constraints that apply across all entities (FR-004 op-log 4 elements, FR-002 logical delete, link smoke chains, E2E pass rate) **disperse** rather than aggregate:
  - FR-004 操作日志四要素 → inline to **every** CRUD row's expected末段 (`...N. 操作日志含 操作人/时间/目标实体/操作类型 4 要素`); 100% sampling + 回滚不悬挂 lives in the most cross-entity business AR (e.g. the link-log AR), not a fresh module-99 AR.
  - FR-002 逻辑删除 → inline to **each** delete AR (write assertion `del_flag=1, 物理记录在`) + **each** list query AR (filter assertion `已逻辑删除记录不返回`).
  - Cross-entity smoke chain (e.g. SC-001 "5-minute new product line → project → version") → place at the **terminal** AR of the chain (e.g. "new version"), not in a standalone module-99 chain AR.
  - E2E pass rate (e.g. SC-003 "4 US through-rate = 100%") → **don't** emit a dedicated TC; assert by the suite's overall pass rate, note in RTM.
  - Module 99 is acceptable **only** when a constraint is truly cross-entity AND impossible to inline anywhere — a rare case in practice. **Patterns** shared across entities (e.g. "delete precondition") still get separate ARs per entity, not merged.
- **CRUD = three ARs (新增 / 编辑 / 删除), not one lumped AR (v2.1 lesson)**: split each entity's CRUD basics into three independent ARs by verb. Don't pack "create + edit + delete" together. Required content per verb-AR:
  - **新增 AR** — 必填字段查看 + 正常创建 (含 4 要素操作日志 inline) + 每个必填字段独立"为空"异常行 + 长度边界 + **`<script>` 特殊符号** + 关联实体不存在的 API 直连拒绝.
  - **编辑 AR** — 修改主字段（如状态/描述）+ **修改非必填字段为空 → 接受 + NULL 持久化**（必有这一行）+ 修改必填字段为空 → 拒绝 + 修改至唯一性冲突 → 拒绝 + **`<script>` 特殊符号** + API 直连关联到已删实体拒绝.
  - **删除 AR** — 正常删除 (含 `del_flag=1` + 物理记录在 + 4 要素操作日志 inline) + 每条删除前置（带子/带关联实体）独立异常行 + API 直连删除不存在记录拒绝.
- **No abstract non-functional ARs**: do **not** invent ARs for security / compatibility / i18n / a11y / maintainability / portability **unless** the spec contains an explicit SC/FR clause for that direction. When in doubt, omit. (Performance is treated separately — see next bullet.)
- **Performance is entirely OOS for functional test suites (v2.1.1 lesson — supersedes the prior ≥1000-record floor)**: performance / time-behaviour assertions (e.g. `SC-004 ≤2s` for list paging, Tab-switch response, search response) are **not part of functional test case design**, regardless of data scale. Do **not** emit dedicated performance TCs at any tier (200 / 2000 / 20000 / higher). Do **not** inline `≤Ns` assertions into list-query AR rows either — list-query ARs only assert *functional correctness + field-return structure + filter/sort/paging logic*, never response time. SC-004-style time-behaviour claims must be **declared OOS in the residual-risk section** with an explicit handoff note ("offloaded to a separate benchmark / performance suite"). The reason: mixing time assertions into functional rows produces flaky tests, conflates two test populations, and forces functional CI to bear performance noise. If the user explicitly demands performance coverage in the same document, push back — recommend a separate benchmark suite as the right home.
- **Name-field XSS minimum subset (v2.1 lesson)**: every name-field-bearing 新增/编辑 AR emits one row `名称含特殊符号 \<script\>` as the minimum XSS subset (异常流 — reject or escape-and-store-safely). Full XSS / SQLi sweep belongs to a separate cso/security-audit pass; this row is the floor, not the ceiling.
- **Exception flow completeness floor per AR**: for each business AR, the exception-flow rows must independently cover every validation declared in the spec for that FR — empty/required, length over-cap, uniqueness conflict, non-existent reference, format-illegal, state-illegal, dictionary-out-of-range, **special character `<script>`**, etc. Each as its own row. Do not consolidate ("名称为空 + 长度超长") into one row.
- **非性能数量化承诺必有用例（v2.1.1 修订）**：spec 中每一条非性能数量化承诺（`≥N条`、`100% 覆盖`、`违规率=100%`、`触发率=100%` 等）都至少有一条对应 TC，且**就近放在它所约束的业务功能 AR**，不汇总。**性能/时间特性承诺（`≤Ns`）整体例外** —— 见上方"Performance is entirely OOS for functional test suites" 规则：所有数据档位均不单设性能 TC，统一在残余风险段标注 OOS + benchmark 转出说明。

### 3.3 1:1 mapping contract (mode `testpoints-to-cases` only)

When `--input` is itself a 测试点 .md (see §1.2 detection), the rendering layer is governed by a strict **byte-equality + arithmetic-equality** contract — not by the heuristic-rich rules used in the spec-derived modes:

- **Cardinality**: `count(output 用例编号 lines) == count(input 测试点 numbered rows)` exactly. Verifiable via `grep -c "^- 用例编号：" <output>.md` against the input's row total.
- **Title preservation**: `output[i].用例名称 == input[i].测试点标题` byte-for-byte. Any tempting "polish" (drop "超级管理员登录，" prefix, shorten parenthetical, fix typos) is **forbidden** — those are upstream issues, fix the 测试点 .md and re-run.
- **ID derivation**: `output[i].用例编号 == "TC-AR" + concat(AR.XX, AR.YYY, AR.ZZZ) + "-" + zfill(row_n, 3)`. Pure function of input — re-running the skill produces byte-identical IDs. Do not introduce session-scoped or random IDs.
- **Pass-through fields**: `output[i].{用例类型, 优先级, 是否准入, UI自动化, API自动化}` copied verbatim from `input[i]`. Re-judging is a class of silent drift; if disagreement exists, surface it as a notice and let the user fix the 测试点.
- **Expected list verbatim + append-only**: `output[i].预期结果` keeps source numbered list in same order. For 异常流, append "平台数据保持不变" as a new bullet only if absent — never overwrite an existing bullet.
- **Generative fields are constrained**: 测试步骤 / 前置条件 / 测试数据 are inferred only from 测试点 标题 + 预期 (steps must be Playwright-friendly per the example's §五: 【菜单】, "按钮", direct field names). Default credentials `admin`/`admin123` plus business params named in the title; **never** add a step or precondition the 测试点 didn't promise.

Why this rigor: the downstream Playwright generator hashes `用例名称` to function names and matches `用例编号` against test-result rows. Silent paraphrase or ID drift here breaks the entire test → run → defect-triage chain — far more damaging than the savings from "improving" a few sentences. Other modes generate from spec and have judgment latitude; **this mode is a pure renderer**.

---

## 4. Pipeline (29119-4 §6)

```
Read inputs → Declare scope (3 domains) → Quality Coverage Matrix → Test Conditions
            → Coverage Items (apply techniques) → Test Cases → Procedures + RTM + Conformity
```

Each step has an output artifact. The mode (§1) determines which are emitted **and** whether they go to the main file or the audit companion.

> **`testpoints-to-cases` bypasses this pipeline entirely.** That mode is a pure 1:1 renderer (测试点 .md → fielded test cases), not a re-derivation. Skip steps 2–5 and 8–11; only step 6 (Test Cases) and step 13 (Self-check) apply. The audit ceremony is already carried by the upstream 测试点 .md and its `<stem>-audit.md` companion — do not regenerate them.

| Step | Output | feature-spec-lite (main / audit) | feature-spec (main / audit) | api-contract | full-conformity |
|---|---|:-:|:-:|:-:|:-:|
| 1 Read inputs | (mental) | ✓ / — | ✓ / — | ✓ | ✓ |
| 2 Declare 3 domains | §6.1 Header `Scope` line | 范围与参数表 / Header full | ✓ / — | ✓ | ✓ |
| 3 Quality Coverage Matrix | §6.2 (8×31) | — / ✓ in-scope rows | ✓ in-scope rows / — | ✓ in-scope rows | ✓ all 31 rows |
| 4 Test Conditions | §6.3 COND-NN | — / ✓ | ✓ / — | ✓ | ✓ |
| 5 Coverage Items | §6.4 CI-NN | — / ✓ | ✓ / — | ✓ | ✓ |
| 6 Test Cases | §6.5 TC-NNN | ✓ (example columns intact) / — | ✓ / — | ✓ | ✓ |
| 7 TC-DOC (product desc + user docs) | §6.6 | skip with reason | skip with reason | skip with reason | ✓ |
| 8 Coverage Summary | §6.7 | — / ✓ | ✓ / — | ✓ | ✓ |
| 9 Conformity Evaluation | §6.8 | — / ✓ light (per-FR pass/fail) | ✓ light / — | ✓ light | ✓ full table |
| 10 RTM | §6.9 | ✓ short table (FR↔AR↔关键测试点) / ✓ full bidirectional | ✓ / — | ✓ | ✓ |
| 11 Defect categorisation | §6.10 | placeholder / — | placeholder / — | placeholder | ✓ |
| 12 Risk & out-of-scope | §6.11 | ✓ 残余风险与未覆盖说明段 / — | ✓ / — | ✓ | ✓ |
| 13 Self-check | §8 mirror | ✓ / — | ✓ / — | ✓ | ✓ |

**Reading the lite column**: the main file gets a "范围与参数" header table (not a full §6.1 header dump), §6.5 TC tables in the example's exact column count, a short FR↔AR↔关键测试点 RTM table, an explicit "残余风险与未覆盖" section, and a 13-item self-check. The audit companion file (`<stem>-audit.md`) gets the heavy ceremony — full Header, in-scope quality matrix, COND/CI tables, full bidirectional RTM, conformity-light per-FR table.

Templates and exact field definitions for §6.1–§6.11 → [references/output-templates.md](references/output-templates.md).

---

## 5. Choosing techniques

Two routing axes that overlap: **input shape** (29119-4) and **quality sub-characteristic** (25000.51). Apply both and union the technique set.

**By input shape:**
1. State machine / lifecycle / workflow → State Transition (mandatory: 0-switch + invalid)
2. Multi-condition business rule → Decision Table
3. Numeric/length/date with bounds → EP + BVA together
4. ≥4 parameters × ≥3 values → Pairwise
5. Structured strings (regex, JSON schema, URL, grammar) → Syntax Testing + EP on field values
6. End-to-end journey → Scenario Testing
7. Source code with safety-criticality → MC/DC or Branch
8. **Always layer**: Error Guessing + a domain checklist (OWASP / WCAG / etc.)

**By sub-characteristic** — for any sub-characteristic marked "在范围" in §6.2, use the technique floor in [references/quality-characteristics.md](references/quality-characteristics.md). Don't generate placeholder cases for sub-characteristics marked out of scope; record the reason in §6.2 and you're done.

---

## 6. Density heuristics (so the output scale matches the input scale)

A spec with N functional requirements should not produce 5N cases (under-tested) or 50N cases (bloat). Aim for:

- **≥1 TC per FR or per acceptance scenario** (functional completeness floor)
- **CRUD as 3 ARs by default**: one entity's CRUD basics emit ≈ 3 ARs (新增 / 编辑 / 删除) before counting uniqueness / list / 人员 etc. Don't lump them.
- **≥4 BVA cases per bounded numeric or length field** — extreme-low / valid / invalid-type / upper-bound (e.g. for 漏洞数 must include `=0`, `=-1`, `=1.5`, `=非数字`, `=int 上界`)
- **Name-field XSS floor**: every 新增/编辑 AR for a name-bearing entity emits 1 row `名称含特殊符号 \<script\>` (异常流, 拒绝或转义安全)
- **Edit-clears-optional floor**: every 编辑 AR emits 1 row "修改非必填字段为空 → 接受 + NULL/空字符串持久化" (often missed)
- **≥1 negative TC per uniqueness constraint, foreign-key constraint, state-machine transition, or precondition** (error-path floor)
- **≥1 TC per in-scope sub-characteristic in §6.2** (quality conformity floor)
- **≥1 negative TC per *non-performance* quantitative claim in product description / user documentation** (claim-falsifiability floor — covers `≥N条`, `100% 覆盖`, `违规率=100%`, `触发率=100%`, etc.). **Performance/time-behaviour claims (`≤Ns`) are excluded** — see next bullet.
- **Performance is OOS for functional suites (v2.1.1, supersedes the prior ≥1000 floor)**: do not emit any performance TC at any data scale. Do not inline `≤Ns` assertions into list-query AR rows. Declare `SC-004`-style time-behaviour claims OOS in the residual-risk section with a benchmark-handoff note. Functional list-query ARs assert correctness, structure, and filter logic only.
- **State-machine coverage**: 0-switch (every adjacent pair) + ≥1 invalid transition + double-confirm dialog confirm/cancel both branches if the spec mandates it
- **Decision-table coverage**: every rule row including the impossible/null-edge combinations (e.g., `parent_id IS NULL` on uniqueness)

Use the floor as a budget, not a target. For a 23-FR spec expect roughly 100–120 cases (≈ 5 cases × 20–25 AR after CRUD-split), weighted toward FRs with state machines, uniqueness, or numeric bounds. **Per-AR ceiling = 8 rows** — when an AR would emit 9+ rows, split into `.001` / `.002` sub-AR. If your output is far below or above this band, double-check before emitting — likely you skipped FRs or fabricated filler.

---

## 7. Workflow

1. **Read** `--input` files and any referenced sub-files (Read/Glob/Grep). If the basis lacks both quantitative claims and procedural steps, warn before continuing.
2. **Decide mode** (§1). Announce it: `Mode: feature-spec — user docs not published yet, §6.6 TC-DOC will be skipped with reason`.
3. **Declare scope** (3 domains, §6.1).
4. **Fill Quality Coverage Matrix** (§6.2) — row-per-sub-characteristic, mark in/out of scope with reason. In `feature-spec` and `api-contract` you may omit rows for sub-characteristics with no in-scope evidence; in `full-conformity` enumerate all 31 rows.
5. **Derive Conditions** by §5 routing + §6 density.
6. **Derive Coverage Items**, applying techniques.
7. **Write Test Cases**. Each TC must include **{ Coverage CIs · Quality Sub-characteristic · Domain · Technique · Priority + reason · Pre/Post-conditions · Expected (UI/API/DB/log facets) }**. If `--example` was given, apply §3 override rule.
8. **Generate TC-DOC** (§6.6) for `full-conformity`; otherwise skip with one-line reason.
9. **Coverage Summary, Conformity Evaluation, RTM** (§6.7–§6.9).
10. **Risk & out-of-scope** (§6.11) — always explicit; hidden gaps violate 25000.51.
11. **Self-check** (§8) before returning.

For a 1-FR end-to-end walk-through (Test Basis → COND → CI → TC → RTM), see [references/example-walkthrough.md](references/example-walkthrough.md).

---

## 8. Self-check (run before returning)

**Mode + scaffolding placement**

- [ ] Mode announced + appropriate sections emitted (§4 mapping)?
- [ ] If mode is `feature-spec-lite`: audit scaffolding is in `<stem>-audit.md` (not prefixed/appended to main)?
- [ ] If `--example` given: §6.5 follows the example **and** §6.1/§6.2/§6.7–§6.11 still present (in main file or `<stem>-audit.md`)?
- [ ] If example columns ≤ 9: main §6.5 column count == example column count (no `覆盖CI/质量子特性/测试技术` injected as extra columns)?

**1:1 mapping closure (mode `testpoints-to-cases` only — §3.3 contract)**

- [ ] `grep -c "^- 用例编号：" <output>.md` equals the total numbered-row count across all AR tables in the input 测试点 .md? (cardinality)
- [ ] Spot-check ≥ 5 random output blocks: `用例名称` is byte-equal to the corresponding input row's `测试点标题` column (including the "超级管理员登录，" prefix)? (title preservation)
- [ ] Every `用例编号` matches the regex `^TC-AR\d{8}-\d{3}$`, and the 8-digit prefix concatenates the AR编号's three segments without dots? (deterministic ID)
- [ ] `用例类型 / 优先级 / 是否准入 / UI自动化 / API自动化` not re-judged versus input? (pass-through)
- [ ] `预期结果` numbered list preserved same-order; "平台数据保持不变" only added as a new trailing bullet for 异常流 when absent in source — not overwriting any existing bullet?
- [ ] Steps reference only objects/fields named in the 测试点 标题 or 预期; no invented preconditions or test data? (no over-generation)
- [ ] Output **does not** regenerate §6.1 Header / §6.2 Quality Matrix / §6.3 COND / §6.4 CI / §6.7–§6.11 — those live with the upstream 测试点 .md?

**Naming + role + structure locks (§3.2)**

- [ ] AR prefix matches the example's namespace (e.g., `AR-SATP-`); no invented prefix like `AR-PVM-`?
- [ ] Module numbering matches example's convention (no flattening every FR into one module)?
- [ ] Single role used throughout; no mid-file switch from `超级管理员` → `管理员`?
- [ ] Every AR table ≤ 8 rows; otherwise split into sub-ARs?

**Coverage discipline (v0.1 + v2.1 lessons)**

- [ ] **One FR = one AR**: cross-FR similar test points are NOT merged into a shared AR; each FR has its own AR even if patterns repeat?
- [ ] **CRUD split**: each entity's CRUD basics are 3 ARs (新增 / 编辑 / 删除), not 1 lumped AR?
- [ ] **Edit AR has "modify optional field to empty → accept" row**? (Required floor — easy to miss)
- [ ] **Name-bearing 新增/编辑 ARs have a `<script>` special-character row**? (Minimum XSS subset)
- [ ] **No module 99 AR by default**? FR-004 op-log 4 elements inline to each CRUD row's expected末段; FR-002 logical delete inline to each delete + list-query AR; chain smoke at terminal AR; E2E pass rate not a separate TC.
- [ ] **No abstract non-functional ARs**: no security / compat / i18n / a11y AR unless the spec has an explicit SC/FR clause for it? (Performance is always excluded — see next item.)
- [ ] **Performance entirely OOS (v2.1.1)**: no list-query AR row asserts `≤Ns` / response time at any data scale (200 / 2000 / 20000 / higher); no dedicated performance TC anywhere; SC-004-style time-behaviour claims appear in the residual-risk section with explicit benchmark-handoff wording (e.g. "由独立 benchmark 集合兜底")?
- [ ] **Exception completeness per AR**: each business AR has an independent exception-flow row for every validation declared in the spec (空 / 长度 / 唯一 / 不存在 / 格式 / 状态 / 字典越界 / 特殊符号 …)? Not consolidated into one "X 且 Y" row?

**Test-design technique floors**

- [ ] Every TC has { CIs · Quality Sub-char · Domain · Technique · Priority · Pre/Post · Expected } — somewhere (main row or audit companion)?
- [ ] BVA: every bounded numeric/length field has at least 4 cases — extreme-low, valid, invalid-type, upper-bound?
- [ ] DT: covers every rule row; impossible / NULL-edge combinations marked explicitly?
- [ ] ST: 0-switch (every adjacent state pair) + ≥1 invalid transition + double-confirm dialog confirm/cancel both branches if applicable?
- [ ] Every *non-performance* quantitative claim in spec (`≥N条`, `100% 覆盖`, `违规率=100%`, etc.) has a TC, placed inline next to its functional anchor (not in a separate "通用" AR)? **Performance claims (`≤Ns`) are excluded — they belong in residual-risk OOS, not in functional TCs.**
- [ ] In `full-conformity`: every user-doc procedure has a TC-DOC?

**Audit closure**

- [ ] Conformity Evaluation only uses 符合 / 部分符合 / 不符合 / PNT, citing TC IDs and measurements?
- [ ] RTM bidirectionally closes (every FR/SC/US has at least one AR row; every AR cites its source); cross-cutting FRs (FR-002, FR-004, etc.) have a "分散承载" row showing which business ARs absorbed them?
- [ ] Risk & out-of-scope section explicit (especially: batch ops, 权限码, i18n, RDM/CQ, 视觉, 可维护性, **性能/时间特性整体 OOS + benchmark 转出说明** 等)?
- [ ] Density within §6 band (≈ 5 cases × AR_count, target 100–120 for 23 FR after CRUD-split)?

Any No → fix and re-emit. Don't ship a partial dual-standard document.

---

## 9. Output language

Default 中文; switch only if the user asks. File path defaults to `--output`; if absent return inline. If `--example` triggered an audit companion, name it `<stem>-audit.md` next to the main output.

ARGUMENTS: $ARGUMENTS
