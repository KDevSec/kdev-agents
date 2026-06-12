# P-B 跨员工 handoff Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 打通需求架构师(req-architect) design-flow 产物（SR/AR/原型/方案）→ 开发工程师(dev-engineer) coding-flow 节点0/节点3 的 spec/plan 输入，复用 B 轨 handoff 原语零重造，朝 M2 收口。

**Architecture:** **纯复用** B 轨 kdev-core `handoff-write`/`handoff-read` CLI（v0.3.0），不改 kdev-core 一行代码。跨员工交接 = 在「同一 feature slug」上做 join：req-architect 在其聚合节点 `n8-merge` 用 `handoff-write` 落一份**交付 manifest**（`artifacts` 指向 sr/ar/prototype/design 路径 + `gate_input` 带 role→path 结构化指针），dev-engineer 在 `n0-env`/`n3-plan` 用 `handoff-read --employee req-architect --node n8-merge` 读同 slug 的上游交付当 spec/plan 输入；上游不存在则回退现有「裸任务」行为（不报错）。所有接线落在通用 `kdev-flow-driver` skill 的契约文档 + 业务 agent persona，**不下放编排逻辑到 orchestrator agent**（守 G-008）。

**Tech Stack:** Python 3.12 / pytest（kdev-core + kdev-team）；Markdown 契约文档（kdev-flow-driver SKILL + node-agent-routing + agent persona）；kdev-core feature-first `.kdev/features/<slug>/handoffs/<员工>/`。

---

## 背景：已核实的复用面（R-009 教训：核实际实现，非只看 spec）

| 事实 | 出处（已核） |
|---|---|
| handoff 存储路径 = `.kdev/features/<slug>/handoffs/<员工>/`（**用户已确认**，非设计文档 §6 的 `.kdev/handoffs/<id>/` 旧稿） | `flow_state.handoff_dir` + `_feature_dir`（`plugins/kdev-core/kdev_core/flow_state.py:29,390`）；req-architect agents 已落此（`req-architect-spec.md:20` / `req-architect-decompose.md:18`） |
| `write_handoff_status(ws, slug, employee, node_id, status, summary, artifacts, gate_input, reason)` 已是「结构化产物指针」：谁(employee)+啥/路径(artifacts)+状态(status)+summary+gate_input | `plugins/kdev-core/kdev_core/flow_state.py:407-460` |
| CLI：`handoff-write --employee --node --status{done\|blocked\|needs_context} --summary [--artifact ...] [--gate-input <json>] [--reason]` / `handoff-read --employee --node` | `plugins/kdev-core/kdev_core/cli.py:329-347` |
| `handoff-read` **要 `--node`** → 消费方须知生产方交付节点 id（本计划用文档常量 `req-architect → n8-merge`，零新代码） | 同上 cli.py:344-347 |
| req-architect `n8-merge` = 「产物聚合+合并交付」节点，编排自做（不派 agent） | `req-architect.node-table.yml:28`；`node-agent-routing.md:110`；`req-architect-orchestrator.md` n8-merge 行 |
| dev-engineer `n0-env`/`n3-plan` = 消费上游 SR/AR 的接入点，当前无上游读取逻辑 | `dev-engineer.node-table.yml:14,17`；`dev-engineer-env.md` / `dev-engineer-plan.md` |
| 基线测试：kdev-core 133 passed / kdev-team 26 passed | `python3 -m pytest -q`（feat/p-b-handoff worktree，2026-06-12） |

**跨员工交付 manifest 约定（本计划锁定，写进 SKILL §2.4ter）：**
- 生产方在其**聚合/交付节点**落一份 `done` 交接：`--employee req-architect --node n8-merge --status done --summary <一句话> --artifact <sr 路径> --artifact <ar 路径> --artifact <prototype 路径> --artifact <design 路径> --gate-input '{"sr":"<路径>","ar":"<路径>","prototype":"<路径>","design":"<路径>"}'`。
- 消费方按 `--employee <生产方> --node <生产方交付节点>` 读，**同 slug** join。生产方→交付节点映射：`req-architect → n8-merge`。
- 上游缺失（`handoff-read` 报 `handoff status not found` = FlowStateError）→ **裸任务回退**，不阻断、不报错。

---

## File Structure

