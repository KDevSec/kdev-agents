# 评审专家(reviewer) 数字员工 TDD 实施 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 按 [spec v0.2](../specs/2026-06-12-评审专家reviewer接入设计-design.md) 把第 4 个员工评审专家（callee 形态）落地：staff 花名册 + dispatch-table + 7 agent + 6+1 standards + 兑现 dev3/req3 评审 gate（reviewer-expert 真发函），全部由 pytest 契约测试守。

**Architecture:** 评审专家是 **callee 员工**（非 flow-owner）：无自有 flow-state、不复用 kdev-flow-driver；被 caller 的 R3 review gate 发函调用（B 轨 handoff），fan-out 到 6 评审能力 agent → 各出百分制评分表 → reviewer-orchestrator inline 仲裁 + 双重通过条件聚合 → 回 verdict，caller `record-gate --by reviewer-expert`。**kdev-core 零改**（reviewer 是纯编排/prose 概念，引擎只读 kind/on_pass/on_reflow；`record-gate --by` 已支持任意值）。

**Tech Stack:** YAML（staff.yml / dispatch-table / node-table）+ Markdown（agent persona / standards / 编排 prose）+ pytest 结构契约测试（house style：见既有 `test_staff.py` / `test_agents.py` / `test_orchestration_config.py`）。**无 Python 运行时代码**——员工由真实 Claude dispatch 执行，测试只锁产物的存在性 + 结构 + 跨产物一致性。

**关键事实（实施前必读，已核验）：**
- kdev-core python **完全不读 `reviewer` 字段**（`node_machine.get_next_actions` 把整个 `gate_spec` 透传给编排器；只 `kind/on_pass/on_reflow` 参与状态机）→ reviewer = 纯编排概念。
- `record-gate --by`（cli.py:275，default `"ai"`）**已支持任意值** → `--by reviewer-expert` 零改。
- 既有 `test_gate_specs_targets_valid_and_reviewer_bound` 已断言 `spec["reviewer"] in {"self","reviewer-expert"}`；dev-engineer 3 gate **已是** `reviewer-expert`（只是 gate-decision-logic prose 标 deferred）；req-architect 3 gate 现为 `self`。
- canonical 员工形态：`staff.yml` 花名册 + `agents/<id>.md`（frontmatter `name/description/model` + 4 段 `## Identity/## Principles/## Critical Actions/## Capabilities`）+ `orchestration/*.yml`。
- 派单全名 `kdev-team:<agent-id>`（G-009）；plugin 改 agent 须 bump version + 刷 marketplace（G-004）。

**本期 scope 边界（YAGNI，spec §9 + 本 plan 收敛）：**
- ✅ 做：staff callee 条目 + dispatch-table + 7 agent + 6+1 standards + req3 gate 翻 reviewer-expert + dev3 去 deferred prose + reviewer 发函编排 prose + plugin bump。
- ⏸ **deferred（本 plan 不做，留 follow-up）**：**L1 flow-config per-gate reviewer 旋钮**——kdev-core 现无「per-gate reviewer 的 L0/L1 config merge」（config 只有 run 级 review_mode/auto_mode）。本期 reviewer 走 **L0 node-table 字段**（self|reviewer-expert）+ 编排读取；per-gate L1 覆盖需 kdev-core 补 config-merge，留后续单独 plan。「回退 self」逃生门本期靠手改 node-table reviewer 字段 / review_mode 人确认轴覆盖。
- ⏸ deferred：核心 10 余 4 评审能力（测试设计/执行/需求方向/迭代拆分，无 caller gate）· 扩展 6 · mode-2 记忆他评（Q-017 已移交蒸馏）· CQO。

---

## File Structure

| 文件 | 责任 | 动作 |
|---|---|---|
| `plugins/kdev-team/staff.yml` | 花名册：reviewer callee 条目 + 三员工 `kind` 判别 | Modify |
| `plugins/kdev-team/orchestration/reviewer.dispatch-table.yml` | 评审路由清单（6 cap→agent→standards→阈值→评对象→caller_gate）；callee 不是 flow node-table | Create |
| `plugins/kdev-team/standards/reviewer/通用评分模板.md` | 100 分制 schema + 双重通过条件 + 循环规则 + 🔴/🟡/⚪ 分级标准 | Create |
| `plugins/kdev-team/standards/reviewer/{SR需求,用户故事,原型,方案架构,代码质量,安全}评审.md` | 6 cap 各自评分维度 + checklist + 阈值 + 评分表 schema | Create |
| `plugins/kdev-team/agents/reviewer-orchestrator.md` | 被调入口：读 request→fan-out→仲裁→双重条件聚合→回 verdict | Create |
| `plugins/kdev-team/agents/reviewer-{sr,story,prototype,design,code,security}.md` | 6 只读评审能力 agent | Create |
| `plugins/kdev-team/orchestration/req-architect.node-table.yml` | g-sr/ar-proto/design-review reviewer `self`→`reviewer-expert` | Modify |
| `plugins/kdev-team/skills/kdev-flow-driver/references/gate-decision-logic.md` | dev3 去 deferred「真发函 reviewer」+ req3 reviewer-expert 判据 | Modify |
| `plugins/kdev-team/skills/kdev-flow-driver/references/node-agent-routing.md` | 追加 reviewer 发函 dispatch 段（caller→reviewer 上下文构造）| Modify |
| `plugins/kdev-team/tests/test_staff.py` | +reviewer callee 断言 + kind 校验 | Modify |
| `plugins/kdev-team/tests/test_agents.py` | +7 reviewer agent 存在 + frontmatter/段落 + 只读原则 | Modify |
| `plugins/kdev-team/tests/test_reviewer_dispatch.py` | dispatch-table schema + 6 cap↔caller_gate 一致性 + standards 存在 | Create |
| `plugins/kdev-team/.claude-plugin/plugin.json` + `CHANGELOG.md` + `<root>/.claude-plugin/marketplace.json` | bump v0.6.0 | Modify |

**Reviewer agent id 命名（kebab，前缀 `reviewer-`）：** `reviewer-orchestrator` `reviewer-sr` `reviewer-story` `reviewer-prototype` `reviewer-design` `reviewer-code` `reviewer-security`。

**Standards 文件名（cap→file）：** sr→`SR需求评审.md` · story→`用户故事评审.md` · prototype→`原型评审.md` · design→`方案架构评审.md` · code→`代码质量评审.md` · security→`安全评审.md`。

---

## Task 1: staff.yml — reviewer callee 条目 + kind 判别

**Files:**
- Modify: `plugins/kdev-team/staff.yml`
- Test: `plugins/kdev-team/tests/test_staff.py`

- [ ] **Step 1: 写失败测试**（追加到 test_staff.py 末尾）

```python
def test_kind_discriminator_on_all_employees():
    d = yaml.safe_load(STAFF.read_text(encoding="utf-8"))
    emps = d["employees"]
    assert emps["dev-engineer"]["kind"] == "flow-owner"
    assert emps["req-architect"]["kind"] == "flow-owner"
    assert emps["reviewer"]["kind"] == "callee"


def test_reviewer_callee_entry():
    d = yaml.safe_load(STAFF.read_text(encoding="utf-8"))
    emp = d["employees"]["reviewer"]
    assert emp["display"] == "评审专家"
    assert emp["kind"] == "callee"
    # callee 用 dispatch_table 取代 node_table（互斥）
    assert emp["dispatch_table"] == "orchestration/reviewer.dispatch-table.yml"
    assert "node_table" not in emp, "callee 不应有 node_table（用 dispatch_table）"
    assert emp["flow_skill"] is None, "callee 无方法论 flow-skill"
    assert emp["standards_dir"] == "standards/reviewer/"
    assert len(emp["agents"]) == 7  # orchestrator + 6 cap
    for a in emp["agents"]:
        assert (AGENTS / f"{a}.md").exists(), f"花名册引用的 agent 不存在: {a}"


def test_flow_owner_keeps_node_table_callee_has_none():
    d = yaml.safe_load(STAFF.read_text(encoding="utf-8"))
    for fid in ("dev-engineer", "req-architect"):
        assert "node_table" in d["employees"][fid]
        assert "dispatch_table" not in d["employees"][fid]
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd /home/lyadmin/Projects/kdev-agents-reviewer && python3 -m pytest plugins/kdev-team/tests/test_staff.py -q`
Expected: FAIL（`KeyError: 'kind'` 或 `KeyError: 'reviewer'`）—— agent 文件还没建，`test_reviewer_callee_entry` 也会因 `.md` 不存在挂。**本 task 先让前两个 kind 断言 + 结构断言过；`reviewer-*.md` 存在断言会在 Task 4/5 补齐后才全绿**（subagent-driven 下，本 task 验证 staff.yml 结构，agent 存在性留到 Task 5 收口跑全量）。

- [ ] **Step 3: 改 staff.yml**（给三员工加 `kind`，新增 reviewer 条目）

给 `dev-engineer` 和 `req-architect` 各加一行 `kind: flow-owner`（放在 `display` 下）。在 `req-architect` 条目后追加：