**改动（kdev-team — 接线主体，纯文档/persona/测试）：**
- Modify `plugins/kdev-team/skills/kdev-flow-driver/SKILL.md` — 新增 §2.4ter「跨员工 handoff（上游交付 → 下游 spec 输入）」+ 生产方→交付节点映射表。
- Modify `plugins/kdev-team/skills/kdev-flow-driver/references/node-agent-routing.md` — req-architect `n8-merge` 行加 `handoff-write` 交付指令；dev-engineer `n0-env`/`n3-plan` 行的「需传上下文」列加「先读上游 req-architect 交付」。
- Modify `plugins/kdev-team/agents/dev-engineer-env.md` — Critical Actions 加「读上游 req-architect 交付（SR+背景），缺失则裸任务」。
- Modify `plugins/kdev-team/agents/dev-engineer-plan.md` — Critical Actions 加「以上游 AR/方案的用户故事/迭代切分作增量清单与 PLAN 起点」。
- Modify `plugins/kdev-team/agents/req-architect-orchestrator.md` — n8-merge 行加「写跨员工交付 handoff（handoff-write）」。
- Modify `plugins/kdev-team/orchestration/req-architect.node-table.yml` — 注释补 n8-merge 落跨员工交付 handoff。
- Create `plugins/kdev-team/tests/test_cross_employee_handoff.py` — 接线契约不变量测试（散文/结构断言，红绿）。
- Modify `plugins/kdev-team/.claude-plugin/plugin.json` — version `0.4.0` → `0.5.0`。
- Modify `plugins/kdev-team/CHANGELOG.md` — 0.5.0 条目。

**改动（kdev-core — 仅加机制锁测试，零生产代码）：**
- Modify `plugins/kdev-core/tests/test_handoffs.py` — 加跨员工 CLI 往返契约测试（生产 req-architect 交付 → 消费 dev-engineer 读，同 slug）。

**不改（守约束）：**
- kdev-core 生产代码（纯复用，不 bump，不动 `flow_state.py`/`cli.py`）。
- orchestrator agent 的编排逻辑（G-008：运行时编排由通用 kdev-flow-driver 承载；orchestrator 文档仅补「写交付 handoff」契约，非自跑逻辑）。
- 旧 `.kdev/flows/`（接 feature-first）。

**计划外（执行后主会话做）：**
- roadmap §1.5.2 + §1.5.8 回写 P-B done。
- G-004：bump 后提示用户刷 marketplace。

---

## Task 1: kdev-team 接线契约测试骨架 + SKILL §2.4ter 跨员工 handoff 段

**Files:**
- Create: `plugins/kdev-team/tests/test_cross_employee_handoff.py`
- Modify: `plugins/kdev-team/skills/kdev-flow-driver/SKILL.md`（在 §2.4bis 后、§2.5 前插入 §2.4ter）

- [ ] **Step 1: Write the failing test**

写 `plugins/kdev-team/tests/test_cross_employee_handoff.py`：

```python
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills/kdev-flow-driver/SKILL.md"
ROUTING = ROOT / "skills/kdev-flow-driver/references/node-agent-routing.md"
DEV_ENV = ROOT / "agents/dev-engineer-env.md"
DEV_PLAN = ROOT / "agents/dev-engineer-plan.md"
REQ_ORCH = ROOT / "agents/req-architect-orchestrator.md"

# 跨员工交付契约常量：生产方 req-architect 在 n8-merge 落交付 handoff，
# 消费方 dev-engineer 同 slug 读。consumer/producer 两侧必须引用同一节点 id。
DELIVERY_NODE = "n8-merge"
PRODUCER = "req-architect"


def _t(p):
    return p.read_text(encoding="utf-8")


def test_skill_has_cross_employee_handoff_section():
    """SKILL 新增 §2.4ter 跨员工 handoff 段（区别于 §2.4bis 同流交接）。"""
    t = _t(SKILL)
    assert "2.4ter" in t
    assert "跨员工" in t


def test_skill_cross_section_documents_producer_consumer_contract():
    """§2.4ter 必含：生产方写交付 + 消费方读 + 同 slug join + 裸任务回退。"""
    t = _t(SKILL)
    start = t.index("2.4ter")
    end = t.index("### 2.5")
    sec = t[start:end]
    assert "handoff-write" in sec      # 生产方落交付
    assert "handoff-read" in sec       # 消费方读
    assert PRODUCER in sec             # req-architect
    assert DELIVERY_NODE in sec        # n8-merge 交付节点
    assert "slug" in sec               # 同 slug join
    assert ("裸任务" in sec) or ("回退" in sec)  # 上游缺失回退


def test_skill_maps_producer_to_delivery_node():
    """SKILL 明确生产方→交付节点映射（req-architect → n8-merge），消费方据此读。"""
    t = _t(SKILL)
    start = t.index("2.4ter")
    end = t.index("### 2.5")
    sec = t[start:end]
    # 映射行同时出现生产方与其交付节点
    assert PRODUCER in sec and DELIVERY_NODE in sec
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd plugins/kdev-team && python3 -m pytest tests/test_cross_employee_handoff.py -v`
Expected: FAIL（`SKILL.md` 尚无 `2.4ter` → `t.index("2.4ter")` 抛 `ValueError: substring not found`）

- [ ] **Step 3: 在 SKILL.md §2.4bis 之后、§2.5 之前插入 §2.4ter**

定位 `plugins/kdev-team/skills/kdev-flow-driver/SKILL.md` 中 `### 2.5 gate 节点 → 判断` 这一行，在它之前插入以下整段：

```markdown
### 2.4ter 跨员工 handoff（上游交付 → 下游 spec 输入）

§2.4bis 是**同一 flow 内**主循环↔业务 agent 的交接（按 `current_node` 读）。本段是**跨员工跨 flow**的交接：上游员工（如需求架构师 req-architect）design-flow 的交付，喂给下游员工（开发工程师 dev-engineer）coding-flow 的 spec/plan 输入。**机制纯复用 B 轨 `handoff-write`/`handoff-read`，不新增原语。**

**join 键 = 同一 feature slug。** 一个 feature 一个 slug：req-architect 在 slug X 上跑 design-flow、落产物到 `.kdev/features/X/handoffs/req-architect/`；dev-engineer 在**同一 slug X** 上跑 coding-flow，读这里当输入。

**生产方（上游）落交付 manifest**：在其**聚合/交付节点**收尾时调一次：

```bash
python3 -m kdev_core handoff-write design-flow <slug> --workspace <ws> \
  --employee req-architect --node n8-merge --status done \
  --summary "<一句话：交付了什么>" \
  --artifact .kdev/features/<slug>/handoffs/req-architect/sr.md \
  --artifact .kdev/features/<slug>/handoffs/req-architect/ar.md \
  --artifact .kdev/features/<slug>/handoffs/req-architect/prototype/ \
  --artifact .kdev/features/<slug>/handoffs/req-architect/design.md \
  --gate-input '{"sr":"<sr 路径>","ar":"<ar 路径>","prototype":"<prototype 路径>","design":"<design 路径>"}'
```
- `artifacts` = 产物路径列表（人/机都能顺着取）；`gate_input` = role→path 结构化指针（消费方按角色精确取 sr/ar/prototype/design）。

**生产方 → 交付节点映射**（消费方据此知道读哪个 `--node`）：

| 生产方（员工）| 交付节点 `--node` | 交付内容 |
|---|---|---|
| `req-architect` | `n8-merge` | SR / AR(迭代+用户故事) / 原型 / 方案 |

**消费方（下游）读上游交付**：下游员工在其入口节点按上表读**同 slug** 的上游交付：

```bash
python3 -m kdev_core handoff-read coding-flow <slug> --workspace <ws> \
  --employee req-architect --node n8-merge
# → {node_id, employee, status, summary, artifacts, gate_input, reason}
```
- `status=done` → 取 `gate_input` 的 role→path 指针 / `artifacts` 作下游 spec/plan 输入（dev-engineer n0-env 读 SR+背景；n3-plan 读 AR+方案切增量）。
- **上游缺失**（`handoff-read` 报 `handoff status not found` = FlowStateError）→ 该 slug 没有上游交付，**回退裸任务**：dev-engineer 按现状（clone+蒸馏 / 自己定增量）走，不阻断、不报错。

**为什么不另起原语**：B 轨 `write/read_handoff_status` 已是「谁产了啥+路径+状态」结构化指针，跨员工只是换 `employee`/`slug` join 维度，零扩展即覆盖（守「复用别重造」）。**gate 判断仍在主循环**（同 §2.4bis 边界：执行甩文件、决策留主控）。
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd plugins/kdev-team && python3 -m pytest tests/test_cross_employee_handoff.py -v`
Expected: PASS（3 个 test 全绿）

- [ ] **Step 5: Commit**

```bash
git -c user.name=ly-AI -c user.email=ly1989abc@126.com add \
  plugins/kdev-team/tests/test_cross_employee_handoff.py \
  plugins/kdev-team/skills/kdev-flow-driver/SKILL.md
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-team): kdev-flow-driver §2.4ter 跨员工 handoff 契约（上游交付→下游 spec 输入）"
```

---

## Task 2: node-agent-routing 接线（写侧 n8-merge + 读侧 n0-env/n3-plan）

**Files:**
- Modify: `plugins/kdev-team/tests/test_cross_employee_handoff.py`（追加 routing 断言）
- Modify: `plugins/kdev-team/skills/kdev-flow-driver/references/node-agent-routing.md`

- [ ] **Step 1: Write the failing test**