```yaml
  reviewer:
    display: 评审专家
    kind: callee                              # 被 caller R3 review gate 发函调用，无自有 flow
    flow_skill: null                          # callee 无方法论 flow-skill
    dispatch_table: orchestration/reviewer.dispatch-table.yml   # 取代 node_table（互斥）
    standards_dir: standards/reviewer/
    runtime_model: opus
    agents:
      - reviewer-orchestrator
      - reviewer-sr
      - reviewer-story
      - reviewer-prototype
      - reviewer-design
      - reviewer-code
      - reviewer-security
```

- [ ] **Step 4: 跑测试**

Run: `python3 -m pytest plugins/kdev-team/tests/test_staff.py::test_kind_discriminator_on_all_employees plugins/kdev-team/tests/test_staff.py::test_flow_owner_keeps_node_table_callee_has_none -q`
Expected: PASS（这两个不依赖 agent 文件）。`test_reviewer_callee_entry` 暂红（agent 未建），Task 5 后转绿。

- [ ] **Step 5: Commit**

```bash
git add plugins/kdev-team/staff.yml plugins/kdev-team/tests/test_staff.py
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-team): staff.yml 加 reviewer callee 条目 + kind 判别（schema delta）"
```

---

## Task 2: reviewer.dispatch-table.yml — 评审路由清单

**Files:**
- Create: `plugins/kdev-team/orchestration/reviewer.dispatch-table.yml`
- Test: `plugins/kdev-team/tests/test_reviewer_dispatch.py`

- [ ] **Step 1: 写失败测试**（新建 test_reviewer_dispatch.py）

```python
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]
DT = ROOT / "orchestration/reviewer.dispatch-table.yml"
AGENTS = ROOT / "agents"
DEV_NT = ROOT / "orchestration/dev-engineer.node-table.yml"
REQ_NT = ROOT / "orchestration/req-architect.node-table.yml"

EXPECTED_CAPS = {"sr", "story", "prototype", "design", "code", "security"}


def _dt():
    return yaml.safe_load(DT.read_text(encoding="utf-8"))


def test_dispatch_table_has_6_caps_with_schema():
    caps = _dt()["capabilities"]
    assert {c["cap"] for c in caps} == EXPECTED_CAPS
    for c in caps:
        for key in ("cap", "agent", "standards", "threshold", "target", "caller_gate"):
            assert key in c, f"{c.get('cap')} 缺字段 {key}"
        assert isinstance(c["threshold"], int) and 0 < c["threshold"] <= 100
        assert isinstance(c["caller_gate"], list) and c["caller_gate"]


def test_each_cap_agent_file_exists():
    for c in _dt()["capabilities"]:
        assert (AGENTS / f"{c['agent']}.md").exists(), f"agent 不存在: {c['agent']}"


def test_each_cap_standards_file_exists():
    for c in _dt()["capabilities"]:
        assert (ROOT / c["standards"]).exists(), f"standards 不存在: {c['standards']}"


def test_caller_gate_refs_real_gates():
    """dispatch-table 声明的 caller_gate 必须是真实存在的 gate（dev/req node-table 的 gate_specs）。"""
    dev = yaml.safe_load(DEV_NT.read_text(encoding="utf-8"))["gate_specs"]
    req = yaml.safe_load(REQ_NT.read_text(encoding="utf-8"))["gate_specs"]
    known = {f"dev-engineer:{g}" for g in dev} | {f"req-architect:{g}" for g in req}
    for c in _dt()["capabilities"]:
        for cg in c["caller_gate"]:
            assert cg in known, f"{c['cap']} 引用了不存在的 caller_gate: {cg}"


def test_review_gates_covered_by_some_cap():
    """dev/req 的每个 review-kind gate 都至少被一个 cap 认领（无悬空 reviewer-expert gate）。"""
    dev = yaml.safe_load(DEV_NT.read_text(encoding="utf-8"))["gate_specs"]
    req = yaml.safe_load(REQ_NT.read_text(encoding="utf-8"))["gate_specs"]
    review_gates = {f"dev-engineer:{g}" for g, s in dev.items() if s["kind"] == "review"}
    review_gates |= {f"req-architect:{g}" for g, s in req.items() if s["kind"] == "review"}
    claimed = set()
    for c in _dt()["capabilities"]:
        claimed |= set(c["caller_gate"])
    missing = review_gates - claimed
    assert not missing, f"这些 review gate 没有 cap 认领: {missing}"
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python3 -m pytest plugins/kdev-team/tests/test_reviewer_dispatch.py -q`
Expected: FAIL（`FileNotFoundError: reviewer.dispatch-table.yml`）

- [ ] **Step 3: 写 dispatch-table**（内容照 spec §3.2，逐字落地）