在 `tests/test_cross_employee_handoff.py` 末尾追加：

```python
def test_routing_req_architect_n8_writes_delivery_handoff():
    """node-agent-routing req-architect n8-merge 行：编排自做 + 写交付 handoff。"""
    t = _t(ROUTING)
    # 取 req-architect 路由段（"# req-architect" 标题之后）
    start = t.index("req-architect（需求架构师）design-flow 路由")
    sec = t[start:]
    assert "n8-merge" in sec
    assert "handoff-write" in sec
    assert "--node n8-merge" in sec


def test_routing_dev_engineer_reads_upstream_at_n0_and_n3():
    """dev-engineer n0-env / n3-plan 上下文列加「读上游 req-architect 交付」。"""
    t = _t(ROUTING)
    # dev-engineer 段在 req-architect 段之前（文件上半部）
    end = t.index("req-architect（需求架构师）design-flow 路由")
    dev_sec = t[:end]
    assert "handoff-read" in dev_sec
    assert "req-architect" in dev_sec
    # 读发生在入口节点
    assert "n0-env" in dev_sec and "n3-plan" in dev_sec
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd plugins/kdev-team && python3 -m pytest tests/test_cross_employee_handoff.py -k "routing" -v`
Expected: FAIL（routing 文档暂无 `handoff-write` / `handoff-read`）

- [ ] **Step 3: 改 node-agent-routing.md（写侧 + 读侧）**

**(a) req-architect 路由段 n8-merge 行**：把这一行（约 line 110）

```markdown
| n8-merge | 产物聚合+合并交付 | **编排自做（不派）** | 需求架构师·编排 | 阶段聚合报告 + 合并交付（参 design-flow output-merge-rules.md）→ docs/design-flow/<slug>/ | 各阶段终版路径 |
```

替换为：

```markdown
| n8-merge | 产物聚合+合并交付 | **编排自做（不派）** | 需求架构师·编排 | 阶段聚合报告 + 合并交付（参 design-flow output-merge-rules.md）→ docs/design-flow/<slug>/；**收尾落跨员工交付 handoff**：`kdev_core handoff-write design-flow <slug> --employee req-architect --node n8-merge --status done --summary ... --artifact sr/ar/prototype/design --gate-input '{"sr":..,"ar":..,"prototype":..,"design":..}'`（供下游 coding-flow 同 slug 读，见 SKILL §2.4ter）| 各阶段终版路径 |
```

**(b) dev-engineer 路由段 n0-env 行**：把（约 line 31）

```markdown
| n0-env | 项目背景对齐 | `kdev-team:dev-engineer-env` | 开发工程师·环境准备 | clone 仓库、栈版本对齐、蒸馏 UED materials → rules.md | repo_url, materials_path（含 AGENTS.md / design-tokens.json / ued-v6.css）, workspace 路径 |
```

替换为：

```markdown
| n0-env | 项目背景对齐 | `kdev-team:dev-engineer-env` | 开发工程师·环境准备 | clone 仓库、栈版本对齐、蒸馏 UED materials → rules.md；**先读同 slug 上游交付**：`kdev_core handoff-read coding-flow <slug> --employee req-architect --node n8-merge`，存在则取 SR+背景作项目背景对齐输入，缺失则裸任务（SKILL §2.4ter） | repo_url, materials_path（含 AGENTS.md / design-tokens.json / ued-v6.css）, workspace 路径, **上游 req-architect 交付 handoff（若同 slug 存在）** |
```

**(c) dev-engineer 路由段 n3-plan 行**：把（约 line 33）

```markdown
| n3-plan | 写 implementation-plan | `kdev-team:dev-engineer-plan` | 开发工程师·实施计划 | 写 PLAN.md：任务拆解、TDD 序列、验收标准 | 任务描述, gate_a_verdict（high/low）, 考题或 spec 文件路径, workspace 路径 |
```

替换为：

```markdown
| n3-plan | 写 implementation-plan | `kdev-team:dev-engineer-plan` | 开发工程师·实施计划 | 写 PLAN.md：任务拆解、TDD 序列、验收标准；**上游存在时**以 `handoff-read --employee req-architect --node n8-merge` 的 AR(迭代+用户故事)/方案切增量清单与 PLAN 起点，缺失则裸任务自定增量（SKILL §2.4ter） | 任务描述, gate_a_verdict（high/low）, 考题或 spec 文件路径, workspace 路径, **上游 req-architect AR/方案 handoff（若同 slug 存在）** |
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd plugins/kdev-team && python3 -m pytest tests/test_cross_employee_handoff.py -v`
Expected: PASS（含新加 routing 2 个 + Task1 的 3 个）

- [ ] **Step 5: Commit**

```bash
git -c user.name=ly-AI -c user.email=ly1989abc@126.com add \
  plugins/kdev-team/tests/test_cross_employee_handoff.py \
  plugins/kdev-team/skills/kdev-flow-driver/references/node-agent-routing.md
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-team): node-agent-routing 接线跨员工 handoff（n8-merge 写 / n0-env+n3-plan 读上游）"
```

---

## Task 3: dev-engineer 业务 agent persona 读上游交付（env / plan）

**Files:**
- Modify: `plugins/kdev-team/tests/test_cross_employee_handoff.py`（追加 agent persona 断言）
- Modify: `plugins/kdev-team/agents/dev-engineer-env.md`
- Modify: `plugins/kdev-team/agents/dev-engineer-plan.md`

- [ ] **Step 1: Write the failing test**

追加：

```python
def test_dev_env_agent_reads_upstream_sr():
    """dev-engineer-env persona：读上游 req-architect 交付（SR+背景），缺失裸任务。"""
    t = _t(DEV_ENV)
    assert "handoff-read" in t
    assert "req-architect" in t
    assert ("裸任务" in t) or ("缺失" in t)


def test_dev_plan_agent_seeds_increments_from_upstream_ar():
    """dev-engineer-plan persona：上游 AR/方案在则以其用户故事/迭代切增量。"""
    t = _t(DEV_PLAN)
    assert "handoff-read" in t
    assert "req-architect" in t
    assert ("AR" in t) or ("用户故事" in t)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd plugins/kdev-team && python3 -m pytest tests/test_cross_employee_handoff.py -k "dev_env or dev_plan" -v`
Expected: FAIL（两 persona 暂无 `handoff-read`）

- [ ] **Step 3: 改 dev-engineer-env.md**

在 `## Critical Actions` 段（`- 产出 env.md...` 之前）插入一条：

```markdown
- **先读上游交付（P-B 跨员工 handoff）**：同 slug 下若存在需求架构师交付，`python3 -m kdev_core handoff-read coding-flow <slug> --employee req-architect --node n8-merge --workspace <ws>`，取 `gate_input.sr` / `summary` 作「项目背景对齐」的需求侧输入（SR + 背景），与 clone/蒸馏的工程侧基线合并进 env.md。**上游缺失（FlowStateError）→ 裸任务**：按现状只做工程侧环境对齐，不阻断（契约见 kdev-flow-driver SKILL §2.4ter）。
```

- [ ] **Step 4: 改 dev-engineer-plan.md**

在 `## Critical Actions` 段（`- **先定增量清单**...` 之前）插入一条：

```markdown
- **先读上游 AR/方案（P-B 跨员工 handoff）**：同 slug 下若存在需求架构师交付，`python3 -m kdev_core handoff-read coding-flow <slug> --employee req-architect --node n8-merge --workspace <ws>`，以 `gate_input.ar`(迭代+用户故事) / `gate_input.design`(方案) 作**增量清单与 PLAN.md 的起点**（用户故事/迭代天然对位「可独立 e2e 的纵向切片」）。**上游缺失 → 裸任务兜底**：按现有「定增量」红线自己判 N（契约见 kdev-flow-driver SKILL §2.4ter）。
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd plugins/kdev-team && python3 -m pytest tests/test_cross_employee_handoff.py -v`
Expected: PASS（全部）

- [ ] **Step 6: Commit**

```bash
git -c user.name=ly-AI -c user.email=ly1989abc@126.com add \
  plugins/kdev-team/tests/test_cross_employee_handoff.py \
  plugins/kdev-team/agents/dev-engineer-env.md \
  plugins/kdev-team/agents/dev-engineer-plan.md
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-team): dev-engineer env/plan persona 读上游 req-architect 交付（P-B 接线）"
```

---

## Task 4: req-architect 生产侧契约文档（orchestrator + node-table 注释）

**Files:**
- Modify: `plugins/kdev-team/tests/test_cross_employee_handoff.py`（追加 producer 断言）
- Modify: `plugins/kdev-team/agents/req-architect-orchestrator.md`
- Modify: `plugins/kdev-team/orchestration/req-architect.node-table.yml`

- [ ] **Step 1: Write the failing test**

追加：