```yaml
# 评审专家 dispatch 路由（callee；被 caller R3 review gate 发函调用，不跑自有 flow）
# 见 spec §3.2。cap→agent→standards→默认阈值→评对象→caller_gate（员工:gate 形）。
capabilities:
  - {cap: sr,        agent: reviewer-sr,        standards: standards/reviewer/SR需求评审.md,   threshold: 80, target: sr.md,             caller_gate: [req-architect:g-sr-review]}
  - {cap: story,     agent: reviewer-story,     standards: standards/reviewer/用户故事评审.md, threshold: 80, target: 用户故事列表,         caller_gate: [req-architect:g-ar-proto-review]}
  - {cap: prototype, agent: reviewer-prototype, standards: standards/reviewer/原型评审.md,     threshold: 75, target: prototype/,          caller_gate: [req-architect:g-ar-proto-review]}
  - {cap: design,    agent: reviewer-design,    standards: standards/reviewer/方案架构评审.md, threshold: 85, target: [design.md, plan.md], caller_gate: [req-architect:g-design-review, dev-engineer:g-plan-review]}
  - {cap: code,      agent: reviewer-code,      standards: standards/reviewer/代码质量评审.md, threshold: 85, target: [src/, tests/, diff], caller_gate: [dev-engineer:g-code-review]}
  - {cap: security,  agent: reviewer-security,  standards: standards/reviewer/安全评审.md,     threshold: 85, target: [security.md, diff], caller_gate: [dev-engineer:g-sec-review]}
# deferred（随 caller 员工建成补，本期不建 agent）:
#   need-direction / iteration-split  ← req 须先加 R1.5/R2.5 gate
#   test-design / test-coverage       ← 测试工程师建成后
# 扩展 6（默认关，留接口）: deploy / perf / docs / compliance / observability / a11y
```

- [ ] **Step 4: 跑测试**

Run: `python3 -m pytest plugins/kdev-team/tests/test_reviewer_dispatch.py::test_dispatch_table_has_6_caps_with_schema plugins/kdev-team/tests/test_reviewer_dispatch.py::test_caller_gate_refs_real_gates -q`
Expected: PASS（schema + caller_gate 引用真实）。`test_each_cap_agent_file_exists` / `test_each_cap_standards_file_exists` 暂红（Task 3/5 补）。`test_review_gates_covered_by_some_cap` 依赖 req gate 仍是 review-kind（它们本来就是），应 PASS。

- [ ] **Step 5: Commit**

```bash
git add plugins/kdev-team/orchestration/reviewer.dispatch-table.yml plugins/kdev-team/tests/test_reviewer_dispatch.py
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-team): reviewer dispatch-table（6 能力路由 + caller_gate 一致性测试）"
```

---

## Task 3: standards/reviewer/ — 通用评分模板 + 6 cap standards

**Files:**
- Create: `plugins/kdev-team/standards/reviewer/通用评分模板.md` + 6 个 cap standards（见 File Structure 文件名表）
- Test: `plugins/kdev-team/tests/test_reviewer_dispatch.py`（追加）

- [ ] **Step 1: 写失败测试**（追加到 test_reviewer_dispatch.py）

```python
STD = ROOT / "standards/reviewer"
COMMON = STD / "通用评分模板.md"
CAP_STANDARDS = ["SR需求评审", "用户故事评审", "原型评审", "方案架构评审", "代码质量评审", "安全评审"]


def test_common_scoring_template_has_required_sections():
    text = COMMON.read_text(encoding="utf-8")
    for need in ["双重通过条件", "总分", "🔴", "🟡", "⚪", "评分表"]:
        assert need in text, f"通用评分模板缺: {need}"
    # 双重通过条件必须明确「总分≥阈值 AND 🔴阻断=0」语义
    assert "阈值" in text and "阻断" in text


def test_each_cap_standards_has_dimensions_and_threshold():
    for name in CAP_STANDARDS:
        f = STD / f"{name}.md"
        assert f.exists(), f"缺 standards: {name}"
        text = f.read_text(encoding="utf-8")
        for need in ["评审对象", "评分维度", "阈值", "问题分级", "评分表"]:
            assert need in text, f"{name} 缺 standards 段: {need}"
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python3 -m pytest plugins/kdev-team/tests/test_reviewer_dispatch.py::test_common_scoring_template_has_required_sections -q`
Expected: FAIL（`FileNotFoundError: 通用评分模板.md`）

- [ ] **Step 3: 写 7 份 standards markdown**

`通用评分模板.md` 必含（spec §3.4 + §4.2 + 概念合稿 §12.4/§12.6）：
- **100 分制 schema**：3-5 维度（每维 20-25 分）合计 100。
- **双重通过条件**：`通过 = 总分 ≥ 阈值（默认见各 cap）AND 🔴阻断 = 0`。
- **问题分级标准**：🔴阻断（必须处置/escalate）/ 🟡重要（建议修，可 tech-debt）/ ⚪轻微。
- **评分表输出 schema**（照 spec §4.2 的 `cap/target/total/dimensions/issues/verdict` YAML 块）。
- **评审循环规则**：FAIL → caller 编排自主判断修哪些 → 增量评；3 次不过 → escalate CEO → 用户拍板。