```python
def test_req_orchestrator_n8_writes_cross_employee_handoff():
    """req-architect-orchestrator n8-merge 行：聚合 + 写跨员工交付 handoff。"""
    t = _t(REQ_ORCH)
    assert "handoff-write" in t
    assert "n8-merge" in t


def test_req_node_table_comment_notes_delivery_handoff():
    """req-architect node-table 注释提及 n8-merge 落跨员工交付 handoff。"""
    nt = (ROOT / "orchestration/req-architect.node-table.yml").read_text(encoding="utf-8")
    assert "handoff" in nt
    assert "n8-merge" in nt
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd plugins/kdev-team && python3 -m pytest tests/test_cross_employee_handoff.py -k "req_orchestrator or req_node_table" -v`
Expected: FAIL（orchestrator 无 `handoff-write`；node-table 无 `handoff`）

- [ ] **Step 3: 改 req-architect-orchestrator.md n8-merge 行**

把节点处理表里这一行：

```markdown
| n8-merge | 自做（编排聚合）| 阶段聚合报告 + 合并交付（output-merge-rules.md）|
```

替换为：

```markdown
| n8-merge | 自做（编排聚合）| 阶段聚合报告 + 合并交付（output-merge-rules.md）→ docs/design-flow/<slug>/；**收尾落跨员工交付 handoff**：`kdev_core handoff-write design-flow <slug> --employee req-architect --node n8-merge --status done --summary ... --artifact sr/ar/prototype/design --gate-input '{role→path}'`，供下游 coding-flow 同 slug `handoff-read` 当 spec/plan 输入（契约见 kdev-flow-driver SKILL §2.4ter）|
```

- [ ] **Step 4: 改 req-architect.node-table.yml 注释**

把这一行注释（约 line 15）：

```yaml
# 产物：运行时落 .kdev/features/<slug>/handoffs/req-architect/；记忆 scope .kdev/memory/staff/req-architect/。
```

替换为：

```yaml
# 产物：运行时落 .kdev/features/<slug>/handoffs/req-architect/；记忆 scope .kdev/memory/staff/req-architect/。
# 跨员工交付（P-B）：n8-merge 收尾落 handoff（handoff-write --employee req-architect --node n8-merge），
#   下游 dev-engineer coding-flow 同 slug handoff-read 当 spec/plan 输入。契约见 kdev-flow-driver SKILL §2.4ter。
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd plugins/kdev-team && python3 -m pytest tests/test_cross_employee_handoff.py -v`
Expected: PASS（全部）

- [ ] **Step 6: Commit**

```bash
git -c user.name=ly-AI -c user.email=ly1989abc@126.com add \
  plugins/kdev-team/tests/test_cross_employee_handoff.py \
  plugins/kdev-team/agents/req-architect-orchestrator.md \
  plugins/kdev-team/orchestration/req-architect.node-table.yml
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-team): req-architect n8-merge 落跨员工交付 handoff（生产侧契约）"
```

---

## Task 5: kdev-core 跨员工 handoff CLI 往返机制锁（零生产代码，纯测试）

**Files:**
- Modify: `plugins/kdev-core/tests/test_handoffs.py`

**说明**：纯复用既有 `handoff-write`/`handoff-read`，无新生产代码 → 本测试是**机制锁/特征测试**：证明 B 轨原语已覆盖「跨员工跨 flow、同 slug join」用法，并锁住路径/schema 防回归。用既有 `run_cli` fixture（`tests/conftest.py`，直调 `cli.main`，自动注入 `--workspace`）。预期**直接 PASS**（非红绿——无新产代码可红）。

- [ ] **Step 1: 追加跨员工 CLI 往返测试**

在 `plugins/kdev-core/tests/test_handoffs.py` 末尾追加：

```python
import json


def test_cross_employee_handoff_cli_roundtrip(run_cli):
    """P-B：生产方 req-architect 在 design-flow 落交付，消费方 dev-engineer
    在同 slug 上 coding-flow 读到——证明 B 轨原语零扩展覆盖跨员工跨 flow。"""
    slug = "user-auth"
    # 生产方写交付 manifest（artifacts + gate_input role→path 指针）
    gi = json.dumps({
        "sr": f".kdev/features/{slug}/handoffs/req-architect/sr.md",
        "ar": f".kdev/features/{slug}/handoffs/req-architect/ar.md",
        "design": f".kdev/features/{slug}/handoffs/req-architect/design.md",
    })
    out = run_cli([
        "handoff-write", "design-flow", slug,
        "--employee", "req-architect", "--node", "n8-merge",
        "--status", "done", "--summary", "SR/AR/方案 交付",
        "--artifact", f".kdev/features/{slug}/handoffs/req-architect/sr.md",
        "--artifact", f".kdev/features/{slug}/handoffs/req-architect/ar.md",
        "--gate-input", gi,
    ])
    assert "n8-merge.handoff.json" in out  # 落在生产方交接目录

    # 消费方（不同 flow / 同 slug / 指生产方 employee+node）读回
    read_out = run_cli([
        "handoff-read", "coding-flow", slug,
        "--employee", "req-architect", "--node", "n8-merge",
    ])
    data = json.loads(read_out)
    assert data["employee"] == "req-architect"
    assert data["status"] == "done"
    assert f".kdev/features/{slug}/handoffs/req-architect/sr.md" in data["artifacts"]
    assert json.loads(data["gate_input"] if isinstance(data["gate_input"], str)
                      else json.dumps(data["gate_input"]))["ar"].endswith("ar.md")


def test_cross_employee_missing_upstream_returns_nonzero(tmp_workspace):
    """消费方读不存在的上游交付 → cli.main 捕获 FlowStateError 返回 rc=1
    （已核 cli.py:368-371 catch+return 1，非抛异常）。编排据此回退裸任务，不静默成功。
    不走 run_cli（它断言 rc==0），直接调 cli.main。"""
    from kdev_core.cli import main as _cli_main
    rc = _cli_main([
        "handoff-read", "coding-flow", "no-such-feature",
        "--employee", "req-architect", "--node", "n8-merge",
        "--workspace", str(tmp_workspace),
    ])
    assert rc == 1
```