6 份 cap standards 各含 5 段（`评审对象` / `评分维度`(3-5 项+每项 checklist) / `阈值`(覆盖默认) / `问题分级` / `评分表`），维度照 spec §4.1「备注」列：
- `SR需求评审.md`（阈值 80）：完整性/清晰性/可验收性/方向对齐。
- `用户故事评审.md`（80）：故事粒度/可独立验收/回溯 SR/无遗漏无重复。
- `原型评审.md`（75）：可用性/一致性/UED 合规/交互流畅。
- `方案架构评审.md`（85，多触点）：事前——技术可行/扩展性/复杂度/选型/风险；事后/plan——与 design 一致/Gate-A·B 合理/模块边界/依赖方向。
- `代码质量评审.md`（85）：spec 一致/正确性/边界/TDD 真过 + 风格/抽象/命名/复杂度/重复 + 架构一致性（事后）。
- `安全评审.md`（85）：OWASP/认证授权/数据安全/输入校验。

> 每份 standards 顶部硬规一行：评审能力 agent 启动须 `recall(scope=/staff/reviewer, subject:review:<cap>)` 召回历史校准（记忆底座 §5.2）。

- [ ] **Step 4: 跑测试**

Run: `python3 -m pytest plugins/kdev-team/tests/test_reviewer_dispatch.py -k "standards or scoring" -q`
Expected: PASS（含 Task 2 的 `test_each_cap_standards_file_exists` 转绿）

- [ ] **Step 5: Commit**

```bash
git add plugins/kdev-team/standards/reviewer/ plugins/kdev-team/tests/test_reviewer_dispatch.py
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-team): reviewer standards（通用评分模板 + 6 cap 评分维度）"
```

---

## Task 4: reviewer-orchestrator.md — 被调编排入口

**Files:**
- Create: `plugins/kdev-team/agents/reviewer-orchestrator.md`
- Test: `plugins/kdev-team/tests/test_agents.py`（追加）

- [ ] **Step 1: 写失败测试**（追加到 test_agents.py）

```python
REVIEWER_AGENTS = [
    "reviewer-orchestrator", "reviewer-sr", "reviewer-story",
    "reviewer-prototype", "reviewer-design", "reviewer-code", "reviewer-security",
]


def test_all_7_reviewer_agents_exist():
    names = {p.stem for p in AGENTS.glob("reviewer-*.md")}
    for a in REVIEWER_AGENTS:
        assert a in names, f"缺 agent: {a}"


def test_each_reviewer_agent_has_frontmatter_and_sections():
    for a in REVIEWER_AGENTS:
        text = (AGENTS / f"{a}.md").read_text(encoding="utf-8")
        fm = _frontmatter(text)
        assert fm, f"{a} 缺 YAML frontmatter"
        assert f"name: {a}" in fm, f"{a} frontmatter name 不匹配文件名"
        assert "description:" in fm and "model:" in fm, f"{a} frontmatter 缺 description/model"
        for sec in SECTIONS:
            assert sec in text, f"{a} 缺段落 {sec}"


def test_reviewer_orchestrator_callee_shape():
    text = (AGENTS / "reviewer-orchestrator.md").read_text(encoding="utf-8")
    # callee：读 dispatch-table、fan-out、仲裁、双重通过条件、record-gate --by reviewer-expert
    assert "dispatch-table" in text or "dispatch_table" in text
    assert "fan-out" in text or "fanout" in text or "并行" in text
    assert "仲裁" in text
    assert "双重" in text and "reviewer-expert" in text
    # callee 明确不复用 kdev-flow-driver（无自有 flow）
    assert "callee" in text


def test_cap_reviewers_are_read_only():
    for a in ["reviewer-sr", "reviewer-story", "reviewer-prototype",
              "reviewer-design", "reviewer-code", "reviewer-security"]:
        text = (AGENTS / f"{a}.md").read_text(encoding="utf-8")
        assert "只读" in text or "不改产物" in text or "不修改产物" in text, \
            f"{a} 须声明只读（守生产者隔离）"
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python3 -m pytest plugins/kdev-team/tests/test_agents.py::test_reviewer_orchestrator_callee_shape -q`
Expected: FAIL（`FileNotFoundError: reviewer-orchestrator.md`）

- [ ] **Step 3: 写 reviewer-orchestrator.md**（照 spec §3.3 + §5 发函 6 步；frontmatter 仿 `req-architect-orchestrator.md`）

frontmatter：`name: reviewer-orchestrator` / `description: 评审专家·编排能力 — callee，被 caller R3 review gate 发函调用…Use when caller 编排到 review gate 且 reviewer=reviewer-expert。` / `model: opus`。
4 段必须覆盖：
- **Identity**：评审专家的编排能力（callee）；被 caller 的 review gate 发函调用，读 `orchestration/reviewer.dispatch-table.yml` fan-out 评审能力。**不复用 kdev-flow-driver、无自有 flow-state**——寄生 caller flow 贡献 verdict。
- **Principles**：守硬规 4/5（只回函请评审的员工编排、不直接命令 caller）；建议为主、拦截经 gate（🔴 经双重通过条件强制 FAIL）；仲裁 inline（不设审查组长）。
- **Critical Actions**：发函 6 步（读 request → 并行 fan-out `kdev-team:reviewer-<cap>` → 收评分表 → inline 仲裁冲突 → 双重通过条件聚合 gate verdict → 写 `handoffs/reviewer/<gate>.handoff.json{verdict,scores,counts,revisions,仲裁,by:reviewer-expert}`）；内置终审聚合（汇总各节点已出分，不重评）。
- **Capabilities**：表列 6 cap→agent；仲裁 3 步（events 留痕→读两评分表找冲突点→偏向一方+重验 / 编排犹豫→升 CEO+标 CQO）。

- [ ] **Step 4: 跑测试**

Run: `python3 -m pytest plugins/kdev-team/tests/test_agents.py::test_reviewer_orchestrator_callee_shape -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add plugins/kdev-team/agents/reviewer-orchestrator.md plugins/kdev-team/tests/test_agents.py
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-team): reviewer-orchestrator（callee 编排：fan-out+仲裁+双重条件聚合）"
```

---

## Task 5: 6 个 reviewer-<cap>.md 评审能力 agent

**Files:**
- Create: `plugins/kdev-team/agents/reviewer-{sr,story,prototype,design,code,security}.md`
- Test: `plugins/kdev-team/tests/test_agents.py`（Task 4 已写断言）+ Task 1/2 的存在性断言此处转绿

- [ ] **Step 1: 测试已在 Task 4 写好**（`test_all_7_reviewer_agents_exist` / `test_each_reviewer_agent_has_frontmatter_and_sections` / `test_cap_reviewers_are_read_only`）。本 task 直接进实现。

- [ ] **Step 2: 跑测试确认失败**

Run: `python3 -m pytest plugins/kdev-team/tests/test_agents.py -k reviewer -q`
Expected: FAIL（6 cap agent 缺文件）

- [ ] **Step 3: 写 6 份 cap agent**（每份 frontmatter `name/description/model: opus` + 4 段；维度照 spec §4.1）

每份模板（以 `reviewer-code` 为例，其余照各 cap 维度替换）：
- **Identity**：评审专家的「代码+质量评审」能力（对应 caller `dev-engineer:g-code-review`）。只读评 src+tests+diff。
- **Principles**：**只读、不改产物**（修复是被评审员工的事，守生产者隔离）；按 standards 维度打百分制；🔴/🟡/⚪ 分级、建议须引证据（行号/transcript 段）。
- **Critical Actions**：① Read 产物 + `standards/reviewer/代码质量评审.md` + `recall(scope=/staff/reviewer, subject:review:code)` ② 按维度打分 ③ 出评分表（spec §4.2 schema）写 `handoffs/reviewer/<gate>.code.score.md` ④ 不改产物、回编排。
- **Capabilities**：列 standards 引用 + 评对象 + 阈值（85）。

其余 5 个对应：sr（→`req:g-sr-review`，阈值 80）/ story（→`req:g-ar-proto-review` AR 部分，80）/ prototype（→`req:g-ar-proto-review` 原型部分，75）/ design（→`req:g-design-review`+`dev:g-plan-review`，多触点，85）/ security（→`dev:g-sec-review`，85）。

- [ ] **Step 4: 跑测试**（全量 kdev-team，Task 1 的 `test_reviewer_callee_entry` + Task 2 的 agent 存在断言此刻应全绿）

Run: `python3 -m pytest plugins/kdev-team/tests/ -q`
Expected: PASS（全部，含先前暂红的 agent 存在性断言）

- [ ] **Step 5: Commit**

```bash
git add plugins/kdev-team/agents/reviewer-sr.md plugins/kdev-team/agents/reviewer-story.md plugins/kdev-team/agents/reviewer-prototype.md plugins/kdev-team/agents/reviewer-design.md plugins/kdev-team/agents/reviewer-code.md plugins/kdev-team/agents/reviewer-security.md
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-team): 6 个 reviewer-<cap> 评审能力 agent（只读，百分制评分表）"
```

---