> 注（已核实，无需运行时分支）：`cli.main` 对 `FlowStateError/NodeMachineError/GateError/ValueError` 统一 `except → print(error) → return 1`（`plugins/kdev-core/kdev_core/cli.py:364-371`），**不冒泡异常**。故缺失用例直接 `assert rc == 1`，且必须绕开 `run_cli`（fixture 内 `assert rc == 0`）。

- [ ] **Step 2: Run test to verify it passes**

Run: `cd plugins/kdev-core && python3 -m pytest tests/test_handoffs.py -v`
Expected: PASS（原有 + 新增 2 个全绿）

- [ ] **Step 3: Commit**

```bash
git -c user.name=ly-AI -c user.email=ly1989abc@126.com add plugins/kdev-core/tests/test_handoffs.py
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "test(kdev-core): 跨员工 handoff CLI 往返机制锁（P-B 复用证明 + 缺失回退）"
```

---

## Task 6: bump kdev-team 版本 + CHANGELOG

**Files:**
- Modify: `plugins/kdev-team/.claude-plugin/plugin.json`
- Modify: `plugins/kdev-team/CHANGELOG.md`

- [ ] **Step 1: bump version**

`plugins/kdev-team/.claude-plugin/plugin.json` 把 `"version": "0.4.0"` 改为 `"version": "0.5.0"`。

- [ ] **Step 2: 写 CHANGELOG 条目**

在 `plugins/kdev-team/CHANGELOG.md` 顶部 `# Changelog` 之后插入：

```markdown
## 0.5.0 — 2026-06-12

**P-B：跨员工 handoff（需求架构师 SR/AR → 开发工程师 coding-flow 输入，M2 收口）**

- `kdev-flow-driver/SKILL.md` 新增 §2.4ter「跨员工 handoff（上游交付 → 下游 spec 输入）」：纯复用 B 轨 `handoff-write`/`handoff-read`，**join 键=同一 feature slug**；定义生产方→交付节点映射（`req-architect → n8-merge`）+ 上游缺失裸任务回退。**不新增 kdev-core 原语**（守「复用别重造」）。
- `references/node-agent-routing.md`：req-architect `n8-merge` 行加「收尾写交付 handoff」；dev-engineer `n0-env`/`n3-plan` 行加「先读同 slug 上游 req-architect 交付」。
- `dev-engineer-env`/`dev-engineer-plan` persona：加读上游交付（SR+背景 / AR+方案切增量），缺失回退裸任务。
- `req-architect-orchestrator` n8-merge + `req-architect.node-table.yml` 注释：补「落跨员工交付 handoff」生产侧契约。
- 编排仍走通用 `kdev-flow-driver`（G-008，不下放 orchestrator agent）；接 feature-first，不碰旧 `.kdev/flows/`。
- 测试：新增 `test_cross_employee_handoff.py`（SKILL/routing/persona/生产侧 契约不变量）；kdev-core 加 `test_handoffs.py` 跨员工 CLI 往返机制锁（零生产代码）。
- ⚠️ G-004：用户须刷 marketplace（`/plugin` 更新/重装）+ 重启 session 才生效。
```

- [ ] **Step 3: 跑全量回归确认不破**

Run: `cd plugins/kdev-team && python3 -m pytest -q && cd ../kdev-core && python3 -m pytest -q`
Expected: kdev-team 全绿（26 + 新增）、kdev-core 全绿（133 + 新增 2）

- [ ] **Step 4: Commit**

```bash
git -c user.name=ly-AI -c user.email=ly1989abc@126.com add \
  plugins/kdev-team/.claude-plugin/plugin.json \
  plugins/kdev-team/CHANGELOG.md
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "chore(kdev-team): bump v0.5.0 + CHANGELOG（P-B 跨员工 handoff）"
```

---

## Task 7: 轻 dogfood 验证（CLI 端到端跑一次跨员工交接）

**Files:** 无（仅运行验证，结果写进完成报告）

- [ ] **Step 1: 临时 workspace 跑一次真实 CLI 往返**

```bash
cd /home/lyadmin/Projects/kdev-agents-p-b-handoff
WS=$(mktemp -d)
# 生产方 req-architect 在 design-flow 落交付（模拟 n8-merge 收尾）
python3 -m kdev_core --help >/dev/null 2>&1 || export PYTHONPATH=plugins/kdev-core
PYTHONPATH=plugins/kdev-core python3 -m kdev_core handoff-write design-flow demo-login --workspace "$WS" \
  --employee req-architect --node n8-merge --status done \
  --summary "登录需求 SR/AR/方案 交付" \
  --artifact .kdev/features/demo-login/handoffs/req-architect/sr.md \
  --artifact .kdev/features/demo-login/handoffs/req-architect/ar.md \
  --gate-input '{"sr":".kdev/features/demo-login/handoffs/req-architect/sr.md","ar":".kdev/features/demo-login/handoffs/req-architect/ar.md"}'
# 消费方 dev-engineer 在 coding-flow 同 slug 读回
PYTHONPATH=plugins/kdev-core python3 -m kdev_core handoff-read coding-flow demo-login --workspace "$WS" \
  --employee req-architect --node n8-merge
echo "--- 落盘位置 ---"
find "$WS/.kdev/features/demo-login/handoffs" -type f
rm -rf "$WS"
```

Expected:
- `handoff-write` 打印 `<WS>/.kdev/features/demo-login/handoffs/req-architect/n8-merge.handoff.json`
- `handoff-read` 打印含 `"employee": "req-architect"`、`"status": "done"`、artifacts 含 sr/ar 路径的 JSON
- 落盘位置确认在 `.kdev/features/<slug>/handoffs/req-architect/`（用户确认的路径）

- [ ] **Step 2: 全量绿 + 记录证据**

Run: `cd plugins/kdev-core && python3 -m pytest -q && cd ../kdev-team && python3 -m pytest -q`
把两段 pytest 末行 + Step 1 的 read JSON 贴进完成报告，作为「接线通」验收证据（设计文档 §7 验收项 3：SR/AR 从 req-architect scope 流到 coding-flow 输入）。

---

## Self-Review（写完核对）

**1. Spec 覆盖（task §范围 1-4 + 设计 §6/§7）：**
- 范围1 handoff manifest 协议（谁产+路径+状态+slug，落 `.kdev/features/<slug>/handoffs/req-architect/`，复用 B 轨）→ Task 1（§2.4ter 契约）+ Task 4（生产侧）+ Task 5（机制锁）✅
- 范围2 coding-flow 入口接线（node0/node3 读上游 SR/AR）→ Task 2（routing）+ Task 3（persona）✅
- 范围3 验证（req-architect 产 → handoff → dev-engineer 读）→ Task 5（CLI 往返测试）+ Task 7（dogfood）✅
- 范围4 bump version + CHANGELOG → Task 6 ✅
- 设计 §7 验收 3「handoff 接线通」→ Task 7 Step 2 证据 ✅

**2. Placeholder 扫描：** 每步含确切路径 + 完整测试代码 + 确切命令与期望输出；无 TBD/TODO/"类似上文"。Task 5 缺失用例给了「据实际行为二选一」的两段完整代码 + 探测命令，非占位。✅

**3. 类型/命名一致：** 交付节点常量 `n8-merge` 在 SKILL/routing/persona/orchestrator/测试 全程一致；生产方 `req-architect`、消费 employee 参数一致；CLI flag（`--employee/--node/--status/--summary/--artifact/--gate-input`）与 `cli.py:333-347` 一致；handoff 文件名 `n8-merge.handoff.json` 与 `_handoff_status_path`（`<node_id>.handoff.json`）一致。✅

**硬约束核对：** 复用 B 轨原语不重造（kdev-core 零生产代码）✅；落 `.kdev/features/<slug>/handoffs/`（用户确认）✅；编排走通用 kdev-flow-driver 不下放 orchestrator（仅补契约文档）✅；接 feature-first 不碰旧 `.kdev/flows/` ✅。