## Task 6: req-architect.node-table — 3 gate reviewer self→reviewer-expert

**Files:**
- Modify: `plugins/kdev-team/orchestration/req-architect.node-table.yml`
- Test: `plugins/kdev-team/tests/test_req_architect_orchestration.py`（追加）

- [ ] **Step 1: 写失败测试**（追加到 test_req_architect_orchestration.py）

```python
def test_req_review_gates_bound_to_reviewer_expert():
    import yaml
    from pathlib import Path
    nt = Path(__file__).resolve().parents[1] / "orchestration/req-architect.node-table.yml"
    specs = yaml.safe_load(nt.read_text(encoding="utf-8"))["gate_specs"]
    for g in ("g-sr-review", "g-ar-proto-review", "g-design-review"):
        assert specs[g]["reviewer"] == "reviewer-expert", f"{g} 应翻 reviewer-expert（兑现评审专家）"
```

（若文件已有等价断言，改其期望值为 `reviewer-expert`。先确认现有断言里有没有锁 `reviewer: self`——有则一并改，避免双源冲突。）

- [ ] **Step 2: 跑测试确认失败**

Run: `python3 -m pytest plugins/kdev-team/tests/test_req_architect_orchestration.py::test_req_review_gates_bound_to_reviewer_expert -q`
Expected: FAIL（现值 `self`）

- [ ] **Step 3: 改 req-architect.node-table.yml**

`gate_specs` 三处 `reviewer: self` → `reviewer: reviewer-expert`。同步改文件顶部注释（现写「阶段1 无第三方评审专家，故 3 闸全 self…待评审专家建成由 L1 config 翻」）→ 改为「评审专家已建（spec 2026-06-12 v0.2 / Q-016）：3 闸 reviewer-expert，编排到 gate 发函 `kdev-team:reviewer-orchestrator`；L1 flow-config 可回退 self（per-gate reviewer 旋钮的 engine 级 merge 待后续 plan，本期 L0 字段生效）」。

- [ ] **Step 4: 跑测试**

Run: `python3 -m pytest plugins/kdev-team/tests/test_req_architect_orchestration.py plugins/kdev-team/tests/test_orchestration_config.py -q`
Expected: PASS（reviewer 值合法仍 ∈ {self, reviewer-expert}）

- [ ] **Step 5: Commit**

```bash
git add plugins/kdev-team/orchestration/req-architect.node-table.yml plugins/kdev-team/tests/test_req_architect_orchestration.py
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-team): req-architect 3 评审 gate self→reviewer-expert（兑现评审专家）"
```

---

## Task 7: 编排 prose — gate-decision-logic + node-agent-routing（dev 去 deferred + reviewer 发函）

**Files:**
- Modify: `plugins/kdev-team/skills/kdev-flow-driver/references/gate-decision-logic.md`
- Modify: `plugins/kdev-team/skills/kdev-flow-driver/references/node-agent-routing.md`
- Test: `plugins/kdev-team/tests/test_skill_slimmed.py`（追加结构断言）

- [ ] **Step 1: 写失败测试**（追加到 test_skill_slimmed.py；若该文件不便扩展，新建 `test_reviewer_wiring.py`）

```python
from pathlib import Path

REF = Path(__file__).resolve().parents[1] / "skills/kdev-flow-driver/references"
GDL = REF / "gate-decision-logic.md"
NAR = REF / "node-agent-routing.md"


def test_gate_logic_dev_gates_no_longer_deferred():
    text = GDL.read_text(encoding="utf-8")
    # dev3 不再「全 deferred」；出现真发函语义
    assert "reviewer-orchestrator" in text
    assert "发函" in text or "dispatch" in text
    # 不再把 g-code-review 当 deferred PASS
    assert "deferred:阶段3-评审专家" not in text or "已兑现" in text


def test_node_routing_has_reviewer_dispatch_section():
    text = NAR.read_text(encoding="utf-8")
    assert "reviewer" in text.lower()
    assert "kdev-team:reviewer-orchestrator" in text
    assert "handoffs/reviewer/" in text
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python3 -m pytest plugins/kdev-team/tests/ -k "reviewer_wiring or skill_slimmed" -q`
Expected: FAIL

- [ ] **Step 3: 改两份 prose**

`gate-decision-logic.md`「Reviewer-Expert Gate（阶段1 全 deferred）」节 → 重写为「Reviewer-Expert Gate（已兑现，发函评审专家）」：dev 3 gate（g-plan/code/sec-review）+ req 3 gate 统一走 spec §5 的发函 6 步：写 `handoffs/reviewer/<gate>.request.json` → dispatch `kdev-team:reviewer-orchestrator`（run_in_background）→ handoff-read verdict → `record-gate --kind review --verdict <V> --by reviewer-expert`。保留一句「L1 flow-config `reviewer: self` 时回退自评（per-gate engine 级 merge 待后续）」。

`node-agent-routing.md` 追加「reviewer 发函 dispatch」段：caller→reviewer 上下文构造（request schema：target_paths/caps/standards_refs/thresholds/request_id/caller/diff_range；产物落 `handoffs/reviewer/`；派单全名 `kdev-team:reviewer-orchestrator`）。

- [ ] **Step 4: 跑测试**

Run: `python3 -m pytest plugins/kdev-team/tests/ -k "reviewer_wiring or skill_slimmed" -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add plugins/kdev-team/skills/kdev-flow-driver/references/gate-decision-logic.md plugins/kdev-team/skills/kdev-flow-driver/references/node-agent-routing.md plugins/kdev-team/tests/
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-team): 编排 prose 兑现 reviewer-expert 发函（去 deferred + reviewer dispatch 段）"
```

---

## Task 8: plugin bump v0.6.0 + CHANGELOG + marketplace + 全量绿

**Files:**
- Modify: `plugins/kdev-team/.claude-plugin/plugin.json`（version → 0.6.0）
- Modify: `plugins/kdev-team/CHANGELOG.md`
- Modify: 仓根 `.claude-plugin/marketplace.json`（若 kdev-team 版本写死在此）
- Test: 全量

- [ ] **Step 1: 写/改测试**（plugin manifest 版本断言，若 test_plugin_manifest.py 锁版本则更新）

Run 先看现状: `python3 -m pytest plugins/kdev-team/tests/test_plugin_manifest.py -q`
若有 `assert version == "0.5.0"` → 改为 `"0.6.0"`。

- [ ] **Step 2: bump version**

`plugin.json` `"version": "0.5.0"` → `"0.6.0"`。`CHANGELOG.md` 顶部加 `## 0.6.0` 条：评审专家(reviewer) callee 员工——dispatch-table + 7 agent + 6+1 standards + dev3/req3 评审 gate 兑现 reviewer-expert。marketplace.json 若有 kdev-team version 字段同步。

- [ ] **Step 3: 跑全量测试**

Run: `python3 -m pytest plugins/kdev-team/tests/ plugins/kdev-core/tests/ -q`
Expected: PASS（kdev-team 全绿含新增 reviewer 测试 + kdev-core 135 不破）

- [ ] **Step 4: 验证基线对比**

Run: `python3 -m pytest plugins/kdev-team/tests/ -q` 应显著多于基线 35（新增 reviewer 测试）。kdev-core 仍 135。

- [ ] **Step 5: Commit**

```bash
git add plugins/kdev-team/.claude-plugin/plugin.json plugins/kdev-team/CHANGELOG.md .claude-plugin/marketplace.json plugins/kdev-team/tests/test_plugin_manifest.py
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "chore(kdev-team): bump v0.6.0 + CHANGELOG（评审专家 reviewer 员工上线）"
```

---

## 完成判据（Definition of Done）

- [ ] `python3 -m pytest plugins/kdev-team/tests/ plugins/kdev-core/tests/ -q` 全绿。
- [ ] staff.yml 有 reviewer callee 条目（kind/dispatch_table/standards_dir/7 agents）+ 两 flow-owner 标 kind。
- [ ] 7 个 reviewer agent + 7 份 standards + dispatch-table 齐全且交叉一致（dispatch-table 引用的 agent/standards/caller_gate 都真实存在）。
- [ ] req 3 gate reviewer == reviewer-expert；gate-decision-logic 去 deferred、有 reviewer 发函 6 步；node-agent-routing 有 reviewer dispatch 段。
- [ ] plugin v0.6.0 + CHANGELOG。
- [ ] kdev-core **零改动**（git diff 不含 plugins/kdev-core）。
- [ ] **未实现声明在案**：L1 per-gate reviewer 旋钮（engine merge）/ 核心 10 余 4 / 扩展 6 / mode-2（已归蒸馏）—— 不在本 plan，spec §9 + 本 plan scope 边界已记。

## 风险 / 注意

- **G-004**：plugin 改 agent 须 bump version + 用户刷 marketplace 重启 session 才激活 `kdev-team:reviewer-*` 直派——本 plan 只到 bump，激活靠用户操作。
- **G-009**：所有派单示例写全名 `kdev-team:reviewer-orchestrator`，裸 id not-found。
- **双源冲突**：Task 6 改 req node-table reviewer 前先 grep 既有测试有没有锁 `reviewer: self`，一并改期望值，避免红。
- **标准内容是 prose**：standards/agent 的「内容质量」结构测试管不到（只锁段落骨架）；内容忠实度靠实施者照 spec §3.3/§4.1 写 + 终审 review 人核。
